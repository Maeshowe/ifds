#!/usr/bin/env python3
"""SIM-1 — pure core of the §11.20 counterfactual exit-geometry measurement.

The question: how much of the realized −$6,460.95 over 88 trading days was
caused by the §11.20 defect (TP1/stop/breakeven anchored to the PLANNED price
while the entry order was MARKET), and how much is the strategy itself?

The method rests on one property: ``evaluate_position_eod`` in
``ifds.state.swing_positions`` is a PURE function — no IBKR, no Telegram, no
state writes. So the counterfactual can be run with the PRODUCTION exit logic
itself, changing only the anchor:

    A (factual)       entry_price = planned, levels = the execution plan's
    B (counterfactual) entry_price = real fill, levels rebased onto that fill
                       with the SAME ATR multiples

Nothing here re-implements an exit rule, so the simulator cannot drift from
production. ``test_uses_the_production_evaluator`` guards that property.

Read-only: this module never writes trading state.
Task: docs/tasks/2026-10-03-sim-counterfactual-geometry.md
"""

from __future__ import annotations

import statistics
import sys
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ifds.state.swing_positions import (  # noqa: E402
    ACTION_HOLD,
    ACTION_TP1,
    EOD_ACTIONS_SAME_DAY_MOC,
    SwingPosition,
    compute_sell_qty,
    evaluate_position_eod,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: ATR multiples Phase 6 uses to place the levels (``config/defaults.py``).
STOP_ATR_MULTIPLE = 2.0
TP1_ATR_MULTIPLE = 1.5
TP2_ATR_MULTIPLE = 3.0

#: Max per-level reconstruction error accepted when recovering the ATR.
#: Plan levels are rounded to the cent, and three independent roundings can
#: compound — hence a tolerance, never exact equality (ifds-rules).
LEVEL_TOLERANCE_USD = 0.02

#: Account equity the production EOD evaluator is given (``account_equity``).
DEFAULT_EQUITY = 100_000.0

#: Production TUNING subset the evaluator reads.
PRODUCTION_TUNING: dict[str, float | int] = {
    "swing_hard_sl_weekly_cumulative_pct": -0.08,
    "swing_trail_atr_multiple": 1.0,
    "swing_time_stop_trading_days": 5,
    "swing_tp1_sell_pct": 0.50,
}

#: Commission model fitted on the 106 observed paper legs (NOT the published
#: IBKR schedule): median abs err $0.04, p90 $0.11.
COMMISSION_FLOOR_USD = 1.05
COMMISSION_PER_SHARE_USD = 0.0057


# ---------------------------------------------------------------------------
# Value types (immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Bar:
    """One daily OHLC session."""

    date: date
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class ExitLeg:
    """One executed exit leg of a position."""

    exit_type: str
    exit_date: date
    exit_price: float
    qty: int


@dataclass(frozen=True)
class SimResult:
    """Outcome of one simulated position.

    ``unresolved`` means the bar window ran out before the position could be
    closed at a price we actually have. Such a position is reported, never
    closed at an invented price.
    """

    legs: tuple[ExitLeg, ...]
    unresolved: bool


# ---------------------------------------------------------------------------
# ATR recovery and level rebasing
# ---------------------------------------------------------------------------


def derive_atr(entry: float, stop: float, tp1: float, tp2: float) -> float | None:
    """Recover the ATR that produced an execution-plan row.

    All three levels come from one ATR, so each implies it. The median of the
    three is taken and then VALIDATED: if any level cannot be reconstructed to
    within ``LEVEL_TOLERANCE_USD``, the row is not self-consistent and ``None``
    is returned. Failing loud matters — a wrong ATR would silently propagate
    into every counterfactual level for that position.
    """
    if entry <= 0:
        return None
    implied = (
        (entry - stop) / STOP_ATR_MULTIPLE,
        (tp1 - entry) / TP1_ATR_MULTIPLE,
        (tp2 - entry) / TP2_ATR_MULTIPLE,
    )
    if any(value <= 0 for value in implied):
        return None
    atr = statistics.median(implied)
    rebuilt = rebase_levels(entry, atr)
    if max(abs(a - b) for a, b in zip(rebuilt, (stop, tp1, tp2))) > LEVEL_TOLERANCE_USD:
        return None
    return atr


def rebase_levels(anchor: float, atr: float) -> tuple[float, float, float]:
    """Place ``(stop, tp1, tp2)`` at the production multiples around ``anchor``.

    Called with the planned price this reproduces the plan; called with the
    real fill it is the corrected geometry — which is the whole experiment.
    """
    return (
        anchor - STOP_ATR_MULTIPLE * atr,
        anchor + TP1_ATR_MULTIPLE * atr,
        anchor + TP2_ATR_MULTIPLE * atr,
    )


# ---------------------------------------------------------------------------
# Day-by-day execution model
# ---------------------------------------------------------------------------


def simulate(
    position: SwingPosition,
    bars: list[Bar],
    config: dict | None = None,
    equity: float = DEFAULT_EQUITY,
) -> SimResult:
    """Replay the production EOD evaluator over ``bars`` from the entry day.

    Execution model, mirroring production:
      * ``TIME_STOP`` → same-day 21:40 MOC → that session's CLOSE.
      * every other exit → next-day 15:30 MARKET → the NEXT session's OPEN.
      * ``TP1`` sells ``qty × 0.50`` and the remainder stays open under the trail.

    The caller's ``position`` is never mutated: configurations A and B share the
    same inputs, so an in-place update would silently cross-contaminate them.
    """
    cfg = {**PRODUCTION_TUNING, **(config or {})}
    pos = replace(position)
    legs: list[ExitLeg] = []

    for index, bar in enumerate(bars):
        action, updates = evaluate_position_eod(
            pos, bar.close, bar.high, bar.low, bar.date, cfg, equity
        )
        pos = replace(pos, **{k: v for k, v in updates.items() if hasattr(pos, k)})

        if action == ACTION_HOLD:
            continue

        qty = compute_sell_qty(pos, action, float(cfg["swing_tp1_sell_pct"]))

        if action in EOD_ACTIONS_SAME_DAY_MOC:
            legs.append(ExitLeg(action, bar.date, bar.close, qty))
            return SimResult(tuple(legs), unresolved=False)

        if index + 1 >= len(bars):
            # Triggered, but there is no next session to fill at.
            return SimResult(tuple(legs), unresolved=True)

        fill = bars[index + 1]
        legs.append(ExitLeg(action, fill.date, fill.open, qty))

        if action != ACTION_TP1:
            return SimResult(tuple(legs), unresolved=False)

        pos = replace(pos, tp1_hit=True, qty_remaining=pos.qty_remaining - qty)

    return SimResult(tuple(legs), unresolved=True)


# ---------------------------------------------------------------------------
# P&L accounting
# ---------------------------------------------------------------------------


def gross_pnl(legs: list[ExitLeg] | tuple[ExitLeg, ...], entry_price: float) -> float:
    """Gross P&L of the legs against the entry anchor (commission excluded)."""
    return sum((leg.exit_price - entry_price) * leg.qty for leg in legs)


def commission(shares: int) -> float:
    """Per-leg commission, calibrated on the observed paper fills."""
    return max(COMMISSION_FLOOR_USD, COMMISSION_PER_SHARE_USD * shares)


def net_pnl(legs: list[ExitLeg] | tuple[ExitLeg, ...], entry_price: float) -> float:
    """Gross P&L less the entry leg's and every exit leg's commission."""
    entry_shares = sum(leg.qty for leg in legs)
    fees = commission(entry_shares) + sum(commission(leg.qty) for leg in legs)
    return gross_pnl(legs, entry_price) - fees
