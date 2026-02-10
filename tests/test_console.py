"""Tests for CLI dashboard console output."""

import pytest

from ifds.models.market import (
    APIHealthResult, APIStatus, BMIData, BMIRegime,
    CircuitBreakerState, DiagnosticsResult, GEXAnalysis, GEXRegime,
    MacroRegime, MarketVolatilityRegime, MomentumClassification,
    Phase1Result, Phase2Result, Phase3Result, Phase4Result, Phase5Result,
    Phase6Result, PipelineContext, PositionSizing, SectorBMIRegime,
    SectorScore, SectorTrend, StockAnalysis, StrategyMode, Ticker,
    TechnicalAnalysis, FlowAnalysis, FundamentalScoring,
)
from ifds.output.console import (
    print_diagnostics, print_phase1, print_phase2,
    print_sector_table, print_scan_summary, print_gex_summary,
    print_final_summary, print_pipeline_result, print_phase_header,
    _print_config_table, _sector_change_arrow,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def macro():
    return MacroRegime(
        vix_value=17.5, vix_regime=MarketVolatilityRegime.NORMAL,
        vix_multiplier=1.0, tnx_value=4.25, tnx_sma20=4.10,
        tnx_rate_sensitive=False,
    )


@pytest.fixture
def diag(macro):
    return DiagnosticsResult(
        api_health=[
            APIHealthResult(provider="polygon", endpoint="/v2/aggs",
                            status=APIStatus.OK, response_time_ms=120.5,
                            is_critical=True),
            APIHealthResult(provider="fmp", endpoint="/v3/stock-screener",
                            status=APIStatus.OK, response_time_ms=200.0,
                            is_critical=True),
            APIHealthResult(provider="unusual_whales", endpoint="/api/darkpool/SPY",
                            status=APIStatus.SKIPPED, error="No API key",
                            is_critical=False),
        ],
        circuit_breaker=CircuitBreakerState(is_active=False),
        macro=macro,
        all_critical_apis_ok=True,
        pipeline_can_proceed=True,
    )


@pytest.fixture
def phase1():
    return Phase1Result(
        bmi=BMIData(bmi_value=49.8, bmi_regime=BMIRegime.YELLOW,
                    daily_ratio=52.0, buy_count=100, sell_count=95),
        strategy_mode=StrategyMode.LONG,
        ticker_count_for_bmi=500,
    )


@pytest.fixture
def phase2():
    return Phase2Result(
        tickers=[Ticker(symbol="AAPL"), Ticker(symbol="MSFT")],
        total_screened=3000,
        earnings_excluded=["GOOG"],
        strategy_mode=StrategyMode.LONG,
    )


@pytest.fixture
def phase3():
    return Phase3Result(
        sector_scores=[
            SectorScore(etf="XLK", sector_name="Technology",
                        momentum_5d=2.5, trend=SectorTrend.UP,
                        rank=1, classification=MomentumClassification.LEADER,
                        sector_bmi=45.0, sector_bmi_regime=SectorBMIRegime.NEUTRAL,
                        score_adjustment=15),
            SectorScore(etf="XLE", sector_name="Energy",
                        momentum_5d=-1.2, trend=SectorTrend.DOWN,
                        rank=11, classification=MomentumClassification.LAGGARD,
                        sector_bmi=22.0, sector_bmi_regime=SectorBMIRegime.OVERSOLD,
                        vetoed=True, veto_reason="Laggard + OVERBOUGHT",
                        score_adjustment=-20),
        ],
        vetoed_sectors=["XLE"],
        active_sectors=["XLK"],
    )


@pytest.fixture
def phase4():
    return Phase4Result(
        analyzed=[_make_stock("AAPL"), _make_stock("MSFT", excluded=True)],
        passed=[_make_stock("AAPL")],
        excluded_count=1,
        clipped_count=0,
        tech_filter_count=0,
        min_score_count=1,
    )


@pytest.fixture
def phase5():
    return Phase5Result(
        analyzed=[
            GEXAnalysis(ticker="AAPL", gex_regime=GEXRegime.POSITIVE),
        ],
        passed=[
            GEXAnalysis(ticker="AAPL", gex_regime=GEXRegime.POSITIVE),
        ],
        excluded_count=0,
        negative_regime_count=0,
    )


@pytest.fixture
def phase6():
    return Phase6Result(
        positions=[_make_position("AAPL"), _make_position("MSFT", score=72.0)],
        total_risk_usd=500.0,
        total_exposure_usd=10000.0,
        freshness_applied_count=1,
    )


@pytest.fixture
def ctx(phase6):
    return PipelineContext(
        run_id="test-run-001",
        strategy_mode=StrategyMode.LONG,
        positions=phase6.positions,
        execution_plan_path="/tmp/execution_plan_test.csv",
    )


# ── Helpers ───────────────────────────────────────────────────────────────

def _make_stock(ticker="AAPL", excluded=False):
    return StockAnalysis(
        ticker=ticker, sector="Technology",
        technical=TechnicalAnalysis(
            price=150.0, sma_200=140.0, sma_20=148.0,
            rsi_14=55.0, atr_14=3.0, trend_pass=True, rsi_score=5,
        ),
        flow=FlowAnalysis(rvol=1.5, rvol_score=10),
        fundamental=FundamentalScoring(funda_score=15),
        combined_score=75.0,
        excluded=excluded,
        exclusion_reason="min_score" if excluded else None,
    )


def _make_position(ticker="AAPL", score=85.0):
    return PositionSizing(
        ticker=ticker, sector="Technology", direction="BUY",
        entry_price=150.0, quantity=10, stop_loss=145.0,
        take_profit_1=160.0, take_profit_2=170.0,
        risk_usd=50.0, combined_score=score, gex_regime="positive",
        multiplier_total=1.2, m_vix=1.0, m_utility=1.1,
        is_fresh=ticker == "AAPL",
    )


# ── Tests ─────────────────────────────────────────────────────────────────

class TestPrintPhaseHeader:
    def test_prints_header(self, capsys):
        print_phase_header(1, "Test Phase", "goal", "logic", "source")
        out = capsys.readouterr().out
        assert "[ 1/6 ] Test Phase" in out
        assert "Cel:" in out
        assert "Logika:" in out
        assert "Forras:" in out


class TestPrintDiagnostics:
    def test_prints_api_health(self, capsys, diag):
        print_diagnostics(diag)
        out = capsys.readouterr().out
        assert "polygon" in out
        assert "fmp" in out
        assert "unusual_whales" in out

    def test_prints_macro(self, capsys, diag):
        print_diagnostics(diag)
        out = capsys.readouterr().out
        assert "VIX=" in out
        assert "17.5" in out

    def test_proceed_message(self, capsys, diag):
        print_diagnostics(diag)
        out = capsys.readouterr().out
        assert "Pipeline CAN proceed" in out

    def test_halt_message(self, capsys, diag):
        diag.pipeline_can_proceed = False
        diag.halt_reason = "Polygon down"
        print_diagnostics(diag)
        out = capsys.readouterr().out
        assert "HALT" in out
        assert "Polygon down" in out

    def test_no_macro(self, capsys, diag):
        diag.macro = None
        print_diagnostics(diag)
        out = capsys.readouterr().out
        assert "VIX=" not in out


class TestPrintPhase1:
    def test_prints_bmi(self, capsys, phase1):
        print_phase1(phase1)
        out = capsys.readouterr().out
        assert "49.8%" in out
        assert "YELLOW" in out
        assert "LONG" in out

    def test_divergence_shown(self, capsys, phase1):
        phase1.bmi.divergence_detected = True
        phase1.bmi.divergence_type = "bearish"
        print_phase1(phase1)
        out = capsys.readouterr().out
        assert "Divergence" in out
        assert "bearish" in out


class TestPrintPhase2:
    def test_prints_universe(self, capsys, phase2):
        print_phase2(phase2)
        out = capsys.readouterr().out
        assert "3000" in out
        assert "Passed: 2" in out
        assert "Earnings excluded: 1" in out


class TestPrintSectorTable:
    def test_prints_sectors(self, capsys, phase3):
        print_sector_table(phase3)
        out = capsys.readouterr().out
        assert "XLK" in out
        assert "Technology" in out
        assert "XLE" in out
        assert "Energy" in out

    def test_vetoed_shown(self, capsys, phase3):
        print_sector_table(phase3)
        out = capsys.readouterr().out
        assert "Vetoed sectors" in out
        assert "XLE" in out


class TestPrintScanSummary:
    def test_prints_counts(self, capsys, phase4):
        print_scan_summary(phase4)
        out = capsys.readouterr().out
        assert "Analyzed: 2" in out
        assert "Passed: 1" in out
        assert "Excluded: 1" in out


class TestPrintGexSummary:
    def test_prints_gex(self, capsys, phase5):
        print_gex_summary(phase5)
        out = capsys.readouterr().out
        assert "Analyzed: 1" in out
        assert "Passed: 1" in out


class TestPrintFinalSummary:
    def test_prints_positions(self, capsys, phase6, ctx):
        print_final_summary(phase6, ctx)
        out = capsys.readouterr().out
        assert "Positions: 2" in out
        assert "AAPL" in out
        assert "MSFT" in out

    def test_freshness_shown(self, capsys, phase6, ctx):
        print_final_summary(phase6, ctx)
        out = capsys.readouterr().out
        assert "Freshness Alpha" in out

    def test_no_positions(self, capsys, ctx):
        empty = Phase6Result()
        print_final_summary(empty, ctx)
        out = capsys.readouterr().out
        assert "Positions: 0" in out


class TestPrintPipelineResult:
    def test_success_banner(self, capsys, ctx):
        print_pipeline_result(ctx, log_file="/tmp/test.jsonl")
        out = capsys.readouterr().out
        assert "PIPELINE COMPLETE" in out
        assert "2 positions" in out
        assert "test-run-001" in out

    def test_no_positions_banner(self, capsys):
        empty_ctx = PipelineContext(run_id="empty-run")
        print_pipeline_result(empty_ctx)
        out = capsys.readouterr().out
        assert "No actionable positions" in out

    def test_shows_csv_and_log(self, capsys, ctx):
        print_pipeline_result(ctx, log_file="/tmp/test.jsonl")
        out = capsys.readouterr().out
        assert "CSV:" in out
        assert "Log:" in out


class TestPrintPhase1BMIChange:
    def test_bmi_change_positive(self, capsys, phase1):
        prev = {"date": "2025-01-01", "bmi": 49.4, "regime": "yellow"}
        print_phase1(phase1, prev_bmi=prev)
        out = capsys.readouterr().out
        assert "+0.4 vs tegnap" in out

    def test_bmi_change_negative(self, capsys, phase1):
        prev = {"date": "2025-01-01", "bmi": 52.0, "regime": "green"}
        print_phase1(phase1, prev_bmi=prev)
        out = capsys.readouterr().out
        assert "-2.2 vs tegnap" in out

    def test_bmi_no_previous(self, capsys, phase1):
        print_phase1(phase1, prev_bmi=None)
        out = capsys.readouterr().out
        assert "vs tegnap" not in out

    def test_bmi_empty_previous(self, capsys, phase1):
        print_phase1(phase1, prev_bmi={})
        out = capsys.readouterr().out
        assert "vs tegnap" not in out


class TestSectorChangeArrow:
    def test_arrow_up(self):
        prev = {"XLK": 1.0}
        result = _sector_change_arrow("XLK", prev, 2.0)
        assert "^" in result

    def test_arrow_down(self):
        prev = {"XLK": 2.0}
        result = _sector_change_arrow("XLK", prev, 1.0)
        assert "v" in result

    def test_arrow_flat(self):
        prev = {"XLK": 2.0}
        result = _sector_change_arrow("XLK", prev, 2.005)
        assert ">" in result

    def test_no_prev(self):
        result = _sector_change_arrow("XLK", None, 2.0)
        assert result == ""

    def test_etf_not_in_prev(self):
        prev = {"XLE": 1.0}
        result = _sector_change_arrow("XLK", prev, 2.0)
        assert result == ""


class TestSectorTableBenchmark:
    def test_benchmark_row_shown(self, capsys, phase3):
        agg = SectorScore(
            etf="AGG", sector_name="Bonds (Benchmark)",
            momentum_5d=0.3, trend=SectorTrend.UP,
            rank=99, classification=MomentumClassification.NEUTRAL,
            sector_bmi=50.0, sector_bmi_regime=SectorBMIRegime.NEUTRAL,
            score_adjustment=0,
        )
        print_sector_table(phase3, benchmark=agg)
        out = capsys.readouterr().out
        assert "AGG" in out
        assert "Bonds (Benchmark)" in out
        assert "Benchmark" in out

    def test_benchmark_not_scored(self, capsys, phase3):
        agg = SectorScore(
            etf="AGG", sector_name="Bonds (Benchmark)",
            momentum_5d=0.3, trend=SectorTrend.UP,
            rank=99, classification=MomentumClassification.NEUTRAL,
            sector_bmi=50.0, sector_bmi_regime=SectorBMIRegime.NEUTRAL,
            score_adjustment=0,
        )
        print_sector_table(phase3, benchmark=agg)
        out = capsys.readouterr().out
        assert "--" in out

    def test_no_benchmark(self, capsys, phase3):
        print_sector_table(phase3, benchmark=None)
        out = capsys.readouterr().out
        assert "AGG" not in out

    def test_sector_table_with_prev_sectors_adds_chg_header(self, capsys, phase3):
        prev = {"XLK": 1.0, "XLE": -0.5}
        print_sector_table(phase3, prev_sectors=prev)
        out = capsys.readouterr().out
        assert "CHG" in out


class TestPrintConfigTable:
    def test_prints_table_fields(self, capsys, monkeypatch):
        monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test")
        monkeypatch.setenv("IFDS_FMP_API_KEY", "test")
        monkeypatch.setenv("IFDS_FRED_API_KEY", "test")
        monkeypatch.setenv("IFDS_ASYNC_ENABLED", "true")
        from ifds.config.loader import Config
        config = Config()
        _print_config_table(config)
        out = capsys.readouterr().out
        assert "BEALLITASOK" in out
        assert "Account equity" in out
        assert "$100,000" in out
        assert "Risk per trade" in out
        assert "0.5%" in out
        assert "Max positions" in out
        assert "Max per sector" in out
        assert "Min score" in out
        assert "Clipping threshold" in out
        assert "VIX multiplier" in out
        assert "Weights" in out
        assert "flow=0.40" in out
        assert "Async" in out
        assert "true" in out

    def test_cache_false_by_default(self, capsys, monkeypatch):
        monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test")
        monkeypatch.setenv("IFDS_FMP_API_KEY", "test")
        monkeypatch.setenv("IFDS_FRED_API_KEY", "test")
        from ifds.config.loader import Config
        config = Config()
        _print_config_table(config)
        out = capsys.readouterr().out
        assert "Cache" in out
        assert "false" in out

    def test_config_table_before_banner(self, capsys, monkeypatch, ctx):
        monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test")
        monkeypatch.setenv("IFDS_FMP_API_KEY", "test")
        monkeypatch.setenv("IFDS_FRED_API_KEY", "test")
        from ifds.config.loader import Config
        config = Config()
        print_pipeline_result(ctx, config=config)
        out = capsys.readouterr().out
        # Config table appears before the PIPELINE COMPLETE banner
        config_pos = out.index("BEALLITASOK")
        banner_pos = out.index("PIPELINE COMPLETE")
        assert config_pos < banner_pos

    def test_no_config_no_table(self, capsys, ctx):
        print_pipeline_result(ctx)
        out = capsys.readouterr().out
        assert "BEALLITASOK" not in out
        assert "PIPELINE COMPLETE" in out
