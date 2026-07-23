# IFDS Daily Review — 2026-06-12 (péntek, Day 19/63 NYSE-count, W24 D5)

## 1. Fejléc
- **Day 19/63** (NYSE-count, `daily_metrics::day_number`, `pt_eod` render egyező; megj.: `cumulative_pnl::trading_days=18` — a 2026-06-01 hiányzó sor miatti -1 eltolás fennáll, §6.2)
- **Realized net: +$0,00** — nulla-fill nap (0 entry, 0 exit). Forrás: `daily_metrics/2026-06-12.json`, `pt_eod` „No fills today", `pt_daily_metrics` „created zero entry for no-exit day"
- **Cumulative: +$1 735,02 (+1,74%)** — változatlan, `cumulative_pnl.json`
- **Net Liq: nem verifikálva** ⚠️ — az IBKR `get_account_summary` ebben a menetben 4× hibázott (MCP-oldali „An error occurred"); a §6.4 Net Liq-delta visszamérés a következő sikeres summary-ig nyitva marad
- **Excess: -0,54%** (portfolio +0,00% vs SPY +0,54%, `daily_metrics::excess_return`) — nulla-fill napon a portfolio-realized definíció szerint 0, így az excess a teljes SPY-mozgás negáltja; ez nem a nyitott pozíciók napi MTM-mozgását méri (lásd lent az unrealized-deltát)
- **Nyitott pozíciók: 6** (IBKR `get_account_positions` és `swing_positions.json` egyező)

## 2. Exits (0)
Nincs exit. `pt_close` 15:30:01: „No EOD action flags set"; 21:40:03: „No TIME_STOP flags". A 06-11 review §8 várt 0 exitet — **tény 0, egyezik**.

## 3. Entries (0)
Nincs új entry. `pt_submit` 15:31:06: a pipeline 3 tickert sized (NSA, JAZZ, ACHC), de mind a 3 **már nyitott pozíció** → race guard skip, „Submitted: 0 tickers — state file untouched". `daily_metrics::positions::opened=0`, `selected_for_entry=0`. A `swing_score_distribution` top-3 (NSA 104,1 / VNO 97,3 / JAZZ 90,1) mind már a könyvben lévő ticker — új belépő nem volt a küszöb felett, amely ne lett volna már nyitva.

## 4. Nyitott pozíciók (6) — forrás: `swing_positions.json` + IBKR positions (mark, unrealized)
| Ticker | days_held | Mark (IBKR) | Unrealized (IBKR) | napi MTM Δ (IBKR daily_pnl) | Stop-buffer | next_action |
|---|---|---|---|---|---|---|
| FFIV | 5 | $397,00 | -$141,28 | +$37,92 | 4,0% (stop $381,52) | **TIME_STOP** (holnap, §5) |
| ACHC | 3 | $24,50 | -$142,00 | -$54,99 | 7,3% (stop $22,84) | HOLD |
| JAZZ | 1 | $229,00 | -$140,20 | -$172,08 ⚠️ | 6,4% (stop $221,64*) | HOLD |
| NSA | 1 | $45,15 | -$109,63 | -$55,08 | 3,8% (stop $43,48) ⚠️ | HOLD |
| TKR | 4 | $137,06 | +$66,49 | -$6,80 | 3,4% (trail $132,55) ⚠️ | HOLD |
| VNO | 2 | $38,27 | -$81,00 | -$112,00 | 5,5% (stop $36,27) | HOLD |
| **Total unrealized** | | | **-$547,62** | **napi MTM Δ ≈ -$363** | | |

*JAZZ stop: a `swing_positions.json` $215,33-at tárol (entry-kori), a cron a 06-12 sizing-ban $221,64-et számolt — a stop-szint forrása a futó state, a 215,33 a kanonikus. A 4 nap alatti unrealized -$547,62 a Day 18 záró -$179,07-ról mélyült (a +$335 realized nap után a nyitott könyv visszahúzott). Notional/sector változatlan (29,72%, RE 13,1%) — nem volt mozgás.

JAZZ napi -$172,08 MTM a legnagyobb egynapos húzás a könyvben (a 06-11-i +2,25% slippature-es entry után), `hipotézis:` a belépési ár-prémium korrekciója — megfigyelés, nem akció.

## 5. Ops-checklist
- ✓ `pt_reconcile` 22:15:06: „Reconciliation OK — silent exit" — **14/14 éles silent OK** (a számláló lép, tegnap 13/13)
- ✓ `pt_eod` 22:11:03: nulla-fill napon a render helyes (`No fills today`, `P&L $+0.00`, `Cumulative +$1,735.02 [Day 19/63]`) — **a self-reentry/Trades-render bug ma nem jelentkezett, mert nem volt fill**; ez nem fix, csak nem-kiváltott állapot. A `Still 6 open positions!` warning ismét megjelent (06-09 §5.5, kozmetikai)
- ✓ Cron-időzítések teljes sor: intraday 14:30:00–14:32:44; close 15:30:01; submit 15:31:01; close 21:40:03; monitor 22:00:09; metrics 22:10:02; eod 22:11:01; reconcile 22:15:02 — sync a 22:16 utáni protokoll szerint, mind a 8 log jelen
- ⚠️ Cron log: **4× UW HTTP 429** (ESI, FLS, CUBE, AAL `darkpool`, attempt 3/3) — tegnap 2× volt (greek-exposure), ma 4× (darkpool); §6.3
- ⚠️ Cron `BEALLITASOK` blokk továbbra is legacy display (0,7%/$700, Max per sector 2, flow=0,60) — 06-11 §6.2 ismétlődés, P3 nyitva
- ✓ `daily_metrics` vs IBKR positions: ticker-lista és qty egyező

## 6. Anomáliák (csak új/változott)
- **6.1 ÚJ P2 — scoring_validation.py belső inkonzisztencia + legacy-swing pooling [Day 63-input]** — a `docs/analysis/scoring-validation.md` fejléce „18 trading days | 456 trades", a Summary „456 trades over 69 trading days". A 456 trade, a 0–142,5 score-tartomány és a LOSS_EXIT/NUKE/SL exit-típusok (a swing rendszerben nem létezők) azt jelzik, hogy a riport a **legacy intraday (63 nap) és a swing (19 nap) adatot összevonja**. Következmény: az §5 „Evidence of alpha" záró-állítás (score vs excess Pearson -0,158**) **kevert mintán** áll, és nem a swing-rendszer izolált jel-érvényességi mérése. v6 szerint Day 63 előtt jel-érvényességi ítélet nincs — ezt a script-állítást **nem fogadom el és nem cáfolom**, csak rögzítem mint Day 63-input metodikai kérdést. Gazda: Dev chat (a scoring_validation scope-jának tisztázása: swing-only szűrés vs pooled). Javaslat: a 4. szekció „267/456 enriched" + a -0,124* tech-korreláció szintén kevert — külön swing-only futás kell a Day 63 edge-audithoz (`docs/foundational/strategic-review/2026-06-10-edge-audit.md` attribution-terv inputja).
- **6.2 P3 (ismétlődő)** — `cumulative_pnl::trading_days=18` vs `day_number=19`: a `daily_history`-ből a 2026-06-01 sor hiányzik (06-11 §6.4). Gazda: CC-task.
- **6.3 P3 megfigyelés** — UW HTTP 429 ráta nő: 06-11 2× (greek-exposure), 06-12 4× (darkpool). `hipotézis:` rate-limit közeli állapot a Phase 4/5 batch-ben — gazda: megfigyelés, ha 5+/nap vagy CRITICAL endpointot érint → P2 CC-task. Megj.: az UW shadow-only, a scoringot nem érinti (deaktivált), így P&L-hatás nincs.
- **6.4 P2 (nyitva, ismétlődő)** — Net Liq-delta visszamérés: a 06-11 reggeli -$55,91 (snapshot vs Day 17 záró) feloldása a mai summary-vel volt tervezve, de a `get_account_summary` ma nem elérhető (MCP-hiba). Átviszem a következő sikeres summary-ig. Gazda: megfigyelés.
- Nincs új P0/P1.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés nélkül)
- **Zero-fill napok**: a W24-ben 1/5 (ma); a deploy óta a 2026-05-26 és 05-29 (0 trade) után a 3. tiszta nulla-fill nap, de ez az első, amikor **6 pozíció nyitva volt és mégis 0 entry** (race guard skip, nem üres univerzum) — n=1 erre az altípusra
- **Next-day MKT fill eltérés**: ma nincs fill, n marad 6, átlag -1,19%
- **Self-reentry**: n marad 2 (VNO, NSA); ma a race guard mindhárom ismételt jelöltet (NSA, JAZZ, ACHC) helyesen skippelte → a self-reentry **csak exit-napon** keletkezik (06-10 VNO, 06-11 NSA mindkettő TP-exit utáni újranyitás), tiszta hold-napon a guard fog — megfigyelés
- **TP-hit ráta**: változatlan 12/19 exit (63,2%); pozitív-exit 16/19 (84,2%) — ma nem volt exit
- **Daily-eval fordulatok**: 8/10, ma az FFIV TIME_STOP-flag az 5. napon a vártnak megfelelő (days_held=5 = max_hold), nem fordulat

