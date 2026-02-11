"""Phase 3: Sector Rotation & Momentum.

Analyzes the 11 SPDR sector ETFs to determine:
1. Momentum ranking (5-day relative performance)
2. Trend (Price vs SMA20)
3. Leader / Neutral / Laggard classification
4. Sector BMI with per-sector oversold/overbought thresholds
5. Veto Matrix for LONG strategy
6. TNX rate sensitivity for Tech/Real Estate

The veto matrix (LONG strategy):
| Momentum | Sector BMI   | Decision          | Score adj |
|----------|-------------|-------------------|-----------|
| Leader   | Any         | ALLOWED           | +15       |
| Neutral  | NEUTRAL     | ALLOWED           | 0         |
| Neutral  | OVERSOLD    | ALLOWED           | 0         |
| Neutral  | OVERBOUGHT  | VETO              | —         |
| Laggard  | OVERSOLD    | ALLOWED (MR)      | -5        |
| Laggard  | NEUTRAL     | VETO              | —         |
| Laggard  | OVERBOUGHT  | VETO              | —         |
"""

import time
from datetime import date, timedelta

from ifds.config.loader import Config
from ifds.data.polygon import PolygonClient
from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity
from ifds.models.market import (
    BreadthRegime,
    MacroRegime,
    MomentumClassification,
    Phase3Result,
    SectorBMIRegime,
    SectorBreadth,
    SectorScore,
    SectorTrend,
    StrategyMode,
)

# ETF → Sector Name mapping
SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLV": "Healthcare",
    "XLI": "Industrials",
    "XLP": "Consumer Defensive",
    "XLY": "Consumer Cyclical",
    "XLB": "Basic Materials",
    "XLC": "Communication Services",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
}


def run_phase3(config: Config, logger: EventLogger,
               polygon: PolygonClient,
               strategy_mode: StrategyMode,
               macro: MacroRegime | None = None,
               sector_bmi_values: dict[str, float] | None = None,
               grouped_daily_bars: list[dict] | None = None,
               fmp=None) -> Phase3Result:
    """Execute Phase 3: Sector Rotation analysis.

    Args:
        config: Validated IFDS configuration.
        logger: Event logger for audit trail.
        polygon: Polygon client for ETF price data.
        strategy_mode: LONG or SHORT from Phase 1.
        macro: Macro regime from Phase 0 (for TNX rate sensitivity).

    Returns:
        Phase3Result with sector scores, vetoes, and active sectors.
    """
    start_time = time.monotonic()
    logger.phase_start(3, "Sector Rotation")

    try:
        momentum_period = config.tuning["sector_momentum_period"]
        sma_period = config.core["sma_short_period"]  # SMA20

        # Fetch price data for all sector ETFs
        sector_data = _fetch_sector_data(polygon, momentum_period, sma_period)

        # Calculate momentum and trend for each sector
        scores = _calculate_sector_scores(sector_data, config)

        # Populate sector BMI from Phase 1 data
        if sector_bmi_values:
            for score in scores:
                if score.etf in sector_bmi_values:
                    score.sector_bmi = sector_bmi_values[score.etf]

        # Rank and classify (Leader / Neutral / Laggard)
        _rank_sectors(scores, config)

        # Apply sector BMI regimes
        _apply_sector_bmi(scores, config)

        # Apply sector breadth analysis (BC14)
        breadth_enabled = config.tuning.get("breadth_enabled", False)
        if breadth_enabled and grouped_daily_bars and fmp:
            _calculate_sector_breadth(scores, grouped_daily_bars, fmp, config, logger)

        # Apply veto matrix (only for LONG strategy)
        if strategy_mode == StrategyMode.LONG:
            _apply_veto_matrix(scores, config, logger)

        # Apply TNX rate sensitivity
        rate_sensitive = False
        if macro and macro.tnx_rate_sensitive:
            rate_sensitive = True
            _apply_rate_sensitivity(scores, config, logger)

        # Build result
        vetoed = [s.etf for s in scores if s.vetoed]
        active = [s.etf for s in scores if not s.vetoed]

        result = Phase3Result(
            sector_scores=scores,
            vetoed_sectors=vetoed,
            active_sectors=active,
            rate_sensitive_penalty=rate_sensitive,
        )

        # Log summary
        logger.log(
            EventType.PHASE_COMPLETE, Severity.INFO, phase=3,
            message=(
                f"Sectors: {len(active)} active, {len(vetoed)} vetoed"
                f"{', rate_sensitive' if rate_sensitive else ''}"
            ),
            data={
                "active_count": len(active),
                "vetoed_count": len(vetoed),
                "vetoed_sectors": vetoed,
                "leaders": [s.etf for s in scores
                            if s.classification == MomentumClassification.LEADER],
                "laggards": [s.etf for s in scores
                             if s.classification == MomentumClassification.LAGGARD],
                "rate_sensitive_penalty": rate_sensitive,
            },
        )

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.phase_complete(3, "Sector Rotation", duration_ms=duration_ms)

        return result

    except Exception as e:
        logger.phase_error(3, "Sector Rotation", str(e))
        raise


