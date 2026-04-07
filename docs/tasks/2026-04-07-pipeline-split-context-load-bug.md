Status: DONE
Updated: 2026-04-07
Priority: P0 — BLOKKOLÓ (pipeline split nem működik, napi orderek 4 napos árakkal mennek)

# Pipeline Split Context Load Bug

## Probléma

A `python -m ifds run --phases 4-6` nem tölti be a mentett Phase 1-3 context-et.
A Phase 4 induláskor "No tickers from Phase 2" → skip Phase 4/5/6.
A `submit_orders.py` ezután a legutolsó létező CSV-ből dolgozik (akár napokkal régebbi árakkal).

**Éles hatás:** 2026-04-07 óta a pipeline split aktív. A 15:45-ös Phase 4-6 minden nap
üres univerzummal fut, a submit az ápr 3-i CSV-t használja. Stale limit árak.

## Gyökérok

`src/ifds/pipeline/runner.py` ~288. sor:

```python
if isinstance(phase, tuple) and phase[0] >= 4 and ctx.macro is None:
    from ifds.pipeline.context_persistence import load_phase13_context
    if load_phase13_context(ctx):
```

A Phase 0 **mindig fut** (mandatory safety check) és beállítja `ctx.macro = diag.macro`.
Ezért `ctx.macro is None` mindig False → a context SOHA nem töltődik be.

## Fix

A feltételt kell javítani. A `ctx.macro is None` helyett `ctx.universe` üresség-vizsgálat:

```python
if isinstance(phase, tuple) and phase[0] >= 4 and not ctx.universe:
    from ifds.pipeline.context_persistence import load_phase13_context
    if load_phase13_context(ctx):
```

Ez biztosítja, hogy ha Phase 2 nem futott (tehát nincs universe), a mentett context betöltődik.

## Érintett fájlok

- `src/ifds/pipeline/runner.py` — feltétel javítás (~288. sor)

## Tesztelés

1. Unit test: `--phases 4-6` → `load_phase13_context` meghívódik
2. Unit test: `--phases 1-6` (teljes pipeline) → `load_phase13_context` NEM hívódik
   (mert Phase 2 már kitöltötte a universe-t)
3. Integration: `state/phase13_ctx.json.gz` megvan, 1366 ticker →
   Phase 4 NEM skip-el, tickerek betöltődnek
4. Edge case: `state/phase13_ctx.json.gz` nem létezik → WARNING log, graceful fail

## Kiegészítő fix: deploy_intraday.sh log redirect

A `scripts/deploy_intraday.sh` crontab sorából hiányzik a log redirect.
A crontab-ban:

```
# JELENLEGI (stdout/stderr elveszik):
45 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && ./scripts/deploy_intraday.sh

# JAVÍTOTT:
45 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && ./scripts/deploy_intraday.sh >> logs/cron_intraday_$(date +\%Y\%m\%d_\%H\%M\%S).log 2>&1
```

## Kiegészítő fix: submit_orders.py stale CSV guard

A `submit_orders.py` ne submitoljon ha az execution plan CSV >1 kereskedési nap régi.
Jelenleg a legutolsó CSV-t olvassa — akár naposat is. Ha a Phase 4-6 nem generált
friss tervet, a submit ne fusson.

## Commit üzenet

```
fix(runner): load Phase 1-3 context when universe is empty in split mode

Phase 0 always runs and sets ctx.macro, causing the context load
condition (ctx.macro is None) to always be False. Changed to check
ctx.universe instead, so Phase 4-6 correctly loads saved Phase 1-3
output from state/phase13_ctx.json.gz.

Bug caused --phases 4-6 to skip all phases with "No tickers from
Phase 2" since the pipeline split went live on 2026-04-06.
```
