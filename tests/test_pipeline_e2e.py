"""End-to-end pipeline integration tests (BC2 Review F2).

Tests that the pipeline runner correctly orchestrates all phases and
propagates context between them.
"""

import pytest
from unittest.mock import patch, MagicMock

from ifds.config.loader import Config
from ifds.models.market import (
    APIHealthResult, APIStatus,
    BMIData, BMIRegime,
    CircuitBreakerState,
    DiagnosticsResult,
    FlowAnalysis,
    FundamentalScoring,
    GEXAnalysis, GEXRegime,
    MacroRegime, MarketVolatilityRegime,
    MomentumClassification,
    Phase1Result, Phase2Result, Phase3Result, Phase4Result, Phase5Result,
    Phase6Result, PositionSizing,
    SectorScore, SectorTrend, SectorBMIRegime,
    StockAnalysis,
    StrategyMode,
    TechnicalAnalysis,
    Ticker,
)
from ifds.pipeline.runner import run_pipeline


@pytest.fixture
def env_setup(monkeypatch):
    """Set up environment for pipeline tests."""
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    monkeypatch.setenv("IFDS_UW_API_KEY", "test_uw")


def _mock_diagnostics_ok():
    """Create a passing DiagnosticsResult."""
    return DiagnosticsResult(
        api_health=[
            APIHealthResult(provider="polygon", endpoint="/test",
                            status=APIStatus.OK, is_critical=True),
            APIHealthResult(provider="fmp", endpoint="/test",
                            status=APIStatus.OK, is_critical=True),
            APIHealthResult(provider="fred", endpoint="/test",
                            status=APIStatus.OK, is_critical=True),
            APIHealthResult(provider="unusual_whales", endpoint="/test",
                            status=APIStatus.OK, is_critical=False),
        ],
        circuit_breaker=CircuitBreakerState(is_active=False),
        macro=MacroRegime(
            vix_value=18.0,
            vix_regime=MarketVolatilityRegime.NORMAL,
            vix_multiplier=1.0,
            tnx_value=4.2,
            tnx_sma20=4.1,
            tnx_rate_sensitive=False,
        ),
        all_critical_apis_ok=True,
        pipeline_can_proceed=True,
    )


def _mock_diagnostics_halt():
    """Create a halting DiagnosticsResult."""
    return DiagnosticsResult(
        api_health=[
            APIHealthResult(provider="polygon", endpoint="/test",
                            status=APIStatus.DOWN, is_critical=True),
        ],
        circuit_breaker=CircuitBreakerState(is_active=False),
        all_critical_apis_ok=False,
        pipeline_can_proceed=False,
        halt_reason="Critical API 'polygon' is DOWN",
    )


def _mock_phase1():
    return Phase1Result(
        bmi=BMIData(bmi_value=45.0, bmi_regime=BMIRegime.YELLOW,
                     daily_ratio=50.0),
        strategy_mode=StrategyMode.LONG,
        ticker_count_for_bmi=100,
    )


def _mock_phase2():
    return Phase2Result(
        tickers=[
            Ticker(symbol="AAPL", sector="Technology", market_cap=3e12,
                   price=180.0, avg_volume=50e6, has_options=True),
            Ticker(symbol="MSFT", sector="Technology", market_cap=2.8e12,
                   price=420.0, avg_volume=25e6, has_options=True),
        ],
        total_screened=3000,
        strategy_mode=StrategyMode.LONG,
    )


def _mock_phase3():
    return Phase3Result(
        sector_scores=[
            SectorScore(etf="XLK", sector_name="Technology",
                        momentum_5d=2.5, trend=SectorTrend.UP, rank=1,
                        classification=MomentumClassification.LEADER,
                        sector_bmi_regime=SectorBMIRegime.NEUTRAL,
                        score_adjustment=15),
        ],
        vetoed_sectors=[],
        active_sectors=["XLK"],
    )


