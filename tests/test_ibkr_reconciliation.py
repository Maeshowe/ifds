"""Tests for scripts/paper_trading/lib/ibkr_reconciliation.py — Rész 1+3.

Covers the pure helper functions (no IBKR API):
- detect_closed_tickers — set difference logic
- classify_exit_from_execution — order_ref + bracket-level matching
- compute_pnl — round-trip P&L
- build_reconcile_report — end-to-end with mocked IBKR data
"""

from __future__ import annotations

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


def _import_module():
    from lib.ibkr_reconciliation import (  # noqa: F401
        PlannedBracket,
        ReconcileReport,
        build_reconcile_report,
        classify_exit_from_execution,
        compute_pnl,
        detect_closed_tickers,
    )
    return {
        "PlannedBracket": PlannedBracket,
        "ReconcileReport": ReconcileReport,
        "build_reconcile_report": build_reconcile_report,
        "classify_exit_from_execution": classify_exit_from_execution,
        "compute_pnl": compute_pnl,
        "detect_closed_tickers": detect_closed_tickers,
    }


# ---------------------------------------------------------------------------
# 1. detect_closed_tickers
# ---------------------------------------------------------------------------


class TestDetectClosedTickers:

    def test_no_divergence(self):
        m = _import_module()
        in_state, in_ibkr = m["detect_closed_tickers"](
            {"VLO", "ON"}, {"VLO", "ON"},
        )
        assert in_state == set()
        assert in_ibkr == set()

    def test_state_has_ghost(self):
        """W21 Day 5 pattern: VLO + ON in state but gone from IBKR."""
        m = _import_module()
        in_state, in_ibkr = m["detect_closed_tickers"](
            ib_position_tickers={"LBRT", "MASI", "CNC"},
            state_tickers={"LBRT", "MASI", "CNC", "VLO", "ON"},
        )
        assert in_state == {"VLO", "ON"}
        assert in_ibkr == set()

    def test_ibkr_has_extra(self):
        """Operator manually opened a position outside the pipeline."""
        m = _import_module()
        in_state, in_ibkr = m["detect_closed_tickers"](
            ib_position_tickers={"VLO", "EXTRA"},
            state_tickers={"VLO"},
        )
        assert in_state == set()
        assert in_ibkr == {"EXTRA"}

    def test_avdl_cvr_permanent_orphan_excluded(self):
        """AVDL.CVR must never count as a divergence."""
        m = _import_module()
        in_state, in_ibkr = m["detect_closed_tickers"](
            ib_position_tickers={"AVDL.CVR", "VLO"},
            state_tickers={"VLO"},
        )
        assert in_ibkr == set()  # AVDL.CVR excluded by default


# ---------------------------------------------------------------------------
# 2. classify_exit_from_execution — order_ref primary path
# ---------------------------------------------------------------------------


class TestClassifyExitOrderRefPath:

    def test_tp1_substring(self):
        m = _import_module()
        result = m["classify_exit_from_execution"](
            order_ref="IFDS_SWING_EC_TP1", fill_price=13.76,
        )
        assert result == "TP1"

    def test_tp2_substring(self):
        m = _import_module()
        result = m["classify_exit_from_execution"](
            order_ref="IFDS_SWING_VLO_TP2", fill_price=290.0,
        )
        assert result == "TP2"

    def test_sl_substring(self):
        m = _import_module()
        result = m["classify_exit_from_execution"](
            order_ref="IFDS_SWING_VLO_SL", fill_price=244.61,
        )
        assert result == "SL"

    def test_trail_substring(self):
        m = _import_module()
        result = m["classify_exit_from_execution"](
            order_ref="IFDS_SWING_LBRT_TRAIL", fill_price=30.0,
        )
        assert result == "TRAIL_SL"

    def test_case_insensitive(self):
        m = _import_module()
        result = m["classify_exit_from_execution"](
            order_ref="ifds_swing_vlo_sl", fill_price=244.61,
        )
        assert result == "SL"


# ---------------------------------------------------------------------------
# 3. classify_exit_from_execution — fallback bracket-level path
# ---------------------------------------------------------------------------


