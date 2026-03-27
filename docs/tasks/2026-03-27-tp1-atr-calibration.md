---
Status: DONE
Updated: 2026-03-27
Note: Quick win — TP1 2×ATR → 0.75×ATR. Több intraday TP1 hit a bracket rendszerben.
---

# TP1 ATR Kalibráció — 2.0× → 0.75× ATR

## Probléma

A jelenlegi TP1 távolság 2× ATR — ez a napi teljes range átlaga, tehát
egy 1-napos kereskedésben szinte elérhetetlen. Az eddigi paper trading
adatokból: nagyon kevés TP1 hit, a legtöbb pozíció MOC-val zárt.

A swing-hybrid-exit-design.md (BC20A, D3 döntés) már rögzítette:
TP1 = 0.75× ATR, ami intraday reálisan elérhető.

**Ez a változtatás a jelenlegi 1-napos rendszerben is segít** — nem kell
hozzá a BC20A teljes infrastruktúra.

**Prioritás:** P1 — közvetlen P&L hatás
**Becsült idő:** 30-45 perc

---

## Implementáció

### 1. defaults.py — CORE szekció

```python
# RÉGI
"tp1_atr_multiple": 2.0,           # TP1 = Entry + 2 * ATR

# ÚJ
"tp1_atr_multiple": 0.75,          # TP1 = Entry + 0.75 * ATR (BC20A D3 döntés)
```

### 2. Hatásvizsgálat — mi változik

A `phase6_sizing.py` `_calculate_position()` metódusában:
```python
tp1_atr = config.core["tp1_atr_multiple"] * atr
# LONG: tp1 = entry + tp1_atr
```

Ezzel a TP1 közelebb kerül az entry-hez:
- Példa: ATR = $2.00, entry = $50.00
  - RÉGI: TP1 = $54.00 (2× ATR = $4.00 távolság)
  - ÚJ: TP1 = $51.50 (0.75× ATR = $1.50 távolság)

A TP2 változatlan marad (3× ATR) — de ellenőrizd a `tp2 > tp1` guard-ot:
```python
if tp2 <= tp1:
    tp2 = tp1 + atr
```
Ez a guard 0.75× TP1 és 3× TP2 mellett nem fog aktiválódni (3.0 > 0.75), rendben.

### 3. scale_out_atr_multiple is releváns?

A `scale_out_atr_multiple: 2.0` is 2× ATR-re van állítva. Ez a Phase 6-ban
a scale-out trigger ár. Ha a TP1-et 0.75×-ra állítjuk, a scale-out trigger
továbbra is 2× ATR-en marad — ami azt jelenti, hogy a scale-out soha nem
triggerelhet a TP1 ELŐTT (mert 2.0 > 0.75). Ez rendben van: a scale-out
a swing rendszerhez készült (BC20A), most nem releváns.

### 4. Bracket A/B split

A `submit_orders.py` SCALE_OUT_PCT = 0.33, tehát:
- Bracket A (TP1): 33% qty → TP1 = entry + 0.75× ATR
- Bracket B (TP2): 67% qty → TP2 = entry + 3× ATR

Ez jó arány: a pozíció harmada hamar profitot realizál, a maradék
kétharmad a nagyobb mozgásra vár (vagy MOC-val zárul).

---

## NE változtassunk

- TP2 (3× ATR) — marad, ez a "home run" target
- SL (1.5× ATR) — marad, ez az alapvető kockázatvédelem
- SCALE_OUT_PCT (0.33) — marad, a 33/67 split logikus
- Call wall TP1 override — marad (`if gex.call_wall > 0 and gex.call_wall > entry`)

---

## Tesztelés

1. Unit: `tp1_atr_multiple=0.75` → TP1 = entry + 0.75 * ATR
2. Unit: TP2 > TP1 guard — nem aktiválódik (3.0 > 0.75)
3. Unit: Call wall override — ha call_wall valid, az használandó (nem ATR)
4. Integration: pipeline run → execution_plan CSV TP1 értékek közelebb az entry-hez
5. Meglévő tesztek: 1034+ passing — regresszió

---

## PARAMETERS.md frissítés

```
tp1_atr_multiple: 0.75  (was 2.0) — BC20A D3 döntés, intraday elérhető TP1
```

---

## Commit üzenet

```
feat(phase6): TP1 calibration 2.0× ATR → 0.75× ATR

Reduce TP1 distance from 2.0× ATR to 0.75× ATR to increase intraday
hit rate. 0.75× ATR is realistically achievable within a trading day
(1× ATR ≈ daily range average). Per BC20A design decision D3.

TP2 (3× ATR) and SL (1.5× ATR) unchanged.
```

---

## Érintett fájlok

- `src/ifds/config/defaults.py` — `tp1_atr_multiple: 0.75`
- `docs/PARAMETERS.md` — frissítés
- Tesztek: meglévő TP1 tesztek frissítése ha hardcoded 2.0 értéket használnak
