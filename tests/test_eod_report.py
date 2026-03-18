"""Tests for EOD report commission tracking.

Covers: commission field presence, zero commission, multiple trades aggregation.
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
    return [
        {
            'pnl': 100.0,
            'commission': comm,
            'exit_type': 'MOC'
        }
        for comm in commission_values
    ]


class TestEODCommission:
    """update_cumulative_pnl() commission field tests."""

    def test_commission_field_populated(self, tmp_path):
        """Daily entry has commission field with correct sum."""
        pnl_file = tmp_path / "cumulative_pnl.json"
        trades = _make_trades([10.50, 5.25, 3.75])

        with patch.dict("sys.modules", {
            "dotenv": MagicMock(),
        }):
            import scripts.paper_trading.eod_report as eod
            eod.CUMULATIVE_PNL_FILE = str(pnl_file)
            eod.LOG_DIR = str(tmp_path)

            data, _ = eod.update_cumulative_pnl(trades, "2026-03-17")

            # Commission should be sum of all trade commissions
            assert len(data['daily_history']) == 1
            daily_entry = data['daily_history'][0]
            assert 'commission' in daily_entry
            assert daily_entry['commission'] == pytest.approx(19.50, abs=0.01)

    def test_commission_zero_when_no_trades(self, tmp_path):
        """Zero commission for empty trades list."""
        pnl_file = tmp_path / "cumulative_pnl.json"
        trades = []

        with patch.dict("sys.modules", {
            "dotenv": MagicMock(),
        }):
            import scripts.paper_trading.eod_report as eod
            eod.CUMULATIVE_PNL_FILE = str(pnl_file)
            eod.LOG_DIR = str(tmp_path)

            data, _ = eod.update_cumulative_pnl(trades, "2026-03-17")

            assert len(data['daily_history']) == 1
            daily_entry = data['daily_history'][0]
            assert daily_entry['commission'] == 0.0

    def test_commission_precision(self, tmp_path):
        """Commission rounded to 4 decimals."""
        pnl_file = tmp_path / "cumulative_pnl.json"
        trades = _make_trades([0.123456, 0.234567, 0.111111])

        with patch.dict("sys.modules", {
            "dotenv": MagicMock(),
        }):
            import scripts.paper_trading.eod_report as eod
            eod.CUMULATIVE_PNL_FILE = str(pnl_file)
            eod.LOG_DIR = str(tmp_path)

            data, _ = eod.update_cumulative_pnl(trades, "2026-03-17")

            daily_entry = data['daily_history'][0]
            # Sum: 0.469134 → rounded to 4 decimals: 0.4691
            assert daily_entry['commission'] == pytest.approx(0.4691, abs=0.0001)

    def test_commission_missing_from_trade(self, tmp_path):
        """Handles trades without commission key (defaults to 0)."""
        pnl_file = tmp_path / "cumulative_pnl.json"
        trades = [
            {'pnl': 100.0, 'commission': 5.0, 'exit_type': 'MOC'},
            {'pnl': 50.0, 'exit_type': 'TP1'},  # No commission key
            {'pnl': 25.0, 'commission': 2.5, 'exit_type': 'MOC'},
        ]

        with patch.dict("sys.modules", {
            "dotenv": MagicMock(),
        }):
            import scripts.paper_trading.eod_report as eod
            eod.CUMULATIVE_PNL_FILE = str(pnl_file)
            eod.LOG_DIR = str(tmp_path)

            data, _ = eod.update_cumulative_pnl(trades, "2026-03-17")

            daily_entry = data['daily_history'][0]
            # 5.0 + 0 + 2.5 = 7.5
            assert daily_entry['commission'] == pytest.approx(7.5, abs=0.01)

    def test_idempotency_with_commission(self, tmp_path):
        """Second run on same day doesn't modify commission."""
        pnl_file = tmp_path / "cumulative_pnl.json"
        trades = _make_trades([10.0, 5.0])

        with patch.dict("sys.modules", {
            "dotenv": MagicMock(),
        }):
            import scripts.paper_trading.eod_report as eod
            eod.CUMULATIVE_PNL_FILE = str(pnl_file)
            eod.LOG_DIR = str(tmp_path)

            # First run
            data1, _ = eod.update_cumulative_pnl(trades, "2026-03-17")
            comm_first = data1['daily_history'][0]['commission']

            # Second run — same date
            data2, _ = eod.update_cumulative_pnl(trades, "2026-03-17")
            comm_second = data2['daily_history'][0]['commission']

            assert comm_first == comm_second
            assert len(data2['daily_history']) == 1  # Still just one entry

    def test_multiple_days_commission_per_day(self, tmp_path):
        """Each day has its own commission sum."""
        pnl_file = tmp_path / "cumulative_pnl.json"
        trades_day1 = _make_trades([10.0])
        trades_day2 = _make_trades([5.0, 5.0])

        with patch.dict("sys.modules", {
            "dotenv": MagicMock(),
        }):
            import scripts.paper_trading.eod_report as eod
            eod.CUMULATIVE_PNL_FILE = str(pnl_file)
            eod.LOG_DIR = str(tmp_path)

            data1, _ = eod.update_cumulative_pnl(trades_day1, "2026-03-16")
            data2, _ = eod.update_cumulative_pnl(trades_day2, "2026-03-17")

            assert len(data2['daily_history']) == 2
            assert data2['daily_history'][0]['commission'] == 10.0
            assert data2['daily_history'][1]['commission'] == 10.0
