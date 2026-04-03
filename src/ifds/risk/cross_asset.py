"""Cross-Asset Regime — ETF voting system for market-wide risk assessment.

Three ETF ratios + yield curve vote on the market state:
- HYG/IEF  (credit spread)      — always votes
- RSP/SPY  (market breadth)      — always votes
- IWM/SPY  (small cap strength)  — conditional: only votes WITH HYG

Regime levels:
- NORMAL:   0 votes   → no adjustments
- CAUTIOUS: 1 vote    → VIX threshold -1
- RISK_OFF: 2 votes   → VIX threshold -3, max_pos 6, min_score 75
- CRISIS:   3+ votes AND VIX > 30 → VIX threshold -5, max_pos 4, min_score 80
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CrossAssetRegime(Enum):
    NORMAL = "NORMAL"
    CAUTIOUS = "CAUTIOUS"
    RISK_OFF = "RISK_OFF"
    CRISIS = "CRISIS"


@dataclass(frozen=True)
class CrossAssetResult:
    """Output of cross-asset regime calculation."""

    regime: CrossAssetRegime
    votes: float                        # 0–4 (incl. yield curve half/full votes)
    hyg_ief_below_sma: bool
    rsp_spy_below_sma: bool
    iwm_spy_below_sma: bool
    yield_curve_inverted: bool
    vix_threshold_delta: int            # -5 to 0
    max_positions_override: int | None  # None = no override
    min_score_override: int | None      # None = no override
    details: dict = field(default_factory=dict)


def calculate_cross_asset_regime(
    ratios: dict[str, list[float]],
    vix_value: float,
    yield_spread: float | None,
    config: dict[str, Any] | None = None,
) -> CrossAssetResult:
    """Calculate cross-asset regime from ETF ratios and yield curve.

    Parameters
    ----------
    ratios:
        ``{"hyg_ief": [daily values], "rsp_spy": [...], "iwm_spy": [...]}``
        Each list should have ≥ ``sma_period`` entries (most recent last).
    vix_value:
        Current VIX level.
    yield_spread:
        2s10s yield spread (T10Y2Y). Positive = normal, negative = inverted.
        ``None`` if unavailable.
    config:
        Overridable thresholds (uses sensible defaults if omitted).
    """
    cfg = config or {}
    sma_period = cfg.get("cross_asset_sma_period", 20)
    crisis_vix = cfg.get("cross_asset_vix_crisis_threshold", 30)
    cautious_delta = cfg.get("cross_asset_cautious_vix_delta", -1)
    risk_off_delta = cfg.get("cross_asset_risk_off_vix_delta", -3)
    crisis_delta = cfg.get("cross_asset_crisis_vix_delta", -5)
    risk_off_max_pos = cfg.get("cross_asset_risk_off_max_positions", 6)
    crisis_max_pos = cfg.get("cross_asset_crisis_max_positions", 4)
    risk_off_min_score = cfg.get("cross_asset_risk_off_min_score", 75)
    crisis_min_score = cfg.get("cross_asset_crisis_min_score", 80)
    yield_threshold = cfg.get("yield_curve_inversion_threshold", 0.0)
    yield_severe = cfg.get("yield_curve_severe_threshold", -0.50)
    yield_vote = cfg.get("yield_curve_vote_weight", 0.5)
    yield_severe_vote = cfg.get("yield_curve_severe_vote_weight", 1.0)

    # --- SMA comparison for each ratio ---
    hyg_ief_below = _is_below_sma(ratios.get("hyg_ief", []), sma_period)
    rsp_spy_below = _is_below_sma(ratios.get("rsp_spy", []), sma_period)
    iwm_spy_below = _is_below_sma(ratios.get("iwm_spy", []), sma_period)

    # --- Voting ---
    votes = 0.0

    if hyg_ief_below:
        votes += 1  # Credit — always votes

    if rsp_spy_below:
        votes += 1  # Breadth — always votes

    # IWM/SPY only votes WITH HYG (conditional)
    if iwm_spy_below and hyg_ief_below:
        votes += 1

    # Yield curve (4th voter)
    yield_inverted = False
    if yield_spread is not None:
        if yield_spread < yield_severe:
            votes += yield_severe_vote
            yield_inverted = True
        elif yield_spread < yield_threshold:
            votes += yield_vote
            yield_inverted = True

    # --- Regime mapping ---
    if votes >= 3 and vix_value > crisis_vix:
        regime = CrossAssetRegime.CRISIS
        vix_delta = crisis_delta
        max_pos = crisis_max_pos
        min_score = crisis_min_score
    elif votes >= 2:
        regime = CrossAssetRegime.RISK_OFF
        vix_delta = risk_off_delta
        max_pos = risk_off_max_pos
        min_score = risk_off_min_score
    elif votes >= 1:
        regime = CrossAssetRegime.CAUTIOUS
        vix_delta = cautious_delta
        max_pos = None
        min_score = None
    else:
        regime = CrossAssetRegime.NORMAL
        vix_delta = 0
        max_pos = None
        min_score = None

    return CrossAssetResult(
        regime=regime,
        votes=votes,
        hyg_ief_below_sma=hyg_ief_below,
        rsp_spy_below_sma=rsp_spy_below,
        iwm_spy_below_sma=iwm_spy_below,
        yield_curve_inverted=yield_inverted,
        vix_threshold_delta=vix_delta,
        max_positions_override=max_pos,
        min_score_override=min_score,
        details={
            "hyg_ief_below": hyg_ief_below,
            "rsp_spy_below": rsp_spy_below,
            "iwm_spy_below": iwm_spy_below,
            "iwm_spy_counted": iwm_spy_below and hyg_ief_below,
            "yield_inverted": yield_inverted,
            "yield_spread": yield_spread,
            "vix_value": vix_value,
        },
    )


def _is_below_sma(values: list[float], period: int) -> bool:
    """Check if the most recent value is below its SMA.

    Returns False if insufficient data.
    """
    if len(values) < period:
        return False
    sma = sum(values[-period:]) / period
    return values[-1] < sma
