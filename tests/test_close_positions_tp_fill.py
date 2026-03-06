"""Tests for close_positions.py — TP/SL fill-aware MOC quantity calculation.

Covers: get_net_open_qty() correctly accounts for intraday bracket fills
before submitting MOC close orders.

Triggered by: 2026-03-05 LION -177 inadvertent short — close_positions.py
sold 537 shares (gross) when only 360 were open after TP1 filled 177.
"""

import os
import sys
from datetime import date, datetime, timezone
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


def _make_fill(con_id, side, shares, order_ref='IFDS_LION_A_TP'):
    """Build a mock ib_insync Fill for a bracket child execution."""
    fill = MagicMock()
    fill.contract.conId = con_id
    fill.execution.side = side
    fill.execution.shares = shares
    fill.execution.orderRef = order_ref
    fill.execution.time = datetime.now(timezone.utc)
    return fill


class TestGetNetOpenQty:
    """get_net_open_qty() returns correct safe MOC quantity."""

    def test_close_positions_partial_tp_fill(self):
        """537 gross, 177 sold via TP1 → returns 360."""
        sys.modules['dotenv'] = MagicMock()
        import scripts.paper_trading.close_positions as cp

        fills = [_make_fill(con_id=1234, side='SLD', shares=177, order_ref='IFDS_LION_A_TP')]
        net = cp.get_net_open_qty('LION', 1234, 537, fills)
        assert net == 360

    def test_close_positions_tp_fill_before_moc(self):
        """Full position closed intraday (TP1 + TP2) → returns 0, no MOC submitted."""
        sys.modules['dotenv'] = MagicMock()
        import scripts.paper_trading.close_positions as cp

        fills = [
            _make_fill(con_id=1234, side='SLD', shares=177, order_ref='IFDS_LION_A_TP'),
            _make_fill(con_id=1234, side='SLD', shares=360, order_ref='IFDS_LION_B_TP'),
        ]
        net = cp.get_net_open_qty('LION', 1234, 537, fills)
        assert net == 0

    def test_close_positions_no_fills(self):
        """No intraday fills → returns gross_qty unchanged."""
        sys.modules['dotenv'] = MagicMock()
        import scripts.paper_trading.close_positions as cp

        net = cp.get_net_open_qty('LION', 1234, 537, [])
        assert net == 537

    def test_close_positions_moc_fills_ignored(self):
        """MOC close fills (orderRef='') are NOT counted as bracket fills."""
        sys.modules['dotenv'] = MagicMock()
        import scripts.paper_trading.close_positions as cp

        # orderRef='' → MOC close, not a bracket fill → should not affect net_qty
        fills = [_make_fill(con_id=1234, side='SLD', shares=360, order_ref='')]
        net = cp.get_net_open_qty('LION', 1234, 360, fills)
        assert net == 360  # no adjustment

    def test_close_positions_other_symbol_fills_ignored(self):
        """Fills for a different conId are not counted."""
        sys.modules['dotenv'] = MagicMock()
        import scripts.paper_trading.close_positions as cp

        fills = [_make_fill(con_id=9999, side='SLD', shares=200, order_ref='IFDS_OTHER_A_TP')]
        net = cp.get_net_open_qty('LION', 1234, 537, fills)
        assert net == 537  # different conId, no adjustment
