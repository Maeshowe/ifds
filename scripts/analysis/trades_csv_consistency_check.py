#!/usr/bin/env python3
"""Trades-CSV ⟷ daily_metrics consistency audit (read-only).

For every date that has both a ``scripts/paper_trading/logs/trades_{date}.csv``
and a ``state/daily_metrics/{date}.json``, compare the CSV against the
broker-authoritative ``trades.details`` block: row count, ticker set, and P&L
sum. Flags days where the CSV diverges — i.e. days the legacy fill-reconstruction
writer corrupted (self-reentry mis-pairing, incomplete exit list). Companion to
the 2026-07-11 eod_report ledger-CSV fix; run it after the fix to confirm 07-08
is clean and to scope which historical CSVs still need verified regeneration.

    python scripts/analysis/trades_csv_consistency_check.py
"""

from __future__ import annotations

import csv
import glob
import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TRADES_DIR = REPO / "scripts" / "paper_trading" / "logs"
DAILY_METRICS_DIR = REPO / "state" / "daily_metrics"
PNL_TOLERANCE = 0.5  # dollars — rounding slack between the CSV and details sums


def audit() -> list[dict]:
    """Return one record per audited date with the divergence verdict."""
    out = []
    for csv_path in sorted(glob.glob(str(TRADES_DIR / "trades_2026-*.csv"))):
        date_str = os.path.basename(csv_path)[len("trades_") : -len(".csv")]
        dm_path = DAILY_METRICS_DIR / f"{date_str}.json"
        if not dm_path.exists():
            continue
        with open(csv_path) as f:
            rows = list(csv.DictReader(f))
        dm = json.load(open(dm_path))
        details = (dm.get("trades") or {}).get("details") or []

        csv_pnl = round(sum(float(r["pnl"]) for r in rows), 2)
        det_pnl = round(sum(float(d.get("pnl", 0)) for d in details), 2)
        csv_tickers = sorted(r["ticker"] for r in rows)
        det_tickers = sorted(d["ticker"] for d in details)
        consistent = (
            len(rows) == len(details)
            and abs(csv_pnl - det_pnl) < PNL_TOLERANCE
            and csv_tickers == det_tickers
        )
        out.append(
            {
                "date": date_str,
                "csv_n": len(rows),
                "det_n": len(details),
                "csv_pnl": csv_pnl,
                "det_pnl": det_pnl,
                "consistent": consistent,
            }
        )
    return out


def main() -> None:
    records = audit()
    print(f"{'date':12}{'csv_n':>6}{'det_n':>6}{'csv_pnl':>11}{'det_pnl':>11}  status")
    diverged = []
    for r in records:
        status = "OK" if r["consistent"] else "DIVERG"
        if not r["consistent"]:
            diverged.append(r["date"])
        print(
            f"{r['date']:12}{r['csv_n']:>6}{r['det_n']:>6}"
            f"{r['csv_pnl']:>11}{r['det_pnl']:>11}  {status}"
        )
    print(f"\n{len(records)} days audited — {len(diverged)} divergent: {diverged or 'none'}")


if __name__ == "__main__":
    main()
