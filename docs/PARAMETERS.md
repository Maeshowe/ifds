# IFDS v2.0 — Teljes Paraméter Audit

> Generálva: `src/ifds/config/defaults.py` (CORE + TUNING + RUNTIME)
> V13 referencia: `reference/settings.yaml`
> Frissitve: 2026-02-18 (BC18-prep utan, 810 teszt)

---

## CORE — Algoritmus Konstansok

Csak fejlesztői módosítás. A matematikai képletek fix paraméterei.

| Kulcs | Érték | Phase | Hatás | V13 megfelelő | Eltérés? |
|-------|-------|-------|-------|----------------|----------|
| `bmi_volume_spike_sigma` | 2.0 | P1 | Volume spike küszöb: v > mean + k×σ | `market_regime.volume_spike_sigma: 2.0` | ✅ Azonos |
| `bmi_sma_period` | 25 | P1 | BMI simítási ablak (SMA25) | `market_regime.bmi.ma_period: 25` | ✅ Azonos |
| `bmi_volume_avg_period` | 20 | P1 | Volume átlag lookback (20 nap) | Implicit (20 nap) | ✅ Azonos |
| `sma_long_period` | 200 | P4 | Hosszú távú trend filter (SMA200) | `technical.sma.long: 200` | ✅ Azonos |
| `sma_mid_period` | 50 | P4 | Mid-term trend (SMA50 bonus, BC9) | `technical.sma.mid: 50` | ✅ Azonos |
| `sma_short_period` | 20 | P3,P4 | Rövid távú trend (SMA20) | `technical.sma.short: 50` | ⚠️ **V13=50, V2=20** |
| `rsi_period` | 14 | P4 | RSI lookback | `technical.rsi.period: 14` | ✅ Azonos |
| `atr_period` | 14 | P4,P6 | ATR lookback | `technical.atr.period: 14` | ✅ Azonos |
| `gex_normalization_factor` | 0.01 | P5 | GEX képlet konstans | Implicit (0.01) | ✅ Azonos |
| `gex_contract_size` | 100 | P5 | Opciós kontraktus szorzó | Implicit (100) | ✅ Azonos |
| `stop_loss_atr_multiple` | 1.5 | P6 | Stop = Entry - 1.5×ATR | `risk.atr_multiplier_stop: 1.5` | ✅ Azonos |
| `tp1_atr_multiple` | 2.0 | P6 | TP1 = Entry + 2×ATR | `risk.reward_ratio_scale_out: 2.0` | ✅ Azonos |
| `tp2_atr_multiple` | 3.0 | P6 | TP2 = Entry + 3×ATR | `risk.reward_ratio_runner: 4.0` | ⚠️ **V13=4R, V2=3R** |
| `scale_out_atr_multiple` | 2.0 | P6 | Scale-out trigger = 2×ATR | `trailing_stop.scale_out.trigger_r: 2.0` | ✅ Azonos |
| `scale_out_pct` | 0.33 | P6 | 33% zárás scale-out-nál | `trailing_stop.scale_out.portion: 0.5` | ⚠️ **V13=50%, V2=33%** |
| `sector_bmi_min_signals` | 5 | P1 | Min buy+sell signal / szektor / nap | `sector_engine.min_sector_tickers: 10` | ⚠️ **V13=10, V2=5** |
| `freshness_lookback_days` | 90 | P6 | Napok mielőtt "friss" | `signal_history.freshness.lookback_days: 90` | ✅ Azonos |
| `freshness_bonus` | 1.5 | P6 | Friss signal szorzó | `strategy.freshness.score_multiplier: 1.75` | ⚠️ **V13=1.75, V2=1.5** |
| `clipping_threshold` | 95 | P4 | Score > 95 = crowded → SKIP | `strategy.clipping.max_score: 85` | ⚠️ **V13=85, V2=95** |
| `weight_flow` | 0.40 | P4 | Flow Analysis súly | `scoring.weights.flow: 0.4` | ✅ Azonos |
| `weight_fundamental` | 0.30 | P4 | Fundamental súly | `scoring.weights.fundamental: 0.3` | ✅ Azonos |
| `weight_technical` | 0.30 | P4 | Technical súly | `scoring.weights.technical: 0.3` | ✅ Azonos |
| `breadth_sma_periods` | [20, 50, 200] | P3 | SMA periódusok breadth számításhoz (BC14) | Nincs | V2 újdonság |
| `breadth_lookback_calendar_days` | 330 | P1 | Lookback Phase 1-ben ha breadth enabled (~220 trading day) (BC14) | Nincs | V2 újdonság |
| `breadth_composite_weights` | (0.20, 0.50, 0.30) | P3 | SMA20/50/200 súlyok a breadth score-ban (BC14) | Nincs | V2 újdonság |
| `obsidian_window` | 63 | P5 | Rolling baseline ablak (trading days) (BC15) | Nincs | V2 újdonság |
| `obsidian_min_periods` | 21 | P5 | Min observations z-score validity-hez (BC15) | Nincs | V2 újdonság |
| `obsidian_feature_weights` | {dark_share: 0.25, gex: 0.25, venue_mix: 0.20, block: 0.15, iv: 0.15} | P5 | Diagnostic feature súlyok (NOT tunable) (BC15) | Nincs | V2 újdonság |
| `obsidian_z_gex_threshold` | 1.5 | P5 | ±1.5 z-score Γ⁺/Γ⁻ klasszifikációhoz (~93rd pctile) (BC15) | Nincs | V2 újdonság |
| `obsidian_z_dex_threshold` | 1.0 | P5 | ±1.0 z-score ABS/DIST klasszifikációhoz (~84th pctile) (BC15) | Nincs | V2 újdonság |
| `obsidian_z_block_threshold` | 1.0 | P5 | +1.0 z-score DD klasszifikációhoz (BC15) | Nincs | V2 újdonság |
| `obsidian_dark_share_dd` | 0.70 | P5 | DarkShare abszolút küszöb DD rule-hoz (BC15) | Nincs | V2 újdonság |
| `obsidian_dark_share_abs` | 0.50 | P5 | DarkShare abszolút küszöb ABS rule-hoz (BC15) | Nincs | V2 újdonság |
| `obsidian_return_abs` | -0.005 | P5 | Daily return küszöb ABS-hoz (≥ -0.5%) (BC15) | Nincs | V2 újdonság |
| `obsidian_return_dist` | 0.005 | P5 | Daily return küszöb DIST-hoz (≤ +0.5%) (BC15) | Nincs | V2 újdonság |
| `factor_volatility_window` | 20 | P5 | Rolling σ ablak faktor volatilitáshoz (BC16) | Nincs | V2 újdonság |

