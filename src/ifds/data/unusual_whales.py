"""Unusual Whales API client.

Provides: Dark Pool data, GEX/Greeks data, Options Flow.
Primary source for institutional flow data. Falls back to Polygon if unavailable.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from typing import Any, TYPE_CHECKING

from ifds.data.base import BaseAPIClient
from ifds.models.market import APIHealthResult, APIStatus

if TYPE_CHECKING:
    from ifds.data.cache import FileCache


class UnusualWhalesClient(BaseAPIClient):
    """Client for Unusual Whales REST API.

    Endpoints used:
    - /api/darkpool/{ticker} — Dark Pool transactions
    - /api/stock/{ticker}/greek-exposure — Aggregate GEX and Greeks
    - /api/stock/{ticker}/greek-exposure/strike — Per-strike GEX (primary)
    """

    HEALTH_CHECK_ENDPOINT = "/api/darkpool/SPY"

    def __init__(self, api_key: str | None = None, timeout: int = 10,
                 max_retries: int = 3, cache: FileCache | None = None,
                 circuit_breaker=None):
        super().__init__(
            base_url="https://api.unusualwhales.com",
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            provider_name="unusual_whales",
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

    def check_health(self) -> APIHealthResult:
        """Check UW API connectivity. Non-critical (has Polygon fallback)."""
        if not self._api_key:
            return APIHealthResult(
                provider=self._provider,
                endpoint=self.HEALTH_CHECK_ENDPOINT,
                status=APIStatus.SKIPPED,
                error="No API key configured",
                is_critical=False,
            )
        return self.health_check(self.HEALTH_CHECK_ENDPOINT, is_critical=False)

    def get_dark_pool(self, ticker: str) -> list[dict] | None:
        """Get Dark Pool transactions for a ticker.

        Returns list of dark pool trade records.
        """
        if not self._api_key:
            return None
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("uw", "darkpool", yesterday, ticker)
            if cached is not None:
                return cached

        endpoint = f"/api/darkpool/{ticker}"
        data = self._get(endpoint, params={"limit": 200},
                         headers=self._auth_headers())
        result = None
        if data and isinstance(data, dict) and data.get("data"):
            result = data["data"]
        elif data and isinstance(data, list):
            result = data

        # Debug: log response shape when data arrived but result is None
        if data is not None and result is None:
            snippet = str(data)[:200]
            print(f"  [DEBUG] DP {ticker}: unexpected response shape: {snippet}",
                  file=sys.stderr)

        if result and self._cache:
            self._cache.put("uw", "darkpool", yesterday, ticker, result)
        return result

    def get_greeks(self, ticker: str) -> dict | None:
        """Get Greek Exposure data for a ticker.

        Returns dict with call_gamma, put_gamma, call_delta, put_delta, etc.
        """
        if not self._api_key:
            return None
        endpoint = f"/api/stock/{ticker}/greek-exposure"
        data = self._get(endpoint, headers=self._auth_headers())
        if data and isinstance(data, dict):
            result = data.get("data", data)
            # UW API wraps response in list — unwrap first element
            if isinstance(result, list):
                return result[0] if result else None
            return result
        return None

    def get_dark_pool_recent(self, limit: int = 200,
                             date: str | None = None,
                             older_than: str | None = None) -> list[dict] | None:
        """Get recent dark pool trades across all tickers.

        Used for batch prefetch — replaces per-ticker calls.
        Params: limit (max 200), date (market date), older_than (pagination cursor).
        """
        if not self._api_key:
            return None
        params: dict = {"limit": min(limit, 200)}
        if date:
            params["date"] = date
        if older_than:
            params["older_than"] = older_than
        endpoint = "/api/darkpool/recent"
        data = self._get(endpoint, params=params, headers=self._auth_headers())
        if data and isinstance(data, dict) and data.get("data"):
            return data["data"]
        if data and isinstance(data, list):
            return data
        if data is not None:
            snippet = str(data)[:200]
            print(f"  [DEBUG] DP recent: unexpected response shape: {snippet}",
                  file=sys.stderr)
        return None

    def get_greek_exposure_by_strike(self, ticker: str) -> list[dict] | None:
        """Get Greek Exposure grouped by strike price.

        Returns list of per-strike GEX dicts with call_gamma, put_gamma, strike.
        All values are strings — caller must convert to float.
        """
        if not self._api_key:
            return None
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("uw", "greek-exposure-strike", yesterday, ticker)
            if cached is not None:
                return cached

        endpoint = f"/api/stock/{ticker}/greek-exposure/strike"
        data = self._get(endpoint, headers=self._auth_headers())
        result = None
        if data and isinstance(data, dict) and data.get("data"):
            result = data["data"]
        elif data and isinstance(data, list):
            result = data
        if result and self._cache:
            self._cache.put("uw", "greek-exposure-strike", yesterday, ticker, result)
        return result
