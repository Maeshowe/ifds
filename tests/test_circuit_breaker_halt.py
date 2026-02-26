"""Tests for submit_orders.py circuit breaker halt + override flag.

Covers: halt without flag, continue with override, Telegram alert on halt.
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture(autouse=True)
def _isolate_submit_env():
    """Prevent submit_orders.py load_dotenv() from polluting env."""
    mod_key = "scripts.paper_trading.submit_orders"
    cached = sys.modules.pop(mod_key, None)
    env_before = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(env_before)
    sys.modules.pop(mod_key, None)
    if cached is not None:
        sys.modules[mod_key] = cached


def _setup_circuit_breaker(tmp_path, cum_pnl=-6000.0):
    """Create a cumulative_pnl.json that triggers the circuit breaker."""
    pnl_file = tmp_path / "cumulative_pnl.json"
    pnl_file.write_text(json.dumps({
        'cumulative_pnl': cum_pnl,
        'trading_days': 5,
    }))
    return str(pnl_file)


MOCK_TICKERS = [{'symbol': 'AAPL', 'limit_price': 150.0, 'total_qty': 10,
                 'qty_tp1': 3, 'qty_tp2': 7, 'direction': 'LONG',
                 'stop_loss': 145.0, 'take_profit_1': 155.0, 'take_profit_2': 160.0}]


class TestCircuitBreakerHalt:
    """Circuit breaker halts submission unless --override flag is given."""

    def test_circuit_breaker_halts_without_flag(self, tmp_path):
        """Circuit breaker trigger -> sys.exit(1) without override flag."""
        pnl_file = _setup_circuit_breaker(tmp_path)
        csv_file = tmp_path / "execution_plan_2026-02-26.csv"
        csv_file.write_text("dummy")

        with patch.dict("sys.modules", {"dotenv": MagicMock()}):
            import scripts.paper_trading.submit_orders as submit
            submit.CUMULATIVE_PNL_FILE = pnl_file

            with patch.object(submit, 'send_telegram'), \
                 patch.object(submit, 'load_execution_plan', return_value=MOCK_TICKERS), \
                 patch('sys.argv', ['submit_orders.py', '--file', str(csv_file)]):
                with pytest.raises(SystemExit) as exc_info:
                    submit.main()
                assert exc_info.value.code == 1

    def test_circuit_breaker_continues_with_override_flag(self, tmp_path):
        """Circuit breaker trigger -> continues with --override-circuit-breaker."""
        pnl_file = _setup_circuit_breaker(tmp_path)
        csv_file = tmp_path / "execution_plan_2026-02-26.csv"
        csv_file.write_text("dummy")

        with patch.dict("sys.modules", {"dotenv": MagicMock()}):
            import scripts.paper_trading.submit_orders as submit
            submit.CUMULATIVE_PNL_FILE = pnl_file

            with patch.object(submit, 'send_telegram'), \
                 patch.object(submit, 'load_execution_plan', return_value=MOCK_TICKERS), \
                 patch('sys.argv', ['submit_orders.py', '--dry-run',
                                    '--override-circuit-breaker', '--file', str(csv_file)]):
                # Should NOT raise SystemExit — dry-run finishes normally
                submit.main()

    def test_circuit_breaker_telegram_alert_on_halt(self, tmp_path):
        """Halt sends Telegram with 'HALTED' message."""
        pnl_file = _setup_circuit_breaker(tmp_path)
        csv_file = tmp_path / "execution_plan_2026-02-26.csv"
        csv_file.write_text("dummy")

        telegram_messages = []

        with patch.dict("sys.modules", {"dotenv": MagicMock()}):
            import scripts.paper_trading.submit_orders as submit
            submit.CUMULATIVE_PNL_FILE = pnl_file

            with patch.object(submit, 'send_telegram', side_effect=lambda msg: telegram_messages.append(msg)), \
                 patch.object(submit, 'load_execution_plan', return_value=MOCK_TICKERS), \
                 patch('sys.argv', ['submit_orders.py', '--file', str(csv_file)]):
                with pytest.raises(SystemExit):
                    submit.main()

            assert len(telegram_messages) >= 1
            assert "HALTED" in telegram_messages[0]