---

## TUNING — Küszöbértékek és Scoring Paraméterek

Operátor által állítható. A piac viselkedéséhez igazítható.

### BMI Regime

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `bmi_green_threshold` | 25 | P1 | BMI ≤ 25% → GREEN (aggressive LONG) | `market_regime.bmi.oversold_threshold: 25` | ✅ Azonos |
| `bmi_red_threshold` | 80 | P1 | BMI ≥ 80% → RED (SHORT) | `market_regime.bmi.overbought_threshold: 80` | ✅ Azonos |
| `bmi_divergence_spy_change_pct` | 1.0 | P1 | SPY emelkedés küszöb divergenciához | `market_regime.divergence.spy_change_threshold: 0.01` | ✅ Azonos |
| `bmi_divergence_bmi_change_pts` | -2.0 | P1 | BMI csökkenés küszöb divergenciához | `market_regime.divergence.bmi_change_threshold: -2.0` | ✅ Azonos |

### Universe Building — LONG

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `universe_min_market_cap` | 2B | P2 | Min piaci kap. | `universe.long.min_market_cap: 2B` | ✅ Azonos |
| `universe_min_price` | $5 | P2 | Min részvényárfolyam | `universe.long.min_price: 5` | ✅ Azonos |
| `universe_min_avg_volume` | 500K | P2 | Min átlag napi forgalom | `universe.long.min_volume: 1M` | ⚠️ **V13=1M, V2=500K** |
| `universe_require_options` | True | P2 | Kell-e opciós piac | Implicit | ✅ |

### Universe Building — SHORT (Zombie)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `zombie_min_market_cap` | 500M | P2 | Zombie min piaci kap. | `universe.zombie.min_market_cap: 500M` | ✅ Azonos |
| `zombie_min_avg_volume` | 500K | P2 | Zombie min forgalom | `universe.zombie.min_volume: 500K` | ✅ Azonos |
| `zombie_min_debt_equity` | 3.0 | P2 | D/E > 3.0 = pénzügyi nehézség | `universe.zombie.debt_equity_min: 3.0` | ✅ Azonos |
| `zombie_max_net_margin` | 0.0 | P2 | Negatív margin | `universe.zombie.net_margin_max: 0` | ✅ Azonos |
| `zombie_max_interest_coverage` | 1.5 | P2 | Alacsony kamatfedezet | `universe.zombie.interest_coverage_max: 1.5` | ✅ Azonos |
| `earnings_exclusion_days` | 5 | P2 | Earnings előtti kizárás | Implicit (5 nap) | ✅ Azonos |

