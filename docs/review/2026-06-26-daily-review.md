# IFDS Daily Review — 2026-06-26 (péntek, Day 28/63 NYSE-count, W26 D5 — heti utolsó nap)

## 1. Fejléc
- **Day 28/63** — `day_number=28` ÉS `trading_days=28` egyező ✓
- **Realized net: +$3,37** (gross +$5,47; commission $2,10) — két TP1 partial exit (TDG +$35,75, RBC -$32,38). **2. egymást követő apró-pozitív nap.** Forrás: `daily_metrics`, `pending_exits`, broker-ledger (`matched=2`)
- **Cumulative: +$540,05 (+0,54%)** — gyakorlatilag flat 3 napja (-$21, +$2, +$3)
- **Net Liq (IBKR, tiszta 06-26 close ablak): $101 339,17** ✓ verifikált — a 06-25 horgonyról ($101 348,69) -$9,52 (flat nap egy -0,72% SPY mellett; a könyv tartotta magát). +$1 339 a startvonal fölött
- **Excess: +0,73%** (portfolio +0,01% vs SPY -0,72%, `daily_metrics`) — SPY-lefelé napon a flat realized pozitív excesst ad
- **Nyitott pozíciók: 8** (0 belépő, 0 teljes kilépő — RBC/TDG TP1 csak partial; IBKR + `swing_positions` + `pt_reconcile` egyező)

## 2. Exits (2 TP1 partial) — forrás: `pending_exits/2026-06-26.json` + broker-ledger
| Idő (CEST) | Ticker | Típus | Qty (partial) | Entry→Exit | Broker realized | TP1-szint | Megjegyzés |
|---|---|---|---|---|---|---|---|
| 15:32:44 | TDG | **TP1** (partial) | 2 / 4 | $1305,78→$1323,65 | **+$35,75** (+1,37%) | $1356,81 | fill a TP1-szint **alatt** |
| 15:32:42 | RBC | **TP1** (partial) | 4 / 9 | $643,55→$635,45 | **-$32,38** (-1,26%) | $667,07 | fill a TP1-szint **és az entry alatt** ⚠️ |
| **Total** | | | | | **+$3,37** | | |

**🔴 §6.1 FELOLDVA — három strukturális tanulság (mind első megjelenés a sorozatban):**
1. **A TP1 partial exit**: RBC 9→qty_remaining 5, TDG 4→2; `tp1_hit=true`, `trail_sl` beállítva (RBC 608,74 / TDG 1286,54). A TP1 a pozíció egy részét adja el, a maradékot trailing-eli. Eddig minden exit teljes pozíció volt — ez az első partial.
2. **A „TP1" flag NEM garantál profitot**: a RBC TP1 -$32,38-cal zárt, a fill ($635,45) a TP1-szint ($667,07) **és az entry ($643,55) alatt**. A 06-25-i eval flagelte (intraday high vélhetően elérte a TP1-et), de a végrehajtás **06-26 15:30-kor** történt, egy -0,72% SPY gap-down napon → veszteség.
3. **A flag→fill lag**: a TP1 a flag-nap **másnapján** 15:30-kor tölt, nem a TP1-áron és nem a flag-napon. Ez a lag az RBC-t „TP1"-ként mínuszba vitte. **Következmény a metrikákra**: az `exits.tp1=2` formálisan TP1-hitet rögzít, de a realizált kimenet (egyik nyereség, egyik veszteség) nem a TP1-árhoz kötött. Gazda: Day 63-input (a TP1-mechanika flag→fill lag a scoring/exit-értékelés tárgya); a címke-vs-valóság eltérés a §6.4 weekly-TP1-torzulást is magyarázza.

## 3. Entries (0)
Nincs új belépő. `selected_for_entry=0`: a top-3 score (RBC 105,0 / TDG 91,2 / ITT 90,1 — **mind Industrials, 4. egymást követő nap tiszta Industrials top-3**) közül RBC+TDG már nyitott, ITT nem lépett be (a max/szektor-logika vagy a rang miatt). `qualified_above_threshold=49`, de 0 belépő.

## 4. Nyitott pozíciók (8) — forrás: IBKR `get_account_positions` (06-26 close, verifikált)
| Ticker | days_held | Mark | Unrealized (IBKR) | next_action |
|---|---|---|---|---|
| PFGC | 1 | $110,44 | **+$249,31** | HOLD |
| SLGN | 1 | $46,23 | +$120,60 | HOLD |
| AXTA | 5 | $34,50 | +$111,42 | **TIME_STOP** (06-29, §9) |
| TDG | 2 | $1328,06 | +$45,62 | HOLD (qty 2, post-TP1 trail) |
| NSA | 3 | $45,43 | +$33,50 | HOLD |
| IEX | 4 | $227,19 | +$14,18 | HOLD |
| RBC | 4 | $630,20 | -$65,41 | HOLD (qty 5, post-TP1 trail $608,74) |
| R | 3 | $260,93 | -$90,54 | HOLD |
| **Total unrealized** | | | **+$418,68** | |

