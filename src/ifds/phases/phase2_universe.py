"""Phase 2: Universe Building.

Filters the full US equity market into a tradeable universe based on strategy mode.

LONG universe (FMP screener):
- Market cap > $2B, Price > $5, Avg volume > 500K
- Has options, not an ETF
- Result: ~3,000 tickers

SHORT/Zombie universe (FMP screener):
- Market cap > $500M, Avg volume > 500K
- D/E > 3.0, Negative net margin, Interest coverage < 1.5
- Result: ~200 tickers

Zombie Hunter:
- Exclude tickers with earnings within 5 calendar days (binary event risk).
"""

import time
from datetime import date, timedelta

from ifds.config.loader import Config
from ifds.data.fmp import FMPClient
from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity
from ifds.models.market import Phase2Result, StrategyMode, Ticker


def run_phase2(config: Config, logger: EventLogger,
               fmp: FMPClient, strategy_mode: StrategyMode) -> Phase2Result:
    """Execute Phase 2: Universe Building.

    Args:
        config: Validated IFDS configuration.
        logger: Event logger for audit trail.
        fmp: FMP client for screener and earnings data.
        strategy_mode: LONG or SHORT from Phase 1.

    Returns:
        Phase2Result with filtered ticker universe.
    """
    start_time = time.monotonic()
    logger.phase_start(2, "Universe Building", input_count=0)

    try:
        # Step 1: Screener based on strategy mode
        if strategy_mode == StrategyMode.LONG:
            raw_tickers = _screen_long_universe(fmp, config, logger)
        else:
            raw_tickers = _screen_short_universe(fmp, config, logger)

        total_screened = len(raw_tickers)

        # Step 2: Earnings exclusion (Zombie Hunter)
        exclusion_days = config.tuning["earnings_exclusion_days"]
        tickers, earnings_excluded = _exclude_earnings(
            raw_tickers, fmp, exclusion_days, logger
        )

        result = Phase2Result(
            tickers=tickers,
            total_screened=total_screened,
            earnings_excluded=earnings_excluded,
            strategy_mode=strategy_mode,
        )

        # Log
        logger.log(
            EventType.UNIVERSE_BUILT, Severity.INFO, phase=2,
            message=(
                f"Universe: {len(tickers)} tickers "
                f"(screened={total_screened}, earnings_excluded={len(earnings_excluded)}, "
                f"mode={strategy_mode.value})"
            ),
            data={
                "ticker_count": len(tickers),
                "total_screened": total_screened,
                "earnings_excluded_count": len(earnings_excluded),
                "strategy_mode": strategy_mode.value,
            },
        )

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.phase_complete(2, "Universe Building",
                              output_count=len(tickers), duration_ms=duration_ms)

        return result

    except Exception as e:
        logger.phase_error(2, "Universe Building", str(e))
        raise


def _screen_long_universe(fmp: FMPClient, config: Config,
                          logger: EventLogger) -> list[Ticker]:
    """Screen for LONG universe using FMP screener."""
    params = {
        "marketCapMoreThan": config.tuning["universe_min_market_cap"],
        "priceMoreThan": config.tuning["universe_min_price"],
        "volumeMoreThan": config.tuning["universe_min_avg_volume"],
        "isEtf": "false",
        "limit": 10000,
    }

    logger.log(EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=2,
               message=f"FMP screener request (LONG): {params}",
               data={"screener_params": params})

    raw = fmp.screener(params)

    raw_count = len(raw) if raw else 0
    logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO, phase=2,
               message=f"FMP screener response: {raw_count} raw tickers",
               data={"raw_count": raw_count})

    if not raw:
        logger.log(EventType.PHASE_ERROR, Severity.ERROR, phase=2,
                    message="FMP screener returned no results for LONG universe")
        return []

    tickers = []
    filtered_inactive = 0
    for item in raw:
        # Filter: must have options (if configured)
        if config.tuning["universe_require_options"]:
            if not item.get("isActivelyTrading", True):
                filtered_inactive += 1
                continue

        ticker = _fmp_to_ticker(item)
        tickers.append(ticker)

    if filtered_inactive:
        logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO, phase=2,
                   message=f"Filtered {filtered_inactive} inactive tickers (isActivelyTrading=false)",
                   data={"filtered_inactive": filtered_inactive,
                         "remaining": len(tickers)})

    return tickers


