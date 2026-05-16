"""Phase 4: Individual Stock Analysis.

Analyzes each ticker from the Phase 2 universe across three dimensions:
1. Technical Analysis — SMA200 trend filter, RSI ideal zone, SMA50, RS vs SPY
2. Flow Analysis — RVOL, Spread, Squat Bar, Dark Pool, PCR, OTM%, Block Trades
3. Fundamental Scoring — Growth, Efficiency, Safety, Insider, Shark Detector

Combined Score = 0.40 * FlowScore + 0.30 * FundaScore + 0.30 * TechScore + SectorAdj
Applied: insider multiplier, min score filter (70), clipping (configurable threshold).
"""

import asyncio
import time
from datetime import date, timedelta

from ifds.config.loader import Config
from ifds.data.adapters import DarkPoolProvider
from ifds.data.fmp import FMPClient
from ifds.data.polygon import PolygonClient
from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity
from ifds.models.market import (
    DarkPoolSignal,
    FlowAnalysis,
    FundamentalScoring,
    Phase4Result,
    SectorScore,
    StockAnalysis,
    StrategyMode,
    TechnicalAnalysis,
    Ticker,
)

# Base score for each sub-dimension (adjustments push up/down from here)
_BASE_SCORE = 50


def _is_danger_zone(fundamental: FundamentalScoring, config: Config) -> bool:
    """Check if ticker has Bottom 10 risk profile.

    Based on MoneyFlows Outlier analysis (T3):
    - Extreme debt (D/E > 5.0)
    - Negative net margin (< -10%)
    - Critical interest coverage (< 1.0)
    Need 2+ signals to trigger (avoid false positives from single metric).
    """
    if not config.tuning.get("danger_zone_enabled", True):
        return False

    danger_signals = 0

    if fundamental.debt_equity is not None:
        if fundamental.debt_equity > config.tuning.get("danger_zone_debt_equity", 5.0):
            danger_signals += 1

    if fundamental.net_margin is not None:
        if fundamental.net_margin < config.tuning.get("danger_zone_net_margin", -0.10):
            danger_signals += 1

    if fundamental.interest_coverage is not None:
        if fundamental.interest_coverage < config.tuning.get("danger_zone_interest_coverage", 1.0):
            danger_signals += 1

    return danger_signals >= config.tuning.get("danger_zone_min_signals", 2)