def _fetch_sector_data(polygon: PolygonClient,
                       momentum_period: int,
                       sma_period: int,
                       etf_override: dict[str, str] | None = None) -> dict[str, dict]:
    """Fetch OHLCV data for sector ETFs (or custom ETF list).

    Args:
        etf_override: If set, fetch only these ETFs instead of SECTOR_ETFS.

    Returns dict: etf -> {bars: [...], close_today, close_5d_ago, sma20}
    """
    today = date.today()
    # Need enough calendar days to cover trading days for SMA20
    lookback = max(momentum_period, sma_period) + 15  # Buffer for weekends/holidays
    from_date = (today - timedelta(days=lookback)).isoformat()
    to_date = today.isoformat()

    sector_data = {}
    etf_list = etf_override or SECTOR_ETFS

    for etf in etf_list:
        bars = polygon.get_aggregates(etf, from_date, to_date)
        if not bars or len(bars) < momentum_period + 1:
            continue

        closes = [b["c"] for b in bars if "c" in b]
        if len(closes) < momentum_period + 1:
            continue

        close_today = closes[-1]
        close_period_ago = closes[-(momentum_period + 1)]

        # SMA20
        sma20 = None
        if len(closes) >= sma_period:
            sma20 = sum(closes[-sma_period:]) / sma_period

        sector_data[etf] = {
            "bars": bars,
            "close_today": close_today,
            "close_period_ago": close_period_ago,
            "sma20": sma20,
        }

    return sector_data


def _calculate_sector_scores(sector_data: dict[str, dict],
                             config: Config,
                             name_override: dict[str, str] | None = None) -> list[SectorScore]:
    """Calculate momentum and trend for each sector.

    Args:
        name_override: If set, use these names instead of SECTOR_ETFS lookup.
    """
    scores = []
    names = name_override or SECTOR_ETFS

    for etf, data in sector_data.items():
        close_today = data["close_today"]
        close_ago = data["close_period_ago"]
        sma20 = data["sma20"]

        # Momentum = 5d relative performance %
        if close_ago > 0:
            momentum = ((close_today - close_ago) / close_ago) * 100
        else:
            momentum = 0.0

        # Trend = UP if price > SMA20
        if sma20 and sma20 > 0:
            trend = SectorTrend.UP if close_today > sma20 else SectorTrend.DOWN
        else:
            trend = SectorTrend.UP  # Default

        score = SectorScore(
            etf=etf,
            sector_name=names.get(etf, etf),
            momentum_5d=round(momentum, 3),
            trend=trend,
        )
        scores.append(score)

    return scores


