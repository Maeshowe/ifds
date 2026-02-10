"""Tests for Dark Pool batch prefetch providers and shared aggregation."""

import asyncio

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from ifds.data.adapters import (
    _aggregate_dp_records,
    UWBatchDarkPoolProvider,
    UWDarkPoolProvider,
)
from ifds.data.async_adapters import AsyncUWBatchDarkPoolProvider
from ifds.events.logger import EventLogger


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="batch-dp-test")


# ============================================================================
# _aggregate_dp_records() — shared pure function
# ============================================================================

class TestAggregateDpRecords:
    def test_bullish_signal(self):
        """dp_buys > dp_sells → BULLISH."""
        records = [
            {"size": "500", "price": "150.50", "nbbo_ask": "150.30", "nbbo_bid": "150.10"},
            {"size": "300", "price": "150.40", "nbbo_ask": "150.30", "nbbo_bid": "150.10"},
        ]
        result = _aggregate_dp_records(records)
        assert result["signal"] == "BULLISH"
        assert result["dp_volume"] == 800
        assert result["dp_buys"] == 800
        assert result["dp_sells"] == 0
        assert result["source"] == "unusual_whales"

    def test_bearish_signal(self):
        """dp_sells > dp_buys → BEARISH."""
        records = [
            {"size": "500", "price": "150.01", "nbbo_ask": "150.15", "nbbo_bid": "150.05"},
            {"size": "300", "price": "150.02", "nbbo_ask": "150.15", "nbbo_bid": "150.05"},
        ]
        result = _aggregate_dp_records(records)
        assert result["signal"] == "BEARISH"
        assert result["dp_sells"] == 800

    def test_neutral_signal(self):
        """dp_buys == dp_sells → NEUTRAL."""
        records = [
            {"size": "500", "price": "150.20", "nbbo_ask": "150.15", "nbbo_bid": "150.05"},
            {"size": "500", "price": "150.01", "nbbo_ask": "150.15", "nbbo_bid": "150.05"},
        ]
        result = _aggregate_dp_records(records)
        assert result["signal"] == "NEUTRAL"
        assert result["dp_buys"] == 500
        assert result["dp_sells"] == 500

    def test_empty_records(self):
        """Empty list → zero volume, NEUTRAL."""
        result = _aggregate_dp_records([])
        assert result["dp_volume"] == 0
        assert result["signal"] == "NEUTRAL"

    def test_nbbo_missing(self):
        """Records without NBBO → volume counted but no buy/sell classification."""
        records = [
            {"size": "1000", "price": "50.00"},
            {"size": "2000", "price": "50.50", "nbbo_ask": "0", "nbbo_bid": "0"},
        ]
        result = _aggregate_dp_records(records)
        assert result["dp_volume"] == 3000
        assert result["dp_buys"] == 0
        assert result["dp_sells"] == 0
        assert result["signal"] == "NEUTRAL"

    def test_dp_pct_from_volume_field(self):
        """dp_pct computed from record's volume field (total stock day volume)."""
        records = [
            {"size": "100", "price": "10.0", "nbbo_ask": "10.5", "nbbo_bid": "9.5",
             "volume": "10000"},
        ]
        result = _aggregate_dp_records(records)
        assert result["total_volume"] == 10000
        assert result["dp_pct"] == 1.0  # 100 / 10000 * 100

    def test_dp_pct_zero_when_no_volume(self):
        """dp_pct is 0.0 when records lack volume field."""
        records = [
            {"size": "100", "price": "10.0", "nbbo_ask": "10.5", "nbbo_bid": "9.5"},
        ]
        result = _aggregate_dp_records(records)
        assert result["dp_pct"] == 0.0
        assert result["total_volume"] == 0


# ============================================================================
# UWBatchDarkPoolProvider — sync batch provider
# ============================================================================

