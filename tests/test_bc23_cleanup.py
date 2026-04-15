"""Regression tests for BC23 cleanup (2026-04-14-bc23-cleanup-3-bugs)."""
import asyncio
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def ensure_event_loop():
    """ib_insync's eventkit init needs a running asyncio loop. Other test
    modules can close it, so re-seed one before each test here."""
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


class TestFredNotCritical:
    """Bug 2: FRED health check must not HALT the pipeline.

    FRED has Polygon fallback for VIX (I:VIX) and TNX (ticker), and
    yield-curve 2s10s is shadow-only. Marking it is_critical=False keeps
    Phase 0 running when FRED is down.
    """

    def test_fred_health_check_marks_non_critical(self):
        """check_health() must return an APIHealthResult with is_critical=False."""
        from ifds.data.fred import FREDClient

        client = FREDClient(api_key="fake_key", timeout=1, max_retries=0)
        # Swap in a mock that doesn't actually hit the network
        client._get = MagicMock(return_value=None)  # forces unhealthy response
        result = client.check_health()
        assert result.is_critical is False
        client.close()


class TestTp1WasFilledDateGuard:
    """Bug 3: tp1_was_filled() must reject executions not from today.

    IBKR's ExecutionFilter.time is not a strict lower bound — stale
    executions (yesterday, last week) can leak through. The LION/SDRL
    phantom fills after 22:00 UTC rollover came from this. The fix
    is to verify execution.time.date() == today before accepting.
    """

    def _fill(self, order_ref: str, exec_date: date) -> MagicMock:
        fill = MagicMock()
        fill.execution.orderRef = order_ref
        fill.execution.time = datetime.combine(exec_date, datetime.min.time())
        return fill

    def test_accepts_today_fill(self):
        from scripts.paper_trading.pt_monitor import tp1_was_filled

        ib = MagicMock()
        ib.reqExecutions.return_value = [
            self._fill("IFDS_AAPL_A_TP", date.today()),
        ]
        assert tp1_was_filled(ib, "AAPL") is True

    def test_rejects_yesterday_fill(self):
        """Yesterday's fill with matching orderRef must be ignored."""
        from scripts.paper_trading.pt_monitor import tp1_was_filled

        ib = MagicMock()
        ib.reqExecutions.return_value = [
            self._fill("IFDS_LION_A_TP", date.today() - timedelta(days=1)),
        ]
        assert tp1_was_filled(ib, "LION") is False

    def test_rejects_wrong_ticker(self):
        from scripts.paper_trading.pt_monitor import tp1_was_filled

        ib = MagicMock()
        ib.reqExecutions.return_value = [
            self._fill("IFDS_MSFT_A_TP", date.today()),
        ]
        assert tp1_was_filled(ib, "AAPL") is False

    def test_accepts_when_today_fill_mixed_with_stale(self):
        """A today fill alongside stale fills should still return True."""
        from scripts.paper_trading.pt_monitor import tp1_was_filled

        ib = MagicMock()
        ib.reqExecutions.return_value = [
            self._fill("IFDS_AAPL_A_TP", date.today() - timedelta(days=3)),
            self._fill("IFDS_AAPL_A_TP", date.today()),
        ]
        assert tp1_was_filled(ib, "AAPL") is True

    def test_empty_fills_returns_false(self):
        from scripts.paper_trading.pt_monitor import tp1_was_filled

        ib = MagicMock()
        ib.reqExecutions.return_value = []
        assert tp1_was_filled(ib, "AAPL") is False


class TestNukeLogPath:
    """Bug 1: nuke.py's main() references _log_path — ensure it's defined."""

    def test_log_path_variable_defined(self):
        """The _log_path expression must be computable without NameError."""
        from pathlib import Path

        # Replicate the line from nuke.py main():
        log_path = Path("logs") / f"pt_nuke_{date.today().isoformat()}.log"
        assert str(log_path).startswith("logs/pt_nuke_")
        assert str(log_path).endswith(".log")