def run_phase4(config: Config, logger: EventLogger,
               polygon: PolygonClient, fmp: FMPClient,
               dp_provider: DarkPoolProvider | None,
               tickers: list[Ticker],
               sector_scores: list[SectorScore],
               strategy_mode: StrategyMode) -> Phase4Result:
    """Execute Phase 4: Individual Stock Analysis.

    Args:
        config: Validated IFDS configuration.
        logger: Event logger for audit trail.
        polygon: Polygon client for OHLCV data.
        fmp: FMP client for fundamentals and insider data.
        dp_provider: Dark Pool provider (UW primary, None if unavailable).
        tickers: Universe from Phase 2.
        sector_scores: Sector rotation results from Phase 3.
        strategy_mode: LONG or SHORT from Phase 1.

    Returns:
        Phase4Result with analyzed stocks and filter results.
    """
    if config.runtime.get("async_enabled", False):
        return asyncio.run(_run_phase4_async(
            config, logger, tickers, sector_scores, strategy_mode,
        ))

    start_time = time.monotonic()
    logger.phase_start(4, "Individual Stock Analysis", input_count=len(tickers))

    try:
        # Build sector name → score_adjustment map (exclude breadth adj — BC14)
        sector_adj_map = {s.sector_name: s.score_adjustment - s.breadth_score_adj
                          for s in sector_scores if not s.vetoed}

        analyzed = []
        passed = []
        tech_filter_count = 0
        min_score_count = 0
        clipped_count = 0
        danger_zone_count = 0

        min_score = config.tuning["combined_score_minimum"]
        clipping_threshold = config.core["clipping_threshold"]

        # Fetch SPY 3-month return (once, reused for all tickers)
        spy_3m_return = None
        spy_from = (date.today() - timedelta(days=365)).isoformat()
        spy_to = date.today().isoformat()
        spy_bars = polygon.get_aggregates("SPY", spy_from, spy_to)
        if spy_bars and len(spy_bars) >= 63:
            spy_closes = [b["c"] for b in spy_bars]
            spy_3m_return = (spy_closes[-1] - spy_closes[-63]) / spy_closes[-63]

        # Probe institutional ownership endpoint availability
        inst_ownership_available = True
        _probe = fmp.get_institutional_ownership("AAPL")
        if _probe is None:
            inst_ownership_available = False
            logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO, phase=4,
                       message="[INFO] Institutional ownership endpoint unavailable (404), "
                               "feature disabled for this run")

        for ticker_obj in tickers:
            symbol = ticker_obj.symbol

            # 1. Fetch OHLCV data (250 calendar days ≈ 200+ trading days)
            from_date = (date.today() - timedelta(days=365)).isoformat()
            to_date = date.today().isoformat()
            bars = polygon.get_aggregates(symbol, from_date, to_date)

            if not bars or len(bars) < 50:
                continue  # Insufficient data

            # 2. Technical Analysis
            technical = _analyze_technical(bars, strategy_mode, config,
                                           spy_3m_return=spy_3m_return)

            # Tech filter: SMA200 trend
            if not technical.trend_pass:
                tech_filter_count += 1
                logger.log(EventType.TICKER_FILTERED, Severity.DEBUG, phase=4,
                           message=f"{symbol} failed SMA200 trend filter",
                           data={"ticker": symbol, "reason": "tech_filter"})
                analysis = StockAnalysis(
                    ticker=symbol, sector=ticker_obj.sector,
                    technical=technical,
                    flow=FlowAnalysis(),
                    fundamental=FundamentalScoring(),
                    excluded=True, exclusion_reason="tech_filter",
                )
                analyzed.append(analysis)
                continue

            # 3. Flow Analysis (with options data for PCR/OTM scoring).
            # Pass 1 (universe scoring) skips dp_provider to stay under the UW
            # rate limit; dark-pool enrichment runs in Pass 2 below for `passed`.
            options_data = polygon.get_options_snapshot(symbol)
            flow = _analyze_flow(symbol, bars, None, config,
                                 options_data=options_data)

            # 4. Fundamental Scoring
            fundamental = _analyze_fundamental(symbol, fmp, config,
                                               skip_inst=not inst_ownership_available)

            # 4b. Danger Zone check (T3 — Bottom 10 filter)
            if _is_danger_zone(fundamental, config):
                danger_zone_count += 1
                logger.log(EventType.TICKER_FILTERED, Severity.INFO, phase=4,
                           message=f"{symbol} filtered: danger zone "
                                   f"(D/E={fundamental.debt_equity}, "
                                   f"margin={fundamental.net_margin}, "
                                   f"IC={fundamental.interest_coverage})",
                           data={"ticker": symbol, "reason": "danger_zone"})
                analysis = StockAnalysis(
                    ticker=symbol, sector=ticker_obj.sector,
                    technical=technical, flow=flow, fundamental=fundamental,
                    excluded=True, exclusion_reason="danger_zone",
                )
                analyzed.append(analysis)
                continue

            # 5. Combined Score
            sector_adj = sector_adj_map.get(ticker_obj.sector, 0)
            combined = _calculate_combined_score(
                technical, flow, fundamental, sector_adj, config
            )

            # 5b. Analyst target + contradiction signal (sync path mirrors async)
            target_data = fmp.get_price_target_consensus(symbol)
            analyst_target = None
            target_high = None
            if target_data and isinstance(target_data, dict):
                if target_data.get("targetConsensus"):
                    try:
                        analyst_target = float(target_data["targetConsensus"])
                    except (ValueError, TypeError):
                        analyst_target = None
                if target_data.get("targetHigh"):
                    try:
                        target_high = float(target_data["targetHigh"])
                    except (ValueError, TypeError):
                        target_high = None
            earnings_history = fmp.get_earnings_history(symbol)
            recent_grades = fmp.get_recent_grades(symbol)

            from ifds.scoring.contradiction_signal import compute_contradiction_signal
            contradiction = compute_contradiction_signal(
                price=technical.price,
                target_consensus=analyst_target,
                target_high=target_high,
                earnings_history=earnings_history if isinstance(earnings_history, list) else None,
                analyst_grades_recent=recent_grades if isinstance(recent_grades, list) else None,
            )

            analysis = StockAnalysis(
                ticker=symbol, sector=ticker_obj.sector,
                technical=technical, flow=flow, fundamental=fundamental,
                combined_score=combined, sector_adjustment=sector_adj,
                shark_detected=fundamental.shark_detected,
                analyst_target=analyst_target,
                contradiction_flag=contradiction.is_contradicted,
                contradiction_reasons=contradiction.reasons,
                contradiction_detail=dict(contradiction.detail),
            )

            # 6. Filters
            if combined > clipping_threshold:
                analysis.excluded = True
                analysis.exclusion_reason = "clipping"
                clipped_count += 1
                logger.log(
                    EventType.CLIPPING_SKIP, Severity.INFO, phase=4,
                    ticker=symbol,
                    message=f"{symbol} score {combined:.1f} — crowded trade (skipping)",
                    data={"ticker": symbol, "score": combined},
                )
            elif combined < min_score:
                analysis.excluded = True
                analysis.exclusion_reason = "min_score"
                min_score_count += 1
            else:
                passed.append(analysis)
                logger.log(
                    EventType.TICKER_SCORED, Severity.INFO, phase=4,
                    ticker=symbol,
                    message=(
                        f"{symbol} → {combined:.1f} "
                        f"(tech={technical.rsi_score}, flow={flow.rvol_score}, "
                        f"funda={fundamental.funda_score}, sector={sector_adj})"
                    ),
                    data={
                        "ticker": symbol,
                        "combined_score": combined,
                        "tech_score": technical.rsi_score,
                        "flow_score": flow.rvol_score,
                        "funda_score": fundamental.funda_score,
                        "sector_adj": sector_adj,
                    },
                )

            analyzed.append(analysis)

        # Debug: tech score breakdown for first 5 ACCEPTED tickers
        for dbg in passed[:5]:
            t = dbg.technical
            tech_total = t.rsi_score + t.sma50_bonus + t.rs_spy_score
            logger.log(
                EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=4,
                ticker=dbg.ticker,
                message=(
                    f"{dbg.ticker} tech: SMA50={t.price}>{t.sma_50:.0f} "
                    f"(+{t.sma50_bonus}), RSI={t.rsi_14:.1f} (+{t.rsi_score}), "
                    f"RS_spy={'+' if t.rs_spy_score > 0 else ''}{t.rs_spy_score} "
                    f"= {tech_total}"
                ),
                data={"ticker": dbg.ticker, "sma50_bonus": t.sma50_bonus,
                      "rsi_score": t.rsi_score, "rs_spy_score": t.rs_spy_score,
                      "tech_total": tech_total, "price": t.price, "sma_50": t.sma_50},
            )

        excluded_count = tech_filter_count + min_score_count + clipped_count + danger_zone_count

        # Pass 2: per-ticker dark-pool enrichment for `passed` only (sync path).
        # Same rationale as the async path: keep the main universe loop off UW.
        if dp_provider is not None and passed:
            _enrich_passed_with_dp_sync(passed, dp_provider, config, logger,
                                        sector_adj_map)
            still_passing = []
            for stock in passed:
                if stock.combined_score > clipping_threshold:
                    stock.excluded = True
                    stock.exclusion_reason = "clipping"
                    clipped_count += 1
                elif stock.combined_score < min_score:
                    stock.excluded = True
                    stock.exclusion_reason = "min_score"
                    min_score_count += 1
                else:
                    still_passing.append(stock)
            dropped = len(passed) - len(still_passing)
            if dropped:
                logger.log(
                    EventType.PHASE_DIAGNOSTIC, Severity.INFO, phase=4,
                    message=(
                        f"Dark-pool re-scoring dropped {dropped} ticker(s) "
                        f"from passed ({len(passed)} → {len(still_passing)})"
                    ),
                    data={"dropped": dropped, "before": len(passed),
                          "after": len(still_passing)},
                )
            passed = still_passing
            excluded_count = tech_filter_count + min_score_count + clipped_count + danger_zone_count

        result = Phase4Result(
            analyzed=analyzed,
            passed=passed,
            excluded_count=excluded_count,
            clipped_count=clipped_count,
            tech_filter_count=tech_filter_count,
            min_score_count=min_score_count,
            danger_zone_count=danger_zone_count,
            clipping_threshold=config.core.get("clipping_threshold", 95),
        )

        logger.log(
            EventType.PHASE_COMPLETE, Severity.INFO, phase=4,
            message=(
                f"Analyzed {len(analyzed)} → Passed {len(passed)} "
                f"(tech_filter={tech_filter_count}, min_score={min_score_count}, "
                f"clipped={clipped_count}, danger_zone={danger_zone_count})"
            ),
            data={
                "analyzed": len(analyzed),
                "passed": len(passed),
                "tech_filter": tech_filter_count,
                "min_score": min_score_count,
                "clipped": clipped_count,
            },
        )

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.phase_complete(4, "Individual Stock Analysis",
                              output_count=len(passed), duration_ms=duration_ms)

        return result

    except Exception as e:
        logger.phase_error(4, "Individual Stock Analysis", str(e))
        raise


# ============================================================================
# Technical Indicators
# ============================================================================

def _calculate_sma(values: list[float], period: int) -> float:
    """Calculate Simple Moving Average over the last `period` values."""
    if not values:
        return 0.0
    if len(values) < period:
        return sum(values) / len(values)
    return sum(values[-period:]) / period


