"""Ticker Universe Liquidity Audit v2 — Distribution-first.

Instead of arbitrary A/B/C/D thresholds, show the actual distributions:
- How many tickers appear on N days (persistence)
- Of those, how many have DP coverage X%
- Of those, how many have options coverage Y%

Output: docs/analysis/ticker-liquidity-audit-v2.md
"""

from __future__ import annotations

import csv
import gzip
import json
import statistics
from collections import defaultdict
from pathlib import Path

SNAPSHOT_DIR = Path("state/phase4_snapshots")
OUTPUT_MD = Path("docs/analysis/ticker-liquidity-audit-v2.md")
OUTPUT_CSV = Path("docs/analysis/ticker-liquidity-audit-v2.csv")


def load_all_snapshots():
    files = sorted(SNAPSHOT_DIR.glob("*.json.gz"))
    snaps = []
    for f in files:
        with gzip.open(f, "rt", encoding="utf-8") as fp:
            records = json.load(fp)
        snaps.append((f.stem.replace(".json", ""), records))
    return snaps


def aggregate(snaps):
    stats = defaultdict(lambda: {
        "days_seen": 0,
        "sector": None,
        "dp_days": 0,
        "dp_pct_values": [],
        "block_counts": [],
        "pcr_days": 0,
        "combined_scores": [],
    })
    for _, records in snaps:
        for r in records:
            t = r["ticker"]
            s = stats[t]
            s["days_seen"] += 1
            if s["sector"] is None:
                s["sector"] = r.get("sector", "Unknown")
            dp_pct = r.get("dark_pool_pct", 0) or 0
            blocks = r.get("block_trade_count", 0) or 0
            if dp_pct > 0 or blocks > 0:
                s["dp_days"] += 1
                if dp_pct > 0:
                    s["dp_pct_values"].append(dp_pct)
                s["block_counts"].append(blocks)
            if r.get("pcr") is not None:
                s["pcr_days"] += 1
            cs = r.get("combined_score", 0)
            if cs > 0:
                s["combined_scores"].append(cs)
    return dict(stats)


def bucket_counts(values, bins):
    """Count values into bins. bins = list of upper bounds."""
    counts = [0] * len(bins)
    for v in values:
        for i, upper in enumerate(bins):
            if v <= upper:
                counts[i] += 1
                break
        else:
            counts[-1] += 1
    return counts


