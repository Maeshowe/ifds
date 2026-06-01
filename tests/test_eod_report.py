"""Tests for eod_report commission handling under the Part A read-only model.

P0 §0.11 Part A: eod_report.update_cumulative_pnl no longer writes
cumulative_pnl.json, so it no longer persists commission into daily_history.
Commission that lands in cumulative_pnl.json now comes from
daily_metrics.record_pending_exits (commission delta from the IBKR
executions) — covered in tests/test_record_pending_exits.py. eod_report
still aggregates commission for the Telegram/CSV display from the trade list.
These tests pin the new read-only contract.
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


def _make_trades(commission_values):
    """Create mock trade dicts with commission."""
    return [{"pnl": 100.0, "commission": comm, "exit_type": "MOC"} for comm in commission_values]


def _import_eod(tmp_path, pnl_file):
    import scripts.paper_trading.eod_report as eod

    eod.CUMULATIVE_PNL_FILE = str(pnl_file)
    eod.LOG_DIR = str(tmp_path)
    return eod


class TestEODCommissionReadOnly:
    """update_cumulative_pnl no longer persists commission (read-only)."""

    def test_no_file_created_no_daily_history_appended(self, tmp_path):
        pnl_file = tmp_path / "cumulative_pnl.json"
        trades = _make_trades([10.50, 5.25, 3.75])
        with patch.dict("sys.modules", {"dotenv": MagicMock()}):
            eod = _import_eod(tmp_path, pnl_file)
            data, daily_pnl = eod.update_cumulative_pnl(trades, "2026-03-17")
            # daily_pnl is still computed for display
            assert daily_pnl == 300.0
            # but nothing is persisted and no entry is appended
            assert data["daily_history"] == []
            assert not pnl_file.exists()

    def test_existing_file_commission_untouched(self, tmp_path):
        pnl_file = tmp_path / "cumulative_pnl.json"
        existing = {
            "start_date": "2026-03-10",
            "initial_capital": 100000,
            "trading_days": 1,
            "cumulative_pnl": 100.0,
            "cumulative_pnl_pct": 0.1,
            "daily_history": [{"date": "2026-03-16", "pnl": 100.0, "commission": 7.0}],
        }
        pnl_file.write_text(json.dumps(existing))
        before = pnl_file.read_text()
        with patch.dict("sys.modules", {"dotenv": MagicMock()}):
            eod = _import_eod(tmp_path, pnl_file)
            data, daily_pnl = eod.update_cumulative_pnl(_make_trades([10.0, 5.0]), "2026-03-17")
            # returns the existing snapshot, no new entry, file unchanged
            assert len(data["daily_history"]) == 1
            assert data["daily_history"][0]["commission"] == 7.0
            assert daily_pnl == 200.0
            assert pnl_file.read_text() == before

    def test_empty_trades_zero_daily_pnl(self, tmp_path):
        pnl_file = tmp_path / "cumulative_pnl.json"
        with patch.dict("sys.modules", {"dotenv": MagicMock()}):
            eod = _import_eod(tmp_path, pnl_file)
            data, daily_pnl = eod.update_cumulative_pnl([], "2026-03-17")
            assert daily_pnl == 0.0
            assert not pnl_file.exists()
