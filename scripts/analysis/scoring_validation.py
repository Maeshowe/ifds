#!/usr/bin/env python3
"""IFDS Scoring Validation & Multiplier Impact Analysis.

Standalone read-only analysis script. Does NOT modify any pipeline state.
Answers the core question: does IFDS scoring generate alpha, or is P&L
purely a function of daily market direction?

Inputs:
    - state/phase4_snapshots/YYYY-MM-DD.json.gz (Phase 4 per-ticker scores)
    - scripts/paper_trading/logs/trades_YYYY-MM-DD.csv (actual fills)
    - scripts/paper_trading/logs/cumulative_pnl.json (daily P&L history)
    - docs/analysis/spy_returns.json (cached SPY daily returns)

Outputs:
    - docs/analysis/scoring-validation.md (report with tables)
    - docs/analysis/plots/*.png (matplotlib scatter + quintile bars)

Usage:
    python scripts/analysis/scoring_validation.py
    python scripts/analysis/scoring_validation.py --fetch-spy  # refresh SPY cache
"""
from __future__ import annotations

import argparse
import csv
import glob
import gzip
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, median, stdev

try:
    import matplotlib

    matplotlib.use("Agg")  # non-interactive backend for script use
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy import stats
except ImportError as e:
    print(f"ERROR: missing analysis dependency ({e}). "
          f"Install: pip install matplotlib scipy numpy", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASE4_DIR = PROJECT_ROOT / "state" / "phase4_snapshots"
TRADES_DIR = PROJECT_ROOT / "scripts" / "paper_trading" / "logs"
CUM_PNL_FILE = TRADES_DIR / "cumulative_pnl.json"
OUT_DIR = PROJECT_ROOT / "docs" / "analysis"
PLOTS_DIR = OUT_DIR / "plots"
REPORT_PATH = OUT_DIR / "scoring-validation.md"
SPY_CACHE = OUT_DIR / "spy_returns.json"

# Approximate weights reconstructed from the pipeline (flow=0.40, funda=0.30, tech=0.30).
# The raw component sums differ — they're normalized downstream. Here we just
# group sub-scores into "flow-ish" / "tech-ish" / "funda-ish" buckets to see
# which bucket correlates with trade P&L.
FLOW_FIELDS = [
    "rvol_score", "dp_pct_score", "pcr_score", "otm_score",
    "block_trade_score", "buy_pressure_score",
]
TECH_FIELDS = ["rsi_score", "sma50_bonus", "rs_spy_score"]
FUNDA_FIELD = "funda_score"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@dataclass
class Trade:
    date: str
    ticker: str
    direction: str
    entry_price: float
    exit_price: float
    exit_type: str
    pnl: float
    pnl_pct: float
    score: float
    sector: str
    # Enriched from Phase 4 snapshot
    flow_subscore: float | None = None
    tech_subscore: float | None = None
    funda_subscore: float | None = None
    # Enriched from SPY cache
    spy_return_pct: float | None = None
    excess_return_pct: float | None = None


def load_trades() -> list[Trade]:
    """Load all trades_*.csv files into Trade dataclasses."""
    trades: list[Trade] = []
    for csv_path in sorted(glob.glob(str(TRADES_DIR / "trades_*.csv"))):
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    trades.append(
                        Trade(
                            date=row["date"],
                            ticker=row["ticker"],
                            direction=row["direction"],
                            entry_price=float(row["entry_price"]),
                            exit_price=float(row["exit_price"]),
                            exit_type=row["exit_type"],
                            pnl=float(row["pnl"]),
                            pnl_pct=float(row["pnl_pct"]),
                            score=float(row["score"]) if row.get("score") else 0.0,
                            sector=row.get("sector", ""),
                        )
                    )
                except (KeyError, ValueError) as e:
                    print(f"WARN skipping row in {csv_path}: {e}")
    return trades


def load_phase4_snapshots() -> dict[str, dict[str, dict]]:
    """Return {date: {ticker: row_dict}} for all available snapshots."""
    out: dict[str, dict[str, dict]] = {}
    for path in sorted(glob.glob(str(PHASE4_DIR / "*.json.gz"))):
        date = Path(path).stem.replace(".json", "")
        with gzip.open(path) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"WARN corrupt snapshot: {path}")
                continue
        if not isinstance(data, list):
            continue
        out[date] = {row["ticker"]: row for row in data if "ticker" in row}
    return out


