# IFDS V13 → V2.0 — Feature Audit (BC15 utan, 692 teszt, 2026-02-11)

> Referencia: `reference/` mappa teljes tartalma vs `src/ifds/` v2.0 kod
> Frissitve: 2026-02-11 (BC15 utan)

---

## Feature Matrix Osszefoglalo

| # | Feature | V13 Modul | V2 Statusz | Prioritas |
|---|---------|-----------|------------|-----------|
| 1 | Options Flow Scoring (PCR, OTM, Block) | flow_engine.py | **DONE** (BC9) | ~~P0~~ |
| 2 | Freshness Alpha aktivalas | signal_generator.py | **DONE** (BC4, pandas kell runtime-ban) | ~~P0~~ |
| 3 | Shark Detector (Cluster Buying) | history_manager.py | **DONE** (BC9) | ~~P1~~ |
| 4 | Dark Pool dp_pct fix | flow_engine.py | **DONE** (BC10) | ~~P1~~ |
| 5 | RSI Ideal Zone scoring | technical_analyzer.py | **DONE** (BC9) | ~~P1~~ |
| 6 | Relative Strength vs SPY (tech) | technical_analyzer.py | **DONE** (BC9) | ~~P1~~ |
| 7 | SMA50 bonus | technical_analyzer.py | **DONE** (BC9) | ~~P1~~ |
| 8 | Buy Pressure + VWAP scoring | flow_engine.py | **DONE** (BC10) | ~~P1~~ |
| 9 | Per-provider Circuit Breaker | global_guard.py | **DONE** (BC11) | ~~P2~~ |
| 10 | Signal Hash Idempotency | global_guard.py | **DONE** (BC11) | ~~P2~~ |
| 11 | GlobalGuard (exposure limit enforcement) | global_guard.py | **DONE** (BC11) | ~~P2~~ |
| 12 | VIX sanity check (5-100 range) | macro_compass.py | **DONE** (BC11) | ~~P2~~ |
| 13 | File-based caching | data/cache.py | **DONE** (BC7) | ~~P2~~ |
| 14 | Per-sector BMI | phase1_regime.py | **DONE** (BC8) | ~~P2~~ |
| 15 | isEtf bug fix | phase2_universe.py | **DONE** (Post-BC9) | ~~P1~~ |
| 16 | Offline Simulation Engine | sim_engine.py | ❌ Hianyzik | **P3** |
| 17 | Call Wall ATR Distance Filter | gex_engine.py | **DONE** (BC12) | ~~P3~~ |
| 18 | Zero Gamma linear interpolation | gex_engine.py | **DONE** (BC12) | ~~P3~~ |
| 19 | Institutional Ownership Trend | fundamental_scorer.py | **DONE** (BC12) | ~~P3~~ |
| 20 | Front-Month Options Filter (DTE 90) | gex_engine.py | **DONE** (BC12) | ~~P3~~ |
| 21 | Survivorship Bias Protection | universe_builder.py | **DONE** (BC13) | ~~P3~~ |
| 22 | Trailing Stop Engine (live) | settings.yaml | ❌ Hianyzik | **P3** |
| 23 | Telegram Alerts | signal_generator.py | **DONE** (BC13) | ~~P3~~ |
| 24 | Fat Finger Protection | global_guard.py | **DONE** (BC12) | ~~P3~~ |
| 25 | Max Daily Trades limit | global_guard.py | **DONE** (BC13) | ~~P3~~ |
| 26 | Notional Limits (daily cap) | settings.yaml | **DONE** (BC13) | ~~P3~~ |
| 27 | VIX EXTREME regime | macro_compass.py | **DONE** (BC12) | ~~P3~~ |
| 28 | Sector Breadth Analysis | sector_engine.py | **DONE** (BC14) | ~~P3~~ |
| 29 | OBSIDIAN MM (7-regime microstructure) | — (V2 novelty) | **DONE** (BC15) | ~~P3~~ |

---

## DONE Feature-ok — Build Cycle szerint

