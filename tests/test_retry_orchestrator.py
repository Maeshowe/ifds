"""Tests for scripts/paper_trading/lib/retry_orchestrator.py

Covers the Day 3 (2026-05-20) Gateway-down scenario: outer retry with
exponential backoff, state reload between attempts, gateway probe gating,
non-retryable error propagation, Telegram critical on exhaustion.

Refs:
    docs/tasks/2026-05-21-submit-retry-storm.md
"""

import os
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _ensure_lib_importable():
    """Add scripts/paper_trading to sys.path so ``from lib.retry_orchestrator`` works."""
    pt_dir = str(Path(__file__).resolve().parent.parent / "scripts" / "paper_trading")
    added = pt_dir not in sys.path
    if added:
        sys.path.insert(0, pt_dir)
    yield
    if added:
        sys.path.remove(pt_dir)


@pytest.fixture
def fake_sleep():
    """A no-op sleep so backoff timing does not slow the test suite."""
    calls: list[float] = []

    def _sleep(seconds: float) -> None:
        calls.append(seconds)

    _sleep.calls = calls  # type: ignore[attr-defined]
    return _sleep


def _make_orchestrator(submit_callable, gateway_check=None, telegram=None,
                       sleep=None, max_attempts=5, initial_backoff=15):
    from lib.retry_orchestrator import IBKRSubmitOrchestrator
    return IBKRSubmitOrchestrator(
        submit_callable=submit_callable,
        gateway_check=gateway_check,
        telegram_notify=telegram,
        max_attempts=max_attempts,
        initial_backoff_seconds=initial_backoff,
        _sleep=sleep if sleep is not None else (lambda s: None),
    )


# ---------------------------------------------------------------------------
# 1. First attempt succeeds — no retries
# ---------------------------------------------------------------------------

class TestHappyPath:

    def test_first_attempt_succeeds_no_retry(self, fake_sleep):
        """Submit callable returns successfully on first attempt — no backoff."""
        submit_calls = []

        def submit(**kwargs):
            submit_calls.append(kwargs)
            return {"submitted": ["VLO"]}

        orch = _make_orchestrator(submit, sleep=fake_sleep)
        result = orch.submit_with_retry(today_str="2026-05-21", tickers=[])

        assert result == {"submitted": ["VLO"]}
        assert len(submit_calls) == 1
        assert fake_sleep.calls == [], "No backoff should fire on first-success"
        assert len(orch.history) == 1
        assert orch.history[0].success is True


# ---------------------------------------------------------------------------
# 2. Retryable failure twice, then succeed
# ---------------------------------------------------------------------------

class TestRetryableFailure:

    def test_retries_until_success(self, fake_sleep):
        """Connect fails twice, succeeds on third attempt."""
        from lib.connection import IBKRConnectionExhausted

        attempts = {"n": 0}

        def submit(**kwargs):
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise IBKRConnectionExhausted(f"Gateway down attempt {attempts['n']}")
            return {"submitted": ["VLO", "ON", "CNC"]}

        orch = _make_orchestrator(submit, sleep=fake_sleep)
        result = orch.submit_with_retry()

        assert result["submitted"] == ["VLO", "ON", "CNC"]
        assert attempts["n"] == 3
        # Two backoffs (after attempt 1 + after attempt 2)
        assert fake_sleep.calls == [15, 30]
        assert [h.success for h in orch.history] == [False, False, True]


# ---------------------------------------------------------------------------
# 3. All retries exhausted → SubmitExhaustedError + Telegram
# ---------------------------------------------------------------------------

class TestRetriesExhausted:

    def test_all_attempts_fail_raises_exhausted(self, fake_sleep):
        """5 retryable failures → SubmitExhaustedError, Telegram notified."""
        from lib.connection import IBKRConnectionExhausted
        from lib.retry_orchestrator import SubmitExhaustedError

        tg_messages: list[str] = []

        def submit(**kwargs):
            raise IBKRConnectionExhausted("gateway never recovers")

        def telegram(msg: str) -> None:
            tg_messages.append(msg)

        orch = _make_orchestrator(submit, telegram=telegram, sleep=fake_sleep)
        with pytest.raises(SubmitExhaustedError) as exc_info:
            orch.submit_with_retry()

        assert isinstance(exc_info.value.last_error, IBKRConnectionExhausted)
        # 5 attempts → 4 inter-attempt backoffs: 15, 30, 60, 120
        assert fake_sleep.calls == [15, 30, 60, 120]
        assert len(tg_messages) == 1
        assert "SUBMIT EXHAUSTED" in tg_messages[0]
        assert "manual intervention" in tg_messages[0]
        assert "submit_orders.py --resume" in tg_messages[0]


# ---------------------------------------------------------------------------
# 4. Non-retryable exception propagates immediately
# ---------------------------------------------------------------------------

