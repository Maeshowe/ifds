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


# ============================================================================
# Swing Trade Simulation (BC20C)
# ============================================================================

def simulate_swing_trade(
    trade: Trade,
    daily_bars: list[dict],
    tp1_atr_mult: float = 0.75,
    trail_atr_mult: float = 1.0,
    trail_atr_volatile: float = 0.75,
    breakeven_atr_mult: float = 0.3,
    max_hold_days: int = 5,
    tp1_exit_pct: float = 0.50,
    fill_window_days: int = 1,
    vwap_prices: dict | None = None,
    mms_regime: str = "undetermined",
) -> Trade:
    """Simulate swing trade lifecycle with trailing stop.

    Day-by-day iteration after fill:
    1. Check SL: if low <= current_sl → full exit remaining qty
    2. Check TP1: if high >= tp1_price and not yet triggered → partial exit
    3. Breakeven: if close > entry + breakeven_atr×ATR → raise SL to entry
    4. Trail: if TP1 triggered, trail_stop = max(prev_trail, high - trail×ATR)
    5. Max hold: if day count >= max_hold_days → exit at close

    Same-day ambiguity (TP1+SL on same bar): conservative → SL exit.

    Args:
        trade: Trade with entry_price, stop_loss, quantity set.
        daily_bars: OHLCV bars AFTER the plan date.
        tp1_atr_mult: TP1 target in ATR multiples from entry.
        trail_atr_mult: Trail stop distance in ATR multiples.
        trail_atr_volatile: Trail distance for MMS VOLATILE regime.
        breakeven_atr_mult: Profit threshold (ATR) to raise SL to entry.
        max_hold_days: Maximum holding period.
        tp1_exit_pct: Fraction of position to exit at TP1.
        fill_window_days: Days to attempt fill.
        vwap_prices: ``{ticker: vwap}`` — if price > vwap×1.02, no fill.
        mms_regime: MMS regime (``"volatile"`` → tighter trail).

    Returns:
        Trade with swing execution results filled in.
    """
    if not daily_bars:
        return trade

    is_long = trade.direction == "BUY"

    # Infer ATR from stop distance: SL = entry ± sl_atr×ATR
    if trade.stop_loss > 0 and trade.entry_price > 0:
        atr = abs(trade.entry_price - trade.stop_loss) / 1.5  # default sl_atr_mult
    else:
        return trade

    if not (atr > 0):
        return trade

    # VWAP entry filter: reject if price > VWAP × 1.02
    if vwap_prices and trade.ticker in vwap_prices:
        vwap = vwap_prices[trade.ticker]
        if vwap > 0 and trade.entry_price > vwap * 1.02:
            trade.exit_type = "vwap_reject"
            return trade

    # MMS VOLATILE → tighter trail
    effective_trail_atr = trail_atr_volatile if mms_regime == "volatile" else trail_atr_mult

    # 1. FILL CHECK (same logic as bracket sim)
    fill_bar_idx = None
    for i in range(min(fill_window_days, len(daily_bars))):
        bar = daily_bars[i]
        if is_long and bar["l"] <= trade.entry_price:
            fill_bar_idx = i
            trade.filled = True
            trade.fill_price = trade.entry_price
            trade.fill_date = _parse_date(bar["date"])
            break
        elif not is_long and bar["h"] >= trade.entry_price:
            fill_bar_idx = i
            trade.filled = True
            trade.fill_price = trade.entry_price
            trade.fill_date = _parse_date(bar["date"])
            break

    if not trade.filled:
        return trade

    # Set up swing state
    entry = trade.fill_price
    tp1_price = round(entry + tp1_atr_mult * atr, 2) if is_long else round(entry - tp1_atr_mult * atr, 2)
    trail_distance = effective_trail_atr * atr
    breakeven_threshold = breakeven_atr_mult * atr
    current_sl = trade.stop_loss
    remaining_qty = trade.quantity
    tp1_triggered = False
    breakeven_done = False
    total_pnl = 0.0

    # Also populate legacy bracket fields for compatibility
    trade.tp1 = tp1_price

    # 2. DAY-BY-DAY SIMULATION
    sim_bars = daily_bars[fill_bar_idx + 1:]
    hold_bars = sim_bars[:max_hold_days]

    for day_idx, bar in enumerate(hold_bars):
        bar_high = bar["h"]
        bar_low = bar["l"]
        bar_close = bar["c"]
        bar_date = _parse_date(bar["date"])
        holding_day = day_idx + 1

        # --- Check SL hit ---
        sl_hit = (bar_low <= current_sl) if is_long else (bar_high >= current_sl)

        # --- Check TP1 hit ---
        tp1_hit = False
        if not tp1_triggered:
            tp1_hit = (bar_high >= tp1_price) if is_long else (bar_low <= tp1_price)

        # Same-day ambiguity: TP1 + SL → conservative SL
        if tp1_hit and sl_hit:
            tp1_hit = False

        if sl_hit:
            # Full exit at SL
            pnl = remaining_qty * (current_sl - entry) if is_long else remaining_qty * (entry - current_sl)
            total_pnl += pnl
            trade.trail_exit_price = current_sl
            trade.holding_days = holding_day
            trade.total_pnl = round(total_pnl, 2)
            if trade.quantity > 0 and entry > 0:
                trade.total_pnl_pct = round(total_pnl / (trade.quantity * entry) * 100, 2)

            if tp1_triggered:
                trade.exit_type = "tp1_partial+trail"
            elif breakeven_done:
                trade.exit_type = "breakeven_stop"
            else:
                trade.exit_type = "stop"

            # Set legacy leg fields for compatibility
            trade.leg1_exit_price = current_sl
            trade.leg1_exit_date = bar_date
            trade.leg1_exit_reason = trade.exit_type
            return trade

        if tp1_hit:
            # Partial exit at TP1
            partial_qty = round(trade.quantity * tp1_exit_pct)
            partial_pnl = partial_qty * (tp1_price - entry) if is_long else partial_qty * (entry - tp1_price)
            total_pnl += partial_pnl
            remaining_qty -= partial_qty

            tp1_triggered = True
            trade.tp1_triggered = True
            trade.tp1_exit_day = holding_day
            trade.partial_exit_qty = partial_qty
            trade.partial_exit_pnl = round(partial_pnl, 2)

            # Activate trail — initial trail SL
            if is_long:
                current_sl = max(current_sl, round(bar_high - trail_distance, 2))
            else:
                current_sl = min(current_sl, round(bar_low + trail_distance, 2))

            if remaining_qty <= 0:
                # Full exit at TP1 (tp1_exit_pct == 1.0)
                trade.exit_type = "tp1_full"
                trade.holding_days = holding_day
                trade.total_pnl = round(total_pnl, 2)
                if trade.quantity > 0 and entry > 0:
                    trade.total_pnl_pct = round(total_pnl / (trade.quantity * entry) * 100, 2)
                trade.leg1_exit_price = tp1_price
                trade.leg1_exit_date = bar_date
                trade.leg1_exit_reason = "tp1_full"
                return trade

        # --- Breakeven check ---
        if not breakeven_done and not tp1_triggered:
            profit = (bar_close - entry) if is_long else (entry - bar_close)
            if profit >= breakeven_threshold:
                current_sl = entry
                breakeven_done = True
                trade.breakeven_triggered = True

        # --- Trail update (after TP1 triggered) ---
        if tp1_triggered:
            if is_long:
                new_trail = round(bar_high - trail_distance, 2)
                current_sl = max(current_sl, new_trail)
            else:
                new_trail = round(bar_low + trail_distance, 2)
                current_sl = min(current_sl, new_trail)

    # --- Max hold exit: close at last bar's close ---
    if hold_bars:
        last_bar = hold_bars[-1]
        exit_price = last_bar["c"]
        exit_date = _parse_date(last_bar["date"])
        pnl = remaining_qty * (exit_price - entry) if is_long else remaining_qty * (entry - exit_price)
        total_pnl += pnl
        trade.trail_exit_price = exit_price
        trade.exit_type = "max_hold"
        trade.holding_days = len(hold_bars)
        trade.total_pnl = round(total_pnl, 2)
        if trade.quantity > 0 and entry > 0:
            trade.total_pnl_pct = round(total_pnl / (trade.quantity * entry) * 100, 2)
        trade.leg1_exit_price = exit_price
        trade.leg1_exit_date = exit_date
        trade.leg1_exit_reason = "max_hold"
    else:
        trade.leg1_exit_reason = "open"

    return trade
