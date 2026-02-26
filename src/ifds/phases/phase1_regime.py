"""Phase 1: Market Regime — Big Money Index (BMI).

Determines whether the market favors LONG or SHORT strategy.

BMI calculation:
1. For each ticker on each day, detect Big Money Buy/Sell signals
   (volume > mean + k*sigma AND direction from close vs open).
2. Daily ratio: B / (B + S) * 100
3. BMI = SMA25 of daily ratios
4. Regime: GREEN (<=25) → aggressive LONG, YELLOW → normal LONG, RED (>=80) → SHORT

Divergence detection:
- Bearish: SPY rises >1% over 5d but BMI drops >2 points → weakness signal
"""

import asyncio
import time
from datetime import date, timedelta

from ifds.config.loader import Config
from ifds.data.polygon import PolygonClient
from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity
from ifds.models.market import (
    BMIData,
    BMIRegime,
    Phase1Result,
    StrategyMode,
)

# FMP sector name → SPDR ETF ticker
# Only mismatch: FMP uses "Financial Services", Phase 3 uses "Financials" (XLF)
FMP_SECTOR_TO_ETF = {
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Energy": "XLE",
    "Healthcare": "XLV",
    "Industrials": "XLI",
    "Consumer Defensive": "XLP",
    "Consumer Cyclical": "XLY",
    "Basic Materials": "XLB",
    "Communication Services": "XLC",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
}


def run_phase1(config: Config, logger: EventLogger,
               polygon: PolygonClient,
               sector_mapping: dict[str, str] | None = None) -> Phase1Result:
    """Execute Phase 1: Market Regime determination via BMI.

    Args:
        config: Validated IFDS configuration.
        logger: Event logger for audit trail.
        polygon: Polygon client for grouped daily bars.

    Returns:
        Phase1Result with BMI data and strategy mode.
    """
    # Async dispatch (BC16): concurrent grouped daily fetching
    if config.runtime.get("async_enabled", False):
        return asyncio.run(_run_phase1_async(
            config, logger, sector_mapping=sector_mapping,
        ))

    start_time = time.monotonic()
    logger.phase_start(1, "Market Regime (BMI)")

    try:
        # Fetch grouped daily bars
        # Market BMI: 25 SMA works with ~39 days (early neutral days count)
        # Sector BMI: needs 20 volume warmup + 25 SMA = 45 actual trading days
        # Breadth (BC14): SMA200 needs ~330 calendar days (~220 trading days)
        breadth_enabled = config.tuning.get("breadth_enabled", False)
        if breadth_enabled:
            lookback = config.core.get("breadth_lookback_calendar_days", 330)
        else:
            lookback = 75
        daily_bars = _fetch_daily_history(polygon, lookback_calendar_days=lookback)

        if not daily_bars or len(daily_bars) < 25:
            logger.phase_error(1, "Market Regime (BMI)",
                               f"Insufficient data: got {len(daily_bars) if daily_bars else 0} days, need 25+")
            # Conservative fallback: YELLOW regime, LONG mode
            bmi = BMIData(
                bmi_value=50.0,
                bmi_regime=BMIRegime.YELLOW,
                daily_ratio=50.0,
            )
            result = Phase1Result(bmi=bmi, strategy_mode=StrategyMode.LONG)
            _log_result(logger, result, start_time, fallback=True)
            return result

        # Calculate daily ratios from grouped bars
        daily_ratios = _calculate_daily_ratios(daily_bars, config,
                                               sector_mapping=sector_mapping,
                                               logger=logger)

        # BMI = SMA25 of daily ratios
        sma_period = config.core["bmi_sma_period"]
        if len(daily_ratios) >= sma_period:
            bmi_value = sum(daily_ratios[-sma_period:]) / sma_period
        else:
            bmi_value = sum(daily_ratios) / len(daily_ratios)

        # Most recent daily ratio
        latest_ratio = daily_ratios[-1] if daily_ratios else 50.0
        latest_bars = daily_bars[-1] if daily_bars else {}
        buy_count = latest_bars.get("_buy_count", 0)
        sell_count = latest_bars.get("_sell_count", 0)

        # Classify regime
        bmi_regime = _classify_bmi(bmi_value, config)

        # Divergence detection
        divergence = _detect_divergence(daily_bars, daily_ratios, config)

        bmi = BMIData(
            bmi_value=round(bmi_value, 2),
            bmi_regime=bmi_regime,
            daily_ratio=round(latest_ratio, 2),
            buy_count=buy_count,
            sell_count=sell_count,
            divergence_detected=divergence is not None,
            divergence_type=divergence,
        )

        # Strategy mode: RED → SHORT, else → LONG
        strategy_mode = StrategyMode.SHORT if bmi_regime == BMIRegime.RED else StrategyMode.LONG

        # Per-sector BMI (if sector mapping available)
        sector_bmi_values: dict[str, float] = {}
        if sector_mapping:
            logger.log(
                EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=1,
                message=f"Sector mapping: {len(sector_mapping)} tickers mapped",
            )
            sector_bmi_values = _calculate_sector_bmi(daily_bars, config, logger=logger)

        ticker_count = daily_bars[-1].get("_ticker_count", 0) if daily_bars else 0
        result = Phase1Result(
            bmi=bmi,
            strategy_mode=strategy_mode,
            ticker_count_for_bmi=ticker_count,
            sector_bmi_values=sector_bmi_values,
            grouped_daily_bars=daily_bars if breadth_enabled else [],  # BC14
        )

        _log_result(logger, result, start_time)
        return result

    except Exception as e:
        logger.phase_error(1, "Market Regime (BMI)", str(e))
        raise


