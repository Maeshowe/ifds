# IFDS Daily Review — 2026-06-18 (csütörtök, Day 23/63 NYSE-count, W25 D4 — heti utolsó nap)

## 1. Fejléc
- **Day 23/63** — `day_number=23` ÉS `trading_days=23` egyező ✓ (a backfill-fix tartja). **06-19 Juneteenth → nincs kereskedés, nincs Day-inkrement; következő trading nap 06-22 = Day 24**
- **Realized net: -$160,56** (gross -$159,40; commission $1,16) — egyetlen exit (VNO TIME_STOP_MOC). Forrás: `daily_metrics`, `pending_exits`, broker-ledger (`matched=1`)
- **Cumulative: +$1 284,86 (+1,28%)** — a 06-11/06-12-i csúcs (+$1 735,02) óta **-$450,16**, ami pontosan a W25 heti net (a teljes heti veszteség a csúcsról számolva)
- **Net Liq (IBKR, tiszta 06-18 close ablak): $100 357,27** ✓ verifikált — a 06-17 horgonyról ($100 252,50) +$104,77 (SPY +0,78% up-nap, VIX 16,42 -10,95%)
- **Excess: -0,94%** (portfolio -0,16% vs SPY +0,78%, `daily_metrics`) — ⚠️ realized-alapú szemantika (#6 inaktív): up-napon a realizált veszteség negatív excesst ad, miközben a nyitott könyv MTM-je javult (§4); **alulteljesítést mutat egy napon, amikor a könyv valójában emelkedett** — a 06-17 tükörképe
- **Nyitott pozíciók: 7** (VNO kilépett, AXTA belépett; IBKR + `swing_positions` + `pt_reconcile` mind egyező)

## 2. Exits (1) — forrás: `pending_exits/2026-06-18.json` + broker-ledger
| Idő (CEST) | Ticker | Típus | Qty | Entry→Exit | Broker realized | Várt (06-17 review §9) | Eltérés |
|---|---|---|---|---|---|---|---|
| 21:59:41 | VNO | **TIME_STOP_MOC** | 160 | $38,78→$37,78 | **-$160,56** (-2,59%) | ≈ -$370 (feltevés: mark ~$36,46 static) | **+$210 a becslés felett** ⚠️ |

**Becslési hiba őszinte rögzítése (2. nap, ellentétes irány)**: a 06-17 review iránya helyes (negatív, tp1_hit=false), de a nagyságrend megint elvétett — **most felfelé**. Ok: ugyanaz mint tegnap (ACHC), a static-mark feltevés. A VNO a 06-18 up-napon $36,46-ról $37,78-ra korrigált (+3,6%), így a MOC-veszteség jóval kisebb. **A tegnapi ACHC-hiba pontos tükörképe**: tegnap a lefelé mozgás miatt alulbecsültem (-$47 vs tény -$271), ma a felfelé korrekció miatt túlbecsültem (-$370 vs tény -$161). **Megerősített tanulság**: a tp1_hit=false TIME_STOP-okra nem adok többé pont-becslést statikus markból; csak irányt és a következő-napi MOC-mark bizonytalanságát jelzem. `exit_type` helyes.

## 3. Entries (1) — forrás: `pt_submit_2026-06-18.log`, `daily_metrics::execution`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 | entry_score |
|---|---|---|---|---|---|---|
| AXTA | **Basic Materials** | 146 | $34,00→$33,73 | **-0,79% (kedvező)** | $31,61 / $35,80 / $37,59 | 79,10 (S_j 79,1) |

AXTA a **4. szektor** (Basic Materials) — a könyv szektor-diverzifikációja érdemben javult (06-16: 2 szektor → ma 4). Kedvező slippage (2. nap egymás után: SJM -0,23%, AXTA -0,79%). AXTA day-0 már **+$111,42 unrealized** (IBKR). A pipeline 3-at sized (EXEL 82,0 / NNN 81,0 / AXTA 79,1), de EXEL+NNN már nyitott → csak AXTA lépett be.

## 4. Nyitott pozíciók (7) — forrás: IBKR `get_account_positions` (06-18 close, verifikált)
| Ticker | days_held | Mark | Unrealized (IBKR) | next_action |
|---|---|---|---|---|
| NNN | 3 | $45,00 | -$333,84 | HOLD |
| JAZZ | 5 | $224,66 | -$244,36 | **TIME_STOP** (06-22, §9) |
| SJM | 1 | $110,86 | -$239,14 | HOLD |
| EXEL | 2 | $51,35 | -$237,50 | HOLD |
| NSA | 5 | $44,45 | -$216,73 | **TIME_STOP** (06-22, §9) |
| CORT | 2 | $79,91 | -$190,88 | HOLD |
| AXTA | 0 | $34,50 | **+$111,42** | HOLD |
| **Total unrealized** | | | **-$1 351,03** | |

A nyitott könyv -$1 351,03-ra **javult** (06-17: -$1 567,71) az up-napon + a VNO kilépésével (a -$370 unrealized -$160 realizálttá vált). AXTA az egyetlen zöld. **Megfigyelés (§7)**: mind a 7 nyitott pozíció `tp1_hit=false` — egyetlen nyitott pozíció sem ütött TP1-et.

**Net Liq-rekonciliáció (§6.4)**: $100 000 + $1 284,86 realized − $1 351,03 unrealized = $99 933,83 várt vs tény $100 357,27 → **+$423,44 reziduum**. Ez +$50-nel feljebb a 06-16/06-17-i stabil ~$373-ról, **kilépett az általam jelzett ±$10 sávból** — de a kiugrás a VNO exit-napi unrealized→realized átmenetével esik egybe (a VNO a 06-17-i -$370 markról -$160 realizálttá vált, +$210 swing), ami exit-napon természetesen perturbálja a reziduumot. Nem eszkalálom, de jelzem; ha a következő nem-exit napon is ~$423 marad, akkor új szint, ha visszaáll ~$373-ra, akkor exit-napi átmeneti. Gazda: megfigyelés.

## 5. Ops-checklist
- ✓ `pt_reconcile` 22:15:06: „Reconciliation OK", state és IBKR egyező (7 ticker) — **18/18 éles silent OK**
- ✓ `pt_eod` fix tartja: „Trades(eod-fills): 0 | persisted: 1"; `P&L $-160.56`, `Cumulative +$1,284.86 [Day 23/63]` helyes
- ✓ IBKR positions vs `swing_positions`: 7 ticker, qty egyező
- ✓ Cron-időzítések teljes sor: intraday 14:30:00–14:32:02; close 15:30:02; submit 15:31:02; VNO MOC submit 21:40:07; monitor 22:00:12; metrics 22:10:02; eod 22:11:02; reconcile 22:15:01 — mind a 8 log jelen
- ✓ Cron log: **0 UW HTTP 429** — a 2/4/3/12/29 sorozat ma megtört (nem monoton); megerősíti a higiéniai (nem trading) besorolást
- ⚠️ Cron `BEALLITASOK` legacy display (0,7%/$700, Max per sector 2, flow=0,60) — ismétlődő P3
- ◽ Phase 6 „sector limit: 1" kizárás (3. nap egymás után, konzisztens 1)
- ✓ `exit_type` (VNO TIME_STOP_MOC) egyezik a kanonikus `pending_exits`-szel

## 6. Anomáliák (csak új/változott)
- **6.1 P2 (nyitva, Day 63-input)** — scoring_validation.py legacy-swing pooling. Nincs változás.
- **6.2 P2 (nyitva, Dev-chat)** — UW kivezetés: a greek-exposure-primary kikapcsolás (verifikáció-feltételes, freeze-safe csak ha a regime-egyezés bizonyított) és a teljes UW-kivezetés (Day 126 data-cost tábla + Day 90 darkpool-audit életképesség) **Dev-chat tétel**, Tamás átviszi. Log Review oldali megfigyelés ehhez: **a darkpool-térfogat verifikálandó** — ma `uw_shadow` 36 ticker logged, `avg_dp_pct 1.32`, de a tegnapi „3/nap" állítás vs a mai 36 logged ellentmond; tisztázni kell, mi a tényleges shadow-darkpool napi rekord-szám (a 36 a Phase 4 univerzum, nem feltétlen a darkpool-sikeres hívások). Gazda: Dev-chat.
- **6.3 P3 (ismétlődő)** — `BEALLITASOK` legacy display + Phase 6 sector-limit kizárás (konzisztens 1/nap). CC futó-config audit.
- **6.4 P2→megfigyelés** — Net Liq-reziduum +$423,44, +$50 a stabil ~$373-ról, exit-napi VNO-átmenettel egybeesve; lásd §4. Következő nem-exit nap dönti el (átmeneti vs új szint).
- **6.5 P3 (ismétlődő)** — planned-vs-broker entry-tárolás: VNO `daily_metrics::entry=38,78` vs `swing::entry_price=38,45`. A §6.4 reziduummal való összefüggés hipotézise él.
- Nincs új P0/P1.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés nélkül)
- **TIME_STOP kimenetek**: n=5 — BEN 06-11 +$159,92, FFIV 06-15 -$152,22, TKR 06-16 +$134,03, ACHC 06-17 -$271,41, **VNO 06-18 -$160,56**. A `tp1_hit` mintázat tart (n kicsi): tp1_hit=false → mind negatív (FFIV, ACHC, VNO); tp1_hit=true → pozitív (TKR). A 06-22-i NSA+JAZZ (mindkettő tp1_hit=false) további teszt
- **ÚJ megfigyelés — TP1-hiány a nyitott könyvben**: mind a 7 nyitott pozíció `tp1_hit=false`; a W25 heti TP1-hit 0/5 (heti report). A swing-pozíciók láthatóan max_hold-ig (5 nap) sodródnak TP1 elérése nélkül — strukturális megfigyelés, jel-érvényességi ítélet nélkül (Day 63 előtt)
- **Notional-kúszás megtört**: 29,72 → 34,51 → 41,61 → 43,72 → **42,54%** (ma kissé vissza, VNO kilépett, AXTA kisebb)
- **Szektor-koncentráció enyhült**: 2 szektor (06-16) → **4 szektor** (RE 16,64% / HC 15,25% / Cons.Def. 5,68% / Basic Mat. 4,96%); observed max 22,79% → 16,64% (VNO kilépésével a RE csökkent)
- **Nyitott könyv unrealized**: -$856,84 (06-16) → -$1 567,71 (06-17) → **-$1 351,03 (06-18)** — az up-napon javult
- **Entry-slippage**: AXTA -0,79% (kedvező, 2. nap); a kedvező slippage-sorozat (SJM, AXTA) ellensúlyozza a 06-11 JAZZ +2,25%-ot
- **TP-hit ráta**: 12/23 exit (52,2%); pozitív-exit 17/23 (73,9%) — a VNO negatív TIME_STOP tovább rontotta

