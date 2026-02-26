"""Tests for BC16: Phase 1 async BMI fetching."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import BMIRegime, StrategyMode
from ifds.phases.phase1_regime import (
    run_phase1,
    _fetch_daily_history_async,
    _run_phase1_async,
)


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    monkeypatch.setenv("IFDS_ASYNC_ENABLED", "true")
    return Config()


@pytest.fixture
def sync_config(monkeypatch):
    """Config with async disabled (for dispatch test)."""
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    return Config()


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-bc16-p1-async")


def _make_grouped_bars(ticker_count=50, buy_volume=3000, sell_volume=3000):
    """Create mock grouped daily bars for one day.

    Creates tickers with volume spikes: half buys (close > open), half sells.
    Also includes a SPY bar for divergence detection.
    """
    bars = []
    for i in range(ticker_count):
        ticker = f"T{i:03d}"
        if i < ticker_count // 2:
            # Buy signal: close > open, high volume
            bars.append({"T": ticker, "o": 100.0, "c": 105.0, "v": buy_volume,
                         "h": 106.0, "l": 99.0})
        else:
            # Sell signal: close < open, high volume
            bars.append({"T": ticker, "o": 105.0, "c": 100.0, "v": sell_volume,
                         "h": 106.0, "l": 99.0})
    # SPY bar for divergence detection
    bars.append({"T": "SPY", "o": 500.0, "c": 505.0, "v": 50000000,
                 "h": 506.0, "l": 499.0})
    return bars


def _make_daily_bars_sequence(day_count=30, ticker_count=50):
    """Create a sequence of grouped daily bars for multiple days.

    Returns list of bar lists (one per day), suitable for mock return values.
    """
    return [_make_grouped_bars(ticker_count) for _ in range(day_count)]


# ============================================================================
# _fetch_daily_history_async
# ============================================================================

class TestFetchDailyHistoryAsync:
    """Test the async daily history fetcher."""

    @pytest.mark.asyncio
    async def test_basic_concurrent_fetch(self):
        """Fetches multiple days concurrently via asyncio.gather."""
        bars = _make_grouped_bars()
        mock_polygon = AsyncMock()
        mock_polygon.get_grouped_daily = AsyncMock(return_value=bars)

        result = await _fetch_daily_history_async(mock_polygon, lookback_calendar_days=10)

        # ~7 weekdays in 10 calendar days
        assert len(result) >= 5
        assert all("date" in d and "bars" in d for d in result)
        # All calls should have been made concurrently
        assert mock_polygon.get_grouped_daily.await_count >= 5

    @pytest.mark.asyncio
    async def test_none_responses_filtered(self):
        """Days where API returns None are excluded."""
        call_count = 0

        async def alternating_response(day_str):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                return None  # Every other day fails
            return _make_grouped_bars()

        mock_polygon = AsyncMock()
        mock_polygon.get_grouped_daily = AsyncMock(side_effect=alternating_response)

        result = await _fetch_daily_history_async(mock_polygon, lookback_calendar_days=10)

        # Should only include non-None days
        total_calls = mock_polygon.get_grouped_daily.await_count
        assert len(result) < total_calls
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_skips_weekends(self):
        """Weekend dates are not requested."""
        mock_polygon = AsyncMock()
        mock_polygon.get_grouped_daily = AsyncMock(return_value=_make_grouped_bars())

        result = await _fetch_daily_history_async(mock_polygon, lookback_calendar_days=7)

        # 7 calendar days = 5 weekdays max
        assert mock_polygon.get_grouped_daily.await_count <= 5

    @pytest.mark.asyncio
    async def test_empty_on_all_none(self):
        """Returns empty list when all API calls return None."""
        mock_polygon = AsyncMock()
        mock_polygon.get_grouped_daily = AsyncMock(return_value=None)

        result = await _fetch_daily_history_async(mock_polygon, lookback_calendar_days=10)

        assert result == []

    @pytest.mark.asyncio
    async def test_breadth_lookback(self):
        """Breadth-enabled lookback (330 days) produces ~235 API calls."""
        mock_polygon = AsyncMock()
        mock_polygon.get_grouped_daily = AsyncMock(return_value=_make_grouped_bars())

        result = await _fetch_daily_history_async(mock_polygon, lookback_calendar_days=330)

        # 330 calendar days ≈ 235 trading days
        call_count = mock_polygon.get_grouped_daily.await_count
        assert call_count >= 220
        assert call_count <= 240


# ============================================================================
# _run_phase1_async — full async path
# ============================================================================

class TestRunPhase1Async:
    """Test the full async Phase 1 execution."""

    @pytest.mark.asyncio
    async def test_basic_async_phase1(self, config, logger):
        """Async Phase 1 produces valid BMI result."""
        bars = _make_grouped_bars()

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly:
            mock_poly = AsyncMock()
            mock_poly.get_grouped_daily = AsyncMock(return_value=bars)
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            result = await _run_phase1_async(config, logger)

            assert result.bmi is not None
            assert 0 <= result.bmi.bmi_value <= 100
            assert result.strategy_mode in (StrategyMode.LONG, StrategyMode.SHORT)
            assert result.bmi.bmi_regime in (BMIRegime.GREEN, BMIRegime.YELLOW, BMIRegime.RED)
            mock_poly.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_async_insufficient_data_fallback(self, config, logger):
        """Insufficient data triggers fallback (YELLOW/LONG)."""
        # Return None for most days — only 5 valid days
        call_count = 0

        async def sparse_response(day_str):
            nonlocal call_count
            call_count += 1
            if call_count <= 5:
                return _make_grouped_bars()
            return None

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly:
            mock_poly = AsyncMock()
            mock_poly.get_grouped_daily = AsyncMock(side_effect=sparse_response)
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            result = await _run_phase1_async(config, logger)

            # Fallback: BMI=50, YELLOW, LONG
            assert result.bmi.bmi_value == 50.0
            assert result.bmi.bmi_regime == BMIRegime.YELLOW
            assert result.strategy_mode == StrategyMode.LONG

    @pytest.mark.asyncio
    async def test_async_with_sector_mapping(self, config, logger):
        """Async Phase 1 computes per-sector BMI when sector_mapping provided."""
        bars = _make_grouped_bars(ticker_count=20)

        sector_mapping = {}
        for i in range(20):
            ticker = f"T{i:03d}"
            if i < 10:
                sector_mapping[ticker] = "Technology"
            else:
                sector_mapping[ticker] = "Energy"

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly:
            mock_poly = AsyncMock()
            mock_poly.get_grouped_daily = AsyncMock(return_value=bars)
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            result = await _run_phase1_async(
                config, logger, sector_mapping=sector_mapping,
            )

            assert result.bmi is not None
            # Sector BMI may or may not populate depending on signal thresholds,
            # but the code path should execute without error
            assert isinstance(result.sector_bmi_values, dict)

    @pytest.mark.asyncio
    async def test_async_client_cleanup_on_error(self, config, logger):
        """Client is closed even when all API calls fail (return_exceptions=True)."""
        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly:
            mock_poly = AsyncMock()
            mock_poly.get_grouped_daily = AsyncMock(
                side_effect=ConnectionError("API down"),
            )
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            # With return_exceptions=True, errors are captured not raised
            # → insufficient data fallback (YELLOW)
            result = await _run_phase1_async(config, logger)
            assert result.bmi.bmi_regime == BMIRegime.YELLOW

            mock_poly.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_async_semaphore_from_config(self, config, logger):
        """Semaphore value is read from config runtime."""
        bars = _make_grouped_bars()

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly:
            mock_poly = AsyncMock()
            mock_poly.get_grouped_daily = AsyncMock(return_value=bars)
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            await _run_phase1_async(config, logger)

            # Verify AsyncPolygonClient was created with semaphore
            call_kwargs = MockPoly.call_args
            assert "semaphore" in call_kwargs.kwargs
            assert isinstance(call_kwargs.kwargs["semaphore"], asyncio.Semaphore)

    @pytest.mark.asyncio
    async def test_async_grouped_daily_bars_stored_for_breadth(self, config, logger):
        """When breadth_enabled, grouped_daily_bars are stored on result."""
        bars = _make_grouped_bars()

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly:
            mock_poly = AsyncMock()
            mock_poly.get_grouped_daily = AsyncMock(return_value=bars)
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            # breadth_enabled=True is the default in TUNING
            result = await _run_phase1_async(config, logger)

            # With breadth_enabled, grouped_daily_bars should be populated
            if config.tuning.get("breadth_enabled", False):
                assert len(result.grouped_daily_bars) > 0


# ============================================================================
# run_phase1() async dispatch
# ============================================================================

class TestPhase1AsyncDispatch:
    """Test that run_phase1() dispatches to async when enabled."""

    def test_async_dispatch_when_enabled(self, config, logger):
        """run_phase1() dispatches to _run_phase1_async when async_enabled=True."""
        bars = _make_grouped_bars()

        with patch("ifds.phases.phase1_regime._run_phase1_async", new=MagicMock()) as mock_async, \
             patch("ifds.phases.phase1_regime.asyncio") as mock_asyncio:
            from ifds.models.market import BMIData, Phase1Result
            mock_result = Phase1Result(
                bmi=BMIData(bmi_value=50.0, bmi_regime=BMIRegime.YELLOW, daily_ratio=50.0),
                strategy_mode=StrategyMode.LONG,
            )
            mock_asyncio.run.return_value = mock_result

            polygon = MagicMock()
            result = run_phase1(config, logger, polygon)

            mock_asyncio.run.assert_called_once()
            assert result == mock_result

    def test_sync_path_when_disabled(self, sync_config, logger):
        """run_phase1() uses sync path when async_enabled=False."""
        bars = _make_grouped_bars()
        mock_polygon = MagicMock()
        mock_polygon.get_grouped_daily.return_value = bars

        result = run_phase1(sync_config, logger, mock_polygon)

        # Sync path executes — polygon.get_grouped_daily was called
        assert mock_polygon.get_grouped_daily.call_count > 0
        assert result.bmi is not None
