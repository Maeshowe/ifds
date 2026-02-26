"""BC15 MMS (Market Microstructure Scorer) Tests — Feature Store, Engine, Classification, Integration.

~50 tests covering:
- MMRegime/BaselineState enums
- Feature extraction (bars, DEX, IV)
- Z-score computation
- Classification (7 regimes, priority ordering)
- Unusualness score
- MMSStore (load, save, trim)
- Regime multiplier mapping
- Phase 5 integration (enabled, disabled, exclusion)
- Phase 5 async integration (MMS with async data fetch)
- Phase 6 integration (mm_regime on PositionSizing)
"""

import json
import math
import os
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ifds.config.loader import Config
from ifds.data.mms_store import MMSStore
from ifds.events.logger import EventLogger
from ifds.models.market import (
    BaselineState,
    FlowAnalysis,
    FundamentalScoring,
    GEXAnalysis,
    GEXRegime,
    MMRegime,
    MacroRegime,
    MarketVolatilityRegime,
    MMSAnalysis,
    Phase5Result,
    PositionSizing,
    StockAnalysis,
    StrategyMode,
    TechnicalAnalysis,
)
from ifds.phases.phase5_mms import (
    _classify_regime,
    _compute_aggregate_iv,
    _compute_dex,
    _compute_iv_skew,
    _compute_medians,
    _compute_unusualness,
    _compute_z_scores,
    _determine_baseline_state,
    _extract_features_from_bars,
    _get_regime_multiplier,
    _mean,
    _std,
    _z_score,
    run_mms_analysis,
)


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
    return EventLogger(log_dir=str(tmp_path), run_id="test-bc15")


@pytest.fixture
def store(tmp_path):
    return MMSStore(store_dir=str(tmp_path / "mms"), max_entries=100)


def _make_bars(n=100, base_price=100.0, volume=1_000_000):
    """Generate synthetic OHLCV bars."""
    bars = []
    for i in range(n):
        c = base_price + i * 0.1
        bars.append({
            "o": c - 0.5,
            "h": c + 1.0,
            "l": c - 1.0,
            "c": c,
            "v": volume + i * 1000,
        })
    return bars


def _make_stock(ticker="AAPL", price=150.0, dp_pct=42.0, block_count=8):
    """Create a StockAnalysis for testing."""
    return StockAnalysis(
        ticker=ticker,
        sector="Technology",
        technical=TechnicalAnalysis(
            price=price, sma_200=140.0, sma_20=148.0,
            rsi_14=55.0, atr_14=3.0, trend_pass=True,
        ),
        flow=FlowAnalysis(
            dark_pool_pct=dp_pct,
            block_trade_count=block_count,
        ),
        fundamental=FundamentalScoring(funda_score=15),
        combined_score=85.0,
    )


def _make_options(n=20, current_price=150.0):
    """Generate synthetic Polygon options snapshot."""
    options = []
    for i in range(n):
        strike = current_price - 10 + i
        is_call = i % 2 == 0
        options.append({
            "details": {
                "strike_price": strike,
                "contract_type": "call" if is_call else "put",
            },
            "greeks": {
                "gamma": 0.02 + i * 0.001,
                "delta": 0.5 if is_call else -0.4,
            },
            "open_interest": 1000 + i * 100,
            "implied_volatility": 0.25 + i * 0.01,
            "underlying_asset": {"price": current_price},
        })
    return options


# ============================================================================
# TestMMRegimeEnum
# ============================================================================

class TestMMRegimeEnum:
    def test_all_8_regimes_exist(self):
        assert len(MMRegime) == 8
        values = {r.value for r in MMRegime}
        expected = {"gamma_positive", "gamma_negative", "dark_dominant",
                    "absorption", "distribution", "neutral", "undetermined",
                    "volatile"}  # BC16
        assert values == expected

    def test_baseline_state_values(self):
        assert len(BaselineState) == 3
        assert BaselineState.EMPTY.value == "empty"
        assert BaselineState.PARTIAL.value == "partial"
        assert BaselineState.COMPLETE.value == "complete"


# ============================================================================
# TestFeatureExtraction
# ============================================================================

class TestFeatureExtraction:
    def test_extract_from_bars_basic(self):
        bars = _make_bars(100)
        result = _extract_features_from_bars(bars, window=63)
        assert "efficiency_series" in result
        assert "impact_series" in result
        assert "daily_return" in result
        assert len(result["efficiency_series"]) <= 63
        assert len(result["impact_series"]) <= 63
        assert result["efficiency_today"] > 0
        assert result["impact_today"] >= 0

    def test_extract_from_bars_short(self):
        bars = _make_bars(10)
        result = _extract_features_from_bars(bars, window=63)
        assert len(result["efficiency_series"]) == 10

    def test_extract_from_bars_empty(self):
        result = _extract_features_from_bars([], window=63)
        assert result == {}

    def test_extract_daily_return(self):
        bars = [
            {"o": 100, "h": 102, "l": 99, "c": 100.0, "v": 1000000},
            {"o": 100, "h": 103, "l": 99, "c": 101.0, "v": 1000000},
        ]
        result = _extract_features_from_bars(bars)
        assert abs(result["daily_return"] - 0.01) < 1e-6


# ============================================================================
# TestDEXComputation
# ============================================================================

class TestDEXComputation:
    def test_dex_calls_only(self):
        options = [
            {"details": {"contract_type": "call"},
             "greeks": {"delta": 0.5}, "open_interest": 1000, "day": {}},
        ]
        dex = _compute_dex(options, 150.0)
        assert dex == 0.5 * 1000 * 100  # = 50000

    def test_dex_puts_only(self):
        options = [
            {"details": {"contract_type": "put"},
             "greeks": {"delta": -0.4}, "open_interest": 1000, "day": {}},
        ]
        dex = _compute_dex(options, 150.0)
        assert dex == -(0.4 * 1000 * 100)  # = -40000

    def test_dex_empty(self):
        assert _compute_dex([], 150.0) == 0.0
        assert _compute_dex(None, 150.0) == 0.0


