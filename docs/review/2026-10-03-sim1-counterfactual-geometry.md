# SIM-1 — a §11.20 exit-geometria ellenpróbája a valós filleken

**Dátum:** 2026-10-03 · **Keret:** D6 SIM-napirend 1. tétel, **post-gate, leíró**
**Task:** `docs/tasks/2026-10-03-sim-counterfactual-geometry.md`
**Reprodukció:** `python scripts/analysis/counterfactual_run.py [--fill-at-close]`

> ⚠️ **Ez a mérés a saját hipotézisemet cáfolta.** 2026-10-03-án azt javasoltam, hogy a
> §11.20 geometriai defekt javítása a −$6 460,95 **érdemi részét** visszanyerheti, és hogy
> ezért a veszteség-rekord „még nem érvényes bizonyíték". A mérés szerint a javítás
> **gyakorlatilag nullát** nyer vissza. A §11.20 defekt valós és az R:R-geometriát tényleg
> rontja — **de nem ez okozta a veszteséget.**

---

## 1. Az eredmény egy sorban

A §11.20 javítása a mintán **−$8** (95% CI **[−$707, +$649]**), miközben a minta tényleges
realizált vesztesége **−$7 657,43**. A hatás **0%**, nem 30%, és nem 50%.

| | |
|---|---|
| Minta (swing-éra zárt pozíciók, lefedett) | **n=78** |
| Telepített notional | $477 264 |
| Tényleges realizált (ezen a mintán) | **−$7 657,43** |
| Σ A (tervezett horgony — ahogy élesben futott) | −$5 349,83 |
| Σ B (fill-horgony — ahogy futnia kellett volna) | −$5 357,89 |
| **Σ B − Σ A** | **−$8,06** |
| Bootstrap 95% CI (20k, párosított) | **[−$707, +$649]** |
| P(a javítás > +$1 000-t nyer) | **0,2%** |
| P(a javítás > +$3 000-t nyer) | **0,0%** |

Az exit **53/78 pozíciónál teljesen változatlan** — a geometriai horgony ott egyáltalán nem
változtatott kimenetet. A maradék 25-nél a hatás **kiegyenlítődik**: +$637 nyereség és
−$645 veszteség.

---

## 2. Miért nulla — a mechanizmus

A §11.20 helyesen mondja, hogy adverz fill mellett a TP1-távolság összenyomódik és a
stop-távolság kitágul (R:R 0,75 → 0,23). **De a P&L-következmény kétirányú:**

| | Tervezett horgony (A) | Fill-horgony (B) |
|---|---|---|
| Stop helye | **lejjebb** (távolabb) | feljebb (közelebb) |
| TP1 helye | **lejjebb** (közelebb) | feljebb (távolabb) |
| → MENTAL_SL első lábként | 9 | **17** |
| → TIME_STOP első lábként | 50 | 44 |
| → TP1 első lábként | 19 | 17 |

A helyes geometria **hamarabb vágja a vesztőt** (a stop-outok majdnem duplázódnak) és
**később veszi a profitot**. A megfigyelt árutakon ez a két hatás **kioltja egymást**.

**Másodlagos, viselkedési megjegyzés (leíró):** a korrekt geometria rövidebb ideig tart
nyitva vesztő pozíciókat. Ez tőke-forgási és kockázati szempontból akkor is előny, ha a
P&L lapos — de **nem P&L-érv**, és nem is mérte senki ilyennek.

---

## 3. A módszer — ugyanaz a kód, más horgony

A mérés azon a tulajdonságon áll, hogy
`src/ifds/state/swing_positions.py::evaluate_position_eod()` **pure függvény**. Ezért az
ellenpróba **a termelési exit-logikával** futott, nem egy újraírt szimulátorral:

- **A konfiguráció** — `entry_price` = tervezett limit-ár, szintek = az execution plan szintjei
- **B konfiguráció** — `entry_price` = **valós fill**, szintek ugyanazokkal az ATR-multiplikátorokkal (2,0 / 1,5 / 3,0) a fillhez horgonyozva

Mindkét konfiguráció P&L-je a **valós fillel** mint költségalappal számol — a kettő között
tehát **kizárólag a szintek helye** különbözik. `test_uses_the_production_evaluator` őrzi,
hogy egy jövőbeli refaktor ne írja újra itt az exit-szabályokat.

