Status: WIP
Updated: 2026-06-08
Note: **P1 (#1-#4) KÉSZ** (2026-06-08, 1916 passing). #1 VIX→Polygon I:VIX, #2 EOD timing (P&L a Part A-ból + cron 22:11), #3 NYSE day-count, #4 commission (live már rögzít + backfill + robustness-warning). Backfillek (`--apply` Mac Mini-n): backfill_polygon_vix.py, backfill_commission.py. **Hátra: P2 (#5 weekly slippage aggregálás, #6 portfolio_return_pct audit), P3 (#7, #8 statisztikai backlog).** Külön task a `2026-06-04-recorder-robust-realized-capture.md` (hétfői 6/8 live smoke).

# Data-quality fix-package (P1/P2/P3)

**Priority**: P1 (4 fix sürgős), P2 (2 megfigyelendő), P3 (2 statisztikai backlog)
**Becsült CC effort**: ~3-4h (P1 csak), +1-2h (P2)
**Érintett**: `scripts/paper_trading/daily_metrics.py`, `scripts/paper_trading/pt_eod.py`, `scripts/paper_trading/lib/ibkr_reconciliation.py`, `scripts/analysis/weekly_metrics.py`, cron-config (Mac Mini)

## Háttér

A Day 13 (2026-06-03), Day 14 (2026-06-04), Day 15 (2026-06-05) napi review-k során a `docs/review/` mappa-ban dokumentált finding-ek alapján 8 data-quality fix szükséges. A Part A robust-realized-capture (a Day 13-i `realizedPNL` aszinkron 0-incidens) **külön task-ban** (`2026-06-04-recorder-robust-realized-capture.md`, WIP, A.2 `ib.fills()` deploy-olva, hétfői 6/8 live smoke).

A scope-ot Tamás 2026-06-06-i két explicit kérése váltotta ki:
1. VIX adatforrás váltás FRED-ről Polygon `I:VIX`-re (FRED 1 napos késés)
2. A többi data-quality finding összeírása egy task-ba

---

## Scope — Prioritás szerint

### P1 — Pénzügyi-rögzítési + napi-tracking pontosság (4 fix)

#### Fix #1 — VIX adatforrás Polygon `I:VIX`-re váltás ✅ KÉSZ (2026-06-08)

> **Implementálva** (`daily_metrics._fetch_vix_from_polygon`, Polygon primary,
> FRED phase0 fallback). Backfill: `scripts/maintenance/backfill_polygon_vix.py`
> (dry-run validálva Day 1-15: 6/5=21.51 +39.68%, 6/4=15.40, 5/27=16.29).
> `--apply` Mac Mini-n futtatandó (state/ gitignored). 1902 passing. +6 teszt.

**Probléma**: a `daily_metrics::market::vix_close` mező a FRED VIX-ből vesz, ami 1 napos késéssel publikál (FRED EOD-batch). A 6/5 daily_metrics `vix_close: 15.78, vix_delta_pct: -5.0` — ez a 6/4 FRED-érték. A valódi 6/5 záró VIX (Tamás screenshot + IBKR + Polygon): **21.50**, **+39.70%** intraday ugrás (major risk-off).

**Hatás**: a `daily_metrics::market::vix_close` mező **rendszerszerűen 1 nappal lemarad**, ami:
- A 22:11-i (új) EOD Telegram-i render-ben téves VIX értéket mutat
- Az `excess_return` és `portfolio_return_pct` számolás kontextus-mezőjét torzítja
- A Strategic_review-i "VIX > 18 + 20+ napi átlag = leállítás" kritérium-kalibráció téves (a 6/5 valódi 21,50 már átlépte a 18-as küszöböt!)
- A `weekly_metrics.py` "low_vol_days/high_vol_days" számolás torzul

**Fix**:
- `daily_metrics.py` (vagy `phase0_diagnostics.py`) VIX-lekérés átállítása **Polygon `I:VIX`** ticker-re
- Endpoint: `https://api.polygon.io/v2/aggregates/v2/ticker/I:VIX/prev` (previous close) vagy `aggregates/v2/ticker/I:VIX/range/1/day/{from}/{to}` (historikus tartomány)
- Plan-B: ha a Polygon `I:VIX` késik vagy hibás → secondary fallback IBKR `get_price_snapshot(I:VIX)` (a connector már él)
- A `vix_delta_pct` is konzisztensen Polygon-tól (current close vs previous close)

**Acceptance criteria**:
- A `daily_metrics::market::vix_close` a Day N (NYSE záró napjának) valódi záró VIX-ét tartalmazza, NEM a Day N-1 értéket
- A `vix_delta_pct` konzisztens (current vs previous close, Polygon `I:VIX`)
- Backfill a Day 1-15 napokra (Polygon historikus `aggregates/v2/ticker/I:VIX/range/1/day/2026-05-18/2026-06-05`)
- Regresszió-teszt:
  - Day 15 (6/5): `vix_close = 21.50 ± 0.1`, `vix_delta_pct ≈ +39.7%`
  - Day 14 (6/4): `vix_close = 15.39 ± 0.1`
  - Day 8 (5/27, MOC katasztrófa): a valódi 5/27 záró VIX
- Unit-teszt mock-elve a Polygon válaszra

**Érintett fájlok**: `scripts/paper_trading/daily_metrics.py`, `scripts/paper_trading/phase0_diagnostics.py`

---

#### Fix #2 — EOD Telegram timing fix (22:05 → 22:11 cron-eltolás) ✅ KÉSZ (2026-06-08)

> **Implementálva**: `eod_report.resolve_eod_display_pnl` — a P&L today a Part A
> `daily_history[today]` net+commission-jéből (broker-authoritatív, a 21:40 MOC
> exitekkel), fallback az eod saját fill-jeire. Cron `scripts/crontab.md`-ben
> 22:05→22:11 (a 22:10 Part A UTÁN) — **Mac Mini-n Tamás alkalmazza**. +3 teszt.

**Probléma**: a `pt_eod.py` cron jelenleg **22:05-kor** fut, miközben a Part A `record_pending_exits` cron **22:10-kor**. Ezért a 22:05-i EOD Telegram:
- A 21:40-i MOC exit-eket nem fogja be (csak 22:10 után rögzül a Part A-ban)
- A `Cumulative` mező a Day N-1 utáni értéket mutat (Day 15: `Cumulative: $+199,50` mutatta, miközben Day 15 záró +$245,25)
- A `P&L today` csak a 15:30-i TP1 exit-eket fogja be (Day 15: $+252,43 mutatott, valódi +$63,84)

**Hatás**: a Telegram-i EOD-render **rendszerszerűen az előző napi cumulative-t mutatja** és a 21:40 MOC exit-eket kihagyja. Ez **valós-idejű operatív tracking-zavart** okoz Tamásnak.

**Fix**:
- Cron-eltolás `pt_eod.py`: **22:05 → 22:11** (a 22:10 Part A UTÁN, 22:15 reconcile ELŐTT)
- A `pt_eod.py` a `cumulative_pnl.json` legfrissebb állapotát olvassa (a Part A 22:10 cron lefutása után)

**Acceptance criteria**:
- A 22:11-i Telegram a Day N záró aktuális (Part A-rögzített) cumulative-t mutatja
- A `P&L today` MINDEN aznapi exit-et tartalmaz (15:30 TP1 + 21:40 MOC)
- Regresszió: a Day 15-i (6/5) 22:11-i Telegram a +$245,25 (broker-authoritative cumulative) és $+63,83 (Day 15 realized) értékeket mutatta volna

**Érintett fájlok**: `scripts/paper_trading/pt_eod.py`, **Mac Mini cron-config** (Tamás manuálisan)

---

#### Fix #3 — `[Day N/63]` mező egységesítés a NYSE-count szemantikára ✅ KÉSZ (2026-06-08)

> **Implementálva**: `eod_report.resolve_nyse_day_number` → `compute_trading_day_number`
> (NYSE-count) a log-sorokban + a legacy/dry-run fallback Telegram-ban. A swing
> Telegram (production) már korábban is NYSE day_number-t használt. +2 teszt.

**Probléma**: a `pt_eod.log` `[Day N/63]` jelenleg a régi `cumulative_pnl::trading_days` mezőt használja (P&L-entry-count szemantika: csak azon napokat számolja, amelyeken volt P&L-entry). A `daily_metrics::day_number` viszont **NYSE trading-day count** (5/18 = D1, ..., 6/5 = D14).

**Példák a Day 15-i log-ban**:
- `cumulative_pnl::trading_days: 13` (P&L-entry-count: 5/18, 19, 20, 21, 22, 26, 27, 28, 29, 6/2, 3, 4, 5 = 13 nap; a 5/29-i 0-entry beleszámol, 6/1-i 0-entry NEM)
- `daily_metrics::day_number: 14` (NYSE-count: 5/18, 19, 20, 21, 22, 26, 27, 28, 29, 6/1, 2, 3, 4, 5 = 14 nap)
- `pt_eod.log`: `[Day 12/63]` ← **TÉVES** (a Day 14 előtti `trading_days: 12` állapot, mert a 22:05 cron a 22:10 Part A előtt fut → még nem növelte a 13-ra)

**Hatás**: a Tamás-i mental-model a NYSE-count szerint dolgozik (a Day 21 checkpoint, Day 63 milestone mind NYSE-count). A Telegram-i `[Day N]` ezzel inkonzisztens.

**Fix**:
- `pt_eod.py` a `daily_metrics.day_number` mezőt használja a `[Day N/63]` rendereléshez
- A `cumulative_pnl::trading_days` mező megmarad (más statisztikai célokra, pl. weekly_metrics)

**Acceptance criteria**:
- A `pt_eod.log` és a Telegram `[Day N/63]` mező a NYSE-count szerint
- Day 15-i (6/5) Telegram: `[Day 14/63]` (NEM `[Day 12/63]`)
- Regresszió: Day 1 = `[Day 1/63]`, Day 8 = `[Day 7/63]`, Day 15 = `[Day 14/63]`

**Érintett fájlok**: `scripts/paper_trading/pt_eod.py`

---

#### Fix #4 — Commission rögzítés a Part A-ban (paralel `realized + commission`) ✅ KÉSZ (2026-06-08)

> **Megállapítás**: a `record_pending_exits` MÁR rögzíti a commission-t paralelben
> (`commission_delta=commission`, exit-leg SLD bázis). A 6/4+6/5 lokális 0 a
> pre-A.2 állapot (async commissionReport nem settle-ölt). **Hozzáadva**:
> robustness-warning ha broker_realized de commission==0 (`commission_zero_with_broker_realized`).
> **Backfill**: `scripts/maintenance/backfill_commission.py` + connector-derived
> `commission_backfill_map.json` (exit-leg, Day 1-15: 6/5=4.39, 6/4=3.92, 5/27=8.04;
> standardizálja a felfújt historikus round-trip értékeket). `--apply` Mac Mini-n.
> +5 teszt. **1916 passing.**

**Probléma**: a Day 14 + Day 15-i `daily_metrics.pnl.commission: 0.0` és a `cumulative_pnl::daily_history.{date}.commission: 0.0` (a Tamás-i restatement előtt, jelenleg már korrigálódott a 6/4 + 6/5 napokra a `restate_day_realized.py` futtatása által). DE a `record_pending_exits` cron **rendszerszerűen NEM rögzíti a commission-t paralelben** — a `realized_pnl` mező már net (commission bevonva), de a `commission` mezőt **külön audit-trail-ben** is rögzíteni kellene.

**Hatás**:
- A `weekly_metrics.py` "Commission: $X" sora **rendszerszerűen alulbecsüli** (a `restate_day_realized.py` manuális futtatása nélkül 0-t mutat)
- A jövő-beli audit-trail (Day 63 milestone, Day 90, élesítés) **nem tartalmazza** a swing-exit commission-eket
- Az "annualized friction" számolás torzul (a Strategic_review-i ~15-17% commission-drag mérése pontatlan)

**Fix**:
- `record_pending_exits` cron a `fetch_today_executions[ticker].commission` mezőt is rögzíti a `pending_exits/{date}.json` ledger-bejegyzésekben
- A `cumulative_pnl::daily_history.{date}.commission`-be aggregálva (paralelben a `realized_pnl`-vel)
- A `daily_metrics::pnl::commission`-be is rögzítve (a `build_daily_metrics` a cumulative-ból veszi)
- A safety-fix logika: ha a `commission` aszinkron 0 vagy hiányzik → fallback `get_account_trades`-re (mint a B opció az `ib.fills()` opció-2-vel)

**Acceptance criteria**:
- Day N záró után: `cumulative_pnl::daily_history.{N}.commission` a Day N összes swing-exit commission-jét tartalmazza
- Regresszió: Day 15 (6/5) commission ≈ **$4,40** (4 exit × ~$1,10/exit)
- Backfill a Day 1-15 napokra a connector `get_account_trades(DAYS_30)` alapján
- A `weekly_metrics.py` W23 "Commission" sora a 4 exit-nap × ~$1-4 commission-summát mutassa

**Érintett fájlok**: `scripts/paper_trading/lib/ibkr_reconciliation.py` (record_pending_exits), `scripts/paper_trading/daily_metrics.py` (build_daily_metrics)

---

### P2 — Másodlagos finding-ek (2 fix)

#### Fix #5 — `weekly_metrics.py` slippage_aggregation_complete

**Probléma**: a `docs/analysis/weekly/2026-W23.md` `Avg MKT fill slippage: -3.77%` és `Worst slippage: -3.77%` — **csak a MSM Day 12-i entry slippage-jét veszi figyelembe**. A W23-ban 4 új entry volt:
- WST (Day 10/6-1) slippage: csak state vs IBKR fill összehasonlítás kell
- MSM (Day 11/6-2): -3.77% (csak ezt veszi)
- BEN (Day 13/6-3): **-1.99% kedvező** (hiányzik!)
- VNO (Day 13/6-3): **-0.79% kedvező** (hiányzik!)
- FFIV (Day 15/6-5): **+0.01% pontos** (hiányzik!)

**Hatás**: a W23 statisztikai aggregátum **az MSM-i kiugró -3.77%-ot mutatja átlagként**, holott a valódi átlag ~-1.6% (4 entry súlyozott).

**Fix**:
- `weekly_metrics.py` az ÖSSZES `daily_metrics::execution::slippage_per_ticker` entry-t aggregálja a heti tartományban, NEM csak az első egyet
- `Avg MKT fill slippage`: súlyozott átlag (qty-vel) a 4 entry-ből
- `Worst slippage`: max(abs(slippage_pct))

**Acceptance criteria**:
- W23-i `Avg slippage` ≈ -1.6% (4 entry: -3.77% MSM, -1.99% BEN, -0.79% VNO, +0.01% FFIV, súlyozva qty-vel)
- W23-i `Worst slippage` = -3.77% (MSM)
- Backfill: `weekly_metrics.py --week 2026-W21` és `2026-W22` is helyes átlagok

**Érintett fájlok**: `scripts/analysis/weekly_metrics.py`

---

#### Fix #6 — `daily_metrics::portfolio_return_pct` definíció audit

**Probléma**: a Day 14 (6/4) `portfolio_return_pct: 0.24` és Day 15 (6/5) `portfolio_return_pct: -0.01` mezőértékek **nem konzisztensek** a Net Liq mozgással:
- Day 14 záró Net Liq ~ $100 273.85 (a `state/daily_equity.json::day_change: +808.59` szerint Day 13 záró $100 465.26 → Day 14 záró $101 273.85)
- Wait — várj. A `daily_equity` Day 13 utáni 100 465.26 → Day 14 utáni 101 273.85, ami +0.80% mozgás, NEM +0.24%
- Day 15 záró Net Liq $100 675.60 (IBKR direkt) — vs Day 14 záró $101 273.85 = -0.59% mozgás, NEM -0.01%

**Hatás**: a `excess_return::excess_pct` is ezzel inkonzisztens:
- Day 14: `excess_pct: -0.13` (portfolio 0.24% - SPY 0.37% = -0.13% ✓ konzisztens önmagával, de portfolio rosszul mérve)
- Day 15: `excess_pct: 2.57` (portfolio -0.01% - SPY -2.58% = +2.57% ✓ önmagával, de portfolio téves)

**Valódi Day 15 mérés a Net Liq alapján**:
- Day 14 záró → Day 15 záró: $101 273.85 → $100 675.60 = **-0.59%** portfolio mozgás
- SPY: -2.58%
- **Valódi excess: -0.59% - (-2.58%) = +1.99%** (NEM +2.57%)

**Akció**:
- A `portfolio_return_pct` számolás auditja: milyen Net Liq referencia-pontot használ?
- Várt definíció: `(Net Liq aznap záró - Net Liq előző-nap záró) / Net Liq előző-nap záró × 100`
- A `daily_equity.json` mezőből vesz, NEM egy közbenső becslésből

**Acceptance criteria**:
- A `portfolio_return_pct` az aznapi Net Liq% mozgása (előző nap záró → aznap záró), a `daily_equity.json`-ból
- Day 15 várt érték: ($100 675.60 - $101 273.85) / $101 273.85 × 100 ≈ **-0.59%** (NEM -0.01%)
- Day 14 várt érték: ($101 273.85 - $100 465.26) / $100 465.26 × 100 ≈ **+0.80%** (NEM +0.24%)
- A `excess_return::excess_pct` ezzel konzisztensen újraszámolva
- Regresszió a Day 1-15 napokra a `daily_equity.json` alapján

**Érintett fájlok**: `scripts/paper_trading/daily_metrics.py`

---

### P3 — Statisztikai megfigyelések (2 backlog)

#### Backlog #7 — Next-day MKT fill kockázat (TP1-limit-order opció vizsgálata)

**Probléma**: a swing pivot TP1-flag a Day N záró ár alapján (EOD eval), de a Day N+1 15:30 MKT fill ár a következő reggeli piaci helyzet függvénye. **Két ellentétes példa eddig**:
- **MSM Day 13→14**: TP1-flag a 6/3 záró $117.17 alapján → 6/4 fill $117.30 = **+0.11% kedvező** (~Day 13 záró mark közeli) ✓
- **BEN Day 14→15**: TP1-flag a 6/4 záró ~$32.16+ alapján → 6/5 fill $31.50 = **-2.05% kedvezőtlen** (-$87 alulteljesítés a Day 14 review-i prognózishoz képest) ⚠️
- **AMH Day 14→15**: TP1-flag 6/4 záró ~$32.96 alapján → 6/5 fill $32.88 = **-0.24%** ≈ semleges ✓

**Hatás**: a Day 14-15 review-mban dokumentált "1-nap-TP1 + kedvező entry-slippage" minta **részlegesen megdőlt** — a kedvező entry-slippage NEM garantálja a kedvező TP1-fill árát.

**Akció (statisztikai mintán, Day 21+ után)**:
- Az 1-2-3 napos gyors swing trade-eken a `next_day_fill_vs_tp1_level` eltérésének mérése
- Ha szignifikáns ($-50+ átlag eltérés a 10+ TP1 exit mintán): **TP1-limit-order opció design doc**
  - TP1 level-en limit order (NEM MKT)
  - Day-only TIF
  - Ha nem fillel a Day N+1 záróra → marad nyitva, Day N+2 EOD eval folytatódik

**Acceptance criteria**:
- Statisztikai elemzés Day 21+ után (legalább 10 TP1 exit a mintán)
- Ha negatív next-day fill kockázat szignifikáns: TP1-limit-order design doc + A/B teszt SIM-L2-vel

**Érintett**: backlog (megfigyelés, NEM implementáció most)

---

#### Backlog #8 — Major-bear-napi TIME_STOP MOC statisztikai mérés

**Probléma**: a Day 15-i SPY -2.58% major-bear-zuhanással a TIME_STOP MOC fill-ek kedvezőtlenebbül kötöttek:
- **ROIV TIME_STOP MOC**: várt -$43 → valódi **-$163.99** (-$120 alulteljesítés)
- **ST TIME_STOP MOC**: várt +$160 → valódi **-$24.60** (-$185 alulteljesítés)
- **Day 15 total realized**: várt +$457 → valódi **+$63.84** (-$393 alulteljesítés, főleg a TIME_STOP MOC-okon)

**Hatás**: a swing pivot `04-risks` §X.X-ben megfigyelendő minta — major-bear-napokon a TIME_STOP MOC fill-ek **rendszerszerűen rosszabbak** a Day N-1 záró mark-hoz képest.

**Akció (statisztikai mintán, Day 30+ után)**:
- A major-bear-napi (SPY < -1.5%) TIME_STOP MOC-ok átlag-vesztesége vs Day N-1 záró mark
- Ha szignifikáns (>$X átlag-veszteség a 5+ major-bear-napi TIME_STOP mintán): alternatív exit-mechanizmus design
  - Lehetőség A: TIME_STOP-elhalasztás 1 nappal (a major-bear-zuhanás utáni napon a piaci re-bound nagyobb)
  - Lehetőség B: TIME_STOP limit-order @ Day N-1 záró mark, GTC 1-nap

**Acceptance criteria**:
- Statisztikai elemzés Day 30+ után (legalább 5 major-bear-napi TIME_STOP)
- Ha szignifikáns: TIME_STOP-elhalasztás vagy alternatív exit-mechanizmus design

**Érintett**: backlog (megfigyelés)

---

## Deploy-sorrend (javasolt)

### Hétvégi deploy (szombat-vasárnap 6/6-6/7)

A P1 #1-#4 fix-ek **mind izoláltak, kis kockázatúak**, érdemes lehet hétvégén deploy-olni a hétfői (6/8) live smoke előtt:

1. **#1 VIX Polygon `I:VIX`** — gyors, izolált változás (1 endpoint-csere + backfill script)
2. **#2 EOD Telegram timing** — cron-config + render-logika (a `pt_eod.py` 22:05 → 22:11)
3. **#3 Day-N unification** — render-logika (a `pt_eod.py` és Telegram-template `daily_metrics.day_number`-t használ)
4. **#4 Commission rögzítés** — a Part A logika (paralel `realized + commission` a record_pending_exits-ben)

Megjegyzés: **#4 függ a `2026-06-04-recorder-robust-realized-capture.md` (A.2) `ib.fills()` deploy-tól** (commit `f95e56d`). Ha az (A.2) opció hétfői (6/8) live smoke-ja zöld, a #4 robust-an működik.

### Hétfői (6/8) live smoke

Az AMH TIME_STOP MOC (várt ~+$170 realized) az első éles teszt a kombinált fix-eknek:
- A `recorder-robust-realized-capture` task (A.2) `ib.fills()` opció verifikációja
- Az új task #4 commission rögzítés éles tesztje
- A #1 VIX Polygon I:VIX a 22:11-i Telegram-on
- A #3 Day-N: `[Day 15/63]` (NEM `[Day 13/63]`)

### P2 deploy (hét közben)

- **#5 weekly_metrics.py slippage_aggregation_complete**
- **#6 portfolio_return_pct definíció audit + javítás**

### P3 backlog (Day 21+ után)

- #7 statisztikai TP1 next-day fill mérés
- #8 statisztikai major-bear-napi TIME_STOP mérés

---

## Verifikáció

### Pre-deploy

- Full suite zöld (baseline: 1875 test passing)
- Linter + format
- Unit-tesztek a #1 (Polygon I:VIX mock), #4 (commission mock), #5 (slippage aggregation), #6 (portfolio_return_pct számolás)

### Post-deploy (hétfő 6/8 esti EOD után)

- **Day 15 (6/5) backfill validáció**:
  - `vix_close = 21.50 ± 0.1, vix_delta_pct ≈ +39.7%` (Polygon)
  - `commission = $4.40 ± 0.1` (4 exit × ~$1.10)
  - `portfolio_return_pct ≈ -0.59%` (Net Liq alapján, NEM -0.01%)
  - `excess_pct ≈ +1.99%` (a -0.59% portfolio - (-2.58%) SPY)
- **Day 16 (6/8) éles**:
  - Telegram 22:11-kor a teljes Day 16 cumulative-t mutat (várt ~+$415, ha AMH TIME_STOP MOC +$170)
  - `[Day 15/63]` (NYSE-count)
  - VIX a Polygon-tól (a Day 16 záró érték)
  - Commission a 22:11-i render-ben

### Sikerkritérium

Day 16 (6/8) EOD Telegram a **teljes-tisztított architektúrán**: helyes Day-N, helyes Cumulative, helyes VIX (Polygon I:VIX), helyes commission, helyes portfolio_return_pct.

---

## Kapcsolódó task-ok

- **`2026-06-04-recorder-robust-realized-capture.md`** (WIP) — Part A robust-realized-capture, hétfői 6/8 live smoke. A #4 commission rögzítés ehhez függ.
- **`2026-06-01-telegram-eod-finomitas.md`** (KÉSZ, deploy 2026-06-03) — Telegram EOD render-tartalom (NYSE Day-N, top movers, day-change, Day 21 chkpt). A #2 + #3 ennek folytatása.
- **`2026-05-28-automated-daily-review-pipeline.md`** (P2 backlog) — autonóm review-pipeline. A #6 portfolio_return_pct audit a cross-check-rétegéhez tartozik.

---

## Backfill scriptek (CC implementáció része)

A P1 fix-ek deploy-ja után a Day 1-15 napi adatok backfill-elése:

- **#1**: `scripts/maintenance/backfill_polygon_vix.py --start 2026-05-18 --end 2026-06-05` (Polygon historikus aggregates)
- **#4**: `scripts/maintenance/backfill_commission.py --start 2026-05-18 --end 2026-06-05` (connector `get_account_trades(DAYS_30)`)
- **#6**: `scripts/maintenance/backfill_portfolio_return.py --start 2026-05-18 --end 2026-06-05` (Net Liq `daily_equity.json` alapján)

A backfill scriptek **idempotensek** (ismételt futtatás biztonságos), és a `cumulative_pnl.json` + `daily_metrics/*.json` fájlokat in-place módosítják (backup-tal).

---

**Vége.**
