"""Async API clients for Polygon, FMP, Unusual Whales, and FRED.

Thin wrappers over AsyncBaseAPIClient — mirrors the sync clients
but uses aiohttp + semaphore for concurrent rate-limited requests.
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any, TYPE_CHECKING

from ifds.data.async_base import AsyncBaseAPIClient
from ifds.models.market import APIHealthResult, APIStatus

if TYPE_CHECKING:
    from ifds.data.cache import FileCache


class AsyncPolygonClient(AsyncBaseAPIClient):
    """Async client for Polygon.io REST API."""

    def __init__(self, api_key: str, timeout: int = 10, max_retries: int = 3,
                 semaphore: asyncio.Semaphore | None = None,
                 cache: FileCache | None = None, circuit_breaker=None):
        super().__init__(
            base_url="https://api.polygon.io",
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            provider_name="polygon",
            semaphore=semaphore,
            circuit_breaker=circuit_breaker,
        )
        self._cache = cache

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _health_check_params(self) -> dict[str, Any]:
        return {"adjusted": "true"}

    async def check_health(self) -> APIHealthResult:
        yesterday = (date.today() - timedelta(days=3)).isoformat()
        endpoint = f"/v2/aggs/grouped/locale/us/market/stocks/{yesterday}"
        return await self.health_check(endpoint, is_critical=True)

    async def get_aggregates(self, ticker: str, from_date: str, to_date: str,
                             timespan: str = "day", multiplier: int = 1) -> list[dict] | None:
        cache_key = f"{from_date}_{to_date}"
        if self._cache:
            cached = self._cache.get("polygon", "aggregates", cache_key, ticker)
            if cached is not None:
                return cached

        endpoint = f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        data = await self._get(endpoint, params={"adjusted": "true", "sort": "asc"},
                               headers=self._auth_headers())
        if data and data.get("results"):
            result = data["results"]
            if self._cache:
                self._cache.put("polygon", "aggregates", cache_key, ticker, result)
            return result
        return None

    async def get_options_snapshot(self, underlying: str) -> list[dict] | None:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("polygon", "options-snapshot", yesterday, underlying)
            if cached is not None:
                return cached

        endpoint = f"/v3/snapshot/options/{underlying}"
        data = await self._get(endpoint, params={"limit": 250},
                               headers=self._auth_headers())
        if data and data.get("results"):
            result = data["results"]
            if self._cache:
                self._cache.put("polygon", "options-snapshot", yesterday, underlying, result)
            return result
        return None

    async def get_grouped_daily(self, date_str: str) -> list[dict] | None:
        if self._cache:
            cached = self._cache.get("polygon", "grouped_daily", date_str, "ALL")
            if cached is not None:
                return cached

        endpoint = f"/v2/aggs/grouped/locale/us/market/stocks/{date_str}"
        data = await self._get(endpoint, params={"adjusted": "true"},
                               headers=self._auth_headers())
        if data and data.get("results"):
            result = data["results"]
            if self._cache:
                self._cache.put("polygon", "grouped_daily", date_str, "ALL", result)
            return result
        return None


class AsyncFMPClient(AsyncBaseAPIClient):
    """Async client for FMP REST API."""

    def __init__(self, api_key: str, timeout: int = 10, max_retries: int = 3,
                 semaphore: asyncio.Semaphore | None = None,
                 cache: FileCache | None = None, circuit_breaker=None):
        super().__init__(
            base_url="https://financialmodelingprep.com",
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            provider_name="fmp",
            semaphore=semaphore,
            circuit_breaker=circuit_breaker,
        )
        self._cache = cache

    def _health_check_params(self) -> dict[str, Any]:
        return {"apikey": self._api_key, "limit": 1, "marketCapMoreThan": 1_000_000_000_000}

    async def check_health(self) -> APIHealthResult:
        return await self.health_check("/stable/company-screener", is_critical=True)

    async def get_financial_growth(self, ticker: str) -> dict | None:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "financial-growth", yesterday, ticker)
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "symbol": ticker, "limit": 1}
        result = await self._get("/stable/financial-growth", params=params)
        if result and isinstance(result, list) and len(result) > 0:
            if self._cache:
                self._cache.put("fmp", "financial-growth", yesterday, ticker, result[0])
            return result[0]
        return None

    async def get_key_metrics(self, ticker: str) -> dict | None:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "key-metrics", yesterday, ticker)
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "symbol": ticker}
        result = await self._get("/stable/key-metrics", params=params)
        if result and isinstance(result, list) and len(result) > 0:
            if self._cache:
                self._cache.put("fmp", "key-metrics", yesterday, ticker, result[0])
            return result[0]
        return None

    async def get_insider_trading(self, ticker: str) -> list[dict] | None:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "insider-trading", yesterday, ticker)
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "symbol": ticker, "limit": 50}
        result = await self._get("/stable/insider-trading/search", params=params)
        if result and self._cache:
            self._cache.put("fmp", "insider-trading", yesterday, ticker, result)
        return result

    async def get_institutional_ownership(self, ticker: str) -> list[dict] | None:
        """Get institutional ownership data (most recent 2 quarters)."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "institutional-ownership", yesterday, ticker)
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "symbol": ticker, "limit": 2}
        result = await self._get("/stable/institutional-ownership/latest", params=params)
        if result and self._cache:
            self._cache.put("fmp", "institutional-ownership", yesterday, ticker, result)
        return result

    async def get_etf_holdings(self, etf_symbol: str) -> list[dict] | None:
        """Get ETF constituent holdings."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "etf-holdings", yesterday, etf_symbol)
            if cached is not None:
                return cached
        params = {"apikey": self._api_key, "symbol": etf_symbol}
        result = await self._get("/stable/etf/holdings", params=params)
        if result and self._cache:
            self._cache.put("fmp", "etf-holdings", yesterday, etf_symbol, result)
        return result


class AsyncUWClient(AsyncBaseAPIClient):
    """Async client for Unusual Whales REST API."""

    def __init__(self, api_key: str | None = None, timeout: int = 10,
                 max_retries: int = 3,
                 semaphore: asyncio.Semaphore | None = None,
                 cache: FileCache | None = None, circuit_breaker=None):
        super().__init__(
            base_url="https://api.unusualwhales.com",
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            provider_name="unusual_whales",
            semaphore=semaphore,
            circuit_breaker=circuit_breaker,
        )
        self._cache = cache

    def _auth_headers(self) -> dict[str, str]:
        if self._api_key:
            return {
                "Authorization": f"Bearer {self._api_key}",
                "User-Agent": "PythonClient",
            }
        return {}

    async def check_health(self) -> APIHealthResult:
        if not self._api_key:
            return APIHealthResult(
                provider=self._provider,
                endpoint="/api/darkpool/SPY",
                status=APIStatus.SKIPPED,
                error="No API key configured",
                is_critical=False,
            )
        return await self.health_check("/api/darkpool/SPY", is_critical=False)

    async def get_dark_pool(self, ticker: str) -> list[dict] | None:
        if not self._api_key:
            return None
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("uw", "darkpool", yesterday, ticker)
            if cached is not None:
                return cached

        endpoint = f"/api/darkpool/{ticker}"
        data = await self._get(endpoint, params={"limit": 200},
                               headers=self._auth_headers())
        result = None
        if data and isinstance(data, dict) and data.get("data"):
            result = data["data"]
        elif data and isinstance(data, list):
            result = data
        if result and self._cache:
            self._cache.put("uw", "darkpool", yesterday, ticker, result)
        return result

    async def get_dark_pool_recent(self, limit: int = 200,
                                    date: str | None = None,
                                    older_than: str | None = None) -> list[dict] | None:
        """Get recent dark pool trades across all tickers (batch prefetch)."""
        if not self._api_key:
            return None
        params: dict = {"limit": min(limit, 200)}
        if date:
            params["date"] = date
        if older_than:
            params["older_than"] = older_than
        endpoint = "/api/darkpool/recent"
        data = await self._get(endpoint, params=params, headers=self._auth_headers())
        if data and isinstance(data, dict) and data.get("data"):
            return data["data"]
        if data and isinstance(data, list):
            return data
        return None

    async def get_greeks(self, ticker: str) -> dict | None:
        if not self._api_key:
            return None
        endpoint = f"/api/stock/{ticker}/greek-exposure"
        data = await self._get(endpoint, headers=self._auth_headers())
        if data and isinstance(data, dict):
            result = data.get("data", data)
            if isinstance(result, list):
                return result[0] if result else None
            return result
        return None

    async def get_greek_exposure_by_strike(self, ticker: str) -> list[dict] | None:
        """Get Greek Exposure grouped by strike price."""
        if not self._api_key:
            return None
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("uw", "greek-exposure-strike", yesterday, ticker)
            if cached is not None:
                return cached

        endpoint = f"/api/stock/{ticker}/greek-exposure/strike"
        data = await self._get(endpoint, headers=self._auth_headers())
        result = None
        if data and isinstance(data, dict) and data.get("data"):
            result = data["data"]
        elif data and isinstance(data, list):
            result = data
        if result and self._cache:
            self._cache.put("uw", "greek-exposure-strike", yesterday, ticker, result)
        return result


class AsyncFREDClient(AsyncBaseAPIClient):
    """Async client for FRED REST API."""

    VIX_SERIES = "VIXCLS"
    TNX_SERIES = "DGS10"

    def __init__(self, api_key: str, timeout: int = 10, max_retries: int = 3,
                 semaphore: asyncio.Semaphore | None = None,
                 cache: FileCache | None = None, circuit_breaker=None):
        super().__init__(
            base_url="https://api.stlouisfed.org",
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            provider_name="fred",
            semaphore=semaphore,
            circuit_breaker=circuit_breaker,
        )
        self._cache = cache

    def _health_check_params(self) -> dict[str, Any]:
        return {
            "series_id": self.VIX_SERIES,
            "sort_order": "desc",
            "limit": 1,
            "file_type": "json",
            "api_key": self._api_key,
        }

    async def check_health(self) -> APIHealthResult:
        return await self.health_check("/fred/series/observations", is_critical=True)

    async def get_series(self, series_id: str, limit: int = 30) -> list[dict] | None:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fred", "series", yesterday, series_id)
            if cached is not None:
                return cached

        params = {
            "series_id": series_id,
            "sort_order": "desc",
            "limit": limit,
            "file_type": "json",
            "api_key": self._api_key,
        }
        data = await self._get("/fred/series/observations", params=params)
        if data and data.get("observations"):
            result = data["observations"]
            if self._cache:
                self._cache.put("fred", "series", yesterday, series_id, result)
            return result
        return None

    async def get_vix(self, limit: int = 30) -> list[dict] | None:
        return await self.get_series(self.VIX_SERIES, limit=limit)

    async def get_tnx(self, limit: int = 30) -> list[dict] | None:
        return await self.get_series(self.TNX_SERIES, limit=limit)
