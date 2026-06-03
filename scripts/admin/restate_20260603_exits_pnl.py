#!/usr/bin/env python3
"""One-time restatement: 2026-06-03 multi-exit realized P&L → broker-authoritative.

P0 §0.11 Option B incident fix (Day 13, 2026-06-03).

The first live multi-exit (AKAM TP1 + ST TP1 + EOG TIME_STOP) recorded
**$0.00** for all three because the recorder reads
``reqExecutions().commissionReport.realizedPNL``, which is populated
asynchronously and was still 0 at the 22:10 run. ``ib.fills()`` (eod_report)
and the connector ``get_account_trades`` show the true values:

    AKAM SELL  8 @ 156.00   realized_pnl = 75.302072   commission 1.027293
    ST   SELL 47 @ 52.51    realized_pnl = 106.074969  commission 1.060146
    EOG  SELL 44 @ 141.55   realized_pnl = 48.462887   commission 1.137013 (MOC)
    --------------------------------------------------------------------
    Σ realized = 229.839928 (→ 229.84)   Σ commission = 3.224452 (→ 3.22)

The 2026-06-03 cumulative entry currently has pnl=0 (3 exits, processed). This
sets it to the broker-authoritative aggregate and recomputes the cumulative:

    pnl:        0.00 → 229.84
    commission: 0.00 → 3.22
    cumulative: -273.76 → -43.92

The exit-type counters (tp1_hits=2, moc_exits=1, trades=3, filled=3) are
already correct from the recorder run — only the P&L was wrong. Idempotent:
re-run is a no-op once applied. The recorder safety-fix (treat realizedPNL==0
as unavailable → fallback) prevents future silent $0; the robust realized
capture is tracked in the Day 14 task.

    python scripts/admin/restate_20260603_exits_pnl.py --dry-run
    python scripts/admin/restate_20260603_exits_pnl.py --apply
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

ENTRY_DATE = "2026-06-03"
BROKER_REALIZED_NET = 229.84  # 75.302072 + 106.074969 + 48.462887
ROUND_TRIP_COMMISSION = 3.22  # 1.027293 + 1.060146 + 1.137013


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
    parser = argparse.ArgumentParser(description="Restate 2026-06-03 multi-exit realized P&L")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.apply and not args.dry_run:
        parser.error("Specify --apply or --dry-run")

    from lib.ibkr_reconciliation import recompute_cumulative_pnl

    cum_data = json.loads(CUM_PNL_PATH.read_text())
    entry = next(
        (e for e in cum_data.get("daily_history", []) if e.get("date") == ENTRY_DATE), None
    )
    if entry is None:
        print(f"ERROR: no {ENTRY_DATE} entry in cumulative_pnl.json")
        sys.exit(1)

    before_pnl = entry.get("pnl")
    before_cum = cum_data.get("cumulative_pnl")

    if abs(float(before_pnl) - BROKER_REALIZED_NET) < 0.01:
        print(f"Already restated: {ENTRY_DATE} pnl={before_pnl} — no-op (idempotent).")
        return

    entry["pnl"] = BROKER_REALIZED_NET
    entry["commission"] = ROUND_TRIP_COMMISSION
    new_cum = recompute_cumulative_pnl(cum_data)
    after_cum = new_cum["cumulative_pnl"]

    print(
        f"{ENTRY_DATE} pnl: {before_pnl} → {BROKER_REALIZED_NET}  "
        f"(commission → {ROUND_TRIP_COMMISSION})"
    )
    print(f"cumulative_pnl: {before_cum} → {after_cum}")

    if args.dry_run:
        print("DRY RUN — no write.")
        return

    _atomic_write_json(CUM_PNL_PATH, new_cum)
    print(f"WROTE {CUM_PNL_PATH.name}.")


if __name__ == "__main__":
    main()