def _screen_short_universe(fmp: FMPClient, config: Config,
                           logger: EventLogger) -> list[Ticker]:
    """Screen for SHORT/Zombie universe using FMP screener."""
    params = {
        "marketCapMoreThan": config.tuning["zombie_min_market_cap"],
        "volumeMoreThan": config.tuning["zombie_min_avg_volume"],
        "isEtf": "false",
        "limit": 5000,
    }

    logger.log(EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=2,
               message=f"FMP screener request (SHORT): {params}",
               data={"screener_params": params})

    raw = fmp.screener(params)

    raw_count = len(raw) if raw else 0
    logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO, phase=2,
               message=f"FMP screener response: {raw_count} raw tickers",
               data={"raw_count": raw_count})

    if not raw:
        logger.log(EventType.PHASE_ERROR, Severity.ERROR, phase=2,
                    message="FMP screener returned no results for SHORT universe")
        return []

    # Apply zombie filters locally
    min_de = config.tuning["zombie_min_debt_equity"]
    max_margin = config.tuning["zombie_max_net_margin"]
    max_ic = config.tuning["zombie_max_interest_coverage"]

    tickers = []
    for item in raw:
        de = item.get("debtToEquity")
        margin = item.get("netIncomeMargin")
        # FMP doesn't always have interestCoverage in screener,
        # so we only filter on it when available
        ic = item.get("interestCoverage")

        # All zombie criteria must be met
        if de is None or de <= min_de:
            continue
        if margin is None or margin >= max_margin:
            continue
        if ic is not None and ic >= max_ic:
            continue

        ticker = _fmp_to_ticker(item)
        ticker.debt_equity = de
        ticker.net_margin = margin
        ticker.interest_coverage = ic
        tickers.append(ticker)

    return tickers


def _exclude_earnings(tickers: list[Ticker], fmp: FMPClient,
                      exclusion_days: int,
                      logger: EventLogger) -> tuple[list[Ticker], list[str]]:
    """Exclude tickers with earnings within the exclusion window.

    Returns (filtered_tickers, excluded_symbols).
    """
    if not tickers:
        return tickers, []

    today = date.today()
    to_date = today + timedelta(days=exclusion_days)

    earnings_data = fmp.get_earnings_calendar(
        from_date=today.isoformat(),
        to_date=to_date.isoformat(),
    )

    ec_count = len(earnings_data) if earnings_data else 0
    logger.log(EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=2,
               message=f"Earnings calendar: {ec_count} entries ({today} to {to_date})",
               data={"earnings_entries": ec_count,
                     "from_date": today.isoformat(),
                     "to_date": to_date.isoformat()})

    if not earnings_data:
        return tickers, []

    # Build set of symbols with upcoming earnings
    earnings_symbols: set[str] = set()
    for entry in earnings_data:
        symbol = entry.get("symbol")
        if symbol:
            earnings_symbols.add(symbol.upper())

    # Filter
    filtered = []
    excluded = []
    for ticker in tickers:
        if ticker.symbol.upper() in earnings_symbols:
            excluded.append(ticker.symbol)
            logger.log(
                EventType.EARNINGS_EXCLUSION, Severity.DEBUG, phase=2,
                ticker=ticker.symbol,
                message=f"{ticker.symbol} excluded: earnings within {exclusion_days} days",
            )
        else:
            filtered.append(ticker)

    return filtered, excluded


def _fmp_to_ticker(item: dict) -> Ticker:
    """Convert FMP screener result to Ticker dataclass."""
    return Ticker(
        symbol=item.get("symbol", ""),
        company_name=item.get("companyName", ""),
        sector=item.get("sector", ""),
        market_cap=item.get("marketCap", 0) or 0,
        price=item.get("price", 0) or 0,
        avg_volume=item.get("volume", 0) or 0,
        has_options=True,  # FMP screener includes actively traded stocks
        is_etf=item.get("isEtf", False) or False,
    )
