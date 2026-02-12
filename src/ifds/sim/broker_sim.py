"""Bracket order simulation (IBKR-compatible).

Simulates the lifecycle of a bracket order:
1. Fill check: D+1 low <= entry_price -> filled @ entry_price
2. Two parallel legs: Leg 1 (33% -> TP1/SL), Leg 2 (66% -> TP2/SL)
3. Same-day ambiguity: conservative -> stop hit (pessimistic for validation)
4. Expired: max_hold_days reached -> exit @ close of last day
"""

from datetime import date

from ifds.sim.models import Trade


def compute_qty_split(quantity: int) -> tuple[int, int]:
    """Split quantity into 33%/66% for bracket legs.

    Returns:
        (qty_tp1, qty_tp2) where qty_tp1 + qty_tp2 == quantity.
    """
    qty_tp1 = round(quantity * 0.33)
    qty_tp2 = quantity - qty_tp1
    return qty_tp1, qty_tp2


def simulate_bracket_order(trade: Trade, daily_bars: list[dict],
                           max_hold_days: int = 10,
                           fill_window_days: int = 1) -> Trade:
    """Simulate a bracket order lifecycle.

    Args:
        trade: Trade object with entry/stop/tp1/tp2 prices set.
        daily_bars: OHLCV bars AFTER the plan date, sorted chronologically.
                    [{"date": "2026-02-13", "o": ..., "h": ..., "l": ..., "c": ..., "v": ...}, ...]
        max_hold_days: Maximum holding period after fill (default 10 trading days).
        fill_window_days: Days to attempt fill (default 1 — IBKR bot cancels next day).

    Returns:
        Trade with execution results filled in.
    """
    if not daily_bars:
        return trade

    is_long = trade.direction == "BUY"

    # Qty split
    trade.qty_tp1, trade.qty_tp2 = compute_qty_split(trade.quantity)

    # 1. FILL CHECK
    fill_bar_idx = None
    for i in range(min(fill_window_days, len(daily_bars))):
        bar = daily_bars[i]
        if is_long:
            # Long: limit buy fills when price drops to entry
            if bar["l"] <= trade.entry_price:
                fill_bar_idx = i
                trade.filled = True
                trade.fill_price = trade.entry_price
                trade.fill_date = _parse_date(bar["date"])
                break
        else:
            # Short: limit sell fills when price rises to entry
            if bar["h"] >= trade.entry_price:
                fill_bar_idx = i
                trade.filled = True
                trade.fill_price = trade.entry_price
                trade.fill_date = _parse_date(bar["date"])
                break

    if not trade.filled:
        return trade

    # 2. BRACKET SIMULATION — bars after fill day
    bracket_bars = daily_bars[fill_bar_idx + 1:]
    if not bracket_bars:
        # Filled on last available bar — both legs open
        trade.leg1_exit_reason = "open"
        trade.leg2_exit_reason = "open"
        return trade

    hold_bars = bracket_bars[:max_hold_days]

    # Simulate Leg 1: qty_tp1 -> TP1/SL
    _simulate_leg(trade, hold_bars, is_long, leg=1,
                  tp_price=trade.tp1, stop_price=trade.stop_loss)

    # Simulate Leg 2: qty_tp2 -> TP2/SL
    _simulate_leg(trade, hold_bars, is_long, leg=2,
                  tp_price=trade.tp2, stop_price=trade.stop_loss)

    # 3. P&L CALCULATION
    if trade.qty_tp1 > 0 and trade.leg1_exit_price > 0:
        if is_long:
            trade.leg1_pnl = trade.qty_tp1 * (trade.leg1_exit_price - trade.fill_price)
        else:
            trade.leg1_pnl = trade.qty_tp1 * (trade.fill_price - trade.leg1_exit_price)

    if trade.qty_tp2 > 0 and trade.leg2_exit_price > 0:
        if is_long:
            trade.leg2_pnl = trade.qty_tp2 * (trade.leg2_exit_price - trade.fill_price)
        else:
            trade.leg2_pnl = trade.qty_tp2 * (trade.fill_price - trade.leg2_exit_price)

    trade.total_pnl = trade.leg1_pnl + trade.leg2_pnl

    if trade.quantity > 0 and trade.fill_price > 0:
        trade.total_pnl_pct = (trade.total_pnl / (trade.quantity * trade.fill_price)) * 100

    # Holding days: from fill to last exit
    exit_dates = []
    if trade.leg1_exit_date:
        exit_dates.append(trade.leg1_exit_date)
    if trade.leg2_exit_date:
        exit_dates.append(trade.leg2_exit_date)
    if exit_dates and trade.fill_date:
        last_exit = max(exit_dates)
        trade.holding_days = (last_exit - trade.fill_date).days

    return trade


def _simulate_leg(trade: Trade, bars: list[dict], is_long: bool,
                  leg: int, tp_price: float, stop_price: float) -> None:
    """Simulate one leg of the bracket order.

    Modifies trade in place for the specified leg (1 or 2).
    """
    for bar in bars:
        bar_high = bar["h"]
        bar_low = bar["l"]
        bar_close = bar["c"]
        bar_date = _parse_date(bar["date"])

        if is_long:
            tp_hit = bar_high >= tp_price if tp_price > 0 else False
            stop_hit = bar_low <= stop_price if stop_price > 0 else False
        else:
            tp_hit = bar_low <= tp_price if tp_price > 0 else False
            stop_hit = bar_high >= stop_price if stop_price > 0 else False

        if tp_hit and stop_hit:
            # Same-day ambiguity -> conservative: STOP
            _set_leg_exit(trade, leg, stop_price, bar_date, "stop")
            return
        elif tp_hit:
            _set_leg_exit(trade, leg, tp_price, bar_date, "tp1" if leg == 1 else "tp2")
            return
        elif stop_hit:
            _set_leg_exit(trade, leg, stop_price, bar_date, "stop")
            return

    # Expired: exit @ close of last bar
    if bars:
        last_bar = bars[-1]
        _set_leg_exit(trade, leg, last_bar["c"],
                      _parse_date(last_bar["date"]), "expired")
    else:
        _set_leg_reason(trade, leg, "open")


def _set_leg_exit(trade: Trade, leg: int, price: float,
                  exit_date: date, reason: str) -> None:
    """Set exit price, date, and reason for a leg."""
    if leg == 1:
        trade.leg1_exit_price = price
        trade.leg1_exit_date = exit_date
        trade.leg1_exit_reason = reason
    else:
        trade.leg2_exit_price = price
        trade.leg2_exit_date = exit_date
        trade.leg2_exit_reason = reason


def _set_leg_reason(trade: Trade, leg: int, reason: str) -> None:
    """Set only the exit reason (no price/date) for a leg."""
    if leg == 1:
        trade.leg1_exit_reason = reason
    else:
        trade.leg2_exit_reason = reason


def _parse_date(date_str: str | date) -> date:
    """Parse date string or return date object as-is."""
    if isinstance(date_str, date):
        return date_str
    return date.fromisoformat(date_str)
