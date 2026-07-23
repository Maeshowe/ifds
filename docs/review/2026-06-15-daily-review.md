# IFDS Daily Review — 2026-06-15 (hétfő, Day 20/63 NYSE-count, W25 D1)

## 1. Fejléc
- **Day 20/63** (NYSE-count, `daily_metrics::day_number`, `pt_eod` render egyező; megj.: `cumulative_pnl::trading_days=19` — a 2026-06-01 hiányzó sor miatti -1 eltolás fennáll, §6.2)
- **Realized net: -$152,22** (gross -$151,12; commission $1,10) — egyetlen exit (FFIV TIME_STOP_MOC). Forrás: `daily_metrics/2026-06-15.json::pnl`, `pending_exits/2026-06-15.json`, `pt_daily_metrics` broker-ledger fetch (`record_pending_exits: matched=1`)
- **Cumulative: +$1 582,80 (+1,58%)** — `cumulative_pnl.json` (1735,02 − 152,22)
- **Net Liq: 06-15 zárásra nem verifikálható** ⚠️ — a hétfői záró summary-ablak elmúlt; az élő IBKR `get_account_summary` MOST a 06-16 intraday értéket adja ($101 327,13, 8 pozíció, $44k gross), nem a hétfői close-t. §6.4/§6.5 Net Liq-szálak retroaktívan nem zárhatók tisztán — előretekintve a summary-t a megfelelő ablakban kell rögzíteni
- **Excess: -1,91%** (portfolio -0,15% vs SPY +1,76%, `daily_metrics::excess_return`) — ⚠️ a portfolio-return realized-alapú szemantika (#6 fix inaktív): a -0,15% = -152,22/$100k, ami **csak az FFIV realizált veszteségét méri**, a nyitott könyv aznapi MTM-emelkedését (SPY +1,76% nap) nem; a -1,91% excess emiatt **felfelé túlozza az alulteljesítést**. Ismétlődő szemantikai tétel (06-09/06-10/06-12)
- **Nyitott pozíciók: 6** (FFIV kilépett, NNN belépett; `swing_positions.json` 06-15 állapot + `pt_reconcile` 22:15 IBKR-egyezés)

## 2. Exits (1) — forrás: `pending_exits/2026-06-15.json` + broker-ledger (`record_pending_exits`)
| Idő (CEST) | Ticker | Típus | Qty | Entry→Exit | Broker realized | Várt (06-12 review §9) | Eltérés |
|---|---|---|---|---|---|---|---|
| 21:59:30 | FFIV | **TIME_STOP_MOC** | 12 | $408,87→$396,18 | **-$152,22** (-3,1%) | ≈ -$140 (feltevés: mark ~$397, MOC zár) | **-$12 a becslés alatt** |

A 06-12 review előrejelezte: ez a deploy óta az **első negatív TIME_STOP** — megerősítve. A becslés iránya és nagyságrendje helyes volt (-$140 vs tény -$152,22); a kis eltérés a MOC-fill ($396,18 vs feltételezett ~$397) és az entry-referencia ($408,87 broker-avg vs $408,66 planned). Az `exit_type` ezúttal **helyes** (`TIME_STOP_MOC`, egyezik a `pending_exits`-szel) — a self-reentry exit_type-bug itt nem aktiválódik, mert ez nem TP2-utáni újranyitás.

## 3. Entries (1) — forrás: `pt_submit_2026-06-15.log`, `daily_metrics::execution`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 | entry_score |
|---|---|---|---|---|---|---|
| NNN | Real Estate | 208 | $46,59→$46,60 | +0,02% (elhanyagolható) | $44,91 / $47,85 / $49,11 | 83,34 (S_j 83,3) |

A pipeline 3 tickert sized (VNO 96,0 / JAZZ 86,3 / NNN 83,3), de VNO és JAZZ már nyitott → race guard skip; csak NNN lépett be. NNN a 3. Real Estate név a könyvben (NSA, VNO mellett) — §7 koncentráció-megfigyelés. A slippage a deploy egyik legjobbja (+0,02%), szemben a 06-11 JAZZ +2,25%-kal.

## 4. Nyitott pozíciók (6) — forrás: `swing_positions.json` (06-15 záró állapot)
| Ticker | days_held | Entry | Stop/Trail | next_action |
|---|---|---|---|---|
| TKR | 5 | $131,83 | trail $134,685 (frissült 132,55-ról, tp1_hit) | **TIME_STOP** (06-16, §9) |
| ACHC | 4 | $25,32 | stop $22,84 | HOLD |
| VNO | 3 | $38,45 | stop $36,27 | HOLD |
| JAZZ | 2 | $229,63 | stop $215,33 | HOLD |
| NSA | 2 | $45,42 | stop $43,48 | HOLD |
| NNN | 0 | $46,59 | stop $44,91 | HOLD |

⚠️ **Net Liq alapú unrealized nem listázható** — az élő IBKR positions a 06-16 intraday markokat adja (EXEL/CORT-tal, TKR esetleges mai exitjével), nem a hétfői close-t; a `swing_positions.json` nem tárol napi markot. A nyitott-könyv hétfői MTM-jét ezért nem riportálom (verifikálatlan lenne).

**Notional: $34 509,82 (34,51% equity)** — emelkedett a 06-12-i 29,72%-ról (NNN belépés + a megmaradt könyv). **Real Estate $22 791,98 = 22,79%** (NSA+VNO+NNN, 3 név) — a 30% notional-cap alatt, de a deploy óta a legmagasabb megfigyelt szektor-koncentráció; §7.

## 5. Ops-checklist
- ✓ `pt_reconcile` 22:15:06: „Reconciliation OK — silent exit", state és IBKR egyező (6 ticker: ACHC, JAZZ, NNN, NSA, TKR, VNO) — **15/15 éles silent OK**
- ⚠️ `pt_eod` 22:11:03: **„Trades: 0"** miközben 1 valódi fill volt (FFIV MOC) — a `Trades: N` alulszámlálás ismétlődése (06-10 §5.4, 06-11 BEN). A `P&L $-152.22`, `Cumulative +$1,582.80 [Day 20/63]` sorok **helyesek**. `Still 6 open positions!` warning ismét (kozmetikai, 06-09 §5.5)
- ✓ Cron-időzítések teljes sor: intraday 14:30:00–14:32:50; close 15:30:02; submit 15:31:01; FFIV MOC submit 21:40:07; monitor 22:00:08; metrics 22:10:01; eod 22:11:01; reconcile 22:15:02 — mind a 8 log jelen (sync a 22:16 utáni protokoll szerint)
- ⚠️ Cron log: **3× UW HTTP 429** (SOLS, IVZ, ELS `darkpool`, attempt 3/3) — folytatódó sorozat: 06-11 2×, 06-12 4×, 06-15 3×; §6.3
- ⚠️ Cron `BEALLITASOK` blokk továbbra is legacy display (0,7%/$700, Max per sector 2, flow=0,60), miközben a sized risk $342–349/pozíció (0,35% swing) — 06-11 §6.2 / 06-12 §6.2 ismétlődés, P3 nyitva
- ✓ `exit_type` (FFIV TIME_STOP_MOC) egyezik a kanonikus `pending_exits`-szel — ma nincs exit_type-bug
- ✓ `daily_metrics` vs broker-ledger: FFIV realized -$152,22 broker_realized_pnl-ből (`record_pending_exits`), egyező

## 6. Anomáliák (csak új/változott)
- **6.1 P2 (nyitva, Day 63-input)** — scoring_validation.py legacy-swing pooling + belső inkonzisztencia (06-12 §6.1). Ma nem futott újra; a swing-only újrafuttatás Dev-chat tételként nyitva. Nincs változás.
- **6.2 P3 (ismétlődő)** — `cumulative_pnl::trading_days=19` vs `day_number=20`: 2026-06-01 sor hiányzik. Gazda: CC-task.
- **6.3 P3 megfigyelés** — UW HTTP 429 sorozat: 06-11 2×, 06-12 4×, 06-15 3× (mind `darkpool` v. `greek-exposure`, mind attempt 3/3, mind nem-CRITICAL endpoint). 3 review-napos átlag ~3/nap. `hipotézis:` rate-limit közeli batch a Phase 4/5-ben — ha 5+/nap vagy CRITICAL endpoint → P2 CC-task. UW shadow-only → P&L-hatás nincs. Gazda: megfigyelés.
- **6.4 P2 (nyitva → részben elévült)** — a 06-11 reggeli -$55,91 Net Liq-delta és a 06-12 esti nem-verifikált Net Liq feloldása a hétfő reggeli summary-re volt tervezve, de a technikai kiesés miatt a review csak 06-16 intraday-ben készül, amikor a summary már a mai napot tükrözi. A két szál **tisztán nem zárható retroaktívan**. Tanulság: a Net Liq-snapshotot a kereskedési nap zárását követő, de a következő nyitás (15:30 CEST) előtti ablakban kell rögzíteni. Gazda: folyamat (review-időzítés).
- **6.5 ÚJ P3 megfigyelés** — entry-referencia eltérés: `daily_metrics::FFIV::entry=408,87` (broker-avg) vs `swing_positions/pending_exits::entry_price=408,66` (planned). A realized broker-avg alapú (helyes), de a két mező eltérése a self-reentry render-bugon túl egy általánosabb planned-vs-broker entry-tárolási kérdés. Gazda: megfigyelés.
- Nincs új P0/P1.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés nélkül)
- **TIME_STOP kimenetek**: n=3 — BEN 06-11 +$159,92 (poz.), [korábbi poz.], **FFIV 06-15 -$152,22 (első negatív)**. A TIME_STOP nem irány-szelektív (a max-hold lejár, MOC zár), így a kimenet a tartás alatti drift függvénye — megfigyelés
- **Notional-kúszás**: 29,72% (06-12) → 34,51% (06-15); a max_concurrent 12 mellett a tényleges 6-7 pozíció, de a per-pozíció notional nőtt — megfigyelés, ha 50%+ közelít → figyelendő
- **Real Estate koncentráció**: 3 név (NSA+VNO+NNN) = 22,79% notional, a deploy óta a legmagasabb megfigyelt egy-szektor érték; 30% cap alatt — n=1 erre a 3-RE-név állapotra
- **Next-day MKT fill eltérés**: FFIV nem MKT-entry hanem TIME_STOP-exit, nem ide tartozik; n marad 6, átlag -1,19%
- **Self-reentry**: n marad 2 (VNO, NSA); ma az exit (FFIV) TIME_STOP volt, nem TP2 → nincs self-reentry-jelölt
- **Zero-fill / race-guard skip**: 06-12 után ma a guard 2 tickert skippelt (VNO, JAZZ), de 1 valódi entry (NNN) volt — nem tiszta skip-nap
- **TP-hit ráta**: változatlan 12/20 exit (60,0%); pozitív-exit 16/20 (80,0%) — az FFIV negatív TIME_STOP rontotta mindkettőt (06-12: 12/19 63,2% / 16/19 84,2%)

