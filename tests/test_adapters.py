"""Tests for data provider adapters and fallback logic."""

import pytest
from unittest.mock import MagicMock

from ifds.data.adapters import (
    FallbackGEXProvider, FallbackDarkPoolProvider,
    UWGEXProvider, PolygonGEXProvider,
    UWDarkPoolProvider,
)
from ifds.events.logger import EventLogger


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="adapter-test")


class TestFallbackGEXProvider:
    def test_uses_primary_when_available(self, logger):
        """When primary (UW) returns data, use it."""
        primary = MagicMock()
        primary.get_gex.return_value = {"net_gex": 1000, "source": "unusual_whales"}
        primary.provider_name.return_value = "unusual_whales"

        fallback = MagicMock()
        fallback.provider_name.return_value = "polygon"

        provider = FallbackGEXProvider(primary, fallback, logger=logger)
        result = provider.get_gex("NVDA")

        assert result["source"] == "unusual_whales"
        primary.get_gex.assert_called_once_with("NVDA")
        fallback.get_gex.assert_not_called()

    def test_falls_back_when_primary_returns_none(self, logger):
        """When primary (UW) returns None, fall back to Polygon."""
        primary = MagicMock()
        primary.get_gex.return_value = None
        primary.provider_name.return_value = "unusual_whales"

        fallback = MagicMock()
        fallback.get_gex.return_value = {"net_gex": 500, "source": "polygon_calculated"}
        fallback.provider_name.return_value = "polygon"

        provider = FallbackGEXProvider(primary, fallback, logger=logger)
        result = provider.get_gex("NVDA")

        assert result["source"] == "polygon_calculated"
        primary.get_gex.assert_called_once()
        fallback.get_gex.assert_called_once_with("NVDA")

    def test_logs_fallback_event(self, logger):
        """Fallback should be logged for audit trail."""
        primary = MagicMock()
        primary.get_gex.return_value = None
        primary.provider_name.return_value = "unusual_whales"

        fallback = MagicMock()
        fallback.get_gex.return_value = {"net_gex": 0}
        fallback.provider_name.return_value = "polygon"

        provider = FallbackGEXProvider(primary, fallback, logger=logger)
        provider.get_gex("AAPL")

        # Check that a fallback event was logged
        fallback_events = [
            e for e in logger.events if e["event_type"] == "API_FALLBACK"
        ]
        assert len(fallback_events) == 1
        assert fallback_events[0]["data"]["primary"] == "unusual_whales"
        assert fallback_events[0]["data"]["fallback"] == "polygon"

    def test_returns_none_when_both_fail(self, logger):
        """When both primary and fallback return None."""
        primary = MagicMock()
        primary.get_gex.return_value = None
        primary.provider_name.return_value = "unusual_whales"

        fallback = MagicMock()
        fallback.get_gex.return_value = None
        fallback.provider_name.return_value = "polygon"

        provider = FallbackGEXProvider(primary, fallback, logger=logger)
        result = provider.get_gex("FAIL")

        assert result is None

    def test_provider_name_combined(self):
        primary = MagicMock()
        primary.provider_name.return_value = "unusual_whales"
        fallback = MagicMock()
        fallback.provider_name.return_value = "polygon"

        provider = FallbackGEXProvider(primary, fallback)
        assert provider.provider_name() == "unusual_whales+polygon"


class TestFallbackDarkPoolProvider:
    def test_uses_primary_when_available(self, logger):
        primary = MagicMock()
        primary.get_dark_pool.return_value = {
            "dp_volume": 1000000, "signal": "BULLISH", "source": "unusual_whales"
        }
        primary.provider_name.return_value = "unusual_whales"

        provider = FallbackDarkPoolProvider(primary, logger=logger)
        result = provider.get_dark_pool("NVDA")

        assert result["signal"] == "BULLISH"

    def test_returns_none_when_primary_fails(self, logger):
        """Dark Pool has no fallback — returns None if UW fails."""
        primary = MagicMock()
        primary.get_dark_pool.return_value = None
        primary.provider_name.return_value = "unusual_whales"

        provider = FallbackDarkPoolProvider(primary, logger=logger)
        result = provider.get_dark_pool("NVDA")

        assert result is None

    def test_logs_no_fallback_available(self, logger):
        primary = MagicMock()
        primary.get_dark_pool.return_value = None
        primary.provider_name.return_value = "unusual_whales"

        provider = FallbackDarkPoolProvider(primary, logger=logger)
        provider.get_dark_pool("AAPL")

        fallback_events = [
            e for e in logger.events if e["event_type"] == "API_FALLBACK"
        ]
        assert len(fallback_events) == 1
        assert fallback_events[0]["data"]["fallback"] == "none"


