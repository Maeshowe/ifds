Status: OPEN
Updated: 2026-04-02
Note: BC20 Phase_20C — Trail SIM support (broker_sim multi-day)
Depends: Phase_20A (rescore engine) kész

# BC20 Phase_20C — SIM-L2 Trail Szimuláció Támogatás

## Cél

A `broker_sim.py`-t kibővíteni multi-day holding + partial exit + trailing stop
szimulálással. Ez az alap a BC20A (Swing Hybrid Exit) SimEngine support-jához,
de önmagában is hasznos: a jelenlegi Paper Trading trail adatait össze tudjuk
hasonlítani a SIM eredményekkel.

## Háttér

A jelenlegi `simulate_bracket_order()` két párhuzamos lábat futtat (33% TP1/SL,
66% TP2/SL), de nincs benne:
- TP1 → trail átváltás (a valós PT-ben Scenario A ezt csinálja)
- Breakeven SL felhúzás
- Max hold days → MOC exit
- Partial exit tracking

## Scope

### 1. `broker_sim.py` — `simulate_swing_trade()` függvény

```python
def simulate_swing_trade(
    trade: Trade,
    daily_bars: list[dict],          # D+0 utáni bars
    tp1_atr_mult: float = 0.75,      # TP1 = entry + 0.75×ATR
    trail_atr_mult: float = 1.0,     # Trail stop = 1×ATR
    breakeven_atr_mult: float = 0.3, # BE trigger = 0.3×ATR profit
    max_hold_days: int = 5,
    tp1_exit_pct: float = 0.50,      # TP1-nél 50% exit
) -> Trade:
    """Simulate swing trade lifecycle.
    
    Day-by-day iteration:
    - Check TP1: if high >= tp1_price → partial exit (tp1_exit_pct)
    - Check SL: if low <= current_sl → full exit remaining qty
    - Breakeven: if close > entry + breakeven_atr * ATR → raise SL to entry
    - Trail: if TP1 triggered, trail_stop = max(prev_trail, high - trail_atr * ATR)
    - Max hold: if D+max_hold_days → exit at close
    """
```

### 2. Trade model bővítés

`models.py` Trade class — új mezők:

```python
# Swing extension fields
tp1_triggered: bool = False
tp1_exit_day: int = 0               # Which holding day TP1 triggered
partial_exit_qty: int = 0           # Qty exited at TP1
partial_exit_pnl: float = 0.0
trail_exit_price: float = 0.0       # Final trail stop exit price
breakeven_triggered: bool = False
exit_type: str = ""                 # "tp1_full", "tp1_partial+trail", "stop", "breakeven_stop", "max_hold"
```

### 3. ValidationSummary bővítés

```python
# Swing metrics
tp1_partial_exits: int = 0          # Partial exits at TP1
trail_exits: int = 0                # Trail stop exits (after TP1)
breakeven_exits: int = 0            # Exits at breakeven SL
max_hold_exits: int = 0             # MOC at max hold day
avg_hold_days_swing: float = 0.0    # Average holding days in swing mode
```

### 4. SIM-L2 variáns config

```yaml
# sim/configs/mode1_swing_variants.yaml
variants:
  - name: "1day_baseline"
    description: "Current 1-day MOC system"
    overrides:
      max_hold_days: 1
      tp1_atr_multiple: 0.75
      tp2_atr_multiple: 3.0

  - name: "swing_5day"
    description: "5-day swing with trail"
    overrides:
      max_hold_days: 5
      tp1_atr_multiple: 0.75
      trailing_stop_atr: 1.0
      breakeven_threshold_atr: 0.3
      tp1_exit_pct: 0.50
      sim_mode: "swing"             # triggers simulate_swing_trade

  - name: "swing_3day_tight"
    description: "3-day swing, tighter trail"
    overrides:
      max_hold_days: 3
      tp1_atr_multiple: 0.5
      trailing_stop_atr: 0.75
      tp1_exit_pct: 0.50
      sim_mode: "swing"
```

### 5. `replay.py` — sim_mode dispatch

```python
# In run_comparison / validate_trades_with_bars:
sim_mode = variant.overrides.get("sim_mode", "bracket")
if sim_mode == "swing":
    trade = simulate_swing_trade(trade, bars, **swing_params)
else:
    trade = simulate_bracket_order(trade, bars, **bracket_params)
```

## Paper Trading vs SIM összehasonlítás

A PT trail adatok (pt_events JSONL / pt_monitor_YYYY-MM-DD.log, cumulative_pnl.json) és a SIM swing eredmények
összehasonlíthatóságát dokumentálni kell:
- PT: Scenario A/B trail (IBKR real fills, intraday granularity)
- SIM: daily OHLCV bars (no intraday, conservative same-day ambiguity)
- Divergencia forrásai: intraday vs EOD, slippage, AVWAP fills

## Tesztelés

- `test_broker_sim_swing.py`:
  - TP1 trigger D+1 → 50% exit, trail aktív D+2
  - Breakeven trigger → SL felhúzás entry-re
  - Trail stop exit → pnl helyes
  - Max hold D+5 → MOC close price
  - Same-day TP1+SL ambiguity → conservative (SL)
  - 0 bars → Trade returned unchanged
- Meglévő `test_broker_sim.py` tesztek továbbra is green

## Commit

```
feat(sim): add swing trade simulation with trail stop support

simulate_swing_trade: day-by-day iteration with TP1 partial exit,
trailing stop activation, breakeven SL raise, and max hold MOC.
New Trade fields: tp1_triggered, partial_exit_qty, exit_type.
Supports 1-day vs 5-day comparison via sim_mode config.
```
