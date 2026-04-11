# BC23 Phase 1 — Scoring Átírás

**Status:** DONE
**Updated:** 2026-04-11
**Priority:** P0
**Effort:** ~1.5h CC
**Depends on:** —
**Ref:** docs/planning/bc23-scoring-exit-redesign.md

---

## Változások

### 1.1 Freshness bonus kikapcsolás

**Fájl:** `src/ifds/config/defaults.py` → CORE

```python
# RÉGI:
"freshness_bonus": 1.5,
# ÚJ:
"freshness_bonus": 1.0,
```

### 1.2 RS vs SPY bonus csökkentés

**Fájl:** `src/ifds/config/defaults.py` → TUNING

```python
# RÉGI:
"rs_spy_bonus": 40,
# ÚJ:
"rs_spy_bonus": 15,
```

### 1.3 Scoring súlyok átrendezés

**Fájl:** `src/ifds/config/defaults.py` → CORE

```python
# RÉGI:
"weight_flow": 0.40,
"weight_fundamental": 0.30,
"weight_technical": 0.30,
# ÚJ:
"weight_flow": 0.60,
"weight_fundamental": 0.10,
"weight_technical": 0.30,
```

## Validáció

A `scripts/analysis/scoring_validation.py` újrafuttatása a meglévő historikus adaton (state/phase4_snapshots + cumulative_pnl.json) az ÚJ súlyokkal. A script-et módosítani kell hogy az új súlyokkal újraszámolja a combined score-okat és újra futtassa a korrelációs elemzést.

Elvárt eredmény:
- A Q5-Q1 spread csökkenése (kevésbé inverz)
- A flow korreláció megmarad vagy javul

Kimenet: `docs/analysis/scoring-validation-bc23.md`

## Tesztek

- Meglévő tesztek PASS (a paraméter változások nem törhetik a logikát)
- Új teszt: `test_freshness_bonus_neutral` — freshness_bonus=1.0 esetén a score nem változik
- Új teszt: `test_scoring_weights_sum` — az új súlyok összege 1.0

## Commit

```
feat(scoring): BC23 Phase 1 — reduce freshness bonus, RS weight, shift to flow-first

- freshness_bonus: 1.5 → 1.0 (eliminates artificial score inflation for "new" tickers)
- rs_spy_bonus: 40 → 15 (reduces momentum chasing dominance in tech_score)
- weight_flow: 0.40 → 0.60, weight_funda: 0.30 → 0.10 (flow is the only component
  with weak alpha per scoring validation report, r=+0.136, p=0.039)

Context: scoring validation showed inverse quintile pattern — highest scores
performed worst (Q5 avg -$13.41 vs Q1 avg +$8.76). The freshness_bonus (×1.5)
and rs_spy_bonus (+40) were the primary drivers of this inversion.
```