def _calculate_rsi(bars: list[dict], period: int = 14) -> float:
    """Calculate RSI (Relative Strength Index).

    RSI = 100 - 100/(1 + RS)
    RS = SMA(gains, period) / SMA(losses, period)
    """
    if len(bars) < period + 1:
        return 50.0  # Neutral if insufficient data

    closes = [b["c"] for b in bars]
    gains = []
    losses = []

    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    if len(gains) < period:
        return 50.0

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _calculate_atr(bars: list[dict], period: int = 14) -> float:
    """Calculate Average True Range.

    TR = max(H-L, |H-C_prev|, |L-C_prev|)
    ATR = SMA(TR, period)
    """
    if len(bars) < 2:
        return 0.0

    true_ranges = []
    for i in range(1, len(bars)):
        high = bars[i]["h"]
        low = bars[i]["l"]
        close_prev = bars[i - 1]["c"]

        tr = max(
            high - low,
            abs(high - close_prev),
            abs(low - close_prev),
        )
        true_ranges.append(tr)

    if not true_ranges:
        return 0.0
    if len(true_ranges) < period:
        return sum(true_ranges) / len(true_ranges)
    return sum(true_ranges[-period:]) / period


def _check_trend_filter(price: float, sma_200: float,
                        strategy_mode: StrategyMode) -> bool:
    """Check if ticker passes SMA200 trend filter."""
    if sma_200 <= 0:
        return True  # No SMA → pass by default
    if strategy_mode == StrategyMode.LONG:
        return price > sma_200
    else:
        return price < sma_200


def _score_rsi(rsi: float, config: Config) -> int:
    """Score RSI using ideal zone gradient.

    [45-65] → +30 (inner), [35-45)/(65-75] → +15 (outer), else → 0.
    """
    inner_low = config.tuning["rsi_ideal_inner_low"]
    inner_high = config.tuning["rsi_ideal_inner_high"]
    outer_low = config.tuning["rsi_ideal_outer_low"]
    outer_high = config.tuning["rsi_ideal_outer_high"]

    if inner_low <= rsi <= inner_high:
        return config.tuning["rsi_ideal_inner_bonus"]
    elif outer_low <= rsi < inner_low or inner_high < rsi <= outer_high:
        return config.tuning["rsi_ideal_outer_bonus"]
    return 0


def _analyze_technical(bars: list[dict], strategy_mode: StrategyMode,
                       config: Config,
                       spy_3m_return: float | None = None) -> TechnicalAnalysis:
    """Analyze all technical indicators for a ticker."""
    closes = [b["c"] for b in bars]
    current_price = closes[-1]

    sma_200 = _calculate_sma(closes, config.core["sma_long_period"])
    sma_20 = _calculate_sma(closes, config.core["sma_short_period"])
    sma_50 = _calculate_sma(closes, config.core["sma_mid_period"])
    rsi_14 = _calculate_rsi(bars, config.core["rsi_period"])
    atr_14 = _calculate_atr(bars, config.core["atr_period"])

    trend_pass = _check_trend_filter(current_price, sma_200, strategy_mode)
    rsi_score = _score_rsi(rsi_14, config)

    # SMA50 bonus
    sma50_bonus = config.tuning["sma50_bonus"] if current_price > sma_50 > 0 else 0

    # Relative Strength vs SPY (3-month)
    rs_vs_spy = None
    rs_spy_score = 0
    if spy_3m_return is not None and len(closes) >= 63:
        ticker_3m_return = (closes[-1] - closes[-63]) / closes[-63]
        rs_vs_spy = round(ticker_3m_return - spy_3m_return, 4)
        if ticker_3m_return > spy_3m_return:
            rs_spy_score = config.tuning["rs_spy_bonus"]

    return TechnicalAnalysis(
        price=current_price,
        sma_200=round(sma_200, 2),
        sma_20=round(sma_20, 2),
        rsi_14=rsi_14,
        atr_14=round(atr_14, 4),
        trend_pass=trend_pass,
        rsi_score=rsi_score,
        sma_50=round(sma_50, 2),
        sma50_bonus=sma50_bonus,
        rs_vs_spy=rs_vs_spy,
        rs_spy_score=rs_spy_score,
    )


# ============================================================================
# Flow Analysis
# ============================================================================

def _score_rvol(rvol: float, config: Config) -> int:
    """Score RVOL (Relative Volume) based on thresholds."""
    if rvol < config.tuning["rvol_low"]:
        return config.tuning["rvol_low_penalty"]
    elif rvol < config.tuning["rvol_normal"]:
        return 0
    elif rvol < config.tuning["rvol_elevated"]:
        return config.tuning["rvol_elevated_bonus"]
    else:
        return config.tuning["rvol_significant_bonus"]


def _analyze_flow(ticker: str, bars: list[dict],
                  dp_provider: DarkPoolProvider | None,
                  config: Config,
                  options_data: list[dict] | None = None) -> FlowAnalysis:
    """Analyze flow metrics: RVOL, spread, squat bar, dark pool, options."""
    dp_data = None
    if dp_provider:
        dp_data = dp_provider.get_dark_pool(ticker)
    return _analyze_flow_from_data(ticker, bars, dp_data, config,
                                   options_data=options_data)


