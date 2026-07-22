Status: KILLED
Updated: 2026-07-21
Data-lane: v1
Attempt-family: A-0001..A-0004 (KILL, Tamás megerősítve 2026-07-21)

# HYP-004 — 5-napos szektor-relatív reversal

> Tartalom: Chat (Dev), 2026-07-21; **Tamás-jóváhagyás rögzítve** (2026-07-21).
> `REGISTERED` a `factors/reversal.py` zöld `sanity()` párja UTÁN — a sorrendet
> a saját lint (`assert_sanity_pair`) is kikényszeríti.
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

Első éles batch: `research/runs/2026-07-20/report.md` (attempt A-0001..A-0004).
Dev-ablak: legacy 59 nap / swing 19 nap; holdout-érintés **0**.

| h | Éra | mean IC | NW t | p | éra-bar | verdikt |
|---|---|---|---|---|---|---|
| 1 | legacy | −0.0183 | −0.94 | 0.350 | 0.0388 | inconclusive |
| 3 | legacy | −0.0143 | −0.82 | 0.421 | 0.0347 | inconclusive |
| 5 | legacy | −0.0298 | −1.52 | 0.157 | 0.0393 | inconclusive |
| 7 | legacy | −0.0278 | −1.42 | 0.199 | 0.0392 | inconclusive |
| 1 | swing | −0.0144 | −0.40 | 0.693 | 0.0718 | inconclusive |
| 3 | swing | −0.0705 | −1.88 | 0.118 | 0.0749 | inconclusive |
| 5 | swing | −0.0950 | −2.54 | 0.085 | 0.0749 | mérhető |
| 7 | swing | −0.1087 | −3.36 | 0.078 | 0.0647 | mérhető |

Šidák-családi p (4 h-variáns): **legacy 0.4946**, **swing 0.2787** — mindkettő BH-fail
(q=0.10). Half-life **2.4 nap** → implikált forgási költség **19 827 bp/év**; a legjobb
bruttó 3 151 bp/év (h=5 swing). Breakeven IC 0.29–0.74.

## KILL/PARK indoklás (ha releváns)

**KILL** — a pre-reg **(a)** kritérium szerint (Chat-javaslat 2026-07-21,
**Tamás megerősítette**; ledger `human_confirmed: true`).

A legacy családi p 0.4946 **elégséges T_eff mellett** (≈13) — tiszta bukás. A swing
p 0.2787 kis T_eff-en önmagában inconclusive lenne, de a döntéshez nem kell. A (b) ág
nem aktiválódott (az előjel helyes), a (c) sem (bruttó-pass hiányában).

**Fegyelmi pont:** a swing h=7 cella (−0.109, NW t=−3.36) **nem ok a felülbírálatra**.
A Šidák-családi p pontosan az ilyen cellakiemelés ellen véd; ha az első érdekes
t-statra kivételt tennénk, a teljes deflációs réteg dekoráció lenne.

### Két tanulság a loop visszacsatolásához

1. **A mechanizmus-tézis NEM dőlt meg — a tradeable erősség tézise bukott.**
   Mind a **8/8 cella negatív előjelű**, ami a mechanizmus irányát támogatja; a jel
   azonban a jelenlegi mintán **defláció után nem válik el a zajtól**.

2. **A költség-oldal önmagában is halálos lett volna.** Breakeven IC **0.29–0.74** vs
   éra-bar **0.03–0.07** — **nagyságrendi rés, nem határeset**. Következmény a
   hipotézis-térre: **gyors-turnover faktor ennél a végrehajtási stílusnál
   (next-day MKT open, 95.5 bp/oldal) strukturálisan halott.**

### Mi marad nyitva

Egy **alacsonyabb forgású reversal-variáns** (hosszabb formációs ablak,
overlap-portfólió implementáció) **ÚJ hipotézisként**, saját mechanizmus-indoklással
regisztrálható. **A KILL erre a specifikációra terminális, nem a témára.**
