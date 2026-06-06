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


class TestResolveEodDisplayPnl:
    """Data-quality fix #2: P&L today from the Part A daily_history entry."""

    def _eod(self, tmp_path):
        with patch.dict("sys.modules", {"dotenv": MagicMock()}):
            import scripts.paper_trading.eod_report as eod

            return eod

    def test_prefers_part_a_entry(self, tmp_path):
        eod = self._eod(tmp_path)
        # Day 15 (6/5): Part A recorded net +63.83, commission 5.39 — the
        # eod_report's own clientId-12 fills only saw the 15:30 TP1 (+252.43).
        cum = {"daily_history": [{"date": "2026-06-05", "pnl": 63.83, "commission": 5.39}]}
        net, commission, gross = eod.resolve_eod_display_pnl(cum, "2026-06-05", 252.43, 2.0)
        assert net == 63.83
        assert commission == 5.39
        assert gross == round(63.83 + 5.39, 2)

    def test_falls_back_when_no_entry(self, tmp_path):
        eod = self._eod(tmp_path)
        cum = {"daily_history": [{"date": "2026-06-04", "pnl": 225.34, "commission": 3.92}]}
        # No 6/5 entry yet (cron ran before Part A) → eod_report's own fills.
        net, commission, gross = eod.resolve_eod_display_pnl(cum, "2026-06-05", 100.0, 4.0)
        assert net == 96.0
        assert commission == 4.0
        assert gross == 100.0

    def test_empty_history_fallback(self, tmp_path):
        eod = self._eod(tmp_path)
        net, commission, gross = eod.resolve_eod_display_pnl({}, "2026-06-05", 50.0, 1.0)
        assert (net, commission, gross) == (49.0, 1.0, 50.0)


class TestResolveNyseDayNumber:
    """Data-quality fix #3: [Day N/63] uses the NYSE trading-day count."""

    def _eod(self, tmp_path):
        with patch.dict("sys.modules", {"dotenv": MagicMock()}):
            import scripts.paper_trading.eod_report as eod

            return eod

    def test_matches_calendar_helper(self, tmp_path):
        eod = self._eod(tmp_path)
        sys.path.insert(0, str(__import__("pathlib").Path(eod.__file__).parent))
        from daily_metrics import compute_trading_day_number

        cum = {"start_date": "2026-05-18"}
        # 6/5 = NYSE Day 14 (5/18..6/5, skipping weekends + 5/25 Memorial Day).
        assert eod.resolve_nyse_day_number(cum, "2026-06-05") == compute_trading_day_number(
            "2026-06-05", "2026-05-18"
        )

    def test_fallback_to_trading_days_when_no_start(self, tmp_path):
        eod = self._eod(tmp_path)
        # Without start_date the calendar helper still returns an int (>=1);
        # this just pins that the call does not raise.
        result = eod.resolve_nyse_day_number({"trading_days": 7}, "2026-06-05")
        assert isinstance(result, int)
