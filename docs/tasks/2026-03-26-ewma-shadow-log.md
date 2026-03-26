---
Status: DONE
Updated: 2026-03-26
Note: Per-ticker DEBUG + aggregated INFO log, PHASE_COMPLETE data bővítve, 4 teszt
---

# EWMA Shadow Log — Score Simítás Láthatóvá Tétele

## Probléma

Az EWMA smoothing (Phase_18A/1) deployolva van, de a pipeline logban
**nem látszik a hatása** — a napi review checklist nem tudja ellenőrizni,
hogy a simítás tényleg működik-e, és mekkora a különbség a raw és az EWMA
score között.

A 3 nap review-ból (`docs/review/2026-03-23..25`) mindegyikben `[!]` szerepel
az EWMA ellenőrzésnél, mert nincs adat a logban.

## Megoldás

Phase 6 scoring logikában (ahol az EWMA alkalmazódik) adjunk hozzá egy
EventLogger DEBUG sort minden tickerre ahol EWMA hatás van:

```python
logger.log(EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=6,
           message=f"[EWMA] {ticker} raw={raw_score:.1f} ewma={ewma_score:.1f} "
                   f"prev={prev_ewma:.1f} delta={ewma_score - raw_score:+.1f}",
           data={
               "ticker": ticker,
               "raw_score": raw_score,
               "ewma_score": ewma_score,
               "prev_ewma": prev_ewma,
               "delta": ewma_score - raw_score,
           })
```

Emellett a Phase 6 summary-ben (ami a cron logba kerül) adjunk egy aggregált sort:

```python
logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO, phase=6,
           message=f"[EWMA] {ewma_count}/{total_count} tickers smoothed, "
                   f"avg delta={avg_delta:+.1f}, max delta={max_delta:+.1f}",
           data={
               "ewma_count": ewma_count,
               "total_count": total_count,
               "avg_delta": avg_delta,
               "max_delta": max_delta,
           })
```

Ahol:
- `ewma_count`: hány tickernél volt korábbi EWMA adat (prev_ewma is not None)
- `avg_delta`: átlagos raw-ewma különbség
- `max_delta`: legnagyobb raw-ewma eltérés (abszolút)

## Implementáció

1. **Phase 6** (`phase6_sizing.py`): az EWMA alkalmazás helyén (ahol `_ewma_score()` hívódik) gyűjtsünk statisztikát
2. **Aggregált log**: Phase 6 summary blokkban
3. **Phase 4 snapshot**: ha az EWMA score mentésekor logolunk is (opcionális, DEBUG szint)

## Tesztelés

1. Unit: EWMA log sor megjelenik ha prev_ewma létezik
2. Unit: EWMA log sor NEM jelenik meg ha prev_ewma is None (első nap)
3. Unit: aggregált summary helyes értékekkel
4. Meglévő tesztek: 1034+ passing — regresszió

## Commit üzenet

```
feat(phase6): add EWMA shadow log for daily review visibility

Log raw vs smoothed score delta per ticker (DEBUG) and aggregate
summary (INFO) during Phase 6. Enables daily review checklist to
verify EWMA smoothing is working and measure its impact.
```

## Érintett fájlok

- `src/ifds/phases/phase6_sizing.py` — EWMA log sorok + aggregált summary
- `tests/test_bc18_ewma.py` — log assertion tesztek
