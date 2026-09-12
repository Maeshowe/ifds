# IFDS Daily Review — 2026-09-11 (péntek, Day 81/63) + **W37 heti zárás**

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ Az IBKR MCP connector ebben a sessionben nem érhető el — bróker-kereszt-ellenőrzés kimaradt.
> Helyette: Mini `reconcile_state` **silent OK**, kanonikus `pending_exits`, Polygon záró markok.

---

# 🔴 P0 — A PRE-REGISZTRÁLT LEÁLLÍTÁSI FELTÉTEL TELJESÜLT

```
STOP-triggerek: ⚠️ BREACH — cum_30d -3.4% < -3.0%
```

**A `cum_30d` ma −3,38%** (−$3 376,44), a pre-reg §3 leállítási küszöbe **−3,0%**.
**A paper trading periódus kezdete óta ez az ELSŐ alkalom, hogy bármely leállítási
feltétel teljesült.**

> **Pre-reg §3 (szó szerint, `2026-05-14…§3.14`, NEM módosítható):**
> **LEÁLLÍTÁS — bármelyik elég:** 10 napi excess < −1,0% **VAGY 30 napi kumulatív < −3,0%**
> **VAGY** 15 napi excess < −1,0%. **DEFAULT: PAPER FOLYTATÁS**, Day 180 újraértékelés.

⚠️ **Ez NEM a `sum`-olvasat vitája.** A D4-döntés (a `mean` az irányadó) a **10/15 napos
excess**-ablakokra vonatkozott, ahol az „átlag" szó kétértelmű volt. A **„30 napi kumulatív"**
egyértelmű, és **ez sérült**.

## A tegnapi aritmetika pontosan teljesült
A 09-10-i review §1-ben ezt írtam: *„a küszöb akkor NEM sérül, ha a mai realizált X > +$30,13"*,
és a markokból ≈ −$285,62-t vezettem le.

| | tegnap jelzett | **tény** |
|---|---|---|
| Bázis a nap nélkül | −$3 030,13 | −$3 030,13 ✓ |
| Napi realizált (X) | ≈ −$285,62 | **−$346,31** |
| **Eredmény** | ≈ −$3 315,75 (−3,32%) | **−$3 376,44 (−3,38%)** |

## ⚠️ A breach NEM átmeneti — a gördülés a következő 8 ülésen is BREACH-ben tart
**Nulla jövőbeli realizált feltevéssel** (a valós érték ehhez hozzáadja az adott nap realizáltját):

| +nap | Kigördülő nap | Új Σ | % | Státusz |
|---|---|---|---|---|
| +1 | 07-30 ($0,00) | −$3 376,44 | **−3,38%** | BREACH |
| +2 | 07-31 (+$176,52) | −$3 552,96 | **−3,55%** | BREACH |
| +3 | 08-03 ($0,00) | −$3 552,96 | **−3,55%** | BREACH |
| +4 | 08-04 (−$25,02) | −$3 527,94 | **−3,53%** | BREACH |
| +5 | 08-05 (+$91,29) | −$3 619,23 | **−3,62%** | BREACH |
| +6 | 08-06 (−$493,70) | −$3 125,53 | **−3,13%** | BREACH |
| +7 | 08-10 (+$110,77) | −$3 236,30 | **−3,24%** | BREACH |
| +8 | 08-11 (+$164,95) | −$3 401,25 | **−3,40%** | BREACH |

📌 **A mutató előbb ROMLIK** (−3,62%-ig), mert a kigördülő napok többsége pozitív. A visszatéréshez
**~+$376 kumulatív javulás** kellene — miközben az ablak négy legnagyobb vesztesége
(08-21 −$794, 09-09 −$668, 09-10 −$521, 09-01 −$502) **csak jóval később** gördül ki.

📌 **A kapu 2026-09-22 — 7 kereskedési nap.** A fenti mechanika szerint a feltétel
**a kapu napján is fennállna**.

## §5.2-érzékenység (a nyitott Tamás-döntés hatása)
Ha a **08-21-i outage-késleltetett tételek** (EQH −$371,36 + DLB TP1 +$154,47 = **−$216,89**)
kimaradnának a számításból:
**`cum_30d` = −$3 159,55 = −3,16% → MÉG MINDIG BREACH.**
📌 **A §5.2 döntés kimenetele tehát NEM változtatja meg a breach tényét.**

## Mit jelent ez eljárásilag
- **A leállítás HUMAN-IN-THE-LOOP döntés, nem automatizmus.** A monitor tervezési elve
  (pre-reg §4): *„kizárólag jelez, nem cselekszik — a leállítás Tamás-döntés."*
- **A pre-reg DEFAULT-ja a PAPER FOLYTATÁS** — de az a *„sem élesítés, sem leállítás"* esetre szól.
  Itt **egy leállítási feltétel kifejezetten teljesült**.
- **Ez a pontos helyzet, amiért a STOP-monitor 2026-07-25-én megépült** (04-risks §4):
  hogy egy leállítási feltétel **ne retroaktívan, hetekkel később** derüljön ki. **Nem az.**
