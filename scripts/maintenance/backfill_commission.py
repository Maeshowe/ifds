#!/usr/bin/env python3
"""Backfill cumulative_pnl daily_history commission (data-quality fix #4).

Standardizes ``cumulative_pnl.json`` ``daily_history[date].commission`` to the
broker-authoritative EXIT-leg (SLD) commission — the same basis the live
recorder (``daily_metrics.record_pending_exits``) uses. Historical entries were
recorded inconsistently (the pre-Part-A eod_report summed all-trade
commissions; some restatements used a round-trip sum; 6/4–6/5 landed at $0
because the async ``commissionReport`` had not settled at record time).

Commission is informational (``daily_history.pnl`` is already NET), so this does
NOT change ``cumulative_pnl`` — it only corrects the audit-trail / friction
metric used by ``weekly_metrics.py`` and the Day 63/90 reviews.

The per-day map is connector-derived (``scripts/maintenance/commission_backfill_map.json``,
from IBKR ``get_account_trades`` — the connector is only reachable from CC, not
the Mac Mini cron, so the values are computed once by CC and applied here).
Idempotent (SET, re-run is a no-op). Backs up before writing. Atomic.

    python scripts/maintenance/backfill_commission.py --dry-run
    python scripts/maintenance/backfill_commission.py --apply
    python scripts/maintenance/backfill_commission.py --map-file other.json --apply
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CUM_PNL_PATH = REPO_ROOT / "scripts" / "paper_trading" / "logs" / "cumulative_pnl.json"
DEFAULT_MAP = Path(__file__).resolve().parent / "commission_backfill_map.json"


def _atomic_write_json(path: Path, data: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _load_map(path: Path) -> dict[str, float]:
    raw = json.loads(path.read_text())
    return {k: float(v) for k, v in raw.items() if not k.startswith("_")}


def backfill(cum_path: Path, commission_map: dict[str, float], apply: bool) -> int:
    data = json.loads(cum_path.read_text())
    history = data.get("daily_history", [])
    by_date = {e.get("date"): e for e in history if isinstance(e, dict)}

    changed = 0
    for date_str in sorted(commission_map):
        new_comm = round(commission_map[date_str], 2)
        entry = by_date.get(date_str)
        if entry is None:
            print(f"  {date_str}: no daily_history entry, skipping")
            continue
        old_comm = entry.get("commission")
        if old_comm == new_comm:
            print(f"  {date_str}: already {new_comm}")
            continue
        print(
            f"  {date_str}: commission {old_comm} → {new_comm}" + ("" if apply else "  [dry-run]")
        )
        if apply:
            entry["commission"] = new_comm
        changed += 1

    if apply and changed:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = cum_path.with_suffix(f".json.bak.pre_commission_backfill.{stamp}")
        backup.write_text(cum_path.read_text())
        _atomic_write_json(cum_path, data)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill daily_history commission (EXIT-leg)")
    parser.add_argument("--map-file", default=str(DEFAULT_MAP), help="date→commission JSON")
    parser.add_argument("--cum-file", default=str(CUM_PNL_PATH), help="cumulative_pnl.json path")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true", help="Write changes (with backup)")
    group.add_argument("--dry-run", action="store_true", help="Preview only (default)")
    args = parser.parse_args()

    commission_map = _load_map(Path(args.map_file))
    cum_path = Path(args.cum_file)
    if not cum_path.exists():
        parser.error(f"cumulative_pnl.json not found: {cum_path}")

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"Commission backfill [{mode}] {cum_path} ({len(commission_map)} day(s))")
    changed = backfill(cum_path, commission_map, args.apply)
    verb = "updated" if args.apply else "would update"
    print(f"Done: {changed} entry(ies) {verb}.")


if __name__ == "__main__":
    main()
