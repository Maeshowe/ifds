"""Regression guard: PTEventLogger must never write to the production
``logs/pt_events_{today}.jsonl`` during the test suite (test-env-hygiene P1,
2026-07-23 daily review §6).

Root cause
----------
Every ``scripts/paper_trading/*.py`` instantiates a **module-level**
``evt = PTEventLogger()`` at import time with the default ``log_dir="logs"``.
Any test that imports one of those scripts (``test_close_positions_split``,
``test_monitor_positions``, ``test_pipeline_e2e``, …) or exercises the legacy
circuit_breaker / trail paths appended fixture events (AAA/BBB/CCC tickers,
``circuit_breaker cum_pnl=-6000``, ``moc_submitted``) to the real production
log. The 2026-07-23 run leaked 176 such events; the recurring 47-line/7613-byte
Sunday signature shows the ``deploy_daily.sh`` Phase 1-3 cron pre-flight pytest
polluted the log every week.

Fix
---
``PTEventLogger`` reads ``IFDS_PT_EVENT_DIR`` (default ``"logs"`` — behaviour
invariant when unset). ``tests/conftest.py`` sets that env var to a tmp dir at
module top (before collection), so every import-time logger redirects there.

This is the third instance of the test-env-hygiene rule (after
phase4_snapshot / 2026-04-15 and uw_shadow / 2026-05-19): a test must never
write into production ``state/`` / ``logs/`` / ``output/``.
"""

import glob
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PROD_LOG_DIR = _REPO_ROOT / "logs"


@pytest.fixture(autouse=True)
def _ensure_lib_importable():
    """Add scripts/paper_trading to sys.path so ``from lib.event_logger`` works."""
    pt_dir = str(_REPO_ROOT / "scripts" / "paper_trading")
    added = pt_dir not in sys.path
    if added:
        sys.path.insert(0, pt_dir)
    yield
    if added:
        sys.path.remove(pt_dir)


def _prod_log_snapshot():
    """Filename → mtime map of the production pt_events logs."""
    return {
        p: os.stat(p).st_mtime
        for p in glob.glob(str(_PROD_LOG_DIR / "pt_events_*.jsonl"))
    }


def test_conftest_sets_isolated_event_dir():
    """conftest.py redirects the event log away from production ``logs/``."""
    event_dir = os.environ.get("IFDS_PT_EVENT_DIR")
    assert event_dir, "conftest.py must set IFDS_PT_EVENT_DIR for the suite"
    assert Path(event_dir).resolve() != _PROD_LOG_DIR.resolve(), (
        "IFDS_PT_EVENT_DIR must not point at the production logs/ dir"
    )


def test_default_logger_honors_isolation_env(monkeypatch, tmp_path):
    """A no-arg ``PTEventLogger()`` (as the scripts create it) writes under
    IFDS_PT_EVENT_DIR, not into ``logs/``."""
    from lib.event_logger import PTEventLogger

    monkeypatch.setenv("IFDS_PT_EVENT_DIR", str(tmp_path))
    logger = PTEventLogger()

    assert Path(logger.path).parent.resolve() == tmp_path.resolve()


def test_production_pt_events_untouched_by_logging(monkeypatch, tmp_path):
    """mtime-invariance: exercising the offending path (a default logger writing
    a legacy circuit_breaker/moc event) must not touch production ``logs/``."""
    from lib.event_logger import PTEventLogger

    monkeypatch.setenv("IFDS_PT_EVENT_DIR", str(tmp_path))
    before = _prod_log_snapshot()

    logger = PTEventLogger()
    logger.log("close", "moc_submitted", ticker="AAA", cum_pnl=-6000)
    logger.log("submit", "circuit_breaker", ticker="BBB")

    assert _prod_log_snapshot() == before, (
        "test wrote into production logs/pt_events_*.jsonl — isolation failed"
    )
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert (tmp_path / f"pt_events_{today}.jsonl").exists()


def test_default_is_logs_without_env(monkeypatch):
    """Behaviour-invariance proof: with IFDS_PT_EVENT_DIR unset the default is
    still ``logs/`` — the production cron path is bit-identical."""
    from lib.event_logger import PTEventLogger

    monkeypatch.delenv("IFDS_PT_EVENT_DIR", raising=False)
    logger = PTEventLogger()

    assert Path(logger.path).parent == Path("logs")
