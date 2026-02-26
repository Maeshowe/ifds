"""Data provider adapters with automatic fallback.

Adapter pattern: Unusual Whales (primary) → Polygon (fallback).
Used for GEX and Dark Pool data where UW provides direct data
but Polygon can calculate approximations.
"""

import time
from abc import ABC, abstractmethod
from typing import Any

from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity


class GEXProvider(ABC):
    """Abstract interface for Gamma Exposure data."""

    @abstractmethod
    def get_gex(self, ticker: str) -> dict | None:
        """Get GEX data for a ticker.

        Expected return dict keys:
        - net_gex: float — Net Gamma Exposure
        - call_wall: float — Strike with max call GEX
        - put_wall: float — Strike with max put GEX
        - zero_gamma: float — Zero gamma level
        - gex_by_strike: list — Per-strike GEX values
        """
        ...

    @abstractmethod
    def provider_name(self) -> str:
        ...


class DarkPoolProvider(ABC):
    """Abstract interface for Dark Pool data."""

    @abstractmethod
    def get_dark_pool(self, ticker: str) -> dict | None:
        """Get Dark Pool activity for a ticker.

        Expected return dict keys:
        - dp_volume: int — Dark pool volume
        - total_volume: int — Total daily volume
        - dp_pct: float — DP as % of total
        - dp_buys: int — Buy-side DP volume
        - dp_sells: int — Sell-side DP volume
        - signal: str — "BULLISH", "BEARISH", or "NEUTRAL"
        """
        ...

    @abstractmethod
    def provider_name(self) -> str:
        ...


class UWGEXProvider(GEXProvider):
    """GEX data from Unusual Whales per-strike endpoint (primary source).

    Uses /api/stock/{ticker}/greek-exposure/strike which returns pre-computed
    dollar GEX (gamma × OI × 100 × spot²) per strike as call_gamma/put_gamma.
    """

    def __init__(self, uw_client):
        self._client = uw_client

    def get_gex(self, ticker: str) -> dict | None:
        data = self._client.get_greek_exposure_by_strike(ticker)
        if not data:
            return None
        return self._calculate_gex_from_strikes(data)

    def _calculate_gex_from_strikes(self, strikes: list[dict]) -> dict | None:
        """Calculate GEX metrics from UW per-strike data.

        UW provides pre-computed dollar GEX: call_gamma (positive),
        put_gamma (negative). All values are strings.
        """
        call_gex: dict[float, float] = {}
        put_gex: dict[float, float] = {}
        gex_by_strike: dict[float, float] = {}

        for entry in strikes:
            strike = _safe_float(entry.get("strike"))
            call_gamma = _safe_float(entry.get("call_gamma"))
            put_gamma = _safe_float(entry.get("put_gamma"))

            if strike == 0:
                continue

            if call_gamma != 0:
                call_gex[strike] = call_gamma
            if put_gamma != 0:
                put_gex[strike] = put_gamma

            net = call_gamma + put_gamma  # put_gamma is already negative
            if net != 0:
                gex_by_strike[strike] = net

        if not gex_by_strike:
            return None

        net_gex = sum(gex_by_strike.values())
        call_wall = max(call_gex, key=call_gex.get) if call_gex else 0
        put_wall = max(put_gex, key=lambda k: abs(put_gex[k])) if put_gex else 0
        zero_gamma = _find_zero_gamma(gex_by_strike)

        return {
            "net_gex": net_gex,
            "call_wall": call_wall,
            "put_wall": put_wall,
            "zero_gamma": zero_gamma,
            "gex_by_strike": [
                {"strike": s, "gex": g}
                for s, g in sorted(gex_by_strike.items())
            ],
            "source": "unusual_whales",
        }

    def provider_name(self) -> str:
        return "unusual_whales"