def _fetch_daily_history(polygon: PolygonClient,
                         lookback_calendar_days: int = 55) -> list[dict]:
    """Fetch grouped daily bars for the lookback period.

    Returns list of dicts, one per trading day, each containing the raw
    ticker bars under key 'bars' and metadata.
    """
    today = date.today()
    days = []

    for offset in range(lookback_calendar_days, 0, -1):
        target = today - timedelta(days=offset)
        # Skip weekends
        if target.weekday() >= 5:
            continue
        days.append(target.isoformat())

    daily_data = []
    for day_str in days:
        bars = polygon.get_grouped_daily(day_str)
        if bars:
            daily_data.append({
                "date": day_str,
                "bars": bars,
            })

    return daily_data


async def _fetch_daily_history_async(polygon, lookback_calendar_days: int = 55,
                                     logger=None) -> list[dict]:
    """Fetch grouped daily bars concurrently with asyncio.gather.

    Same logic as _fetch_daily_history() but fires all requests in parallel,
    rate-limited by the AsyncPolygonClient's semaphore.
    """
    today = date.today()
    days = []

    for offset in range(lookback_calendar_days, 0, -1):
        target = today - timedelta(days=offset)
        if target.weekday() >= 5:
            continue
        days.append(target.isoformat())

    # Fire all requests concurrently — semaphore handles rate limiting
    results = await asyncio.gather(
        *[polygon.get_grouped_daily(day_str) for day_str in days],
        return_exceptions=True
    )

    daily_data = []
    for day_str, result in zip(days, results):
        if isinstance(result, BaseException):
            if logger:
                from ifds.events.types import EventType, Severity
                logger.log(EventType.API_ERROR, Severity.WARNING,
                           phase=1, message=f"Polygon request failed for {day_str}: {result}")
            continue
        if result:
            daily_data.append({"date": day_str, "bars": result})

    return daily_data


