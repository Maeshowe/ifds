"""Tests for analyst price target contradiction penalty (M_target, Phase 6)."""

import pytest
from unittest.mock import MagicMock
from ifds.config.loader import Config
from ifds.phases.phase6_sizing import _calculate_target_multiplier, _calculate_multiplier_total
from ifds.models.market import (
    FlowAnalysis,
    FundamentalScoring,
    GEXAnalysis,
    GEXRegime,
    MacroRegime,
    MarketVolatilityRegime,
    StockAnalysis,
    TechnicalAnalysis,
)


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    monkeypatch.setenv("IFDS_ASYNC_ENABLED", "false")
    return Config()


class TestCalculateTargetMultiplier:
    def test_price_10_pct_above_target_no_penalty(self, config):
        result = _calculate_target_multiplier(110.0, 100.0, config)
        assert result == 1.0

    def test_price_25_pct_above_target_moderate_penalty(self, config):
        result = _calculate_target_multiplier(125.0, 100.0, config)
        assert result == pytest.approx(0.85)

    def test_price_55_pct_above_target_severe_penalty(self, config):
        result = _calculate_target_multiplier(155.0, 100.0, config)
        assert result == pytest.approx(0.60)

    def test_analyst_target_none_no_penalty(self, config):
        result = _calculate_target_multiplier(150.0, None, config)
        assert result == 1.0

    def test_analyst_target_zero_no_penalty(self, config):
        result = _calculate_target_multiplier(150.0, 0.0, config)
        assert result == 1.0

    def test_price_below_target_no_penalty(self, config):
        result = _calculate_target_multiplier(80.0, 100.0, config)
        assert result == 1.0

    def test_price_at_threshold_boundary(self, config):
        # Exactly 20% → not strictly > threshold → no penalty
        result = _calculate_target_multiplier(120.0, 100.0, config)
        assert result == 1.0

    def test_feature_disabled(self, config):
        config.tuning["target_overshoot_enabled"] = False
        result = _calculate_target_multiplier(200.0, 100.0, config)
        assert result == 1.0

    def test_custom_thresholds(self, config):
        config.tuning["target_overshoot_threshold"] = 0.10
        config.tuning["target_overshoot_penalty"] = 0.90
        result = _calculate_target_multiplier(115.0, 100.0, config)
        assert result == pytest.approx(0.90)


class TestMTargetInChain:
    def _make_stock(self, price=100.0, analyst_target=None):
        return StockAnalysis(
            ticker="TEST",
            sector="Technology",
            technical=TechnicalAnalysis(
                price=price, sma_200=90.0, sma_20=95.0,
                rsi_14=55.0, atr_14=3.0, trend_pass=True,
            ),
            flow=FlowAnalysis(),
            fundamental=FundamentalScoring(),
            combined_score=75.0,
            analyst_target=analyst_target,
        )

    def _make_gex(self):
        return GEXAnalysis(
            ticker="TEST",
            gex_regime=GEXRegime.POSITIVE,
            gex_multiplier=1.0,
        )

    def _make_macro(self):
        return MacroRegime(
            vix_value=18.0,
            vix_regime=MarketVolatilityRegime.LOW,
            vix_multiplier=1.0,
            tnx_value=4.2,
            tnx_sma20=4.1,
            tnx_rate_sensitive=False,
        )

    def test_m_target_included_in_multipliers_dict(self, config):
        stock = self._make_stock(price=100.0, analyst_target=None)
        _, multipliers = _calculate_multiplier_total(stock, self._make_gex(), self._make_macro(), config)
        assert "m_target" in multipliers
        assert multipliers["m_target"] == 1.0

    def test_m_target_penalty_reduces_m_total(self, config):
        # 55% above target → severe penalty 0.60
        stock_no_target = self._make_stock(price=100.0, analyst_target=None)
        stock_with_target = self._make_stock(price=155.0, analyst_target=100.0)

        _, mult_no = _calculate_multiplier_total(stock_no_target, self._make_gex(), self._make_macro(), config)
        _, mult_with = _calculate_multiplier_total(stock_with_target, self._make_gex(), self._make_macro(), config)

        assert mult_with["m_target"] == pytest.approx(0.60)
        assert mult_no["m_target"] == 1.0

    def test_m_total_clamp_preserved(self, config):
        # Even with severe penalty, m_total floor is 0.25
        stock = self._make_stock(price=200.0, analyst_target=100.0)
        m_total, _ = _calculate_multiplier_total(stock, self._make_gex(), self._make_macro(), config)
        assert m_total >= 0.25
        assert m_total <= 2.0
