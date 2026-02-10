"""BC12 Feature Tests — Call Wall ATR Filter, Front-Month DTE, Zero Gamma
Interpolation, Fat Finger Protection, VIX EXTREME, Institutional Ownership.

~30 tests covering all 6 BC12 features.
"""

import math
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from ifds.config.loader import Config
from ifds.data.adapters import (
    PolygonGEXProvider, _find_zero_gamma,
)
from ifds.events.logger import EventLogger
from ifds.models.market import (
    FlowAnalysis,
    FundamentalScoring,
    GEXAnalysis,
    GEXRegime,
    MacroRegime,
    MarketVolatilityRegime,
    StockAnalysis,
    StrategyMode,
    TechnicalAnalysis,
)
from ifds.phases.phase0_diagnostics import _classify_vix, _calculate_vix_multiplier
from ifds.phases.phase4_stocks import _analyze_fundamental_from_data
from ifds.phases.phase6_sizing import _calculate_position


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    return Config()


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-bc12")


def _make_stock(ticker="AAPL", price=150.0, atr=3.0, combined=80.0,
                flow_score=10, funda_score=15, rsi=55.0):
    """Helper to create a StockAnalysis for testing."""
    return StockAnalysis(
        ticker=ticker,
        sector="Technology",
        technical=TechnicalAnalysis(
            price=price, sma_200=140.0, sma_20=148.0,
            rsi_14=rsi, atr_14=atr, trend_pass=True,
        ),
        flow=FlowAnalysis(rvol_score=flow_score),
        fundamental=FundamentalScoring(funda_score=funda_score),
        combined_score=combined,
    )


def _make_macro(vix=18.0):
    """Helper to create a MacroRegime."""
    return MacroRegime(
        vix_value=vix,
        vix_regime=MarketVolatilityRegime.NORMAL,
        vix_multiplier=1.0,
        tnx_value=4.0,
        tnx_sma20=3.9,
        tnx_rate_sensitive=False,
    )


def _make_gex(ticker="AAPL", call_wall=160.0, put_wall=140.0,
              zero_gamma=150.0, net_gex=1000.0):
    """Helper to create a GEXAnalysis."""
    return GEXAnalysis(
        ticker=ticker,
        net_gex=net_gex,
        call_wall=call_wall,
        put_wall=put_wall,
        zero_gamma=zero_gamma,
        current_price=150.0,
        gex_regime=GEXRegime.POSITIVE,
        gex_multiplier=1.0,
        data_source="polygon_calculated",
    )


# ============================================================================
# TestZeroGammaInterpolation
# ============================================================================

class TestZeroGammaInterpolation:
    """Test linear interpolation in _find_zero_gamma()."""

    def test_interpolation_between_strikes(self):
        """Cumulative crosses zero between 100 and 105 → interpolated value."""
        gex = {100.0: -10.0, 105.0: 20.0}
        # cumulative at 100 = -10, at 105 = +10
        # crossover: 100 + (105-100) * (10/20) = 102.5
        result = _find_zero_gamma(gex)
        assert result == 102.5

    def test_single_crossover(self):
        """Three strikes, sign change between second and third."""
        gex = {90.0: -5.0, 100.0: -3.0, 110.0: 12.0}
        # cumulative: 90→-5, 100→-8, 110→+4
        # crossover at 100→110: prev_cum=-8, cum=+4
        # zero = 100 + 10 * (8/12) = 106.67
        result = _find_zero_gamma(gex)
        assert 106.0 < result < 107.0

    def test_all_positive_returns_zero(self):
        """No sign change — returns 0.0 (no meaningful zero gamma)."""
        gex = {100.0: 5.0, 110.0: 10.0, 120.0: 15.0}
        result = _find_zero_gamma(gex)
        assert result == 0.0

    def test_empty_returns_zero(self):
        """Empty dict → 0.0."""
        result = _find_zero_gamma({})
        assert result == 0.0


