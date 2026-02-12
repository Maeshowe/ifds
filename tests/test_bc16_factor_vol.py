"""Tests for BC16: Factor Volatility framework.

Tests the new VOLATILE regime, factor volatility computation,
regime confidence, and σ_20-weighted unusualness scoring.
"""

import math

import pytest

from ifds.models.market import BaselineState, MMRegime
from ifds.phases.phase5_obsidian import (
    _classify_regime,
    _compute_factor_volatility,
    _compute_median_rolling_sigmas,
    _compute_regime_confidence,
    _compute_unusualness,
)


def _make_historical_entries(n=40, gex_base=100.0, gex_noise=10.0,
                              dex_base=5000.0, dex_noise=500.0):
    """Create mock historical entries with controlled noise levels.

    Each entry has gex, dex, dark_share, block_count, iv_rank values
    with Gaussian-like variation around base values.
    """
    import random
    rng = random.Random(42)  # Deterministic
    entries = []
    for i in range(n):
        entries.append({
            "date": f"2026-01-{i + 1:02d}" if i < 28 else f"2026-02-{i - 27:02d}",
            "gex": gex_base + rng.gauss(0, gex_noise),
            "dex": dex_base + rng.gauss(0, dex_noise),
            "dark_share": 0.30 + rng.gauss(0, 0.05),
            "block_count": max(0, 5 + rng.gauss(0, 2)),
            "iv_rank": 0.25 + rng.gauss(0, 0.05),
            "raw_score": rng.uniform(0.1, 1.5),
        })
    return entries


# ============================================================================
# TestComputeFactorVolatility
# ============================================================================

class TestComputeFactorVolatility:
    """Test _compute_factor_volatility — rolling σ per feature."""

    def test_basic_computation(self):
        """Computes σ for features with enough data."""
        entries = _make_historical_entries(30)
        result = _compute_factor_volatility(entries, window=20)

        assert "gex" in result
        assert "dex" in result
        assert result["gex"] is not None
        assert result["gex"] > 0  # Should have non-zero std

    def test_insufficient_data(self):
        """Returns None when fewer entries than window."""
        entries = _make_historical_entries(10)
        result = _compute_factor_volatility(entries, window=20)

        assert result["gex"] is None
        assert result["dex"] is None

    def test_constant_values_zero_var(self):
        """Constant feature values produce σ=0."""
        entries = [{"gex": 100.0, "dex": 5000.0, "dark_share": 0.3,
                     "block_count": 5.0, "iv_rank": 0.25}
                   for _ in range(25)]
        result = _compute_factor_volatility(entries, window=20)

        assert result["gex"] == 0.0
        assert result["dex"] == 0.0

    def test_high_noise_produces_high_sigma(self):
        """Higher noise in data → higher σ."""
        low_noise = _make_historical_entries(30, gex_noise=1.0)
        high_noise = _make_historical_entries(30, gex_noise=100.0)

        low_vol = _compute_factor_volatility(low_noise, window=20)
        high_vol = _compute_factor_volatility(high_noise, window=20)

        assert high_vol["gex"] > low_vol["gex"]


# ============================================================================
# TestComputeMedianRollingSigmas
# ============================================================================

class TestComputeMedianRollingSigmas:
    """Test _compute_median_rolling_sigmas — median of rolling σ windows."""

    def test_basic_median(self):
        """Computes median rolling σ with enough history."""
        entries = _make_historical_entries(50)
        result = _compute_median_rolling_sigmas(entries, window=20)

        assert "gex" in result
        assert result["gex"] > 0

    def test_insufficient_history(self):
        """Returns 0 when history < 2× window."""
        entries = _make_historical_entries(15)
        result = _compute_median_rolling_sigmas(entries, window=20)

        assert result["gex"] == 0.0

    def test_all_features_present(self):
        """All 5 microstructure features computed."""
        entries = _make_historical_entries(50)
        result = _compute_median_rolling_sigmas(entries, window=20)

        for feat in ["gex", "dex", "dark_share", "block_count", "iv_rank"]:
            assert feat in result


