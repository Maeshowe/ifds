"""Regression tests for runner.py trading-day-guard SKIP path.

Background — the 2026-05-24 weekly cron crash:

The commit ``e9d617a2`` (2026-04-03, NYSE calendar introduction) added a
``trading day guard`` at the top of ``run_pipeline`` that short-circuits
when the day is not an NYSE trading day (weekend, holiday, etc.). The
guard logs an event before returning ``PipelineResult(success=True)``,
but it referenced ``EventType.PIPELINE_COMPLETE`` — a name that does
NOT exist in the EventType enum (only ``PIPELINE_START``, ``PIPELINE_END``,
``PIPELINE_HALT`` exist).

The bug was latent for ~7 weeks because:

1. The Sunday ``0 22 * * 0`` weekly cron is the ONLY scheduled invocation
   that always hits this path (Sundays are non-trading days).
2. ``tests/conftest.py`` globally sets ``IFDS_SKIP_TRADING_DAY_GUARD=1``
   which disables this code path in the unit-test suite, so no existing
   test exercised it.
3. The cron's stderr/stdout is captured to a file (``logs/cron_*.log``);
   nobody actively monitored those logs for AttributeError tracebacks.

Symptom (2026-05-24 22:00 cron run):

    Traceback (most recent call last):
      ...
      File "src/ifds/pipeline/runner.py", line 107, in run_pipeline
        logger.log(EventType.PIPELINE_COMPLETE, Severity.INFO, message=msg)
    AttributeError: type object 'EventType' has no attribute 'PIPELINE_COMPLETE'

Impact: the entire Phase 1-3 weekly refresh (BMI, universe, sector
rotation) failed silently every Sunday from 2026-04-03 to 2026-05-24 —
~8 weekly cycles. Phase 4-6 intraday continued with ``state/phase13_ctx.json.gz``
stale by up to 7 days, contaminating sector ranking + universe screening
downstream.

These regression tests guarantee:

1. ``EventType.PIPELINE_END`` exists (the correct enum value).
2. ``EventType.PIPELINE_COMPLETE`` does NOT exist — the source code
   must not reference it (caught by static check on the source file).
3. The SKIP path returns ``success=True`` without raising AttributeError
   (caught by exercising the path with mocks).

Refs: 2026-05-24-Phase13-cron-crash incident,
operator-emergency-procedure.md Pattern 5.
"""

from __future__ import annotations

import inspect
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from ifds.events.types import EventType


def test_pipeline_end_enum_exists() -> None:
    """``EventType.PIPELINE_END`` must exist (the correct lifecycle value)."""
    assert EventType.PIPELINE_END.value == "PIPELINE_END"


def test_pipeline_complete_enum_does_not_exist() -> None:
    """``EventType.PIPELINE_COMPLETE`` must NOT exist (the 2026-05-24 bug name).

    If a future contributor reintroduces this, they must also add the
    matching enum value to ``ifds/events/types.py`` — otherwise the
    runtime AttributeError reproduces.
    """
    with pytest.raises(AttributeError):
        _ = EventType.PIPELINE_COMPLETE  # type: ignore[attr-defined]


def test_runner_source_does_not_reference_pipeline_complete() -> None:
    """Static guard: ``runner.run_pipeline`` source must not reference
    the broken enum name. Catches regressions even before the trading
    day guard branch is exercised."""
    from ifds.pipeline import runner

    src = inspect.getsource(runner.run_pipeline)
    assert "EventType.PIPELINE_COMPLETE" not in src, (
        "runner.run_pipeline references EventType.PIPELINE_COMPLETE which "
        "does not exist in the EventType enum. Use EventType.PIPELINE_END. "
        "See 2026-05-24 weekly Phase 1-3 cron crash."
    )


def test_trading_day_guard_skip_path_does_not_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The NYSE-closed-today SKIP path must return ``success=True`` and
    NOT raise AttributeError.

    Reproduces the 2026-05-24 production crash conditions:

    - Trading-day guard is ENABLED (env override cleared)
    - ``is_nyse_trading_day`` returns False (Sunday / holiday)
    - ``dry_run=False`` (matches production cron invocation)
    """
    # conftest.py sets IFDS_SKIP_TRADING_DAY_GUARD=1 globally — clear it
    # for this test so the guard actually engages.
    monkeypatch.delenv("IFDS_SKIP_TRADING_DAY_GUARD", raising=False)

    # Required env for IFDS Config.from_env() — minimal viable keys.
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_UW_API_KEY", "test_uw")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")

    # Disable side-effect env (Telegram + other external integrations)
    monkeypatch.delenv("IFDS_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("IFDS_TELEGRAM_CHAT_ID", raising=False)

    from ifds.pipeline.runner import run_pipeline

    # Force the NYSE-closed branch
    with patch(
        "ifds.utils.calendar.is_nyse_trading_day", return_value=False
    ), patch(
        "ifds.utils.calendar.get_holiday_name",
        return_value="Test Holiday",
    ):
        result = run_pipeline(phase=None, dry_run=False)

    assert result.success is True
    assert "NYSE closed" in (result.message or "")
