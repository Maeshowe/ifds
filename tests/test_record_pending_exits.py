"""Tests for daily_metrics.record_pending_exits / apply_pending_exits.

P0 §0.11 Part A — the pending-exit recorder is the SOLE cumulative_pnl.json
writer for swing exits. Covers the pure matcher and the orchestrator
(idempotency, missing-execution, ledger mark_processed) with a fake IBKR
connection. CUM_PNL_FILE is monkeypatched to tmp so production state is
never touched (per .claude/rules/ifds-rules.md test-hygiene rule).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _ensure_lib_importable():
    pt_dir = str(Path(__file__).resolve().parent.parent / "scripts" / "paper_trading")
    added = pt_dir not in sys.path
    if added:
        sys.path.insert(0, pt_dir)
    yield
    if added:
        sys.path.remove(pt_dir)


def _dm():
    import importlib

    import daily_metrics as m

    return importlib.reload(m)


def _pe():
    import importlib

    import lib.pending_exits as m

    return importlib.reload(m)


def _seed_cum(initial_history=None):
    return {
        "start_date": "2026-05-18",
        "initial_capital": 100_000,
        "trading_days": len(initial_history or []),
        "cumulative_pnl": round(sum(e["pnl"] for e in (initial_history or [])), 2),
        "cumulative_pnl_pct": 0.0,
        "daily_history": list(initial_history or []),
    }


def _exec(ticker, side, shares, price, commission=1.0, order_ref=""):
    """A normalised execution dict (the shape fetch_today_executions returns)."""
    return {
        "ticker": ticker,
        "side": side,
        "shares": float(shares),
        "price": float(price),
        "time": datetime(2026, 5, 28, 20, 0, tzinfo=timezone.utc),
        "order_ref": order_ref,
        "order_id": 1,
        "commission": commission,
    }


class FakeIB:
    """Placeholder IBKR handle — fetch_today_executions is monkeypatched, so
    this is only used to satisfy the ``ib is not None`` branch (no connect)."""


# ---------------------------------------------------------------------------
# apply_pending_exits — pure matcher
# ---------------------------------------------------------------------------


class TestApplyPendingExits:
    def test_single_time_stop_match(self):
        dm = _dm()
        cum = _seed_cum([{"date": "2026-05-28", "pnl": 0.0, "commission": 0.0,
                          "trades": 0, "filled": 0, "moc_exits": 0}])
        rec = {"key": "AMH_TIME_STOP_2026-05-28", "ticker": "AMH",
               "entry_price": 32.11, "qty": 249, "exit_type": "TIME_STOP", "processed": False}
        execs = [{"ticker": "AMH", "side": "SLD", "shares": 249.0,
                  "price": 31.00, "commission": 2.0}]

        out, matched, warnings = dm.apply_pending_exits(cum, "2026-05-28", [rec], execs)

        assert matched == ["AMH_TIME_STOP_2026-05-28"]
        assert warnings == []
        # gross = 249 * (31.00 - 32.11) = -276.39 ; net = -276.39 - 2.0 = -278.39
        entry = next(e for e in out["daily_history"] if e["date"] == "2026-05-28")
        assert entry["pnl"] == pytest.approx(-278.39, abs=0.01)
        assert entry["moc_exits"] == 1
        assert entry["trades"] == 1
        assert out["cumulative_pnl"] == pytest.approx(-278.39, abs=0.01)

    def test_no_matching_execution_warns_unprocessed(self):
        dm = _dm()
        cum = _seed_cum()
        rec = {"key": "AMH_TIME_STOP_2026-05-28", "ticker": "AMH",
               "entry_price": 32.11, "qty": 249, "exit_type": "TIME_STOP", "processed": False}
        out, matched, warnings = dm.apply_pending_exits(cum, "2026-05-28", [rec], [])
        assert matched == []
        assert warnings == [{"key": "AMH_TIME_STOP_2026-05-28", "reason": "no_matching_execution"}]
        assert out["cumulative_pnl"] == 0.0  # unchanged

    def test_tp1_partial_uses_sold_qty(self):
        dm = _dm()
        cum = _seed_cum()
        rec = {"key": "ON_TP1_2026-05-22", "ticker": "ON",
               "entry_price": 109.48, "qty": 27, "exit_type": "TP1", "processed": False}
        execs = [{"ticker": "ON", "side": "SLD", "shares": 27.0, "price": 115.41, "commission": 2.07}]
        out, matched, warnings = dm.apply_pending_exits(cum, "2026-05-22", [rec], execs)
        assert matched == ["ON_TP1_2026-05-22"]
        entry = out["daily_history"][0]
        # gross = 27 * (115.41 - 109.48) = 160.11 ; net = 160.11 - 2.07 = 158.04
        assert entry["pnl"] == pytest.approx(158.04, abs=0.01)
        assert entry["tp1_hits"] == 1

    def test_multiple_sld_fills_weighted(self):
        dm = _dm()
        cum = _seed_cum()
        rec = {"key": "X_TP1_2026-05-28", "ticker": "X", "entry_price": 100.0,
               "qty": 100, "exit_type": "TP1", "processed": False}
        execs = [
            {"ticker": "X", "side": "SLD", "shares": 60.0, "price": 110.0, "commission": 1.0},
            {"ticker": "X", "side": "SLD", "shares": 40.0, "price": 105.0, "commission": 1.0},
        ]
        out, matched, _ = dm.apply_pending_exits(cum, "2026-05-28", [rec], execs)
        # weighted = (60*110 + 40*105)/100 = 108.0 ; gross = 100*(108-100)=800 ; net=800-2=798
        assert out["daily_history"][0]["pnl"] == pytest.approx(798.0, abs=0.01)
        assert matched == ["X_TP1_2026-05-28"]

    def test_bot_executions_ignored(self):
        dm = _dm()
        cum = _seed_cum()
        rec = {"key": "AMH_TIME_STOP_2026-05-28", "ticker": "AMH",
               "entry_price": 32.11, "qty": 249, "exit_type": "TIME_STOP", "processed": False}
        execs = [{"ticker": "AMH", "side": "BOT", "shares": 249.0, "price": 31.0, "commission": 1.0}]
        out, matched, warnings = dm.apply_pending_exits(cum, "2026-05-28", [rec], execs)
        assert matched == []
        assert warnings[0]["reason"] == "no_matching_execution"

    def test_duplicate_ticker_same_day_guarded(self):
        dm = _dm()
        cum = _seed_cum()
        recs = [
            {"key": "X_TP1_2026-05-28", "ticker": "X", "entry_price": 100.0,
             "qty": 50, "exit_type": "TP1", "processed": False},
            {"key": "X_TIME_STOP_2026-05-28", "ticker": "X", "entry_price": 100.0,
             "qty": 50, "exit_type": "TIME_STOP", "processed": False},
        ]
        execs = [{"ticker": "X", "side": "SLD", "shares": 50.0, "price": 110.0, "commission": 1.0}]
        out, matched, warnings = dm.apply_pending_exits(cum, "2026-05-28", recs, execs)
        assert matched == ["X_TP1_2026-05-28"]
        assert any(w["reason"] == "duplicate_ticker_same_day" for w in warnings)

    def test_qty_mismatch_still_records_with_warning(self):
        dm = _dm()
        cum = _seed_cum()
        rec = {"key": "X_TP1_2026-05-28", "ticker": "X", "entry_price": 100.0,
               "qty": 100, "exit_type": "TP1", "processed": False}
        execs = [{"ticker": "X", "side": "SLD", "shares": 80.0, "price": 110.0, "commission": 1.0}]
        out, matched, warnings = dm.apply_pending_exits(cum, "2026-05-28", [rec], execs)
        assert matched == ["X_TP1_2026-05-28"]
        assert any(w["reason"] == "qty_mismatch" for w in warnings)


# ---------------------------------------------------------------------------
# record_pending_exits — orchestrator (fake IBKR, tmp cumulative file)
# ---------------------------------------------------------------------------


class TestRecordPendingExits:
    def _setup(self, tmp_path, monkeypatch, ledger_records, executions, cum_seed=None):
        dm = _dm()
        pe = _pe()
        ledger_dir = tmp_path / "pending_exits"
        ledger_dir.mkdir()
        (ledger_dir / "2026-05-28.json").write_text(json.dumps(ledger_records))
        cum_file = tmp_path / "cumulative_pnl.json"
        cum_file.write_text(json.dumps(cum_seed if cum_seed is not None else _seed_cum()))
        monkeypatch.setattr(dm, "CUM_PNL_FILE", cum_file)
        # Bypass the real IBKR fetch (and its ib_insync import) — return the
        # normalised executions directly.
        import lib.ibkr_reconciliation as recon
        monkeypatch.setattr(recon, "fetch_today_executions", lambda ib, td: executions)
        return dm, pe, str(ledger_dir), cum_file

    def test_early_return_when_no_unprocessed(self, tmp_path, monkeypatch):
        dm, pe, ledger_dir, cum_file = self._setup(
            tmp_path, monkeypatch,
            [{"key": "AMH_TIME_STOP_2026-05-28", "ticker": "AMH", "entry_price": 32.11,
              "qty": 249, "exit_type": "TIME_STOP", "processed": True}],
            [],
        )
        summary = dm.record_pending_exits("2026-05-28", ledger_dir=ledger_dir, ib=FakeIB())
        assert summary["unprocessed"] == 0
        assert summary["connected"] is False
        assert summary["matched"] == 0

    def test_full_match_writes_and_marks_processed(self, tmp_path, monkeypatch):
        ledger = [{"key": "AMH_TIME_STOP_2026-05-28", "ticker": "AMH", "entry_price": 32.11,
                   "qty": 249, "exit_type": "TIME_STOP", "sector": "Real Estate", "processed": False}]
        dm, pe, ledger_dir, cum_file = self._setup(
            tmp_path, monkeypatch, ledger,
            [_exec("AMH", "SLD", 249, 31.00, commission=2.0)],
            cum_seed=_seed_cum([{"date": "2026-05-28", "pnl": 0.0, "commission": 0.0,
                                 "trades": 0, "filled": 0, "moc_exits": 0}]),
        )
        summary = dm.record_pending_exits("2026-05-28", ledger_dir=ledger_dir, ib=FakeIB())
        assert summary["matched"] == 1
        # cumulative written
        written = json.loads(cum_file.read_text())
        entry = next(e for e in written["daily_history"] if e["date"] == "2026-05-28")
        assert entry["pnl"] == pytest.approx(-278.39, abs=0.01)
        # ledger marked processed
        assert pe.load_pending_exits("2026-05-28", ledger_dir)[0]["processed"] is True

    def test_idempotent_rerun_no_double_count(self, tmp_path, monkeypatch):
        ledger = [{"key": "AMH_TIME_STOP_2026-05-28", "ticker": "AMH", "entry_price": 32.11,
                   "qty": 249, "exit_type": "TIME_STOP", "processed": False}]
        dm, pe, ledger_dir, cum_file = self._setup(
            tmp_path, monkeypatch, ledger,
            [_exec("AMH", "SLD", 249, 31.00, commission=2.0)],
            cum_seed=_seed_cum([{"date": "2026-05-28", "pnl": 0.0, "commission": 0.0,
                                 "trades": 0, "filled": 0, "moc_exits": 0}]),
        )
        dm.record_pending_exits("2026-05-28", ledger_dir=ledger_dir, ib=FakeIB())
        first = json.loads(cum_file.read_text())["cumulative_pnl"]
        # second run — ledger now processed, must be a no-op
        summary2 = dm.record_pending_exits("2026-05-28", ledger_dir=ledger_dir, ib=FakeIB())
        assert summary2["unprocessed"] == 0
        second = json.loads(cum_file.read_text())["cumulative_pnl"]
        assert first == second

    def test_dry_run_no_write(self, tmp_path, monkeypatch):
        ledger = [{"key": "AMH_TIME_STOP_2026-05-28", "ticker": "AMH", "entry_price": 32.11,
                   "qty": 249, "exit_type": "TIME_STOP", "processed": False}]
        dm, pe, ledger_dir, cum_file = self._setup(
            tmp_path, monkeypatch, ledger,
            [_exec("AMH", "SLD", 249, 31.00, commission=2.0)],
        )
        before = cum_file.read_text()
        summary = dm.record_pending_exits(
            "2026-05-28", dry_run=True, ledger_dir=ledger_dir, ib=FakeIB(),
        )
        assert summary["matched"] == 1
        assert cum_file.read_text() == before  # not written
        assert pe.load_pending_exits("2026-05-28", ledger_dir)[0]["processed"] is False

    def test_missing_execution_leaves_unprocessed(self, tmp_path, monkeypatch):
        ledger = [{"key": "AMH_TIME_STOP_2026-05-28", "ticker": "AMH", "entry_price": 32.11,
                   "qty": 249, "exit_type": "TIME_STOP", "processed": False}]
        dm, pe, ledger_dir, cum_file = self._setup(tmp_path, monkeypatch, ledger, [])
        before = cum_file.read_text()
        summary = dm.record_pending_exits("2026-05-28", ledger_dir=ledger_dir, ib=FakeIB())
        assert summary["matched"] == 0
        assert summary["warnings"][0]["reason"] == "no_matching_execution"
        assert cum_file.read_text() == before
        assert pe.load_pending_exits("2026-05-28", ledger_dir)[0]["processed"] is False
