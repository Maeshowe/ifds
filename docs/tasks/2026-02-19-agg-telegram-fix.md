# Task: AGG ETF Benchmark — Telegram Sector Table Fix

**Date:** 2026-02-19
**Priority:** LOW
**Scope:** Bugfix — AGG bond benchmark missing from Telegram sector table

---

## Probléma

A CLI console output tartalmazza az AGG (iShares Core U.S. Aggregate Bond ETF) sort a szektortáblázat alján mint benchmark. A Telegram output nem tartalmazza.

**Console (console.py):** `print_sector_table(phase3, prev_sectors, benchmark=agg_benchmark)` → AGG sor megjelenik szeparátorral a tábla végén.

**Telegram (telegram.py):** `_format_sector_table(ctx.sector_scores)` → csak 11 SPDR szektor, AGG hiányzik.

## Gyökérok

A `runner.py` Phase 3 blokkjában:
1. `agg_benchmark` SectorScore-t lekéri Polygon-ból ✅
2. Átadja a `print_sector_table`-nek (console) ✅
3. **NEM menti el a `ctx`-be** ❌
4. A `telegram.py` a `ctx.sector_scores`-ból dolgozik → AGG nincs benne

## Megoldás

### 1. PipelineContext bővítés

**Fájl:** `src/ifds/models/market.py`

Add `agg_benchmark` field to `PipelineContext`:
```python
agg_benchmark: SectorScore | None = None
```

### 2. Runner — mentés ctx-be

**Fájl:** `src/ifds/pipeline/runner.py`

A Phase 3 blokkban, az `agg_benchmark` kiszámítása után:
```python
ctx.agg_benchmark = agg_benchmark
```

(A `print_sector_table` hívás előtt vagy után, mindegy.)

### 3. Telegram — AGG sor hozzáadása

**Fájl:** `src/ifds/output/telegram.py`

Módosítás: `_format_sector_table` kapjon egy opcionális `benchmark` paramétert.

```python
def _format_sector_table(sector_scores: list, benchmark=None) -> str:
```

A sorted_scores iteráció UTÁN, ha benchmark is not None:
```python
    if benchmark:
        # Separator line
        rows.append("-" * len(header))
        
        mom = benchmark.momentum_5d
        arrow = "^" if mom > 0 else "v"
        mom_str = f"{arrow} {mom:+.2f}%"
        
        bmi_str = f"{benchmark.sector_bmi:.0f}%" if benchmark.sector_bmi is not None else "N/A"
        regime = benchmark.sector_bmi_regime.value.upper()
        
        if benchmark.breadth is not None:
            b_score_str = f"{benchmark.breadth.breadth_score:.0f}"
            raw_regime = benchmark.breadth.breadth_regime.value.upper()
            b_regime_str = _BREADTH_SHORT.get(raw_regime, raw_regime)
        else:
            b_score_str = "N/A"
            b_regime_str = "N/A"
        
        row = (
            f"{benchmark.etf:<5}"
            f"{mom_str:>9} "
            f"{'Benchmark':<9}"
            f"{'--':<6}"
            f"{bmi_str:<5}"
            f"{regime:<9}"
            f"{b_score_str:<6}"
            f"{b_regime_str:<8}"
        )
        rows.append(row)
```

### 4. Telegram hívás frissítés

A `_format_phases_0_to_4` Phase 3 blokkjában:
```python
# BEFORE:
lines.append(_format_sector_table(ctx.sector_scores))

# AFTER:
lines.append(_format_sector_table(ctx.sector_scores, benchmark=ctx.agg_benchmark))
```

## Fájlok
- `src/ifds/models/market.py` — `PipelineContext.agg_benchmark` field
- `src/ifds/pipeline/runner.py` — `ctx.agg_benchmark = agg_benchmark`
- `src/ifds/output/telegram.py` — `_format_sector_table` benchmark param + AGG row

## Tesztek
- Meglévő tesztek NEM törhetnek (a benchmark opcionális paraméter)
- Új teszt: `test_format_sector_table_with_benchmark` — ellenőrzi hogy az AGG sor megjelenik
- Új teszt: `test_format_sector_table_without_benchmark` — ha None, nincs extra sor

## Validáció
- `pytest` — all existing tests pass + 1-2 new
- Telegram üzenetben az AGG sor megjelenik szeparátorral a tábla végén
