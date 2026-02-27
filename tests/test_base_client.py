"""Tests for BaseAPIClient retry logic (C6)."""

import pytest
from unittest.mock import MagicMock, patch
import requests

from ifds.data.base import BaseAPIClient


class ConcreteClient(BaseAPIClient):
    def __init__(self, **kwargs):
        super().__init__(base_url="https://api.example.com", **kwargs)


class TestBaseClientRetry:

    def test_retry_on_500_then_success(self):
        """Retry on 5xx, succeed on 2nd attempt."""
        client = ConcreteClient(max_retries=3, timeout=5)
        mock_resp_500 = MagicMock()
        mock_resp_500.status_code = 500
        mock_resp_500.raise_for_status.side_effect = requests.HTTPError(
            response=mock_resp_500
        )
        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200
        mock_resp_200.raise_for_status.return_value = None
        mock_resp_200.json.return_value = {"ok": True}

        with patch.object(client._session, 'get',
                          side_effect=[mock_resp_500, mock_resp_200]), \
             patch('time.sleep'):
            result = client._get("/test")
        assert result == {"ok": True}

    def test_no_retry_on_404(self):
        """4xx (except 429) — no retry, immediate return None."""
        client = ConcreteClient(max_retries=3, timeout=5)
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = requests.HTTPError(
            response=mock_resp
        )

        with patch.object(client._session, 'get', return_value=mock_resp) as mock_get:
            result = client._get("/test")
        assert result is None
        assert mock_get.call_count == 1  # no retry

    def test_retry_on_429_rate_limit(self):
        """429 rate limit triggers retry."""
        client = ConcreteClient(max_retries=3, timeout=5)
        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429
        mock_resp_429.raise_for_status.side_effect = requests.HTTPError(
            response=mock_resp_429
        )
        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200
        mock_resp_200.raise_for_status.return_value = None
        mock_resp_200.json.return_value = {"ok": True}

        with patch.object(client._session, 'get',
                          side_effect=[mock_resp_429, mock_resp_200]), \
             patch('time.sleep'):
            result = client._get("/test")
        assert result == {"ok": True}

    def test_all_retries_exhausted_returns_none(self):
        """All retries fail → return None, no exception raised."""
        client = ConcreteClient(max_retries=3, timeout=5)
        with patch.object(client._session, 'get',
                          side_effect=requests.exceptions.ConnectionError("refused")), \
             patch('time.sleep'):
            result = client._get("/test")
        assert result is None

    def test_timeout_triggers_retry(self):
        """Timeout triggers retry up to max_retries."""
        client = ConcreteClient(max_retries=2, timeout=5)
        with patch.object(client._session, 'get',
                          side_effect=requests.exceptions.Timeout()), \
             patch('time.sleep') as mock_sleep:
            result = client._get("/test")
        assert result is None
        assert mock_sleep.call_count == 1  # sleep between attempt 1 and 2