def _rank_sectors(scores: list[SectorScore], config: Config) -> None:
    """Rank sectors by momentum and classify as Leader/Neutral/Laggard."""
    leader_count = config.tuning["sector_leader_count"]
    laggard_count = config.tuning["sector_laggard_count"]
    leader_bonus = config.tuning["sector_leader_bonus"]
    laggard_penalty = config.tuning["sector_laggard_penalty"]

    # Sort by momentum descending
    sorted_scores = sorted(scores, key=lambda s: s.momentum_5d, reverse=True)

    for rank, score in enumerate(sorted_scores, 1):
        score.rank = rank

        if rank <= leader_count:
            score.classification = MomentumClassification.LEADER
            score.score_adjustment = leader_bonus
        elif rank > len(sorted_scores) - laggard_count:
            score.classification = MomentumClassification.LAGGARD
            score.score_adjustment = laggard_penalty
        else:
            score.classification = MomentumClassification.NEUTRAL
            score.score_adjustment = 0


def _apply_sector_bmi(scores: list[SectorScore], config: Config) -> None:
    """Apply sector-specific BMI thresholds.

    Note: Full sector BMI calculation requires per-ticker volume data
    within each sector. For now, we use the sector ETF's momentum
    as a proxy for sector health. When sector BMI is set externally
    (e.g., from a pre-calculated data source), it overrides this.
    """
    thresholds = config.tuning["sector_bmi_thresholds"]

    for score in scores:
        if score.sector_bmi is not None:
            # Use pre-calculated sector BMI
            bounds = thresholds.get(score.etf, (12, 80))
            oversold_threshold, overbought_threshold = bounds

            if score.sector_bmi < oversold_threshold:
                score.sector_bmi_regime = SectorBMIRegime.OVERSOLD
            elif score.sector_bmi > overbought_threshold:
                score.sector_bmi_regime = SectorBMIRegime.OVERBOUGHT
            else:
                score.sector_bmi_regime = SectorBMIRegime.NEUTRAL


def _apply_veto_matrix(scores: list[SectorScore], config: Config,
                       logger: EventLogger) -> None:
    """Apply the LONG strategy veto matrix.

    Rules:
    - Leader + Any BMI regime → ALLOWED (+15)
    - Neutral + NEUTRAL/OVERSOLD → ALLOWED (0)
    - Neutral + OVERBOUGHT → VETO
    - Laggard + OVERSOLD → ALLOWED (Mean Reversion, -5)
    - Laggard + NEUTRAL → VETO
    - Laggard + OVERBOUGHT → VETO
    """
    mr_penalty = config.tuning["sector_laggard_mr_penalty"]

    for score in scores:
        cls = score.classification
        bmi = score.sector_bmi_regime

        if cls == MomentumClassification.LEADER:
            # Leaders always pass
            score.vetoed = False

        elif cls == MomentumClassification.NEUTRAL:
            if bmi == SectorBMIRegime.OVERBOUGHT:
                score.vetoed = True
                score.veto_reason = "Neutral + Overbought"
            else:
                score.vetoed = False

        elif cls == MomentumClassification.LAGGARD:
            if bmi == SectorBMIRegime.OVERSOLD:
                # Mean Reversion opportunity
                score.vetoed = False
                score.score_adjustment = mr_penalty
                score.veto_reason = None
            else:
                score.vetoed = True
                score.veto_reason = f"Laggard + {bmi.value}"

        if score.vetoed:
            logger.log(
                EventType.SECTOR_VETO, Severity.INFO, phase=3,
                message=f"Sector VETO: {score.etf} ({score.sector_name}) — {score.veto_reason}",
                data={
                    "etf": score.etf,
                    "classification": cls.value,
                    "sector_bmi_regime": bmi.value,
                    "reason": score.veto_reason,
                },
            )


