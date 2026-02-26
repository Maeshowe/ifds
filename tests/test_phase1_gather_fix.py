"""Tests for Phase 1 asyncio.gather return_exceptions fix.

Covers: single failure tolerance, all failures, partial success.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from ifds.phases.phase1_regime import _fetch_daily_history_async


@pytest.fixture
def mock_logger():
    logger = MagicMock()
    return logger


class TestGatherReturnExceptions:
    """asyncio.gather in _fetch_daily_history_async tolerates exceptions."""

    @pytest.mark.asyncio
    async def test_gather_tolerates_single_polygon_failure(self, mock_logger):
        """One Polygon 429 among valid results — does not crash."""
        polygon = AsyncMock()
        # First call raises, rest return valid bars
        polygon.get_grouped_daily.side_effect = [
            Exception("429 Too Many Requests"),
            [{"T": "AAPL", "v": 1000}],
            [{"T": "MSFT", "v": 2000}],
        ]

        result = await _fetch_daily_history_async(
            polygon, lookback_calendar_days=5, logger=mock_logger
        )

        # Should have some results (not crash)
        assert isinstance(result, list)
        # Logger should have logged the failure
        mock_logger.log.assert_called_once()
        assert "failed" in mock_logger.log.call_args[1]["message"]

    @pytest.mark.asyncio
    async def test_gather_tolerates_all_failures(self, mock_logger):
        """All Polygon requests fail — returns empty list, no crash."""
        polygon = AsyncMock()
        polygon.get_grouped_daily.side_effect = Exception("connection timeout")

        result = await _fetch_daily_history_async(
            polygon, lookback_calendar_days=5, logger=mock_logger
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_gather_partial_success(self, mock_logger):
        """3 calls, 1 fails — 2 valid results returned."""
        polygon = AsyncMock()
        valid_bars = [{"T": "AAPL", "v": 1000}]
        polygon.get_grouped_daily.side_effect = [
            valid_bars,
            Exception("HTTP 429"),
            valid_bars,
        ]

        result = await _fetch_daily_history_async(
            polygon, lookback_calendar_days=5, logger=mock_logger
        )

        # Exactly 2 valid results (the 2 that didn't throw)
        valid_count = len([r for r in result if r])
        assert valid_count == 2
        assert mock_logger.log.call_count == 1
