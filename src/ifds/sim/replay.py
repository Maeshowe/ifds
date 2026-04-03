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
    new_tp1 = overrides.get("tp1_atr_multiple", 0.75)
    new_tp2 = overrides.get("tp2_atr_multiple", 3.0)

    trade.stop_loss = round(trade.entry_price - new_sl * atr, 2)
    trade.tp1 = round(trade.entry_price + new_tp1 * atr, 2)
    trade.tp2 = round(trade.entry_price + new_tp2 * atr, 2)
    return trade


# ============================================================================
# YAML Config Loading
# ============================================================================

def load_variants_from_yaml(yaml_path: str) -> tuple[list[SimVariant], dict]:
    """Load variant definitions from YAML config file.

    Returns (variants, metadata) where metadata may contain ``mode``
    and ``snapshot_dir`` for Mode 2 configs.
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Variant config not found: {yaml_path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    if not data or "variants" not in data:
        raise ValueError(f"Invalid variant config: missing 'variants' key")

    mode = str(data.get("mode", 1))
    metadata = {
        "mode": f"mode{mode}" if not mode.startswith("mode") else mode,
        "snapshot_dir": data.get("snapshot_dir", "state/phase4_snapshots"),
    }

    variants = []
    for v in data["variants"]:
        variants.append(SimVariant(
            name=v.get("name", "unnamed"),
            description=v.get("description", ""),
            overrides=v.get("overrides") or {},
            mode=metadata["mode"],
        ))
    return variants, metadata


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

        # Get variant-specific params
        hold = variant.overrides.get("max_hold_days", max_hold_days)
        fill_window = variant.overrides.get("fill_window_days", 1)
        sim_mode = variant.overrides.get("sim_mode", "bracket")
        swing_params = {
            k: variant.overrides[k]
            for k in ("tp1_atr_mult", "trail_atr_mult", "trail_atr_volatile", "breakeven_atr_mult", "tp1_exit_pct", "mms_regime")
            if k in variant.overrides
        }

        # Simulate
        variant.trades, variant.summary = validate_trades_with_bars(
            trades_copy, bars_by_ticker, hold, fill_window,
            sim_mode=sim_mode, swing_params=swing_params or None,
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
        sim_mode = variant.overrides.get("sim_mode", "bracket")
        swing_params = {
            k: variant.overrides[k]
            for k in ("tp1_atr_mult", "trail_atr_mult", "trail_atr_volatile", "breakeven_atr_mult", "tp1_exit_pct", "mms_regime")
            if k in variant.overrides
        }

        variant.trades, variant.summary = validate_trades_with_bars(
            trades_copy, bars_by_ticker, hold, fill_window,
            sim_mode=sim_mode, swing_params=swing_params or None,
        )

    return compare_variants(variants)


# ============================================================================
# Mode 2: Re-Score Comparison
# ============================================================================

def run_mode2_comparison(
    variants: list[SimVariant],
    snapshot_dir: str = "state/phase4_snapshots",
    polygon_api_key: str | None = None,
    max_hold_days: int = 10,
    cache_dir: str | None = None,
    gex_multiplier: float = 1.0,
    vix: float | None = None,
) -> ComparisonReport:
    """Run Mode 2: re-score Phase 4 snapshots with different configs.

    For each variant:
      1. Load all snapshots from ``snapshot_dir``
      2. For each day: ``rescore_snapshot`` → sized positions → Trade objects
      3. Fetch Polygon bars (shared, once)
      4. Simulate brackets (reuse ``validate_trades_with_bars``)
      5. Compare variants statistically

    Args:
        variants: SimVariant list with config overrides.
        snapshot_dir: Path to Phase 4 snapshot files.
        polygon_api_key: For fetching post-plan bars.
        max_hold_days: Bracket simulation window.
        cache_dir: Polygon bar cache.
        gex_multiplier: Mock GEX multiplier (1.0 = neutral).
        vix: VIX level for M_vix (None = no penalty).
    """
    from datetime import date as date_cls

    from ifds.data.phase4_snapshot import load_phase4_snapshot
    from ifds.sim.rescore import rescore_snapshot

    if not variants:
        return ComparisonReport()

    # 1. Discover snapshot dates
    snap_dir = Path(snapshot_dir)
    if not snap_dir.exists():
        return ComparisonReport(baseline=variants[0])

    snapshot_files = sorted(snap_dir.glob("*.json.gz")) + sorted(snap_dir.glob("*.json"))
    # Deduplicate dates (prefer .json.gz)
    seen_dates: dict[str, Path] = {}
    for f in snapshot_files:
        date_str = f.stem.replace(".json", "")
        if date_str not in seen_dates:
            seen_dates[date_str] = f
    snapshot_dates = sorted(seen_dates.keys())

    if not snapshot_dates:
        return ComparisonReport(baseline=variants[0])

    # 2. For each variant: rescore all days → Trade objects
    for variant in variants:
        all_trades: list[Trade] = []
        ewma_state: dict[str, float] = {}

        for date_str in snapshot_dates:
            records = load_phase4_snapshot(date_str, snapshot_dir)
            if not records:
                continue

            positions = rescore_snapshot(
                records,
                config_overrides=variant.overrides,
                gex_multiplier=gex_multiplier,
                vix=vix,
                ewma_state=ewma_state if variant.overrides.get("ewma_enabled") else None,
            )

            run_date = date_cls.fromisoformat(date_str)

            for pos in positions:
                trade = Trade(
                    run_id=f"rescore_{date_str}",
                    run_date=run_date,
                    ticker=pos.ticker,
                    score=pos.combined_score,
                    gex_regime="neutral",
                    multiplier=pos.m_total,
                    entry_price=pos.entry_price,
                    quantity=pos.quantity,
                    direction=pos.direction,
                    stop_loss=pos.stop_loss,
                    tp1=pos.tp1,
                    tp2=pos.tp2,
                    sector=pos.sector,
                )
                all_trades.append(trade)

        variant.trades = all_trades

    # 3. Fetch bars (once, shared across variants)
    # Collect all unique (ticker, run_date) across all variants
    all_variant_trades: list[Trade] = []
    for v in variants:
        all_variant_trades.extend(v.trades)
    bars_by_ticker = _fetch_bars_once(
        all_variant_trades, polygon_api_key, max_hold_days, cache_dir,
    )

    # 4. Simulate for each variant
    for variant in variants:
        if not variant.trades:
            variant.summary = aggregate_summary([])
            continue

        hold = variant.overrides.get("max_hold_days", max_hold_days)
        fill_window = variant.overrides.get("fill_window_days", 1)
        sim_mode = variant.overrides.get("sim_mode", "bracket")
        swing_params = {
            k: variant.overrides[k]
            for k in ("tp1_atr_mult", "trail_atr_mult", "trail_atr_volatile", "breakeven_atr_mult", "tp1_exit_pct", "mms_regime")
            if k in variant.overrides
        }

        variant.trades, variant.summary = validate_trades_with_bars(
            variant.trades, bars_by_ticker, hold, fill_window,
            sim_mode=sim_mode, swing_params=swing_params or None,
        )

    # 5. Compare
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
