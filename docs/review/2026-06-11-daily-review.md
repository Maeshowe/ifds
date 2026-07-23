# IFDS Daily Review — 2026-06-11 (csütörtök, Day 18/63 NYSE-count, W24 D4)

## 1. Fejléc
- **Day 18/63** (NYSE-count, `daily_metrics::day_number`; megj.: `cumulative_pnl::trading_days=17`, a `daily_history`-ből a 2026-06-01 sor hiányzik — §6.4)
- **Realized net: +$335,97** (gross +$338,19; commission $2,22) — forrás: `daily_metrics/2026-06-11.json::pnl`, IBKR `get_account_trades(TODAY)` egyező
- **Cumulative: +$1 735,02 (+1,74%)** — `cumulative_pnl.json`
- **Net Liq (IBKR `get_account_summary`, 22:00 után): $101 796,61** — napi Δ a ma reggeli 08:11 CEST IBKR-snapshothoz ($101 303,20) képest **+$493,41**; a Day 17 review-ban rögzített záróhoz ($101 359,11) képest +$437,50 ⚠️ (a két referencia közti -$55,91 reggeli delta feloldatlan — §6.5)
- **Excess: -1,36%** (portfolio +0,34% — realized-net% / initial capital szemantika, `daily_metrics::excess_return` — vs SPY +1,70%)
- **Nyitott pozíciók: 6** (IBKR `get_account_positions` és `swing_positions.json` egyező)

## 2. Exits (2) — forrás: `pending_exits/2026-06-11.json` + IBKR trades
| Idő (CEST) | Ticker | Típus | Qty | Entry→Fill | Broker realized | Várt (06-10 review §6.1) | Eltérés |
|---|---|---|---|---|---|---|---|
| 15:30:23 | NSA | **TP2** | 94 | $43,43→$45,30 (NYSE) | **+$176,05** | +$204 — +$262 (feltevés: fill $45,60–46,21) | **-$28 a sáv alja alatt** |
| 21:59:42 | BEN | TIME_STOP (MOC) | 126 | $30,51→$31,78 (NYSE MOC) | **+$159,92** | +$62 (feltevés: fill ~$31,00) | **+$98 a várt felett** |
| **Total** | | | | | **+$335,97** | +$266 — +$324 | **+$12 a sáv teteje fölött** |

Várt-vs-tény megjegyzések: a NSA TP2 fill ($45,30) a TP2 levelt ($46,21) nem érte el — a teljes NSA trade (TP1 +$159,13 + TP2 +$176,05 = +$335,18) a 06-10-i +$363–421 prognózis alatt zárt -$28-cal. A BEN-eltérés oka: a fill-feltevés ($31,00) a Day 17 záró trail-szinten állt, a tényleges MOC $31,78. Cumulative várt +$1 665–1 723 → tény +$1 735,02.

## 3. Entries (2) — forrás: `pt_submit_2026-06-11.log`, `daily_metrics::execution`, IBKR trades
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 |
|---|---|---|---|---|---|
| NSA (self-reentry) | Real Estate | 153 | $45,42→$45,86 | +0,97% kedvezőtlen | $43,48 / $46,88 / $48,33 |
| JAZZ | Healthcare | 24 | $229,63→$234,80 | **+2,25% kedvezőtlen** ⚠️ | $215,33 / $240,36 / $251,09 |

NSA self-reentry: TP2 SELL 13:30:23Z → új BUY 13:31:08Z (45 mp), 2. eset a 06-10-i VNO után. JAZZ slippage a napi avg (1,14%) felett; a planned a 12:30-as execution_plan ára, a fill 15:31-kor, +1,70% SPY-napon — §6.3.

## 4. Nyitott pozíciók (6) — forrás: `swing_positions.json` + IBKR positions (mark, unrealized)
| Ticker | days_held | Mark | Unrealized | Stop-buffer | next_action |
|---|---|---|---|---|---|
| ACHC | 2 | $24,89 | -$87,01 | 8,2% (stop $22,84) | HOLD |
| FFIV | 4 | $393,84 | -$179,20 | 3,1% (stop $381,52) ⚠️ | HOLD |
| JAZZ | 0 | $236,40 | +$37,40 | 8,9% (stop $215,33) | HOLD |
| NSA | 0 | $45,51 | -$54,55 | 4,5% (stop $43,48) | HOLD |
| TKR | 3 | $137,40 | +$73,29 | 3,5% (trail $132,55, frissült 128,63-ról) | HOLD |
| VNO | 1 | $38,97 | +$31,00 | 6,9% (stop $36,27) | HOLD |
| **Total unrealized** | | | **-$179,07** | | |

Notional $29 723,02 (29,72% equity); sector observed max Real Estate 13,1% (VNO+NSA) a 30% cap alatt (`daily_metrics::swing_state`).