def main():
    snaps = load_all_snapshots()
    total_days = len(snaps)
    print(f"Loaded {total_days} snapshots, {sum(len(r) for _, r in snaps)} records")

    stats = aggregate(snaps)
    total_tickers = len(stats)
    print(f"Unique tickers: {total_tickers}")

    # Persistence histogram
    persistence = [s["days_seen"] for s in stats.values()]
    print(f"\n=== Persistence (days seen out of {total_days}) ===")
    bins = [1, 3, 5, 10, 15, 20, 25, 30, 35, total_days]
    bin_counts = bucket_counts(persistence, bins)
    labels = ["1 day", "2-3", "4-5", "6-10", "11-15", "16-20", "21-25",
              "26-30", "31-35", f"36-{total_days}"]
    for lbl, c in zip(labels, bin_counts):
        pct = c / total_tickers * 100
        bar = "█" * int(pct / 2)
        print(f"  {lbl:>10}  {c:5d}  ({pct:5.1f}%)  {bar}")

    # Among persistent tickers (≥10 days), DP coverage distribution
    persistent = [(t, s) for t, s in stats.items() if s["days_seen"] >= 10]
    print(f"\n=== DP Coverage — tickers with ≥10 days ({len(persistent)} total) ===")
    dp_cov = [s["dp_days"] / s["days_seen"] for _, s in persistent]
    cov_bins = [0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
    cov_labels = ["0-10%", "10-25%", "25-50%", "50-75%", "75-90%", "90-100%"]
    counts = bucket_counts(dp_cov, cov_bins)
    for lbl, c in zip(cov_labels, counts):
        pct = c / len(persistent) * 100 if persistent else 0
        bar = "█" * int(pct / 2)
        print(f"  {lbl:>10}  {c:5d}  ({pct:5.1f}%)  {bar}")

    # Options coverage
    print(f"\n=== Options Coverage — tickers with ≥10 days ===")
    opt_cov = [s["pcr_days"] / s["days_seen"] for _, s in persistent]
    counts = bucket_counts(opt_cov, cov_bins)
    for lbl, c in zip(cov_labels, counts):
        pct = c / len(persistent) * 100 if persistent else 0
        bar = "█" * int(pct / 2)
        print(f"  {lbl:>10}  {c:5d}  ({pct:5.1f}%)  {bar}")

    # The intersection: top candidates
    print(f"\n=== Top 30 institutional-data tickers ===")
    print("Sorted by: days_seen × dp_coverage × opt_coverage")
    scored = []
    for t, s in stats.items():
        if s["days_seen"] < 5:
            continue
        dp_c = s["dp_days"] / s["days_seen"]
        opt_c = s["pcr_days"] / s["days_seen"]
        score = s["days_seen"] * dp_c * opt_c
        scored.append((score, t, s, dp_c, opt_c))
    scored.sort(reverse=True)

    print(f"  {'Ticker':>6}  {'Sector':<18}  {'Days':>4}  {'DP%':>5}  {'Opt%':>5}  {'AvgDP':>5}  {'AvgBlocks':>9}")
    for score, t, s, dp_c, opt_c in scored[:30]:
        avg_dp = statistics.mean(s["dp_pct_values"]) if s["dp_pct_values"] else 0
        avg_blk = statistics.mean(s["block_counts"]) if s["block_counts"] else 0
        sector = (s["sector"] or "?")[:18]
        print(f"  {t:>6}  {sector:<18}  {s['days_seen']:>4}  "
              f"{dp_c*100:>4.0f}%  {opt_c*100:>4.0f}%  {avg_dp:>4.0f}%  {avg_blk:>9.1f}")

    # Write markdown
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("# Ticker Universe Liquidity Audit v2 (Distribution-first)\n\n")
        f.write(f"**Dataset:** {total_days} Phase 4 snapshots "
                f"({snaps[0][0]} → {snaps[-1][0]}), ")
        f.write(f"{sum(len(r) for _, r in snaps)} total records, ")
        f.write(f"{total_tickers} unique tickers.\n\n")
        f.write(f"**Average passes per ticker:** "
                f"{sum(len(r) for _, r in snaps) / total_tickers:.1f} "
                f"(out of {total_days} possible days)\n\n")

        f.write("## Key finding\n\n")
        f.write("The Phase 4 ticker universe is **highly rotational**: most tickers "
                "appear only on a few days, not consistently across weeks. "
                "This alone is worth discussing for the scoring design.\n\n")

        f.write("## Persistence histogram (days seen out of {})\n\n".format(total_days))
        f.write("| Days seen | Ticker count | % of universe |\n|---|---|---|\n")
        for lbl, c in zip(labels, bin_counts):
            pct = c / total_tickers * 100
            f.write(f"| {lbl} | {c} | {pct:.1f}% |\n")

        f.write("\n## DP Coverage — among persistent tickers (≥10 days seen, "
                f"{len(persistent)} total)\n\n")
        f.write("| DP coverage bucket | Ticker count | % |\n|---|---|---|\n")
        counts = bucket_counts(dp_cov, cov_bins)
        for lbl, c in zip(cov_labels, counts):
            pct = c / len(persistent) * 100 if persistent else 0
            f.write(f"| {lbl} | {c} | {pct:.1f}% |\n")

        f.write("\n## Options Coverage — among persistent tickers\n\n")
        f.write("| Opt coverage bucket | Ticker count | % |\n|---|---|---|\n")
        counts = bucket_counts(opt_cov, cov_bins)
        for lbl, c in zip(cov_labels, counts):
            pct = c / len(persistent) * 100 if persistent else 0
            f.write(f"| {lbl} | {c} | {pct:.1f}% |\n")

        f.write("\n## Top 50 institutional-data tickers\n\n")
        f.write("Ranked by `days_seen × dp_coverage × opt_coverage`. "
                "These are the tickers where the Phase 4 pipeline "
                "consistently produces both dark pool and options data.\n\n")
        f.write("| # | Ticker | Sector | Days | DP% | Opt% | Avg DP | Avg Blocks | Avg Score |\n")
        f.write("|---|--------|--------|------|-----|------|--------|------------|-----------|\n")
        for i, (score, t, s, dp_c, opt_c) in enumerate(scored[:50], 1):
            avg_dp = statistics.mean(s["dp_pct_values"]) if s["dp_pct_values"] else 0
            avg_blk = statistics.mean(s["block_counts"]) if s["block_counts"] else 0
            avg_cs = statistics.mean(s["combined_scores"]) if s["combined_scores"] else 0
            f.write(f"| {i} | {t} | {s['sector']} | {s['days_seen']} | "
                    f"{dp_c*100:.0f}% | {opt_c*100:.0f}% | "
                    f"{avg_dp:.0f}% | {avg_blk:.1f} | {avg_cs:.1f} |\n")

    # CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "sector", "days_seen", "dp_days", "dp_coverage",
                    "pcr_days", "opt_coverage", "avg_dp_pct", "avg_block_count",
                    "avg_combined_score", "composite_score"])
        for score, t, s, dp_c, opt_c in scored:
            avg_dp = statistics.mean(s["dp_pct_values"]) if s["dp_pct_values"] else 0
            avg_blk = statistics.mean(s["block_counts"]) if s["block_counts"] else 0
            avg_cs = statistics.mean(s["combined_scores"]) if s["combined_scores"] else 0
            w.writerow([t, s["sector"], s["days_seen"], s["dp_days"],
                        f"{dp_c:.3f}", s["pcr_days"], f"{opt_c:.3f}",
                        f"{avg_dp:.2f}", f"{avg_blk:.1f}", f"{avg_cs:.1f}",
                        f"{score:.2f}"])

    print(f"\nReport: {OUTPUT_MD}")
    print(f"CSV:    {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
