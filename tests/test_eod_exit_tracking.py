"""Tests for EOD report orderRef-based exit classification.

Covers: classify_exit_by_ref(), build_trade_report() with orderRef,
        update_cumulative_pnl() loss_exit_hits/trail_hits fields.
"""

import json
import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

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


def _import_eod():
    sys.modules['dotenv'] = MagicMock()
    import scripts.paper_trading.eod_report as eod
    return eod


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


# ---------------------------------------------------------------------------
# classify_exit_by_ref() unit tests
# ---------------------------------------------------------------------------


class TestClassifyExitByRef:
    """orderRef pattern matching."""

    def test_tp1_from_orderref(self):
        eod = _import_eod()
        assert eod.classify_exit_by_ref("IFDS_MRVL_A_TP") == "TP1"

    def test_tp2_from_orderref(self):
        eod = _import_eod()
        assert eod.classify_exit_by_ref("IFDS_COP_B_TP") == "TP2"

    def test_sl_from_orderref(self):
        eod = _import_eod()
        assert eod.classify_exit_by_ref("IFDS_LB_A_SL") == "SL"
        assert eod.classify_exit_by_ref("IFDS_LB_B_SL") == "SL"

    def test_loss_exit_from_orderref(self):
        eod = _import_eod()
        assert eod.classify_exit_by_ref("IFDS_BTU_LOSS_EXIT") == "LOSS_EXIT"

    def test_trail_b_from_orderref(self):
        eod = _import_eod()
        assert eod.classify_exit_by_ref("IFDS_CSGS_B_TRAIL") == "TRAIL"

    def test_trail_full_from_orderref(self):
        eod = _import_eod()
        assert eod.classify_exit_by_ref("IFDS_CRUS_TRAIL") == "TRAIL"

    def test_empty_orderref_returns_none(self):
        eod = _import_eod()
        assert eod.classify_exit_by_ref("") is None
        assert eod.classify_exit_by_ref(None) is None

    def test_unknown_orderref_returns_none(self):
        eod = _import_eod()
        assert eod.classify_exit_by_ref("IFDS_MRVL_AVWAP") is None
        assert eod.classify_exit_by_ref("IFDS_COP") is None

    def test_trail_suffix_priority_over_sl(self):
        """_B_TRAIL ends with _TRAIL, not _SL — must be TRAIL."""
        eod = _import_eod()
        assert eod.classify_exit_by_ref("IFDS_XYZ_B_TRAIL") == "TRAIL"


# ---------------------------------------------------------------------------
# build_trade_report() with orderRef integration
# ---------------------------------------------------------------------------


class TestBuildTradeReportOrderRef:
    """orderRef flows through to exit_type in trade records."""

    def test_loss_exit_classified_from_orderref(self):
        """SELL fill with LOSS_EXIT orderRef → exit_type='LOSS_EXIT'."""
        eod = _import_eod()

        buy = _make_fill('BTU', 'BOT', 36.27, 59, order_ref='IFDS_BTU')
        sell = _make_fill('BTU', 'SLD', 35.71, 59, order_ref='IFDS_BTU_LOSS_EXIT')
        meta = {'BTU': {'score': 75, 'sector': 'Energy', 'sl_price': 34.0,
                        'tp1_price': 38.0, 'tp2_price': 40.0}}

        trades = eod.build_trade_report([buy, sell], meta)

        assert len(trades) == 1
        assert trades[0]['exit_type'] == 'LOSS_EXIT'
        assert trades[0]['ticker'] == 'BTU'

    def test_trail_classified_from_orderref(self):
        """SELL fill with B_TRAIL orderRef → exit_type='TRAIL'."""
        eod = _import_eod()

        buy = _make_fill('CSGS', 'BOT', 80.16, 250, order_ref='IFDS_CSGS_B')
        sell = _make_fill('CSGS', 'SLD', 81.50, 250, order_ref='IFDS_CSGS_B_TRAIL')
        meta = {'CSGS': {'score': 85, 'sector': 'Technology', 'sl_price': 78.0,
                         'tp1_price': 82.0, 'tp2_price': 84.0}}

        trades = eod.build_trade_report([buy, sell], meta)

        assert len(trades) == 1
        assert trades[0]['exit_type'] == 'TRAIL'

    def test_tp1_from_orderref_overrides_price_match(self):
        """orderRef takes precedence over price-based classification."""
        eod = _import_eod()

        buy = _make_fill('COP', 'BOT', 125.0, 44, order_ref='IFDS_COP_A')
        # Exit price matches SL tolerance but orderRef says TP1
        sell = _make_fill('COP', 'SLD', 122.02, 44, order_ref='IFDS_COP_A_TP')
        meta = {'COP': {'score': 80, 'sector': 'Energy', 'sl_price': 122.0,
                        'tp1_price': 128.0, 'tp2_price': 130.0}}

        trades = eod.build_trade_report([buy, sell], meta)

        assert len(trades) == 1
        assert trades[0]['exit_type'] == 'TP1'

    def test_moc_fallback_when_no_orderref(self):
        """Empty orderRef falls back to price-based → MOC."""
        eod = _import_eod()

        buy = _make_fill('LB', 'BOT', 71.31, 64, order_ref='')
        sell = _make_fill('LB', 'SLD', 72.06, 64, order_ref='')
        meta = {'LB': {'score': 70, 'sector': 'Energy', 'sl_price': 69.0,
                        'tp1_price': 74.0, 'tp2_price': 76.0}}

        trades = eod.build_trade_report([buy, sell], meta)

        assert len(trades) == 1
        assert trades[0]['exit_type'] == 'MOC'

    def test_mixed_exit_types_in_single_report(self):
        """Multiple tickers with different exit types in one report."""
        eod = _import_eod()

        fills = [
            _make_fill('AAA', 'BOT', 100.0, 10, order_ref='IFDS_AAA_A'),
            _make_fill('AAA', 'SLD', 103.0, 10, order_ref='IFDS_AAA_A_TP'),
            _make_fill('BBB', 'BOT', 50.0, 20, order_ref='IFDS_BBB'),
            _make_fill('BBB', 'SLD', 48.0, 20, order_ref='IFDS_BBB_LOSS_EXIT'),
            _make_fill('CCC', 'BOT', 80.0, 15, order_ref='IFDS_CCC_B'),
            _make_fill('CCC', 'SLD', 82.0, 15, order_ref='IFDS_CCC_B_TRAIL'),
        ]
        meta = {
            'AAA': {'score': 85, 'sector': 'Tech', 'sl_price': 97, 'tp1_price': 103, 'tp2_price': 106},
            'BBB': {'score': 70, 'sector': 'Energy', 'sl_price': 47, 'tp1_price': 53, 'tp2_price': 55},
            'CCC': {'score': 78, 'sector': 'Fin', 'sl_price': 77, 'tp1_price': 83, 'tp2_price': 85},
        }

        trades = eod.build_trade_report(fills, meta)

        by_ticker = {t['ticker']: t['exit_type'] for t in trades}
        assert by_ticker == {'AAA': 'TP1', 'BBB': 'LOSS_EXIT', 'CCC': 'TRAIL'}


