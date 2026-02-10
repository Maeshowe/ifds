"""Tests for Phase 5: GEX (Gamma Exposure) Analysis."""

import pytest
from unittest.mock import MagicMock

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import (
    FlowAnalysis,
    FundamentalScoring,
    GEXRegime,
    StockAnalysis,
    StrategyMode,
    TechnicalAnalysis,
)
from ifds.phases.phase5_gex import (
    run_phase5,
    _classify_gex_regime,
    _get_gex_multiplier,
)


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    return Config()


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-phase5")


def _make_stock(ticker, price=150.0, combined_score=75.0):
    """Create a mock StockAnalysis for Phase 5 input."""
    return StockAnalysis(
        ticker=ticker,
        sector="Technology",
        technical=TechnicalAnalysis(
            price=price, sma_200=140.0, sma_20=148.0,
            rsi_14=55.0, atr_14=2.5, trend_pass=True,
        ),
        flow=FlowAnalysis(),
        fundamental=FundamentalScoring(),
        combined_score=combined_score,
    )


# ============================================================================
# GEX Regime Classification Tests
# ============================================================================

class TestGEXClassification:
    def test_positive_regime(self):
        # Price > ZeroGamma AND NetGEX > 0
        regime = _classify_gex_regime(
            current_price=160.0, zero_gamma=150.0, net_gex=1000.0
        )
        assert regime == GEXRegime.POSITIVE

    def test_negative_regime(self):
        # Price < ZeroGamma
        regime = _classify_gex_regime(
            current_price=140.0, zero_gamma=150.0, net_gex=-500.0
        )
        assert regime == GEXRegime.NEGATIVE

    def test_high_vol_transition_zone(self):
        # Within 2% of ZeroGamma
        regime = _classify_gex_regime(
            current_price=151.0, zero_gamma=150.0, net_gex=1000.0
        )
        # 1/150 * 100 = 0.67% → within 2%
        assert regime == GEXRegime.HIGH_VOL

    def test_high_vol_price_above_but_negative_gex(self):
        # Price > ZeroGamma but NetGEX <= 0 → HIGH_VOL
        regime = _classify_gex_regime(
            current_price=200.0, zero_gamma=150.0, net_gex=-100.0
        )
        assert regime == GEXRegime.HIGH_VOL

    def test_zero_gamma_zero_defaults_positive(self):
        # No zero gamma data → POSITIVE (assume benign)
        regime = _classify_gex_regime(
            current_price=150.0, zero_gamma=0.0, net_gex=0.0
        )
        assert regime == GEXRegime.POSITIVE

    def test_negative_zero_gamma_defaults_positive(self):
        regime = _classify_gex_regime(
            current_price=150.0, zero_gamma=-10.0, net_gex=0.0
        )
        assert regime == GEXRegime.POSITIVE

    def test_transition_zone_boundary_2_pct(self):
        # Exactly 2% away → should be HIGH_VOL
        zero_gamma = 100.0
        price = 102.0  # 2% distance
        regime = _classify_gex_regime(price, zero_gamma, net_gex=500.0)
        assert regime == GEXRegime.HIGH_VOL

    def test_just_outside_transition_zone(self):
        # Just beyond 2% → POSITIVE (price > zero_gamma, net_gex > 0)
        zero_gamma = 100.0
        price = 102.1  # 2.1% distance
        regime = _classify_gex_regime(price, zero_gamma, net_gex=500.0)
        assert regime == GEXRegime.POSITIVE

    def test_negative_just_outside_transition(self):
        # Below zero gamma, outside 2% → NEGATIVE
        zero_gamma = 100.0
        price = 97.5  # 2.5% below
        regime = _classify_gex_regime(price, zero_gamma, net_gex=-100.0)
        assert regime == GEXRegime.NEGATIVE


# ============================================================================
# GEX Multiplier Tests
# ============================================================================

class TestGEXMultiplier:
    def test_positive_multiplier(self, config):
        mult = _get_gex_multiplier(GEXRegime.POSITIVE, config)
        assert mult == 1.0

    def test_negative_multiplier(self, config):
        mult = _get_gex_multiplier(GEXRegime.NEGATIVE, config)
        assert mult == 0.5

    def test_high_vol_multiplier(self, config):
        mult = _get_gex_multiplier(GEXRegime.HIGH_VOL, config)
        assert mult == 0.6


# ============================================================================
# Phase 5 Integration Tests
# ============================================================================

