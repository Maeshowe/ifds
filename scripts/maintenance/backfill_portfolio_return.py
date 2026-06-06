#!/usr/bin/env python3
"""Backfill daily_metrics portfolio_return_pct + excess_pct (data-quality fix #6).

Recomputes ``excess_return.portfolio_return_pct`` as the day-over-day NetLiq %
move (mark-to-market, from ``state/daily_equity.json``) instead of the
realized-P&L / initial-capital estimate, and recomputes ``excess_pct`` against
the metrics file's own ``spy_return_pct``. For a swing book holding positions
overnight, the NetLiq move is the meaningful daily return vs SPY (e.g. Day 15
6/5: 101273.85 → 100675.60 = -0.59%, not the realized-only -0.01%).

Only days where ``daily_equity.json`` has BOTH the date and a prior date are
corrected; earlier days (before the §3a equity store existed) are left as the
realized estimate. Idempotent (SET), backs up before writing, atomic.

    python scripts/maintenance/backfill_portfolio_return.py --start 2026-05-18 --end 2026-06-05 --dry-run
    python scripts/maintenance/backfill_portfolio_return.py --start 2026-05-18 --end 2026-06-05 --apply
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
METRICS_DIR = REPO_ROOT / "state" / "daily_metrics"

_PT_DIR = REPO_ROOT / "scripts" / "paper_trading"
if str(_PT_DIR) not in sys.path:
    sys.path.insert(0, str(_PT_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from daily_metrics import _compute_portfolio_return_from_equity  # noqa: E402


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


def _iter_dates(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def backfill(start: date, end: date, apply: bool) -> int:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    changed = 0
    for d in _iter_dates(start, end):
        iso = d.isoformat()
        path = METRICS_DIR / f"{iso}.json"
        if not path.exists():
            continue

        ret = _compute_portfolio_return_from_equity(iso)
        if ret is None:
            print(f"  {iso}: no equity pair, leaving as realized estimate")
            continue

        data = json.loads(path.read_text())
        block = data.get("excess_return")
        if not isinstance(block, dict):
            print(f"  {iso}: no excess_return block, skipping")
            continue

        new_ret = round(ret, 2)
        spy = block.get("spy_return_pct")
        new_excess = round(ret - spy, 2) if spy is not None else None

        old_ret = block.get("portfolio_return_pct")
        old_excess = block.get("excess_pct")
        if old_ret == new_ret and old_excess == new_excess:
            print(f"  {iso}: already correct (ret={new_ret}, excess={new_excess})")
            continue

        print(
            f"  {iso}: portfolio_return {old_ret} → {new_ret}, "
            f"excess {old_excess} → {new_excess}" + ("" if apply else "  [dry-run]")
        )
        if apply:
            backup = path.with_suffix(f".json.bak.pre_portfolio_return_backfill.{stamp}")
            backup.write_text(path.read_text())
            block["portfolio_return_pct"] = new_ret
            block["excess_pct"] = new_excess
            _atomic_write_json(path, data)
        changed += 1
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill portfolio_return_pct from NetLiq equity")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD inclusive")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD inclusive")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true", help="Write changes (with backup)")
    group.add_argument("--dry-run", action="store_true", help="Preview only (default)")
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    if start > end:
        parser.error("--start must be <= --end")

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"portfolio_return backfill [{mode}] {start} → {end} (daily_equity NetLiq)")
    changed = backfill(start, end, args.apply)
    verb = "updated" if args.apply else "would update"
    print(f"Done: {changed} file(s) {verb}.")


if __name__ == "__main__":
    main()
