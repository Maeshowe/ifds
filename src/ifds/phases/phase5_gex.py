"""Phase 5: GEX (Gamma Exposure) Analysis.

Classifies each Phase 4 candidate into GEX regimes and applies filters:
- POSITIVE: Price > ZeroGamma AND NetGEX > 0 — low volatility, magnet effect
- NEGATIVE: Price < ZeroGamma — high volatility, unstable
- HIGH_VOL: Transition zone (within 2% of ZeroGamma)

NEGATIVE regime excludes tickers in LONG strategy.
GEX multiplier adjusts final position sizing (1.0 / 0.5 / 0.6).
"""

import asyncio
import time

from ifds.config.loader import Config
from ifds.data.adapters import GEXProvider
from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity
from ifds.models.market import (
    GEXAnalysis,
    GEXRegime,
    Phase5Result,
    StockAnalysis,
    StrategyMode,
)


def run_phase5(config: Config, logger: EventLogger,
               gex_provider: GEXProvider,
               stock_analyses: list[StockAnalysis],
               strategy_mode: StrategyMode) -> Phase5Result:
    """Execute Phase 5: GEX Regime Analysis.

    Args:
        config: Validated IFDS configuration.
        logger: Event logger for audit trail.
        gex_provider: GEX data provider (FallbackGEXProvider).
        stock_analyses: Passed candidates from Phase 4.
        strategy_mode: LONG or SHORT from Phase 1.

    Returns:
        Phase5Result with GEX-filtered candidates.
    """
    if config.runtime.get("async_enabled", False):
        return asyncio.run(_run_phase5_async(
            config, logger, stock_analyses, strategy_mode,
        ))

    start_time = time.monotonic()
    logger.phase_start(5, "GEX Analysis", input_count=len(stock_analyses))

    try:
        # Take top 100 candidates by combined_score
        sorted_candidates = sorted(
            stock_analyses, key=lambda s: s.combined_score, reverse=True
        )[:100]

        analyzed = []
        passed = []
        excluded_count = 0
        negative_count = 0

        for stock in sorted_candidates:
            ticker = stock.ticker
            gex_data = gex_provider.get_gex(ticker)

            if gex_data is None:
                # No GEX data — pass through with POSITIVE default
                logger.log(
                    EventType.API_ERROR, Severity.DEBUG, phase=5,
                    ticker=ticker,
                    message=f"{ticker} no GEX data from any provider — defaulting to POSITIVE regime",
                )
                gex_analysis = GEXAnalysis(
                    ticker=ticker,
                    current_price=stock.technical.price,
                    gex_regime=GEXRegime.POSITIVE,
                    gex_multiplier=config.tuning["gex_positive_multiplier"],
                    data_source="none",
                )
                analyzed.append(gex_analysis)
                passed.append(gex_analysis)
                continue

            net_gex = gex_data.get("net_gex", 0.0)
            call_wall = gex_data.get("call_wall", 0.0)
            put_wall = gex_data.get("put_wall", 0.0)
            zero_gamma = gex_data.get("zero_gamma", 0.0)
            current_price = stock.technical.price
            source = gex_data.get("source", "")

            # Call wall ATR filter: zero out call_wall if too far from price
            atr = stock.technical.atr_14
            max_atr_dist = config.tuning.get("call_wall_max_atr_distance", 5.0)
            if call_wall > 0 and atr > 0:
                if abs(call_wall - current_price) > atr * max_atr_dist:
                    call_wall = 0.0

            regime = _classify_gex_regime(current_price, zero_gamma, net_gex)
            multiplier = _get_gex_multiplier(regime, config)

            # Debug logging for first 5 tickers
            n_contracts = len(gex_data.get("gex_by_strike", []))
            if len(analyzed) < 5:
                logger.log(
                    EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=5,
                    message=(
                        f"[GEX_DEBUG] {ticker}: regime={regime.value}, "
                        f"net_gex={net_gex:.0f}, zero_gamma={zero_gamma:.2f}, "
                        f"price={current_price:.2f}, call_wall={call_wall:.2f}, "
                        f"put_wall={put_wall:.2f}, contracts={n_contracts}, "
                        f"source={source}"
                    ),
                )

            gex_analysis = GEXAnalysis(
                ticker=ticker,
                net_gex=net_gex,
                call_wall=call_wall,
                put_wall=put_wall,
                zero_gamma=zero_gamma,
                current_price=current_price,
                gex_regime=regime,
                gex_multiplier=multiplier,
                data_source=source,
            )

            # NEGATIVE regime → excluded in LONG strategy
            if regime == GEXRegime.NEGATIVE and strategy_mode == StrategyMode.LONG:
                gex_analysis.excluded = True
                gex_analysis.exclusion_reason = "negative_gex_long"
                excluded_count += 1
                negative_count += 1
                logger.log(
                    EventType.GEX_EXCLUSION, Severity.INFO, phase=5,
                    ticker=ticker,
                    message=(
                        f"{ticker} NEGATIVE GEX regime — excluded in LONG mode "
                        f"(price={current_price:.2f}, zero_gamma={zero_gamma:.2f})"
                    ),
                    data={
                        "ticker": ticker,
                        "regime": regime.value,
                        "price": current_price,
                        "zero_gamma": zero_gamma,
                        "net_gex": net_gex,
                    },
                )
            else:
                if regime == GEXRegime.NEGATIVE:
                    negative_count += 1
                passed.append(gex_analysis)

            analyzed.append(gex_analysis)

        result = Phase5Result(
            analyzed=analyzed,
            passed=passed,
            excluded_count=excluded_count,
            negative_regime_count=negative_count,
        )

        logger.log(
            EventType.PHASE_COMPLETE, Severity.INFO, phase=5,
            message=(
                f"GEX analyzed {len(analyzed)} → Passed {len(passed)} "
                f"(excluded={excluded_count}, negative={negative_count})"
            ),
            data={
                "analyzed": len(analyzed),
                "passed": len(passed),
                "excluded": excluded_count,
                "negative": negative_count,
            },
        )

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.phase_complete(5, "GEX Analysis",
                              output_count=len(passed), duration_ms=duration_ms)

        return result

    except Exception as e:
        logger.phase_error(5, "GEX Analysis", str(e))
        raise


