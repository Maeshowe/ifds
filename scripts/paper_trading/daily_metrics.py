#!/usr/bin/env python3
"""IFDS Paper Trading — Daily Metrics Collection.

Runs at 22:10 CEST (after EOD report at 22:05). Reads pipeline outputs
and trade results to produce a structured daily metrics JSON for
walk-forward scoring validation.

Usage:
    python scripts/paper_trading/daily_metrics.py
    python scripts/paper_trading/daily_metrics.py --date 2026-04-10  # backfill
"""
from __future__ import annotations

import argparse
import csv
import glob
import gzip
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

try:
    from lib.log_setup import setup_pt_logger
    logger = setup_pt_logger("daily_metrics")
except ModuleNotFoundError:
    import logging
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")
    logger = logging.getLogger("daily_metrics")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CUM_PNL_FILE = PROJECT_ROOT / "scripts" / "paper_trading" / "logs" / "cumulative_pnl.json"
TRADES_DIR = PROJECT_ROOT / "scripts" / "paper_trading" / "logs"
EXEC_PLAN_DIR = PROJECT_ROOT / "output"
PHASE4_DIR = PROJECT_ROOT / "state" / "phase4_snapshots"
METRICS_DIR = PROJECT_ROOT / "state" / "daily_metrics"
INITIAL_CAPITAL = 100_000


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _load_cumulative_pnl() -> dict:
    if not CUM_PNL_FILE.exists():
        return {}
    with open(CUM_PNL_FILE) as f:
        return json.load(f)


def _find_daily_entry(cum_data: dict, target_date: str) -> dict:
    """Find the daily_history entry for a specific date."""
    for entry in cum_data.get("daily_history", []):
        if entry.get("date") == target_date:
            return entry
    return {}


def _load_trades(target_date: str) -> list[dict]:
    path = TRADES_DIR / f"trades_{target_date}.csv"
    if not path.exists():
        return []
    trades = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                trades.append({
                    "ticker": row["ticker"],
                    "score": float(row.get("score", 0) or 0),
                    "entry_price": float(row["entry_price"]),
                    "exit_price": float(row["exit_price"]),
                    "pnl": float(row["pnl"]),
                    "pnl_pct": float(row["pnl_pct"]),
                    "exit_type": row["exit_type"],
                    "sector": row.get("sector", ""),
                    "commission": float(row.get("commission", 0) or 0),
                })
            except (KeyError, ValueError):
                continue
    return trades


