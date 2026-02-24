"""Tests for IBKR Connection Hardening.

Covers retry logic, timeout, Telegram alert on failure.
"""

from unittest.mock import patch, MagicMock
import pytest


class TestIBKRConnect:
    """Test connect() retry and alert behavior."""

    def test_connect_success_first_attempt(self):
        """Successful connection on first try."""
        mock_ib = MagicMock()
        with patch("scripts.paper_trading.lib.connection.IB", return_value=mock_ib):
            from scripts.paper_trading.lib.connection import connect, PAPER_PORT
            result = connect(client_id=10, max_retries=3, timeout=15.0)
        mock_ib.connect.assert_called_once_with(
            "127.0.0.1", PAPER_PORT, clientId=10, timeout=15.0
        )
        assert result is mock_ib

    def test_connect_retry_then_success(self):
        """First attempt fails, second succeeds."""
        mock_ib = MagicMock()
        mock_ib.connect.side_effect = [Exception("timeout"), None]
        with patch("scripts.paper_trading.lib.connection.IB", return_value=mock_ib), \
             patch("scripts.paper_trading.lib.connection.time.sleep"):
            from scripts.paper_trading.lib.connection import connect
            result = connect(client_id=10, max_retries=3, retry_delay=0)
        assert mock_ib.connect.call_count == 2
        assert result is mock_ib

    def test_connect_all_retries_fail_exits(self):
        """All attempts fail -> sys.exit(1) + Telegram alert."""
        mock_ib = MagicMock()
        mock_ib.connect.side_effect = Exception("connection refused")
        with patch("scripts.paper_trading.lib.connection.IB", return_value=mock_ib), \
             patch("scripts.paper_trading.lib.connection.time.sleep"), \
             patch("scripts.paper_trading.lib.connection._send_telegram_alert") as mock_tg:
            from scripts.paper_trading.lib.connection import connect
            with pytest.raises(SystemExit) as exc_info:
                connect(client_id=10, max_retries=3, retry_delay=0)
        assert exc_info.value.code == 1
        assert mock_ib.connect.call_count == 3
        mock_tg.assert_called_once()

    def test_connect_telegram_alert_content(self):
        """Telegram alert contains correct info."""
        mock_ib = MagicMock()
        mock_ib.connect.side_effect = Exception("gateway down")
        with patch("scripts.paper_trading.lib.connection.IB", return_value=mock_ib), \
             patch("scripts.paper_trading.lib.connection.time.sleep"), \
             patch("scripts.paper_trading.lib.connection._send_telegram_alert") as mock_tg:
            from scripts.paper_trading.lib.connection import connect
            with pytest.raises(SystemExit):
                connect(host="127.0.0.1", port=7497, client_id=10,
                        max_retries=2, retry_delay=0)
        alert_msg = mock_tg.call_args[0][0]
        assert "IBKR CONNECTION FAILED" in alert_msg
        assert "127.0.0.1:7497" in alert_msg
        assert "ClientId: 10" in alert_msg
        assert "2/2" in alert_msg

    def test_connect_telegram_failure_does_not_block(self):
        """Telegram error does not prevent sys.exit."""
        mock_ib = MagicMock()
        mock_ib.connect.side_effect = Exception("fail")
        with patch("scripts.paper_trading.lib.connection.IB", return_value=mock_ib), \
             patch("scripts.paper_trading.lib.connection.time.sleep"), \
             patch("scripts.paper_trading.lib.connection._send_telegram_alert",
                   side_effect=Exception("telegram down")):
            from scripts.paper_trading.lib.connection import connect
            with pytest.raises(SystemExit):
                connect(client_id=10, max_retries=1, retry_delay=0)

    def test_disconnect_called_between_retries(self):
        """ib.disconnect() called after failed attempts."""
        mock_ib = MagicMock()
        mock_ib.connect.side_effect = [Exception("fail"), None]
        with patch("scripts.paper_trading.lib.connection.IB", return_value=mock_ib), \
             patch("scripts.paper_trading.lib.connection.time.sleep"):
            from scripts.paper_trading.lib.connection import connect
            connect(client_id=10, max_retries=3, retry_delay=0)
        # disconnect called once (after first failed attempt)
        mock_ib.disconnect.assert_called_once()
