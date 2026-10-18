# A valódi round-trip költség — a kilépési oldal először megmérve

**Dátum:** 2026-10-18 · **Keret:** a 2. lépés, read-only mérés
**Task:** `docs/tasks/2026-10-18-true-roundtrip-cost.md`
**Reprodukció:** `python scripts/analysis/roundtrip_cost.py`

---

## 1. Két lelet, és a második a fontosabb

**(1) A kilépési oldal NEM ingyenes.** Előjeles shortfall **+50,0 bp** (belépés: +38,8).
A motor `2c` feltevése — „a kilépés annyiba kerül, mint a belépés" — **nagyjából helyes**,
sőt enyhén **alábecsüli** a kilépést.

**(2) De a BECSLŐ rossz.** A cost-model `median(|slippage|)`-et használ, ami a
**szimmetrikus drift félszélességét is költségnek számolja** — pedig az kiátlagolódik.

| | n | `median\|.\|` | **előjeles átlag** | adverz |
|---|---:|---:|---:|---:|
| **Belépés** (swing) | 82 | **83,9** | **+38,8** | 70% |
| **Kilépés** shortfall | 108 | 123,4 | **+50,0** | 62% |
| Kilépés — csak végrehajtás | 108 | 10,1 | +23,2 | 60% |

> 🟢 **Független földelés:** a SIM-1 **dollár-könyvelése** a belépési oldalra
> `$1 958 / $477 264 = **41,0 bp**`-t adott. Ez az **előjeles** becslővel egyezik
> (34,9 bp notional-súlyozott), **nem** a `median|.|` 83,9-cel. A median-konvenció
> nagyjából **megduplázza** a valós várható költséget.

## 2. A fal

| Konvenció | round trip | **breakeven IC** |
|---|---:|---:|
| **Feltételezett** `2c`, median\|.\| — a mai motor | 167,7 bp | **0,2795** |
| Mért belépés+kilépés, median\|.\| | 207,3 bp | 0,3454 |
| **Mért belépés+kilépés, ELŐJELES** ← a helyes | **88,9 bp** | **0,1481** |

**A fal feleződik: 0,280 → 0,148.**

És ha a §11.28-ban dokumentált (szándékosan **nem** implementált) konstrukciós
korrekciót is beszámítjuk (`κ = φ(z_c)/q ≈ 1,8` long-only top-q könyvre), a fal
**~0,082** lenne.

⚠️ **A verdikt ettől nem változik.** A score-család mért `|IC| < 0,009` —
a javított falhoz képest is **16×** hiány (κ-val ~9×). De a szám, amit két hete
mondtam, **kétszer akkora volt a valósnál**.

## 3. Estimand-fegyelem — amit előre ki kellett kerülni

A meglévő két szám **nem volt összemérhető**, és naiv összeadásuk megismételte volna
a 2026-10-04-i hibát:

| Szám | Referencia | Mit mér |
|---|---|---|
| belépési 83,5 bp | a plan `limit_price`-a | **döntés → fill** (drift + végrehajtás) |
| SIM-1 exit 6,6 / 61,2 bp | az ordertípus ígérte ár | **csak végrehajtás** |

Ezért **három külön nevesített metrika** mindkét oldalon: *implementation shortfall*,
*execution slippage*, *delay cost*. A riport **soha nem vonja össze őket.**

### A döntési pont levezetése (cronból + kódból, nem feltételezve)

| Exit-típus | Flag | Submit | Fill | Döntési ár |
|---|---|---|---|---|
| `TIME_STOP` | D−1 20:00 UTC eod_eval | D 19:40 UTC | D close | **D−1 close** |
| `TP1/TP2/*_SL` | D 20:00 UTC eod_eval | D+1 13:30 UTC | D+1 open | **D close** |

A fill-időbélyegek ezt megerősítik: **68 fill 19:59–20:00 UTC** (záró) és
**34 fill 13:30–13:32 UTC** (nyitás).

## 4. 🔴 A kilépési késleltetés egy JAVÍTHATÓ tervezési döntés

| Exit-típus | n | shortfall | ebből végrehajtás | **ebből késleltetés** |
|---|---:|---:|---:|---:|
| TIME_STOP | 68 | 121,9 | **5,4** | **122,6** |
| TP1 | 25 | 116,7 | 37,9 | 60,1 |
| MENTAL_SL | 10 | 155,1 | 73,1 | 81,2 |

*(median |bp|; előjeles alapon a teljes kilépésre shortfall +50,0 = végrehajtás +23,2
+ késleltetés +26,8)*

**A TIME_STOP végrehajtása gyakorlatilag ingyen van (5,4 bp) — a költség a
KÉSLELTETÉSBEN van.** Az ok szerkezeti: a döntés a D−1-i 20:00 UTC eod_evalon
születik, a végrehajtás D 19:40-kor — **egy teljes session** elsodródás.

> Ez **nem piaci adottság, hanem tervezési döntés**. A belépő referenciája ~1 órával
> a fill előtti; a kilépőé **egy teljes sessionnel**. Ugyanazon a napon döntve és
> végrehajtva a kilépési késleltetés nagy része megszűnne.

## 5. Minta és kizárások

**119 exit láb → 108 árazva, 11 kizárva**, tételesen:
10 × „nincs fill-rekord" (a korai swing-napok, ahol a `trades.details` még nem létezett)
+ 1 × adat-egészség: **PFGC 2026-07-28, fill 114,07 a napi sávon kívül
[114,68 ; 116,71]** — ugyanaz az ellenőrzés, ami a SIM-1-ben is két rossz fillt fogott.

## 6. Korlátok

1. **A döntési pont levezetett, nem logolt.** A cron + a `swing_positions.py`
   akció-szemantika alapján; a fill-időbélyegek megerősítik, de egy
   `decision_price` mező a ledgerben jobb lenne. Backlog-tétel.
2. **Egyetlen rezsim** (2026-05-18 → 09-30), 108 láb.
3. **A `median|.|` sorokat megtartom** az összehasonlíthatóságért a
   `cost_model.json`-nal — de a breakeven-hez az előjeles a helyes.
4. **Nem módosítottam a `cost_model.json`-t.** A becslő cseréje a
   `frl_cost.build_cost_model`-ben **értékelő-motor-változás**, külön döntés —
   ez a riport a bemenete, nem a végrehajtása.
5. A `TRAIL_SL` n=1 és a `TP2` n=4 — ezek a sorok zajosak, nem következtetésre valók.

## 7. Mit jelent ez a következő lépésre

A fal **0,280 → 0,148**, és ennek **két harmada a becslő-csere**, nem a kilépési oldal
felfedezése. A végrehajtási javítás tere:

- a **kilépési késleltetés** (~27 bp előjelesen) nagyrészt **szerkezeti és javítható**
- a **belépési oldal** LMT-vel (SIM-EXEC: +$2 442) szintén
- a maradék tiszta végrehajtás (**execution only: +23,2 bp kilépésen**) a piac ára

Együtt ~0,10 alá vihető fal reálisnak tűnik — de **a mért |IC| < 0,009 ettől még
egy nagyságrenddel alatta van.**
