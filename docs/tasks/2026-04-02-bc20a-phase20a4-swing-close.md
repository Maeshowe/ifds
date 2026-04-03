Status: DONE
Updated: 2026-04-03
Note: BC20A Phase_20A_4 — close_positions.py Swing Management (~3h CC)
Depends: Phase_20A_2 (PositionTracker) + Phase_20A_3 (Pipeline Split)

# BC20A Phase_20A_4 — close_positions.py Swing Management

## Cél

A `close_positions.py`-t átalakítani az 1-napos MOC rendszerből swing
position management-re: hold day tracking, breakeven SL, IBKR TRAIL order,
max hold D+5 MOC fallback, earnings korai exit.

## Scope

### 1. Napi management lifecycle

```
21:45 CET → close_positions.py fut:

For each position in PositionTracker:
  1. Increment hold_days
  2. Check earnings risk → korai MOC exit
  3. Check max hold (D+5) → MOC exit
  4. Check TP1 status:
     - If TP1 triggered today → activate TRAIL order (remaining qty)
     - If TP1 was triggered earlier → update trail stop
  5. Breakeven check:
     - If current_price > entry + 0.3×ATR AND NOT breakeven_triggered:
       → Modify SL order to entry price (breakeven)
  6. Trail update (if trail active):
     - new_trail = max(current_trail, current_high - trail_atr × ATR)
     - Modify IBKR TRAIL order if tighter
  7. Update PositionTracker state
```

### 2. Hold day tracking

```python
from ifds.utils.trading_calendar import TradingCalendar

calendar = TradingCalendar()

def count_trading_days(entry_date: str, today: date) -> int:
    """Count trading days between entry and today (inclusive)."""
    return calendar.trading_days_between(
        date.fromisoformat(entry_date), today
    )
```

A `trading_calendar.py` (BC18-prep) már elérhető — pandas_market_calendars
alapú trading day számolás.

### 3. Breakeven SL felhúzás

```python
def check_breakeven(pos: OpenPosition, current_price: float) -> bool:
    """Check if SL should be raised to entry (breakeven)."""
    if pos.breakeven_triggered:
        return False
    threshold = pos.entry_price + pos.atr_at_entry * BREAKEVEN_ATR_MULT  # 0.3
    return current_price >= threshold

# IBKR SL módosítás
if check_breakeven(pos, current_price):
    # Modify existing SL order to entry price
    ib.reqGlobalCancel()  # cancel old SL
    new_sl = StopOrder('SELL', pos.remaining_qty, pos.entry_price)
    ib.placeOrder(contract, new_sl)
    tracker.update_position(pos.ticker, 
        breakeven_triggered=True, sl_price=pos.entry_price)
```

### 4. IBKR TRAIL order aktiválás (TP1 után)

```python
def activate_trail(pos: OpenPosition, ib, contract):
    """Activate IBKR TRAIL order for remaining qty after TP1."""
    trail_amount = pos.atr_at_entry * TRAIL_ATR_MULT  # 1.0×ATR
    
    # Cancel existing SL for remaining qty
    # Place TRAIL order
    trail = Order()
    trail.action = 'SELL'
    trail.totalQuantity = pos.remaining_qty
    trail.orderType = 'TRAIL'
    trail.trailingPercent = 0  # use absolute amount
    trail.auxPrice = trail_amount  # trailing amount in $
    trail.orderRef = f"IFDS_{pos.ticker}_TRAIL"
    
    ib.placeOrder(contract, trail)
    tracker.update_position(pos.ticker,
        tp1_triggered=True,
        trail_amount_usd=trail_amount,
        current_trail_stop=current_price - trail_amount)
```

### 5. Max hold D+5 → MOC exit

```python
for pos in tracker.get_expired():
    # Submit MOC for remaining_qty
    moc = MarketOrder('SELL', pos.remaining_qty)
    moc.orderRef = f"IFDS_{pos.ticker}_MAXHOLD"
    ib.placeOrder(contract, moc)
    tracker.remove_position(pos.ticker)
    logger.info(f"[MAX HOLD] {pos.ticker} D+{pos.hold_days} → MOC {pos.remaining_qty}sh")
```

### 6. Earnings korai exit

```python
from ifds.data.fmp import FMPClient

def check_earnings_risk(pos: OpenPosition, fmp: FMPClient) -> bool:
    """Check if ticker has earnings within 1 trading day."""
    earnings = fmp.get_earnings_calendar(pos.ticker, days=3)
    if earnings:
        next_earnings = min(earnings, key=lambda e: e["date"])
        trading_days = calendar.trading_days_between(date.today(), next_earnings["date"])
        return trading_days <= 1
    return False
```

### 7. Config kulcsok

```python
TUNING = {
    # Swing Management (BC20A)
    "breakeven_threshold_atr": 0.3,     # 0.3×ATR profit → SL breakeven
    "trailing_stop_atr": 1.0,           # Trail distance = 1×ATR
    "trailing_stop_atr_volatile": 0.75, # VOLATILE regime → tighter trail
    "max_hold_trading_days": 5,
    "earnings_exit_days": 1,            # Exit if earnings within 1 trading day
}
```

## A jelenlegi Scenario A/B kezelése

A swing management **leváltja** a jelenlegi Scenario A + B logikát:
- Scenario A (TP1 → trail) → beépül a TRAIL order aktiválásba
- Scenario B (19:00 CET loss exit) → beépül a breakeven + max hold logikába
- `pt_monitor.py` marad az intraday 5-perces monitoring-hoz, de a swing
  management a close_positions.py-ban fut naponta egyszer

## Tesztelés

- `test_swing_close.py`:
  - D+0: pozíció nyitva, hold_days=0
  - D+1 TP1 triggered: trail activated, remaining_qty helyes
  - D+2 breakeven: SL felhúzás entry-re
  - D+5: MOC exit
  - Earnings risk: korai exit
  - Trail update: new_trail > old_trail → frissítve
  - Trail update: new_trail < old_trail → nem változik (csak felfelé)
- Meglévő close_positions tesztek: all green

## Commit

```
feat(close_positions): swing position management with trail + breakeven

Replace 1-day MOC exit with multi-day swing management:
hold day tracking, breakeven SL at 0.3×ATR profit, IBKR TRAIL
order after TP1, max hold D+5 MOC fallback, earnings risk exit.
Uses PositionTracker for state persistence.
```
