"""Tests for EOD report MOC close recognition.

Covers: orderRef='' MOC closes where entry fill is from a previous day.
Triggered by: 2026-03-04 EOD showing 0 trades / $0.00 despite 6 real trades.
"""

import os
import sys
from datetime import date
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _isolate_eod_env():
    """Prevent eod_report.py load_dotenv() from polluting env."""
    mod_key = "scripts.paper_trading.eod_report"
    cached = sys.modules.pop(mod_key, None)
    env_before = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(env_before)
    sys.modules.pop(mod_key, None)
    if cached is not None:
        sys.modules[mod_key] = cached


def _make_fill(symbol, side, price, qty, order_ref=''):
    """Build a mock ib_insync fill object."""
    fill = MagicMock()
    fill.contract.symbol = symbol
    fill.execution.side = side
    fill.execution.price = price
    fill.execution.shares = qty
    fill.execution.time = MagicMock()
    fill.execution.time.date.return_value = date.today()
    fill.execution.orderRef = order_ref
    fill.commissionReport = None
    return fill


class TestMOCOrderRefEmpty:
    """build_trade_report() handles MOC closes with orderRef=''."""

    def test_eod_moc_orderref_empty(self):
        """SLD fill with orderRef='' is recognized when pnl_by_symbol provided."""
        with MagicMock() as _mock_dotenv:
            import sys
            sys.modules['dotenv'] = MagicMock()
            import scripts.paper_trading.eod_report as eod

        sell_fill = _make_fill('AR', 'SLD', 37.87, 304, order_ref='')
        meta = {}
        pnl_by_symbol = {'AR': 255.80}

        trades = eod.build_trade_report([sell_fill], meta, pnl_by_symbol=pnl_by_symbol)

        assert len(trades) == 1
        t = trades[0]
        assert t['ticker'] == 'AR'
        assert t['exit_type'] == 'MOC'
        assert t['exit_price'] == 37.87
        assert t['exit_qty'] == 304
        assert t['pnl'] == 255.80

    def test_eod_portfolio_realizedpnl_entry_price_derived(self):
        """Entry price is back-calculated from realized P&L."""
        with MagicMock():
            import sys
            sys.modules['dotenv'] = MagicMock()
            import scripts.paper_trading.eod_report as eod

        # pnl = (exit - entry) * qty  →  entry = exit - pnl/qty
        # 255.80 = (37.87 - entry) * 304  →  entry = 37.87 - 255.80/304 ≈ 37.03
        sell_fill = _make_fill('AR', 'SLD', 37.87, 304, order_ref='')
        pnl_by_symbol = {'AR': 255.80}

        trades = eod.build_trade_report([sell_fill], {}, pnl_by_symbol=pnl_by_symbol)

        assert len(trades) == 1
        expected_entry = round(37.87 - 255.80 / 304, 2)
        assert trades[0]['entry_price'] == expected_entry

    def test_eod_zero_trades_not_reported_on_moc_day(self):
        """6 MOC closes produce 6 trade records, not 0."""
        with MagicMock():
            import sys
            sys.modules['dotenv'] = MagicMock()
            import scripts.paper_trading.eod_report as eod

        # Mirror the 2026-03-04 log exactly
        fills_data = [
            ('AR',   'SLD', 37.87,  304, 255.80),
            ('TIGO', 'SLD', 72.48,   62,  25.51),
            ('NYT',  'SLD', 81.02,   96, -39.50),
            ('ENPH', 'SLD', 42.68,  126, -28.22),
            ('LYV',  'SLD', 158.49,  32, -70.21),
            ('TS',   'SLD', 53.55,  151,  89.08),
        ]
        fills = [_make_fill(sym, side, price, qty) for sym, side, price, qty, _ in fills_data]
        pnl_by_symbol = {sym: pnl for sym, _, _, _, pnl in fills_data}

        trades = eod.build_trade_report(fills, {}, pnl_by_symbol=pnl_by_symbol)

        assert len(trades) == 6
        total_pnl = sum(t['pnl'] for t in trades)
        assert abs(total_pnl - 232.46) < 0.01
        assert all(t['exit_type'] == 'MOC' for t in trades)
