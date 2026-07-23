# IFDS Daily Review — 2026-06-23 (kedd, Day 25/63 NYSE-count, W26 D2)

## 1. Fejléc
- **Day 25/63** — `day_number=25` ÉS `trading_days=25` egyező ✓ (backfill tartja)
- **Realized net: -$330,91** (gross -$329,79; commission $1,12) — egyetlen exit (SJM MENTAL_SL, az **első mental-stop a sorozatban**). Forrás: `daily_metrics`, `pending_exits`, broker-ledger (`matched=1`, `sl_hits`)
- **Cumulative: +$555,46 (+0,56%)** — a 06-11-i csúcs (+$1 735,02) óta **-$1 179,56** (7 trading nap). A W25 (-$450,16) + W26-eddig (-$729,40, 2 nap) együtt
- **Net Liq (IBKR, tiszta 06-23 close ablak): $100 028,05** ✓ verifikált — **gyakorlatilag a $100 000-es startvonalon** (+$28). MTM-alapon a számla a swing-éra nyereségének nagy részét visszaadta: a +$555,46 realizáltat a -$915,25 unrealized nyitott könyv ellensúlyozza
- **Excess: +1,12%** (portfolio -0,33% vs SPY -1,45%, `daily_metrics`) — ⚠️ realized-alapú (#6): nagy SPY-lefelé napon a kisebb realizált veszteség pozitív excesst ad, miközben a nyitott könyv MTM-je is esett; felfelé torzít
- **Nyitott pozíciók: 8** (SJM kilépett, NSA+R belépett — a könyv 7→8-ra nőtt; IBKR + `swing_positions` + `pt_reconcile` mind egyező)

## 2. Exits (1) — forrás: `pending_exits/2026-06-23.json` + broker-ledger
| Idő (CEST) | Ticker | Típus | Qty | Entry→Exit | Broker realized | Várt (06-22 review §9) | Eltérés |
|---|---|---|---|---|---|---|---|
| 15:30:26 | SJM | **MENTAL_SL** | 49 | $115,76→$109,01 | **-$330,91** (-5,83%) | irány: negatív (pont-becslés szándékosan nincs) | irány helyes |

**Mechanika-verifikáció ✓**: a MENTAL_SL **15:30:19-kor MKT SELL-ként futott** (piacnyitás), **nem 21:40 MOC-on** — ahogy a `next_day_planned::exits_at_1530` jelezte. Ez megerősíti, hogy a mental-stop a TIME_STOP-tól eltérő mechanikán (nyitó-exit) zár. SJM tp1_hit=false → negatív, a §7 mintázat szerint. **A -$330,91 a swing-éra legnagyobb egyszeri realizált vesztesége** (abszolútban; az ACHC -$271,41 és -7,55% a legnagyobb %-ban).
⚠️ **exit_type-bug (ismétlődő P1)**: `daily_metrics::trades::details::SJM::exit_type="TP1"` — HIBÁS (kanonikus `pending_exits`: MENTAL_SL). A `record_pending_exits` log és az `exits.sl=1` aggregát **helyesen** MENTAL_SL/sl_hits-be sorolta; a hiba szűken a `trades.details`/`best`/`worst` címkében van. Az exit_type-determináció a fill-timestamp alapján továbbra is megbízhatatlan (a `03c77d8` az eod Trades-számot javította, az exit_type-determinációt nem).

## 3. Entries (2) — forrás: `pt_submit_2026-06-23.log`, `daily_metrics::execution`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 | entry_score |
|---|---|---|---|---|---|---|
| NSA (re-entry) | Real Estate | 150 | $44,74→$45,20 | +1,03% ⚠️ | $42,76 / $46,23 / $47,71 | 96,69 (S_j 96,7) |
| R (Ryder) | Industrials | 22 | $265,06→$265,00 | -0,02% (kedvező) | $249,71 / $276,57 / $288,09 | 85,39 (S_j 85,4) |

**NSA re-entry (1-napos gap)**: NSA 06-22-n TIME_STOP-pal kilépett (-$179,65), majd 06-23-n újra kvalifikált (S_j 96,7) és újra belépett. **Nem self-reentry** (nem azonos-napi TP2-utáni), hanem 1-napos gap utáni újraszelekció. Megfigyelés (§7): a rendszer ismételten NSA-t választ (magas score), holott az előző tartás veszteséggel zárt. R (Ryder) a 3. Industrials név. A pipeline 3-at sized (RBC 105,3 / NSA 96,7 / SAIA 90,6), RBC skip → NSA+R lépett be.

## 4. Nyitott pozíciók (8) — forrás: IBKR `get_account_positions` (06-23 close, verifikált)
| Ticker | days_held | Mark | Unrealized (IBKR) | next_action |
|---|---|---|---|---|
| EXEL | 4 | $51,34 | -$238,60 | HOLD |
| CORT | 4 | $79,85 | -$193,70 | HOLD |
| IEX | 1 | $221,17 | -$184,48 | HOLD |
| NNN | 5 | $46,02 | -$121,68 | **TIME_STOP** (06-24, §9) |
| RBC | 1 | $633,44 | -$88,57 | HOLD |
| R | 0 | $263,36 | -$37,08 | HOLD |
| NSA | 0 | $44,96 | -$37,00 | HOLD |
| AXTA | 2 | $33,64 | -$14,14 | HOLD |
| **Total unrealized** | | | **-$915,25** | |

A nyitott könyv -$915,25-re **javult** (06-22: -$1 094,88) az SJM (-$418) kilépésével, **de mind a 8 pozíció mínuszban** — a 06-22-i zöldek (RBC +$22, AXTA +$86) a -1,45%-os napon átfordultak. NNN holnap TIME_STOP (days_held=5, tp1_hit=false).

**Net Liq-rekonciliáció (§6.4)**: $100 000 + $555,46 − $915,25 = $99 640,21 várt vs tény $100 028,05 → **+$387,84 reziduum** — a recent sáv közepén (06-16…06-23: +371,78 / +374,79 / +423,44 / +407,13 / +387,84; átlag ~$393±25). Stabil fix offset, nem növekvő. Gazda: megfigyelés.

## 5. Ops-checklist
- ✓ `pt_reconcile` 22:15:06: „Reconciliation OK", state és IBKR egyező (8 ticker) — **20/20 éles silent OK**
- ✓ `pt_eod` fix tartja: „Trades(eod-fills): 0 | persisted: 1"; `P&L $-330.91`, `Cumulative +$555.46 [Day 25/63]` helyes
- ✓ IBKR positions vs `swing_positions`: 8 ticker, qty egyező
- ✓ Cron-időzítések: close 15:30:19 (MENTAL_SL MKT SELL) + 21:40:03 (nincs TIME_STOP); submit 15:31:02; monitor 22:00:10; metrics 22:10:02; eod 22:11:01; reconcile 22:15:02
- ⚠️ Cron `BEALLITASOK` legacy display — ismétlődő P3
- ⚠️ `daily_metrics::trades::exit_type="TP1"` MENTAL_SL-re — §2, ismétlődő P1

## 6. Anomáliák (csak új/változott)
- **6.1 P2 (nyitva, Day 63-input)** — scoring_validation legacy-swing pooling. Nincs változás.
- **6.2 P2 (nyitva, Dev-chat)** — UW kivezetés. Megfigyelés: a `uw_shadow::would_have_been_penalty_count` tovább nő (06-18: 1 → 06-22: 9 → 06-23: 13), `avg_dp_pct=6,40` (06-22: 4,34) — a darkpool-shadow napi adatai erősen ingadoznak. Dev-chat tétel.
- **6.3 ÚJ P3 megfigyelés — notional 50% fölött** — `total_notional_pct_equity=50,11%` (06-22: 43,25%), IBKR gross_position_value $49 415 megerősíti, leverage 0,49. A kúszás-sorozat: 42,54 → 43,25 → **50,11%**. 8 pozíció (max_concurrent 12), 3 magas-árú Industrials (RBC $5,7k, R $5,8k, IEX $7,3k). `hipotézis:` a magas-árú Industrials nevek notional-súlya emeli; a 0,35% risk-per-trade mellett a kockázat kontrollált, de a bruttó kitettség az 50%-os pszichológiai szintet átlépte. Gazda: megfigyelés (ha 60%+ → figyelendő); Day 63-input lehet a notional-cap explicit beállításához.
- **6.4 P2→megfigyelés** — Net Liq-reziduum +$387,84, sáv-közép; §4.
- **6.5 P3 (ismétlődő)** — planned-vs-broker entry: SJM `entry=115,76` vs `115,99`; NSA re-entry `entry` planned 44,74 / filled 45,20.
- **6.6 P3 (nyitva)** — IEX high_vol M_gex verifikáció (06-22 §6.6). Ma az `uw_shadow::gex_regime_distribution` 10 high_vol / 34 positive — a high_vol regime gyakori; a swing M_gex-kezelése verifikálandó. Gazda: megfigyelés.
- Nincs új P0.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés nélkül)
- **Exit-kimenetek tp1_hit szerint**: a `tp1_hit=false → negatív` mintázat kiterjedt a MENTAL_SL-re is (SJM, tp1_hit=false, -$330,91). Összesített (TIME_STOP + MENTAL_SL): tp1_hit=false → **6/6 negatív** (FFIV, ACHC, VNO, NSA, JAZZ, SJM); tp1_hit=true → 2/2 pozitív (TKR, BEN). n=8 exit, a mintázat erős és konzisztens — de Day 63 előtt **nincs jel-érvényességi ítélet**, csak rögzítés
- **TP1-hiány tart**: mind a 8 nyitott pozíció tp1_hit=false; a deploy óta egyetlen jelenleg nyitott pozíció sem ütött TP1-et
- **Cumulative-trajektória — drawdown a csúcsról**: +$1 735,02 (06-11) → +$555,46 (06-23), **-$1 179,56 hét trading nap alatt** (6 napból 5 negatív). MTM-alapon (Net Liq) a számla a startvonalon (+$28). A P&L pozitív marad a deploy-starthoz képest, de a csúcs-gain ~68%-a visszaadva
- **Notional**: 50,11% — első alkalom 50% fölött (§6.3)
- **Szektor-eloszlás**: 4 szektor (Industrials 19,01% — RBC+IEX+R 3 név / RE 16,40% / HC 9,74% / Basic Mat 4,96%); Consumer Defensive kiesett (SJM). observed max 19,01%
- **VIX-emelkedés**: 16,42 (06-18) → 17,28 (06-22) → 19,26 (06-23, +11,46%) — 2. egymást követő risk-off nap, a VIX 19 fölött
- **Entry-slippage**: NSA +1,03% (kedvezőtlen), R -0,02% (semleges)
- **TP-hit ráta**: 12/26 exit (46,2%); pozitív-exit 17/26 (65,4%)
- **NSA-ciklus**: belépés 06-11 → TIME_STOP exit 06-22 (-$179,65) → re-entry 06-23; a rendszer ismételten szelektálja (magas score), a köztes tartás veszteséges volt — megfigyelés

