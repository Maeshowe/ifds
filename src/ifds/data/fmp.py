"""Financial Modeling Prep (FMP) API client.

Provides: Company screener (fundamentals), earnings calendar, insider trading.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from typing import Any, TYPE_CHECKING
from urllib.parse import urlencode

from ifds.data.base import BaseAPIClient
from ifds.models.market import APIHealthResult

if TYPE_CHECKING:
    from ifds.data.cache import FileCache


class FMPClient(BaseAPIClient):
    """Client for FMP REST API.

    Endpoints used:
    - /stable/company-screener — Fundamental screening
    - /stable/earnings-calendar — Earnings dates
    - /stable/insider-trading/search — Insider transactions
    - /stable/key-metrics — Key financial metrics (TTM)
    - /stable/financial-growth — Revenue/EPS growth rates
    """

    HEALTH_CHECK_ENDPOINT = "/stable/company-screener"

    def __init__(self, api_key: str, timeout: int = 10, max_retries: int = 3,
                 cache: FileCache | None = None, circuit_breaker=None):
        super().__init__(
            base_url="https://financialmodelingprep.com",
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            provider_name="fmp",
            circuit_breaker=circuit_breaker,
        )
        self._cache = cache

    def _health_check_params(self) -> dict[str, Any]:
        return {"apikey": self._api_key, "limit": 1, "marketCapMoreThan": 1_000_000_000_000}

    def check_health(self) -> APIHealthResult:
        """Check FMP API connectivity."""
        return self.health_check(self.HEALTH_CHECK_ENDPOINT, is_critical=True)

    def screener(self, params: dict[str, Any]) -> list[dict] | None:
        """Run the company screener with given filters.

        Args:
            params: Screener filter parameters (marketCapMoreThan, etc.)

        Returns:
            List of company dicts matching filters, or None on failure.
        """
        query = {"apikey": self._api_key, **params}
        # Debug: log the full request URL (redact API key)
        debug_params = {k: v for k, v in query.items() if k != "apikey"}
        url = f"{self._base_url}{self.HEALTH_CHECK_ENDPOINT}?{urlencode(debug_params)}"
        print(f"  [FMP SCREENER] {url}", file=sys.stderr)
        return self._get(self.HEALTH_CHECK_ENDPOINT, params=query,
                         headers=self._auth_headers())

    def get_earnings_calendar(self, from_date: str, to_date: str) -> list[dict] | None:
        """Get earnings calendar for a date range.

        Args:
            from_date: Start date (YYYY-MM-DD).
            to_date: End date (YYYY-MM-DD).
        """
        cache_date = f"{from_date}_{to_date}"
        if self._cache:
            cached = self._cache.get("fmp", "earnings-calendar", cache_date, "ALL")
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "from": from_date, "to": to_date}
        result = self._get("/stable/earnings-calendar", params=params,
                           headers=self._auth_headers())
        if result and self._cache:
            self._cache.put("fmp", "earnings-calendar", cache_date, "ALL", result)
        return result

    def get_insider_trading(self, ticker: str) -> list[dict] | None:
        """Get insider trading transactions for a ticker."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "insider-trading", yesterday, ticker)
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "symbol": ticker, "limit": 50}
        result = self._get("/stable/insider-trading/search", params=params,
                           headers=self._auth_headers())
        if result and self._cache:
            self._cache.put("fmp", "insider-trading", yesterday, ticker, result)
        return result

    def get_key_metrics(self, ticker: str) -> dict | None:
        """Get trailing twelve months key financial metrics.

        Returns dict with: roe, netIncomeMargin, debtToEquity, interestCoverage, etc.
        """
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "key-metrics", yesterday, ticker)
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "symbol": ticker}
        result = self._get("/stable/key-metrics", params=params,
                           headers=self._auth_headers())
        if result and isinstance(result, list) and len(result) > 0:
            if self._cache:
                self._cache.put("fmp", "key-metrics", yesterday, ticker, result[0])
            return result[0]
        return None

    def get_sector_mapping(self, limit: int = 3000) -> dict[str, str]:
        """Get ticker→sector mapping from FMP screener.

        Single API call. Returns {ticker: fmp_sector_name}.
        Cached via FileCache if available.
        """
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "sector-mapping", yesterday, "ALL")
            if cached is not None:
                return cached

        params = {
            "marketCapMoreThan": 500_000_000,
            "volumeMoreThan": 100_000,
            "limit": limit,
        }
        result = self.screener(params)
        if not result:
            return {}

        mapping = {r["symbol"]: r["sector"] for r in result
                   if r.get("symbol") and r.get("sector")}

        if mapping and self._cache:
            self._cache.put("fmp", "sector-mapping", yesterday, "ALL", mapping)
        return mapping

    def get_institutional_ownership(self, ticker: str) -> list[dict] | None:
        """Get institutional ownership data (most recent 2 quarters)."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "institutional-ownership", yesterday, ticker)
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "symbol": ticker, "limit": 2}
        result = self._get("/stable/institutional-ownership/latest", params=params,
                           headers=self._auth_headers())
        if result and self._cache:
            self._cache.put("fmp", "institutional-ownership", yesterday, ticker, result)
        return result

    def get_financial_growth(self, ticker: str) -> dict | None:
        """Get most recent financial growth rates.

        Returns dict with: revenueGrowth, epsgrowth, etc.
        """
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self._cache:
            cached = self._cache.get("fmp", "financial-growth", yesterday, ticker)
            if cached is not None:
                return cached

        params = {"apikey": self._api_key, "symbol": ticker, "limit": 1}
        result = self._get("/stable/financial-growth", params=params,
                           headers=self._auth_headers())
        if result and isinstance(result, list) and len(result) > 0:
            if self._cache:
                self._cache.put("fmp", "financial-growth", yesterday, ticker, result[0])
            return result[0]
        return None
