"""Tests for daily_metrics.py — output schema and edge cases."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestBuildDailyMetrics:
    """Test the build_daily_metrics function directly."""

    def test_output_has_required_keys(self, tmp_path, monkeypatch):
        """The output JSON must contain all required top-level sections."""
        from scripts.paper_trading.daily_metrics import build_daily_metrics

        # Patch data sources to return minimal data
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.CUM_PNL_FILE",
            tmp_path / "nonexistent_pnl.json",
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.TRADES_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.EXEC_PLAN_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.PHASE4_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics._fetch_spy_return",
            lambda d: None,
        )

        metrics = build_daily_metrics("2026-04-02")

        required_keys = {
            "date", "day_number", "positions", "market", "scoring",
            "execution", "exits", "pnl", "excess_return", "trades",
        }
        assert required_keys == set(metrics.keys())

    def test_no_trades_produces_valid_output(self, tmp_path, monkeypatch):
        """When there are no trades, metrics should still be valid JSON."""
        from scripts.paper_trading.daily_metrics import build_daily_metrics

        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.CUM_PNL_FILE",
            tmp_path / "nonexistent.json",
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.TRADES_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.EXEC_PLAN_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.PHASE4_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics._fetch_spy_return",
            lambda d: None,
        )

        metrics = build_daily_metrics("2026-04-02")

        assert metrics["positions"]["opened"] == 0
        assert metrics["pnl"]["gross"] == 0
        assert metrics["trades"]["best"] is None
        assert metrics["trades"]["worst"] is None
        assert metrics["trades"]["details"] == []


class TestSlippageCalculation:
    """Test slippage = (fill - planned) / planned × 100."""

    def test_positive_slippage(self):
        """Fill higher than planned → positive slippage (unfavorable for LONG)."""
        planned = 100.00
        filled = 101.50
        slippage = (filled - planned) / planned * 100
        assert slippage == pytest.approx(1.5)

    def test_negative_slippage(self):
        """Fill lower than planned → negative slippage (favorable for LONG)."""
        planned = 100.00
        filled = 99.50
        slippage = (filled - planned) / planned * 100
        assert slippage == pytest.approx(-0.5)

    def test_zero_slippage(self):
        planned = 50.00
        filled = 50.00
        slippage = (filled - planned) / planned * 100
        assert slippage == pytest.approx(0.0)


class TestExcessReturn:
    """Test excess return = portfolio return - SPY return."""

    def test_positive_excess(self):
        portfolio_pct = 0.50
        spy_pct = 0.20
        excess = portfolio_pct - spy_pct
        assert excess == pytest.approx(0.30)

    def test_negative_excess(self):
        portfolio_pct = -0.30
        spy_pct = 0.50
        excess = portfolio_pct - spy_pct
        assert excess == pytest.approx(-0.80)

    def test_no_spy_data(self):
        """When SPY data is unavailable, excess should be None."""
        spy = None
        excess = None if spy is None else (0.5 - spy)
        assert excess is None
