# IFDS Daily Review — 2026-09-16 (szerda, Day 84/63)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ IBKR MCP connector nem elérhető — bróker-kereszt-ellenőrzés kimaradt; helyette Mini
> `reconcile_state` **silent OK**, kanonikus `pending_exits`, Polygon záró markok.

## 0. 🔴 D7 NAPI KÖTELEZŐ SOR — leállítási feltétel státusza

| | |
|---|---|
| **`cum_30d`** | **−4,26%** (−$4 258,16) — **BREACH**, **4. kereskedési nap** |
| **Breach-sorozat** | 09-11 −3,38% → 09-14 −3,38% → 09-15 −3,45% → **09-16 −4,26%** — **romlik** |
| Ma (09-17) kigördül | 08-04, **−$25,02** → bázis **−4,23%** |
| A breach feloldásához ma kellene | **> +$1 233,14** realizált |
| A mai flagek implikált várakozása | YPF TRAIL_SL ≈ +$22, RCI TIME_STOP ≈ −$205 → **Σ ≈ −$182** |

### ⚠️ A gördülés szerint a breach a KAPU NAPJÁIG fennmarad
**Nulla jövőbeli realizált feltevéssel** (a valós érték ehhez hozzáadja az adott nap realizáltját):

| +nap | Dátum | Kigördül | Új Σ | % | Státusz |
|---|---|---|---|---|---|
| +1 | 09-17 | 08-04 (−$25,02) | −$4 233,14 | **−4,23%** | BREACH |
| +2 | 09-18 | 08-05 (+$91,29) | −$4 324,43 | **−4,32%** | BREACH |
| +3 | 09-21 | 08-06 (−$493,70) | −$3 830,73 | **−3,83%** | BREACH |
| +4 | **09-22 (KAPU)** | 08-10 (+$110,77) | −$3 941,50 | **−3,94%** | **BREACH** |

📌 **A legjobb eset a következő 4 ülésen −3,83%** — a −3,0%-os küszöb visszaszerzéséhez
**~+$830–1 230** kumulatív realizált javulás kellene 4 nap alatt. **A D7 által előrejelzett
helyzet tehát beáll: a leállítási feltétel a kapu napján (09-22) is fenn fog állni**, hacsak
rendkívüli pozitív realizált nem érkezik.
⚠️ **Ez a monitor mechanikus állapota, nem a kapu-kimenetel előrejelzése** (§3).

🟢 A pre-reg irányadó **excess**-triggerek **mind tiszták**: `excess_10d_mean` −0,06% |
`excess_15d_mean` −0,03% | `excess_10d_sum` −0,61% | `excess_15d_sum` −0,50%.
**A `cum_30d` az egyetlen fennálló breach.**

**Kapu: 2026-09-22 — 4 kereskedési nap.**

## 1. Fejléc
- **Realized net: −$803,37** (gross −$800,34, komm. $3,03) — **2 exit, mindkettő nagy veszteség**.
  🔴 **A swing-éra 2. legrosszabb realizált napja** (08-21 −$794,39 → ma **−$803,37**; az új 2. hely).
- **Cumulative: −$3 910,71 (−3,91%)** — új mélypont.
- **Net Liq: $96 319,73** — napi Δ **−$422,42**.
- **Excess: −0,36%** (portfolio −0,80% vs SPY −0,44%).
- **VIX 17,56 (+2,09%)**, SPY −0,44% — harmadik egymást követő eső nap.
- **Nyitott pozíciók: 7**; kitettség **60,24% → 45,74%**.

## 2. Exits (2)
| Idő (UTC) | Ticker | Kanonikus típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 13:30:30 | **ELVN** | **MENTAL_SL** | 87 | 57,59 → **52,65** | **−$430,15** (−8,59%) | ≈ −$366 | −$64 |
| 19:59:30 | **FBP** | TIME_STOP | 333 | 28,72 → **27,60** | **−$373,22** (−3,90%) | ≈ −$201 | **−$172** |
| **Σ** | | | | | **−$803,37** | ≈ −$568 | **−$235** |

