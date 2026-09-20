# IFDS Daily Review — 2026-09-18 (péntek, Day 86/63) + **W38 heti zárás**

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ IBKR MCP connector nem elérhető — bróker-kereszt-ellenőrzés kimaradt; helyette Mini
> `reconcile_state` **silent OK**, kanonikus `pending_exits`, Polygon záró markok.

## 0. 🔴 D7 NAPI KÖTELEZŐ SOR — **az utolsó előtti nap a kapu előtt**
| | |
|---|---|
| **`cum_30d`** | **−5,15%** (−$5 152,43) — **BREACH**, **6. kereskedési nap** |
| Breach-sorozat | −3,38% → −3,38% → −3,45% → −4,26% → −4,62% → **−5,15%** — **monoton romlik** |
| Gördülés | 09-21: **−4,66%** · **09-22 (KAPU): −4,77%** *(0 jövőbeli realizált feltevéssel)* |
| **A kapu napján** | **BREACH** — a küszöbhöz **~+$1 770** kumulatív javulás kellene 2 nap alatt |

🟢 A pre-reg **irányadó** triggerek tiszták: `excess_10d_mean` **−0,10%**, `excess_15d_mean` **−0,11%**;
az `excess_10d_sum` is **lejött** (−0,98%). ⚠️ `excess_15d_sum` −1,68% BREACH (**D4: megfigyelés**).
**A `cum_30d` az egyetlen irányadó breach — és ez a 6. napja áll fenn.**

**Kapu: 2026-09-22 (kedd) — 1 kereskedési nap (09-21, hétfő) van hátra.**

## 1. Fejléc
- **Realized net: −$445,70** (gross −$444,28, komm. $1,42) — **1 exit**.
- **Cumulative: −$4 740,00 (−4,74%)** — új mélypont.
- **Net Liq: $95 885,19** — napi Δ **−$221,86**.
- **Excess: −0,32%** (portfolio −0,44% vs SPY −0,12%).
- **VIX 14,86 (−3,76%)**, SPY −0,12% — csendes nap.
- **Nyitott pozíciók: 6**; kitettség **50,46% → 39,58%**.

## 2. Exits (1)
| Idő (UTC) | Ticker | Kanonikus típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 19:59:33 | **OGE** | TIME_STOP | 232 | 47,38 → **45,46** | **−$445,70** (−4,05%) | ≈ −$248 | **−$198** |

⚠️ **A becslés HATODIK egymást követő napja alulbecsüli a veszteséget.** Az OGE a csütörtöki
46,30-as zárómarkról 45,46-ra esett. A sorozat: −$64 / −$172 / −$29 / −$171 / −$202 / **−$198**.
📌 **Ez már nem véletlen-eloszlású**: hat napból hat alkalommal **ugyanabba az irányba** tévedett.
**Leíró megfigyelés (G3)** — mechanizmust nem állítok, de a „tegnapi záró ≈ mai záró" feltevés
az aktuális tapén **rendszeresen optimista**.

📌 Az **OGE** a 09-10-i belépő volt (Utilities, +0,96% adverz fill) — teljes ciklusa **−$445,70**,
6 kereskedési nap alatt −4,05%.

## 3. Entries (0)
Nem volt belépő. A kitettség **39,58%**-ra esett (a 09-14-i 69,94%-os rekordról **négy nap alatt**).

## 4. Nyitott pozíciók (6) — 09-18 záró mark
| Ticker | Szektor | Bázis (fill) | Záró | Unrealized |
|---|---|---|---|---|
| MANH (TP1 után) | Technology | 207,82 | 211,46 | **+$47,32** |
| IMAX | Comm. Services | 52,80 | 52,77 | −$2,90 |
| CRBG | Fin. Services | 34,97 | 34,81 | −$37,60 |
| NWSA | Comm. Services | 30,13 | 29,78 | −$92,05 |
| EQH | Fin. Services | 54,96 | 53,95 | −$142,41 |
| **TS** | Basic Materials | 57,39 | 56,25 | **−$156,18** |
| **Σ** | | | | **−$383,82** |

A könyv **−$567,75 → −$383,82**; **1/6 pozitív**. A **TS hétfőn TIME_STOP-on zár** (≈ −$156).

## 5. Ops-checklist
- ✓ **Cron-lánc**: 14:30 Phase 4-6, 15:31 submit (0 tétel), 21:40 time_stop (OGE MOC),
  22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- 🔴 **D7-sor** (§0): `cum_30d` −5,15%, BREACH, 6. nap.
- ✓ **Az `exit_type` ma HELYES** (`TIME_STOP_MOC` a 21:40-es ablakban) — konzisztens §11.17-tel.

## 6. Anomáliák
- **🔴 A `cum_30d` monoton romlása** (§0) — hat nap alatt −3,38% → −5,15%.
- **⚠️ A becslés 6/6 egyirányú tévedése** (§2).
- **✅ VÁLTOZATLAN**: §11.17 `exit_type`, §11.18 szektor-cap rés, §11.20 (TP1/stop/breakeven
  a tervezett árhoz; a trail helyes), `swing_state.exits_today`, `commission_total`,
  `reconcile` csak ticker-halmaz, TP1 utáni max_hold-túlfutás, **FileVault**, **sync-rés**,
  **§5.1/§5.2 döntések**.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Visszalépés exit után** — n=13; **3 teljes ciklus lezárva, mind negatív** (Σ −$1 027,01).