- ⚠️ **Nem teszek javaslatot a leállításra vagy a folytatásra** — a §3 kritériumok
  pre-regisztráltak, a döntés a tiéd. Amit adhatok: a fenti tények és mechanika.

**🔴 TAMÁS-DÖNTÉS SZÜKSÉGES.**

---

## 1. Fejléc
- **Realized net: −$346,31** (gross −$343,90, komm. $2,41) — **2 exit**.
- **Cumulative: −$3 205,51 (−3,21%)** — **először megy $3 000 alá**.
- **Net Liq: $96 835,62** — napi Δ **−$152,58**.
- **Excess: −1,20%** (portfolio −0,34% vs SPY **+0,85%**). **MTM: −1,01%** — azonos előjel.
- **VIX 15,83 (−11,27%)**, SPY **+0,85%** — erős risk-on visszapattanás.
- **Nyitott pozíciók: 7**.

## 2. Exits (2)
| Idő (UTC) | Ticker | Kanonikus típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 13:30:09 | YPF | **TP1** (102→51) | 51 | 54,21 → 55,24 | **+$52,49** (+1,90%) | ≈ +$96 | −$43 |
| 19:59:30 | **NWS** | TIME_STOP | 228 | 34,46 → **32,71** | **−$398,80** (−5,08%) | ≈ −$382 | −$17 |
| **Σ** | | | | | **−$346,31** | ≈ −$286 | **−$61** |

📌 Az NWS-becslés **$17-on belül** volt; a Σ-hibát a YPF adta (a papír a csütörtöki 56,06-os
markról 55,24-re esett a TP1-fillnél, egy +0,85%-os SPY-napon).

## 3. Entries (1)
| Ticker | Qty | Planned→Fill | Slippage | Szektor |
|---|---|---|---|---|
| TS | 137 | 56,92 → **57,39** | +0,83% (adverz) | Basic Materials |

69 → **7 nyitott tétel**, kitettség **51,28%**.

## 4. Nyitott pozíciók (7) — 09-11 záró mark
| Ticker | Szektor | Bázis | Záró | Unrealized |
|---|---|---|---|---|
| YPF (TP1 után) | Energy | 54,21 | 55,55 | **+$68,34** |
| EQH | Fin. Services | 53,12 | 53,34 | **+$30,28** |
| TS | Basic Materials | 57,39 | 57,39 | $0,00 (ma nyílt) |
| RCI | Comm. Services | 36,83 | 36,21 | −$136,40 |
| OGE | Utilities | 47,37 | 46,55 | −$190,24 |
| ELVN | Healthcare | 57,57 | 54,32 | **−$282,75** |
| FBP | Fin. Services | 28,72 | 27,69 | **−$341,33** |
| **Σ** | | | | **−$852,10** |

A könyv **−$1 045,12 → −$852,10** (+$193,02) — részben átsorolás (NWS realizálódott). **2/7 pozitív.**
Az **ELVN** a második napján már **−$282,75**-en (−5,6%) — a 09-10-i „olcsóbb visszalépés"
azóta romlott.

## 5. Ops-checklist
- ✓ **Teljes cron-lánc lefutott**: 14:30 Phase 4-6, 15:30 eod_flags (YPF TP1), 15:31 submit (TS),
  21:40 time_stop (NWS MOC), 22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- 🔴 **`cum_30d` −3,38% — BREACH** (lásd P0).
- ⚠️ `excess_15d_sum` **−2,69%** BREACH — **D4: megfigyelés, nem trigger**.
- ✓ A **pre-reg irányadó excess-triggerek tiszták**: `excess_10d_mean` **−0,05%**,
  `excess_15d_mean` **−0,18%** (küszöb −1,0%).
- ℹ️ **Holnapra nincs tervezett exit** (`next_day_planned` üres).

## 6. Anomáliák
- **🔴 A `cum_30d` breach** — lásd P0. **A review-időszak legfontosabb eseménye.**
- **📌 Az `exit_type` defekt HARMADIK egymást követő napja nem tüzelt** — ma a YPF valódi TP1
  volt a 15:30-as ablakban, tehát a címke helyesen „TP1". **Konzisztens a 09-09-i korrigált
  mechanizmussal** (az ablak alapértelmezése véletlenül egyezik a tényleges típussal).
- **✅ VÁLTOZATLAN**: `swing_state.exits_today`, `commission_total` csak exit-láb,
  `entry_price=planned`, `reconcile` csak ticker-halmaz, **szektor-cap rés (§11.18)**,
  **TP1 utáni max_hold-túlfutás**, **FileVault**, **`docs/analysis/` sync-rés**,
  **§5.1/§5.2 döntések**.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **MENTAL_SL** — n=7, változatlan.
- **TP1-sorozat** — **n=7** (+YPF +$52,49). Teljesen lezárt ciklus: n=6, Σ +$850,84.
- **Pozitív realizált nap** — 27/73 (ma nem).
- **Visszalépés exit után** — n=9 (6 drágább / 3 olcsóbb).
- **Next-day MKT fill slippage** — CC-éra **n=48** (+TS +0,83%): **35 adverz / 13 kedvező** (72,9%).
- **Kitettség** — 51,28%.
- **Rally/risk-off aszimmetria** — erős rally-nap (SPY +0,85%), realized szerint **−1,20% lemaradás**.
  Sorozat: **14** rally-lemaradás vs 15 eső-napi felülteljesítés.
