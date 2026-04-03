"""SIM-L2 Mode 2 Re-Score Engine.

Re-scores Phase 4 snapshots with config overrides to measure the impact
of scoring features (EWMA, MMS, M_target, BMI guard, weights, …).

Reproduces the scoring formula from ``phase4_stocks._calculate_combined_score``
and sizing logic from ``phase6_sizing._calculate_multiplier_total`` with
minimal external dependencies so the SIM stays fully isolated.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ifds.data.phase4_snapshot import snapshot_to_stock_analysis
from ifds.models.market import StockAnalysis

# Base score used by flow/funda components (same as Phase 4/6)
_BASE_SCORE = 50

# ------------------------------------------------------------------
# Default config — mirrors production defaults from config/defaults.py
# ------------------------------------------------------------------

_DEFAULT_CONFIG: dict[str, Any] = {
    # Scoring weights
    "weight_flow": 0.40,
    "weight_fundamental": 0.30,
    "weight_technical": 0.30,
    # Insider
    "insider_strong_buy_threshold": 3,
    "insider_buy_multiplier": 1.25,
    "insider_strong_sell_threshold": -3,
    "insider_sell_multiplier": 0.75,
    # Multiplier thresholds
    "multiplier_flow_threshold": 80,
    "multiplier_flow_value": 1.25,
    "multiplier_funda_threshold": 60,
    "multiplier_funda_value": 0.50,
    "multiplier_utility_threshold": 85,
    "multiplier_utility_max": 1.3,
    # M_target
    "target_overshoot_enabled": True,
    "target_overshoot_threshold": 0.20,
    "target_overshoot_penalty": 0.85,
    "target_severe_threshold": 0.50,
    "target_severe_penalty": 0.60,
    # VIX
    "vix_penalty_start": 20,
    "vix_penalty_rate": 0.02,
    # EWMA
    "ewma_enabled": False,
    "ewma_span": 10,
    # Sizing
    "account_equity": 100_000,
    "risk_per_trade_pct": 0.5,
    "stop_loss_atr_multiple": 1.5,
    "tp1_atr_multiple": 0.75,
    "tp2_atr_multiple": 2.0,
    "max_positions": 8,
    "combined_score_minimum": 70,
}


# ------------------------------------------------------------------
# Re-scored position result
# ------------------------------------------------------------------

@dataclass(frozen=True)
class RescoredPosition:
    """A single re-scored and sized position."""

    ticker: str
    sector: str
    combined_score: float
    original_score: float
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float
    quantity: int
    m_total: float
    m_flow: float = 1.0
    m_insider: float = 1.0
    m_funda: float = 1.0
    m_gex: float = 1.0
    m_vix: float = 1.0
    m_utility: float = 1.0
    m_target: float = 1.0
    direction: str = "BUY"


# ------------------------------------------------------------------
# Scoring
# ------------------------------------------------------------------

def _build_config(overrides: dict[str, Any]) -> dict[str, Any]:
    """Merge overrides into default config (immutable — returns new dict)."""
    return {**_DEFAULT_CONFIG, **overrides}


def _rescore_combined_score(
    stock: StockAnalysis,
    cfg: dict[str, Any],
) -> float:
    """Reproduce Phase 4 combined score with overridable weights.

    Formula:  (w_flow × FlowScore + w_funda × FundaScore + w_tech × TechScore
               + sector_adj) × insider_multiplier
    """
    tech_score = (
        stock.technical.rsi_score
        + stock.technical.sma50_bonus
        + stock.technical.rs_spy_score
    )
    flow_score = min(100, max(0, _BASE_SCORE + stock.flow.rvol_score))
    funda_score = _BASE_SCORE + stock.fundamental.funda_score

    w_flow = cfg["weight_flow"]
    w_funda = cfg["weight_fundamental"]
    w_tech = cfg["weight_technical"]

    combined = (
        w_flow * flow_score
        + w_funda * funda_score
        + w_tech * tech_score
        + stock.sector_adjustment
    )

    combined *= stock.fundamental.insider_multiplier

    return round(combined, 2)


# ------------------------------------------------------------------
# EWMA
# ------------------------------------------------------------------

def _ewma_score(
    current: float,
    prev_ewma: float | None,
    span: int = 10,
) -> float:
    """Exponentially weighted moving average (mirrors Phase 6)."""
    if prev_ewma is None:
        return current
    alpha = 2.0 / (span + 1)
    return round(alpha * current + (1 - alpha) * prev_ewma, 2)


# ------------------------------------------------------------------
# Sizing multipliers
# ------------------------------------------------------------------

def _calculate_m_target(
    price: float,
    analyst_target: float | None,
    cfg: dict[str, Any],
) -> float:
    """Analyst price target penalty (M_target ∈ [0.60, 1.0])."""
    if not cfg.get("target_overshoot_enabled", True):
        return 1.0
    if analyst_target is None or analyst_target <= 0:
        return 1.0

    overshoot = (price - analyst_target) / analyst_target
    if overshoot > cfg["target_severe_threshold"]:
        return cfg["target_severe_penalty"]
    if overshoot > cfg["target_overshoot_threshold"]:
        return cfg["target_overshoot_penalty"]
    return 1.0


def _calculate_m_vix(vix: float | None, cfg: dict[str, Any]) -> float:
    """VIX-based sizing penalty."""
    if vix is None:
        return 1.0
    start = cfg.get("vix_penalty_start", 20)
    rate = cfg.get("vix_penalty_rate", 0.02)
    if vix <= start:
        return 1.0
    return max(0.5, 1.0 - (vix - start) * rate)


def _calculate_sizing(
    stock: StockAnalysis,
    combined_score: float,
    cfg: dict[str, Any],
    gex_multiplier: float = 1.0,
    vix: float | None = None,
) -> RescoredPosition | None:
    """Calculate position sizing from re-scored stock.

    Returns None if ATR/entry is invalid or quantity would be zero.
    """
    atr = stock.technical.atr_14
    entry = stock.technical.price

    if not (atr > 0) or not (entry > 0):
        return None

    # --- Multipliers ---
    flow_score = _BASE_SCORE + stock.flow.rvol_score
    m_flow = (
        cfg["multiplier_flow_value"]
        if flow_score > cfg["multiplier_flow_threshold"]
        else 1.0
    )

    m_insider = stock.fundamental.insider_multiplier

    funda_score = _BASE_SCORE + stock.fundamental.funda_score
    m_funda = (
        cfg["multiplier_funda_value"]
        if funda_score < cfg["multiplier_funda_threshold"]
        else 1.0
    )

    m_gex = gex_multiplier

    m_vix = _calculate_m_vix(vix, cfg)

    utility_threshold = cfg["multiplier_utility_threshold"]
    utility_max = cfg["multiplier_utility_max"]
    if combined_score > utility_threshold:
        m_utility = min(utility_max, 1.0 + (combined_score - utility_threshold) / 100)
    else:
        m_utility = 1.0

    m_target = _calculate_m_target(entry, stock.analyst_target, cfg)

    m_total = m_flow * m_insider * m_funda * m_gex * m_vix * m_utility * m_target
    m_total = max(0.25, min(2.0, m_total))

    # --- Quantity ---
    account_equity = cfg["account_equity"]
    risk_pct = cfg["risk_per_trade_pct"]
    sl_mult = cfg["stop_loss_atr_multiple"]

    base_risk = account_equity * risk_pct / 100
    adjusted_risk = base_risk * m_total
    stop_distance = sl_mult * atr
    quantity = math.floor(adjusted_risk / stop_distance)

    if quantity <= 0:
        return None

    # --- Bracket targets ---
    stop_loss = round(entry - stop_distance, 2)
    tp1 = round(entry + cfg["tp1_atr_multiple"] * atr, 2)
    tp2 = round(entry + cfg["tp2_atr_multiple"] * atr, 2)
    if tp2 <= tp1:
        tp2 = round(tp1 + atr, 2)

    return RescoredPosition(
        ticker=stock.ticker,
        sector=stock.sector,
        combined_score=combined_score,
        original_score=stock.combined_score,
        entry_price=entry,
        stop_loss=stop_loss,
        tp1=tp1,
        tp2=tp2,
        quantity=quantity,
        m_total=round(m_total, 4),
        m_flow=m_flow,
        m_insider=m_insider,
        m_funda=m_funda,
        m_gex=m_gex,
        m_vix=m_vix,
        m_utility=round(m_utility, 4),
        m_target=m_target,
    )


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------

def rescore_snapshot(
    snapshot_records: list[dict],
    config_overrides: dict[str, Any] | None = None,
    gex_multiplier: float = 1.0,
    vix: float | None = None,
    ewma_state: dict[str, float] | None = None,
) -> list[RescoredPosition]:
    """Re-score a single day's Phase 4 snapshot with config overrides.

    Parameters
    ----------
    snapshot_records:
        Output of ``load_phase4_snapshot()`` — list of flat dicts.
    config_overrides:
        Keys to override in the default config (weights, thresholds, flags).
    gex_multiplier:
        Mock GEX multiplier applied to all tickers (default 1.0 = neutral).
    vix:
        VIX level for M_vix calculation (None = no penalty).
    ewma_state:
        Previous day's EWMA scores ``{ticker: ewma_value}``.
        Updated in-place with new EWMA values if ``ewma_enabled``.

    Returns
    -------
    list[RescoredPosition]
        Sized positions sorted by combined_score descending, capped at
        ``max_positions``.
    """
    cfg = _build_config(config_overrides or {})
    min_score = cfg["combined_score_minimum"]
    max_positions = cfg.get("max_positions", 8)
    ewma_enabled = cfg.get("ewma_enabled", False)
    ewma_span = cfg.get("ewma_span", 10)
    ewma = ewma_state if ewma_state is not None else {}

    stocks = [snapshot_to_stock_analysis(r) for r in snapshot_records]

    # Re-score
    scored: list[tuple[StockAnalysis, float]] = []
    for stock in stocks:
        score = _rescore_combined_score(stock, cfg)

        if ewma_enabled:
            prev = ewma.get(stock.ticker)
            score = _ewma_score(score, prev, span=ewma_span)
            ewma[stock.ticker] = score

        if score >= min_score:
            scored.append((stock, score))

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # Size and cap
    positions: list[RescoredPosition] = []
    for stock, score in scored:
        if len(positions) >= max_positions:
            break
        pos = _calculate_sizing(stock, score, cfg, gex_multiplier, vix)
        if pos is not None:
            positions.append(pos)

    return positions