def _analyze_flow_from_data(ticker: str, bars: list[dict],
                            dp_data: dict | None,
                            config: Config,
                            options_data: list[dict] | None = None) -> FlowAnalysis:
    """Analyze flow metrics from pre-fetched data (no API calls)."""
    # RVOL
    volumes = [b["v"] for b in bars]
    volume_today = volumes[-1]
    volume_sma_20 = _calculate_sma(volumes, config.core["sma_short_period"])
    rvol = volume_today / volume_sma_20 if volume_sma_20 > 0 else 1.0

    # Spread analysis
    spreads = [b["h"] - b["l"] for b in bars]
    spread_today = spreads[-1]
    spread_sma_10 = _calculate_sma(spreads, 10)
    spread_ratio = spread_today / spread_sma_10 if spread_sma_10 > 0 else 1.0

    # RVOL scoring
    rvol_score = _score_rvol(rvol, config)

    # Squat bar detection
    squat = (rvol > config.tuning["squat_bar_rvol_min"]
             and spread_ratio < config.tuning["squat_bar_spread_ratio_max"])
    squat_bonus = config.tuning["squat_bar_bonus"] if squat else 0

    # Dark pool — recalculate dp_pct using Polygon daily volume
    dp_pct = 0.0
    dp_signal = None
    dp_pct_score = 0

    if dp_data:
        dp_volume = dp_data.get("dp_volume", 0)
        daily_volume = bars[-1]["v"] if bars else 0
        if daily_volume > 0 and dp_volume > 0:
            dp_pct = round((dp_volume / daily_volume) * 100, 2)

        threshold = config.tuning["dark_pool_volume_threshold_pct"]
        if dp_pct > threshold:
            raw_signal = dp_data.get("signal", "")
            if raw_signal == "BULLISH":
                dp_signal = DarkPoolSignal.BULLISH
            elif raw_signal == "BEARISH":
                dp_signal = DarkPoolSignal.BEARISH
            else:
                dp_signal = DarkPoolSignal.NEUTRAL

        # dp_pct scoring — inclusive boundaries (sign-flipped 2026-05-08).
        # Buckets: dp_pct < threshold → 0; threshold ≤ dp_pct < dp_high → bonus
        # (now negative); dp_pct ≥ dp_high → high_bonus (now negative).
        # 2026-05-26 (Day 63 §3.2): gated by uw_dark_pool_scoring_enabled.
        # When disabled the raw dp_pct is still captured by the UW shadow log.
        if config.tuning.get("uw_dark_pool_scoring_enabled", True):
            dp_high = config.tuning["dp_pct_high_threshold"]
            if dp_pct >= dp_high:
                dp_pct_score = config.tuning["dp_pct_high_bonus"]
            elif dp_pct >= threshold:
                dp_pct_score = config.tuning["dp_pct_bonus"]

    # Buy Pressure + VWAP
    last_bar = bars[-1]
    close = last_bar["c"]
    high = last_bar["h"]
    low = last_bar["l"]
    vwap = last_bar.get("vw")

    # Fallback: typical price if vw missing
    if vwap is None or vwap <= 0:
        vwap = (high + low + close) / 3

    buy_pressure_score = 0

    # Buy Pressure: where did price close within the bar?
    bar_range = high - low
    if bar_range > 0:
        buy_pos = (close - low) / bar_range
        if buy_pos > 0.7:
            buy_pressure_score += config.tuning["buy_pressure_strong_bonus"]
        elif buy_pos < 0.3:
            buy_pressure_score += config.tuning["buy_pressure_weak_penalty"]

    # VWAP accumulation signal
    if vwap > 0:
        if close > vwap:
            buy_pressure_score += config.tuning["vwap_accumulation_bonus"]
            # Strong accumulation: > 1% above VWAP
            if (close - vwap) / vwap > 0.01:
                buy_pressure_score += 5
        elif close < vwap:
            buy_pressure_score += config.tuning["vwap_distribution_penalty"]

    # Options flow scoring (PCR, OTM call ratio)
    pcr = None
    pcr_score = 0
    otm_call_ratio = None
    otm_score = 0
    if options_data:
        # Front-month DTE filter with <5 contract fallback
        max_dte = config.tuning.get("gex_max_dte", 90)
        from datetime import date as _date
        today = _date.today()
        filtered_opts = []
        if max_dte > 0:
            for opt in options_data:
                exp_str = opt.get("details", {}).get("expiration_date")
                if exp_str:
                    try:
                        exp_date = _date.fromisoformat(exp_str)
                        if (exp_date - today).days > max_dte:
                            continue
                    except ValueError:
                        pass
                filtered_opts.append(opt)
            if len(filtered_opts) < 5:
                filtered_opts = list(options_data)  # Fallback: use all
        else:
            filtered_opts = list(options_data)

        current_price = bars[-1]["c"]
        call_vol = put_vol = otm_call_vol = 0
        for opt in filtered_opts:
            details = opt.get("details", {})
            day_data = opt.get("day", {})
            ctype = details.get("contract_type", "").lower()
            strike = details.get("strike_price", 0)
            vol = day_data.get("volume", 0) or 0
            if ctype == "call":
                call_vol += vol
                if strike > current_price:
                    otm_call_vol += vol
            elif ctype == "put":
                put_vol += vol
        if call_vol > 0:
            pcr = round(put_vol / call_vol, 3)
            if pcr < config.tuning["pcr_bullish_threshold"]:
                pcr_score = config.tuning["pcr_bullish_bonus"]
            elif pcr > config.tuning["pcr_bearish_threshold"]:
                pcr_score = config.tuning["pcr_bearish_penalty"]
            otm_call_ratio = round(otm_call_vol / call_vol, 3)
            if otm_call_ratio > config.tuning["otm_call_ratio_threshold"]:
                otm_score = config.tuning["otm_call_bonus"]

    # Block trade scoring from DP data
    block_trade_count = dp_data.get("block_trade_count", 0) if dp_data else 0
    block_trade_score = 0
    if block_trade_count > config.tuning["block_trade_very_high"]:
        block_trade_score = config.tuning["block_trade_very_high_bonus"]
    elif block_trade_count > config.tuning["block_trade_significant"]:
        block_trade_score = config.tuning["block_trade_significant_bonus"]

    return FlowAnalysis(
        volume_today=volume_today,
        volume_sma_20=round(volume_sma_20, 2),
        rvol=round(rvol, 3),
        rvol_score=rvol_score + squat_bonus + pcr_score + otm_score + block_trade_score + dp_pct_score + buy_pressure_score,
        spread_today=round(spread_today, 4),
        spread_sma_10=round(spread_sma_10, 4),
        spread_ratio=round(spread_ratio, 3),
        squat_bar=squat,
        squat_bar_bonus=squat_bonus,
        dark_pool_pct=round(dp_pct, 2),
        dark_pool_signal=dp_signal,
        dp_pct_score=dp_pct_score,
        pcr=pcr,
        pcr_score=pcr_score,
        otm_call_ratio=otm_call_ratio,
        otm_score=otm_score,
        block_trade_count=block_trade_count,
        block_trade_score=block_trade_score,
        vwap=round(vwap, 4),
        buy_pressure_score=buy_pressure_score,
        venue_entropy=dp_data.get("venue_entropy", 0.0) if dp_data else 0.0,
        # Dollar-weighted fields (from adapter QW commit 533763b)
        dp_volume_shares=int(dp_data.get("dp_volume", 0)) if dp_data else 0,
        total_volume=int(dp_data.get("total_volume", 0)) if dp_data else 0,
        dp_volume_dollars=float(dp_data.get("dp_volume_dollars", 0.0)) if dp_data else 0.0,
        block_trade_dollars=float(dp_data.get("block_trade_dollars", 0.0)) if dp_data else 0.0,
    )


# ============================================================================
# Fundamental Scoring
# ============================================================================

def _calculate_insider_score(insider_data: list[dict] | None,
                             config: Config) -> int:
    """Calculate insider trading net score (buys - sells in last 30d)."""
    if not insider_data:
        return 0

    lookback = config.tuning["insider_lookback_days"]
    cutoff = (date.today() - timedelta(days=lookback)).isoformat()

    score = 0
    for trade in insider_data:
        trade_date = trade.get("transactionDate", "")
        if not trade_date or trade_date < cutoff:
            continue
        txn_type = trade.get("acquistionOrDisposition", "")
        if txn_type == "A":  # Acquisition (buy)
            score += 1
        elif txn_type == "D":  # Disposition (sell)
            score -= 1

    return score