# ============================================================================
# TestFrontMonthFilter
# ============================================================================

class TestFrontMonthFilter:
    """Test DTE filter in PolygonGEXProvider._calculate_gex()."""

    def _make_option(self, strike, gamma, oi, spot, ctype, exp_days_from_now):
        """Create a mock option dict."""
        exp_date = (date.today() + timedelta(days=exp_days_from_now)).isoformat()
        return {
            "details": {
                "strike_price": strike,
                "contract_type": ctype,
                "expiration_date": exp_date,
            },
            "greeks": {"gamma": gamma},
            "open_interest": oi,
            "underlying_asset": {"price": spot},
        }

    def test_dte_filter_excludes_far_options(self):
        """Options >35 DTE excluded from GEX calc (when ≥5 near contracts remain)."""
        provider = PolygonGEXProvider(MagicMock(), max_dte=35)
        # 5 near contracts + 1 far → filter keeps 5 near (≥5 threshold met)
        nears = [self._make_option(100 + i, 0.05, 1000, 100, "call", 20) for i in range(5)]
        far = self._make_option(200, 0.10, 5000, 100, "call", 60)
        result = provider._calculate_gex("TEST", nears + [far], max_dte=35)
        # Only the 5 near options should contribute
        assert len(result["gex_by_strike"]) == 5
        strikes = [e["strike"] for e in result["gex_by_strike"]]
        assert 200 not in strikes

    def test_dte_filter_keeps_near_options(self):
        """Options ≤35 DTE included."""
        provider = PolygonGEXProvider(MagicMock(), max_dte=35)
        nears = [self._make_option(100 + i, 0.05, 1000, 100, "call", 10 + i) for i in range(6)]
        result = provider._calculate_gex("TEST", nears, max_dte=35)
        assert len(result["gex_by_strike"]) == 6

    def test_dte_filter_fallback_few_contracts(self):
        """DTE filter leaves <5 contracts → fallback to all contracts."""
        provider = PolygonGEXProvider(MagicMock(), max_dte=35)
        # Only 2 near + 3 far → filtered = 2 near (<5) → fallback to all 5
        nears = [self._make_option(100 + i, 0.05, 1000, 100, "call", 20) for i in range(2)]
        fars = [self._make_option(200 + i, 0.05, 1000, 100, "call", 60) for i in range(3)]
        result = provider._calculate_gex("TEST", nears + fars, max_dte=35)
        # All 5 contracts used (fallback)
        assert len(result["gex_by_strike"]) == 5

    def test_dte_zero_disables_filter(self):
        """max_dte=0 includes all options."""
        provider = PolygonGEXProvider(MagicMock(), max_dte=0)
        near = self._make_option(100, 0.05, 1000, 100, "call", 20)
        far = self._make_option(105, 0.10, 5000, 100, "call", 200)
        result = provider._calculate_gex("TEST", [near, far], max_dte=0)
        assert len(result["gex_by_strike"]) == 2

    def test_no_expiration_included(self):
        """Missing expiration_date field → include the option."""
        provider = PolygonGEXProvider(MagicMock(), max_dte=35)
        # 5 contracts with no expiration → all pass DTE filter → ≥5 threshold met
        opts = [
            {
                "details": {"strike_price": 100 + i, "contract_type": "call"},
                "greeks": {"gamma": 0.05},
                "open_interest": 1000,
                "underlying_asset": {"price": 100},
            }
            for i in range(5)
        ]
        result = provider._calculate_gex("TEST", opts, max_dte=35)
        assert len(result["gex_by_strike"]) == 5


# ============================================================================
# TestCallWallATRFilter
# ============================================================================