### Sector Momentum (Phase 3)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `sector_leader_count` | 3 | P3 | Top 3 = Leader | `sector_engine.top_n: 3` | ✅ Azonos |
| `sector_laggard_count` | 3 | P3 | Bottom 3 = Laggard | `sector_engine.bottom_n: 3` | ✅ Azonos |
| `sector_leader_bonus` | +15 | P3,P4 | Leader score bonus | `sector_engine.mean_reversion.leader_bonus: 15` | ✅ Azonos |
| `sector_laggard_penalty` | -20 | P3,P4 | Laggard score penalty | `sector_engine.mean_reversion.standard_laggard_penalty: -20` | ✅ Azonos |
| `sector_laggard_mr_penalty` | -5 | P3,P4 | Laggard + Oversold (MR) | `sector_engine.mean_reversion.laggard_penalty_override: -5` | ✅ Azonos |
| `sector_momentum_period` | 5 | P3 | 5-day relative performance | `sector_engine.momentum_roc_period: 5` | ✅ Azonos |
| `max_positions_per_sector` | 3 | P6 | Max pozíció / szektor | `trading.sector_cap: 3` | ✅ Azonos |

### Individual Stock — RSI (Phase 4)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `rsi_oversold` | 30 | P4 | RSI < 30 → oversold | `technical.rsi.oversold: 30` | ✅ Azonos |
| `rsi_overbought` | 70 | P4 | RSI > 70 → overbought | `technical.rsi.overbought: 70` | ✅ Azonos |
| `rsi_oversold_bonus` | +5 | P4 | Oversold bonus (legacy) | — | Lecserélve RSI Ideal Zone-ra |
| `rsi_overbought_penalty` | -5 | P4 | Overbought penalty (legacy) | — | Lecserélve RSI Ideal Zone-ra |

### RSI Ideal Zone (BC9)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `rsi_ideal_inner_low` | 45 | P4 | Inner zone alsó határ | `technical.rsi.ideal_min: 45` | ✅ Azonos |
| `rsi_ideal_inner_high` | 65 | P4 | Inner zone felső határ | `technical.rsi.ideal_max: 65` | ✅ Azonos |
| `rsi_ideal_outer_low` | 35 | P4 | Outer zone alsó határ | Implicit | ✅ |
| `rsi_ideal_outer_high` | 75 | P4 | Outer zone felső határ | Implicit | ✅ |
| `rsi_ideal_inner_bonus` | 30 | P4 | [45-65] → +30 | +30 | ✅ Azonos |
| `rsi_ideal_outer_bonus` | 15 | P4 | [35-45) or (65-75] → +15 | +15 | ✅ Azonos |

### SMA50 & RS vs SPY (BC9)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `sma50_bonus` | 30 | P4 | Price > SMA50 → +30 | +30 | ✅ Azonos |
| `rs_spy_bonus` | 40 | P4 | 3-month outperformance vs SPY → +40 | +40 | ✅ Azonos |

### Individual Stock — RVOL (Phase 4)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `rvol_low` | 0.5 | P4 | RVOL < 0.5 → low | `flow.rvol.high: 1.5` | ✅ Küszöb eltér |
| `rvol_normal` | 1.0 | P4 | RVOL < 1.0 → normal | Implicit | ✅ |
| `rvol_elevated` | 1.5 | P4 | RVOL ≥ 1.5 → elevated | `flow.rvol.high: 1.5` | ✅ Azonos |
| `rvol_low_penalty` | -10 | P4 | Alacsony RVOL büntetés | Nincs ilyen | ⚠️ **V2 extra** |
| `rvol_elevated_bonus` | +5 | P4 | Emelt RVOL bonus | V13: +10 | ⚠️ **V13=+10, V2=+5** |
| `rvol_significant_bonus` | +15 | P4 | Jelentős RVOL bonus | V13: +20 | ⚠️ **V13=+20, V2=+15** |

### Squat Bar Detection (Phase 4)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `squat_bar_rvol_min` | 2.0 | P4 | Min RVOL squat bar-hoz | Nincs explicit | V2 újdonság |
| `squat_bar_spread_ratio_max` | 0.9 | P4 | Max spread ratio | Nincs explicit | V2 újdonság |
| `squat_bar_bonus` | +10 | P4 | Squat bar bonus | Nincs explicit | V2 újdonság |