def _insider_multiplier(insider_score: int, config: Config) -> float:
    """Get position sizing multiplier from insider activity."""
    if insider_score > config.tuning["insider_strong_buy_threshold"]:
        return config.tuning["insider_buy_multiplier"]
    elif insider_score < config.tuning["insider_strong_sell_threshold"]:
        return config.tuning["insider_sell_multiplier"]
    return 1.0


def _detect_shark(insider_data: list[dict] | None, config: Config) -> bool:
    """Detect insider cluster buying (2+ unique insiders, $100K+, within 10 days)."""
    if not insider_data:
        return False
    lookback = config.tuning["shark_lookback_days"]
    cutoff = (date.today() - timedelta(days=lookback)).isoformat()
    unique_buyers: set[str] = set()
    total_value = 0.0
    for trade in insider_data:
        td = trade.get("transactionDate", "")
        if not td or td < cutoff or trade.get("acquistionOrDisposition") != "A":
            continue
        insider_id = trade.get("reportingCik") or trade.get("reportingName", "")
        if insider_id:
            unique_buyers.add(insider_id)
        shares = trade.get("securitiesTransacted", 0) or 0
        price = trade.get("price", 0) or 0
        total_value += shares * price
    return (len(unique_buyers) >= config.tuning["shark_min_unique_insiders"]
            and total_value >= config.tuning["shark_min_total_value"])


def _analyze_fundamental(ticker: str, fmp: FMPClient,
                         config: Config,
                         skip_inst: bool = False) -> FundamentalScoring:
    """Analyze fundamental metrics and insider activity."""
    growth = fmp.get_financial_growth(ticker)
    metrics = fmp.get_key_metrics(ticker)
    insider_data = fmp.get_insider_trading(ticker)
    inst_data = None if skip_inst else fmp.get_institutional_ownership(ticker)
    return _analyze_fundamental_from_data(ticker, growth, metrics, insider_data, config,
                                          inst_data=inst_data)


def _analyze_fundamental_from_data(ticker: str, growth: dict | None,
                                   metrics: dict | None,
                                   insider_data: list[dict] | None,
                                   config: Config,
                                   inst_data: list[dict] | None = None) -> FundamentalScoring:
    """Score fundamentals from pre-fetched data (no API calls)."""
    rev_growth = growth.get("revenueGrowth") if growth else None
    eps_growth = growth.get("epsgrowth") if growth else None

    net_margin = None
    roe = None
    debt_equity = None
    interest_coverage = None
    if metrics:
        roe = metrics.get("roeTTM")
        debt_equity = metrics.get("debtToEquityTTM")
        interest_coverage = metrics.get("interestCoverageTTM")
        if "netIncomePerShareTTM" in metrics and metrics.get("revenuePerShareTTM"):
            rev_per = metrics["revenuePerShareTTM"]
            ni_per = metrics["netIncomePerShareTTM"]
            net_margin = (ni_per / rev_per) if rev_per > 0 else None
        else:
            net_margin = None

    score = 0
    bonus = config.tuning["funda_score_bonus"]
    penalty = config.tuning["funda_score_penalty"]
    debt_penalty = config.tuning["funda_debt_penalty"]

    if rev_growth is not None:
        threshold_good = config.tuning["funda_revenue_growth_good"] / 100
        threshold_bad = config.tuning["funda_revenue_growth_bad"] / 100
        if rev_growth > threshold_good:
            score += bonus
        elif rev_growth < threshold_bad:
            score += penalty

    if eps_growth is not None:
        threshold_good = config.tuning["funda_eps_growth_good"] / 100
        threshold_bad = config.tuning["funda_eps_growth_bad"] / 100
        if eps_growth > threshold_good:
            score += bonus
        elif eps_growth < threshold_bad:
            score += penalty

    if net_margin is not None:
        threshold_good = config.tuning["funda_net_margin_good"] / 100
        threshold_bad = config.tuning["funda_net_margin_bad"]
        if net_margin > threshold_good:
            score += bonus
        elif net_margin < threshold_bad:
            score += penalty

    if roe is not None:
        threshold_good = config.tuning["funda_roe_good"] / 100
        threshold_bad = config.tuning["funda_roe_bad"] / 100
        if roe > threshold_good:
            score += bonus
        elif roe < threshold_bad:
            score += penalty

    if debt_equity is not None:
        if debt_equity < config.tuning["funda_debt_equity_good"]:
            score += bonus
        elif debt_equity > config.tuning["funda_debt_equity_bad"]:
            score += debt_penalty

    if interest_coverage is not None:
        if interest_coverage < config.tuning["funda_interest_coverage_bad"]:
            score += debt_penalty

    insider_score = _calculate_insider_score(insider_data, config)
    insider_mult = _insider_multiplier(insider_score, config)

    # Shark detector: cluster buying bonus
    shark_detected = _detect_shark(insider_data, config)
    if shark_detected:
        score += config.tuning["shark_score_bonus"]

    # Institutional ownership trend (QoQ comparison)
    inst_trend = "unknown"
    inst_score = 0
    if inst_data and len(inst_data) >= 2:
        recent = inst_data[0].get("totalInvested", 0) or 0
        previous = inst_data[1].get("totalInvested", 0) or 0
        if previous > 0:
            change_pct = (recent - previous) / previous
            if change_pct > 0.02:
                inst_trend = "increasing"
                inst_score = 10
            elif change_pct < -0.02:
                inst_trend = "decreasing"
                inst_score = -5
            else:
                inst_trend = "stable"
        score += inst_score

    return FundamentalScoring(
        revenue_growth_yoy=rev_growth,
        eps_growth_yoy=eps_growth,
        net_margin=net_margin,
        roe=roe,
        debt_equity=debt_equity,
        interest_coverage=interest_coverage,
        insider_score=insider_score,
        insider_multiplier=insider_mult,
        funda_score=score,
        shark_detected=shark_detected,
        inst_ownership_trend=inst_trend,
        inst_ownership_score=inst_score,
    )


# ============================================================================
# Combined Score
# ============================================================================

def _calculate_combined_score(technical: TechnicalAnalysis,
                              flow: FlowAnalysis,
                              fundamental: FundamentalScoring,
                              sector_adj: int,
                              config: Config) -> float:
    """Calculate weighted combined score.

    Formula: 0.40 * FlowScore + 0.30 * FundaScore + 0.30 * TechScore + SectorAdj
    Flow/Funda: base 50 + adjustments.
    Tech: rsi_score + sma50_bonus + rs_spy_score (0-100, no base).
    Insider multiplier applied at the end.
    """
    tech_score = technical.rsi_score + technical.sma50_bonus + technical.rs_spy_score
    flow_score = min(100, max(0, _BASE_SCORE + flow.rvol_score))  # cap [0, 100]
    funda_score = _BASE_SCORE + fundamental.funda_score  # funda_score includes shark

    w_flow = config.core["weight_flow"]
    w_funda = config.core["weight_fundamental"]
    w_tech = config.core["weight_technical"]

    combined = (
        w_flow * flow_score
        + w_funda * funda_score
        + w_tech * tech_score
        + sector_adj
    )

    # Apply insider multiplier
    combined *= fundamental.insider_multiplier

    return round(combined, 2)


