Status: DONE
Updated: 2026-03-30
Note: Fixed — logger param added to _calculate_position(), 2 regression tests

# Fix: phase6_sizing.py — missing logger in _calculate_position()

## Probléma

A mai (2026-03-30) pipeline Phase 6-ban crashelt:

```
File "phase6_sizing.py", line 577, in _calculate_position
    logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO, phase=6,
    ^^^^^^
NameError: name 'logger' is not defined
```

A `_calculate_position()` privát függvény használja a `logger`-t az M_target penalty logolásához (~577. sor), de nem kapja paraméterként. A `logger` a `run_phase6()` scope-jában létezik, de nem adódik tovább.

## Miért nem jött elő eddig

Az M_target penalty logolás csak akkor triggerel, ha `multipliers["m_target"] < 1.0` ÉS az `analyst_target` valid szám. A korábbi napokban vagy nem volt target penalty, vagy a feltétel nem teljesült. Ma a VIX 30.89 (panic) + BMI 46.3 környezetben több ticker is analyst target felett kereskedett, így a penalty aktiválódott és triggerelte a crasht.

## Megoldás

1. Add `logger: EventLogger` paramétert a `_calculate_position()` függvényhez
2. A `run_phase6()`-ban a híváskor add át a `logger`-t
3. Ellenőrizd, hogy nincs más privát függvény ami szintén logger nélkül használja

## Érintett kód

`src/ifds/phases/phase6_sizing.py`

**Függvény szignatúra (régi):**
```python
def _calculate_position(
    stock, gex, macro, config, strategy_mode,
    original_scores, fresh_tickers, sector_map,
    mms_map, bmi_value,
) -> PositionSizing | None:
```

**Függvény szignatúra (új):**
```python
def _calculate_position(
    stock, gex, macro, config, strategy_mode,
    original_scores, fresh_tickers, sector_map,
    mms_map, bmi_value, logger,
) -> PositionSizing | None:
```

**Hívás (run_phase6, ~250. sor):**
```python
pos = _calculate_position(stock, gex, macro, config, strategy_mode,
                          original_scores, fresh_tickers, _sector_map,
                          _mms_map, bmi_value, logger)
```

## Tesztelés

- Meglévő tesztek KELL HOGY TÖRJENEK ha a paramétert nem adják át → javítani
- Adj hozzá tesztet: M_target < 1.0 esetén a logger.log meghívódik (mock logger)
- `pytest` all green

## Commit

```
fix(phase6): add missing logger parameter to _calculate_position

Pipeline crashed with NameError when M_target penalty tried to log.
The _calculate_position() helper used logger without receiving it
as a parameter. Pass logger from run_phase6() caller.
```

## Utána

Fix + push után Tamás újrafuttatja a pipeline-t Mac Mini-n:
```bash
cd ~/SSH-Services/ifds && python -m ifds run 2>&1 | tee logs/cron_20260330_manual.log
```
