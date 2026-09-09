# IFDS Daily Review — 2026-09-08 (kedd, Day 78/63)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ✅ **IBKR MCP kereszt-ellenőrzés lefutott** — 6 pozíció ≡ `held_tickers`, a realizált pennyre egyezik.
> ℹ️ **2026-09-07 = Labor Day, a tőzsde ZÁRVA** — a hiányzó `daily_metrics/2026-09-07.json`
> **várt viselkedés, NEM outage** (a `verify_outage_days()` NYSE-session alapon számol).
> A hétfőre tervezett három exit ezért **kedden** futott.

## 1. Fejléc
- **Realized net: +$91,34** (gross +$94,67, komm. $3,33) — **3 exit**.
  🟢 **Két pozitív realizált nap egymás után** (09-04 +$504,57, ma +$91,34); az érában **27/70**.
- **Cumulative: −$1 669,56 (−1,67%)** — **a legjobb állás 08-21 óta**.
- **Net Liq: $97 707,23** — napi Δ **−$833,31**. ⚠️ A NetLiq **nagyot esett** egy pozitív
  realizált napon: a nyitott könyv **−$931,85**-öt vesztett (§5).
- **Excess: +0,64%** (portfolio +0,09% vs SPY −0,55%). ⚠️ **MTM: −0,30%** →
  **ELLENTÉTES ELŐJEL** (15. eset), **exit mellett** (§7).
- **VIX 15,67 (+2,42%)**, SPY **−0,55%** — risk-off.
- **Nyitott pozíciók: 6** — bróker-verifikálva ✓

## 2. 🟢 A STOP-triggerek második ülése tisztán
```
STOP-triggerek: ✓ nincs breach (mind a pre-reg ablak kiértékelve)
```
`excess_10d_mean` **−0,05%** | `excess_15d_mean` **−0,02%** | `excess_10d_sum` −0,46% |
`excess_15d_sum` −0,34% | **`cum_30d` −1,25%** (küszöb −3,0%, távolság **1,75 pp**).
A 09-01-i **0,23 pp**-es szorítás óta a `cum_30d` **folyamatosan tágul**.

## 3. Exits (3) — a hétfői flagek, kedden végrehajtva
| Idő (UTC) | Ticker | Típus | Qty | Entry → Exit | Realized |
|---|---|---|---|---|---|
| 19:59:32 | **CRBG** (TP1-maradék) | TIME_STOP | 102 | 32,93 → 33,74 | **+$82,53** (+2,46%) |
| 19:59:42 | **IMAX** | TIME_STOP | 83 | 52,51 → 52,66 | **+$12,83** (+0,29%) |
| 19:59:32 | **RCI** (TP1-maradék) | TIME_STOP | 132 | 36,88 → 36,85 | **−$4,02** (−0,08%) |
| **Σ** | | | | | **+$91,34** |

**Bróker-verifikáció**: `realized_pnl` +12,833328 / +82,53361 / −4,024339 = **+91,342599** —
a `daily_metrics` nettójával **pennyre** egyezik ✓ (a 09-04-i tételek is igazolva:
FBP +227,101269, CRBG +149,903089, RCI TP1 három láb Σ +127,570542).

### ✅ Két TP1-ciklus lezárult — a sorozat n=6, mind pozitív
| Ciklus | TP1 | Maradék | **Nettó** |
|---|---|---|---|
| **RCI** | +$127,57 (09-04) | **−$4,02** (09-08) | **+$123,55** |
| **CRBG** | +$149,90 (09-04) | **+$82,53** (09-08) | **+$232,43** |

**Mind a hat teljesen lezárt TP1-ciklus pozitív**: IMAX +$69,48 | DLB +$95,30 |
PSO +$288,57 | AMR +$41,51 | **RCI +$123,55** | **CRBG +$232,43** → **Σ +$850,84**.
⚠️ **n=6, nem általánosítható (G3)** — de a D6 SIM-napirend TP1-tételének legerősebb inputja.

📌 **Az IMAX MÁSODIK ciklusa TP1 nélkül zárt**: belépő 08-28 @ 52,48 → TIME_STOP 09-08 @ 52,66
= **+$12,83**. Az első ciklusa (TP1-gyel) **+$69,48** volt. **n=1 összevetés, leíró.**