# ============================================================================
# Dark-pool Pass-2 enrichment (per-ticker UW fetch, only for passed tickers)
# ============================================================================


def _recompute_dp_pct_score(dp_pct: float, config: Config) -> int:
    """Apply the same inclusive-boundary scoring used in _analyze_flow_from_data.

    2026-05-26 (Day 63 §3.2): gated by ``uw_dark_pool_scoring_enabled``. When
    disabled the function returns 0 regardless of dp_pct — the raw dp_pct is
    still captured by the UW shadow log.
    """
    if not config.tuning.get("uw_dark_pool_scoring_enabled", True):
        return 0
    base_threshold = config.tuning["dark_pool_volume_threshold_pct"]
    high_threshold = config.tuning["dp_pct_high_threshold"]
    if dp_pct >= high_threshold:
        return config.tuning["dp_pct_high_bonus"]
    if dp_pct >= base_threshold:
        return config.tuning["dp_pct_bonus"]
    return 0


def _apply_dp_enrichment(stock: StockAnalysis, dp_data: dict | None,
                         config: Config, sector_adj: int) -> None:
    """Mutate stock.flow with new dp_pct + dp_pct_score and re-score combined.

    Uses the dp_data["total_volume"] field as the denominator (UW reports the
    stock's full-day volume on every record; the aggregator takes the max).
    This is a close approximation of the Polygon daily volume used in Pass 1.
    """
    if not dp_data:
        return

    dp_volume = int(dp_data.get("dp_volume", 0) or 0)
    total_volume = int(dp_data.get("total_volume", 0) or 0)
    if total_volume <= 0 or dp_volume <= 0:
        return

    new_dp_pct = round((dp_volume / total_volume) * 100, 2)
    new_dp_score = _recompute_dp_pct_score(new_dp_pct, config)

    # Adjust the flow aggregate: rvol_score currently has the OLD dp_pct_score
    # (which was 0, since Pass 1 ran with dp_data=None). Subtract old, add new.
    old_dp_score = stock.flow.dp_pct_score
    stock.flow.dark_pool_pct = new_dp_pct
    stock.flow.dp_pct_score = new_dp_score
    stock.flow.dp_volume_shares = dp_volume
    stock.flow.total_volume = total_volume
    stock.flow.rvol_score = stock.flow.rvol_score - old_dp_score + new_dp_score

    # Re-compute combined_score with the updated flow score
    stock.combined_score = _calculate_combined_score(
        stock.technical, stock.flow, stock.fundamental, sector_adj, config,
    )


def _enrich_passed_with_dp_sync(
    passed: list[StockAnalysis],
    dp_provider,
    config: Config,
    logger: EventLogger,
    sector_adj_map: dict[str, int],
) -> None:
    """Sync counterpart to ``_enrich_passed_with_dp_async`` — serial fetch
    with inter-call delay (default 200 ms, see async docstring for rationale).
    """
    import time as _time
    delay_s = config.runtime.get("dp_enrichment_delay_s", 0.2)
    enriched = 0
    for stock in passed:
        try:
            dp_data = dp_provider.get_dark_pool(stock.ticker)
        except Exception as e:
            logger.log(EventType.API_ERROR, Severity.WARNING, phase=4,
                       ticker=stock.ticker,
                       message=f"{stock.ticker} dp enrichment failed: {e}")
            dp_data = None
        if dp_data is not None:
            sector_adj = sector_adj_map.get(stock.sector, 0)
            _apply_dp_enrichment(stock, dp_data, config, sector_adj)
            if stock.flow.dark_pool_pct > 0:
                enriched += 1
        if delay_s > 0:
            _time.sleep(delay_s)
    logger.log(
        EventType.PHASE_DIAGNOSTIC, Severity.INFO, phase=4,
        message=f"Dark-pool Pass 2: enriched {enriched}/{len(passed)} passed tickers",
        data={"enriched": enriched, "passed": len(passed)},
    )


async def _enrich_passed_with_dp_async(
    passed: list[StockAnalysis],
    dp_provider,
    config: Config,
    logger: EventLogger,
    sector_adj_map: dict[str, int],
) -> None:
    """Pass 2: per-ticker UW dark-pool fetch + re-score for tickers that passed.

    Sequential with inter-call delay (default 200 ms) — the UW Basic tier
    rate-limits well below the 5-parallel × 300 ms ≈ 17 req/s burst that
    asyncio.gather produced (W20 D3 measurement: ~28% of enrichment calls
    hit HTTP 429). 166 tickers × 200 ms = ~33 s extra; fits well inside the
    15-minute Phase 4-6 cron window and frees UW rate budget for Phase 5 GEX.
    """
    delay_s = config.runtime.get("dp_enrichment_delay_s", 0.2)
    for stock in passed:
        try:
            dp_data = await dp_provider.get_dark_pool(stock.ticker)
        except Exception as e:
            logger.log(EventType.API_ERROR, Severity.WARNING, phase=4,
                       ticker=stock.ticker,
                       message=f"{stock.ticker} dp enrichment failed: {e}")
            dp_data = None
        if dp_data is not None:
            sector_adj = sector_adj_map.get(stock.sector, 0)
            _apply_dp_enrichment(stock, dp_data, config, sector_adj)
        if delay_s > 0:
            await asyncio.sleep(delay_s)

    enriched = sum(1 for s in passed if s.flow.dark_pool_pct > 0)
    logger.log(
        EventType.PHASE_DIAGNOSTIC, Severity.INFO, phase=4,
        message=f"Dark-pool Pass 2: enriched {enriched}/{len(passed)} passed tickers",
        data={"enriched": enriched, "passed": len(passed)},
    )


# ============================================================================
# Async Phase 4 — concurrent ticker processing
# ============================================================================