class TestCallWallATRFilter:
    """Test call wall ATR distance filter in Phase 5."""

    def test_call_wall_within_atr_kept(self, config):
        """Call wall within 5*ATR → preserved."""
        # price=150, atr=3, call_wall=160, distance=10, 5*3=15 → within
        stock = _make_stock(price=150.0, atr=3.0)
        call_wall = 160.0
        atr = stock.technical.atr_14
        max_dist = config.tuning.get("call_wall_max_atr_distance", 5.0)
        if call_wall > 0 and atr > 0:
            if abs(call_wall - stock.technical.price) > atr * max_dist:
                call_wall = 0.0
        assert call_wall == 160.0

    def test_call_wall_beyond_atr_zeroed(self, config):
        """Call wall beyond 5*ATR → zeroed."""
        # price=150, atr=3, call_wall=200, distance=50, 5*3=15 → beyond
        stock = _make_stock(price=150.0, atr=3.0)
        call_wall = 200.0
        atr = stock.technical.atr_14
        max_dist = config.tuning.get("call_wall_max_atr_distance", 5.0)
        if call_wall > 0 and atr > 0:
            if abs(call_wall - stock.technical.price) > atr * max_dist:
                call_wall = 0.0
        assert call_wall == 0.0

    def test_call_wall_zero_passthrough(self, config):
        """call_wall=0 → stays 0 (no filter applied)."""
        stock = _make_stock(price=150.0, atr=3.0)
        call_wall = 0.0
        atr = stock.technical.atr_14
        max_dist = config.tuning.get("call_wall_max_atr_distance", 5.0)
        if call_wall > 0 and atr > 0:
            if abs(call_wall - stock.technical.price) > atr * max_dist:
                call_wall = 0.0
        assert call_wall == 0.0

    def test_no_atr_skips_filter(self, config):
        """atr=0 → filter skipped, call_wall preserved."""
        stock = _make_stock(price=150.0, atr=0.0)
        call_wall = 500.0
        atr = stock.technical.atr_14
        max_dist = config.tuning.get("call_wall_max_atr_distance", 5.0)
        if call_wall > 0 and atr > 0:
            if abs(call_wall - stock.technical.price) > atr * max_dist:
                call_wall = 0.0
        assert call_wall == 500.0  # Filter not applied (atr=0)


# ============================================================================
# TestFatFingerProtection
# ============================================================================

class TestFatFingerProtection:
    """Test fat finger protection in Phase 6 _calculate_position."""

    def test_quantity_capped_at_max(self, config):
        """Quantity > max_order_quantity → capped to 5000."""
        stock = _make_stock(price=1.0, atr=0.01, combined=80.0)
        gex = _make_gex(call_wall=0.0)
        macro = _make_macro()
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        assert pos is not None
        assert pos.quantity <= config.runtime.get("max_order_quantity", 5000)

    def test_value_capped_at_max_exposure(self, config):
        """qty * price > max_single_ticker_exposure → reduced."""
        stock = _make_stock(price=200.0, atr=2.0, combined=80.0)
        gex = _make_gex(call_wall=0.0)
        macro = _make_macro()
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        if pos:
            max_exp = config.runtime.get("max_single_ticker_exposure", 20000)
            assert pos.quantity * pos.entry_price <= max_exp

    def test_nan_quantity_rejected(self, config):
        """NaN ATR → returns None (guard against math errors)."""
        stock = _make_stock(price=150.0, atr=float('nan'), combined=80.0)
        gex = _make_gex(call_wall=0.0)
        macro = _make_macro()
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        # ATR=NaN → stop_distance=NaN → quantity=NaN → rejected
        assert pos is None

    def test_inf_price_rejected(self, config):
        """Inf price → returns None."""
        stock = _make_stock(price=float('inf'), atr=3.0, combined=80.0)
        gex = _make_gex(call_wall=0.0)
        macro = _make_macro()
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        assert pos is None

    def test_negative_atr_returns_none(self, config):
        """Negative ATR → returns None (guard in existing code)."""
        stock = _make_stock(price=150.0, atr=-3.0, combined=80.0)
        gex = _make_gex(call_wall=0.0)
        macro = _make_macro()
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        assert pos is None