def _mock_phase4():
    return Phase4Result(
        analyzed=[
            StockAnalysis(
                ticker="AAPL", sector="Technology",
                technical=TechnicalAnalysis(
                    price=180.0, sma_200=160.0, sma_20=175.0,
                    rsi_14=55.0, atr_14=3.5, trend_pass=True,
                ),
                flow=FlowAnalysis(rvol=1.3, rvol_score=5),
                fundamental=FundamentalScoring(funda_score=10),
                combined_score=78.0,
            ),
        ],
        passed=[
            StockAnalysis(
                ticker="AAPL", sector="Technology",
                technical=TechnicalAnalysis(
                    price=180.0, sma_200=160.0, sma_20=175.0,
                    rsi_14=55.0, atr_14=3.5, trend_pass=True,
                ),
                flow=FlowAnalysis(rvol=1.3, rvol_score=5),
                fundamental=FundamentalScoring(funda_score=10),
                combined_score=78.0,
            ),
        ],
        excluded_count=1,
        tech_filter_count=1,
    )


def _mock_phase5():
    return Phase5Result(
        analyzed=[
            GEXAnalysis(ticker="AAPL", net_gex=500.0, zero_gamma=170.0,
                        current_price=180.0, gex_regime=GEXRegime.POSITIVE,
                        gex_multiplier=1.0),
        ],
        passed=[
            GEXAnalysis(ticker="AAPL", net_gex=500.0, zero_gamma=170.0,
                        current_price=180.0, gex_regime=GEXRegime.POSITIVE,
                        gex_multiplier=1.0),
        ],
    )


def _mock_phase6():
    return Phase6Result(
        positions=[
            PositionSizing(
                ticker="AAPL", sector="Technology", direction="BUY",
                entry_price=180.0, quantity=111, stop_loss=175.5,
                take_profit_1=186.0, take_profit_2=189.0,
                risk_usd=500.0, combined_score=78.0,
                gex_regime="POSITIVE", multiplier_total=1.0,
            ),
        ],
        total_risk_usd=500.0,
        total_exposure_usd=19980.0,
    )


# Patch paths: patch the source modules since runner uses lazy imports
_P0 = "ifds.phases.phase0_diagnostics.run_phase0"
_P1 = "ifds.phases.phase1_regime.run_phase1"
_P2 = "ifds.phases.phase2_universe.run_phase2"
_P3 = "ifds.phases.phase3_sectors.run_phase3"
_P4 = "ifds.phases.phase4_stocks.run_phase4"
_P5 = "ifds.phases.phase5_gex.run_phase5"
_P6 = "ifds.phases.phase6_sizing.run_phase6"


def _mock_client_class(*args, **kwargs):
    """Return a mock client with close() method."""
    client = MagicMock()
    client.close = MagicMock()
    return client


class TestEndToEnd:
    """Full pipeline with all phases mocked."""

    @patch("ifds.output.execution_plan.write_trade_plan", return_value="/tmp/trade.csv")
    @patch("ifds.output.execution_plan.write_full_scan_matrix", return_value="/tmp/scan.csv")
    @patch("ifds.output.execution_plan.write_execution_plan", return_value="/tmp/test.csv")
    @patch(_P6, return_value=_mock_phase6())
    @patch(_P5, return_value=_mock_phase5())
    @patch(_P4, return_value=_mock_phase4())
    @patch(_P3, return_value=_mock_phase3())
    @patch(_P2, return_value=_mock_phase2())
    @patch(_P1, return_value=_mock_phase1())
    @patch(_P0, return_value=_mock_diagnostics_ok())
    @patch("ifds.data.unusual_whales.UnusualWhalesClient", _mock_client_class)
    @patch("ifds.data.polygon.PolygonClient", _mock_client_class)
    @patch("ifds.data.fmp.FMPClient", _mock_client_class)
    def test_full_pipeline_flow(self, mock_p0, mock_p1, mock_p2, mock_p3,
                                 mock_p4, mock_p5, mock_p6, mock_output,
                                 mock_scan, mock_trade,
                                 env_setup, tmp_path, monkeypatch):
        monkeypatch.setenv("IFDS_LOG_DIR", str(tmp_path))

        result = run_pipeline()

        assert result.success is True
        ctx = result.context

        # Phase 0 → diagnostics populated
        assert ctx.diagnostics is not None
        assert ctx.macro is not None
        assert ctx.uw_available is True

        # Phase 1 → strategy mode propagated
        assert ctx.strategy_mode == StrategyMode.LONG
        assert ctx.bmi_regime == BMIRegime.YELLOW

        # Phase 2 → universe populated
        assert len(ctx.universe) == 2
        assert ctx.universe[0].symbol == "AAPL"

        # Phase 3 → sector scores populated
        assert len(ctx.sector_scores) == 1
        assert ctx.sector_scores[0].etf == "XLK"

        # Phase 4 → stock analyses propagated
        assert ctx.phase4 is not None
        assert len(ctx.stock_analyses) == 1
        assert ctx.stock_analyses[0].ticker == "AAPL"

        # Phase 5 → GEX analyses propagated
        assert ctx.phase5 is not None
        assert len(ctx.gex_analyses) == 1
        assert ctx.gex_analyses[0].ticker == "AAPL"

        # Phase 6 → positions propagated
        assert ctx.phase6 is not None
        assert len(ctx.positions) == 1
        assert ctx.positions[0].ticker == "AAPL"
        assert ctx.execution_plan_path == "/tmp/test.csv"


