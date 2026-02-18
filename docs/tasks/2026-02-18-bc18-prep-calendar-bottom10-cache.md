# Task: BC18-prep — Trading Calendar + Bottom 10 Filter + Cache TTL Fix

**Date:** 2026-02-18
**Priority:** NORMAL
**Scope:** BC18 előrehozott elemek + backlog fix
**Builds on:** BC16 pipeline, phase4_stocks.py, sim/validator.py, data/cache.py

---

## Deliverable 1: T9 — NYSE Trading Calendar Integration

### Probléma
A pipeline nem ismeri az NYSE ünnepnapokat. Presidents' Day (feb 16) típusú problémák:
- Phase 2 earnings exclusion rossz dátumra szűrhet
- SimEngine fill window kereskedési napok helyett naptári napokat számol
- `_parse_run_date` nem tudja, hogy az adott nap ünnep-e

### Megoldás
`pandas_market_calendars` (vagy `exchange_calendars`) csomag integrálása.

**Új fájl:** `src/ifds/utils/trading_calendar.py`

```python
"""NYSE trading calendar utilities."""

import exchange_calendars as xcals
# VAGY: import pandas_market_calendars as mcal

def get_nyse_calendar():
    """Get NYSE trading calendar."""
    return xcals.get_calendar("XNYS")

def is_trading_day(date) -> bool:
    """Check if a date is a valid NYSE trading day."""

def next_trading_day(date, n=1):
    """Get the nth next trading day after date."""

def prev_trading_day(date, n=1):
    """Get the nth previous trading day before date."""

def trading_days_between(start, end) -> list:
    """Get list of trading days between two dates."""

def add_trading_days(date, n) -> date:
    """Add n trading days to a date (skip weekends + holidays)."""
```

**Dependency:** `exchange_calendars` (lightweight, no pandas dependency needed for basic usage). Check if already installed; if not, prefer `exchange_calendars` over `pandas_market_calendars` (smaller footprint).

### Integration Points

1. **SimEngine `broker_sim.py`** — `fill_window_days` should count trading days, not calendar days:
   ```python
   # BEFORE: for i in range(min(fill_window_days, len(daily_bars))):
   # AFTER: filter daily_bars to only trading days, then iterate
   ```
   Actually, since daily_bars from Polygon already only contain trading days, this may already be correct. **Verify** — if Polygon only returns bars for trading days, then the calendar is implicit. But the `max_hold_days` calculation in validator.py uses `timedelta(days=max_hold_days + fill_window_days + 5)` which counts calendar days for the Polygon request range. The `+ 5` padding should handle most holidays, but verify.

2. **Phase 2 `phase2_universe.py`** — Earnings exclusion date window should use trading days:
   ```python
   # Check if earnings date falls within next N trading days
   # Currently uses calendar days — should use trading_days_between()
   ```

3. **Execution plan CSV date handling** — `load_execution_plans()` in `validator.py` skips plans from today. No change needed, but could use `is_trading_day()` to skip weekend/holiday plans if any exist.

4. **SimEngine `validator.py`** — The `to_date` calculation for Polygon bars:
   ```python
   # Currently: to_date = run_date + timedelta(days=max_hold_days + fill_window_days + 5)
   # Better: to_date = add_trading_days(run_date, max_hold_days + fill_window_days + 2)
   ```
   This is more precise and avoids requesting too many or too few days.

### Tests
- `test_is_trading_day` — Presidents' Day 2026-02-16 = False, 2026-02-17 = True
- `test_next_trading_day` — From Friday → Monday (or Tuesday if Monday is holiday)
- `test_trading_days_between` — Feb 12-18 2026 = [12, 13, 17, 18] (4 days, not 5)
- `test_add_trading_days` — From Feb 12, +3 trading days = Feb 18 (skipping weekend + holiday)

---

## Deliverable 2: T3 — Bottom 10 Negative Filter (Phase 4)

### Probléma
A MoneyFlows Outlier elemzés (feb 13 journal) kimutatta:
- Bottom 10 veszteségek szisztematikusan nagyobbak (-28% to -40%) mint Top 20 nyereségek
- Közös profil: extrém eladósodottság, negatív margin, alacsony interest coverage
- Az IFDS jelenleg nincs explicit negatív szűrő ezekre — a funda score bünteti, de nem szűri ki

### Megoldás
Phase 4-ben, a combined score számítás ELŐTT, explicit "danger zone" szűrő:

```python
def _is_danger_zone(fundamental: FundamentalScoring, config: Config) -> bool:
    """Check if ticker has Bottom 10 risk profile.
    
    Based on MoneyFlows Outlier analysis:
    - Extreme debt (D/E > 5.0)
    - Negative net margin
    - Critical interest coverage (< 1.0)
    - Multiple danger signals compound the risk
    """
    danger_signals = 0
    
    if fundamental.debt_equity is not None:
        if fundamental.debt_equity > config.tuning.get("danger_zone_debt_equity", 5.0):
            danger_signals += 1
    
    if fundamental.net_margin is not None:
        if fundamental.net_margin < config.tuning.get("danger_zone_net_margin", -0.10):
            danger_signals += 1
    
    if fundamental.interest_coverage is not None:
        if fundamental.interest_coverage < config.tuning.get("danger_zone_interest_coverage", 1.0):
            danger_signals += 1
    
    # Need 2+ signals to trigger (avoid false positives from single metric)
    return danger_signals >= config.tuning.get("danger_zone_min_signals", 2)
```

