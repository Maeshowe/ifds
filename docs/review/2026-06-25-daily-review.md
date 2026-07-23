# IFDS Daily Review — 2026-06-25 (csütörtök, Day 27/63 NYSE-count, W26 D4)

## 1. Fejléc
- **Day 27/63** — `day_number=27` ÉS `trading_days=27` egyező ✓
- **Realized net: +$2,26** (gross +$4,49; commission $2,23) — két exit (EXEL -$31,84 + CORT +$34,10, mindkettő TIME_STOP_MOC). **Az első pozitív nap 06-16 óta** (ha épphogy). Forrás: `daily_metrics`, `pending_exits`, broker-ledger (`matched=2`)
- **Cumulative: +$536,68 (+0,54%)** — gyakorlatilag flat (+$2,26)
- **Net Liq (IBKR, tiszta 06-25 close ablak): $101 348,69** ✓ verifikált — a 06-24 horgonyról ($100 523,94) **+$824,75**; a flat SPY-napon (+0,14%) az Industrials-nevek MTM-szárnyalása (IEX +195, R +190, RBC +90 napi) emelte. Net Liq +$1 349 a startvonal fölött
- **Excess: -0,14%** (portfolio +0,00% vs SPY +0,14%, `daily_metrics`) — realized-alapú (#6); a flat realized a kis SPY-emelkedés alatt, de a nyitott könyv valójában +$871-et javult (lásd §4)
- **Nyitott pozíciók: 8** (EXEL+CORT kilépett, PFGC+SLGN belépett; IBKR + `swing_positions` + `pt_reconcile` mind egyező)

## 2. Exits (2) — forrás: `pending_exits/2026-06-25.json` + broker-ledger
| Idő (CEST) | Ticker | Típus | Qty | Entry→Exit | Broker realized | Várt (06-24 review §9) | Eltérés |
|---|---|---|---|---|---|---|---|
| 21:59:45 | CORT | **TIME_STOP_MOC** | 47 | $83,99→$84,72 | **+$34,10** (+0,86%) | irány: negatív (pont-becslés nincs) | **irány HIBÁS — pozitív** |
| 21:59:32 | EXEL | **TIME_STOP_MOC** | 110 | $53,52→$53,23 | **-$31,84** (-0,54%) | irány: negatív (pont-becslés nincs) | irány helyes |
| **Total** | | | | | **+$2,26** | | |

**🔴 Mintázat-ellenpélda (őszinte rögzítés)**: a CORT tp1_hit=false volt, **mégis pozitív** (+$34,10) — a CORT a 06-24-i korrekció után az entry fölé sodródott és ott time-stopolt. **Ez a 06-11 óta követett „tp1_hit=false → negatív" mintázat ELSŐ ellenpéldája.** A mintázat ezzel tp1_hit=false-ra **7 negatív / 1 pozitív** (n=8), tp1_hit=true → 2/2 pozitív. A mintázat gyengül — ahogy egy kis-mintás megfigyeléstől várható; rögzítem, hogy nem ragaszkodom hozzá. ✓ `exit_type` mindkettőre helyes ma.

## 3. Entries (2) — forrás: `pt_submit_2026-06-25.log`, `daily_metrics::execution`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 | entry_score |
|---|---|---|---|---|---|---|
| PFGC | Consumer Defensive | 63 | $106,43→$106,47 | +0,04% (semleges) | $100,91 / $110,57 / $114,70 | 83,88 (S_j 83,9) |
| SLGN | **Consumer Cyclical** | 128 | $44,67→$45,28 | +1,37% ⚠️ | $41,95 / $46,71 / $48,75 | 77,48 (S_j 77,5) |

PFGC visszahozza a Consumer Defensive-et (SJM kilépése után), SLGN **új szektor** (Consumer Cyclical). A könyv 5 szektor. SLGN slippage emelt (+1,37%). A pipeline 3-at sized (RBC 104,5 / SAIA 91,9 / TDG 89,0 — **mind Industrials**), de RBC+TDG már nyitott → a top-3-ból egy sem új belépő; PFGC/SLGN alacsonyabb rangról lépett be. **Megj.: a top-3 harmadik egymást követő napon tiszta Industrials** (§7 szelekciós koncentráció).

## 4. Nyitott pozíciók (8) — forrás: IBKR `get_account_positions` (06-25 close, verifikált)
| Ticker | days_held | Mark | Unrealized (IBKR) | next_action |
|---|---|---|---|---|
| AXTA | 4 | $34,73 | +$144,99 | HOLD |
| TDG | 1 | $1332,56 | +$109,24 | **TP1** (06-26 15:30, §9) ⚠️ |
| R | 2 | $269,67 | +$101,74 | HOLD |
| RBC | 3 | $648,89 | +$50,48 | **TP1** (06-26 15:30, §9) ⚠️ |
| PFGC | 0 | $107,27 | +$49,40 | HOLD |
| IEX | 3 | $228,07 | +$43,22 | HOLD |
| SLGN | 0 | $45,33 | +$5,40 | HOLD |
| NSA | 2 | $44,84 | -$55,00 | HOLD |
| **Total unrealized** | | | **+$449,47** | |

**A nyitott könyv +$449,47-re FORDULT** (06-24: -$421,56, napi swing ~+$871) — az Industrials-nevek (IEX, R, RBC) erős napja egy flat SPY mellett. 7/8 pozíció zöld, csak NSA mínusz. **Először net-pozitív a nyitott könyv régóta.**

**Net Liq-rekonciliáció (§6.4)**: $100 000 + $536,68 + $449,47 = $100 986,15 várt vs tény $101 348,69 → **+$362,54 reziduum** — a recent sáv alja (átlag ~$391±30). Stabil. Gazda: megfigyelés.

## 5. Ops-checklist
- ✓ `pt_reconcile` 22:15:06: „Reconciliation OK", state és IBKR egyező (8 ticker) — **22/22 éles silent OK**
- ✓ `pt_eod` fix tartja: „Trades(eod-fills): 0 | persisted: 2"; `P&L $+2.26`, `Cumulative +$536.68 [Day 27/63]` helyes
- ✓ IBKR positions vs `swing_positions`: 8 ticker, qty egyező
- ✓ Cron-időzítések: close 15:30:03 + 21:40:27/34 (EXEL, CORT MOC); submit 15:31:02; monitor 22:00:09 (2 flag: RBC, TDG TP1); metrics 22:10:02; eod 22:11:02; reconcile 22:15:01
- ⚠️ Cron `BEALLITASOK` legacy display — ismétlődő P3
- ✓ `exit_type` (EXEL, CORT TIME_STOP_MOC) helyes ma

## 6. Anomáliák (csak új/változott)
- **6.1 ÚJ P2 — RBC/TDG TP1-flag, de a close-mark a TP1-szint ALATT** — RBC TP1-re flagelve, de IBKR mark $648,89 < TP1 $667,07; TDG flagelve, mark $1332,56 < TP1 $1356,81. `hipotézis (két ág):` (a) a swing TP1-eval az intraday high-t nézi (RBC/TDG napon belül elérte a TP1-et, close alatta) → by design; (b) a TP1-flag téves (exit_type-determináció gyengeség, vagy stale TP1-szint). **Holnap dönti el**: ha 15:30-kor a fill a TP1-szint alatt (~mai mark) jön, a „TP1" címke félrevezető (early exit TP1-nek címkézve); ha a TP1-szinten/felette, akkor legitim intraday-high trigger. **Ez közvetlenül érinti, hogy a take-profit-aszály ténylegesen megtörik-e holnap.** Gazda: holnapi verifikáció (fill-ár vs TP1-szint), majd ha (b) → CC-task.
- **6.2 P2 (nyitva, Day 63-input)** — scoring_validation legacy-swing pooling. Nincs változás.
- **6.3 P2 (nyitva, Dev-chat)** — UW kivezetés. `uw_shadow` ma `avg_dp_pct=0,0`, `penalty_count=0` (3. napja vagy 0 vagy magas — ingadozás tart). Dev-chat.
- **6.4 P3 (megerősítve, ismétlődő)** — `exits_today::TP1=2` miközben ma 2 TIME_STOP futott (EXEL, CORT); a `2` a holnapra beállított RBC/TDG TP1-flageket számolja. A monitor log explicit. Gazda: CC-task (exits_today csak lefutott exitek). Megj.: ez a bug most TP1-nek címkézi a holnapi flageket, ami a heti/napi TP1-statisztikát is torzíthatja, ha onnan olvas
- **6.5 P3 (ismétlődő)** — planned-vs-broker entry; Net Liq-reziduum +$362,54 (sáv-alja).
- Nincs új P0/P1.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés nélkül)
- **Take-profit aszály — státusz**: technikailag **tart** (ma is 0 TP1/TP2 hit, mindkét exit TIME_STOP); a 06-11-i NSA TP2 óta 10 trading nap TP-hit nélkül. **DE holnap RBC+TDG TP1-re flagelve** — ha legitim (§6.1), ez törné meg az aszályt. A §6.1 nélkül nem jelenthető ki, hogy az aszály véget ér
- **Exit-kimenetek tp1_hit szerint (ELLENPÉLDÁVAL)**: tp1_hit=false → **7 negatív / 1 pozitív** (CORT +$34,10 az első kivétel); tp1_hit=true → 2/2 pozitív. n=10 exit. A mintázat már nem tiszta bináris — rögzítve
- **Nyitott könyv MTM-fordulat**: -$421,56 (06-24) → **+$449,47 (06-25)**, ~+$871 napi swing az Industrials-erőből egy flat SPY-n. Először net-pozitív régóta; 7/8 pozíció zöld
- **Industrials-koncentráció + szelekció**: a top-3 score **3. napja tiszta Industrials** (ma RBC/SAIA/TDG); a szektor 24,20% (4 név), közelít a 30% caphez. Ma nem nőtt (a belépők Cons.Def/Cyclical)
- **Cumulative**: +$536,68; a csúcsról (06-11 +$1 735) -$1 198, de a 2 napos stabilizáció (-$21, +$2) megállította a W25-W26 vérzést. MTM-alapon (Net Liq) +$1 349
- **Notional**: 45,61% (06-24) → 48,30% (ma)
- **VIX**: 19,56 → 19,08 (-2,42%) — enyhén vissza, magas szinten
- **Entry-slippage**: PFGC +0,04%, SLGN +1,37%
- **TP-hit ráta**: 12/29 exit (41,4%); pozitív-exit 18/29 (62,1%) — a CORT pozitív exit javította a pozitív-rátát

