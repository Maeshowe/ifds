"""Level 1 Forward Validator.

Loads execution plan CSVs, fetches post-plan OHLCV from Polygon,
runs bracket order simulation, and aggregates results.
"""

import asyncio
import csv
import re
from datetime import date, timedelta
from pathlib import Path

from ifds.sim.broker_sim import compute_qty_split, simulate_bracket_order
from ifds.sim.models import Trade, ValidationSummary


# ============================================================================
# CSV Loading
# ============================================================================

def load_execution_plans(output_dir: str = "output") -> list[Trade]:
    """Load all execution_plan_*.csv files and convert to Trade objects.

    Parses run_id and run_date from the filename pattern:
      execution_plan_run_YYYYMMDD_HHMMSS_<hex>.csv

    Only includes plans older than 1 day (need post-plan data).

    Returns:
        List of Trade objects with entry parameters set.
    """
    out_path = Path(output_dir)
    if not out_path.exists():
        return []

    trades = []
    today = date.today()

    for csv_file in sorted(out_path.glob("execution_plan_*.csv")):
        run_id = csv_file.stem.replace("execution_plan_", "")

        # Parse date from run_id: run_YYYYMMDD_HHMMSS_hex
        run_date = _parse_run_date(run_id)
        if run_date is None:
            continue

        # Skip plans from today (no post-plan data yet)
        if run_date >= today:
            continue

        with open(csv_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    quantity = int(row.get("quantity", 0))
                    if quantity <= 0:
                        continue

                    entry_price = float(row.get("limit_price", 0))
                    if entry_price <= 0:
                        continue

                    tp1 = float(row.get("take_profit_1", 0))
                    tp2 = float(row.get("take_profit_2", 0))
                    stop = float(row.get("stop_loss", 0))

                    qty_tp1, qty_tp2 = compute_qty_split(quantity)

                    trade = Trade(
                        run_id=run_id,
                        run_date=run_date,
                        ticker=row.get("instrument_id", ""),
                        score=float(row.get("score", 0)),
                        gex_regime=row.get("gex_regime", ""),
                        multiplier=float(row.get("multiplier_total", 1.0)),
                        entry_price=entry_price,
                        quantity=quantity,
                        direction=row.get("direction", "BUY"),
                        stop_loss=stop,
                        tp1=tp1,
                        tp2=tp2,
                        qty_tp1=qty_tp1,
                        qty_tp2=qty_tp2,
                        sector=row.get("sector", ""),
                    )
                    trades.append(trade)
                except (ValueError, KeyError):
                    continue

    return trades


def _parse_run_date(run_id: str) -> date | None:
    """Extract date from run_id: run_YYYYMMDD_HHMMSS_hex."""
    match = re.match(r"run_(\d{8})_", run_id)
    if match:
        try:
            return date(int(match.group(1)[:4]),
                        int(match.group(1)[4:6]),
                        int(match.group(1)[6:8]))
        except ValueError:
            return None
    return None


# ============================================================================
# Polygon Data Fetching (async with cache)
# ============================================================================

async def _fetch_bars_for_trades(trades: list[Trade],
                                 polygon_api_key: str,
                                 max_hold_days: int = 10,
                                 fill_window_days: int = 1,
                                 cache_dir: str | None = None) -> dict[str, dict[str, list[dict]]]:
    """Fetch post-plan OHLCV bars for all trades.

    Returns:
        {ticker: {run_date_iso: [bar_dicts]}} — bars starting from plan_date + 1.
    """
    from ifds.data.async_clients import AsyncPolygonClient

    # Deduplicate (ticker, from_date, to_date) requests
    today = date.today()
    requests: dict[tuple[str, str, str], list] = {}
    for trade in trades:
        from_date = (trade.run_date + timedelta(days=1)).isoformat()
        # Use trading calendar for precise range, cap at today to avoid stale cache
        try:
            from ifds.utils.trading_calendar import add_trading_days
            raw_to = add_trading_days(trade.run_date, max_hold_days + fill_window_days + 2)
        except Exception:
            # Fallback: calendar days + padding for weekends/holidays
            raw_to = trade.run_date + timedelta(days=max_hold_days + fill_window_days + 5)
        to_date = min(today, raw_to).isoformat()
        key = (trade.ticker, from_date, to_date)
        if key not in requests:
            requests[key] = []
        requests[key].append(trade)

    # Fetch with semaphore rate limiting
    sem = asyncio.Semaphore(10)
    cache = None
    if cache_dir:
        from ifds.data.cache import FileCache
        cache = FileCache(cache_dir)

    polygon = AsyncPolygonClient(
        api_key=polygon_api_key,
        timeout=10,
        max_retries=3,
        semaphore=sem,
        cache=cache,
    )

    results: dict[str, dict[str, list[dict]]] = {}

    try:
        tasks = []
        task_keys = []
        for (ticker, from_d, to_d) in requests:
            tasks.append(polygon.get_aggregates(ticker, from_d, to_d))
            task_keys.append((ticker, from_d, to_d))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for (ticker, from_d, to_d), response in zip(task_keys, responses):
            if isinstance(response, Exception) or response is None:
                continue

            bars = []
            for bar in response:
                # Polygon agg bars: {"t": timestamp_ms, "o", "h", "l", "c", "v", ...}
                if "t" in bar:
                    bar_date = date.fromtimestamp(bar["t"] / 1000).isoformat()
                    bars.append({
                        "date": bar_date,
                        "o": bar.get("o", 0),
                        "h": bar.get("h", 0),
                        "l": bar.get("l", 0),
                        "c": bar.get("c", 0),
                        "v": bar.get("v", 0),
                    })
                elif "date" in bar:
                    bars.append(bar)

            if ticker not in results:
                results[ticker] = {}
            results[ticker][from_d] = bars

    finally:
        await polygon.close()

    return results


# ============================================================================
# Validation Orchestrator
# ============================================================================

def validate_execution_plans(output_dir: str = "output",
                             polygon_api_key: str | None = None,
                             max_hold_days: int = 10,
                             fill_window_days: int = 1,
                             cache_dir: str | None = None) -> tuple[list[Trade], ValidationSummary]:
    """Run forward validation on all execution plan CSVs.

    1. Load execution_plan_*.csv from output_dir
    2. Fetch post-plan OHLCV from Polygon (async, cached)
    3. Run bracket simulation on each trade
    4. Aggregate ValidationSummary

    Args:
        output_dir: Directory containing execution_plan CSVs.
        polygon_api_key: Polygon API key. If None, uses IFDS_POLYGON_API_KEY env var.
        max_hold_days: Maximum holding period (default 10).
        fill_window_days: Days to attempt fill (default 1).
        cache_dir: Cache directory for Polygon responses.

    Returns:
        (list of Trade objects with results, ValidationSummary)
    """
    import os

    if polygon_api_key is None:
        polygon_api_key = os.environ.get("IFDS_POLYGON_API_KEY", "")

    # 1. Load trades from CSVs
    trades = load_execution_plans(output_dir)
    if not trades:
        return [], ValidationSummary()

    # 2. Fetch OHLCV data
    bars_data = asyncio.run(_fetch_bars_for_trades(
        trades, polygon_api_key, max_hold_days, fill_window_days, cache_dir,
    ))

    # 3. Simulate each trade
    for trade in trades:
        from_date = (trade.run_date + timedelta(days=1)).isoformat()
        ticker_data = bars_data.get(trade.ticker, {})
        bars = ticker_data.get(from_date, [])
        simulate_bracket_order(trade, bars, max_hold_days, fill_window_days)

    # 4. Aggregate
    summary = aggregate_summary(trades)

    return trades, summary


def validate_trades_with_bars(trades: list[Trade],
                              bars_by_ticker: dict[str, list[dict]],
                              max_hold_days: int = 10,
                              fill_window_days: int = 1) -> tuple[list[Trade], ValidationSummary]:
    """Validate trades with pre-provided bars (for testing without Polygon).

    Args:
        trades: Trade objects with entry parameters.
        bars_by_ticker: {ticker: [bar_dicts]} — bars starting from plan_date + 1.
        max_hold_days: Maximum holding period.
        fill_window_days: Days to attempt fill.

    Returns:
        (list of Trade objects with results, ValidationSummary)
    """
    for trade in trades:
        bars = bars_by_ticker.get(trade.ticker, [])
        simulate_bracket_order(trade, bars, max_hold_days, fill_window_days)

    summary = aggregate_summary(trades)
    return trades, summary


# ============================================================================
# Summary Aggregation
# ============================================================================

def aggregate_summary(trades: list[Trade]) -> ValidationSummary:
    """Aggregate trade results into ValidationSummary."""
    summary = ValidationSummary()
    summary.total_trades = len(trades)

    filled = [t for t in trades if t.filled]
    summary.filled_trades = len(filled)
    summary.unfilled_trades = summary.total_trades - summary.filled_trades

    if not filled:
        # Metadata
        run_dates = [t.run_date for t in trades if t.run_date]
        if run_dates:
            summary.date_range_start = min(run_dates)
            summary.date_range_end = max(run_dates)
        summary.plan_count = len(set(t.run_id for t in trades))
        return summary

    # Leg 1 stats
    for t in filled:
        if t.leg1_exit_reason in ("tp1",):
            summary.leg1_tp_hits += 1
        elif t.leg1_exit_reason == "stop":
            summary.leg1_stop_hits += 1
        elif t.leg1_exit_reason == "expired":
            summary.leg1_expired += 1

    leg1_resolved = summary.leg1_tp_hits + summary.leg1_stop_hits
    if leg1_resolved > 0:
        summary.leg1_win_rate = summary.leg1_tp_hits / leg1_resolved * 100

    # Leg 2 stats
    for t in filled:
        if t.leg2_exit_reason in ("tp2",):
            summary.leg2_tp_hits += 1
        elif t.leg2_exit_reason == "stop":
            summary.leg2_stop_hits += 1
        elif t.leg2_exit_reason == "expired":
            summary.leg2_expired += 1

    leg2_resolved = summary.leg2_tp_hits + summary.leg2_stop_hits
    if leg2_resolved > 0:
        summary.leg2_win_rate = summary.leg2_tp_hits / leg2_resolved * 100

    # P&L
    pnls = [t.total_pnl for t in filled]
    summary.total_pnl = sum(pnls)
    summary.avg_pnl_per_trade = summary.total_pnl / len(filled)

    pnl_pcts = [t.total_pnl_pct for t in filled]
    summary.avg_pnl_pct = sum(pnl_pcts) / len(pnl_pcts) if pnl_pcts else 0

    best = max(filled, key=lambda t: t.total_pnl)
    worst = min(filled, key=lambda t: t.total_pnl)
    summary.best_trade_pnl = best.total_pnl
    summary.best_trade_ticker = best.ticker
    summary.worst_trade_pnl = worst.total_pnl
    summary.worst_trade_ticker = worst.ticker

    # Holding days
    holding = [t.holding_days for t in filled if t.holding_days > 0]
    summary.avg_holding_days = sum(holding) / len(holding) if holding else 0

    # GEX regime breakdown
    gex_groups: dict[str, list[Trade]] = {}
    for t in filled:
        regime = t.gex_regime or "unknown"
        gex_groups.setdefault(regime, []).append(t)

    for regime, group in gex_groups.items():
        pnl = sum(t.total_pnl for t in group)
        wins = sum(1 for t in group if t.total_pnl > 0)
        wr = wins / len(group) * 100 if group else 0
        summary.pnl_by_gex_regime[regime] = {
            "pnl": round(pnl, 2),
            "trades": len(group),
            "win_rate": round(wr, 1),
        }

    # Score bucket breakdown
    buckets = {"70-80": [], "80-90": [], "90+": []}
    for t in filled:
        if t.score >= 90:
            buckets["90+"].append(t)
        elif t.score >= 80:
            buckets["80-90"].append(t)
        else:
            buckets["70-80"].append(t)

    for bucket, group in buckets.items():
        if group:
            wins = sum(1 for t in group if t.total_pnl > 0)
            summary.win_rate_by_score_bucket[bucket] = round(
                wins / len(group) * 100, 1)

    # Metadata
    run_dates = [t.run_date for t in trades if t.run_date]
    if run_dates:
        summary.date_range_start = min(run_dates)
        summary.date_range_end = max(run_dates)
    summary.plan_count = len(set(t.run_id for t in trades))

    return summary
