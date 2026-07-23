# IFDS Daily Review — 2026-06-24 (szerda, Day 26/63 NYSE-count, W26 D3)

## 1. Fejléc
- **Day 26/63** — `day_number=26` ÉS `trading_days=26` egyező ✓
- **Realized net: -$21,04** (gross -$19,76; commission $1,28) — egyetlen exit (NNN TIME_STOP_MOC, apró veszteség). Forrás: `daily_metrics`, `pending_exits`, broker-ledger (`matched=1`)
- **Cumulative: +$534,42 (+0,53%)** — a vérzés ma **megállt** (közel flat nap); a 06-11-i csúcs (+$1 735,02) óta -$1 200,60
- **Net Liq (IBKR, tiszta 06-24 close ablak): $100 523,94** ✓ verifikált — a 06-23 horgonyról ($100 028,05) **+$495,89**; a flat napon (SPY -0,05%) a nyitott könyv ~$494-et javult, a Net Liq visszatért a startvonal fölé (+$524)
- **Excess: +0,03%** (portfolio -0,02% vs SPY -0,05%, `daily_metrics`) — közel nulla, flat nap, a torzítás minimális
- **Nyitott pozíciók: 8** (NNN kilépett, TDG belépett; IBKR + `swing_positions` + `pt_reconcile` mind egyező)

## 2. Exits (1) — forrás: `pending_exits/2026-06-24.json` + broker-ledger
| Idő (CEST) | Ticker | Típus | Qty | Entry→Exit | Broker realized | Várt (06-23 review §9) | Eltérés |
|---|---|---|---|---|---|---|---|
| 21:59:42 | NNN | **TIME_STOP_MOC** | 208 | $46,61→$46,51 | **-$21,04** (-0,22%) | irány: negatív (pont-becslés nincs) | irány helyes, marginális |

NNN MOC-ra majdnem flat-re korrigált ($46,02 06-23 mark → $46,51 exit), így a veszteség minimális. tp1_hit=false → negatív (de épphogy). ✓ **`exit_type` ma helyes** (`TIME_STOP_MOC`, egyezik a `pending_exits`-szel) — a bug nem aktiválódott (tiszta TIME_STOP, nem re-entry/mental_sl).

## 3. Entries (1) — forrás: `pt_submit_2026-06-24.log`, `daily_metrics::execution`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 | entry_score |
|---|---|---|---|---|---|---|
| TDG | **Industrials** | 4 | $1297,68→$1305,00 | +0,56% | $1218,84 / $1356,81 / $1415,94 | 84,51 (S_j 84,5) |

TDG (TransDigm) **4. Industrials név** a könyvben (RBC, IEX, R mellett); magas-árú ($1305/részvény, 4 qty = ~$5,2k notional). A pipeline 3-at sized (RBC 105,0 / NSA 94,5 / SAIA 91,2), RBC+NSA már nyitott → csak TDG lépett be (a top-2 ismét RBC/NSA, mint 06-22/06-23 — §7 szelekciós koncentráció). TDG day-0 már +$69,68 unrealized.

## 4. Nyitott pozíciók (8) — forrás: IBKR `get_account_positions` (06-24 close, verifikált)
| Ticker | days_held | Mark | Unrealized (IBKR) | napi MTM Δ | next_action |
|---|---|---|---|---|---|
| AXTA | 3 | $34,66 | **+$134,78** | +$148,92 | HOLD |
| TDG | 0 | $1322,67 | **+$69,68** | +$69,68 | HOLD |
| EXEL | 5 | $52,87 | -$70,30 | +$168,30 | **TIME_STOP** (06-25, §9) |
| RBC | 2 | $633,55 | -$87,58 | +$0,99 | HOLD |
| R | 1 | $261,00 | -$89,00 | -$51,92 | HOLD |
| CORT | 5 | $81,56 | -$113,33 | +$80,37 | **TIME_STOP** (06-25, §9) |
| NSA | 1 | $44,44 | -$115,00 | -$78,00 | HOLD |
| IEX | 2 | $222,16 | -$151,81 | +$32,67 | HOLD |
| **Total unrealized** | | | **-$421,56** | | |

