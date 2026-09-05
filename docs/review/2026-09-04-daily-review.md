# IFDS Daily Review — 2026-09-04 (péntek, Day 77/63) + **W36 heti** + **kétheti scoring-validation**

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ Az IBKR MCP connector ebben a sessionben nem érhető el — bróker-kereszt-ellenőrzés **kimaradt**.
> Helyette: Mini `reconcile_state` **silent OK** (`state ≡ IBKR`), záró markok **Polygon**-ból.

## 1. Fejléc
- **Realized net: +$504,57** (gross +$508,98, komm. $4,41) — **3 exit, MIND A HÁROM POZITÍV**.
  🟢 **A swing-éra 2. legjobb realizált napja** (rekord: 06-10, +$631,96).
- **Cumulative: −$1 760,90 (−1,76%)** — a −$2 265-ös mélypontról **$504,57-tal javult**.
- **Net Liq: $98 540,54** — napi Δ **−$653,61**. ⚠️ A NetLiq **esett** egy +$504-es realizált napon:
  a nyereség **átsorolás** volt (unrealized → realized), és a maradék könyv romlott (§5).
- **Excess: +0,89%** (portfolio +0,51% vs SPY −0,39%) — az éra egyik legjobb napi excess-e.
- **VIX 14,38 (+0,42%)**, SPY **−0,39%**.
- **Nyitott pozíciók: 8**.

## 2. 🟢 MINDEN STOP-TRIGGER TISZTA — először a review-időszakban
```
STOP-triggerek: ✓ nincs breach (mind a pre-reg ablak kiértékelve)
```
| Trigger | 09-03 | **09-04** | Küszöb |
|---|---|---|---|
| `excess_10d_mean` | −0,29% | **−0,08%** | −1,0% |
| `excess_15d_mean` | −0,10% | **−0,03%** | −1,0% |
| `excess_10d_sum` | −2,90% ⚠️ | **−0,81%** ✓ | −1,0% |
| `excess_15d_sum` | −1,44% ⚠️ | **−0,51%** ✓ | −1,0% |
| **`cum_30d`** | −2,37% | **−1,34%** | **−3,0%** |

📌 **A `cum_30d` −2,37% → −1,34%**, a küszöbtől **1,66 pp**. Két hajtóereje: a mai **+$504,57**,
és a tegnap jelzett **kedvező gördülés** (a 07-23-i **−$531,32** kigördült az ablakból).
**Hat ülés alatt** a mutató −2,77% (a valaha volt legszorosabb) → −1,34%-ra tágult.
⚠️ A `sum`-olvasatok D4 szerint megfigyelés — de **most először ezek is a küszöb felett**.

## 3. Exits (3) — mind pozitív, az éra első ilyen napja
| Idő (UTC) | Ticker | Típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 13:30:24 | **RCI** | **TP1** (264→132) | 132 | 36,88 → 37,85 | **+$127,57** (+2,62%) | ≈ +$148 | −$20 |
| 13:31:18 | **CRBG** | **TP1** (203→101) | 101 | 32,94 → 34,42 | **+$149,90** (+4,51%) | ≈ +$184 | −$34 |
| 19:59:31 | **FBP** | TIME_STOP | 379 | 27,91 → 28,51 | **+$227,10** (+2,15%) | ≈ +$207 | +$20 |
| **Σ** | | | | | **+$504,57** | ≈ +$539 | **−$34** |

✅ **A becslés pontossága helyreállt**: Σ-hiba **−$34** egy ≈$539-es várakozáson (6,3%), és
egyetlen tétel sem tért el $34-nél többel. Ez a **legjobb pontosság** a sorozatban — szemben az
előző három üléssel ($282 / $226 / $122), ahol **mindhárom eltérést egyedi papír-sokk** okozta.
**A módszer nyugodt piacon működik; sokkra vak.**

📌 **A FBP a legnagyobb pozitív TIME_STOP az érában** (+$227,10, 379 db).

## 4. Entries (2) — mindkettő kedvező fillel
| Ticker | Qty | Planned→Fill | Slippage | Szektor |
|---|---|---|---|---|
| **EQH** | 136 | 53,54 → **53,11** | **−0,80%** (kedvező) | Financial Services |
| **MANH** | 24 | 222,35 → **220,00** | **−1,06%** (kedvező) | Technology |

