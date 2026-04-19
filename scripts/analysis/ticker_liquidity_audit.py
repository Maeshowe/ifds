"""Ticker Universe Liquidity Audit (First Iteration).

Scans state/phase4_snapshots/*.json.gz and categorizes tickers
by institutional data availability and stability.

LIMITATIONS:
- Current snapshot does NOT persist dp_volume ($), total_volume,
  venue_entropy, or GEX metrics (net_gex, call_wall, zero_gamma).
- Therefore this audit measures DATA PRESENCE + STABILITY only,
  not dollar-weighted institutional signal strength.
- A follow-up snapshot enrichment task is planned for W18+.

Output: docs/analysis/ticker-liquidity-audit.md
        docs/analysis/ticker-liquidity-audit.csv  (raw per-ticker stats)
"""

from __future__ import annotations

import csv
import gzip
import json
import statistics
from collections import defaultdict
from pathlib import Path

SNAPSHOT_DIR = Path("state/phase4_snapshots")
OUTPUT_MD = Path("docs/analysis/ticker-liquidity-audit.md")
OUTPUT_CSV = Path("docs/analysis/ticker-liquidity-audit.csv")


def load_all_snapshots() -> list[tuple[str, list[dict]]]:
    """Load every snapshot file, return list of (date_str, records)."""
    files = sorted(SNAPSHOT_DIR.glob("*.json.gz"))
    snapshots = []
    for f in files:
        date_str = f.stem.replace(".json", "")
        try:
            with gzip.open(f, "rt", encoding="utf-8") as fp:
                records = json.load(fp)
            snapshots.append((date_str, records))
        except Exception as e:
            print(f"  [WARN] Could not read {f.name}: {e}")
    return snapshots


def aggregate_per_ticker(snapshots: list[tuple[str, list[dict]]]) -> dict[str, dict]:
    """Aggregate stats per ticker across all snapshots."""
    stats = defaultdict(lambda: {
        "days_seen": 0,
        "sector": None,
        "dp_pct_values": [],        # dark_pool_pct on days when it was >0
        "dp_days": 0,                # days with any DP data
        "block_counts": [],
        "pcr_values": [],
        "pcr_days": 0,               # days with PCR data (options chain present)
        "otm_values": [],
        "combined_scores": [],
    })

    for date_str, records in snapshots:
        for r in records:
            t = r["ticker"]
            s = stats[t]
            s["days_seen"] += 1
            if s["sector"] is None:
                s["sector"] = r.get("sector", "Unknown")

            # DP presence: dark_pool_pct > 0 OR block_trade_count > 0
            dp_pct = r.get("dark_pool_pct", 0) or 0
            blocks = r.get("block_trade_count", 0) or 0
            if dp_pct > 0 or blocks > 0:
                s["dp_days"] += 1
                if dp_pct > 0:
                    s["dp_pct_values"].append(dp_pct)
                s["block_counts"].append(blocks)

            # Options presence: pcr not None
            pcr = r.get("pcr")
            if pcr is not None:
                s["pcr_days"] += 1
                s["pcr_values"].append(pcr)
                otm = r.get("otm_call_ratio")
                if otm is not None:
                    s["otm_values"].append(otm)

            cs = r.get("combined_score", 0)
            if cs > 0:
                s["combined_scores"].append(cs)

    return dict(stats)


def categorize(stats: dict, total_days: int) -> str:
    """Classify ticker into A/B/C/D based on coverage + stability."""
    days = stats["days_seen"]
    if days == 0:
        return "D"

    dp_coverage = stats["dp_days"] / days
    opt_coverage = stats["pcr_days"] / days

    dp_pct_stability = 0.0
    if len(stats["dp_pct_values"]) >= 5:
        mean = statistics.mean(stats["dp_pct_values"])
        std = statistics.stdev(stats["dp_pct_values"])
        # Coefficient of variation: lower = more stable
        dp_pct_stability = (std / mean) if mean > 0 else 999.0

    # Coverage over total calendar: appears in >=50% of snapshots = persistent
    persistence = days / total_days

    # Category logic
    if (dp_coverage >= 0.8 and opt_coverage >= 0.8 and
        persistence >= 0.5 and dp_pct_stability < 1.0):
        return "A"  # Signal-rich: stable DP + options + persistent
    if (dp_coverage >= 0.5 and opt_coverage >= 0.5 and persistence >= 0.3):
        return "B"  # Partial: one strong, other present
    if (dp_coverage >= 0.2 or opt_coverage >= 0.2):
        return "C"  # Noisy: intermittent signal
    return "D"      # Unusable: rare appearance


