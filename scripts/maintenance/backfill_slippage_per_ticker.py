#!/usr/bin/env python3
"""Backfill daily_metrics slippage_per_ticker.filled from IBKR fills (task #1).

Rewrites ``daily_metrics[date].execution.slippage_per_ticker[ticker].filled`` to
the broker-authoritative IBKR BUY (entry) fill price and recomputes
``slippage_pct`` from each file's existing ``planned`` limit. Before the
2026-06-09 fix, ``build_daily_metrics`` stored the submit-time state entry_price
(== planned) as ``filled``, hiding real entry slippage (e.g. TKR 6/8: planned
$131.83 vs real fill $133.71 = +1.43%, recorded as 0.0%). Also recomputes the
qty-weighted ``avg_fill_slippage_pct``.

The per-(date,ticker) fill map is connector-derived
(``scripts/maintenance/slippage_backfill_map.json``, from IBKR
get_account_trades — connector only reachable from CC, not the Mac Mini cron,
so the values are computed once by CC and applied here). Only tickers present in
BOTH the file's slippage_per_ticker and the map are touched. Idempotent (SET),
backs up before writing, atomic.

    python scripts/maintenance/backfill_slippage_per_ticker.py --dry-run
    python scripts/maintenance/backfill_slippage_per_ticker.py --apply
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
METRICS_DIR = REPO_ROOT / "state" / "daily_metrics"
DEFAULT_MAP = Path(__file__).resolve().parent / "slippage_backfill_map.json"


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


def _load_map(path: Path) -> dict[str, dict]:
    raw = json.loads(path.read_text())
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def _recompute_avg(slip: dict) -> float:
    total_qty = sum((s.get("qty", 0) or 0) for s in slip.values())
    if slip and total_qty > 0:
        return round(
            sum(s["slippage_pct"] * (s.get("qty", 0) or 0) for s in slip.values()) / total_qty, 2
        )
    if slip:
        return round(sum(s["slippage_pct"] for s in slip.values()) / len(slip), 2)
    return 0.0


def backfill(fill_map: dict[str, dict], apply: bool) -> int:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    changed = 0
    for date_str in sorted(fill_map):
        path = METRICS_DIR / f"{date_str}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        slip = (data.get("execution") or {}).get("slippage_per_ticker")
        if not isinstance(slip, dict):
            continue

        touched = False
        for ticker, fill_price in fill_map[date_str].items():
            entry = slip.get(ticker)
            if not isinstance(entry, dict):
                continue
            planned = entry.get("planned")
            if not planned:
                continue
            new_filled = round(float(fill_price), 4)
            new_pct = round((new_filled - planned) / planned * 100, 2)
            if entry.get("filled") == new_filled and entry.get("slippage_pct") == new_pct:
                continue
            print(
                f"  {date_str} {ticker}: filled {entry.get('filled')} → {new_filled}, "
                f"slip {entry.get('slippage_pct')} → {new_pct}" + ("" if apply else "  [dry-run]")
            )
            if apply:
                entry["filled"] = new_filled
                entry["slippage_pct"] = new_pct
            touched = True
            changed += 1

        if touched and apply:
            data["execution"]["avg_fill_slippage_pct"] = _recompute_avg(slip)
            backup = path.with_suffix(f".json.bak.pre_slippage_backfill.{stamp}")
            backup.write_text(path.read_text())
            _atomic_write_json(path, data)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill slippage_per_ticker.filled from IBKR")
    parser.add_argument("--map-file", default=str(DEFAULT_MAP), help="date→ticker→fill JSON")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true", help="Write changes (with backup)")
    group.add_argument("--dry-run", action="store_true", help="Preview only (default)")
    args = parser.parse_args()

    fill_map = _load_map(Path(args.map_file))
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"Slippage backfill [{mode}] ({len(fill_map)} day(s))")
    changed = backfill(fill_map, args.apply)
    verb = "updated" if args.apply else "would update"
    print(f"Done: {changed} ticker-entry(ies) {verb}.")


if __name__ == "__main__":
    main()