📌 **A becslés negyedik napja alulbecsüli a veszteséget** — mindkét papír a keddi zárómark alá
esett (ELVN 53,36 → 52,65; FBP 28,11 → 27,60) egy harmadik eső napon. A minta konzisztens:
**eső tapén a „tegnapi záró ≈ mai záró" feltevés rendszeresen optimista.**

### 📌 Két teljes visszalépési ciklus zárult — mindkettő a visszalépés ellen szól
| Ticker | 1. ciklus | Visszalépés | 2. ciklus | **Összesen** |
|---|---|---|---|---|
| **ELVN** | 08-25→09-01 TIME_STOP **−$197,89** | 09-10 @ 57,57 (**−0,47%, „olcsóbb"**) | 09-16 MENTAL_SL **−$430,15** | **−$628,04** |
| **FBP** | →09-04 TIME_STOP **+$227,10** | 09-08 @ 28,71 (+0,70%) | 09-16 TIME_STOP **−$373,22** | **−$146,12** |

⚠️ **Az ELVN a „kedvezőbb áron visszavett" eset volt** — és a második ciklusa **kétszer akkora
veszteséget** hozott, mint az első. **n=2, nem általánosítható (G3)**, de a D6 SIM-napirend
visszalépés-tételének közvetlen inputja.

### ⚠️ A §11.17 `exit_type` defekt HARMADIK esete
`pending_exits` (kanonikus): **ELVN = MENTAL_SL**. `trades.details.exit_type`: **„TP1"** ❌,
fill 13:30:30Z — a **normál 15:30-as ablak**. A `daily_metrics::exits` blokk helyesen `sl: 1`.
**Pontosan a 09-09-én korrigált mechanizmus** (az ablak alapértelmezett címkéje), harmadszor
(MANH 09-09, INTA 09-10, **ELVN 09-16**).

## 3. Entries (0)
Nem volt belépő. A kitettség **45,74%**-ra esett (a 09-14-i 69,94%-os rekordról), a könyv
7 tételre szűkült.

## 4. Nyitott pozíciók (7) — 09-16 záró mark
| Ticker | Szektor | Bázis (fill) | Záró | Unrealized |
|---|---|---|---|---|
| MANH (TP1 után) | Technology | 207,82 | 212,03 | **+$54,73** |
| YPF (TP1 után) | Energy | 54,21 | 54,65 | +$22,44 |
| CRBG | Fin. Services | 34,97 | 34,85 | −$28,20 |
| IMAX | Comm. Services | 52,80 | 52,07 | −$76,40 |
| TS | Basic Materials | 57,39 | 56,30 | −$149,33 |
| RCI | Comm. Services | 36,83 | 35,90 | −$204,60 |
| **OGE** | Utilities | 47,37 | 46,01 | **−$315,52** |
| **Σ** | | | | **−$696,88** |

A könyv **−$1 067,75 → −$696,88** (+$370,87) — a javulás **átsorolás** (az ELVN és az FBP
realizálódott). **2/7 pozitív.** Az **OGE** a legrosszabb tétel (−$315,52, −2,9%).

## 5. Ops-checklist
- ✓ **Cron-lánc**: 14:30 Phase 4-6, 15:30 eod_flags (ELVN MENTAL_SL), 15:31 submit (0 tétel),
  21:40 time_stop (FBP MOC), 22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- 🔴 **D7-sor** (§0): `cum_30d` −4,26%, BREACH, 4. nap, **romló**.
- 🟢 Az összes irányadó excess-trigger tiszta.
- 📌 **ÚJ EXIT-TÍPUS a holnapi flagek között: `YPF_TRAIL_SL`** — az első **trailing-stop** exit
  a review-időszakban. A YPF a TP1 utáni maradék, amelyre a trail aktív.

## 6. Anomáliák
- **🔴 A `cum_30d` a kapu napjáig BREACH-ben marad** a gördülés szerint (§0) — a D7 által
  előrejelzett helyzet.
- **📌 Két teljes visszalépési ciklus zárult, mindkettő negatív összeggel** (§2) — köztük az
  „olcsóbb" ELVN.
- **⚠️ A §11.17 defekt 3. esete** (§2) — a mechanizmus stabilan reprodukálódik.
- **📌 A becslés 4. napja alulbecsül eső tapén** (§2).
- **✅ VÁLTOZATLAN**: `swing_state.exits_today`, `commission_total` csak exit-láb,
  `entry_price=planned` (§11.10/§11.20), `reconcile` csak ticker-halmaz, szektor-cap rés (§11.18),
  TP1 utáni max_hold-túlfutás, **FileVault**, **sync-rés**, **§5.1/§5.2 döntések**.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **MENTAL_SL** — **n=8** (+ELVN −$430,15).
- **TP1 (teljes swing-éra)** — n=25, ebből 3 negatív. *(Ma nem bővült.)*
- **Visszalépés exit után** — n=12; **2 teljes ciklus lezárva**, mindkettő negatív (§2).
- **Next-day MKT fill slippage** — CC-éra n=51, változatlan (ma 0 belépő).
- **Kitettség** — **45,74%** (a 69,94%-os rekordról két nap alatt).
- **Pozitív realizált nap** — 28/76 (ma nem).
- **Rally/risk-off aszimmetria** — eső nap, realized szerint **−0,36% lemaradás** (ritka:
  eső napon is lemaradás). Sorozat: 14 rally-lemaradás vs 15 eső-napi felülteljesítés.
- **TP-hit / pozitív-exit**: **0/2**. **Várt-vs-tény**: **−$235**.

## 8. Ma (csütörtök, 09-17) — várt + feltevés *(nagyságrend, nem előrejelzés)*
| Idő | Ticker | Típus | Qty | Bázis / 09-16 záró | `várt` |
|---|---|---|---|---|---|
| 15:30 | **YPF** | **TRAIL_SL** (új típus) | 51 | 54,21 / 54,65 | **≈ +$22** |
| 21:40 | **RCI** | TIME_STOP | 220 | 36,83 / 35,90 | **≈ −$205** |
| **Σ** | | | | | **≈ −$182** |

📌 A **YPF TRAIL_SL** az első trailing-stop exit — érdemes megnézni, hogy a trail-szint a
**tervezett** vagy a **valós** belépőhöz kötött-e (a §11.20 mintájára).
📌 Az **RCI** a **09-09-i „olcsóbb visszalépés"** (−0,05%) — ha ma zár, az a **harmadik**
teljes visszalépési ciklus lesz.
- **Fókuszlista**: (1) **D7-sor**; (2) a két exit; (3) a YPF trail-geometriája;
  (4) **a kapuig 4 kereskedési nap** — a **§5.1/§5.2 döntés + új pin** még nyitott.

## 9. Freeze-sor
🔓 Freeze feloldva 08-17 — **D6: a production konfiguráció FAGYVA 2026-09-22-ig**; **D7: a breach
nem indok paraméter-változtatásra.** G1/G3–G7 élnek. Ma **nem történt** production-kód változás.

## 10. A nap egy mondatban
Két stop-jellegű exit **−$803,37**-tal (a swing-éra 2. legrosszabb napja) új mélypontra vitte a
kumulatívat (**−$3 910,71**), és a **`cum_30d` −4,26%-ra romlott — negyedik napja BREACH-ben**;
a gördülési tábla szerint **a feltétel a kapu napján (09-22) is fennáll majd**, ahogy a D7
előre jelezte. A nap mellékterméke két lezárult visszalépési ciklus — **mindkettő negatív**,
köztük az „olcsóbban" visszavett **ELVN**, amelynek második ciklusa **kétszer akkora veszteséget**
hozott, mint az első.
