# IFDS Daily Review — 2026-06-16 (kedd, Day 21/63 NYSE-count, W25 D2)

## 1. Fejléc
- **Day 21/63** (NYSE-count, `daily_metrics::day_number`, `pt_eod` render egyező; megj.: `cumulative_pnl::trading_days=20` — a 2026-06-01 hiányzó sor miatti -1 eltolás fennáll, §6.2)
- **Realized net: +$134,03** (gross +$135,09; commission $1,06) — egyetlen exit (TKR TIME_STOP_MOC). Forrás: `daily_metrics/2026-06-16.json::pnl`, `pending_exits/2026-06-16.json`, `pt_daily_metrics` broker-ledger fetch (`record_pending_exits: matched=1`)
- **Cumulative: +$1 716,83 (+1,72%)** — `cumulative_pnl.json` (1582,80 + 134,03)
- **Net Liq (IBKR `get_account_summary`, tiszta 06-16 close ablak): $101 231,77** ✓ verifikált — gross_position_value $41 132,08, leverage 0,41. Ez az első tiszta Net Liq-olvasat a 06-11 reggel óta; **új horgony** a további delta-méréshez (§6.4)
- **Excess: +0,73%** (portfolio +0,14% vs SPY -0,60%, `daily_metrics::excess_return`) — ⚠️ realized-alapú szemantika (#6 fix inaktív): a +0,14% csak a TKR realizált nyereségét méri; SPY-lefelé napon ez **felfelé túlozza a felülteljesítést** (a nyitott könyv MTM-je aznap esett — lásd §4 unrealized). A 06-15 tükörképe: a szemantika mindkét irányba torzít
- **Nyitott pozíciók: 7** (TKR kilépett, EXEL+CORT belépett; IBKR `get_account_positions` és `swing_positions.json` és `pt_reconcile` 22:15 mind egyező)

## 2. Exits (1) — forrás: `pending_exits/2026-06-16.json` + broker-ledger
| Idő (CEST) | Ticker | Típus | Qty | Entry→Exit | Broker realized | Várt (06-15 review §9) | Eltérés |
|---|---|---|---|---|---|---|---|
| 21:59:31 | TKR | **TIME_STOP_MOC** | 20 | $133,79→$140,49 | **+$134,03** (+5,01%) | pozitív (feltevés: trail közelében, tp1_hit, nyereségben) | irány helyes, +5,01% |

A 06-15 review előrejelezte: az FFIV-vel ellentétben a TKR pozitív lesz (már TP1-et ütött, nyereségben állt) — **megerősítve, +$134,03**. Az `exit_type` helyes (`TIME_STOP_MOC`). Megj.: entry-referencia $133,79 (broker-avg, a 20 maradék qty-ra) vs `swing_positions::entry_price=131,83` (eredeti) — a 06-15 §6.5 planned-vs-broker entry-tárolási kérdés ismétlődése, a realized broker-avg alapú (helyes).

## 3. Entries (2) — forrás: `pt_submit_2026-06-16.log`, `daily_metrics::execution`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 | entry_score |
|---|---|---|---|---|---|---|
| EXEL | Healthcare | 110 | $53,00→$53,50 | +0,94% ⚠️ | $49,83 / $55,37 / $57,75 | 80,28 (S_j 80,3) |
| CORT | Healthcare | 47 | $83,12→$83,95 | +1,00% ⚠️ | $75,73 / $88,66 / $94,20 | 78,07 (S_j 78,1) |

Mindkét entry Healthcare; avg slippage +0,96% (vs 06-15 NNN +0,02%). A pipeline 3 tickert sized (VNO 94,8 / EXEL 80,3 / CORT 78,1), VNO már nyitott → skip; EXEL+CORT belépett. **A könyv mostantól csak 2 szektor**: 4 Healthcare (ACHC, JAZZ, EXEL, CORT) + 3 Real Estate (VNO, NSA, NNN) — §7.

## 4. Nyitott pozíciók (7) — forrás: IBKR `get_account_positions` (06-16 close, verifikált) + `swing_positions.json`
| Ticker | days_held | Mark | Unrealized (IBKR) | next_action |
|---|---|---|---|---|
| JAZZ | 3 | $226,88 | **-$191,08** | HOLD |
| NSA | 3 | $44,69 | -$180,01 | HOLD |
| EXEL | 0 | $52,10 | -$155,00 | HOLD |
| VNO | 4 | $37,82 | -$153,00 | HOLD |
| NNN | 1 | $46,16 | -$92,56 | HOLD |
| ACHC | 5 | $24,99 | -$72,91 | **TIME_STOP** (06-17, §9) |
| CORT | 0 | $83,71 | -$12,28 | HOLD |
| **Total unrealized** | | | **-$856,84** | |

A teljes nyitott könyv -$856,84 unrealized húzáson (a 06-12-i -$547 és a 06-15-i nem-mért szint után tovább mélyült). JAZZ a legmélyebb (-$191), a 06-11-i +2,25%-os slippature-es entry tovább korrigál. **Net Liq-rekonciliáció (megfigyelés, §6.5)**: $100 000 + $1 716,83 realized − $856,84 unrealized = $100 859,99 várt vs tény Net Liq $101 231,77 → **+$371,78 reziduum** — a memóriában rögzített Net Liq-delta-anomália mintázatába illik; rögzítve, nem hajszolom.

**Notional: $41 609,86 (41,61% equity)** — folytatódó kúszás: 29,72% (06-12) → 34,51% (06-15) → 41,61% (06-16). Healthcare $18 817,88 (18,82%), Real Estate $22 791,98 (22,79%); observed max 22,79% a 30% cap alatt. §7.

## 5. Ops-checklist
- ✓ `pt_reconcile` 22:15:06: „Reconciliation OK — silent exit", state és IBKR egyező (7 ticker) — **16/16 éles silent OK**
- ✓ IBKR `get_account_positions` vs `swing_positions.json`: 7 ticker, qty mind egyező (ACHC 141, CORT 47, EXEL 110, JAZZ 24, NNN 208, NSA 153, VNO 160)
- ⚠️ `pt_eod` 22:11:04: **„Trades: 0"** miközben 1 valódi fill volt (TKR MOC) — `Trades: N` alulszámlálás ismétlődése (06-10/06-11/06-15). `P&L $+134.03`, `Cumulative +$1,716.83 [Day 21/63]` helyes. `Still 7 open positions!` warning (kozmetikai)
- ✓ Cron-időzítések teljes sor: intraday 14:30:00–14:32:30; close 15:30:02; submit 15:31:01; TKR MOC submit 21:40:06; monitor 22:00:10; metrics 22:10:01; eod 22:11:02; reconcile 22:15:02 — mind a 8 log jelen
- 🔴 Cron log: **12× UW HTTP 429** — 2× darkpool (HUN, UA, Phase 0) + **10× greek-exposure/strike** (NNN, VNO, EXEL, CORT, JAZZ, ACHC, SJM, TKR, HUM, REG, Phase 4/5). Jelentős eszkaláció: 06-11 2× → 06-12 4× → 06-15 3× → **06-16 12×**. §6.3 — **P2-re emelve**
- ⚠️ Cron `BEALLITASOK` blokk legacy display (0,7%/$700, Max per sector 2, flow=0,60) — ismétlődő P3
- ⚠️ Cron Phase 6: **„Excluded — sector limit: 1"** — első megfigyelt szektor-limit kizárás a sizing-ban; §6.6
- ✓ `exit_type` (TKR TIME_STOP_MOC) egyezik a kanonikus `pending_exits`-szel

## 6. Anomáliák (csak új/változott)
- **6.1 P2 (nyitva, Day 63-input)** — scoring_validation.py legacy-swing pooling (06-12 §6.1). Ma nem futott. Nincs változás.
- **6.2 P3 (ismétlődő)** — `trading_days=20` vs `day_number=21`: 2026-06-01 sor hiányzik. Gazda: CC-task.
- **6.3 P2 (EMELVE P3→P2)** — UW HTTP 429 ma 12× (2 darkpool + 10 greek-exposure), a 4 review-napos sorozat (2/4/3/12) éles emelkedése, és **most a greek-exposure/strike endpointot éri**, ami a Phase 5 GEX-input forrása (nem csak a shadow darkpool). `hipotézis:` a Phase 4→5 batch egyszerre tüzel sok greek-exposure hívást rate-limit fölött; a GEX fallback Polygon-options-ra megy (Phase 5 mégis 37→32 passed), így a sizing nem állt le, de a GEX-regime minőség romolhat. Gazda: CC-task — UW hívás-throttling/retry-backoff a Phase 4/5-ben, vagy a greek-exposure batch ütemezése. **Megj.: az UW deaktivált a scoringban (PCR+OTM-inverse only), de a GEX-regime a sizing M_gex-éhez kell** — verifikálni, hogy a 429-ek M_gex-fallbackot triggerelnek-e (a cron mind M_gex=1,000-et mutat ma, ami a positive-regime default).
- **6.4 P2 (új horgony)** — a Net Liq tiszta olvasata megvan (06-16 close $101 231,77). A 06-11/06-12-i régi szálak retroaktívan zárhatatlanok, de innen a delta-mérés folytatható. Gazda: megfigyelés (06-17 close summary vs ez).
- **6.5 P3 (ismétlődő)** — planned-vs-broker entry-tárolás: TKR `daily_metrics::entry=133,79` vs `swing::entry_price=131,83` (06-15 §6.5). Gazda: megfigyelés.
- **6.6 ÚJ P3 megfigyelés** — Phase 6 „sector limit: 1" kizárás (első eset). A `BEALLITASOK` legacy „Max per sector 2"-t mutat, miközben 4 Healthcare pozíció nyitva van → a tényleges kizárási szabály a 30% notional-cap (vagy a swing sector-logika), nem a 2/sector. `hipotézis:` a sizing helyesen a notional-capet alkalmazza, a kizárt 1 ticker a 30% közeli szektorba esett — verifikálni, hogy melyik szabály tüzelt. Gazda: megfigyelés / CC-verifikáció a §6.2-vel együtt (futó config audit).
- Nincs új P0/P1.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés nélkül)
- **TIME_STOP kimenetek**: n=4 — BEN 06-11 +$159,92, [korábbi poz.], FFIV 06-15 -$152,22, **TKR 06-16 +$134,03**. A kimenet a tartás alatti drift függvénye; a tp1_hit-es TKR pozitív, a tp1-et nem ütött FFIV negatív volt — megfigyelés (nem következtetés: n túl kicsi)
- **Notional-kúszás**: 29,72% → 34,51% → **41,61%** (3 egymást követő nap emelkedés); max_concurrent 12, tényleges 7 pozíció. Ha a tendencia folytatódik, a per-pozíció sizing × pozíciószám közelíthet a magasabb kitettséghez — megfigyelendő, ítélet nélkül
- **Szektor-koncentráció**: a könyv **csak 2 szektor** (4 Healthcare + 3 Real Estate); egyik sem lépi a 30% capet (HC 18,82%, RE 22,79%), de szektor-szintű diverzifikáció nincs a két csoporton túl — n=1 erre az állapotra
- **Entry-slippage**: EXEL +0,94%, CORT +1,00% (mindkettő emelt); a deploy-sorozat szórása nagy (06-15 NNN +0,02% … 06-11 JAZZ +2,25%)
- **TP-hit ráta**: 12/21 exit (57,1%); pozitív-exit 17/21 (81,0%) — a TKR pozitív TIME_STOP javította a pozitív-exit rátát (06-15: 16/20 80,0%)
- **Self-reentry**: n marad 2 (a TKR exit TIME_STOP, nem TP2 → nincs új jelölt)