def _classify_gex_regime(current_price: float, zero_gamma: float,
                         net_gex: float) -> GEXRegime:
    """Classify GEX regime based on price vs zero gamma level.

    Rules:
    - Price > ZeroGamma AND NetGEX > 0 → POSITIVE
    - Price < ZeroGamma → NEGATIVE
    - Transition zone (within 2% of ZeroGamma) → HIGH_VOL
    - ZeroGamma = 0 (no data) → POSITIVE (assume benign)
    """
    if zero_gamma <= 0:
        return GEXRegime.POSITIVE

    # Transition zone: within 2% of zero gamma
    distance_pct = abs(current_price - zero_gamma) / zero_gamma * 100
    if distance_pct <= 2.0:
        return GEXRegime.HIGH_VOL

    if current_price > zero_gamma and net_gex > 0:
        return GEXRegime.POSITIVE
    elif current_price < zero_gamma:
        return GEXRegime.NEGATIVE
    else:
        # Price > ZeroGamma but NetGEX <= 0 → transitioning
        return GEXRegime.HIGH_VOL


def _get_gex_multiplier(regime: GEXRegime, config: Config) -> float:
    """Map GEX regime to position sizing multiplier."""
    if regime == GEXRegime.POSITIVE:
        return config.tuning["gex_positive_multiplier"]
    elif regime == GEXRegime.NEGATIVE:
        return config.tuning["gex_negative_multiplier"]
    else:  # HIGH_VOL
        return config.tuning["gex_high_vol_multiplier"]


# ============================================================================
# Async Phase 5 — concurrent GEX analysis
# ============================================================================

