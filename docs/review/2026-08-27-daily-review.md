# IFDS Daily Review — 2026-08-27 (csütörtök, Day 71/63)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ **Késve készült** (2026-08-28) — a mai (08-28) review + a **W35 heti zárás** még hátra van.

## 1. Fejléc
- **Realized net: +$20,05** (gross +$21,12, komm. $1,07) — **1 exit**.
  🟢 **AZ ELSŐ POZITÍV REALIZÁLT NAP 2026-08-11 ÓTA — 11 ülés után.**
- **Cumulative: −$1 830,45 (−1,83%)** — a mélypontról **$20,05-tal javult**.
- **Net Liq: $98 937,56** — napi Δ **−$146,54**. ⚠️ A NetLiq **esett** egy pozitív realizált napon:
  a nyitott könyv −$184-et vesztett (§4).
- **Excess: −0,63%** (portfolio +0,02% vs SPY **+0,66%**). **MTM: −0,81%** — azonos előjel, 0,18 pp rés.
- **VIX 14,45 (−5,00%)**, SPY **+0,66%** — határozott risk-on nap; a VIX a swing-éra mélypontja közelében.
- **Nyitott pozíciók: 9** (`reconcile_silent_ok` ✓).

## 2. Exits (1)
| Idő (UTC) | Ticker | Típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 19:59:41 | **DLB** (TP1-maradék) | TIME_STOP | 47 | 61,98 → **62,41** | **+$20,05** (+0,69%) | ≈ +$140 | **−$120** |

🟢 **A ritka POZITÍV max_hold-exit — most tényleg.** A friss exit-sorozatban ez az első
nyereséges TIME_STOP (előtte: FBIN −$415, SN −$162, ZBRA −$194, BANC −$315, IMAX −$7).

⚠️ **De a becslésem $120-szal tévedett** — a DLB a szerdai 64,95-ös záróról **62,41-re esett**
(−3,9%) a csütörtöki ülésen. Ez az **ötödik egymást követő** érdemi tévedés a mark-alapú
egy-napos extrapolációval; a §8 „várt" oszlop **nagyságrend, nem előrejelzés**.

### ✅ A DLB self-reentry-ciklus TELJES MÉRLEGE (lezárva)
| Esemény | Dátum | Összeg |
|---|---|---|
| Kiléptetés max_hold-on @ 61,13, majd visszavétel @ 61,95 — **súrlódás** | 08-18→19 | **−$79,22** |
| **TP1** (47 db @ 65,27) | 08-21 | **+$154,47** |
| **TIME_STOP** (47 db @ 62,41) | 08-27 | **+$20,05** |
| **Nettó** | | **+$95,30** |

📌 A self-reentry **összességében nyereséges lett** — de a **súrlódás a nyereség 45%-át elvitte**.
Ez a `max_hold` ↔ belépő-jel ellentmondás **első teljesen lezárt, végig mért esete**, és a
**D6 SIM-napirend 1. tételének** (max_hold-érzékenység) legjobb egyedi inputja. **Leíró (G3).**

## 3. Entries (2)
| Ticker | Qty | Planned→Fill | Slippage | Szektor |
|---|---|---|---|---|
| FBP | 379 | 28,12 → **27,90** | **−0,78%** (kedvező) | Financial Services |
| RCI | 264 | 36,93 → **36,87** | **−0,16%** (kedvező) | Comm. Services |

🟢 **Mindkét fill kedvező** — qty-súlyozott átlag **−0,53%**, a CC-éra **második** kedvező napi átlaga
(az első 08-20 volt, −0,20%). **88 ticker** a küszöb felett (87-ről).

