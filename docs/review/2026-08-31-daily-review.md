# IFDS Daily Review — 2026-08-31 (hétfő, Day 73/63)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ **Az IBKR MCP connector ebben a sessionben nem érhető el** — a bróker-oldali kereszt-ellenőrzés
> **kimaradt**. Helyette: a Mini `reconcile_state` **silent OK**-ot adott (`state ≡ IBKR`), és a
> `pending_exits` feldolgozva. A záró markok **Polygon**-ból.

## 1. Fejléc
- **Realized net: +$64,57** (gross +$65,60, komm. $1,03) — **1 exit**.
  🟢 **A második pozitív realizált nap** (08-27 után) — az érában **24/65**.
- **Cumulative: −$1 774,94 (−1,77%)** — a mélypontról **$64,57-tal javult**.
- **Net Liq: $98 527,86** — napi Δ **+$93,36**.
- **Excess: +0,36%** (portfolio +0,07% vs SPY −0,30%). **MTM: +0,39%** — azonos előjel,
  mindössze **0,03 pp rés** (a sorozat egyik legszorosabb egyezése).
- **VIX 14,92 (+3,40%)**, SPY **−0,30%** — enyhe risk-off.
- **Nyitott pozíciók: 10** — **éra-rekord** (`max_concurrent` 12).

## 2. Exits (1)
| Idő (UTC) | Ticker | Típus | Qty | Entry → Exit | Realized |
|---|---|---|---|---|---|
| 13:30:25 | **AMR** | **TP1** (13→7) | 6 | 219,25 → **230,01** | **+$64,57** (+4,91%) |

📌 **A negyedik TP1, és mind a négy pozitív** (DLB +$154,47 | PSO +$121,76 | IMAX +$76,32 |
**AMR +$64,57**). Az AMR különösen tanulságos: **08-26-án +1,56%-os adverz fillel** vettük
(a CC-éra 3. legrosszabb belépője) — **és mégis ez lett a legjobb százalékos TP1** (+4,91%).
A **rossz belépő-fill nem determinálta a kimenetelt**. ⚠️ **n=1, leíró (G3).**

A maradék **7 db AMR +$116,90**-en áll — a könyv legjobb tétele (§4).

## 3. Entries (1)
| Ticker | Qty | Planned→Fill | Slippage | Szektor |
|---|---|---|---|---|
| IMVT | 111 | 41,20 → **41,48** | +0,68% (adverz) | Healthcare |

**69 ticker** a küszöb felett — **jelentős visszaesés** a pénteki 95-ről (−27%).

## 4. Nyitott pozíciók (10) — 08-31 záró mark
| Ticker | Szektor | Bázis | Záró | Unrealized |
|---|---|---|---|---|
| AMR (TP1 után) | Energy | 219,00 | 235,70 | **+$116,90** |
| RGEN | Healthcare | 180,72 | 180,98 | +$6,50 |
| RCI | Comm. Services | 36,87 | 36,89 | +$5,28 |
| FBP | Fin. Services | 27,90 | 27,88 | −$7,58 |
| MD | Healthcare | 26,62 | 26,23 | −$71,37 |
| IMVT | Healthcare | 41,48 | 40,82 | −$73,26 |
| NWBI | Fin. Services | 15,39 | 15,29 | −$74,18 |
| CRBG | Fin. Services | 32,92 | 32,54 | −$77,14 |
| IMAX | Comm. Services | 52,48 | 51,20 | −$106,24 |
| ELVN | Healthcare | 60,35 | 57,89 | **−$191,88** |
| **Σ** | | | | **−$472,97** |

A könyv **−$517,95 → −$472,97** (+$44,98) — érdemben **változatlan**, 3/10 pozitív.
Az **ELVN** negyedik napja a legrosszabb tétel, és **ma este TIME_STOP-on zár** (§8).

⚠️ **Kitettség: `total_notional` 63,48% — éra-rekord** (10 tétel). **Financial Services 29,27%**,
a 30%-os cap **0,73 pp-re** — a `sector_cap_proximity` P2 flag **második napja** tüzel.