## 8. HETI ZÁRÁS — W25 (jún 15–18, 4 nap, Juneteenth-rövidített) — forrás: `docs/analysis/weekly/2026-W25.md`
- **Heti net: -$450,16** (gross -$445,74, commission -$4,42) — a deploy óta a **leggyengébb hét** (a rögzített heti netek közül a legalacsonyabb; W24 volt a legerősebb +$1 489,77, a fordulat egy hét alatt). Win-napok: **1/4** (csak 06-16 TKR pozitív)
- **Heti excess: -1,14%** (portfolio -0,45% vs SPY +0,69%) — negatív, a W24 +0,90% után
- **Exit-mix (heti): 4× TIME_STOP MOC** (FFIV, TKR, ACHC, VNO) — 0 TP1, 0 TP2, 0 SL, 0 LOSS_EXIT. **A hét összes exitje idő-stop volt** — a 4 max_hold pozíció mind lejárt, egyik sem TP-n vagy stop-on zárt
- **TP1: 0/5 hit (0%)**; az „R:R realized 1:0.00" mező ezen a héten **strukturálisan n/a** (0 TP1-hit), tehát itt nem dönthető el, hogy a W24-ben jelzett R:R-számítási gyanú bug-e vagy valós nulla — a következő TP1-hites héten verifikálandó
- **Slippage (heti): avg +0,05%** (a kedvező SJM/AXTA húzta le), worst +1,00% (CORT 06-16)
- **Dinamikus küszöb**: zero-position 0/4, low-position (<3) 4/4 — konzisztensen kevés, koncentrált belépő
- **Scoring Quality avg 0,0 / corr n/a**: az entry_score perzisztálás továbbra is hiányos (a legtöbb pozíció entry_score=0,0 a state-ben); ismétlődő megfigyelés
- **Heti összegzés egy mondatban**: a W25 a swing-éra első egyértelműen negatív hete (-$450,16, -1,14% excess, 1/4 win-nap), a hét mind a 4 exitje TIME_STOP volt, és a cumulative a +$1 735 csúcsról +$1 285-re húzódott vissza