def write_markdown(per_ticker: dict, total_days: int, snapshot_dates: list[str]) -> None:
    """Write human-readable markdown report."""
    cats = defaultdict(list)
    for t, s in per_ticker.items():
        s["_category"] = categorize(s, total_days)
        cats[s["_category"]].append(t)

    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(f"# Ticker Universe Liquidity Audit (First Iteration)\n\n")
        f.write(f"**Generated:** from {total_days} snapshots ")
        f.write(f"({snapshot_dates[0]} → {snapshot_dates[-1]})\n")
        f.write(f"**Unique tickers seen:** {len(per_ticker)}\n\n")
        f.write("## Limitation\n\n")
        f.write("This audit measures **data presence + stability** only. ")
        f.write("Dollar-weighted signal strength (dp_volume, venue_entropy, GEX metrics) ")
        f.write("is NOT captured because the Phase 4 snapshot does not currently persist these fields. ")
        f.write("See `docs/tasks/2026-04-XX-phase4-snapshot-enrichment.md` for the follow-up task.\n\n")

        f.write("## Category Distribution\n\n")
        f.write("| Category | Meaning | Ticker Count | % of Universe |\n")
        f.write("|----------|---------|--------------|---------------|\n")
        total = len(per_ticker)
        for cat in ["A", "B", "C", "D"]:
            n = len(cats[cat])
            pct = (n / total * 100) if total else 0
            meaning = {
                "A": "Signal-rich: stable DP + options + persistent",
                "B": "Partial: one signal strong, other present",
                "C": "Noisy: intermittent signal",
                "D": "Unusable: rare appearance",
            }[cat]
            f.write(f"| **{cat}** | {meaning} | {n} | {pct:.1f}% |\n")
        f.write("\n")

        f.write("## Category A — Top 50 by persistence\n\n")
        f.write("Tickers that consistently produce institutional data, "
                "sorted by number of days seen.\n\n")
        a_sorted = sorted(cats["A"],
                          key=lambda t: per_ticker[t]["days_seen"],
                          reverse=True)[:50]
        f.write("| Ticker | Sector | Days Seen | DP Coverage | Opt Coverage | Avg DP% | Avg Blocks |\n")
        f.write("|--------|--------|-----------|-------------|--------------|---------|------------|\n")
        for t in a_sorted:
            s = per_ticker[t]
            days = s["days_seen"]
            dp_cov = s["dp_days"] / days if days else 0
            opt_cov = s["pcr_days"] / days if days else 0
            avg_dp = statistics.mean(s["dp_pct_values"]) if s["dp_pct_values"] else 0
            avg_blk = statistics.mean(s["block_counts"]) if s["block_counts"] else 0
            f.write(f"| {t} | {s['sector']} | {days} | "
                    f"{dp_cov:.0%} | {opt_cov:.0%} | {avg_dp:.1f}% | {avg_blk:.1f} |\n")
        f.write("\n")

        f.write("## Category D — Sample of 30\n\n")
        f.write("Tickers where the Phase 4 filter passed them at least once, "
                "but institutional data is essentially absent.\n\n")
        d_sample = sorted(cats["D"],
                          key=lambda t: per_ticker[t]["days_seen"],
                          reverse=True)[:30]
        f.write("| Ticker | Sector | Days Seen | DP Days | Opt Days |\n")
        f.write("|--------|--------|-----------|---------|----------|\n")
        for t in d_sample:
            s = per_ticker[t]
            f.write(f"| {t} | {s['sector']} | "
                    f"{s['days_seen']} | {s['dp_days']} | {s['pcr_days']} |\n")
        f.write("\n")

        f.write("## Sector Distribution — Category A\n\n")
        sec_counts = defaultdict(int)
        for t in cats["A"]:
            sec_counts[per_ticker[t]["sector"]] += 1
        f.write("| Sector | Count |\n|--------|-------|\n")
        for sec, cnt in sorted(sec_counts.items(), key=lambda x: -x[1]):
            f.write(f"| {sec} | {cnt} |\n")
        f.write("\n")

        f.write("## Recommendation\n\n")
        n_a = len(cats["A"])
        n_ab = n_a + len(cats["B"])
        f.write(f"The **Institutional Relevance Filter** for BC24 should consider "
                f"restricting the scoring universe to **Category A + B** ({n_ab} tickers) "
                f"from the current ~1700-1800 Phase 2 universe. "
                f"Category C/D tickers add noise to the scoring without providing ")
        f.write("reliable institutional signal.\n\n")
        f.write("Next step: extend snapshot enrichment to capture dp_volume ($), "
                "venue_entropy, and GEX metrics → enables dollar-weighted re-categorization "
                "in W18-W19.\n")


