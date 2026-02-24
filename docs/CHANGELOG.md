# IFDS v2.0 Changelog

> Build Cycle BC1 → BC19 | 2026-02-06 – 2026-02-18

---

## IBKR Connection Hardening + Telegram Phase 2 Breakdown (848 tests)

### IBKR Connection Hardening
- `connect()` retry logika: konfigurálható `max_retries=3`, `retry_delay=5.0s`, `timeout=15.0s`
- Port konstansok: `PAPER_PORT=7497`, `LIVE_PORT=7496`, `DEFAULT_CLIENT_ID=10`
- Env var override: `IBKR_CONNECT_MAX_RETRIES`, `IBKR_CONNECT_RETRY_DELAY`, `IBKR_CONNECT_TIMEOUT`
- `_send_telegram_alert()`: Telegram értesítés ha minden retry kimerül
- Retry közben `ib.disconnect()` hívás (clean reconnect)
- 6 új teszt (`test_ibkr_connection.py`)

### Telegram Phase 2 Earnings Breakdown
- `Phase2Result` bővítés: `bulk_excluded_count`, `ticker_specific_excluded_count` mezők
- `_exclude_earnings()` return type: 2-tuple → 4-tuple `(filtered, excluded, bulk_n, ticker_n)`
- Telegram Phase 2 sor: `Earnings excluded: 12 (bulk=10, ticker-specific=2)` — csak ha ticker_specific > 0
- 3 új teszt (`TestPhase2EarningsBreakdown` in `test_earnings_telegram.py`)

---

## Earnings Date Telegram + Zombie Hunter Fix (839 tests)

### Earnings Date Column in Telegram Exec Table
- `FMPClient.get_next_earnings_date()`: ticker-specific `/stable/earnings?symbol=` endpoint
- `_format_exec_table()`: opcionális `earnings_map` paraméter → EARN oszlop (MM-DD vagy N/A)
- Format chain: `send_daily_report()` → `_format_success()` → `_format_phases_5_to_6()` — `fmp` param átadás
- Pipeline runner: dedikált FMPTelegram client a Telegram híváshoz
- 16 új teszt (`test_earnings_telegram.py`)
- **Trigger**: KEP earnings dátum hibás volt a bulk FMP calendar-ban

### Zombie Hunter — Ticker-specific Earnings Fallback
- `_exclude_earnings()` kétlépcsős megközelítés:
  - **Pass 1**: Bulk `/stable/earnings-calendar` (változatlan, gyors)
  - **Pass 2**: `/stable/earnings?symbol=` per-ticker a survivor-okra (`ThreadPoolExecutor`, max_workers=20)
- Fail-open policy: API hiba → ticker átengedett (WARNING log)
- Summary log: `bulk=N, ticker-specific=M` — látható melyik pass mit fogott
- 6 új teszt (`TestEarningsExclusionPass2` in `test_phase2.py`)
- **Trigger**: ALC (Feb 24) és KEP (Feb 23) kimaradt a bulk calendar-ból

---

## AGG Telegram Fix + Warning Cleanup (817 tests)

### AGG Benchmark in Telegram Sector Table
- **Bugfix**: AGG (iShares Core U.S. Aggregate Bond ETF) benchmark sor hiányzott a Telegram szektortáblázatból
- `PipelineContext.agg_benchmark` mező hozzáadva (`market.py`)
- `runner.py`: `ctx.agg_benchmark = agg_benchmark` mentés Phase 3-ban
- `telegram.py`: `_format_sector_table()` kapott `benchmark` paramétert — AGG sor szeparátorral a tábla végén
- 7 új teszt (`test_agg_telegram_fix.py`)

### Test Warning Cleanup
- **AsyncMock coroutine warning**: `_run_phase1_async` patch `new=MagicMock()`-kal (asyncio.run is mock → coroutine sosem awaited)
- **scipy precision warning**: paired t-test adatokhoz kis noise hozzáadva (identikus differenciák → catastrophic cancellation)
- **Eredmény**: 817 passed, 0 warnings

---

## BC18-prep — Trading Calendar + Danger Zone + Cache TTL Fix (810 tests)

