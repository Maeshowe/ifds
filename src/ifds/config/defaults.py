"""IFDS configuration defaults.

Three layers:
- CORE: Algorithm constants (formulas, fixed logic). Changed by developers only.
- TUNING: Thresholds, weights, scoring parameters. Changed by operator.
- RUNTIME: Account size, API keys, paths. Changed per environment.
"""

# ============================================================================
# CORE — Algorithm constants (do not change unless you understand the math)
# ============================================================================

CORE = {
    # BMI (Big Money Index)
    "bmi_volume_spike_sigma": 2.0,      # k in volume spike detection
    "bmi_sma_period": 25,               # BMI smoothing period (days)
    "bmi_volume_avg_period": 20,        # Volume average lookback (days)

    # Technical Analysis
    "sma_long_period": 200,             # Long-term trend filter
    "sma_mid_period": 50,              # Mid-term trend (SMA50 bonus)
    "sma_short_period": 20,            # Short-term trend
    "rsi_period": 14,                   # RSI lookback
    "atr_period": 14,                   # ATR lookback

    # GEX
    "gex_normalization_factor": 0.01,   # GEX formula constant
    "gex_contract_size": 100,           # Options contract multiplier

    # Position Sizing
    "stop_loss_atr_multiple": 1.5,      # k in StopLoss = Entry - k * ATR
    "tp1_atr_multiple": 2.0,           # TP1 = Entry + 2 * ATR
    "tp2_atr_multiple": 3.0,           # TP2 = Entry + 3 * ATR
    "scale_out_atr_multiple": 2.0,     # Scale-out trigger at 2 * ATR
    "scale_out_pct": 0.33,             # Close 33% at scale-out

    # Sector BMI
    "sector_bmi_min_signals": 5,       # Min buy+sell signals per sector per day

    # Sector Breadth (BC14)
    "breadth_sma_periods": [20, 50, 200],           # SMA periods to compute
    "breadth_lookback_calendar_days": 330,           # ~220 trading days for SMA200 (with holiday buffer)
    "breadth_composite_weights": (0.20, 0.50, 0.30), # SMA20, SMA50, SMA200 weights

    # MMS — Market Microstructure Scorer (BC15)
    "mms_window": 63,                                    # Rolling baseline window (trading days)
    "mms_min_periods": 21,                               # Min observations for z-score validity
    "mms_feature_weights": {                             # Diagnostic weights (NOT tunable)
        "dark_share": 0.25,
        "gex": 0.25,
        "venue_mix": 0.20,                               # Excluded (no data), weight preserved
        "block_intensity": 0.15,
        "iv_rank": 0.15,
    },
    "mms_z_gex_threshold": 1.5,                          # ±1.5 for Γ⁺/Γ⁻ (~93rd percentile)
    "mms_z_dex_threshold": 1.0,                          # ±1.0 for ABS/DIST (~84th percentile)
    "mms_z_block_threshold": 1.0,                        # +1.0 for DD (~84th percentile)
    "mms_dark_share_dd": 0.70,                           # DarkShare absolute for DD rule
    "mms_dark_share_abs": 0.50,                          # DarkShare absolute for ABS rule
    "mms_return_abs": -0.005,                            # Daily return threshold for ABS (≥ -0.5%)
    "mms_return_dist": 0.005,                            # Daily return threshold for DIST (≤ +0.5%)

    # Freshness Alpha
    "freshness_lookback_days": 90,     # Days before signal is "fresh"
    "freshness_bonus": 1.5,            # Score multiplier for fresh signals

    # Clipping Logic
    "clipping_threshold": 95,          # Score above this = crowded trade → SKIP

    # Scoring Weights
    "weight_flow": 0.40,               # Flow Analysis weight
    "weight_fundamental": 0.30,        # Fundamental weight
    "weight_technical": 0.30,          # Technical weight
}

# ============================================================================
# TUNING — Thresholds and scoring parameters (operator-adjustable)
# ============================================================================