A nyitott könyv +$418,68 (06-25: +$449,47) — 6/8 zöld. PFGC szárnyal (+$249, Consumer Defensive), SLGN +$120. R és RBC mínusz (Industrials visszahúzott a -0,72% napon). **Notional 43,14%** (06-25: 48,30%) — a TP1-partialök csökkentették az Industrials-t **19,05%**-ra (06-25: 24,20%), a koncentráció enyhült.

**Net Liq-rekonciliáció**: $100 000 + $540,05 + $418,68 = $100 958,73 vs tény $101 339,17 → **+$380,44 reziduum** (sáv-közép, átlag ~$390±30). Stabil. Megfigyelés.

## 5. Ops-checklist
- ✓ `pt_reconcile` 22:15:06: „Reconciliation OK", state és IBKR egyező (8 ticker) — **23/23 éles silent OK**
- ✓ `pt_eod` fix tartja: „Trades(eod-fills): 0 | persisted: 2"; `P&L $+3.37`, `Cumulative +$540.05 [Day 28/63]` helyes
- ✓ IBKR positions vs `swing_positions`: 8 ticker, qty egyező (RBC 5, TDG 2 partial)
- ✓ Cron-időzítések: TP1 exits 15:32:42/44 (15:30 ablak); submit 15:31; monitor 22:00:09 (1 flag: AXTA TIME_STOP); metrics 22:10:02; eod 22:11:02; reconcile 22:15:01
- ⚠️ Cron `BEALLITASOK` legacy display — ismétlődő P3
- ⚠️ `daily_metrics::trades::exit_type="TP1"` mindkét sorra — ez **most helyes** (valóban TP1-flag volt), de a RBC esetén a „TP1" címke egy veszteséges next-day fillt takar (§2)

## 6. Anomáliák (csak új/változott)
- **6.1 FELOLDVA → Day 63-input** — RBC/TDG TP1: partial exit + flag→fill lag + „TP1" címke veszteséggel (RBC). Részletek §2. A take-profit-mechanika viselkedése rögzítve a Day 63 edge-audithoz.
- **6.2 ÚJ P2 — weekly_metrics TP1-szekció torzult** — a `2026-W26.md`: „TP1 hits 3/7, avg profit -$109,18" — de a héten csak 2 TP1 futott (RBC -32,38, TDG +35,75, valós avg +1,69). A 3-as szám és a -$109,18 avg **nem egyezik a broker-valósággal**. `hipotézis:` a §6.4 `exits_today` flag-számláló szennyezi a weekly TP1-aggregátot (a holnapi flageket TP1-hitként húzza be). Gazda: CC-task (weekly_metrics TP1-forrás: `exits{}` vagy broker-ledger, NE `exits_today`). **Ez most konkrét hibás riport-számot termelt, nem csak elvi kockázat.**
- **6.3 P2 (nyitva, Day 63-input)** — scoring_validation legacy-swing pooling. Nincs változás.
- **6.4 P3 (megerősítve, ismétlődő)** — `exits_today::TIME_STOP=1` miközben ma 2 TP1 futott; a `1` a hétfői AXTA_TIME_STOP flag. A §6.2 gyökéroka. Gazda: CC-task.
- **6.5 P2 (Dev-chat)** — UW kivezetés. `uw_shadow` ma is 0 penalty. Dev-chat.
- **6.6 ⚠️ Kétheti riport nem található** — a „biweekly report" említve, de a szinkronizált fában NINCS (`docs/analysis/`, `docs/analysis/weekly/`, `state/` átnézve — nincs biweekly fájl). `hipotézis:` más útvonal, vagy a script kimenete nem szinkronizálódott, vagy külön kézi anyag. Kérlek add meg az útvonalat vagy illeszd be — addig a kétheti zárást nem tudom a review-ba foglalni.
- Nincs új P0/P1.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés nélkül)
- **Take-profit aszály — formálisan megtört, de árnyaltan**: az `exits.tp1=2` az első TP1-rekord 06-10 óta (10 trading nap után). DE egyik (RBC) veszteséges volt a flag→fill lag miatt (§2), és mindkettő partial. Tehát a „TP-profit visszatért" állítás **nem tiszta** — a mechanika nyereség-realizálása a next-day fillen múlik, nem a TP1-áron
- **Exit-kimenetek tp1_hit szerint**: a partial-TP1 után RBC/TDG immár tp1_hit=true; a korábbi „tp1_hit=false→negatív" mintázat (7 neg / 1 poz, CORT) változatlan a teljes exitekre
- **Industrials-koncentráció enyhült**: 24,20% → 19,05% (TP1-partialök); de a top-3 score 4. napja tiszta Industrials → a szelekciós koncentráció megmarad, a notional-koncentrációt a partial-exitek csökkentik
- **Nyitott könyv**: +$449 (06-25) → +$418 (06-26), net-pozitív tartós; 6/8 zöld
- **Cumulative**: +$540,05; a csúcsról (06-11 +$1 735) -$1 195, de a W26 utolsó 3 napja stabilizálódott (flat). MTM (Net Liq) +$1 339
- **VIX**: 19,08 → 18,35 (-2,86%) — enyhülő
- **TP-hit ráta**: 14/31 exit (45,2%, a 2 TP1-gyel); pozitív-exit 19/31 (61,3%)

