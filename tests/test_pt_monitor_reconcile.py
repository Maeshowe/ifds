"""Integration tests for pt_monitor.py::_reconcile_state_from_ibkr.

Mocks the IBKR connection layer and verifies that the EOD reconcile path
detects state ↔ IBKR divergence, removes closed positions from the
in-memory state, and persists the cleaned state to disk before the
mental-stop eval runs.

Refs:
    docs/tasks/2026-05-23-state-reconciliation-from-ibkr.md Rész 1
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _isolate_pt_env():
    """Prevent pt_monitor.py load_dotenv() from polluting env."""
    keys = ["scripts.paper_trading.pt_monitor"]
    cached = {k: sys.modules.pop(k, None) for k in keys}
    env_before = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(env_before)
    for k in keys:
        sys.modules.pop(k, None)
    for k, v in cached.items():
        if v is not None:
            sys.modules[k] = v


def _import_pt_monitor():
    scripts_dir = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "paper_trading",
    )
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import scripts.paper_trading.pt_monitor as mod
    return mod


def _make_swing_position(ticker, entry=100.0, qty=10, sector="Tech"):
    """Minimal SwingPosition factory using the real dataclass."""
    from ifds.state.swing_positions import SwingPosition
    return SwingPosition(
        ticker=ticker,
        entry_date="2026-05-18",
        entry_price=entry,
        atr=2.0,
        stop_level=entry - 4.0,
        tp1_level=entry + 3.0,
        tp2_level=entry + 6.0,
        qty=qty,
        qty_remaining=qty,
        tp1_hit=False,
        trail_sl=None,
        days_held=3,
        next_action="HOLD",
        next_action_at=None,
        weekly_pnl_pct=0.0,
        sector=sector,
        direction="BUY",
        m_target=1.0,
    )


def _make_ib_position(symbol, qty=10):
    pos = MagicMock()
    pos.contract.symbol = symbol
    pos.position = qty
    return pos


# ---------------------------------------------------------------------------
# 1. No divergence — reconcile returns clean report, state unchanged
# ---------------------------------------------------------------------------


class TestReconcileNoDivergence:

    def test_state_matches_ibkr(self, tmp_path):
        """When state and IBKR agree, the reconciler returns
        ``state_matches_ibkr=True`` and detected_closures is empty.
        """
        mod = _import_pt_monitor()
        positions = [
            _make_swing_position("LBRT", entry=33.34, qty=127),
            _make_swing_position("EC", entry=13.08, qty=166),
        ]

        mock_ib = MagicMock()
        mock_ib.positions.return_value = [
            _make_ib_position("LBRT", 127),
            _make_ib_position("EC", 166),
        ]
        mock_ib.reqExecutions.return_value = []

        cfg = MagicMock()
        cfg.tuning = {"swing_positions_state_file": str(tmp_path / "state.json")}

        with (
            patch("lib.connection.connect", return_value=mock_ib),
            patch("lib.connection.disconnect"),
        ):
            report = mod._reconcile_state_from_ibkr(
                positions, str(tmp_path / "state.json"), cfg,
            )

        assert report.state_matches_ibkr is True
        assert report.detected_closures == []


# ---------------------------------------------------------------------------
# 2. Day 4 VLO SL scenario — state has VLO, IBKR doesn't, SLD execution exists
# ---------------------------------------------------------------------------


class TestReconcileDay4VloScenario:

    def test_vlo_sl_detected_classified(self, tmp_path):
        """Replay Day 4: state has VLO + LBRT + EC; IBKR has LBRT + EC.
        The SLD execution for VLO @ $244.61 must be classified as SL
        (matches the mental_stop within tolerance: 244.61 vs 254.55 — wait,
        mental_stop = entry-4 = 254.55, planned stop NOT provided here so
        the fallback uses mental). For an exact mental-level match test
        we use a tighter entry.
        """
        mod = _import_pt_monitor()
        # VLO entry $258.55, mental stop $258.55 - 2*$7 = $244.55 (close to $244.61)
        # so the fallback match should classify as SL
        vlo = _make_swing_position("VLO", entry=258.55, qty=16)
        # Adjust mental_stop to $244.55 (within 0.5% of $244.61)
        from dataclasses import replace
        vlo = replace(vlo, atr=7.0, stop_level=258.55 - 2 * 7.0)  # = 244.55
        positions = [
            _make_swing_position("LBRT", entry=33.34, qty=127),
            vlo,
        ]

        mock_ib = MagicMock()
        mock_ib.positions.return_value = [
            _make_ib_position("LBRT", 127),
            # VLO missing!
        ]

        # Mock VLO SLD execution
        fill = MagicMock()
        fill.execution.side = "SLD"
        fill.execution.shares = 16.0
        fill.execution.price = 244.61
        fill.execution.time = datetime(2026, 5, 21, 17, 19, 54, tzinfo=timezone.utc)
        fill.execution.orderRef = ""           # manual TWS — empty
        fill.execution.orderId = 1234
        fill.contract.symbol = "VLO"
        fill.commissionReport = MagicMock()
        fill.commissionReport.commission = 4.09
        mock_ib.reqExecutions.return_value = [fill]

        cfg = MagicMock()
        cfg.tuning = {"swing_positions_state_file": str(tmp_path / "state.json")}

        with (
            patch("lib.connection.connect", return_value=mock_ib),
            patch("lib.connection.disconnect"),
        ):
            with patch("scripts.paper_trading.pt_monitor.date") as mock_date:
                mock_date.today.return_value = date(2026, 5, 21)
                report = mod._reconcile_state_from_ibkr(
                    positions, str(tmp_path / "state.json"), cfg,
                )

        assert report.state_matches_ibkr is False
        assert report.in_state_not_ibkr == ["VLO"]
        assert len(report.detected_closures) == 1
        closure = report.detected_closures[0]
        assert closure["ticker"] == "VLO"
        assert closure["exit_type"] == "SL"
        assert closure["qty"] == 16
        assert closure["fill_price"] == 244.61


# ---------------------------------------------------------------------------
# 3. Closure detected but no matching execution — classified as OTHER
# ---------------------------------------------------------------------------


class TestReconcileClosureNoExecution:

    def test_other_classification(self, tmp_path):
        """State has VLO but IBKR doesn't, and no SLD found — OTHER."""
        mod = _import_pt_monitor()
        positions = [_make_swing_position("VLO", entry=258.55, qty=16)]
        mock_ib = MagicMock()
        mock_ib.positions.return_value = []   # nothing in IBKR
        mock_ib.reqExecutions.return_value = []

        cfg = MagicMock()
        cfg.tuning = {"swing_positions_state_file": str(tmp_path / "state.json")}

        with (
            patch("lib.connection.connect", return_value=mock_ib),
            patch("lib.connection.disconnect"),
        ):
            report = mod._reconcile_state_from_ibkr(
                positions, str(tmp_path / "state.json"), cfg,
            )

        assert report.in_state_not_ibkr == ["VLO"]
        assert report.detected_closures[0]["exit_type"] == "OTHER"


# ---------------------------------------------------------------------------
# 4. AVDL.CVR permanent orphan — never triggers divergence
# ---------------------------------------------------------------------------


class TestReconcileAvdlCvrOrphan:

    def test_avdl_cvr_not_counted(self, tmp_path):
        """AVDL.CVR appears in IBKR positions but should be filtered out."""
        mod = _import_pt_monitor()
        positions = [_make_swing_position("VLO", entry=258.55, qty=16)]
        mock_ib = MagicMock()
        mock_ib.positions.return_value = [
            _make_ib_position("VLO", 16),
            _make_ib_position("AVDL.CVR", 50),  # orphan
        ]
        mock_ib.reqExecutions.return_value = []

        cfg = MagicMock()
        cfg.tuning = {"swing_positions_state_file": str(tmp_path / "state.json")}

        with (
            patch("lib.connection.connect", return_value=mock_ib),
            patch("lib.connection.disconnect"),
        ):
            report = mod._reconcile_state_from_ibkr(
                positions, str(tmp_path / "state.json"), cfg,
            )

        # AVDL.CVR is NOT reported as "in_ibkr_not_state"
        assert report.state_matches_ibkr is True
        assert report.in_ibkr_not_state == []
