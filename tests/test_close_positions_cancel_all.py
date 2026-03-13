"""Tests for close_positions.py — cancel ALL open orders before MOC.

Fix triggered by: 2026-03-12 IRDM 63sh leftover — partial entry fill left
residual bracket orders (SL/TP2) without IFDS_ orderRef, which the previous
IFDS_-only cancel filter missed.
"""

import os
import sys
from unittest.mock import patch, MagicMock

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


def _make_order(order_ref=''):
    """Build a mock IBKR order."""
    order = MagicMock()
    order.orderRef = order_ref
    return order


def _make_position(symbol, qty, con_id=12345):
    """Create a mock IBKR position object."""
    pos = MagicMock()
    pos.contract.symbol = symbol
    pos.contract.conId = con_id
    pos.contract.secType = 'STK'
    pos.position = qty
    return pos


def _run_main_with_orders(open_orders, positions=None):
    """Run close_positions.main() with mocked IB connection.

    Returns (mock_ib, cancel_calls).
    """
    if positions is None:
        positions = [_make_position("AAPL", 100)]

    mock_ib = MagicMock()
    mock_ib.positions.return_value = positions
    mock_ib.openOrders.return_value = open_orders
    mock_ib.reqExecutions.return_value = []

    mock_stock = MagicMock()

    with patch("scripts.paper_trading.close_positions.send_telegram", MagicMock()), \
         patch.dict("os.environ", {
             "IFDS_TELEGRAM_BOT_TOKEN": "test",
             "IFDS_TELEGRAM_CHAT_ID": "123",
         }):
        mock_connect = MagicMock(return_value=mock_ib)
        mock_get_account = MagicMock(return_value="DUH118657")
        mock_disconnect = MagicMock()
        mock_create_moc = MagicMock(
            side_effect=lambda qty, acc, action='SELL': MagicMock(qty=qty, action=action)
        )

        with patch.dict("sys.modules", {
            "lib": MagicMock(),
            "lib.connection": MagicMock(
                connect=mock_connect,
                get_account=mock_get_account,
                disconnect=mock_disconnect,
            ),
            "lib.orders": MagicMock(
                create_moc_order=mock_create_moc,
            ),
            "ib_insync": MagicMock(
                Stock=MagicMock(return_value=mock_stock),
                ExecutionFilter=MagicMock(),
            ),
        }):
            from scripts.paper_trading.close_positions import main
            main()

    cancel_calls = mock_ib.cancelOrder.call_args_list
    return mock_ib, cancel_calls


class TestCancelAllOrders:
    """Cancel loop must cancel ALL open orders, not just IFDS_ tagged."""

    def test_ifds_orders_cancelled(self):
        """Standard IFDS_ bracket orders are cancelled."""
        orders = [
            _make_order('IFDS_AAPL_A_TP'),
            _make_order('IFDS_AAPL_B_SL'),
        ]
        _, cancel_calls = _run_main_with_orders(orders)
        assert len(cancel_calls) == 2

    def test_non_ifds_orders_also_cancelled(self):
        """Orders without IFDS_ prefix (residual split-leg) are also cancelled."""
        orders = [
            _make_order(''),          # no orderRef
            _make_order('OCA_12345'), # OCA group order
        ]
        _, cancel_calls = _run_main_with_orders(orders)
        assert len(cancel_calls) == 2

    def test_mixed_ifds_and_non_ifds(self):
        """Both IFDS_ and non-IFDS_ orders are cancelled (IRDM scenario)."""
        orders = [
            _make_order('IFDS_IRDM_A_TP'),
            _make_order('IFDS_IRDM_B_SL'),
            _make_order(''),  # residual bracket from partial fill
        ]
        _, cancel_calls = _run_main_with_orders(orders)
        assert len(cancel_calls) == 3

    def test_no_open_orders(self):
        """No orders → no cancelOrder calls."""
        _, cancel_calls = _run_main_with_orders([])
        assert len(cancel_calls) == 0

    def test_cancel_before_moc(self):
        """cancelOrder is called before placeOrder (MOC submission)."""
        orders = [_make_order('IFDS_AAPL_B_SL')]
        mock_ib, _ = _run_main_with_orders(orders)

        # Verify call order: cancelOrder before placeOrder
        call_names = [c[0] for c in mock_ib.method_calls]
        cancel_idx = next(i for i, n in enumerate(call_names) if n == 'cancelOrder')
        place_idx = next(i for i, n in enumerate(call_names) if n == 'placeOrder')
        assert cancel_idx < place_idx
