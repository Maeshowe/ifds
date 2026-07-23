# IFDS Daily Review — 2026-06-22 (hétfő, Day 24/63 NYSE-count, W26 D1)

## 1. Fejléc
- **Day 24/63** — `day_number=24` ÉS `trading_days=24` egyező ✓ (backfill tartja). Az előző trading nap 06-18 volt (06-19 Juneteenth skip); a 3 napos szünet hold-napot nem fogyasztott
- **Realized net: -$398,49** (gross -$396,20; commission $2,29) — két exit (NSA + JAZZ, mindkettő TIME_STOP_MOC, 06-19-ről átcsúszva). Forrás: `daily_metrics`, `pending_exits`, broker-ledger (`matched=2`)
- **Cumulative: +$886,37 (+0,89%)** — **először $1 000 alatt** a 06-09 óta; a 06-11-i csúcs (+$1 735,02) óta **-$848,65** (6 trading nap)
- **Net Liq (IBKR, tiszta 06-22 close ablak): $100 198,62** ✓ verifikált — a 06-18 horgonyról ($100 357,27) -$158,65 (SPY -0,31% nap)
- **Excess: -0,08%** (portfolio -0,40% vs SPY -0,31%, `daily_metrics`) — közel nulla, enyhén negatív; realized-alapú (#6 inaktív), de ma a portfolio és SPY közel mozgott, így a torzítás kicsi
- **Nyitott pozíciók: 7** (NSA+JAZZ kilépett, RBC+IEX belépett; IBKR + `swing_positions` + `pt_reconcile` mind egyező)

## 2. Exits (2) — forrás: `pending_exits/2026-06-22.json` + broker-ledger
| Idő (CEST) | Ticker | Típus | Qty | Entry→Exit | Broker realized | Várt (06-18 review §9) | Eltérés |
|---|---|---|---|---|---|---|---|
| 21:59:31 | NSA | **TIME_STOP_MOC** | 153 | $45,87→$44,70 | **-$179,65** (-2,56%) | irány: negatív (pont-becslés szándékosan nincs) | irány helyes |
| 21:59:30 | JAZZ | **TIME_STOP_MOC** | 24 | $234,89→$225,77 | **-$218,84** (-3,88%) | irány: negatív (pont-becslés szándékosan nincs) | irány helyes |
| **Total** | | | | | **-$398,49** | | |

Mindkét exit tp1_hit=false → mindkettő negatív, a §7 mintázat szerint. A 06-18 review-ban tudatosan **nem adtam pont-becslést** (a 06-17/06-18 ACHC/VNO tanulság: 3 napos szünet után a MOC-mark nem becsülhető) — csak irányt jeleztem, ami mindkettőre stimmelt. `exit_type` mindkettőre helyes. Megj.: NSA a mai sizing-ban újra kvalifikált (S_j 98,7, 145 qty), de a race guard skippelte (még volt pozíciója), majd 21:40-kor TIME_STOP-pal kilépett — **nem self-reentry** (a pozíció megszűnt, nem újranyílt).

## 3. Entries (2) — forrás: `pt_submit_2026-06-22.log`, `daily_metrics::execution`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 | entry_score |
|---|---|---|---|---|---|---|
| RBC | **Industrials** | 9 | $639,18→$643,17 | +0,62% ⚠️ | $601,99 / $667,07 / $694,96 | 103,58 (S_j 103,6) |
| IEX | **Industrials** | 33 | $224,93→$226,73 | +0,80% ⚠️ | $214,44 / $232,80 / $240,66 | 98,37 (S_j 98,4) |

RBC+IEX az **5. szektor** (Industrials) — a könyv szektor-diverzifikációja tovább javult (06-16: 2 → ma 5 szektor). Mindkettő emelt (kedvezőtlen) slippage, a 06-17/06-18-i kedvező sorozat (SJM, AXTA) után. **RBC entry_score 103,58 — a deploy-sorozat egyik legmagasabbja** (>95, de a swing S_j-skálán nem „crowded"-exclusion). IEX a sizing-ban `high_vol` GEX-flaggel lépett be (MULT mégis 1,000 a cron-táblában — `hipotézis:` a swing GEX-kezelés a high_vol-t nem bünteti M_gex-szel mint a legacy 0,6×; §6 megfigyelés). A pipeline 3-at sized (RBC 103,6 / NSA 98,7 / IEX 98,4), NSA skip → RBC+IEX lépett be.

## 4. Nyitott pozíciók (7) — forrás: IBKR `get_account_positions` (06-22 close, verifikált)
| Ticker | days_held | Mark | Unrealized (IBKR) | next_action |
|---|---|---|---|---|
| SJM | 2 | $107,19 | **-$418,97** | **MENTAL_SL** (06-23 15:30, §9) — mark a $108,94 stop ALATT |
| NNN | 4 | $45,16 | -$300,56 | HOLD |
| EXEL | 3 | $51,35 | -$237,50 | HOLD |
| CORT | 3 | $79,71 | -$200,28 | HOLD |
| IEX | 0 | $225,36 | -$46,21 | HOLD |
| RBC | 0 | $645,73 | +$22,04 | HOLD |
| AXTA | 1 | $34,33 | +$86,60 | HOLD |
| **Total unrealized** | | | **-$1 094,88** | |

A nyitott könyv -$1 094,88-ra **javult** (06-18: -$1 351,03) — főként az NSA (-$216) és JAZZ (-$244) unrealized realizálttá válásával. RBC+AXTA zöld, IEX kis mínusz day-0. **SJM a legmélyebb (-$418,97), és a markja a stop alatt** → MENTAL_SL holnap.

**Net Liq-rekonciliáció (§6.4)**: $100 000 + $886,37 − $1 094,88 = $99 791,49 várt vs tény $100 198,62 → **+$407,13 reziduum**. A recent sávban marad (06-16…06-22: +$371,78 / +$374,79 / +$423,44 / +$407,13). A 06-18-i +$423 és a mai +$407 mindkettő exit-nap; tiszta nem-exit nap kell a sáv aljának (~$373) megerősítéséhez. Stabil ~$390±35, fix számviteli offset jellegű. Gazda: megfigyelés.

## 5. Ops-checklist
- ✓ `pt_reconcile` 22:15:06: „Reconciliation OK", state és IBKR egyező (7 ticker) — **19/19 éles silent OK**
- ✓ `pt_eod` fix tartja: „Trades(eod-fills): 0 | persisted: 2" — a cross-client MOC valós számát (2) mutatja; `P&L $-398.49`, `Cumulative +$886.37 [Day 24/63]` helyes
- ✓ IBKR positions vs `swing_positions`: 7 ticker, qty egyező
- ✓ Cron-időzítések teljes sor: intraday 14:30:01–14:32:57; close 15:30:02; submit 15:31:02; NSA+JAZZ MOC submit 21:40:07–08; monitor 22:00:10; metrics 22:10:02; eod 22:11:02; reconcile 22:15:01 — mind a 8 log jelen
- ◽ Cron log: 4× UW HTTP 429 (mind darkpool: DRS, BROS, GL, KNX) — vissza a darkpool-only mintára (06-18: 0, 06-17: 29 greek-exposure); a sorozat ugrál, higiéniai besorolás áll
- ⚠️ Cron `BEALLITASOK` legacy display — ismétlődő P3
- ✓ Phase 6 „sector limit: 0" ma (a 3 napos 1-es sorozat megszakadt — az új belépők Industrials, nem ütköztek cap-pel)
- ✓ `exit_type` (NSA, JAZZ TIME_STOP_MOC) egyezik a kanonikus `pending_exits`-szel

## 6. Anomáliák (csak új/változott)
- **6.1 P2 (nyitva, Day 63-input)** — scoring_validation legacy-swing pooling. Nincs változás.
- **6.2 P2 (nyitva, Dev-chat)** — UW kivezetés. Megfigyelés: ma a darkpool 429 visszatért (4×), és a `uw_shadow::would_have_been_penalty_count=9` (06-18: 1) — a darkpool-shadow térfogat-kérdés (Dev-chat) szempontjából releváns adat, hogy a penalty-count napról napra erősen ingadozik. Gazda: Dev-chat.
- **6.3 ÚJ P3** — `daily_metrics::swing_state::exits_today` **„MENTAL_SL: 1"-et mutat**, miközben a ténylegesen végrehajtott exitek ma 2× TIME_STOP voltak (NSA, JAZZ); az `exits.moc=2` helyes. Az `exits_today` a holnapra **beállított flaget** számolja exitként, ami félrevezető (a MENTAL_SL még nem futott le, holnap 15:30 a terv). `hipotézis:` az exits_today a next_action flageket is beleszámolja a végrehajtott exitek helyett. Gazda: CC-task (exits_today csak a ténylegesen lefutott exiteket számolja).
- **6.4 P2→megfigyelés** — Net Liq-reziduum +$407,13, a recent sávban; lásd §4.
- **6.5 P3 (ismétlődő)** — planned-vs-broker entry: NSA `entry=45,87` vs `45,42`; JAZZ `234,89` vs `229,63`.
- **6.6 ÚJ P3 megfigyelés** — IEX `high_vol` GEX-regime-mel lépett be, MULT 1,000 (a cron-tábla szerint). A legacy-ben high_vol → M_gex 0,6×. `hipotézis:` a swing sizing a high_vol-t nem bünteti, vagy a megjelenítés stale. Gazda: megfigyelés / CC-verifikáció (a swing M_gex-logika high_vol-kezelése).
- Nincs új P0/P1.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés nélkül)
- **TIME_STOP kimenetek**: n=7 — BEN +$159,92, FFIV -$152,22, TKR +$134,03, ACHC -$271,41, VNO -$160,56, **NSA -$179,65, JAZZ -$218,84**. A `tp1_hit` mintázat **erősödik** (n=7): tp1_hit=false → **5/5 negatív** (FFIV, ACHC, VNO, NSA, JAZZ); tp1_hit=true → 2/2 pozitív (TKR, BEN). Megfigyelés, nem következtetés (Day 63 előtt nincs jel-érvényességi ítélet), de a konzisztencia rögzítendő
- **ÚJ exit-típus — MENTAL_SL**: a sorozatban az **első mental-stop trigger** (SJM, holnap 15:30). Eddig minden swing-exit TIME_STOP volt; ez az első ár-alapú (stop alá esett) kilépés-flag
- **TP1-hiány tart**: mind a 7 nyitott pozíció tp1_hit=false; a deploy óta a swing-pozíciók túlnyomórészt max_hold-ig sodródnak TP1 nélkül
- **Szektor-diverzifikáció tovább javult**: **5 szektor** (Industrials 13,18% / HC 9,74% / RE 9,69% / Cons.Def. 5,68% / Basic Mat. 4,96%); observed max 22,79% (06-16) → 13,18% (ma). A 2-szektor koncentráció teljesen feloldódott
- **Nyitott könyv unrealized**: -$1 567,71 (06-17) → -$1 351,03 (06-18) → **-$1 094,88 (06-22)** — javuló sorozat
- **Notional**: 42,54% (06-18) → 43,25% (ma) — stabil ~43%
- **Entry-slippage**: RBC +0,62%, IEX +0,80% (mindkettő kedvezőtlen) — a kedvező SJM/AXTA után visszafordult
- **TP-hit ráta**: 12/25 exit (48,0%) — **50% alá esett**; pozitív-exit 17/25 (68,0%)
- **Cumulative-trajektória**: a +$1 735 csúcs (06-11) óta 6 trading napból 4 negatív (06-15, 17, 18, 22), 1 pozitív (06-16), 1 flat — a +$886-os szint a 06-09 óta a legalacsonyabb

## 8. Heti kontextus — W26 D1
W26 első nap: -$398,49. A W25 (-$450,16) negatív lendülete átnyúlt. Heti zárás péntek (06-26).

## 9. Holnap (2026-06-23, kedd, Day 25, W26 D2)
- **Várt exit: 1** — **SJM MENTAL_SL**, `next_day_planned::exits_at_1530: ["SJM_MENTAL_SL"]`. ⚠️ Megj.: a MENTAL_SL **15:30-kor (piacnyitás) zár, nem 21:40 MOC-on** (eltér a TIME_STOP-tól). SJM days_held=2, mark $107,19 a stop ($108,94) alatt, unrealized -$418,97 → `irány-hipotézis:` negatív realized (a mental-stop definíció szerint a stop alatt zár), **de pont-becslést nem adok** (a 15:30-as nyitó-fill a holnapi nyitó-mark függvénye). Ez lesz az **első ténylegesen lefutott MENTAL_SL** — figyelni a végrehajtás mechanikáját (15:30 fill, nem MOC)
- Fókusz a 06-23 review-ban: (1) SJM MENTAL_SL végrehajtás + mechanika-verifikáció (15:30 vs MOC); (2) Net Liq vs $100 198,62 és a reziduum (nem-exit napon a sáv alja?); (3) AXTA/RBC követés (zöldek); (4) a TP1-hiány és a tp1_hit-mintázat folytatódik-e; (5) §6.6 IEX high_vol M_gex verifikáció
- **Net Liq-rögzítés**: 06-23 close summary a 22:16 CEST utáni ablakban

## 10. Freeze-sor
Paraméter-érintő változás ma: **nincs**.

## 11. A nap egy mondatban
A két átcsúszott idő-stop (NSA -$180, JAZZ -$219) -$398,49-es napot adott, a cumulative először esett $1 000 alá (+$886,37) a 06-11-i csúcsról -$849-cel, két új Industrials entry (RBC, IEX) ötödik szektorra bővítette a könyvet emelt slippage-dzsel, a tp1_hit=false→negatív TIME_STOP-mintázat n=7-en 5/5-re erősödött, és holnap az első MENTAL_SL (SJM, a stop alatt) zár.
