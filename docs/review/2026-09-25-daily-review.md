# IFDS Daily Review — 2026-09-25 (péntek, Day 91/63) + **W39 heti zárás**

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ IBKR MCP connector nem elérhető — bróker-kereszt-ellenőrzés kimaradt; helyette Mini
> `reconcile_state` **silent OK**, kanonikus `pending_exits`, Polygon záró markok.

## 0. 🔴 D7 NAPI KÖTELEZŐ SOR + a kapu státusza
| | |
|---|---|
| **`cum_30d`** | **−5,62%** (−$5 623,85) — **BREACH**, **11. kereskedési nap** |
| **Kapu-futás** | 🔴 **TOVÁBBRA SEM TÖRTÉNT MEG** (0 db 09-es attribution-riport, mindkét gépen) |
| **§5.1 / §5.2 döntés** | **nem született meg**; pin **`68fc00e`** |
| **A kapu dátuma (09-22) óta** | **3 kereskedési nap** *(a review dátumán, 09-28-án: 4)* |

🟢 A pre-reg **irányadó** triggerek tiszták: `excess_10d_mean` **−0,36%**, `excess_15d_mean` **−0,22%**.
⚠️ `sum`-olvasatok BREACH — **D4: megfigyelés**.

📌 **A 09-22-i P0 (04-risks §11.21) a negyedik kereskedési napja nyitva.** A két út —
**(1) futás dokumentált dátum-eltéréssel**, **(2) a kapu-dátum újra-rögzítése** — változatlan;
mindkettő **írásbeli rögzítést kíván a futás ELŐTT**. **CC nem választ; Tamás-döntés.**
⚠️ Ez immár nem „kockázat", hanem **tény**: a kapu-döntés **négy kereskedési nappal késik**,
és a késés **nincs írásban rögzítve** — ezt pótolni kell, bármelyik utat választod.

## 1. Fejléc
- **Realized net: −$162,92** (gross −$161,74, komm. $1,18) — **1 exit**.
- **Cumulative: −$5 835,69 (−5,84%)** — új mélypont.
- **Net Liq: $94 953,76** — napi Δ **+$322,79** (a NetLiq harmadik napja emelkedik).
- **Excess: −0,71%** (portfolio −0,16% vs SPY +0,54%).
- **VIX 14,80 (−5,55%)**, SPY +0,54%.
- **Nyitott pozíciók: 3**; kitettség **29,54% → 21,94%** — **az éra legalacsonyabbja**.

## 2. Exits (1)
| Idő (UTC) | Ticker | Kanonikus típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 19:59:32 | **EQH** | TIME_STOP | 141 | 54,98 → 53,82 | **−$162,92** (−2,10%) | ≈ −$331 | **+$168** |

✅ **Második egymást követő kedvező eltérés** (+$24, **+$168**) — a kilenc napos egyirányú
sorozat megfordulása megerősítve. Az EQH a csütörtöki 52,61-es markról **53,82-ra emelkedett**.

### 📌 Az EQH ciklusa zárult — a visszalépési kép finomítva
| Ticker | Post-visszalépési ciklus | Eredmény |
|---|---|---|
| ELVN | 09-10 visszalépés → 09-16 MENTAL_SL | **−$430,15** |
| FBP | 09-08 → 09-16 TIME_STOP | **−$373,22** |
| RCI | 09-09 → 09-17 TIME_STOP | **−$376,40** |
| **EQH** | **09-17 → 09-25 TIME_STOP** | **−$162,92** |
| IMAX #2 | 08-28 → 09-08 TIME_STOP | **+$12,83** |
| IMAX #3 | 09-14 → 09-23 (TP1 + TS) | **+$58,62** |

📌 **Hat lezárt post-visszalépési ciklus: 4 negatív / 2 pozitív — és MINDKÉT pozitív az IMAX.**
*(Korábbi review-kban „3/3 negatív"-ot írtam; az IMAX két ciklusa ugyanebbe a kategóriába
tartozik, ezért a pontos kép 4/2. **Címke-pontosítás**, nem új adat.)*
Az **EQH teljes mérlege** (1. ciklus +$112,06 → visszalépés +1,87%-kal drágábban → −$162,92):
**−$50,86**.

