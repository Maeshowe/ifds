"""Tests for eod_report.update_cumulative_pnl read-only contract.

P0 §0.11 Part A neutralised the eod_report cumulative WRITE: the sole
cumulative_pnl.json writer is now daily_metrics.record_pending_exits.
update_cumulative_pnl is display-only — it loads the current cumulative
snapshot and computes today's display P&L from the trade list, but must
NOT modify or write the file.
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
    return [{"pnl": pnl, "exit_type": "MOC"} for pnl in pnl_values]


class TestEODCumulativeReadOnly:
    """update_cumulative_pnl() no longer writes — display-only."""

    def test_does_not_create_file(self, tmp_path):
        """With no existing file, update_cumulative_pnl returns a fresh
        in-memory dict but does NOT create the file on disk."""
        pnl_file = tmp_path / "cumulative_pnl.json"
        trades = _make_trades([100.0, -30.0])

        with patch.dict("sys.modules", {"dotenv": MagicMock()}):
            import scripts.paper_trading.eod_report as eod

            eod.CUMULATIVE_PNL_FILE = str(pnl_file)
            eod.LOG_DIR = str(tmp_path)

            data, daily_pnl = eod.update_cumulative_pnl(trades, "2026-02-25")
            assert daily_pnl == 70.0
            assert not pnl_file.exists()  # NOT written

    def test_does_not_modify_existing_file(self, tmp_path):
        """An existing cumulative file is read but never mutated/appended."""
        pnl_file = tmp_path / "cumulative_pnl.json"
        existing = {
            "start_date": "2026-02-20",
            "initial_capital": 100000,
            "trading_days": 3,
            "cumulative_pnl": 250.0,
            "cumulative_pnl_pct": 0.25,
            "daily_history": [
                {
                    "date": "2026-02-24",
                    "pnl": 250.0,
                    "commission": 5.0,
                    "trades": 2,
                    "filled": 2,
                    "moc_exits": 2,
                },
            ],
        }
        pnl_file.write_text(json.dumps(existing))
        before = pnl_file.read_text()

        with patch.dict("sys.modules", {"dotenv": MagicMock()}):
            import scripts.paper_trading.eod_report as eod

            eod.CUMULATIVE_PNL_FILE = str(pnl_file)
            eod.LOG_DIR = str(tmp_path)

            data, daily_pnl = eod.update_cumulative_pnl(_make_trades([100.0]), "2026-02-25")

            # Returned snapshot reflects the existing file, unchanged
            assert data["cumulative_pnl"] == 250.0
            assert data["trading_days"] == 3
            assert len(data["daily_history"]) == 1
            assert daily_pnl == 100.0
            # File on disk untouched
            assert pnl_file.read_text() == before

    def test_repeated_calls_never_double_count(self, tmp_path):
        """Calling twice can never inflate cumulative (no write at all)."""
        pnl_file = tmp_path / "cumulative_pnl.json"
        existing = {
            "start_date": "2026-02-20",
            "initial_capital": 100000,
            "trading_days": 1,
            "cumulative_pnl": 100.0,
            "cumulative_pnl_pct": 0.1,
            "daily_history": [{"date": "2026-02-24", "pnl": 100.0}],
        }
        pnl_file.write_text(json.dumps(existing))

        with patch.dict("sys.modules", {"dotenv": MagicMock()}):
            import scripts.paper_trading.eod_report as eod

            eod.CUMULATIVE_PNL_FILE = str(pnl_file)
            eod.LOG_DIR = str(tmp_path)

            d1, _ = eod.update_cumulative_pnl(_make_trades([50.0]), "2026-02-25")
            d2, _ = eod.update_cumulative_pnl(_make_trades([50.0]), "2026-02-25")
            assert d1["cumulative_pnl"] == d2["cumulative_pnl"] == 100.0
            assert json.loads(pnl_file.read_text())["cumulative_pnl"] == 100.0
