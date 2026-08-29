# IFDS Daily Review — 2026-08-28 (péntek, Day 72/63) + **W35 heti zárás**

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.

## 1. Fejléc
- **Realized net: −$9,06** (gross −$5,96, komm. $3,10) — **2 exit**. Lapos realizált nap.
- **Cumulative: −$1 839,51 (−1,84%)**.
- **Net Liq: $98 434,50** — napi Δ **−$503,06**. **A legnagyobb egynapos NetLiq-esés 08-17 óta**;
  a mozgás gyakorlatilag teljes egészében a **nyitott könyvben** volt (§4).
- **Excess: +0,22%** (portfolio −0,01% vs SPY −0,23%). ⚠️ **MTM: −0,28%** →
  **ELLENTÉTES ELŐJEL** (13. eset). **Ma volt exit** — tehát ez **nem** a 0-exit-artefakt,
  hanem a §D3/M általános mechanizmusa (§6).
- **VIX 14,45 (−0,41%)**, SPY **−0,23%** — csendes, enyhén eső nap.
- **Nyitott pozíciók: 9** (`reconcile_silent_ok` ✓).

## 2. Exits (2) — mindkettő TIME_STOP MOC
| Idő (UTC) | Ticker | Típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 19:59:41 | **PSO** (TP1-maradék) | TIME_STOP | 265 | 16,08 → **16,71** | **+$166,81** (+3,91%) | ≈ +$155 | **+$12** |
| 19:59:32 | **FMS** | TIME_STOP | 288 | 23,69 → **23,08** | **−$175,87** (−2,58%) | ≈ −$120 | −$56 |
| **Σ** | | | | | **−$9,06** | ≈ +$35 | **−$44** |

📌 **A becslés végre közel járt** — a PSO-nál $12-on belül. Az öt egymást követő $50–150-es
tévedés sorozata **megszakadt** (a Σ-hiba −$44, tételenként +$12 / −$56).

### ✅ A PSO TP1-ciklus TELJES MÉRLEGE (lezárva) — a legjobb eddig
| Esemény | Dátum | Összeg |
|---|---|---|
| **TP1** (265 db @ 16,54) | 08-25 | **+$121,76** |
| **TIME_STOP** (265 db @ 16,71) | 08-28 | **+$166,81** |
| **Nettó** | | **+$288,57** |

📌 **A harmadik teljesen lezárt TP1-ciklus, és messze a legjobb**: IMAX +$69,48 |
DLB +$95,30 | **PSO +$288,57**. Mindhárom pozitív. **A TP1-ág itt nem levágta, hanem
megduplázta a nyereséget** — a maradék fél pozíció **jobban** teljesített, mint a TP1.
⚠️ **n=3 — nem általánosítható (G3)**, de a D6 SIM-napirend 3. tételének (TP1-elérés)
közvetlen inputja.

## 3. Entries (2)
| Ticker | Qty | Planned→Fill | Slippage | Szektor |
|---|---|---|---|---|
| **IMAX** | 83 | 51,94 → **52,48** | **+1,04%** (adverz) | Comm. Services |
| CRBG | 203 | 32,63 → **32,92** | +0,89% (adverz) | Financial Services |

Qty-súlyozott átlag **+0,93%** — **mindkettő adverz**, a csütörtöki kedvező nap után visszafordult.
**95 ticker** a küszöb felett (88-ról) — a jelölt-lista tovább duzzad.

📌 **IMAX-visszalépés — és ELŐSZÖR OLCSÓBBAN.** Az IMAX **08-26-án** TIME_STOP-on kiszállt
**52,63**-on, ma **52,48**-on visszavettük — **−0,29%-kal olcsóbban**. Az összes eddigi
visszalépés (JAZZ +2,8%, GTES +11,3%, EQH +9,5%, DLB +1,34%) **drágább** volt.
**Az első olcsóbb visszalépés.** *(A fill maga +1,04%-kal a tervezett ár fölött telt ki —
a két szám külön dolog: az egyik a ciklushoz, a másik a végrehajtáshoz méri.)*

## 4. Nyitott pozíciók (9) — 08-28 záró mark
| Ticker | Szektor | Bázis | Záró | Unrealized |
|---|---|---|---|---|
| AMR | Energy | 219,00 | 226,23 | **+$93,99** |
| FBP | Fin. Services | 27,90 | 28,01 | +$41,69 |
| MD | Healthcare | 26,62 | 26,61 | −$1,83 |
| NWBI | Fin. Services | 15,39 | 15,34 | −$35,18 |
| CRBG | Fin. Services | 32,92 | 32,61 | −$62,93 |
| RCI | Comm. Services | 36,87 | 36,59 | −$73,92 |
| RGEN | Healthcare | 180,72 | 176,27 | −$111,25 |
| IMAX | Comm. Services | 52,48 | 50,38 | −$174,30 |
| ELVN | Healthcare | 60,35 | 57,86 | **−$194,22** |
| **Σ** | | | | **−$517,95** |