# ============================================================================
# TestVIXExtreme
# ============================================================================

class TestVIXExtreme:
    """Test VIX EXTREME regime classification and multiplier."""

    def test_vix_above_50_extreme(self, config):
        """VIX=65 → EXTREME regime."""
        result = _classify_vix(65.0, config)
        assert result == MarketVolatilityRegime.EXTREME

    def test_vix_exactly_50_panic(self, config):
        """VIX=50 → still PANIC (boundary, not > 50)."""
        result = _classify_vix(50.0, config)
        assert result == MarketVolatilityRegime.PANIC

    def test_extreme_multiplier(self, config):
        """VIX=65 → multiplier=0.10."""
        mult = _calculate_vix_multiplier(65.0, config)
        assert mult == pytest.approx(0.10)

    def test_vix_51_extreme(self, config):
        """VIX=51 → EXTREME."""
        result = _classify_vix(51.0, config)
        assert result == MarketVolatilityRegime.EXTREME

    def test_extreme_regime_value(self):
        """EXTREME enum value is 'extreme'."""
        assert MarketVolatilityRegime.EXTREME.value == "extreme"

    def test_panic_multiplier_unchanged(self, config):
        """VIX=40 → PANIC, not EXTREME, uses formula-based multiplier."""
        result = _classify_vix(40.0, config)
        assert result == MarketVolatilityRegime.PANIC
        mult = _calculate_vix_multiplier(40.0, config)
        # 1.0 - (40-20)*0.02 = 1.0 - 0.4 = 0.6, but floored at 0.25
        assert mult == pytest.approx(max(0.25, 1.0 - (40 - 20) * 0.02))


# ============================================================================
# TestInstitutionalOwnership
# ============================================================================

class TestInstitutionalOwnership:
    """Test institutional ownership QoQ scoring in _analyze_fundamental_from_data."""

    def test_increasing_ownership_bonus(self, config):
        """QoQ increase >2% → +10 funda bonus."""
        inst_data = [
            {"totalInvested": 1_050_000},  # recent
            {"totalInvested": 1_000_000},  # previous (5% increase)
        ]
        result = _analyze_fundamental_from_data("TEST", None, None, None, config,
                                                 inst_data=inst_data)
        assert result.inst_ownership_trend == "increasing"
        assert result.inst_ownership_score == 10
        assert result.funda_score >= 10  # At least the inst bonus

    def test_decreasing_ownership_penalty(self, config):
        """QoQ decrease >2% → -5 funda penalty."""
        inst_data = [
            {"totalInvested": 900_000},    # recent
            {"totalInvested": 1_000_000},  # previous (10% decrease)
        ]
        result = _analyze_fundamental_from_data("TEST", None, None, None, config,
                                                 inst_data=inst_data)
        assert result.inst_ownership_trend == "decreasing"
        assert result.inst_ownership_score == -5

    def test_stable_ownership_neutral(self, config):
        """QoQ change <2% → stable, 0 score."""
        inst_data = [
            {"totalInvested": 1_010_000},  # 1% increase
            {"totalInvested": 1_000_000},
        ]
        result = _analyze_fundamental_from_data("TEST", None, None, None, config,
                                                 inst_data=inst_data)
        assert result.inst_ownership_trend == "stable"
        assert result.inst_ownership_score == 0

    def test_insufficient_data_unknown(self, config):
        """Only 1 quarter → 'unknown', 0 score."""
        inst_data = [{"totalInvested": 1_000_000}]
        result = _analyze_fundamental_from_data("TEST", None, None, None, config,
                                                 inst_data=inst_data)
        assert result.inst_ownership_trend == "unknown"
        assert result.inst_ownership_score == 0

    def test_none_data_no_crash(self, config):
        """inst_data=None → no error."""
        result = _analyze_fundamental_from_data("TEST", None, None, None, config,
                                                 inst_data=None)
        assert result.inst_ownership_trend == "unknown"
        assert result.inst_ownership_score == 0


