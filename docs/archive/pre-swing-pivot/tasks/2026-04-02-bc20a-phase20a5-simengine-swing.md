Status: DONE
Updated: 2026-04-03
Note: BC20A Phase_20A_5 — SimEngine Swing Support (~4h CC)
Depends: BC20 Phase_20C (Trail SIM) + Phase_20A_2 (PositionTracker)

# BC20A Phase_20A_5 — SimEngine Swing Support (Full Integration)

## Cél

A BC20 Phase_20C trail SIM-et kibővíteni a teljes swing lifecycle
szimulálással: VWAP entry filter, TP1 50% partial exit (nem 33%),
breakeven SL, OBSIDIAN regime-dependent trail, multi-day Position Tracker
állapotgép. Ez teszi lehetővé az 1-day vs swing A/B tesztet.

## Háttér

A Phase_20C egy alap swing szimulálást ad (TP1 partial + trail + max hold).
Ez a Phase azt bővíti ki a production-kész swing rendszer teljes logikájával.

## Scope

### 1. `broker_sim.py` — `simulate_swing_trade()` bővítés

Phase_20C-ben az alap megvan. Bővítések:

```python
def simulate_swing_trade(
    trade: Trade,
    daily_bars: list[dict],
    tp1_atr_mult: float = 0.75,
    trail_atr_mult: float = 1.0,
    trail_atr_volatile: float = 0.75,    # ÚJ: OBSIDIAN VOLATILE
    breakeven_atr_mult: float = 0.3,
    max_hold_days: int = 5,
    tp1_exit_pct: float = 0.50,          # 50% (nem 33%)
    vwap_prices: dict | None = None,     # ÚJ: VWAP entry filter
    mms_regime: str = "undetermined",    # ÚJ: OBSIDIAN regime
) -> Trade:
```

Változások Phase_20C-hez képest:
- `tp1_exit_pct = 0.50` (nem 0.33 — a design doc 50%-ot mond)
- `trail_atr_volatile`: ha mms_regime == "volatile" → tighter trail
- VWAP entry filter: ha vwap_prices megvan és price > vwap × 1.02 → no fill

### 2. `validator.py` bővítés — swing mode

A `validate_trades_with_bars()` swing módban a Polygon-tól `max_hold_days + 2`
napnyi bars-t kér (fill window + holding period).

### 3. SIM-L2 Comparison — 1-day vs swing

```yaml
# sim/configs/mode1_1day_vs_swing.yaml
variants:
  - name: "1day_moc"
    description: "Current: 1-day, MOC exit, 33%/66% bracket"
    overrides:
      max_hold_days: 1
      sim_mode: "bracket"
      
  - name: "swing_5day_50pct"
    description: "Swing: 5-day, 50% TP1, trail, breakeven"
    overrides:
      max_hold_days: 5
      tp1_exit_pct: 0.50
      trailing_stop_atr: 1.0
      breakeven_threshold_atr: 0.3
      sim_mode: "swing"
```

### 4. PT vs SIM összehasonlítás tool

Script a PT eredmények és SIM eredmények összevetéséhez:

```python
# scripts/sim/compare_pt_sim.py
def compare_pt_vs_sim(
    pt_cumulative: dict,        # cumulative_pnl.json
    sim_summary: ValidationSummary,
    date_range: tuple[date, date],
) -> dict:
    """Compare Paper Trading actual vs SIM predicted results."""
```

## Tesztelés

- Phase_20C tesztek bővítése:
  - 50% partial exit (nem 33%)
  - VWAP reject: price > vwap × 1.02 → no fill
  - VOLATILE trail: 0.75×ATR (nem 1.0×ATR)
  - 1-day vs swing comparison: different results
- `test_compare_pt_sim.py`: PT/SIM összevetés

## Commit

```
feat(sim): full swing simulation with VWAP filter and OBSIDIAN trail

Extends Phase_20C swing sim with 50% TP1 partial exit, VWAP
entry filter, OBSIDIAN VOLATILE tighter trail (0.75×ATR),
and 1-day vs 5-day swing comparison support.
```
