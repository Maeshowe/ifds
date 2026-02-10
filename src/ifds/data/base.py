"""Base API client with retry logic and health check."""

import sys
import time
from typing import Any

import requests

from ifds.models.market import APIHealthResult, APIStatus


class BaseAPIClient:
    """Base class for all IFDS API clients.

    Provides:
    - Retry logic with configurable attempts and timeout
    - Health check endpoint testing
    - Common request handling
    """

    def __init__(self, base_url: str, api_key: str | None = None,
                 timeout: int = 10, max_retries: int = 3,
                 provider_name: str = "unknown",
                 circuit_breaker=None):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._max_retries = max_retries
        self._provider = provider_name
        self._circuit_breaker = circuit_breaker
        self._session = requests.Session()

    def _get(self, endpoint: str, params: dict[str, Any] | None = None,
             headers: dict[str, str] | None = None) -> dict | list | None:
        """Make a GET request with retry logic.

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

        for attempt in range(1, self._max_retries + 1):
            try:
                resp = self._session.get(
                    url, params=params, headers=headers,
                    timeout=self._timeout,
                )
                resp.raise_for_status()
                if self._circuit_breaker:
                    self._circuit_breaker.record_success()
                return resp.json()
            except requests.exceptions.Timeout:
                last_error = f"Timeout after {self._timeout}s (attempt {attempt}/{self._max_retries})"
            except requests.exceptions.ConnectionError:
                last_error = f"Connection error (attempt {attempt}/{self._max_retries})"
            except requests.exceptions.HTTPError as e:
                last_error = f"HTTP {e.response.status_code} (attempt {attempt}/{self._max_retries})"
                # Don't retry on 4xx client errors (except 429 rate limit)
                if e.response.status_code < 500 and e.response.status_code != 429:
                    break
            except Exception as e:
                last_error = f"{type(e).__name__}: {e} (attempt {attempt}/{self._max_retries})"

            if attempt < self._max_retries:
                time.sleep(1.0 * attempt)  # Simple linear backoff

        # All retries exhausted — record failure
        if self._circuit_breaker:
            self._circuit_breaker.record_failure()
        print(
            f"  [API ERROR] {self._provider} {endpoint}: {last_error}",
            file=sys.stderr,
        )
        return None

    def health_check(self, endpoint: str, is_critical: bool = True) -> APIHealthResult:
        """Test connectivity to a specific endpoint.

        Args:
            endpoint: The API endpoint to test.
            is_critical: If True, failure means pipeline must HALT.

        Returns:
            APIHealthResult with status and timing.
        """
        url = f"{self._base_url}{endpoint}"
        start = time.monotonic()
        retries_used = 0
        error = "Unknown error"

        for attempt in range(1, self._max_retries + 1):
            retries_used = attempt - 1
            try:
                resp = self._session.get(
                    url, params=self._health_check_params(),
                    headers=self._auth_headers(),
                    timeout=self._timeout,
                )
                elapsed_ms = (time.monotonic() - start) * 1000

                if resp.status_code == 200:
                    return APIHealthResult(
                        provider=self._provider, endpoint=endpoint,
                        status=APIStatus.OK, response_time_ms=elapsed_ms,
                        is_critical=is_critical, retries_used=retries_used,
                    )
                else:
                    error = f"HTTP {resp.status_code}"
                    if resp.status_code < 500 and resp.status_code != 429:
                        return APIHealthResult(
                            provider=self._provider, endpoint=endpoint,
                            status=APIStatus.DOWN, error=error,
                            response_time_ms=elapsed_ms,
                            is_critical=is_critical, retries_used=retries_used,
                        )

            except requests.exceptions.Timeout:
                error = f"Timeout after {self._timeout}s"
            except requests.exceptions.ConnectionError:
                error = "Connection refused"
            except Exception as e:
                error = f"{type(e).__name__}: {e}"

            if attempt < self._max_retries:
                time.sleep(1.0 * attempt)

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

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()