## 8. Heti kontextus — W26 D2
W26 két nap: -$398,49 + -$330,91 = **-$729,40**. A W25 (-$450,16) negatív lendülete folytatódik és gyorsul. Heti zárás péntek (06-26).

## 9. Holnap (2026-06-24, szerda, Day 26, W26 D3)
- **Várt exit: 1** — **NNN TIME_STOP**, `next_day_planned::time_stops_at_2140: ["NNN_TIME_STOP"]`. NNN days_held=5, tp1_hit=false, qty 208, 06-23 close mark $46,02 vs entry $46,59, unrealized -$121,68 → `irány-hipotézis:` a tp1_hit=false mintázat szerint negatív, **de pont-becslést nem adok** (a 06-24 MOC-mark a holnapi nap függvénye). 21:40 MOC (nem 15:30, mert TIME_STOP)
- Fókusz a 06-24 review-ban: (1) NNN TIME_STOP realized; (2) a tp1_hit-mintázat n=9-re; (3) Net Liq vs $100 028,05 (a startvonal közelében — figyelni, átlép-e alá MTM-alapon); (4) notional 50%+ iránya; (5) a 8-pozíciós könyv egyöntetű mínusz iránya egy esetleges 3. risk-off napon; (6) VIX-trend (19,26 → ?)
- **Net Liq-rögzítés**: 06-24 close summary a 22:16 CEST utáni ablakban

## 10. Freeze-sor
Paraméter-érintő változás ma: **nincs**.

## 11. A nap egy mondatban
Az első MENTAL_SL (SJM) 15:30-kor — nem MOC-on — futott le -$330,91-gyel (a swing-éra legnagyobb egyszeri realizált vesztesége), a cumulative +$555,46-ra esett (a 06-11-i csúcsról -$1 180, MTM-alapon a Net Liq a $100k startvonalon), két új entry (NSA re-entry, R) nyolcra emelte a könyvet 50% fölötti notionallel, és a tp1_hit=false→negatív exit-mintázat n=8-on 6/6-ra erősödött egy 2. egymást követő risk-off napon (VIX 19,26).