class TestUWBatchDarkPoolProvider:
    def _make_records(self, tickers_sizes):
        """Build mock records: [(ticker, size, executed_at), ...]"""
        records = []
        for ticker, size, ts in tickers_sizes:
            records.append({
                "ticker": ticker,
                "size": str(size),
                "price": "100.0",
                "nbbo_ask": "100.05",
                "nbbo_bid": "99.95",
                "executed_at": ts,
            })
        return records

    def test_prefetch_groups_by_ticker(self, logger):
        """3 tickers mixed → correct grouping."""
        client = MagicMock()
        page1 = self._make_records([
            ("AAPL", 100, "2026-02-09T10:00:00"),
            ("NVDA", 200, "2026-02-09T10:01:00"),
            ("AAPL", 150, "2026-02-09T10:02:00"),
            ("TSLA", 300, "2026-02-09T10:03:00"),
        ])
        client.get_dark_pool_recent.side_effect = [page1, []]

        provider = UWBatchDarkPoolProvider(client, logger=logger, max_pages=5, page_delay=0)
        provider.prefetch()

        assert "AAPL" in provider._cache
        assert "NVDA" in provider._cache
        assert "TSLA" in provider._cache
        assert len(provider._cache["AAPL"]) == 2
        assert len(provider._cache["NVDA"]) == 1

    def test_get_dark_pool_from_cache(self, logger):
        """After prefetch, returns aggregated data for cached ticker."""
        client = MagicMock()
        page1 = self._make_records([
            ("SPY", 500, "2026-02-09T10:00:00"),
            ("SPY", 300, "2026-02-09T10:01:00"),
        ])
        client.get_dark_pool_recent.side_effect = [page1, []]

        provider = UWBatchDarkPoolProvider(client, logger=logger, max_pages=5, page_delay=0)
        provider.prefetch()
        result = provider.get_dark_pool("SPY")

        assert result is not None
        assert result["dp_volume"] == 800
        assert result["signal"] == "BULLISH"

    def test_cache_miss_returns_none(self, logger):
        """Ticker not in cache → None."""
        client = MagicMock()
        client.get_dark_pool_recent.return_value = []

        provider = UWBatchDarkPoolProvider(client, logger=logger, max_pages=5, page_delay=0)
        provider.prefetch()

        assert provider.get_dark_pool("MISSING") is None

    def test_pagination_uses_older_than(self, logger):
        """Verify older_than passed from last record's executed_at."""
        client = MagicMock()
        page1 = self._make_records([
            ("AAPL", 100, "2026-02-09T10:00:00"),
        ])
        page2 = self._make_records([
            ("NVDA", 200, "2026-02-09T09:00:00"),
        ])
        client.get_dark_pool_recent.side_effect = [page1, page2, []]

        provider = UWBatchDarkPoolProvider(client, logger=logger, max_pages=5, page_delay=0)
        provider.prefetch()

        calls = client.get_dark_pool_recent.call_args_list
        assert calls[0].kwargs.get("older_than") is None or \
               calls[0] == ((200,), {"limit": 200, "date": None, "older_than": None})
        # Second call should use executed_at from last record of page1
        assert calls[1].kwargs.get("older_than") == "2026-02-09T10:00:00" or \
               calls[1][1].get("older_than") == "2026-02-09T10:00:00"

    def test_stops_on_empty_page(self, logger):
        """Empty response → stop pagination."""
        client = MagicMock()
        client.get_dark_pool_recent.side_effect = [
            self._make_records([("AAPL", 100, "ts1")]),
            [],
        ]
        provider = UWBatchDarkPoolProvider(client, logger=logger, max_pages=10, page_delay=0)
        provider.prefetch()

        assert client.get_dark_pool_recent.call_count == 2

    def test_max_pages_respected(self, logger):
        """Stops after max_pages even if data keeps coming."""
        client = MagicMock()
        page = self._make_records([("AAPL", 100, "ts1")])
        client.get_dark_pool_recent.return_value = page

        provider = UWBatchDarkPoolProvider(client, logger=logger, max_pages=3, page_delay=0)
        provider.prefetch()

        assert client.get_dark_pool_recent.call_count == 3

    def test_auto_prefetch_on_first_call(self, logger):
        """Lazy prefetch if not called explicitly."""
        client = MagicMock()
        page1 = self._make_records([("AAPL", 500, "ts1")])
        client.get_dark_pool_recent.side_effect = [page1, []]

        provider = UWBatchDarkPoolProvider(client, logger=logger, max_pages=5, page_delay=0)
        # Don't call prefetch() — should auto-trigger on first get_dark_pool()
        result = provider.get_dark_pool("AAPL")

        assert result is not None
        assert result["dp_volume"] == 500
        assert provider._prefetched is True

    def test_provider_name(self):
        """Returns 'unusual_whales_batch'."""
        client = MagicMock()
        provider = UWBatchDarkPoolProvider(client)
        assert provider.provider_name() == "unusual_whales_batch"

    @patch("ifds.data.adapters.time.sleep")
    def test_page_delay_called(self, mock_sleep, logger):
        """Verify sleep between pages (not after last)."""
        client = MagicMock()
        page = self._make_records([("A", 1, "ts")])
        client.get_dark_pool_recent.side_effect = [page, page, []]

        provider = UWBatchDarkPoolProvider(client, logger=logger, max_pages=5, page_delay=0.5)
        provider.prefetch()

        # Sleep called between page 0→1 and page 1→2 (not after last page which is empty)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(0.5)

    def test_logs_data_prefetch_event(self, logger):
        """Prefetch should log DATA_PREFETCH event."""
        client = MagicMock()
        page1 = self._make_records([
            ("AAPL", 100, "ts1"),
            ("NVDA", 200, "ts2"),
        ])
        client.get_dark_pool_recent.side_effect = [page1, []]

        provider = UWBatchDarkPoolProvider(client, logger=logger, max_pages=5, page_delay=0)
        provider.prefetch()

        prefetch_events = [
            e for e in logger.events if e["event_type"] == "DATA_PREFETCH"
        ]
        assert len(prefetch_events) == 1
        assert "2 trades" in prefetch_events[0]["message"]
        assert "2 tickers" in prefetch_events[0]["message"]