A nyitott könyv -$421,56-ra **jelentősen javult** (06-23: -$915,25) a flat napon — AXTA (+$135) és TDG (+$70) zöld, a többi mínusz mérséklődött. **A holnap kilépő EXEL és CORT ma sokat korrigált** (daily_pnl +$168 / +$80), így a holnapi TIME_STOP-juk a mai szintről kevésbé negatív lehet (de pont-becslést nem adok).

**Net Liq-rekonciliáció (§6.4)**: $100 000 + $534,42 − $421,56 = $100 112,86 várt vs tény $100 523,94 → **+$411,08 reziduum** — a recent sávban (06-16…06-24: 371,78 / 374,79 / 423,44 / 407,13 / 387,84 / 411,08; átlag ~$396±25). Stabil fix offset. Gazda: megfigyelés.

## 5. Ops-checklist
- ✓ `pt_reconcile` 22:15:07: „Reconciliation OK", state és IBKR egyező (8 ticker) — **21/21 éles silent OK**
- ✓ `pt_eod` fix tartja: „Trades(eod-fills): 0 | persisted: 1"; `P&L $-21.04`, `Cumulative +$534.42 [Day 26/63]` helyes
- ✓ IBKR positions vs `swing_positions`: 8 ticker, qty egyező
- ✓ Cron-időzítések: close 15:30:02 + 21:40:07 (NNN MOC); submit 15:31:01; monitor 22:00:10 (2 flag: EXEL, CORT); metrics 22:10:02; eod 22:11:02; reconcile 22:15:02
- ⚠️ Cron `BEALLITASOK` legacy display — ismétlődő P3
- ✓ `exit_type` (NNN TIME_STOP_MOC) helyes ma

## 6. Anomáliák (csak új/változott)
- **6.1 P2 (nyitva, Day 63-input)** — scoring_validation legacy-swing pooling. Nincs változás.
- **6.2 P2 (nyitva, Dev-chat)** — UW kivezetés. Megfigyelés: a `uw_shadow` ma `avg_dp_pct=0,0`, `penalty_count=0` (06-23: 6,40 / 13) — a darkpool-shadow napi adatok **extrém ingadozása** folytatódik (0 → 13 → 0 három nap alatt), ami a Dev-chat darkpool-térfogat-kérdését élesíti (a shadow-adat nem stabil). Dev-chat tétel.
- **6.3 P3 (megerősítve, ismétlődő)** — `exits_today::TIME_STOP=2` miközben ma 1 TIME_STOP futott (NNN); a `2` a holnapra beállított 2 flaget (EXEL, CORT) számolja. A 06-22-i megfigyelés megerősítve (a monitor log explicit: „2 exit flags set" holnapra). Gazda: CC-task (exits_today csak a ténylegesen lefutott exiteket számolja).
- **6.4 P2→megfigyelés** — Net Liq-reziduum +$411,08, sávban; §4.
- **6.5 P3 (ismétlődő)** — planned-vs-broker entry: NNN `entry=46,61` vs `46,59`; TDG planned 1297,68 / filled 1305,00.
- **6.6 P3 (nyitva)** — high_vol M_gex verifikáció. Ma `gex_regime_distribution` 6 high_vol / 31 positive / 3 unknown. Dev/CC-verifikáció.
- Nincs új P0/P1.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés nélkül)
- **🔴 Take-profit aszály — a legfontosabb strukturális megfigyelés**: a 06-11-i NSA TP2 óta **egyetlen take-profit (TP1 vagy TP2) sem ütött** — a 06-15…06-24 időszak (9 trading nap) **minden exitje TIME_STOP vagy MENTAL_SL** volt, és a cumulative ezalatt -$1 200,60-at vesztett a csúcsról. Mind a 8 jelenleg nyitott pozíció tp1_hit=false. A swing-pozíciók belépnek, sodródnak, és max_hold-on/mental-stopon zárnak a profit-célok elérése nélkül. Day 63 előtt **nincs jel-érvényességi ítélet**, de ez a mintázat a Day 63 gate scoring/exit-értékelésének központi kérdése lesz
- **Exit-kimenetek tp1_hit szerint**: tp1_hit=false → 7/7 negatív (FFIV, ACHC, VNO, NSA, JAZZ, SJM, NNN); tp1_hit=true → 2/2 pozitív (TKR, BEN). n=9 exit, konzisztens
- **Szektor-rotáció koncentrációba**: a korai Real Estate-klaszter (06-15/16, 22,79%) után most **Industrials-klaszter** épül (RBC, IEX, R, TDG = 4 név, **24,20%**, közelít a 30% caphez). A swing scoring ismételten Industrials-t szelektál (a top-3-ban RBC/SAIA visszatérő). RE leolvadt 6,71%-ra (csak NSA)
- **Cumulative-trajektória**: a vérzés ma megállt (-$21 flat nap); +$534,42, a csúcsról (06-11) -$1 200,60. MTM-alapon a Net Liq visszatért a startvonal fölé (+$524) a nyitott könyv javulásával
- **Notional**: 50,11% (06-23) → 45,61% (ma, NNN kilépett)
- **VIX**: 19,26 (06-23) → 19,56 (ma, +0,36%) — magas szinten stabilizálódott, a 2 napos risk-off után flat nap
- **Entry-slippage**: TDG +0,56%
- **TP-hit ráta**: 12/27 exit (44,4%); pozitív-exit 17/27 (63,0%)

