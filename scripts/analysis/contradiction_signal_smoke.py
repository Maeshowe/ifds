#!/usr/bin/env python3
"""Smoke test for ifds.scoring.contradiction_signal.

Runs the signal against historical entry prices for known W17/W18 cases and
prints a markdown-friendly verdict table. NOT part of CI — manual verification
only. Requires IFDS_FMP_API_KEY in the environment.

Usage:
    python scripts/analysis/contradiction_signal_smoke.py
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ifds.data.fmp import FMPClient
from ifds.scoring.contradiction_signal import compute_contradiction_signal


# (ticker, entry_price, snapshot_date, note)
CASES: list[tuple[str, float, str, str]] = [
    ("DTE",  153.29, "2026-05-01", "W18 péntek — Q1 earnings miss, IFDS score 92"),
    ("CARG", 38.54,  "2026-04-22", "W17 — price 2.8% consensus fölött, CONTRADICTION flagged"),
    ("POST", 105.59, "2026-04-27", "W18 hétfő — -$299 napi vesztes"),
    ("NIO",  6.43,   "2026-04-28", "W18 kedd — -$239 LOSS_EXIT"),
    ("SKM",  39.46,  "2026-04-20", "W17 — JPM+Citi downgrade flagged"),
]


def main() -> int:
    api_key = os.environ.get("IFDS_FMP_API_KEY")
    if not api_key:
        print("ERROR: IFDS_FMP_API_KEY missing", file=sys.stderr)
        return 1
    client = FMPClient(api_key)

    print("| Ticker | Entry  | Consensus | High | Beats | Flag  | Reasons |")
    print("|--------|--------|-----------|------|-------|-------|---------|")
    for ticker, entry, dt_str, _note in CASES:
        target = client.get_price_target_consensus(ticker)
        earnings = client.get_earnings_history(ticker)
        grades = client.get_recent_grades(ticker)

        consensus = target.get("targetConsensus") if target else None
        high = target.get("targetHigh") if target else None
        beats_str = "—"
        if earnings:
            n_beat = sum(
                1 for e in earnings[:4]
                if isinstance(e.get("epsActual"), (int, float))
                and isinstance(e.get("epsEstimated"), (int, float))
                and e["epsActual"] >= e["epsEstimated"]
            )
            n = sum(
                1 for e in earnings[:4]
                if isinstance(e.get("epsActual"), (int, float))
                and isinstance(e.get("epsEstimated"), (int, float))
            )
            beats_str = f"{n_beat}/{n}"

        result = compute_contradiction_signal(
            price=entry,
            target_consensus=consensus,
            target_high=high,
            earnings_history=earnings,
            analyst_grades_recent=grades,
            today=date.fromisoformat(dt_str),
        )
        cons_s = f"${consensus}" if consensus else "—"
        high_s = f"${high}" if high else "—"
        flag_s = "**TRUE**" if result.is_contradicted else "False"
        reasons = ", ".join(result.reasons) or "—"
        print(f"| {ticker} | ${entry:.2f} | {cons_s} | {high_s} | {beats_str} | {flag_s} | {reasons} |")

    return 0


if __name__ == "__main__":
    sys.exit(main())
