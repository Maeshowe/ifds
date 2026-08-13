# IFDS Daily Review — 2026-08-12 (szerda, Day 60/63 NYSE-count)

> Executor: **CC** (CC-only, [[division-of-labor-chat-cc]]). READ-ONLY; forrás minden szám mellett;
> IBKR MCP kereszt-ellenőrzés lefutott. Day 63 előtt nincs jel-ítélet.

## 1. Fejléc
- **Day 60/63** (NYSE-count). ⚠️ `cumulative_trading_days=52`.
- **Realized net: $0,00** (0 exit). **Cumulative: +$195,74 (+0,196%)** — változatlan.
- **Net Liq: $99 939,71** — `daily_equity.json`; **napi Δ: −$223,82** (08-11: $100 163,53).
  ⚠️ **$100k alatt** — másodszor a swing-érában (első: 07-20, $99 901,31).
- **Excess: −0,25%** — `daily_metrics::excess_return` (portfolio 0,00% vs SPY +0,25%). Emelkedő tape,
  **rekord-alacsony VIX 14,45** (−5,43%).
- **Nyitott pozíciók: 7** (`swing_positions` ≡ IBKR 7 ✓, `reconcile::no_divergence`).

## 2. Exits (0)
Nincs végrehajtott exit. **Ma beállított flagek: SSNC, VLTO, JAZZ — mind TIME_STOP** (mindhárom day-5
max_hold) → **holnap (08-13) 21:40 MOC**. A könyv 7 → 4 tételre könnyül.

## 3. Entries (0)
Nincs mai belépő (`new_entries=[]`; submit `existing_skip`: DLB/STE/ADT). A slippage-sorozat n=19 marad.

## 4. Nyitott pozíciók (7) — `swing_positions` + IBKR `get_account_positions`
| Ticker | days_held | Mark | Unrealized | Stop-buffer | next_action |
|---|---|---|---|---|---|
| VLTO | **5** | 96,67 | −$19,48 | 6,60% | **TIME_STOP** (holnap 21:40) |
| STE | 2 | 236,60 | −$34,60 | 5,60% | HOLD |
| DLB | 2 | 61,39 | −$34,84 | 5,41% | HOLD |
| SSNC | **5** | 80,14 | −$154,40 | 5,55% | **TIME_STOP** (holnap 21:40) |
| ADT | 1 | 7,31 | −$156,59 | 3,28% | HOLD |
| GTES | 4 | 27,83 | −$228,80 | 4,10% | HOLD |
| JAZZ | **5** | 248,95 | −$332,21 | 1,12% | **TIME_STOP** (holnap 21:40) |

⚠️ **Total unrealized: −$960,92** — **a swing-éra mélypontja**, és **mind a 7 pozíció negatív**
(a −$697,74-ről tovább romlott). Notional 37,89%.

## 5. Ops-checklist
- ✓ **Reconcile 7/7 silent OK** — `pt_events` 22:15 `reconcile::no_divergence`.
- ✓ **Teljes cron-lánc**: 10:10 monitor (tiszta), 15:31 submit (0 új), **21:40 time_stop üresen futott**
  (nem volt flag), 22:00 eod_eval (**3 TIME_STOP flag**), 22:10 metrics, 22:20 review_data.
- ✓ **Nincs ERROR**; a 20:11 `eod::leftover_warning` (7) normál.
- ✓ **`pt_events` tiszta** (9 sor).
- ⚠️ **STOP-triggerek** (D4: `mean` az irányadó): `excess_10d_mean` **−0,32%** vs −1,0% → **✓ nincs halt**.
  `sum` −3,22% (megfigyelés). **`cum_30d` −1,25%** — **harmadszor javult** (−1,81 → −1,55 → −1,52 → −1,25).
- ✓ **v2 enrichment sink**: `766/518` ≡ scan-matrix **766/518** — pontos egyezés.

