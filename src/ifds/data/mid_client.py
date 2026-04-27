"""MID API client — consumes /api/bundle/latest.

Shadow-mode only. The MIDClient is currently used for data collection
and offline sector-rotation comparison; it does NOT affect the IFDS
Phase 3 sector rotation, scoring, or VETO pipeline.

Authentication: every request to /api/* must include the X-API-Key
header. If the key is missing or invalid, the server returns 401/403
and the client returns an empty dict — non-fatal.

Rate limit policy: in-memory cache for 5 minutes (the bundle refreshes
once daily, so one fetch per pipeline run is sufficient).
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MIDClient:
    """HTTP client for the MID (Macro Intelligence Dashboard) bundle API."""

    BASE_URL = "https://mid.ssh.services/api"
    CACHE_TTL_SECONDS = 300  # 5 minutes

    def __init__(self, api_key: str | None, timeout: int = 10) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._cache: dict[str, Any] | None = None
        self._cache_ts: float | None = None

    def _headers(self) -> dict[str, str]:
        """Build auth headers. X-API-Key is required for /api/*."""
        if not self._api_key:
            return {}
        return {
            "X-API-Key": self._api_key,
            "Accept": "application/json",
        }

    def _cache_valid(self) -> bool:
        if self._cache is None or self._cache_ts is None:
            return False
        return (time.time() - self._cache_ts) < self.CACHE_TTL_SECONDS

    def get_bundle(self, force_refresh: bool = False) -> dict[str, Any]:
        """Fetch the latest MID bundle (cached for 5 minutes).

        Args:
            force_refresh: bypass cache and force a fresh HTTP fetch.

        Returns:
            The full bundle dict on success, or an empty dict ``{}``
            on any failure (network error, auth error, malformed JSON).
            Failure is non-fatal — the caller should treat ``{}`` as
            "MID unavailable" and continue.
        """
        if not self._api_key:
            logger.debug("MIDClient: no API key configured, skipping fetch")
            return {}

        if not force_refresh and self._cache_valid():
            return self._cache  # type: ignore[return-value]

        url = f"{self.BASE_URL}/bundle/latest"
        try:
            response = httpx.get(url, headers=self._headers(), timeout=self._timeout)
            response.raise_for_status()
            bundle = response.json()
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"MID API returned {e.response.status_code} for {url} — "
                f"returning empty bundle"
            )
            return {}
        except (httpx.HTTPError, httpx.TimeoutException, ValueError) as e:
            logger.warning(f"MID API unavailable ({type(e).__name__}: {e}) — "
                           f"returning empty bundle")
            return {}

        if not isinstance(bundle, dict):
            logger.warning(f"MID API returned non-dict payload (type={type(bundle).__name__}) "
                           f"— returning empty bundle")
            return {}

        self._cache = bundle
        self._cache_ts = time.time()
        return bundle

    def get_sectors(self) -> list[dict[str, Any]]:
        """Return the sector CAS list from ``bundle.etf_xray.sectors``.

        Returns an empty list on any failure.
        """
        bundle = self.get_bundle()
        etf_xray = bundle.get("etf_xray", {}) if bundle else {}
        sectors = etf_xray.get("sectors", []) if isinstance(etf_xray, dict) else []
        return sectors if isinstance(sectors, list) else []

    def get_regime(self) -> dict[str, Any]:
        """Return current regime + TPI summary from ``bundle.flat`` and
        ``bundle.engines.tpi``.

        Returns an empty dict on any failure.
        """
        bundle = self.get_bundle()
        if not bundle:
            return {}
        flat = bundle.get("flat", {}) if isinstance(bundle.get("flat"), dict) else {}
        engines = bundle.get("engines", {}) if isinstance(bundle.get("engines"), dict) else {}
        tpi = engines.get("tpi", {}) if isinstance(engines.get("tpi"), dict) else {}
        return {
            "regime": flat.get("regime"),
            "tpi_score": flat.get("tpi"),
            "tpi_state": tpi.get("state"),
            "growth": flat.get("growth"),
            "inflation": flat.get("inflation"),
            "policy": flat.get("policy"),
            "rpi": flat.get("rpi"),
            "esi": flat.get("esi"),
        }