A könyv **−$6,67 → −$517,95** (**−$511,28**) — a napi mozgás egésze. **2/9 pozitív.**
Az **ELVN** (−2,49 pont, a top-1 jelölt négy napja) és a friss **IMAX** (−$174 az első napon)
vitte a legtöbbet.

## 5. Ops-checklist
- ✓ **Teljes cron-lánc lefutott**: 14:30 Phase 4-6, 15:31 submit (IMAX, CRBG), 21:40 time_stop
  (2 MOC), 22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- 🟡 **ÚJ AUTOMATA FLAG TÜZELT** — a 1a pipeline `sector_cap_proximity` **P2**:
  *„Financial Services 29.3% > 25% (cap 30%)"*. **Ez a flag most szólalt meg először** az
  általam vitt review-időszakban — **a monitorozás működik** (§6).
- ✓ **STOP-triggerek** (D4: a `mean` az irányadó):
  `excess_10d_mean` **−0,05%** ✓ | `excess_15d_mean` **−0,08%** ✓ | `cum_30d` **−2,07%** ✓
  🟢 Az `excess_10d_sum` is **rendben** (−0,48%). ⚠️ `excess_15d_sum` **−1,24%** BREACH
  (a −1,0%-os küszöb közelében) — **D4: megfigyelés**.
- 📌 **`cum_30d` −2,07%** — **négy napja mozdulatlan** (−2,07 / −2,08 / −2,06 / −2,07),
  a küszöbtől **0,93 pp**. Továbbra is az egyetlen valódi trigger-közelség.

## 6. Anomáliák (új/változott/lezárt)
- **🟡 P2 (ÚJ, AUTOMATA) — szektor-cap közelség: Financial Services 29,27%.**
  A cap **30%**, a figyelmeztetési küszöb 25% — a rés **0,73 pp**. Összetétel: NWBI $11 988,60
  + FBP $10 657,48 + CRBG $6 623,89. **Ez az eddigi legmagasabb szektor-kitettség**
  (előző csúcs: Healthcare 20,93%). A `total_notional` **60,20%** — a keddi 42,85%-ról.
  ⚠️ **Nem limit-sértés**, de a mai belépő (CRBG) **tovább növelte** a már figyelmeztetett szektort.
  **Megfigyelés-tárgy**; ha a cap ténylegesen kötni kezd, az a Phase 6 sizing viselkedését is érinti.
- **📌 ÖTÖDIK NAPJA: a top-3 jelölt teljesen Healthcare, a belépők mégsem azok.**
  Ma: **ELVN 102,7 | MD 101,2 | RGEN 95,4** → belépők **IMAX** (Comm. Services) és
  **CRBG** (Fin. Services). ℹ️ A **négynapos „bitre azonos" Healthcare-befagyás MEGTÖRT**
  (az FMS kilépésével $20 934,58 → **$14 068,66**), de **a mintázat maga áll**: a rendszer
  öt egymást követő napon **nem** a saját top-3-ából választ. **Leíró (G3)** — a mechanizmust
  továbbra sem azonosítottam; **kapu utáni** vizsgálati tétel (D6: prod fagyva).
- **📌 13. ELLENTÉTES-ELŐJELŰ NAP** (realized +0,22% vs MTM −0,28%, rés 0,50 pp) — **exit mellett**.
  Ez ismét a 08-19-én rögzített korrekciót erősíti: a szétválás **nem** a 0-exites napokhoz
  kötött (13-ból **10-en volt exit**), hanem abból ered, hogy a realized-olvasat **nem látja a
  nyitott könyvet** — ma a könyv −$511-et vesztett, a realizált −$9,06 volt.
- **✅ VÁLTOZATLAN**: `exit_type` ma helyes (normál ablak, §11.17), `swing_state.exits_today`
  félrenevezés (ma `{TP1:1}` ≡ a **hétfői** AMR flag), `commission_total` csak exit-láb,
  `entry_price=planned`, `reconcile` csak ticker-halmaz, **FileVault**,
  **`docs/analysis/` sync-rés**, **§5.1/§5.2 döntések**.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **TP1-ciklusok (teljesen lezárt)** — **n=3, mind pozitív**: IMAX +$69,48 | DLB +$95,30 |
  **PSO +$288,57**. Σ **+$453,35**.
- **Visszalépés exit után** — **n=4**, és ma az **első OLCSÓBB** (IMAX −0,29%; korábban
  JAZZ +2,8%, GTES +11,3%, EQH +9,5%, DLB +1,34%).
