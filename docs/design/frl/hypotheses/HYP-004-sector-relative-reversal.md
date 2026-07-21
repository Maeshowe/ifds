Status: DRAFT
Updated: 2026-07-21
Data-lane: v1
Attempt-family: —

# HYP-004 — 5-napos szektor-relatív reversal

> Tartalom: Chat (Dev), 2026-07-21. A `Status: REGISTERED` átállítás Chat/Tamás
> lépése — a lint addig futás-tiltással kezeli (hypothesis-first).
> Ez az egyetlen azonnal, teljes értékűen tesztelhető hipotézis (tiszta v1 OHLCV),
> ezért az első éles batch-futás jelöltje.

## Mechanizmus (MIÉRT létezne — kötelező, teszt ELŐTT írva)

A rövid horizontú keresztmetszeti reversal a legrégebben dokumentált anomáliák
egyike (Jegadeesh 1990, Lehmann 1990: 1 hetes–1 hónapos megfordulás). Közgazdasági
motorja a **likviditás-nyújtás kompenzációja**: a nem-informált vételi/eladási
nyomás a fair value-n túlra tolja az árat, a visszahúzást a likviditás-nyújtó
aratja le.

A **szektor-relatív** változat kiszűri a szektor-momentum komponenst, és az
idioszinkratikus túllövést izolálja.

IFDS-specifikus relevancia: a legacy **„magas pontszám paradoxon"** (Q5 a
legrosszabb; négy egymást követő napon a napi top-score volt a leggyengébb
performer) megfigyelésileg konzisztens azzal, hogy a rendszer **lokális
túllövésnél vásárolt relatív nyerteseket**. Ez a faktor ugyanannak a jelenségnek
a tükörmérése a **teljes keresztmetszeten** — nem a trade-mintán (G1).

## Várt előjel és horizont

**NEGATÍV IC**: a múltbeli 5-napos szektor-relatív hozam a forward szektor-relatív
hozam **ellen** hat. Várt maximum **h=3–5**, h=7-re lecsengve.

A sanity-kontraktus `expected_sign = -1`-gyel fut: a beépített reversal-os
szintetikus panelen a faktornak negatív IC-t kell adnia.

## Ki a vesztes oldal / milyen frikció tartja fenn

Rövid horizontú **flow-chaser kereslet** (retail momentum, részben index/ETF
rebalance-nyomás). Azért nem arbitrálódik el, mert a kiaknázása **rövid távú
inventory-kockázat** viselését és **magas turnovert** igényel — ami egyben a mi
fő kockázatunk is.

## Költségprofil (várt turnover)

**MAGAS** turnover, várt half-life **~2–4 nap**.

Ez a hipotézis szándékosan a **cost-kapu stressz-tesztje** is. Előzetesen
rögzítve: reális kimenet az, hogy a **bruttó IC szignifikáns, a costed-IC ≤ 0**
a jelenlegi ~191 bp round-trip mellett (`cost_model.json`: 95.5 bp/oldal, n=28,
⚠️ kis-n). **Ez nem kudarc**, hanem a spec §5.3 kapu első éles demonstrációja.

## Pre-reg metrika és kill-kritérium

**Metrika:** szektor-relatív Spearman IC, h ∈ {1, 3, 5, 7}, **elsődleges h=5**;
éra-kvalifikált bar a §5.2 szerint (`max(0.02, 2×SE)`); a 4 h-variáns **EGY
attempt-család**, Šidák-családi minimum-p; costed-IC a `cost_model.json`
aktuális swing-értékén.

**Kill/Park-kritérium (a teszt ELŐTT rögzítve):**

| # | Feltétel | Döntés |
|---|---|---|
| a | családi Šidák p ≥ 0.10 a dev-ablakon, elégséges T_eff mellett | **KILL** |
| b | várttal ellentétes előjel (pozitív mean IC) **MINDKÉT** érán | **KILL** — a mechanizmus-tézis megdőlt |
| c | bruttó-pass, de **costed-IC ≤ 0** | **PARK** `execution-style-input` címkével |

A (c) ág indoka: **költség-korlátos, nem jel-korlátos** eredmény. A végrehajtási
stílus esetleges jövőbeli változása (next-day MKT open → limit/LOO belépő; Day 63
utáni vita) reaktiválhatja. A PARK auto-retest triggere ilyenkor a cost-modell
javulására, nem a minta növekedésére figyel.

## Eredmény (a batch tölti)

—

## KILL/PARK indoklás (ha releváns)

—
