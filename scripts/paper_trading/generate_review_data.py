#!/usr/bin/env python3
"""Deterministic daily-review data aggregator (autonomous review pipeline 1a).

Reads the LOCAL state/log sources for a trading day and emits a structured
``state/review_data/{date}.json``: computed fields + rule-based anomaly flags.
This module is pure/local — runnable WITHOUT IBKR. The connector-dependent
cross-check (1b: realized P&L gap, state/IBKR divergence, cumulative drift,
per-ticker slippage, stop-proximity) is layered on by the review generator
(1c) when it has IBKR access.

Input sources (all optional — missing → degrade gracefully):
  - scripts/paper_trading/logs/cumulative_pnl.json
  - state/daily_metrics/{date}.json
  - state/swing_positions.json
  - state/uw_shadow/{date}.json
  - logs/pt_{submit,close,monitor,reconcile,eod}_{date}.log

Local anomaly flags (§3 rule-set, the subset computable without IBKR):
  - days_held_calendar_bug (P1), atr_floor_breach (P1), atr_ceiling_breach (P2),
    single_position_concentration (P2), sector_cap_proximity (P2),
    reconcile_silent_ok (positive)

Usage:
    python scripts/paper_trading/generate_review_data.py --date 2026-06-03
    python scripts/paper_trading/generate_review_data.py            # today
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CUM_PNL_FILE = PROJECT_ROOT / "scripts" / "paper_trading" / "logs" / "cumulative_pnl.json"
DAILY_METRICS_DIR = PROJECT_ROOT / "state" / "daily_metrics"
SWING_STATE_FILE = PROJECT_ROOT / "state" / "swing_positions.json"
UW_SHADOW_DIR = PROJECT_ROOT / "state" / "uw_shadow"
LOGS_DIR = PROJECT_ROOT / "logs"
REVIEW_DATA_DIR = PROJECT_ROOT / "state" / "review_data"

INITIAL_CAPITAL = 100_000
SWING_PIVOT_START_DATE = "2026-05-18"
MAX_HOLD_DAYS = 5
ATR_FLOOR = 0.005
ATR_CEILING = 0.05
SINGLE_POS_CAP = 0.12
SECTOR_CAP_PROXIMITY = 0.25


# ---------------------------------------------------------------------------
# Loaders (small, mockable)
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _read_log(name: str, target_date: str) -> list[str]:
    path = LOGS_DIR / f"pt_{name}_{target_date}.log"
    try:
        return path.read_text().splitlines()
    except OSError:
        return []


# ---------------------------------------------------------------------------
# Day numbering
# ---------------------------------------------------------------------------


def _nyse_day_number(target_date: str, start: str = SWING_PIVOT_START_DATE) -> int:
    try:
        from ifds.utils.trading_calendar import trading_days_between

        return len(trading_days_between(date.fromisoformat(start), date.fromisoformat(target_date)))
    except Exception:  # noqa: BLE001 — calendar optional
        s, e = date.fromisoformat(start), date.fromisoformat(target_date)
        return (
            0
            if e < s
            else sum(1 for i in range((e - s).days + 1) if (s + timedelta(days=i)).weekday() < 5)
        )


def _calendar_weekday_number(target_date: str, start: str = SWING_PIVOT_START_DATE) -> int:
    s, e = date.fromisoformat(start), date.fromisoformat(target_date)
    return (
        0
        if e < s
        else sum(1 for i in range((e - s).days + 1) if (s + timedelta(days=i)).weekday() < 5)
    )


# ---------------------------------------------------------------------------
# Position enrichment + anomaly flags
# ---------------------------------------------------------------------------


def _enrich_position(p: dict, target_date: str) -> dict:
    entry_price = float(p.get("entry_price", 0.0) or 0.0)
    atr = float(p.get("atr", 0.0) or 0.0)
    qty = int(p.get("qty_remaining", p.get("qty", 0)) or 0)
    entry_date = p.get("entry_date")
    days_held_trading = p.get("days_held")
    days_held_calendar = None
    if entry_date:
        try:
            days_held_calendar = (
                date.fromisoformat(target_date) - date.fromisoformat(entry_date)
            ).days
        except ValueError:
            days_held_calendar = None
    atr_pct = (atr / entry_price) if entry_price > 0 else None
    notional = entry_price * qty
    return {
        "ticker": p.get("ticker"),
        "sector": p.get("sector", ""),
        "entry_price": round(entry_price, 2),
        "qty_remaining": qty,
        "notional": round(notional, 2),
        "atr": round(atr, 4),
        "atr_pct": round(atr_pct, 4) if atr_pct is not None else None,
        "stop_level": p.get("stop_level"),
        "days_held_trading": days_held_trading,
        "days_held_calendar": days_held_calendar,
        "next_action": p.get("next_action"),
    }


def _local_flags(
    positions: list[dict], sector_dist: dict, reconcile_lines: list[str]
) -> list[dict]:
    """Apply the local (no-IBKR) subset of the §3 anomaly rule-set."""
    flags: list[dict] = []
    equity = float(INITIAL_CAPITAL)

    for ep in positions:
        tk = ep["ticker"]
        # days_held calendar-bug: calendar ≠ trading-day AND near the time-stop
        dh_t, dh_c = ep["days_held_trading"], ep["days_held_calendar"]
        if dh_t is not None and dh_c is not None and dh_t != dh_c and dh_t >= MAX_HOLD_DAYS - 1:
            flags.append(
                {
                    "flag": "days_held_calendar_bug",
                    "priority": "P1",
                    "ticker": tk,
                    "detail": f"days_held trading={dh_t} vs calendar={dh_c} near time-stop",
                }
            )
        # ATR band breaches
        ap = ep["atr_pct"]
        if ap is not None and ap < ATR_FLOOR:
            flags.append(
                {
                    "flag": "atr_floor_breach",
                    "priority": "P1",
                    "ticker": tk,
                    "detail": f"atr_pct {ap:.4f} < {ATR_FLOOR}",
                }
            )
        if ap is not None and ap > ATR_CEILING:
            flags.append(
                {
                    "flag": "atr_ceiling_breach",
                    "priority": "P2",
                    "ticker": tk,
                    "detail": f"atr_pct {ap:.4f} > {ATR_CEILING}",
                }
            )
        # single-position concentration
        if equity > 0 and ep["notional"] / equity > SINGLE_POS_CAP:
            flags.append(
                {
                    "flag": "single_position_concentration",
                    "priority": "P2",
                    "ticker": tk,
                    "detail": f"notional {ep['notional']:.0f} = {ep['notional'] / equity * 100:.1f}% > {SINGLE_POS_CAP * 100:.0f}%",
                }
            )

    # sector cap proximity
    for sector, notional in (sector_dist or {}).items():
        if equity > 0 and notional / equity > SECTOR_CAP_PROXIMITY:
            flags.append(
                {
                    "flag": "sector_cap_proximity",
                    "priority": "P2",
                    "sector": sector,
                    "detail": f"{sector} {notional / equity * 100:.1f}% > {SECTOR_CAP_PROXIMITY * 100:.0f}% (cap 30%)",
                }
            )

    # reconcile silent OK (positive signal)
    if any("silent exit" in ln.lower() or "silent ok" in ln.lower() for ln in reconcile_lines):
        flags.append(
            {
                "flag": "reconcile_silent_ok",
                "priority": "positive",
                "detail": "state ≡ IBKR (reconcile silent OK)",
            }
        )

    return flags


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------


def build_review_data(target_date: str) -> dict:
    """Aggregate the local sources for ``target_date`` into a review_data dict."""
    cum = _load_json(CUM_PNL_FILE) or {}
    metrics = _load_json(DAILY_METRICS_DIR / f"{target_date}.json") or {}
    swing = _load_json(SWING_STATE_FILE) or {}
    uw = _load_json(UW_SHADOW_DIR / f"{target_date}.json")

    daily_entry = next(
        (e for e in cum.get("daily_history", []) if e.get("date") == target_date), {}
    )

    raw_positions = swing.get("positions", []) if isinstance(swing, dict) else []
    positions = [_enrich_position(p, target_date) for p in raw_positions]

    sector_dist: dict[str, float] = {}
    for ep in positions:
        sector_dist[ep["sector"] or "UNKNOWN"] = (
            sector_dist.get(ep["sector"] or "UNKNOWN", 0.0) + ep["notional"]
        )

    new_entries = [ep["ticker"] for ep in positions if ep["days_held_calendar"] == 0] or (
        metrics.get("swing_state", {}) or {}
    ).get("new_entries_tickers", [])

    reconcile_lines = _read_log("reconcile", target_date)
    flags = _local_flags(positions, sector_dist, reconcile_lines)

    nyse_n = _nyse_day_number(target_date)
    cal_n = _calendar_weekday_number(target_date)

    uw_summary = {}
    if isinstance(uw, dict):
        uw_summary = {
            "tickers_logged": uw.get("tickers_logged", len(uw) if uw else 0),
        }
    elif isinstance(uw, list):
        uw_summary = {"tickers_logged": len(uw)}

    return {
        "date": target_date,
        "day_number": {
            "nyse_trading": nyse_n,
            "calendar_weekday": cal_n,
            "cumulative_trading_days": cum.get("trading_days"),
            "inconsistent": nyse_n != cal_n,
        },
        "pnl": {
            "realized_today": daily_entry.get("pnl"),
            "commission": daily_entry.get("commission"),
            "cumulative": cum.get("cumulative_pnl"),
            "cumulative_pct": cum.get("cumulative_pnl_pct"),
        },
        "exits": {
            "tp1": daily_entry.get("tp1_hits", 0),
            "tp2": daily_entry.get("tp2_hits", 0),
            "sl": daily_entry.get("sl_hits", 0),
            "loss_exit": daily_entry.get("loss_exit_hits", 0),
            "trail": daily_entry.get("trail_hits", 0),
            "moc": daily_entry.get("moc_exits", 0),
        },
        "positions": {
            "open_count": len(positions),
            "new_entries": new_entries,
            "sector_distribution": {k: round(v, 2) for k, v in sector_dist.items()},
            "sector_pct": {k: round(v / INITIAL_CAPITAL * 100, 2) for k, v in sector_dist.items()},
            "detail": positions,
        },
        "uw_shadow": uw_summary,
        "flags": flags,
        "source_note": "1a deterministic local aggregate; IBKR cross-check (1b) added by 1c",
    }


def main() -> None:
    import logging

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("generate_review_data")

    parser = argparse.ArgumentParser(description="Daily-review data aggregator (1a)")
    parser.add_argument("--date", help="YYYY-MM-DD (default: today)")
    args = parser.parse_args()
    target_date = args.date or date.today().isoformat()

    data = build_review_data(target_date)
    REVIEW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REVIEW_DATA_DIR / f"{target_date}.json"
    out_path.write_text(json.dumps(data, indent=2))
    n_flags = len(data["flags"])
    logger.info(
        "review_data written: %s — Day %s (NYSE), %d positions, %d flags",
        out_path,
        data["day_number"]["nyse_trading"],
        data["positions"]["open_count"],
        n_flags,
    )


if __name__ == "__main__":
    main()
