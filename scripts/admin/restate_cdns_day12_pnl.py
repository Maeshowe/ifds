#!/usr/bin/env python3
"""One-time restatement: Day 12 (2026-06-02) CDNS TP2 → broker-authoritative.

P0 §0.11 Option B follow-up.

The Day 12 CDNS TP2 was recorded by the pre-Option-B recorder using
swing-attribution (state.entry_price $373.85): pnl=$450.10, commission=$0.
Option B switches the recorder to the IBKR broker-authoritative realized_pnl
(consistent with the Day 1-9 canonical basis). This one-off corrects the
already-recorded Day 12 entry to the broker value from
get_account_trades (DAYS_7), trade 00025b44.6a1eea50.01.01:

    CDNS SELL 14 @ 406.00  2026-06-02  realized_pnl = 434.820138  (net)
    round-trip commission = 1.000042 (buy) + 1.119862 (sell) = 2.12

    pnl:        450.10 → 434.82   (Δ -15.28: $13.16 entry slippage + $2.12 commission)
    commission:   0.00 → 2.12
    cumulative: -258.48 → -273.76

Idempotent: directly SETS the entry to the broker values (re-run is a no-op
once applied). From Day 13 onward the recorder records broker realized_pnl
natively — no restatement ever needed again.

    python scripts/admin/restate_cdns_day12_pnl.py --dry-run
    python scripts/admin/restate_cdns_day12_pnl.py --apply
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

ENTRY_DATE = "2026-06-02"
BROKER_REALIZED_NET = 434.82  # IBKR realized_pnl 434.820138, trade 00025b44.6a1eea50.01.01
ROUND_TRIP_COMMISSION = 2.12  # 1.000042 buy + 1.119862 sell


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
    parser = argparse.ArgumentParser(description="Restate Day 12 CDNS TP2 to broker-authoritative")
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
        f"{ENTRY_DATE} pnl: {before_pnl} → {BROKER_REALIZED_NET}  (commission → {ROUND_TRIP_COMMISSION})"
    )
    print(f"cumulative_pnl: {before_cum} → {after_cum}")

    if args.dry_run:
        print("DRY RUN — no write.")
        return

    _atomic_write_json(CUM_PNL_PATH, new_cum)
    print(f"WROTE {CUM_PNL_PATH.name}.")


if __name__ == "__main__":
    main()
