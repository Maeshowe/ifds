"""Async base API client with aiohttp, retry logic, and semaphore rate limiting."""

import asyncio
import sys
import time
from typing import Any

import aiohttp

from ifds.models.market import APIHealthResult, APIStatus


class AsyncBaseAPIClient:
    """Async base class for all IFDS API clients.

    Mirrors BaseAPIClient but uses aiohttp.ClientSession with:
    - Per-provider asyncio.Semaphore for rate limiting
    - Async retry with asyncio.sleep() backoff
    - Lazy session creation (created on first request)
    """

    def __init__(self, base_url: str, api_key: str | None = None,
                 timeout: int = 10, max_retries: int = 3,
                 provider_name: str = "unknown",
                 semaphore: asyncio.Semaphore | None = None,
                 circuit_breaker=None):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._max_retries = max_retries
        self._provider = provider_name
        self._semaphore = semaphore or asyncio.Semaphore(10)
        self._circuit_breaker = circuit_breaker
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Lazily create aiohttp session on first use."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def _get(self, endpoint: str, params: dict[str, Any] | None = None,
                   headers: dict[str, str] | None = None) -> dict | list | None:
        """Make an async GET request with semaphore + retry logic.

        Returns parsed JSON on success, None on failure after all retries.
        """
        # Circuit breaker pre-check
        if self._circuit_breaker and not self._circuit_breaker.allow_request():
            print(
                f"  [CIRCUIT BREAKER] {self._provider} OPEN — skipping {endpoint}",
                file=sys.stderr,
            )
            return None

        url = f"{self._base_url}{endpoint}"
        last_error = "Unknown error"
        session = await self._ensure_session()

        for attempt in range(1, self._max_retries + 1):
            try:
                async with self._semaphore:
                    async with session.get(url, params=params, headers=headers) as resp:
                        if resp.status >= 400:
                            last_error = f"HTTP {resp.status} (attempt {attempt}/{self._max_retries})"
                            # Don't retry 4xx except 429
                            if resp.status < 500 and resp.status != 429:
                                break
                        else:
                            if self._circuit_breaker:
                                self._circuit_breaker.record_success()
                            return await resp.json()
            except asyncio.TimeoutError:
                last_error = f"Timeout (attempt {attempt}/{self._max_retries})"
            except aiohttp.ClientConnectionError:
                last_error = f"Connection error (attempt {attempt}/{self._max_retries})"
            except Exception as e:
                last_error = f"{type(e).__name__}: {e} (attempt {attempt}/{self._max_retries})"

            if attempt < self._max_retries:
                await asyncio.sleep(1.0 * attempt)

        # All retries exhausted — record failure
        if self._circuit_breaker:
            self._circuit_breaker.record_failure()
        print(
            f"  [API ERROR] {self._provider} {endpoint}: {last_error}",
            file=sys.stderr,
        )
        return None

    async def health_check(self, endpoint: str, is_critical: bool = True) -> APIHealthResult:
        """Async health check for a specific endpoint."""
        url = f"{self._base_url}{endpoint}"
        start = time.monotonic()
        retries_used = 0
        error = "Unknown error"
        session = await self._ensure_session()

        for attempt in range(1, self._max_retries + 1):
            retries_used = attempt - 1
            try:
                async with self._semaphore:
                    async with session.get(
                        url,
                        params=self._health_check_params(),
                        headers=self._auth_headers(),
                    ) as resp:
                        elapsed_ms = (time.monotonic() - start) * 1000

                        if resp.status == 200:
                            return APIHealthResult(
                                provider=self._provider, endpoint=endpoint,
                                status=APIStatus.OK, response_time_ms=elapsed_ms,
                                is_critical=is_critical, retries_used=retries_used,
                            )
                        else:
                            error = f"HTTP {resp.status}"
                            if resp.status < 500 and resp.status != 429:
                                return APIHealthResult(
                                    provider=self._provider, endpoint=endpoint,
                                    status=APIStatus.DOWN, error=error,
                                    response_time_ms=elapsed_ms,
                                    is_critical=is_critical, retries_used=retries_used,
                                )

            except asyncio.TimeoutError:
                error = f"Timeout"
            except aiohttp.ClientConnectionError:
                error = "Connection refused"
            except Exception as e:
                error = f"{type(e).__name__}: {e}"

            if attempt < self._max_retries:
                await asyncio.sleep(1.0 * attempt)

        elapsed_ms = (time.monotonic() - start) * 1000
        return APIHealthResult(
            provider=self._provider, endpoint=endpoint,
            status=APIStatus.DOWN, error=error,
            response_time_ms=elapsed_ms,
            is_critical=is_critical, retries_used=retries_used,
        )

    def _auth_headers(self) -> dict[str, str]:
        """Override in subclasses to provide authentication headers."""
        return {}

    def _health_check_params(self) -> dict[str, Any]:
        """Override in subclasses to provide health check query params."""
        return {}

    @property
    def provider(self) -> str:
        return self._provider

    async def close(self) -> None:
        """Close the underlying aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