## 4. Nyitott pozíciók (9) — 08-27 záró mark
| Ticker | Szektor | Bázis | Záró | Unrealized |
|---|---|---|---|---|
| PSO (TP1 után) | Comm. Services | 16,08 | 16,66 | **+$155,02** |
| AMR | Energy | 219,00 | 227,38 | **+$108,94** |
| MD | Healthcare | 26,62 | 26,80 | +$32,94 |
| RGEN | Healthcare | 180,72 | 182,03 | +$32,75 |
| ELVN | Healthcare | 60,35 | 60,50 | +$11,70 |
| NWBI | Fin. Services | 15,39 | 15,33 | −$42,98 |
| FBP | Fin. Services | 27,90 | 27,71 | −$72,01 |
| RCI | Comm. Services | 36,87 | 36,44 | −$113,52 |
| FMS | Healthcare | 23,69 | 23,27 | **−$119,52** |
| **Σ** | | | | **−$6,67** |

A könyv **+$177,74 → −$6,67** (−$184,41) — **gyakorlatilag nullán**, a pozitív sorozat megszakadt.
**5/9 pozitív.** Az **AMR** a tegnapi +1,56%-os rossz fill ellenére **+$108,94**-en áll.

⚠️ **Kitettség-rekord: `total_notional` 42,85% → 60,39%** — a swing-éra legmagasabb értéke
(9 tétel, `max_concurrent` 12). Limit-sértés **nincs**: a legnagyobb szektor **Financial Services
22,65%** a 30%-os cap ellenében. **Megfigyelés-tárgy.**

## 5. Ops-checklist
- ✓ **Teljes cron-lánc lefutott**: 14:30 Phase 4-6, 15:31 submit (FBP, RCI), 21:40 time_stop (DLB MOC),
  22:00–22:45 eod-lánc. `reconcile_silent_ok`, `pending_exits` feldolgozva.
- ✓ **STOP-triggerek** (D4: a `mean` az irányadó):
  `excess_10d_mean` **−0,07%** ✓ | `excess_15d_mean` **−0,12%** ✓ | `cum_30d` **−2,06%** ✓
- 🟢 **Az `excess_10d_sum` LEJÖTT a BREACH-ről** (−0,74%). ⚠️ Ugyanakkor az `excess_15d_sum`
  **visszament** BREACH-re (−0,87% → **−1,79%**). A kettő **felváltva** billeg, ahogy az ablakok
  gördülnek — **D4: mindkettő megfigyelés, nem trigger.**
- 📌 **`cum_30d` −2,08% → −2,06%** — a küszöbtől **0,94 pp**. Három napja lényegében mozdulatlan
  (−2,07 / −2,08 / −2,06). **Továbbra is az egyetlen valódi trigger-közelség.**

## 6. Anomáliák (új/változott/lezárt)
- **📌 NEGYEDIK NAPJA: a top-3 jelölt teljesen Healthcare, a belépő mégsem az.**
  08-27: top-3 **MD 100,8 | ELVN 100,5 | RGEN 94,0** → belépők **FBP** (Fin. Services) és
  **RCI** (Comm. Services). A Healthcare-kitettség **négy napja bitre azonos: $20 934,58**
  — vagyis **egyetlen Healthcare-tétel sem nyílt és nem zárt** azóta.
  A cap 30%, a Healthcare 20,93% → **nem a cap köti**. A mintázat **stabil és ismétlődő**.
  ⚠️ **Leíró (G3)** — a mechanizmust továbbra sem azonosítottam. **Kapu után** (D6: prod fagyva)
  érdemes a Phase 6 szektor-logikát megnézni; addig **megfigyelés-sorozat**.
- **📌 Kitettség-rekord (60,39%)** — §4. Nem limit-sértés, de a swing-éra maximuma, és **két nap
  alatt 42,85% → 60,39%** (4 új belépő). Együtt olvasandó azzal, hogy a könyv épp nullára esett.