## 8. Heti kontextus — W26 D3
W26 három nap: -$398,49 -$330,91 -$21,04 = **-$750,44**. A flat nap (-$21) lassította a W25-W26 negatív sorozatot. Heti zárás **péntek (06-26)** — a holnap (06-25) az utolsó előtti nap.

## 9. Holnap (2026-06-25, csütörtök, Day 27, W26 D4)
- **Várt exit: 2** — **EXEL TIME_STOP + CORT TIME_STOP**, `next_day_planned::time_stops_at_2140`. Mindkettő Healthcare, days_held=5, tp1_hit=false. 06-24 close unrealized EXEL -$70,30, CORT -$113,33 (mindkettő **ma sokat korrigált** felfelé) → `irány-hipotézis:` a tp1_hit=false mintázat szerint negatív, **de pont-becslést nem adok** (a 06-25 MOC-mark a holnapi nap függvénye; a mai korrekció után a kimenet bizonytalanabb mint valaha). 21:40 MOC
- Fókusz a 06-25 review-ban: (1) EXEL+CORT TIME_STOP realized; (2) a tp1_hit-mintázat n=11-re; (3) a take-profit-aszály folytatódik-e (lesz-e bármi TP-hit); (4) Net Liq vs $100 523,94; (5) Industrials-koncentráció iránya (közelít-e a 30% caphez egy újabb Industrials belépővel); (6) a holnap az utolsó előtti heti nap — péntek heti zárás
- **Net Liq-rögzítés**: 06-25 close summary a 22:16 CEST utáni ablakban

## 10. Freeze-sor
Paraméter-érintő változás ma: **nincs**.

## 11. A nap egy mondatban
Az NNN TIME_STOP marginális -$21,04-gyel zárt egy flat napon (SPY -0,05%), megállítva a W25-W26 vérzést, a cumulative +$534,42-n, a Net Liq visszatért a startvonal fölé (+$524) a nyitott könyv -$915-ről -$422-re javulásával, egy új high-price Industrials entry (TDG) negyedik Industrials névként 24,2%-os szektor-koncentrációt épített — miközben a 06-11 óta tartó take-profit-aszály (9 trading nap, 0 TP-hit, minden exit TIME_STOP/MENTAL_SL) a legfontosabb nyitott strukturális kérdés.