class TestPhase5Integration:
    def test_long_excludes_negative(self, config, logger):
        """NEGATIVE regime excluded in LONG mode."""
        gex_provider = MagicMock()
        gex_provider.get_gex.return_value = {
            "net_gex": -500.0,
            "call_wall": 160.0,
            "put_wall": 130.0,
            "zero_gamma": 200.0,  # Price (150) < zero_gamma → NEGATIVE
            "source": "test",
        }

        stocks = [_make_stock("AAPL", price=150.0)]
        result = run_phase5(config, logger, gex_provider, stocks, StrategyMode.LONG)

        assert result.excluded_count == 1
        assert result.negative_regime_count == 1
        assert len(result.passed) == 0

    def test_short_allows_negative(self, config, logger):
        """NEGATIVE regime NOT excluded in SHORT mode."""
        gex_provider = MagicMock()
        gex_provider.get_gex.return_value = {
            "net_gex": -500.0,
            "call_wall": 160.0,
            "put_wall": 130.0,
            "zero_gamma": 200.0,  # NEGATIVE
            "source": "test",
        }

        stocks = [_make_stock("AAPL", price=150.0)]
        result = run_phase5(config, logger, gex_provider, stocks, StrategyMode.SHORT)

        assert result.excluded_count == 0
        assert result.negative_regime_count == 1
        assert len(result.passed) == 1

    def test_positive_passes_through(self, config, logger):
        gex_provider = MagicMock()
        gex_provider.get_gex.return_value = {
            "net_gex": 1000.0,
            "call_wall": 170.0,
            "put_wall": 130.0,
            "zero_gamma": 140.0,  # Price (150) > zero_gamma, net_gex > 0 → POSITIVE
            "source": "test",
        }

        stocks = [_make_stock("AAPL", price=150.0)]
        result = run_phase5(config, logger, gex_provider, stocks, StrategyMode.LONG)

        assert result.excluded_count == 0
        assert len(result.passed) == 1
        assert result.passed[0].gex_regime == GEXRegime.POSITIVE

    def test_no_gex_data_passes_with_default(self, config, logger):
        """No GEX data → pass through with POSITIVE default."""
        gex_provider = MagicMock()
        gex_provider.get_gex.return_value = None

        stocks = [_make_stock("AAPL")]
        result = run_phase5(config, logger, gex_provider, stocks, StrategyMode.LONG)

        assert len(result.passed) == 1
        assert result.passed[0].gex_regime == GEXRegime.POSITIVE
        assert result.passed[0].data_source == "none"

    def test_top_100_limit(self, config, logger):
        """Only top 100 candidates processed."""
        gex_provider = MagicMock()
        gex_provider.get_gex.return_value = None  # Pass through

        stocks = [_make_stock(f"T{i:03d}", combined_score=50 + i * 0.5)
                  for i in range(150)]

        result = run_phase5(config, logger, gex_provider, stocks, StrategyMode.LONG)

        assert len(result.analyzed) == 100

    def test_gex_exclusion_logged(self, config, logger):
        """GEX_EXCLUSION event is logged for excluded tickers."""
        gex_provider = MagicMock()
        gex_provider.get_gex.return_value = {
            "net_gex": -500.0,
            "call_wall": 160.0,
            "put_wall": 130.0,
            "zero_gamma": 200.0,
            "source": "test",
        }

        stocks = [_make_stock("EXCL", price=150.0)]
        result = run_phase5(config, logger, gex_provider, stocks, StrategyMode.LONG)

        # Verify exclusion details
        excluded = result.analyzed[0]
        assert excluded.excluded is True
        assert excluded.exclusion_reason == "negative_gex_long"

    def test_mixed_regimes(self, config, logger):
        """Multiple stocks with different GEX regimes."""
        gex_provider = MagicMock()

        def mock_gex(ticker):
            if ticker == "POS":
                return {"net_gex": 1000, "call_wall": 170, "put_wall": 130,
                        "zero_gamma": 140, "source": "test"}
            elif ticker == "NEG":
                return {"net_gex": -500, "call_wall": 160, "put_wall": 130,
                        "zero_gamma": 200, "source": "test"}
            elif ticker == "HV":
                return {"net_gex": 100, "call_wall": 155, "put_wall": 145,
                        "zero_gamma": 150, "source": "test"}  # Within 2%
            return None

        gex_provider.get_gex.side_effect = mock_gex

        stocks = [
            _make_stock("POS", price=150.0, combined_score=80),
            _make_stock("NEG", price=150.0, combined_score=75),
            _make_stock("HV", price=150.0, combined_score=70),
        ]

        result = run_phase5(config, logger, gex_provider, stocks, StrategyMode.LONG)

        assert len(result.analyzed) == 3
        assert result.excluded_count == 1  # NEG excluded
        assert len(result.passed) == 2     # POS + HV
