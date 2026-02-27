"""Tests for AsyncBaseAPIClient retry logic (C7)."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from ifds.data.async_base import AsyncBaseAPIClient


class ConcreteAsyncClient(AsyncBaseAPIClient):
    def __init__(self, **kwargs):
        super().__init__(base_url="https://api.example.com", **kwargs)


def _make_response(status, json_data=None):
    """Create a mock aiohttp response as async context manager."""
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data)
    # Make it work as async context manager
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _setup_client(max_retries=3, timeout=5):
    """Create client with mock session properly configured."""
    client = ConcreteAsyncClient(max_retries=max_retries, timeout=timeout)
    mock_session = MagicMock()
    mock_session.closed = False  # prevent _ensure_session from creating real session
    client._session = mock_session
    return client, mock_session


class TestAsyncBaseClientRetry:

    @pytest.mark.asyncio
    async def test_retry_on_500_then_success(self):
        """Retry on 5xx, succeed on 2nd attempt."""
        client, mock_session = _setup_client(max_retries=3)
        mock_session.get = MagicMock(side_effect=[
            _make_response(500),
            _make_response(200, {"ok": True}),
        ])

        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await client._get("/test")
        assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_no_retry_on_404(self):
        """4xx (except 429) — no retry."""
        client, mock_session = _setup_client(max_retries=3)
        mock_session.get = MagicMock(return_value=_make_response(404))

        result = await client._get("/test")
        assert result is None
        assert mock_session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_429_rate_limit(self):
        """429 rate limit triggers retry."""
        client, mock_session = _setup_client(max_retries=3)
        mock_session.get = MagicMock(side_effect=[
            _make_response(429),
            _make_response(200, {"data": "ok"}),
        ])

        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await client._get("/test")
        assert result == {"data": "ok"}

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_returns_none(self):
        """All retries fail → None, no exception."""
        client, mock_session = _setup_client(max_retries=2)
        mock_session.get = MagicMock(
            side_effect=aiohttp.ClientConnectionError("refused")
        )

        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await client._get("/test")
        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_triggers_retry(self):
        """asyncio.TimeoutError triggers retry."""
        client, mock_session = _setup_client(max_retries=2)
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())

        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await client._get("/test")
        assert result is None
        assert mock_sleep.call_count == 1
