"""MMS — Market Microstructure Scorer (BC15).

Market microstructure diagnostic engine for IFDS.
No new API calls — reuses Polygon bars, options snapshot, and dark pool batch.

7 regimes (priority-ordered):
  1. Γ⁺ (gamma_positive)  — volatility suppression
  2. Γ⁻ (gamma_negative)  — liquidity vacuum
  3. DD (dark_dominant)    — institutional accumulation
  4. ABS (absorption)      — passive absorption
  5. DIST (distribution)   — distribution into strength
  6. NEU (neutral)         — no rule matched
  7. UND (undetermined)    — insufficient baseline

Unusualness score U ∈ [0, 100]: weighted |Z| sum → percentile rank.
"""

import math
from datetime import date as _date

from ifds.data.mms_store import MMSStore
from ifds.models.market import (
    BaselineState,
    GEXRegime,
    MMRegime,
    MMSAnalysis,
    StockAnalysis,
)


# ============================================================================
# Feature Extraction
# ============================================================================

def _extract_features_from_bars(bars: list[dict], window: int = 63) -> dict:
    """Extract price-derived features from OHLCV bars.

    Returns dict with efficiency/impact series (for z-scores from bars)
    plus today's values and daily return.
    """
    if not bars or len(bars) < 2:
        return {}

    # Use last `window` bars for series
    recent = bars[-window:] if len(bars) >= window else bars

    efficiency_series = []
    impact_series = []
    for bar in recent:
        h, l, c, o = bar.get("h", 0), bar.get("l", 0), bar.get("c", 0), bar.get("o", 0)
        v = bar.get("v", 0)
        if v > 0:
            efficiency_series.append((h - l) / v)
            impact_series.append(abs(c - o) / v)

    # Daily return from last two bars
    prev_c = bars[-2].get("c", 0)
    curr_c = bars[-1].get("c", 0)
    daily_return = (curr_c - prev_c) / prev_c if prev_c != 0 else 0.0

    return {
        "efficiency_series": efficiency_series,
        "impact_series": impact_series,
        "efficiency_today": efficiency_series[-1] if efficiency_series else 0.0,
        "impact_today": impact_series[-1] if impact_series else 0.0,
        "daily_return": daily_return,
    }


def _compute_dex(options_data: list[dict], current_price: float) -> float:
    """Net Dealer Delta Exposure from Polygon options snapshot.

    DEX = Σ(delta × OI × 100) for calls - Σ(|delta| × OI × 100) for puts.
    Reuses same options data already fetched for PCR/OTM/GEX.
    """
    if not options_data or current_price <= 0:
        return 0.0

    call_dex = 0.0
    put_dex = 0.0

    for opt in options_data:
        details = opt.get("details", {})
        greeks = opt.get("greeks", {})
        day = opt.get("day", {})

        delta = greeks.get("delta", 0) or 0
        oi = opt.get("open_interest", day.get("open_interest", 0)) or 0
        contract_type = details.get("contract_type", "").lower()

        if oi <= 0:
            continue

        if contract_type == "call":
            call_dex += delta * oi * 100
        elif contract_type == "put":
            put_dex += abs(delta) * oi * 100

    return call_dex - put_dex


def _compute_aggregate_iv(options_data: list[dict], current_price: float) -> float:
    """Average ATM implied volatility from Polygon options snapshot.

    Filters ATM-ish contracts (strike within 5% of current_price).
    Returns average IV or 0.0 if no data.
    """
    if not options_data or current_price <= 0:
        return 0.0

    atm_ivs = []
    low = current_price * 0.95
    high = current_price * 1.05

    for opt in options_data:
        details = opt.get("details", {})
        strike = details.get("strike_price", 0)
        if not (low <= strike <= high):
            continue

        iv = opt.get("implied_volatility")
        if iv is not None and iv > 0:
            atm_ivs.append(iv)

    return sum(atm_ivs) / len(atm_ivs) if atm_ivs else 0.0


# ============================================================================
# Z-Score Computation
# ============================================================================

