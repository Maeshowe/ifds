#!/usr/bin/env python3
"""One-time backfill: Day 9 (2026-05-28) AMH TIME_STOP realized P&L.

P0 §0.11 Part A, deploy step 4 — backfill variant.

The pending-exit recorder (daily_metrics.record_pending_exits) uses IBKR
``reqExecutions``, which only returns the CURRENT session's fills. Run on
2026-06-01 it cannot reach the 2026-05-28 AMH MOC fill, so the seeded ledger
entry stays unprocessed (correctly — the recorder never fabricates P&L).

For this one-time historical backfill we therefore use the broker-authoritative
realized P&L from the IBKR connector ``get_account_trades`` (DAYS_30):

    AMH SELL 249 @ 31.99  MOC NYSE  2026-05-28T19:59:32Z
    trade id 0000e0d5.6a1ab106.01.01
    IBKR realized_pnl = -57.484092   (net, incl. round-trip commission)

Note the actual 5/22 BUY fills averaged 32.21 (29+120+100 @ 32.21), NOT the
32.11 quoted in docs/review/2026-05-22 — IBKR's realized already reflects the
true 32.21 entry and all commissions, so we apply it directly.

This applies the realized to the existing 2026-05-28 cumulative_pnl entry
(currently pnl=0), recomputes totals, and marks the ledger entry processed.
Idempotent: gated on the ledger ``processed`` flag.

    python scripts/admin/backfill_amh_day9_pnl.py --dry-run
    python scripts/admin/backfill_amh_day9_pnl.py --apply

From Day 10 (2026-05-29) onward the live mechanism handles everything
same-day (close_positions writes the ledger, record_pending_exits captures
the fill at the 22:10 cron when reqExecutions still has it) — no backfill needed.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CUM_PNL_PATH = REPO_ROOT / "scripts" / "paper_trading" / "logs" / "cumulative_pnl.json"
PENDING_EXITS_DIR = str(REPO_ROOT / "state" / "pending_exits")

_PT_DIR = REPO_ROOT / "scripts" / "paper_trading"
if str(_PT_DIR) not in sys.path:
    sys.path.insert(0, str(_PT_DIR))

LEDGER_DATE = "2026-05-28"
LEDGER_KEY = "AMH_TIME_STOP_2026-05-28"

# IBKR get_account_trades (DAYS_30), trade 0000e0d5.6a1ab106.01.01
AMH_REALIZED_NET = -57.48  # IBKR realized_pnl (net, incl. all commissions)
AMH_ROUND_TRIP_COMMISSION = 2.70  # 1.458392 sell + 1.245747 buy (5/22) round-trip


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
    parser = argparse.ArgumentParser(description="Backfill Day 9 AMH realized P&L")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.apply and not args.dry_run:
        parser.error("Specify --apply or --dry-run")

    from lib.ibkr_reconciliation import recompute_cumulative_pnl, update_cumulative_history_entry
    from lib.pending_exits import load_pending_exits, mark_processed

    # Idempotency: skip if the ledger entry is already processed.
    records = load_pending_exits(LEDGER_DATE, PENDING_EXITS_DIR)
    amh = next((r for r in records if r.get("key") == LEDGER_KEY), None)
    if amh is None:
        print(f"ERROR: ledger entry {LEDGER_KEY} not found — run seed_amh_day9_ledger.py first.")
        sys.exit(1)
    if amh.get("processed"):
        print(f"Already processed: {LEDGER_KEY} — no-op (idempotent).")
        return

    cum_data = json.loads(CUM_PNL_PATH.read_text())
    before = cum_data.get("cumulative_pnl")

    new_cum = update_cumulative_history_entry(
        cum_data,
        LEDGER_DATE,
        pnl_delta=AMH_REALIZED_NET,
        commission_delta=AMH_ROUND_TRIP_COMMISSION,
        trades_delta=1,
        filled_delta=1,
        counter_increments={"moc_exits": 1},
    )
    new_cum = recompute_cumulative_pnl(new_cum)
    after = new_cum["cumulative_pnl"]
    entry = next(e for e in new_cum["daily_history"] if e["date"] == LEDGER_DATE)

    print(f"cumulative_pnl: {before} → {after}  (Δ {AMH_REALIZED_NET})")
    print(
        f"2026-05-28 entry: pnl={entry['pnl']} commission={entry['commission']} "
        f"moc_exits={entry.get('moc_exits')} trades={entry['trades']}"
    )
    print(f"trading_days: {new_cum['trading_days']}")

    if args.dry_run:
        print("DRY RUN — no write.")
        return

    _atomic_write_json(CUM_PNL_PATH, new_cum)
    mark_processed(LEDGER_DATE, {LEDGER_KEY}, PENDING_EXITS_DIR)
    print(f"WROTE {CUM_PNL_PATH.name}; ledger {LEDGER_KEY} marked processed.")


if __name__ == "__main__":
    main()