class PolygonGEXProvider(GEXProvider):
    """GEX data calculated from Polygon options chain (fallback)."""

    def __init__(self, polygon_client, max_dte: int = 35):
        self._client = polygon_client
        self._max_dte = max_dte

    def get_gex(self, ticker: str) -> dict | None:
        options = self._client.get_options_snapshot(ticker)
        if not options:
            return None
        return self._calculate_gex(ticker, options, max_dte=self._max_dte)

    def _calculate_gex(self, ticker: str, options: list[dict],
                       max_dte: int = 90) -> dict:
        """Calculate GEX from raw options chain data.

        GEX per strike = Gamma * OI * 100 * Spot^2 * 0.01
        Options beyond max_dte are excluded (front-month filter).
        If DTE filter leaves <5 contracts, all contracts are used as fallback.
        """
        from datetime import date as _date
        today = _date.today()

        # Pre-filter by DTE, with <5 contract fallback
        filtered = options
        if max_dte > 0:
            dte_filtered = []
            for opt in options:
                exp_str = opt.get("details", {}).get("expiration_date")
                if exp_str:
                    try:
                        exp_date = _date.fromisoformat(exp_str)
                        if (exp_date - today).days > max_dte:
                            continue
                    except ValueError:
                        pass  # Bad date format → include
                dte_filtered.append(opt)
            if len(dte_filtered) >= 5:
                filtered = dte_filtered
            # else: <5 contracts after DTE filter → use all

        gex_by_strike: dict[float, float] = {}
        call_gex: dict[float, float] = {}
        put_gex: dict[float, float] = {}

        for opt in filtered:
            details = opt.get("details", {})
            greeks = opt.get("greeks", {})
            day = opt.get("day", {})

            strike = details.get("strike_price", 0)
            gamma = greeks.get("gamma", 0)
            oi = opt.get("open_interest", day.get("open_interest", 0))
            spot = opt.get("underlying_asset", {}).get("price", 0)
            contract_type = details.get("contract_type", "").lower()

            if not all([strike, gamma, spot]):
                continue

            gex = gamma * oi * 100 * (spot ** 2) * 0.01

            if contract_type == "call":
                call_gex[strike] = call_gex.get(strike, 0) + gex
                gex_by_strike[strike] = gex_by_strike.get(strike, 0) + gex
            elif contract_type == "put":
                put_gex[strike] = put_gex.get(strike, 0) + gex
                gex_by_strike[strike] = gex_by_strike.get(strike, 0) - gex

        net_gex = sum(call_gex.values()) - sum(put_gex.values())
        call_wall = max(call_gex, key=call_gex.get) if call_gex else 0
        put_wall = max(put_gex, key=lambda k: abs(put_gex[k])) if put_gex else 0

        zero_gamma = _find_zero_gamma(gex_by_strike)

        return {
            "net_gex": net_gex,
            "call_wall": call_wall,
            "put_wall": put_wall,
            "zero_gamma": zero_gamma,
            "gex_by_strike": [
                {"strike": s, "gex": g}
                for s, g in sorted(gex_by_strike.items())
            ],
            "source": "polygon_calculated",
        }

    def provider_name(self) -> str:
        return "polygon"


class UWDarkPoolProvider(DarkPoolProvider):
    """Dark Pool data from Unusual Whales (primary source)."""

    def __init__(self, uw_client):
        self._client = uw_client

    def get_dark_pool(self, ticker: str) -> dict | None:
        data = self._client.get_dark_pool(ticker)
        if not data:
            return None
        return _aggregate_dp_records(data)

    def provider_name(self) -> str:
        return "unusual_whales"


class UWBatchDarkPoolProvider(DarkPoolProvider):
    """Dark Pool using /api/darkpool/recent batch prefetch.

    Fetches all recent DP trades in ~15 paginated calls,
    groups by ticker, serves from in-memory cache.
    Replaces ~882 per-ticker API calls.
    """

    def __init__(self, uw_client, logger: EventLogger | None = None,
                 max_pages: int = 15, page_delay: float = 0.5):
        self._client = uw_client
        self._logger = logger
        self._max_pages = max_pages
        self._page_delay = page_delay
        self._cache: dict[str, list[dict]] = {}
        self._prefetched = False

    def prefetch(self, date: str | None = None) -> None:
        """Fetch all recent DP trades and group by ticker."""
        self._cache.clear()
        older_than = None

        for page in range(self._max_pages):
            records = self._client.get_dark_pool_recent(
                limit=200, date=date, older_than=older_than,
            )
            if not records:
                break

            for record in records:
                ticker = record.get("ticker", "")
                if ticker:
                    self._cache.setdefault(ticker, []).append(record)

            older_than = records[-1].get("executed_at")
            if not older_than:
                break

            if page < self._max_pages - 1 and self._page_delay > 0:
                time.sleep(self._page_delay)

        self._prefetched = True
        if self._logger:
            self._logger.log(
                EventType.DATA_PREFETCH, Severity.INFO, phase=4,
                message=f"Dark Pool batch: {sum(len(v) for v in self._cache.values())} "
                        f"trades across {len(self._cache)} tickers",
            )

    def get_dark_pool(self, ticker: str) -> dict | None:
        if not self._prefetched:
            self.prefetch()
        records = self._cache.get(ticker)
        if not records:
            return None
        return _aggregate_dp_records(records)

    def provider_name(self) -> str:
        return "unusual_whales_batch"


class FallbackGEXProvider(GEXProvider):
    """GEX provider with automatic fallback: UW → Polygon."""

    def __init__(self, primary: GEXProvider, fallback: GEXProvider,
                 logger: EventLogger | None = None):
        self._primary = primary
        self._fallback = fallback
        self._logger = logger

    def get_gex(self, ticker: str) -> dict | None:
        result = self._primary.get_gex(ticker)
        if result is not None:
            return result

        if self._logger:
            self._logger.api_fallback(
                self._primary.provider_name(),
                self._fallback.provider_name(),
                f"GEX data unavailable for {ticker}",
            )
        fallback_result = self._fallback.get_gex(ticker)
        if fallback_result is None and self._logger:
            self._logger.log(
                EventType.API_ERROR, Severity.DEBUG, phase=5,
                message=(
                    f"No GEX data for {ticker} from either "
                    f"{self._primary.provider_name()} or "
                    f"{self._fallback.provider_name()} — will default to POSITIVE regime"
                ),
                data={"ticker": ticker},
            )
        return fallback_result

    def provider_name(self) -> str:
        return f"{self._primary.provider_name()}+{self._fallback.provider_name()}"