def _calculate_daily_ratios(daily_data: list[dict],
                            config: Config,
                            sector_mapping: dict[str, str] | None = None,
                            logger: EventLogger | None = None) -> list[float]:
    """Calculate daily Big Money buy/sell ratios.

    For each day, scan all tickers. A ticker has a Big Money signal if:
    - Volume > mean_20d + k * sigma_20d (volume spike)
    - Buy if close > open, Sell if close < open

    Daily ratio = B / (B + S) * 100

    Since we have grouped daily data (all tickers per day), we need
    rolling volume stats per ticker. We build these incrementally.
    """
    k = config.core["bmi_volume_spike_sigma"]
    vol_period = config.core["bmi_volume_avg_period"]

    # Build per-ticker volume history: ticker -> list of volumes
    ticker_volumes: dict[str, list[float]] = {}

    daily_ratios = []

    for i, day in enumerate(daily_data):
        bars = day["bars"]
        buy_signals = 0
        sell_signals = 0
        ticker_count = 0
        sector_buys: dict[str, int] = {}
        sector_sells: dict[str, int] = {}

        for bar in bars:
            ticker = bar.get("T", "")
            volume = bar.get("v", 0)
            open_price = bar.get("o", 0)
            close = bar.get("c", 0)

            if not ticker or volume <= 0 or open_price <= 0:
                continue

            # Update volume history
            if ticker not in ticker_volumes:
                ticker_volumes[ticker] = []
            ticker_volumes[ticker].append(volume)

            # Need enough history for volume stats
            vol_hist = ticker_volumes[ticker]
            if len(vol_hist) < vol_period:
                continue

            # Calculate volume mean and sigma over the lookback
            recent = vol_hist[-vol_period:]
            mean_vol = sum(recent) / vol_period
            variance = sum((v - mean_vol) ** 2 for v in recent) / vol_period
            sigma_vol = variance ** 0.5

            # Volume spike detection
            threshold = mean_vol + k * sigma_vol
            if volume > threshold:
                if close > open_price:
                    buy_signals += 1
                elif close < open_price:
                    sell_signals += 1

                # Per-sector signal tracking
                if sector_mapping and ticker in sector_mapping:
                    etf = FMP_SECTOR_TO_ETF.get(sector_mapping[ticker])
                    if etf:
                        if close > open_price:
                            sector_buys[etf] = sector_buys.get(etf, 0) + 1
                        elif close < open_price:
                            sector_sells[etf] = sector_sells.get(etf, 0) + 1

            ticker_count += 1

        # Debug: log per-sector signal counts
        if logger and sector_mapping and (sector_buys or sector_sells):
            logger.log(
                EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=1,
                message=(
                    f"Day {day.get('date', '?')}: sector signals = "
                    f"{sum(sector_buys.values())} buys, "
                    f"{sum(sector_sells.values())} sells, "
                    f"sectors={sorted(set(sector_buys.keys()) | set(sector_sells.keys()))}"
                ),
            )

        # Daily ratio
        total = buy_signals + sell_signals
        if total > 0:
            ratio = (buy_signals / total) * 100
        else:
            ratio = 50.0  # Neutral if no signals

        daily_ratios.append(ratio)

        # Store counts on the day dict for later access
        day["_buy_count"] = buy_signals
        day["_sell_count"] = sell_signals
        day["_ticker_count"] = ticker_count
        day["_sector_buys"] = sector_buys
        day["_sector_sells"] = sector_sells

    return daily_ratios


