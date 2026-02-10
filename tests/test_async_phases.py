"""Tests for async Phase 4 and Phase 5 code paths."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import (
    GEXAnalysis,
    GEXRegime,
    MomentumClassification,
    SectorBMIRegime,
    SectorScore,
    SectorTrend,
    StockAnalysis,
    StrategyMode,
    TechnicalAnalysis,
    FlowAnalysis,
    FundamentalScoring,
    Ticker,
)
from ifds.phases.phase4_stocks import (
    _analyze_flow_from_data,
    _analyze_fundamental_from_data,
    _run_phase4_async,
)
from ifds.phases.phase5_gex import _run_phase5_async


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    monkeypatch.setenv("IFDS_ASYNC_ENABLED", "true")
    return Config()


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-async")


def _make_bars(count=210, base_price=100, volume=1000):
    """Create mock OHLCV bars (uptrend by default)."""
    bars = []
    for i in range(count):
        c = base_price + i * 0.1
        bars.append({"o": c, "h": c + 2, "l": c - 2, "c": c, "v": volume})
    return bars


def _make_tickers(count=3, sector="Technology"):
    return [Ticker(symbol=f"TICK{i}", sector=sector, market_cap=10e9,
                   price=100.0, avg_volume=1e6) for i in range(count)]


def _make_sector_scores():
    return [SectorScore(
        etf="XLK",
        sector_name="Technology",
        momentum_5d=2.0,
        rank=1,
        classification=MomentumClassification.LEADER,
        score_adjustment=15,
        trend=SectorTrend.UP,
        sector_bmi_regime=SectorBMIRegime.NEUTRAL,
        vetoed=False,
    )]


# ============================================================================
# Extracted pure-computation functions
# ============================================================================

class TestAnalyzeFlowFromData:
    """Test _analyze_flow_from_data with pre-fetched data."""

    def test_basic_flow(self, config):
        bars = _make_bars(50, volume=1000)
        bars[-1]["v"] = 3000  # High RVOL

        result = _analyze_flow_from_data("TEST", bars, None, config)
        assert result.rvol > 1.0
        assert result.rvol_score > 0
        assert result.dark_pool_signal is None

    def test_with_dark_pool_data(self, config):
        bars = _make_bars(50)
        dp_data = {
            "dp_pct": 50.0,
            "signal": "BULLISH",
            "dp_volume": 500,       # 500 / bars[-1].v(1000) * 100 = 50%
            "total_volume": 1000000,
        }

        result = _analyze_flow_from_data("TEST", bars, dp_data, config)
        assert result.dark_pool_pct == 50.0
        from ifds.models.market import DarkPoolSignal
        assert result.dark_pool_signal == DarkPoolSignal.BULLISH

    def test_none_dp_data(self, config):
        bars = _make_bars(50)
        result = _analyze_flow_from_data("TEST", bars, None, config)
        assert result.dark_pool_pct == 0.0
        assert result.dark_pool_signal is None


class TestAnalyzeFundamentalFromData:
    """Test _analyze_fundamental_from_data with pre-fetched data."""

    def test_good_fundamentals(self, config):
        growth = {"revenueGrowth": 0.20, "epsgrowth": 0.25}
        metrics = {
            "roeTTM": 0.20,
            "debtToEquityTTM": 0.3,
            "interestCoverageTTM": 10.0,
            "netIncomePerShareTTM": 5.0,
            "revenuePerShareTTM": 20.0,
        }
        insider = []

        result = _analyze_fundamental_from_data("TEST", growth, metrics, insider, config)
        assert result.funda_score > 0
        assert result.revenue_growth_yoy == 0.20
        assert result.insider_multiplier == 1.0

    def test_all_none(self, config):
        result = _analyze_fundamental_from_data("TEST", None, None, None, config)
        assert result.funda_score == 0
        assert result.insider_multiplier == 1.0

    def test_bad_debt(self, config):
        metrics = {
            "debtToEquityTTM": 5.0,
            "interestCoverageTTM": 0.5,
        }
        result = _analyze_fundamental_from_data("TEST", None, metrics, None, config)
        assert result.funda_score < 0


# ============================================================================
# Async Phase 4
# ============================================================================

class TestPhase4Async:
    """Test the async Phase 4 code path."""

    @pytest.mark.asyncio
    async def test_async_phase4_basic(self, config, logger):
        """Async Phase 4 processes tickers concurrently."""
        bars = _make_bars(210, base_price=100)
        bars[-1]["c"] = 200  # Above SMA200
        bars[-1]["v"] = 3000  # High RVOL

        tickers = _make_tickers(2)
        sectors = _make_sector_scores()

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly, \
             patch("ifds.data.async_clients.AsyncFMPClient") as MockFMP, \
             patch("ifds.data.async_clients.AsyncUWClient"):

            mock_poly = AsyncMock()
            mock_poly.get_aggregates = AsyncMock(return_value=bars)
            mock_poly.get_options_snapshot = AsyncMock(return_value=None)
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            mock_fmp = AsyncMock()
            mock_fmp.get_financial_growth = AsyncMock(return_value={
                "revenueGrowth": 0.15, "epsgrowth": 0.20,
            })
            mock_fmp.get_key_metrics = AsyncMock(return_value={
                "roeTTM": 0.20, "debtToEquityTTM": 0.3,
            })
            mock_fmp.get_insider_trading = AsyncMock(return_value=[])
            mock_fmp.close = AsyncMock()
            MockFMP.return_value = mock_fmp

            result = await _run_phase4_async(
                config, logger, tickers, sectors, StrategyMode.LONG,
            )

            assert len(result.analyzed) == 2
            # 3 calls: 1 SPY + 2 tickers
            assert mock_poly.get_aggregates.await_count == 3
            assert mock_poly.close.await_count == 1

    @pytest.mark.asyncio
    async def test_async_phase4_tech_filter(self, config, logger):
        """Tickers failing SMA200 are filtered in async path."""
        # Downtrend: price below SMA200
        bars = _make_bars(210, base_price=200)
        bars[-1]["c"] = 50  # Below SMA200

        tickers = _make_tickers(1)
        sectors = _make_sector_scores()

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly, \
             patch("ifds.data.async_clients.AsyncFMPClient") as MockFMP:

            mock_poly = AsyncMock()
            mock_poly.get_aggregates = AsyncMock(return_value=bars)
            mock_poly.get_options_snapshot = AsyncMock(return_value=None)
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            mock_fmp = AsyncMock()
            mock_fmp.close = AsyncMock()
            MockFMP.return_value = mock_fmp

            result = await _run_phase4_async(
                config, logger, tickers, sectors, StrategyMode.LONG,
            )

            assert result.tech_filter_count == 1
            assert len(result.passed) == 0
            # FMP should NOT be called if tech filter fails
            mock_fmp.get_financial_growth.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_async_phase4_insufficient_data(self, config, logger):
        """Tickers with insufficient bars are skipped."""
        bars = _make_bars(10)  # Only 10 bars (need 50)

        tickers = _make_tickers(1)
        sectors = _make_sector_scores()

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly, \
             patch("ifds.data.async_clients.AsyncFMPClient") as MockFMP:

            mock_poly = AsyncMock()
            mock_poly.get_aggregates = AsyncMock(return_value=bars)
            mock_poly.get_options_snapshot = AsyncMock(return_value=None)
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            mock_fmp = AsyncMock()
            mock_fmp.close = AsyncMock()
            MockFMP.return_value = mock_fmp

            result = await _run_phase4_async(
                config, logger, tickers, sectors, StrategyMode.LONG,
            )

            assert len(result.analyzed) == 0

    @pytest.mark.asyncio
    async def test_async_phase4_fmp_exception(self, config, logger):
        """FMP exception is logged and treated as None — ticker still scored."""
        bars = _make_bars(210, base_price=100)
        bars[-1]["c"] = 200  # Above SMA200
        bars[-1]["v"] = 3000

        tickers = _make_tickers(1)
        sectors = _make_sector_scores()

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly, \
             patch("ifds.data.async_clients.AsyncFMPClient") as MockFMP, \
             patch("ifds.data.async_clients.AsyncUWClient"):

            mock_poly = AsyncMock()
            mock_poly.get_aggregates = AsyncMock(return_value=bars)
            mock_poly.get_options_snapshot = AsyncMock(return_value=None)
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            mock_fmp = AsyncMock()
            mock_fmp.get_financial_growth = AsyncMock(
                side_effect=ConnectionError("FMP down"),
            )
            mock_fmp.get_key_metrics = AsyncMock(
                side_effect=TimeoutError("FMP timeout"),
            )
            mock_fmp.get_insider_trading = AsyncMock(return_value=[])
            mock_fmp.close = AsyncMock()
            MockFMP.return_value = mock_fmp

            result = await _run_phase4_async(
                config, logger, tickers, sectors, StrategyMode.LONG,
            )

            # Ticker should still be analyzed (with None growth/metrics)
            assert len(result.analyzed) == 1
            analysis = result.analyzed[0]
            assert analysis.fundamental.revenue_growth_yoy is None
            assert analysis.fundamental.roe is None
            # funda_score = 0 when all metrics are None
            assert analysis.fundamental.funda_score == 0

            # Verify exceptions were logged
            log_file = logger.log_file
            import json
            events = []
            with open(log_file) as f:
                for line in f:
                    ev = json.loads(line)
                    if ev.get("event_type") == "API_ERROR":
                        events.append(ev)
            assert len(events) == 2  # growth + metrics failed
            assert "FMP down" in events[0]["message"]
            assert "FMP timeout" in events[1]["message"]


# ============================================================================
# Async Phase 5
# ============================================================================

class TestPhase5Async:
    """Test the async Phase 5 code path."""

    def _make_stock_analyses(self, count=3):
        """Create mock Phase 4 passed stocks."""
        analyses = []
        for i in range(count):
            analyses.append(StockAnalysis(
                ticker=f"TICK{i}",
                sector="Technology",
                technical=TechnicalAnalysis(price=100.0 + i, sma_200=90.0,
                                            sma_20=95.0, rsi_14=55.0,
                                            atr_14=2.0, trend_pass=True),
                flow=FlowAnalysis(rvol_score=5),
                fundamental=FundamentalScoring(funda_score=10),
                combined_score=75.0 + i,
            ))
        return analyses

    @pytest.mark.asyncio
    async def test_async_phase5_basic(self, config, logger):
        """Async Phase 5 processes GEX concurrently."""
        stocks = self._make_stock_analyses(3)

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly, \
             patch("ifds.data.async_clients.AsyncUWClient"):

            mock_poly = AsyncMock()
            mock_poly.get_options_snapshot = AsyncMock(return_value=None)
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            result = await _run_phase5_async(
                config, logger, stocks, StrategyMode.LONG,
            )

            # All 3 should pass with POSITIVE default (no GEX data)
            assert len(result.passed) == 3
            assert all(g.gex_regime == GEXRegime.POSITIVE for g in result.passed)

    @pytest.mark.asyncio
    async def test_async_phase5_with_gex_data(self, config, logger):
        """Async Phase 5 correctly classifies GEX regimes."""
        stocks = self._make_stock_analyses(1)

        mock_options = [{
            "details": {"strike_price": 100, "contract_type": "call"},
            "greeks": {"gamma": 0.05},
            "open_interest": 1000,
            "underlying_asset": {"price": 105},
        }]

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly, \
             patch("ifds.data.async_clients.AsyncUWClient"):

            mock_poly = AsyncMock()
            mock_poly.get_options_snapshot = AsyncMock(return_value=mock_options)
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            result = await _run_phase5_async(
                config, logger, stocks, StrategyMode.LONG,
            )

            assert len(result.analyzed) == 1
            assert result.analyzed[0].data_source == "polygon_calculated"

    @pytest.mark.asyncio
    async def test_async_phase5_cleanup(self, config, logger):
        """Async Phase 5 closes clients even on success."""
        stocks = self._make_stock_analyses(1)

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockPoly, \
             patch("ifds.data.async_clients.AsyncUWClient"):

            mock_poly = AsyncMock()
            mock_poly.get_options_snapshot = AsyncMock(return_value=None)
            mock_poly.close = AsyncMock()
            MockPoly.return_value = mock_poly

            await _run_phase5_async(
                config, logger, stocks, StrategyMode.LONG,
            )

            mock_poly.close.assert_awaited_once()
