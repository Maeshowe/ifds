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
- Exclude tickers with earnings within N calendar days (binary event risk, default 7).

SEC Filing Exclusion (Fázis 1, 2026-05-16):
- Exclude tickers with a predicted 10-Q (or 10-K proxy) within `sec_filing_lookahead_days`.
- Plugs the AGNC-style hole where FMP's earnings_calendar misses the SEC filing event.
"""

import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

from ifds.config.loader import Config
from ifds.data.fmp import FMPClient
from ifds.data.sec_edgar import SecEdgarClient
from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity
from ifds.models.market import Phase2Result, StrategyMode, Ticker


def run_phase2(
    config: Config,
    logger: EventLogger,
    fmp: FMPClient,
    strategy_mode: StrategyMode,
    grouped_daily_bars: list[dict] | None = None,
) -> Phase2Result:
    """Execute Phase 2: Universe Building.

    Args:
        config: Validated IFDS configuration.
        logger: Event logger for audit trail.
        fmp: FMP client for screener and earnings data.
        strategy_mode: LONG or SHORT from Phase 1.
        grouped_daily_bars: Phase 1's Polygon grouped dailies (~38 sessions, already
            fetched for the BMI SMA25). Used by the liquidity floor, which is in
            SHADOW MODE: it measures and reports, it does not yet narrow the
            universe. See docs/tasks/2026-10-20-universe-fail-open-decision.md §9.

    Returns:
        Phase2Result with filtered ticker universe.
    """
    start_time = time.monotonic()
    logger.phase_start(2, "Universe Building", input_count=0)

    try:
        # Step 1: Screener based on strategy mode
        if strategy_mode == StrategyMode.LONG:
            raw_tickers = _screen_long_universe(
                fmp, config, logger, grouped_daily_bars=grouped_daily_bars
            )
        else:
            raw_tickers = _screen_short_universe(fmp, config, logger)

        total_screened = len(raw_tickers)

        # Step 2: Earnings exclusion (Zombie Hunter)
        exclusion_days = config.tuning["earnings_exclusion_days"]
        tickers, earnings_excluded, bulk_n, ticker_n = _exclude_earnings(
            raw_tickers, fmp, exclusion_days, logger
        )

        # Step 3: SEC 10-Q / 10-K filing exclusion (Fázis 1, 2026-05-16)
        tickers, sec_excluded = _exclude_sec_filings(tickers, config, logger)

        result = Phase2Result(
            tickers=tickers,
            total_screened=total_screened,
            earnings_excluded=earnings_excluded,
            strategy_mode=strategy_mode,
            bulk_excluded_count=bulk_n,
            ticker_specific_excluded_count=ticker_n,
            sec_filing_excluded=sec_excluded,
            universe_provenance=dict(_LAST_UNIVERSE_PROVENANCE),
        )

        # Survivorship bias protection: snapshot + diff
        _save_universe_snapshot(tickers, config, logger)

        # Log
        logger.log(
            EventType.UNIVERSE_BUILT,
            Severity.INFO,
            phase=2,
            message=(
                f"Universe: {len(tickers)} tickers "
                f"(screened={total_screened}, earnings_excluded={len(earnings_excluded)}, "
                f"sec_filing_excluded={len(sec_excluded)}, mode={strategy_mode.value})"
            ),
            data={
                "ticker_count": len(tickers),
                "total_screened": total_screened,
                "earnings_excluded_count": len(earnings_excluded),
                "sec_filing_excluded_count": len(sec_excluded),
                "strategy_mode": strategy_mode.value,
            },
        )

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.phase_complete(
            2, "Universe Building", output_count=len(tickers), duration_ms=duration_ms
        )

        return result

    except Exception as e:
        logger.phase_error(2, "Universe Building", str(e))
        raise


#: Filled by ``_screen_long_universe`` and read by ``run_phase2`` — the provenance
#: of the universe it just built. Module-level because the screening helper returns a
#: plain ticker list and threading a second return value through every caller and test
#: would be a larger change than this record is worth.
_LAST_UNIVERSE_PROVENANCE: dict = {}


def _screen_long_universe(
    fmp: FMPClient,
    config: Config,
    logger: EventLogger,
    grouped_daily_bars: list[dict] | None = None,
) -> list[Ticker]:
    """Screen for LONG universe.

    2026-05-18 (Day 63 §3.9): the default `universe_source` is now
    "swing_sp500_r1000" — the FMP screener result is **intersected** with the
    S&P 500 + Russell 1000 union so per-ticker FMP enrichment (sector,
    market_cap, price, volume) is preserved while the universe membership
    comes from a stable index-based source. Legacy `fmp_screener` source
    kept as fallback (set `universe_source: "fmp_screener"` in config).
    """
    params = {
        "marketCapMoreThan": config.tuning["universe_min_market_cap"],
        "priceMoreThan": config.tuning["universe_min_price"],
        # avgVolumeMoreThan, NOT volumeMoreThan. FMP's `volume` field is TODAY'S
        # PARTIAL intraday volume; the average lives in `avgVolume`. Passing an
        # "average volume" threshold to the partial-volume filter made the universe
        # a function of WHEN the phase ran: measured 2026-10-20 at 11:51 ET, AFL
        # showed volume 199,786 against avgVolume 2,001,023 and was excluded from a
        # 500k floor despite a $60bn cap. Membership coverage went 51.5% -> 89.7%
        # on this one word. Verified honoured (a dropped FMP param does not move the
        # count): avgVolumeMoreThan gives 2125/402/9 at 500k/5M/50M, while
        # averageVolumeMoreThan returns the unfiltered 4733 exactly like a fabricated
        # control param. Report: docs/review/2026-10-20-screener-intraday-volume-bug.md
        "avgVolumeMoreThan": config.tuning["universe_min_avg_volume"],
        "isEtf": "false",
        "limit": 10000,
    }

    logger.log(
        EventType.PHASE_DIAGNOSTIC,
        Severity.DEBUG,
        phase=2,
        message=f"FMP screener request (LONG): {params}",
        data={"screener_params": params},
    )

    raw = fmp.screener(params)

    raw_count = len(raw) if raw else 0
    logger.log(
        EventType.PHASE_DIAGNOSTIC,
        Severity.INFO,
        phase=2,
        message=f"FMP screener response: {raw_count} raw tickers",
        data={"raw_count": raw_count},
    )

    if not raw:
        logger.log(
            EventType.PHASE_ERROR,
            Severity.ERROR,
            phase=2,
            message="FMP screener returned no results for LONG universe",
        )
        return []

    universe_source = config.tuning.get("universe_source", "swing_sp500_r1000")
    swing_membership: set[str] | None = None
    membership_sectors: dict[str, str] = {}
    universe = None
    if universe_source == "swing_sp500_r1000":
        universe = _load_swing_membership(fmp, config, logger)
        if universe is not None:
            swing_membership = {s.upper() for s in universe.symbols}
            membership_sectors = dict(universe.sectors)
        if swing_membership is None:
            # F-1c/F-1d (D-U1, approved 2026-10-20): the legacy screener is NOT a
            # staler membership list, it is a DIFFERENT population. Substituting it
            # is what hid nine weeks of degradation (2026-08-16 .. 10-19) and swapped
            # 377 of 730 names (52%) for non-members. Since the staleness ladder in
            # `SwingUniverseSource` now serves an expired cache rather than giving up,
            # reaching here means there is no usable membership AT ALL — which must
            # stop the phase, not silently redefine the universe.
            logger.log(
                EventType.CONFIG_WARNING,
                Severity.ERROR,
                phase=2,
                message=(
                    "Swing universe unavailable (no live source and no usable cache) — "
                    "REFUSING to substitute the raw FMP screener. The pipeline context "
                    "will not be written; fix the membership source."
                ),
            )
            raise RuntimeError(
                "Swing universe unavailable: no live source and no usable cache. "
                "Substituting the legacy screener would silently change the scored "
                "population (D-U1/F-1d)."
            )

    # --- (C): membership ∩ liquidity floor, with the screener as ENRICHMENT ------
    # Approved 2026-10-20 (D-U2 = (C)). The screener no longer DEFINES the universe;
    # it supplies sector / market cap / price / volume for names the membership and
    # the floor already selected. Measured on the switch day: the live screener-
    # intersected universe was 919 of 1027 members, the floor passed 909, and only
    # 11 floor-passing members had no screener row at all.
    floor_result = None
    if swing_membership is not None:
        floor_result = _liquidity_floor(swing_membership, config, logger, grouped_daily_bars)

    tickers = []
    filtered_inactive = 0
    filtered_membership = 0
    filtered_floor = 0
    filtered_no_enrichment = 0
    rescued_from_membership = 0

    if floor_result is not None:
        by_symbol = {
            (item.get("symbol") or "").upper().replace(".", "-"): item for item in raw
        }
        filtered_floor = len(swing_membership) - len(floor_result.passed)
        for symbol in sorted(floor_result.passed):
            item = by_symbol.get(symbol)
            if item is None:
                # The screener never returned this member, so there is no row to
                # enrich from. Since 2026-10-20 the GICS sector comes from the same
                # Wikipedia fetch as the membership, and the floor already computed
                # this name's price and median volume — so the record can be built
                # without a single extra API call. market_cap stays 0: it is written
                # to the universe audit snapshot and read by nothing else.
                #
                # A sector is still MANDATORY: it drives Phase 3 breadth and the
                # sector caps, so a sectorless name is excluded rather than guessed.
                sector = membership_sectors.get(symbol)
                price, median_volume = floor_result.metrics.get(symbol, (0.0, 0.0))
                if not sector or price <= 0:
                    filtered_no_enrichment += 1
                    continue
                tickers.append(
                    Ticker(
                        symbol=symbol,
                        company_name="",
                        sector=sector,
                        market_cap=0,
                        price=price,
                        avg_volume=median_volume,
                        has_options=True,
                        is_etf=False,
                    )
                )
                rescued_from_membership += 1
                continue
            if config.tuning["universe_require_options"] and not item.get(
                "isActivelyTrading", True
            ):
                filtered_inactive += 1
                continue
            tickers.append(_fmp_to_ticker(item))
    else:
        # Degraded path: no liquidity floor (no bars, i.e. `breadth_enabled` off), or
        # the legacy `universe_source`. Falls back to screener ∩ membership — still
        # membership-constrained, so no population swap, but the screener's
        # composition leaks back in. Logged loudly below.
        for item in raw:
            if config.tuning["universe_require_options"]:
                if not item.get("isActivelyTrading", True):
                    filtered_inactive += 1
                    continue
            if swing_membership is not None:
                symbol = (item.get("symbol") or "").upper().replace(".", "-")
                if symbol not in swing_membership:
                    filtered_membership += 1
                    continue
            tickers.append(_fmp_to_ticker(item))

    if filtered_inactive:
        logger.log(
            EventType.PHASE_DIAGNOSTIC,
            Severity.INFO,
            phase=2,
            message=f"Filtered {filtered_inactive} inactive tickers (isActivelyTrading=false)",
            data={"filtered_inactive": filtered_inactive, "remaining": len(tickers)},
        )

    if filtered_membership:
        logger.log(
            EventType.PHASE_DIAGNOSTIC,
            Severity.INFO,
            phase=2,
            message=(
                f"Swing universe filter: {filtered_membership} tickers "
                f"excluded (not in S&P 500 + Russell 1000)"
            ),
            data={
                "swing_membership_size": len(swing_membership or []),
                "filtered_membership": filtered_membership,
                "remaining": len(tickers),
            },
        )

    if floor_result is not None:
        _LAST_UNIVERSE_PROVENANCE.clear()
        _LAST_UNIVERSE_PROVENANCE.update(
            {
                "universe_definition": "index_union_plus_liquidity_floor",
                "membership": universe.provenance() if universe is not None else {},
                "floor": floor_result.provenance(),
                "rescued_from_membership": rescued_from_membership,
                "excluded_no_sector": filtered_no_enrichment,
                "excluded_inactive": filtered_inactive,
                "built": len(tickers),
            }
        )
        logger.log(
            EventType.PHASE_DIAGNOSTIC,
            Severity.INFO,
            phase=2,
            message=(
                f"Universe (C): {len(tickers)} tickers from {len(swing_membership)} members "
                f"— floor excluded {filtered_floor}, rescued from membership "
                f"{rescued_from_membership}, no sector {filtered_no_enrichment}, "
                f"inactive {filtered_inactive}"
            ),
            data={
                "universe_definition": "index_union_plus_liquidity_floor",
                "membership": len(swing_membership),
                "floor_passed": len(floor_result.passed),
                "excluded_floor": filtered_floor,
                "rescued_from_membership": rescued_from_membership,
                "excluded_no_sector": filtered_no_enrichment,
                "excluded_inactive": filtered_inactive,
                "floor_provenance": floor_result.provenance(),
            },
        )
    elif swing_membership is not None:
        logger.log(
            EventType.CONFIG_WARNING,
            Severity.ERROR,
            phase=2,
            message=(
                "Universe DEGRADED to screener ∩ membership: the liquidity floor was "
                "unavailable, so the screener's composition defines the universe again. "
                "Still membership-constrained (no population swap). Check `breadth_enabled`."
            ),
            data={"universe_definition": "screener_intersect_membership_degraded"},
        )
        _LAST_UNIVERSE_PROVENANCE.clear()
        _LAST_UNIVERSE_PROVENANCE.update(
            {
                "universe_definition": "screener_intersect_membership_degraded",
                "membership": universe.provenance() if universe is not None else {},
                "degraded": True,
                "built": len(tickers),
            }
        )

    return tickers


def _liquidity_floor(
    membership: set[str],
    config: Config,
    logger: EventLogger,
    grouped_daily_bars: list[dict] | None,
):
    """Compute the (C) liquidity floor over index membership, or None if impossible.

    (C), approved 2026-10-20: the universe is `membership ∩ floor`, and the floor is a
    pure function of Phase 1's completed daily bars — a median over 20 sessions — so it
    is immune to the two defects that defined the universe before it:

    * the FMP screener's own composition, which swung the scored panel between 226 and
      1479 names week to week when it was intersected with membership, and
    * the screener's ``volume`` field being TODAY'S PARTIAL intraday volume, which made
      the universe a function of the hour the phase ran (measured 2026-10-20: the same
      call returned 1207 rows mid-session and 2125 against the true average).

    Returns None when the floor cannot be computed — no bars, i.e. ``breadth_enabled``
    off. The caller then degrades to screener ∩ membership with an ERROR, which is the
    old behaviour: still membership-constrained, so no population swap, but the
    screener's composition leaks back in.
    """
    if not grouped_daily_bars:
        logger.log(
            EventType.CONFIG_WARNING,
            Severity.WARNING,
            phase=2,
            message=(
                "Liquidity floor unavailable: Phase 1 supplied no grouped daily bars "
                "(check `breadth_enabled`). Falling back to screener ∩ membership."
            ),
        )
        return None

    from ifds.data.liquidity_floor import DEFAULT_LOOKBACK_SESSIONS, compute_floor

    try:
        return compute_floor(
            membership,
            grouped_daily_bars,
            min_price=float(config.tuning["universe_min_price"]),
            min_avg_volume=float(config.tuning["universe_min_avg_volume"]),
            lookback=int(
                config.tuning.get("universe_floor_lookback_sessions", DEFAULT_LOOKBACK_SESSIONS)
            ),
        )
    except (ValueError, KeyError) as exc:
        logger.log(
            EventType.CONFIG_WARNING,
            Severity.ERROR,
            phase=2,
            message=(
                f"Liquidity floor failed ({exc}) — falling back to screener ∩ membership."
            ),
        )
        return None


def _load_swing_membership(fmp: FMPClient, config: Config, logger: EventLogger):
    """Load the membership as a ``UniverseResult``, or None on failure.

    Returns the whole result rather than a bare symbol set so the GICS sectors that
    came from the same Wikipedia fetch survive to the caller — without them a member
    the FMP screener never returned would have no sector and could not be built.
    """
    from ifds.data.swing_universe import SwingUniverseSource

    cache_dir = Path(
        config.tuning.get(
            "swing_universe_cache_dir",
            "state/swing_universe",
        )
    )
    ttl_days = int(config.tuning.get("swing_universe_cache_ttl_days", 7))
    source = SwingUniverseSource(cache_dir=cache_dir, cache_ttl_days=ttl_days)
    try:
        symbols = source.get_universe(fmp_client=fmp)
    except Exception as exc:
        logger.log(
            EventType.CONFIG_WARNING,
            Severity.WARNING,
            phase=2,
            message=f"Swing universe load failed: {exc}",
        )
        return None

    logger.log(
        EventType.PHASE_DIAGNOSTIC,
        Severity.INFO,
        phase=2,
        message=f"Swing universe loaded: {len(symbols)} symbols " f"(S&P 500 + Russell 1000 union)",
        data={
            "swing_universe_size": len(symbols),
            "universe_provenance": symbols.provenance(),
        },
    )
    return symbols


def _screen_short_universe(fmp: FMPClient, config: Config, logger: EventLogger) -> list[Ticker]:
    """Screen for SHORT/Zombie universe using FMP screener."""
    params = {
        "marketCapMoreThan": config.tuning["zombie_min_market_cap"],
        # Same fix as the LONG path: the threshold means AVERAGE volume, so it goes
        # to avgVolumeMoreThan and not to FMP's partial-day `volume` filter.
        "avgVolumeMoreThan": config.tuning["zombie_min_avg_volume"],
        "isEtf": "false",
        "limit": 5000,
    }

    logger.log(
        EventType.PHASE_DIAGNOSTIC,
        Severity.DEBUG,
        phase=2,
        message=f"FMP screener request (SHORT): {params}",
        data={"screener_params": params},
    )

    raw = fmp.screener(params)

    raw_count = len(raw) if raw else 0
    logger.log(
        EventType.PHASE_DIAGNOSTIC,
        Severity.INFO,
        phase=2,
        message=f"FMP screener response: {raw_count} raw tickers",
        data={"raw_count": raw_count},
    )

    if not raw:
        logger.log(
            EventType.PHASE_ERROR,
            Severity.ERROR,
            phase=2,
            message="FMP screener returned no results for SHORT universe",
        )
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


def _exclude_earnings(
    tickers: list[Ticker], fmp: FMPClient, exclusion_days: int, logger: EventLogger
) -> tuple[list[Ticker], list[str], int, int]:
    """Exclude tickers with earnings within the exclusion window.

    Two-pass approach:
    1. Bulk FMP earnings-calendar (fast, covers most tickers)
    2. Ticker-specific /stable/earnings?symbol= for any ticker that
       survived pass 1 (catches ADRs and others missed by bulk endpoint)

    Returns (filtered_tickers, excluded_symbols, bulk_count, ticker_specific_count).
    """
    if not tickers:
        return tickers, [], 0, 0

    today = date.today()
    to_date = today + timedelta(days=exclusion_days)
    today_str = today.isoformat()
    to_date_str = to_date.isoformat()

    # --- Pass 1: Bulk calendar ---
    earnings_data = fmp.get_earnings_calendar(
        from_date=today_str,
        to_date=to_date_str,
    )

    ec_count = len(earnings_data) if earnings_data else 0
    logger.log(
        EventType.PHASE_DIAGNOSTIC,
        Severity.DEBUG,
        phase=2,
        message=f"Earnings calendar: {ec_count} entries ({today_str} to {to_date_str})",
        data={"earnings_entries": ec_count, "from_date": today_str, "to_date": to_date_str},
    )

    # Build set of symbols caught by bulk
    bulk_earnings_symbols: set[str] = set()
    if earnings_data:
        for entry in earnings_data:
            symbol = entry.get("symbol")
            if symbol:
                bulk_earnings_symbols.add(symbol.upper())

    # Pass 1 filter
    filtered = []
    excluded = []
    for ticker in tickers:
        if ticker.symbol.upper() in bulk_earnings_symbols:
            excluded.append(ticker.symbol)
            logger.log(
                EventType.EARNINGS_EXCLUSION,
                Severity.DEBUG,
                phase=2,
                ticker=ticker.symbol,
                message=f"{ticker.symbol} excluded: earnings within {exclusion_days} days (bulk calendar)",
            )
        else:
            filtered.append(ticker)

    bulk_excluded_count = len(excluded)

    # --- Pass 2: Ticker-specific check for survivors ---
    # Uses /stable/earnings?symbol= — more reliable for ADRs and smaller caps
    from concurrent.futures import ThreadPoolExecutor, as_completed

    pass2_excluded: list[str] = []
    pass2_filtered: list[Ticker] = []

    def _check_one(ticker: Ticker) -> tuple[Ticker, bool, str | None]:
        """Check single ticker earnings. Returns (ticker, should_exclude, date)."""
        try:
            next_date = fmp.get_next_earnings_date(ticker.symbol)
            if next_date and today_str <= next_date <= to_date_str:
                return ticker, True, next_date
            return ticker, False, next_date
        except Exception:
            return ticker, False, None  # fail-open

    max_workers = min(20, len(filtered)) if filtered else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_check_one, t): t for t in filtered}
        for future in as_completed(futures):
            try:
                ticker_obj, should_exclude, next_date = future.result()
            except Exception:
                ticker_obj = futures[future]
                pass2_filtered.append(ticker_obj)
                continue

            if should_exclude:
                pass2_excluded.append(ticker_obj.symbol)
                excluded.append(ticker_obj.symbol)
                logger.log(
                    EventType.EARNINGS_EXCLUSION,
                    Severity.INFO,
                    phase=2,
                    ticker=ticker_obj.symbol,
                    message=(
                        f"{ticker_obj.symbol} excluded: earnings within {exclusion_days} days "
                        f"(ticker-specific: {next_date}, missed by bulk calendar)"
                    ),
                )
            else:
                pass2_filtered.append(ticker_obj)

    logger.log(
        EventType.PHASE_DIAGNOSTIC,
        Severity.INFO,
        phase=2,
        message=(
            f"Earnings exclusion: {len(excluded)} total "
            f"(bulk={bulk_excluded_count}, ticker-specific={len(pass2_excluded)})"
        ),
        data={
            "total_excluded": len(excluded),
            "bulk_excluded": bulk_excluded_count,
            "ticker_specific_excluded": len(pass2_excluded),
            "ticker_specific_catches": pass2_excluded,
        },
    )

    return pass2_filtered, excluded, bulk_excluded_count, len(pass2_excluded)


def _exclude_sec_filings(
    tickers: list[Ticker], config: Config, logger: EventLogger
) -> tuple[list[Ticker], list[str]]:
    """Exclude tickers with an upcoming 10-Q / 10-K filing (Fázis 1, 2026-05-16).

    Closes the AGNC 2026-05-04 case: a 10-Q event (not earnings) caused a
    -$380 LOSS_EXIT. FMP's earnings_calendar misses these.

    Fail-open by design: any failure to query SEC EDGAR (network, stale
    cache > 2d, missing CIK) → ticker passes through. Risk-asymmetry is
    documented in the task spec §8 — false negative <2-5% accepted under
    the 12-position concurrent cap.
    """
    if not config.tuning.get("sec_filing_exclusion_enabled", False):
        return tickers, []

    if not tickers:
        return tickers, []

    cache_dir = Path(config.tuning.get("sec_filing_cache_dir", "state/sec_cache"))
    lookahead_days = int(config.tuning.get("sec_filing_lookahead_days", 10))
    tolerance_days = int(config.tuning.get("sec_filing_quarterly_tolerance_days", 10))
    cik_refresh_days = int(config.tuning.get("sec_filing_cik_refresh_days", 30))
    filings_refresh_days = int(config.tuning.get("sec_filing_filings_refresh_days", 1))

    client = SecEdgarClient(
        cache_dir=cache_dir,
        cik_refresh_days=cik_refresh_days,
        filings_refresh_days=filings_refresh_days,
        tolerance_days=tolerance_days,
    )

    filtered: list[Ticker] = []
    excluded: list[str] = []
    for ticker in tickers:
        try:
            if client.has_upcoming_10q_or_10k(ticker.symbol, lookahead_days=lookahead_days):
                excluded.append(ticker.symbol)
                logger.log(
                    EventType.SEC_FILING_EXCLUSION,
                    Severity.INFO,
                    phase=2,
                    ticker=ticker.symbol,
                    message=(
                        f"{ticker.symbol} excluded: predicted 10-Q within "
                        f"{lookahead_days}d (±{tolerance_days}d tolerance)"
                    ),
                )
            else:
                filtered.append(ticker)
        except Exception as exc:
            # Defensive fail-open: a single ticker's exception must not derail Phase 2
            logger.log(
                EventType.API_FALLBACK,
                Severity.WARNING,
                phase=2,
                ticker=ticker.symbol,
                message=f"SEC EDGAR check failed for {ticker.symbol} ({exc}) — fail-open",
            )
            filtered.append(ticker)

    logger.log(
        EventType.PHASE_DIAGNOSTIC,
        Severity.INFO,
        phase=2,
        message=(
            f"SEC filing exclusion: {len(excluded)} tickers excluded "
            f"(lookahead={lookahead_days}d ±{tolerance_days}d)"
        ),
        data={
            "sec_filing_excluded_count": len(excluded),
            "sec_filing_excluded": excluded[:50],
            "lookahead_days": lookahead_days,
            "tolerance_days": tolerance_days,
        },
    )

    return filtered, excluded


def _fmp_to_ticker(item: dict) -> Ticker:
    """Convert FMP screener result to Ticker dataclass."""
    return Ticker(
        symbol=item.get("symbol", ""),
        company_name=item.get("companyName", ""),
        sector=item.get("sector", ""),
        market_cap=item.get("marketCap", 0) or 0,
        price=item.get("price", 0) or 0,
        # `avgVolume`, not `volume`: the field is named avg_volume and FMP's
        # `volume` is today's PARTIAL intraday figure (2026-10-20 finding).
        avg_volume=item.get("avgVolume", item.get("volume", 0)) or 0,
        has_options=True,  # FMP screener includes actively traded stocks
        is_etf=item.get("isEtf", False) or False,
    )


def _save_universe_snapshot(tickers: list[Ticker], config: Config, logger: EventLogger) -> None:
    """Save universe snapshot and log diffs vs previous day (BC13)."""
    snap_dir = config.runtime.get("survivorship_snapshot_dir", "state/universe_snapshots")
    max_snaps = config.runtime.get("survivorship_max_snapshots", 30)

    try:
        os.makedirs(snap_dir, exist_ok=True)

        today = date.today().isoformat()
        snapshot = [
            {"symbol": t.symbol, "market_cap": t.market_cap, "sector": t.sector} for t in tickers
        ]

        # Save today's snapshot
        snap_path = os.path.join(snap_dir, f"{today}.json")
        with open(snap_path, "w") as f:
            json.dump(snapshot, f)

        # Compare with most recent previous snapshot
        existing = sorted(
            [fn for fn in os.listdir(snap_dir) if fn.endswith(".json") and fn != f"{today}.json"],
            reverse=True,
        )
        if existing:
            prev_path = os.path.join(snap_dir, existing[0])
            with open(prev_path) as f:
                prev_data = json.load(f)
            prev_symbols = {r["symbol"] for r in prev_data}
            curr_symbols = {t.symbol for t in tickers}

            removed = sorted(prev_symbols - curr_symbols)
            added = sorted(curr_symbols - prev_symbols)

            if removed:
                logger.log(
                    EventType.PHASE_DIAGNOSTIC,
                    Severity.WARNING,
                    phase=2,
                    message=f"[SURVIVORSHIP] Removed from universe: {removed}",
                    data={"removed_count": len(removed), "removed": removed[:50]},
                )
            if added:
                logger.log(
                    EventType.PHASE_DIAGNOSTIC,
                    Severity.INFO,
                    phase=2,
                    message=f"[SURVIVORSHIP] New in universe: {added}",
                    data={"added_count": len(added), "added": added[:50]},
                )
            if not removed and not added:
                logger.log(
                    EventType.PHASE_DIAGNOSTIC,
                    Severity.DEBUG,
                    phase=2,
                    message="[SURVIVORSHIP] Universe unchanged",
                )

        # Prune old snapshots beyond max
        all_snaps = sorted(
            [fn for fn in os.listdir(snap_dir) if fn.endswith(".json")],
            reverse=True,
        )
        for old in all_snaps[max_snaps:]:
            os.remove(os.path.join(snap_dir, old))

    except Exception as e:
        logger.log(
            EventType.CONFIG_WARNING,
            Severity.WARNING,
            phase=2,
            message=f"[SURVIVORSHIP] Error saving snapshot: {e}",
        )