### Options Flow Scoring (BC9)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `pcr_bullish_threshold` | 0.7 | P4 | PCR < 0.7 → bullish | `flow.options.pcr_bullish_max: 0.7` | ✅ Azonos |
| `pcr_bearish_threshold` | 1.3 | P4 | PCR > 1.3 → bearish | `flow.options.pcr_bearish_min: 1.3` | ✅ Azonos |
| `pcr_bullish_bonus` | 15 | P4 | Bullish PCR bonus | +15 | ✅ Azonos |
| `pcr_bearish_penalty` | -10 | P4 | Bearish PCR penalty | -10 | ✅ Azonos |
| `otm_call_ratio_threshold` | 0.4 | P4 | > 40% OTM calls → bonus | `flow.options.otm_call_threshold: 0.4` | ✅ Azonos |
| `otm_call_bonus` | 10 | P4 | OTM call bonus | +10 | ✅ Azonos |
| `block_trade_significant` | 5 | P4 | >5 blocks → bonus | V13: 5 | ✅ Azonos |
| `block_trade_very_high` | 20 | P4 | >20 blocks → higher bonus | V13: 20 | ✅ Azonos |
| `block_trade_significant_bonus` | 10 | P4 | Significant blocks bonus | +10 | ✅ Azonos |
| `block_trade_very_high_bonus` | 15 | P4 | Very high blocks bonus | +15 | ✅ Azonos |

### Dark Pool Percentage Scoring (BC10)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `dark_pool_volume_threshold_pct` | 40 | P4 | DP > 40% = signal | `strategy.dark_pool.min_pct: 40` | ✅ Azonos |
| `dp_pct_high_threshold` | 60 | P4 | dp_pct > 60% → higher bonus | Implicit | ✅ |
| `dp_pct_bonus` | 10 | P4 | dp_pct > 40% → +10 | +10 | ✅ Azonos |
| `dp_pct_high_bonus` | 15 | P4 | dp_pct > 60% → +15 | +15 | ✅ Azonos |

### Buy Pressure + VWAP (BC10)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `buy_pressure_strong_bonus` | 15 | P4 | buy_pos > 0.7 → +15 | +15 | ✅ Azonos |
| `buy_pressure_weak_penalty` | -15 | P4 | buy_pos < 0.3 → -15 | -15 | ✅ Azonos |
| `vwap_accumulation_bonus` | 10 | P4 | close > VWAP → +10 | +10 | ✅ Azonos |
| `vwap_distribution_penalty` | -5 | P4 | close < VWAP → -5 | -5 | ✅ Azonos |

### Shark Detector (BC9)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `shark_min_unique_insiders` | 2 | P4 | 2+ different insiders | 2 | ✅ Azonos |
| `shark_lookback_days` | 10 | P4 | Within 10 days | 10 | ✅ Azonos |
| `shark_min_total_value` | 100,000 | P4 | Total $100K+ | $100K | ✅ Azonos |
| `shark_score_bonus` | 10 | P4 | Shark detected → +10 funda | +10 | ✅ Azonos |

### Fundamental Scoring (Phase 4)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `funda_revenue_growth_good` | 10% | P4 | Jó revenue growth | `fundamental.growth.revenue_min: 20%` | ⚠️ **V13=20%, V2=10%** |
| `funda_revenue_growth_bad` | -10% | P4 | Rossz revenue growth | Implicit | ✅ |
| `funda_eps_growth_good` | 15% | P4 | Jó EPS growth | `fundamental.growth.eps_min: 20%` | ⚠️ **V13=20%, V2=15%** |
| `funda_eps_growth_bad` | -15% | P4 | Rossz EPS growth | Implicit | ✅ |
| `funda_net_margin_good` | 15% | P4 | Jó net margin | `fundamental.efficiency.net_margin_min: 10%` | ⚠️ **V13=10%, V2=15%** |
| `funda_net_margin_bad` | 0% | P4 | Rossz net margin | Implicit | ✅ |
| `funda_roe_good` | 15% | P4 | Jó ROE | `fundamental.efficiency.roe_min: 15%` | ✅ Azonos |
| `funda_roe_bad` | 5% | P4 | Rossz ROE | Implicit | ✅ |
| `funda_debt_equity_good` | 0.5 | P4 | Jó D/E | `fundamental.safety.debt_equity_max: 1.0` | ⚠️ **V13=1.0, V2=0.5** |
| `funda_debt_equity_bad` | 2.0 | P4 | Rossz D/E | Implicit | ✅ |
| `funda_interest_coverage_bad` | 1.5 | P4 | Rossz kamatfedezet | Implicit | ✅ |
| `funda_score_bonus` | +5 | P4 | Jó metrika bonus | V13: +15/+20 | ⚠️ **V13 nagyobb** |
| `funda_score_penalty` | -5 | P4 | Rossz metrika penalty | V13: 0 | ⚠️ **V2 extra** |
| `funda_debt_penalty` | -10 | P4 | Magas adósság büntetés | Implicit | ✅ |