- **TP1 (teljes swing-éra)** — n=25, ebből 3 negatív. **MENTAL_SL** — n=8. **TRAIL_SL** — n=1.
- **Next-day MKT fill slippage** — CC-éra n=53, változatlan (ma 0 belépő).
- **Kitettség** — **39,58%** (négy nap alatt 69,94%-ról).
- **Pozitív realizált nap** — 28/78 (ma nem).
- **Rally/risk-off aszimmetria** — enyhén eső nap, realized szerint −0,32% lemaradás.
- **TP-hit / pozitív-exit**: **0/1**. **Várt-vs-tény**: **−$198** (6. egyirányú).

---

# W38 heti zárás (2026-09-14 – 09-18)

| Mérőszám | **W38** | *(W37)* | *(W36)* |
|---|---|---|---|
| **Net P&L** | **−$1 534,49** | *−$1 444,61* | *+$78,61* |
| Cumulative | **−$4 740,00 (−4,74%)** | *−$3 205,51* | *−$1 760,90* |
| Portfolio heti | −1,53% | *−1,44%* | *+0,09%* |
| SPY heti | −0,34% | *−0,76%* | *+0,11%* |
| **Excess vs SPY** | **−1,19%** | *−0,68%* | *−0,02%* |
| **Nyerő napok** | **1 / 5** | *1/4* | *3/5* |

🔴 **A review-időszak LEGROSSZABB hete** (−$1 534,49), megelőzve a W37-et. **Két egymást követő
hét, együtt −$2 979,10.**

## 🔴 KÖTELEZŐ TP1-KORREKCIÓ (a §11.17 defekt miatt, harmadik hét sorban)
| | **A riport ezt írja** | **KANONIKUS valóság** (`pending_exits`) |
|---|---|---|
| TP1-találat | **3 / 5 (60%)** | **1 / 5** (csak a MANH) |
| TP1 átlag | **−$150,41** | **−$13,89** |

A riport **TP1-nek számolta** az **ELVN MENTAL_SL**-jét (−$430,15) és a **YPF TRAIL_SL**-jét (−$7,19).
Ellenőrzés: `(−13,89 − 430,15 − 7,19) / 3 = −150,41` ✓ — pontosan a riport száma.
📌 A riport **önmagával is ellentmond**: az „Exit Breakdown" helyesen **TP1 | N=1**, **TRAIL | N=1**,
**SL | N=1**, **MOC | N=4** (az `exits` blokkból). **A W38 helyes TP1-sora: 1/5, −$13,89.**

## A hét kanonikus exit-listája
| Nap | Ticker | Típus | Realized |
|---|---|---|---|
| 09-15 | MANH | **TP1** | −$13,89 |
| 09-15 | EQH | TIME_STOP | **+$112,06** |
| 09-16 | ELVN | **MENTAL_SL** | −$430,15 |
| 09-16 | FBP | TIME_STOP | −$373,22 |
| 09-17 | YPF | **TRAIL_SL** | −$7,19 |
| 09-17 | RCI | TIME_STOP | −$376,40 |
| 09-18 | OGE | TIME_STOP | −$445,70 |

📌 **7 exitből 6 veszteséges**; az egyetlen pozitív az EQH max_hold-exitje. **Négy TIME_STOP
együtt −$1 083,26.**

## A hét karaktere (tényszerű)
- **A hét a `cum_30d`-t −3,45%-ról −5,15%-ra vitte** — a breach nem enyhült, hanem **elmélyült**.
- **A veszteség széles, nem egy tételre koncentrált**: négy exit −$370 és −$446 között.
- **Három visszalépési ciklus zárult le ezen a héten** (ELVN, FBP, RCI) — **mind negatív**.
- **Az excess −1,19%**: abszolút **és** relatíve is rossz hét.

## Hétfő (09-21) és a kapu
1. **TS TIME_STOP** (137, ≈ −$156) — az egyetlen flagelt exit.
2. **🔴 A kapuig 1 kereskedési nap.** A `cum_30d` a kapu napján **−4,77%** körül várható
   (0 realizált feltevéssel) — **a leállítási feltétel fennáll**, ahogy a D7 rögzítette.
3. **⚠️ A §5.1 / §5.2 Tamás-döntés MÉG NYITOTT**, és **mindkettő új pint kíván** a
   `gate_sample.py`-ban (jelenlegi `68fc00e`). A gate-protokoll **§6/3** szerint a mintát
   **a futás ELŐTT** kell fixálni — **ez hétfőn esedékes, különben a kapu-futás a jelenlegi
   (nem véglegesített) §5-listával menne.**

## 8. Freeze-sor
🔓 Freeze feloldva 08-17 — **D6: prod FAGYVA 2026-09-22-ig**; **D7: a breach nem indok
paraméter-változtatásra.** G1/G3–G7 élnek. Ma **nem történt** production-kód változás.

## 9. A nap egy mondatban
Egyetlen max_hold-exit **−$445,70**-nel zárta a **review-időszak legrosszabb hetét** (−$1 534,49,
7 exitből 6 veszteséges), a `cum_30d` **−5,15%-ra mélyült — hatodik napja BREACH-ben, monoton
romlóan** —, a becslésem **hatodik egymást követő napon ugyanabba az irányba** tévedett, és a
heti riport **harmadszorra** számolt hamis TP1-eket (3/5 helyett a kanonikus **1/5**); **a kapuig
egyetlen kereskedési nap maradt, a §5.1/§5.2 döntés pedig még nyitott.**