- **Next-day MKT fill slippage** — CC-éra **n=37** (+IMAX +1,04%, +CRBG +0,89%, mindkettő adverz):
  **27 adverz / 10 kedvező** (73,0%). Teljes éra: n=63, 43 adverz (68,3%).
- **Szektor-koncentráció** — **Financial Services 29,27%, éra-rekord** (§6). Healthcare 14,07%.
- **Kitettség** — **60,20%**, második napja 60% felett.
- **Outage-késleltetett exit** — n=4 (+ a 08-21-i EQH/DLB **döntés alatt**, §5.2).
- **Rally/risk-off aszimmetria** — eső nap, realized szerint +0,22% felülteljesítés.
  Sorozat: 11 rally-lemaradás vs **10** eső-napi felülteljesítés.
- **TP-hit / pozitív-exit**: **1/2**. **Várt-vs-tény**: **−$44** — a sorozat legjobb pontossága
  öt hét óta.

---

# W35 heti zárás (2026-08-24 – 08-28)

## Számok
| Mérőszám | W35 | *(W34)* |
|---|---|---|
| **Net P&L** | **−$306,94** | *−$1 082,69* |
| Cumulative | **−$1 839,51 (−1,84%)** | *−$1 532,57* |
| Portfolio heti | −0,30% | *−1,07%* |
| SPY heti | **+0,48%** | *−1,37%* |
| **Excess vs SPY** | **−0,78%** | *+0,30%* |
| **Nyerő napok** | **1 / 5** | *0 / 5* |
| Nyitott pozíciók (hét) | 9 (1,8/nap) | *6 (1,2/nap)* |
| **TP1-találat** | **2 / 9 (22%), átlag +$99,04** | *0/6 — **hibás**, lásd §11.17* |
| Zero-pozíciós nap | **0/5** | *1/5* |

## A hét karaktere (tényszerű)
- **Tükörkép a W34-hez képest.** W34: **abszolút rossz** (−$1 083), **relatíve jó** (+0,30%).
  W35: **abszolút jóval jobb** (−$307, a veszteség **72%-kal kisebb**), **relatíve rosszabb**
  (−0,78%), mert az SPY **+0,48%**-ot emelkedett. **A két olvasatot külön kell olvasni.**
- **A hét eredményét a TP1-ág vitte**: a három lezárt ciklusból kettő (**PSO +$288,57**,
  DLB +$95,30) ezen a héten zárt. Nélkülük a hét lényegesen rosszabb lenne.
- **✅ A heti TP1-metrika MŰKÖDIK** (2/9, átlag **+$99,04**) — szemben a W34 hibás 0/6-ával.
  Ez **közvetlenül megerősíti a §11.17 diagnózist**: a W34-es hiba az **outage** okozta
  késett fillek következménye volt, nem a metrikáé. Normál héten a mező helyes.
- **A kitettség strukturálisan megnőtt**: 9 nyitott tétel, **60,20%** notional,
  **Financial Services 29,27%** — mindkettő éra-rekord, és 0 zero-pozíciós nap (W34: 1).
- **A könyv a hét végére −$517,95-re fordult** (hétfőn még +$242 volt) — a jövő hét nyitó terhe.

## Következő hét (2026-08-31 – 09-04)
1. **`cum_30d`** (−2,07%, négy napja mozdulatlan) — az egyetlen valódi trigger-közelség.
2. **Financial Services 29,27%** — a 30%-os cap 0,73 pp-re; figyelni, hogy a Phase 6 sizing köti-e.
3. **Tamás-döntés × 2** (a 08-21-i review §6): a **§5.1 részleges-outage** kritérium és a
   **§5.2 EQH/DLB** besorolás. Mindkettő `gate_sample.py`-t és **új pint** érinthet.
   **A kapuig (2026-09-22) 17 kereskedési nap van.**
4. **FileVault** — 3. előfordulás óta nyitva.
5. A **D6 SIM-napirend** indítása (prod fagyva; a revíziók SIM-ben).

## 9. Freeze-sor
🔓 A freeze 08-17-én feloldódott — **de a D6 szerint a production konfiguráció FAGYVA marad
2026-09-22-ig**. A **G1/G3–G7 guardrailek élnek**. Ma **nem történt** production-kód változás.

## 10. A nap egy mondatban
Lapos realizált nap (−$9,06) mögött **három érdemi esemény**: a **PSO TP1-ciklusa +$288,57-tal
lezárult** (a három lezárt ciklus mind pozitív, Σ +$453), az **IMAX-ot először vettük vissza
olcsóbban**, mint ahogy kiléptettük, és a **`sector_cap_proximity` automata flag először
tüzelt** (Financial Services **29,27%**, a cap 0,73 pp-re) — miközben a könyv −$518-ra fordult
és a NetLiq **08-17 óta a legnagyobbat esett** (−$503).