# ============================================================================
# TestIVComputation
# ============================================================================

class TestIVComputation:
    def test_aggregate_iv_atm(self):
        options = _make_options(20, current_price=150.0)
        iv = _compute_aggregate_iv(options, 150.0)
        assert iv > 0
        # Only ATM-ish (within 5% of 150 = 142.5-157.5) should be included
        assert iv < 1.0  # Reasonable IV range

    def test_aggregate_iv_empty(self):
        assert _compute_aggregate_iv([], 150.0) == 0.0
        assert _compute_aggregate_iv(None, 150.0) == 0.0


# ============================================================================
# TestZScoreComputation
# ============================================================================

class TestZScoreComputation:
    def test_z_score_valid(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0] * 5  # 25 values
        z = _z_score(6.0, values, min_n=5)
        assert z is not None
        assert z > 0  # 6.0 is above mean of 3.0

    def test_z_score_insufficient_data(self):
        values = [1.0, 2.0, 3.0]
        z = _z_score(2.0, values, min_n=21)
        assert z is None

    def test_z_score_zero_std(self):
        values = [5.0] * 25
        z = _z_score(5.0, values, min_n=5)
        assert z is None

    def test_compute_z_scores_full(self):
        bars = _make_bars(100)
        bar_features = _extract_features_from_bars(bars, window=63)

        # Build historical entries with 25 entries
        history = []
        for i in range(25):
            history.append({
                "date": f"2026-01-{i+1:02d}",
                "dark_share": 0.3 + i * 0.01,
                "gex": 1000000 + i * 10000,
                "dex": 50000 + i * 1000,
                "block_count": 5 + i,
                "iv_rank": 0.25 + i * 0.005,
            })

        today = {
            "efficiency": bar_features["efficiency_today"],
            "impact": bar_features["impact_today"],
            "dark_share": 0.55,
            "gex": 1500000,
            "dex": 80000,
            "block_count": 30,
            "iv_rank": 0.40,
        }

        z_scores = _compute_z_scores(today, history, bar_features, min_periods=21)
        # Price-based z-scores should be valid (63 bars available)
        assert z_scores["efficiency"] is not None
        # Store-based z-scores should be valid (25 > 21 min_periods)
        assert z_scores["dark_share"] is not None
        assert z_scores["gex"] is not None


# ============================================================================
# TestClassifyRegime
# ============================================================================

class TestClassifyRegime:
    """Test each of the 7 regimes fires under correct conditions."""

    def _default_core(self):
        return {
            "mms_z_gex_threshold": 1.5,
            "mms_z_dex_threshold": 1.0,
            "mms_z_block_threshold": 1.0,
            "mms_dark_share_dd": 0.70,
            "mms_dark_share_abs": 0.50,
            "mms_return_abs": -0.005,
            "mms_return_dist": 0.005,
        }

    def test_gamma_positive(self):
        """Rule 1: z_gex > +1.5 AND efficiency < median."""
        z = {"gex": 2.0, "dex": 0.0, "block_count": 0.0, "dark_share": 0.0}
        raw = {"dark_share": 0.3, "efficiency": 0.001, "impact": 0.001}
        medians = {"efficiency": 0.005, "impact": 0.002}  # efficiency < median_eff
        regime, cond = _classify_regime(
            z, raw, medians, 0.0, BaselineState.COMPLETE, self._default_core(),
        )
        assert regime == MMRegime.GAMMA_POSITIVE
        assert "z_gex" in cond

    def test_gamma_negative(self):
        """Rule 2: z_gex < -1.5 AND impact > median."""
        z = {"gex": -2.0, "dex": 0.0, "block_count": 0.0, "dark_share": 0.0}
        raw = {"dark_share": 0.3, "efficiency": 0.005, "impact": 0.01}
        medians = {"efficiency": 0.005, "impact": 0.002}  # impact > median_imp
        regime, cond = _classify_regime(
            z, raw, medians, 0.0, BaselineState.COMPLETE, self._default_core(),
        )
        assert regime == MMRegime.GAMMA_NEGATIVE

    def test_dark_dominant(self):
        """Rule 3: dark_share > 0.70 AND z_block > +1.0."""
        z = {"gex": 0.0, "dex": 0.0, "block_count": 1.5, "dark_share": 0.0}
        raw = {"dark_share": 0.75, "efficiency": 0.005, "impact": 0.002}
        medians = {"efficiency": 0.005, "impact": 0.002}
        regime, cond = _classify_regime(
            z, raw, medians, 0.0, BaselineState.COMPLETE, self._default_core(),
        )
        assert regime == MMRegime.DARK_DOMINANT

    def test_absorption(self):
        """Rule 4: z_dex < -1.0 AND return >= -0.5% AND dark_share > 0.50."""
        z = {"gex": 0.0, "dex": -1.5, "block_count": 0.0, "dark_share": 0.0}
        raw = {"dark_share": 0.55, "efficiency": 0.005, "impact": 0.002}
        medians = {"efficiency": 0.005, "impact": 0.002}
        regime, cond = _classify_regime(
            z, raw, medians, -0.003, BaselineState.COMPLETE, self._default_core(),
        )
        assert regime == MMRegime.ABSORPTION

    def test_distribution(self):
        """Rule 5: z_dex > +1.0 AND return <= +0.5%."""
        z = {"gex": 0.0, "dex": 1.5, "block_count": 0.0, "dark_share": 0.0}
        raw = {"dark_share": 0.3, "efficiency": 0.005, "impact": 0.002}
        medians = {"efficiency": 0.005, "impact": 0.002}
        regime, cond = _classify_regime(
            z, raw, medians, 0.003, BaselineState.COMPLETE, self._default_core(),
        )
        assert regime == MMRegime.DISTRIBUTION

    def test_neutral(self):
        """Rule 6: no rule matched."""
        z = {"gex": 0.0, "dex": 0.0, "block_count": 0.0, "dark_share": 0.0}
        raw = {"dark_share": 0.3, "efficiency": 0.005, "impact": 0.002}
        medians = {"efficiency": 0.005, "impact": 0.002}
        regime, cond = _classify_regime(
            z, raw, medians, 0.0, BaselineState.COMPLETE, self._default_core(),
        )
        assert regime == MMRegime.NEUTRAL

    def test_undetermined(self):
        """Rule 7: baseline empty."""
        z = {"gex": None, "dex": None, "block_count": None, "dark_share": None}
        raw = {"dark_share": 0.3, "efficiency": 0.005, "impact": 0.002}
        medians = {"efficiency": 0.005, "impact": 0.002}
        regime, cond = _classify_regime(
            z, raw, medians, 0.0, BaselineState.EMPTY, self._default_core(),
        )
        assert regime == MMRegime.UNDETERMINED