## 8. Heti zárás — W24 (jún 08–12), forrás: `docs/analysis/weekly/2026-W24.md` + `cumulative_pnl`
- **Heti net: +$1 489,77** (gross +$1 499,65, commission -$9,88) — a deploy óta a **legerősebb hét** a daily_history alapján (W23 ~ +$954, jún 02–05 négy nap; W24 öt nap); szuperlatívusz-mentesen: a rögzített heti net-ek közül a legmagasabb, n=4 teljes hét
- **Heti excess: +0,90%** (portfolio +1,50% vs SPY +0,60%) — pozitív, a 2. pozitív-excess hét (W21/W22/W23 vegyes)
- **Win-napok: 4/5** (péntek flat)
- **Exit-mix (heti)**: TP1 ×3, TP2 ×2, MOC ×4 — 0 SL, 0 LOSS_EXIT a héten
- **TP1 teljesítmény**: 5/6 hit (83%), avg +$192,29; az „R:R realized 1:0.00" mező a weekly_metrics-ben **gyanús/hibás** ⚠️ — `hipotézis:` a script R:R-számítása nulla nevezővel vagy hiányzó SL-referenciával fut (a héten 0 SL volt), gazda: CC-task (weekly_metrics R:R mező audit)
- **Slippage (heti)**: avg MKT +0,68%, worst +2,25% (JAZZ 06-11)
- **Dinamikus küszöb**: zero-position 1/5, low-position (<3) 4/5 — a rendszer a héten konzisztensen kevés, koncentrált belépőt adott
- **Scoring Quality avg score 0,0**: a weekly_metrics az entry_score=0,0 tárolt mezőből számol (a legtöbb pozíció entry_score-ja 0,0 a state-ben, csak NSA/JAZZ kapott 100,71/87,44-et) — a „Score→P&L correlation: n/a" ezért, nem mérési hiba; megfigyelés, hogy az entry_score perzisztálása hiányos (06-xx-en már látott pattern: a régebbi entry-k 0,0-val maradtak)

