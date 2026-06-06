#!/usr/bin/env python3
"""IFDS Paper Trading — Daily Metrics Collection.

Runs at 22:10 CEST (after EOD report at 22:05). Reads pipeline outputs
and trade results to produce a structured daily metrics JSON for
walk-forward scoring validation.

Usage:
    python scripts/paper_trading/daily_metrics.py
    python scripts/paper_trading/daily_metrics.py --date 2026-04-10  # backfill
"""

from __future__ import annotations

import argparse
import csv
import glob
import gzip
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

try:
    from lib.log_setup import setup_pt_logger

    logger = setup_pt_logger("daily_metrics")
except ModuleNotFoundError:
    import logging

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )
    logger = logging.getLogger("daily_metrics")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CUM_PNL_FILE = PROJECT_ROOT / "scripts" / "paper_trading" / "logs" / "cumulative_pnl.json"
TRADES_DIR = PROJECT_ROOT / "scripts" / "paper_trading" / "logs"
EXEC_PLAN_DIR = PROJECT_ROOT / "output"
PHASE4_DIR = PROJECT_ROOT / "state" / "phase4_snapshots"
METRICS_DIR = PROJECT_ROOT / "state" / "daily_metrics"
LOGS_DIR = PROJECT_ROOT / "logs"
UW_SHADOW_DIR = PROJECT_ROOT / "state" / "uw_shadow"
PENDING_EXITS_DIR = PROJECT_ROOT / "state" / "pending_exits"
INITIAL_CAPITAL = 100_000

# clientId for the record_pending_exits IBKR connection (P0 §0.11 Part A).
# Distinct from submit=10/close=11/eod=12/nuke=13/monitor=14/trail=15/
# avwap=16/gateway=17 to avoid session takeover.
RECORD_PENDING_CLIENT_ID = 18

# Swing exit_type → cumulative_pnl.json daily_history counter key.
EXIT_TYPE_TO_COUNTER = {
    "TP1": "tp1_hits",
    "TP2": "tp2_hits",
    "SL": "sl_hits",
    "HARD_SL": "sl_hits",
    "MENTAL_SL": "sl_hits",
    "TRAIL_SL": "trail_hits",
    "TRAIL": "trail_hits",
    "LOSS_EXIT": "loss_exit_hits",
    "MOC": "moc_exits",
    "TIME_STOP": "moc_exits",
}

SWING_PIVOT_START_DATE_DEFAULT = "2026-05-18"


def compute_trading_day_number(target_date: str, start_date: str | None = None) -> int:
    """Day-N as the NYSE trading-day count from the swing-pivot start (inclusive).

    Telegram-finomítás §1: the canonical Day-N is the number of NYSE trading
    days in [start_date, target_date] (Memorial Day etc. excluded), NOT
    ``cumulative_pnl.trading_days`` (which only counts days with a P&L entry →
    understated on no-exit days). Consistent with ``days_held`` being
    trading-day based. Falls back to a weekday count if the calendar is
    unavailable.
    """
    start = start_date or SWING_PIVOT_START_DATE_DEFAULT
    try:
        from ifds.utils.trading_calendar import trading_days_between

        return len(trading_days_between(date.fromisoformat(start), date.fromisoformat(target_date)))
    except Exception:  # noqa: BLE001 — calendar optional; weekday fallback
        s = date.fromisoformat(start)
        e = date.fromisoformat(target_date)
        if e < s:
            return 0
        return sum(1 for i in range((e - s).days + 1) if (s + timedelta(days=i)).weekday() < 5)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _load_cumulative_pnl() -> dict:
    if not CUM_PNL_FILE.exists():
        return {}
    with open(CUM_PNL_FILE) as f:
        return json.load(f)


def _find_daily_entry(cum_data: dict, target_date: str) -> dict:
    """Find the daily_history entry for a specific date."""
    for entry in cum_data.get("daily_history", []):
        if entry.get("date") == target_date:
            return entry
    return {}


def _load_trades(target_date: str) -> list[dict]:
    path = TRADES_DIR / f"trades_{target_date}.csv"
    if not path.exists():
        return []
    trades = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                trades.append(
                    {
                        "ticker": row["ticker"],
                        "score": float(row.get("score", 0) or 0),
                        "entry_price": float(row["entry_price"]),
                        "exit_price": float(row["exit_price"]),
                        "pnl": float(row["pnl"]),
                        "pnl_pct": float(row["pnl_pct"]),
                        "exit_type": row["exit_type"],
                        "sector": row.get("sector", ""),
                        "commission": float(row.get("commission", 0) or 0),
                    }
                )
            except (KeyError, ValueError):
                continue
    return trades