### A becslés ellenőrzése (4 napos ablakon át)
A 09-04-i zárómarkokból implikált várakozás: IMAX ≈ −$71 | RCI ≈ +$85 | CRBG ≈ +$158 →
**Σ ≈ +$172**; tény **+$91,34** (**Δ −$81**). Tételenként **+$84 / −$89 / −$75**.
⚠️ **Ez a legnehezebb eset eddig**: az extrapoláció **négy naptári napot** (Labor Day-hétvége)
hidalt át, nem egyet. A Σ-hiba mégis kisebb, mint a 09-01–09-03 sorozaté.

## 4. Entries (1) — **FBP-visszalépés**
| Ticker | Qty | Planned→Fill | Slippage | Szektor |
|---|---|---|---|---|
| **FBP** | 333 | 28,51 → **28,71** | **+0,70%** (adverz) | Financial Services |

📌 **Az FBP-t 09-04-én TIME_STOP-on zártuk 28,51-en** (+$227,10 — az éra legnagyobb pozitív
TIME_STOP-ja), **ma 28,71-en visszavettük** — **+0,70%-kal drágábban**.
⚠️ **A `planned` ár PONTOSAN a 09-04-i exit-ár (28,51)** — ugyanaz a mintázat, mint a
DLB-nél 08-19-én (planned 61,10 ≈ exit 61,13). **A rendszer a saját exit-árára tervezi a
visszalépést, és fölötte kapja meg.**
**Visszalépés-sorozat n=7**: JAZZ +2,8% | GTES +11,3% | EQH(1) +9,5% | DLB +1,34% |
IMAX −0,29% | EQH(2) +7,5% | **FBP +0,70%** — **6/7 drágábban**. **Leíró (G3).**

A top-3 jelölt ma **teljesen Financial Services** (CRBG 89,9 | **FBP 89,7** | EQH 89,4);
69 ticker a küszöb felett.

## 5. Nyitott pozíciók (6) — 09-08 záró mark (IBKR)
| Ticker | Szektor | Bázis | Záró | Unrealized |
|---|---|---|---|---|
| EQH | Fin. Services | 53,12 | 52,04 | −$146,52 |
| FBP | Fin. Services | 28,72 | 28,08 | −$211,46 |
| IMVT | Healthcare | 41,49 | 39,57 | −$213,01 |
| NWS | Comm. Services | 34,45 | 33,34 | −$253,82 |
| MANH | Technology | 220,04 | 207,92 | **−$290,92** |
| INTA | Technology | 42,90 | 39,86 | **−$310,06** |
| **Σ** | | | | **−$1 425,79** |

🔴 **A könyv −$493,94 → −$1 425,79 (−$931,85), és MIND A HAT tétel negatív.**
A romlás széles: INTA −$310, MANH −$291, NWS −$254. A friss **FBP már az első napon −$211**-en áll.
Kitettség **38,80%**, a legnagyobb szektor Financial Services **16,78%** — a captól messze.

## 6. Ops-checklist
- ✓ **Teljes cron-lánc lefutott**: 14:30 Phase 4-6, 15:31 submit (FBP), 21:40 time_stop (3 MOC),
  22:00–22:45 eod-lánc. `reconcile_silent_ok` — **és bróker-oldalról is igazolva**.
- ✓ **Minden STOP-trigger tiszta** (§2), második ülése.
- ℹ️ **09-07 Labor Day** — nincs `daily_metrics`, ez **várt** (nem §5.1 outage).

## 7. Anomáliák (új/változott/lezárt)
- **📌 15. ELLENTÉTES-ELŐJELŰ NAP** (realized **+0,64%** vs MTM **−0,30%**, rés 0,94 pp) —
  **exit mellett**. A mai a **legtisztább illusztráció** eddig: a realizált **+$91,34**, miközben
  a nyitott könyv **−$931,85**-öt vesztett és a NetLiq **−$833,31**-gyel esett. A realized-olvasat
  **„felülteljesítést" könyvelt egy olyan napon, amikor a portfólió közel $1 000-t bukott**.
  Ez pontosan a §D3/M korlát, amit a kapu-riportban idézni kell.
- **📌 Az FBP-visszalépés a saját exit-árára tervezve** (§4) — a DLB (08-19) után a **második
  dokumentált eset**, ahol a `planned` ár megegyezik az előző napi exit-árral. **A max_hold ↔
  belépő-jel ellentmondás mechanikája**, most már mintázatként. **D6 SIM-input.**
