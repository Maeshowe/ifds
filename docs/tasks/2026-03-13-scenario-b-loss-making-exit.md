---
Status: OPEN
Updated: 2026-03-13
---

# Feature: Scenario B kiterjesztés — veszteséges pozíció korai zárása 19:00 CET-kor

## Kontextus

A `pt_monitor.py` Scenario B logikája jelenleg csak a **profitable** esetet kezeli:
ha 19:00 CET-kor az ár > entry * 1.005, trail aktivál. Ha a pozíció veszteséges,
semmi nem történik — a pozíció MOC-ra vár.

**Megfigyelt eset (2026-03-12, Day 19):**
- IMAX entry ~$39.78, MOC @$38.24 → **−$303.00**
- Ha 19:00-kor az ár már pl. −1.5% volt, korai zárással a veszteség kisebb lett volna

## Ötlet

Ha 19:00 CET-kor egy pozíció **veszteséges** (ár < entry * threshold), zárjuk le
azonnal piaci áron — ne várjunk MOC-ra.

```python
# Scenario B — loss making ág (vázlat)
if current_price < s["entry_price"] * LOSS_THRESHOLD:
    # SELL qty at market immediately
    # log + Telegram alert: "position loss-making at 19:00, closing early"
    s["trail_active"] = False
    s["scenario_b_eligible"] = False
```

**LOSS_THRESHOLD** — pl. 0.995 (−0.5%), 0.990 (−1.0%) — értékét adatból kell meghatározni.

## Mielőtt implementálnánk

Az alábbi kérdéseket kell adatból megválaszolni a 21 napos paper trading után:

1. Hány esetben volt a 19:00-as ár rosszabb a végső MOC árnál? (azaz a piac
   MOC-ra visszapattant — a korai zárás többet bukott volna)
2. Hány esetben volt a 19:00-as ár jobb a MOC árnál? (azaz a korai zárás
   kevesebbet bukott volna)
3. Mi lett volna az optimális threshold?

A Phase 4 Snapshot adatokból (feb 19-től) és a trades CSV-kből ez visszamenőleg
kiszámolható.

## Prioritás

**Low** — BC20 scope kandidáns. Ne implementáljuk amíg a 21 napos paper trading
le nem zárult és az adatok nem támasztják alá.

## Érintett fájlok

- `scripts/paper_trading/pt_monitor.py` — Scenario B loss-making ág
- `tests/paper_trading/test_pt_monitor.py` — új unit tesztek
