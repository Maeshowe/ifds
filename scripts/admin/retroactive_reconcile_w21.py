"""Retroactive reconciliation for W21 (Day 2 + Day 4 + Day 5).

One-shot script to repair the W21 (2026-05-18 → 2026-05-22) state and
P&L records after the 2026-05-23 IBKR Trades audit revealed:

* **Day 2 (2026-05-19)** — EC TP1 50% partial close was misclassified as
  ``MOC`` in ``daily_metrics`` and ``cumulative_pnl.json`` (the 21:40 MOC
  cron rolled it up under that bucket). The realized P&L was captured
  correctly ($112.31 gross), but the exit type and counters are wrong.

* **Day 4 (2026-05-21) 19:19:54 CEST** — VLO SL bracket triggered
  autonomously in the IBKR Workstation (manual SL+TP1 child orders Tamás
  placed on Day 3 alongside the manual workaround entries for the Error
  354 incident). 16 shares SLD @ $244.61, net realized -$227.06.
  **Not captured** in daily_metrics, swing_positions, or cumulative_pnl.

* **Day 5 (2026-05-22) 16:40:20 CEST** — ON TP1 bracket triggered
  autonomously (same source as VLO). 27 shares SLD @ $115.41, net
  realized +$159.12. **Not captured** in any state file either.

The script writes:
* ``state/daily_metrics/2026-05-19.json`` — reclassify EC MOC → TP1
* ``state/daily_metrics/2026-05-21.json`` — VLO SL trade + counters
* ``state/daily_metrics/2026-05-22.json`` — ON TP1 trade + counters
* ``state/swing_positions.json``         — remove VLO + ON (closed)
* ``scripts/paper_trading/logs/cumulative_pnl.json`` — daily_history fix

Backups are written next to each file as ``*.bak.pre_retroreconcile.{ts}``.

Idempotency: a sentinel field
``daily_metrics[date]["_retroreconcile_applied"] = "<timestamp>"`` marks
each touched daily_metrics file, and the script skips a date whose
sentinel is already present (so repeat ``--apply`` runs are no-ops).

Usage::

    python scripts/admin/retroactive_reconcile_w21.py --dry-run   # audit
    python scripts/admin/retroactive_reconcile_w21.py --apply     # write

Refs:
    docs/tasks/2026-05-23-state-reconciliation-from-ibkr.md
    docs/review/2026-05-21-daily-review.md §9
    docs/review/2026-05-22-daily-review.md §9
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("retroactive_reconcile_w21")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Pure cumulative_pnl.json mutators now live in the paper-trading lib so the
# Part A pending-exits recorder shares one implementation (P0 §0.11). Re-export
# here for back-compat with the existing retroactive tests.
_PT_DIR = REPO_ROOT / "scripts" / "paper_trading"
if str(_PT_DIR) not in sys.path:
    sys.path.insert(0, str(_PT_DIR))
from lib.ibkr_reconciliation import (  # noqa: E402
    recompute_cumulative_pnl,
    update_cumulative_history_entry,
)
DAILY_METRICS_DIR = REPO_ROOT / "state" / "daily_metrics"
SWING_STATE_PATH = REPO_ROOT / "state" / "swing_positions.json"
CUMULATIVE_PNL_PATH = REPO_ROOT / "scripts" / "paper_trading" / "logs" / "cumulative_pnl.json"

SENTINEL_KEY = "_retroreconcile_applied"


@dataclass(frozen=True)
class TradeRecord:
    """A single retroactive trade to apply.

    Values are from the 2026-05-23 IBKR TWS Trades audit (Log Review chat).
    """

    date: str
    ticker: str
    qty: int
    entry: float
    exit: float
    exit_type: str        # "TP1" | "SL" | "TP2" | "TRAIL_SL" ...
    gross: float          # IBKR Net Total (pre-commission)
    commission: float
    net: float            # IBKR Net Incl. Commission
    notes: str = ""


# Day 2 EC TP1 (RECLASSIFY only — P&L is already in the daily_metrics).
# The 332→166 partial close at $13.76 was rolled into 2 fills, each
# reported as MOC. Switch them to TP1 and decrement moc_exits.
EC_DAY2_RECLASSIFY = {
    "date": "2026-05-19",
    "ticker": "EC",
    "moc_exits_decrement": 2,   # 2 fills were classified as MOC
    "tp1_hits_increment": 1,    # 1 distinct TP1 trigger (= 1 hit)
    "new_exit_type": "TP1",     # both fill entries in trades.details
}

# Day 4 VLO SL — full close from the manual Workstation SL bracket.
VLO_DAY4 = TradeRecord(
    date="2026-05-21",
    ticker="VLO",
    qty=16,
    entry=258.55,      # state entry_price (manual fill Day 3)
    exit=244.61,       # IBKR Trades log fill price
    exit_type="SL",
    gross=-222.97,     # IBKR Net Total
    commission=4.09,   # round-trip commission
    net=-227.06,       # IBKR Net Incl. Commission
    notes="Manual Workstation SL bracket trigger 19:19:54 CEST",
)

# Day 5 ON TP1 — full close from the manual Workstation TP1 bracket.
ON_DAY5 = TradeRecord(
    date="2026-05-22",
    ticker="ON",
    qty=27,
    entry=109.48,      # state entry_price (manual fill Day 3)
    exit=115.41,       # IBKR Trades log fill price (planned TP1, exact match)
    exit_type="TP1",
    gross=161.19,      # IBKR Net Total
    commission=2.07,
    net=159.12,
    notes="Manual Workstation TP1 bracket trigger 16:40:20 CEST",
)

# The expected cumulative_pnl after the retroactive reconcile is applied.
# Source: docs/tasks/2026-05-23-state-reconciliation-from-ibkr.md §2.5.
EXPECTED_FINAL_CUMULATIVE = 42.63


# ---------------------------------------------------------------------------
# Pure helpers (unit-testable)
# ---------------------------------------------------------------------------

def reclassify_ec_day2(daily_metrics: dict) -> dict:
    """Apply the EC Day 2 MOC→TP1 reclassification to a daily_metrics dict.

    Returns a new dict (immutable input). The P&L numbers are NOT changed
    — only the exit categorization moves from MOC to TP1.
    """
    out = copy.deepcopy(daily_metrics)

    # Counter swap
    exits = out.setdefault("exits", {})
    moc_before = exits.get("moc", 0)
    exits["moc"] = max(0, moc_before - EC_DAY2_RECLASSIFY["moc_exits_decrement"])
    exits["tp1"] = exits.get("tp1", 0) + EC_DAY2_RECLASSIFY["tp1_hits_increment"]

    # Trades.details exit_type rewrite for the EC entries
    trades = out.setdefault("trades", {"best": None, "worst": None, "details": []})
    for entry in trades.get("details", []):
        if entry.get("ticker") == "EC" and entry.get("exit_type") == "MOC":
            entry["exit_type"] = "TP1"

    # Best/worst exit_type rewrite if they point to the EC trade
    for slot in ("best", "worst"):
        rec = trades.get(slot)
        if rec and rec.get("ticker") == "EC" and rec.get("exit_type") == "MOC":
            rec["exit_type"] = "TP1"

    out[SENTINEL_KEY] = datetime.now(timezone.utc).isoformat()
    return out


def append_trade_to_daily_metrics(
    daily_metrics: dict,
    trade: TradeRecord,
    new_cumulative: float,
) -> dict:
    """Append a TradeRecord to a daily_metrics dict and refresh pnl + exits.

    Returns a new dict (immutable input). Updates:
    * ``pnl.gross``, ``pnl.commission``, ``pnl.net``, ``pnl.cumulative``,
      ``pnl.cumulative_pct``
    * ``exits.{sl|tp1|tp2|trail|moc|loss_exit}`` — increment based on
      ``trade.exit_type``
    * ``execution.commission_total`` — bump by ``trade.commission``
    * ``trades.details`` — append the new trade entry
    * ``trades.best``, ``trades.worst`` — refresh
    """
    out = copy.deepcopy(daily_metrics)

    # pnl
    pnl = out.setdefault("pnl", {})
    pnl["gross"] = round(pnl.get("gross", 0.0) + trade.gross, 2)
    pnl["commission"] = round(pnl.get("commission", 0.0) + trade.commission, 2)
    pnl["net"] = round(pnl.get("net", 0.0) + trade.net, 2)
    pnl["cumulative"] = round(new_cumulative, 2)
    pnl["cumulative_pct"] = round(new_cumulative / 100_000 * 100, 3)

    # exits — map exit_type to the counter key
    exit_map = {
        "TP1": "tp1",
        "TP2": "tp2",
        "SL": "sl",
        "HARD_SL": "sl",
        "MENTAL_SL": "sl",
        "LOSS_EXIT": "loss_exit",
        "TRAIL_SL": "trail",
        "TRAIL": "trail",
        "MOC": "moc",
        "TIME_STOP": "moc",
    }
    counter_key = exit_map.get(trade.exit_type)
    if counter_key:
        exits = out.setdefault("exits", {})
        exits[counter_key] = exits.get(counter_key, 0) + 1

    # execution.commission_total
    execution = out.setdefault("execution", {})
    execution["commission_total"] = round(
        execution.get("commission_total", 0.0) + trade.commission, 2
    )

    # trades.details
    trades = out.setdefault("trades", {"best": None, "worst": None, "details": []})
    new_entry = {
        "ticker": trade.ticker,
        "score": 0.0,
        "entry": trade.entry,
        "exit": trade.exit,
        "pnl": trade.net,
        "exit_type": trade.exit_type,
        "qty": trade.qty,
        "gross": trade.gross,
        "commission": trade.commission,
        "notes": trade.notes,
    }
    trades.setdefault("details", []).append(new_entry)

    # best/worst — refresh against details
    nets = [
        (d.get("pnl", 0), {"ticker": d.get("ticker"), "pnl": d.get("pnl"),
                            "pnl_pct": 0.0, "exit_type": d.get("exit_type")})
        for d in trades["details"]
    ]
    if nets:
        nets.sort(key=lambda t: t[0])
        trades["worst"] = nets[0][1]
        trades["best"] = nets[-1][1]

    out[SENTINEL_KEY] = datetime.now(timezone.utc).isoformat()
    return out


def remove_closed_positions(swing_state: dict, tickers_to_remove: set[str]) -> dict:
    """Remove tickers from swing_positions.json positions list."""
    out = copy.deepcopy(swing_state)
    before = len(out.get("positions", []))
    out["positions"] = [
        p for p in out.get("positions", []) if p.get("ticker") not in tickers_to_remove
    ]
    after = len(out["positions"])
    out["last_updated"] = datetime.now(timezone.utc).isoformat()
    out["_retroreconcile_removed"] = sorted(tickers_to_remove)
    logger.info(f"swing_positions: {before} → {after} (removed {tickers_to_remove})")
    return out


# ---------------------------------------------------------------------------
# I/O orchestration
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _write_json_backup(path: Path, data: dict, backup_suffix: str) -> Path:
    """Write data to path after backing up the current file."""
    bak = path.with_suffix(path.suffix + f".bak.{backup_suffix}")
    if path.exists():
        shutil.copy2(path, bak)
        logger.info(f"backup: {bak.name}")
    path.write_text(json.dumps(data, indent=2))
    logger.info(f"wrote: {path.name}")
    return bak


def _already_applied(daily_metrics: dict) -> bool:
    return SENTINEL_KEY in daily_metrics


def reconcile(*, dry_run: bool) -> dict:
    """Top-level reconciliation orchestrator.

    Returns a summary dict for logging / verification.
    """
    summary = {"mode": "dry-run" if dry_run else "apply", "actions": []}
    backup_suffix = f"pre_retroreconcile.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # --- Day 2 EC TP1 reclassify ----------------------------------------
    day2_path = DAILY_METRICS_DIR / "2026-05-19.json"
    day2 = _load_json(day2_path)
    if _already_applied(day2):
        logger.info("Day 2 (2026-05-19): already reconciled — skipping")
        summary["actions"].append({"date": "2026-05-19", "skipped": True})
    else:
        day2_new = reclassify_ec_day2(day2)
        summary["actions"].append({
            "date": "2026-05-19",
            "change": "EC MOC → TP1 reclassify",
            "exits_before": day2.get("exits"),
            "exits_after": day2_new.get("exits"),
        })
        if not dry_run:
            _write_json_backup(day2_path, day2_new, backup_suffix)

    # --- Day 4 VLO SL  + Day 5 ON TP1: build the new state + cumulative -
    cum_path = CUMULATIVE_PNL_PATH
    cum_data = _load_json(cum_path)

    # Apply VLO Day 4 to daily_metrics + cumulative_pnl
    day4_path = DAILY_METRICS_DIR / "2026-05-21.json"
    day4 = _load_json(day4_path)
    if _already_applied(day4):
        logger.info("Day 4 (2026-05-21): already reconciled — skipping")
        summary["actions"].append({"date": "2026-05-21", "skipped": True})
    else:
        # Provisional cumulative: Day 3 cumulative + VLO net = 107.27 - 227.06 = -119.79
        day4_cum = cum_data["daily_history"][2]["pnl"]  # Day 3 entry
        # Sum cumulative across history up to but not including Day 4
        day4_cum_pre = sum(
            e["pnl"] for e in cum_data["daily_history"]
            if e["date"] < "2026-05-21"
        )
        day4_cumulative_after = day4_cum_pre + VLO_DAY4.net
        day4_new = append_trade_to_daily_metrics(day4, VLO_DAY4, day4_cumulative_after)
        summary["actions"].append({
            "date": "2026-05-21",
            "change": f"VLO SL {VLO_DAY4.qty}@{VLO_DAY4.exit} net {VLO_DAY4.net}",
            "cumulative_before": cum_data.get("cumulative_pnl"),
            "cumulative_after": day4_cumulative_after,
        })
        if not dry_run:
            _write_json_backup(day4_path, day4_new, backup_suffix)
        # Update cumulative_pnl daily_history
        cum_data = update_cumulative_history_entry(
            cum_data, "2026-05-21",
            pnl_delta=VLO_DAY4.net,
            commission_delta=VLO_DAY4.commission,
            trades_delta=1,
            filled_delta=1,
            counter_increments={"sl_hits": 1},
        )

    # Apply ON Day 5 to daily_metrics + cumulative_pnl
    day5_path = DAILY_METRICS_DIR / "2026-05-22.json"
    day5 = _load_json(day5_path)
    if _already_applied(day5):
        logger.info("Day 5 (2026-05-22): already reconciled — skipping")
        summary["actions"].append({"date": "2026-05-22", "skipped": True})
    else:
        day5_cum_pre = sum(
            e["pnl"] for e in cum_data["daily_history"]
            if e["date"] < "2026-05-22"
        )
        day5_cumulative_after = day5_cum_pre + ON_DAY5.net
        day5_new = append_trade_to_daily_metrics(day5, ON_DAY5, day5_cumulative_after)
        summary["actions"].append({
            "date": "2026-05-22",
            "change": f"ON TP1 {ON_DAY5.qty}@{ON_DAY5.exit} net {ON_DAY5.net}",
            "cumulative_after": day5_cumulative_after,
        })
        if not dry_run:
            _write_json_backup(day5_path, day5_new, backup_suffix)
        cum_data = update_cumulative_history_entry(
            cum_data, "2026-05-22",
            pnl_delta=ON_DAY5.net,
            commission_delta=ON_DAY5.commission,
            trades_delta=1,
            filled_delta=1,
            counter_increments={"tp1_hits": 1},
        )

    # Day 2 cumulative_pnl counter adjustments (separate from daily_metrics)
    cum_data = update_cumulative_history_entry(
        cum_data, "2026-05-19",
        counter_decrements={"moc_exits": EC_DAY2_RECLASSIFY["moc_exits_decrement"]},
        counter_increments={"tp1_hits": EC_DAY2_RECLASSIFY["tp1_hits_increment"]},
    )

    # Recompute totals
    cum_data = recompute_cumulative_pnl(cum_data)

    if not dry_run:
        _write_json_backup(cum_path, cum_data, backup_suffix)

    summary["final_cumulative_pnl"] = cum_data["cumulative_pnl"]
    summary["expected_final_cumulative"] = EXPECTED_FINAL_CUMULATIVE
    summary["match_expected"] = abs(
        cum_data["cumulative_pnl"] - EXPECTED_FINAL_CUMULATIVE
    ) < 5.0  # Allow $5 commission rounding tolerance

    # --- Swing state cleanup: VLO + ON full remove ---------------------
    swing_state = _load_json(SWING_STATE_PATH)
    before_positions = {p["ticker"] for p in swing_state.get("positions", [])}
    if "VLO" in before_positions or "ON" in before_positions:
        swing_new = remove_closed_positions(swing_state, {"VLO", "ON"})
        summary["actions"].append({
            "swing_positions_before": len(swing_state.get("positions", [])),
            "swing_positions_after": len(swing_new.get("positions", [])),
        })
        if not dry_run:
            _write_json_backup(SWING_STATE_PATH, swing_new, backup_suffix)
    else:
        summary["actions"].append({"swing_positions": "already clean"})

    return summary


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    parser = argparse.ArgumentParser(description="Retroactive W21 reconciliation")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Audit mode — show changes without writing files.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Live mode — write changes with backups.",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.error("Specify either --dry-run or --apply")
    if args.dry_run and args.apply:
        parser.error("--dry-run and --apply are mutually exclusive")

    summary = reconcile(dry_run=args.dry_run)
    print("\n=== Reconcile Summary ===")
    print(json.dumps(summary, indent=2, default=str))

    if not summary.get("match_expected", True):
        logger.warning(
            "Final cumulative_pnl %s differs from expected %s by more than $5. "
            "Review the trade constants and rerun.",
            summary.get("final_cumulative_pnl"),
            summary.get("expected_final_cumulative"),
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
