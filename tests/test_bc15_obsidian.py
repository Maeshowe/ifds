"""BC15 OBSIDIAN MM Tests — Feature Store, Engine, Classification, Integration.

~40 tests covering:
- MMRegime/BaselineState enums
- Feature extraction (bars, DEX, IV)
- Z-score computation
- Classification (7 regimes, priority ordering)
- Unusualness score
- ObsidianStore (load, save, trim)
- Regime multiplier mapping
- Phase 5 integration (enabled, disabled, exclusion)
- Phase 6 integration (mm_regime on PositionSizing)
"""

import json
import math
import os
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from ifds.config.loader import Config
from ifds.data.obsidian_store import ObsidianStore
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
    ObsidianAnalysis,
    Phase5Result,
    PositionSizing,
    StockAnalysis,
    StrategyMode,
    TechnicalAnalysis,
)
from ifds.phases.phase5_obsidian import (
    _classify_regime,
    _compute_aggregate_iv,
    _compute_dex,
    _compute_medians,
    _compute_unusualness,
    _compute_z_scores,
    _determine_baseline_state,
    _extract_features_from_bars,
    _get_regime_multiplier,
    _mean,
    _std,
    _z_score,
    run_obsidian_analysis,
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
    return ObsidianStore(store_dir=str(tmp_path / "obsidian"), max_entries=100)


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
    def test_all_7_regimes_exist(self):
        assert len(MMRegime) == 7
        values = {r.value for r in MMRegime}
        expected = {"gamma_positive", "gamma_negative", "dark_dominant",
                    "absorption", "distribution", "neutral", "undetermined"}
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
            "obsidian_z_gex_threshold": 1.5,
            "obsidian_z_dex_threshold": 1.0,
            "obsidian_z_block_threshold": 1.0,
            "obsidian_dark_share_dd": 0.70,
            "obsidian_dark_share_abs": 0.50,
            "obsidian_return_abs": -0.005,
            "obsidian_return_dist": 0.005,
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
            "obsidian_z_gex_threshold": 1.5,
            "obsidian_z_dex_threshold": 1.0,
            "obsidian_z_block_threshold": 1.0,
            "obsidian_dark_share_dd": 0.70,
            "obsidian_dark_share_abs": 0.50,
            "obsidian_return_abs": -0.005,
            "obsidian_return_dist": 0.005,
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
# TestObsidianStore
# ============================================================================

class TestObsidianStore:
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
        small_store = ObsidianStore(store_dir=str(tmp_path / "obs"), max_entries=5)
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
            "obsidian_regime_multipliers": {
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
# TestRunObsidianAnalysis
# ============================================================================

class TestRunObsidianAnalysis:
    def test_full_analysis_cold_start(self, config, store):
        """Day 1: no history → UND regime."""
        bars = _make_bars(100)
        options = _make_options(20)
        stock = _make_stock()

        result = run_obsidian_analysis(
            config.core, config.tuning,
            "AAPL", bars, options, stock, {"net_gex": 500000}, store,
        )
        assert isinstance(result, ObsidianAnalysis)
        assert result.ticker == "AAPL"
        # First run with no history → UND or NEU depending on bar-based z-scores
        assert result.mm_regime in (MMRegime.UNDETERMINED, MMRegime.NEUTRAL)
        assert result.baseline_state in (BaselineState.EMPTY, BaselineState.PARTIAL)
        assert 0 <= result.unusualness_score <= 100

    def test_full_analysis_no_bars(self, config, store):
        """No bars → UND with EMPTY baseline."""
        stock = _make_stock()
        result = run_obsidian_analysis(
            config.core, config.tuning,
            "AAPL", None, None, stock, None, store,
        )
        assert result.mm_regime == MMRegime.UNDETERMINED
        assert result.baseline_state == BaselineState.EMPTY

    def test_store_populated_after_analysis(self, config, store):
        """Feature store should have 1 entry after first analysis."""
        bars = _make_bars(100)
        stock = _make_stock()
        run_obsidian_analysis(
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
    def test_obsidian_disabled_no_polygon(self, config, logger):
        """When obsidian disabled and no polygon → no obsidian analyses."""
        from ifds.phases.phase5_gex import run_phase5

        mock_gex = MagicMock()
        mock_gex.get_gex.return_value = {
            "net_gex": 500000, "call_wall": 160, "put_wall": 140,
            "zero_gamma": 150, "gex_by_strike": [], "source": "test",
        }

        stocks = [_make_stock("AAPL")]
        # obsidian_enabled=False, obsidian_store_always_collect=False → no OBSIDIAN
        config.tuning["obsidian_enabled"] = False
        config.tuning["obsidian_store_always_collect"] = False

        result = run_phase5(config, logger, mock_gex, stocks, StrategyMode.LONG,
                            polygon=None)
        assert result.obsidian_analyses == []
        assert result.obsidian_enabled is False

    def test_obsidian_always_collect_stores_data(self, config, logger, tmp_path):
        """When always_collect=True, store gets populated even if disabled."""
        from ifds.phases.phase5_gex import run_phase5

        config.tuning["obsidian_enabled"] = False
        config.tuning["obsidian_store_always_collect"] = True
        config.runtime["obsidian_store_dir"] = str(tmp_path / "obsidian")

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
        assert len(result.obsidian_analyses) == 1
        assert result.obsidian_enabled is False
        # Store should have data
        store = ObsidianStore(store_dir=str(tmp_path / "obsidian"))
        entries = store.load("AAPL")
        assert len(entries) == 1

    def test_obsidian_enabled_overrides_multiplier(self, config, logger, tmp_path):
        """When enabled, obsidian overrides gex_multiplier."""
        from ifds.phases.phase5_gex import run_phase5

        config.tuning["obsidian_enabled"] = True
        config.tuning["obsidian_store_always_collect"] = True
        config.runtime["obsidian_store_dir"] = str(tmp_path / "obsidian")

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
        assert result.obsidian_enabled is True
        assert len(result.obsidian_analyses) == 1
        # The gex_multiplier on the passed GEXAnalysis should reflect OBSIDIAN
        gex = result.passed[0]
        obs = result.obsidian_analyses[0]
        assert gex.gex_multiplier == obs.regime_multiplier

    def test_obsidian_gex_data_preserved(self, config, logger, tmp_path):
        """OBSIDIAN carries GEX structural data (call_wall etc.)."""
        from ifds.phases.phase5_gex import run_phase5

        config.tuning["obsidian_enabled"] = True
        config.runtime["obsidian_store_dir"] = str(tmp_path / "obsidian")

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
        obs = result.obsidian_analyses[0]
        assert obs.call_wall == 160.0
        assert obs.put_wall == 140.0
        assert obs.net_gex == 500000
        assert obs.data_source == "unusual_whales"


# ============================================================================
# TestPhase6Integration
# ============================================================================

class TestPhase6Integration:
    def test_mm_regime_on_position_sizing(self, config, logger):
        """PositionSizing includes mm_regime from OBSIDIAN."""
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
        obsidian_map = {
            "AAPL": ObsidianAnalysis(
                ticker="AAPL",
                mm_regime=MMRegime.DARK_DOMINANT,
                unusualness_score=75.5,
            ),
        }

        pos = _calculate_position(
            stock, gex, macro, config, StrategyMode.LONG,
            obsidian_map=obsidian_map,
        )
        assert pos is not None
        assert pos.mm_regime == "dark_dominant"
        assert pos.unusualness_score == 75.5

    def test_no_obsidian_empty_fields(self, config, logger):
        """Without obsidian, mm_regime is empty string."""
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
# TestObsidianAnalysisDataclass
# ============================================================================

class TestObsidianAnalysisDataclass:
    def test_default_values(self):
        obs = ObsidianAnalysis(ticker="AAPL")
        assert obs.mm_regime == MMRegime.UNDETERMINED
        assert obs.unusualness_score == 0.0
        assert obs.regime_multiplier == 0.75
        assert obs.baseline_state == BaselineState.EMPTY
        assert obs.excluded is False
        assert obs.gex_regime == GEXRegime.POSITIVE

    def test_phase5_result_obsidian_fields(self):
        result = Phase5Result()
        assert result.obsidian_analyses == []
        assert result.obsidian_enabled is False
