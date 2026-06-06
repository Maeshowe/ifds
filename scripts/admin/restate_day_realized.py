#!/usr/bin/env python3
"""Restate a day's cumulative_pnl entry to broker-authoritative realized P&L.

Reusable parametrized admin tool (replaces the per-day one-off restatement
scripts). Until the recorder reliably captures the IBKR broker realized live
(Day 14 task A — `reqExecutions.realizedPNL` is async and the
request→sleep→re-request approach still fell back), the recorder records the
swing-attribution ESTIMATE (planned state.entry_price). This tool corrects a
day's entry to the broker-authoritative aggregate fetched (by CC) from the
connector ``get_account_trades``.

The IBKR ``realized_pnl`` is the broker's official net realized for the closing
trades; we set it directly as the daily_history ``pnl`` (consistent with the
Day 9 AMH / Day 12 CDNS / Day 13 restatements). ``commission`` is the separate
informational round-trip sum. Idempotent: SETS the values (re-run is a no-op
once applied). Atomic write.

    python scripts/admin/restate_day_realized.py --date 2026-06-04 \
        --realized 225.34 --commission 3.92 --dry-run
    python scripts/admin/restate_day_realized.py --date 2026-06-04 \
        --realized 225.34 --commission 3.92 --apply
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CUM_PNL_PATH = REPO_ROOT / "scripts" / "paper_trading" / "logs" / "cumulative_pnl.json"

_PT_DIR = REPO_ROOT / "scripts" / "paper_trading"
if str(_PT_DIR) not in sys.path:
    sys.path.insert(0, str(_PT_DIR))


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Restate a day's realized P&L to broker values")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--realized", type=float, required=True, help="broker realized net (sum)")
    parser.add_argument("--commission", type=float, default=0.0, help="round-trip commission sum")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.apply and not args.dry_run:
        parser.error("Specify --apply or --dry-run")

    from lib.ibkr_reconciliation import recompute_cumulative_pnl

    cum_data = json.loads(CUM_PNL_PATH.read_text())
    entry = next((e for e in cum_data.get("daily_history", []) if e.get("date") == args.date), None)
    if entry is None:
        print(f"ERROR: no {args.date} entry in cumulative_pnl.json")
        sys.exit(1)

    before_pnl = entry.get("pnl")
    before_cum = cum_data.get("cumulative_pnl")
    realized = round(args.realized, 2)
    commission = round(args.commission, 2)

    if abs(float(before_pnl) - realized) < 0.01:
        print(f"Already restated: {args.date} pnl={before_pnl} — no-op (idempotent).")
        return

    entry["pnl"] = realized
    entry["commission"] = commission
    new_cum = recompute_cumulative_pnl(cum_data)
    after_cum = new_cum["cumulative_pnl"]

    print(f"{args.date} pnl: {before_pnl} → {realized}  (commission → {commission})")
    print(f"cumulative_pnl: {before_cum} → {after_cum}")

    if args.dry_run:
        print("DRY RUN — no write.")
        return

    _atomic_write_json(CUM_PNL_PATH, new_cum)
    print(f"WROTE {CUM_PNL_PATH.name}.")


if __name__ == "__main__":
    main()