def write_csv(per_ticker: dict) -> None:
    """Write raw per-ticker stats as CSV."""
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "sector", "category", "days_seen",
                    "dp_days", "dp_coverage", "pcr_days", "opt_coverage",
                    "avg_dp_pct", "dp_pct_cv", "avg_block_count",
                    "avg_pcr", "avg_combined_score"])
        for t, s in sorted(per_ticker.items()):
            days = s["days_seen"]
            dp_cov = s["dp_days"] / days if days else 0
            opt_cov = s["pcr_days"] / days if days else 0
            avg_dp = statistics.mean(s["dp_pct_values"]) if s["dp_pct_values"] else 0
            dp_cv = 0
            if len(s["dp_pct_values"]) >= 2:
                mean = statistics.mean(s["dp_pct_values"])
                std = statistics.stdev(s["dp_pct_values"])
                dp_cv = (std / mean) if mean > 0 else 0
            avg_blk = statistics.mean(s["block_counts"]) if s["block_counts"] else 0
            avg_pcr = statistics.mean(s["pcr_values"]) if s["pcr_values"] else 0
            avg_cs = statistics.mean(s["combined_scores"]) if s["combined_scores"] else 0
            w.writerow([t, s["sector"], s.get("_category", "?"),
                        days, s["dp_days"], f"{dp_cov:.2f}",
                        s["pcr_days"], f"{opt_cov:.2f}",
                        f"{avg_dp:.2f}", f"{dp_cv:.2f}", f"{avg_blk:.1f}",
                        f"{avg_pcr:.3f}", f"{avg_cs:.1f}"])


def main() -> None:
    print("Loading Phase 4 snapshots...")
    snapshots = load_all_snapshots()
    if not snapshots:
        print("  ERROR: No snapshots found in", SNAPSHOT_DIR)
        return
    total_days = len(snapshots)
    dates = [d for d, _ in snapshots]
    total_records = sum(len(r) for _, r in snapshots)
    print(f"  Loaded {total_days} snapshots ({dates[0]} → {dates[-1]}), "
          f"{total_records} total records")

    print("Aggregating per-ticker stats...")
    per_ticker = aggregate_per_ticker(snapshots)
    print(f"  Unique tickers: {len(per_ticker)}")

    print("Categorizing + writing reports...")
    write_markdown(per_ticker, total_days, dates)
    write_csv(per_ticker)

    # Console summary
    cats = defaultdict(int)
    for s in per_ticker.values():
        cats[s.get("_category", "?")] += 1
    total = len(per_ticker)
    print("\n=== Category Distribution ===")
    for cat in ["A", "B", "C", "D"]:
        n = cats[cat]
        pct = (n / total * 100) if total else 0
        print(f"  {cat}: {n:4d} tickers ({pct:5.1f}%)")
    print()
    print(f"Markdown report: {OUTPUT_MD}")
    print(f"CSV raw data:    {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