class FallbackDarkPoolProvider(DarkPoolProvider):
    """Dark Pool provider with automatic fallback: batch → per-ticker."""

    def __init__(self, primary: DarkPoolProvider,
                 fallback: DarkPoolProvider | None = None,
                 logger: EventLogger | None = None):
        self._primary = primary
        self._fallback = fallback
        self._logger = logger

    def get_dark_pool(self, ticker: str) -> dict | None:
        result = self._primary.get_dark_pool(ticker)
        if result is not None:
            return result

        if self._fallback is not None:
            result = self._fallback.get_dark_pool(ticker)
            if result is not None:
                return result

        if self._logger:
            self._logger.log(
                EventType.API_FALLBACK, Severity.DEBUG,
                message=(
                    f"Fallback: {self._primary.provider_name()} → none "
                    f"(Dark Pool data unavailable for {ticker} — no fallback)"
                ),
                data={
                    "primary": self._primary.provider_name(),
                    "fallback": "none",
                    "reason": f"Dark Pool data unavailable for {ticker} — no fallback",
                },
            )
        return None

    def provider_name(self) -> str:
        return self._primary.provider_name()


def _aggregate_dp_records(records: list[dict]) -> dict:
    """Aggregate raw DP trade records into signal dict.

    Classifies buy/sell by NBBO midpoint comparison.
    Reused by UWDarkPoolProvider and UWBatchDarkPoolProvider.

    Uses the 'volume' field from DP records (total stock day volume)
    to compute dp_pct = dp_volume / total_volume * 100.
    """
    import math
    from collections import Counter

    dp_buys = 0
    dp_sells = 0
    dp_volume = 0
    total_volume = 0
    block_trade_count = 0
    venue_counts: Counter = Counter()

    for record in records:
        size = _safe_int(record.get("size", 0))
        dp_volume += size

        # Each DP record carries the stock's total day volume
        vol = _safe_int(record.get("volume", 0))
        if vol > total_volume:
            total_volume = vol

        price = _safe_float(record.get("price", 0))

        # Block trade detection ($500K+ notional)
        if size * price > 500_000:
            block_trade_count += 1

        # Venue tracking for Shannon entropy
        mc = record.get("market_center", "UNKNOWN")
        venue_counts[mc] += size

        nbbo_ask = _safe_float(record.get("nbbo_ask", 0))
        nbbo_bid = _safe_float(record.get("nbbo_bid", 0))

        if nbbo_ask > 0 and nbbo_bid > 0 and price > 0:
            midpoint = (nbbo_ask + nbbo_bid) / 2
            if price >= midpoint:
                dp_buys += size
            else:
                dp_sells += size

    if dp_buys > dp_sells:
        signal = "BULLISH"
    elif dp_sells > dp_buys:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"

    dp_pct = round((dp_volume / total_volume) * 100, 2) if total_volume > 0 else 0.0

    # Venue entropy: Shannon entropy over volume-weighted venue distribution
    total_venue_vol = sum(venue_counts.values())
    if total_venue_vol > 0:
        probs = [v / total_venue_vol for v in venue_counts.values()]
        venue_entropy = -sum(p * math.log(p) for p in probs if p > 0)
    else:
        venue_entropy = 0.0

    return {
        "dp_volume": dp_volume,
        "total_volume": total_volume,
        "dp_pct": dp_pct,
        "dp_buys": dp_buys,
        "dp_sells": dp_sells,
        "signal": signal,
        "source": "unusual_whales",
        "block_trade_count": block_trade_count,
        "venue_entropy": venue_entropy,
    }


def _find_zero_gamma(gex_by_strike: dict[float, float]) -> float:
    """Find the price level where cumulative GEX crosses zero.

    Iterates strikes in sorted order accumulating GEX values.
    Uses linear interpolation between bracketing strikes for precision.
    """
    if not gex_by_strike:
        return 0.0

    cumulative = 0.0
    prev_strike = 0.0
    for strike in sorted(gex_by_strike):
        prev_cum = cumulative
        cumulative += gex_by_strike[strike]
        if prev_cum != 0 and ((prev_cum < 0 and cumulative >= 0) or (prev_cum > 0 and cumulative <= 0)):
            # Linear interpolation between prev_strike and strike
            denom = cumulative - prev_cum
            if denom != 0 and prev_strike > 0:
                zero = prev_strike + (strike - prev_strike) * (-prev_cum / denom)
                return round(zero, 2)
            return strike
        prev_strike = strike
    # No zero crossing found → no meaningful zero gamma level
    return 0.0


def _safe_float(val: Any) -> float:
    """Safely convert to float, defaulting to 0.0."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(val: Any) -> int:
    """Safely convert to int, defaulting to 0."""
    if val is None:
        return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0
