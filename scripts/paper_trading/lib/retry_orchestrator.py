"""IBKR submit orchestrator — autonomous outer retry on Gateway disconnect.

Day 3 (2026-05-20) incident: the 15:31 CEST submit_orders cron exhausted
its inner connect() retries (3× 5s) within ~30 seconds while the IBKR
Gateway was down (15:25→16:00 window). The legacy code path then called
``sys.exit(1)`` and **never re-attempted** even though the Gateway
recovered ~16:00. Manual operator intervention (Tamás) was required to
re-trigger the submit at 16:05.

This module wraps the submit function in an **outer retry loop** with
exponential backoff that spans the typical Gateway outage window
(~5-20 min). State is reloaded on each attempt so the existing-position
deduplication remains correct (avoids double-submits).

Wiring
------

::

    from lib.retry_orchestrator import (
        IBKRSubmitOrchestrator, SubmitExhaustedError,
    )
    from lib.connection import IBKRConnectionExhausted

    orchestrator = IBKRSubmitOrchestrator(
        submit_callable=submit_swing_market_only,
        gateway_check=check_gateway_alive,
    )
    try:
        result = orchestrator.submit_with_retry(
            tickers=tickers, dry_run=args.dry_run,
            today_str=today_str, cfg=cfg,
            swing_state_file=state_file,
        )
    except SubmitExhaustedError as exc:
        logger.error(f"[SUBMIT_EXHAUSTED] {exc}")
        sys.exit(1)

Refs:
    docs/tasks/2026-05-21-submit-retry-storm.md
    docs/review/2026-05-20-daily-review.md §0.5
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("submit_retry_orchestrator")


class SubmitExhaustedError(Exception):
    """Raised by ``IBKRSubmitOrchestrator.submit_with_retry`` after all
    outer attempts fail. The underlying error chain is attached.

    The caller is responsible for the final ``sys.exit(1)`` and any
    user-facing notification beyond the Telegram critical alert that
    the orchestrator has already sent.
    """

    def __init__(self, message: str, last_error: BaseException | None = None):
        super().__init__(message)
        self.last_error = last_error


@dataclass
class SubmitAttemptResult:
    """One outer attempt result. Used internally for diagnostics."""

    attempt: int
    success: bool
    error: BaseException | None = None
    duration_seconds: float = 0.0


@dataclass
class IBKRSubmitOrchestrator:
    """Orchestrates a submit-callable with autonomous outer retry.

    The wrapped ``submit_callable`` is expected to:

    * Establish its own IBKR connection (via ``connect(...,
      raise_on_exhaust=True)`` from ``lib.connection``).
    * Load the latest swing-positions state and execution plan internally,
      so a re-attempt on a later outer cycle picks up any intervening
      state changes (e.g. a fill that arrived after a partial submit).
    * Either return a result-like object, or raise an exception that the
      orchestrator can classify as retryable.

    Retryable exceptions (the orchestrator keeps trying):
      * ``IBKRConnectionExhausted`` from ``lib.connection``
      * Any exception type listed in ``retryable_exceptions``

    Non-retryable exceptions propagate immediately (e.g. malformed
    execution plan CSV, missing config — operator must fix and re-run).

    Parameters
    ----------
    submit_callable:
        Function that performs the actual submit. Called with all the
        kwargs passed to :meth:`submit_with_retry`.
    gateway_check:
        Optional cheap probe (returns ``bool``) run BEFORE the
        ``submit_callable`` on each outer attempt. If it returns False
        the attempt is skipped (counted) and the backoff starts.
    telegram_notify:
        Optional function ``(message: str) -> None`` called with the
        critical alert when all attempts are exhausted.
    max_attempts:
        Outer retry count (default 5). The first attempt is the initial
        submit; subsequent attempts are retries.
    initial_backoff_seconds:
        Base backoff seconds (default 15). Doubles each retry:
        15s → 30s → 60s → 120s → 240s. Total wait across 4 backoffs
        between 5 attempts: ~7.75 minutes.
    retryable_exceptions:
        Tuple of exception types treated as retryable. Defaults to a
        small set; callers can extend it for custom error types.
    """

    submit_callable: Callable[..., Any]
    gateway_check: Callable[[], bool] | None = None
    telegram_notify: Callable[[str], None] | None = None
    max_attempts: int = 5
    initial_backoff_seconds: int = 15
    retryable_exceptions: tuple[type[BaseException], ...] = field(default_factory=tuple)
    _sleep: Callable[[float], None] = time.sleep
    history: list[SubmitAttemptResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Late-imported so the lib.connection module is optional in unit
        # tests that drive the orchestrator with pure mocks.
        if not self.retryable_exceptions:
            try:
                from lib.connection import IBKRConnectionExhausted

                self.retryable_exceptions = (IBKRConnectionExhausted, ConnectionError)
            except ImportError:
                self.retryable_exceptions = (ConnectionError,)

    def backoff_seconds(self, attempt: int) -> int:
        """Exponential backoff: 15s, 30s, 60s, 120s, 240s.

        ``attempt`` is the 1-indexed attempt number that just failed.
        Returns the wait before the NEXT attempt.
        """
        return self.initial_backoff_seconds * (2 ** (attempt - 1))

    def submit_with_retry(self, **kwargs: Any) -> Any:
        """Run the submit callable with outer retry.

        Returns the submit_callable's return value on the first
        successful attempt. Raises :class:`SubmitExhaustedError` if all
        attempts fail with retryable errors.
        """
        self.history.clear()
        last_error: BaseException | None = None

        for attempt in range(1, self.max_attempts + 1):
            attempt_start = time.monotonic()

            if self.gateway_check is not None:
                try:
                    alive = self.gateway_check()
                except Exception as exc:
                    logger.warning(
                        f"[RETRY {attempt}/{self.max_attempts}] gateway_check "
                        f"raised {type(exc).__name__}: {exc} — treating as down"
                    )
                    alive = False
                if not alive:
                    duration = time.monotonic() - attempt_start
                    self.history.append(
                        SubmitAttemptResult(
                            attempt=attempt,
                            success=False,
                            error=ConnectionError("gateway_check returned False"),
                            duration_seconds=duration,
                        )
                    )
                    if attempt < self.max_attempts:
                        delay = self.backoff_seconds(attempt)
                        logger.warning(
                            f"[RETRY {attempt}/{self.max_attempts}] Gateway "
                            f"probe down. Backing off {delay}s before next attempt..."
                        )
                        self._sleep(delay)
                    last_error = self.history[-1].error
                    continue

            try:
                result = self.submit_callable(**kwargs)
                duration = time.monotonic() - attempt_start
                self.history.append(
                    SubmitAttemptResult(
                        attempt=attempt,
                        success=True,
                        duration_seconds=duration,
                    )
                )
                logger.info(
                    f"[SUBMIT_OK attempt={attempt}/{self.max_attempts}] "
                    f"completed in {duration:.1f}s"
                )
                return result

            except self.retryable_exceptions as exc:
                duration = time.monotonic() - attempt_start
                last_error = exc
                self.history.append(
                    SubmitAttemptResult(
                        attempt=attempt,
                        success=False,
                        error=exc,
                        duration_seconds=duration,
                    )
                )
                logger.warning(
                    f"[RETRY {attempt}/{self.max_attempts}] "
                    f"{type(exc).__name__}: {exc} "
                    f"(attempt duration {duration:.1f}s)"
                )
                if attempt < self.max_attempts:
                    delay = self.backoff_seconds(attempt)
                    logger.info(f"Backing off {delay}s before next attempt...")
                    self._sleep(delay)

            except Exception as exc:
                # Non-retryable — propagate immediately so the operator
                # can fix the root cause (malformed plan, config error, …).
                duration = time.monotonic() - attempt_start
                self.history.append(
                    SubmitAttemptResult(
                        attempt=attempt,
                        success=False,
                        error=exc,
                        duration_seconds=duration,
                    )
                )
                logger.error(
                    f"[SUBMIT_FATAL attempt={attempt}/{self.max_attempts}] "
                    f"non-retryable {type(exc).__name__}: {exc}"
                )
                raise

        # All retries exhausted
        message = (
            f"\U0001f6a8 <b>SUBMIT EXHAUSTED</b> — manual intervention required\n"
            f"Attempts: {self.max_attempts}/{self.max_attempts}\n"
            f"Last error: {type(last_error).__name__ if last_error else 'n/a'}: "
            f"{last_error}\n"
            f"Manual resubmit: <code>python scripts/paper_trading/"
            f"submit_orders.py --resume</code>"
        )
        logger.error(
            f"[SUBMIT_EXHAUSTED] All {self.max_attempts} attempts failed. "
            f"Last error: {last_error}"
        )
        if self.telegram_notify is not None:
            try:
                self.telegram_notify(message)
            except Exception as tg_exc:
                logger.warning(
                    f"Telegram critical alert failed: {tg_exc}. "
                    f"Continuing with SubmitExhaustedError raise."
                )
        raise SubmitExhaustedError(
            f"Max retries ({self.max_attempts}) exhausted",
            last_error=last_error,
        )