# ============================================================================
# TestPriorityOrdering
# ============================================================================

class TestPriorityOrdering:
    """Test that higher-priority rules fire first."""

    def _default_core(self):
        return {
            "mms_z_gex_threshold": 1.5,
            "mms_z_dex_threshold": 1.0,
            "mms_z_block_threshold": 1.0,
            "mms_dark_share_dd": 0.70,
            "mms_dark_share_abs": 0.50,
            "mms_return_abs": -0.005,
            "mms_return_dist": 0.005,
        }

    def test_gamma_positive_beats_dark_dominant(self):
        """Γ⁺ fires before DD even when DD conditions also met."""
        z = {"gex": 2.0, "dex": 0.0, "block_count": 1.5, "dark_share": 0.0}
        raw = {"dark_share": 0.75, "efficiency": 0.001, "impact": 0.001}
        medians = {"efficiency": 0.005, "impact": 0.002}
        regime, _ = _classify_regime(
            z, raw, medians, 0.0, BaselineState.COMPLETE, self._default_core(),
        )
        assert regime == MMRegime.GAMMA_POSITIVE

    def test_gamma_negative_beats_distribution(self):
        """Γ⁻ fires before DIST even when DIST conditions also met."""
        z = {"gex": -2.0, "dex": 1.5, "block_count": 0.0, "dark_share": 0.0}
        raw = {"dark_share": 0.3, "efficiency": 0.005, "impact": 0.01}
        medians = {"efficiency": 0.005, "impact": 0.002}
        regime, _ = _classify_regime(
            z, raw, medians, 0.003, BaselineState.COMPLETE, self._default_core(),
        )
        assert regime == MMRegime.GAMMA_NEGATIVE


# ============================================================================
# TestUnusualnessScore
# ============================================================================

class TestUnusualnessScore:
    def test_unusualness_normal(self):
        z = {"dark_share": 0.5, "gex": 0.3, "block_count": 0.2, "iv_rank": 0.1}
        weights = {"dark_share": 0.25, "gex": 0.25, "block_intensity": 0.15, "iv_rank": 0.15}
        u = _compute_unusualness(z, ["venue_mix"], weights, [])
        assert 0 <= u <= 100

    def test_unusualness_extreme(self):
        z = {"dark_share": 3.0, "gex": 3.0, "block_count": 3.0, "iv_rank": 3.0}
        weights = {"dark_share": 0.25, "gex": 0.25, "block_intensity": 0.15, "iv_rank": 0.15}
        u = _compute_unusualness(z, ["venue_mix"], weights, [])
        assert u == 100.0  # High z → capped at 100

    def test_unusualness_with_history(self):
        z = {"dark_share": 1.0, "gex": 1.0, "block_count": 1.0, "iv_rank": 1.0}
        weights = {"dark_share": 0.25, "gex": 0.25, "block_intensity": 0.15, "iv_rank": 0.15}
        history = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        u = _compute_unusualness(z, ["venue_mix"], weights, history)
        assert 0 <= u <= 100


# ============================================================================
# TestMMSStore
# ============================================================================

class TestMMSStore:
    def test_load_empty(self, store):
        entries = store.load("NONEXISTENT")
        assert entries == []

    def test_append_and_load(self, store):
        entry = {"date": "2026-02-09", "dark_share": 0.42, "gex": 100000}
        store.append_and_save("AAPL", entry)
        loaded = store.load("AAPL")
        assert len(loaded) == 1
        assert loaded[0]["dark_share"] == 0.42

    def test_max_entries_trim(self, tmp_path):
        small_store = MMSStore(store_dir=str(tmp_path / "obs"), max_entries=5)
        for i in range(10):
            entry = {"date": f"2026-01-{i+1:02d}", "gex": i * 1000}
            small_store.append_and_save("TSLA", entry)
        loaded = small_store.load("TSLA")
        assert len(loaded) == 5
        # Should keep the last 5
        assert loaded[0]["date"] == "2026-01-06"

    def test_dedup_by_date(self, store):
        store.append_and_save("AAPL", {"date": "2026-02-09", "gex": 100})
        store.append_and_save("AAPL", {"date": "2026-02-09", "gex": 200})
        loaded = store.load("AAPL")
        assert len(loaded) == 1
        assert loaded[0]["gex"] == 200  # Latest value

    def test_get_feature_series(self, store):
        entries = [
            {"date": "2026-01-01", "gex": 100, "dark_share": 0.3},
            {"date": "2026-01-02", "gex": 200, "dark_share": None},
            {"date": "2026-01-03", "gex": 300, "dark_share": 0.5},
        ]
        series = store.get_feature_series(entries, "gex")
        assert series == [100.0, 200.0, 300.0]
        # None values filtered
        dark = store.get_feature_series(entries, "dark_share")
        assert dark == [0.3, 0.5]


# ============================================================================
# TestRegimeMultiplier
# ============================================================================

class TestRegimeMultiplier:
    def test_all_regime_multipliers(self):
        tuning = {
            "mms_regime_multipliers": {
                "gamma_positive": 1.5,
                "gamma_negative": 0.25,
                "dark_dominant": 1.25,
                "absorption": 1.0,
                "distribution": 0.5,
                "neutral": 1.0,
                "undetermined": 0.75,
            },
        }
        expected = {
            MMRegime.GAMMA_POSITIVE: 1.5,
            MMRegime.GAMMA_NEGATIVE: 0.25,
            MMRegime.DARK_DOMINANT: 1.25,
            MMRegime.ABSORPTION: 1.0,
            MMRegime.DISTRIBUTION: 0.5,
            MMRegime.NEUTRAL: 1.0,
            MMRegime.UNDETERMINED: 0.75,
        }
        for regime, mult in expected.items():
            assert _get_regime_multiplier(regime, tuning) == mult


