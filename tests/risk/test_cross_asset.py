"""Tests for Cross-Asset Regime (BC21 Phase_21B).

Covers:
- Voting logic (HYG/IEF, RSP/SPY, IWM/SPY conditional)
- Yield curve voter (half/full vote)
- Regime mapping (NORMAL, CAUTIOUS, RISK_OFF, CRISIS)
- VIX threshold delta
- Max positions + min score overrides
- Edge cases (insufficient data, disabled)
"""

import pytest

from ifds.risk.cross_asset import (
    CrossAssetRegime,
    CrossAssetResult,
    _is_below_sma,
    calculate_cross_asset_regime,
)


def _make_ratios(
    hyg_ief_trend: str = "above",
    rsp_spy_trend: str = "above",
    iwm_spy_trend: str = "above",
    n: int = 25,
) -> dict[str, list[float]]:
    """Generate ratio time series.

    trend: "above" = latest above SMA20, "below" = latest below SMA20.
    """
    def _series(trend: str) -> list[float]:
        # SMA20 of flat series at 1.0 = 1.0
        # "below": last value < 1.0 → dip to 0.95
        # "above": last value = 1.02 → above SMA
        base = [1.0] * n
        if trend == "below":
            base[-1] = 0.90  # Clearly below SMA20 of ~1.0
        else:
            base[-1] = 1.02
        return base

    return {
        "hyg_ief": _series(hyg_ief_trend),
        "rsp_spy": _series(rsp_spy_trend),
        "iwm_spy": _series(iwm_spy_trend),
    }


class TestIsbelowSma:

    def test_above_sma(self):
        values = [1.0] * 20 + [1.05]
        assert _is_below_sma(values, 20) is False

    def test_below_sma(self):
        values = [1.0] * 20 + [0.95]
        assert _is_below_sma(values, 20) is True

    def test_insufficient_data(self):
        values = [1.0] * 10  # Only 10 values, need 20
        assert _is_below_sma(values, 20) is False

    def test_empty(self):
        assert _is_below_sma([], 20) is False


class TestVoting:

    def test_0_votes_normal(self):
        """All ratios above SMA → NORMAL."""
        ratios = _make_ratios("above", "above", "above")
        result = calculate_cross_asset_regime(ratios, vix_value=20.0, yield_spread=0.5)
        assert result.regime == CrossAssetRegime.NORMAL
        assert result.votes == 0
        assert result.vix_threshold_delta == 0

    def test_1_vote_hyg_cautious(self):
        """Only HYG/IEF below → 1 vote → CAUTIOUS."""
        ratios = _make_ratios("below", "above", "above")
        result = calculate_cross_asset_regime(ratios, vix_value=20.0, yield_spread=0.5)
        assert result.regime == CrossAssetRegime.CAUTIOUS
        assert result.votes == 1
        assert result.vix_threshold_delta == -1

    def test_1_vote_rsp_cautious(self):
        """Only RSP/SPY below → 1 vote → CAUTIOUS."""
        ratios = _make_ratios("above", "below", "above")
        result = calculate_cross_asset_regime(ratios, vix_value=20.0, yield_spread=0.5)
        assert result.regime == CrossAssetRegime.CAUTIOUS
        assert result.votes == 1

    def test_2_votes_risk_off(self):
        """HYG + RSP below → 2 votes → RISK_OFF."""
        ratios = _make_ratios("below", "below", "above")
        result = calculate_cross_asset_regime(ratios, vix_value=20.0, yield_spread=0.5)
        assert result.regime == CrossAssetRegime.RISK_OFF
        assert result.votes == 2
        assert result.vix_threshold_delta == -3
        assert result.max_positions_override == 6
        assert result.min_score_override == 75

    def test_3_votes_low_vix_risk_off(self):
        """All 3 below but VIX ≤ 30 → RISK_OFF (not CRISIS)."""
        ratios = _make_ratios("below", "below", "below")
        result = calculate_cross_asset_regime(ratios, vix_value=25.0, yield_spread=0.5)
        assert result.regime == CrossAssetRegime.RISK_OFF
        assert result.votes == 3

    def test_3_votes_high_vix_crisis(self):
        """All 3 below + VIX > 30 → CRISIS."""
        ratios = _make_ratios("below", "below", "below")
        result = calculate_cross_asset_regime(ratios, vix_value=35.0, yield_spread=0.5)
        assert result.regime == CrossAssetRegime.CRISIS
        assert result.votes == 3
        assert result.vix_threshold_delta == -5
        assert result.max_positions_override == 4
        assert result.min_score_override == 80


