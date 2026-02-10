"""Tests for monitoring CSV outputs (full_scan_matrix, trade_plan, execution_plan extension)."""

import csv

import pytest

from ifds.events.logger import EventLogger
from ifds.models.market import (
    FlowAnalysis,
    FundamentalScoring,
    MomentumClassification,
    PositionSizing,
    SectorBMIRegime,
    SectorScore,
    StockAnalysis,
    TechnicalAnalysis,
)
from ifds.output.execution_plan import (
    COLUMNS,
    SCAN_COLUMNS,
    TRADE_PLAN_COLUMNS,
    write_execution_plan,
    write_full_scan_matrix,
    write_trade_plan,
)


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path / "logs"), run_id="csv-test")


def _make_stock(ticker="AAPL", sector="Technology", excluded=False,
                exclusion_reason=None, score=75.0, rvol_score=10,
                funda_score=15, rsi_score=5, price=150.0, atr=3.0):
    return StockAnalysis(
        ticker=ticker, sector=sector,
        technical=TechnicalAnalysis(
            price=price, sma_200=140.0, sma_20=148.0,
            rsi_14=55.0, atr_14=atr, trend_pass=True, rsi_score=rsi_score,
        ),
        flow=FlowAnalysis(rvol_score=rvol_score),
        fundamental=FundamentalScoring(funda_score=funda_score),
        combined_score=score,
        excluded=excluded,
        exclusion_reason=exclusion_reason,
    )


def _make_sector(sector_name="Technology", etf="XLK", sector_bmi=25.0,
                 regime=SectorBMIRegime.NEUTRAL, vetoed=False,
                 classification=MomentumClassification.NEUTRAL):
    return SectorScore(
        etf=etf, sector_name=sector_name, sector_bmi=sector_bmi,
        sector_bmi_regime=regime, vetoed=vetoed, classification=classification,
    )


def _make_position(ticker="AAPL", score=80.0, is_fresh=False,
                   m_vix=1.0, m_utility=1.0, sector_bmi=25.0,
                   sector_regime="NEUTRAL", is_mean_reversion=False):
    return PositionSizing(
        ticker=ticker, sector="Technology", direction="BUY",
        entry_price=150.0, quantity=100, stop_loss=145.5,
        take_profit_1=156.0, take_profit_2=159.0,
        risk_usd=500.0, combined_score=score,
        gex_regime="POSITIVE", multiplier_total=1.0,
        m_vix=m_vix, m_utility=m_utility,
        is_fresh=is_fresh,
        sector_bmi=sector_bmi, sector_regime=sector_regime,
        is_mean_reversion=is_mean_reversion,
    )


# ============================================================================
# Full Scan Matrix tests
# ============================================================================

class TestFullScanMatrix:
    def test_writes_correct_columns(self, tmp_path, logger):
        stocks = [_make_stock()]
        sectors = [_make_sector()]
        path = write_full_scan_matrix(stocks, sectors, "LONG",
                                      str(tmp_path), "run1", logger)
        with open(path) as f:
            reader = csv.DictReader(f)
            assert list(reader.fieldnames) == SCAN_COLUMNS

    def test_accepted_ticker_status(self, tmp_path, logger):
        stocks = [_make_stock(excluded=False)]
        sectors = [_make_sector()]
        path = write_full_scan_matrix(stocks, sectors, "LONG",
                                      str(tmp_path), "run1", logger)
        with open(path) as f:
            rows = list(csv.DictReader(f))
            assert rows[0]["Status"] == "ACCEPTED"
            assert rows[0]["Reason"] == ""

    def test_rejected_tech_filter(self, tmp_path, logger):
        stocks = [_make_stock(excluded=True, exclusion_reason="tech_filter")]
        sectors = [_make_sector()]
        path = write_full_scan_matrix(stocks, sectors, "LONG",
                                      str(tmp_path), "run1", logger)
        with open(path) as f:
            rows = list(csv.DictReader(f))
            assert rows[0]["Status"] == "REJECTED"
            assert rows[0]["Reason"] == "Tech Filter (Price < SMA200)"

    def test_rejected_min_score(self, tmp_path, logger):
        stocks = [_make_stock(excluded=True, exclusion_reason="min_score")]
        sectors = [_make_sector()]
        path = write_full_scan_matrix(stocks, sectors, "LONG",
                                      str(tmp_path), "run1", logger)
        with open(path) as f:
            rows = list(csv.DictReader(f))
            assert rows[0]["Reason"] == "Score < 70"

    def test_rejected_clipping(self, tmp_path, logger):
        stocks = [_make_stock(excluded=True, exclusion_reason="clipping")]
        sectors = [_make_sector()]
        path = write_full_scan_matrix(stocks, sectors, "LONG",
                                      str(tmp_path), "run1", logger)
        with open(path) as f:
            rows = list(csv.DictReader(f))
            assert rows[0]["Reason"] == "Crowded Trade (Score > 95)"

    def test_sector_veto_overrides_reason(self, tmp_path, logger):
        stocks = [_make_stock(excluded=True, exclusion_reason="min_score")]
        sectors = [_make_sector(vetoed=True)]
        path = write_full_scan_matrix(stocks, sectors, "LONG",
                                      str(tmp_path), "run1", logger)
        with open(path) as f:
            rows = list(csv.DictReader(f))
            assert rows[0]["Reason"] == "Sector VETO (Technology, neutral, neutral)"

    def test_sub_scores(self, tmp_path, logger):
        stocks = [_make_stock(rvol_score=10, funda_score=15, rsi_score=5)]
        sectors = [_make_sector()]
        path = write_full_scan_matrix(stocks, sectors, "LONG",
                                      str(tmp_path), "run1", logger)
        with open(path) as f:
            rows = list(csv.DictReader(f))
            assert rows[0]["Flow_Score"] == "60"    # 50 + 10
            assert rows[0]["Funda_Score"] == "65"   # 50 + 15
            assert rows[0]["Tech_Score"] == "5"     # 0 + 5 (no base for tech)

    def test_sector_context(self, tmp_path, logger):
        stocks = [_make_stock()]
        sectors = [_make_sector(etf="XLK", sector_bmi=20.5,
                                regime=SectorBMIRegime.OVERSOLD)]
        path = write_full_scan_matrix(stocks, sectors, "LONG",
                                      str(tmp_path), "run1", logger)
        with open(path) as f:
            rows = list(csv.DictReader(f))
            assert rows[0]["Sector_ETF"] == "XLK"
            assert rows[0]["Sector_BMI"] == "20.5"
            assert rows[0]["Sector_Regime"] == "oversold"

    def test_no_sector_match(self, tmp_path, logger):
        stocks = [_make_stock(sector="Unknown")]
        sectors = [_make_sector()]  # Technology, not Unknown
        path = write_full_scan_matrix(stocks, sectors, "LONG",
                                      str(tmp_path), "run1", logger)
        with open(path) as f:
            rows = list(csv.DictReader(f))
            assert rows[0]["Sector_ETF"] == ""
            assert rows[0]["Sector_BMI"] == ""


