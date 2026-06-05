"""Tests for generate_review.py — review pipeline 1b cross-check + 1c renderer.

Connector-independent: the IBKR snapshot is injected, so the cross-check logic
and the markdown renderer are fully unit-testable offline.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _pt_path():
    pt = str(Path(__file__).resolve().parent.parent / "scripts" / "paper_trading")
    added = pt not in sys.path
    if added:
        sys.path.insert(0, pt)
    yield
    if added:
        sys.path.remove(pt)


def _gr():
    import importlib

    import generate_review as m

    return importlib.reload(m)


def _review_data(**over):
    base = {
        "date": "2026-06-04",
        "day_number": {"nyse_trading": 13},
        "pnl": {"realized_today": 243.42, "cumulative": 199.5, "commission": 0.0},
        "exits": {"tp1": 1, "tp2": 0, "sl": 0, "loss_exit": 0, "trail": 0, "moc": 2},
        "positions": {
            "open_count": 7,
            "new_entries": [],
            "sector_pct": {"Healthcare": 10.0, "Technology": 4.0},
            "detail": [
                {
                    "ticker": "WST",
                    "sector": "Healthcare",
                    "entry_price": 322.8,
                    "qty_remaining": 18,
                    "days_held_trading": 3,
                    "atr_pct": 0.03,
                    "next_action": "HOLD",
                },
            ],
        },
        "uw_shadow": {"tickers_logged": 30},
        "flags": [
            {
                "flag": "single_position_concentration",
                "priority": "P2",
                "ticker": "JHG",
                "detail": "14.98% > 12%",
            }
        ],
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# 1b cross-check
# ---------------------------------------------------------------------------


class TestCrossCheck:
    def test_pnl_tracking_gap_flagged(self):
        # the 2026-06-04 case: recorded +243.42 (swing-attr) vs broker +200
        gr = _gr()
        flags = gr.build_cross_check_flags(_review_data(), {"realized_today": 200.0})
        f = next(f for f in flags if f["flag"] == "pnl_tracking_gap")
        assert f["priority"] == "P0"
        assert "gap" in f["detail"]

    def test_no_pnl_gap_within_tolerance(self):
        gr = _gr()
        flags = gr.build_cross_check_flags(_review_data(), {"realized_today": 243.0})
        assert not any(f["flag"] == "pnl_tracking_gap" for f in flags)

    def test_state_ibkr_divergence(self):
        gr = _gr()
        flags = gr.build_cross_check_flags(_review_data(), {"position_tickers": ["WST", "EXTRA"]})
        f = next(f for f in flags if f["flag"] == "state_ibkr_divergence")
        assert f["priority"] == "P0" and "EXTRA" in f["detail"]

    def test_no_divergence_when_match(self):
        gr = _gr()
        flags = gr.build_cross_check_flags(_review_data(), {"position_tickers": ["WST"]})
        assert not any(f["flag"] == "state_ibkr_divergence" for f in flags)

    def test_cumulative_drift(self):
        gr = _gr()
        # cumulative 199.5 vs implied (101000 - 100000 - 500 = 500) → drift -300.5
        flags = gr.build_cross_check_flags(
            _review_data(), {"net_liq": 101000.0, "unrealized": 500.0}
        )
        f = next(f for f in flags if f["flag"] == "cumulative_drift")
        assert f["priority"] == "P0"

    def test_no_drift_within_tolerance(self):
        gr = _gr()
        # implied = 100240 - 100000 - 0 = 240; cum 243.42 → drift 3.42 < 50
        flags = gr.build_cross_check_flags(_review_data(), {"net_liq": 100240.0, "unrealized": 0.0})
        assert not any(f["flag"] == "cumulative_drift" for f in flags)

    def test_missing_ibkr_keys_skips_checks(self):
        gr = _gr()
        assert gr.build_cross_check_flags(_review_data(), {}) == []


# ---------------------------------------------------------------------------
# 1c renderer
# ---------------------------------------------------------------------------


class TestRenderer:
    def test_has_core_sections(self):
        gr = _gr()
        md = gr.render_review_markdown(_review_data())
        for section in [
            "# IFDS Daily Review",
            "## ⚠️ CHAT ESCALATION",
            "## 1. Trades",
            "## 2. EOD State",
            "## 5. Anomáliák",
            "## 7. Files referenced",
            "## 8. Strukturális",
        ]:
            assert section in md
        assert "Day 13" in md and "WST" in md

    def test_p0_section_when_cross_check_p0(self):
        gr = _gr()
        cc = [{"flag": "pnl_tracking_gap", "priority": "P0", "detail": "gap $+43"}]
        md = gr.render_review_markdown(_review_data(), cross_check_flags=cc)
        assert "## 0. Kritikus finding (P0)" in md
        assert "pnl_tracking_gap" in md

    def test_no_p0_section_when_clean(self):
        gr = _gr()
        md = gr.render_review_markdown(_review_data())  # only a P2 local flag
        assert "## 0. Kritikus finding (P0)" not in md

    def test_positions_table_and_flags_listed(self):
        gr = _gr()
        md = gr.render_review_markdown(_review_data())
        assert "| WST | Healthcare |" in md
        assert "single_position_concentration" in md  # §5 lists local flags