## 5. Ops-checklist
- ⚠️ `pt_reconcile_2026-06-11.log` **hiányzik a MacBook-szinkronból** — a silent-OK számláló **12/12-n marad, a 13. nem verifikálható** (§6.1)
- ⚠️ `pt_eod_2026-06-11.log` **hiányzik** — Telegram-render egyezés ma nem ellenőrizhető (§6.1)
- ✓ Cron-időzítések: intraday 14:30:00–14:32:12; close 15:30:06; submit 15:31:01; BEN MOC submit 21:40:06 (a 06-10-i 21:44-es késés nem ismétlődött); monitor 22:00:09; daily_metrics 22:10:01
- ⚠️ Cron log: 2× UW HTTP 429 (RRX, BEN `greek-exposure/strike`, attempt 3/3); Phase 5: 2 ticker excluded NEGATIVE regime
- ✓ `daily_metrics` vs IBKR: fillek, realized P&L, commission egyező
- ⚠️ `daily_metrics::trades::details::NSA::exit_type: "TP1"` — HIBÁS, kanonikus `pending_exits`: TP2 (ismert P1, első: 06-10 VNO, 06-10 review §5.1 — a fix még nem deployolt)

## 6. Anomáliák (csak új/változott)
- **6.1 ÚJ P1?** — `pt_reconcile` és `pt_eod` log hiányzik a szinkronizált fában; a `pt_daily_metrics` 22:10:13-kor írt. `hipotézis:` a sync a 22:11/22:15-ös cron-slotok előtt futott — ellenőrzés: sync újrafuttatás, és ha utána is hiányzik → cron-kimaradás, P1 CC-task. Gazda: Tamás (re-sync) → utána döntés.
- **6.2 ÚJ P3** — cron `BEALLITASOK` blokk legacy display-értékeket mutat (Risk per trade 0,7%/$700, Max per sector 2, weights flow=0,60/funda=0,10/tech=0,30), miközben a sized risk $297–349/pozíció (a 0,35%-os swing-paraméterrel konzisztens). `hipotézis:` display-only stale print — gazda: CC-task (verifikáció, hogy a futó config a swing-értékeket használja).
- **6.3 P3 megfigyelés** — JAZZ entry-slippage +2,25% (planned a 12:30 plan-ből, fill 15:31). Forrás: `daily_metrics::execution`. Gazda: megfigyelés.
- **6.4 ÚJ P3** — `cumulative_pnl::trading_days=17` vs `daily_metrics::day_number=18`: a `daily_history`-ből a 2026-06-01 sor hiányzik. Gazda: CC-task (backfill vagy számláló-egyeztetés).
- **6.5 P2 megfigyelés (ma reggelről)** — IBKR Net Liq 08:11 CEST: $101 303,20 vs a Day 17 review-ban rögzített záró $101 359,11 (-$55,91, nulla fill mellett). `hipotézis:` díj/kamat-tétel vagy snapshot-időpont-különbség — ellenőrzés: a holnapi reggeli summary + a (re-sync utáni) reconcile log. Gazda: megfigyelés.
- Ismert, visszatérő: `exit_type` fill-timestamp bug (06-10 §5.1, ma NSA-n ismétlődött — §5 utolsó sor); `portfolio_return_pct` realized-alapú szemantika (#6 fix inaktív, első: 06-09/06-10 §5.3).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés nélkül)
- **Next-day MKT fill eltérés**: NSA TP2 fill $45,30 vs level $46,21 = -1,97% kedvezőtlen → **n=6, átlag -1,19%** (az 5 korábbi átlag -1,03% + mai eset; számítás: review-soros könyvelés)
- **Self-reentry**: **n=2** (VNO 06-10: entry $38,77, mai mark $38,97, +$31 unrealized, nyitott; NSA 06-11: entry $45,86, day-0 mark $45,51, -$55 unrealized)
- **Major risk-off napok excess**: n=2, átlag +2,28% — ma nem risk-off nap (SPY +1,70%), nincs új eset
- **TP-hit ráta**: 12/19 exit (63,2%); **pozitív-exit ráta**: 16/19 (84,2%); TP2-hit: 3/19 — n=19 exit a 05-18 deploy óta
- **Daily-eval fordulatok**: 8/10, ma új eset nincs

## 8. Holnap (péntek, 2026-06-12, W24 D5)
- **Várt exit: 0** — `pt_monitor` 22:00:09: „Evaluated 6 positions — 0 exit flags set"; várt realized $0 (feltevés: nincs intraday mental-stop-sértés a napi eval előtt)
- Fókusz: (1) reconcile + eod log re-sync és §6.1 feloldás; (2) FFIV 3,1% stop-buffer; (3) NSA + JAZZ day-1 mark; (4) §6.5 Net Liq-delta visszamérés a reggeli summary-vel; (5) **heti zárás blokk** (péntek)

## 9. Freeze-sor
Paraméter-érintő változás ma: **nincs**.

## 10. A nap egy mondatban
Két pozitív exit (NSA TP2 +$176, BEN TIME_STOP +$160) +$335,97 realized napot adott, a cumulative +$1 735,02-re lépett, két új entry (NSA self-reentry, JAZZ) nyílt, a reconcile- és eod-log a szinkronból hiányzik.