## 9. Holnap/hétfő (2026-06-15, W25 D1)
- **Várt exit: 1** — FFIV TIME_STOP, `next_action_at` 2026-06-12T20:00:08Z flag, `next_day_planned::time_stops_at_2140: ["FFIV_TIME_STOP"]`. FFIV days_held=5 (=max_hold), entry $408,66, mai mark $397,00 → `hipotézis:` ha a hétfői MOC a mostani szint körül, a 12 qty-n ≈ -$140 realized (feltevés: mark nem mozdul lényegesen; a TIME_STOP MOC-on zár, nem áron). Ez lenne a deploy óta az **első negatív TIME_STOP** (a korábbi 2 — BEN 06-11, és a 06-xx — pozitív volt)
- Fókusz: (1) FFIV TIME_STOP realized; (2) §6.4 Net Liq-delta a hétfő reggeli summary-vel (két nyitott szál: -$55,91 + a péntek esti nem-verifikált); (3) JAZZ/NSA/VNO unrealized — a könyv -$547 húzáson áll, hétfői MTM-irány; (4) §6.1 scoring_validation swing-only újrafuttatás mint Day 63-input
- W25 a Phase 3 (re-deploy + new paper) ablak első hete a project-instrukció szerint — megj.: a swing pivot „new paper Day 1 ≈jún 23" még nem itt van, W25 a felvezetés

## 10. Freeze-sor
Paraméter-érintő változás ma: **nincs**. A §6.1 scoring_validation pooling kérdés **Day 63-input** címkével rögzítve, nem freeze-sértő (read-only analízis).

## 11. A nap egy mondatban
Tiszta nulla-fill péntek (a race guard mindhárom ismételt jelöltet skippelte), a cumulative +$1 735,02-n állt, a W24 +$1 489,77 net / +0,90% excess a deploy óta rögzített legerősebb hét, miközben a nyitott könyv -$547 unrealized húzásba ment és hétfőre az FFIV TIME_STOP (várhatóan első negatív idő-stop) esedékes.
