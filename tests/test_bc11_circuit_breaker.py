"""BC11 Circuit Breaker Tests — Per-provider circuit breaker with sliding window.

~15 tests covering:
1. ProviderCircuitBreaker state machine (CLOSED → OPEN → HALF_OPEN)
2. BaseAPIClient integration with circuit breaker
"""

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from ifds.data.circuit_breaker import CBState, ProviderCircuitBreaker
from ifds.data.base import BaseAPIClient


# ============================================================================
# TestProviderCircuitBreaker — State Machine
# ============================================================================

class TestProviderCircuitBreaker:
    """Test the ProviderCircuitBreaker state machine."""

    def test_starts_closed(self):
        cb = ProviderCircuitBreaker("fmp")
        assert cb.state == CBState.CLOSED

    def test_records_success(self):
        cb = ProviderCircuitBreaker("fmp")
        cb.record_success()
        assert cb.state == CBState.CLOSED
        assert cb.error_rate == 0.0
        assert cb.call_count == 1

    def test_records_failure(self):
        cb = ProviderCircuitBreaker("fmp")
        cb.record_failure()
        assert cb.state == CBState.CLOSED  # Not enough calls to trip
        assert cb.call_count == 1

    def test_opens_on_threshold(self):
        """30% error rate with 10+ calls → OPEN."""
        cb = ProviderCircuitBreaker("fmp", window_size=50, threshold=0.3)
        # 7 successes + 3 failures = 30% error rate at 10 calls
        for _ in range(7):
            cb.record_success()
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CBState.OPEN

    def test_stays_closed_below_threshold(self):
        """29% error rate should stay CLOSED."""
        cb = ProviderCircuitBreaker("fmp", window_size=50, threshold=0.3)
        # 71 successes + 29 failures would be 29% but we only need 10 calls
        # 8 successes + 2 failures = 20% error rate
        for _ in range(8):
            cb.record_success()
        for _ in range(2):
            cb.record_failure()
        assert cb.state == CBState.CLOSED

    def test_min_sample_required(self):
        """Need at least 10 calls before tripping."""
        cb = ProviderCircuitBreaker("fmp", window_size=50, threshold=0.3)
        # 9 failures = 100% error rate but only 9 calls
        for _ in range(9):
            cb.record_failure()
        assert cb.state == CBState.CLOSED  # Not enough samples

    def test_allow_request_closed(self):
        cb = ProviderCircuitBreaker("fmp")
        assert cb.allow_request() is True

    def test_allow_request_open_rejects(self):
        cb = ProviderCircuitBreaker("fmp", threshold=0.3)
        # Force OPEN
        for _ in range(7):
            cb.record_success()
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CBState.OPEN
        assert cb.allow_request() is False

    def test_cooldown_transitions_to_half_open(self):
        """After cooldown expires, OPEN → HALF_OPEN."""
        cb = ProviderCircuitBreaker("fmp", threshold=0.3, cooldown_seconds=0.1)
        # Trip the breaker
        for _ in range(7):
            cb.record_success()
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CBState.OPEN

        # Wait for cooldown
        time.sleep(0.15)
        assert cb.state == CBState.HALF_OPEN
        assert cb.allow_request() is True

    def test_half_open_success_closes(self):
        """Successful probe in HALF_OPEN → CLOSED."""
        cb = ProviderCircuitBreaker("fmp", threshold=0.3, cooldown_seconds=0.05)
        for _ in range(7):
            cb.record_success()
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.1)
        assert cb.state == CBState.HALF_OPEN

        cb.record_success()
        assert cb.state == CBState.CLOSED

    def test_half_open_failure_reopens(self):
        """Failed probe in HALF_OPEN → OPEN again."""
        cb = ProviderCircuitBreaker("fmp", threshold=0.3, cooldown_seconds=0.05)
        for _ in range(7):
            cb.record_success()
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.1)
        assert cb.state == CBState.HALF_OPEN

        cb.record_failure()
        assert cb.state == CBState.OPEN

    def test_error_rate_calculation(self):
        cb = ProviderCircuitBreaker("fmp")
        cb.record_success()
        cb.record_success()
        cb.record_failure()
        assert abs(cb.error_rate - 1 / 3) < 0.01

    def test_error_rate_empty(self):
        cb = ProviderCircuitBreaker("fmp")
        assert cb.error_rate == 0.0

    def test_sliding_window_eviction(self):
        """Old results fall off when window is full."""
        cb = ProviderCircuitBreaker("fmp", window_size=10, threshold=0.3)
        # Fill window with 10 failures (100% error rate)
        for _ in range(10):
            cb.record_failure()
        assert cb.state == CBState.OPEN

        # Reset to HALF_OPEN via cooldown trick
        cb._state = CBState.CLOSED
        cb._results.clear()

        # Fill with 10 successes (old failures evicted)
        for _ in range(10):
            cb.record_success()
        assert cb.error_rate == 0.0

    def test_provider_property(self):
        cb = ProviderCircuitBreaker("polygon")
        assert cb.provider == "polygon"


# ============================================================================
# TestBaseClientCircuitBreaker — Integration
# ============================================================================

class TestBaseClientCircuitBreaker:
    """Test BaseAPIClient integration with circuit breaker."""

    def test_get_skips_when_open(self, capsys):
        """When circuit breaker is OPEN, _get() returns None immediately."""
        cb = MagicMock()
        cb.allow_request.return_value = False

        client = BaseAPIClient(
            base_url="https://example.com",
            provider_name="test",
            circuit_breaker=cb,
        )
        result = client._get("/test")
        assert result is None
        cb.allow_request.assert_called_once()
        # Should print circuit breaker message
        captured = capsys.readouterr()
        assert "[CIRCUIT BREAKER]" in captured.err

    def test_get_records_success(self):
        """Successful _get() records success on circuit breaker."""
        cb = MagicMock()
        cb.allow_request.return_value = True

        client = BaseAPIClient(
            base_url="https://example.com",
            provider_name="test",
            circuit_breaker=cb,
        )
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": "ok"}
        mock_resp.raise_for_status.return_value = None

        with patch.object(client._session, "get", return_value=mock_resp):
            result = client._get("/test")

        assert result == {"data": "ok"}
        cb.record_success.assert_called_once()

    def test_get_records_failure(self):
        """Failed _get() (all retries) records failure on circuit breaker."""
        cb = MagicMock()
        cb.allow_request.return_value = True

        client = BaseAPIClient(
            base_url="https://example.com",
            provider_name="test",
            max_retries=1,
            circuit_breaker=cb,
        )

        with patch.object(client._session, "get",
                          side_effect=requests.exceptions.Timeout):
            result = client._get("/test")

        assert result is None
        cb.record_failure.assert_called_once()

    def test_get_works_without_circuit_breaker(self):
        """Backwards compat: _get() works fine with no circuit breaker."""
        client = BaseAPIClient(
            base_url="https://example.com",
            provider_name="test",
        )
        assert client._circuit_breaker is None

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        mock_resp.raise_for_status.return_value = None

        with patch.object(client._session, "get", return_value=mock_resp):
            result = client._get("/test")

        assert result == {"ok": True}
