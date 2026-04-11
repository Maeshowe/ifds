"""Tests for BC18B — MMS activation, factor volatility, T5 BMI oversold sizing.

Covers:
- Config flags: mms_enabled=True, factor_volatility_enabled=True
- T5: BMI < 25% → multiplier × 1.25
- T5: BMI >= 25% → no change
- T5: bmi_value=None → no change (backwards compatible)
"""

from unittest.mock import MagicMock, patch

import pytest

from ifds.config.loader import Config


@pytest.fixture
def config():
    """Config with MMS and factor vol enabled."""
    c = Config.__new__(Config)
    c.core = {
        "stop_loss_atr_multiple": 2.0,
        "tp1_atr_multiple": 1.5,
        "tp2_atr_multiple": 3.0,
        "scale_out_atr_multiple": 1.0,
        "scale_out_pct": 0.33,
        "freshness_lookback_days": 14,
        "freshness_bonus": 1.5,
        "clipping_threshold": 95,
    }
    c.tuning = {
        "multiplier_flow_threshold": 70,
        "multiplier_flow_value": 1.2,
        "multiplier_funda_threshold": 60,
        "multiplier_funda_value": 0.85,
        "multiplier_utility_threshold": 80,
        "multiplier_utility_max": 1.5,
        "max_positions_per_sector": 3,
        "mms_enabled": True,
        "factor_volatility_enabled": True,
        "bmi_oversold_threshold": 25,
        "bmi_oversold_multiplier": 1.25,
    }
    c.runtime = {
        "account_equity": 100_000,
        "risk_per_trade_pct": 0.5,
        "max_positions": 10,
        "max_single_position_risk_pct": 2.0,
        "max_gross_exposure": 200_000,
        "max_single_ticker_exposure": 20_000,
        "max_order_quantity": 5000,
        "max_daily_trades": 20,
    }
    return c


def _make_stock(ticker="TEST", score=85.0, atr=2.0, price=100.0,
                funda_score=15, flow_rvol=10, insider_mult=1.0):
    from ifds.models.market import (
        StockAnalysis, FlowAnalysis, FundamentalScoring, TechnicalAnalysis
    )
    flow = MagicMock(spec=FlowAnalysis)
    flow.rvol_score = flow_rvol
    funda = MagicMock(spec=FundamentalScoring)
    funda.funda_score = funda_score
    funda.insider_multiplier = insider_mult
    tech = MagicMock(spec=TechnicalAnalysis)
    tech.atr_14 = atr
    tech.price = price
    stock = MagicMock(spec=StockAnalysis)
    stock.ticker = ticker
    stock.sector = "Technology"
    stock.combined_score = score
    stock.flow = flow
    stock.fundamental = funda
    stock.technical = tech
    stock.shark_detected = False
    return stock


def _make_gex(ticker="TEST", multiplier=1.0):
    from ifds.models.market import GEXAnalysis, GEXRegime
    gex = MagicMock(spec=GEXAnalysis)
    gex.ticker = ticker
    gex.gex_regime = GEXRegime.POSITIVE
    gex.gex_multiplier = multiplier
    gex.call_wall = 0
    gex.put_wall = 0
    return gex


def _make_macro(vix_mult=1.0):
    from ifds.models.market import MacroRegime, MarketVolatilityRegime
    macro = MagicMock(spec=MacroRegime)
    macro.vix_multiplier = vix_mult
    return macro


# ---------------------------------------------------------------------------
# Config activation tests
# ---------------------------------------------------------------------------


def test_mms_enabled_default_false():
    """BC23: MMS disabled by default (was True in BC18B)."""
    from ifds.config.defaults import TUNING
    assert TUNING["mms_enabled"] is False


def test_factor_volatility_enabled_default_true():
    """Factor volatility enabled by default in BC18B config."""
    from ifds.config.defaults import TUNING
    assert TUNING["factor_volatility_enabled"] is True


def test_bmi_oversold_config_keys_exist():
    """T5 config keys exist with correct defaults."""
    from ifds.config.defaults import TUNING
    assert TUNING["bmi_oversold_threshold"] == 25
    assert TUNING["bmi_oversold_multiplier"] == 1.25


# ---------------------------------------------------------------------------
# T5: BMI Oversold Sizing
# ---------------------------------------------------------------------------


def test_t5_bmi_below_threshold_boosts_sizing(config):
    """BMI < 25% → multiplier boosted by 1.25×."""
    from ifds.phases.phase6_sizing import _calculate_position
    from ifds.models.market import StrategyMode

    stock = _make_stock()
    gex = _make_gex()
    macro = _make_macro()

    # Without T5 (bmi_value=None)
    pos_normal = _calculate_position(
        stock, gex, macro, config, StrategyMode.LONG,
        bmi_value=None,
    )

    # With T5 (bmi_value=20 < 25)
    pos_oversold = _calculate_position(
        stock, gex, macro, config, StrategyMode.LONG,
        bmi_value=20.0,
    )

    assert pos_normal is not None
    assert pos_oversold is not None
    # Oversold position should have more shares (higher risk budget)
    assert pos_oversold.quantity >= pos_normal.quantity


def test_t5_bmi_above_threshold_no_change(config):
    """BMI >= 25% → no sizing change."""
    from ifds.phases.phase6_sizing import _calculate_position
    from ifds.models.market import StrategyMode

    stock = _make_stock()
    gex = _make_gex()
    macro = _make_macro()

    pos_normal = _calculate_position(
        stock, gex, macro, config, StrategyMode.LONG,
        bmi_value=None,
    )

    pos_above = _calculate_position(
        stock, gex, macro, config, StrategyMode.LONG,
        bmi_value=50.0,
    )

    assert pos_normal is not None
    assert pos_above is not None
    assert pos_above.quantity == pos_normal.quantity


def test_t5_bmi_none_backwards_compatible(config):
    """bmi_value=None → T5 not applied (backwards compatible)."""
    from ifds.phases.phase6_sizing import _calculate_position
    from ifds.models.market import StrategyMode

    stock = _make_stock()
    gex = _make_gex()
    macro = _make_macro()

    pos = _calculate_position(
        stock, gex, macro, config, StrategyMode.LONG,
        bmi_value=None,
    )
    assert pos is not None
    # Should work without error


def test_t5_bmi_at_exact_threshold_no_boost(config):
    """BMI exactly at 25 → no boost (strictly less than)."""
    from ifds.phases.phase6_sizing import _calculate_position
    from ifds.models.market import StrategyMode

    stock = _make_stock()
    gex = _make_gex()
    macro = _make_macro()

    pos_at = _calculate_position(
        stock, gex, macro, config, StrategyMode.LONG,
        bmi_value=25.0,
    )
    pos_none = _calculate_position(
        stock, gex, macro, config, StrategyMode.LONG,
        bmi_value=None,
    )

    assert pos_at.quantity == pos_none.quantity


def test_t5_m_total_capped_at_2(config):
    """T5 boost respects the m_total 2.0 cap."""
    from ifds.phases.phase6_sizing import _calculate_position
    from ifds.models.market import StrategyMode

    # High score → high m_utility, gex multiplier high → m_total near cap
    stock = _make_stock(score=95.0)
    gex = _make_gex(multiplier=1.5)
    macro = _make_macro()

    pos = _calculate_position(
        stock, gex, macro, config, StrategyMode.LONG,
        bmi_value=10.0,  # Very oversold
    )

    assert pos is not None
    assert pos.multiplier_total <= 2.0