def _calculate_sector_bmi(daily_data: list[dict],
                          config: Config,
                          logger: EventLogger | None = None) -> dict[str, float]:
    """Calculate per-sector BMI from daily sector buy/sell data.

    Same algorithm as market BMI: SMA25 of daily sector ratios.
    Requires _sector_buys/_sector_sells to be set on each day dict.

    Returns: {ETF: bmi_value} for sectors with sufficient data.
    """
    sma_period = config.core["bmi_sma_period"]
    min_signals = config.core.get("sector_bmi_min_signals", 5)

    # Collect per-sector daily ratios
    sector_ratios: dict[str, list[float]] = {}

    for day in daily_data:
        buys = day.get("_sector_buys", {})
        sells = day.get("_sector_sells", {})
        all_etfs = set(buys.keys()) | set(sells.keys())

        for etf in all_etfs:
            b = buys.get(etf, 0)
            s = sells.get(etf, 0)
            total = b + s
            if total >= min_signals:
                ratio = (b / total) * 100
            else:
                ratio = 50.0  # Neutral if insufficient signals
            sector_ratios.setdefault(etf, []).append(ratio)

    # Debug: log sector ratio day counts
    if logger:
        ratio_counts = {etf: len(r) for etf, r in sector_ratios.items()}
        logger.log(
            EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=1,
            message=(
                f"Sector BMI: ratio day counts={ratio_counts}, "
                f"sma_period={sma_period}, min_signals={min_signals}"
            ),
        )

    # SMA25 per sector
    result = {}
    for etf, ratios in sector_ratios.items():
        if len(ratios) >= sma_period:
            bmi = sum(ratios[-sma_period:]) / sma_period
            result[etf] = round(bmi, 2)

    if logger:
        logger.log(
            EventType.PHASE_DIAGNOSTIC, Severity.INFO, phase=1,
            message=f"Sector BMI results: {result}",
        )

    return result


def _classify_bmi(bmi_value: float, config: Config) -> BMIRegime:
    """Classify BMI into regime."""
    green = config.tuning["bmi_green_threshold"]
    red = config.tuning["bmi_red_threshold"]

    if bmi_value <= green:
        return BMIRegime.GREEN
    elif bmi_value >= red:
        return BMIRegime.RED
    else:
        return BMIRegime.YELLOW


def _detect_divergence(daily_data: list[dict],
                       daily_ratios: list[float],
                       config: Config) -> str | None:
    """Detect BMI divergence with SPY.

    Bearish divergence: SPY up >1% in 5d but BMI down >2 points.
    """
    if len(daily_data) < 6 or len(daily_ratios) < 6:
        return None

    spy_change_threshold = config.tuning["bmi_divergence_spy_change_pct"]
    bmi_change_threshold = config.tuning["bmi_divergence_bmi_change_pts"]

    # Find SPY close for today and 5 days ago
    spy_close_today = _find_spy_close(daily_data[-1])
    spy_close_5d = _find_spy_close(daily_data[-6])

    if spy_close_today is None or spy_close_5d is None or spy_close_5d == 0:
        return None

    spy_change_pct = ((spy_close_today - spy_close_5d) / spy_close_5d) * 100
    bmi_change = daily_ratios[-1] - daily_ratios[-6]

    # Bearish divergence: SPY up, BMI down
    if spy_change_pct > spy_change_threshold and bmi_change < bmi_change_threshold:
        return "bearish"

    return None


def _find_spy_close(day_data: dict) -> float | None:
    """Find SPY closing price from a day's grouped bars."""
    for bar in day_data.get("bars", []):
        if bar.get("T") == "SPY":
            return bar.get("c")
    return None


def _log_result(logger: EventLogger, result: Phase1Result,
                start_time: float, fallback: bool = False) -> None:
    """Log Phase 1 result."""
    bmi = result.bmi

    logger.log(
        EventType.REGIME_DECISION, Severity.INFO, phase=1,
        message=(
            f"BMI={bmi.bmi_value:.1f}% ({bmi.bmi_regime.value}) → "
            f"strategy={result.strategy_mode.value}"
            f"{' [DIVERGENCE: ' + bmi.divergence_type + ']' if bmi.divergence_detected else ''}"
            f"{' [FALLBACK: insufficient data]' if fallback else ''}"
        ),
        data={
            "bmi_value": bmi.bmi_value,
            "bmi_regime": bmi.bmi_regime.value,
            "daily_ratio": bmi.daily_ratio,
            "buy_count": bmi.buy_count,
            "sell_count": bmi.sell_count,
            "strategy_mode": result.strategy_mode.value,
            "divergence_detected": bmi.divergence_detected,
            "divergence_type": bmi.divergence_type,
            "ticker_count": result.ticker_count_for_bmi,
            "fallback": fallback,
        },
    )

    duration_ms = (time.monotonic() - start_time) * 1000
    logger.phase_complete(1, "Market Regime (BMI)", duration_ms=duration_ms)


