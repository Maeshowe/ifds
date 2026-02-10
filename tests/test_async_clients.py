"""Tests for async API clients (AsyncBaseAPIClient + provider clients)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ifds.data.async_base import AsyncBaseAPIClient
from ifds.data.async_clients import (
    AsyncFMPClient,
    AsyncFREDClient,
    AsyncPolygonClient,
    AsyncUWClient,
)
from ifds.models.market import APIStatus


# ============================================================================
# AsyncBaseAPIClient
# ============================================================================

class TestAsyncBaseClient:
    """Tests for the async base client."""

    @pytest.mark.asyncio
    async def test_get_success(self):
        """Successful GET returns parsed JSON."""
        client = AsyncBaseAPIClient(
            base_url="https://example.com",
            api_key="test",
            provider_name="test",
        )
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"results": [1, 2, 3]})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.closed = False
        client._session = mock_session

        result = await client._get("/test")
        assert result == {"results": [1, 2, 3]}
        await client.close()

    @pytest.mark.asyncio
    async def test_get_returns_none_on_4xx(self):
        """4xx errors return None without retry."""
        client = AsyncBaseAPIClient(
            base_url="https://example.com",
            api_key="test",
            max_retries=3,
            provider_name="test",
        )
        mock_resp = AsyncMock()
        mock_resp.status = 404
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.closed = False
        client._session = mock_session

        result = await client._get("/missing")
        assert result is None
        # 4xx should not retry — only 1 call
        assert mock_session.get.call_count == 1
        await client.close()

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """Semaphore limits concurrent requests."""
        sem = asyncio.Semaphore(2)
        client = AsyncBaseAPIClient(
            base_url="https://example.com",
            api_key="test",
            provider_name="test",
            semaphore=sem,
        )

        concurrent = 0
        max_concurrent = 0

        original_get = client._get

        async def tracking_get(*args, **kwargs):
            nonlocal concurrent, max_concurrent
            concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)
            await asyncio.sleep(0.01)
            concurrent -= 1
            return {"ok": True}

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"ok": True})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.closed = False
        client._session = mock_session

        tasks = [client._get(f"/test/{i}") for i in range(5)]
        await asyncio.gather(*tasks)
        await client.close()

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """Closing a client twice doesn't raise."""
        client = AsyncBaseAPIClient(
            base_url="https://example.com",
            provider_name="test",
        )
        await client.close()  # No session yet
        await client.close()  # Still no error


# ============================================================================
# AsyncPolygonClient
# ============================================================================

class TestAsyncPolygonClient:

    @pytest.mark.asyncio
    async def test_get_aggregates(self):
        """get_aggregates extracts results from response."""
        client = AsyncPolygonClient(api_key="test_key")
        client._get = AsyncMock(return_value={
            "results": [
                {"o": 100, "h": 105, "l": 99, "c": 103, "v": 10000},
            ],
            "resultsCount": 1,
        })

        result = await client.get_aggregates("AAPL", "2026-01-01", "2026-02-01")
        assert len(result) == 1
        assert result[0]["c"] == 103
        await client.close()

    @pytest.mark.asyncio
    async def test_get_aggregates_returns_none_on_failure(self):
        """Returns None when API returns no results."""
        client = AsyncPolygonClient(api_key="test_key")
        client._get = AsyncMock(return_value=None)

        result = await client.get_aggregates("AAPL", "2026-01-01", "2026-02-01")
        assert result is None
        await client.close()

    @pytest.mark.asyncio
    async def test_get_options_snapshot(self):
        """get_options_snapshot extracts results."""
        client = AsyncPolygonClient(api_key="test_key")
        client._get = AsyncMock(return_value={
            "results": [{"details": {"strike_price": 150}}],
        })

        result = await client.get_options_snapshot("AAPL")
        assert len(result) == 1
        await client.close()

    @pytest.mark.asyncio
    async def test_auth_headers(self):
        """Polygon uses Bearer token auth."""
        client = AsyncPolygonClient(api_key="my_key")
        assert client._auth_headers() == {"Authorization": "Bearer my_key"}
        await client.close()


# ============================================================================
# AsyncFMPClient
# ============================================================================

