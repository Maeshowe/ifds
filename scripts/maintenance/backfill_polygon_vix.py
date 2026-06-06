#!/usr/bin/env python3
"""Backfill daily_metrics VIX from Polygon I:VIX (data-quality fix #1).

The ``daily_metrics.market.vix_close`` field historically came from the Phase 0
MACRO_REGIME event, which is FRED-sourced. FRED publishes VIX with a 1-day lag
(EOD batch), so every backfilled day systematically carries the Day N-1 close
on Day N. The most visible failure: 6/5 recorded ``vix_close: 15.78`` (the 6/4
FRED value) while the true 6/5 close was 21.51 (+39.7% major risk-off, which
already crosses the Strategic-review VIX>18 shutdown threshold).

This tool rewrites ``market.vix_close`` and ``market.vix_delta_pct`` for each
existing ``state/daily_metrics/{date}.json`` in the requested range using the
authoritative Polygon ``I:VIX`` close (and the immediately preceding trading-day
close for the delta) — the same source the live recorder now uses.

Idempotent (re-run is a no-op once correct). Backs up each file before writing.

    python scripts/maintenance/backfill_polygon_vix.py --start 2026-05-18 --end 2026-06-05 --dry-run
    python scripts/maintenance/backfill_polygon_vix.py --start 2026-05-18 --end 2026-06-05 --apply
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

from daily_metrics import _fetch_vix_from_polygon  # noqa: E402


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
            continue  # not a recorded trading day

        with open(path) as f:
            data = json.load(f)
        market = data.get("market")
        if not isinstance(market, dict):
            print(f"  {iso}: no market section, skipping")
            continue

        close, prev = _fetch_vix_from_polygon(iso)
        if close is None:
            print(f"  {iso}: Polygon I:VIX unavailable, leaving unchanged")
            continue

        new_close = round(close, 2)
        new_delta = round((close - prev) / prev * 100, 2) if prev and prev > 0 else None

        old_close = market.get("vix_close")
        old_delta = market.get("vix_delta_pct")
        if old_close == new_close and old_delta == new_delta:
            print(f"  {iso}: already correct (vix={new_close}, Δ={new_delta})")
            continue

        print(
            f"  {iso}: vix {old_close} → {new_close}, "
            f"Δ% {old_delta} → {new_delta}" + ("" if apply else "  [dry-run]")
        )
        if apply:
            backup = path.with_suffix(f".json.bak.pre_vix_backfill.{stamp}")
            backup.write_text(path.read_text())
            market["vix_close"] = new_close
            market["vix_delta_pct"] = new_delta
            _atomic_write_json(path, data)
        changed += 1
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill daily_metrics VIX from Polygon I:VIX")
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

    apply = args.apply
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"VIX backfill [{mode}] {start} → {end} (Polygon I:VIX)")
    changed = backfill(start, end, apply)
    verb = "updated" if apply else "would update"
    print(f"Done: {changed} file(s) {verb}.")


if __name__ == "__main__":
    main()