# ============================================================================
# AsyncUWBatchDarkPoolProvider — async batch provider
# ============================================================================

class TestAsyncUWBatchDarkPoolProvider:
    def _make_records(self, tickers_sizes):
        records = []
        for ticker, size, ts in tickers_sizes:
            records.append({
                "ticker": ticker,
                "size": str(size),
                "price": "100.0",
                "nbbo_ask": "100.05",
                "nbbo_bid": "99.95",
                "executed_at": ts,
            })
        return records

    @pytest.mark.asyncio
    async def test_prefetch_groups_by_ticker(self, logger):
        """Async: 3 tickers mixed → correct grouping."""
        client = AsyncMock()
        page1 = self._make_records([
            ("AAPL", 100, "ts1"),
            ("NVDA", 200, "ts2"),
            ("AAPL", 150, "ts3"),
        ])
        client.get_dark_pool_recent.side_effect = [page1, []]

        provider = AsyncUWBatchDarkPoolProvider(client, logger=logger, max_pages=5, page_delay=0)
        await provider.prefetch()

        assert len(provider._cache["AAPL"]) == 2
        assert len(provider._cache["NVDA"]) == 1

    @pytest.mark.asyncio
    async def test_get_dark_pool_from_cache(self, logger):
        """Async: returns aggregated data for cached ticker."""
        client = AsyncMock()
        page1 = self._make_records([
            ("SPY", 500, "ts1"),
            ("SPY", 300, "ts2"),
        ])
        client.get_dark_pool_recent.side_effect = [page1, []]

        provider = AsyncUWBatchDarkPoolProvider(client, logger=logger, max_pages=5, page_delay=0)
        await provider.prefetch()
        result = await provider.get_dark_pool("SPY")

        assert result is not None
        assert result["dp_volume"] == 800

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, logger):
        """Async: ticker not in cache → None."""
        client = AsyncMock()
        client.get_dark_pool_recent.return_value = []

        provider = AsyncUWBatchDarkPoolProvider(client, logger=logger, max_pages=5, page_delay=0)
        await provider.prefetch()

        assert await provider.get_dark_pool("MISSING") is None

    @pytest.mark.asyncio
    async def test_auto_prefetch(self, logger):
        """Async: lazy prefetch on first get_dark_pool()."""
        client = AsyncMock()
        page1 = self._make_records([("TSLA", 1000, "ts1")])
        client.get_dark_pool_recent.side_effect = [page1, []]

        provider = AsyncUWBatchDarkPoolProvider(client, logger=logger, max_pages=5, page_delay=0)
        result = await provider.get_dark_pool("TSLA")

        assert result is not None
        assert result["dp_volume"] == 1000
        assert provider._prefetched is True

    def test_provider_name(self):
        """Returns 'unusual_whales_batch'."""
        client = AsyncMock()
        provider = AsyncUWBatchDarkPoolProvider(client)
        assert provider.provider_name() == "unusual_whales_batch"


# ============================================================================
# Regression: UWDarkPoolProvider still works after _aggregate_dp_records extraction
# ============================================================================

class TestUWDarkPoolProviderRefactored:
    def test_returns_bullish_signal(self):
        """Existing per-ticker provider still works."""
        client = MagicMock()
        client.get_dark_pool.return_value = [
            {"size": "500", "price": "150.20", "nbbo_ask": "150.15", "nbbo_bid": "150.05"},
            {"size": "300", "price": "150.12", "nbbo_ask": "150.15", "nbbo_bid": "150.05"},
        ]
        provider = UWDarkPoolProvider(client)
        result = provider.get_dark_pool("AAPL")

        assert result is not None
        assert result["signal"] == "BULLISH"
        assert result["dp_volume"] == 800
        assert result["source"] == "unusual_whales"

    def test_returns_none_when_no_data(self):
        """Still returns None when client returns None."""
        client = MagicMock()
        client.get_dark_pool.return_value = None
        provider = UWDarkPoolProvider(client)
        assert provider.get_dark_pool("FAIL") is None