async def _run_phase1_async(config: Config, logger: EventLogger,
                             sector_mapping: dict[str, str] | None = None) -> Phase1Result:
    """Async Phase 1: fetch grouped daily bars concurrently with semaphore rate limiting.

    Same computation as the sync path — only the data fetching is parallelised.
    Follows the Phase 4/5 async pattern (BC5).
    """
    from ifds.data.async_clients import AsyncPolygonClient

    start_time = time.monotonic()
    logger.phase_start(1, "Market Regime (BMI) (async)")

    sem_polygon = asyncio.Semaphore(config.runtime.get("async_sem_polygon", 5))

    polygon = AsyncPolygonClient(
        api_key=config.get_api_key("polygon"),
        timeout=config.runtime["api_timeout_polygon"],
        max_retries=config.runtime["api_max_retries"],
        semaphore=sem_polygon,
    )

    try:
        # Same lookback logic as sync path
        breadth_enabled = config.tuning.get("breadth_enabled", False)
        if breadth_enabled:
            lookback = config.core.get("breadth_lookback_calendar_days", 330)
        else:
            lookback = 75

        daily_bars = await _fetch_daily_history_async(polygon, lookback_calendar_days=lookback, logger=logger)

        if not daily_bars or len(daily_bars) < 25:
            logger.phase_error(1, "Market Regime (BMI)",
                               f"Insufficient data: got {len(daily_bars) if daily_bars else 0} days, need 25+")
            bmi = BMIData(bmi_value=50.0, bmi_regime=BMIRegime.YELLOW, daily_ratio=50.0)
            result = Phase1Result(bmi=bmi, strategy_mode=StrategyMode.LONG)
            _log_result(logger, result, start_time, fallback=True)
            return result

        # Pure computation — identical to sync path
        daily_ratios = _calculate_daily_ratios(daily_bars, config,
                                                sector_mapping=sector_mapping,
                                                logger=logger)

        sma_period = config.core["bmi_sma_period"]
        if len(daily_ratios) >= sma_period:
            bmi_value = sum(daily_ratios[-sma_period:]) / sma_period
        else:
            bmi_value = sum(daily_ratios) / len(daily_ratios)

        latest_ratio = daily_ratios[-1] if daily_ratios else 50.0
        latest_bars = daily_bars[-1] if daily_bars else {}
        buy_count = latest_bars.get("_buy_count", 0)
        sell_count = latest_bars.get("_sell_count", 0)

        bmi_regime = _classify_bmi(bmi_value, config)
        divergence = _detect_divergence(daily_bars, daily_ratios, config)

        bmi = BMIData(
            bmi_value=round(bmi_value, 2),
            bmi_regime=bmi_regime,
            daily_ratio=round(latest_ratio, 2),
            buy_count=buy_count,
            sell_count=sell_count,
            divergence_detected=divergence is not None,
            divergence_type=divergence,
        )

        strategy_mode = StrategyMode.SHORT if bmi_regime == BMIRegime.RED else StrategyMode.LONG

        sector_bmi_values: dict[str, float] = {}
        if sector_mapping:
            logger.log(EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=1,
                       message=f"Sector mapping: {len(sector_mapping)} tickers mapped")
            sector_bmi_values = _calculate_sector_bmi(daily_bars, config, logger=logger)

        ticker_count = daily_bars[-1].get("_ticker_count", 0) if daily_bars else 0
        result = Phase1Result(
            bmi=bmi,
            strategy_mode=strategy_mode,
            ticker_count_for_bmi=ticker_count,
            sector_bmi_values=sector_bmi_values,
            grouped_daily_bars=daily_bars if breadth_enabled else [],
        )

        _log_result(logger, result, start_time)
        return result

    except Exception as e:
        logger.phase_error(1, "Market Regime (BMI)", str(e))
        raise
    finally:
        await polygon.close()