## 8. HETI ZÁRÁS — W26 (jún 22–26, 5 nap) — forrás: `docs/analysis/weekly/2026-W26.md`
- **Heti net: -$744,81** (gross -$735,79, commission -$9,02) — a 2. negatív hét sorozatban (W25 -$450,16); a deploy óta a **legnagyobb heti veszteség**
- **Heti excess: +1,65%** (portfolio -0,74% vs SPY **-2,39%**) — **pozitív excess egy erősen negatív SPY-héten**: a portfolio kevésbé esett mint a piac. Ez a long-only swing defenzív viselkedése egy risk-off héten (a W25 +0,90% és a W26 +1,65% excess két egymást követő pozitív-excess hét, miközben az abszolút P&L negatív)
- **Win-napok: 2/5** (06-25, 06-26 a két apró-pozitív)
- **Exit-mix (heti)**: TP1 ×2, MOC ×5, SL ×1 (a MENTAL_SL az SL-be sorolva) — 8 exit, az első TP1-ek a héten
- **⚠️ TP1-statisztika hibás** (§6.2): „avg profit -$109,18 / 3 hits" — broker-valóság 2 hit, avg +$1,69. weekly_metrics-fix kell
- **Slippage (heti): avg +0,90%**, worst +1,37% (SLGN)
- **Dinamikus küszöb**: zero-position 1/5, low-position 4/5
- **Heti egy mondatban**: a W26 a deploy legnagyobb heti vesztesége (-$744,81), de pozitív excess-szel (+1,65%) egy -2,39%-os SPY-héten — a long-only swing relatíve védett a risk-off héten, miközben abszolútban veszít

## 9. Hétfő (2026-06-29, Day 29, W27 D1)
- **Várt exit: 1** — **AXTA TIME_STOP**, days_held=5, tp1_hit=false, qty 146, 06-26 mark $34,50 vs entry $34,00, unrealized +$111,42 → `irány-hipotézis:` **a CORT-ellenpélda óta nem feltétlen negatív** (AXTA nyereségben áll, mint a CORT volt) — pont-becslést nem adok; figyelni, hogy a 2. tp1_hit=false-pozitív TIME_STOP lesz-e (ami tovább gyengítené a mintázatot)
- Fókusz a hétfői review-ban: (1) AXTA TIME_STOP realized + a tp1_hit-mintázat; (2) RBC/TDG trailing-maradék sorsa (post-TP1); (3) a TP1 flag→fill lag újabb esetei; (4) Net Liq vs $101 339,17; (5) §6.2 weekly TP1-fix státusz
- **Net Liq-rögzítés**: 06-29 close summary a 22:16 CEST utáni ablakban

## 10. Freeze-sor
Paraméter-érintő változás ma: **nincs**.

## 11. A nap egy mondatban
2. apró-pozitív nap (+$3,37): az első TP1-ek 06-10 óta (TDG +$35,75, RBC -$32,38) feloldták a §6.1-et, megmutatva hogy a TP1 partial exit + másnapi 15:30 fill, és hogy a „TP1" címke veszteséges is lehet (RBC a TP1-szint és entry alatt töltött); a W26 a deploy legnagyobb heti vesztesége (-$744,81) de pozitív excess-szel (+1,65%) egy -2,39%-os SPY-héten — és a weekly TP1-statisztika a flag-számláló bug miatt hibás számot (-$109,18 avg) termelt.