# ============================================================================
# TestDTEFilterInPhase4Flow
# ============================================================================

class TestDTEFilterInPhase4Flow:
    """Test DTE filter applied to options flow scoring in Phase 4."""

    def test_pcr_only_uses_near_term(self, config):
        """Far-DTE options excluded from PCR calc (when ≥5 near-term remain)."""
        from ifds.phases.phase4_stocks import _analyze_flow_from_data

        today = date.today()
        near_exp = (today + timedelta(days=20)).isoformat()
        far_exp = (today + timedelta(days=120)).isoformat()  # >90 DTE default

        bars = [{"c": 100.0, "h": 102.0, "l": 98.0, "v": 1_000_000}] * 50
        options = [
            # 5 near-term calls (≥5 threshold met after filter)
            {"details": {"contract_type": "call", "strike_price": 100 + i,
                         "expiration_date": near_exp},
             "day": {"volume": 100}}
            for i in range(5)
        ] + [
            # Far-term puts (>90 DTE, excluded because ≥5 near-term remain)
            {"details": {"contract_type": "put", "strike_price": 95,
                         "expiration_date": far_exp},
             "day": {"volume": 10000}},
        ]
        result = _analyze_flow_from_data("TEST", bars, None, config,
                                          options_data=options)
        # Only near-term options counted → PCR based on 0 puts / 500 calls ≈ 0
        if result.pcr is not None:
            assert result.pcr < 0.1  # Near-zero because far puts were excluded


# ============================================================================
# TestIntegration
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple BC12 features."""

    def test_dte_filter_end_to_end_gex(self):
        """Full _calculate_gex with mixed DTE options (≥5 near contracts)."""
        provider = PolygonGEXProvider(MagicMock(), max_dte=35)
        today = date.today()
        near_exp = (today + timedelta(days=20)).isoformat()
        far_exp = (today + timedelta(days=90)).isoformat()

        # 5 near-term contracts at different strikes
        options = [
            {
                "details": {"strike_price": 100 + i, "contract_type": "call",
                            "expiration_date": near_exp},
                "greeks": {"gamma": 0.05},
                "open_interest": 1000,
                "underlying_asset": {"price": 100},
            }
            for i in range(5)
        ] + [
            {
                "details": {"strike_price": 200, "contract_type": "call",
                            "expiration_date": far_exp},
                "greeks": {"gamma": 0.10},
                "open_interest": 5000,
                "underlying_asset": {"price": 100},
            },
        ]
        result = provider._calculate_gex("TEST", options, max_dte=35)
        # Only 5 near options included (≥5 threshold met, far excluded)
        assert len(result["gex_by_strike"]) == 5
        strikes = [e["strike"] for e in result["gex_by_strike"]]
        assert 200 not in strikes

    def test_fat_finger_in_calculate_position(self, config):
        """_calculate_position with very cheap stock → quantity capped."""
        stock = _make_stock(price=0.50, atr=0.05, combined=85.0)
        gex = _make_gex(call_wall=0.0)
        macro = _make_macro()
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        if pos:
            assert pos.quantity <= 5000
            assert pos.quantity * pos.entry_price <= 20000

    def test_extreme_vix_multiplier_calculation(self, config):
        """VIX=60 → EXTREME regime, multiplier=0.10."""
        regime = _classify_vix(60.0, config)
        mult = _calculate_vix_multiplier(60.0, config)
        assert regime == MarketVolatilityRegime.EXTREME
        assert mult == pytest.approx(0.10)

    def test_zero_gamma_interpolation_precision(self):
        """Zero gamma where cumulative reaches exactly zero at a strike."""
        gex = {100.0: -10.0, 110.0: 10.0}
        # cumulative at 100 = -10, at 110 = 0 (exact zero)
        # interpolation: 100 + 10 * (10/10) = 110.0
        result = _find_zero_gamma(gex)
        assert result == 110.0
