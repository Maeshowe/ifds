#!/usr/bin/env python3
"""One-shot: seed the Day 9 (2026-05-28) AMH TIME_STOP pending-exit ledger.

P0 §0.11 Part A, deploy step 4. The pending-exit ledger did NOT exist on Day 9
(close_positions started writing it only from this Part A deploy), so the Day 9
AMH TIME_STOP MOC has no ledger entry and its realized P&L is still missing
from cumulative_pnl.json (the -$651.10 canonical baseline ends at Day 8).

This script hand-seeds the single AMH ledger entry for 2026-05-28 so that the
normal recorder can capture it from the live IBKR fill:

    python scripts/admin/seed_amh_day9_ledger.py --apply
    python scripts/paper_trading/daily_metrics.py --date 2026-05-28

The recorder (record_pending_exits) then matches the AMH SLD execution
(still in the connector's DAYS_30 history) and writes the realized P&L delta,
moving cumulative from -$651.10 by the AMH realized amount. Idempotent: the
ledger key (AMH_TIME_STOP_2026-05-28) prevents a duplicate append, and
record_pending_exits skips already-processed keys.

AMH Day 9 position (the 249-share leg that TIME_STOP'd, NOT the 2026-05-29
re-entry):
    entry_price = 32.11   (docs/review/2026-05-22-daily-review.md — entry)
    qty         = 249
    entry_date  = 2026-05-22  (Day 5 entry)
    exit_type   = TIME_STOP   (Day 9 EOD, days_held=5)
    sector      = Real Estate
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PENDING_EXITS_DIR = str(REPO_ROOT / "state" / "pending_exits")

_PT_DIR = REPO_ROOT / "scripts" / "paper_trading"
if str(_PT_DIR) not in sys.path:
    sys.path.insert(0, str(_PT_DIR))

LEDGER_DATE = "2026-05-28"
AMH_RECORD = {
    "ticker": "AMH",
    "entry_price": 32.11,
    "entry_date": "2026-05-22",
    "qty": 249,
    "exit_type": "TIME_STOP",
    "sector": "Real Estate",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Day 9 AMH pending-exit ledger")
    parser.add_argument("--apply", action="store_true", help="Write the ledger entry")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be written")
    args = parser.parse_args()
    if not args.apply and not args.dry_run:
        parser.error("Specify --apply or --dry-run")

    from lib.pending_exits import append_pending_exit, load_pending_exits, make_key

    key = make_key("AMH", "TIME_STOP", LEDGER_DATE)
    existing = load_pending_exits(LEDGER_DATE, PENDING_EXITS_DIR)
    print(f"ledger dir: {PENDING_EXITS_DIR}")
    print(f"existing records for {LEDGER_DATE}: {len(existing)}")
    print(f"target key: {key}")

    if args.dry_run:
        print("DRY RUN — would append:")
        print(AMH_RECORD)
        return

    res = append_pending_exit(AMH_RECORD, ledger_dir=PENDING_EXITS_DIR, today=LEDGER_DATE)
    print(f"result: {res}")
    print("Next: python scripts/paper_trading/daily_metrics.py --date 2026-05-28")


if __name__ == "__main__":
    main()