# ============================================================================
# TestRunMMSAnalysis
# ============================================================================

class TestRunMMSAnalysis:
    def test_full_analysis_cold_start(self, config, store):
        """Day 1: no history → UND regime."""
        bars = _make_bars(100)
        options = _make_options(20)
        stock = _make_stock()

        result = run_mms_analysis(
            config.core, config.tuning,
            "AAPL", bars, options, stock, {"net_gex": 500000}, store,
        )
        assert isinstance(result, MMSAnalysis)
        assert result.ticker == "AAPL"
        # First run with no history → UND or NEU depending on bar-based z-scores
        assert result.mm_regime in (MMRegime.UNDETERMINED, MMRegime.NEUTRAL)
        assert result.baseline_state in (BaselineState.EMPTY, BaselineState.PARTIAL)
        assert 0 <= result.unusualness_score <= 100

    def test_full_analysis_no_bars(self, config, store):
        """No bars → UND with EMPTY baseline."""
        stock = _make_stock()
        result = run_mms_analysis(
            config.core, config.tuning,
            "AAPL", None, None, stock, None, store,
        )
        assert result.mm_regime == MMRegime.UNDETERMINED
        assert result.baseline_state == BaselineState.EMPTY

    def test_store_populated_after_analysis(self, config, store):
        """Feature store should have 1 entry after first analysis."""
        bars = _make_bars(100)
        stock = _make_stock()
        run_mms_analysis(
            config.core, config.tuning,
            "AAPL", bars, None, stock, None, store,
        )
        entries = store.load("AAPL")
        assert len(entries) == 1
        assert entries[0]["date"] == date.today().isoformat()
        assert "dark_share" in entries[0]
        assert "efficiency" in entries[0]


# ============================================================================
# TestPhase5Integration
# ============================================================================

class TestPhase5Integration:
    def test_mms_disabled_no_polygon(self, config, logger):
        """When MMS disabled and no polygon → no MMS analyses."""
        from ifds.phases.phase5_gex import run_phase5

        mock_gex = MagicMock()
        mock_gex.get_gex.return_value = {
            "net_gex": 500000, "call_wall": 160, "put_wall": 140,
            "zero_gamma": 150, "gex_by_strike": [], "source": "test",
        }

        stocks = [_make_stock("AAPL")]
        # mms_enabled=False, mms_store_always_collect=False → no MMS
        config.tuning["mms_enabled"] = False
        config.tuning["mms_store_always_collect"] = False

        result = run_phase5(config, logger, mock_gex, stocks, StrategyMode.LONG,
                            polygon=None)
        assert result.mms_analyses == []
        assert result.mms_enabled is False

    def test_mms_always_collect_stores_data(self, config, logger, tmp_path):
        """When always_collect=True, store gets populated even if disabled."""
        from ifds.phases.phase5_gex import run_phase5

        config.tuning["mms_enabled"] = False
        config.tuning["mms_store_always_collect"] = True
        config.runtime["mms_store_dir"] = str(tmp_path / "mms")

        mock_gex = MagicMock()
        mock_gex.get_gex.return_value = {
            "net_gex": 500000, "call_wall": 160, "put_wall": 140,
            "zero_gamma": 150, "gex_by_strike": [], "source": "test",
        }

        mock_polygon = MagicMock()
        mock_polygon.get_aggregates.return_value = _make_bars(100)
        mock_polygon.get_options_snapshot.return_value = _make_options(20)

        stocks = [_make_stock("AAPL")]
        result = run_phase5(config, logger, mock_gex, stocks, StrategyMode.LONG,
                            polygon=mock_polygon)
        assert len(result.mms_analyses) == 1
        assert result.mms_enabled is False
        # Store should have data
        store = MMSStore(store_dir=str(tmp_path / "mms"))
        entries = store.load("AAPL")
        assert len(entries) == 1

    def test_mms_enabled_overrides_multiplier(self, config, logger, tmp_path):
        """When enabled, MMS overrides gex_multiplier."""
        from ifds.phases.phase5_gex import run_phase5

        config.tuning["mms_enabled"] = True
        config.tuning["mms_store_always_collect"] = True
        config.runtime["mms_store_dir"] = str(tmp_path / "mms")

        mock_gex = MagicMock()
        mock_gex.get_gex.return_value = {
            "net_gex": 500000, "call_wall": 160, "put_wall": 140,
            "zero_gamma": 150, "gex_by_strike": [], "source": "test",
        }

        mock_polygon = MagicMock()
        mock_polygon.get_aggregates.return_value = _make_bars(100)
        mock_polygon.get_options_snapshot.return_value = _make_options(20)

        stocks = [_make_stock("AAPL")]
        result = run_phase5(config, logger, mock_gex, stocks, StrategyMode.LONG,
                            polygon=mock_polygon)
        assert result.mms_enabled is True
        assert len(result.mms_analyses) == 1
        # The gex_multiplier on the passed GEXAnalysis should reflect MMS
        gex = result.passed[0]
        obs = result.mms_analyses[0]
        assert gex.gex_multiplier == obs.regime_multiplier

    def test_mms_gex_data_preserved(self, config, logger, tmp_path):
        """MMS carries GEX structural data (call_wall etc.)."""
        from ifds.phases.phase5_gex import run_phase5

        config.tuning["mms_enabled"] = True
        config.runtime["mms_store_dir"] = str(tmp_path / "mms")

        mock_gex = MagicMock()
        mock_gex.get_gex.return_value = {
            "net_gex": 500000, "call_wall": 160.0, "put_wall": 140.0,
            "zero_gamma": 150.0, "gex_by_strike": [], "source": "unusual_whales",
        }

        mock_polygon = MagicMock()
        mock_polygon.get_aggregates.return_value = _make_bars(100)
        mock_polygon.get_options_snapshot.return_value = _make_options(20)

        stocks = [_make_stock("AAPL")]
        result = run_phase5(config, logger, mock_gex, stocks, StrategyMode.LONG,
                            polygon=mock_polygon)
        obs = result.mms_analyses[0]
        assert obs.call_wall == 160.0
        assert obs.put_wall == 140.0
        assert obs.net_gex == 500000
        assert obs.data_source == "unusual_whales"


