# Task: phase1_regime.py — asyncio.gather return_exceptions fix

**Date:** 2026-02-26
**Priority:** CRITICAL — production risk
**Source:** QA Audit `2026-02-26-code-review.md` Finding F1
**Scope:** `src/ifds/phases/phase1_regime.py`

---

## A probléma

`phase1_regime.py:203` — `asyncio.gather` `return_exceptions=True` nélkül fut:

```python
results = await asyncio.gather(
    *[polygon.get_grouped_daily(day_str) for day_str in days]
)
```

~40 konkurens Polygon kérés indul. Ha bármelyik 429-et vagy timeout-ot dob, **az összes többi task megszakad** és Phase 1 crashel. Az egész napi pipeline leáll.

**Bizonyíték:** A kódbázis többi 5 `asyncio.gather` hívása (phase4:970, phase4:1024, phase5:411, phase5:417, validator:164) mind helyesen használja a `return_exceptions=True` paramétert.

---

## Fix

```python
# ELŐTTE
results = await asyncio.gather(
    *[polygon.get_grouped_daily(day_str) for day_str in days]
)

# UTÁNA
results = await asyncio.gather(
    *[polygon.get_grouped_daily(day_str) for day_str in days],
    return_exceptions=True
)
```

A gather után szűrd ki a hibás eredményeket a meglévő loop-ban:

```python
valid_results = []
for i, result in enumerate(results):
    if isinstance(result, BaseException):
        logger.log(f"[PHASE1] Polygon request failed for {days[i]}: {result}")
        continue
    valid_results.append(result)
results = valid_results
```

---

## Tesztelés

Új teszt: `tests/test_phase1_regime.py` (vagy meglévő fájlba):

```python
def test_gather_tolerates_single_polygon_failure():
    """Ha egy Polygon kérés 429-et dob, Phase 1 nem crashel."""
    ...

def test_gather_tolerates_all_failures():
    """Ha minden Polygon kérés hibás, Phase 1 üres listával tér vissza."""
    ...

def test_gather_partial_success():
    """3-ból 1 hiba — 2 valid result feldolgozva."""
    ...
```

---

## Git

```bash
git add src/ifds/phases/phase1_regime.py tests/test_phase1_regime.py
git commit -m "fix: asyncio.gather return_exceptions=True in Phase 1 (phase1_regime.py:203)

Single Polygon 429/timeout crashed entire Phase 1 pipeline.
Added return_exceptions=True + BaseException filter loop.
3 new tests: single failure, all failures, partial success.

QA Finding: 2026-02-26-code-review.md F1 [CRITICAL]"
git push
```
