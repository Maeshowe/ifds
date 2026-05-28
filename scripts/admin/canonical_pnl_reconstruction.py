#!/usr/bin/env python3
"""Canonical P&L reconstruction — rebuild cumulative_pnl.json from IBKR truth.

P0 fix (04-risks §0.11, 2026-05-28): the ``close_positions.py`` exits (TP2/MOC/SL)
never wrote realized P&L back to ``cumulative_pnl.json`` / ``daily_metrics``. The
W21 retroactive reconcile (``retroactive_reconcile_w21.py``, 2026-05-25) patched
Day 2-5 with *approximate* numbers, but Day 8 (2026-05-27) — 7 exits, -$695.79
realized — fell through entirely. Official tracking showed +$39.33; IBKR truth is
-$651.10 realized (a $690 over-statement).

This script does a **full-history idempotent rebuild** of ``cumulative_pnl.json``
``daily_history`` from the IBKR-canonical per-day realized P&L (source:
``get_account_trades`` via the IBKR MCP connector, 2026-05-28; each fill carries
IBKR's own ``realized_pnl`` field, cross-validated against
``proceeds - cost - commission`` to ±$0.02).

Idempotent: it REPLACES daily_history wholesale with the canonical constants, so
re-running yields an identical file. Safe to run multiple times.

Convention (matches the existing schema + retroactive_reconcile_w21.py):
  - ``pnl`` per day = NET realized (IBKR realized_pnl; commission already deducted).
    ``recompute`` sums these → ``cumulative_pnl``.
  - ``commission`` per day = IBKR per-day total commission (buy+sell), INFORMATIONAL
    only (the net is already in ``pnl``). Do NOT compute gross as pnl+commission
    per-day — the day-total includes entry-leg commissions. Portfolio-level:
    gross -$628.18 + commission -$22.92 = net -$651.10.

Usage:
    python scripts/admin/canonical_pnl_reconstruction.py --dry-run   # show diff
    python scripts/admin/canonical_pnl_reconstruction.py --apply     # backup + write
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger("canonical_pnl")

REPO_ROOT = Path(__file__).resolve().parents[2]
CUMULATIVE_PNL_PATH = REPO_ROOT / "scripts" / "paper_trading" / "logs" / "cumulative_pnl.json"

# Expected cumulative after rebuild — sanity gate.
EXPECTED_CUMULATIVE = -651.10
CUMULATIVE_TOLERANCE = 0.05


def _entry(
    date: str,
    pnl: float,
    commission: float,
    trades: int = 0,
    *,
    tp1: int = 0,
    tp2: int = 0,
    sl: int = 0,
    trail: int = 0,
    moc: int = 0,
    loss_exit: int = 0,
) -> dict:
    """Build one daily_history entry in the canonical schema."""
    return {
        "date": date,
        "pnl": pnl,
        "commission": commission,
        "trades": trades,
        "filled": trades,
        "tp1_hits": tp1,
        "tp2_hits": tp2,
        "sl_hits": sl,
        "loss_exit_hits": loss_exit,
        "trail_hits": trail,
        "moc_exits": moc,
    }


# IBKR-canonical realized P&L per trading day (NET). Source: get_account_trades
# (DAYS_30) 2026-05-28, SELL fills since 2026-05-18, AVDL.CVR corporate-action
# excluded. See module docstring for provenance + cross-validation.
CANONICAL_HISTORY: list[dict] = [
    _entry("2026-05-18", 0.00, 0.00, trades=0),                       # Day 1 — entries only
    _entry("2026-05-19", 112.63, 2.08, trades=1, tp1=1),             # EC TP1
    _entry("2026-05-20", -6.37, 5.01, trades=1),                     # VLO IFDS_DEBUG 1-share cleanup
    _entry("2026-05-21", -220.69, 3.08, trades=1, sl=1),            # VLO SL (Tamás Day 3 TWS bracket)
    _entry("2026-05-22", 159.12, 2.32, trades=1, tp1=1),           # ON TP1 (Tamás Day 3 TWS bracket)
    _entry("2026-05-26", 0.00, 0.00, trades=0),                     # Day 7 — EOG+AKAM entries only, no exits
    _entry("2026-05-27", -695.79, 9.48, trades=7, tp2=1, moc=6),  # EC TP2 + 6× TIME_STOP MOC
]


def recompute(cum_data: dict) -> dict:
    """Recalculate cumulative_pnl + pct + trading_days from daily_history net pnl."""
    out = dict(cum_data)
    history = out.get("daily_history", [])
    cum = round(sum(e.get("pnl", 0.0) for e in history), 2)
    initial = out.get("initial_capital", 100_000)
    out["cumulative_pnl"] = cum
    out["cumulative_pnl_pct"] = round(cum / initial * 100, 3)
    out["trading_days"] = len(history)
    return out


def rebuild(cum_data: dict) -> dict:
    """Replace daily_history with the canonical history and recompute totals.

    Preserves ``start_date`` + ``initial_capital``; everything else derives from
    CANONICAL_HISTORY. Idempotent (full replace).
    """
    out = dict(cum_data)
    out["daily_history"] = [dict(e) for e in CANONICAL_HISTORY]
    return recompute(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Canonical cumulative_pnl.json rebuild")
    parser.add_argument("--apply", action="store_true", help="Write the file (default: dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Show diff without writing")
    args = parser.parse_args()
    apply = args.apply and not args.dry_run

    if not CUMULATIVE_PNL_PATH.exists():
        logger.error(f"Not found: {CUMULATIVE_PNL_PATH}")
        raise SystemExit(1)

    current = json.loads(CUMULATIVE_PNL_PATH.read_text())
    rebuilt = rebuild(current)

    # Sanity gate — the rebuild must land on the verified canonical cumulative.
    cum = rebuilt["cumulative_pnl"]
    if abs(cum - EXPECTED_CUMULATIVE) > CUMULATIVE_TOLERANCE:
        logger.error(
            f"ABORT: rebuilt cumulative {cum} != expected {EXPECTED_CUMULATIVE} "
            f"(tolerance {CUMULATIVE_TOLERANCE}). Check CANONICAL_HISTORY."
        )
        raise SystemExit(2)

    logger.info("=== Canonical P&L reconstruction ===")
    logger.info(f"  cumulative_pnl:  {current.get('cumulative_pnl')} → {cum}")
    logger.info(f"  cumulative_pct:  {current.get('cumulative_pnl_pct')} → {rebuilt['cumulative_pnl_pct']}")
    logger.info(f"  trading_days:    {current.get('trading_days')} → {rebuilt['trading_days']}")
    logger.info("  daily_history (net pnl per day):")
    for e in rebuilt["daily_history"]:
        logger.info(f"    {e['date']}  net={e['pnl']:>9.2f}  comm={e['commission']:>5.2f}  "
                    f"trades={e['trades']}  tp1={e['tp1_hits']} tp2={e['tp2_hits']} "
                    f"sl={e['sl_hits']} moc={e['moc_exits']}")

    if not apply:
        logger.info("DRY-RUN — no file written. Re-run with --apply to commit.")
        return

    backup = CUMULATIVE_PNL_PATH.with_suffix(
        CUMULATIVE_PNL_PATH.suffix + f".bak.pre_canonical.{datetime.now():%Y%m%d_%H%M%S}"
    )
    shutil.copy2(CUMULATIVE_PNL_PATH, backup)
    logger.info(f"backup: {backup.name}")
    CUMULATIVE_PNL_PATH.write_text(json.dumps(rebuilt, indent=4))
    logger.info(f"wrote: {CUMULATIVE_PNL_PATH.name} (cumulative {cum})")


if __name__ == "__main__":
    main()