TUNING = {
    # BMI Regime thresholds
    "bmi_green_threshold": 25,          # BMI <= 25% → GREEN (aggressive long)
    "bmi_red_threshold": 80,            # BMI >= 80% → RED (short/defensive)

    # BMI Divergence
    "bmi_divergence_spy_change_pct": 1.0,   # SPY must rise > 1%
    "bmi_divergence_bmi_change_pts": -2.0,  # BMI must drop > 2 points

    # Universe Building — LONG
    "universe_min_market_cap": 2_000_000_000,   # $2B
    "universe_min_price": 5.0,                   # $5
    "universe_min_avg_volume": 500_000,          # 500K shares/day
    "universe_require_options": True,

    # Universe Building — SHORT (Zombie)
    "zombie_min_market_cap": 500_000_000,       # $500M
    "zombie_min_avg_volume": 500_000,
    "zombie_min_debt_equity": 3.0,              # D/E > 3.0
    "zombie_max_net_margin": 0.0,               # Negative margin
    "zombie_max_interest_coverage": 1.5,

    # Zombie Hunter (Earnings exclusion)
    "earnings_exclusion_days": 7,               # Skip if earnings within 7 calendar days

    # Sector Momentum
    "sector_leader_count": 3,                   # Top 3 → Leader
    "sector_laggard_count": 3,                  # Bottom 3 → Laggard
    "sector_leader_bonus": 15,                  # Leader score bonus
    "sector_laggard_penalty": -20,              # Laggard score penalty
    "sector_laggard_mr_penalty": -5,            # Laggard + Oversold (Mean Reversion)
    "sector_momentum_period": 5,                # 5-day relative performance

    # Individual Stock — RSI thresholds
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "rsi_oversold_bonus": 5,
    "rsi_overbought_penalty": -5,

    # Individual Stock — RVOL thresholds
    "rvol_low": 0.5,
    "rvol_normal": 1.0,
    "rvol_elevated": 1.5,
    "rvol_low_penalty": -10,
    "rvol_elevated_bonus": 5,
    "rvol_significant_bonus": 15,

    # Squat Bar Detection
    "squat_bar_rvol_min": 2.0,
    "squat_bar_spread_ratio_max": 0.9,
    "squat_bar_bonus": 10,

    # Dark Pool
    "dark_pool_volume_threshold_pct": 40,       # DP > 40% of total volume

    # Fundamental Scoring
    "funda_revenue_growth_good": 10,            # > 10% YoY
    "funda_revenue_growth_bad": -10,
    "funda_eps_growth_good": 15,
    "funda_eps_growth_bad": -15,
    "funda_net_margin_good": 15,
    "funda_net_margin_bad": 0,
    "funda_roe_good": 15,
    "funda_roe_bad": 5,
    "funda_debt_equity_good": 0.5,
    "funda_debt_equity_bad": 2.0,
    "funda_interest_coverage_bad": 1.5,
    "funda_score_bonus": 5,
    "funda_score_penalty": -5,
    "funda_debt_penalty": -10,

    # Insider Activity
    "insider_lookback_days": 30,
    "insider_strong_buy_threshold": 3,
    "insider_strong_sell_threshold": -3,
    "insider_buy_multiplier": 1.25,
    "insider_sell_multiplier": 0.75,

    # Combined Score minimum
    "combined_score_minimum": 70,

    # GEX Regime multipliers
    "gex_positive_multiplier": 1.0,
    "gex_negative_multiplier": 0.5,
    "gex_high_vol_multiplier": 0.6,

    # VIX thresholds
    "vix_low": 15,
    "vix_normal": 20,
    "vix_elevated": 30,
    "vix_penalty_start": 20,
    "vix_penalty_rate": 0.02,                   # Per VIX point above threshold
    "vix_multiplier_floor": 0.25,

    # TNX Rate Sensitivity
    "tnx_sensitivity_pct": 5,                   # TNX > SMA20 * 1.05
    "tnx_sensitive_sectors": ["Technology", "Real Estate"],

    # Risk Management multipliers
    # M_flow threshold = 80: flow_score = BASE(50) + rvol_score.
    # rvol_score max realistic ~+30 (elevated+squat). Threshold 80 means only
    # genuinely strong flow (rvol_score > 30) gets the 1.25× boost.
    # This is a deliberate conservative choice — most tickers stay at M_flow=1.0.
    "multiplier_flow_threshold": 80,
    "multiplier_flow_value": 1.25,
    "multiplier_funda_threshold": 60,
    "multiplier_funda_value": 0.50,
    "multiplier_utility_threshold": 85,
    "multiplier_utility_max": 1.3,

    # Sector Diversification
    "max_positions_per_sector": 3,

    # Options Flow Scoring (BC9)
    "pcr_bullish_threshold": 0.7,              # PCR < 0.7 → bullish bonus
    "pcr_bearish_threshold": 1.3,              # PCR > 1.3 → bearish penalty
    "pcr_bullish_bonus": 15,
    "pcr_bearish_penalty": -10,
    "otm_call_ratio_threshold": 0.4,           # > 40% OTM calls → bonus
    "otm_call_bonus": 10,
    "block_trade_significant": 5,              # >5 blocks → bonus
    "block_trade_very_high": 20,               # >20 blocks → higher bonus
    "block_trade_significant_bonus": 10,
    "block_trade_very_high_bonus": 15,

    # Dark Pool Percentage Scoring (BC10)
    "dp_pct_high_threshold": 60,              # dp_pct > 60% → higher bonus
    "dp_pct_bonus": 10,                        # dp_pct > 40% → +10
    "dp_pct_high_bonus": 15,                  # dp_pct > 60% → +15

    # Buy Pressure + VWAP (BC10)
    "buy_pressure_strong_bonus": 15,           # buy_pos > 0.7 → +15
    "buy_pressure_weak_penalty": -15,          # buy_pos < 0.3 → -15
    "vwap_accumulation_bonus": 10,             # close > VWAP → +10
    "vwap_distribution_penalty": -5,           # close < VWAP → -5

    # Shark Detector (BC9)
    "shark_min_unique_insiders": 2,            # 2+ different insiders
    "shark_lookback_days": 10,                 # within 10 days
    "shark_min_total_value": 100_000,          # total $100K+
    "shark_score_bonus": 10,

    # RSI Ideal Zone (BC9 — replaces old ±5 scoring)
    "rsi_ideal_inner_low": 45,
    "rsi_ideal_inner_high": 65,
    "rsi_ideal_outer_low": 35,
    "rsi_ideal_outer_high": 75,
    "rsi_ideal_inner_bonus": 30,               # [45-65] → +30
    "rsi_ideal_outer_bonus": 15,               # [35-45) or (65-75] → +15

    # SMA50 & RS vs SPY (BC9)
    "sma50_bonus": 30,                         # price > SMA50 → +30
    "rs_spy_bonus": 40,                        # 3-month outperformance vs SPY → +40

    # Call Wall ATR Filter (BC12)
    "call_wall_max_atr_distance": 5.0,         # Max ATR multiples from price to call wall

    # Front-Month Options Filter (BC12)
    "gex_max_dte": 90,                         # Only include options within 90 DTE (3 months)

    # VIX EXTREME regime (BC12)
    "vix_extreme_threshold": 50,               # VIX > 50 → EXTREME regime
    "vix_extreme_multiplier": 0.10,            # Position sizing × 0.1 in EXTREME

    # Sector Breadth Analysis (BC14)
    "breadth_enabled": True,
    "breadth_strong_threshold": 70,
    "breadth_weak_threshold": 50,
    "breadth_very_weak_threshold": 30,
    "breadth_strong_bonus": 5,
    "breadth_weak_penalty": -5,
    "breadth_very_weak_penalty": -15,
    "breadth_divergence_penalty": -10,
    "breadth_divergence_etf_threshold": 2.0,        # ETF 5d change %
    "breadth_divergence_breadth_threshold": 5.0,     # SMA50 breadth momentum points
    "breadth_min_constituents": 10,

    # Sector-specific BMI thresholds (oversold, overbought)
    "sector_bmi_thresholds": {
        "XLK": (12, 85),   # Technology
        "XLF": (10, 80),   # Financials
        "XLE": (10, 75),   # Energy
        "XLV": (12, 80),   # Healthcare
        "XLI": (12, 80),   # Industrials
        "XLP": (15, 75),   # Consumer Defensive
        "XLY": (9, 80),    # Consumer Cyclical
        "XLB": (12, 80),   # Basic Materials
        "XLC": (12, 80),   # Communication Services
        "XLRE": (9, 85),   # Real Estate
        "XLU": (15, 75),   # Utilities
    },

    # MMS (BC15)
    "mms_enabled": False,                              # Feature flag (opt-in)
    "mms_store_always_collect": True,                  # Accumulate feature store even when disabled
    "mms_regime_multipliers": {                        # Phase 6 sizing multipliers per regime
        "gamma_positive": 1.5,
        "gamma_negative": 0.25,
        "dark_dominant": 1.25,
        "absorption": 1.0,
        "distribution": 0.5,
        "neutral": 1.0,
        "undetermined": 0.75,
        "volatile": 0.60,                            # VOL: unstable microstructure (BC16)
    },

    # Factor Volatility (BC16)
    "factor_volatility_enabled": False,               # Feature flag (opt-in)
    "factor_volatility_window": 20,                   # Rolling σ window (trading days)
    "factor_volatility_confidence_floor": 0.6,        # Minimum confidence multiplier

    # Danger Zone Filter (BC18-prep — T3 Bottom 10)
    "danger_zone_enabled": True,                      # Explicit negative filter
    "danger_zone_debt_equity": 5.0,                   # D/E > 5.0 = extreme leverage
    "danger_zone_net_margin": -0.10,                  # Net margin < -10% = burning cash
    "danger_zone_interest_coverage": 1.0,             # IC < 1.0 = can't cover debt
    "danger_zone_min_signals": 2,                     # Need 2+ danger signals to filter
}