| Feature | BC | Reszletek |
|---------|-----|-----------|
| Freshness Alpha | BC4 | pandas-alapu signal_history, 1.5x szorzo |
| File-based caching | BC7 | `data/cache/{provider}/{endpoint}/{date}/{symbol}.json` |
| Per-sector BMI | BC8 | FMP sector mapping, SMA25 per sector, sector_bmi_regime |
| Options Flow Scoring | BC9 | PCR < 0.7 → +15, OTM ratio > 40% → +10, Block trades >5 → +10, >20 → +15 |
| Shark Detector | BC9 | 2+ insider, 10 nap, $100K+ → +10 funda bonus |
| RSI Ideal Zone | BC9 | [45-65] → +30, [35-45)/(65-75] → +15, else → 0 |
| SMA50 bonus | BC9 | Price > SMA50 → +30 |
| RS vs SPY | BC9 | Ticker 3mo return > SPY 3mo return → +40 |
| isEtf bug fix | Post-BC9 | `isEtf: False` (boolean) → `"false"` (string) |
| dp_pct fix | BC10 | Polygon volume mint nevezo, dp_volume / bars[-1]["v"] × 100 |
| Buy Pressure + VWAP | BC10 | buy_pos=(close-low)/(high-low), VWAP=Polygon vw field |
| Circuit Breaker | BC11 | Per-provider sliding window (50 call), 30% error → OPEN, 60s cooldown |
| Signal Hash Dedup | BC11 | SHA256(ticker\|direction\|date)[:16], 24h TTL, state/signal_hashes.json |
| GlobalGuard logging | BC11 | [GLOBALGUARD] prefix, gross + single ticker exposure logolas |
| VIX sanity check | BC11 | [5.0, 100.0] range, fallback 20.0 |
| Zero Gamma interpolation | BC12 | Linearis interpolacio ket bracketing strike kozott |
| DTE Filter (90 nap) | BC12 | GEX + PCR/OTM: csak ≤90 DTE opciok, <5 kontraktus fallback |
| Call Wall ATR Filter | BC12 | abs(call_wall - price) > 5×ATR → call_wall = 0 |
| Fat Finger Protection | BC12 | NaN guard, max_order_quantity=5000, max_single_ticker_exposure cap |
| VIX EXTREME | BC12 | VIX > 50 → EXTREME regime, multiplier 0.10 |
| Institutional Ownership | BC12 | FMP `/stable/institutional-ownership/latest`, QoQ change > 2% → +10 |
| Survivorship Bias | BC13 | Universe snapshot + diff logging `[SURVIVORSHIP]`, max 30 snapshot |
| Telegram Alerts | BC13+BC15 | `send_daily_report()` unified, non-blocking, env var gated. BC15: merged health+trade into single message |
| Max Daily Trades | BC13 | `max_daily_trades=20`, `state/daily_trades.json`, midnight reset |
| Notional Limits | BC13 | `max_daily_notional=200K`, `max_position_notional=25K`, per-trade + napi cap |
| Sector Breadth Analysis | BC14 | 7 breadth regime, SMA20/50/200 %-above, divergence detection, FMP ETF holdings |
| OBSIDIAN MM | BC15 | 7 MM regime (Γ⁺/Γ⁻/DD/ABS/DIST/NEU/UND), feature store, z-score baseline, unusualness score |

---

## Maradek Hianyzok — P3 Backlog

| # | Feature | Reszletek | Becsult ido |
|---|---------|-----------|-------------|
| 1 | **SimEngine (backtesting)** | Offline replay engine: re-score, filter, size pipeline CSV-kbol. Parameter sensitivity. | 8-12 ora |
| 2 | **Trailing Stop Engine** | Breakeven@1R, trail@2R, distance=1R behind price. Live execution. | 4-6 ora |

---

## V13 Feature Lefedettseg (aktualis)

```
reference/ fajl               V2 lefedettseg  Hianyzik
-------------------------------------------------------------------
risk_manager.py          [==========-]  98%    Trailing live
global_guard.py          [==========] 100%    TELJES (BC13)
flow_engine.py           [==========] 100%    TELJES (BC10)
sim_engine.py            [=----------]  10%    Offline replay, param sensitivity
history_manager.py       [=========--]  90%    Batch freshness
fundamental_scorer.py    [==========] 100%    TELJES (BC12)
gex_engine.py            [==========] 100%    TELJES (BC12)
technical_analyzer.py    [==========] 100%    TELJES (BC9)
sector_engine.py         [==========] 100%    TELJES (BC14: breadth)
market_regime.py         [==========] 100%    TELJES (BC8)
universe_builder.py      [==========] 100%    TELJES (BC13)
macro_compass.py         [==========] 100%    TELJES (BC12)
signal_generator.py      [==========-]  95%    Sim snapshot
settings.yaml            [==========-]  96%    ~2 config kulcs hianyzik
-------------------------------------------------------------------
Osszesitett:             [==========-]  ~96%   (BC15: +OBSIDIAN V2 novelty, +Telegram unified report, +deploy scripts)
```

---

## Config Kulcsok — V13 vs V2 Hianyzok (aktualis)

| YAML kulcs | V13 Ertek | V2 Megfeleloje | Statusz |
|------------|-----------|----------------|---------|
| `scoring.bonuses.shark_signal` | 10 | `TUNING.shark_score_bonus` | **DONE** (BC9) |
| `flow.options.pcr_bullish_max` | 0.7 | `TUNING.pcr_bullish_threshold` | **DONE** (BC9) |
| `flow.options.otm_call_threshold` | 0.4 | `TUNING.otm_call_ratio_threshold` | **DONE** (BC9) |
| `flow.dark_pool.block_trade_min_usd` | $500K | `TUNING.block_trade_significant` | **DONE** (BC9) |
| `technical.rsi.ideal_min` | 45 | `TUNING.rsi_ideal_inner_low` | **DONE** (BC9) |
| `technical.rsi.ideal_max` | 65 | `TUNING.rsi_ideal_inner_high` | **DONE** (BC9) |
| `technical.relative_strength.benchmark` | SPY | Hardcoded | **DONE** (BC9) |
| `scoring.gex.atr_distance_multiplier` | 5.0 | `TUNING.call_wall_max_atr_distance` | **DONE** (BC12) |
| `global_guard.max_order_quantity` | 5000 | `RUNTIME.max_order_quantity` | **DONE** (BC12) |
| `global_guard.signal_hash_ttl_hours` | 24 | `SignalDedup` (24h TTL, date-based) | **DONE** (BC11) |
| `scanning.error_rate_abort_threshold` | 0.3 | `RUNTIME.cb_error_threshold` | **DONE** (BC11) |
| `strategy.dark_pool.min_block_size` | 10000 | Nincs | ❌ P3 |
| `strategy.dark_pool.min_notional` | $1M | Nincs | ❌ P3 |
| `global_guard.max_order_value` | $1500 | `RUNTIME.max_position_notional` | **DONE** (BC13) |
| `global_guard.max_daily_trades` | 20 | `RUNTIME.max_daily_trades` | **DONE** (BC13) |
| `alerts.telegram.*` | Telegram bot | `RUNTIME.telegram_*` | **DONE** (BC13) |