### Insider Activity (Phase 4)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `insider_lookback_days` | 30 | P4 | Insider tevékenység ablak | `fundamental.insider.lookback_days: 30` | ✅ Azonos |
| `insider_strong_buy_threshold` | 3 | P4 | Net buys > 3 → strong buy | Implicit | ✅ |
| `insider_strong_sell_threshold` | -3 | P4 | Net sells < -3 → strong sell | Implicit | ✅ |
| `insider_buy_multiplier` | 1.25 | P6 | M_insider buy boost | `risk.multipliers.insider_bonus_multiplier: 1.25` | ✅ Azonos |
| `insider_sell_multiplier` | 0.75 | P6 | M_insider sell penalty | Implicit (0.75) | ✅ |

### Combined Score

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `combined_score_minimum` | 70 | P4 | Min score az elfogadáshoz | `scoring.thresholds.min_score: 70` | ✅ Azonos |

### GEX Multipliers (Phase 5→6)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `gex_positive_multiplier` | 1.0 | P6 | POSITIVE GEX → no change | Implicit (1.0) | ✅ Azonos |
| `gex_negative_multiplier` | 0.5 | P6 | NEGATIVE GEX → 50% méret | 0.5 | ✅ Azonos |
| `gex_high_vol_multiplier` | 0.6 | P6 | HIGH_VOL → 60% méret | 0.6 | ✅ Azonos |

### Call Wall ATR Filter (BC12)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `call_wall_max_atr_distance` | 5.0 | P5 | Max ATR multiples price→call wall | `scoring.gex.atr_distance_multiplier: 5.0` | ✅ Azonos |

### DTE Filter (BC12)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `gex_max_dte` | 90 | P4,P5 | Max DTE for options in GEX + flow scoring | `gex.front_month_dte: 35` | ⚠️ **V13=35, V2=90** |

### Sector Breadth (BC14)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `breadth_enabled` | True | P1,P3 | Breadth analízis be/ki | Nincs | V2 újdonság |
| `breadth_strong_threshold` | 70 | P3 | breadth_score > 70 → STRONG bonus | Nincs | V2 újdonság |
| `breadth_weak_threshold` | 50 | P3 | breadth_score < 50 → WEAK penalty | Nincs | V2 újdonság |
| `breadth_very_weak_threshold` | 30 | P3 | breadth_score < 30 → VERY WEAK penalty | Nincs | V2 újdonság |
| `breadth_strong_bonus` | 5 | P3 | STRONG breadth → +5 score adj | Nincs | V2 újdonság |
| `breadth_weak_penalty` | -5 | P3 | WEAK breadth → -5 score adj | Nincs | V2 újdonság |
| `breadth_very_weak_penalty` | -15 | P3 | VERY WEAK breadth → -15 score adj | Nincs | V2 újdonság |
| `breadth_divergence_penalty` | -10 | P3 | Bearish divergence → -10 extra | Nincs | V2 újdonság |
| `breadth_divergence_etf_threshold` | 2.0 | P3 | ETF 5d change % küszöb divergenciához | Nincs | V2 újdonság |
| `breadth_divergence_breadth_threshold` | 5.0 | P3 | SMA50 breadth momentum pont küszöb | Nincs | V2 újdonság |
| `breadth_min_constituents` | 10 | P3 | Min holdings a breadth számításhoz | Nincs | V2 újdonság |

### OBSIDIAN MM (BC15+BC16)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `obsidian_enabled` | False | P5 | OBSIDIAN klasszifikáció be/ki | Nincs | V2 újdonság |
| `obsidian_store_always_collect` | True | P5 | Feature store akkumuláció enabled/disabled-tól függetlenül | Nincs | V2 újdonság |
| `obsidian_regime_multipliers` | {VOLATILE: 0.6, Γ⁺: 1.5, Γ⁻: 0.25, DD: 1.25, ABS: 1.0, DIST: 0.5, NEU: 1.0, UND: 0.75} | P6 | Per-regime position sizing multiplier (8 regime — BC16) | Nincs | V2 újdonság |
| `factor_volatility_enabled` | False | P5 | Factor volatility framework be/ki (BC16) | Nincs | V2 újdonság |
| `factor_volatility_confidence_floor` | 0.6 | P5 | Min regime confidence — multiplier floor (BC16) | Nincs | V2 újdonság |

