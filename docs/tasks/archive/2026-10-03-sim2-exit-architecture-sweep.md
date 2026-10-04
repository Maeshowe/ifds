Status: DONE
Updated: 2026-10-03
Note: EREDMÉNY — 0/15 cella pozitív, 0/14 Šidák-szignifikáns; a legjobb cella (3/2,0) −$4 187, p=0,35. Az exit-architektúra NEM menti meg a könyvet. Kitettség-diagnosztika: r=−0,738, −$1,95/pozíció-nap → negatív drift a belépőkben. Riport: docs/review/2026-10-03-sim2-exit-architecture-sweep.md. D6 SIM-napirend 2. tétel, post-gate. A SIM-1 (ae5e668) a geometria-hipotézist kizárta; a reziduális ~72% (irány/szelekció) még lehet exit-architektúra VAGY jel. Ez a task az exit-architektúra ágat teszteli. A RÁCS A FUTÁS ELŐTT RÖGZÍTVE (lásd §3) — post-hoc rács-bővítés TILOS.

# SIM-2 — exit-architektúra sweep a fix belépőkön (`max_hold` × TP1)

## 1. A kérdés

A SIM-1 megmérte, hogy a §11.20 geometria-javítás **≈$0**-t nyer (−$8, CI [−707, +649]),
és a veszteséget így dekomponálta: belépési slippage 26%, commission 3%, geometria 0%,
**reziduális irány/szelekció ≈72%**.

A reziduális két dolog lehet:
- **(a) exit-architektúra** — a belépők jók vagy semlegesek, de a `max_hold=5` / TP1=1,5·ATR
  konfiguráció rosszul fejezi be őket. Erősítő megfigyelés: a **TIME_STOP az első lábak
  50/78-a** (A konfiguráció), és a swing-érában a TIME_STOP hordozza a veszteséget
  (Σ −10,25%) szemben a TP2-vel (+25,08%).
- **(b) jel** — a belépők rosszak, és semmilyen exit nem javítja meg. Konzisztens a kapu
  mért ρ = +0,073-ával, ami a mért költségen számolt breakeven IC (0,15–0,18) **alatt** van.

Ez a task **csak (a)-t** teszteli. Ha (a) megbukik, az **(b) felé tolja** a mérleget — de
nem bizonyítja (b)-t.

## 2. Megközelítés — a belépők FIXEK

A sweep **ugyanazon a 78 valós pozíción** fut, amin a SIM-1 (azonos ticker, belépési dátum,
valós fill, valós ATR, valós qty). **Csak az exit-paraméterek változnak.**

Ez **szándékos elhatárolás**: a `sim/` Mode-2 re-score azt is megváltoztatná, hogy *mely*
tickerek kerülnek be — akkor nem lehetne a különbséget az exitnek betudni. A szelekciós
dimenzió külön kérdés (SIM-3), nem ez.

Eszköz: a SIM-1 validált harnesse (`counterfactual_geometry.simulate`), ami a **termelési**
`evaluate_position_eod()` pure függvényt futtatja. A hitelességi kapu már megvan
(72/76 = 95% exit-szekvencia egyezés, 9/9 szint-rekonstrukció).

**Horgony: a valós fill (B konfiguráció).** Nincs értelme egy jövőbeli architektúrát a
tervezett árhoz horgonyozni — azt a defektet amúgy is javítjuk.

## 3. A RÁCS — a futás ELŐTT rögzítve

| Tengely | Jelenlegi (baseline) | Pre-regisztrált értékek |
|---|---|---|
| `max_hold` (`swing_time_stop_trading_days`) | **5** | **{3, 5, 7, 10, 15}** |
| TP1 multiplikátor (`tp1_level = fill + m·ATR`) | **1,5** | **{1,0, 1,5, 2,0}** |

→ **15 cella**, ebből 1 a baseline → **14 összehasonlítás**.
Šidák α=0,05-re: **α_per-test = 1 − 0,95^(1/14) = 0,00366**.

**Fixen tartva** (nem a rács része): stop = 2,0·ATR, TP2 = 3,0·ATR, trail = 1,0·ATR,
`tp1_sell_pct` = 0,50, HARD_SL = −8% (amúgy is inert, 0/78).

