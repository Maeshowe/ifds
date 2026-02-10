"""Async data provider adapters with automatic fallback.

Async version of adapters.py — reuses pure-computation functions
(_safe_float, _safe_int, GEX calculation) from the sync module.
"""

import asyncio

from ifds.data.adapters import (
    _safe_float, _safe_int, _find_zero_gamma, _aggregate_dp_records,
)
from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity


def _calculate_uw_gex(strikes: list[dict]) -> dict | None:
    """Calculate GEX metrics from UW per-strike data (pure computation).

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


class AsyncGEXProvider:
    """Abstract async interface for Gamma Exposure data."""

    async def get_gex(self, ticker: str) -> dict | None:
        raise NotImplementedError

    def provider_name(self) -> str:
        raise NotImplementedError


class AsyncDarkPoolProvider:
    """Abstract async interface for Dark Pool data."""

    async def get_dark_pool(self, ticker: str) -> dict | None:
        raise NotImplementedError

    def provider_name(self) -> str:
        raise NotImplementedError


class AsyncUWGEXProvider(AsyncGEXProvider):
    """Async GEX from UW per-strike endpoint (primary source)."""

    def __init__(self, uw_client):
        self._client = uw_client

    async def get_gex(self, ticker: str) -> dict | None:
        data = await self._client.get_greek_exposure_by_strike(ticker)
        if not data:
            return None
        return _calculate_uw_gex(data)

    def provider_name(self) -> str:
        return "unusual_whales"


class AsyncPolygonGEXProvider(AsyncGEXProvider):
    """Async GEX calculated from Polygon options chain."""

    def __init__(self, polygon_client, max_dte: int = 35):
        self._client = polygon_client
        self._max_dte = max_dte

    async def get_gex(self, ticker: str) -> dict | None:
        options = await self._client.get_options_snapshot(ticker)
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


class AsyncUWDarkPoolProvider(AsyncDarkPoolProvider):
    """Async Dark Pool data from Unusual Whales."""

    def __init__(self, uw_client):
        self._client = uw_client

    async def get_dark_pool(self, ticker: str) -> dict | None:
        data = await self._client.get_dark_pool(ticker)
        if not data:
            return None
        return _aggregate_dp_records(data)

    def provider_name(self) -> str:
        return "unusual_whales"


class AsyncUWBatchDarkPoolProvider(AsyncDarkPoolProvider):
    """Async Dark Pool batch prefetch via /api/darkpool/recent."""

    def __init__(self, uw_client, logger: EventLogger | None = None,
                 max_pages: int = 15, page_delay: float = 0.3):
        self._client = uw_client
        self._logger = logger
        self._max_pages = max_pages
        self._page_delay = page_delay
        self._cache: dict[str, list[dict]] = {}
        self._prefetched = False

    async def prefetch(self, date: str | None = None) -> None:
        """Fetch all recent DP trades and group by ticker."""
        self._cache.clear()
        older_than = None

        for page in range(self._max_pages):
            records = await self._client.get_dark_pool_recent(
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
                await asyncio.sleep(self._page_delay)

        self._prefetched = True
        if self._logger:
            self._logger.log(
                EventType.DATA_PREFETCH, Severity.INFO, phase=4,
                message=f"Dark Pool batch: {sum(len(v) for v in self._cache.values())} "
                        f"trades across {len(self._cache)} tickers",
            )

    async def get_dark_pool(self, ticker: str) -> dict | None:
        if not self._prefetched:
            await self.prefetch()
        records = self._cache.get(ticker)
        if not records:
            return None
        return _aggregate_dp_records(records)

    def provider_name(self) -> str:
        return "unusual_whales_batch"


class AsyncFallbackGEXProvider(AsyncGEXProvider):
    """Async GEX with automatic fallback: UW → Polygon."""

    def __init__(self, primary: AsyncGEXProvider, fallback: AsyncGEXProvider,
                 logger: EventLogger | None = None):
        self._primary = primary
        self._fallback = fallback
        self._logger = logger

    async def get_gex(self, ticker: str) -> dict | None:
        result = await self._primary.get_gex(ticker)
        if result is not None:
            return result

        if self._logger:
            self._logger.api_fallback(
                self._primary.provider_name(),
                self._fallback.provider_name(),
                f"GEX data unavailable for {ticker}",
            )
        fallback_result = await self._fallback.get_gex(ticker)
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


class AsyncFallbackDarkPoolProvider(AsyncDarkPoolProvider):
    """Async Dark Pool with fallback: batch → per-ticker."""

    def __init__(self, primary: AsyncDarkPoolProvider,
                 fallback: AsyncDarkPoolProvider | None = None,
                 logger: EventLogger | None = None):
        self._primary = primary
        self._fallback = fallback
        self._logger = logger

    async def get_dark_pool(self, ticker: str) -> dict | None:
        result = await self._primary.get_dark_pool(ticker)
        if result is not None:
            return result

        if self._fallback is not None:
            result = await self._fallback.get_dark_pool(ticker)
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
