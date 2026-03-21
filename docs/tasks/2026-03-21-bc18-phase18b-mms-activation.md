---
Status: OPEN
Updated: 2026-03-21
Note: BC18 Phase_18B — MMS + Factor Vol aktiválás, T5 sizing. Baseline kész (25 nap).
---

# BC18 Phase_18B — MMS Activation + Factor Volatility + T5 Sizing

## Kontextus

Az MMS store 25 napos baseline-nal rendelkezik (21 volt a minimum). A `mms_enabled`
és `factor_volatility_enabled` config flag-ek `False`-on állnak — aktiválni kell.

A T5 (BMI extreme oversold sizing) új kód, de egyszerű Phase 6 kiegészítés.

**Prioritás:** P1 — BC18 leggyorsabb deliverable, nincs dependency
**Becsült idő:** 1-2 óra

---

## Teendők

### 1. MMS aktiválás

`defaults.py` TUNING szekció:
```python
"mms_enabled": True,  # BC18B: activated 2026-03-21 (25-day baseline)
```

**Hatás:** Phase 5 MMS regime multiplier élesedik Phase 6-ban.
A `phase5_mms.py` `classify_regime()` eredménye → `gex_analysis.gex_multiplier` override.

### 2. Factor Volatility aktiválás

```python
"factor_volatility_enabled": True,  # BC18B: activated (BC16 code ready, 20 tests)
```

**Hatás:** VOLATILE regime detektálás (σ_gex > 2× median AND σ_dex > 2× median → 0.60× multiplier).
Regime confidence: `max(floor, 1.0 - σ_20/median_σ_20)`.

### 3. T5 — BMI Extreme Oversold Sizing

Phase 6 `_calculate_position_size()` kiegészítés:

```python
# T5: BMI extreme oversold → aggressive sizing
BMI_OVERSOLD_THRESHOLD = 25  # config key: bmi_oversold_threshold
BMI_OVERSOLD_MULTIPLIER = 1.25  # config key: bmi_oversold_multiplier

if bmi_value < config.tuning.get("bmi_oversold_threshold", 25):
    position_multiplier *= config.tuning.get("bmi_oversold_multiplier", 1.25)
```

**Új config kulcsok** (`defaults.py` TUNING):
```python
"bmi_oversold_threshold": 25,          # BMI < 25% = extreme oversold
"bmi_oversold_multiplier": 1.25,       # Aggressive sizing boost
```

---

## Tesztelés

1. Unit: MMS enabled → Phase 5 regime multiplier propagálódik Phase 6-ba
2. Unit: Factor volatility enabled → VOLATILE regime detektálás működik
3. Unit: T5 BMI < 25 → multiplier × 1.25
4. Unit: T5 BMI >= 25 → nincs változás
5. Integration: pipeline run MMS enabled + factor vol → scoring nem változik regressziót
6. Meglévő tesztek: 987 passing — regresszió

---

## Commit üzenet

```
feat(phase6): activate MMS regime multipliers and factor volatility (BC18B)

Enable mms_enabled and factor_volatility_enabled config flags.
MMS store has 25-day baseline (21 minimum met).
Add T5: BMI extreme oversold (<25%) aggressive sizing (×1.25).

987+ tests passing.
```

---

## Érintett fájlok

- `src/ifds/config/defaults.py` — config flag flip + T5 kulcsok
- `src/ifds/phases/phase6_sizing.py` — T5 oversold sizing logika
- `tests/test_bc18_mms_activation.py` — új tesztek