## 5. Ops-checklist
- ✓ **Teljes cron-lánc lefutott**: 14:30 Phase 4-6, 15:30 eod_flags (AMR TP1), 15:31 submit (IMVT),
  22:00–22:45 eod-lánc. `reconcile_silent_ok` — **state ≡ IBKR** (a Mini futtatta).
- 🟡 **`sector_cap_proximity` P2, 2. nap** — Financial Services 29,3% (cap 30%). **Nem nőtt tovább**
  (a mai belépő Healthcare volt), de a szint tartja magát.
- ✓ **STOP-triggerek** (D4: a `mean` az irányadó):
  `excess_10d_mean` **−0,06%** ✓ | `excess_15d_mean` **−0,07%** ✓ | `excess_10d_sum` −0,59% ✓
- ⚠️ **`cum_30d` −2,07% → −2,27%** — a négynapos mozdulatlanság után **romlott**; a −3,0%-os
  küszöbtől **0,73 pp**. **Ez a legszorosabb távolság eddig** (a korábbi legjobb 0,85 pp volt,
  08-21-én). **Továbbra is az egyetlen valódi trigger-közelség — és most közeledik.**
- ⚠️ **`excess_15d_sum` −1,02%** — **hajszálnyira a küszöb alatt** (−1,0%), technikailag BREACH.
  **D4: a `sum` megfigyelés, nem trigger.**

## 6. Anomáliák (új/változott/lezárt)
- **🔴 KORREKCIÓ — öt review megfigyelését félreértelmeztem.**
  08-25 óta minden nap rögzítettem, hogy *„a top-3 jelölt teljesen Healthcare, a belépő mégsem az"*,
  és ezt **megmagyarázatlan mintázatként** vittem tovább, kapu utáni Phase 6 vizsgálati tételként.
  **A magyarázat mundán, és már ismert volt.**

  A `top_3_scores` a **teljes Phase 4 univerzum** top-3-a (`daily_metrics.py`: a snapshot
  `combined_score` szerint rendezve) — de **mind a 15 top-3 tétel az öt nap alatt olyan pozíció
  volt, amit a nap elején MÁR TARTOTTUNK**:

  | Nap | Top-3 (\* = már tartott) | Belépő |
  |---|---|---|
  | 08-25 | ELVN\*, MD\*, FMS\* | NWBI |
  | 08-26 | MD\*, ELVN\*, RGEN\* | AMR |
  | 08-27 | MD\*, ELVN\*, RGEN\* | FBP, RCI |
  | 08-28 | ELVN\*, MD\*, RGEN\* | CRBG, IMAX |
  | 08-31 | IMAX\*, FBP\*, MD\* | IMVT |

  **15/15.** A `submit_orders.py` a meglévő pozíciókat **`existing_skip`-pel kihagyja** (ezt a
  08-17-i review §3-ban magam is rögzítettem a DLB-nél). Tehát a belépő **szükségszerűen** a
  top-3 alól jön — **ez a tervezett viselkedés, nem anomália**.

  📌 **A tanulság a saját munkámról**: egy mintázatot öt napon át „megmagyarázatlanként" vittem
  tovább anélkül, hogy a mezőt előállító kódot megnéztem volna. **A mezőt a forrásáig kell
  visszakövetni, mielőtt mintázatot állítok róla.** A Healthcare-koncentráció **ténye** áll
  (20,93% négy napig változatlan = nem nyílt/zárt Healthcare tétel), de a hozzá fűzött
  „a rendszer nem a top-3-ból választ" **értelmezés téves volt** — visszavonva.
- **📌 Rossz belépő-fill ≠ rossz kimenetel (n=1).** Az AMR a CC-éra 3. legrosszabb fillje
  (+1,56%, 08-26) után a **legjobb százalékos TP1**-et adta (+4,91%). **Leíró (G3)**, egyetlen eset.