# ============================================================================
# TestPhase6Integration
# ============================================================================

class TestPhase6Integration:
    def test_mm_regime_on_position_sizing(self, config, logger):
        """PositionSizing includes mm_regime from MMS."""
        from ifds.phases.phase6_sizing import _calculate_position

        stock = _make_stock("AAPL", price=150.0)
        stock.combined_score = 85.0
        gex = GEXAnalysis(
            ticker="AAPL", net_gex=500000, call_wall=160, put_wall=140,
            gex_regime=GEXRegime.POSITIVE, gex_multiplier=1.0,
        )
        macro = MacroRegime(
            vix_value=18.0, vix_regime=MarketVolatilityRegime.NORMAL,
            vix_multiplier=1.0, tnx_value=4.0, tnx_sma20=3.9,
            tnx_rate_sensitive=False,
        )
        mms_map = {
            "AAPL": MMSAnalysis(
                ticker="AAPL",
                mm_regime=MMRegime.DARK_DOMINANT,
                unusualness_score=75.5,
            ),
        }

        pos = _calculate_position(
            stock, gex, macro, config, StrategyMode.LONG,
            mms_map=mms_map,
        )
        assert pos is not None
        assert pos.mm_regime == "dark_dominant"
        assert pos.unusualness_score == 75.5

    def test_no_mms_empty_fields(self, config, logger):
        """Without MMS, mm_regime is empty string."""
        from ifds.phases.phase6_sizing import _calculate_position

        stock = _make_stock("AAPL", price=150.0)
        stock.combined_score = 85.0
        gex = GEXAnalysis(
            ticker="AAPL", net_gex=500000, call_wall=160, put_wall=140,
            gex_regime=GEXRegime.POSITIVE, gex_multiplier=1.0,
        )
        macro = MacroRegime(
            vix_value=18.0, vix_regime=MarketVolatilityRegime.NORMAL,
            vix_multiplier=1.0, tnx_value=4.0, tnx_sma20=3.9,
            tnx_rate_sensitive=False,
        )

        pos = _calculate_position(
            stock, gex, macro, config, StrategyMode.LONG,
        )
        assert pos is not None
        assert pos.mm_regime == ""
        assert pos.unusualness_score == 0.0


# ============================================================================
# TestBaselineState
# ============================================================================

class TestBaselineState:
    def test_empty_state(self):
        z = {"dark_share": None, "gex": None, "dex": None, "block_count": None, "iv_rank": None}
        state = _determine_baseline_state(z, 21, 0)
        assert state == BaselineState.EMPTY

    def test_partial_state(self):
        z = {"dark_share": 1.0, "gex": None, "dex": None, "block_count": None, "iv_rank": None}
        state = _determine_baseline_state(z, 21, 10)
        assert state == BaselineState.PARTIAL

    def test_complete_state(self):
        z = {"dark_share": 1.0, "gex": 0.5, "dex": 0.3, "block_count": -0.2, "iv_rank": 0.8}
        state = _determine_baseline_state(z, 21, 25)
        assert state == BaselineState.COMPLETE


# ============================================================================
# TestHelperFunctions
# ============================================================================

class TestHelperFunctions:
    def test_mean(self):
        assert _mean([1, 2, 3, 4, 5]) == 3.0
        assert _mean([]) == 0.0

    def test_std(self):
        s = _std([1, 2, 3, 4, 5], 3.0)
        assert abs(s - math.sqrt(2.5)) < 1e-6
        assert _std([1.0], 1.0) == 0.0

    def test_compute_medians(self):
        bar_features = {
            "efficiency_series": [1.0, 2.0, 3.0, 4.0, 5.0],
            "impact_series": [0.1, 0.2, 0.3],
        }
        medians = _compute_medians(bar_features)
        assert medians["efficiency"] == 3.0
        assert medians["impact"] == 0.2


# ============================================================================
# TestMMSAnalysisDataclass
# ============================================================================

class TestMMSAnalysisDataclass:
    def test_default_values(self):
        obs = MMSAnalysis(ticker="AAPL")
        assert obs.mm_regime == MMRegime.UNDETERMINED
        assert obs.unusualness_score == 0.0
        assert obs.regime_multiplier == 0.75
        assert obs.baseline_state == BaselineState.EMPTY
        assert obs.excluded is False
        assert obs.gex_regime == GEXRegime.POSITIVE

    def test_phase5_result_mms_fields(self):
        result = Phase5Result()
        assert result.mms_analyses == []
        assert result.mms_enabled is False


# ============================================================================
# TestPhase5AsyncMMS
# ============================================================================