- **📌 A könyv egy nap alatt −$932** (§5) — mind a hat tétel negatív, az első ilyen 09-01 óta.
- **✅ VÁLTOZATLAN**: `exit_type` ma helyes (normál ablak, §11.17), `swing_state.exits_today`
  félrenevezés (ma `{TIME_STOP:1, MENTAL_SL:1}` ≡ a **mai** IMVT/MANH flagek), `commission_total`
  csak exit-láb, `entry_price=planned`, `reconcile` csak ticker-halmaz,
  **szektor-cap monitorozási rés (§11.18)**, **a TP1 utáni max_hold-túlfutás (09-04 §7, nyitott)**,
  **FileVault**, **`docs/analysis/` sync-rés**, **§5.1/§5.2 döntések**.

## 8. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **TP1-ciklusok (teljesen lezárt)** — **n=6, MIND POZITÍV**, Σ **+$850,84**.
- **Pozitív realizált nap** — **27/70**; két egymást követő (09-04, 09-08).
- **Visszalépés exit után** — **n=7**, ebből **6 drágábban** (ma FBP +0,70%).
- **Next-day MKT fill slippage** — CC-éra **n=43** (+FBP +0,70%, adverz): **31 adverz / 12 kedvező**
  (72,1%). Teljes éra: n=69, 47 adverz (68,1%).
- **Szektor-koncentráció** — Financial Services **16,78%**, a captól messze.
- **Kitettség** — 38,80% (a 63,48%-os rekordról tartósan lejjebb).
- **Rally/risk-off aszimmetria** — eső nap, realized szerint +0,64% felülteljesítés.
  Sorozat: 13 rally-lemaradás vs **14** eső-napi felülteljesítés.
- **Ellentétes-előjelű nap** — **15/56**.
- **Outage-késleltetett exit** — n=4 (+ a 08-21-i EQH/DLB **döntés alatt**, §5.2).
- **TP-hit / pozitív-exit**: **2/3**. **Várt-vs-tény**: **−$81** egy 4 napos ablakon (§3).

## 9. Ma (szerda, 09-09) — várt + feltevés *(nagyságrend, nem előrejelzés)*
**Két exit**:

| Idő | Ticker | Típus | Qty | Bázis / 09-08 záró | `várt` |
|---|---|---|---|---|---|
| 15:30 | **MANH** | **MENTAL_SL** | 24 | 220,04 / 207,92 | **≈ −$291** |
| 21:40 | **IMVT** | TIME_STOP | 111 | 41,49 / 39,57 | **≈ −$213** |
| **Σ** | | | | | **≈ −$504** |

📌 A **MANH** öt kereskedési nap alatt −5,5%-ot esett (220,00 → 207,92) — ez lenne a **6. MENTAL_SL**
az érában; a korábbi ötös átlaga **−$333,73** (teljes minta, kétheti riport §6).
📌 Az **IMVT** hetedik napja a könyv egyik legrosszabb tétele.
Ha teljesül: cumulative −$1 669,56 → **~−$2 174**. A könyv **6 → 4 tételre** csökken.

- **Fókuszlista**: (1) a két exit; (2) a **−$1 425,79-es könyv** — mind a hat negatív;
  (3) a **`cum_30d`** (−1,25%, tágul); (4) az **FBP** első teljes napja a visszavétel után.

## 10. Freeze-sor
🔓 A freeze 08-17-én feloldódott — **de a D6 szerint a production konfiguráció FAGYVA marad
2026-09-22-ig**. A **G1/G3–G7 guardrailek élnek**. Ma **nem történt** production-kód változás.
**A kapuig 10 kereskedési nap.**

## 11. A nap egy mondatban
Három exit **+$91,34**-gyel (a cumulative 08-21 óta a legjobb állásra, −$1 669,56-ra javult), és
ezzel **két további TP1-ciklus zárult le pozitívan** — mind a hat lezárt ciklus pozitív, Σ **+$850,84**
—, miközben a nap **a §D3/M korlát legtisztább illusztrációja** lett: a realized-olvasat
**+0,64% felülteljesítést** könyvelt egy napon, amikor **a nyitott könyv −$932-t vesztett** és
mind a hat tétel negatívba fordult; az **FBP-t pedig a rendszer a saját 09-04-i exit-árára
tervezve, +0,70%-kal drágábban vette vissza**.
