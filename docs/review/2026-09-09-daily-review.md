# IFDS Daily Review — 2026-09-09 (szerda, Day 79/63)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ Az IBKR MCP connector ebben a sessionben nem érhető el — bróker-kereszt-ellenőrzés **kimaradt**.
> Helyette: Mini `reconcile_state` **silent OK** (`state ≡ IBKR`), kanonikus `pending_exits`,
> záró markok **Polygon**-ból.

## 1. Fejléc
- **Realized net: −$668,36** (gross −$666,14, komm. $2,22) — **2 exit, mindkettő nagy veszteség**.
  🔴 **A swing-éra 3. legrosszabb realizált napja** (08-21 −$794,39 és 05-27 −$695,79 után).
- **Cumulative: −$2 337,92 (−2,34%)** — **új mélypont** (a korábbi 09-01, −$2 277,01).
- **Net Liq: $97 300,69** — napi Δ **−$406,54**.
- **Excess: −0,20%** (portfolio −0,67% vs SPY −0,46%). ⚠️ **MTM: +0,04%** →
  **ELLENTÉTES ELŐJEL** (16. eset), exit mellett.
- **VIX 16,43 (+4,52%)**, SPY **−0,46%** — risk-off, a VIX két nap alatt 14,38 → 16,43.
- **Nyitott pozíciók: 6**.

## 2. Exits (2)
| Idő (UTC) | Ticker | Kanonikus típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 13:30:06 | **MANH** | **MENTAL_SL** | 24 | 220,09 → **205,00** | **−$362,11** (−6,86%) | ≈ −$291 | −$71 |
| 19:59:42 | **IMVT** | TIME_STOP | 111 | 41,50 → **38,74** | **−$306,25** (−6,65%) | ≈ −$213 | −$93 |
| **Σ** | | | | | **−$668,36** | ≈ −$504 | **−$164** |

⚠️ **Mindkét tétel tovább esett** a keddi zárómark alatt (MANH 207,92 → 205,00; IMVT 39,57 → 38,74),
így a becslés **mindkét irányban ugyanabba** tévedett. A hiba iránya konzisztens a
risk-off tapével (VIX +4,52%).

📌 A **MANH a 6. MENTAL_SL** az érában. A teljes minta MENTAL_SL-átlaga **−$333,73** (n=5,
kétheti riport §6) — a mai **−$362,11** ebbe a tartományba esik. **Leíró (G3).**

## 3. 🔴 KORREKCIÓ a §11.17 diagnózishoz — az `exit_type` az ABLAK ALAPÉRTELMEZETT címkéjét adja
2026-08-25-én ezt rögzítettem (04-risks §11.17): *„amikor a fill a várt időablakba esik, a mező
HELYES."* **A mai nap ezt cáfolja.**

| Forrás | MANH |
|---|---|
| **Kanonikus** (`pending_exits`) | **MENTAL_SL** |
| `daily_metrics::exits` blokk | `sl: 1` ✓ **helyes** |
| **`daily_metrics::trades.details.exit_type`** | **„TP1"** ❌ |
| Fill | **13:30:06Z — a NORMÁL 15:30-as ablak** |

**A pontosított mechanizmus:** az osztályozó **azt a címkét adja, ami az adott időablak
ALAPÉRTELMEZETT exit-típusa** — 15:30 → „TP1", 21:40 → „TIME_STOP_MOC", ablakon kívül → „MOC".
Ezért **akkor téved, ha a tényleges exit-típus eltér az ablak alapértelmezésétől**:
- **MENTAL_SL a 15:30-as ablakban → „TP1"** (ma)
- TP1 és MENTAL_SL az ablakokon kívül → „MOC" (08-21, outage)

