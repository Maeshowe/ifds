"""Tests for close_positions.py — Bracket B fill-aware MOC quantity calculation.

Covers: get_net_open_qty() correctly accounts for intraday Bracket B fills
only (_B_SL, _B_TRAIL, _TRAIL), and does NOT subtract Bracket A TP1 fills
(_A_TP) which IBKR already removes from pos.position.

Fix triggered by: 2026-03-11 LASR 17sh leftover — Bracket A TP1 fill was
incorrectly deducted from Bracket B pos.position (35sh), causing only 18sh
MOC instead of 35sh.
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _isolate_close_env():
    """Prevent close_positions.py load_dotenv() from polluting env."""
    mod_key = "scripts.paper_trading.close_positions"
    cached = sys.modules.pop(mod_key, None)
    env_before = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(env_before)
    sys.modules.pop(mod_key, None)
    if cached is not None:
        sys.modules[mod_key] = cached


def _make_fill(con_id, side, shares, order_ref='IFDS_LASR_A_TP'):
    """Build a mock ib_insync Fill for a bracket child execution."""
    fill = MagicMock()
    fill.contract.conId = con_id
    fill.execution.side = side
    fill.execution.shares = shares
    fill.execution.orderRef = order_ref
    fill.execution.time = datetime.now(timezone.utc)
    return fill


def _load_cp():
    sys.modules['dotenv'] = MagicMock()
    import scripts.paper_trading.close_positions as cp
    return cp


class TestGetNetOpenQtyBracketAIgnored:
    """Bracket A TP1 fills (_A_TP) must NOT be deducted from MOC qty."""

    def test_a_tp_fill_not_deducted(self):
        """LASR case: _A_TP filled 17sh, Bracket B pos=35 → MOC=35 (not 18)."""
        cp = _load_cp()
        fills = [_make_fill(con_id=100, side='SLD', shares=17, order_ref='IFDS_LASR_A_TP')]
        net = cp.get_net_open_qty('LASR', 100, 35, fills)
        assert net == 35  # _A_TP not deducted

    def test_a_tp_fill_different_ticker(self):
        """_A_TP fill for LION also not deducted."""
        cp = _load_cp()
        fills = [_make_fill(con_id=200, side='SLD', shares=177, order_ref='IFDS_LION_A_TP')]
        net = cp.get_net_open_qty('LION', 200, 360, fills)
        assert net == 360


class TestGetNetOpenQtyBracketBDeducted:
    """Bracket B fills (_B_SL, _B_TRAIL, _TRAIL) ARE deducted from MOC qty."""

    def test_b_sl_fill_deducted(self):
        """Bracket B stop loss fill → deducted from MOC qty."""
        cp = _load_cp()
        fills = [_make_fill(con_id=100, side='SLD', shares=35, order_ref='IFDS_LASR_B_SL')]
        net = cp.get_net_open_qty('LASR', 100, 35, fills)
        assert net == 0

    def test_b_trail_fill_deducted(self):
        """Bracket B trailing stop fill → deducted from MOC qty."""
        cp = _load_cp()
        fills = [_make_fill(con_id=100, side='SLD', shares=35, order_ref='IFDS_LASR_B_TRAIL')]
        net = cp.get_net_open_qty('LASR', 100, 35, fills)
        assert net == 0

    def test_trail_fill_deducted(self):
        """Legacy _TRAIL suffix → deducted from MOC qty."""
        cp = _load_cp()
        fills = [_make_fill(con_id=100, side='SLD', shares=20, order_ref='IFDS_LASR_TRAIL')]
        net = cp.get_net_open_qty('LASR', 100, 35, fills)
        assert net == 15

    def test_partial_b_sl_fill(self):
        """Partial Bracket B SL fill → correct remainder."""
        cp = _load_cp()
        fills = [_make_fill(con_id=100, side='SLD', shares=10, order_ref='IFDS_LASR_B_SL')]
        net = cp.get_net_open_qty('LASR', 100, 35, fills)
        assert net == 25


class TestGetNetOpenQtyEdgeCases:
    """Edge cases for get_net_open_qty()."""

    def test_no_fills(self):
        """No intraday fills → returns gross_qty unchanged."""
        cp = _load_cp()
        net = cp.get_net_open_qty('LASR', 100, 52, [])
        assert net == 52

    def test_moc_fills_ignored(self):
        """MOC close fills (orderRef='') are NOT counted as bracket fills."""
        cp = _load_cp()
        fills = [_make_fill(con_id=100, side='SLD', shares=35, order_ref='')]
        net = cp.get_net_open_qty('LASR', 100, 35, fills)
        assert net == 35

    def test_other_conid_fills_ignored(self):
        """Fills for a different conId are not counted."""
        cp = _load_cp()
        fills = [_make_fill(con_id=999, side='SLD', shares=35, order_ref='IFDS_OTHER_B_SL')]
        net = cp.get_net_open_qty('LASR', 100, 35, fills)
        assert net == 35

    def test_buy_side_fills_ignored(self):
        """BUY fills are not counted (only SLD matters for long positions)."""
        cp = _load_cp()
        fills = [_make_fill(con_id=100, side='BOT', shares=35, order_ref='IFDS_LASR_B_SL')]
        net = cp.get_net_open_qty('LASR', 100, 35, fills)
        assert net == 35

    def test_mixed_a_tp_and_b_sl(self):
        """_A_TP ignored + _B_SL deducted in same fill list."""
        cp = _load_cp()
        fills = [
            _make_fill(con_id=100, side='SLD', shares=17, order_ref='IFDS_LASR_A_TP'),
            _make_fill(con_id=100, side='SLD', shares=10, order_ref='IFDS_LASR_B_SL'),
        ]
        net = cp.get_net_open_qty('LASR', 100, 35, fills)
        assert net == 25  # only _B_SL deducted, _A_TP ignored

    def test_never_goes_negative(self):
        """Result is clamped to 0 even if bracket_sold > gross_qty."""
        cp = _load_cp()
        fills = [_make_fill(con_id=100, side='SLD', shares=50, order_ref='IFDS_LASR_B_SL')]
        net = cp.get_net_open_qty('LASR', 100, 35, fills)
        assert net == 0
