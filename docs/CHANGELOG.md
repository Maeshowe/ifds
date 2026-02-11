# IFDS v2.0 Changelog

> Build Cycle BC1 → BC15 | 2026-02-06 – 2026-02-11

---

## BC15 — OBSIDIAN MM Integration (686 tests)

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
- **Models**: MMRegime enum (7 values), BaselineState enum, ObsidianAnalysis dataclass
  - Phase5Result: +obsidian_analyses, +obsidian_enabled
  - PositionSizing: +mm_regime, +unusualness_score
- **Console**: OBSIDIAN regime distribution in GEX summary
- Config: 10 CORE + 3 TUNING + 2 RUNTIME OBSIDIAN keys
- Tesztek: 50 új (test_bc15_obsidian.py)

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