def load_cumulative_pnl() -> dict:
    if not CUM_PNL_FILE.exists():
        return {}
    with open(CUM_PNL_FILE) as f:
        return json.load(f)


def load_spy_returns() -> dict[str, float]:
    """Return {YYYY-MM-DD: daily_return_pct}."""
    if not SPY_CACHE.exists():
        return {}
    with open(SPY_CACHE) as f:
        return json.load(f)


def fetch_and_cache_spy_returns(dates: list[str]) -> dict[str, float]:
    """Fetch SPY daily bars via PolygonClient and cache returns as a dict."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from ifds.data.polygon import PolygonClient
    except ImportError as e:
        print(f"WARN cannot import PolygonClient ({e}) — SPY analysis will be skipped")
        return {}

    api_key = os.environ.get("IFDS_POLYGON_API_KEY")
    if not api_key:
        print("WARN IFDS_POLYGON_API_KEY not set — SPY analysis will be skipped")
        return {}

    from datetime import date as _date, timedelta
    if not dates:
        return {}
    # Pad start by 5 calendar days so we have a prior close to compute
    # the first trading day's return.
    start = (_date.fromisoformat(min(dates)) - timedelta(days=5)).isoformat()
    end = max(dates)

    try:
        client = PolygonClient(api_key)
        bars = client.get_aggregates("SPY", start, end, timespan="day")
    except Exception as e:
        print(f"WARN PolygonClient fetch failed: {e}")
        return {}

    if not bars:
        print("WARN no SPY bars returned")
        return {}

    # Polygon aggregates: each bar is a dict with 't' (ms timestamp), 'c' (close).
    bars_sorted = sorted(bars, key=lambda b: b.get("t", 0))
    returns: dict[str, float] = {}
    prev_close: float | None = None
    for bar in bars_sorted:
        ts_ms = bar.get("t")
        close = bar.get("c")
        if ts_ms is None or close is None:
            continue
        bar_date = _date.fromtimestamp(ts_ms / 1000).isoformat()
        if prev_close is not None and prev_close > 0:
            returns[bar_date] = (float(close) - prev_close) / prev_close * 100.0
        prev_close = float(close)

    if returns:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(SPY_CACHE, "w") as f:
            json.dump(returns, f, indent=2, sort_keys=True)
        print(f"Cached {len(returns)} SPY returns to {SPY_CACHE}")
    return returns


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------


def enrich_with_snapshot(trades: list[Trade], snapshots: dict[str, dict[str, dict]]) -> None:
    """Attach flow/tech/funda sub-scores from the Phase 4 snapshot for each trade."""
    for t in trades:
        snap = snapshots.get(t.date, {}).get(t.ticker)
        if not snap:
            continue
        t.flow_subscore = sum(snap.get(f, 0) or 0 for f in FLOW_FIELDS)
        t.tech_subscore = sum(snap.get(f, 0) or 0 for f in TECH_FIELDS)
        t.funda_subscore = snap.get(FUNDA_FIELD, 0) or 0


def enrich_with_spy(trades: list[Trade], spy_returns: dict[str, float]) -> None:
    """Attach SPY daily return and excess return (beta=1.0 assumption)."""
    for t in trades:
        spy_ret = spy_returns.get(t.date)
        if spy_ret is None:
            continue
        t.spy_return_pct = spy_ret
        # Simple market-neutral excess: assume beta=1.0, no factor model
        t.excess_return_pct = t.pnl_pct - spy_ret


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


def pearson(xs: list[float], ys: list[float]) -> tuple[float, float]:
    if len(xs) < 3:
        return (float("nan"), float("nan"))
    r, p = stats.pearsonr(xs, ys)
    return (float(r), float(p))


def spearman(xs: list[float], ys: list[float]) -> tuple[float, float]:
    if len(xs) < 3:
        return (float("nan"), float("nan"))
    r, p = stats.spearmanr(xs, ys)
    return (float(r), float(p))


def score_quintiles(trades: list[Trade]) -> list[dict]:
    """Split trades into 5 quintiles by score and compute P&L stats."""
    sorted_trades = sorted(trades, key=lambda t: t.score)
    n = len(sorted_trades)
    if n < 5:
        return []
    out = []
    for q in range(5):
        lo = q * n // 5
        hi = (q + 1) * n // 5 if q < 4 else n
        bucket = sorted_trades[lo:hi]
        pnls = [t.pnl for t in bucket]
        pcts = [t.pnl_pct for t in bucket]
        wins = sum(1 for t in bucket if t.pnl > 0)
        out.append({
            "quintile": q + 1,
            "n": len(bucket),
            "score_range": f"{bucket[0].score:.1f}–{bucket[-1].score:.1f}",
            "avg_pnl": mean(pnls) if pnls else 0,
            "median_pnl": median(pnls) if pnls else 0,
            "avg_pnl_pct": mean(pcts) if pcts else 0,
            "win_rate": wins / len(bucket) * 100 if bucket else 0,
            "total_pnl": sum(pnls),
        })
    return out


def exit_type_breakdown(trades: list[Trade]) -> list[dict]:
    by_type: dict[str, list[Trade]] = defaultdict(list)
    for t in trades:
        by_type[t.exit_type].append(t)
    out = []
    for exit_type, bucket in sorted(by_type.items()):
        pnls = [t.pnl for t in bucket]
        pcts = [t.pnl_pct for t in bucket]
        wins = sum(1 for t in bucket if t.pnl > 0)
        out.append({
            "exit_type": exit_type,
            "n": len(bucket),
            "avg_pnl": mean(pnls) if pnls else 0,
            "median_pnl": median(pnls) if pnls else 0,
            "avg_pnl_pct": mean(pcts) if pcts else 0,
            "win_rate": wins / len(bucket) * 100 if bucket else 0,
            "total_pnl": sum(pnls),
        })
    return out


def win_rate_by_bucket(trades: list[Trade], bounds: list[float]) -> list[dict]:
    """Win rate for score buckets. bounds = [89, 91, 93, inf] → 3 buckets."""
    out = []
    for i in range(len(bounds) - 1):
        lo, hi = bounds[i], bounds[i + 1]
        bucket = [t for t in trades if lo <= t.score < hi]
        if not bucket:
            continue
        wins = sum(1 for t in bucket if t.pnl > 0)
        out.append({
            "range": f"{lo:.0f}–{hi:.0f}",
            "n": len(bucket),
            "win_rate": wins / len(bucket) * 100,
            "avg_pnl": mean(t.pnl for t in bucket),
            "avg_pnl_pct": mean(t.pnl_pct for t in bucket),
        })
    return out


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------


def plot_scatter(xs: list[float], ys: list[float], xlabel: str, ylabel: str,
                 title: str, path: Path) -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(xs, ys, alpha=0.5, s=20)
    ax.axhline(0, color="gray", linewidth=0.5)
    if len(xs) >= 3:
        # Linear fit
        coeffs = np.polyfit(xs, ys, 1)
        xfit = np.linspace(min(xs), max(xs), 100)
        ax.plot(xfit, np.polyval(coeffs, xfit), "r--", linewidth=1,
                label=f"slope={coeffs[0]:.3f}")
        ax.legend()
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def plot_quintile_bars(quintiles: list[dict], path: Path) -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    labels = [f"Q{q['quintile']}\n{q['score_range']}" for q in quintiles]
    avg_pnl = [q["avg_pnl"] for q in quintiles]
    win_rate = [q["win_rate"] for q in quintiles]
    ax1.bar(labels, avg_pnl, color=["C3" if v < 0 else "C2" for v in avg_pnl])
    ax1.axhline(0, color="gray", linewidth=0.5)
    ax1.set_ylabel("Average P&L ($)")
    ax1.set_title("Avg P&L by score quintile")
    ax1.grid(True, axis="y", alpha=0.3)
    ax2.bar(labels, win_rate, color="C0")
    ax2.axhline(50, color="gray", linewidth=0.5, linestyle="--")
    ax2.set_ylabel("Win rate (%)")
    ax2.set_title("Win rate by score quintile")
    ax2.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def fmt_corr(r: float, p: float) -> str:
    if r != r:  # NaN
        return "n/a"
    stars = ""
    if p < 0.01:
        stars = "**"
    elif p < 0.05:
        stars = "*"
    return f"{r:+.3f}{stars} (p={p:.3f})"


def generate_report(trades: list[Trade], snapshots: dict, cum_pnl: dict,
                    spy_returns: dict[str, float]) -> str:
    lines: list[str] = []
    lines.append("# IFDS Scoring Validation Report")
    lines.append("")
    lines.append(f"Generated: {cum_pnl.get('trading_days', '?')} trading days | "
                 f"{len(trades)} trades | "
                 f"{len(snapshots)} Phase 4 snapshots | "
                 f"SPY returns: {len(spy_returns)} days cached")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("Standalone read-only analysis. Joins Phase 4 per-ticker scores "
                 "with actual IBKR trade results to answer: **does the IFDS "
                 "scoring system generate alpha, or is P&L a function of daily "
                 "market direction only?**")
    lines.append("")
    lines.append("Significance legend: `*` = p<0.05, `**` = p<0.01")
    lines.append("")

    if not trades:
        lines.append("No trades available — aborting analysis.")
        return "\n".join(lines)

    # --- Overview
    total_pnl = sum(t.pnl for t in trades)
    wins = sum(1 for t in trades if t.pnl > 0)
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- Total trades: **{len(trades)}**")
    lines.append(f"- Total P&L: **${total_pnl:+,.2f}**")
    lines.append(f"- Win rate: **{wins / len(trades) * 100:.1f}%**")
    lines.append(f"- Avg P&L per trade: **${mean(t.pnl for t in trades):+,.2f}**")
    lines.append(f"- Median P&L: **${median(t.pnl for t in trades):+,.2f}**")
    lines.append(f"- Score range: {min(t.score for t in trades):.1f}–"
                 f"{max(t.score for t in trades):.1f}")
    lines.append("")

    # --- 1. Score → P&L correlation
    lines.append("## 1. Score → P&L Correlation")
    lines.append("")
    scores = [t.score for t in trades]
    pnls = [t.pnl for t in trades]
    pcts = [t.pnl_pct for t in trades]
    lines.append(f"- Pearson (score vs P&L $): {fmt_corr(*pearson(scores, pnls))}")
    lines.append(f"- Spearman (score vs P&L $): {fmt_corr(*spearman(scores, pnls))}")
    lines.append(f"- Pearson (score vs P&L %): {fmt_corr(*pearson(scores, pcts))}")
    lines.append("")
    plot_scatter(scores, pnls, "Score", "P&L ($)",
                 "Score vs P&L", PLOTS_DIR / "01_score_vs_pnl.png")
    lines.append("![Score vs P&L](plots/01_score_vs_pnl.png)")
    lines.append("")

    # --- 2. Quintile analysis
    lines.append("## 2. Score Quintile Analysis")
    lines.append("")
    quintiles = score_quintiles(trades)
    rows = [
        [
            f"Q{q['quintile']}",
            q["score_range"],
            str(q["n"]),
            f"${q['avg_pnl']:+,.2f}",
            f"${q['median_pnl']:+,.2f}",
            f"{q['avg_pnl_pct']:+.2f}%",
            f"{q['win_rate']:.1f}%",
            f"${q['total_pnl']:+,.2f}",
        ]
        for q in quintiles
    ]
    lines.append(md_table(
        ["Quintile", "Score range", "N", "Avg P&L", "Median P&L",
         "Avg %", "Win rate", "Total P&L"],
        rows,
    ))
    lines.append("")
    plot_quintile_bars(quintiles, PLOTS_DIR / "02_quintile_bars.png")
    lines.append("![Quintile P&L](plots/02_quintile_bars.png)")
    lines.append("")

    top_q = quintiles[-1] if quintiles else {}
    bot_q = quintiles[0] if quintiles else {}
    if top_q and bot_q:
        delta = top_q["avg_pnl"] - bot_q["avg_pnl"]
        lines.append(f"**Top–bottom spread**: ${delta:+,.2f} "
                     f"(Q5 avg ${top_q['avg_pnl']:+,.2f} vs "
                     f"Q1 avg ${bot_q['avg_pnl']:+,.2f})")
        lines.append("")

    # --- 3. Win rate by score bucket (task spec: 89–91, 91–93, 93+)
    lines.append("## 3. Win Rate by Score Bucket")
    lines.append("")
    buckets = win_rate_by_bucket(trades, [89, 91, 93, 999])
    if buckets:
        rows = [
            [b["range"], str(b["n"]), f"{b['win_rate']:.1f}%",
             f"${b['avg_pnl']:+,.2f}", f"{b['avg_pnl_pct']:+.2f}%"]
            for b in buckets
        ]
        lines.append(md_table(
            ["Score range", "N", "Win rate", "Avg P&L", "Avg %"],
            rows,
        ))
        lines.append("")

    # --- 4. Score components (reconstructed from Phase 4 snapshot)
    enriched = [t for t in trades if t.flow_subscore is not None]
    lines.append("## 4. Score Component Impact")
    lines.append("")
    lines.append(f"Snapshot join: **{len(enriched)} / {len(trades)}** trades "
                 f"enriched with Phase 4 sub-scores.")
    lines.append("")
    lines.append("Sub-score buckets reconstructed from snapshot fields:")
    lines.append(f"- **flow**: {', '.join(FLOW_FIELDS)}")
    lines.append(f"- **tech**: {', '.join(TECH_FIELDS)}")
    lines.append(f"- **funda**: `{FUNDA_FIELD}`")
    lines.append("")
    if len(enriched) >= 3:
        flows = [t.flow_subscore for t in enriched]
        techs = [t.tech_subscore for t in enriched]
        fundas = [t.funda_subscore for t in enriched]
        epnls = [t.pnl for t in enriched]
        lines.append(f"- Pearson (flow vs P&L): {fmt_corr(*pearson(flows, epnls))}")
        lines.append(f"- Pearson (tech vs P&L): {fmt_corr(*pearson(techs, epnls))}")
        lines.append(f"- Pearson (funda vs P&L): {fmt_corr(*pearson(fundas, epnls))}")
        lines.append("")
        plot_scatter(flows, epnls, "Flow subscore", "P&L ($)",
                     "Flow subscore vs P&L",
                     PLOTS_DIR / "03a_flow_vs_pnl.png")
        plot_scatter(techs, epnls, "Tech subscore", "P&L ($)",
                     "Tech subscore vs P&L",
                     PLOTS_DIR / "03b_tech_vs_pnl.png")
        plot_scatter(fundas, epnls, "Funda subscore", "P&L ($)",
                     "Funda subscore vs P&L",
                     PLOTS_DIR / "03c_funda_vs_pnl.png")
        lines.append("![Flow](plots/03a_flow_vs_pnl.png)")
        lines.append("![Tech](plots/03b_tech_vs_pnl.png)")
        lines.append("![Funda](plots/03c_funda_vs_pnl.png)")
        lines.append("")

    # --- 5. Market direction control (SPY)
    lines.append("## 5. Market Direction Control (SPY Excess Return)")
    lines.append("")
    with_spy = [t for t in trades if t.excess_return_pct is not None]
    if not with_spy:
        lines.append("⚠️  SPY returns cache is empty — cannot compute excess "
                     "returns. Run with `--fetch-spy` (requires "
                     "`IFDS_POLYGON_API_KEY`) to enable this section.")
        lines.append("")
    else:
        lines.append(f"SPY-joined: **{len(with_spy)} / {len(trades)}** trades.")
        lines.append("")
        lines.append("Excess return = trade P&L % − SPY daily return % "
                     "(beta assumption: 1.0)")
        lines.append("")
        scores_e = [t.score for t in with_spy]
        excess = [t.excess_return_pct for t in with_spy]
        raw = [t.pnl_pct for t in with_spy]
        lines.append(f"- Pearson (score vs raw P&L%): "
                     f"{fmt_corr(*pearson(scores_e, raw))}")
        lines.append(f"- Pearson (score vs **excess**): "
                     f"{fmt_corr(*pearson(scores_e, excess))}")
        lines.append(f"- Spearman (score vs **excess**): "
                     f"{fmt_corr(*spearman(scores_e, excess))}")
        lines.append("")
        plot_scatter(scores_e, excess,
                     "Score", "Excess return % (vs SPY)",
                     "Score vs market-neutral excess",
                     PLOTS_DIR / "04_score_vs_excess.png")
        lines.append("![Score vs excess](plots/04_score_vs_excess.png)")
        lines.append("")
        # Interpretation hint
        raw_r, _ = pearson(scores_e, raw)
        ex_r, _ = pearson(scores_e, excess)
        if raw_r == raw_r and ex_r == ex_r:
            if abs(ex_r) > 0.1:
                lines.append("→ Score correlates with market-neutral excess return. "
                             "**Evidence of alpha.**")
            elif abs(raw_r) > 0.1 and abs(ex_r) < 0.05:
                lines.append("→ Score correlates with raw P&L but the correlation "
                             "**disappears after SPY removal**. The scoring is "
                             "mirroring market direction, not generating alpha.")
            else:
                lines.append("→ Score does not meaningfully correlate with P&L "
                             "before or after SPY removal — inconclusive or no edge.")
            lines.append("")

    # --- 6. Exit type breakdown
    lines.append("## 6. Exit Type Breakdown")
    lines.append("")
    exits = exit_type_breakdown(trades)
    rows = [
        [
            e["exit_type"], str(e["n"]),
            f"${e['avg_pnl']:+,.2f}",
            f"${e['median_pnl']:+,.2f}",
            f"{e['avg_pnl_pct']:+.2f}%",
            f"${e['total_pnl']:+,.2f}",
        ]
        for e in exits
    ]
    lines.append(md_table(
        ["Exit type", "N", "Avg P&L", "Median P&L", "Avg %", "Total P&L"],
        rows,
    ))
    lines.append("")

    # --- Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Sample size: **{len(trades)} trades** over "
                 f"{len(set(t.date for t in trades))} trading days")
    lines.append(f"- Total P&L: **${total_pnl:+,.2f}** "
                 f"({total_pnl / 100_000 * 100:+.2f}% of $100k)")
    lines.append(f"- Win rate: **{wins / len(trades) * 100:.1f}%**")
    if quintiles:
        lines.append(f"- Q5–Q1 spread: **${quintiles[-1]['avg_pnl'] - quintiles[0]['avg_pnl']:+,.2f}**")
    lines.append("")
    lines.append("---")
    lines.append("*Generated by `scripts/analysis/scoring_validation.py`*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="IFDS scoring validation & multiplier impact analysis"
    )
    parser.add_argument(
        "--fetch-spy", action="store_true",
        help="Fetch SPY daily returns via Polygon and update the cache",
    )
    args = parser.parse_args()

    print(f"Loading trades from {TRADES_DIR}...")
    trades = load_trades()
    print(f"  {len(trades)} trades loaded")

    print(f"Loading Phase 4 snapshots from {PHASE4_DIR}...")
    snapshots = load_phase4_snapshots()
    print(f"  {len(snapshots)} snapshots loaded")

    print(f"Loading cumulative P&L from {CUM_PNL_FILE}...")
    cum_pnl = load_cumulative_pnl()

    dates = sorted({t.date for t in trades})

    if args.fetch_spy:
        print("Fetching SPY daily returns via Polygon...")
        spy_returns = fetch_and_cache_spy_returns(dates)
    else:
        spy_returns = load_spy_returns()
        print(f"  {len(spy_returns)} SPY returns loaded from cache")

    print("Enriching trades with snapshot sub-scores...")
    enrich_with_snapshot(trades, snapshots)
    enriched_count = sum(1 for t in trades if t.flow_subscore is not None)
    print(f"  {enriched_count} / {len(trades)} trades enriched")

    if spy_returns:
        enrich_with_spy(trades, spy_returns)
        with_spy_count = sum(1 for t in trades if t.excess_return_pct is not None)
        print(f"  {with_spy_count} / {len(trades)} trades joined with SPY")

    print("Generating report...")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = generate_report(trades, snapshots, cum_pnl, spy_returns)
    with open(REPORT_PATH, "w") as f:
        f.write(report)
    print(f"Report written to {REPORT_PATH}")
    print(f"Plots written to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
