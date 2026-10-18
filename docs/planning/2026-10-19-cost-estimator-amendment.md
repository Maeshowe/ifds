# PRE-REG AMENDMENT — a költség-becslő: csak valódi súrlódás, oldalanként mérve

**Dátum:** 2026-10-19
**Státusz:** ⏳ **JAVASLAT — Tamás döntésére vár.** Implementáció csak jóváhagyás után.
**Módosítja:** FRL-spec **§5.3** (becslő) · `scripts/research/frl_cost.py::build_cost_model`
**Előzmény:** `docs/review/2026-10-18-roundtrip-cost.md` §8 — három nyitott kérdés, itt eldöntve

---

## 0. IDŐZÍTÉSI TANÚSÍTVÁNY

> A 2026-10-18-i riport **kimondta**, hogy a cserét **nem implementálom**, amíg az
> (a)/(b)/(c) nyitott. Ez a dokumentum azokat **méréssel** dönti el, és **az
> implementáció előtt** rögzíti az eredményt. A score-család mind a 17 kara
> **statisztikai** KILL (`|IC| < éra-bar`), a (e) kapuig el sem jutottak — tehát
> **egyetlen verdikt sem függ ettől** (bizonyítva: §5).

---

## 1. Amit a 2026-10-18-i riport nyitva hagyott

| | Kérdés |
|---|---|
| **(a)** | A kilépési késleltetés költség, vagy kettős könyvelés a gross ellen? |
| **(b)** | A gross `close(t)`-hez horgonyoz, a költség a plan áráhozz — melyik a helyes? |
| **(c)** | A kapuba a pontbecslés vagy a felső korlát menjen? |

---

## 2. (a) ELDÖNTVE — a késleltetés KETTŐS KÖNYVELÉS

**A modell holding-periódusa `close(t) → close(t+h)`** (`frl_returns`: *„Returns are
close-to-close over NYSE trading days"*; HYP-005: *„a forward return t-napi close-tól"*).

A `TIME_STOP` fillje **`close(t+h)`** — **pontosan a modell kilépési pontja**. Amit
„késleltetésnek" mértem (`close(D−1) → close(D)`), az **a tartási perióduson BELÜL** van,
és a `gross = IC·σ_cs(h)·(252/h)` tag **már jóváírja**. Költségként terhelni **kétszer
vonná le ugyanazt**.

> ✅ **Döntés: a kilépési oldalon kizárólag a VÉGREHAJTÁSI slippage a költség**
> (fill vs. az ordertípus által ígért ár), a shortfall **nem**.

## 3. (b) ELDÖNTVE — és a mérés egy elkerülhető hibát tárt fel

A horgony-kérdést nem érveléssel, hanem **dekompozícióval** döntöttem el (n=80):

| Szakasz | előjeles | 95% CI | p | adverz |
|---|---:|---|---:|---:|
| plan → **OPEN** (overnight/pre-open rés) | **−1,5 bp** | [−20,7; +17,8] | **0,878** | 46% |
| **OPEN → fill** (a csengő utáni elsodródás) | **+48,3 bp** | **[+31,0; +64,3]** | **<0,0001** | **78%** |

**Az overnight rés nulla** — a plan ára kiváló becslése a nyitásnak. A belépési költség
**teljes egésze** a nyitás **utáni** elsodródás, és a fill a napi sáv **69%-ánál** landol.

> ✅ **Döntés: a költség a VALÓDI SÚRLÓDÁS — `fill` vs. az az ár, ami a kereskedés
> pillanatában elérhető volt** (belépésnél `open`, kilépésnél az ordertípus referenciája).
> A döntés-ártól mért elsodródás **horizont-eltérés, nem súrlódás**, és a gross
> specifikációjába tartozik, nem a költségbe.

### 3.1 🔴 A mechanizmus — és belső validáció két független oldalról

A submit cron **15:31 Budapest = 09:31 ET**, **egy perccel a nyitó csengő UTÁN** →
lemaradunk a **nyitó aukcióról**, és megvesszük az első percek momentumát.

A kilépési oldal **függetlenül megerősíti**:

| Ordertípus | n | tiszta végrehajtás |
|---|---:|---:|
| **TIME_STOP — MOC (aukciós)** | 68 | **+1,4 bp** |
| TP1 — market a csengő után | 25 | +46,8 bp |
| MENTAL_SL — market a csengő után | 10 | +80,8 bp |