### D1: NYSE Trading Calendar (`exchange_calendars`)
- **New module**: `src/ifds/utils/trading_calendar.py`
  - `is_trading_day()` — NYSE ünnepnap + hétvége detekció
  - `next_trading_day()`, `prev_trading_day()` — n kereskedési nap előre/hátra
  - `trading_days_between()` — kereskedési napok listája tartományban
  - `add_trading_days()` — n kereskedési nap hozzáadás (pozitív/negatív)
  - `count_trading_days()` — kereskedési napok száma két dátum között
- **Dependency**: `exchange_calendars` v4.13.1 (NYSE=XNYS, cached singleton)
- Integrálva: SimEngine `validator.py` — `to_date` számítás kereskedési napokkal

### D2: Bottom 10 Danger Zone Filter (T3)
- **New function**: `_is_danger_zone()` in `phase4_stocks.py`
  - D/E > 5.0, net margin < -10%, interest coverage < 1.0
  - 2+ szignál kell a szűréshez (false positive elkerülés)
- Integrálva: Phase 4 sync + async path (step 4b, funda scoring után, combined score előtt)
- `danger_zone_count` hozzáadva `Phase4Result`-hoz (`market.py`)
- 5 TUNING konfig kulcs: `danger_zone_enabled`, `_debt_equity`, `_net_margin`, `_interest_coverage`, `_min_signals`

### D3: Cache TTL Fix (forward-looking date ranges)
- `to_date = min(today, raw_to)` — jövőbeli dátumok cap-elése stale cache elkerülésére
- Kereskedési naptár használat pontosabb tartományhoz (fallback: calendar days + 5)
- Tesztek: 26 új (15 calendar + 9 danger zone + 2 cache TTL)

---

## BC19 — SIM-L2 Mód 1: Parameter Sweep + Phase 4 Snapshot (784 tests)

### Deliverable 1: Parameter Sweep Engine
- **New module**: `src/ifds/sim/replay.py` — multi-variant bracket order comparison
  - `recalculate_bracket()` — ATR-implied recalculation from original SL: `ATR = (entry - stop) / original_sl_atr_mult`
  - `load_variants_from_yaml()` — YAML config loading for variant definitions
  - `run_comparison()` — full orchestrator: load CSVs, fetch bars once, run N variants, compare
  - `run_comparison_with_bars()` — offline testing version (pre-provided bars)
- **New module**: `src/ifds/sim/comparison.py` — statistical comparison (scipy)
  - `compare_variants()` — first variant = baseline, rest = challengers
  - Paired t-test (`scipy.stats.ttest_rel`) on per-trade P&L matched by (ticker, run_date)
  - `MIN_PAIRED_TRADES = 30` — below this → `insufficient_data=True`
- **Extended**: `src/ifds/sim/report.py` — comparison report
  - `print_comparison_report()` — colorama console: baseline vs challengers, ΔP&L, Δwin rate, p-value
  - `write_comparison_csv()` — CSV with variant metrics + deltas + significance
- **Extended**: `src/ifds/sim/models.py` — L2 dataclasses
  - `SimVariant` (name, description, overrides, trades, summary)
  - `VariantDelta` (pnl_delta, win_rate deltas, p_value, is_significant)
  - `ComparisonReport` (baseline, challengers, deltas)
  - `ValidationSummary.fill_rate` property
- **CLI**: `python -m ifds compare` subcommand
  - `--config variants.yaml` — YAML-based multi-variant definition
  - `--baseline` / `--challenger` — inline variant naming
  - `--override-sl-atr`, `--override-tp1-atr`, `--override-tp2-atr`, `--override-hold-days`

### Deliverable 2: Phase 4 Snapshot Persistence
- **New module**: `src/ifds/data/phase4_snapshot.py`
  - `save_phase4_snapshot()` — daily gzipped JSON (`{date}.json.gz`) of StockAnalysis data
  - `load_phase4_snapshot()` — load by date string, returns list of flat dicts
  - `_stock_to_dict()` — flat dict from StockAnalysis (technical + flow + fundamental fields)
- **Pipeline wired**: Phase 4 snapshot saved automatically after Phase 6 in `runner.py`
- **Config**: `phase4_snapshot_enabled=True`, `phase4_snapshot_dir="state/phase4_snapshots"`
- Tesztek: 32 új (24 test_sim_replay.py + 8 test_phase4_snapshot.py)

---

## Paper Trading + Bugfixes (2026-02-17 – 2026-02-18)

