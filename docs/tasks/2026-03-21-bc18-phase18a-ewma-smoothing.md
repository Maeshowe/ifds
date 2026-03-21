---
Status: DONE
Updated: 2026-03-21
Note: Implemented — _ewma_score(), state persistence, Phase 6 integration, 9 tests
---

# BC18 Phase_18A/1 — EWMA Smoothing a Scoring Pipeline-ban

## Kontextus

A Phase 4 combined score napi ingadozása (jitter) okoz false signal-okat:
egy ticker egyik nap 85, másnap 72, harmadik nap 88 score-ral fut. Az EWMA
(Exponentially Weighted Moving Average) simítás csökkenti ezt a zajt.

**Független a crowdedness döntéstől** — bármikor implementálható.

**Prioritás:** P1
**Becsült idő:** 2-3 óra

---

## Megközelítés

### EWMA logika

A Phase 4 combined score-t (vagy a Phase 6 sizing input-ot) simítjuk az
elmúlt N nap score-jával, EWMA span=10 ablakkal.

```python
# EWMA(t) = α * score(t) + (1 - α) * EWMA(t-1)
# ahol α = 2 / (span + 1) = 2/11 ≈ 0.182

def ewma_score(current_score: float, prev_ewma: float | None, span: int = 10) -> float:
    if prev_ewma is None:
        return current_score
    alpha = 2.0 / (span + 1)
    return alpha * current_score + (1 - alpha) * prev_ewma
```

### Hol tároljuk az előző EWMA-t?

**Phase 4 Snapshot** (`phase4_snapshot.py`) — már létezik napi persistence.
A snapshot-ba bekerül `ewma_score` mező, amit másnap olvasunk.

```python
# phase4_snapshot.py — snapshot bővítés
snapshot[ticker]["ewma_score"] = ewma_value

# phase6_sizing.py — EWMA olvasás
prev_snapshot = load_previous_snapshot(yesterday)
if prev_snapshot and ticker in prev_snapshot:
    prev_ewma = prev_snapshot[ticker].get("ewma_score")
    smoothed = ewma_score(combined_score, prev_ewma, span=config.tuning["ewma_span"])
```

### Config kulcsok

```python
# defaults.py TUNING szekció
"ewma_enabled": False,            # Feature flag (opt-in)
"ewma_span": 10,                  # EWMA smoothing window (trading days)
```

---

## Implementáció

1. **Config**: `ewma_enabled`, `ewma_span` kulcsok `defaults.py`-ba
2. **EWMA helper**: `src/ifds/phases/phase6_sizing.py` — `_ewma_score()` pure function
3. **Snapshot bővítés**: `phase4_snapshot.py` — `ewma_score` mező persist
4. **Phase 6 integráció**: ha `ewma_enabled`, olvasd a tegnapi snapshot-ot, simítsd a score-t
5. **Tesztek**: EWMA calc, snapshot roundtrip, no-history fallback

---

## Tesztelés

1. Unit: `ewma_score(85.0, None, 10)` → `85.0` (no history)
2. Unit: `ewma_score(85.0, 80.0, 10)` → `80.0 * 0.818 + 85.0 * 0.182 ≈ 80.91`
3. Unit: EWMA disabled → combined_score unchanged
4. Unit: Snapshot load/save with ewma_score field
5. Edge case: First day (no previous snapshot) → raw score used
6. Meglévő tesztek: 987+ passing — regresszió

---

## Commit üzenet

```
feat(phase6): EWMA score smoothing (BC18A, span=10)

Add exponential weighted moving average smoothing to Phase 6 scoring
to reduce daily jitter in combined scores. Uses Phase 4 snapshot for
persistence across pipeline runs.

Config: ewma_enabled (default False), ewma_span (default 10).
```

---

## Érintett fájlok

- `src/ifds/config/defaults.py` — `ewma_enabled`, `ewma_span`
- `src/ifds/phases/phase6_sizing.py` — `_ewma_score()` + integráció
- `src/ifds/data/phase4_snapshot.py` — `ewma_score` mező persist
- `tests/test_bc18_ewma.py` — új tesztek
