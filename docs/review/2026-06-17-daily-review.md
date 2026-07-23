# IFDS Daily Review — 2026-06-17 (szerda, Day 22/63 NYSE-count, W25 D3)

## 1. Fejléc
- **Day 22/63** — `daily_metrics::day_number=22` ÉS `cumulative_pnl::trading_days=22` **egyező** ✓ — a backfill-fix (`4f75455`) bevált: a 2026-06-01 zero-sor jelen (22 sor a daily_history-ben), az off-by-one megszűnt. §6.2 **LEZÁRVA**. Megj.: a Juneteenth-üzenet „06-18 = Day 22"-je off-by-one volt; az autoritatív NYSE-count szerint **06-17 = Day 22 → 06-18 = Day 23 → (06-19 Juneteenth skip) → 06-22 = Day 24**
- **Realized net: -$271,41** (gross -$270,31; commission $1,10) — egyetlen exit (ACHC TIME_STOP_MOC). Forrás: `daily_metrics/2026-06-17.json`, `pending_exits`, `pt_daily_metrics` broker-ledger (`matched=1`)
- **Cumulative: +$1 445,42 (+1,45%)** — `cumulative_pnl.json` (1716,83 − 271,41). A 06-11-i csúcs (+$1 735,02) óta -$289,60 (W25 három napja: -152,22 / +134,03 / -271,41)
- **Net Liq (IBKR, tiszta 06-17 close ablak): $100 252,50** ✓ verifikált — a 06-16 horgonyról ($101 231,77) **-$979,27** egy risk-off napon (SPY -1,25%, VIX 18,73 +14,14%)
- **Excess: +0,98%** (portfolio -0,27% vs SPY -1,25%, `daily_metrics`) — ⚠️ realized-alapú szemantika (#6 inaktív): SPY-lefelé napon a kis realizált veszteség pozitív excesst ad, miközben a nyitott könyv MTM-je -$711-et esett (§4); a +0,98% **felfelé túlozza a felülteljesítést**
- **Nyitott pozíciók: 7** (ACHC kilépett, SJM belépett; IBKR + `swing_positions` + `pt_reconcile` mind egyező)

## 2. Exits (1) — forrás: `pending_exits/2026-06-17.json` + broker-ledger
| Idő (CEST) | Ticker | Típus | Qty | Entry→Exit | Broker realized | Várt (06-16 review §9) | Eltérés |
|---|---|---|---|---|---|---|---|
| 21:59:41 | ACHC | **TIME_STOP_MOC** | 141 | $25,51→$23,59 | **-$271,41** (-7,55%) | ≈ -$47 (feltevés: mark ~$24,99 static) | **-$224 a becslés alatt** ⚠️ |

**Becslési hiba őszinte rögzítése**: a 06-16 review iránya helyes volt (negatív, mert tp1_hit=false, FFIV-minta), de a nagyságrend súlyosan elvétett. Ok: a becslés a 06-16 close markot ($24,99) statikusnak feltételezte; valójában az ACHC a 06-17 risk-off napon $23,59-ig esett (-5,6% intraday a pozícióban). A TIME_STOP MOC-on zár, nem áron — egy lefelé napon ez a teljes napi esést elnyeli. **Ez a swing-éra legnagyobb egynapi vesztesége** (-$271,41), és a 2. negatív TIME_STOP. `exit_type` helyes (`TIME_STOP_MOC`).

## 3. Entries (1) — forrás: `pt_submit_2026-06-17.log`, `daily_metrics::execution`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 | entry_score |
|---|---|---|---|---|---|---|
| SJM | **Consumer Defensive** | 49 | $115,99→$115,72 | **-0,23% (kedvező)** | $108,94 / $121,28 / $126,56 | 77,41 (S_j 77,4) |

SJM az **első Consumer Defensive név** — a könyv visszatért 3 szektorra (a 06-16-i 2-szektor koncentráció után). Negatív (kedvező) slippage: a fill a planned alatt. A pipeline 3-at sized (NNN 89,1 / EXEL 82,8 / SJM 77,4), de NNN+EXEL már nyitott → csak SJM lépett be.

## 4. Nyitott pozíciók (7) — forrás: IBKR `get_account_positions` (06-17 close, verifikált)
| Ticker | days_held | Mark | Unrealized (IBKR) | next_action |
|---|---|---|---|---|
| VNO | 5 | $36,46 | **-$370,60** | **TIME_STOP** (06-18, §9) — mark a $36,27 stop felett 0,5% |
| NSA | 4 | $43,63 | -$342,19 | HOLD |
| NNN | 2 | $45,13 | -$306,80 | HOLD |
| JAZZ | 4 | $226,93 | -$189,88 | HOLD |
| SJM | 0 | $112,96 | -$136,24 | HOLD |
| EXEL | 1 | $52,44 | -$117,60 | HOLD |
| CORT | 1 | $81,75 | -$104,40 | HOLD |
| **Total unrealized** | | | **-$1 567,71** | |

A nyitott könyv -$1 567,71-re mélyült (06-16: -$856,84, egynapi -$711 a risk-off napon). A 3 Real Estate név (VNO+NSA+NNN) együtt **-$1 019,59** — a húzás java. VNO holnap TIME_STOP, a stopja közvetlen közelében ($36,46 mark vs $36,27 stop).

**Net Liq-rekonciliáció (§6.4)**: $100 000 + $1 445,42 realized − $1 567,71 unrealized = $99 877,71 várt vs tény $100 252,50 → **+$374,79 reziduum**. Tegnap +$371,78 volt → a reziduum **stabil ~+$373** (±$3 két napon át), tehát **rendszeres számviteli offset, nem növekvő szivárgás** — ez részben megnyugtató a §6.4-re nézve.

## 5. Ops-checklist
- ✓ `pt_reconcile` 22:15:06: „Reconciliation OK", state és IBKR egyező (7 ticker) — **17/17 éles silent OK**
- ✓ **`pt_eod` fix verifikálva**: „Trades(eod-fills): 0 | persisted: 1" — a `03c77d8` bevált, a persisted (valós cross-client MOC) számot mutatja. A `P&L $-271.41`, `Cumulative +$1,445.42 [Day 22/63]` helyes. (A `Still 7 open positions!` warning kozmetikai, marad)
- ✓ IBKR positions vs `swing_positions`: 7 ticker, qty egyező (CORT 47, EXEL 110, JAZZ 24, NNN 208, NSA 153, SJM 49, VNO 160)
- ✓ Cron-időzítések teljes sor: intraday 14:30:01–14:32:23; close 15:30:02; submit 15:31:02; ACHC MOC submit 21:40:07; monitor 22:00:10; metrics 22:10:02; eod 22:11:02; reconcile 22:15:02 — mind a 8 log jelen
- ◽ Cron log: **29× UW HTTP 429** (mind greek-exposure/strike, attempt 3/3) — a sorozat tovább nő (06-16 12× → 29×), de a **verdikt lezárva** (Polygon-GEX fallback mind a 40 tickert fedi, 0 no-data, M_gex valid POSITIVE; throttling Day 63-ra halasztva). Higiéniai megfigyelés, **nem flagelem trading-kockázatként**
- ⚠️ Cron `BEALLITASOK` legacy display (0,7%/$700, Max per sector 2, flow=0,60) — ismétlődő P3, §6.3
- ◽ Phase 6 „sector limit: 1" kizárás (2. nap egymás után) — §6.3
- ✓ `exit_type` (ACHC TIME_STOP_MOC) egyezik a kanonikus `pending_exits`-szel

## 6. Anomáliák (csak új/változott)
- **6.1 P2 (nyitva, Day 63-input)** — scoring_validation.py legacy-swing pooling (06-12 §6.1). Nincs változás; Dev-chat tétel.
- **6.2 LEZÁRVA** — `trading_days` off-by-one: a backfill-fix (`4f75455`) élesítve, ma `trading_days=22=day_number`, 06-01 zero-sor jelen, cumulative 1445,42 helyes. A §5.4 safety net a recidiva ellen. Verifikáció kész.
- **6.3 P3 (ismétlődő)** — (a) `BEALLITASOK` legacy display; (b) Phase 6 sector-limit kizárás (06-16 §6.6 ismétlődése, ma is 1). Mindkettő display/sizing-audit tétel, gazda CC (futó config verifikáció). A sector-limit kizárás 2 napja konzisztens 1 — `hipotézis:` egy stabilan a notional-cap közelébe eső szektor (vélhetően Real Estate 22,79%, vagy a 4. Healthcare jelölt) — nem blokkoló.
- **6.4 P2→megfigyelés** — Net Liq-reziduum stabil ~+$373 (06-16: +$371,78, 06-17: +$374,79). A stabilitás arra utal, hogy **fix számviteli offset** (pl. a broker-avg entry-költség és a planned-entry közti rendszeres különbség, vagy egy nyitó jutalék-tétel), nem növekvő anomália. A 06-11-i régi -$55,91 szál ettől függetlenül zárhatatlan. Gazda: megfigyelés, ha a reziduum kilép a ±$10 sávból → CC-vizsgálat.
- **6.5 P3 (ismétlődő)** — planned-vs-broker entry-tárolás: ACHC `daily_metrics::entry=25,51` vs `swing::entry_price=25,32` (06-15/06-16 ismétlődés). `hipotézis:` ez a forrása a §6.4 stabil reziduumnak is — a két tétel **összefügghet**; ha a CC a §6.5-öt vizsgálja, a §6.4 offset is magyarázódhat. Gazda: megfigyelés.
- Nincs új P0/P1.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés nélkül)
- **TIME_STOP kimenetek**: n=4 — BEN 06-11 +$159,92, FFIV 06-15 -$152,22, TKR 06-16 +$134,03, **ACHC 06-17 -$271,41**. Fejlődő mintázat (n kicsi, nem következtetés): a **tp1_hit=true** exitek pozitívak (TKR), a **tp1_hit=false** exitek negatívak (FFIV, ACHC) — a holnapi VNO (tp1_hit=false) e mintázat tesztje
- **Notional-kúszás**: 29,72% → 34,51% → 41,61% → **43,72%** (4 nap emelkedés); 7 pozíció, max_concurrent 12
- **Nyitott könyv unrealized**: -$179 (06-12) → -$547 → [06-15 nem mért] → -$856,84 (06-16) → **-$1 567,71 (06-17)** — egyértelmű mélyülés a risk-off fordulón
- **Szektor-koncentráció**: 3 szektor (RE 22,79% / HC 15,25% / Cons.Def. 5,68%); RE a 3 névvel a legmélyebb húzásban
- **Entry-slippage**: SJM -0,23% (kedvező); a sorozat szórása nagy (06-11 JAZZ +2,25% … ma SJM -0,23%)
- **TP-hit ráta**: 12/22 exit (54,5%); pozitív-exit 17/22 (77,3%) — az ACHC negatív TIME_STOP rontotta (06-16: 12/21 57,1% / 17/21 81,0%)