### VIX Thresholds (Phase 0→6)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `vix_low` | 15 | P0 | VIX < 15 = alacsony | Implicit | ✅ |
| `vix_normal` | 20 | P0 | VIX < 20 = normál | `macro.thresholds.vix_high: 20` | ✅ Azonos |
| `vix_elevated` | 30 | P0 | VIX > 30 = magas | `macro.thresholds.vix_extreme: 30` | ✅ Azonos |
| `vix_extreme_threshold` | 50 | P0 | VIX > 50 = EXTREME (BC12) | Nincs | V2 újdonság |
| `vix_extreme_multiplier` | 0.10 | P6 | EXTREME → position × 0.10 (BC12) | Nincs | V2 újdonság |
| `vix_penalty_start` | 20 | P6 | VIX büntetés kezdete | `risk.multipliers.vix_penalty_threshold: 20.0` | ✅ Azonos |
| `vix_penalty_rate` | 0.02 | P6 | -2% / VIX pont | `risk.multipliers.vix_penalty_slope: 0.02` | ✅ Azonos |
| `vix_multiplier_floor` | 0.25 | P6 | Min VIX multiplier | `risk.multipliers.vix_min_multiplier: 0.25` | ✅ Azonos |

### TNX Rate Sensitivity

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `tnx_sensitivity_pct` | 5 | P0,P3 | TNX > SMA20 × 1.05 → sensitive | Implicit | ✅ |
| `tnx_sensitive_sectors` | [Technology, Real Estate] | P3 | Kamatérzékeny szektorok | Implicit | ✅ |

### Risk Management Multipliers (Phase 6)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `multiplier_flow_threshold` | 80 | P6 | Flow > 80 → M_flow boost | `risk.multipliers.flow_bonus_threshold: 80` | ✅ Azonos |
| `multiplier_flow_value` | 1.25 | P6 | M_flow boost értéke | `risk.multipliers.flow_bonus_multiplier: 1.25` | ✅ Azonos |
| `multiplier_funda_threshold` | 60 | P6 | Funda < 60 → M_funda penalty | `risk.multipliers.funda_penalty_threshold: 60` | ✅ Azonos |
| `multiplier_funda_value` | 0.50 | P6 | M_funda penalty értéke | `risk.multipliers.funda_penalty_multiplier: 0.5` | ✅ Azonos |
| `multiplier_utility_threshold` | 85 | P6 | Score > 85 → M_utility boost | `risk.utility.threshold: 85.0` | ✅ Azonos |
| `multiplier_utility_max` | 1.3 | P6 | Max M_utility | `risk.utility.max_multiplier: 1.3` | ✅ Azonos |

### Sector BMI Thresholds

| ETF | Oversold | Overbought | V13 Oversold | V13 Overbought | Eltérés? |
|-----|----------|------------|-------------|----------------|----------|
| XLK | 12 | 85 | 12 | 85 | ✅ |
| XLF | 10 | 80 | 10 | 80 | ✅ |
| XLE | 10 | 75 | 10 | 75 | ✅ |
| XLV | 12 | 80 | 12 | 80 | ✅ |
| XLI | 12 | 80 | 12 | 80 | ✅ |
| XLP | 15 | 75 | 15 | 75 | ✅ |
| XLY | 9 | 80 | 9 | 80 | ✅ |
| XLB | 12 | 80 | 12 | 80 | ✅ |
| XLC | 12 | 80 | 12 | 80 | ✅ |
| XLRE | 9 | 85 | 9 | 85 | ✅ |
| XLU | 15 | 75 | 15 | 75 | ✅ |

### Danger Zone Filter (BC18-prep — T3 Bottom 10)

| Kulcs | Érték | Phase | Hatás |
|-------|-------|-------|-------|
| `danger_zone_enabled` | True | P4 | Explicit negatív szűrő engedélyezés |
| `danger_zone_debt_equity` | 5.0 | P4 | D/E > 5.0 = extrém tőkeáttétel |
| `danger_zone_net_margin` | -0.10 | P4 | Nettó margin < -10% = pénzégetés |
| `danger_zone_interest_coverage` | 1.0 | P4 | IC < 1.0 = adósságszolgálat fedezetlen |
| `danger_zone_min_signals` | 2 | P4 | Min 2 veszélyjel a szűréshez |

---

## RUNTIME — Környezet-Specifikus

