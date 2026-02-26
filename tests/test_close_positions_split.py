"""Tests for close_positions.py MOC order size limit split.

Covers: single order (small + exact limit), 2-leg split, 3-leg split,
Telegram aggregation for split positions.
"""

from unittest.mock import patch, MagicMock, call
import os
import sys
import pytest


@pytest.fixture(autouse=True)
def _isolate_close_positions_env():
    """Prevent close_positions.py load_dotenv() from polluting env.

    Module-level load_dotenv() in close_positions.py sets IFDS_ASYNC_ENABLED=true
    from .env, which breaks phase1/4/5 test mocks (async path bypass).
    """
    # Remove cached module so each test gets a fresh import
    mod_key = "scripts.paper_trading.close_positions"
    cached = sys.modules.pop(mod_key, None)
    env_before = os.environ.copy()
    yield
    # Restore environment
    os.environ.clear()
    os.environ.update(env_before)
    # Remove module again to prevent leaking to next test file
    sys.modules.pop(mod_key, None)
    if cached is not None:
        sys.modules[mod_key] = cached


def _make_position(symbol, qty, con_id=12345):
    """Create a mock IBKR position object."""
    pos = MagicMock()
    pos.contract.symbol = symbol
    pos.contract.conId = con_id
    pos.contract.secType = 'STK'
    pos.position = qty
    return pos


def _run_main_with_positions(positions):
    """Run close_positions.main() with mocked IB connection and given positions.

    Returns (mock_ib, place_order_calls, telegram_message).
    """
    mock_ib = MagicMock()
    mock_ib.positions.return_value = positions
    mock_ib.openOrders.return_value = []

    mock_stock = MagicMock()

    telegram_messages = []

    def capture_telegram(msg):
        telegram_messages.append(msg)

    with patch("scripts.paper_trading.close_positions.send_telegram", side_effect=capture_telegram), \
         patch.dict("os.environ", {
             "IFDS_TELEGRAM_BOT_TOKEN": "test",
             "IFDS_TELEGRAM_CHAT_ID": "123",
         }):
        # We need to patch the lazy imports inside main()
        mock_connect = MagicMock(return_value=mock_ib)
        mock_get_account = MagicMock(return_value="DUH118657")
        mock_disconnect = MagicMock()
        mock_create_moc = MagicMock(side_effect=lambda qty, acc, action='SELL': MagicMock(qty=qty, action=action))

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
            "ib_insync": MagicMock(Stock=MagicMock(return_value=mock_stock)),
        }):
            from scripts.paper_trading.close_positions import main
            main()

    place_order_calls = mock_ib.placeOrder.call_args_list
    tg_msg = telegram_messages[0] if telegram_messages else None
    return mock_ib, place_order_calls, tg_msg


class TestMOCOrderSplit:
    """Test MOC order splitting for IBKR precautionary size limit."""

    def test_moc_small_position_single_order(self):
        """400 shares -> single MOC order, no split."""
        positions = [_make_position("AAPL", 400)]
        mock_ib, place_calls, _ = _run_main_with_positions(positions)

        assert mock_ib.placeOrder.call_count == 1

    def test_moc_exact_limit_single_order(self):
        """500 shares (exact limit) -> single MOC order, no split."""
        positions = [_make_position("MSFT", 500)]
        mock_ib, place_calls, _ = _run_main_with_positions(positions)

        assert mock_ib.placeOrder.call_count == 1

    def test_moc_large_position_split_two(self):
        """611 shares -> two legs: 500 + 111."""
        positions = [_make_position("KMI", 611)]
        mock_ib, place_calls, _ = _run_main_with_positions(positions)

        assert mock_ib.placeOrder.call_count == 2

    def test_moc_very_large_position_split_three(self):
        """1200 shares -> three legs: 500 + 500 + 200."""
        positions = [_make_position("F", 1200)]
        mock_ib, place_calls, _ = _run_main_with_positions(positions)

        assert mock_ib.placeOrder.call_count == 3

    def test_moc_split_telegram_aggregated(self):
        """Split position appears aggregated in Telegram (total qty, not per-leg)."""
        positions = [_make_position("KMI", 611)]
        _, _, tg_msg = _run_main_with_positions(positions)

        assert tg_msg is not None
        assert "KMI: SELL 611 shares" in tg_msg
        assert "Closing 1 positions" in tg_msg
        # Should NOT contain leg info
        assert "leg" not in tg_msg.lower()