## 9. Következő trading nap (2026-06-22, hétfő, Day 24, W26 D1) — 06-19 Juneteenth SKIP
- **Várt exit: 2** — **NSA TIME_STOP + JAZZ TIME_STOP**, mindkettő `next_day_planned::time_stops_at_2140`. ⚠️ **Fontos: ezek 06-22-re csúsznak**, mert 06-19 Juneteenth (guard skip). Mindkettő days_held=5, tp1_hit=false; 06-18 close unrealized NSA -$216,73, JAZZ -$244,36. `irány-hipotézis:` a tp1_hit=false mintázat szerint negatív, **de pont-becslést nem adok** (a 06-17/06-18 tanulság: 3 napos szünet után a 06-22-i MOC-mark nem becsülhető a 06-18 markból; a hétvégi/ünnepi gap iránya ismeretlen)
- A 3 napos szünet (06-19 ünnep + hétvége) nem fogyaszt hold-napot (trading-napban számol), nem keletkezik mesterséges idő-stop
- Fókusz a 06-22 review-ban: (1) NSA+JAZZ TIME_STOP realized + a tp1_hit-mintázat n=7-re bővítése; (2) Net Liq vs $100 357,27 és a reziduum (átmeneti $423 vagy új szint?); (3) a nyitott könyv 3 napos gap utáni iránya; (4) AXTA day-3 követés (az egyetlen zöld); (5) a TP1-hiány mintázat folytatódik-e
- **Net Liq-rögzítés**: 06-22 close summary a 22:16 CEST utáni ablakban

## 10. Freeze-sor
Paraméter-érintő változás ma: **nincs**. (UW-kivezetés Dev-chat tétel, nem freeze-érintő amíg verifikáció-feltételes.)

## 11. A nap egy mondatban
A VNO TIME_STOP -$160,56-ot realizált (a 06-17-i becslésem felfelé vétett, a VNO up-napi korrekciója miatt — a tegnapi ACHC-hiba tükörképe), egy új Basic Materials entry (AXTA) kedvező slippage-dzsel és day-0 +$111-gyel lépett be négyre bővítve a szektorszámot, a cumulative +$1 284,86-ra csökkent, és a W25 a swing-éra első negatív hete lett (-$450,16, 1/4 win-nap, mind a 4 exit TIME_STOP) — a következő trading nap 06-22, két átcsúszott idő-stoppal (NSA, JAZZ).
