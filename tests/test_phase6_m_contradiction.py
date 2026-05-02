"""Phase 6 — M_contradiction multiplier tests."""
from __future__ import annotations

import pytest

from ifds.config.loader import Config
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
from ifds.phases.phase6_sizing import _calculate_multiplier_total


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    return Config()


@pytest.fixture
def macro():
    return MacroRegime(
        vix_value=18.0, vix_regime=MarketVolatilityRegime.NORMAL,
        vix_multiplier=1.0, tnx_value=4.2, tnx_sma20=4.1,
        tnx_rate_sensitive=False,
    )


def _stock(*, contradiction_flag: bool = False,
           reasons: tuple[str, ...] = ()) -> StockAnalysis:
    return StockAnalysis(
        ticker="T", sector="Technology",
        technical=TechnicalAnalysis(
            price=100.0, sma_200=90.0, sma_20=98.0,
            rsi_14=55.0, atr_14=2.0, trend_pass=True,
        ),
        flow=FlowAnalysis(),
        fundamental=FundamentalScoring(funda_score=15),
        combined_score=90.0,
        contradiction_flag=contradiction_flag,
        contradiction_reasons=reasons,
    )


def _gex() -> GEXAnalysis:
    return GEXAnalysis(
        ticker="T", net_gex=500.0, call_wall=0.0, put_wall=0.0,
        zero_gamma=90.0, current_price=100.0,
        gex_regime=GEXRegime.POSITIVE, gex_multiplier=1.0,
    )


class TestMContradiction:

    def test_applied_when_flagged(self, config, macro):
        """A flagged ticker receives the configured multiplier (default 0.80)."""
        stock = _stock(contradiction_flag=True, reasons=("earnings_beats_below_half (1/4)",))
        m_total, mults = _calculate_multiplier_total(stock, _gex(), macro, config)
        assert mults["m_contradiction"] == 0.80
        assert m_total == pytest.approx(0.80)

    def test_skipped_when_not_flagged(self, config, macro):
        """Non-flagged ticker → multiplier stays at 1.0 (no-op)."""
        stock = _stock(contradiction_flag=False)
        _, mults = _calculate_multiplier_total(stock, _gex(), macro, config)
        assert mults["m_contradiction"] == 1.0

    def test_disabled_via_config(self, config, macro):
        """m_contradiction_enabled=False → 1.0 even if the flag is set."""
        config.tuning["m_contradiction_enabled"] = False
        stock = _stock(contradiction_flag=True, reasons=("price_above_analyst_high",))
        _, mults = _calculate_multiplier_total(stock, _gex(), macro, config)
        assert mults["m_contradiction"] == 1.0

    def test_combined_with_other_multipliers(self, config, macro):
        """M_total chains M_gex × M_vix × M_target × M_contradiction."""
        # m_vix=0.9 (slight VIX penalty), m_gex=1.0, m_target=1.0, m_contradiction=0.80
        macro_v = MacroRegime(
            vix_value=22.0, vix_regime=MarketVolatilityRegime.NORMAL,
            vix_multiplier=0.9, tnx_value=4.2, tnx_sma20=4.1,
            tnx_rate_sensitive=False,
        )
        stock = _stock(contradiction_flag=True)
        m_total, mults = _calculate_multiplier_total(stock, _gex(), macro_v, config)
        # 1.0 (gex) × 0.9 (vix) × 1.0 (target) × 0.80 (contradiction) = 0.72
        assert mults["m_contradiction"] == 0.80
        assert mults["m_vix"] == 0.9
        assert m_total == pytest.approx(0.72, abs=1e-6)