async def _run_phase5_async(config: Config, logger: EventLogger,
                            stock_analyses: list[StockAnalysis],
                            strategy_mode: StrategyMode) -> Phase5Result:
    """Async Phase 5: process GEX for all candidates concurrently."""
    from ifds.data.async_clients import AsyncPolygonClient, AsyncUWClient
    from ifds.data.async_adapters import (
        AsyncFallbackGEXProvider, AsyncPolygonGEXProvider, AsyncUWGEXProvider,
    )

    start_time = time.monotonic()
    logger.phase_start(5, "GEX Analysis (async)", input_count=len(stock_analyses))

    sem_ticker = asyncio.Semaphore(config.runtime.get("async_max_tickers", 10))
    sem_polygon = asyncio.Semaphore(config.runtime.get("async_sem_polygon", 5))
    sem_uw = asyncio.Semaphore(config.runtime.get("async_sem_uw", 5))

    polygon = AsyncPolygonClient(
        api_key=config.get_api_key("polygon"),
        timeout=config.runtime.get("api_timeout_polygon_options", 15),
        max_retries=config.runtime["api_max_retries"],
        semaphore=sem_polygon,
    )

    uw_client = None
    uw_key = config.get_api_key("unusual_whales")
    max_dte = config.tuning.get("gex_max_dte", 35)

    if uw_key:
        uw_client = AsyncUWClient(
            api_key=uw_key,
            timeout=config.runtime["api_timeout_uw"],
            max_retries=config.runtime["api_max_retries"],
            semaphore=sem_uw,
        )
        gex_provider = AsyncFallbackGEXProvider(
            AsyncUWGEXProvider(uw_client),
            AsyncPolygonGEXProvider(polygon, max_dte=max_dte),
            logger=logger,
        )
    else:
        gex_provider = AsyncPolygonGEXProvider(polygon, max_dte=max_dte)

    sorted_candidates = sorted(
        stock_analyses, key=lambda s: s.combined_score, reverse=True
    )[:100]

    analyzed = []
    passed = []
    excluded_count = 0
    negative_count = 0

    async def process_gex(stock: StockAnalysis):
        async with sem_ticker:
            return await gex_provider.get_gex(stock.ticker)

    try:
        tasks = [process_gex(stock) for stock in sorted_candidates]
        gex_results = await asyncio.gather(*tasks, return_exceptions=True)

        for stock, gex_data in zip(sorted_candidates, gex_results):
            ticker = stock.ticker

            if isinstance(gex_data, BaseException):
                logger.log(EventType.API_ERROR, Severity.WARNING, phase=5,
                           ticker=ticker,
                           message=f"{ticker} GEX fetch failed: {gex_data}")
                gex_data = None

            if gex_data is None:
                logger.log(
                    EventType.API_ERROR, Severity.DEBUG, phase=5,
                    ticker=ticker,
                    message=f"{ticker} no GEX data from any provider — defaulting to POSITIVE regime",
                )
                gex_analysis = GEXAnalysis(
                    ticker=ticker,
                    current_price=stock.technical.price,
                    gex_regime=GEXRegime.POSITIVE,
                    gex_multiplier=config.tuning["gex_positive_multiplier"],
                    data_source="none",
                )
                analyzed.append(gex_analysis)
                passed.append(gex_analysis)
                continue

            net_gex = gex_data.get("net_gex", 0.0)
            call_wall = gex_data.get("call_wall", 0.0)
            put_wall = gex_data.get("put_wall", 0.0)
            zero_gamma = gex_data.get("zero_gamma", 0.0)
            current_price = stock.technical.price
            source = gex_data.get("source", "")

            # Call wall ATR filter: zero out call_wall if too far from price
            atr = stock.technical.atr_14
            max_atr_dist = config.tuning.get("call_wall_max_atr_distance", 5.0)
            if call_wall > 0 and atr > 0:
                if abs(call_wall - current_price) > atr * max_atr_dist:
                    call_wall = 0.0

            regime = _classify_gex_regime(current_price, zero_gamma, net_gex)
            multiplier = _get_gex_multiplier(regime, config)

            # Debug logging for first 5 tickers
            n_contracts = len(gex_data.get("gex_by_strike", []))
            if len(analyzed) < 5:
                logger.log(
                    EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=5,
                    message=(
                        f"[GEX_DEBUG] {ticker}: regime={regime.value}, "
                        f"net_gex={net_gex:.0f}, zero_gamma={zero_gamma:.2f}, "
                        f"price={current_price:.2f}, call_wall={call_wall:.2f}, "
                        f"put_wall={put_wall:.2f}, contracts={n_contracts}, "
                        f"source={source}"
                    ),
                )

            gex_analysis = GEXAnalysis(
                ticker=ticker,
                net_gex=net_gex,
                call_wall=call_wall,
                put_wall=put_wall,
                zero_gamma=zero_gamma,
                current_price=current_price,
                gex_regime=regime,
                gex_multiplier=multiplier,
                data_source=source,
            )

            if regime == GEXRegime.NEGATIVE and strategy_mode == StrategyMode.LONG:
                gex_analysis.excluded = True
                gex_analysis.exclusion_reason = "negative_gex_long"
                excluded_count += 1
                negative_count += 1
                logger.log(
                    EventType.GEX_EXCLUSION, Severity.INFO, phase=5,
                    ticker=ticker,
                    message=(
                        f"{ticker} NEGATIVE GEX regime — excluded in LONG mode "
                        f"(price={current_price:.2f}, zero_gamma={zero_gamma:.2f})"
                    ),
                    data={
                        "ticker": ticker,
                        "regime": regime.value,
                        "price": current_price,
                        "zero_gamma": zero_gamma,
                        "net_gex": net_gex,
                    },
                )
            else:
                if regime == GEXRegime.NEGATIVE:
                    negative_count += 1
                passed.append(gex_analysis)

            analyzed.append(gex_analysis)

        result = Phase5Result(
            analyzed=analyzed,
            passed=passed,
            excluded_count=excluded_count,
            negative_regime_count=negative_count,
        )

        logger.log(
            EventType.PHASE_COMPLETE, Severity.INFO, phase=5,
            message=(
                f"GEX analyzed {len(analyzed)} → Passed {len(passed)} "
                f"(excluded={excluded_count}, negative={negative_count})"
            ),
            data={
                "analyzed": len(analyzed),
                "passed": len(passed),
                "excluded": excluded_count,
                "negative": negative_count,
            },
        )

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.phase_complete(5, "GEX Analysis (async)",
                              output_count=len(passed), duration_ms=duration_ms)

        return result

    except Exception as e:
        logger.phase_error(5, "GEX Analysis (async)", str(e))
        raise
    finally:
        await polygon.close()
        if uw_client:
            await uw_client.close()
