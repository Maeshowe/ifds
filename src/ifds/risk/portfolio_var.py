"""Parametric Portfolio Value at Risk.

Simplified VaR calculation assuming independent positions (worst case).
Suitable for a pipeline pre-flight check — not a full risk model.

VaR_portfolio = sqrt(sum(VaR_i^2))
VaR_i = position_value × daily_vol × z_score
daily_vol ≈ ATR_14 / price (crude volatility proxy)
"""

from __future__ import annotations

import math
from typing import Any

# z-score for common confidence levels
_Z_SCORES = {
    0.90: 1.282,
    0.95: 1.645,
    0.99: 2.326,
}


def calculate_portfolio_var(
    positions: list[Any],
    confidence: float = 0.95,
    horizon_days: int = 1,
) -> tuple[float, float]:
    """Calculate parametric portfolio VaR.

    Parameters
    ----------
    positions:
        PositionSizing objects with ``entry_price``, ``quantity``,
        and ``technical.atr_14`` (via the ``atr_14`` access pattern below).
    confidence:
        Confidence level (0.90, 0.95, 0.99).
    horizon_days:
        Holding horizon in trading days (default 1).

    Returns
    -------
    (var_usd, var_pct)
        Absolute VaR in USD and as % of total position value.
    """
    z = _Z_SCORES.get(confidence, 1.645)

    per_position_vars: list[float] = []
    total_value = 0.0

    for pos in positions:
        price = pos.entry_price
        qty = pos.quantity

        # ATR access: PositionSizing doesn't carry ATR directly,
        # so we infer it from stop_loss distance (SL = entry - 1.5×ATR)
        if price > 0 and pos.stop_loss > 0:
            atr = abs(price - pos.stop_loss) / 1.5
        else:
            continue

        if not (atr > 0) or not (price > 0) or qty <= 0:
            continue

        position_value = price * qty
        daily_vol = atr / price  # ATR-based daily volatility proxy
        position_var = position_value * daily_vol * z * math.sqrt(horizon_days)
        per_position_vars.append(position_var)
        total_value += position_value

    if not per_position_vars:
        return 0.0, 0.0

    # Independent positions: VaR_portfolio = sqrt(sum(VaR_i^2))
    portfolio_var = math.sqrt(sum(v ** 2 for v in per_position_vars))
    var_pct = (portfolio_var / total_value * 100) if total_value > 0 else 0.0

    return round(portfolio_var, 2), round(var_pct, 4)


def trim_positions_by_var(
    positions: list[Any],
    account_equity: float,
    max_var_pct: float = 3.0,
    confidence: float = 0.95,
) -> tuple[list[Any], int, float]:
    """Remove weakest positions until portfolio VaR is within limit.

    Iteratively removes the position with the lowest ``combined_score``
    until VaR ≤ max_var_pct of account_equity.

    Returns
    -------
    (remaining_positions, removed_count, final_var_pct)
    """
    remaining = list(positions)
    removed = 0

    while remaining:
        var_usd, var_pct = calculate_portfolio_var(remaining, confidence)
        account_var_pct = (var_usd / account_equity * 100) if account_equity > 0 else 0.0

        if account_var_pct <= max_var_pct:
            return remaining, removed, round(account_var_pct, 4)

        # Remove weakest position (lowest combined_score)
        if len(remaining) <= 1:
            break
        weakest_idx = min(range(len(remaining)), key=lambda i: remaining[i].combined_score)
        remaining.pop(weakest_idx)
        removed += 1

    final_var_usd, _ = calculate_portfolio_var(remaining, confidence)
    final_var_pct = (final_var_usd / account_equity * 100) if account_equity > 0 else 0.0
    return remaining, removed, round(final_var_pct, 4)