Per-futtatás beállítások, .env-ből / config fájlból betöltve.

### Account

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `account_equity` | $100,000 | P6 | Számla méret | `risk.account_equity: 100000` | ✅ Azonos |
| `risk_per_trade_pct` | 0.5% | P6 | Kockázat / trade | `risk.risk_per_trade_pct: 1.5%` | ⚠️ **V13=1.5%, V2=0.5%** |

### Position Limits

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `max_positions` | 8 | P6 | Max párhuzamos pozíció | `trading.max_positions: 15` | ⚠️ **V13=15, V2=8** |
| `max_single_position_risk_pct` | 1.5% | P6 | Max egy pozíció kockázata | `risk.max_risk_pct: 3%` | ⚠️ **V13=3%, V2=1.5%** |
| `max_gross_exposure` | $100,000 | P6 | Max bruttó kitettség | `global_guard.max_gross_exposure: 35000` | ⚠️ **V13=35K, V2=100K** |
| `max_single_ticker_exposure` | $20,000 | P6 | Max ticker kitettség | `global_guard.max_ticker_exposure: 6000` | ⚠️ **V13=6K, V2=20K** |

### Fat Finger Protection (BC12)

| Kulcs | Érték | Phase | Hatás | V13 | Eltérés? |
|-------|-------|-------|-------|-----|----------|
| `max_order_quantity` | 5000 | P6 | Hard cap on shares per position | `global_guard.max_order_quantity: 5000` | ✅ Azonos |

### API Keys

| Kulcs | Env Var | Szükséges? |
|-------|---------|------------|
| `polygon_api_key` | IFDS_POLYGON_API_KEY | Igen (critical) |
| `unusual_whales_api_key` | IFDS_UW_API_KEY | Nem (opcionális) |
| `fmp_api_key` | IFDS_FMP_API_KEY | Igen (critical) |
| `fred_api_key` | IFDS_FRED_API_KEY | Igen (critical) |

### API Timeouts

| Kulcs | Érték | V13 |
|-------|-------|-----|
| `api_timeout_polygon` | 10s | `api.timeout: 30` |
| `api_timeout_polygon_options` | 15s | `api.timeout: 30` |
| `api_timeout_uw` | 10s | `api.timeout: 30` |
| `api_timeout_fmp` | 10s | `api.timeout: 30` |
| `api_timeout_fred` | 10s | `api.timeout: 30` |
| `api_max_retries` | 3 | `api.retries: 3` |

### Async Concurrency

| Kulcs | Érték | V13 | Megjegyzés |
|-------|-------|-----|------------|
| `async_enabled` | False | Nincs | V2 újdonság (IFDS_ASYNC_ENABLED=true) |
| `async_sem_polygon` | 10 | `api.concurrency.polygon: 20` | ⚠️ **V13=20, V2=10** (BC16: 5→10) |
| `async_sem_fmp` | 8 | `api.concurrency.fmp: 5` | ⚠️ **V13=5, V2=8** (BC16 tuned) |
| `async_sem_uw` | 5 | Nincs | V2 újdonság |
| `async_max_tickers` | 10 | Nincs | V2 újdonság (BC16 tuned) |

### Dark Pool Batch

| Kulcs | Érték | V13 | Megjegyzés |
|-------|-------|-----|------------|
| `dp_batch_max_pages` | 15 | Nincs | V2 újdonság (BC6) |
| `dp_batch_page_delay` | 0.5s | Nincs | V2 újdonság |
| `dp_batch_page_delay_async` | 0.3s | Nincs | V2 újdonság |

### Cache

| Kulcs | Érték | V13 | Megjegyzés |
|-------|-------|-----|------------|
| `cache_enabled` | False | Nincs | V2 újdonság (BC7) (IFDS_CACHE_ENABLED=true) |
| `cache_dir` | data/cache | Nincs | V2 újdonság |
| `cache_max_age_days` | 7 | Nincs | V2 újdonság |

### Circuit Breaker (Drawdown)

| Kulcs | Érték | V13 | Eltérés? |
|-------|-------|-----|----------|
| `circuit_breaker_drawdown_limit_pct` | 3.0% | `global_guard.drawdown_circuit_breaker_pct: 5%` | ⚠️ **V13=5%, V2=3%** |
| `circuit_breaker_state_file` | state/circuit_breaker.json | `global_guard.persistence_file` | Más path |

### Per-provider Circuit Breaker (BC11)

