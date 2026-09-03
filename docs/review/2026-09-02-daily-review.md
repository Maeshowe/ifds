# IFDS Daily Review — 2026-09-02 (szerda, Day 75/63)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ✅ **Az IBKR MCP connector visszatért** — a bróker-oldali kereszt-ellenőrzés **lefutott**
> (a 09-01-i tételeket is visszamenőleg megerősítette).

## 1. Fejléc
- **Realized net: +$34,60** (gross +$38,90, komm. $4,30) — **1 exit**.
  🟢 **A harmadik pozitív realizált nap** (08-27, 08-31 után) — az érában **25/67**.
- **Cumulative: −$2 242,41 (−2,24%)**.
- **Net Liq: $98 488,82** — napi Δ **+$643,95**, a legnagyobb egynapos emelkedés hetek óta.
- **Excess: −0,40%** (portfolio +0,04% vs SPY +0,44%). ⚠️ **MTM: +0,22%** →
  **ELLENTÉTES ELŐJEL** (14. eset), **exit mellett** (§6).
- **VIX 15,27 (−6,55%)**, SPY **+0,44%** — risk-on visszapattanás a keddi sokk után.
- **Nyitott pozíciók: 8** — **bróker-verifikálva** (`get_account_positions` ≡ `held_tickers`) ✓

## 2. 🟢 A `cum_30d` visszahúzódott — a tegnap leírt mechanika pontosan úgy működött

| | tegnap (09-01) | **ma (09-02)** |
|---|---|---|
| `cum_30d` | **−2,77%** | **−2,30%** |
| Távolság a −3,0%-tól | 0,23 pp ($231,65) | **0,70 pp ($704,80)** |
| Ablak | 07-20 → 09-01 | 07-21 → 09-02 |

A tegnapi review §2-ben rögzítettem: *„holnap a 07-20-i nap gördül ki, ami −$438,55 volt… a
küszöb akkor sérülne, ha X < −$670,20."* A mai realizált **+$34,60** volt → **nem sérült**,
és a mutató **0,47 pp-t javult**. **A leírt aritmetika teljesült.**

⚠️ **De a következő gördülés kedvezőtlen**: holnap a **07-21-i nap gördül ki, ami +$54,83**
volt — vagyis egy **pozitív** nap távozik az ablakból. A mutató **továbbra is a legfontosabb
figyelendő tétel**; a távolság riportálható, a kimenetel előrejelzése nem (§3).

## 3. Exits (1)
| Idő (UTC) | Ticker | Típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 19:59:42 | **NWBI** | TIME_STOP | 780 | 15,40 → **15,44** | **+$34,60** (+0,29%) | ≈ **−$191** | **+$226** |

**Bróker-verifikáció**: NWBI SELL 780 @ 15,44 MOC, `realized_pnl` **+34,59517**, komm. 4,30253 —
a `daily_metrics`-szel **pennyre** egyezik ✓

⚠️ **Két egymást követő nap, két $200+-os becslési tévedés, ellentétes irányban**:
tegnap **RGEN −$282** (a papír egy ülés alatt −6,07%), ma **NWBI +$226** (a papír **+2,0%**-ot
emelkedett a 15,14-es keddi záróról, miközben az SPY +0,44%-ot). A „tegnapi záró ≈ mai záró"
feltevés **egyedi papír-mozgásra vak** — ezt a §9 „várt" oszlopnál következetesen jelzem.

📌 **Visszamenőleges megerősítés**: a bróker a **09-01-i** tételeket is igazolta —
MD (két láb: −12,97 + −16,62 = **−29,59**), ELVN **−197,89**, RGEN **−274,59**. Mind egyezik.

## 4. Entries (2)
| Ticker | Qty | Planned→Fill | Slippage | Szektor |
|---|---|---|---|---|
| **INTA** | 102 | 42,22 → **42,89** | **+1,59%** (adverz) | Technology |
| NWS | 228 | 34,23 → **34,4482** | +0,64% (adverz) | Comm. Services |