**Az aukciós megbízás gyakorlatilag ingyen van; a csengő utáni market 47–81 bp.**
A belépési +48,3 bp **ugyanaz a mechanizmus, ugyanakkora** — két független oldal,
egy magyarázat. Ez nem feltevés: a saját adatunk.

## 4. (c) ELDÖNTVE — a meglévő kétküszöbös szerkezet megmarad

A (e) kapu ma **medián + p75** sávval dolgozik, és a köztes zóna `INCONCLUSIVE_ON_COST`.
Ez **már** a konzervatív, aszimmetrikus-veszteség-tudatos terv. Nem kell új fogalom —
csak a két szám előjeles analógja:

| (e) kapu slot | ma | **előjeles analóg** |
|---|---|---|
| `breakeven(median)` | `median(\|slippage\|)` | **pontbecslés** (notional-súlyozott előjeles átlag) |
| `breakeven(p75)` ← a kötő | `p75(\|slippage\|)` | **egyoldalas 95% felső konfidencia-korlát** |

> ⚠️ A p75 analógja **nem** az előjeles p75 — az egy per-trade kvantilis, míg a becslő
> most egy **portfólió-szintű első momentum**. A bizonytalanság a **középértékben** van,
> tehát a sáv felső vége a **középérték** felső korlátja.

## 5. Az új becslő és a fal

```
cost_bps_per_side_entry = notional-súlyozott előjeles (fill − open)/open,  qty > 0
cost_bps_per_side_exit  = előjeles (reference − fill)/reference,           per ordertípus
round_trip              = c_entry + c_exit            # NEM 2·c_entry
breakeven_ic            = round_trip / (σ_cs(h) · 1e4)
```

| | belépés | kilépés | round trip | **breakeven** |
|---|---:|---:|---:|---:|
| **pontbecslés** (medián-slot) | 48,3 | 23,2 | **71,5 bp** | **0,1192** |
| **felső korlát** (p75-slot, kötő) | 64,3 | 31,7 | **96,0 bp** | **0,1600** |
| *a mai motor (2 × median\|.\|)* | *83,5* | *—* | *167,0 bp* | *0,2783* |

**Kötelező adat-higiénia:** a `qty = 0` sorok **kizárva** — `MSM 2026-06-04 (−377 bp)` és
`VLO 2026-05-20 (−167 bp)` **meg nem történt trade-ek**, és véletlenül a két legnagyobb
kedvező print, tehát a szennyezés **lefelé** torzított.

## 6. Verdikt-invariancia (kötelező kísérő)

A `promote_verdict()` **ténylegesen lefuttatva** mind a 23 ledger-soron, a régi és az új
költség-modellel → **a bizonyítást az implementációs commit tartalmazza**. Elvárás: **0/23**,
mert mind a 17 score-családi kar `|IC| < éra-bar` miatt a (e) kapuig **el sem jut**.

## 7. 🟢 És egy AKCIÓKÉPES, SZIGNIFIKÁNS lelet

**A belépési +48,3 bp [31,0; 64,3], p < 0,0001 nem piaci adottság — egy perc késlekedés.**
Nyitó-aukciós (MOO) megbízással a nyitás **az** a fill.

| Forgatókönyv | round trip | breakeven |
|---|---:|---:|
| ma | 71,5 bp | 0,1192 |
| **MOO belépővel** | **23,2 bp** | **0,0387** |

**A fal a mai motorhoz képest 7×-esére javulna.** ⚠️ A mért `|IC| < 0,009` ettől **még
mindig 4× alatta van** — a halott jelet ez sem menti meg. De egy **jövőbeli** jelcsalád
küszöbe 0,278-ról **~0,04-re** esne, és ez **gyökeresen megváltoztatja, mi kereshető**.

📌 Ez **konzisztens a SIM-EXEC-kel** (+$2 442 limit-belépővel) — és **megmagyarázza**:
nem a tervezett ár volt különleges, hanem a nyitás utáni momentum elkerülése.

## 8. Mit kérek

| Döntés | |
|---|---|
| **D-C1** | A becslő „csak valódi súrlódás, oldalanként" alakra — **elfogadva / nem** |
| **D-C2** | `qty = 0` sorok kizárása (adat-higiénia) — **elfogadva / nem** |
| **D-C3** | A p75-slot = egyoldalas 95% felső korlát — **elfogadva / nem** |
| **D-C4** | A **MOO belépő** felvétele a javítandók közé (production, nem most) — **igen / nem** |