| Kulcs | Érték | V13 | Megjegyzés |
|-------|-------|-----|------------|
| `cb_window_size` | 50 | Nincs | Sliding window meret |
| `cb_error_threshold` | 0.3 | `scanning.error_rate_abort_threshold: 0.3` | ✅ Azonos |
| `cb_cooldown_seconds` | 60 | Nincs | OPEN → HALF_OPEN cooldown |

### Signal Deduplication (BC11)

| Kulcs | Érték | V13 | Megjegyzés |
|-------|-------|-----|------------|
| `signal_hash_file` | state/signal_hashes.json | `global_guard.signal_hash_file` | ✅ Funkcionálisan azonos |

### Survivorship Bias (BC13)

| Kulcs | Érték | V13 | Megjegyzés |
|-------|-------|-----|------------|
| `survivorship_snapshot_dir` | state/universe_snapshots | Nincs | Universe snapshot mappa |
| `survivorship_max_snapshots` | 30 | Nincs | Max megőrzött snapshot |

### Telegram Alerts (BC13)

| Kulcs | Érték | Env Var | Megjegyzés |
|-------|-------|---------|------------|
| `telegram_bot_token` | None | IFDS_TELEGRAM_BOT_TOKEN | Opcionális — ha nincs, alerts disabled |
| `telegram_chat_id` | None | IFDS_TELEGRAM_CHAT_ID | Opcionális — mindkettő kell |
| `telegram_timeout` | 5 | — | HTTP POST timeout (s) |

### Max Daily Trades (BC13)

| Kulcs | Érték | V13 | Megjegyzés |
|-------|-------|-----|------------|
| `max_daily_trades` | 20 | `global_guard.max_daily_trades: 20` | ✅ Azonos |
| `daily_trades_file` | state/daily_trades.json | Nincs | State file (midnight reset) |

### Notional Limits (BC13)

| Kulcs | Érték | V13 | Megjegyzés |
|-------|-------|-----|------------|
| `max_daily_notional` | 200,000 | Nincs | Napi összesített notional cap |
| `max_position_notional` | 25,000 | `global_guard.max_order_value: 1500` | ⚠️ **V13=$1.5K, V2=$25K** |
| `daily_notional_file` | state/daily_notional.json | Nincs | State file (midnight reset) |

### OBSIDIAN Feature Store (BC15)

| Kulcs | Érték | V13 | Megjegyzés |
|-------|-------|-----|------------|
| `obsidian_store_dir` | state/obsidian | Nincs | Per-ticker JSON feature history mappa |
| `obsidian_max_store_entries` | 100 | Nincs | Max napi entry per ticker (trim oldest) |

### Phase 4 Snapshot (BC19)

| Kulcs | Érték | V13 | Megjegyzés |
|-------|-------|-----|------------|
| `phase4_snapshot_enabled` | True | Nincs | Napi Phase 4 StockAnalysis mentés |
| `phase4_snapshot_dir` | state/phase4_snapshots | Nincs | Gzipped JSON snapshot mappa |

### Output

| Kulcs | Érték | V13 |
|-------|-------|-----|
| `output_dir` | output | `history.execution.directory: data` |
| `log_dir` | logs | `logging.file.path: moneyflows.log` |
| `signal_history_file` | state/signal_history.parquet | `signal_history.file: data/signal_history.parquet` |

---

## Összefoglaló: Szignifikáns V13→V2 Eltérések

| Paraméter | V13 | V2 | Hatás |
|-----------|-----|-----|-------|
| `freshness_bonus` | **1.75** | **1.5** | V13 agresszívebb freshness boost |
| `clipping_threshold` | **85** | **95** | V13 korábban clippel |
| `tp2_atr_multiple` | **4R** | **3R** | V13 nagyobb TP2 target |
| `scale_out_pct` | **50%** | **33%** | V13 több pozíciót zár |
| `risk_per_trade_pct` | **1.5%** | **0.5%** | V13 3× agresszívebb |
| `max_positions` | **15** | **8** | V13 több pozíciót tart |
| `universe_min_avg_volume` | **1M** | **500K** | V2 lazább likviditás filter |
| `sma_short_period` | **50** | **20** | V2 rövidebb trend filter |
| `funda_revenue_growth_good` | **20%** | **10%** | V2 lazább fundamental filter |
| `async_sem_polygon` | **20** | **10** | V2 konzervatívabb rate limit (BC16) |
| `gex_max_dte` | **35** | **90** | V2 szélesebb options ablak |

**Figyelem**: A V13 settings.yaml "20-DAY TEST CONFIGURATION" megjegyzéssel van ellátva — egyes értékek (risk_per_trade: 1.5%, max_positions: 15) tesztelési célúak, nem prod értékek.