# ============================================================================
# TestComputeRegimeConfidence
# ============================================================================

class TestComputeRegimeConfidence:
    """Test _compute_regime_confidence — stability measure."""

    def test_stable_regime(self):
        """Low current σ vs median → high confidence."""
        factor_vol = {"gex": 5.0}
        median_sigmas = {"gex": 50.0}  # Current σ is 10% of median

        confidence = _compute_regime_confidence(factor_vol, median_sigmas, floor=0.6)

        assert confidence >= 0.9  # Very stable

    def test_unstable_regime(self):
        """High current σ vs median → low confidence (floored)."""
        factor_vol = {"gex": 100.0}
        median_sigmas = {"gex": 50.0}  # Current σ is 2× median

        confidence = _compute_regime_confidence(factor_vol, median_sigmas, floor=0.6)

        assert confidence == 0.6  # Floored

    def test_no_data_returns_stable(self):
        """Missing data → assume stable (1.0)."""
        confidence = _compute_regime_confidence({"gex": None}, {"gex": 0.0}, floor=0.6)
        assert confidence == 1.0

    def test_floor_enforced(self):
        """Confidence never drops below floor."""
        factor_vol = {"gex": 200.0}
        median_sigmas = {"gex": 10.0}  # 20× median → very unstable

        confidence = _compute_regime_confidence(factor_vol, median_sigmas, floor=0.6)

        assert confidence == 0.6


# ============================================================================
# TestVolatileRegime
# ============================================================================

class TestVolatileRegime:
    """Test VOLATILE regime classification (BC16)."""

    def test_volatile_when_both_sigmas_high(self):
        """VOLATILE triggers when σ_gex > 2× median AND σ_dex > 2× median."""
        z_scores = {"gex": 0.5, "dex": 0.3, "efficiency": 0.0, "impact": 0.0,
                     "dark_share": 0.0, "block_count": 0.0, "iv_rank": 0.0}
        raw = {"dark_share": 0.2, "efficiency": 0.001, "impact": 0.001}
        medians = {"efficiency": 0.001, "impact": 0.001}
        factor_vol = {"gex": 30.0, "dex": 1500.0}
        median_sigs = {"gex": 10.0, "dex": 500.0}  # Both > 2× median

        regime, cond = _classify_regime(
            z_scores, raw, medians, 0.001, BaselineState.COMPLETE, {},
            factor_vol=factor_vol, median_sigmas=median_sigs,
        )

        assert regime == MMRegime.VOLATILE
        assert "sigma_gex" in cond

    def test_not_volatile_when_only_gex_high(self):
        """VOLATILE needs BOTH σ_gex and σ_dex above 2× median."""
        z_scores = {"gex": 0.5, "dex": 0.3, "efficiency": 0.0, "impact": 0.0,
                     "dark_share": 0.0, "block_count": 0.0, "iv_rank": 0.0}
        raw = {"dark_share": 0.2, "efficiency": 0.001, "impact": 0.001}
        medians = {"efficiency": 0.001, "impact": 0.001}
        factor_vol = {"gex": 30.0, "dex": 500.0}  # Only gex > 2×
        median_sigs = {"gex": 10.0, "dex": 500.0}

        regime, _ = _classify_regime(
            z_scores, raw, medians, 0.001, BaselineState.COMPLETE, {},
            factor_vol=factor_vol, median_sigmas=median_sigs,
        )

        assert regime != MMRegime.VOLATILE

    def test_volatile_has_priority_over_other_rules(self):
        """VOLATILE fires before Γ⁺ when both conditions met."""
        z_scores = {"gex": 2.0, "dex": 0.5, "efficiency": 0.0, "impact": 0.0,
                     "dark_share": 0.0, "block_count": 0.0, "iv_rank": 0.0}
        # Γ⁺ conditions: z_gex > 1.5 AND efficiency < median
        raw = {"dark_share": 0.2, "efficiency": 0.0005, "impact": 0.001}
        medians = {"efficiency": 0.001, "impact": 0.001}  # eff < median ✓
        factor_vol = {"gex": 30.0, "dex": 1500.0}
        median_sigs = {"gex": 10.0, "dex": 500.0}

        regime, _ = _classify_regime(
            z_scores, raw, medians, 0.001, BaselineState.COMPLETE,
            {"obsidian_z_gex_threshold": 1.5},
            factor_vol=factor_vol, median_sigmas=median_sigs,
        )

        assert regime == MMRegime.VOLATILE  # VOLATILE beats Γ⁺

    def test_volatile_multiplier_value(self):
        """VOLATILE regime has multiplier 0.60."""
        from ifds.phases.phase5_obsidian import _get_regime_multiplier
        tuning = {"obsidian_regime_multipliers": {"volatile": 0.60}}
        assert _get_regime_multiplier(MMRegime.VOLATILE, tuning) == 0.60

    def test_no_volatile_without_factor_vol(self):
        """Without factor_vol data, VOLATILE cannot trigger."""
        z_scores = {"gex": 0.5, "dex": 0.3, "efficiency": 0.0, "impact": 0.0,
                     "dark_share": 0.0, "block_count": 0.0, "iv_rank": 0.0}
        raw = {"dark_share": 0.2, "efficiency": 0.001, "impact": 0.001}
        medians = {"efficiency": 0.001, "impact": 0.001}

        regime, _ = _classify_regime(
            z_scores, raw, medians, 0.001, BaselineState.COMPLETE, {},
        )

        assert regime != MMRegime.VOLATILE  # Falls through to NEU


