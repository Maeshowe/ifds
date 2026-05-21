# BC23 Phase 4 — Egyszerűsítés és Flow Dekompozíció

**Status:** DONE
**Updated:** 2026-04-11
**Priority:** P0
**Effort:** ~3h CC
**Depends on:** BC23 Phase 1, Phase 2, Phase 3
**Ref:** docs/planning/bc23-scoring-exit-redesign.md

---

## Változások

### 4.1 MMS sizing kikapcsolás

**Fájl:** `src/ifds/config/defaults.py` → TUNING

```python
# RÉGI:
"mms_enabled": True,
# ÚJ:
"mms_enabled": False,
```

Az MMS feature store továbbra is gyűjt adatot (`mms_store_always_collect: True` marad). A sizing hatás kikapcsol, mert 93/100 ticker "undetermined" (nincs elég baseline adat) → az undetermined multiplier (0.75) egységesen bünteti az összes tickert, nem differenciál.

### 4.2 VWAP guard: REDUCE eltávolítás

**Fájl:** `src/ifds/phases/vwap.py`

A `vwap_entry_check()` függvényben a REDUCE ág eltávolítása:

```python
# RÉGI:
def vwap_entry_check(price, vwap):
    dist = vwap_distance_pct(price, vwap)
    if dist > reject_threshold:
        return "REJECT"
    elif dist > reduce_threshold:
        return "REDUCE"
    return "PASS"

# ÚJ:
def vwap_entry_check(price, vwap):
    dist = vwap_distance_pct(price, vwap)
    if dist > reject_threshold:
        return "REJECT"
    return "PASS"
```

A `_calculate_position()`-ban a `vwap_reduction` logika eltávolítása (vagy hagyható, mert REDUCE soha nem tér vissza).

### 4.3 Multiplier chain egyszerűsítés

**Fájl:** `src/ifds/phases/phase6_sizing.py` → `_calculate_multiplier_total()`

```python
def _calculate_multiplier_total(stock, gex, macro, config):
    # Kikapcsolt multiplierek — fix 1.0
    m_flow = 1.0
    m_insider = 1.0
    m_funda = 1.0
    m_utility = 1.0

    # Aktív multiplierek — változatlan logika
    m_gex = gex.gex_multiplier
    m_vix = macro.vix_multiplier
    m_target = _calculate_target_multiplier(
        stock.technical.price, stock.analyst_target, config
    )

    m_total = m_vix * m_gex * m_target
    m_total = max(0.25, min(2.0, m_total))

    multipliers = {
        "m_flow": m_flow,
        "m_insider": m_insider,
        "m_funda": m_funda,
        "m_gex": m_gex,
        "m_vix": m_vix,
        "m_utility": m_utility,
        "m_target": m_target,
    }
    return m_total, multipliers
```

A multiplier dict struktúra marad (a logolás és a CSV output kompatibilitás miatt), de a kikapcsolt értékek fix 1.0.

**FONTOS:** a `_calculate_position()`-ban a `bmi_oversold_multiplier` logika is kikapcsol (T5):
```python
# RÉGI:
if bmi_value is not None:
    bmi_threshold = config.tuning.get("bmi_oversold_threshold", 25)
    if bmi_value < bmi_threshold:
        bmi_mult = config.tuning.get("bmi_oversold_multiplier", 1.25)
        m_total = min(2.0, m_total * bmi_mult)

# ÚJ: eltávolítani vagy kommentelni — a BMI guard (Phase 6 max_positions csökkentés)
# már kezeli az extrém BMI-t, nem kell dupla mechanizmus
```

### 4.4 Flow al-komponens dekompozíció elemzés

**Fájl:** `scripts/analysis/flow_decomposition.py` (ÚJ)

A `scoring_validation.py` mintájára, de a flow_score al-komponenseire bontva:

```python
# A Phase 4 snapshotokból kiolvassuk az egyes flow al-komponenseket:
# - rvol_score (pure RVOL, squat nélkül)
# - squat_bar_bonus
# - dp_pct_score
# - pcr_score
# - otm_score
# - block_trade_score
# - buy_pressure_score

# Mindegyikre:
# 1. Pearson korreláció az adott napi P&L-lel
# 2. Spearman korreláció
# 3. Quintilis elemzés (top/bottom 20%)
# 4. Market cap szegmentálás: <$10B vs $10-50B vs >$50B
```

A Phase 4 snapshotokban (`state/phase4_snapshots/`) a flow al-komponensek külön mezőkben vannak-e? Ellenőrizd:
```bash
gzcat state/phase4_snapshots/2026-04-08.json.gz | python3 -c "
import json, sys
d = json.load(sys.stdin)
# Nézd meg az első ticker flow mezőit
for ticker, data in list(d.items())[:1]:
    print(json.dumps(data, indent=2))
" | head -50
```

Ha az al-komponensek nem külön mezőkben vannak a snapshotban → a Phase 4 snapshot mentést bővíteni kell (de ez nem blokkoló — a meglévő adatokból amennyit lehet).

Kimenet: `docs/analysis/flow-decomposition.md` — táblák, korrelációs számok

## Tesztek

- `test_multiplier_chain_simplified` — M_total = M_vix × M_gex × M_target, a többi 1.0
- `test_mms_disabled_no_sizing_effect` — mms_enabled=False esetén nincs multiplier hatás
- `test_vwap_no_reduce` — VWAP guard csak REJECT-et ad, REDUCE nem létezik
- Meglévő multiplier tesztek frissítése
- Meglévő VWAP tesztek frissítése

## Commit

```
feat(simplify): BC23 Phase 4 — multiplier chain, MMS, VWAP simplification

- Multiplier chain: 7 → 3 active (M_vix, M_gex, M_target)
  M_flow, M_insider, M_funda, M_utility fixed at 1.0
  (scoring validation: M_total did not correlate with P&L)
- MMS sizing: disabled (93/100 tickers "undetermined", flat 0.75× penalty)
  Feature store continues collecting baseline data
- VWAP guard: REDUCE path removed, only REJECT remains
- BMI oversold aggressive sizing (T5) removed — redundant with BMI guard

analysis: flow decomposition — per-component P&L correlation
  Standalone analysis to identify which flow sub-components are predictive.
  Output: docs/analysis/flow-decomposition.md
```