## 8. Heti kontextus — W25 D2
Kedd net +$134,03, a hétfői -$152,22 után a héten kumulatív -$18,19 (2 nap). A W25 a Phase 3 ablak; heti zárás péntek (06-19).

## 9. Holnap (2026-06-17, W25 D3)
- **Várt exit: 1** — ACHC TIME_STOP, `next_action_at` 2026-06-16T20:00:09Z, `next_day_planned::time_stops_at_2140: ["ACHC_TIME_STOP"]`. ACHC days_held=5 (=max_hold), tp1_hit=false, qty 141, entry $25,32, 06-16 close mark $24,99 → `hipotézis:` enyhén negatív vagy közel nulla realized (feltevés: MOC a mostani mark körül; 141 × ($24,99−$25,32) ≈ −$47, a tp1_hit=false miatt inkább az FFIV-mintához hasonló, de kisebb nagyságrend). Ez lenne a hét 3. TIME_STOP-ja (FFIV neg, TKR poz, ACHC ?)
- Fókusz a holnapi review-ban: (1) ACHC TIME_STOP realized; (2) UW 429 §6.3 — verifikálni az M_gex-fallback hatást; (3) Net Liq 06-17 close vs $101 231,77 (§6.4 új horgony); (4) notional-kúszás iránya; (5) a nyitott könyv -$856 unrealized húzásának iránya egy SPY-lefelé nap után
- **Net Liq-rögzítés**: 06-17 close summary a 22:16 CEST utáni, 06-18 15:30 előtti ablakban

## 10. Freeze-sor
Paraméter-érintő változás ma: **nincs**.

## 11. A nap egy mondatban
A TKR TIME_STOP +$134,03-at realizált (+5,01%, a 06-15-i pozitív-prognózis megerősítve), két új Healthcare entry (EXEL, CORT) lépett be emelt slippage-dzsel, a cumulative +$1 716,83-ra állt vissza, de a könyv -$856,84 unrealized húzásra mélyült, a notional 41,61%-ra kúszott és csak 2 szektorra koncentrálódott — miközben az UW 429-hibák 12-re ugrottak és most a GEX-input greek-exposure endpointot érik.