def _apply_rate_sensitivity(scores: list[SectorScore], config: Config,
                            logger: EventLogger) -> None:
    """Apply TNX rate sensitivity penalty to sensitive sectors.

    When TNX > SMA20 * 1.05, Technology and Real Estate get additional penalty.
    """
    sensitive_sectors = config.tuning["tnx_sensitive_sectors"]

    for score in scores:
        if score.sector_name in sensitive_sectors and not score.vetoed:
            score.score_adjustment -= 10  # Rate sensitivity penalty
            logger.log(
                EventType.SECTOR_VETO, Severity.INFO, phase=3,
                message=f"Rate sensitivity: {score.etf} ({score.sector_name}) -10 penalty",
                data={
                    "etf": score.etf,
                    "sector_name": score.sector_name,
                    "penalty": -10,
                    "reason": "TNX rate sensitivity",
                },
            )


# ---------------------------------------------------------------------------
# BC14: Sector Breadth Analysis
# ---------------------------------------------------------------------------

def _compute_sma(prices: list[float], period: int) -> float | None:
    """Simple moving average of last `period` values. None if insufficient."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def _build_ticker_close_history(grouped_daily_bars: list[dict],
                                tickers: set[str]) -> dict[str, list[float]]:
    """Extract per-ticker closing price time series from grouped daily bars.

    Returns {ticker: [chronological_closes]} for tickers with ≥20 data points.
    """
    # grouped_daily_bars is a list of dicts, each representing one day's data
    # Each day dict has ticker keys with bar data (o, h, l, c, v, etc.)
    # Also has metadata keys like _buy_count, _sell_count, _ticker_count
    histories: dict[str, list[float | None]] = {t: [] for t in tickers}

    for day in grouped_daily_bars:
        day_tickers = set()
        # Extract closes from the day's bars (Phase 1 uses "bars" key)
        bars = day.get("bars", day.get("results", []))
        day_map: dict[str, float] = {}
        for bar in bars:
            t = bar.get("T", "")
            if t in tickers:
                day_map[t] = bar.get("c", 0.0)
                day_tickers.add(t)

        for t in tickers:
            if t in day_map:
                histories[t].append(day_map[t])
            else:
                histories[t].append(None)

    # Filter: only keep tickers with ≥20 non-None values
    result: dict[str, list[float]] = {}
    for t, vals in histories.items():
        clean = [v for v in vals if v is not None]
        if len(clean) >= 20:
            result[t] = clean

    return result


def _calculate_breadth(etf: str, holdings: list[str],
                       ticker_histories: dict[str, list[float]],
                       config: Config) -> SectorBreadth:
    """Calculate % above SMA20/50/200 for sector constituents."""
    periods = config.core.get("breadth_sma_periods", [20, 50, 200])
    weights = config.core.get("breadth_composite_weights", (0.20, 0.50, 0.30))

    pct_above = {}
    total_with_data = 0

    for period in periods:
        above = 0
        counted = 0
        for ticker in holdings:
            hist = ticker_histories.get(ticker)
            if hist is None or len(hist) < period:
                continue
            counted += 1
            sma = _compute_sma(hist, period)
            if sma is not None and hist[-1] > sma:
                above += 1
        pct = (above / counted * 100) if counted > 0 else 0.0
        pct_above[period] = pct
        if period == periods[0]:
            total_with_data = counted

    pct_20 = pct_above.get(periods[0], 0.0) if len(periods) > 0 else 0.0
    pct_50 = pct_above.get(periods[1], 0.0) if len(periods) > 1 else 0.0
    pct_200 = pct_above.get(periods[2], 0.0) if len(periods) > 2 else 0.0

    w0 = weights[0] if len(weights) > 0 else 0.0
    w1 = weights[1] if len(weights) > 1 else 0.0
    w2 = weights[2] if len(weights) > 2 else 0.0
    breadth_score = w0 * pct_20 + w1 * pct_50 + w2 * pct_200

    return SectorBreadth(
        etf=etf,
        constituent_count=total_with_data,
        pct_above_sma20=round(pct_20, 1),
        pct_above_sma50=round(pct_50, 1),
        pct_above_sma200=round(pct_200, 1),
        breadth_score=round(breadth_score, 1),
    )


def _compute_pct_above_sma_n_days_ago(holdings: list[str],
                                       ticker_histories: dict[str, list[float]],
                                       period: int,
                                       days_ago: int) -> float | None:
    """Recompute pct_above_sma for `days_ago` by slicing histories."""
    above = 0
    counted = 0
    for ticker in holdings:
        hist = ticker_histories.get(ticker)
        if hist is None or len(hist) < period + days_ago:
            continue
        sliced = hist[:-days_ago] if days_ago > 0 else hist
        counted += 1
        sma = _compute_sma(sliced, period)
        if sma is not None and sliced[-1] > sma:
            above += 1
    if counted == 0:
        return None
    return above / counted * 100


def _classify_breadth_regime(breadth: SectorBreadth,
                             pct_sma50_5d_ago: float | None) -> None:
    """Classify breadth regime using SMA50 and SMA200 dimensions."""
    b50 = breadth.pct_above_sma50
    b200 = breadth.pct_above_sma200

    if b50 > 70 and b200 > 70:
        regime = BreadthRegime.STRONG
    elif b50 > 70 and 30 <= b200 <= 70:
        regime = BreadthRegime.EMERGING
    elif 30 <= b50 <= 70 and b200 > 70:
        regime = BreadthRegime.CONSOLIDATING
    elif 30 <= b50 <= 70 and 30 <= b200 <= 70:
        regime = BreadthRegime.NEUTRAL
    elif b50 < 30 and 30 <= b200 <= 70:
        regime = BreadthRegime.WEAKENING
    elif b50 < 30 and b200 < 30:
        regime = BreadthRegime.WEAK
    elif b50 > 50 and b200 < 30:
        regime = BreadthRegime.RECOVERY
    else:
        regime = BreadthRegime.NEUTRAL  # Catch-all

    breadth.breadth_regime = regime

    # Breadth momentum: SMA50 pct now vs 5 days ago
    if pct_sma50_5d_ago is not None:
        breadth.breadth_momentum = round(b50 - pct_sma50_5d_ago, 1)


def _detect_breadth_divergence(etf_momentum_5d: float,
                                breadth_momentum: float,
                                config: Config) -> tuple[bool, str | None]:
    """Detect price-breadth divergence.

    Bearish: ETF up >2% AND breadth momentum SMA50 < -5 points
    Bullish: ETF down <-2% AND breadth momentum SMA50 > +5 points
    """
    etf_threshold = config.tuning.get("breadth_divergence_etf_threshold", 2.0)
    breadth_threshold = config.tuning.get("breadth_divergence_breadth_threshold", 5.0)

    if etf_momentum_5d > etf_threshold and breadth_momentum < -breadth_threshold:
        return True, "bearish"
    if etf_momentum_5d < -etf_threshold and breadth_momentum > breadth_threshold:
        return True, "bullish"
    return False, None


def _apply_breadth_score_adjustment(breadth: SectorBreadth,
                                     config: Config) -> None:
    """Set score_adjustment based on breadth_score and divergence."""
    strong_threshold = config.tuning.get("breadth_strong_threshold", 70)
    weak_threshold = config.tuning.get("breadth_weak_threshold", 50)
    very_weak_threshold = config.tuning.get("breadth_very_weak_threshold", 30)

    strong_bonus = config.tuning.get("breadth_strong_bonus", 10)
    weak_penalty = config.tuning.get("breadth_weak_penalty", -5)
    very_weak_penalty = config.tuning.get("breadth_very_weak_penalty", -15)
    divergence_penalty = config.tuning.get("breadth_divergence_penalty", -10)

    bs = breadth.breadth_score
    if bs > strong_threshold:
        adj = strong_bonus
    elif bs < very_weak_threshold:
        adj = very_weak_penalty
    elif bs < weak_threshold:
        adj = weak_penalty
    else:
        adj = 0

    if breadth.divergence_detected and breadth.divergence_type == "bearish":
        adj += divergence_penalty

    breadth.score_adjustment = adj


def _calculate_sector_breadth(scores: list[SectorScore],
                               grouped_daily_bars: list[dict],
                               fmp, config: Config,
                               logger: EventLogger) -> None:
    """Orchestrate breadth calculation for all sectors.

    1. Fetch ETF holdings (12 FMP calls, cached)
    2. Build ticker close histories from grouped bars
    3. Calculate breadth → classify → divergence → score adjustment
    """
    min_constituents = config.tuning.get("breadth_min_constituents", 10)

    # Collect all unique holding tickers across all ETFs
    etf_holdings: dict[str, list[str]] = {}
    all_tickers: set[str] = set()

    for score in scores:
        holdings_data = fmp.get_etf_holdings(score.etf)
        if not holdings_data:
            logger.log(
                EventType.PHASE_DIAGNOSTIC, Severity.WARNING, phase=3,
                message=f"[BREADTH] {score.etf}: no holdings data",
            )
            continue
        tickers = [h.get("asset", h.get("symbol", ""))
                   for h in holdings_data
                   if h.get("asset", h.get("symbol", ""))]
        if len(tickers) < min_constituents:
            logger.log(
                EventType.PHASE_DIAGNOSTIC, Severity.WARNING, phase=3,
                message=f"[BREADTH] {score.etf}: only {len(tickers)} holdings < {min_constituents}",
            )
            continue
        etf_holdings[score.etf] = tickers
        all_tickers.update(tickers)

    if not all_tickers:
        logger.log(
            EventType.PHASE_DIAGNOSTIC, Severity.WARNING, phase=3,
            message="[BREADTH] No valid holdings found for any sector",
        )
        return

    # Build ticker close histories from grouped bars (shared across all ETFs)
    ticker_histories = _build_ticker_close_history(grouped_daily_bars, all_tickers)

    logger.log(
        EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=3,
        message=f"[BREADTH] {len(all_tickers)} unique tickers, "
                f"{len(ticker_histories)} with sufficient history",
    )

    for score in scores:
        holdings = etf_holdings.get(score.etf)
        if not holdings:
            continue

        # Calculate breadth percentages
        breadth = _calculate_breadth(score.etf, holdings, ticker_histories, config)

        # SMA50 pct 5 days ago (for momentum and divergence)
        pct_sma50_5d_ago = _compute_pct_above_sma_n_days_ago(
            holdings, ticker_histories, period=50, days_ago=5,
        )

        # Classify regime
        _classify_breadth_regime(breadth, pct_sma50_5d_ago)

        # Detect divergence (using ETF's 5d momentum from sector data)
        if breadth.breadth_momentum != 0.0:
            detected, div_type = _detect_breadth_divergence(
                score.momentum_5d, breadth.breadth_momentum, config,
            )
            breadth.divergence_detected = detected
            breadth.divergence_type = div_type

        # Apply score adjustment
        _apply_breadth_score_adjustment(breadth, config)

        # Attach to sector score
        score.breadth = breadth
        score.breadth_score_adj = breadth.score_adjustment
        score.score_adjustment += breadth.score_adjustment

        logger.log(
            EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=3,
            message=(
                f"[BREADTH] {score.etf}: score={breadth.breadth_score:.0f} "
                f"regime={breadth.breadth_regime.value} "
                f"sma20={breadth.pct_above_sma20:.0f}% "
                f"sma50={breadth.pct_above_sma50:.0f}% "
                f"sma200={breadth.pct_above_sma200:.0f}% "
                f"adj={breadth.score_adjustment:+d}"
                f"{' DIVERGENCE=' + breadth.divergence_type if breadth.divergence_detected else ''}"
            ),
        )
