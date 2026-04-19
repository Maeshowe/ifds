"""Regression tests for UW Client Quick Wins (2026-04-17).

Covers:
- UW-CLIENT-API-ID header added to both sync and async auth headers
- _aggregate_dp_records() emits dp_volume_dollars and block_trade_dollars
- Existing fields (dp_volume shares, dp_pct) unchanged for backward compat
"""
from __future__ import annotations


class TestUwAuthHeaders:
    """Fix #1: UW-CLIENT-API-ID: 100001 is required by the UW API spec."""

    def test_sync_headers_include_client_api_id(self):
        from ifds.data.unusual_whales import UnusualWhalesClient

        client = UnusualWhalesClient(api_key="fake-key")
        headers = client._auth_headers()
        try:
            assert headers["UW-CLIENT-API-ID"] == "100001"
            assert headers["Authorization"] == "Bearer fake-key"
            assert headers["Accept"] == "application/json"
        finally:
            client.close()

    def test_sync_headers_empty_without_key(self):
        from ifds.data.unusual_whales import UnusualWhalesClient

        client = UnusualWhalesClient(api_key=None)
        try:
            assert client._auth_headers() == {}
        finally:
            client.close()

    def test_async_headers_include_client_api_id(self):
        from ifds.data.async_clients import AsyncUWClient

        client = AsyncUWClient(api_key="fake-key")
        headers = client._auth_headers()
        assert headers["UW-CLIENT-API-ID"] == "100001"
        assert headers["Authorization"] == "Bearer fake-key"
        assert headers["Accept"] == "application/json"


class TestAggregateDpRecordsNewFields:
    """Fix #3: premium aggregation + block_trade_dollars."""

    def test_premium_summed_into_dp_volume_dollars(self):
        from ifds.data.adapters import _aggregate_dp_records

        records = [
            {"size": 100, "price": 150.0, "premium": 15_000.0,
             "volume": 10_000_000, "nbbo_ask": 150.5, "nbbo_bid": 149.5},
            {"size": 200, "price": 150.0, "premium": 30_000.0,
             "volume": 10_000_000, "nbbo_ask": 150.5, "nbbo_bid": 149.5},
        ]
        result = _aggregate_dp_records(records)
        assert result["dp_volume_dollars"] == 45_000.0
        assert result["dp_volume"] == 300  # shares unchanged

    def test_block_trade_dollars_summed(self):
        """Trades with notional > $500K contribute to block_trade_dollars."""
        from ifds.data.adapters import _aggregate_dp_records

        records = [
            # Block trade: 10000 × 100 = $1M > $500K
            {"size": 10_000, "price": 100.0, "premium": 1_000_000.0,
             "volume": 50_000_000, "nbbo_ask": 100.1, "nbbo_bid": 99.9},
            # Non-block: 100 × 100 = $10K < $500K
            {"size": 100, "price": 100.0, "premium": 10_000.0,
             "volume": 50_000_000, "nbbo_ask": 100.1, "nbbo_bid": 99.9},
            # Block trade: 5000 × 200 = $1M > $500K
            {"size": 5_000, "price": 200.0, "premium": 1_000_000.0,
             "volume": 50_000_000, "nbbo_ask": 200.1, "nbbo_bid": 199.9},
        ]
        result = _aggregate_dp_records(records)
        assert result["block_trade_count"] == 2
        assert result["block_trade_dollars"] == 2_000_000.0

    def test_existing_fields_unchanged(self):
        """Backward compatibility — old fields still present and correct."""
        from ifds.data.adapters import _aggregate_dp_records

        records = [
            {"size": 500, "price": 100.0, "premium": 50_000.0,
             "volume": 1_000_000, "nbbo_ask": 100.5, "nbbo_bid": 99.5},
        ]
        result = _aggregate_dp_records(records)
        # Pre-existing fields untouched
        assert "dp_volume" in result
        assert "dp_pct" in result
        assert "dp_buys" in result
        assert "dp_sells" in result
        assert "signal" in result
        assert "block_trade_count" in result
        assert "venue_entropy" in result
        # New fields present (non-breaking addition)
        assert "dp_volume_dollars" in result
        assert "block_trade_dollars" in result

    def test_empty_records_zero_dollars(self):
        from ifds.data.adapters import _aggregate_dp_records

        result = _aggregate_dp_records([])
        assert result["dp_volume_dollars"] == 0.0
        assert result["block_trade_dollars"] == 0.0

    def test_missing_premium_defaults_to_zero(self):
        """Records without premium field should not crash — treated as 0."""
        from ifds.data.adapters import _aggregate_dp_records

        records = [
            {"size": 100, "price": 50.0, "volume": 10_000,
             "nbbo_ask": 50.1, "nbbo_bid": 49.9},  # no premium
        ]
        result = _aggregate_dp_records(records)
        assert result["dp_volume_dollars"] == 0.0
        assert result["dp_volume"] == 100  # still counted in shares