class TestIWMConditional:

    def test_iwm_alone_no_vote(self):
        """IWM below without HYG → no extra vote."""
        ratios = _make_ratios("above", "above", "below")
        result = calculate_cross_asset_regime(ratios, vix_value=20.0, yield_spread=0.5)
        assert result.regime == CrossAssetRegime.NORMAL
        assert result.votes == 0
        assert not result.details["iwm_spy_counted"]

    def test_iwm_with_hyg_counts(self):
        """IWM below WITH HYG below → 3rd vote counted."""
        ratios = _make_ratios("below", "above", "below")
        result = calculate_cross_asset_regime(ratios, vix_value=20.0, yield_spread=0.5)
        assert result.votes == 2  # HYG + IWM (conditional)
        assert result.details["iwm_spy_counted"]
        assert result.regime == CrossAssetRegime.RISK_OFF


class TestYieldCurveVoter:

    def test_normal_curve_no_vote(self):
        """Positive spread → no extra vote."""
        ratios = _make_ratios("below", "above", "above")
        result = calculate_cross_asset_regime(ratios, vix_value=20.0, yield_spread=0.3)
        assert result.votes == 1
        assert not result.yield_curve_inverted

    def test_inverted_half_vote(self):
        """Inverted (< 0) → +0.5 vote."""
        ratios = _make_ratios("below", "above", "above")
        result = calculate_cross_asset_regime(ratios, vix_value=20.0, yield_spread=-0.1)
        assert result.votes == 1.5
        assert result.yield_curve_inverted

    def test_deep_inversion_full_vote(self):
        """Deep inversion (< -0.5) → +1.0 vote."""
        ratios = _make_ratios("below", "above", "above")
        result = calculate_cross_asset_regime(ratios, vix_value=20.0, yield_spread=-0.6)
        assert result.votes == 2.0
        assert result.yield_curve_inverted
        assert result.regime == CrossAssetRegime.RISK_OFF

    def test_yield_none_no_vote(self):
        """yield_spread=None → no extra vote."""
        ratios = _make_ratios("below", "above", "above")
        result = calculate_cross_asset_regime(ratios, vix_value=20.0, yield_spread=None)
        assert result.votes == 1

    def test_yield_pushes_to_crisis(self):
        """2 ETF votes + deep inversion + high VIX → CRISIS."""
        ratios = _make_ratios("below", "below", "above")
        result = calculate_cross_asset_regime(ratios, vix_value=35.0, yield_spread=-0.6)
        assert result.votes == 3.0
        assert result.regime == CrossAssetRegime.CRISIS


class TestConfigOverrides:

    def test_custom_crisis_vix_threshold(self):
        """Custom crisis VIX threshold (40 instead of 30)."""
        ratios = _make_ratios("below", "below", "below")
        cfg = {"cross_asset_vix_crisis_threshold": 40}
        result = calculate_cross_asset_regime(ratios, vix_value=35.0, yield_spread=0.5, config=cfg)
        # VIX 35 < 40 → RISK_OFF, not CRISIS
        assert result.regime == CrossAssetRegime.RISK_OFF

    def test_custom_max_positions(self):
        cfg = {"cross_asset_crisis_max_positions": 3}
        ratios = _make_ratios("below", "below", "below")
        result = calculate_cross_asset_regime(ratios, vix_value=35.0, yield_spread=0.5, config=cfg)
        assert result.max_positions_override == 3


class TestEdgeCases:

    def test_empty_ratios(self):
        """Empty ratios → NORMAL."""
        result = calculate_cross_asset_regime({}, vix_value=20.0, yield_spread=0.5)
        assert result.regime == CrossAssetRegime.NORMAL

    def test_short_ratio_series(self):
        """Ratio series shorter than SMA period → treated as above (no vote)."""
        ratios = {"hyg_ief": [0.9] * 5, "rsp_spy": [0.9] * 5, "iwm_spy": [0.9] * 5}
        result = calculate_cross_asset_regime(ratios, vix_value=35.0, yield_spread=0.5)
        assert result.regime == CrossAssetRegime.NORMAL