**A rács post-hoc bővítése TILOS.** Bármilyen további tengely (stop, trail, sell_pct)
**2. szakasz: exploratív**, p-érték nélkül, kizárólag hipotézis-generáló címkével.

## 4. A statisztika — előre rögzítve

- **Primer metrika**: cellánkénti **Σ net P&L** a közös mintán.
- **Inferencia**: **párosított** összehasonlítás a baseline (5 / 1,5) ellen, pozíció-szinten
  (`pnl_cell − pnl_baseline`). Párosított t-teszt **és** párosított bootstrap CI (20k) —
  a P&L erősen nem-normális, ezért a bootstrap a döntő, a t csak referencia.
- **Multiplicitás**: Šidák, m=14. Szignifikancia-állítás csak α_per < 0,00366 alatt.
- **Közös minta**: egy pozíció **csak akkor** kerül be, ha **MINDEN cellában feloldható**
  (elég bar a leghosszabb `max_hold`-hoz). Különben egy hosszabb hold azért tűnne jobbnak,
  mert elhagyja a friss pozíciókat. A közös minta n-je a riportban szerepel.

### 4.1 Az aszimmetria, amit előre kimondok

**Ez a mérés csak az egyik irányban konklúzív.**
- Ha **még a legjobb cella is veszít** → a következtetés **robusztus**, a multiplicitás nem
  számít (az csak a legjobbat inflálja, és az is negatív).
- Ha a legjobb cella **pozitív** → a multiplicitás **döntően** számít, és az eredmény
  **nem promótálható** ezen az adaton; out-of-sample / új pre-reg kell.

## 5. Megvalósíthatósági korlát — slot-kontenció (KÖTELEZŐ riportálni)

A fix-belépős sweep **figyelmen kívül hagyja a kapacitást**: élesben `max_allowed=5`/nap és
`max_concurrent=12`. Egy `max_hold=15` cella 20+ egyidejű pozíciót igényelhet → **nem
stratégia, hanem artefakt**.

Ezért minden cellára ki kell számolni a **szimulált egyidejű pozíció-számot** (a fix
belépési dátumok + a cella szimulált exit-dátumai alapján), és jelölni, ha meghaladja a
12-es élő korlátot. Egy ilyen cella eredménye **felső korlát**, nem megvalósítható hozam.

## 6. Implementációs terv

- [x] `tests/test_exit_sweep.py` — TDD a sweep tiszta egységeire (közös minta, párosítás,
      konkurrencia-számolás, Šidák)
- [x] `scripts/analysis/exit_sweep.py` — a rács futtatása + párosított statisztika + riport
- [x] Bar-ablak kiterjesztése a leghosszabb `max_hold`-ra (SIM-1: 9 session → itt 17)
- [x] Baseline-konzisztencia check: a (5 / 1,5) cella **reprodukálja** a SIM-1 B-számát
      (−$5 357,89) a közös mintán — ha nem, a harness-paraméterezés hibás
- [x] Teljes rács + konkurrencia riportálása (MINDEN cella, nem a legjobb)
- [x] 2. szakasz (exploratív, p-érték nélkül): stop-multiplikátor próba
- [x] Riport `docs/review/2026-10-03-sim2-exit-architecture-sweep.md`

## 7. Keretezés (G1 / pre-reg)

Post-gate, leíró. A kapu mintájába/küszöbeibe visszamenőleg **nem** számít be, és azokat
**nem** módosítja. Bármely jövőbeli élő periódus **új pre-regisztrációt** kíván; ez a
szám annak inputja. A §3 küszöbök nem módosíthatók ennek fényében.

## 8. Commit üzenet

```
feat(analysis): SIM-2 — exit-architektúra sweep a fix belépőkön

max_hold {3,5,7,10,15} × TP1 {1.0,1.5,2.0} a SIM-1 validált harnessén,
a valós filleken. A rács a futás előtt rögzítve (14 összehasonlítás,
Šidák α_per=0.00366), a közös minta minden cellában feloldható pozíciókra
szűkítve, slot-kontenció cellánként riportálva.
```
