#!/usr/bin/env python3
"""IFDS — Flow Sub-Component Decomposition Analysis.

The aggregated flow_score is a sum of 6 sub-components. This script
asks: which individual sub-component is actually predictive of realized
P&L? The output informs the next iteration of scoring weights.

Inputs:
    state/phase4_snapshots/*.json.gz   — per-ticker sub-component scores
    scripts/paper_trading/logs/trades_*.csv — fill + exit P&L

Output:
    docs/analysis/flow-decomposition.md — per-component correlation tables
    docs/analysis/plots/flow_*.png       — scatter per component

Usage:
    python scripts/analysis/flow_decomposition.py
    python scripts/analysis/flow_decomposition.py --since 2026-04-13  # BC23 only
"""
from __future__ import annotations

import argparse
import csv
import glob
import gzip
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, median

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy import stats
except ImportError as e:
    print(f"ERROR: missing analysis dependency ({e}). "
          f"pip install matplotlib scipy numpy", file=sys.stderr)
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASE4_DIR = PROJECT_ROOT / "state" / "phase4_snapshots"
TRADES_DIR = PROJECT_ROOT / "scripts" / "paper_trading" / "logs"
OUT_DIR = PROJECT_ROOT / "docs" / "analysis"
PLOTS_DIR = OUT_DIR / "plots"

# Individual flow sub-components present in the Phase 4 snapshot.
# squat_bar is a boolean; include but skip in correlation.
FLOW_COMPONENTS = [
    "rvol_score",
    "dp_pct_score",
    "pcr_score",
    "otm_score",
    "block_trade_score",
    "buy_pressure_score",
]


@dataclass
class TradeJoin:
    date: str
    ticker: str
    pnl: float
    pnl_pct: float
    exit_type: str
    components: dict[str, float] = field(default_factory=dict)


def load_trades(since: str | None = None) -> list[TradeJoin]:
    out: list[TradeJoin] = []
    for path in sorted(glob.glob(str(TRADES_DIR / "trades_*.csv"))):
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                if since and row["date"] < since:
                    continue
                try:
                    out.append(TradeJoin(
                        date=row["date"],
                        ticker=row["ticker"],
                        pnl=float(row["pnl"]),
                        pnl_pct=float(row["pnl_pct"]),
                        exit_type=row["exit_type"],
                    ))
                except (KeyError, ValueError):
                    continue
    return out


def load_snapshot_components() -> dict[tuple[str, str], dict[str, float]]:
    """Return {(date, ticker): {component: score}} from all snapshots."""
    out: dict[tuple[str, str], dict[str, float]] = {}
    for path in sorted(glob.glob(str(PHASE4_DIR / "*.json.gz"))):
        date = Path(path).stem.replace(".json", "")
        with gzip.open(path) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
        if not isinstance(data, list):
            continue
        for row in data:
            ticker = row.get("ticker")
            if not ticker:
                continue
            comps: dict[str, float] = {}
            for c in FLOW_COMPONENTS:
                val = row.get(c)
                if val is None:
                    continue
                try:
                    comps[c] = float(val)
                except (TypeError, ValueError):
                    continue
            # squat_bar bonus: treat boolean as 0/1 multiplied by a notional +10
            squat = row.get("squat_bar")
            if squat is not None:
                comps["squat_bar"] = 10.0 if bool(squat) else 0.0
            out[(date, ticker)] = comps
    return out


def enrich_trades(trades: list[TradeJoin],
                  snapshots: dict[tuple[str, str], dict[str, float]]) -> int:
    enriched = 0
    for t in trades:
        comps = snapshots.get((t.date, t.ticker))
        if comps:
            t.components = comps
            enriched += 1
    return enriched


def pearson(xs: list[float], ys: list[float]) -> tuple[float, float]:
    if len(xs) < 3 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return (float("nan"), float("nan"))
    r, p = stats.pearsonr(xs, ys)
    return (float(r), float(p))


def spearman(xs: list[float], ys: list[float]) -> tuple[float, float]:
    if len(xs) < 3 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return (float("nan"), float("nan"))
    r, p = stats.spearmanr(xs, ys)
    return (float(r), float(p))


def quintile_stats(trades: list[TradeJoin], component: str) -> list[dict]:
    """Score quintiles for a single sub-component."""
    valid = [t for t in trades if component in t.components]
    if len(valid) < 5:
        return []
    sorted_trades = sorted(valid, key=lambda t: t.components[component])
    n = len(sorted_trades)
    out = []
    for q in range(5):
        lo = q * n // 5
        hi = (q + 1) * n // 5 if q < 4 else n
        bucket = sorted_trades[lo:hi]
        if not bucket:
            continue
        pnls = [t.pnl for t in bucket]
        wins = sum(1 for t in bucket if t.pnl > 0)
        out.append({
            "quintile": q + 1,
            "range": f"{bucket[0].components[component]:.1f}–{bucket[-1].components[component]:.1f}",
            "n": len(bucket),
            "avg_pnl": mean(pnls),
            "win_rate": wins / len(bucket) * 100,
        })
    return out