Qty-súlyozott átlag **+0,93%**. Az **INTA +1,59% a CC-éra 3.** és a **teljes éra 4.** legnagyobb
adverz fillje (rekord: FBIN +2,44%). **59 ticker** a küszöb felett.

## 5. 🟢 A szektor-cap szorítása FELOLDÓDOTT — és a mechanizmus tiszta
Tegnap rögzítettem, hogy a Phase 6 **`sector limit: 3`**-mal kizárt jelölteket, és **0 belépő** lett.
Ma **2 belépő** volt, és a `sector_cap_proximity` flag **eltűnt** a `review_data`-ból.

**Az ok mechanikus és követhető**: az **NWBI kilépésével** ($11 988,60 notional) a
**Financial Services 29,27% → 17,28%**-ra esett, felszabadítva a fejteret a 30%-os cap alatt.

| Szektor | 09-01 | **09-02** |
|---|---|---|
| Financial Services | **29,27%** | **17,28%** |
| Communication Services | 14,06% | **21,86%** (NWS) |
| Technology | — | 4,31% (INTA) |
| Healthcare | 4,57% | 4,57% |
| Energy | 1,51% | 1,51% |

📌 A korlát tehát **nem strukturális, hanem állapotfüggő**: egyetlen nagy Financial Services
tétel kilépése feloldotta. **Leíró (G3)** — de a **D6 SIM-napirend** szempontjából érdekes,
hogy a cap **egy napra ténylegesen elzárta** a belépést.

## 6. Nyitott pozíciók (8) — 09-02 záró mark (IBKR)
| Ticker | Szektor | Bázis | Záró | Unrealized |
|---|---|---|---|---|
| FBP | Fin. Services | 27,91 | 28,42 | **+$195,18** |
| CRBG | Fin. Services | 32,93 | 33,54 | **+$124,84** |
| AMR (TP1 után) | Energy | 219,08 | 233,29 | **+$99,49** |
| NWS | Comm. Services | 34,45 | 34,41 | −$9,86 |
| RCI | Comm. Services | 36,88 | 36,65 | −$59,40 |
| IMAX | Comm. Services | 52,49 | 51,68 | −$67,40 |
| INTA | Technology | 42,90 | 41,49 | −$143,80 |
| IMVT | Healthcare | 41,49 | 39,49 | **−$221,89** |
| **Σ** | | | | **−$82,83** |

🟢 **A könyv −$670,38 → −$82,83** (**+$587,55**). Ebből **+$550,03 a hat továbbvitt tételé**
(−$479,20 → +$70,83) — **erős, széles visszapattanás**; a két új belépő (−$153,66) rontott rajta.
**3/8 pozitív.** A kitettség 49,54%.

## 7. Ops-checklist
- ✓ **Teljes cron-lánc lefutott**: 14:30 Phase 4-6, 15:31 submit (INTA, NWS), 21:40 time_stop
  (NWBI MOC), 22:00–22:45 eod-lánc. `reconcile_silent_ok` — **és ma bróker-oldalról is igazolva**.
- 🟢 **A `sector_cap_proximity` flag ELTŰNT** (§5).
- ✓ **STOP-triggerek** (D4: a `mean` az irányadó):
  `excess_10d_mean` **−0,10%** ✓ | `excess_15d_mean` **−0,10%** ✓ | `excess_10d_sum` −0,99% ✓
  (**hajszálnyira** a küszöb felett) | **`cum_30d` −2,30%** ✓ (§2)
  ⚠️ `excess_15d_sum` −1,47% BREACH — **D4: megfigyelés, nem trigger**.

## 8. Anomáliák (új/változott/lezárt)
- **🟢 A `cum_30d`-szorítás oldódott** (§2) — de a következő ablak-gördülés **kedvezőtlen**
  (+$54,83 távozik). **Marad a napi első szám.**