- **TP-hit / pozitív-exit**: **1/2**. **Várt-vs-tény**: **−$61**.

---

# W37 heti zárás (2026-09-07 – 09-11, 4 kereskedési nap — 09-07 Labor Day)

| Mérőszám | **W37** | *(W36)* | *(W35)* |
|---|---|---|---|
| **Net P&L** | **−$1 444,61** | *+$78,61* | *−$306,94* |
| Cumulative | **−$3 205,51 (−3,21%)** | *−$1 760,90* | *−$1 839,51* |
| Portfolio heti | −1,44% | *+0,09%* | *−0,30%* |
| SPY heti | −0,76% | *+0,11%* | *+0,48%* |
| **Excess vs SPY** | **−0,68%** | *−0,02%* | *−0,78%* |
| **Nyerő napok** | **1 / 4** | *3/5* | *1/5* |
| Kereskedési nap | **4** (Labor Day) | *5* | *5* |

## 🔴 KÖTELEZŐ KORREKCIÓ — a riport TP1-metrikája hibás (előre jelezve)
A 09-09-i és 09-10-i review-ban előre jeleztem, hogy a **§11.17 defekt** (az `exit_type` az
időablak alapértelmezett címkéjét adja) **elrontja a W37 TP1-sorát**. **Így is lett:**

| | **A riport ezt írja** | **KANONIKUS valóság** (`pending_exits`) |
|---|---|---|
| TP1-találat | **3 / 6 (50%)** | **1 / 6** (csak a YPF) |
| TP1 átlag-profit | **−$276,97** | **+$52,49** |

**A riport a MANH (−$362,11) és az INTA (−$521,28) MENTAL_SL-jét is TP1-nek számolta.**
Ellenőrzés: `(52,49 − 362,11 − 521,28) / 3 = −276,97` ✓ — pontosan a riport száma.

📌 A riport **önmagával is ellentmond**: az „Exit Breakdown" szekció helyesen `TP1 | N=1`-et ír
(az a `daily_metrics::exits` blokkból jön). **A W37 helyes TP1-sora: 1/6, átlag +$52,49.**
A kanonikus heti exit-lista: 4 TIME_STOP, 2 MENTAL_SL, 1 TIME_STOP (NWS), **1 TP1 (YPF)**.

## A hét karaktere (tényszerű)
- **A review-időszak legrosszabb hete** (−$1 444,61), **4 nap alatt** — és ez vitte a
  `cum_30d`-t a leállítási küszöb alá.
- **A veszteséget három tétel adta**: INTA −$521,28 (−11,91%, éra-rekord %), NWS −$398,80,
  MANH −$362,11. **Mindhárom stop-jellegű exit** (2 MENTAL_SL + 1 max_hold).
- **A VIX a hét közepén 18,00-ig ment** (09-04: 14,38), majd pénteken −11,27%-ot esett —
  a heti kép **risk-off csúcs, majd visszapattanás**.
- **Az excess −0,68%**: a hét abszolút **és** relatíve is rossz — a W34/W36 mintázata
  (az egyik olvasat kompenzál) **most nem érvényesült**.

## Következő hét (2026-09-14 – 09-18)
1. **🔴 A `cum_30d` breach kezelése — TAMÁS-DÖNTÉS.** A P0 szekció minden számot tartalmaz.
2. **A kapu 2026-09-22 — 7 kereskedési nap.** A fenti mechanika szerint a feltétel a kapu
   napján is fennállna; a két kérdés **összekapcsolódott**.
3. **§5.1 / §5.2 Tamás-döntés** — a §5.2 a breach tényét nem változtatja (lásd P0), de a
   kapu-mintát igen, és **új pint** kíván a `gate_sample.py`-ban.
4. **FileVault** — a 3. előfordulás óta nyitva.

## 8. Freeze-sor
🔓 A freeze 08-17-én feloldódott — **de a D6 szerint a production konfiguráció FAGYVA marad
2026-09-22-ig**. A **G1/G3–G7 guardrailek élnek**. Ma **nem történt** production-kód változás.

## 9. A nap egy mondatban
Két exit **−$346,31**-gyel a kumulatívat először vitte **$3 000 alá** (−$3 205,51) — és ezzel
**a paper trading periódus kezdete óta először teljesült egy pre-regisztrált leállítási feltétel**:
a **`cum_30d` −3,38%** a −3,0%-os küszöb ellenében, pontosan a tegnap levezetett aritmetika
szerint; a breach **nem átmeneti** (nulla jövőbeli realizált mellett is legalább 8 ülésen át
fennáll, előbb −3,62%-ig romolva), a **§5.2 döntés kimenetele sem változtat rajta**, és
**a kapu napján (09-22) is fennállna** — **a leállítás human-in-the-loop döntés, Tamásé**.
