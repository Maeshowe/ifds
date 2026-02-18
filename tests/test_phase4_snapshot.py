"""Tests for Phase 4 Snapshot Persistence (BC19)."""

import gzip
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from ifds.data.phase4_snapshot import (
    _stock_to_dict,
    load_phase4_snapshot,
    save_phase4_snapshot,
)
from ifds.models.market import (
    FlowAnalysis,
    FundamentalScoring,
    StockAnalysis,
    TechnicalAnalysis,
)


# ============================================================================
# Fixtures
# ============================================================================

def _make_stock(ticker="AAPL", score=85.0) -> StockAnalysis:
    """Create a test StockAnalysis."""
    return StockAnalysis(
        ticker=ticker,
        sector="Technology",
        technical=TechnicalAnalysis(
            price=150.0, sma_200=140.0, sma_20=148.0,
            rsi_14=55.0, atr_14=3.5, trend_pass=True,
            rsi_score=30, sma_50=145.0, sma50_bonus=30,
            rs_vs_spy=0.05, rs_spy_score=40,
        ),
        flow=FlowAnalysis(
            rvol=1.5, rvol_score=10,
            dark_pool_pct=35.0, dp_pct_score=10,
            pcr=0.6, pcr_score=15,
            otm_call_ratio=0.45, otm_score=10,
            block_trade_count=3, block_trade_score=10,
            buy_pressure_score=10,
        ),
        fundamental=FundamentalScoring(
            revenue_growth_yoy=0.15,
            eps_growth_yoy=0.20,
            net_margin=0.12,
            roe=0.18,
            debt_equity=0.5,
            insider_score=2,
            insider_multiplier=1.0,
            funda_score=15,
            shark_detected=False,
            inst_ownership_trend="increasing",
            inst_ownership_score=10,
        ),
        combined_score=score,
        sector_adjustment=10,
    )


# ============================================================================
# TestSaveAndLoad
# ============================================================================

class TestSaveAndLoad:

    def test_roundtrip(self, tmp_path):
        """Save and load produces identical data."""
        stocks = [_make_stock("AAPL"), _make_stock("MSFT", score=78.0)]

        with patch("ifds.data.phase4_snapshot.date") as mock_date:
            mock_date.today.return_value = date(2026, 2, 18)
            mock_date.side_effect = lambda *a, **k: date(*a, **k)
            path = save_phase4_snapshot(stocks, str(tmp_path))

        assert path.exists()
        assert path.name == "2026-02-18.json.gz"

        data = load_phase4_snapshot("2026-02-18", str(tmp_path))
        assert len(data) == 2
        assert data[0]["ticker"] == "AAPL"
        assert data[1]["ticker"] == "MSFT"
        assert data[0]["combined_score"] == 85.0
        assert data[1]["combined_score"] == 78.0


class TestSnapshotContent:

    def test_all_fields_present(self, tmp_path):
        """Snapshot contains all expected fields."""
        stocks = [_make_stock()]

        with patch("ifds.data.phase4_snapshot.date") as mock_date:
            mock_date.today.return_value = date(2026, 2, 18)
            mock_date.side_effect = lambda *a, **k: date(*a, **k)
            save_phase4_snapshot(stocks, str(tmp_path))

        data = load_phase4_snapshot("2026-02-18", str(tmp_path))
        record = data[0]

        # Core
        assert "ticker" in record
        assert "sector" in record
        assert "combined_score" in record
        assert "sector_adjustment" in record

        # Technical
        assert "price" in record
        assert "sma_200" in record
        assert "sma_50" in record
        assert "rsi_14" in record
        assert "atr_14" in record
        assert "rs_vs_spy" in record

        # Flow
        assert "rvol" in record
        assert "dark_pool_pct" in record
        assert "pcr" in record
        assert "block_trade_count" in record
        assert "buy_pressure_score" in record

        # Fundamental
        assert "revenue_growth_yoy" in record
        assert "eps_growth_yoy" in record
        assert "insider_score" in record
        assert "inst_ownership_trend" in record

    def test_field_values_correct(self, tmp_path):
        """Snapshot values match source data."""
        stock = _make_stock()

        with patch("ifds.data.phase4_snapshot.date") as mock_date:
            mock_date.today.return_value = date(2026, 2, 18)
            mock_date.side_effect = lambda *a, **k: date(*a, **k)
            save_phase4_snapshot([stock], str(tmp_path))

        data = load_phase4_snapshot("2026-02-18", str(tmp_path))
        r = data[0]

        assert r["price"] == 150.0
        assert r["rsi_14"] == 55.0
        assert r["rvol"] == 1.5
        assert r["funda_score"] == 15
        assert r["inst_ownership_trend"] == "increasing"


class TestSnapshotOverwrite:

    def test_overwrite_same_day(self, tmp_path):
        """Writing same day twice overwrites (idempotent)."""
        with patch("ifds.data.phase4_snapshot.date") as mock_date:
            mock_date.today.return_value = date(2026, 2, 18)
            mock_date.side_effect = lambda *a, **k: date(*a, **k)

            save_phase4_snapshot([_make_stock("AAPL")], str(tmp_path))
            save_phase4_snapshot([_make_stock("MSFT")], str(tmp_path))

        data = load_phase4_snapshot("2026-02-18", str(tmp_path))
        assert len(data) == 1
        assert data[0]["ticker"] == "MSFT"  # Second write wins


class TestLoadNonexistent:

    def test_returns_empty_list(self, tmp_path):
        """Loading nonexistent date returns empty list."""
        data = load_phase4_snapshot("2026-01-01", str(tmp_path))
        assert data == []


class TestSnapshotDirCreation:

    def test_creates_dir(self, tmp_path):
        """Creates snapshot dir if it doesn't exist."""
        nested = tmp_path / "deep" / "nested" / "dir"
        assert not nested.exists()

        with patch("ifds.data.phase4_snapshot.date") as mock_date:
            mock_date.today.return_value = date(2026, 2, 18)
            mock_date.side_effect = lambda *a, **k: date(*a, **k)
            save_phase4_snapshot([_make_stock()], str(nested))

        assert nested.exists()


class TestStockToDict:

    def test_conversion(self):
        """_stock_to_dict produces expected keys."""
        stock = _make_stock()
        d = _stock_to_dict(stock)
        assert isinstance(d, dict)
        assert d["ticker"] == "AAPL"
        assert d["combined_score"] == 85.0
        assert d["price"] == 150.0
        assert d["rvol"] == 1.5
        assert d["funda_score"] == 15


class TestPipelineIntegration:

    def test_config_defaults(self):
        """Phase 4 snapshot config keys exist in defaults."""
        from ifds.config.defaults import RUNTIME
        assert "phase4_snapshot_enabled" in RUNTIME
        assert RUNTIME["phase4_snapshot_enabled"] is True
        assert "phase4_snapshot_dir" in RUNTIME
        assert RUNTIME["phase4_snapshot_dir"] == "state/phase4_snapshots"