# ============================================================================
# TestUnusualnessWithFactorVol
# ============================================================================

class TestUnusualnessWithFactorVol:
    """Test σ_20-weighted unusualness scoring (BC16)."""

    def test_vol_weighting_increases_score(self):
        """Features with high σ_20 get amplified in unusualness."""
        z_scores = {"dark_share": 1.5, "gex": 2.0, "block_count": 1.0, "iv_rank": 0.5}
        weights = {"dark_share": 0.25, "gex": 0.25, "block_intensity": 0.15, "iv_rank": 0.15}

        # Without factor vol
        u_base = _compute_unusualness(z_scores, [], weights, [])

        # With factor vol (gex is volatile → amplified)
        factor_vol = {"dark_share": 0.05, "gex": 50.0, "block_count": 2.0, "iv_rank": 0.05}
        median_sigs = {"dark_share": 0.05, "gex": 10.0, "block_count": 2.0, "iv_rank": 0.05}

        u_vol = _compute_unusualness(z_scores, [], weights, [],
                                      factor_vol=factor_vol, median_sigmas=median_sigs)

        assert u_vol > u_base  # Vol-weighted should be higher

    def test_no_factor_vol_unchanged(self):
        """Without factor_vol, scoring is unchanged from BC15."""
        z_scores = {"dark_share": 1.0, "gex": 1.0, "block_count": 1.0, "iv_rank": 1.0}
        weights = {"dark_share": 0.25, "gex": 0.25, "block_intensity": 0.15, "iv_rank": 0.15}

        u1 = _compute_unusualness(z_scores, [], weights, [])
        u2 = _compute_unusualness(z_scores, [], weights, [],
                                   factor_vol=None, median_sigmas=None)

        assert u1 == u2


# ============================================================================
# TestObsidianAnalysisNewFields
# ============================================================================

class TestObsidianAnalysisNewFields:
    """Test new BC16 fields on ObsidianAnalysis."""

    def test_default_values(self):
        from ifds.models.market import ObsidianAnalysis
        obs = ObsidianAnalysis(ticker="TEST")
        assert obs.regime_confidence == 1.0
        assert obs.factor_volatility == {}

    def test_volatile_regime_enum(self):
        """VOLATILE is a valid MMRegime."""
        assert MMRegime.VOLATILE.value == "volatile"
        from ifds.models.market import ObsidianAnalysis
        obs = ObsidianAnalysis(ticker="TEST", mm_regime=MMRegime.VOLATILE)
        assert obs.mm_regime == MMRegime.VOLATILE