## 8. Heti kontextus — W25 D3
Szerda net -$271,41; a hét eddig (3 nap): -$289,60 kumulatív. SPY risk-off fordulat (VIX 16→18,73). **Holnap (06-18, Day 23) a hét utolsó kereskedési napja** (06-19 Juneteenth skip) → **a W25 heti zárás a holnapi review-ban** lesz (06-15…06-18, 4 nap).

## 9. Holnap (2026-06-18, csütörtök, Day 23, W25 D4 — utolsó heti nap)
- **Várt exit: 1** — VNO TIME_STOP, `next_action_at` 2026-06-17T20:00:09Z, `next_day_planned::time_stops_at_2140: ["VNO_TIME_STOP"]`. VNO days_held=5, tp1_hit=false, qty 160, entry $38,45, 06-17 mark $36,46 → `hipotézis:` negatív realized ≈ -$370 (feltevés: MOC a mostani mark körül; a tp1_hit=false miatt az FFIV/ACHC-mintába illik). Ez lenne a hét 4. TIME_STOP-ja (2 neg, 1 poz, +VNO)
- Fókusz a holnapi review-ban: (1) **W25 heti zárás blokk**; (2) VNO TIME_STOP realized + a tp1_hit-mintázat tesztje; (3) Net Liq 06-18 close vs $100 252,50, és a reziduum stabilitása (±$373?); (4) a nyitott könyv -$1 567 húzásának iránya; (5) notional-kúszás
- **Net Liq-rögzítés**: 06-18 close summary a 22:16 CEST utáni ablakban (utána Juneteenth + hétvége, a következő trading nap 06-22)
- Megj.: a 06-19 Juneteenth-en a cronok a guard miatt nem futnak → nincs daily_metrics sor, nincs Day-inkrement; a TIME_STOP-ok trading-napban számolnak, így a 3 napos szünet nem fogyaszt hold-napot

## 10. Freeze-sor
Paraméter-érintő változás ma: **nincs**.

## 11. A nap egy mondatban
Az ACHC TIME_STOP a swing-éra legnagyobb egynapi veszteségét hozta (-$271,41, -7,55%) egy risk-off napon (SPY -1,25%, VIX +14%), a 06-16-i becslés iránya helyes de nagyságrendje a static-mark feltevés miatt súlyosan elvétett; egy új Consumer Defensive entry (SJM) kedvező slippage-dzsel lépett be, a cumulative +$1 445,42-re csökkent, a nyitott könyv -$1 567,71-re mélyült (a 3 Real Estate név -$1 020-a a java), és holnap a VNO TIME_STOP zárja a Juneteenth-rövidített hetet.