class TestAsyncFMPClient:

    @pytest.mark.asyncio
    async def test_get_financial_growth(self):
        """get_financial_growth returns first element."""
        client = AsyncFMPClient(api_key="test_key")
        client._get = AsyncMock(return_value=[
            {"revenueGrowth": 0.15, "epsgrowth": 0.20},
        ])

        result = await client.get_financial_growth("AAPL")
        assert result["revenueGrowth"] == 0.15
        await client.close()

    @pytest.mark.asyncio
    async def test_get_key_metrics(self):
        """get_key_metrics returns first element."""
        client = AsyncFMPClient(api_key="test_key")
        client._get = AsyncMock(return_value=[
            {"roeTTM": 0.25, "debtToEquityTTM": 1.5},
        ])

        result = await client.get_key_metrics("AAPL")
        assert result["roeTTM"] == 0.25
        await client.close()

    @pytest.mark.asyncio
    async def test_get_insider_trading(self):
        """get_insider_trading returns list."""
        client = AsyncFMPClient(api_key="test_key")
        client._get = AsyncMock(return_value=[
            {"transactionDate": "2026-01-15", "acquistionOrDisposition": "A"},
        ])

        result = await client.get_insider_trading("AAPL")
        assert len(result) == 1
        await client.close()

    @pytest.mark.asyncio
    async def test_returns_none_on_empty(self):
        """Returns None when API returns empty list."""
        client = AsyncFMPClient(api_key="test_key")
        client._get = AsyncMock(return_value=[])

        result = await client.get_financial_growth("AAPL")
        assert result is None
        await client.close()


# ============================================================================
# AsyncUWClient
# ============================================================================

class TestAsyncUWClient:

    @pytest.mark.asyncio
    async def test_get_dark_pool(self):
        """get_dark_pool returns data from response."""
        client = AsyncUWClient(api_key="test_key")
        client._get = AsyncMock(return_value={
            "data": [{"ticker": "AAPL", "size": 10000}],
        })

        result = await client.get_dark_pool("AAPL")
        assert len(result) == 1
        assert result[0]["size"] == 10000
        await client.close()

    @pytest.mark.asyncio
    async def test_returns_none_without_key(self):
        """Returns None if no API key configured."""
        client = AsyncUWClient(api_key=None)
        result = await client.get_dark_pool("AAPL")
        assert result is None
        await client.close()

    @pytest.mark.asyncio
    async def test_get_greeks(self):
        """get_greeks unwraps data field."""
        client = AsyncUWClient(api_key="test_key")
        client._get = AsyncMock(return_value={
            "data": [{"call_gamma": 1500.0, "put_gamma": 800.0}],
        })

        result = await client.get_greeks("AAPL")
        assert result["call_gamma"] == 1500.0
        await client.close()

    @pytest.mark.asyncio
    async def test_auth_headers(self):
        """UW uses Bearer + User-Agent."""
        client = AsyncUWClient(api_key="my_key")
        headers = client._auth_headers()
        assert headers["Authorization"] == "Bearer my_key"
        assert headers["User-Agent"] == "PythonClient"
        await client.close()

    @pytest.mark.asyncio
    async def test_health_skipped_without_key(self):
        """Health check returns SKIPPED without API key."""
        client = AsyncUWClient(api_key=None)
        result = await client.check_health()
        assert result.status == APIStatus.SKIPPED
        await client.close()


# ============================================================================
# AsyncFREDClient
# ============================================================================

class TestAsyncFREDClient:

    @pytest.mark.asyncio
    async def test_get_vix(self):
        """get_vix extracts observations."""
        client = AsyncFREDClient(api_key="test_key")
        client._get = AsyncMock(return_value={
            "observations": [{"date": "2026-02-07", "value": "17.80"}],
        })

        result = await client.get_vix(limit=1)
        assert len(result) == 1
        assert result[0]["value"] == "17.80"
        await client.close()

    @pytest.mark.asyncio
    async def test_get_tnx(self):
        """get_tnx extracts observations."""
        client = AsyncFREDClient(api_key="test_key")
        client._get = AsyncMock(return_value={
            "observations": [{"date": "2026-02-07", "value": "4.21"}],
        })

        result = await client.get_tnx(limit=1)
        assert result[0]["value"] == "4.21"
        await client.close()

    @pytest.mark.asyncio
    async def test_returns_none_on_missing_observations(self):
        """Returns None when no observations key."""
        client = AsyncFREDClient(api_key="test_key")
        client._get = AsyncMock(return_value={})

        result = await client.get_series("VIXCLS")
        assert result is None
        await client.close()