## 6. Anomáliák (új/változott/lezárt)
- **✅ LEZÁRVA — a JAZZ „stop-közeli" figyelés (08-11 §6/P2).** A JAZZ **a stop FÖLÖTT zárt**
  (mark 248,95 vs stop 246,15, buffer **0,74% → 1,12%**), ezért **nem** kapott MENTAL_SL-t;
  a **day-5 max_hold** miatt TIME_STOP-ot kapott.
  📌 **Verifikálva a kódból** (`swing_positions.py::evaluate`): a prioritás **HARD_SL → MENTAL_SL → TP2
  → TP1 → TRAIL_SL → TIME_STOP → HOLD**, azaz a **MENTAL_SL (2.) megelőzi a TIME_STOP-ot (6.)** —
  tehát a TIME_STOP besorolás **bizonyítja**, hogy a záró a stop fölött volt. *(A `swing_manager.py`-ben
  látható „max_hold elöl" sorrend egy másik ág: a trail/breakeven kezelése, nem a flag-besorolás.)*
  **Ezzel a „stop-közeli" sorozat: 4 riasztásból 4 visszapattant** (USFD 07-20, ROIV 07-29, CTAS 08-03,
  JAZZ 08-11); egyedül a CTAS lett **másodszorra** valódi (08-05).
- **⚠️ ÚJ — a könyv 7/7 negatív, unrealized −$960,92 (swing-éra mélypont).** Nincs egyetlen nyereséges
  tétel sem. A romlás **széles**, nem egy tétel hajtja (a legnagyobb a JAZZ −$332, de öt másik is
  −$19…−$229 között). Tényszerű rögzítés; a három holnapi TIME_STOP ebből ~−$506-ot realizál (§8).
- **⚠️ Változott — a MTM- és a realized-olvasat kezd szétnyílni.** A 10 napos MTM-átlag **−0,47%**
  vs a realized `mean` **−0,32%** (08-11: −0,40% vs −0,29%). **Nem ellentétes irány** (a D3 szerinti
  P1-eset nem áll fenn), de a **rés nő** — a nyitott könyv romlása gyorsabb, mint amit a realized-only
  mező mutat. **Követendő.**
- **Ismert, nyitott** (nem ismételve): `exit_type` mező hibás, entry_price=planned (§11.10),
  **FileVault** (Tamás-döntés).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **n=19, ma nem nőtt** (0 belépő). |medián| 0,91%, torzítás +0,24%.
- **Self-reentry** — n=2, változatlan.
- **Outage-késleltetett exit** — n=4, változatlan.
- **Rally/risk-off aszimmetria** — ma emelkedő nap (SPY +0,25%), a könyv **0,00%** → excess −0,25%.
  A sorozat: **5 rally-lemaradás vs 5 eső-napi felülteljesítés**. **Az aszimmetria továbbra is
  konzisztens** (a könyv emelkedő napon nem emelkedik, eső napon jobban tart).
- **„Stop-közeli" riasztás** — **n=5**: 4 visszapattant (USFD, ROIV, CTAS-1, JAZZ), 1 valódi (CTAS-2).
  *(Új sorozat, a 08-12-i JAZZ-lezárással formálisan rögzítve.)*
- **TP-hit / pozitív-exit**: ma 0 exit.
- **Várt-vs-tény**: ma nem mérhető (0 exit volt tervezve ✓).

## 8. Holnap (csütörtök, 08-13) — várt + feltevés
**Három TIME_STOP 21:40 MOC** (mind day-5 max_hold; feltevés: csütörtöki close ≈ szerdai mark):
| Ticker | Qty | Mark → bázis | `várt` |
|---|---|---|---|
| VLTO | 56 | 96,67 / 97,02 | **−$19** |
| SSNC | 65 | 80,14 / 82,52 | **−$154** |
| JAZZ | 22 | 248,95 / 264,05 | **−$332** |
| **Σ** | | | **≈ −$506** |

Ha teljesül: cumulative **+$195,74 → ~−$310**. A könyv **4 tételre** csökken (STE, DLB, ADT, GTES).

- **Fókuszlista**: (1) a három exit várt-vs-tény; (2) az unrealized −$961 alakulása a maradó könyvön;
  (3) a `cum_30d` javuló trendje (−1,25%) a realizálás után; (4) a MTM/realized rés (§6);
  (5) **kapu: Day 63 ~08-17 — 3 trading nap** (freeze-feloldás + első leíró `signal_attribution`).

## 9. Freeze-sor
**Paraméter-érintő változás ma: nincs.** Freeze él Day 63-ig.

## 10. A nap egy mondatban
Csendes szerda (0 exit, 0 belépő) rekord-alacsony VIX mellett (14,45), de a nyitott könyv a swing-éra
mélypontjára esett (**−$960,92, mind a 7 tétel negatív**), a NetLiq $100k alá csúszott, és holnap
három day-5 TIME_STOP realizál ebből ~−$506-ot.
