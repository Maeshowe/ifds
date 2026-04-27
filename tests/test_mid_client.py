"""Unit tests for MIDClient (shadow-mode bundle fetch).

Mirrors the mocking pattern used by tests for unusual_whales / fred —
``httpx.get`` is patched, no real network.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import httpx
import pytest


@pytest.fixture
def sample_bundle() -> dict:
    """Mirrors the live /api/bundle/latest response on 2026-04-27."""
    return {
        "flat": {
            "regime": "Stagflation",
            "confidence": 0.10108678936284508,
            "growth": 0.23928571428571432,
            "inflation": 0.8131968789560814,
            "policy": 0.5121441478933665,
            "growth_dir": "flat",
            "inflation_dir": "flat",
            "policy_dir": "flat",
            "tpi": 43.0,
            "rpi": 47.264515035168216,
            "esi": 0.2232,
            "esi_label": "neutral",
            "yield_curve_regime": "bull_steepener",
            "s2s10_bps": 50.99999999999998,
            "top_sectors": ["XLK", "XLE", "XLB"],
            "bottom_sectors": ["XLV", "XLF", "XLY"],
            "as_of_date": "2026-04-27",
            "age_days": 11,
        },
        "engines": {
            "tpi": {
                "state": "HIGH",
                "description": "Significant pressure. Multiple systems near thresholds.",
            },
        },
        "etf_xray": {
            "sectors": [
                {"etf": "XLK", "consensus_state": "OVERWEIGHT", "score": 88},
                {"etf": "XLE", "consensus_state": "ACCUMULATING", "score": 72},
                {"etf": "XLU", "consensus_state": "UNDERWEIGHT", "score": 22},
            ],
        },
    }


def _ok_response(payload: dict) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = payload
    return resp


class TestMidClientAuth:
    """X-API-Key header is required on every /api/* request."""

    def test_no_api_key_returns_empty(self) -> None:
        from ifds.data.mid_client import MIDClient

        client = MIDClient(api_key=None)
        assert client.get_bundle() == {}

    def test_headers_include_x_api_key(self, sample_bundle: dict) -> None:
        from ifds.data.mid_client import MIDClient

        with patch("ifds.data.mid_client.httpx.get") as mock_get:
            mock_get.return_value = _ok_response(sample_bundle)
            client = MIDClient(api_key="fake-key")
            client.get_bundle()

        call = mock_get.call_args
        headers = call.kwargs.get("headers") or call[1].get("headers")
        assert headers["X-API-Key"] == "fake-key"
        assert headers["Accept"] == "application/json"


class TestMidClientCache:
    """Two consecutive calls within TTL hit the cache (one HTTP fetch)."""

    def test_cache_within_ttl(self, sample_bundle: dict) -> None:
        from ifds.data.mid_client import MIDClient

        with patch("ifds.data.mid_client.httpx.get") as mock_get:
            mock_get.return_value = _ok_response(sample_bundle)
            client = MIDClient(api_key="fake-key")
            first = client.get_bundle()
            second = client.get_bundle()

        assert first == second == sample_bundle
        assert mock_get.call_count == 1

    def test_force_refresh_bypasses_cache(self, sample_bundle: dict) -> None:
        from ifds.data.mid_client import MIDClient

        with patch("ifds.data.mid_client.httpx.get") as mock_get:
            mock_get.return_value = _ok_response(sample_bundle)
            client = MIDClient(api_key="fake-key")
            client.get_bundle()
            client.get_bundle(force_refresh=True)

        assert mock_get.call_count == 2

    def test_cache_expires_after_ttl(self, sample_bundle: dict) -> None:
        from ifds.data.mid_client import MIDClient

        with patch("ifds.data.mid_client.httpx.get") as mock_get:
            mock_get.return_value = _ok_response(sample_bundle)
            client = MIDClient(api_key="fake-key")
            client.get_bundle()
            # Simulate TTL expiry by backdating the timestamp
            client._cache_ts = (client._cache_ts or time.time()) - (
                client.CACHE_TTL_SECONDS + 1
            )
            client.get_bundle()

        assert mock_get.call_count == 2


class TestMidClientFailure:
    """Any failure mode returns an empty dict — non-fatal."""

    def test_network_timeout(self) -> None:
        from ifds.data.mid_client import MIDClient

        with patch("ifds.data.mid_client.httpx.get",
                   side_effect=httpx.TimeoutException("slow")):
            client = MIDClient(api_key="fake-key")
            assert client.get_bundle() == {}

    def test_http_4xx(self) -> None:
        from ifds.data.mid_client import MIDClient

        bad_resp = MagicMock(spec=httpx.Response)
        bad_resp.status_code = 401
        bad_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "unauthorized", request=MagicMock(), response=bad_resp,
        )
        with patch("ifds.data.mid_client.httpx.get", return_value=bad_resp):
            client = MIDClient(api_key="bad-key")
            assert client.get_bundle() == {}

    def test_malformed_json(self) -> None:
        from ifds.data.mid_client import MIDClient

        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.side_effect = ValueError("not json")

        with patch("ifds.data.mid_client.httpx.get", return_value=resp):
            client = MIDClient(api_key="fake-key")
            assert client.get_bundle() == {}

    def test_non_dict_payload(self) -> None:
        from ifds.data.mid_client import MIDClient

        with patch("ifds.data.mid_client.httpx.get",
                   return_value=_ok_response(["not", "a", "dict"])):
            client = MIDClient(api_key="fake-key")
            assert client.get_bundle() == {}


class TestMidClientHelpers:
    """get_sectors / get_regime extract from bundle defensively."""

    def test_get_sectors(self, sample_bundle: dict) -> None:
        from ifds.data.mid_client import MIDClient

        with patch("ifds.data.mid_client.httpx.get",
                   return_value=_ok_response(sample_bundle)):
            client = MIDClient(api_key="fake-key")
            sectors = client.get_sectors()

        assert len(sectors) == 3
        assert sectors[0]["etf"] == "XLK"

    def test_get_sectors_missing_field(self) -> None:
        from ifds.data.mid_client import MIDClient

        with patch("ifds.data.mid_client.httpx.get",
                   return_value=_ok_response({"flat": {}})):
            client = MIDClient(api_key="fake-key")
            assert client.get_sectors() == []

    def test_get_regime(self, sample_bundle: dict) -> None:
        from ifds.data.mid_client import MIDClient

        with patch("ifds.data.mid_client.httpx.get",
                   return_value=_ok_response(sample_bundle)):
            client = MIDClient(api_key="fake-key")
            regime = client.get_regime()

        # Original 8 fields (unchanged behavior)
        assert regime["regime"] == "Stagflation"
        assert regime["tpi_score"] == 43.0
        assert regime["tpi_state"] == "HIGH"
        assert regime["growth"] == pytest.approx(0.2392857, rel=1e-5)
        assert regime["inflation"] == pytest.approx(0.8131969, rel=1e-5)
        assert regime["policy"] == pytest.approx(0.5121441, rel=1e-5)
        assert regime["rpi"] == pytest.approx(47.2645150, rel=1e-5)
        assert regime["esi"] == 0.2232

    def test_get_regime_new_fields(self, sample_bundle: dict) -> None:
        """Verify the 12 new fields added per live API verification (2026-04-27)."""
        from ifds.data.mid_client import MIDClient

        with patch("ifds.data.mid_client.httpx.get",
                   return_value=_ok_response(sample_bundle)):
            client = MIDClient(api_key="fake-key")
            regime = client.get_regime()

        assert regime["confidence"] == pytest.approx(0.10108679, rel=1e-5)
        assert regime["growth_dir"] == "flat"
        assert regime["inflation_dir"] == "flat"
        assert regime["policy_dir"] == "flat"
        assert regime["tpi_description"].startswith("Significant pressure")
        assert regime["esi_label"] == "neutral"
        assert regime["yield_curve_regime"] == "bull_steepener"
        assert regime["s2s10_bps"] == pytest.approx(51.0, rel=1e-3)
        assert regime["top_sectors"] == ["XLK", "XLE", "XLB"]
        assert regime["bottom_sectors"] == ["XLV", "XLF", "XLY"]
        assert regime["as_of_date"] == "2026-04-27"
        assert regime["age_days"] == 11

    def test_get_regime_alternate_field_paths(self) -> None:
        """yc_regime/s2s10/bundle-level top_sectors fallbacks."""
        from ifds.data.mid_client import MIDClient

        bundle = {
            "flat": {
                "regime": "Goldilocks",
                "yc_regime": "bear_flattener",
                "s2s10": 12.5,
            },
            "top_sectors": ["XLY"],
            "bottom_sectors": ["XLP"],
            "as_of_date": "2026-04-28",
            "age_days": 0,
        }
        with patch("ifds.data.mid_client.httpx.get",
                   return_value=_ok_response(bundle)):
            client = MIDClient(api_key="fake-key")
            regime = client.get_regime()

        assert regime["yield_curve_regime"] == "bear_flattener"
        assert regime["s2s10_bps"] == 12.5
        assert regime["top_sectors"] == ["XLY"]
        assert regime["bottom_sectors"] == ["XLP"]
        assert regime["as_of_date"] == "2026-04-28"
        assert regime["age_days"] == 0

    def test_get_regime_missing_optional_fields(self) -> None:
        """Missing fields ⇒ None for scalars, [] for sector lists."""
        from ifds.data.mid_client import MIDClient

        with patch("ifds.data.mid_client.httpx.get",
                   return_value=_ok_response({"flat": {"regime": "Goldilocks"}})):
            client = MIDClient(api_key="fake-key")
            regime = client.get_regime()

        assert regime["regime"] == "Goldilocks"
        assert regime["confidence"] is None
        assert regime["tpi_description"] is None
        assert regime["yield_curve_regime"] is None
        assert regime["s2s10_bps"] is None
        assert regime["top_sectors"] == []
        assert regime["bottom_sectors"] == []
        assert regime["as_of_date"] is None
        assert regime["age_days"] is None

    def test_get_regime_empty_bundle(self) -> None:
        from ifds.data.mid_client import MIDClient

        client = MIDClient(api_key=None)
        assert client.get_regime() == {}