def _load_execution_plan(target_date: str) -> dict[str, dict]:
    """Load planned entries from execution plan CSV. Returns {ticker: row}."""
    date_str = target_date.replace("-", "")
    pattern = str(EXEC_PLAN_DIR / f"execution_plan_run_{date_str}_*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        return {}
    planned: dict[str, dict] = {}
    with open(files[-1], newline="") as f:
        for row in csv.DictReader(f):
            planned[row["instrument_id"]] = {
                "limit_price": float(row["limit_price"]),
                "quantity": int(row["quantity"]),
                "score": float(row.get("score", 0) or 0),
                "multiplier_total": float(row.get("multiplier_total", 1) or 1),
                "risk_usd": float(row.get("risk_usd", 0) or 0),
            }
    return planned


def _build_swing_state(target_date: str, planned: dict, snapshot: list) -> dict:
    """Task #5 §2: swing_state metrics block.

    Reads ``state/swing_positions.json`` and aggregates the swing portfolio view
    for the daily Telegram report:
      - open_positions, new_entries_today, total_notional
      - sector_distribution
      - sector_observed_max_pct (computed daily max sector share — display)
      - sector_cap_pct (explicit config from swing_sector_cap_pct × 100 — display)
      - avg/max days_held
      - next_day_planned (15:30 exits + 21:40 TIME_STOPs)
      - swing_score_distribution (qualifying threshold count, top 3 scores)

    Note on sector metrics semantics
    --------------------------------
    The 2026-05-20 Day 3 daily review §0.6 mistakenly interpreted the
    pre-rename ``sector_max_pct`` field as a config cap (15%), which led to
    a false-positive "P0 hotfix" task (`docs/tasks/2026-05-21-sector-cap-
    hotfix.md`, REJECTED).  To prevent recurrence the two distinct concepts
    are now serialized under disambiguating keys:

    * ``sector_observed_max_pct`` — max(sector_share) across current
      positions, observed daily metric.
    * ``sector_cap_pct`` — ``swing_sector_cap_pct × 100`` from the config
      (Day 63 decision §3.11 = 30%), explicit so any downstream reader can
      compare observed vs cap without consulting `defaults.py`.

    Refs: docs/tasks/2026-05-21-sector-metric-clarity.md
    """
    try:
        from ifds.config.loader import Config
        from ifds.state.swing_positions import load_swing_positions
    except ImportError:
        return {}

    try:
        cfg = Config()
        state_file = cfg.tuning.get(
            "swing_positions_state_file",
            "state/swing_positions.json",
        )
        max_concurrent = int(cfg.tuning.get("swing_max_concurrent", 12))
        threshold = float(cfg.tuning.get("swing_score_threshold", 50.0))
        equity = float(cfg.runtime.get("account_equity", 100_000.0))
        sector_cap_pct = float(cfg.tuning.get("swing_sector_cap_pct", 0.30)) * 100
    except Exception:
        state_file = "state/swing_positions.json"
        max_concurrent = 12
        threshold = 50.0
        equity = 100_000.0
        sector_cap_pct = 30.0

    positions = load_swing_positions(state_file)

    new_entries = [p for p in positions if p.entry_date == target_date]
    total_notional = sum(p.entry_price * p.qty_remaining for p in positions)

    sector_distribution: dict[str, float] = {}
    for p in positions:
        sector = p.sector or "UNKNOWN"
        sector_distribution[sector] = (
            sector_distribution.get(sector, 0.0) + p.entry_price * p.qty_remaining
        )
    sector_observed_max_pct = (
        max(v / equity * 100 for v in sector_distribution.values()) if sector_distribution else 0.0
    )

    if positions:
        avg_days_held = sum(p.days_held for p in positions) / len(positions)
        max_days_held = max(p.days_held for p in positions)
    else:
        avg_days_held = 0.0
        max_days_held = 0

    exits_today: dict[str, int] = {}
    next_day_exits_1530: list[str] = []
    next_day_time_stops: list[str] = []
    for p in positions:
        action = p.next_action
        if action and action != "HOLD":
            exits_today[action] = exits_today.get(action, 0) + 1
            label = f"{p.ticker}_{action}"
            if action == "TIME_STOP":
                next_day_time_stops.append(label)
            else:
                next_day_exits_1530.append(label)

    qualifying = 0
    top_scores: list[dict] = []
    if snapshot:
        # _load_phase4_snapshot returns {ticker: data}; tests pass list-of-rows.
        rows = list(snapshot.values()) if isinstance(snapshot, dict) else list(snapshot)
        scored = sorted(rows, key=lambda r: float(r.get("combined_score", 0.0)), reverse=True)
        qualifying = sum(1 for r in scored if float(r.get("combined_score", 0.0)) >= threshold)
        for r in scored[:3]:
            top_scores.append(
                {
                    "ticker": r.get("ticker", "?"),
                    "S_j": round(float(r.get("combined_score", 0.0)), 1),
                    "sector": r.get("sector", ""),
                }
            )

    return {
        "open_positions": len(positions),
        "max_concurrent": max_concurrent,
        "new_entries_today": len(new_entries),
        "new_entries_tickers": [p.ticker for p in new_entries],
        "held_tickers": [p.ticker for p in positions],  # §5: Top S_j status labels
        "total_notional": round(total_notional, 2),
        "total_notional_pct_equity": round(total_notional / equity * 100, 2) if equity > 0 else 0.0,
        "sector_distribution": {k: round(v, 2) for k, v in sector_distribution.items()},
        "sector_observed_max_pct": round(sector_observed_max_pct, 2),
        "sector_cap_pct": round(sector_cap_pct, 2),
        "avg_days_held": round(avg_days_held, 2),
        "max_days_held": max_days_held,
        "exits_today": exits_today,
        "next_day_planned": {
            "exits_at_1530": next_day_exits_1530,
            "time_stops_at_2140": next_day_time_stops,
        },
        "swing_score_distribution": {
            "qualifying_threshold_50": qualifying,
            "threshold": threshold,
            "selected_for_entry": len(new_entries),
            "top_3_scores": top_scores,
        },
    }


def _load_uw_shadow_summary(target_date: str) -> dict:
    """Load and summarize the daily UW shadow snapshot (Day 63 §3.2).

    Returns an empty-but-typed dict if no snapshot for the date exists.
    """
    path = UW_SHADOW_DIR / f"{target_date}.json"
    if not path.exists():
        return {
            "snapshot_path": None,
            "tickers_logged": 0,
            "avg_dp_pct": 0.0,
            "would_have_been_penalty_count": 0,
            "gex_regime_distribution": {},
            "m_gex_avg_would_have_been": 1.0,
        }
    try:
        snapshot = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("UW shadow snapshot unreadable for %s: %s", target_date, exc)
        return {
            "snapshot_path": str(path),
            "tickers_logged": 0,
            "avg_dp_pct": 0.0,
            "would_have_been_penalty_count": 0,
            "gex_regime_distribution": {},
            "m_gex_avg_would_have_been": 1.0,
        }

    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from ifds.data.uw_shadow import summarize_shadow_snapshot

    summary = summarize_shadow_snapshot(snapshot)
    summary["snapshot_path"] = str(path)
    return summary


def _load_phase4_snapshot(target_date: str) -> dict[str, dict]:
    """Load Phase 4 snapshot. Returns {ticker: data}."""
    path = PHASE4_DIR / f"{target_date}.json.gz"
    if not path.exists():
        return {}
    with gzip.open(path) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return {}
    if not isinstance(data, list):
        return {}
    return {row["ticker"]: row for row in data if "ticker" in row}


def _load_phase0_vix(target_date: str, logs_dir: Path | None = None) -> float | None:
    """Parse VIX close from Phase 0 MACRO_REGIME events for target_date.

    Reads ``logs/ifds_run_YYYYMMDD_*.jsonl`` and returns the most recent
    ``data.vix_value`` from a MACRO_REGIME event in phase 0. Returns None
    if no log exists or no event carries vix_value.
    """
    base = logs_dir or LOGS_DIR
    date_str = target_date.replace("-", "")
    pattern = str(base / f"ifds_run_{date_str}_*.jsonl")
    files = sorted(glob.glob(pattern))
    if not files:
        return None

    latest_vix: float | None = None
    for log_path in files:
        try:
            with open(log_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event.get("event_type") != "MACRO_REGIME":
                        continue
                    if event.get("phase") != 0:
                        continue
                    data = event.get("data")
                    if not isinstance(data, dict):
                        continue
                    vix_value = data.get("vix_value")
                    if isinstance(vix_value, (int, float)):
                        latest_vix = float(vix_value)
        except OSError:
            continue
    return latest_vix


def _fetch_vix_from_polygon(target_date: str) -> tuple[float | None, float | None]:
    """Fetch ``(close, prev_close)`` for I:VIX from Polygon for target_date.

    Polygon ``I:VIX`` is the authoritative same-day VIX source: FRED
    publishes VIX with a 1-day lag (EOD batch), so the Phase 0 MACRO_REGIME
    event (FRED-sourced) systematically reports the Day N-1 close on Day N.

    Returns the close of the bar dated ``target_date`` and the close of the
    immediately preceding trading-day bar (for a self-consistent delta).
    Either element is ``None`` when its bar is unavailable; ``close`` is
    ``None`` (triggering the caller's fallback) when no bar matches
    ``target_date`` — never the stale latest bar.
    """
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from ifds.data.polygon import PolygonClient
    except ImportError:
        return None, None

    api_key = os.environ.get("IFDS_POLYGON_API_KEY")
    if not api_key:
        return None, None

    from_date = (date.fromisoformat(target_date) - timedelta(days=10)).isoformat()
    try:
        client = PolygonClient(api_key)
        bars = client.get_aggregates("I:VIX", from_date, target_date, timespan="day")
    except Exception as e:
        logger.warning(f"VIX fetch failed: {e}")
        return None, None

    if not bars:
        return None, None

    dated: list[tuple[date, float]] = []
    for bar in bars:
        ts = bar.get("t")
        close = bar.get("c")
        if ts is None or close is None:
            continue
        bar_date = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date()
        dated.append((bar_date, float(close)))
    dated.sort(key=lambda item: item[0])
    if not dated:
        return None, None

    target = date.fromisoformat(target_date)
    close_val = next((c for d, c in dated if d == target), None)
    if close_val is None:
        return None, None

    prev_val: float | None = None
    for d, c in dated:
        if d < target:
            prev_val = c  # dated is ascending → keep last bar strictly before target
    return close_val, prev_val


def _load_previous_vix_close(target_date: str) -> float | None:
    """Read vix_close from the previous trading day's daily_metrics.json (if any)."""
    try:
        cur = date.fromisoformat(target_date)
    except ValueError:
        return None
    for back in range(1, 8):
        prev = (cur - timedelta(days=back)).isoformat()
        path = METRICS_DIR / f"{prev}.json"
        if not path.exists():
            continue
        try:
            with open(path) as f:
                prev_data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        prev_vix = (prev_data.get("market") or {}).get("vix_close")
        if isinstance(prev_vix, (int, float)):
            return float(prev_vix)
    return None


def _fetch_spy_return(target_date: str) -> float | None:
    """Fetch SPY daily return from Polygon (single API call)."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from ifds.data.polygon import PolygonClient
    except ImportError:
        return None

    api_key = os.environ.get("IFDS_POLYGON_API_KEY")
    if not api_key:
        return None

    prev_date = (date.fromisoformat(target_date) - timedelta(days=5)).isoformat()
    try:
        client = PolygonClient(api_key)
        bars = client.get_aggregates("SPY", prev_date, target_date, timespan="day")
    except Exception as e:
        logger.warning(f"SPY fetch failed: {e}")
        return None

    if not bars or len(bars) < 2:
        return None

    bars_sorted = sorted(bars, key=lambda b: b.get("t", 0))
    prev_close = bars_sorted[-2].get("c")
    today_close = bars_sorted[-1].get("c")
    if prev_close and today_close and prev_close > 0:
        return (today_close - prev_close) / prev_close * 100
    return None


# ---------------------------------------------------------------------------
# Pending-exit recorder — SOLE cumulative_pnl.json writer for swing exits
# (P0 §0.11 Part A). Routes around the eod_report clientId-12 ib.fills()
# cross-client blind spot that silently dropped Day 9 AMH realized P&L.
# ---------------------------------------------------------------------------


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON to ``path`` atomically (temp file + os.replace)."""
    import tempfile

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


def apply_pending_exits(
    cum_data: dict,
    target_date: str,
    unprocessed_records: list[dict],
    executions: list[dict],
) -> tuple[dict, list[str], list[dict]]:
    """Pure: match unprocessed ledger entries to SLD executions and apply
    realized P&L deltas to ``cum_data``.

    Returns ``(new_cum_data, matched_keys, warnings)``. Immutable input —
    threads each match through ``update_cumulative_history_entry`` (which
    copies) and recomputes the cumulative totals only if anything matched.

    Matching is by ticker: all of the day's SLD fills for a ticker are
    aggregated (qty-weighted avg fill price, summed commission). A ledger
    entry with no matching SLD execution is left unprocessed and surfaced
    as a warning — never fabricated. A second ledger entry for an already-
    consumed ticker is skipped (guards against double counting).
    """
    from lib.ibkr_reconciliation import (
        compute_pnl,
        recompute_cumulative_pnl,
        update_cumulative_history_entry,
    )

    sld_by_ticker: dict[str, list[dict]] = {}
    for ex in executions:
        if ex.get("side") != "SLD":
            continue
        sld_by_ticker.setdefault(ex["ticker"], []).append(ex)

    out = cum_data
    matched_keys: list[str] = []
    warnings: list[dict] = []
    used_tickers: set[str] = set()

    for rec in unprocessed_records:
        ticker = rec["ticker"]
        if ticker in used_tickers:
            warnings.append({"key": rec["key"], "reason": "duplicate_ticker_same_day"})
            continue
        sld_list = sld_by_ticker.get(ticker, [])
        if not sld_list:
            warnings.append({"key": rec["key"], "reason": "no_matching_execution"})
            continue
        total_qty = sum(e["shares"] for e in sld_list)
        if total_qty <= 0:
            warnings.append({"key": rec["key"], "reason": "zero_qty_execution"})
            continue

        weighted_price = sum(e["price"] * e["shares"] for e in sld_list) / total_qty
        commission = round(sum((e.get("commission") or 0.0) for e in sld_list), 2)
        counter = EXIT_TYPE_TO_COUNTER.get(rec["exit_type"], "moc_exits")

        # Option B (P0 §0.11): prefer the IBKR broker-authoritative realized_pnl
        # (already NET of commission) so swing exits use the SAME basis as the
        # Day 1-9 canonical reconstruction. Fall back to swing-attribution
        # (planned state.entry_price) only if any matched SLD fill lacks
        # realized_pnl (e.g. historical backfill where reqExecutions can't reach
        # the commissionReport) — surfaced as a warning, never silent.
        rpnls = [e.get("realized_pnl") for e in sld_list]
        if rpnls and all(r is not None for r in rpnls):
            net = round(sum(rpnls), 2)
            pnl_source = "broker_realized_pnl"
        else:
            gross = compute_pnl(rec["entry_price"], weighted_price, int(total_qty))
            net = round(gross - commission, 2)
            pnl_source = "state_attribution_fallback"
            warnings.append({"key": rec["key"], "reason": "realized_pnl_unavailable_fallback"})

        if int(total_qty) != int(rec.get("qty", total_qty)):
            warnings.append(
                {
                    "key": rec["key"],
                    "reason": "qty_mismatch",
                    "ledger_qty": rec.get("qty"),
                    "filled_qty": int(total_qty),
                }
            )

        out = update_cumulative_history_entry(
            out,
            target_date,
            pnl_delta=net,
            commission_delta=commission,
            trades_delta=1,
            filled_delta=1,
            counter_increments={counter: 1},
        )
        matched_keys.append(rec["key"])
        used_tickers.add(ticker)
        logger.info(
            "record_pending_exits: %s %s qty=%d @ %.4f → net $%+.2f (%s, %s)",
            rec["ticker"],
            rec["exit_type"],
            int(total_qty),
            weighted_price,
            net,
            counter,
            pnl_source,
        )

    if matched_keys:
        out = recompute_cumulative_pnl(out)

    return out, matched_keys, warnings


def record_pending_exits(
    target_date: str,
    *,
    dry_run: bool = False,
    ledger_dir: str | None = None,
    ib: object | None = None,
) -> dict:
    """Capture swing-exit realized P&L for ``target_date`` into cumulative_pnl.

    Loads the pending-exit ledger, matches each unprocessed entry to its
    IBKR SLD fill, writes the realized P&L delta to cumulative_pnl.json
    (atomic), and marks the ledger entries processed. Idempotent: a re-run
    skips already-processed keys, so no double counting.

    Returns early (no IBKR connect) when there is nothing to process.
    ``ledger_dir`` / ``ib`` are injectable for testing.
    """
    from lib.pending_exits import load_pending_exits, mark_processed

    ledger_dir = ledger_dir or str(PENDING_EXITS_DIR)
    records = load_pending_exits(target_date, ledger_dir)
    unprocessed = [r for r in records if not r.get("processed")]

    summary = {
        "date": target_date,
        "ledger_records": len(records),
        "unprocessed": len(unprocessed),
        "matched": 0,
        "matched_keys": [],
        "warnings": [],
        "connected": False,
        "dry_run": dry_run,
        "cumulative_pnl": None,
    }

    if not unprocessed:
        logger.info(f"record_pending_exits: no unprocessed ledger entries for {target_date}")
        # §5.4: ensure a (zero) daily_history entry exists for this trading day
        # so the cumulative history has no gaps on no-exit days. record_pending_exits
        # stays the SOLE cumulative_pnl writer; this only creates a missing
        # zero-row (never touches an existing entry).
        try:
            from lib.ibkr_reconciliation import (
                recompute_cumulative_pnl,
                update_cumulative_history_entry,
            )

            cum_data = _load_cumulative_pnl()
            has_entry = any(e.get("date") == target_date for e in cum_data.get("daily_history", []))
            if cum_data and not has_entry:
                new_cum = recompute_cumulative_pnl(
                    update_cumulative_history_entry(cum_data, target_date)
                )
                if not dry_run:
                    _atomic_write_json(CUM_PNL_FILE, new_cum)
                summary["created_zero_entry"] = True
                logger.info(
                    f"record_pending_exits: created zero entry for no-exit day {target_date}"
                )
        except Exception as exc:  # noqa: BLE001 — zero-entry bookkeeping must not break the run
            logger.warning(f"record_pending_exits zero-entry failed: {exc}")
        return summary

    own_ib = None
    try:
        if ib is None:
            from lib.connection import connect

            ib = connect(
                client_id=RECORD_PENDING_CLIENT_ID,
                context_label="daily_metrics.record_pending_exits",
            )
            own_ib = ib
        summary["connected"] = True

        from lib.ibkr_reconciliation import fetch_today_executions

        td = date.fromisoformat(target_date)
        executions = fetch_today_executions(ib, td)
        logger.info(f"record_pending_exits: {len(executions)} executions fetched for {target_date}")

        cum_data = _load_cumulative_pnl()
        new_cum, matched_keys, warnings = apply_pending_exits(
            cum_data, target_date, unprocessed, executions
        )

        summary["matched"] = len(matched_keys)
        summary["matched_keys"] = matched_keys
        summary["warnings"] = warnings

        for w in warnings:
            logger.warning("record_pending_exits warning: %s", w)

        if matched_keys and not dry_run:
            _atomic_write_json(CUM_PNL_FILE, new_cum)
            mark_processed(target_date, set(matched_keys), ledger_dir)
            summary["cumulative_pnl"] = new_cum.get("cumulative_pnl")
            logger.info(
                "record_pending_exits: %d exits recorded, cumulative now $%+.2f",
                len(matched_keys),
                new_cum.get("cumulative_pnl", 0.0),
            )
        else:
            summary["cumulative_pnl"] = new_cum.get("cumulative_pnl")
    finally:
        if own_ib is not None:
            try:
                from lib.connection import disconnect

                disconnect(own_ib)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"record_pending_exits disconnect failed: {exc}")

    return summary


# ---------------------------------------------------------------------------
# Metrics calculation
# ---------------------------------------------------------------------------


def build_daily_metrics(target_date: str) -> dict:
    """Build the complete daily metrics JSON for a given date."""
    cum_data = _load_cumulative_pnl()
    daily = _find_daily_entry(cum_data, target_date)
    trades = _load_trades(target_date)
    planned = _load_execution_plan(target_date)
    snapshot = _load_phase4_snapshot(target_date)
    uw_shadow_summary = _load_uw_shadow_summary(target_date)
    swing_state = _build_swing_state(target_date, planned, snapshot)

    # --- Positions ---
    qualified_count = len(snapshot) if snapshot else 0
    threshold = 85  # BC23 dynamic_position_score_threshold

    # --- Scoring ---
    scores = {t["ticker"]: t["score"] for t in trades if t["score"] > 0}
    avg_score = sum(scores.values()) / len(scores) if scores else 0
    min_score = min(scores.values()) if scores else 0
    max_score = max(scores.values()) if scores else 0

    # --- Slippage ---
    slippage: dict[str, dict] = {}
    for t in trades:
        sym = t["ticker"]
        if sym in planned:
            p = planned[sym]["limit_price"]
            f = t["entry_price"]
            slippage[sym] = {
                "planned": p,
                "filled": f,
                "slippage_pct": round((f - p) / p * 100, 2) if p > 0 else 0,
            }
    avg_slippage = (
        sum(s["slippage_pct"] for s in slippage.values()) / len(slippage) if slippage else 0
    )

    # --- Commission / Exits / P&L ---
    # Swing-era metadata-sync (P0 §0.11 #3b + Day 14 fix): the exits/commission/
    # P&L come from the cumulative_pnl daily_history entry that
    # record_pending_exits populates (Part A) WHENEVER that entry exists — it is
    # the authoritative exit-type + realized source. The eod trades CSV is NOT
    # used for these because it mislabels swing exits (everything → MOC) and can
    # miss cross-client MOC fills (e.g. the 2026-06-03 EOG TIME_STOP), and its
    # presence is non-deterministic (depends on whether ib.fills() saw the exit
    # by 22:05). The CSV still feeds scoring/slippage (per-trade data the
    # recorder doesn't track). The daily_history ``pnl`` is NET (Option B);
    # gross is reconstructed as net + commission.
    _DAILY_COUNTER_MAP = {
        "tp1": "tp1_hits",
        "tp2": "tp2_hits",
        "sl": "sl_hits",
        "loss_exit": "loss_exit_hits",
        "trail": "trail_hits",
        "moc": "moc_exits",
    }
    if daily:
        commission_total = float(daily.get("commission", 0.0) or 0.0)
        exits_block = {k: int(daily.get(src, 0) or 0) for k, src in _DAILY_COUNTER_MAP.items()}
        net_pnl = float(daily.get("pnl", 0.0) or 0.0)
        gross_pnl = round(net_pnl + commission_total, 2)
    else:
        commission_total = sum(t["commission"] for t in trades)
        exit_counts: dict[str, int] = {}
        for t in trades:
            et = t["exit_type"]
            exit_counts[et] = exit_counts.get(et, 0) + 1
        exits_block = {
            "tp1": exit_counts.get("TP1", 0),
            "tp2": exit_counts.get("TP2", 0),
            "sl": exit_counts.get("SL", 0),
            "loss_exit": exit_counts.get("LOSS_EXIT", 0),
            "trail": exit_counts.get("TRAIL", 0),
            "moc": exit_counts.get("MOC", 0),
        }
        gross_pnl = daily.get("pnl", sum(t["pnl"] for t in trades))
        net_pnl = gross_pnl - commission_total

    # "opened" = new entries today (independent of exits) — prefer swing_state;
    # fall back to len(trades) only for the legacy day-trade path.
    opened_count = int(swing_state.get("new_entries_today", 0)) if swing_state else len(trades)

    cum_pnl = cum_data.get("cumulative_pnl", 0)
    cum_pct = cum_data.get("cumulative_pnl_pct", 0)

    # --- SPY excess return ---
    spy_return = _fetch_spy_return(target_date)
    portfolio_return = gross_pnl / INITIAL_CAPITAL * 100
    excess = (portfolio_return - spy_return) if spy_return is not None else None

    # --- Best / worst trade ---
    best = max(trades, key=lambda t: t["pnl"]) if trades else None
    worst = min(trades, key=lambda t: t["pnl"]) if trades else None

    # --- VIX close (Polygon I:VIX primary → FRED phase0 log fallback) ---
    # FRED publishes VIX with a 1-day lag, so the Phase 0 MACRO_REGIME event
    # reports the Day N-1 close on Day N. Polygon I:VIX carries the true
    # same-day close. See docs/tasks/2026-06-06-data-quality-fix-package.md #1.
    vix_close, vix_prev = _fetch_vix_from_polygon(target_date)
    if vix_close is None:
        vix_close = _load_phase0_vix(target_date)
        if vix_close is not None:
            logger.warning(
                "VIX: Polygon I:VIX unavailable for %s, falling back to FRED "
                "phase0 value (may lag 1 day): %.2f",
                target_date,
                vix_close,
            )
    vix_delta_pct: float | None = None
    if vix_close is not None:
        prev_vix = vix_prev if vix_prev is not None else _load_previous_vix_close(target_date)
        if prev_vix is not None and prev_vix > 0:
            vix_delta_pct = (vix_close - prev_vix) / prev_vix * 100

    return {
        "date": target_date,
        "day_number": compute_trading_day_number(target_date, cum_data.get("start_date")),
        "positions": {
            "opened": opened_count,
            "qualified_above_threshold": qualified_count,
            "threshold": threshold,
            "max_allowed": 5,
        },
        "market": {
            "spy_return_pct": round(spy_return, 2) if spy_return is not None else None,
            "vix_close": round(vix_close, 2) if vix_close is not None else None,
            "vix_delta_pct": round(vix_delta_pct, 2) if vix_delta_pct is not None else None,
            "strategy": "LONG",
        },
        "scoring": {
            "avg_score": round(avg_score, 1),
            "min_score": round(min_score, 1),
            "max_score": round(max_score, 1),
            "scores": {k: round(v, 1) for k, v in scores.items()},
        },
        "execution": {
            "avg_fill_slippage_pct": round(avg_slippage, 2),
            "slippage_per_ticker": slippage,
            "commission_total": round(commission_total, 2),
        },
        "exits": exits_block,
        "pnl": {
            "gross": round(gross_pnl, 2),
            "commission": round(commission_total, 2),
            "net": round(net_pnl, 2),
            "cumulative": round(cum_pnl, 2),
            "cumulative_pct": round(cum_pct, 2),
        },
        "excess_return": {
            "portfolio_return_pct": round(portfolio_return, 2),
            "spy_return_pct": round(spy_return, 2) if spy_return is not None else None,
            "excess_pct": round(excess, 2) if excess is not None else None,
        },
        "uw_shadow_summary": uw_shadow_summary,
        "swing_state": swing_state,
        "trades": {
            "best": (
                {
                    "ticker": best["ticker"],
                    "pnl": round(best["pnl"], 2),
                    "pnl_pct": round(best["pnl_pct"], 2),
                    "exit_type": best["exit_type"],
                }
                if best
                else None
            ),
            "worst": (
                {
                    "ticker": worst["ticker"],
                    "pnl": round(worst["pnl"], 2),
                    "pnl_pct": round(worst["pnl_pct"], 2),
                    "exit_type": worst["exit_type"],
                }
                if worst
                else None
            ),
            "details": [
                {
                    "ticker": t["ticker"],
                    "score": round(t["score"], 1),
                    "entry": round(t["entry_price"], 2),
                    "exit": round(t["exit_price"], 2),
                    "pnl": round(t["pnl"], 2),
                    "exit_type": t["exit_type"],
                }
                for t in sorted(trades, key=lambda x: x["pnl"], reverse=True)
            ],
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    try:
        from lib.trading_day_guard import check_trading_day

        check_trading_day(logger)
    except ModuleNotFoundError:
        pass

    parser = argparse.ArgumentParser(description="IFDS Daily Metrics Collection")
    parser.add_argument("--date", help="Override date (YYYY-MM-DD) for backfill")
    args = parser.parse_args()

    target_date = args.date or date.today().isoformat()
    logger.info(f"Daily metrics collection — {target_date}")

    # Capture swing-exit realized P&L FIRST so build_daily_metrics reads the
    # updated cumulative_pnl.json (P0 §0.11 Part A — sole cumulative writer).
    # Guarded: a recorder failure (IBKR down) must not block metrics build;
    # the ledger is idempotent so the next run retries.
    try:
        rec_summary = record_pending_exits(target_date)
        logger.info(
            f"record_pending_exits: matched={rec_summary['matched']} "
            f"unprocessed={rec_summary['unprocessed']} "
            f"warnings={len(rec_summary['warnings'])}"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"record_pending_exits failed (metrics build continues): {exc}")

    metrics = build_daily_metrics(target_date)

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = METRICS_DIR / f"{target_date}.json"
    with open(out_path, "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info(
        f"Metrics written: {out_path} — "
        f"{metrics['positions']['opened']} trades, "
        f"P&L ${metrics['pnl']['gross']:+,.2f}, "
        f"cum ${metrics['pnl']['cumulative']:+,.2f}"
    )


if __name__ == "__main__":
    main()