A 08-25-i bizonyíték (PSO/IMAX TP1 → „TP1") **véletlenül volt konzisztens**: azok valóban TP1-ek
voltak a 15:30-as ablakban. **A §11.17 állítása túl megengedő volt — pontosítva.**

⚠️ **Előrejelezhető következmény a W37 heti riportra**: a heti TP1-metrika **túl fog számolni** —
a MANH **MENTAL_SL-jét TP1-találatnak veszi −$362,11-gyel**, ami a „TP1 avg profit" sort
érdemben rontja. **A pénteki heti zárásban ezt korrigálni kell** a kanonikus `pending_exits`
alapján.
✅ **A kaput nem érinti** (invariáns #2: a betöltő a `pending_exits`-ből olvas).
📌 **Gyakorlati szabály innentől**: a review a `daily_metrics::exits` blokkot és a
`pending_exits`-et használja, a `trades.details.exit_type`-ot **soha**.

## 4. Entries (2)
| Ticker | Qty | Planned→Fill | Slippage | Szektor |
|---|---|---|---|---|
| **RCI** | 220 | 36,87 → **36,83** | **−0,11%** (kedvező) | Comm. Services |
| **YPF** | 102 | 53,09 → **54,18** | **+2,05%** (adverz) | Energy (új) |

📌 **RCI-visszalépés — és OLCSÓBBAN.** Az RCI-t **tegnap** TIME_STOP-on zártuk **36,85**-en
(−$4,02), ma **36,83**-on visszavettük — **−0,05%-kal olcsóbban**. Ez a **második olcsóbb**
visszalépés (08-28 IMAX −0,29% után). **Sorozat n=8, ebből 6 drágább / 2 olcsóbb.**
⚠️ **A `planned` ár (36,87) ismét gyakorlatilag az előző exit-ár** — a DLB/FBP mintázat harmadszor.

📌 **A YPF +2,05% a CC-éra 2.** és a **teljes éra 3.** legnagyobb adverz fillje
(rekord: FBIN +2,44%, JAZZ +2,25%).

A top-3 jelölt **teljesen Financial Services** (FBP 90,7 | CRBG 90,1 | EQH 87,4); 73 ticker a küszöb felett.

## 5. Nyitott pozíciók (6) — 09-09 záró mark
| Ticker | Szektor | Bázis | Záró | Unrealized |
|---|---|---|---|---|
| YPF | Energy | 54,18 | 54,61 | **+$43,86** |
| RCI | Comm. Services | 36,83 | 36,44 | −$85,80 |
| EQH | Fin. Services | 53,12 | 52,09 | −$139,72 |
| FBP | Fin. Services | 28,72 | 27,78 | −$311,36 |
| NWS | Comm. Services | 34,45 | 33,08 | −$313,10 |
| INTA | Technology | 42,90 | 38,64 | **−$434,50** |
| **Σ** | | | | **−$1 240,62** |

A könyv **−$1 425,79 → −$1 240,62** (+$185,17) — de a javulás **átsorolás**: a két legrosszabb
tétel (IMVT, MANH) **realizálódott**. **1/6 pozitív.** Az **INTA** a legrosszabb (−$434,50,
−9,9% a bázistól) — és **ma 15:30-kor MENTAL_SL-en zárhat** (§9).
Kitettség **42,41%**, a legnagyobb szektor Financial Services **16,78%**.

## 6. Ops-checklist
- ✓ **Teljes cron-lánc lefutott**: 14:30 Phase 4-6, 15:30 eod_flags (MANH MENTAL_SL),
  15:31 submit (RCI, YPF), 21:40 time_stop (IMVT MOC), 22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- ✓ **STOP-triggerek** (D4: a `mean` az irányadó):
  `excess_10d_mean` **−0,00%** ✓ | `excess_15d_mean` **−0,07%** ✓ | `excess_10d_sum` −0,03% ✓
  ⚠️ `excess_15d_sum` **−1,03%** — **hajszálnyival** a −1,0% alatt, technikailag BREACH.
  **D4: a `sum` megfigyelés, nem trigger.**
- 📌 **`cum_30d` −1,25% → −1,88%** (küszöbig **1,12 pp**) — a mai −$668 visszahúzta, de
  **bőven a 09-01-i 0,23 pp-es szorítás felett**.

## 7. Anomáliák (új/változott/lezárt)
- **🔴 §11.17 KORREKCIÓ** (§3) — az `exit_type` az **ablak alapértelmezett** címkéjét adja,
  nem a tényleges exit-típust. A 08-25-i „normál ablakban helyes" állítás **túl megengedő volt**.
  **W37-hatás: a heti TP1-metrika túlszámol** — a pénteki zárásban korrigálandó.
- **📌 Az RCI-visszalépés a saját exit-árára tervezve, olcsóbban** (§4) — a `planned` = előző
  exit-ár mintázat **harmadik** dokumentált esete (DLB 08-19, FBP 09-08, **RCI 09-09**).
  ⚠️ Most **olcsóbban** kaptuk meg — a mechanizmus tehát **kétirányú**, ahogy a §5.2-nél is
  rögzítettük az outage-késésekre. **D6 SIM-input.**
- **📌 16. ellentétes-előjelű nap** (realized −0,20% vs MTM +0,04%) — a rés kicsi (0,24 pp),
  de az irány ismét szétvált.
- **✅ VÁLTOZATLAN**: `swing_state.exits_today` félrenevezés (ma `{MENTAL_SL:1}` ≡ a **mai** INTA flag),
  `commission_total` csak exit-láb, `entry_price=planned`, `reconcile` csak ticker-halmaz,
  **szektor-cap monitorozási rés (§11.18)**, **a TP1 utáni max_hold-túlfutás (09-04 §7, nyitott)**,
  **FileVault**, **`docs/analysis/` sync-rés**, **§5.1/§5.2 döntések**.

## 8. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **TP1-ciklusok (teljesen lezárt)** — n=6, mind pozitív, Σ **+$850,84**. Ma nem bővült.
- **MENTAL_SL** — **n=6** (+MANH −$362,11); a teljes minta átlaga −$333,73 volt n=5-nél.
- **Pozitív realizált nap** — 27/71 (ma nem).
- **Visszalépés exit után** — **n=8**, ebből **6 drágább / 2 olcsóbb** (ma RCI −0,05%).
  **`planned` = előző exit-ár: n=3** (DLB, FBP, RCI).
- **Next-day MKT fill slippage** — CC-éra **n=45** (+RCI −0,11%, +YPF **+2,05%**):
  **32 adverz / 13 kedvező** (71,1%). Teljes éra: n=71, 48 adverz (67,6%).
- **Szektor-koncentráció** — Financial Services 16,78%, a captól messze.
- **Kitettség** — 42,41%.
- **Rally/risk-off aszimmetria** — eső nap, realized szerint **−0,20% lemaradás** (ritka: eső napon
  is lemaradás, mert a realizált nagyobbat esett az indexnél).
  Sorozat: 13 rally-lemaradás vs 14 eső-napi felülteljesítés (ma egyik sem).
- **TP-hit / pozitív-exit**: **0/2**. **Várt-vs-tény**: **−$164**, mindkét tétel ugyanabba az irányba.

## 9. Ma (csütörtök, 09-10) — várt + feltevés *(nagyságrend, nem előrejelzés)*
**Egy exit**:

| Idő | Ticker | Típus | Qty | Bázis / 09-09 záró | `várt` |
|---|---|---|---|---|---|
| 15:30 | **INTA** | **MENTAL_SL** | 102 | 42,90 / 38,64 | **≈ −$435** |

📌 Ez lenne a **7. MENTAL_SL** és **két egymást követő napon a második** (MANH tegnap).
Az INTA a belépés óta **−9,9%**-ot esett (42,89 → 38,64, 5 kereskedési nap).
Ha teljesül: cumulative −$2 337,92 → **~−$2 773**. A könyv **6 → 5 tételre** csökken.

⚠️ **A becslés az elmúlt két napon ugyanabba az irányba tévedett** ($71 és $93, mindkettő
tovább-esés) — risk-off tapén a mark-alapú extrapoláció **rendszeresen alulbecsli a veszteséget**.

- **Fókuszlista**: (1) az INTA MENTAL_SL; (2) a **`cum_30d`** (−1,88%, visszahúzódott);
  (3) a **−$1 240,62-es könyv** (1/6 pozitív); (4) a VIX (16,43, két nap alatt +14%).

## 10. Freeze-sor
🔓 A freeze 08-17-én feloldódott — **de a D6 szerint a production konfiguráció FAGYVA marad
2026-09-22-ig**. A **G1/G3–G7 guardrailek élnek**. Ma **nem történt** production-kód változás.
**A kapuig 9 kereskedési nap.**

## 11. A nap egy mondatban
Két exit **−$668,36**-tal (a swing-éra 3. legrosszabb napja, új kumulatív mélypont −$2 337,92),
mindkét tétel a keddi mark alatt zárt egy erősödő risk-off tapén — és a nap **cáfolta a
08-25-én rögzített `exit_type`-diagnózisom egy részét**: a MANH **MENTAL_SL**-jét a rendszer a
**normál 15:30-as ablakban „TP1"-nek** címkézte, mert az osztályozó **az ablak alapértelmezett
címkéjét** adja, nem a tényleges típust — ami a **pénteki heti TP1-metrikát is torzítani fogja**,
ha nem korrigálom.