def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float], mean_val: float) -> float:
    if len(values) < 2:
        return 0.0
    variance = sum((v - mean_val) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def _z_score(value: float, values: list[float], min_n: int) -> float | None:
    """Compute z-score. Returns None if insufficient data or zero std."""
    if len(values) < min_n:
        return None
    m = _mean(values)
    s = _std(values, m)
    if s == 0:
        return None
    return (value - m) / s


def _compute_z_scores(today_features: dict, historical_entries: list[dict],
                      bar_features: dict, min_periods: int) -> dict[str, float | None]:
    """Compute z-scores for each MMS feature.

    Price features (efficiency, impact): use bar_features series (250 values available).
    Microstructure features (gex, dex, dark_share, block, iv): use store entries.
    Returns {feature: z_score_or_None}. None if n < min_periods or std == 0.
    """
    z = {}

    # Price-based z-scores from bars (always available from Day 1)
    eff_series = bar_features.get("efficiency_series", [])
    imp_series = bar_features.get("impact_series", [])
    z["efficiency"] = _z_score(
        today_features.get("efficiency", 0.0), eff_series, min_periods
    )
    z["impact"] = _z_score(
        today_features.get("impact", 0.0), imp_series, min_periods
    )

    # Microstructure z-scores from store
    store_features = ["dark_share", "gex", "dex", "block_count", "iv_rank"]
    for feat in store_features:
        series = [e.get(feat) for e in historical_entries if e.get(feat) is not None]
        series = [float(v) for v in series]
        z[feat] = _z_score(today_features.get(feat, 0.0), series, min_periods)

    return z


def _compute_medians(bar_features: dict) -> dict[str, float]:
    """Compute median efficiency and impact from bar series."""
    medians = {}
    for key in ("efficiency_series", "impact_series"):
        series = bar_features.get(key, [])
        if series:
            sorted_s = sorted(series)
            n = len(sorted_s)
            if n % 2 == 0:
                medians[key.replace("_series", "")] = (sorted_s[n // 2 - 1] + sorted_s[n // 2]) / 2
            else:
                medians[key.replace("_series", "")] = sorted_s[n // 2]
        else:
            medians[key.replace("_series", "")] = 0.0
    return medians


# ============================================================================
# Factor Volatility (BC16)
# ============================================================================

def _compute_factor_volatility(historical_entries: list[dict],
                                window: int = 20) -> dict[str, float | None]:
    """Compute rolling σ for each microstructure feature over last `window` entries.

    Returns {feature: σ_value_or_None}. None if insufficient data.
    """
    features = ["gex", "dex", "dark_share", "block_count", "iv_rank"]
    result = {}

    for feat in features:
        series = [float(e[feat]) for e in historical_entries
                  if e.get(feat) is not None]
        if len(series) >= window:
            recent = series[-window:]
            m = sum(recent) / len(recent)
            var = sum((v - m) ** 2 for v in recent) / (len(recent) - 1)
            result[feat] = math.sqrt(var)
        else:
            result[feat] = None

    return result


def _compute_median_rolling_sigmas(historical_entries: list[dict],
                                    window: int = 20) -> dict[str, float]:
    """Compute median of rolling σ for each feature across the full history.

    For each feature, computes rolling σ at every valid position,
    then returns the median. Used as the baseline for VOLATILE detection
    and regime confidence.
    """
    features = ["gex", "dex", "dark_share", "block_count", "iv_rank"]
    result = {}

    for feat in features:
        series = [float(e[feat]) for e in historical_entries
                  if e.get(feat) is not None]
        if len(series) < window * 2:
            result[feat] = 0.0
            continue

        rolling_sigmas = []
        for i in range(window, len(series) + 1):
            segment = series[i - window:i]
            m = sum(segment) / len(segment)
            var = sum((v - m) ** 2 for v in segment) / (len(segment) - 1)
            rolling_sigmas.append(math.sqrt(var))

        if not rolling_sigmas:
            result[feat] = 0.0
            continue

        sorted_s = sorted(rolling_sigmas)
        n = len(sorted_s)
        if n % 2 == 0:
            result[feat] = (sorted_s[n // 2 - 1] + sorted_s[n // 2]) / 2
        else:
            result[feat] = sorted_s[n // 2]

    return result


def _compute_regime_confidence(factor_vol: dict[str, float | None],
                                median_sigmas: dict[str, float],
                                floor: float = 0.6) -> float:
    """Compute regime confidence based on GEX volatility stability.

    confidence = 1.0 - min(1.0, σ_20(gex) / median(σ_20(gex)))
    Returns [floor, 1.0]. Higher = more stable regime.
    """
    sigma_gex = factor_vol.get("gex")
    median_sigma_gex = median_sigmas.get("gex", 0.0)

    if sigma_gex is None or median_sigma_gex == 0:
        return 1.0  # No data → assume stable

    ratio = sigma_gex / median_sigma_gex
    confidence = max(0.0, 1.0 - min(1.0, ratio))
    return max(floor, confidence)


# ============================================================================
# Classification (priority-ordered rules)
# ============================================================================

def _determine_baseline_state(z_scores: dict, min_periods: int,
                              historical_count: int) -> BaselineState:
    """Determine baseline maturity based on z-score availability."""
    if historical_count == 0:
        return BaselineState.EMPTY

    micro_features = ["dark_share", "gex", "dex", "block_count", "iv_rank"]
    valid_count = sum(1 for f in micro_features if z_scores.get(f) is not None)

    if valid_count == len(micro_features):
        return BaselineState.COMPLETE
    elif valid_count > 0:
        return BaselineState.PARTIAL
    else:
        return BaselineState.EMPTY


def _classify_regime(z_scores: dict, raw_features: dict,
                     medians: dict, daily_return: float,
                     baseline_state: BaselineState,
                     config_core: dict,
                     factor_vol: dict | None = None,
                     median_sigmas: dict | None = None) -> tuple[MMRegime, dict]:
    """Priority-ordered MMS classification.

    Rules (first match wins):
    0. UND: baseline empty
    0.5 VOL: σ_gex > 2× median AND σ_dex > 2× median (BC16)
    1. Γ⁺: z_gex > +1.5 AND efficiency < median
    2. Γ⁻: z_gex < -1.5 AND impact > median
    3. DD: dark_share > 0.70 AND z_block > +1.0
    4. ABS: z_dex < -1.0 AND return >= -0.5% AND dark_share > 0.50
    5. DIST: z_dex > +1.0 AND return <= +0.5%
    6. NEU: no rule matched (with some baseline data)

    Returns (regime, triggering_conditions).
    """
    z_gex_th = config_core.get("mms_z_gex_threshold", 1.5)
    z_dex_th = config_core.get("mms_z_dex_threshold", 1.0)
    z_block_th = config_core.get("mms_z_block_threshold", 1.0)
    dark_dd = config_core.get("mms_dark_share_dd", 0.70)
    dark_abs = config_core.get("mms_dark_share_abs", 0.50)
    return_abs = config_core.get("mms_return_abs", -0.005)
    return_dist = config_core.get("mms_return_dist", 0.005)

    z_gex = z_scores.get("gex")
    z_dex = z_scores.get("dex")
    z_block = z_scores.get("block_count")
    dark_share = raw_features.get("dark_share", 0.0)
    efficiency = raw_features.get("efficiency", 0.0)
    impact = raw_features.get("impact", 0.0)
    median_eff = medians.get("efficiency", 0.0)
    median_imp = medians.get("impact", 0.0)

    # UND: baseline empty → cannot classify
    if baseline_state == BaselineState.EMPTY:
        return MMRegime.UNDETERMINED, {"reason": "baseline_empty"}

    # Rule 0.5: VOLATILE — σ_gex > 2× median AND σ_dex > 2× median (BC16)
    if factor_vol and median_sigmas:
        sigma_gex = factor_vol.get("gex")
        sigma_dex = factor_vol.get("dex")
        median_sigma_gex = median_sigmas.get("gex", 0)
        median_sigma_dex = median_sigmas.get("dex", 0)
        if (sigma_gex is not None and sigma_dex is not None
                and median_sigma_gex > 0 and median_sigma_dex > 0
                and sigma_gex > 2 * median_sigma_gex
                and sigma_dex > 2 * median_sigma_dex):
            return MMRegime.VOLATILE, {
                "sigma_gex": sigma_gex, "sigma_dex": sigma_dex,
                "median_sigma_gex": median_sigma_gex,
                "median_sigma_dex": median_sigma_dex,
            }

    # Rule 1: Γ⁺ — z_gex > +threshold AND efficiency < median
    if z_gex is not None and z_gex > z_gex_th and efficiency < median_eff:
        return MMRegime.GAMMA_POSITIVE, {
            "z_gex": z_gex, "efficiency": efficiency, "median_eff": median_eff,
        }

    # Rule 2: Γ⁻ — z_gex < -threshold AND impact > median
    if z_gex is not None and z_gex < -z_gex_th and impact > median_imp:
        return MMRegime.GAMMA_NEGATIVE, {
            "z_gex": z_gex, "impact": impact, "median_imp": median_imp,
        }

    # Rule 3: DD — dark_share > 0.70 AND z_block > +1.0
    if dark_share > dark_dd and z_block is not None and z_block > z_block_th:
        return MMRegime.DARK_DOMINANT, {
            "dark_share": dark_share, "z_block": z_block,
        }

    # Rule 4: ABS — z_dex < -1.0 AND return >= -0.5% AND dark_share > 0.50
    if (z_dex is not None and z_dex < -z_dex_th
            and daily_return >= return_abs and dark_share > dark_abs):
        return MMRegime.ABSORPTION, {
            "z_dex": z_dex, "daily_return": daily_return, "dark_share": dark_share,
        }

    # Rule 5: DIST — z_dex > +1.0 AND return <= +0.5%
    if z_dex is not None and z_dex > z_dex_th and daily_return <= return_dist:
        return MMRegime.DISTRIBUTION, {
            "z_dex": z_dex, "daily_return": daily_return,
        }

    # Rule 6: NEU — no rule matched
    return MMRegime.NEUTRAL, {"reason": "no_rule_matched"}


# ============================================================================
# Unusualness Score
# ============================================================================

def _compute_unusualness(z_scores: dict, excluded_features: list[str],
                         feature_weights: dict,
                         historical_raw_scores: list[float],
                         factor_vol: dict | None = None,
                         median_sigmas: dict | None = None) -> float:
    """Compute unusualness score U ∈ [0, 100].

    Without factor vol: S = Σ(w_k × |z_k|)
    With factor vol (BC16): S = Σ(w_k × |z_k| × (1 + σ_20_norm))
      where σ_20_norm = σ_20(feat) / median(σ_20(feat)), or 0 if unavailable.

    U = PercentileRank(S | historical raw scores) × 100.
    If no history, use linear mapping capped at 100.
    """
    # Scoring features (the 5 weighted ones)
    scoring_features = ["dark_share", "gex", "block_count", "iv_rank"]
    # venue_mix always excluded

    raw_score = 0.0
    for feat in scoring_features:
        if feat in excluded_features:
            continue
        z = z_scores.get(feat)
        if z is None:
            continue
        # Map feature names to weight keys
        weight_key = feat
        if feat == "block_count":
            weight_key = "block_intensity"
        w = feature_weights.get(weight_key, 0.0)

        # Factor volatility weighting (BC16)
        vol_mult = 1.0
        if factor_vol and median_sigmas:
            sigma = factor_vol.get(feat)
            median_sigma = median_sigmas.get(feat, 0)
            if sigma is not None and median_sigma > 0:
                vol_mult = 1.0 + (sigma / median_sigma)

        raw_score += w * abs(z) * vol_mult

    # Percentile rank against history
    if historical_raw_scores and len(historical_raw_scores) >= 5:
        count_below = sum(1 for s in historical_raw_scores if s <= raw_score)
        u = (count_below / len(historical_raw_scores)) * 100.0
    else:
        # Linear mapping: S of 2.0 → U=100 (generous early mapping)
        u = min(100.0, raw_score * 50.0)

    return round(min(100.0, max(0.0, u)), 1)


# ============================================================================
# Top-level Per-ticker Function
# ============================================================================

def _get_regime_multiplier(regime: MMRegime, config_tuning: dict) -> float:
    """Look up sizing multiplier for a regime."""
    multipliers = config_tuning.get("mms_regime_multipliers", {})
    return multipliers.get(regime.value, 0.75)


def run_mms_analysis(
    config_core: dict,
    config_tuning: dict,
    ticker: str,
    bars: list[dict] | None,
    options_data: list[dict] | None,
    stock: StockAnalysis,
    gex_data: dict | None,
    store: MMSStore,
) -> MMSAnalysis:
    """Full MMS analysis for one ticker.

    1. Extract features from bars/options/stock.flow
    2. Load historical entries from store
    3. Compute z-scores (bar-based + store-based)
    4. Determine baseline state
    5. Classify regime
    6. Compute unusualness score
    7. Get multiplier from regime
    8. Append today's features to store
    """
    result = MMSAnalysis(ticker=ticker)
    excluded_features = ["venue_mix"]  # Always excluded
    result.excluded_features = excluded_features

    window = config_core.get("mms_window", 63)
    min_periods = config_core.get("mms_min_periods", 21)
    feature_weights = config_core.get("mms_feature_weights", {})

    # 1. Extract features
    bar_features = _extract_features_from_bars(bars, window) if bars else {}
    if not bar_features:
        result.mm_regime = MMRegime.UNDETERMINED
        result.baseline_state = BaselineState.EMPTY
        result.baseline_days = len(store.load(ticker))
        result.regime_multiplier = _get_regime_multiplier(MMRegime.UNDETERMINED, config_tuning)
        return result

    current_price = stock.technical.price if stock.technical else 0.0

    # Raw features for today
    dex = _compute_dex(options_data, current_price) if options_data else 0.0
    iv_rank = _compute_aggregate_iv(options_data, current_price) if options_data else 0.0
    dark_share = stock.flow.dark_pool_pct / 100.0 if stock.flow else 0.0
    block_count = float(stock.flow.block_trade_count) if stock.flow else 0.0
    net_gex = gex_data.get("net_gex", 0.0) if gex_data else 0.0

    today_features = {
        "efficiency": bar_features.get("efficiency_today", 0.0),
        "impact": bar_features.get("impact_today", 0.0),
        "dark_share": dark_share,
        "gex": net_gex,
        "dex": dex,
        "block_count": block_count,
        "iv_rank": iv_rank,
    }

    # 2. Load history from store
    historical = store.load(ticker)
    result.baseline_days = len(historical)

    # 3. Compute z-scores
    z_scores = _compute_z_scores(today_features, historical, bar_features, min_periods)

    # 3b. Factor Volatility (BC16)
    fv_enabled = config_tuning.get("factor_volatility_enabled", False)
    factor_vol = None
    median_sigmas = None
    if fv_enabled and historical:
        fv_window = config_tuning.get("factor_volatility_window", 20)
        factor_vol = _compute_factor_volatility(historical, fv_window)
        median_sigmas = _compute_median_rolling_sigmas(historical, fv_window)
        result.factor_volatility = {k: v for k, v in factor_vol.items() if v is not None}

    # 4. Baseline state
    baseline_state = _determine_baseline_state(z_scores, min_periods, len(historical))
    result.baseline_state = baseline_state

    # 5. Classify regime
    medians = _compute_medians(bar_features)
    daily_return = bar_features.get("daily_return", 0.0)
    regime, conditions = _classify_regime(
        z_scores, today_features, medians, daily_return, baseline_state, config_core,
        factor_vol=factor_vol, median_sigmas=median_sigmas,
    )
    result.mm_regime = regime
    result.triggering_conditions = conditions

    # 6. Unusualness score
    historical_raw_scores = store.get_feature_series(historical, "raw_score")
    raw_score = 0.0
    scoring_features = ["dark_share", "gex", "block_count", "iv_rank"]
    for feat in scoring_features:
        if feat in excluded_features:
            continue
        z = z_scores.get(feat)
        if z is None:
            continue
        weight_key = "block_intensity" if feat == "block_count" else feat
        raw_score += feature_weights.get(weight_key, 0.0) * abs(z)

    result.unusualness_score = _compute_unusualness(
        z_scores, excluded_features, feature_weights, historical_raw_scores,
        factor_vol=factor_vol, median_sigmas=median_sigmas,
    )

    # Top drivers: features with highest |z| contribution
    drivers = []
    for feat in scoring_features:
        z = z_scores.get(feat)
        if z is not None and feat not in excluded_features:
            weight_key = "block_intensity" if feat == "block_count" else feat
            w = feature_weights.get(weight_key, 0.0)
            drivers.append((feat, w * abs(z)))
    drivers.sort(key=lambda x: x[1], reverse=True)
    result.top_drivers = [d[0] for d in drivers[:3]]

    # 7. Multiplier (with confidence adjustment — BC16)
    base_mult = _get_regime_multiplier(regime, config_tuning)
    if fv_enabled and factor_vol and median_sigmas:
        floor = config_tuning.get("factor_volatility_confidence_floor", 0.6)
        confidence = _compute_regime_confidence(factor_vol, median_sigmas, floor)
        result.regime_confidence = confidence
        result.regime_multiplier = base_mult * max(floor, confidence)
    else:
        result.regime_multiplier = base_mult

    # 8. Append today's entry to store
    entry = {
        "date": _date.today().isoformat(),
        "dark_share": dark_share,
        "gex": net_gex,
        "dex": dex,
        "block_count": block_count,
        "iv_rank": iv_rank,
        "efficiency": today_features["efficiency"],
        "impact": today_features["impact"],
        "daily_return": daily_return,
        "raw_score": raw_score,
    }
    store.append_and_save(ticker, entry, existing=historical)

    return result