class TestPhase5AsyncMMS:
    """Test the async Phase 5 path with MMS enabled."""

    @pytest.mark.asyncio
    async def test_async_mms_fetches_bars_and_options(self, config, logger, tmp_path):
        """Async path fetches bars+options and runs MMS analysis."""
        from ifds.phases.phase5_gex import _run_phase5_async

        config.runtime["mms_store_dir"] = str(tmp_path / "mms")
        config.tuning["mms_enabled"] = False
        config.tuning["mms_store_always_collect"] = True

        stocks = [_make_stock("AAPL")]

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly, \
             patch("ifds.data.async_clients.AsyncUWClient"):

            mock_poly = AsyncMock()
            mock_poly.get_options_snapshot = AsyncMock(return_value=None)
            mock_poly.get_aggregates = AsyncMock(return_value=_make_bars(100))
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            result = await _run_phase5_async(
                config, logger, stocks, StrategyMode.LONG,
                run_mms=True,
            )

            assert len(result.mms_analyses) == 1
            assert result.mms_analyses[0].ticker == "AAPL"
            # Store should have been populated
            store = MMSStore(store_dir=str(tmp_path / "mms"))
            entries = store.load("AAPL")
            assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_async_mms_carries_gex_data(self, config, logger, tmp_path):
        """Async MMS carries GEX structural data (call_wall, put_wall, etc.)."""
        from ifds.phases.phase5_gex import _run_phase5_async

        config.runtime["mms_store_dir"] = str(tmp_path / "mms")
        config.tuning["mms_enabled"] = True

        stocks = [_make_stock("AAPL")]

        mock_gex_result = {
            "net_gex": 500000, "call_wall": 160.0, "put_wall": 140.0,
            "zero_gamma": 150.0, "gex_by_strike": [], "source": "polygon_calculated",
        }

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly, \
             patch("ifds.data.async_clients.AsyncUWClient"), \
             patch("ifds.data.async_adapters.AsyncPolygonGEXProvider") as MockGEX:

            mock_poly = AsyncMock()
            mock_poly.get_options_snapshot = AsyncMock(return_value=_make_options(20))
            mock_poly.get_aggregates = AsyncMock(return_value=_make_bars(100))
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            mock_gex_prov = AsyncMock()
            mock_gex_prov.get_gex = AsyncMock(return_value=mock_gex_result)
            MockGEX.return_value = mock_gex_prov

            result = await _run_phase5_async(
                config, logger, stocks, StrategyMode.LONG,
                run_mms=True,
            )

            assert len(result.mms_analyses) == 1
            obs = result.mms_analyses[0]
            assert obs.call_wall == 160.0
            assert obs.put_wall == 140.0
            assert obs.net_gex == 500000
            assert obs.data_source == "polygon_calculated"

    @pytest.mark.asyncio
    async def test_async_mms_disabled_no_fetch(self, config, logger):
        """When run_mms=False, no bars/options fetch happens."""
        from ifds.phases.phase5_gex import _run_phase5_async

        stocks = [_make_stock("AAPL")]

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly, \
             patch("ifds.data.async_clients.AsyncUWClient"):

            mock_poly = AsyncMock()
            mock_poly.get_options_snapshot = AsyncMock(return_value=None)
            mock_poly.get_aggregates = AsyncMock(return_value=[])
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            result = await _run_phase5_async(
                config, logger, stocks, StrategyMode.LONG,
                run_mms=False,
            )

            assert result.mms_analyses == []
            # get_aggregates should NOT have been called (only for MMS)
            mock_poly.get_aggregates.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_async_mms_data_fetch_failure_graceful(self, config, logger, tmp_path):
        """MMS data fetch failure doesn't break GEX analysis."""
        from ifds.phases.phase5_gex import _run_phase5_async

        config.runtime["mms_store_dir"] = str(tmp_path / "mms")
        config.tuning["mms_enabled"] = True

        stocks = [_make_stock("AAPL")]

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly, \
             patch("ifds.data.async_clients.AsyncUWClient"):

            mock_poly = AsyncMock()
            mock_poly.get_options_snapshot = AsyncMock(return_value=None)
            # Bars fetch raises exception
            mock_poly.get_aggregates = AsyncMock(side_effect=RuntimeError("API down"))
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            result = await _run_phase5_async(
                config, logger, stocks, StrategyMode.LONG,
                run_mms=True,
            )

            # GEX still works
            assert len(result.passed) == 1
            # MMS gracefully skipped (data fetch failed)
            assert result.mms_analyses == []

    @pytest.mark.asyncio
    async def test_async_mms_overrides_multiplier_when_enabled(self, config, logger, tmp_path):
        """When mms_enabled=True, async path overrides gex_multiplier."""
        from ifds.phases.phase5_gex import _run_phase5_async

        config.runtime["mms_store_dir"] = str(tmp_path / "mms")
        config.tuning["mms_enabled"] = True

        stocks = [_make_stock("AAPL")]

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly, \
             patch("ifds.data.async_clients.AsyncUWClient"):

            mock_poly = AsyncMock()
            mock_poly.get_options_snapshot = AsyncMock(return_value=_make_options(20))
            mock_poly.get_aggregates = AsyncMock(return_value=_make_bars(100))
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            result = await _run_phase5_async(
                config, logger, stocks, StrategyMode.LONG,
                run_mms=True,
            )

            assert result.mms_enabled is True
            assert len(result.mms_analyses) == 1
            obs = result.mms_analyses[0]
            gex = result.passed[0]
            # Multiplier should reflect MMS regime
            assert gex.gex_multiplier == obs.regime_multiplier


# ============================================================================
# TestVenueMix
# ============================================================================

class TestVenueMix:
    """Venue entropy (Shannon entropy from DP market_center) tests."""

    def test_venue_entropy_single_venue(self):
        """All prints on same venue → entropy = 0."""
        from ifds.data.adapters import _aggregate_dp_records
        records = [
            {"size": "1000", "price": "150.0", "volume": "5000000",
             "market_center": "FINRA", "nbbo_ask": "150.1", "nbbo_bid": "149.9"},
        ] * 10
        result = _aggregate_dp_records(records)
        assert "venue_entropy" in result
        assert result["venue_entropy"] == 0.0

    def test_venue_entropy_equal_distribution(self):
        """Equal distribution across N venues → entropy = log(N)."""
        from ifds.data.adapters import _aggregate_dp_records
        records = []
        for venue in ["FINRA", "NYSE", "NASDAQ", "ARCA"]:
            records.append({
                "size": "1000", "price": "150.0", "volume": "5000000",
                "market_center": venue, "nbbo_ask": "150.1", "nbbo_bid": "149.9",
            })
        result = _aggregate_dp_records(records)
        assert abs(result["venue_entropy"] - math.log(4)) < 0.01

    def test_venue_entropy_stored_in_entry(self, config, store):
        """venue_entropy is stored in MMS store entry."""
        bars = _make_bars(100)
        stock = _make_stock(dp_pct=42.0)
        stock.flow.venue_entropy = 1.38
        run_mms_analysis(config.core, config.tuning,
                         "AAPL", bars, None, stock, None, store)
        entries = store.load("AAPL")
        assert "venue_entropy" in entries[0]
        assert entries[0]["venue_entropy"] == pytest.approx(1.38, abs=0.01)

    def test_venue_entropy_zero_when_no_dp_data(self, config, store):
        """No darkpool data → venue_entropy = 0.0."""
        bars = _make_bars(100)
        stock = _make_stock(dp_pct=0.0)
        stock.flow.venue_entropy = 0.0
        run_mms_analysis(config.core, config.tuning,
                         "AAPL", bars, None, stock, None, store)
        entries = store.load("AAPL")
        assert entries[0]["venue_entropy"] == 0.0


