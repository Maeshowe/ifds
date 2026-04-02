"""Tests for close_positions.py — net BOT-SLD fill-based MOC quantity calculation.

Covers: get_net_open_qty() correctly computes MOC qty from today's fills
using total_bought - total_sold (suffix-independent).

Replaces old suffix-based logic that missed _LOSS_EXIT, _AVWAP_*_TP fills
and caused leftover positions on 3 consecutive days (CNX, EMN, CENX).
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


def _make_fill(con_id, side, shares, order_ref=''):
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


class TestGetNetOpenQtyBasic:
    """Core BOT-SLD calculation tests."""

    def test_entry_only_no_exits(self):
        """Bought 100, no sells → MOC 100."""
        cp = _load_cp()
        fills = [_make_fill(con_id=100, side='BOT', shares=100, order_ref='IFDS_AAPL')]
        net = cp.get_net_open_qty('AAPL', 100, 100, fills)
        assert net == 100

    def test_fully_closed_intraday(self):
        """Bought 100, sold 100 via TP → MOC 0."""
        cp = _load_cp()
        fills = [
            _make_fill(con_id=100, side='BOT', shares=100, order_ref='IFDS_AAPL'),
            _make_fill(con_id=100, side='SLD', shares=33, order_ref='IFDS_AAPL_A_TP'),
            _make_fill(con_id=100, side='SLD', shares=67, order_ref='IFDS_AAPL_B_TRAIL'),
        ]
        net = cp.get_net_open_qty('AAPL', 100, 0, fills)
        assert net == 0

    def test_partial_exit_bracket_a_tp(self):
        """Bought 100, A_TP sold 33 → MOC 67."""
        cp = _load_cp()
        fills = [
            _make_fill(con_id=100, side='BOT', shares=100, order_ref='IFDS_AAPL'),
            _make_fill(con_id=100, side='SLD', shares=33, order_ref='IFDS_AAPL_A_TP'),
        ]
        net = cp.get_net_open_qty('AAPL', 100, 67, fills)
        assert net == 67

    def test_partial_exit_bracket_b_sl(self):
        """Bought 100, B_SL sold 67 → MOC 33."""
        cp = _load_cp()
        fills = [
            _make_fill(con_id=100, side='BOT', shares=100, order_ref='IFDS_AAPL'),
            _make_fill(con_id=100, side='SLD', shares=67, order_ref='IFDS_AAPL_B_SL'),
        ]
        net = cp.get_net_open_qty('AAPL', 100, 33, fills)
        assert net == 33


class TestGetNetOpenQtyNewExitTypes:
    """Regression: exit types that the old suffix logic missed."""

    def test_loss_exit_fill_counted(self):
        """LOSS_EXIT fill (Scenario B) is correctly counted as SLD."""
        cp = _load_cp()
        fills = [
            _make_fill(con_id=100, side='BOT', shares=183, order_ref='IFDS_CNX'),
            _make_fill(con_id=100, side='SLD', shares=60, order_ref='IFDS_CNX_LOSS_EXIT'),
        ]
        # Old logic: missed _LOSS_EXIT → MOC=183 → leftover 123sh
        # New logic: net = 183 - 60 = 123
        net = cp.get_net_open_qty('CNX', 100, 183, fills)
        assert net == 123

    def test_avwap_tp_fills_counted(self):
        """AVWAP bracket TP fills are correctly counted."""
        cp = _load_cp()
        fills = [
            _make_fill(con_id=200, side='BOT', shares=108, order_ref='IFDS_EMN'),
            _make_fill(con_id=200, side='SLD', shares=36, order_ref='IFDS_EMN_AVWAP_A_TP'),
        ]
        # Old logic: missed _AVWAP_A_TP → MOC=108 → leftover 36sh
        # New logic: net = 108 - 36 = 72
        net = cp.get_net_open_qty('EMN', 200, 72, fills)
        assert net == 72

    def test_avwap_b_tp_fill_counted(self):
        """AVWAP bracket B TP2 fill is correctly counted."""
        cp = _load_cp()
        fills = [
            _make_fill(con_id=300, side='BOT', shares=50, order_ref='IFDS_CENX'),
            _make_fill(con_id=300, side='SLD', shares=27, order_ref='IFDS_CENX_AVWAP_B_TP'),
        ]
        net = cp.get_net_open_qty('CENX', 300, 23, fills)
        assert net == 23

    def test_mixed_exit_types(self):
        """Multiple exit types in same day — all counted."""
        cp = _load_cp()
        fills = [
            _make_fill(con_id=100, side='BOT', shares=200, order_ref='IFDS_TEST'),
            _make_fill(con_id=100, side='SLD', shares=66, order_ref='IFDS_TEST_A_TP'),
            _make_fill(con_id=100, side='SLD', shares=50, order_ref='IFDS_TEST_LOSS_EXIT'),
            _make_fill(con_id=100, side='SLD', shares=30, order_ref='IFDS_TEST_B_TRAIL'),
        ]
        # net = 200 - (66 + 50 + 30) = 54
        net = cp.get_net_open_qty('TEST', 100, 54, fills)
        assert net == 54


class TestGetNetOpenQtyEdgeCases:
    """Edge cases for get_net_open_qty()."""

    def test_no_fills_returns_gross_qty(self):
        """No intraday fills → returns gross_qty unchanged."""
        cp = _load_cp()
        net = cp.get_net_open_qty('LASR', 100, 52, [])
        assert net == 52

    def test_other_conid_fills_ignored(self):
        """Fills for a different conId are not counted."""
        cp = _load_cp()
        fills = [
            _make_fill(con_id=999, side='BOT', shares=100, order_ref='IFDS_OTHER'),
            _make_fill(con_id=999, side='SLD', shares=100, order_ref='IFDS_OTHER_B_SL'),
        ]
        net = cp.get_net_open_qty('LASR', 100, 35, fills)
        assert net == 35

    def test_never_goes_negative(self):
        """Result is clamped to 0 even if sold > bought (stale position data)."""
        cp = _load_cp()
        fills = [
            _make_fill(con_id=100, side='BOT', shares=35, order_ref='IFDS_LASR'),
            _make_fill(con_id=100, side='SLD', shares=50, order_ref='IFDS_LASR_B_SL'),
        ]
        net = cp.get_net_open_qty('LASR', 100, 35, fills)
        assert net == 0

    def test_only_sold_fills_no_bot(self):
        """Only SLD fills, no BOT entry in today's fills (pre-existing position).

        This can happen if position was opened on a prior day — no BOT fill today.
        Falls back to 0 since net = 0 - sold = negative → clamped to 0.
        But gross_qty from positions() shows shares exist.
        In this case, sold > 0 means intraday exits happened, so net=0 is correct
        if the position was fully closed.
        """
        cp = _load_cp()
        fills = [
            _make_fill(con_id=100, side='SLD', shares=35, order_ref='IFDS_LASR_B_SL'),
        ]
        net = cp.get_net_open_qty('LASR', 100, 35, fills)
        assert net == 0

    def test_prior_day_position_no_fills_today(self):
        """Position from prior day, no fills today for this contract.

        Other contracts may have fills, but not this one.
        Should return gross_qty (nothing happened today).
        """
        cp = _load_cp()
        fills = [
            _make_fill(con_id=999, side='BOT', shares=50, order_ref='IFDS_OTHER'),
        ]
        net = cp.get_net_open_qty('LASR', 100, 35, fills)
        assert net == 35
