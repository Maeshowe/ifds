"""Ledger-sourced daily trade CSV (P1 fix 2026-07-11).

Verifies build_trade_report_from_ledger() fixes the three defects the 2026-07-08
review §6.2 surfaced in trades_YYYY-MM-DD.csv:
  1. self-reentry mis-pairing (new BUY basis paired with old exit)
  2. incomplete exit list (only the eod-fills window, not all exits)
  3. metadata contamination (plan-score / N/A sector / hardcoded MOC exit_type)

Data mirrors the actual corrupt 2026-07-08 case (broker-verified).
"""

from __future__ import annotations

import os
import sys

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


def _eod():
    from unittest.mock import MagicMock

    sys.modules["dotenv"] = MagicMock()
    import scripts.paper_trading.eod_report as eod

    return eod


# --- Defect 1: self-reentry mis-pairing (07-08 PFGC) ---


def test_self_reentry_pfgc_single_row_old_basis():
    """PFGC exited AND re-entered same day. The CSV must have exactly ONE PFGC
    row — the exit at the OLD basis ($106.5→112.38, +$370.17) — never the
    mis-paired new-entry price ($115.25) / -$180.81. The re-entry is not an exit."""
    eod = _eod()
    # pending_exits has only the EXIT (the new 62-qty entry is NOT an exit row)
    exits = [
        {"ticker": "PFGC", "exit_type": "TP2", "qty": 63, "entry_score": 83.88,
         "sector": "Consumer Defensive", "processed": True},
    ]
    details = {
        "PFGC": {"ticker": "PFGC", "entry": 106.5, "exit": 112.38, "qty": 63,
                 "pnl": 370.17, "commission": 1.5},
    }
    rows = eod.build_trade_report_from_ledger(exits, details, {}, "2026-07-08")
    assert len(rows) == 1
    r = rows[0]
    assert r["ticker"] == "PFGC"
    assert r["entry_price"] == 106.5  # OLD basis, NOT the new-entry 115.25
    assert r["exit_price"] == 112.38
    assert r["pnl"] == 370.17  # broker realized, NOT the mis-paired -180.81
    assert r["entry_qty"] == 63 and r["exit_qty"] == 63  # exit qty, NOT the 62-qty re-entry
    assert r["exit_type"] == "TP2"  # ledger, NOT hardcoded "MOC"


# --- Defect 3: metadata + Defect (partial-exit) qty ---


def test_partial_exit_uses_exit_leg_qty_and_entry_metadata():
    """NSA/SLGN TP1 partials: entry_qty is the SOLD leg (75/64), not the full
    position (150/128); score is the entry_score, sector is real, exit_type=TP1."""
    eod = _eod()
    exits = [
        {"ticker": "NSA", "exit_type": "TP1", "qty": 75, "entry_score": 96.69,
         "sector": "Real Estate", "processed": True},
        {"ticker": "SLGN", "exit_type": "TP1", "qty": 64, "entry_score": 77.48,
         "sector": "Consumer Cyclical", "processed": True},
    ]
    details = {
        "NSA": {"ticker": "NSA", "entry": 45.22, "exit": 45.38, "qty": 75,
                "pnl": 11.91, "commission": 1.08},
        "SLGN": {"ticker": "SLGN", "entry": 45.3, "exit": 44.32, "qty": 64,
                 "pnl": -63.01, "commission": 1.07},
    }
    rows = {r["ticker"]: r for r in
            eod.build_trade_report_from_ledger(exits, details, {}, "2026-07-08")}
    assert rows["NSA"]["entry_qty"] == 75  # sold leg, NOT the full 150
    assert rows["SLGN"]["entry_qty"] == 64  # NOT the full 128
    assert rows["NSA"]["exit_type"] == "TP1"  # NOT "MOC"
    assert rows["SLGN"]["exit_type"] == "TP1"
    assert rows["NSA"]["score"] == 96.69  # entry_score, NOT plan-score / 0
    assert rows["NSA"]["sector"] == "Real Estate"  # NOT "N/A"
    assert rows["SLGN"]["score"] == 77.48  # NOT the 84.3 plan-score


# --- Defect 2: completeness ---


def test_completeness_is_pending_exits_union_not_fetch_window():
    """All 7 processed exits become rows (the union of pending_exits), not the
    3-row eod-fills window the old builder captured."""
    eod = _eod()
    tickers = ["NSA", "PFGC", "SLGN", "RBC", "IEX", "R", "TDG"]
    exits = [{"ticker": t, "exit_type": "TIME_STOP", "qty": 5, "entry_score": 50,
              "sector": "Industrials", "processed": True} for t in tickers]
    details = {t: {"ticker": t, "entry": 10.0, "exit": 11.0, "qty": 5,
                   "pnl": 5.0, "commission": 0.1} for t in tickers}
    rows = eod.build_trade_report_from_ledger(exits, details, {}, "2026-07-08")
    assert len(rows) == 7  # NOT the 3-row window
    assert {r["ticker"] for r in rows} == set(tickers)


# --- Robustness: unprocessed excluded, missing detail skipped, sl/tp from levels ---


def test_unprocessed_excluded_missing_detail_skipped_levels_used():
    eod = _eod()
    exits = [
        {"ticker": "AAA", "exit_type": "TP1", "qty": 10, "entry_score": 80,
         "sector": "S", "processed": True},
        {"ticker": "BBB", "exit_type": "TP1", "qty": 10, "entry_score": 80,
         "sector": "S", "processed": False},   # unprocessed → excluded
        {"ticker": "CCC", "exit_type": "TP1", "qty": 10, "entry_score": 80,
         "sector": "S", "processed": True},     # no broker detail → skipped
    ]
    details = {"AAA": {"ticker": "AAA", "entry": 10.0, "exit": 11.0, "qty": 10,
                       "pnl": 10.0, "commission": 0.1}}
    # AAA still open (partial) → sl/tp from swing_positions levels
    levels = {"AAA": {"ticker": "AAA", "stop_level": 8.0, "tp1_level": 12.0, "tp2_level": 14.0}}
    rows = eod.build_trade_report_from_ledger(exits, details, levels, "2026-07-08")
    assert [r["ticker"] for r in rows] == ["AAA"]  # BBB unprocessed, CCC no detail
    assert rows[0]["sl_price"] == 8.0 and rows[0]["tp1_price"] == 12.0 and rows[0]["tp2_price"] == 14.0
    assert rows[0]["pnl_pct"] == pytest.approx(10.0 / (10.0 * 10) * 100, abs=0.01)  # 10.0%