## 8. Heti kontextus — W25 D1
A W25 a Phase 3 (re-deploy + new paper) ablak első hete a project-instrukció szerint; a „new paper Day 1 ≈jún 23" még nem itt van. Hétfő net -$152,22, az első negatív nap a 06-08 óta tartó sorozat után (06-08…06-11 mind pozitív, 06-12 flat). Heti zárás majd péntek (06-19).

## 9. Holnap (2026-06-16, W25 D2) — MEGJEGYZÉS: a mai kereskedés a review írásakor MÁR FUT (17:16 CEST)
- **Várt exit: 1** — TKR TIME_STOP, `next_action_at` 2026-06-15T20:00:07Z, `next_day_planned::time_stops_at_2140: ["TKR_TIME_STOP"]`. TKR days_held=5 (=max_hold), tp1_hit=true, qty_remaining=20, trail $134,685, entry $131,83 → `hipotézis:` a 20 qty maradékon a trail-szint felett pozitív realized várható (feltevés: MOC a trail közelében; ellentétben az FFIV-vel, a TKR már TP1-et ütött és nyereségben áll)
- Fókusz a holnapi (06-16) review-ban: (1) TKR TIME_STOP realized; (2) a notional-kúszás és RE-koncentráció iránya; (3) a 06-16 intraday már látott új entryk (EXEL, CORT a `swing_positions`-ben, entry_date 2026-06-16) — ezek a 06-16 nap tételei, a holnapi review tárgya, itt csak jelzem hogy a mai szubmisszió megtörtént
- **Net Liq-rögzítés**: a 06-16 záró summary-t a 22:16 CEST utáni, de 06-17 15:30 előtti ablakban kell rögzíteni (§6.4 tanulság)

## 10. Freeze-sor
Paraméter-érintő változás ma: **nincs**.

## 11. A nap egy mondatban
Az FFIV TIME_STOP a deploy óta első negatív idő-stopként -$152,22-t realizált (a 06-12-i becslés iránya helyes), egy új Real Estate entry (NNN) lépett be a race guard két skipje mellett, a cumulative +$1 582,80-ra csökkent, és a könyv notionalja 34,51%-ra kúszott három Real Estate névvel (22,79%).