### IBKR Paper Trading Module
- **New module**: `scripts/paper_trading/` — 21-day daytrading test via IBKR Paper ($100K)
  - `submit_orders.py` — CSV → two independent bracket orders per ticker (33% TP1 / 67% TP2), Adaptive algo, DAY TIF
  - `close_positions.py` — MOC close for remaining positions at 15:45 ET
  - `eod_report.py` — EOD report, daily CSV, cumulative P&L JSON, Telegram summary
  - `nuke.py` — Emergency cancel all orders + close all positions (MKT via SMART)
  - `lib/connection.py` — IBKR Gateway connector (port 7497, Python 3.14+ asyncio compat)
  - `lib/orders.py` — Bracket order creation, MOC orders, contract validation
- Safety rails: $100K exposure limit, circuit breaker at -$5K, min qty 2, idempotency check, CVR/non-STK filter
- `--dry-run` mode in submit_orders + eod_report sends Telegram without IBKR connection
- Cron: 15:35 submit, 21:45 MOC close, 22:05 EOD report (CET, Mon-Fri)

### Bugfixes
- **close_positions.py late-fill bug**: Cancel all unfilled IFDS bracket orders (orderRef `IFDS_*`) before querying positions for MOC — prevents overnight carry from late fills after 15:50 ET cutoff
- **OBSIDIAN day counter**: Added `baseline_days` field to `ObsidianAnalysis`, populated from store entry count. Telegram now shows actual `day N/21` instead of hardcoded "day 1/21"
- **nuke.py contract routing**: `qualifyContracts()` + `Stock(conId=..., exchange='SMART')` instead of reusing position contract (avoids Error 10311)

### Company Intel v2
- `scripts/company_intel.py` — 4 new FMP endpoints (profile, grades-consensus, grades, news/stock)
- English prompt with 10 data sources, anti-hallucination rules, max 200 words
- Transcript: first 1500 + last 1500 chars (captures analyst Q&A)

---

## SIM-L1 — Forward Validation Engine (752 tests)

**SimEngine Level 1: bracket order simulation from execution plan CSVs**

- **New module**: `src/ifds/sim/` — designed for Level 2 (replay) and Level 3 (full backtest) extension
  - `models.py` — Trade + ValidationSummary dataclasses
  - `broker_sim.py` — IBKR bracket order simulation (33/66% qty split)
  - `validator.py` — CSV loading, async Polygon bar fetch, summary aggregation
  - `report.py` — Console report (colorama), CSV trades, JSON summary
- **Bracket Logic**:
  - Fill check: D+1 low <= entry → filled @ entry (LONG); high >= entry (SHORT)
  - Fill window: 1 day (IBKR bot cancels next day)
  - Two parallel legs: Leg1 (33% qty → TP1/SL), Leg2 (66% qty → TP2/SL)
  - Same-day TP+stop ambiguity → conservative: stop hit (pessimistic)
  - Expired trades: exit @ close of last bar after max_hold_days (10)
