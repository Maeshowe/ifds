"""Tests for EOD report idempotency guard.

Covers: duplicate day skipped, different days both recorded.
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture(autouse=True)
def _isolate_eod_env():
    """Prevent eod_report.py load_dotenv() from polluting env."""
    mod_key = "scripts.paper_trading.eod_report"
    cached = sys.modules.pop(mod_key, None)
    env_before = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(env_before)
    sys.modules.pop(mod_key, None)
    if cached is not None:
        sys.modules[mod_key] = cached


def _make_trades(pnl_values):
    """Create mock trade dicts."""
    return [{'pnl': pnl, 'exit_type': 'MOC'} for pnl in pnl_values]


class TestEODIdempotency:
    """update_cumulative_pnl() idempotency guard."""

    def test_eod_idempotency_second_run_skipped(self, tmp_path):
        """Second run on same day does not modify cumulative data."""
        pnl_file = tmp_path / "cumulative_pnl.json"
        trades = _make_trades([100.0, -30.0])

        with patch.dict("sys.modules", {
            "dotenv": MagicMock(),
        }):
            import scripts.paper_trading.eod_report as eod
            # Override file paths
            eod.CUMULATIVE_PNL_FILE = str(pnl_file)
            eod.LOG_DIR = str(tmp_path)

            # First run
            data1, pnl1 = eod.update_cumulative_pnl(trades, "2026-02-25")
            cum_after_first = data1['cumulative_pnl']
            days_after_first = data1['trading_days']
            history_len_first = len(data1['daily_history'])

            # Second run — same date
            data2, pnl2 = eod.update_cumulative_pnl(trades, "2026-02-25")
            assert data2['cumulative_pnl'] == cum_after_first
            assert data2['trading_days'] == days_after_first
            assert len(data2['daily_history']) == history_len_first

    def test_eod_different_days_both_recorded(self, tmp_path):
        """Two different days are both recorded."""
        pnl_file = tmp_path / "cumulative_pnl.json"
        trades_day1 = _make_trades([100.0])
        trades_day2 = _make_trades([50.0])

        with patch.dict("sys.modules", {
            "dotenv": MagicMock(),
        }):
            import scripts.paper_trading.eod_report as eod
            eod.CUMULATIVE_PNL_FILE = str(pnl_file)
            eod.LOG_DIR = str(tmp_path)

            data1, _ = eod.update_cumulative_pnl(trades_day1, "2026-02-25")
            data2, _ = eod.update_cumulative_pnl(trades_day2, "2026-02-26")

            assert data2['trading_days'] == 2
            assert len(data2['daily_history']) == 2
            assert data2['cumulative_pnl'] == 150.0
