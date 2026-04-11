#!/usr/bin/env python3
"""IFDS — Weekly Metrics Aggregation.

Reads daily_metrics JSON files for a given week and generates:
  1. Markdown weekly report → docs/analysis/weekly/YYYY-WNN.md
  2. Telegram summary message

Usage:
    python scripts/analysis/weekly_metrics.py                  # current week
    python scripts/analysis/weekly_metrics.py --week 2026-04-14  # specific Monday
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parents[2]
METRICS_DIR = PROJECT_ROOT / "state" / "daily_metrics"
WEEKLY_DIR = PROJECT_ROOT / "docs" / "analysis" / "weekly"
INITIAL_CAPITAL = 100_000


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _load_week_metrics(week_start: date) -> list[dict]:
    """Load daily metrics JSONs for Mon-Fri of the given week."""
    days: list[dict] = []
    for i in range(5):
        day = week_start + timedelta(days=i)
        path = METRICS_DIR / f"{day.isoformat()}.json"
        if path.exists():
            with open(path) as f:
                try:
                    days.append(json.load(f))
                except json.JSONDecodeError:
                    continue
    return days


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate_week(days: list[dict]) -> dict:
    """Compute weekly aggregate metrics from daily JSON files."""
    n = len(days)

    total_positions = sum(d["positions"]["opened"] for d in days)
    avg_positions = total_positions / n if n else 0
    qualified_avg = mean(
        d["positions"]["qualified_above_threshold"] for d in days
    ) if n else 0

    # P&L
    gross_pnl = sum(d["pnl"]["gross"] for d in days)
    commission = sum(d["execution"]["commission_total"] for d in days)
    net_pnl = gross_pnl - commission
    cum_pnl = days[-1]["pnl"]["cumulative"] if days else 0
    cum_pct = days[-1]["pnl"]["cumulative_pct"] if days else 0
    win_days = sum(1 for d in days if d["pnl"]["gross"] > 0)

    # SPY excess
    spy_returns = [
        d["market"]["spy_return_pct"]
        for d in days
        if d["market"]["spy_return_pct"] is not None
    ]
    spy_weekly = sum(spy_returns) if spy_returns else None
    portfolio_weekly = gross_pnl / INITIAL_CAPITAL * 100
    excess = (portfolio_weekly - spy_weekly) if spy_weekly is not None else None

    # Exits
    exit_keys = ["tp1", "tp2", "sl", "loss_exit", "trail", "moc"]
    exits = {k: sum(d["exits"].get(k, 0) for d in days) for k in exit_keys}

    # TP1 performance
    all_trades = []
    for d in days:
        all_trades.extend(d.get("trades", {}).get("details", []))
    tp1_trades = [t for t in all_trades if t["exit_type"] == "TP1"]
    tp1_avg_pnl = mean(t["pnl"] for t in tp1_trades) if tp1_trades else 0
    sl_trades = [t for t in all_trades if t["exit_type"] in ("SL", "LOSS_EXIT")]
    sl_avg_pnl = mean(abs(t["pnl"]) for t in sl_trades) if sl_trades else 0
    rr_ratio = (tp1_avg_pnl / sl_avg_pnl) if sl_avg_pnl > 0 else 0

    # Scoring
    all_scores = []
    for d in days:
        all_scores.extend(d.get("scoring", {}).get("scores", {}).values())
    avg_score = mean(all_scores) if all_scores else 0

    # Score → P&L correlation (simple, within-week)
    score_pnl_pairs = [
        (t["score"], t["pnl"]) for t in all_trades if t.get("score", 0) > 0
    ]
    week_corr = _simple_correlation(score_pnl_pairs)

    # Slippage
    slippages = []
    for d in days:
        for s in d.get("execution", {}).get("slippage_per_ticker", {}).values():
            slippages.append(s.get("slippage_pct", 0))
    avg_slippage = mean(slippages) if slippages else 0
    worst_slippage = max(slippages, default=0)

    # Dynamic threshold days
    zero_position_days = sum(1 for d in days if d["positions"]["opened"] == 0)
    low_position_days = sum(1 for d in days if 0 < d["positions"]["opened"] < 3)

    return {
        "trading_days": n,
        "total_positions": total_positions,
        "avg_positions_per_day": round(avg_positions, 1),
        "qualified_avg_per_day": round(qualified_avg, 1),
        "win_days": win_days,
        "gross_pnl": round(gross_pnl, 2),
        "commission": round(commission, 2),
        "net_pnl": round(net_pnl, 2),
        "cum_pnl": round(cum_pnl, 2),
        "cum_pct": round(cum_pct, 2),
        "portfolio_weekly_pct": round(portfolio_weekly, 2),
        "spy_weekly_pct": round(spy_weekly, 2) if spy_weekly is not None else None,
        "excess_pct": round(excess, 2) if excess is not None else None,
        "exits": exits,
        "tp1_count": len(tp1_trades),
        "tp1_avg_pnl": round(tp1_avg_pnl, 2),
        "rr_ratio": round(rr_ratio, 2),
        "avg_score": round(avg_score, 1),
        "week_score_pnl_corr": round(week_corr, 3) if week_corr is not None else None,
        "avg_slippage_pct": round(avg_slippage, 2),
        "worst_slippage_pct": round(worst_slippage, 2),
        "commission_pct_of_gross": (
            round(commission / abs(gross_pnl) * 100, 1)
            if gross_pnl != 0 else 0
        ),
        "zero_position_days": zero_position_days,
        "low_position_days": low_position_days,
    }


def _simple_correlation(pairs: list[tuple[float, float]]) -> float | None:
    """Pearson correlation for small samples. Returns None if n < 3."""
    if len(pairs) < 3:
        return None
    try:
        from scipy.stats import pearsonr
        xs, ys = zip(*pairs)
        # Constant input → undefined correlation
        if len(set(xs)) < 2 or len(set(ys)) < 2:
            return None
        r, _ = pearsonr(xs, ys)
        return float(r)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_markdown(week_start: date, agg: dict) -> str:
    week_end = week_start + timedelta(days=4)
    iso_week = week_start.isocalendar()
    week_label = f"{iso_week[0]}-W{iso_week[1]:02d}"

    lines = [
        f"# IFDS Weekly Report — {week_label} ({week_start.strftime('%b %d')}–{week_end.strftime('%b %d')})",
        "",
        "## Summary",
        f"- Trading days: {agg['trading_days']}",
        f"- Positions opened: {agg['total_positions']} (avg {agg['avg_positions_per_day']}/day)",
        f"- Win days: {agg['win_days']}/{agg['trading_days']}",
        "",
        "## P&L",
        f"- Gross: **${agg['gross_pnl']:+,.2f}**",
        f"- Commission: -${agg['commission']:,.2f}",
        f"- Net: **${agg['net_pnl']:+,.2f}**",
        f"- Cumulative: ${agg['cum_pnl']:+,.2f} ({agg['cum_pct']:+.2f}%)",
        "",
    ]

    # SPY excess
    lines.append("## SPY-Adjusted Excess Return")
    if agg["spy_weekly_pct"] is not None:
        lines.append(f"- Portfolio weekly: {agg['portfolio_weekly_pct']:+.2f}%")
        lines.append(f"- SPY weekly: {agg['spy_weekly_pct']:+.2f}%")
        lines.append(f"- **Excess: {agg['excess_pct']:+.2f}%**")
    else:
        lines.append("- SPY data not available")
    lines.append("")

    # Exits
    lines.append("## Exit Breakdown")
    lines.append("| Exit | N | Avg P&L |")
    lines.append("|------|---|---------|")
    for k in ["tp1", "tp2", "trail", "moc", "loss_exit", "sl"]:
        n = agg["exits"].get(k, 0)
        if n > 0:
            lines.append(f"| {k.upper()} | {n} | — |")
    lines.append("")

    # TP1
    lines.append("## TP1 Performance")
    lines.append(f"- TP1 hits: {agg['tp1_count']}/{agg['total_positions']} "
                 f"({agg['tp1_count']/agg['total_positions']*100:.0f}%)"
                 if agg["total_positions"] > 0 else "- No positions")
    lines.append(f"- TP1 avg profit: ${agg['tp1_avg_pnl']:+,.2f}")
    lines.append(f"- R:R realized: 1:{agg['rr_ratio']:.2f}")
    lines.append("")

    # Scoring
    lines.append("## Scoring Quality")
    lines.append(f"- Avg score: {agg['avg_score']:.1f}")
    corr = agg.get("week_score_pnl_corr")
    lines.append(f"- Score→P&L correlation (week): r={corr:+.3f}" if corr else "- Score→P&L correlation: n/a")
    lines.append(f"- Qualified avg: {agg['qualified_avg_per_day']:.1f}/day")
    lines.append("")

    # Slippage
    lines.append("## Slippage & Commission")
    lines.append(f"- Avg MKT fill slippage: {agg['avg_slippage_pct']:+.2f}%")
    lines.append(f"- Worst slippage: {agg['worst_slippage_pct']:+.2f}%")
    lines.append(f"- Commission: ${agg['commission']:,.2f} "
                 f"({agg['commission_pct_of_gross']:.0f}% of gross P&L)")
    lines.append("")

    # Dynamic threshold
    lines.append("## Dynamic Threshold")
    lines.append(f"- Zero-position days: {agg['zero_position_days']}/{agg['trading_days']}")
    lines.append(f"- Low-position days (<3): {agg['low_position_days']}/{agg['trading_days']}")
    lines.append("")

    lines.append("---")
    lines.append(f"*Generated by `scripts/analysis/weekly_metrics.py`*")

    return "\n".join(lines)


def telegram_summary(week_start: date, agg: dict) -> str:
    iso_week = week_start.isocalendar()
    week_label = f"{iso_week[0]}-W{iso_week[1]:02d}"
    tp1_rate = (
        f"{agg['tp1_count']}/{agg['total_positions']} "
        f"({agg['tp1_count']/agg['total_positions']*100:.0f}%)"
        if agg["total_positions"] > 0 else "0"
    )
    excess = f"{agg['excess_pct']:+.2f}%" if agg["excess_pct"] is not None else "n/a"
    return (
        f"IFDS WEEKLY — {week_label}\n"
        f"Net P&L: ${agg['net_pnl']:+,.2f} | Cum: ${agg['cum_pnl']:+,.0f} ({agg['cum_pct']:+.2f}%)\n"
        f"Excess vs SPY: {excess}\n"
        f"Positions: {agg['total_positions']} ({agg['avg_positions_per_day']}/day) | Win days: {agg['win_days']}/{agg['trading_days']}\n"
        f"TP1: {tp1_rate} | R:R: 1:{agg['rr_ratio']:.2f}\n"
        f"Commission: ${agg['commission']:,.0f} ({agg['commission_pct_of_gross']:.0f}% of gross)"
    )


def _send_telegram(message: str) -> None:
    """Send via Telegram Bot API. Non-blocking."""
    try:
        import requests
        token = os.environ.get("IFDS_TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("IFDS_TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            return
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="IFDS Weekly Metrics Aggregation")
    parser.add_argument("--week", help="Monday of the week (YYYY-MM-DD)")
    parser.add_argument("--no-telegram", action="store_true",
                        help="Skip Telegram notification")
    args = parser.parse_args()

    if args.week:
        week_start = date.fromisoformat(args.week)
    else:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

    print(f"Loading daily metrics for week starting {week_start}...")
    days = _load_week_metrics(week_start)

    if not days:
        print(f"No daily metrics found for week {week_start}. "
              f"Run daily_metrics.py first or check --week date.")
        sys.exit(0)

    print(f"  Found {len(days)} trading days with metrics")

    agg = aggregate_week(days)

    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    iso_week = week_start.isocalendar()
    week_label = f"{iso_week[0]}-W{iso_week[1]:02d}"
    report_path = WEEKLY_DIR / f"{week_label}.md"

    report = generate_markdown(week_start, agg)
    with open(report_path, "w") as f:
        f.write(report)
    print(f"Report written: {report_path}")

    tg = telegram_summary(week_start, agg)
    print(f"\nTelegram summary:\n{tg}")

    if not args.no_telegram:
        _send_telegram(tg)
        print("Telegram sent.")


if __name__ == "__main__":
    main()