class TestUWGEXProvider:
    def test_returns_gex_from_per_strike_data(self):
        """UW per-strike endpoint → full GEX dict with walls and zero_gamma."""
        uw_client = MagicMock()
        uw_client.get_greek_exposure_by_strike.return_value = [
            {"strike": "150", "call_gamma": "5000000", "put_gamma": "-8000000"},
            {"strike": "155", "call_gamma": "9000000", "put_gamma": "-3000000"},
            {"strike": "160", "call_gamma": "7000000", "put_gamma": "-2000000"},
        ]

        provider = UWGEXProvider(uw_client)
        result = provider.get_gex("AAPL")

        assert result is not None
        assert result["source"] == "unusual_whales"
        assert result["call_wall"] == 155  # max call_gamma
        assert result["put_wall"] == 150   # max |put_gamma|
        assert "zero_gamma" in result
        assert "net_gex" in result
        assert len(result["gex_by_strike"]) == 3

    def test_net_gex_calculation(self):
        """net_gex = sum(call_gamma + put_gamma) per strike."""
        uw_client = MagicMock()
        uw_client.get_greek_exposure_by_strike.return_value = [
            {"strike": "100", "call_gamma": "10000", "put_gamma": "-4000"},
            {"strike": "110", "call_gamma": "8000", "put_gamma": "-6000"},
        ]

        provider = UWGEXProvider(uw_client)
        result = provider.get_gex("TEST")

        # (10000-4000) + (8000-6000) = 6000 + 2000 = 8000
        assert result["net_gex"] == 8000.0

    def test_zero_gamma_included(self):
        """Result includes zero_gamma field as float."""
        uw_client = MagicMock()
        uw_client.get_greek_exposure_by_strike.return_value = [
            {"strike": "100", "call_gamma": "3000", "put_gamma": "-1000"},
            {"strike": "110", "call_gamma": "1000", "put_gamma": "-5000"},
        ]

        provider = UWGEXProvider(uw_client)
        result = provider.get_gex("TEST")

        assert isinstance(result["zero_gamma"], float)
        assert result["zero_gamma"] > 0

    def test_returns_none_when_no_strike_data(self):
        """Client returns None → provider returns None."""
        uw_client = MagicMock()
        uw_client.get_greek_exposure_by_strike.return_value = None

        provider = UWGEXProvider(uw_client)
        assert provider.get_gex("FAIL") is None

    def test_empty_strike_data_returns_none(self):
        """Empty list → no strikes to process → None."""
        uw_client = MagicMock()
        uw_client.get_greek_exposure_by_strike.return_value = []

        provider = UWGEXProvider(uw_client)
        assert provider.get_gex("FAIL") is None

    def test_all_zero_gamma_returns_none(self):
        """All strikes have zero gamma → no useful data → None."""
        uw_client = MagicMock()
        uw_client.get_greek_exposure_by_strike.return_value = [
            {"strike": "150", "call_gamma": "0", "put_gamma": "0"},
        ]

        provider = UWGEXProvider(uw_client)
        assert provider.get_gex("FLAT") is None

    def test_string_values_converted(self):
        """All UW values are strings — must be converted to float."""
        uw_client = MagicMock()
        uw_client.get_greek_exposure_by_strike.return_value = [
            {"strike": "152.5", "call_gamma": "9356683.42", "put_gamma": "-12337386.05"},
        ]

        provider = UWGEXProvider(uw_client)
        result = provider.get_gex("SPY")

        assert result is not None
        assert result["call_wall"] == 152.5
        assert result["put_wall"] == 152.5
        assert result["net_gex"] == pytest.approx(9356683.42 + (-12337386.05))
