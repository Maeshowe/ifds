#!/usr/bin/env python3
"""MID vs IFDS — Offline Sector Rotation Comparison.

Reads:
- ``state/mid_bundles/YYYY-MM-DD.json.gz`` — MID daily bundle (etf_xray.sectors)
- ``state/phase4_snapshots/YYYY-MM-DD.json.gz`` — IFDS Phase 4 (sector aggregation)

For each day in the requested window, it produces a tabular comparison:
which sectors did each system favor, where did they agree, and where
did they disagree. The forward-return scoring (who was "right") is
left out of this first iteration — it requires a Polygon adapter call
chain. The current goal is a smoke check + manual review.

Usage:
    python scripts/analysis/mid_vs_ifds_sector_comparison.py \\
        --start 2026-04-27 --end 2026-04-29 \\
        --output docs/analysis/mid-vs-ifds-sectors-W18-wednesday-check.md

If --output is omitted, the report is printed to stdout.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MID_BUNDLES_DIR = PROJECT_ROOT / "state" / "mid_bundles"
PHASE4_DIR = PROJECT_ROOT / "state" / "phase4_snapshots"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _load_gz_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def load_mid_sectors(target: date) -> list[dict]:
    """Extract bundle.etf_xray.sectors for a given date. Returns [] on miss."""
    bundle = _load_gz_json(MID_BUNDLES_DIR / f"{target.isoformat()}.json.gz")
    if not isinstance(bundle, dict):
        return []
    etf_xray = bundle.get("etf_xray", {})
    if not isinstance(etf_xray, dict):
        return []
    sectors = etf_xray.get("sectors", [])
    return sectors if isinstance(sectors, list) else []


def load_ifds_sectors(target: date) -> list[dict]:
    """Aggregate Phase 4 snapshot tickers by sector.

    Returns a list of ``{sector, n_passed, top_score, avg_score}`` dicts
    sorted descending by avg_score.
    """
    snap = _load_gz_json(PHASE4_DIR / f"{target.isoformat()}.json.gz")
    if not isinstance(snap, list):
        return []

    by_sector: dict[str, list[float]] = {}
    for row in snap:
        if not isinstance(row, dict):
            continue
        sector = row.get("sector") or "(unknown)"
        score = row.get("combined_score")
        try:
            score_f = float(score) if score is not None else None
        except (TypeError, ValueError):
            score_f = None
        if score_f is None:
            continue
        by_sector.setdefault(sector, []).append(score_f)

    out: list[dict] = []
    for sector, scores in by_sector.items():
        if not scores:
            continue
        out.append({
            "sector": sector,
            "n_passed": len(scores),
            "top_score": max(scores),
            "avg_score": sum(scores) / len(scores),
        })
    out.sort(key=lambda r: r["avg_score"], reverse=True)
    return out


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def _mid_top_sectors(sectors: list[dict], n: int = 5) -> list[str]:
    """Pick the strongest MID sectors. Strength = consensus_state ranking
    (OVERWEIGHT > ACCUMULATING > NEUTRAL > DECREASING > UNDERWEIGHT).
    Falls back to ETF symbol order if the schema is unexpected.
    """
    rank = {
        "OVERWEIGHT": 4,
        "ACCUMULATING": 3,
        "NEUTRAL": 2,
        "DECREASING": 1,
        "UNDERWEIGHT": 0,
    }

    def key(s: dict) -> tuple[int, float]:
        state = (s.get("consensus_state") or s.get("state") or "").upper()
        score = float(s.get("score", 0) or 0)
        return (rank.get(state, -1), score)

    enriched = sorted(sectors, key=key, reverse=True)
    out: list[str] = []
    for s in enriched[:n]:
        symbol = s.get("etf") or s.get("symbol") or s.get("ticker")
        if symbol:
            out.append(str(symbol))
    return out


def _ifds_top_sectors(sectors: list[dict], n: int = 5) -> list[str]:
    return [s["sector"] for s in sectors[:n] if s.get("sector")]


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def build_report(start: date, end: date) -> str:
    lines: list[str] = []
    lines.append(f"# MID vs IFDS — Sector Rotation Comparison")
    lines.append("")
    lines.append(f"Window: **{start.isoformat()} → {end.isoformat()}**")
    lines.append("")
    lines.append("Source data:")
    lines.append(f"- MID bundles: `{MID_BUNDLES_DIR}/`")
    lines.append(f"- IFDS Phase 4 snapshots: `{PHASE4_DIR}/`")
    lines.append("")
    lines.append("Forward-return scoring is intentionally omitted in this "
                 "first iteration — see the daily review for context.")
    lines.append("")

    cur = start
    days_with_both = 0
    days_with_mid = 0
    days_with_ifds = 0
    while cur <= end:
        # Skip weekends to keep output compact
        if cur.weekday() >= 5:
            cur += timedelta(days=1)
            continue

        mid_sectors = load_mid_sectors(cur)
        ifds_sectors = load_ifds_sectors(cur)

        if mid_sectors:
            days_with_mid += 1
        if ifds_sectors:
            days_with_ifds += 1
        if mid_sectors and ifds_sectors:
            days_with_both += 1

        lines.append(f"## {cur.isoformat()} ({cur.strftime('%a')})")
        lines.append("")

        if not mid_sectors and not ifds_sectors:
            lines.append("_(no data)_")
            lines.append("")
            cur += timedelta(days=1)
            continue

        mid_top = _mid_top_sectors(mid_sectors, n=5)
        ifds_top = _ifds_top_sectors(ifds_sectors, n=5)

        rows = [
            ["MID top 5 (ETF)", ", ".join(mid_top) if mid_top else "_(none)_"],
            ["IFDS top 5 (sector name)",
             ", ".join(ifds_top) if ifds_top else "_(none)_"],
            ["MID sector count", str(len(mid_sectors))],
            ["IFDS sector count", str(len(ifds_sectors))],
        ]
        lines.append(_md_table(["Field", "Value"], rows))
        lines.append("")

        if ifds_sectors:
            lines.append("**IFDS Phase 4 — top sectors by avg score:**")
            lines.append("")
            ifds_rows = [
                [s["sector"], str(s["n_passed"]),
                 f"{s['avg_score']:.1f}", f"{s['top_score']:.1f}"]
                for s in ifds_sectors[:10]
            ]
            lines.append(_md_table(
                ["Sector", "N passed", "Avg score", "Top score"], ifds_rows))
            lines.append("")

        cur += timedelta(days=1)

    # --- Summary ---
    lines.append("## Coverage summary")
    lines.append("")
    summary_rows = [
        ["Days with MID bundle", str(days_with_mid)],
        ["Days with IFDS snapshot", str(days_with_ifds)],
        ["Days with both", str(days_with_both)],
    ]
    lines.append(_md_table(["Metric", "Count"], summary_rows))
    lines.append("")
    lines.append("---")
    lines.append("*Generated by `scripts/analysis/mid_vs_ifds_sector_comparison.py`*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline MID vs IFDS sector-rotation comparison."
    )
    parser.add_argument("--start", required=True, type=_parse_date,
                        help="Start date (YYYY-MM-DD).")
    parser.add_argument("--end", required=True, type=_parse_date,
                        help="End date (YYYY-MM-DD).")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output markdown path. If omitted, prints to stdout.")
    args = parser.parse_args()

    if args.start > args.end:
        print("ERROR: --start must be on or before --end", file=sys.stderr)
        return 2

    report = build_report(args.start, args.end)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
