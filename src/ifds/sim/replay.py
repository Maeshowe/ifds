"""Level 2 Parameter Sweep — Multi-variant bracket order comparison.

Loads execution plan CSVs once, fetches bars once, then runs each variant
with different TP/SL/hold parameters and compares results.
"""

import copy
from pathlib import Path

import yaml

from ifds.sim.broker_sim import simulate_bracket_order
from ifds.sim.comparison import compare_variants
from ifds.sim.models import ComparisonReport, SimVariant, Trade
from ifds.sim.validator import (
    aggregate_summary,
    load_execution_plans,
    validate_trades_with_bars,
)


# ============================================================================
# Parameter Override
# ============================================================================

def recalculate_bracket(trade: Trade, overrides: dict,
                        original_sl_atr_mult: float = 1.5) -> Trade:
    """Recalculate TP/SL from implied ATR and new multipliers.

    The execution plan CSV contains entry_price and stop_loss. We infer ATR:
        ATR = (entry_price - stop_loss) / original_sl_atr_mult

    Then apply new multipliers to compute new TP/SL values.
    """
    if trade.entry_price <= 0 or trade.stop_loss <= 0:
        return trade

    atr = (trade.entry_price - trade.stop_loss) / original_sl_atr_mult
    if atr <= 0:
        return trade

    new_sl = overrides.get("stop_loss_atr_multiple", original_sl_atr_mult)
    new_tp1 = overrides.get("tp1_atr_multiple", 2.0)
    new_tp2 = overrides.get("tp2_atr_multiple", 3.0)

    trade.stop_loss = round(trade.entry_price - new_sl * atr, 2)
    trade.tp1 = round(trade.entry_price + new_tp1 * atr, 2)
    trade.tp2 = round(trade.entry_price + new_tp2 * atr, 2)
    return trade


# ============================================================================
# YAML Config Loading
# ============================================================================

def load_variants_from_yaml(yaml_path: str) -> list[SimVariant]:
    """Load variant definitions from YAML config file."""
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Variant config not found: {yaml_path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    if not data or "variants" not in data:
        raise ValueError(f"Invalid variant config: missing 'variants' key")

    variants = []
    for v in data["variants"]:
        variants.append(SimVariant(
            name=v.get("name", "unnamed"),
            description=v.get("description", ""),
            overrides=v.get("overrides", {}),
        ))
    return variants


# ============================================================================
# Comparison Orchestrator
# ============================================================================

def run_comparison(
    variants: list[SimVariant],
    output_dir: str = "output",
    polygon_api_key: str | None = None,
    max_hold_days: int = 10,
    cache_dir: str | None = None,
    original_sl_atr_mult: float = 1.5,
) -> ComparisonReport:
    """Run multi-variant parameter sweep on execution plan data.

    1. Load execution plan CSVs once
    2. Fetch Polygon bars once (if API key provided)
    3. For each variant: deep copy trades, apply overrides, simulate, aggregate
    4. Compare variants statistically

    Args:
        variants: List of SimVariant with name/overrides.
        output_dir: Directory containing execution_plan CSVs.
        polygon_api_key: Polygon API key for fetching bars.
        max_hold_days: Default max holding period.
        cache_dir: Cache directory for Polygon responses.
        original_sl_atr_mult: Original SL ATR multiplier used in pipeline.

    Returns:
        ComparisonReport with baseline, challengers, and deltas.
    """
    if not variants:
        return ComparisonReport()

    # 1. Load base trades
    base_trades = load_execution_plans(output_dir)
    if not base_trades:
        return ComparisonReport(baseline=variants[0])

    # 2. Fetch bars (once for all variants)
    bars_by_ticker = _fetch_bars_once(base_trades, polygon_api_key,
                                       max_hold_days, cache_dir)

    # 3. Run each variant
    for variant in variants:
        trades_copy = _deep_copy_trades(base_trades)

        # Apply parameter overrides
        if variant.overrides:
            for trade in trades_copy:
                recalculate_bracket(trade, variant.overrides, original_sl_atr_mult)

        # Get variant-specific max_hold_days
        hold = variant.overrides.get("max_hold_days", max_hold_days)
        fill_window = variant.overrides.get("fill_window_days", 1)

        # Simulate
        variant.trades, variant.summary = validate_trades_with_bars(
            trades_copy, bars_by_ticker, hold, fill_window,
        )

    # 4. Compare
    return compare_variants(variants)


def run_comparison_with_bars(
    variants: list[SimVariant],
    base_trades: list[Trade],
    bars_by_ticker: dict[str, list[dict]],
    max_hold_days: int = 10,
    original_sl_atr_mult: float = 1.5,
) -> ComparisonReport:
    """Run comparison with pre-provided trades and bars (for testing)."""
    if not variants:
        return ComparisonReport()

    for variant in variants:
        trades_copy = _deep_copy_trades(base_trades)

        if variant.overrides:
            for trade in trades_copy:
                recalculate_bracket(trade, variant.overrides, original_sl_atr_mult)

        hold = variant.overrides.get("max_hold_days", max_hold_days)
        fill_window = variant.overrides.get("fill_window_days", 1)

        variant.trades, variant.summary = validate_trades_with_bars(
            trades_copy, bars_by_ticker, hold, fill_window,
        )

    return compare_variants(variants)


# ============================================================================
# Internal helpers
# ============================================================================

def _deep_copy_trades(trades: list[Trade]) -> list[Trade]:
    """Deep copy trade list to avoid mutation between variants."""
    return [copy.deepcopy(t) for t in trades]


def _fetch_bars_once(trades: list[Trade], polygon_api_key: str | None,
                     max_hold_days: int, cache_dir: str | None
                     ) -> dict[str, list[dict]]:
    """Fetch bars for all tickers once (shared across variants).

    Returns {ticker: [bar_dicts]} — flat mapping for validate_trades_with_bars.
    """
    if not polygon_api_key:
        return {}

    import asyncio
    from datetime import timedelta

    from ifds.sim.validator import _fetch_bars_for_trades

    # Fetch the nested structure
    nested = asyncio.run(_fetch_bars_for_trades(
        trades, polygon_api_key, max_hold_days, 1, cache_dir,
    ))

    # Flatten: {ticker: {from_date: bars}} -> {ticker: bars}
    # For each ticker, merge all date ranges (they should be the same per ticker)
    flat: dict[str, list[dict]] = {}
    for ticker, date_map in nested.items():
        for from_date, bars in date_map.items():
            if ticker not in flat:
                flat[ticker] = bars
            # If multiple run dates for same ticker, keep the one with most bars
            elif len(bars) > len(flat[ticker]):
                flat[ticker] = bars

    return flat