async def _run_phase4_async(config: Config, logger: EventLogger,
                            tickers: list[Ticker],
                            sector_scores: list[SectorScore],
                            strategy_mode: StrategyMode) -> Phase4Result:
    """Async Phase 4: process tickers concurrently with semaphore rate limiting."""
    from ifds.data.async_clients import AsyncPolygonClient, AsyncFMPClient, AsyncUWClient
    from ifds.data.async_adapters import AsyncUWDarkPoolProvider

    start_time = time.monotonic()
    logger.phase_start(4, "Individual Stock Analysis (async)", input_count=len(tickers))

    sem_ticker = asyncio.Semaphore(config.runtime.get("async_max_tickers", 10))
    sem_polygon = asyncio.Semaphore(config.runtime.get("async_sem_polygon", 5))
    sem_fmp = asyncio.Semaphore(config.runtime.get("async_sem_fmp", 8))
    sem_uw = asyncio.Semaphore(config.runtime.get("async_sem_uw", 5))

    polygon = AsyncPolygonClient(
        api_key=config.get_api_key("polygon"),
        timeout=config.runtime["api_timeout_polygon"],
        max_retries=config.runtime["api_max_retries"],
        semaphore=sem_polygon,
    )
    fmp = AsyncFMPClient(
        api_key=config.get_api_key("fmp"),
        timeout=config.runtime["api_timeout_fmp"],
        max_retries=config.runtime["api_max_retries"],
        semaphore=sem_fmp,
    )

    # Dark Pool: per-ticker fetch (async). See sync runner.py for rationale.
    dp_provider = None
    uw_client = None
    uw_key = config.get_api_key("unusual_whales")
    if uw_key:
        uw_client = AsyncUWClient(
            api_key=uw_key,
            timeout=config.runtime["api_timeout_uw"],
            max_retries=config.runtime["api_max_retries"],
            semaphore=sem_uw,
        )
        dp_provider = AsyncUWDarkPoolProvider(uw_client)

    # Exclude breadth adj from ticker-level score (BC14)
    sector_adj_map = {s.sector_name: s.score_adjustment - s.breadth_score_adj
                      for s in sector_scores if not s.vetoed}
    min_score = config.tuning["combined_score_minimum"]
    clipping_threshold = config.core["clipping_threshold"]

    # Fetch SPY 3-month return (once, reused for all tickers)
    spy_3m_return = None
    spy_from = (date.today() - timedelta(days=365)).isoformat()
    spy_to = date.today().isoformat()
    spy_bars = await polygon.get_aggregates("SPY", spy_from, spy_to)
    if spy_bars and len(spy_bars) >= 63:
        spy_closes = [b["c"] for b in spy_bars]
        spy_3m_return = (spy_closes[-1] - spy_closes[-63]) / spy_closes[-63]

    analyzed = []
    passed = []
    tech_filter_count = 0
    min_score_count = 0
    clipped_count = 0
    danger_zone_count = 0

    # Probe institutional ownership endpoint availability
    inst_ownership_available = True
    _probe = await fmp.get_institutional_ownership("AAPL")
    if _probe is None:
        inst_ownership_available = False
        logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO, phase=4,
                   message="[INFO] Institutional ownership endpoint unavailable (404), "
                           "feature disabled for this run")

    async def _noop():
        return None

    async def process_ticker(ticker_obj: Ticker):
        symbol = ticker_obj.symbol

        # Stage 1: Polygon OHLCV
        from_date = (date.today() - timedelta(days=365)).isoformat()
        to_date = date.today().isoformat()

        async with sem_ticker:
            bars = await polygon.get_aggregates(symbol, from_date, to_date)

            if not bars or len(bars) < 50:
                return None  # Insufficient data

            # Stage 2: Technical analysis (pure computation)
            technical = _analyze_technical(bars, strategy_mode, config,
                                           spy_3m_return=spy_3m_return)

            if not technical.trend_pass:
                return StockAnalysis(
                    ticker=symbol, sector=ticker_obj.sector,
                    technical=technical,
                    flow=FlowAnalysis(),
                    fundamental=FundamentalScoring(),
                    excluded=True, exclusion_reason="tech_filter",
                )

            # Stage 3: Parallel FMP + Options + Inst + Target + Contradiction
            # signal inputs (8 calls at once).
            #
            # NOTE (2026-05-12): dark-pool fetch removed from the main loop.
            # With ~1425 tickers × per-ticker UW = HTTP 429 rate-limit storm.
            # Two-pass scoring: dp_pct treated as 0 here, then enriched only
            # for the `passed` set (~100-200 tickers) before returning.
            results = await asyncio.gather(
                fmp.get_financial_growth(symbol),
                fmp.get_key_metrics(symbol),
                fmp.get_insider_trading(symbol),
                _noop(),  # was dp_provider.get_dark_pool — moved to Pass 2
                polygon.get_options_snapshot(symbol),
                fmp.get_institutional_ownership(symbol) if inst_ownership_available else _noop(),
                fmp.get_price_target_consensus(symbol),
                fmp.get_earnings_history(symbol),
                fmp.get_recent_grades(symbol),
                return_exceptions=True,
            )

            # Unpack — treat exceptions as None, log failures
            _labels = (
                "fmp_growth", "fmp_metrics", "fmp_insider", "dark_pool",
                "options", "inst_ownership", "price_target",
                "earnings_history", "recent_grades",
            )
            for idx, label in enumerate(_labels):
                if isinstance(results[idx], BaseException):
                    logger.log(EventType.API_ERROR, Severity.WARNING, phase=4,
                               ticker=symbol,
                               message=f"{symbol} {label} fetch failed: {results[idx]}")
            growth = results[0] if not isinstance(results[0], BaseException) else None
            metrics = results[1] if not isinstance(results[1], BaseException) else None
            insider_data = results[2] if not isinstance(results[2], BaseException) else None
            dp_data = results[3] if not isinstance(results[3], BaseException) else None
            options_data = results[4] if not isinstance(results[4], BaseException) else None
            inst_data = results[5] if not isinstance(results[5], BaseException) else None
            target_data = results[6] if not isinstance(results[6], BaseException) else None
            earnings_history = results[7] if not isinstance(results[7], BaseException) else None
            recent_grades = results[8] if not isinstance(results[8], BaseException) else None
            analyst_target: float | None = None
            target_high: float | None = None
            if target_data and isinstance(target_data, dict):
                if target_data.get("targetConsensus"):
                    try:
                        analyst_target = float(target_data["targetConsensus"])
                    except (ValueError, TypeError):
                        analyst_target = None
                if target_data.get("targetHigh"):
                    try:
                        target_high = float(target_data["targetHigh"])
                    except (ValueError, TypeError):
                        target_high = None

            # Stage 4: Score with pre-fetched data (pure computation)
            flow = _analyze_flow_from_data(symbol, bars, dp_data, config,
                                           options_data=options_data)
            fundamental = _analyze_fundamental_from_data(
                symbol, growth, metrics, insider_data, config,
                inst_data=inst_data,
            )

            # Stage 4b: Danger Zone check (T3 — Bottom 10 filter)
            if _is_danger_zone(fundamental, config):
                return StockAnalysis(
                    ticker=symbol, sector=ticker_obj.sector,
                    technical=technical, flow=flow, fundamental=fundamental,
                    excluded=True, exclusion_reason="danger_zone",
                )

            sector_adj = sector_adj_map.get(ticker_obj.sector, 0)
            combined = _calculate_combined_score(
                technical, flow, fundamental, sector_adj, config,
            )

            # Contradiction signal (BC23 W18+, 2026-05-02): pure-function eval
            # of structured FMP fundamentals. Defensive — missing inputs ⇒ no flag.
            from ifds.scoring.contradiction_signal import compute_contradiction_signal
            contradiction = compute_contradiction_signal(
                price=technical.price,
                target_consensus=analyst_target,
                target_high=target_high,
                earnings_history=earnings_history if isinstance(earnings_history, list) else None,
                analyst_grades_recent=recent_grades if isinstance(recent_grades, list) else None,
            )

            return StockAnalysis(
                ticker=symbol, sector=ticker_obj.sector,
                technical=technical, flow=flow, fundamental=fundamental,
                combined_score=combined, sector_adjustment=sector_adj,
                shark_detected=fundamental.shark_detected,
                analyst_target=analyst_target,
                contradiction_flag=contradiction.is_contradicted,
                contradiction_reasons=contradiction.reasons,
                contradiction_detail=dict(contradiction.detail),
            )

    try:
        tasks = [process_ticker(t) for t in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                continue
            if result is None:
                continue

            analyzed.append(result)

            if result.excluded and result.exclusion_reason == "tech_filter":
                tech_filter_count += 1
                logger.log(EventType.TICKER_FILTERED, Severity.DEBUG, phase=4,
                           message=f"{result.ticker} failed SMA200 trend filter",
                           data={"ticker": result.ticker, "reason": "tech_filter"})
            elif result.excluded and result.exclusion_reason == "danger_zone":
                danger_zone_count += 1
                logger.log(EventType.TICKER_FILTERED, Severity.INFO, phase=4,
                           message=f"{result.ticker} filtered: danger zone "
                                   f"(D/E={result.fundamental.debt_equity}, "
                                   f"margin={result.fundamental.net_margin}, "
                                   f"IC={result.fundamental.interest_coverage})",
                           data={"ticker": result.ticker, "reason": "danger_zone"})
            elif result.combined_score > clipping_threshold:
                result.excluded = True
                result.exclusion_reason = "clipping"
                clipped_count += 1
                logger.log(
                    EventType.CLIPPING_SKIP, Severity.INFO, phase=4,
                    ticker=result.ticker,
                    message=f"{result.ticker} score {result.combined_score:.1f} — crowded trade (skipping)",
                    data={"ticker": result.ticker, "score": result.combined_score},
                )
            elif result.combined_score < min_score:
                result.excluded = True
                result.exclusion_reason = "min_score"
                min_score_count += 1
            else:
                passed.append(result)
                logger.log(
                    EventType.TICKER_SCORED, Severity.INFO, phase=4,
                    ticker=result.ticker,
                    message=(
                        f"{result.ticker} → {result.combined_score:.1f} "
                        f"(tech={result.technical.rsi_score}, flow={result.flow.rvol_score}, "
                        f"funda={result.fundamental.funda_score}, sector={result.sector_adjustment})"
                    ),
                    data={
                        "ticker": result.ticker,
                        "combined_score": result.combined_score,
                    },
                )

        # Debug: tech score breakdown for first 5 ACCEPTED tickers
        for dbg in passed[:5]:
            t = dbg.technical
            tech_total = t.rsi_score + t.sma50_bonus + t.rs_spy_score
            logger.log(
                EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=4,
                ticker=dbg.ticker,
                message=(
                    f"{dbg.ticker} tech: SMA50={t.price}>{t.sma_50:.0f} "
                    f"(+{t.sma50_bonus}), RSI={t.rsi_14:.1f} (+{t.rsi_score}), "
                    f"RS_spy={'+' if t.rs_spy_score > 0 else ''}{t.rs_spy_score} "
                    f"= {tech_total}"
                ),
                data={"ticker": dbg.ticker, "sma50_bonus": t.sma50_bonus,
                      "rsi_score": t.rsi_score, "rs_spy_score": t.rs_spy_score,
                      "tech_total": tech_total, "price": t.price, "sma_50": t.sma_50},
            )

        excluded_count = tech_filter_count + min_score_count + clipped_count + danger_zone_count

        # Pass 2: dark-pool enrichment for `passed` tickers only (2026-05-12).
        # The main loop above ran without UW dp_provider to stay under the
        # rate limit on the 1425-ticker universe. Now per-ticker fetch and
        # re-score only the (~100-200) tickers that already passed scoring.
        if dp_provider is not None and passed:
            sector_adj_map_pass2 = sector_adj_map
            await _enrich_passed_with_dp_async(
                passed, dp_provider, config, logger, sector_adj_map_pass2,
            )

            # Re-filter after re-scoring: dp penalty may drop tickers below
            # min_score or push them past clipping; rebuild passed/analyzed
            # bookkeeping.
            still_passing = []
            for stock in passed:
                if stock.combined_score > clipping_threshold:
                    stock.excluded = True
                    stock.exclusion_reason = "clipping"
                    clipped_count += 1
                elif stock.combined_score < min_score:
                    stock.excluded = True
                    stock.exclusion_reason = "min_score"
                    min_score_count += 1
                else:
                    still_passing.append(stock)
            dropped = len(passed) - len(still_passing)
            if dropped:
                logger.log(
                    EventType.PHASE_DIAGNOSTIC, Severity.INFO, phase=4,
                    message=(
                        f"Dark-pool re-scoring dropped {dropped} ticker(s) "
                        f"from passed ({len(passed)} → {len(still_passing)})"
                    ),
                    data={"dropped": dropped, "before": len(passed),
                          "after": len(still_passing)},
                )
            passed = still_passing
            excluded_count = tech_filter_count + min_score_count + clipped_count + danger_zone_count

        phase4_result = Phase4Result(
            analyzed=analyzed,
            passed=passed,
            excluded_count=excluded_count,
            clipped_count=clipped_count,
            tech_filter_count=tech_filter_count,
            min_score_count=min_score_count,
            danger_zone_count=danger_zone_count,
            clipping_threshold=config.core.get("clipping_threshold", 95),
        )

        logger.log(
            EventType.PHASE_COMPLETE, Severity.INFO, phase=4,
            message=(
                f"Analyzed {len(analyzed)} → Passed {len(passed)} "
                f"(tech_filter={tech_filter_count}, min_score={min_score_count}, "
                f"clipped={clipped_count}, danger_zone={danger_zone_count})"
            ),
            data={
                "analyzed": len(analyzed),
                "passed": len(passed),
                "tech_filter": tech_filter_count,
                "min_score": min_score_count,
                "clipped": clipped_count,
            },
        )

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.phase_complete(4, "Individual Stock Analysis (async)",
                              output_count=len(passed), duration_ms=duration_ms)

        return phase4_result

    except Exception as e:
        logger.phase_error(4, "Individual Stock Analysis (async)", str(e))
        raise
    finally:
        await polygon.close()
        await fmp.close()
        if uw_client:
            await uw_client.close()
