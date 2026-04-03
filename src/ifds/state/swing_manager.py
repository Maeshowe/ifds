"""Swing Position Manager — daily lifecycle logic for multi-day positions.

Called by ``close_positions.py`` at 21:45 CET. For each open position:
1. Increment hold_days
2. Check earnings risk → early MOC exit
3. Check max hold (D+5) → MOC exit
4. Check breakeven threshold → raise SL to entry
5. Check TP1 status → activate trail for remaining qty
6. Update trail stop (only upward)

This module contains the **decision logic** — IBKR order execution is
handled by ``close_positions.py`` using the returned action list.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any

from ifds.state.position_tracker import OpenPosition, PositionTracker


class SwingAction(Enum):
    """Actions returned by the swing manager for IBKR execution."""
    MOC_EXIT = "moc_exit"               # Full position MOC close
    ACTIVATE_TRAIL = "activate_trail"   # Place IBKR TRAIL order
    MODIFY_SL = "modify_sl"            # Modify SL order to new price
    UPDATE_TRAIL = "update_trail"       # Update trail stop price
    NO_ACTION = "no_action"


@dataclass(frozen=True)
class SwingDecision:
    """A single management decision for one position."""
    ticker: str
    action: SwingAction
    reason: str
    qty: int = 0
    price: float = 0.0                  # New SL or trail stop price
    trail_amount: float = 0.0           # For TRAIL orders: trailing amount $
    details: dict = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.details is None:
            object.__setattr__(self, "details", {})


# ------------------------------------------------------------------
# Default config
# ------------------------------------------------------------------

_DEFAULTS: dict[str, Any] = {
    "breakeven_threshold_atr": 0.3,
    "trailing_stop_atr": 1.0,
    "max_hold_trading_days": 5,
    "earnings_exit_days": 1,
}


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------

def run_swing_management(
    tracker: PositionTracker,
    current_prices: dict[str, float],
    earnings_dates: dict[str, str] | None = None,
    config: dict[str, Any] | None = None,
    today: date | None = None,
) -> list[SwingDecision]:
    """Run daily swing management cycle.

    Parameters
    ----------
    tracker:
        PositionTracker with current open positions.
    current_prices:
        ``{ticker: last_price}`` for all open positions.
    earnings_dates:
        ``{ticker: "YYYY-MM-DD"}`` of next earnings dates.
    config:
        Overridable thresholds.
    today:
        Reference date (default: today).

    Returns
    -------
    list[SwingDecision]
        Actions to execute in IBKR (caller handles order placement).
    """
    cfg = {**_DEFAULTS, **(config or {})}
    today = today or date.today()
    earnings = earnings_dates or {}

    decisions: list[SwingDecision] = []

    # 1. Increment hold days
    tracker.increment_hold_days()

    for pos in tracker.get_all():
        price = current_prices.get(pos.ticker)
        if price is None:
            continue

        # 2. Earnings risk → early exit
        earn_str = earnings.get(pos.ticker)
        if earn_str:
            try:
                earn_date = date.fromisoformat(earn_str)
                days_until = (earn_date - today).days
                if 0 <= days_until <= cfg["earnings_exit_days"]:
                    decisions.append(SwingDecision(
                        ticker=pos.ticker,
                        action=SwingAction.MOC_EXIT,
                        reason="earnings_risk",
                        qty=pos.remaining_qty,
                        details={"earnings_date": earn_str, "days_until": days_until},
                    ))
                    continue
            except ValueError:
                pass

        # 3. Max hold → MOC exit
        if pos.hold_days >= cfg["max_hold_trading_days"]:
            decisions.append(SwingDecision(
                ticker=pos.ticker,
                action=SwingAction.MOC_EXIT,
                reason="max_hold",
                qty=pos.remaining_qty,
                details={"hold_days": pos.hold_days, "max": cfg["max_hold_trading_days"]},
            ))
            continue

        # 4. Breakeven check
        if not pos.breakeven_triggered and not pos.tp1_triggered:
            be_threshold = pos.entry_price + pos.atr_at_entry * cfg["breakeven_threshold_atr"]
            if price >= be_threshold:
                decisions.append(SwingDecision(
                    ticker=pos.ticker,
                    action=SwingAction.MODIFY_SL,
                    reason="breakeven",
                    qty=pos.remaining_qty,
                    price=pos.entry_price,
                ))
                tracker.update_position(
                    pos.ticker,
                    breakeven_triggered=True,
                    sl_price=pos.entry_price,
                )

        # 5. TP1 triggered → activate trail
        if pos.tp1_triggered and pos.trail_amount_usd == 0:
            trail_amount = pos.atr_at_entry * cfg["trailing_stop_atr"]
            trail_stop = round(price - trail_amount, 2)
            decisions.append(SwingDecision(
                ticker=pos.ticker,
                action=SwingAction.ACTIVATE_TRAIL,
                reason="tp1_trail_activation",
                qty=pos.remaining_qty,
                trail_amount=round(trail_amount, 2),
                price=trail_stop,
            ))
            tracker.update_position(
                pos.ticker,
                trail_amount_usd=round(trail_amount, 2),
                current_trail_stop=trail_stop,
            )

        # 6. Trail update (only upward)
        if pos.trail_amount_usd > 0 and pos.current_trail_stop > 0:
            new_trail = round(price - pos.trail_amount_usd, 2)
            if new_trail > pos.current_trail_stop:
                decisions.append(SwingDecision(
                    ticker=pos.ticker,
                    action=SwingAction.UPDATE_TRAIL,
                    reason="trail_tighten",
                    qty=pos.remaining_qty,
                    price=new_trail,
                    details={"prev_trail": pos.current_trail_stop},
                ))
                tracker.update_position(pos.ticker, current_trail_stop=new_trail)

    return decisions