class TestPipelineHalt:
    """Pipeline stops when diagnostics fail."""

    @patch(_P0, return_value=_mock_diagnostics_halt())
    def test_diagnostics_failure_halts_pipeline(self, mock_p0, env_setup,
                                                 tmp_path, monkeypatch):
        monkeypatch.setenv("IFDS_LOG_DIR", str(tmp_path))

        result = run_pipeline()

        assert result.success is False
        assert "HALT" in result.message
        assert "polygon" in result.message

    @patch(_P0, return_value=_mock_diagnostics_halt())
    def test_halt_does_not_run_subsequent_phases(self, mock_p0, env_setup,
                                                   tmp_path, monkeypatch):
        monkeypatch.setenv("IFDS_LOG_DIR", str(tmp_path))

        result = run_pipeline()

        ctx = result.context
        assert ctx.phase1 is None
        assert ctx.phase2 is None
        assert ctx.phase3 is None
        assert ctx.phase4 is None
        assert ctx.phase5 is None


class TestSinglePhase:
    """--phase flag runs only that phase."""

    @patch(_P0, return_value=_mock_diagnostics_ok())
    def test_phase_0_only(self, mock_p0, env_setup, tmp_path, monkeypatch):
        monkeypatch.setenv("IFDS_LOG_DIR", str(tmp_path))

        result = run_pipeline(phase=0, dry_run=True)

        assert result.success is True
        ctx = result.context
        assert ctx.diagnostics is not None
        # Other phases should not have run
        assert ctx.phase1 is None

    @patch("ifds.data.polygon.PolygonClient", _mock_client_class)
    @patch(_P3, return_value=_mock_phase3())
    @patch(_P0, return_value=_mock_diagnostics_ok())
    def test_phase_3_only(self, mock_p0, mock_p3, env_setup,
                           tmp_path, monkeypatch):
        monkeypatch.setenv("IFDS_LOG_DIR", str(tmp_path))

        result = run_pipeline(phase=3)

        assert result.success is True
        ctx = result.context
        # Phase 0 always runs, Phase 3 ran, but Phase 1/2 skipped
        assert ctx.diagnostics is not None
        assert ctx.phase1 is None
        assert ctx.phase2 is None
        assert ctx.phase3 is not None

    @patch(_P0, return_value=_mock_diagnostics_ok())
    def test_phase_6_only_no_data(self, mock_p0, env_setup, tmp_path, monkeypatch):
        """Phase 6 only mode with no Phase 4/5 data → skips gracefully."""
        monkeypatch.setenv("IFDS_LOG_DIR", str(tmp_path))

        result = run_pipeline(phase=6)

        assert result.success is True
        ctx = result.context
        assert ctx.phase6 is None  # Skipped due to no data
