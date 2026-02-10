"""FRED (Federal Reserve Economic Data) API client.

Provides: VIX, TNX (10-Year Treasury Yield), and other macro indicators.
Free API key required: https://fred.stlouisfed.org/docs/api/api_key.html
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, TYPE_CHECKING

from ifds.data.base import BaseAPIClient
from ifds.models.market import APIHealthResult

if TYPE_CHECKING:
    from ifds.data.cache import FileCache


class FREDClient(BaseAPIClient):
    """Client for FRED REST API.

    Endpoints used:
    - /fred/series/observations — Time series data

    Series IDs:
    - VIXCLS: VIX Close
    - DGS10: 10-Year Treasury Constant Maturity Rate
    """

    HEALTH_CHECK_ENDPOINT = "/fred/series/observations"

    # FRED series IDs
    VIX_SERIES = "VIXCLS"
    TNX_SERIES = "DGS10"

    def __init__(self, api_key: str, timeout: int = 10,
                 max_retries: int = 3, cache: FileCache | None = None,
                 circuit_breaker=None):
        super().__init__(
            base_url="https://api.stlouisfed.org",
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            provider_name="fred",
            circuit_breaker=circuit_breaker,
        )
        self._cache = cache

    def _health_check_params(self) -> dict[str, Any]:
        params = {
            "series_id": self.VIX_SERIES,
            "sort_order": "desc",
            "limit": 1,
            "file_type": "json",
        }
        params["api_key"] = self._api_key
        return params

    def check_health(self) -> APIHealthResult:
        """Check FRED API connectivity."""
        return self.health_check(self.HEALTH_CHECK_ENDPOINT, is_critical=True)

    def get_series(self, series_id: str, limit: int = 30) -> list[dict] | None:
        """Get recent observations for a FRED series.

        Args:
            series_id: FRED series identifier (e.g., "VIXCLS").
            limit: Number of recent observations to return.

        Returns:
            List of observation dicts with 'date' and 'value' keys, or None.
        """
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
        }
        params["api_key"] = self._api_key

        data = self._get(self.HEALTH_CHECK_ENDPOINT, params=params)
        if data and data.get("observations"):
            result = data["observations"]
            if self._cache:
                self._cache.put("fred", "series", yesterday, series_id, result)
            return result
        return None

    def get_vix(self, limit: int = 30) -> list[dict] | None:
        """Get recent VIX values."""
        return self.get_series(self.VIX_SERIES, limit=limit)

    def get_tnx(self, limit: int = 30) -> list[dict] | None:
        """Get recent 10-Year Treasury Yield values."""
        return self.get_series(self.TNX_SERIES, limit=limit)