Az ATR nem becsült: a plan-sor három szintje **ugyanabból az ATR-ből** származik, így
egzaktan visszafejthető (a három implikált érték mediánja, majd ±$0,02 toleranciával
validálva — a plan centre kerekít, három kerekítés összeadódhat).

### 3.1 A szint-rekonstrukció közvetlen validációja

16 pozícióra megvan a termelés **tárolt** geometriája (`swing_positions.json` backupok).
Ahol a horgony a tervezett ár volt, a rekonstrukcióm **9/9-ben centre egyezik** a
termelés által tárolt `atr` / `stop_level` / `tp1_level` értékekkel.

A 7 nem-egyező mind **2026-05-18…05-20**, a swing-pivot első napjai: ott a tárolt
`entry_price` **nem** a plan limit-ára (az ATR viszont ott is egyezik). Ezek a pozíciók
a mintában **nincsenek benne** (ellenőrizve: 0 átfedés), tehát az eredményt nem érintik.
📌 Önálló nyitott kérdés, hogy a §11.20 defekt **mikor keletkezett** — a pivot első
napjain a horgony még más volt.

---

## 4. A hitelességi kapu — a B-szám előtt

**Az A konfigurációnak reprodukálnia kellett a valóságot.** Ez a kapu a protokoll
szerint a B-szám közlésének előfeltétele volt.

| Kritérium | Eredmény (n=76) |
|---|---|
| Exit-típus **szekvencia** azonos | **72/76 (95%)** |
| Első exit-típus azonos | 74/76 (97%) |
| P&L-eltérés medián \|Δ\| | $56,02 |
| P&L-eltérés p90 \|Δ\| | $197,40 |
| Σ A vs Σ tényleges | −$5 776,53 vs −$7 657,43 |

A 4 típus-eltérés tételesen: RBC 06-22 (sim TP1+TIME_STOP / tény TP1+MENTAL_SL),
SAIC 07-31 (TP1+TIME_STOP / TP1+TP2), NSA 06-23 (TIME_STOP / TP1+TIME_STOP),
PFGC 06-25 (TP1+TIME_STOP / TP2).

### 4.1 A Σ-rés oka — megmérve, nem feltételezve

A $1 881-es Σ-rés **nem koncentrált** (a 6 legnagyobb eltérés a teljes |Δ| csak 25%-a),
tehát nem outage-outlierek okozzák. A valódi ok a **végrehajtás-időzítési zaj**, amit
közvetlenül megmértem a ledger valós exit-árain:

| Láb-típus | \|exit − OPEN\| medián | \|exit − CLOSE\| medián | melyikhez közelebb |
|---|---|---|---|
| TIME_STOP / MOC (n=77) | 107,9 bp | **6,6 bp** | **69/77 a CLOSE-hoz** |
| next-day 15:30 MKT (n=38) | **61,2 bp** | 81,2 bp | 21/38 az OPEN-hez |

- A MOC-láb modellje (aznapi close) **egzakt**: 6,6 bp.
- A next-day market-láb (következő nyitás) az **empirikusan jobb** választás (61 vs 81 bp),
  **de ~61 bp irreducibilis zajt hordoz** — ez pontosan a kapu $56-os medián |Δ|-ja.

Ez a zaj a **párosított** A↔B különbségből **kiesik** ott, ahol A és B ugyanakkor és
ugyanúgy lép ki (53/78 pozíció). Ezért a B−A becslés jóval pontosabb, mint amit a kapu
Σ-rése sugall — a bootstrap CI ezt kvantifikálja.

---

## 5. Érzékenységi ellenőrzés

A végrehajtási feltevés **felcserélve** (minden next-day exit a következő nap **close**-ján,
nem az open-ján — szándékosan maximálisan eltérő feltevés):

| Modell | Σ B − Σ A | 95% CI |
|---|---|---|
| **open-fill (empirikusan helyes, primer)** | **−$8** | [−$707, +$649] |
| close-fill (stressz-teszt) | +$1 146 | [+$185, +$2 340] |

**A verdikt modell-stabil abban, ami számít:** a hatás **egyik modellben sem haladja meg a
~$2 340-et**, és a primer modellben **nulla**. A modell-bizonytalanság (±$1 150) nagyobb,
mint a minta-bizonytalanság (±$700) — de **mindkettő egy nagyságrenddel a $7 657-es kérdés
alatt van.**

---

## 6. A veszteség dekompozíciója (n=78 minta)

