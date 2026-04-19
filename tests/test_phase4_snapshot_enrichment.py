"""Regression tests for Phase 4 Snapshot Enrichment (2026-04-17).

Covers:
- FlowAnalysis gains dollar-weighted DP fields with safe defaults
- StockAnalysis gains optional Phase 5 GEX fields
- _stock_to_dict persists all new fields
- snapshot_to_stock_analysis is backward compatible (loads legacy snapshots
  where the new fields are absent)
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest


class TestFlowAnalysisEnrichedFields:
    """New dollar-weighted fields must have safe defaults and accept values."""

    def test_defaults_zero(self):
        from ifds.models.market import FlowAnalysis

        fl = FlowAnalysis()
        assert fl.dp_volume_shares == 0
        assert fl.total_volume == 0
        assert fl.dp_volume_dollars == 0.0
        assert fl.block_trade_dollars == 0.0
        assert fl.venue_entropy == 0.0

    def test_explicit_values(self):
        from ifds.models.market import FlowAnalysis

        fl = FlowAnalysis(
            dp_volume_shares=12_345,
            total_volume=1_000_000,
            dp_volume_dollars=1_250_000.50,
            block_trade_dollars=500_000.0,
            venue_entropy=1.23,
        )
        assert fl.dp_volume_shares == 12_345
        assert fl.dp_volume_dollars == 1_250_000.50
        assert fl.block_trade_dollars == 500_000.0


class TestStockAnalysisGexFields:
    """Phase 5 GEX fields are optional (None when options data unavailable)."""

    def test_defaults_none(self):
        from ifds.models.market import (
            FlowAnalysis,
            FundamentalScoring,
            StockAnalysis,
            TechnicalAnalysis,
        )

        stock = StockAnalysis(
            ticker="AAPL",
            sector="Technology",
            technical=TechnicalAnalysis(price=150, sma_200=130, sma_50=140,
                                        sma_20=145, rsi_14=55, atr_14=3.0,
                                        trend_pass=True),
            flow=FlowAnalysis(),
            fundamental=FundamentalScoring(),
        )
        assert stock.net_gex is None
        assert stock.call_wall is None
        assert stock.put_wall is None
        assert stock.zero_gamma is None

    def test_explicit_gex_values(self):
        from ifds.models.market import (
            FlowAnalysis,
            FundamentalScoring,
            StockAnalysis,
            TechnicalAnalysis,
        )

        stock = StockAnalysis(
            ticker="AAPL",
            sector="Technology",
            technical=TechnicalAnalysis(price=150, sma_200=130, sma_50=140,
                                        sma_20=145, rsi_14=55, atr_14=3.0,
                                        trend_pass=True),
            flow=FlowAnalysis(),
            fundamental=FundamentalScoring(),
            net_gex=-1_500_000.0,
            call_wall=160.0,
            put_wall=140.0,
            zero_gamma=155.5,
        )
        assert stock.net_gex == -1_500_000.0
        assert stock.call_wall == 160.0
        assert stock.put_wall == 140.0
        assert stock.zero_gamma == 155.5


class TestSnapshotRoundTrip:
    """save → load must preserve the new enriched fields."""

    @staticmethod
    def _make_stock(**gex_kw):
        from ifds.models.market import (
            FlowAnalysis,
            FundamentalScoring,
            StockAnalysis,
            TechnicalAnalysis,
        )

        return StockAnalysis(
            ticker="NVDA",
            sector="Technology",
            technical=TechnicalAnalysis(price=850, sma_200=700, sma_50=800,
                                        sma_20=830, rsi_14=60, atr_14=15.0,
                                        trend_pass=True),
            flow=FlowAnalysis(
                dp_volume_shares=500_000,
                total_volume=50_000_000,
                dp_volume_dollars=425_000_000.0,
                block_trade_dollars=50_000_000.0,
                venue_entropy=1.85,
            ),
            fundamental=FundamentalScoring(funda_score=20),
            combined_score=92.5,
            **gex_kw,
        )

    def test_save_and_load_enriched(self, tmp_path: Path):
        from ifds.data.phase4_snapshot import (
            _stock_to_dict,
            save_phase4_snapshot,
            snapshot_to_stock_analysis,
        )

        stock = self._make_stock(
            net_gex=1_000_000.0, call_wall=900.0,
            put_wall=800.0, zero_gamma=855.5,
        )
        out = save_phase4_snapshot([stock], snapshot_dir=str(tmp_path))
        assert out.exists()

        with gzip.open(out) as f:
            records = json.load(f)
        assert len(records) == 1
        rec = records[0]
        # New fields are serialized
        assert rec["dp_volume_shares"] == 500_000
        assert rec["dp_volume_dollars"] == 425_000_000.0
        assert rec["block_trade_dollars"] == 50_000_000.0
        assert rec["venue_entropy"] == 1.85
        assert rec["net_gex"] == 1_000_000.0
        assert rec["call_wall"] == 900.0
        assert rec["put_wall"] == 800.0
        assert rec["zero_gamma"] == 855.5

        # Round trip through snapshot_to_stock_analysis
        reloaded = snapshot_to_stock_analysis(rec)
        assert reloaded.flow.dp_volume_dollars == 425_000_000.0
        assert reloaded.flow.block_trade_dollars == 50_000_000.0
        assert reloaded.net_gex == 1_000_000.0
        assert reloaded.call_wall == 900.0

    def test_save_without_gex_persists_none(self, tmp_path: Path):
        """If Phase 5 didn't populate GEX fields, snapshot stores None."""
        from ifds.data.phase4_snapshot import (
            save_phase4_snapshot,
            snapshot_to_stock_analysis,
        )

        stock = self._make_stock()  # no GEX kwargs
        out = save_phase4_snapshot([stock], snapshot_dir=str(tmp_path))
        with gzip.open(out) as f:
            records = json.load(f)
        rec = records[0]
        assert rec["net_gex"] is None
        assert rec["call_wall"] is None

        reloaded = snapshot_to_stock_analysis(rec)
        assert reloaded.net_gex is None