## 3. Entries (0)
Nem volt belépő. **3 nyitott tétel**, kitettség **21,94%** — az éra legalacsonyabb szintje.
**Holnapra nincs tervezett exit.**

## 4. Nyitott pozíciók (3) — 09-25 záró mark
| Ticker | Szektor | Bázis (fill) | Záró | Unrealized |
|---|---|---|---|---|
| MD | Healthcare | 26,18 | 26,31 | **+$26,78** |
| NWBI | Fin. Services | 15,46 | 15,31 | −$100,65 |
| EXLS | Technology | 35,51 | 34,75 | −$135,28 |
| **Σ** | | | | **−$209,15** |

🟢 A könyv **−$688,65 → −$209,15** (+$479,50) — részben átsorolás (EQH), részben valós javulás.
**1/3 pozitív.**

## 5. Ops-checklist
- ✓ **Cron-lánc**: 14:30 Phase 4-6, 15:31 submit (0 tétel), 21:40 time_stop (EQH MOC),
  22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- 🔴 **D7-sor** (§0): `cum_30d` −5,62%, BREACH, 11. nap.
- 🔴 **A kapu-futás elmaradása** (§0) — 4. kereskedési nap.
- ✓ Az `exit_type` ma helyes (`TIME_STOP_MOC` a 21:40-es ablakban).

## 6. Anomáliák
- **🔴 A kapu-futás elmaradása immár 4 kereskedési nap, írásbeli rögzítés nélkül** (§0).
- **✅ A becslés megfordulása megerősítve** (2. kedvező nap, §2).
- **📌 A visszalépési kép címke-pontosítása**: 6 lezárt post-visszalépési ciklus, **4 negatív /
  2 pozitív**, mindkét pozitív az IMAX (§2).
- **✅ VÁLTOZATLAN**: §11.17 `exit_type`, §11.18 szektor-cap rés, §11.20, §11.21,
  `swing_state.exits_today`, `commission_total`, `reconcile` csak ticker-halmaz,
  TP1 utáni max_hold-túlfutás, **FileVault**, **sync-rés**.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Post-visszalépési ciklusok** — **n=6**: 4 negatív / 2 pozitív (mindkettő IMAX).
- **Teljesen lezárt TP1-ciklusok** — n=8 (7 pozitív + 1 negatív), Σ +$883,98.
- **TP1 (teljes swing-éra)** — n=26, ebből 3 negatív. **MENTAL_SL** — n=9. **TRAIL_SL** — n=1.
- **Next-day MKT fill slippage** — CC-éra n=56, változatlan (ma 0 belépő).
- **Kitettség** — **21,94%**, az éra legalacsonyabbja.
- **Pozitív realizált nap** — 29/83 (ma nem).
- **Becslési irány** — **2 egymást követő kedvező** eltérés a 9 napos ellenkező sorozat után.
- **TP-hit / pozitív-exit**: **0/1**. **Várt-vs-tény**: **+$168**.

---

# W39 heti zárás (2026-09-21 – 09-25)

| Mérőszám | **W39** | *(W38)* | *(W37)* | *(W36)* |
|---|---|---|---|---|
| **Net P&L** | **−$1 095,69** | *−$1 534,49* | *−$1 444,61* | *+$78,61* |
| Cumulative | **−$5 835,69 (−5,84%)** | *−$4 740,00* | *−$3 205,51* | *−$1 760,90* |
| Portfolio heti | −1,09% | *−1,53%* | *−1,44%* | *+0,09%* |
| SPY heti | **+1,27%** | *−0,34%* | *−0,76%* | *+0,11%* |
| **Excess vs SPY** | 🔴 **−2,36%** | *−1,19%* | *−0,68%* | *−0,02%* |
| **Nyerő napok** | **1 / 5** | *1/5* | *1/4* | *3/5* |
| Nyitott pozíciók (hét) | 3 (0,6/nap) | *5* | *6* | *5* |