# ---------------------------------------------------------------------------
# update_cumulative_pnl() new fields
# ---------------------------------------------------------------------------


class TestCumulativePnlNewFields:
    """loss_exit_hits and trail_hits in daily_history."""

    def _make_trades_with_exits(self, exit_types):
        return [{'pnl': 10.0, 'commission': 1.0, 'exit_type': et} for et in exit_types]

    def test_loss_exit_counted(self, tmp_path):
        eod = _import_eod()
        eod.CUMULATIVE_PNL_FILE = str(tmp_path / "cum.json")
        eod.LOG_DIR = str(tmp_path)

        trades = self._make_trades_with_exits(['MOC', 'LOSS_EXIT', 'TP1', 'LOSS_EXIT'])
        data, _ = eod.update_cumulative_pnl(trades, "2026-03-23")

        entry = data['daily_history'][0]
        assert entry['loss_exit_hits'] == 2
        assert entry['trail_hits'] == 0
        assert entry['moc_exits'] == 1
        assert entry['tp1_hits'] == 1

    def test_trail_counted(self, tmp_path):
        eod = _import_eod()
        eod.CUMULATIVE_PNL_FILE = str(tmp_path / "cum.json")
        eod.LOG_DIR = str(tmp_path)

        trades = self._make_trades_with_exits(['TRAIL', 'MOC', 'TRAIL'])
        data, _ = eod.update_cumulative_pnl(trades, "2026-03-23")

        entry = data['daily_history'][0]
        assert entry['trail_hits'] == 2
        assert entry['loss_exit_hits'] == 0
        assert entry['moc_exits'] == 1

    def test_backward_compat_old_entries_no_new_fields(self, tmp_path):
        """Old daily_history entries without new fields don't break."""
        eod = _import_eod()
        pnl_file = tmp_path / "cum.json"
        eod.CUMULATIVE_PNL_FILE = str(pnl_file)
        eod.LOG_DIR = str(tmp_path)

        # Simulate old format (no loss_exit_hits/trail_hits)
        old_data = {
            'start_date': '2026-03-01',
            'initial_capital': 100000,
            'trading_days': 1,
            'cumulative_pnl': 100.0,
            'cumulative_pnl_pct': 0.1,
            'daily_history': [{
                'date': '2026-03-22',
                'pnl': 100.0,
                'commission': 5.0,
                'trades': 5,
                'filled': 5,
                'tp1_hits': 1,
                'tp2_hits': 0,
                'sl_hits': 0,
                'moc_exits': 4,
            }],
        }
        with open(pnl_file, 'w') as f:
            json.dump(old_data, f)

        trades = self._make_trades_with_exits(['LOSS_EXIT'])
        data, _ = eod.update_cumulative_pnl(trades, "2026-03-23")

        assert len(data['daily_history']) == 2
        # Old entry untouched
        assert 'loss_exit_hits' not in data['daily_history'][0]
        # New entry has fields
        assert data['daily_history'][1]['loss_exit_hits'] == 1
        assert data['daily_history'][1]['trail_hits'] == 0


# ---------------------------------------------------------------------------
# check_gateway.py
# ---------------------------------------------------------------------------


class TestCheckGateway:
    """Gateway health check script uses short timeout and correct clientId."""

    def test_check_gateway_uses_client_id_17(self):
        """check_gateway.py connects with clientId=17."""
        sys.modules['dotenv'] = MagicMock()
        import scripts.paper_trading.check_gateway as cg

        assert cg.HEALTH_CHECK_TIMEOUT == 3.0
        assert cg.HEALTH_CHECK_RETRIES == 1

    def test_check_gateway_short_timeout(self):
        """Health check timeout is shorter than default (15s)."""
        sys.modules['dotenv'] = MagicMock()
        import scripts.paper_trading.check_gateway as cg

        assert cg.HEALTH_CHECK_TIMEOUT < 5.0