def fmt_corr(r: float, p: float) -> str:
    if r != r:
        return "n/a"
    stars = "**" if p < 0.01 else "*" if p < 0.05 else ""
    return f"{r:+.3f}{stars} (p={p:.3f})"


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def plot_component_scatter(trades: list[TradeJoin], component: str,
                           out_path: Path) -> None:
    valid = [t for t in trades if component in t.components]
    if len(valid) < 3:
        return
    xs = [t.components[component] for t in valid]
    ys = [t.pnl for t in valid]
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(xs, ys, alpha=0.5, s=20)
    ax.axhline(0, color="gray", linewidth=0.5)
    if len(set(xs)) >= 2:
        coeffs = np.polyfit(xs, ys, 1)
        xfit = np.linspace(min(xs), max(xs), 100)
        ax.plot(xfit, np.polyval(coeffs, xfit), "r--", linewidth=1,
                label=f"slope={coeffs[0]:.2f}")
        ax.legend()
    ax.set_xlabel(component)
    ax.set_ylabel("P&L ($)")
    ax.set_title(f"{component} vs P&L")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=100)
    plt.close(fig)


def generate_report(trades: list[TradeJoin], enriched: int,
                    since: str | None) -> str:
    lines: list[str] = []
    lines.append("# IFDS Flow Sub-Component Decomposition")
    lines.append("")
    scope = f"since {since}" if since else "all available history"
    lines.append(f"Scope: {scope} | Trades: {len(trades)} | "
                 f"Enriched with snapshot: {enriched}")
    lines.append("")
    lines.append("Each flow sub-component is correlated against realized P&L "
                 "to identify which ones actually predict outcomes.")
    lines.append("")
    lines.append("Significance: `*` = p<0.05, `**` = p<0.01")
    lines.append("")

    enriched_trades = [t for t in trades if t.components]
    if not enriched_trades:
        lines.append("No enriched trades — unable to decompose.")
        return "\n".join(lines)

    # --- Correlation table ---
    lines.append("## 1. Per-Component Correlation with P&L")
    lines.append("")
    all_components = FLOW_COMPONENTS + ["squat_bar"]
    corr_rows: list[list[str]] = []
    for c in all_components:
        valid = [t for t in enriched_trades if c in t.components]
        if len(valid) < 3:
            corr_rows.append([c, str(len(valid)), "n/a", "n/a", "n/a"])
            continue
        xs = [t.components[c] for t in valid]
        ys = [t.pnl for t in valid]
        pr = pearson(xs, ys)
        sr = spearman(xs, ys)
        mean_x = mean(xs)
        corr_rows.append([
            c, str(len(valid)), fmt_corr(*pr), fmt_corr(*sr),
            f"{mean_x:.2f}",
        ])
    lines.append(md_table(
        ["Component", "N", "Pearson", "Spearman", "Avg score"],
        corr_rows,
    ))
    lines.append("")

    # --- Quintile analysis per component ---
    lines.append("## 2. Quintile Analysis per Component")
    lines.append("")
    for c in FLOW_COMPONENTS:
        qs = quintile_stats(enriched_trades, c)
        if not qs:
            continue
        lines.append(f"### {c}")
        lines.append("")
        rows = [
            [f"Q{q['quintile']}", q["range"], str(q["n"]),
             f"${q['avg_pnl']:+,.2f}", f"{q['win_rate']:.0f}%"]
            for q in qs
        ]
        lines.append(md_table(
            ["Quintile", "Range", "N", "Avg P&L", "Win rate"],
            rows,
        ))
        lines.append("")
        if qs:
            spread = qs[-1]["avg_pnl"] - qs[0]["avg_pnl"]
            lines.append(f"**Q5–Q1 spread**: ${spread:+,.2f}")
            lines.append("")

    # --- Scatter plots ---
    lines.append("## 3. Scatter Plots")
    lines.append("")
    for c in FLOW_COMPONENTS:
        out_path = PLOTS_DIR / f"flow_{c}.png"
        plot_component_scatter(enriched_trades, c, out_path)
        if out_path.exists():
            lines.append(f"![{c}](plots/flow_{c}.png)")
            lines.append("")

    # --- Interpretation hints ---
    lines.append("## 4. Interpretation Hints")
    lines.append("")
    lines.append("- **Positive, significant Pearson (p<0.05)** → keep / emphasize")
    lines.append("- **Negative correlation** → consider removing or inverting")
    lines.append("- **High N, r≈0** → noise; consider dropping")
    lines.append("- **Low N but strong signal** → monitor for more data")
    lines.append("")
    lines.append("---")
    lines.append("*Generated by `scripts/analysis/flow_decomposition.py`*")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Flow sub-component decomposition analysis"
    )
    parser.add_argument(
        "--since", metavar="YYYY-MM-DD",
        help="Filter trades to date >= value",
    )
    parser.add_argument(
        "--output", default="flow-decomposition.md",
        help="Output filename (relative to docs/analysis/)",
    )
    args = parser.parse_args()

    print(f"Loading trades...")
    trades = load_trades(since=args.since)
    print(f"  {len(trades)} trades loaded")

    print(f"Loading Phase 4 snapshots...")
    snapshots = load_snapshot_components()
    print(f"  {len(snapshots)} (date, ticker) entries across all snapshots")

    enriched = enrich_trades(trades, snapshots)
    print(f"  {enriched} / {len(trades)} trades enriched with sub-components")

    print("Generating report...")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = generate_report(trades, enriched, args.since)
    out_path = OUT_DIR / args.output
    with open(out_path, "w") as f:
        f.write(report)
    print(f"Report: {out_path}")
    print(f"Plots:  {PLOTS_DIR}")


if __name__ == "__main__":
    main()