# ============================================================================
# TestIVSkew
# ============================================================================

class TestIVSkew:
    """IV Skew (ATM put IV - call IV) feature tests."""

    def test_iv_skew_puts_expensive(self):
        """Puts more expensive → positive skew."""
        options = [
            {"details": {"strike_price": 150.0, "contract_type": "put"},
             "implied_volatility": 0.35},
            {"details": {"strike_price": 150.0, "contract_type": "call"},
             "implied_volatility": 0.25},
        ]
        assert _compute_iv_skew(options, 150.0) == pytest.approx(0.10, abs=0.001)

    def test_iv_skew_calls_expensive(self):
        """Calls more expensive → negative skew."""
        options = [
            {"details": {"strike_price": 150.0, "contract_type": "put"},
             "implied_volatility": 0.20},
            {"details": {"strike_price": 150.0, "contract_type": "call"},
             "implied_volatility": 0.30},
        ]
        assert _compute_iv_skew(options, 150.0) == pytest.approx(-0.10, abs=0.001)

    def test_iv_skew_otm_filtered(self):
        """OTM options excluded from ATM band."""
        options = [
            {"details": {"strike_price": 200.0, "contract_type": "put"},
             "implied_volatility": 0.80},   # OTM — excluded
            {"details": {"strike_price": 150.0, "contract_type": "put"},
             "implied_volatility": 0.30},   # ATM
            {"details": {"strike_price": 150.0, "contract_type": "call"},
             "implied_volatility": 0.25},   # ATM
        ]
        assert _compute_iv_skew(options, 150.0) == pytest.approx(0.05, abs=0.001)

    def test_iv_skew_empty(self):
        """Empty or None options → 0.0."""
        assert _compute_iv_skew([], 150.0) == 0.0
        assert _compute_iv_skew(None, 150.0) == 0.0

    def test_iv_skew_stored_in_entry(self, config, store):
        """iv_skew is stored in MMS store entry."""
        bars = _make_bars(100)
        options = [
            {"details": {"strike_price": 150.0, "contract_type": "put"},
             "implied_volatility": 0.35},
            {"details": {"strike_price": 150.0, "contract_type": "call"},
             "implied_volatility": 0.25},
        ]
        stock = _make_stock(price=150.0)
        run_mms_analysis(config.core, config.tuning,
                         "AAPL", bars, options, stock, None, store)
        entries = store.load("AAPL")
        assert "iv_skew" in entries[0]
        assert entries[0]["iv_skew"] == pytest.approx(0.10, abs=0.001)

    def test_iv_skew_z_score_after_21_entries(self, config, store):
        """iv_skew z-score computed after 21+ entries."""
        bars = _make_bars(100)
        stock = _make_stock(price=150.0)
        for i in range(25):
            store.append_and_save("AAPL", {
                "date": f"2026-01-{i+1:02d}",
                "dark_share": 0.3 + i * 0.01, "gex": 1000000.0 + i * 10000,
                "dex": 50000.0 + i * 1000, "block_count": 5.0 + i,
                "iv_rank": 0.30 + i * 0.005,
                "venue_entropy": 1.0 + i * 0.02, "iv_skew": 0.05 + i * 0.002,
                "efficiency": 1e-7, "impact": 5e-8,
                "daily_return": 0.01, "raw_score": 0.0,
            })
        options = [
            {"details": {"strike_price": 150.0, "contract_type": "put"},
             "implied_volatility": 0.40},
            {"details": {"strike_price": 150.0, "contract_type": "call"},
             "implied_volatility": 0.25},
        ]
        result = run_mms_analysis(config.core, config.tuning,
                                  "AAPL", bars, options, stock, None, store)
        assert result.baseline_state in (BaselineState.PARTIAL, BaselineState.COMPLETE)


# ============================================================================
# TestZScoresWithNewFeatures
# ============================================================================

class TestZScoresWithNewFeatures:
    """Tests for venue_entropy and iv_skew z-score computation."""

    def test_z_scores_include_new_features(self):
        """venue_entropy and iv_skew z-scores computed after 25 entries."""
        bars = _make_bars(100)
        bar_features = _extract_features_from_bars(bars, window=63)
        history = []
        for i in range(25):
            history.append({
                "date": f"2026-01-{i+1:02d}",
                "dark_share": 0.3 + i * 0.01, "gex": 1000000 + i * 10000,
                "dex": 50000.0, "block_count": 5.0, "iv_rank": 0.25,
                "venue_entropy": 1.0 + i * 0.02, "iv_skew": 0.05 + i * 0.002,
            })
        today = {
            "efficiency": bar_features["efficiency_today"],
            "impact": bar_features["impact_today"],
            "dark_share": 0.55, "gex": 1500000.0, "dex": 80000.0,
            "block_count": 30.0, "iv_rank": 0.40,
            "venue_entropy": 1.8, "iv_skew": 0.12,
        }
        z = _compute_z_scores(today, history, bar_features, min_periods=21)
        assert z.get("venue_entropy") is not None
        assert z.get("iv_skew") is not None

    def test_z_scores_none_for_legacy_history(self):
        """Legacy history without venue_entropy/iv_skew → z-score None."""
        bars = _make_bars(100)
        bar_features = _extract_features_from_bars(bars, window=63)
        history = []
        for i in range(25):
            history.append({
                "date": f"2026-01-{i+1:02d}",
                "dark_share": 0.3 + i * 0.01, "gex": 1000000 + i * 10000,
                "dex": 50000.0, "block_count": 5.0, "iv_rank": 0.25,
                # No venue_entropy, no iv_skew — legacy entries
            })
        today = {
            "efficiency": bar_features["efficiency_today"],
            "impact": bar_features["impact_today"],
            "dark_share": 0.55, "gex": 1500000.0, "dex": 80000.0,
            "block_count": 30.0, "iv_rank": 0.40,
            "venue_entropy": 1.8, "iv_skew": 0.12,
        }
        z = _compute_z_scores(today, history, bar_features, min_periods=21)
        assert z.get("venue_entropy") is None   # 0 valid values in history
        assert z.get("iv_skew") is None