- **⚠️ A `cum_30d` közeledik** (−2,27%, 0,73 pp a küszöbtől) — §5. **A jövő heti fókusz első pontja.**
- **✅ VÁLTOZATLAN**: `exit_type` ma helyes (`TP1`, normál ablak — §11.17), `swing_state.exits_today`
  félrenevezés (ma `{TIME_STOP:3}` ≡ a **mai esti** flagek), `commission_total` csak exit-láb,
  `entry_price=planned`, `reconcile` csak ticker-halmaz, **FileVault**,
  **`docs/analysis/` sync-rés**, **§5.1/§5.2 döntések**.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **TP1-sorozat** — **n=4, mind pozitív** (DLB, PSO, IMAX, **AMR**). Ebből **3 ciklus lezárt**:
  IMAX +$69,48 | DLB +$95,30 | PSO +$288,57 (Σ **+$453,35**).
- **Pozitív realizált nap** — **24/65**; ma a második 08-11 óta (08-27 és 08-31).
- **Next-day MKT fill slippage** — CC-éra **n=38** (+IMVT +0,68%, adverz): **28 adverz / 10 kedvező**
  (73,7%). Teljes éra: n=64, 44 adverz (68,8%).
- **Szektor-koncentráció** — Financial Services **29,27%** (2. nap a flag-küszöb felett).
- **Kitettség** — **63,48%, éra-rekord** (10 tétel).
- **Visszalépés exit után** — n=4 (az IMAX 08-28-i, olcsóbb esete a legutóbbi).
- **Outage-késleltetett exit** — n=4 (+ a 08-21-i EQH/DLB **döntés alatt**, §5.2).
- **Rally/risk-off aszimmetria** — eső nap, realized szerint +0,36% felülteljesítés.
  Sorozat: 11 rally-lemaradás vs **11** eső-napi felülteljesítés — **kiegyenlítődött**.
- **Ellentétes-előjelű nap** — **13/52**, ma nem (mindkettő pozitív, 0,03 pp rés).
- **TP-hit / pozitív-exit**: **1/1**.

## 8. Ma (kedd, 09-01) — várt + feltevés
**Három TIME_STOP 21:40 MOC** (feltevés: keddi close ≈ hétfői záró):

| Ticker | Qty | Bázis / záró | `várt` |
|---|---|---|---|
| **ELVN** | 78 | 60,35 / 57,89 | **≈ −$192** |
| MD | 183 | 26,62 / 26,23 | ≈ −$71 |
| RGEN | 25 | 180,72 / 180,98 | ≈ +$7 |
| **Σ** | | | **≈ −$256** |

⚠️ **Nagyságrend, nem előrejelzés** — az elmúlt két hétben a becslés hatszor tévedett $44–150-nel.
Ha teljesül: cumulative −$1 774,94 → **~−$2 031** (először $2 000 alatt). A könyv **10 → 7 tételre**
csökken, és a **Healthcare-kitettség érdemben lecsökken** (ELVN + MD + RGEN kiszáll).

- **Fókuszlista**: (1) a három TIME_STOP; (2) a **`cum_30d`** (−2,27%, **közeledik**);
  (3) a Financial Services 29,27% (3. nap?); (4) a **63,48%-os kitettség** lecsengése.

## 9. Freeze-sor
🔓 A freeze 08-17-én feloldódott — **de a D6 szerint a production konfiguráció FAGYVA marad
2026-09-22-ig**. A **G1/G3–G7 guardrailek élnek**. Ma **nem történt** production-kód változás.
**A kapuig 15 kereskedési nap.**

## 10. A nap egy mondatban
Második pozitív nap (**+$64,57**, a negyedik TP1 — és mind a négy pozitív), amelyet épp az a
tétel adott, amit **a CC-éra 3. legrosszabb belépő-filljével** vettünk — miközben a kitettség
**éra-rekord 63,48%**-ra nőtt, a **`cum_30d` −2,27%-ra közeledett a −3,0%-os küszöbhöz**
(a valaha volt legkisebb, 0,73 pp-es távolság), és **visszavontam** egy öt review-n át vitt
téves értelmezést: a top-3 jelölt azért nem lesz belépő, mert **mind a 15 esetben már tartott
pozíció volt**, amit a `submit` `existing_skip`-pel kihagy.