# ============================================================================
# Trade Plan tests
# ============================================================================

class TestTradePlan:
    def test_writes_correct_columns(self, tmp_path, logger):
        positions = [_make_position()]
        stocks = [_make_stock()]
        path = write_trade_plan(positions, stocks, str(tmp_path), "run1", logger)
        with open(path) as f:
            reader = csv.DictReader(f)
            assert list(reader.fieldnames) == TRADE_PLAN_COLUMNS

    def test_top_20_limit(self, tmp_path, logger):
        positions = [_make_position(f"T{i}", score=90-i) for i in range(25)]
        stocks = [_make_stock(f"T{i}") for i in range(25)]
        path = write_trade_plan(positions, stocks, str(tmp_path), "run1", logger)
        with open(path) as f:
            rows = list(csv.DictReader(f))
            assert len(rows) == 20

    def test_rank_ordering(self, tmp_path, logger):
        positions = [_make_position("A", 90), _make_position("B", 80)]
        stocks = [_make_stock("A"), _make_stock("B")]
        path = write_trade_plan(positions, stocks, str(tmp_path), "run1", logger)
        with open(path) as f:
            rows = list(csv.DictReader(f))
            assert rows[0]["Rank"] == "1"
            assert rows[0]["Ticker"] == "A"
            assert rows[1]["Rank"] == "2"

    def test_fresh_flag(self, tmp_path, logger):
        positions = [_make_position("AAPL", is_fresh=True)]
        stocks = [_make_stock("AAPL")]
        path = write_trade_plan(positions, stocks, str(tmp_path), "run1", logger)
        with open(path) as f:
            rows = list(csv.DictReader(f))
            assert rows[0]["Flags"] == "FRESH"

    def test_no_flags(self, tmp_path, logger):
        positions = [_make_position("AAPL", is_fresh=False)]
        stocks = [_make_stock("AAPL")]
        path = write_trade_plan(positions, stocks, str(tmp_path), "run1", logger)
        with open(path) as f:
            rows = list(csv.DictReader(f))
            assert rows[0]["Flags"] == ""


# ============================================================================
# Execution Plan extension tests
# ============================================================================

class TestExecutionPlanExtension:
    def test_extended_columns(self):
        assert "mult_vix" in COLUMNS
        assert "mult_utility" in COLUMNS
        assert "sector_bmi" in COLUMNS
        assert "sector_regime" in COLUMNS
        assert "is_mean_reversion" in COLUMNS
        assert len(COLUMNS) == 18  # 13 original + 5 new

    def test_new_columns_in_csv(self, tmp_path, logger):
        positions = [_make_position(m_vix=0.8, m_utility=1.2,
                                    sector_bmi=25.0, sector_regime="OVERSOLD",
                                    is_mean_reversion=True)]
        path = write_execution_plan(positions, str(tmp_path), "run1", logger)
        with open(path) as f:
            rows = list(csv.DictReader(f))
            assert rows[0]["mult_vix"] == "0.8"
            assert rows[0]["mult_utility"] == "1.2"
            assert rows[0]["sector_bmi"] == "25.0"
            assert rows[0]["sector_regime"] == "OVERSOLD"
            assert rows[0]["is_mean_reversion"] == "True"

    def test_sector_bmi_none_writes_empty(self, tmp_path, logger):
        positions = [_make_position(sector_bmi=None)]
        path = write_execution_plan(positions, str(tmp_path), "run1", logger)
        with open(path) as f:
            rows = list(csv.DictReader(f))
            assert rows[0]["sector_bmi"] == ""