### Config additions in `defaults.py`

Add to TUNING:
```python
"danger_zone_debt_equity": 5.0,          # D/E > 5 = extreme leverage
"danger_zone_net_margin": -0.10,         # Net margin < -10% = burning cash
"danger_zone_interest_coverage": 1.0,    # IC < 1 = can't cover debt payments
"danger_zone_min_signals": 2,            # Need 2+ danger signals to filter
```

### Integration in `phase4_stocks.py`

After fundamental scoring, before combined score:
```python
# Danger zone check (T3 — Bottom 10 filter)
if _is_danger_zone(fundamental, config):
    analysis = StockAnalysis(
        ticker=symbol, sector=ticker_obj.sector,
        technical=technical, flow=flow, fundamental=fundamental,
        excluded=True, exclusion_reason="danger_zone",
    )
    danger_zone_count += 1
    analyzed.append(analysis)
    continue
```

Add `danger_zone_count` to Phase4Result and logging.

Same for async path (`_run_phase4_async`).

### Tests
- `test_danger_zone_high_debt_negative_margin` — D/E=8, margin=-15% → filtered
- `test_danger_zone_single_signal_passes` — D/E=8 only → NOT filtered (need 2+)
- `test_danger_zone_low_debt_passes` — D/E=1.5, margin=10% → passes
- `test_danger_zone_none_values` — None fields → not counted as danger
- `test_danger_zone_config_override` — Custom thresholds work
- `test_phase4_danger_zone_integration` — End-to-end: dangerous ticker excluded from passed list

---

## Deliverable 3: Cache TTL Fix (Forward-Looking Date Ranges)

### Probléma
Ma azonosított bug: Polygon aggregates cache forward-looking date range-eket cache-el (pl. `from=2026-02-12&to=2026-02-27`). Ha a futtatás feb 12-én történt, 3 bar-t kapott. Feb 18-án ugyanaz a cache key-re 3 bart ad vissza, holott 5 bar elérhető.

### Megoldás
A `FileCache`-ben: ha a cache key `to_date` > today, ne cache-elje (vagy rövidebb TTL).

**Fájl:** Keresse meg a cache implementációt — valószínűleg `src/ifds/data/cache.py` vagy hasonló.

Logika:
```python
def should_cache(self, cache_key: str, response) -> bool:
    """Don't cache responses for date ranges that extend into the future."""
    # Extract to_date from cache key if it's a Polygon aggregates request
    # If to_date > today: don't cache
    # If to_date <= today: cache normally
```

Alternatív megközelítés (egyszerűbb): a SimEngine `_fetch_bars_for_trades` ne kérjen jövőbeli dátumot. Ehelyett `to_date = min(today, calculated_to_date)`. Így a cache key mindig a múltba mutat, és a cache valid.

```python
# In validator.py _fetch_bars_for_trades:
from datetime import date
today = date.today()
to_date = min(today, trade.run_date + timedelta(days=max_hold_days + fill_window_days + 5))
to_date_str = to_date.isoformat()
```

**Javaslat:** A második megközelítés (to_date cap) egyszerűbb és nem törékeny. A cache rendszer nem kell módosítani.

Fontos: ha T9 (trading calendar) is bekerül, a `to_date` számítás használja a `add_trading_days()` függvényt.

### Tests
- `test_fetch_bars_to_date_capped` — to_date never exceeds today
- `test_fetch_bars_uses_trading_days` — (ha T9 is kész) uses trading calendar

---

## Files to create
1. `src/ifds/utils/trading_calendar.py`
2. `tests/test_trading_calendar.py`

## Files to modify
1. `src/ifds/phases/phase4_stocks.py` — danger zone filter (sync + async paths)
2. `src/ifds/models/market.py` — `Phase4Result.danger_zone_count` field
3. `src/ifds/config/defaults.py` — danger zone TUNING keys
4. `src/ifds/sim/validator.py` — to_date cap + optional trading calendar usage
5. `src/ifds/output/telegram.py` — danger zone count in report (optional)
6. `src/ifds/output/console.py` — danger zone count in console output (optional)

## Validation
- `pytest` — all 784+ existing tests pass + ~12-15 new tests
- No breaking changes to existing pipeline behavior
- Danger zone filter is additive (only filters MORE tickers, never fewer)
- Cache fix is backward-compatible

## Dependency check
- `exchange_calendars` — check if installed, if not `pip install exchange_calendars`
- If `exchange_calendars` is problematic, fall back to `pandas_market_calendars`
