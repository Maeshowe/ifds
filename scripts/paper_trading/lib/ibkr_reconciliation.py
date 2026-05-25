"""IBKR state reconciliation — autonomous bracket trigger detection.

Shared helpers for the daily 22:00 EOD reconcile (called by
``pt_monitor.py::run_eod_eval``) and the exit-type classifier used by
``daily_metrics.py`` to populate ``exits.{tp1,tp2,sl,trail,...}`` and
``cumulative_pnl.daily_history.*_hits`` counters.

Rationale
---------
The 2026-05-23 IBKR TWS Trades audit revealed that the swing-pivot
``submit_swing_market_only`` is correctly market-only per Day 63 §3.12,
but Tamás's manual Workstation SL+TP1 child orders on Day 3 (the Error
354 workaround) auto-triggered on Day 4 and Day 5 — and nothing in the
local state caught it. Day 4 ``daily_metrics`` showed pnl=$0 while
the actual realized was -$227.06; Day 5 showed $0 while actual was
+$159.12. The local state ``swing_positions.json`` kept VLO + ON as
HOLD positions through W21 close.

This module fixes the **structural blind spot**: every EOD eval (and
optionally any submit-orders run) queries ``ib.positions()`` and
``ib.reqExecutions()``, detects positions that disappeared between
state and IBKR, classifies the exit, and writes the realized P&L back
to ``daily_metrics`` + ``cumulative_pnl``.

Refs:
    docs/tasks/2026-05-23-state-reconciliation-from-ibkr.md (Rész 1 + 3)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

logger = logging.getLogger("ibkr_reconciliation")


# ---------------------------------------------------------------------------
# Pure helpers — unit-test friendly, no IBKR API dependency
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlannedBracket:
    """The planned bracket levels for a swing position.

    Sourced from the ``pt_submit_*.log`` line:
    ``TICKER: MKT BUY N @ ~$entry | stop $X | TP1 $Y | TP2 $Z``

    Note that these are the **planned-entry-based** levels (not the
    actual-fill-based mental levels in ``swing_positions.json``). The
    Day 3 manual Workstation child orders Tamás placed use these planned
    levels — so the classifier must check planned first, then mental.
    """

    ticker: str
    planned_stop: float | None = None
    planned_tp1: float | None = None
    planned_tp2: float | None = None
    mental_stop: float | None = None      # from swing_positions.json
    mental_tp1: float | None = None
    mental_tp2: float | None = None


@dataclass
class ReconcileReport:
    """Outcome of a single reconcile run."""

    detected_closures: list[dict[str, Any]] = field(default_factory=list)
    in_state_not_ibkr: list[str] = field(default_factory=list)
    in_ibkr_not_state: list[str] = field(default_factory=list)
    state_matches_ibkr: bool = True
    errors: list[str] = field(default_factory=list)


def detect_closed_tickers(
    ib_position_tickers: set[str],
    state_tickers: set[str],
    permanent_orphans: set[str] = frozenset({"AVDL.CVR"}),
) -> tuple[set[str], set[str]]:
    """Identify tickers that disappeared between state and IBKR.

    Returns ``(in_state_not_ibkr, in_ibkr_not_state)``.

    ``permanent_orphans`` (default ``{"AVDL.CVR"}``) are tickers that
    appear in IBKR but should never trigger reconcile activity (e.g.
    contingent value rights that cannot be liquidated from the paper
    account).
    """
    state = set(state_tickers)
    ibkr = set(ib_position_tickers) - permanent_orphans
    return state - ibkr, ibkr - state


def classify_exit_from_execution(
    *,
    order_ref: str,
    fill_price: float,
    planned: PlannedBracket | None = None,
    tolerance_pct: float = 0.5,
) -> str:
    """Classify an exit fill into TP1/TP2/SL/TRAIL_SL/OTHER.

    **Primary**: substring match on ``order_ref`` (set by submit_orders
    when it uses the bracket builder — e.g. ``IFDS_SWING_EC_TP1``).

    **Fallback**: if ``order_ref`` is empty (Tamás manual TWS bracket),
    match ``fill_price`` against the planned and mental bracket levels
    within ``tolerance_pct`` percent. Planned levels (from
    ``pt_submit_*.log``) take precedence because that's what the manual
    Workstation order entry used.

    Returns one of:
    - ``"TP1"``, ``"TP2"``, ``"SL"``, ``"TRAIL_SL"`` — bracket trigger
    - ``"OTHER"`` — could not classify (manual close, MOC, time stop)
    """
    ref_upper = (order_ref or "").upper()

    # Substring detection — most reliable
    if "_TP1" in ref_upper:
        return "TP1"
    if "_TP2" in ref_upper:
        return "TP2"
    if "_TRAIL" in ref_upper:
        return "TRAIL_SL"
    if "_SL" in ref_upper:
        return "SL"

    # Fallback: bracket-level matching (manual Workstation bracket orders
    # have empty order_ref — Day 3-5 W21 pattern)
    if planned is not None:
        return _match_fill_to_planned_level(fill_price, planned, tolerance_pct)

    return "OTHER"


def _match_fill_to_planned_level(
    fill_price: float,
    planned: PlannedBracket,
    tolerance_pct: float,
) -> str:
    """Match a fill price to the closest planned (then mental) level.

    Returns the matching exit_type label, or "OTHER" if no level is
    within the tolerance band.
    """
    tol = tolerance_pct / 100.0
    # Priority: planned levels first (manual Workstation matches these),
    # then mental levels (`swing_positions.json`).
    candidates: list[tuple[float, str]] = []
    if planned.planned_stop is not None:
        candidates.append((planned.planned_stop, "SL"))
    if planned.planned_tp1 is not None:
        candidates.append((planned.planned_tp1, "TP1"))
    if planned.planned_tp2 is not None:
        candidates.append((planned.planned_tp2, "TP2"))
    if planned.mental_stop is not None:
        candidates.append((planned.mental_stop, "SL"))
    if planned.mental_tp1 is not None:
        candidates.append((planned.mental_tp1, "TP1"))
    if planned.mental_tp2 is not None:
        candidates.append((planned.mental_tp2, "TP2"))

    for level, label in candidates:
        if level <= 0:
            continue
        if abs(fill_price - level) / level <= tol:
            return label
    return "OTHER"


def compute_pnl(
    entry_price: float,
    exit_price: float,
    qty: int,
    side: str = "BUY",
) -> float:
    """Compute gross P&L for a single round-trip trade.

    For a BUY position (long): pnl = qty * (exit - entry).
    For a SELL position (short): pnl = qty * (entry - exit).
    """
    direction = 1 if side.upper() == "BUY" else -1
    return round(direction * qty * (exit_price - entry_price), 4)


# ---------------------------------------------------------------------------
# IBKR API wrappers — thin layer, mockable in tests
# ---------------------------------------------------------------------------


def fetch_today_position_tickers(ib: Any) -> set[str]:
    """Return the symbols of currently-open IBKR positions (non-zero qty)."""
    tickers = set()
    for p in ib.positions():
        if p.position != 0:
            tickers.add(p.contract.symbol)
    return tickers


def fetch_today_executions(ib: Any, today: date) -> list[dict[str, Any]]:
    """Return today's executions as a list of plain dicts.

    Each dict contains: ``ticker``, ``side``, ``shares``, ``price``,
    ``time`` (datetime), ``order_ref`` (str), ``order_id`` (int),
    ``commission`` (float or None).

    Uses ``ExecutionFilter(time="YYYYMMDD 00:00:00")`` then post-filters
    by execution date — per .claude/rules/ifds-rules.md the IBKR
    ExecutionFilter is not strict and stale fills can leak through.
    """
    from ib_insync import ExecutionFilter

    today_str = today.strftime("%Y%m%d")
    raw = ib.reqExecutions(ExecutionFilter(time=f"{today_str} 00:00:00"))

    out: list[dict[str, Any]] = []
    for fill in raw:
        exec_obj = fill.execution
        exec_date = exec_obj.time.date() if hasattr(exec_obj.time, "date") else None
        if exec_date != today:
            logger.debug(
                f"Skipping stale execution: {fill.contract.symbol} "
                f"@{exec_obj.time}"
            )
            continue
        commission: float | None = None
        if hasattr(fill, "commissionReport") and fill.commissionReport:
            commission = float(getattr(fill.commissionReport, "commission", 0.0))
        out.append({
            "ticker": fill.contract.symbol,
            "side": exec_obj.side,           # "BOT" | "SLD"
            "shares": float(exec_obj.shares),
            "price": float(exec_obj.price),
            "time": exec_obj.time,
            "order_ref": exec_obj.orderRef or "",
            "order_id": int(exec_obj.orderId),
            "commission": commission,
        })
    return out


# ---------------------------------------------------------------------------
# Top-level orchestrator — called by pt_monitor.py::run_eod_eval
# ---------------------------------------------------------------------------


def build_reconcile_report(
    ib_position_tickers: set[str],
    state_tickers: set[str],
    executions: list[dict[str, Any]],
    planned_brackets: dict[str, PlannedBracket],
    state_positions_by_ticker: dict[str, Any] | None = None,
) -> ReconcileReport:
    """Build a ReconcileReport from already-fetched IBKR data.

    Pure function (no IBKR API calls) — wraps the detection +
    classification logic so it can be unit-tested end-to-end.

    For each ticker that disappeared from IBKR but is still in state,
    look up the matching SLD execution and classify it.
    """
    in_state_not_ibkr, in_ibkr_not_state = detect_closed_tickers(
        ib_position_tickers, state_tickers,
    )

    report = ReconcileReport(
        in_state_not_ibkr=sorted(in_state_not_ibkr),
        in_ibkr_not_state=sorted(in_ibkr_not_state),
        state_matches_ibkr=not in_state_not_ibkr and not in_ibkr_not_state,
    )

    if not in_state_not_ibkr:
        return report

    # Group executions by ticker (SLD only — we're looking for closures)
    sld_by_ticker: dict[str, list[dict[str, Any]]] = {}
    for ex in executions:
        if ex["side"] != "SLD":
            continue
        sld_by_ticker.setdefault(ex["ticker"], []).append(ex)

    state_pos = state_positions_by_ticker or {}

    for ticker in sorted(in_state_not_ibkr):
        sld_list = sld_by_ticker.get(ticker, [])
        if not sld_list:
            report.detected_closures.append({
                "ticker": ticker,
                "exit_type": "OTHER",
                "reason": "no_matching_execution",
                "fill_price": None,
                "qty": None,
                "gross": None,
            })
            continue

        # If multiple SLD fills for the same ticker, use the latest one
        # (a partial fill from earlier would be the TP1 then full close;
        # the latest is the "real" closure).
        sld = max(sld_list, key=lambda e: e["time"])
        total_qty = sum(e["shares"] for e in sld_list)

        planned = planned_brackets.get(ticker)
        exit_type = classify_exit_from_execution(
            order_ref=sld["order_ref"],
            fill_price=sld["price"],
            planned=planned,
        )

        entry_price = None
        if ticker in state_pos:
            entry_price = state_pos[ticker].get("entry_price")
        gross = (
            compute_pnl(entry_price, sld["price"], int(total_qty))
            if entry_price is not None else None
        )

        report.detected_closures.append({
            "ticker": ticker,
            "exit_type": exit_type,
            "fill_price": sld["price"],
            "qty": int(total_qty),
            "entry_price": entry_price,
            "gross": gross,
            "commission": sum(
                e["commission"] or 0.0 for e in sld_list
            ),
            "order_ref": sld["order_ref"],
            "time": sld["time"].isoformat() if hasattr(sld["time"], "isoformat") else str(sld["time"]),
        })

    return report
