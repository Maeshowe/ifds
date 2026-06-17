#!/usr/bin/env python3
"""One-time backfill: insert the missing 2026-06-01 zero daily_history row.

2026-06-01 was a NYSE trading day (Day 9) with **zero exits** (no P&L entry).
The §5.4 zero-row safety net in daily_metrics.record_pending_exits — which now
ensures every trading day gets a (zero) daily_history row so the history has no
gaps — was not yet active on 06-01, so that day is missing from
``cumulative_pnl.json::daily_history``. As a result ``trading_days``
(= ``len(daily_history)``) under-counts by 1 versus the NYSE trading-day number
(``daily_metrics.compute_trading_day_number`` / the [Day N/63] label, which are
already correct).

This replays exactly what the live §5.4 safety net would have done on 06-01:

    recompute_cumulative_pnl(update_cumulative_history_entry(cum_data, "2026-06-01"))

which inserts a zero-initialised, date-sorted row and recomputes
``trading_days``. Because 06-01 has zero net P&L, **no cumulative dollar value
changes** — the script asserts this before writing. From 06-02 onward the live
mechanism already fills every day, so no further backfill is needed.

    python scripts/admin/backfill_2026-06-01_zero_row.py --dry-run
    python scripts/admin/backfill_2026-06-01_zero_row.py --apply

Idempotent: a no-op if the 2026-06-01 row already exists.

NOTE: run on the Mac Mini (the authoritative cumulative_pnl.json). The MacBook
copy is a sync mirror and would be overwritten by the next sync_from_mini.sh.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CUM_PNL_PATH = REPO_ROOT / "scripts" / "paper_trading" / "logs" / "cumulative_pnl.json"

_PT_DIR = REPO_ROOT / "scripts" / "paper_trading"
if str(_PT_DIR) not in sys.path:
    sys.path.insert(0, str(_PT_DIR))

BACKFILL_DATE = "2026-06-01"


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
    parser = argparse.ArgumentParser(description="Backfill the missing 2026-06-01 zero row")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.apply and not args.dry_run:
        parser.error("Specify --apply or --dry-run")

    from lib.ibkr_reconciliation import recompute_cumulative_pnl, update_cumulative_history_entry

    cum_data = json.loads(CUM_PNL_PATH.read_text())

    # Idempotency: skip if the 06-01 row already exists.
    if any(e.get("date") == BACKFILL_DATE for e in cum_data.get("daily_history", [])):
        print("2026-06-01 row already present — no-op (idempotent).")
        return

    before_cum = cum_data.get("cumulative_pnl")
    before_pct = cum_data.get("cumulative_pnl_pct")
    before_days = cum_data.get("trading_days")
    before_len = len(cum_data.get("daily_history", []))

    new_cum = recompute_cumulative_pnl(update_cumulative_history_entry(cum_data, BACKFILL_DATE))

    after_cum = new_cum.get("cumulative_pnl")
    after_pct = new_cum.get("cumulative_pnl_pct")
    after_days = new_cum.get("trading_days")
    after_len = len(new_cum.get("daily_history", []))
    row = next(e for e in new_cum["daily_history"] if e["date"] == BACKFILL_DATE)

    # SAFETY: a zero-P&L backfill must not move any cumulative dollar value.
    assert after_cum == before_cum, f"cumulative_pnl changed: {before_cum} → {after_cum} (abort!)"
    assert after_pct == before_pct, f"cumulative_pnl_pct changed: {before_pct} → {after_pct}"
    assert row["pnl"] == 0 and row["commission"] == 0, f"06-01 row not zero: {row}"
    assert after_len == before_len + 1, "exactly one row should be added"

    print(f"daily_history rows: {before_len} → {after_len}  (+1: {BACKFILL_DATE} zero-row)")
    print(f"trading_days:       {before_days} → {after_days}")
    print(f"cumulative_pnl:     {before_cum} (UNCHANGED — zero-P&L day) ✓")
    print(f"inserted row:       {json.dumps(row)}")

    if args.dry_run:
        print("DRY RUN — no write.")
        return

    # Timestamped backup of the live financial-state file before writing.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = CUM_PNL_PATH.with_suffix(f".json.bak.pre_0601_backfill.{stamp}")
    backup.write_text(CUM_PNL_PATH.read_text())
    _atomic_write_json(CUM_PNL_PATH, new_cum)
    print(f"BACKUP {backup.name}")
    print(f"WROTE  {CUM_PNL_PATH.name}  (trading_days now {after_days})")


if __name__ == "__main__":
    main()