- **Validator**: `validate_execution_plans(output_dir, polygon_api_key)` — full orchestrator
  - Loads all `execution_plan_*.csv` files (skips today's date)
  - Async Polygon bar fetch with semaphore=10, FileCache wired
  - `validate_trades_with_bars()` for offline testing without API
- **Report Output**:
  - Console: colorama report with fill rate, leg win rates, P&L stats, GEX regime breakdown
  - `validation_trades.csv` (28 columns) + `validation_summary.json`
- **Aggregation**: P&L by GEX regime, win rate by score bucket (70-80, 80-90, 90+)
- Tesztek: 24 új (test_sim_validator.py)

### Freshness Alpha Fix

- **Uncapped freshness bonus**: `combined_score = original * bonus` (was `min(100.0, original * bonus)`)
  - Problem: with empty signal_history, ALL tickers FRESH → capped at 100 → identical M_utility → no ranking differentiation
  - Solution: let combined_score go above 100 (max: 95 × 1.5 = 142.5, clipping already at 95)
  - M_utility now differentiates: `1.0 + (score - 85) / 100` gives different values per ticker

---

## BC16 — Phase 1 Async + Semaphore Tuning + Factor Volatility (728 tests)

**Phase 1 async migration, final semaphore tuning, OBSIDIAN factor volatility framework**

- **Phase 1 Async**: `_run_phase1_async()` in `phase1_regime.py`
  - `_fetch_daily_history_async()` — `asyncio.gather` for ~235 grouped daily calls
  - Dispatch: `if async_enabled → asyncio.run(_run_phase1_async(...))`
  - Pure computation unchanged: `_calculate_daily_ratios`, `_calculate_sector_bmi`, `_classify_bmi`, `_detect_divergence`
- **Semaphore Tuning** (final values):
  - `async_sem_polygon`: 5 → **10** (headroom for parallel phases)
  - `async_sem_fmp`: 8 → **5** → **8** (429 at 12, stable at 8)
  - `async_max_tickers`: 10 → **8** → **10** (429 at 15, stable at 10)
- **Factor Volatility Framework** (OBSIDIAN extension):
  - `_compute_factor_volatility()` — rolling σ per feature (window=20)
  - `_compute_median_rolling_sigmas()` — median of rolling σ windows
  - `_compute_regime_confidence()` — stability measure: `1.0 - min(1.0, σ/median_σ)`, floored at 0.6
- **VOLATILE regime** (8th MM regime): σ_gex > 2× median AND σ_dex > 2× median → multiplier **0.60**
  - Priority: checked first (before Γ⁺), fires before all other regime rules
  - Final multiplier: `base_mult × max(floor, confidence)`
- **Unusualness σ_20 weighting**: `S = Σ(w × |z| × (1 + σ_20_norm))` — volatile features amplified
- **Models**: MMRegime enum: 7 → **8 values** (added VOLATILE), ObsidianAnalysis: +regime_confidence, +factor_volatility
- Config: `factor_volatility_enabled=False`, `factor_volatility_window=20`, `factor_volatility_confidence_floor=0.6`, `obsidian_regime_multipliers.volatile=0.60`
- Tesztek: 13 (test_bc16_phase1_async.py) + 20 (test_bc16_factor_vol.py)

---

## BC15 — OBSIDIAN MM Integration (692 tests)

**Phase 5 upgrade: 7-regime market microstructure diagnostic engine**

- **OBSIDIAN Engine**: `phases/phase5_obsidian.py` (~300 lines)
  - Deterministic, priority-ordered regime classification from z-scored microstructure features
  - 7 features from existing data (no new API calls): DarkShare, GEX, DEX, Block Intensity, IV Rank, Efficiency, Impact
  - DEX (Dealer Delta Exposure): `Σ(delta × OI × 100)` from Polygon options snapshot
  - IV Rank: average ATM implied volatility (strike within 5% of price)
  - Pure Python statistics (mean, std, z-score, median) — no pandas dependency
- **7 MM Regimes**: Γ⁺ (gamma_positive), Γ⁻ (gamma_negative), DD (dark_dominant), ABS (absorption), DIST (distribution), NEU (neutral), UND (undetermined)
  - Priority-ordered: first matching rule wins
  - Regime multipliers: Γ⁺=1.5, Γ⁻=0.25, DD=1.25, ABS=1.0, DIST=0.5, NEU=1.0, UND=0.75
- **Feature Store**: `data/obsidian_store.py` — per-ticker JSON persistence (`state/obsidian/{TICKER}.json`)
  - Atomic writes (tempfile + os.replace), max 100 entries, date dedup
  - `obsidian_store_always_collect=True`: accumulates features even when OBSIDIAN classification disabled
  - Rolling baseline: W=63 days, N_min=21 for z-score validity
- **Unusualness Score**: U ∈ [0, 100] — weighted |Z| sum → percentile rank
- **Cold Start**: UND/NEU for first 21 runs → progressively activates as store fills
- **Phase 5 Integration**: OBSIDIAN overrides `gex_analysis.gex_multiplier` → Phase 6 picks it up transparently
  - Γ⁻ + LONG → excluded (replaces GEX NEGATIVE exclusion when enabled)
  - call_wall/put_wall/zero_gamma preserved for Phase 6 TP targets
  - **Async support**: Two-phase gather (GEX + OBSIDIAN bars/options), FileCache wired
- **Models**: MMRegime enum (7 values), BaselineState enum, ObsidianAnalysis dataclass
  - Phase5Result: +obsidian_analyses, +obsidian_enabled
  - PositionSizing: +mm_regime, +unusualness_score
- **Console**: OBSIDIAN regime distribution in GEX summary
- **Telegram**: Unified daily report (`send_daily_report` / `send_failure_report`)
  - Single merged message: BMI, sectors, breadth, scanned, GEX, OBSIDIAN store stats, exec plan
  - Failure notification with error message and duration
  - Per-phase timing in runner (Phase 0-6 `time.monotonic()` logging)
  - Env var fix: `IFDS_TELEGRAM_BOT_TOKEN` + `IFDS_TELEGRAM_CHAT_ID` added to loader
- **Deploy Scripts**: `scripts/deploy_daily.sh` (cron-friendly pipeline runner), `scripts/setup_cron.sh` (weekday 22:00 cron), `.env.example`
- Config: 10 CORE + 3 TUNING + 2 RUNTIME OBSIDIAN keys
- Tesztek: 55 új (test_bc15_obsidian.py) + 7 telegram (test_bc13_backlog.py rewrite)

---

## BC14 — Sector Breadth Analysis (636 tests)

**Phase 3 extension: per-sector breadth regimes, divergence detection, FMP ETF holdings**

- **Sector Breadth Engine**: 7 breadth functions in `phase3_sectors.py`
  - `_compute_sma()`, `_build_ticker_close_history()`, `_calculate_breadth()`
  - `_classify_breadth_regime()`, `_detect_breadth_divergence()`, `_apply_breadth_score_adjustment()`
- **7 Breadth Regimes**: STRONG, EMERGING, CONSOLIDATING, NEUTRAL, WEAKENING, WEAK, RECOVERY
  - Classification based on pct_above_SMA50 and pct_above_SMA200
- **Divergence Detection**: Bearish (ETF up >2% + breadth momentum <-5) / Bullish (ETF down <-2% + breadth momentum >+5)
- **Score Adjustments**: breadth_score > 70 → +5 (strong), < 50 → -5 (weak), < 30 → -15 (very weak), bearish divergence → -10
- **FMP ETF Holdings**: `get_etf_holdings()` — sync + async, FileCache-cached
- **Phase 1 Lookback**: 75 → 330 calendar days when breadth enabled (SMA200 needs ~220 trading days)
- **Console**: B.SCORE + B.REGIME columns in sector table, abbreviations (CONSOL, Comm Svc)
- **Models**: BreadthRegime enum, SectorBreadth dataclass, SectorScore.breadth field
- Config: 3 CORE + 11 TUNING breadth keys
- Tesztek: 43 új (test_bc14_breadth.py)

### Post-BC14 Fixes
- Phase 6 daily counter fix: raw_positions (20) → final_positions (3) count correction
- Phase 6 rejection diagnostic logging
- Breadth lookback 290 → 330 (holiday buffer for SMA200)
- breadth_strong_bonus 10 → 5 (crowding prevention at clipping_threshold=95)
- Console sector table reformat with `_cw()` helper for color-safe fixed-width
- **Breadth adj isolated from ticker scores**: `sector_adj_map` subtracts `breadth_score_adj` — breadth only affects Phase 3 sector ranking (leader/neutral/laggard), NOT Phase 4 combined score. Crowded: 43 (stabil, BC12 baseline).

---

## BC13 — P3 Backlog (593 tests)

**4 feature: Survivorship Bias, Telegram Alerts, Max Daily Trades, Notional Limits**

- **Survivorship Bias Protection**: Universe snapshot mentés `state/universe_snapshots/{date}.json`, diff logging `[SURVIVORSHIP]`, max 30 snapshot pruning
- **Telegram Alerts**: `src/ifds/output/telegram.py` — opcionális (env var gated), non-blocking POST, Markdown format
  - Runner wiring: try/except Phase 6 után, soha nem állítja meg a pipeline-t
- **Max Daily Trades**: `state/daily_trades.json`, midnight reset, `max_daily_trades=20`
  - Phase 6: dedup után, sizing előtt ellenőriz
  - `[GLOBALGUARD] Daily trade limit reached` logging
- **Notional Limits**: Per-pozíció (`max_position_notional=25K`) + napi (`max_daily_notional=200K`)
  - Per-pozíció: quantity csökkentés ha notional > cap
  - Napi: skip ha összesített notional > cap
  - `[GLOBALGUARD]` logging mindkét limitre
- Phase6Result: +2 mező (`excluded_daily_trade_limit`, `excluded_notional_limit`)
- Config: +10 RUNTIME kulcs
- Tesztek: 29 új (test_bc13_backlog.py) + 1 fixture fix (test_phase6.py)

---

## BC12 — P3 Nice-to-haves (563 tests)

**6 feature + 1 critical bug fix**

- **Zero Gamma Interpolation**: Linearis interpolacio bracketing strike-ok kozott (`_find_zero_gamma()`)
- **DTE Filter**: ≤90 DTE opciok GEX + PCR/OTM scoringhoz, <5 kontraktus fallback
- **Call Wall ATR Filter**: `abs(call_wall - price) > 5×ATR` → call_wall nullazas
- **Fat Finger Protection**: NaN guard, max_order_quantity=5000, exposure cap
- **VIX EXTREME**: VIX > 50 → EXTREME regime, multiplier 0.10
- **Institutional Ownership**: FMP inst ownership QoQ trend, +10/-5 funda bonus
- **GEX sign fix**: Polygon put GEX signed convention (kivonva gex_by_strike-bol), `_find_zero_gamma()` fallback 0.0
- Config: +4 TUNING, +1 RUNTIME kulcs
- Tesztek: 34 uj (test_bc12_features.py)

---

## BC11 — P2 Robustness (530 tests)

**4 feature: Circuit Breaker, Signal Dedup, GlobalGuard, VIX Sanity**

- **Per-provider Circuit Breaker**: `ProviderCircuitBreaker` — CLOSED → OPEN (>30% error, 50 call window) → HALF_OPEN (60s cooldown) → CLOSED
  - Integralt BaseAPIClient._get() es AsyncBaseAPIClient._get()-be
  - Runner: 4 CB peldany (polygon, fmp, uw, fred) megosztva phase-ek kozott
- **Signal Dedup**: SHA256(ticker|direction|date)[:16], state/signal_hashes.json, 24h TTL
  - Phase 6: ellenorzes sizing elott, rogzites utana, mentes vegen
- **VIX Sanity Check**: `_validate_vix()` — [5.0, 100.0] range, kivul → WARNING + default 20.0
- **GlobalGuard Logging**: `[GLOBALGUARD]` prefix exposure elutasitasokhoz
- Config: cb_window_size=50, cb_error_threshold=0.3, cb_cooldown_seconds=60, signal_hash_file
- Tesztek: 38 uj (test_bc11_circuit_breaker.py + test_bc11_robustness.py)

---

## BC10 — dp_pct Fix + Buy Pressure VWAP (492 tests)

**2 P1 feature: dp_pct recalculation, Buy Pressure + VWAP scoring**

- **dp_pct fix**: `dp_volume / bars[-1]["v"] * 100` — Polygon volume mint nevezo (nem UW)
  - dp_pct scoring: >40% → +10, >60% → +15
- **Buy Pressure**: `(close - low) / (high - low)` — >0.7: +15, <0.3: -15
- **VWAP scoring**: Polygon `vw` field, fallback `(H+L+C)/3`
  - close > VWAP → +10, strong(>1%) → +5, close < VWAP → -5
- FlowAnalysis: +3 mezo (dp_pct_score, vwap, buy_pressure_score)
- Config: +7 TUNING kulcs
- Tesztek: 15 uj (test_bc10_scoring.py)

### Post-BC10 Fixes
- Flow score cap [0, 100]
- Clipping threshold 90 → 95
- CSV flow cap fix

---

## BC9 — Options Flow + Shark + Tech Scoring (476 tests)

**5 feature: PCR/OTM/Block scoring, Shark Detector, RSI Ideal Zone, SMA50, RS vs SPY**

- **Options Flow**: PCR < 0.7 → +15, OTM > 40% → +10, Block >5 → +10, >20 → +15
- **Shark Detector**: 2+ insider, 10 nap, $100K+ → +10 funda
- **RSI Ideal Zone**: [45-65] → +30 (inner), [35-45)/(65-75] → +15 (outer), else → 0
- **SMA50 bonus**: Price > SMA50 → +30
- **RS vs SPY**: Ticker 3mo return > SPY 3mo → +40
- Score range: 10-145 (flow), 50-150 (tech), 15-95 (funda), 55-110 (combined)
- Config: +22 TUNING kulcs, sma_mid_period=50 (CORE)
- Tesztek: 30 uj (test_bc9_scoring.py)

### Post-BC9 Fixes
- isEtf bug: `False` (bool) → `"false"` (string)
- Tech score normalization: `min(100.0, original * bonus)`
- Clipping 90, sector limit 3, score differentiation

---

## BC8 — Per-Sector BMI + MAP-IT Activation (446 tests)

**Per-sector BMI values, sector_bmi_regime activation**

- **FMP sector mapping**: `get_sector_mapping()` — single screener call, {ticker: sector}
- **Per-sector BMI**: `_calculate_sector_bmi()` — SMA25 per sector from daily ratios
- **Phase 3 integration**: `SectorScore.sector_bmi` populalva valos adattal
- Existing `_apply_sector_bmi()` es `_apply_veto_matrix()` aktivalta
- Config: `sector_bmi_min_signals=5`, `lookback_calendar_days=75`
- Debug logging: PHASE_DIAGNOSTIC event type
- Tesztek: 22 uj (test_sector_bmi.py)

---

## CLI Dashboard (392 tests)

**Console output colorama-val**

- `src/ifds/output/console.py` — 8 print fuggveny
- Phase header, diagnostics, sector table, scan summary, GEX summary, final summary
- Colorama graceful fallback (stub ha nincs installalva)
- Wired runner.py-ban minden phase utan

---

## BC7 — Monitoring CSVs + File-based Caching (372 tests)

**3 CSV output, FileCache**

- **3 CSV**: execution_plan (18 col), full_scan_matrix (14 col), trade_plan (8 col)
- **PositionSizing**: +4 mezo (sector_etf, sector_bmi, sector_regime, is_mean_reversion)
- **FileCache**: `data/cache/{provider}/{endpoint}/{date}/{symbol}.json`
  - Today never cached, atomic write (tempfile + os.replace)
  - Config: cache_enabled, cache_dir, cache_max_age_days=7
  - Minden sync + async client `cache=` param

---

## BC6 — Dark Pool Batch Fetch (340 tests)

**882 per-ticker call → 15 paginated batch call (98% reduction)**

- `/api/darkpool/recent` batch endpoint
- `UWBatchDarkPoolProvider` (sync), `AsyncUWBatchDarkPoolProvider` (async)
- `_aggregate_dp_records()` shared pure function
- Pagination: `older_than` cursor
- Config: dp_batch_max_pages=15, dp_batch_page_delay=0.5/0.3

---

## BC5 — Async Migration (299 tests)

**Phase 4: 11.2 min → 2.4 min (4.6x speedup)**

- `async_enabled=False` default, `IFDS_ASYNC_ENABLED=true`
- Uj fajlok: async_base.py, async_clients.py, async_adapters.py
- Phase 4/5: `_from_data()` pure-computation extraction
- Per-provider semaphores: polygon=5, fmp=8, uw=5, max_tickers=10

---

## BC4 — Phase 6: Position Sizing + Output (266 tests)

**Phase 6 implementation, Freshness Alpha, CSV output**

- M_total = M_flow x M_insider x M_funda x M_gex x M_vix x M_utility, clamp [0.25, 2.0]
- Stop = Entry - 1.5 x ATR, TP1 = call_wall or 2 x ATR, TP2 = 3 x ATR
- Freshness Alpha: pandas optional, 1.5x multiplier, 90 nap lookback
- Position limits: max 8, max 2/sector, gross $100K, ticker $20K
- execution_plan CSV output

---

## BC3 — Phase 4-5: Stock Analysis + GEX (213 tests)

**Individual stock analysis, GEX regime classification**

- Phase 4: Technical (RSI, SMA200, ATR) + Fundamental (growth, metrics, insider) + Flow (RVOL, squat, DP)
- Phase 5: GEX regime (POSITIVE/NEGATIVE/HIGH_VOL), FallbackGEXProvider (UW → Polygon)
- Combined score = 0.40*flow + 0.30*funda + 0.30*tech + sector_adj

---

## BC2 — Phase 1-3: BMI + Universe + Sectors (123 tests)

**Market regime, universe building, sector rotation**

- Phase 1: BMI (Big Money Index) — volume spike detection, SMA25, regime classification
- Phase 2: FMP screener universe, earnings exclusion, LONG/SHORT filtering
- Phase 3: Sector momentum (11 ETFs), leader/laggard, VETO matrix, TNX sensitivity

---

## BC1 — Infrastructure + Phase 0 (51 tests)

**Project foundation, Phase 0 diagnostics**

- Config loader: CORE/TUNING/RUNTIME dicts, env var loading
- Data layer: BaseAPIClient, Polygon/FMP/UW/FRED clients
- Phase 0: Health checks, VIX 3-level fallback, TNX SMA20
- EventLogger: Structured logging, phase_start/complete/error
- Models: All dataclasses and enums in market.py