def _load_execution_plan(target_date: str) -> dict[str, dict]:
    """Load planned entries from execution plan CSV. Returns {ticker: row}."""
    date_str = target_date.replace("-", "")
    pattern = str(EXEC_PLAN_DIR / f"execution_plan_run_{date_str}_*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        return {}
    planned: dict[str, dict] = {}
    with open(files[-1], newline="") as f:
        for row in csv.DictReader(f):
            planned[row["instrument_id"]] = {
                "limit_price": float(row["limit_price"]),
                "quantity": int(row["quantity"]),
                "score": float(row.get("score", 0) or 0),
                "multiplier_total": float(row.get("multiplier_total", 1) or 1),
                "risk_usd": float(row.get("risk_usd", 0) or 0),
            }
    return planned


def _load_phase4_snapshot(target_date: str) -> dict[str, dict]:
    """Load Phase 4 snapshot. Returns {ticker: data}."""
    path = PHASE4_DIR / f"{target_date}.json.gz"
    if not path.exists():
        return {}
    with gzip.open(path) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return {}
    if not isinstance(data, list):
        return {}
    return {row["ticker"]: row for row in data if "ticker" in row}


def _fetch_spy_return(target_date: str) -> float | None:
    """Fetch SPY daily return from Polygon (single API call)."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from ifds.data.polygon import PolygonClient
    except ImportError:
        return None

    api_key = os.environ.get("IFDS_POLYGON_API_KEY")
    if not api_key:
        return None

    prev_date = (date.fromisoformat(target_date) - timedelta(days=5)).isoformat()
    try:
        client = PolygonClient(api_key)
        bars = client.get_aggregates("SPY", prev_date, target_date, timespan="day")
    except Exception as e:
        logger.warning(f"SPY fetch failed: {e}")
        return None

    if not bars or len(bars) < 2:
        return None

    bars_sorted = sorted(bars, key=lambda b: b.get("t", 0))
    prev_close = bars_sorted[-2].get("c")
    today_close = bars_sorted[-1].get("c")
    if prev_close and today_close and prev_close > 0:
        return (today_close - prev_close) / prev_close * 100
    return None


# ---------------------------------------------------------------------------
# Metrics calculation
# ---------------------------------------------------------------------------


def build_daily_metrics(target_date: str) -> dict:
    """Build the complete daily metrics JSON for a given date."""
    cum_data = _load_cumulative_pnl()
    daily = _find_daily_entry(cum_data, target_date)
    trades = _load_trades(target_date)
    planned = _load_execution_plan(target_date)
    snapshot = _load_phase4_snapshot(target_date)

    # --- Positions ---
    qualified_count = len(snapshot) if snapshot else 0
    threshold = 85  # BC23 dynamic_position_score_threshold

    # --- Scoring ---
    scores = {t["ticker"]: t["score"] for t in trades if t["score"] > 0}
    avg_score = sum(scores.values()) / len(scores) if scores else 0
    min_score = min(scores.values()) if scores else 0
    max_score = max(scores.values()) if scores else 0

    # --- Slippage ---
    slippage: dict[str, dict] = {}
    for t in trades:
        sym = t["ticker"]
        if sym in planned:
            p = planned[sym]["limit_price"]
            f = t["entry_price"]
            slippage[sym] = {
                "planned": p,
                "filled": f,
                "slippage_pct": round((f - p) / p * 100, 2) if p > 0 else 0,
            }
    avg_slippage = (
        sum(s["slippage_pct"] for s in slippage.values()) / len(slippage)
        if slippage else 0
    )

    # --- Commission ---
    commission_total = sum(t["commission"] for t in trades)

    # --- Exits ---
    exit_counts: dict[str, int] = {}
    for t in trades:
        et = t["exit_type"]
        exit_counts[et] = exit_counts.get(et, 0) + 1

    # --- P&L ---
    gross_pnl = daily.get("pnl", sum(t["pnl"] for t in trades))
    net_pnl = gross_pnl - commission_total
    cum_pnl = cum_data.get("cumulative_pnl", 0)
    cum_pct = cum_data.get("cumulative_pnl_pct", 0)

    # --- SPY excess return ---
    spy_return = _fetch_spy_return(target_date)
    portfolio_return = gross_pnl / INITIAL_CAPITAL * 100
    excess = (portfolio_return - spy_return) if spy_return is not None else None

    # --- Best / worst trade ---
    best = max(trades, key=lambda t: t["pnl"]) if trades else None
    worst = min(trades, key=lambda t: t["pnl"]) if trades else None

    # --- VIX (from Phase 0 log or snapshot) ---
    # Not available directly — leave as None for now
    vix_close = None

    return {
        "date": target_date,
        "day_number": cum_data.get("trading_days", 0),

        "positions": {
            "opened": len(trades),
            "qualified_above_threshold": qualified_count,
            "threshold": threshold,
            "max_allowed": 5,
        },

        "market": {
            "spy_return_pct": round(spy_return, 2) if spy_return is not None else None,
            "vix_close": vix_close,
            "strategy": "LONG",
        },

        "scoring": {
            "avg_score": round(avg_score, 1),
            "min_score": round(min_score, 1),
            "max_score": round(max_score, 1),
            "scores": {k: round(v, 1) for k, v in scores.items()},
        },

        "execution": {
            "avg_fill_slippage_pct": round(avg_slippage, 2),
            "slippage_per_ticker": slippage,
            "commission_total": round(commission_total, 2),
        },

        "exits": {
            "tp1": exit_counts.get("TP1", 0),
            "tp2": exit_counts.get("TP2", 0),
            "sl": exit_counts.get("SL", 0),
            "loss_exit": exit_counts.get("LOSS_EXIT", 0),
            "trail": exit_counts.get("TRAIL", 0),
            "moc": exit_counts.get("MOC", 0),
        },

        "pnl": {
            "gross": round(gross_pnl, 2),
            "commission": round(commission_total, 2),
            "net": round(net_pnl, 2),
            "cumulative": round(cum_pnl, 2),
            "cumulative_pct": round(cum_pct, 2),
        },

        "excess_return": {
            "portfolio_return_pct": round(portfolio_return, 2),
            "spy_return_pct": round(spy_return, 2) if spy_return is not None else None,
            "excess_pct": round(excess, 2) if excess is not None else None,
        },

        "trades": {
            "best": {
                "ticker": best["ticker"],
                "pnl": round(best["pnl"], 2),
                "pnl_pct": round(best["pnl_pct"], 2),
                "exit_type": best["exit_type"],
            } if best else None,
            "worst": {
                "ticker": worst["ticker"],
                "pnl": round(worst["pnl"], 2),
                "pnl_pct": round(worst["pnl_pct"], 2),
                "exit_type": worst["exit_type"],
            } if worst else None,
            "details": [
                {
                    "ticker": t["ticker"],
                    "score": round(t["score"], 1),
                    "entry": round(t["entry_price"], 2),
                    "exit": round(t["exit_price"], 2),
                    "pnl": round(t["pnl"], 2),
                    "exit_type": t["exit_type"],
                }
                for t in sorted(trades, key=lambda x: x["pnl"], reverse=True)
            ],
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    try:
        from lib.trading_day_guard import check_trading_day
        check_trading_day(logger)
    except ModuleNotFoundError:
        pass

    parser = argparse.ArgumentParser(description="IFDS Daily Metrics Collection")
    parser.add_argument("--date", help="Override date (YYYY-MM-DD) for backfill")
    args = parser.parse_args()

    target_date = args.date or date.today().isoformat()
    logger.info(f"Daily metrics collection — {target_date}")

    metrics = build_daily_metrics(target_date)

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = METRICS_DIR / f"{target_date}.json"
    with open(out_path, "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info(
        f"Metrics written: {out_path} — "
        f"{metrics['positions']['opened']} trades, "
        f"P&L ${metrics['pnl']['gross']:+,.2f}, "
        f"cum ${metrics['pnl']['cumulative']:+,.2f}"
    )


if __name__ == "__main__":
    main()