class TestNonRetryablePropagates:

    def test_value_error_propagates_no_retry(self, fake_sleep):
        """ValueError (not in retryable_exceptions) propagates on first attempt."""
        def submit(**kwargs):
            raise ValueError("malformed execution plan: missing 'limit_price' column")

        orch = _make_orchestrator(submit, sleep=fake_sleep)
        with pytest.raises(ValueError, match="malformed execution plan"):
            orch.submit_with_retry()

        # Exactly one attempt, no backoff
        assert len(orch.history) == 1
        assert fake_sleep.calls == []


# ---------------------------------------------------------------------------
# 5. Gateway probe gates the attempt
# ---------------------------------------------------------------------------

class TestGatewayProbe:

    def test_probe_returns_false_triggers_backoff_without_submit(self, fake_sleep):
        """Gateway probe down → no submit call, just backoff."""
        submit_calls = []

        def submit(**kwargs):
            submit_calls.append(kwargs)
            return {"submitted": []}

        probe_calls = {"n": 0}

        def probe() -> bool:
            probe_calls["n"] += 1
            if probe_calls["n"] < 3:
                return False
            return True  # third attempt: probe up

        orch = _make_orchestrator(submit, gateway_check=probe, sleep=fake_sleep)
        result = orch.submit_with_retry()

        assert result == {"submitted": []}
        assert len(submit_calls) == 1, (
            "Submit should run only after probe returns True (attempt 3)"
        )
        # Probe was called 3 times. First two probes returned False → backoff after
        # each. Third probe returned True → submit ran → no further backoff.
        assert probe_calls["n"] == 3
        assert fake_sleep.calls == [15, 30]

    def test_probe_raises_treated_as_down(self, fake_sleep):
        """Probe raising an exception → treated as down (NOT propagated)."""
        from lib.retry_orchestrator import SubmitExhaustedError

        def submit(**kwargs):
            return {"submitted": []}

        def probe() -> bool:
            raise OSError("socket refused")

        orch = _make_orchestrator(
            submit, gateway_check=probe, sleep=fake_sleep, max_attempts=2,
        )
        with pytest.raises(SubmitExhaustedError):
            orch.submit_with_retry()
        # 2 attempts → 1 backoff
        assert fake_sleep.calls == [15]


# ---------------------------------------------------------------------------
# 6. Exponential backoff schedule (15s → 30s → 60s → 120s → 240s)
# ---------------------------------------------------------------------------

class TestBackoffSchedule:

    def test_backoff_seconds_doubles_per_attempt(self):
        from lib.retry_orchestrator import IBKRSubmitOrchestrator

        orch = IBKRSubmitOrchestrator(
            submit_callable=lambda **k: None,
            initial_backoff_seconds=15,
        )
        assert orch.backoff_seconds(1) == 15
        assert orch.backoff_seconds(2) == 30
        assert orch.backoff_seconds(3) == 60
        assert orch.backoff_seconds(4) == 120
        assert orch.backoff_seconds(5) == 240


# ---------------------------------------------------------------------------
# 7. State reload between attempts — submit_callable invoked with the same
#    kwargs each time, so its inner load_swing_positions runs fresh.
# ---------------------------------------------------------------------------

class TestStateReloadBetweenAttempts:

    def test_kwargs_passed_unchanged_every_attempt(self, fake_sleep):
        """The orchestrator passes identical kwargs each attempt; the submit
        callable is responsible for reloading state internally.
        """
        from lib.connection import IBKRConnectionExhausted

        seen_kwargs = []

        def submit(**kwargs):
            seen_kwargs.append(dict(kwargs))
            if len(seen_kwargs) < 2:
                raise IBKRConnectionExhausted("first attempt down")
            return "ok"

        orch = _make_orchestrator(submit, sleep=fake_sleep)
        orch.submit_with_retry(
            tickers=[{"symbol": "VLO"}], today_str="2026-05-21", cfg=None,
        )

        assert len(seen_kwargs) == 2
        assert seen_kwargs[0] == seen_kwargs[1], (
            "Same kwargs each attempt — submit_callable's internal "
            "load_swing_positions does the per-attempt state refresh."
        )


# ---------------------------------------------------------------------------
# 8. Telegram notify failure does NOT mask the SubmitExhaustedError
# ---------------------------------------------------------------------------

class TestTelegramFailureNonBlocking:

    def test_telegram_send_failure_swallowed(self, fake_sleep):
        """If telegram_notify raises, the orchestrator still raises SubmitExhausted."""
        from lib.connection import IBKRConnectionExhausted
        from lib.retry_orchestrator import SubmitExhaustedError

        def submit(**kwargs):
            raise IBKRConnectionExhausted("gateway down")

        def bad_telegram(msg: str) -> None:
            raise RuntimeError("telegram API outage")

        orch = _make_orchestrator(
            submit, telegram=bad_telegram, sleep=fake_sleep, max_attempts=2,
        )
        with pytest.raises(SubmitExhaustedError):
            orch.submit_with_retry()