| Komponens | Összeg | Arány |
|---|---|---|
| Belépési slippage ((fill − tervezett) × qty) | **−$1 958** | **26%** |
| Commission (modellezett, kalibrált) | −$215 | 3% |
| **§11.20 exit-geometria** | **−$8 … +$1 146** | **0% … 15%** |
| **Reziduális — irány / szelekció** | **≈ −$5 484** | **≈ 72%** |
| **Tényleges realizált** | **−$7 657,43** | 100% |

Belépési slippage: **41 bp** a notionalra, **55/78 (71%) adverz fill** — ez megerősíti a
§11.20 „~73% adverz" állítását, független úton.

HARD_SL **egyik konfigurációban sem tüzel** (0/78) — a −8%-os heti kapu pozíció-szintű
notionalon (≈$6 100 átlag) inert. Ez eddig nem volt kimondva.

---

## 7. Mit jelent ez — és mit NEM

**Amit eldönt:**
1. A **geometria-hipotézis halott.** A −$7 657 nem a §11.20 defekt következménye. A javítás
   továbbra is **helyes** elvégezni (az R:R-geometria valóban rossz, és a „breakeven" név
   valóban hazudik) — de **nem P&L-helyreállítási tétel**, és nem indokol élesítést.
2. A veszteség ~**72%-a irány/szelekció**, nem mechanika. Ez a kapu mért ρ = **+0,073**
   olvasatával **konzisztens** — két független úton ugyanaz a kép.
3. Az **én korábbi érvem**, hogy „a stratégia soha nem futott helyes geometriával, tehát a
   veszteség-rekord nem érvényes bizonyíték", **megbukott**. A rekord érvényesebb, mint
   gondoltam.

**Amit NEM dönt el:**
A reziduális 72% még mindig lehet **exit-architektúra**-probléma és nem **jel**-probléma:
a TIME_STOP az első lábak **50/78-a** (A konfiguráció). A tartási idő / TP1-küszöb kérdését
a **SIM-2** (`max_hold` × TP1 sweep, Mode-2 re-score + párosított t-teszt) teszteli. SIM-1
tehát **szűkítette** a hipotézis-teret — kizárta a geometriát —, de nem zárta le.

---

## 8. Korlátok (őszintén)

1. **n=78**, a 93 swing-éra zárt pozícióból. 13 kizárva, mert a `slippage_per_ticker` mező
   a korai napokon még nem létezett (fill nélkül nincs ellenpróba) — ez **adathiány, nem
   szelekció**, és a kizárás a futás előtt rögzült a taskban.
2. **2 kizárva adat-egészség alapon**: IMAX 08-18 (fill 52,75 a napi sávon kívül
   [50,54; 52,39]) és FBP 09-08 (28,71 vs [28,02; 28,57]). Ezek vagy korrekciós-évjárat-,
   vagy fill-rögzítési anomáliák. **Nyitott kérdés**, nem elhanyagolható: ha a fill a napi
   sávon kívül van, valamelyik adat hibás.
3. A bar-adat `adjusted=true` **a letöltés pillanatában**. A 2026-07-24 előtti rész
   ~2026-07-25-én, a többi 2026-10-03-án került cache-be — egy közbeeső split elvileg
   inkonzisztenciát okozhat. A fill∈[low,high] health-check ezt durva szinten szűri
   (2 találat), finom szinten nem.
4. A commission-modell `max($1,05; $0,0057/részvény)`, a 106 megfigyelt lábra illesztve
   (medián abs. hiba $0,04, p90 $0,11, összesen $126,73 modellezett vs $134,90 megfigyelt).
   Az A↔B különbségre ez szinte teljesen kiesik (azonos qty, közel azonos láb-szerkezet).
5. A minta realizáltja **−$7 657,43**, nem a −$6 460,95 all-time kumulatív — a kettő nem
   ugyanaz a halmaz (az utóbbi tartalmazza a legacy-érát és a 15 kizárt pozíciót).
   **Ne legyen összekeverve.**

---

## 9. Keretezés (G1 / pre-reg)

- A kapu-futás **2026-10-03-án lezárult** (`docs/decisions/2026-10-03-gate-run-outcome.md`),
  tehát a G3 nyelvi tilalom feloldódott.
- Ez a mérés **post-gate, leíró**: a kapu mintájába vagy a §3 küszöbeibe **visszamenőleg nem
  számít be**, és azokat **nem módosítja**. A pre-reg a kánon.
- Bármely jövőbeli élő periódus **új pre-regisztrációt** kíván; ez a szám annak **inputja**.