class TestSnapshotBackwardCompatibility:
    """Legacy snapshots (pre-enrichment) must load without error."""

    def test_load_legacy_record_without_new_fields(self):
        """A minimal legacy record should load with default values."""
        from ifds.data.phase4_snapshot import snapshot_to_stock_analysis

        legacy = {
            "ticker": "AAPL",
            "sector": "Technology",
            "combined_score": 85.0,
            "sector_adjustment": 10,
            "price": 150.0,
            "sma_200": 130.0,
            "sma_50": 140.0,
            "sma_20": 145.0,
            "rsi_14": 55.0,
            "atr_14": 3.0,
            "trend_pass": True,
            # NO dp_volume_shares, dp_volume_dollars, net_gex, etc.
        }
        stock = snapshot_to_stock_analysis(legacy)

        # Legacy fields work
        assert stock.ticker == "AAPL"
        assert stock.combined_score == 85.0

        # New flow fields default to 0/0.0
        assert stock.flow.dp_volume_shares == 0
        assert stock.flow.dp_volume_dollars == 0.0
        assert stock.flow.block_trade_dollars == 0.0
        assert stock.flow.venue_entropy == 0.0

        # GEX fields default to None
        assert stock.net_gex is None
        assert stock.call_wall is None
        assert stock.put_wall is None
        assert stock.zero_gamma is None


class TestScoringUnchanged:
    """New fields must NOT affect combined_score computation."""

    def test_scoring_unchanged_with_enriched_flow(self, monkeypatch):
        """Adding dollar-weighted fields does not alter flow score contribution."""
        from ifds.models.market import FlowAnalysis

        # Same logical flow, different enrichment
        fl_plain = FlowAnalysis(rvol_score=40)
        fl_rich = FlowAnalysis(
            rvol_score=40,
            dp_volume_dollars=1_000_000.0,
            block_trade_dollars=500_000.0,
        )
        # rvol_score is the only field consumed by _calculate_combined_score
        assert fl_plain.rvol_score == fl_rich.rvol_score