🔴 **Az excess −2,36% a review-időszak legrosszabb heti értéke** — és a hét abszolút vesztesége
mellett az **SPY +1,27%-ot emelkedett**, ami a relatív képet külön rontja.
📌 **Három egymást követő veszteséges hét: W37 + W38 + W39 = −$4 074,79.**

## 🔴 KÖTELEZŐ TP1-KORREKCIÓ (negyedik hét sorban, a §11.17 defekt miatt)
| | **A riport ezt írja** | **KANONIKUS valóság** (`pending_exits`) |
|---|---|---|
| TP1-találat | **2 / 3 (67%)** | **1 / 3** (csak az IMAX) |
| TP1 átlag | **−$236,41** | **+$32,36** |

A riport **TP1-nek számolta a NWSA MENTAL_SL-jét** (−$505,17).
Ellenőrzés: `(32,36 − 505,17) / 2 = −236,41` ✓ — pontosan a riport száma.
📌 Az „Exit Breakdown" helyesen **TP1 | N=1**, **SL | N=1**, **MOC | N=5**.
**A W39 helyes TP1-sora: 1/3, +$32,36.**

## A hét kanonikus exit-listája
| Nap | Ticker | Típus | Realized |
|---|---|---|---|
| 09-21 | TS | TIME_STOP | −$199,47 |
| 09-22 | **IMAX** | **TP1** | **+$32,36** |
| 09-22 | CRBG | TIME_STOP | −$275,16 |
| 09-22 | MANH | TIME_STOP | −$11,59 |
| 09-23 | **IMAX** | TIME_STOP | **+$26,26** |
| 09-24 | NWSA | **MENTAL_SL** | −$505,17 |
| 09-25 | EQH | TIME_STOP | −$162,92 |

📌 **7 exitből 5 veszteséges**; a két pozitív **mindkettő IMAX**.

## A hét karaktere (tényszerű)
- **A hét a kapu hetét is magában foglalta** — és a **kapu-futás elmaradt** (§0).
- **A könyv leépült**: 6 → 3 nyitott tétel, kitettség 40,24% → **21,94%**. A hét **3 belépőt**
  hozott (0,6/nap), a legkevesebbet a review-időszakban.
- **A `cum_30d` −5,22% → −5,62%** — a breach a hét minden napján fennállt.
- **Az IMAX volt a hét egyetlen nyereséges tickere** (+$58,62 a 3. ciklusából).

## Következő hét (2026-09-28 – 10-02)
1. **🔴 A kapu-döntés** — négy kereskedési nap késés, írásbeli rögzítés nélkül (§0).
2. **Hétfőn nincs tervezett exit**; 3 nyitott tétel.
3. **`cum_30d`** — a breach 11. napja; a gördülés a jövő héten enyhülhet
   (a 08-13/08-14-i nagy veszteségek kigördülnek).
4. **FileVault** — a 3. előfordulás óta nyitva.

## 8. Freeze-sor
⚠️ A D6 prod-fagyás formálisan 09-22-vel lejárt, **de a feloldás a kapu utánra szólt**, és a futás
nem történt meg → a production-konfiguráció változtatása **továbbra sem indokolt** (§11.21).
**G1/G3–G7 élnek.** Ma **nem történt** production-kód változás.

## 9. A nap egy mondatban
Egyetlen max_hold-exit **−$162,92**-vel (a becslésnél **$168-cal kedvezőbben** — második egymást
követő kedvező eltérés) zárta a **review-időszak legrosszabb heti excess-ét** (**−2,36%**, miközben
az SPY +1,27%-ot ment); a könyv **3 tételre és 21,94%-os kitettségre** épült le, a **`cum_30d`
−5,62%-on, tizenegyedik napja BREACH-ben** áll — és a **kapu-futás négy kereskedési nappal a
dátum után is elmaradt, írásbeli rögzítés nélkül.**