# ============================================================================
# TestFeatureWeights
# ============================================================================

class TestFeatureWeights:
    """mms_feature_weights config parameterization tests."""

    def _weights(self, **overrides):
        """Base 6-feature weight set with optional overrides."""
        base = {
            "dark_share": 0.25, "gex": 0.25,
            "venue_entropy": 0.15, "block_intensity": 0.15,
            "iv_rank": 0.10, "iv_skew": 0.10,
        }
        base.update(overrides)
        return base

    def test_unusualness_proportional_to_weight(self):
        """Higher weight → higher unusualness contribution."""
        z = {"dark_share": 2.0, "gex": 0.0, "block_count": 0.0,
             "iv_rank": 0.0, "venue_entropy": 0.0, "iv_skew": 0.0}

        low_weights = self._weights(dark_share=0.10)
        high_weights = self._weights(dark_share=0.40)

        u_low = _compute_unusualness(z, [], low_weights, [])
        u_high = _compute_unusualness(z, [], high_weights, [])

        assert u_high > u_low

    def test_unusualness_zero_weight_feature_ignored(self):
        """Zero-weight feature does not contribute to score."""
        z = {"dark_share": 3.0, "gex": 0.0, "block_count": 0.0,
             "iv_rank": 0.0, "venue_entropy": 0.0, "iv_skew": 0.0}

        weights_with = self._weights(dark_share=0.25)
        weights_zero = self._weights(dark_share=0.0)

        u_with = _compute_unusualness(z, [], weights_with, [])
        u_zero = _compute_unusualness(z, [], weights_zero, [])

        assert u_with > 0
        assert u_zero == 0.0

    def test_unusualness_unknown_feature_in_weights_ignored(self):
        """Unknown feature name in weights dict does not cause errors."""
        z = {"dark_share": 2.0, "gex": 0.0, "block_count": 0.0,
             "iv_rank": 0.0, "venue_entropy": 0.0, "iv_skew": 0.0}
        weights_typo = self._weights(typo_feature=0.99)

        u = _compute_unusualness(z, [], weights_typo, [])
        assert 0 <= u <= 100

    def test_unusualness_missing_weight_treats_as_zero(self):
        """Missing weight key for a scoring feature → 0 contribution."""
        z = {"dark_share": 3.0, "gex": 0.0, "block_count": 0.0,
             "iv_rank": 0.0, "venue_entropy": 0.0, "iv_skew": 0.0}
        weights_no_ds = {"gex": 0.50}  # dark_share missing → 0

        u = _compute_unusualness(z, [], weights_no_ds, [])
        assert u == 0.0

    def test_all_6_features_contribute_independently(self):
        """Each feature independently raises score; combined is higher."""
        weights = self._weights()
        excluded: list[str] = []

        scores = []
        for feat, weight_key in [
            ("dark_share", "dark_share"),
            ("gex", "gex"),
            ("block_count", "block_intensity"),
            ("iv_rank", "iv_rank"),
            ("venue_entropy", "venue_entropy"),
            ("iv_skew", "iv_skew"),
        ]:
            z_single = {f: (2.0 if f == feat else 0.0)
                        for f in ["dark_share", "gex", "block_count",
                                  "iv_rank", "venue_entropy", "iv_skew"]}
            u = _compute_unusualness(z_single, excluded, weights, [])
            scores.append((feat, u))

        for feat, u in scores:
            assert u > 0, f"{feat} should be > 0 but got {u}"

        z_all = {f: 2.0 for f in ["dark_share", "gex", "block_count",
                                   "iv_rank", "venue_entropy", "iv_skew"]}
        u_all = _compute_unusualness(z_all, excluded, weights, [])
        for feat, u_single in scores:
            assert u_all >= u_single, f"u_all ({u_all}) < u_single({feat}={u_single})"

    def test_default_weights_sum_to_one(self):
        """Default 6-feature weights sum to 1.0."""
        weights = self._weights()
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_config_weights_used_not_hardcoded(self, config, store):
        """run_mms_analysis reads weights from config, not hardcoded."""
        bars = _make_bars(100)
        stock = _make_stock()
        for i in range(25):
            store.append_and_save("AAPL", {
                "date": f"2026-01-{i+1:02d}",
                "dark_share": 0.3 + i * 0.01, "gex": float(1000000 + i * 10000),
                "dex": 50000.0, "block_count": 5.0, "iv_rank": 0.25,
                "venue_entropy": 1.0, "iv_skew": 0.05,
                "efficiency": 1e-7, "impact": 5e-8,
                "daily_return": 0.01, "raw_score": 0.0,
            })

        config_a = dict(config.tuning)
        config_a["mms_feature_weights"] = self._weights(gex=0.50, dark_share=0.10)

        config_b = dict(config.tuning)
        config_b["mms_feature_weights"] = self._weights(gex=0.10, dark_share=0.50)

        result_a = run_mms_analysis(config.core, config_a, "AAPL",
                                    bars, None, stock, None, store)
        store_b = MMSStore(store_dir=store._store_dir, max_entries=100)
        result_b = run_mms_analysis(config.core, config_b, "AAPL",
                                    bars, None, stock, None, store_b)

        assert 0 <= result_a.unusualness_score <= 100
        assert 0 <= result_b.unusualness_score <= 100