class TestClassifyExitFallbackPath:

    def test_planned_sl_match(self):
        """Day 4 VLO SL pattern: empty order_ref, fill matches planned stop."""
        m = _import_module()
        planned = m["PlannedBracket"](
            ticker="VLO",
            planned_stop=244.71,
            planned_tp1=276.05,
            planned_tp2=289.48,
        )
        result = m["classify_exit_from_execution"](
            order_ref="", fill_price=244.61, planned=planned,
        )
        # Within 0.5% of $244.71 → SL
        assert result == "SL"

    def test_planned_tp1_exact_match(self):
        """Day 5 ON TP1 pattern: empty order_ref, fill exactly at planned TP1."""
        m = _import_module()
        planned = m["PlannedBracket"](
            ticker="ON",
            planned_stop=93.50,
            planned_tp1=115.41,
            planned_tp2=124.80,
        )
        result = m["classify_exit_from_execution"](
            order_ref="", fill_price=115.41, planned=planned,
        )
        assert result == "TP1"

    def test_no_match_within_tolerance_returns_other(self):
        m = _import_module()
        planned = m["PlannedBracket"](
            ticker="X",
            planned_stop=100.0,
            planned_tp1=120.0,
            planned_tp2=140.0,
        )
        # Fill at 110 — between TP1 and SL, > 0.5% from both
        result = m["classify_exit_from_execution"](
            order_ref="", fill_price=110.0, planned=planned,
        )
        assert result == "OTHER"

    def test_planned_takes_precedence_over_mental(self):
        """When both planned and mental levels match, planned wins."""
        m = _import_module()
        planned = m["PlannedBracket"](
            ticker="VLO",
            planned_stop=244.71,
            mental_stop=240.64,
        )
        # Fill matches planned $244.71 — must classify as SL, not OTHER
        # (mental_stop $240.64 also a candidate, but planned has priority)
        result = m["classify_exit_from_execution"](
            order_ref="", fill_price=244.61, planned=planned,
        )
        assert result == "SL"

    def test_no_planned_no_order_ref_returns_other(self):
        m = _import_module()
        result = m["classify_exit_from_execution"](
            order_ref="", fill_price=100.0,
        )
        assert result == "OTHER"


# ---------------------------------------------------------------------------
# 4. compute_pnl
# ---------------------------------------------------------------------------


class TestComputePnl:

    def test_long_profit(self):
        m = _import_module()
        # ON TP1: 27 × ($115.41 - $109.48) = 27 × $5.93 = $160.11
        assert m["compute_pnl"](109.48, 115.41, 27) == pytest.approx(160.11, abs=0.01)

    def test_long_loss(self):
        m = _import_module()
        # VLO SL: 16 × ($244.61 - $258.55) = 16 × -$13.94 = -$223.04
        assert m["compute_pnl"](258.55, 244.61, 16) == pytest.approx(-223.04, abs=0.01)

    def test_short_profit(self):
        m = _import_module()
        # Short closed lower: 10 × ($100 - $95) = +$50
        assert m["compute_pnl"](100, 95, 10, side="SELL") == 50.0


# ---------------------------------------------------------------------------
# 5. build_reconcile_report — end-to-end Day 4 VLO SL scenario
# ---------------------------------------------------------------------------


class TestBuildReconcileReportDay4Vlo:

    def test_day4_vlo_sl_classified(self):
        """The Day 4 VLO SL bracket trigger ends up as a TP1=0/SL=1 closure."""
        m = _import_module()
        executions = [
            {
                "ticker": "VLO",
                "side": "SLD",
                "shares": 16.0,
                "price": 244.61,
                "time": datetime(2026, 5, 21, 17, 19, 54, tzinfo=timezone.utc),
                "order_ref": "",  # manual TWS bracket — no IFDS ref
                "order_id": 1234,
                "commission": 4.09,
            },
        ]
        report = m["build_reconcile_report"](
            ib_position_tickers={"LBRT", "MASI", "EC", "PFGC", "ON", "CNC", "WMB", "DXCM"},
            state_tickers={"LBRT", "MASI", "EC", "PFGC", "VLO", "ON", "CNC", "WMB", "DXCM"},
            executions=executions,
            planned_brackets={
                "VLO": m["PlannedBracket"](
                    ticker="VLO",
                    planned_stop=244.71,
                    planned_tp1=276.05,
                    planned_tp2=289.48,
                ),
            },
            state_positions_by_ticker={
                "VLO": {"entry_price": 258.55, "qty_remaining": 16, "sector": "Energy"},
            },
        )
        assert report.in_state_not_ibkr == ["VLO"]
        assert report.in_ibkr_not_state == []
        assert len(report.detected_closures) == 1
        closure = report.detected_closures[0]
        assert closure["ticker"] == "VLO"
        assert closure["exit_type"] == "SL"
        assert closure["qty"] == 16
        assert closure["gross"] == pytest.approx(-223.04, abs=0.01)
        assert closure["fill_price"] == 244.61


# ---------------------------------------------------------------------------
# 6. build_reconcile_report — no-divergence happy path
# ---------------------------------------------------------------------------


class TestReportNoDivergence:

    def test_state_matches_ibkr(self):
        m = _import_module()
        report = m["build_reconcile_report"](
            ib_position_tickers={"VLO", "ON"},
            state_tickers={"VLO", "ON"},
            executions=[],
            planned_brackets={},
        )
        assert report.state_matches_ibkr is True
        assert report.detected_closures == []


# ---------------------------------------------------------------------------
# 7. build_reconcile_report — closure with no matching execution
# ---------------------------------------------------------------------------


class TestReportClosureWithoutExecution:

    def test_other_classification_no_execution(self):
        """Ticker missing from IBKR but no execution log for it."""
        m = _import_module()
        report = m["build_reconcile_report"](
            ib_position_tickers={"ON"},
            state_tickers={"VLO", "ON"},
            executions=[],         # no SLD for VLO
            planned_brackets={},
        )
        assert report.in_state_not_ibkr == ["VLO"]
        assert len(report.detected_closures) == 1
        assert report.detected_closures[0]["exit_type"] == "OTHER"
        assert report.detected_closures[0]["reason"] == "no_matching_execution"