- **🟢 A szektor-cap-blokk feloldódott** (§5) — állapotfüggő, nem strukturális korlát.
- **📌 14. ELLENTÉTES-ELŐJELŰ NAP** (realized −0,40% vs MTM +0,22%, rés 0,62 pp) — **exit mellett**.
  A 14-ből **11-en volt exit**. Ismét a 08-19-i korrekciót erősíti: a szétválás oka az, hogy a
  realized-olvasat **nem látja a nyitott könyvet** — ma a könyv **+$588**-at javult, a realizált
  +$34,60 volt.
- **📌 A becslési módszer korlátja két napon át, ellentétes irányban** (RGEN −$282, NWBI +$226) — §3.
- **✅ VÁLTOZATLAN**: `exit_type` ma helyes (normál ablak, §11.17), `swing_state.exits_today`
  félrenevezés (ma `{TIME_STOP:1}` ≡ a **mai** AMR flag), `commission_total` csak exit-láb,
  `entry_price=planned`, `reconcile` csak ticker-halmaz, **FileVault**,
  **`docs/analysis/` sync-rés**, **§5.1/§5.2 döntések**.

## 9. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **TP1-sorozat** — n=4, mind pozitív; 3 ciklus lezárt (Σ +$453,35). Ma nem bővült.
- **Pozitív realizált nap** — **25/67**; ma a harmadik 08-11 óta.
- **Next-day MKT fill slippage** — CC-éra **n=40** (+INTA +1,59%, +NWS +0,64%): **30 adverz /
  10 kedvező (75,0%)**. Teljes éra: n=66, 46 adverz (69,7%).
- **Szektor-koncentráció** — Financial Services **29,27% → 17,28%**; a legnagyobb most
  Communication Services **21,86%**.
- **Kitettség** — 49,54% (a 63,48%-os rekordról).
- **Rally/risk-off aszimmetria** — emelkedő nap, realized szerint −0,40% lemaradás.
  Sorozat: **12** rally-lemaradás vs 12 eső-napi felülteljesítés — **ismét kiegyenlítve**.
- **Ellentétes-előjelű nap** — **14/53**.
- **Outage-késleltetett exit** — n=4 (+ a 08-21-i EQH/DLB **döntés alatt**, §5.2).
- **TP-hit / pozitív-exit**: **1/1**. **Várt-vs-tény**: **+$226** (§3).

## 10. Ma (csütörtök, 09-03) — várt + feltevés
**Egy TIME_STOP 21:40 MOC**:

| Ticker | Qty | Bázis / záró | `várt` |
|---|---|---|---|
| **AMR** (TP1-maradék) | 7 | 219,08 / 233,29 | **≈ +$99** |

📌 Ha teljesül, az **AMR lenne a negyedik teljesen lezárt TP1-ciklus**: TP1 +$64,57 (08-31)
+ ≈ +$99 = **≈ +$164** — és **mind a négy ciklus pozitív** lenne.
⚠️ **Nagyságrend, nem előrejelzés** — két napja $282, tegnap $226 volt a tévedés.

- **Fókuszlista**: (1) a **`cum_30d`** (−2,30%; a gördülés ma kedvezőtlen); (2) az AMR-ciklus zárása;
  (3) az **IMVT** (−$221,89, a könyv legrosszabb tétele); (4) a −$82,83-as könyv.

## 11. Freeze-sor
🔓 A freeze 08-17-én feloldódott — **de a D6 szerint a production konfiguráció FAGYVA marad
2026-09-22-ig**. A **G1/G3–G7 guardrailek élnek**. Ma **nem történt** production-kód változás.
**A kapuig 13 kereskedési nap.**

## 12. A nap egy mondatban
A **`cum_30d` a tegnap leírt aritmetika szerint pontosan visszahúzódott** (−2,77% → −2,30%,
a küszöbtől már 0,70 pp), a **szektor-cap szorítása egyetlen kilépéssel feloldódott**
(Financial Services 29,27% → 17,28%, és ma **2 belépő** ment át) — miközben a nap harmadik
pozitív realizált napja volt (**+$34,60**, egy $226-tal a becslésem fölött záró NWBI-vel) és a
**könyv $588-at javult**, döntően a hat továbbvitt tétel széles visszapattanásából.
