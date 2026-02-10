"""Polygon.io API client.

Provides: OHLCV price data, options chain snapshots.
Used as primary source for price/volume and fallback for GEX/options.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, TYPE_CHECKING

from ifds.data.base import BaseAPIClient
from ifds.models.market import APIHealthResult

if TYPE_CHECKING:
    from ifds.data.cache import FileCache


class PolygonClient(BaseAPIClient):
    """Client for Polygon.io REST API.

    Endpoints used:
    - /v2/aggs/ticker/{ticker}/range — OHLCV aggregates
    - /v3/snapshot/options/{underlyingAsset} — Options chain snapshot
    - /v2/aggs/grouped/locale/us/market/stocks/{date} — Grouped daily bars
    """

    HEALTH_CHECK_ENDPOINT = "/v2/aggs/grouped/locale/us/market/stocks"

    def __init__(self, api_key: str, timeout: int = 10, max_retries: int = 3,
                 cache: FileCache | None = None, circuit_breaker=None):
        super().__init__(
            base_url="https://api.polygon.io",
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            provider_name="polygon",
            circuit_breaker=circuit_breaker,
        )
        self._cache = cache

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _health_check_params(self) -> dict[str, Any]:
        return {"adjusted": "true"}

    def check_health(self) -> APIHealthResult:
        """Check Polygon API connectivity."""
        yesterday = (date.today() - timedelta(days=3)).isoformat()
        endpoint = f"{self.HEALTH_CHECK_ENDPOINT}/{yesterday}"
        return self.health_check(endpoint, is_critical=True)

    def get_aggregates(self, ticker: str, from_date: str, to_date: str,
                       timespan: str = "day", multiplier: int = 1) -> list[dict] | None:
        """Get OHLCV aggregates for a ticker.

        Args:
            ticker: Stock ticker symbol.
            from_date: Start date (YYYY-MM-DD).
            to_date: End date (YYYY-MM-DD).
            timespan: day, hour, minute, etc.
            multiplier: Size of timespan multiplier.

        Returns:
            List of bar dicts or None on failure.
        """
        cache_key = f"{from_date}_{to_date}"
        if self._cache:
            cached = self._cache.get("polygon", "aggregates", cache_key, ticker)
            if cached is not None:
                return cached

        endpoint = f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        data = self._get(endpoint, params={"adjusted": "true", "sort": "asc"},
                         headers=self._auth_headers())
        if data and data.get("results"):
            result = data["results"]
            if self._cache:
                self._cache.put("polygon", "aggregates", cache_key, ticker, result)
            return result
        return None

    def get_options_snapshot(self, underlying: str) -> list[dict] | None:
        """Get options chain snapshot for a ticker.

        Returns list of option contract details with greeks.
        Cached by yesterday's date — Phase 5 GEX reuses cached data.
        """
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("polygon", "options-snapshot", yesterday, underlying)
            if cached is not None:
                return cached

        endpoint = f"/v3/snapshot/options/{underlying}"
        data = self._get(endpoint, params={"limit": 250},
                         headers=self._auth_headers())
        if data and data.get("results"):
            result = data["results"]
            if self._cache:
                self._cache.put("polygon", "options-snapshot", yesterday, underlying, result)
            return result
        return None

    def get_grouped_daily(self, date_str: str) -> list[dict] | None:
        """Get grouped daily bars for all tickers on a given date.

        Used for BMI calculation (volume spike detection across universe).

        Args:
            date_str: Date in YYYY-MM-DD format.

        Returns:
            List of bar dicts (T=ticker, o, h, l, c, v, vw, n) or None.
        """
        if self._cache:
            cached = self._cache.get("polygon", "grouped_daily", date_str, "ALL")
            if cached is not None:
                return cached

        endpoint = f"{self.HEALTH_CHECK_ENDPOINT}/{date_str}"
        data = self._get(endpoint, params={"adjusted": "true"},
                         headers=self._auth_headers())
        if data and data.get("results"):
            result = data["results"]
            if self._cache:
                self._cache.put("polygon", "grouped_daily", date_str, "ALL", result)
            return result
        return None

    def get_vix(self, days_back: int = 10) -> float | None:
        """Get latest VIX value from Polygon I:VIX index.

        Uses the aggregates endpoint with the I:VIX ticker symbol.
        Returns the most recent close value with sanity check (5-100 range).

        Args:
            days_back: Number of calendar days to look back for data.

        Returns:
            VIX float value, or None if unavailable or out of range.
        """
        today = date.today()
        from_date = (today - timedelta(days=days_back)).isoformat()
        to_date = today.isoformat()

        bars = self.get_aggregates("I:VIX", from_date, to_date)
        if not bars:
            return None

        vix_value = bars[-1].get("c")
        if vix_value is None:
            return None

        vix_value = float(vix_value)

        # Sanity check: VIX should be in reasonable range
        # Historical: ~9 (2017 low) to ~82 (2020 COVID spike)
        if not (5.0 <= vix_value <= 100.0):
            return None

        return vix_value

    def check_options_health(self) -> APIHealthResult:
        """Check Polygon Options API connectivity."""
        return self.health_check(
            "/v3/snapshot/options/SPY",
            is_critical=True,
        )