- **✅ VÁLTOZATLAN**: `exit_type` ma helyes (`TIME_STOP_MOC`, normál ablak — konzisztens §11.17-tel),
  `swing_state.exits_today` félrenevezés (ma `{TIME_STOP:2}` ≡ a **mai** FMS/PSO flagek),
  `commission_total` csak exit-láb, `entry_price=planned`, `reconcile` csak ticker-halmaz,
  **FileVault**, **`docs/analysis/` sync-rés**, **§5.1/§5.2 döntések**.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **🆕 Pozitív realizált nap** — **23/63 az érában**; ma az **első 08-11 óta (11 ülés)**.
- **Self-reentry** — n=3. A **DLB ciklusa LEZÁRVA: +$95,30 nettó**, a súrlódás a nyereség 45%-a (§2).
- **TP1-sorozat** — n=3, mind pozitív; két ciklus már teljesen lezárt (IMAX +$69,48, DLB +$95,30).
- **Next-day MKT fill slippage** — CC-éra **n=35** (+FBP −0,78%, +RCI −0,16%, **mindkettő kedvező**):
  **25 adverz / 10 kedvező** (71,4% adverz). Teljes éra: n=61, 41 adverz (67,2%).
- **Szektor-koncentráció (Healthcare)** — **20,93%, negyedik napja bitre változatlan**.
- **Kitettség** — **60,39%, éra-rekord** (42,85% → 60,39% két nap alatt).
- **„Rés utáni visszalépés"** — lezárt sorozat, n=3, mind negatív.
- **Outage-késleltetett exit** — n=4 (+ a 08-21-i EQH/DLB **döntés alatt**, §5.2).
- **Rally/risk-off aszimmetria** — erős emelkedő nap (SPY +0,66%), realized szerint **−0,63% lemaradás**.
  Sorozat: **11** rally-lemaradás vs 9 eső-napi felülteljesítés. **A rally-lemaradás sorozat vezet.**
- **TP-hit / pozitív-exit**: **1/1**. **Várt-vs-tény**: **−$120** (§2) — 5. egymást követő érdemi tévedés.

## 8. Ma (péntek, 08-28) — várt + feltevés
**Két TIME_STOP 21:40 MOC** (feltevés: pénteki close ≈ csütörtöki záró):

| Ticker | Qty | Bázis / záró | `várt` |
|---|---|---|---|
| **FMS** | 288 | 23,69 / 23,27 | **≈ −$120** |
| **PSO** (TP1-maradék) | 265 | 16,08 / 16,66 | **≈ +$155** |
| **Σ** | | | **≈ +$35** |

⚠️ **A becslés az elmúlt öt alkalomból ötször tévedett $50–150-nel** — ez **nagyságrend**.
Ha teljesül: cumulative −$1 830,45 → **~−$1 795**. A könyv **9 → 7 tételre** csökken.

📌 A **PSO** lenne a **harmadik teljesen lezárt TP1-ciklus** (TP1 +$121,76 + ≈ +$155 ≈ **+$277**).
- **Fókuszlista**: (1) a két TIME_STOP; (2) a **W35 heti zárás**; (3) a **`cum_30d`** (−2,06%);
  (4) a Healthcare-mintázat (5. nap?); (5) a **60,39%-os kitettség** alakulása.

## 9. Freeze-sor
🔓 A freeze 08-17-én feloldódott — **de a D6 szerint a production konfiguráció FAGYVA marad
2026-09-22-ig**. A **G1/G3–G7 guardrailek élnek**. Ma **nem történt** production-kód változás.

## 10. A nap egy mondatban
**Az első pozitív realizált nap 11 ülés után** (+$20,05, a friss sorozat első nyereséges
max_hold-exitje) — bár a becslésemtől $120-szal elmaradva —, és ezzel **lezárult a DLB
self-reentry-ciklus +$95,30-cal**, amelynek **45%-át a felesleges oda-vissza súrlódása vitte el**;
közben a kitettség **éra-rekord 60,39%-ra** ugrott, a könyv nullára esett (−$6,67), a jelölt-lista
top-3-ja pedig **negyedik napja teljesen Healthcare, a belépők negyedik napja mégsem azok**.
