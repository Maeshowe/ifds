"""Per-provider circuit breaker with sliding window error tracking."""

import time
from collections import deque
from enum import Enum


class CBState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Halted — all calls rejected
    HALF_OPEN = "half_open"  # Cooldown expired — allow 1 probe call


class ProviderCircuitBreaker:
    """Tracks error rate per API provider using a sliding window.

    States:
        CLOSED   → normal, tracking errors
        OPEN     → halted, rejects all calls until cooldown expires
        HALF_OPEN → allows 1 probe call to test recovery

    Usage:
        cb = ProviderCircuitBreaker("fmp", window_size=50, threshold=0.3)
        if cb.allow_request():
            result = api_call()
            if result is not None:
                cb.record_success()
            else:
                cb.record_failure()
    """

    def __init__(self, provider: str, window_size: int = 50,
                 threshold: float = 0.3, cooldown_seconds: float = 60.0):
        self._provider = provider
        self._window_size = window_size
        self._threshold = threshold
        self._cooldown = cooldown_seconds
        self._results: deque[bool] = deque(maxlen=window_size)
        self._state = CBState.CLOSED
        self._opened_at: float = 0.0

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def state(self) -> CBState:
        """Current state (auto-transitions OPEN → HALF_OPEN on cooldown expiry)."""
        if self._state == CBState.OPEN:
            if time.monotonic() - self._opened_at >= self._cooldown:
                self._state = CBState.HALF_OPEN
        return self._state

    @property
    def error_rate(self) -> float:
        """Current error rate in the sliding window."""
        if not self._results:
            return 0.0
        errors = sum(1 for r in self._results if not r)
        return errors / len(self._results)

    @property
    def call_count(self) -> int:
        """Total calls in the sliding window."""
        return len(self._results)

    def allow_request(self) -> bool:
        """Check if a request should be allowed."""
        s = self.state
        if s == CBState.CLOSED:
            return True
        if s == CBState.HALF_OPEN:
            return True  # Allow probe
        return False  # OPEN

    def record_success(self) -> None:
        """Record a successful API call."""
        self._results.append(True)
        if self._state == CBState.HALF_OPEN:
            self._state = CBState.CLOSED

    def record_failure(self) -> None:
        """Record a failed API call."""
        self._results.append(False)
        if self._state == CBState.HALF_OPEN:
            self._state = CBState.OPEN
            self._opened_at = time.monotonic()
        elif self._state == CBState.CLOSED:
            self._check_threshold()

    def _check_threshold(self) -> None:
        """Check if error rate exceeds threshold → transition to OPEN."""
        if len(self._results) >= 10 and self.error_rate >= self._threshold:
            self._state = CBState.OPEN
            self._opened_at = time.monotonic()