Qty-súlyozott átlag **−0,84%** — a **CC-éra legjobb napi fill-átlaga** (előző legjobb: −0,53%).

📌 **Az EQH visszalépés — n=5, és ismét DRÁGÁBBAN.** Az EQH-t **08-21-én MENTAL_SL-en**
zártuk **49,40**-en (−$371,36; ez volt a „rés utáni visszalépés" sorozat 3. lezárt esete),
ma **53,11**-en vettük vissza — **+7,5%-kal magasabban**. A 08-28-i IMAX (−0,29%, olcsóbb)
után ez visszatér a **drágább** mintázathoz. Sorozat: JAZZ +2,8% | GTES +11,3% | EQH(1) +9,5% |
DLB +1,34% | IMAX −0,29% | **EQH(2) +7,5%**. ⚠️ **Leíró (G3)**, n=6.

## 5. Nyitott pozíciók (8) — 09-04 záró mark
| Ticker | Szektor | Bázis | Záró | Unrealized |
|---|---|---|---|---|
| CRBG (TP1 után) | Fin. Services | 32,93 | 34,47 | **+$157,59** |
| RCI (TP1 után) | Comm. Services | 36,88 | 37,52 | **+$85,14** |
| EQH | Fin. Services | 53,11 | 52,96 | −$20,40 |
| IMAX | Comm. Services | 52,49 | 51,64 | −$70,72 |
| INTA | Technology | 42,90 | 41,71 | −$121,36 |
| NWS | Comm. Services | 34,45 | 33,90 | −$126,14 |
| MANH | Technology | 220,00 | 213,77 | −$149,52 |
| IMVT | Healthcare | 41,49 | 39,25 | **−$248,53** |
| **Σ** | | | | **−$493,94** |

A könyv **+$645,85 → −$493,94** (−$1 139,79) — de ebből **~$505 az exitekkel realizálódott**
(átsorolás, nem veszteség). **2/8 pozitív.** Kitettség **41,82%**, a legnagyobb szektor
Communication Services **16,99%** — a captól messze, a `sector_cap_proximity` **nem tüzelt**.
Az **IMVT** ötödik napja a legrosszabb tétel (−$248,53).

## 6. Ops-checklist
- ✓ **Teljes cron-lánc lefutott**: 14:30 Phase 4-6, 15:30 eod_flags (2 TP1), 15:31 submit
  (EQH, MANH), 21:40 time_stop (FBP MOC), 22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- 🟢 **Minden STOP-trigger tiszta** (§2) — a review-időszakban először.
- 📌 **`max_days_held: 6`** — az **RCI** 6 kereskedési napon áll a `max_hold_trading_days: 5`
  mellett. **Nem belső inkonzisztencia**: a `review_data` szerint
  `days_held_trading = days_held_expected_trading = 6` (egyeznek). Lásd §7.

## 7. Anomáliák (új/változott/lezárt)
- **📌 NYITOTT MEGFIGYELÉS — a TP1 utáni maradék rendszeresen túlfut a `max_hold=5`-ön.**
  Három megfigyelt eset: **DLB** (TP1 08-21 → TIME_STOP 08-27, 6. nap), **PSO** (TP1 08-25 →
  TIME_STOP 08-28, 6. nap), **RCI** (TP1 09-04, ma **6. nap**, TIME_STOP hétfőre → 7. nap).
  A `swing_manager.py:127` szabálya `hold_days >= 5 → MOC_EXIT`, és a flag→másnapi-végrehajtás
  architektúra **strukturálisan egy nap csúszást ad**. Az RCI-nél viszont **09-03-án TP1-flag
  született** (`pt_monitor` log: `RCI: TP1`), holott a kód a `max_hold`-ot a TP1 **ELŐTT**
  ellenőrzi — ez a precedencia-út **még nincs végigkövetve**.
  ⚠️ **Nem állítok defektet** — a `review_data` konzisztencia-mezője (`days_held_expected_trading`)
  **egyetért** a 6-tal. Rögzítem **nyitott megfigyelésként**, a bizonyítékkal.
  📌 **Ez közvetlenül a D6 SIM-napirend 1. tételét (max_hold-érzékenység) érinti** — a
  vizsgálat **kapu utáni** (D6: prod fagyva 09-22-ig).
- **📌 Az EQH visszalépés +7,5%-kal drágábban** (§4) — a sorozat n=6.
- **✅ VÁLTOZATLAN**: `exit_type` ma helyes (normál ablak, §11.17), `swing_state.exits_today`
  félrenevezés (ma `{TIME_STOP:3}` ≡ a **hétfői** IMAX/RCI/CRBG flagek), `commission_total`
  csak exit-láb, `entry_price=planned`, `reconcile` csak ticker-halmaz,
  **szektor-cap monitorozási rés (§11.18)**, **FileVault**, **`docs/analysis/` sync-rés**,
  **§5.1/§5.2 döntések**.

## 8. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **TP1-sorozat** — **n=6, mind pozitív** (DLB, PSO, IMAX, AMR, **RCI +$127,57**, **CRBG +$149,90**).
  Teljesen lezárt ciklus: **n=4**, Σ **+$494,86**.
- **Pozitív realizált nap** — **26/69**; a mai a 2. legjobb az érában.
- **Next-day MKT fill slippage** — CC-éra **n=42** (+EQH −0,80%, +MANH −1,06%, **mindkettő kedvező**):
  **30 adverz / 12 kedvező** (71,4%). A napi átlag **−0,84%** a CC-éra legjobbja.
- **Visszalépés exit után** — **n=6**; ma az EQH **+7,5%-kal drágábban**.
- **Szektor-koncentráció** — Comm. Services **16,99%**, a captól messze.
- **Kitettség** — 41,82%.
- **Rally/risk-off aszimmetria** — eső nap, realized szerint **+0,89% felülteljesítés**.
  Sorozat: 13 rally-lemaradás vs **13** eső-napi felülteljesítés — **kiegyenlítve**.
- **Outage-késleltetett exit** — n=4 (+ a 08-21-i EQH/DLB **döntés alatt**, §5.2).
- **TP-hit / pozitív-exit**: **3/3**. **Várt-vs-tény**: **−$34** — a sorozat legjobb pontossága.

---

# W36 heti zárás (2026-08-31 – 09-04)

| Mérőszám | **W36** | *(W35)* | *(W34)* |
|---|---|---|---|
| **Net P&L** | **+$78,61** 🟢 | *−$306,94* | *−$1 082,69* |
| Cumulative | **−$1 760,90 (−1,76%)** | *−$1 839,51* | *−$1 532,57* |
| Portfolio heti | +0,09% | *−0,30%* | *−1,07%* |
| SPY heti | +0,11% | *+0,48%* | *−1,37%* |
| **Excess vs SPY** | **−0,02%** | *−0,78%* | *+0,30%* |
| **Nyerő napok** | **3 / 5** 🟢 | *1/5* | *0/5* |
| **TP1-találat** | **3/5 (60%), átlag +$114,01** | *2/9 (22%)* | *0/6 (hibás)* |
| Zero-pozíciós nap | 2/5 | *0/5* | *1/5* |
| Legrosszabb slippage | +1,59% (INTA) | *+1,56%* | *+1,39%* |

## A hét karaktere (tényszerű)
- 🟢 **AZ ELSŐ POZITÍV HÉT** a review-időszakban (+$78,61), és a **legjobb nyerő-nap-arány** (3/5).
- **Az excess viszont gyakorlatilag nulla (−0,02%)** — a hét **abszolút** pozitív, **relatíve**
  semleges (az SPY +0,11%-ot ment). A W34/W35 tanulsága ismétlődik: **a két olvasat külön értendő**.
- **A hetet a TP1-ág vitte**: 3 TP1 (RCI, CRBG + az AMR TP1 08-31-én), átlag **+$114,01**.
  A **TP1-találati arány 60%** — messze a legjobb hét.
- ⚠️ **A jutalék a bruttó 15%-a** ($14,11 / $92,72) — a kis bruttó miatt magas arány, nem
  költség-emelkedés. Megfigyelendő, ha a bruttó tartósan alacsony marad.
- **A hét íve**: 09-01 mélypont (−$502, `cum_30d` a küszöb 0,23 pp-ére) → 09-04 (+$505, minden
  trigger tiszta). **Egy hét alatt a legszorosabb trigger-állásból a legtágabba.**

---

# Kétheti scoring-validation (`scoring_validation.py --fetch-spy`)

> ⚠️ **G1: a `scoring_validation.py` NEM kapu-input** — sem mellette, sem ellene (gate-protokoll §7).
> ⚠️ **G3: nincs jel-érvényességi nyelv** a kapu-futásig (2026-09-22). Az alábbi **kizárólag leíró**.

**Minta**: 514 trade / 69 kereskedési nap / 130 Phase 4 snapshot; **291/514 enriched**.

### A swing-éra sor (az egyetlen architektúra-releváns nézet)
| Éra | N | Pearson (score vs **excess**) | Pearson (score vs raw P&L%) |
|---|---|---|---|
| legacy (≤2026-05-15) | 442 | +0,022 (p=0,651) | +0,006 (p=0,899) |
| **swing (≥2026-05-18)** | **72** | **−0,386** (p=0,001) | **−0,315** (p=0,007) |
| pooled ⚠️ | 514 | −0,138 (p=0,002) | −0,106 (p=0,016) |

✅ **A riport MOST MÁR tartalmazza az éra-bontást** (§5.1, „G5 — kötelező") — a korábban
ismert **éra-poolozási rés lezárult** a szerszám oldalán. A pooled sor kifejezetten meg van
jelölve, hogy két stratégiát kever.

**Változás az előző kétheti óta** (n=48, Pearson −0,409, p=0,004):
| | előző | **most** |
|---|---|---|
| swing N | 48 | **72** (+50%) |
| Pearson (excess) | −0,409 | **−0,386** |
| p | 0,004 | **0,001** |

📌 **Tényszerű megállapítás**: a minta **50%-kal nőtt**, az együttható **gyakorlatilag változatlan**
(−0,409 → −0,386), a p-érték szigorodott. **Ebből semmilyen jel-érvényességi állítás nem
vonható le (G3), és a kapuba nem idézhető (G1).** A kapu egyetlen inputja a pinelt
`signal_attribution.py` (`c5e9ed0`) + a `gate_sample.py` wrapper (`68fc00e`).

### Egyéb leíró metszetek (teljes minta, éra-keverten — óvatosan)
- **Komponensek**: flow **+0,152** (p=0,009) | tech −0,045 (p=0,448) | funda −0,074 (p=0,209).
- **Kvintilis-spread**: Q5 átlag −$10,25 vs Q1 −$18,87 → **+$8,63**; a Q2 (91–93) a legjobb
  (+$4,17 átlag, 57,3% win).
- **Exit-típus (teljes minta)**: TP2 **+$277,99** átlag (n=7) | TP1 **+$50,38** (n=54) |
  MOC +$9,36 (n=332) | TIME_STOP **−$70,89** (n=36) | MENTAL_SL **−$333,73** (n=5) |
  LOSS_EXIT −$104,96 (n=47). ⚠️ **Éra-kevert** — a swing-éra saját bontása a Day 63
  összefoglalóban van.

## Következő hét (2026-09-07 – 09-11)
1. **Hétfőn 3 TIME_STOP** (IMAX, RCI, CRBG) — a RCI és CRBG TP1-maradéka.
2. **`cum_30d`** (−1,34%) — a szorítás oldódott, de a heti gördülés figyelendő.
3. **Tamás-döntés × 2** (08-21-i review §6): **§5.1 részleges-outage** kritérium és a
   **§5.2 EQH/DLB** besorolás. **A kapuig 11 kereskedési nap.**
4. **FileVault** — a 3. előfordulás óta nyitva.
5. A **D6 SIM-napirend** indítása (prod fagyva) — a `max_hold` kérdéshez ma új input érkezett (§7).

## 9. Freeze-sor
🔓 A freeze 08-17-én feloldódott — **de a D6 szerint a production konfiguráció FAGYVA marad
2026-09-22-ig**. A **G1/G3–G7 guardrailek élnek**. Ma **nem történt** production-kód változás.

## 10. A nap egy mondatban
**Három exit, mind pozitív (+$504,57, az éra 2. legjobb napja)**, a becslés végre **$34-en belül**,
mindkét belépő **kedvező fillel** (−0,84%, a CC-éra legjobbja) — és ezzel **minden STOP-trigger
tisztára állt** (a `cum_30d` hat ülés alatt −2,77%-ról −1,34%-ra tágult); a hét **az első pozitív
hét** lett (+$78,61, 3/5 nyerő nap, 60% TP1-találat), a kétheti scoring-validation pedig
**50%-kal nagyobb swing-mintán gyakorlatilag változatlan együtthatót** adott (−0,409 → −0,386,
p=0,001) — **leíró, nem kapu-input**.