## 8. Heti kontextus — W26 D4
W26 négy nap: -$398,49 -$330,91 -$21,04 +$2,26 = **-$748,18**. A 2 napos stabilizáció után. **Holnap (06-26) péntek → W26 heti zárás** (5 nap), és RBC+TDG TP1-exitekkel indul
- **Megj.**: ha akarod, holnap futtasd a `weekly_metrics.py`-t a heti zárás blokkhoz

## 9. Holnap (2026-06-26, péntek, Day 28, W26 D5 — heti utolsó nap)
- **Várt exit: 2** — **RBC TP1 + TDG TP1**, `next_day_planned::exits_at_1530` (15:30, nem MOC — TP1 a nyitó-exit mechanikán). ⚠️ **§6.1 nyitott kérdés**: mindkettő close-markja a TP1-szint alatt — a fill-ár dönti el, hogy ez legitim TP1 (aszály-megtörés) vagy félrecímkézett early exit. RBC unrealized +$50,48, TDG +$109,24 → `irány-hipotézis:` pozitív (mindkettő nyereségben), **de pont-becslést nem adok** (a 15:30 nyitó-fill a holnapi nyitótól függ). **Ha ez TP1-partial (fél pozíció + trail), figyelni a qty-t** — eddig minden exit teljes pozíció volt
- Fókusz a 06-26 review-ban: (1) **§6.1 feloldás** — RBC/TDG fill-ár vs TP1-szint, legitim TP1-e; (2) **a take-profit-aszály megtörik-e**; (3) **W26 heti zárás blokk**; (4) TP1-partial vs teljes exit mechanika; (5) Net Liq vs $101 348,69; (6) Industrials-koncentráció
- **Net Liq-rögzítés**: 06-26 close summary a 22:16 CEST utáni ablakban

## 10. Freeze-sor
Paraméter-érintő változás ma: **nincs**.

## 11. A nap egy mondatban
Apró pozitív nap (+$2,26, az első 06-16 óta): a CORT TIME_STOP +$34,10-zel megtörte a „tp1_hit=false→negatív" mintázatot (első ellenpélda), a nyitott könyv az Industrials-erőből -$422-ről +$449-re fordult (Net Liq +$1 349), két új entry (PFGC, SLGN) ötödik szektorra bővített — és holnap RBC+TDG TP1-re flagelve, ami megtörhetné a 06-11 óta tartó take-profit-aszályt, ha a fill-ár megerősíti a TP1-szint elérését (§6.1 nyitott).