# ============================================================================
# RUNTIME — Environment-specific (loaded from env vars / config file)
# ============================================================================

RUNTIME = {
    # Account
    "account_equity": 100_000,          # USD
    "risk_per_trade_pct": 0.5,          # 0.5% per trade

    # Position Limits
    "max_positions": 8,
    "max_single_position_risk_pct": 1.5,
    "max_gross_exposure": 100_000,
    "max_single_ticker_exposure": 20_000,

    # API Keys (MUST be loaded from env vars, never hardcoded)
    "polygon_api_key": None,            # IFDS_POLYGON_API_KEY
    "unusual_whales_api_key": None,     # IFDS_UW_API_KEY
    "fmp_api_key": None,                # IFDS_FMP_API_KEY
    "fred_api_key": None,               # IFDS_FRED_API_KEY (free but required)

    # API Timeouts and Retries
    "api_timeout_polygon": 10,
    "api_timeout_polygon_options": 15,
    "api_timeout_uw": 10,
    "api_timeout_fmp": 10,
    "api_timeout_fred": 10,
    "api_max_retries": 3,

    # Async Concurrency (Phase 1/4/5 parallel processing — BC16 tuning)
    "async_enabled": False,                 # Set IFDS_ASYNC_ENABLED=true to enable
    "async_sem_polygon": 10,                # Polygon paid tier ~10 req/s
    "async_sem_fmp": 8,                     # FMP middle ground (429 at 12, too slow at 5)
    "async_sem_uw": 5,                      # UW conservative default
    "async_max_tickers": 10,                # 10 tickers × ~5 FMP calls = 50 concurrent

    # Dark Pool Batch Prefetch
    "dp_batch_max_pages": 15,              # Max pagination pages for /recent
    "dp_batch_page_delay": 0.5,            # Seconds between paginated calls (sync)
    "dp_batch_page_delay_async": 0.3,      # Seconds between paginated calls (async)

    # File-based Cache
    "cache_enabled": False,                 # Set IFDS_CACHE_ENABLED=true to enable
    "cache_dir": "data/cache",             # Cache directory path
    "cache_max_age_days": 7,               # Days before cleanup deletes old files

    # Circuit Breaker (drawdown)
    "circuit_breaker_drawdown_limit_pct": 3.0,
    "circuit_breaker_state_file": "state/circuit_breaker.json",

    # Per-provider Circuit Breaker (API error rate)
    "cb_window_size": 50,                  # Sliding window of recent calls
    "cb_error_threshold": 0.3,             # 30% error rate → OPEN
    "cb_cooldown_seconds": 60,             # Seconds before HALF_OPEN probe

    # Signal Deduplication
    "signal_hash_file": "state/signal_hashes.json",

    # Fat Finger Protection (BC12)
    "max_order_quantity": 5000,                # Hard cap on shares per position

    # Survivorship Bias (BC13)
    "survivorship_snapshot_dir": "state/universe_snapshots",
    "survivorship_max_snapshots": 30,

    # Telegram Alerts (BC13) — env vars: IFDS_TELEGRAM_BOT_TOKEN, IFDS_TELEGRAM_CHAT_ID
    "telegram_bot_token": None,
    "telegram_chat_id": None,
    "telegram_timeout": 5,

    # Max Daily Trades (BC13)
    "max_daily_trades": 20,
    "daily_trades_file": "state/daily_trades.json",

    # Notional Limits (BC13)
    "max_daily_notional": 200_000,
    "max_position_notional": 25_000,
    "daily_notional_file": "state/daily_notional.json",

    # MMS Feature Store (BC15)
    "mms_store_dir": "state/mms",
    "mms_max_store_entries": 100,

    # Phase 4 Snapshot (BC19 — SIM-L2 Mód 2 prep)
    "phase4_snapshot_enabled": True,
    "phase4_snapshot_dir": "state/phase4_snapshots",

    # Output
    "output_dir": "output",
    "log_dir": "logs",

    # Signal History (Freshness Alpha)
    "signal_history_file": "state/signal_history.parquet",
}
