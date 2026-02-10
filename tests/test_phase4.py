"""Tests for Phase 4: Individual Stock Analysis."""

import pytest
from unittest.mock import MagicMock

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import (
    DarkPoolSignal,
    FlowAnalysis,
    FundamentalScoring,
    SectorScore,
    StockAnalysis,
    StrategyMode,
    TechnicalAnalysis,
    Ticker,
    MomentumClassification,
    SectorTrend,
    SectorBMIRegime,
)
from ifds.phases.phase4_stocks import (
    run_phase4,
    _calculate_sma,
    _calculate_rsi,
    _calculate_atr,
    _check_trend_filter,
    _score_rsi,
    _score_rvol,
    _analyze_technical,
    _analyze_flow,
    _analyze_fundamental,
    _calculate_insider_score,
    _insider_multiplier,
    _detect_shark,
    _calculate_combined_score,
    _BASE_SCORE,
)


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    return Config()


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-phase4")


def _make_bar(close, high=None, low=None, volume=1000, open_price=None):
    """Create a mock OHLCV bar."""
    if high is None:
        high = close + 1
    if low is None:
        low = close - 1
    if open_price is None:
        open_price = close
    return {"o": open_price, "h": high, "l": low, "c": close, "v": volume}


def _make_bars(closes, volume=1000):
    """Create bars from a list of close prices."""
    return [_make_bar(c, volume=volume) for c in closes]


# ============================================================================
# SMA Tests
# ============================================================================

class TestSMA:
    def test_basic_calculation(self):
        assert _calculate_sma([10, 20, 30], 3) == 20.0

    def test_uses_last_n_values(self):
        # SMA(3) of [1,2,3,4,5] should be avg of [3,4,5] = 4.0
        assert _calculate_sma([1, 2, 3, 4, 5], 3) == 4.0

    def test_insufficient_data_uses_all(self):
        # Less data than period → use all available
        result = _calculate_sma([10, 20], 5)
        assert result == 15.0

    def test_empty_list(self):
        assert _calculate_sma([], 5) == 0.0

    def test_single_value(self):
        assert _calculate_sma([42.0], 1) == 42.0

    def test_period_one(self):
        assert _calculate_sma([10, 20, 30], 1) == 30.0


# ============================================================================
# RSI Tests
# ============================================================================

class TestRSI:
    def test_neutral_flat_market(self):
        # All same close → no gains, no losses → 50.0
        bars = _make_bars([100] * 20)
        rsi = _calculate_rsi(bars, 14)
        assert rsi == 50.0

    def test_uptrend_high_rsi(self):
        # Consistently rising → RSI near 100
        closes = [100 + i * 2 for i in range(30)]
        bars = _make_bars(closes)
        rsi = _calculate_rsi(bars, 14)
        assert rsi > 90

    def test_downtrend_low_rsi(self):
        # Consistently falling → RSI near 0
        closes = [200 - i * 2 for i in range(30)]
        bars = _make_bars(closes)
        rsi = _calculate_rsi(bars, 14)
        assert rsi < 10

    def test_insufficient_data_returns_neutral(self):
        bars = _make_bars([100, 101, 102])
        rsi = _calculate_rsi(bars, 14)
        assert rsi == 50.0

    def test_all_gains_no_losses(self):
        closes = [100 + i for i in range(20)]
        bars = _make_bars(closes)
        rsi = _calculate_rsi(bars, 14)
        assert rsi == 100.0


# ============================================================================
# ATR Tests
# ============================================================================

class TestATR:
    def test_basic_calculation(self):
        # Simple bars where TR is predictable
        bars = [
            {"o": 100, "h": 105, "l": 95, "c": 100, "v": 1000},
            {"o": 100, "h": 106, "l": 94, "c": 101, "v": 1000},
            {"o": 101, "h": 107, "l": 95, "c": 102, "v": 1000},
        ]
        atr = _calculate_atr(bars, period=2)
        assert atr > 0

    def test_single_bar_returns_zero(self):
        bars = [_make_bar(100)]
        assert _calculate_atr(bars) == 0.0

    def test_known_values(self):
        # TR for bar 1: max(106-94, |106-100|, |94-100|) = max(12, 6, 6) = 12
        # TR for bar 2: max(107-95, |107-101|, |95-101|) = max(12, 6, 6) = 12
        # ATR(2) = (12+12)/2 = 12
        bars = [
            {"o": 100, "h": 105, "l": 95, "c": 100, "v": 1000},
            {"o": 100, "h": 106, "l": 94, "c": 101, "v": 1000},
            {"o": 101, "h": 107, "l": 95, "c": 102, "v": 1000},
        ]
        atr = _calculate_atr(bars, period=2)
        assert atr == 12.0

    def test_insufficient_data_averages_available(self):
        bars = [
            {"o": 100, "h": 110, "l": 90, "c": 100, "v": 1000},
            {"o": 100, "h": 110, "l": 90, "c": 100, "v": 1000},
        ]
        # Only 1 TR value, period=14 → average of that 1 value
        atr = _calculate_atr(bars, period=14)
        assert atr == 20.0  # max(110-90, |110-100|, |90-100|) = 20


# ============================================================================
# Trend Filter Tests
# ============================================================================

class TestTrendFilter:
    def test_long_above_sma200_passes(self):
        assert _check_trend_filter(150.0, 140.0, StrategyMode.LONG) is True

    def test_long_below_sma200_fails(self):
        assert _check_trend_filter(130.0, 140.0, StrategyMode.LONG) is False

    def test_short_below_sma200_passes(self):
        assert _check_trend_filter(130.0, 140.0, StrategyMode.SHORT) is True

    def test_short_above_sma200_fails(self):
        assert _check_trend_filter(150.0, 140.0, StrategyMode.SHORT) is False

    def test_zero_sma_always_passes(self):
        assert _check_trend_filter(100.0, 0.0, StrategyMode.LONG) is True
        assert _check_trend_filter(100.0, 0.0, StrategyMode.SHORT) is True

    def test_equal_price_and_sma_long_fails(self):
        # Price == SMA200 is not > SMA200
        assert _check_trend_filter(140.0, 140.0, StrategyMode.LONG) is False

    def test_equal_price_and_sma_short_fails(self):
        # Price == SMA200 is not < SMA200
        assert _check_trend_filter(140.0, 140.0, StrategyMode.SHORT) is False


# ============================================================================
# RSI Scoring Tests
# ============================================================================

class TestRSIScoring:
    def test_inner_zone_bonus(self, config):
        # RSI 50 is in [45-65] → +30
        score = _score_rsi(50.0, config)
        assert score == 30

    def test_outer_zone_low_bonus(self, config):
        # RSI 40 is in [35-45) → +15
        score = _score_rsi(40.0, config)
        assert score == 15

    def test_outer_zone_high_bonus(self, config):
        # RSI 70 is in (65-75] → +15
        score = _score_rsi(70.0, config)
        assert score == 15

    def test_outside_no_adjustment(self, config):
        # RSI 25 is outside all zones → 0
        score = _score_rsi(25.0, config)
        assert score == 0

    def test_inner_boundary_low(self, config):
        # 45 is in [45-65] (inclusive)
        assert _score_rsi(45.0, config) == 30

    def test_inner_boundary_high(self, config):
        # 65 is in [45-65] (inclusive)
        assert _score_rsi(65.0, config) == 30

    def test_outer_boundary_high(self, config):
        # 75 is in (65-75] (inclusive upper)
        assert _score_rsi(75.0, config) == 15


# ============================================================================
# RVOL Scoring Tests
# ============================================================================

class TestRVOLScoring:
    def test_low_volume_penalty(self, config):
        score = _score_rvol(0.3, config)
        assert score == -10

    def test_normal_volume_neutral(self, config):
        score = _score_rvol(0.7, config)
        assert score == 0

    def test_elevated_volume_bonus(self, config):
        score = _score_rvol(1.2, config)
        assert score == 5

    def test_significant_volume_bonus(self, config):
        score = _score_rvol(2.0, config)
        assert score == 15

    def test_exact_low_boundary(self, config):
        # 0.5 is not < 0.5
        assert _score_rvol(0.5, config) == 0

    def test_exact_normal_boundary(self, config):
        # 1.0 is not < 1.0
        assert _score_rvol(1.0, config) == 5

    def test_exact_elevated_boundary(self, config):
        # 1.5 is not < 1.5
        assert _score_rvol(1.5, config) == 15


# ============================================================================
# Flow Analysis & Squat Bar Tests
# ============================================================================

class TestFlowAnalysis:
    def test_squat_bar_detected(self, config):
        # RVOL > 2.0 and SpreadRatio < 0.9
        # Make last bar have huge volume and narrow spread
        bars = []
        for i in range(25):
            bars.append({"o": 100, "h": 110, "l": 90, "c": 100, "v": 1000})
        # Last bar: huge volume (RVOL > 2.0), narrow spread (SpreadRatio < 0.9)
        bars.append({"o": 100, "h": 102, "l": 99, "c": 101, "v": 5000})

        flow = _analyze_flow("TEST", bars, None, config)
        assert flow.squat_bar is True
        assert flow.squat_bar_bonus == 10

    def test_squat_bar_not_detected_low_rvol(self, config):
        bars = _make_bars([100] * 25)
        flow = _analyze_flow("TEST", bars, None, config)
        assert flow.squat_bar is False
        assert flow.squat_bar_bonus == 0

    def test_rvol_calculated(self, config):
        bars = []
        for i in range(25):
            bars.append({"o": 100, "h": 101, "l": 99, "c": 100, "v": 1000})
        # Last bar: 3x volume
        bars.append({"o": 100, "h": 101, "l": 99, "c": 100, "v": 3000})
        flow = _analyze_flow("TEST", bars, None, config)
        assert flow.rvol > 2.0

    def test_dark_pool_with_provider(self, config):
        dp_provider = MagicMock()
        dp_provider.get_dark_pool.return_value = {
            "dp_pct": 55.0,
            "dp_volume": 550,
            "signal": "BULLISH",
        }
        bars = _make_bars([100] * 25)
        flow = _analyze_flow("TEST", bars, dp_provider, config)
        assert flow.dark_pool_signal == DarkPoolSignal.BULLISH
        assert flow.dark_pool_pct == 55.0

    def test_dark_pool_below_threshold(self, config):
        dp_provider = MagicMock()
        dp_provider.get_dark_pool.return_value = {
            "dp_pct": 20.0,
            "dp_volume": 200,  # 200/1000 = 20% — below 40% threshold
            "signal": "BULLISH",
        }
        bars = _make_bars([100] * 25)
        flow = _analyze_flow("TEST", bars, dp_provider, config)
        assert flow.dark_pool_signal is None  # Below threshold

    def test_no_dark_pool_provider(self, config):
        bars = _make_bars([100] * 25)
        flow = _analyze_flow("TEST", bars, None, config)
        assert flow.dark_pool_signal is None
        assert flow.dark_pool_pct == 0.0


# ============================================================================
# Fundamental Scoring Tests
# ============================================================================

class TestFundamentalScoring:
    def _mock_fmp(self, growth=None, metrics=None, insider=None):
        fmp = MagicMock()
        fmp.get_financial_growth.return_value = growth
        fmp.get_key_metrics.return_value = metrics
        fmp.get_insider_trading.return_value = insider
        return fmp

    def test_good_revenue_growth_bonus(self, config):
        fmp = self._mock_fmp(
            growth={"revenueGrowth": 0.20, "epsgrowth": 0.0},
        )
        f = _analyze_fundamental("TEST", fmp, config)
        assert f.funda_score > 0

    def test_bad_eps_growth_penalty(self, config):
        fmp = self._mock_fmp(
            growth={"revenueGrowth": 0.0, "epsgrowth": -0.20},
        )
        f = _analyze_fundamental("TEST", fmp, config)
        assert f.funda_score < 0

    def test_high_debt_equity_penalty(self, config):
        fmp = self._mock_fmp(
            metrics={"debtToEquityTTM": 5.0},
        )
        f = _analyze_fundamental("TEST", fmp, config)
        assert f.funda_score < 0  # debt_penalty = -10

    def test_low_interest_coverage_penalty(self, config):
        fmp = self._mock_fmp(
            metrics={"interestCoverageTTM": 1.0},
        )
        f = _analyze_fundamental("TEST", fmp, config)
        assert f.funda_score < 0

    def test_no_data_returns_zero_score(self, config):
        fmp = self._mock_fmp()
        f = _analyze_fundamental("TEST", fmp, config)
        assert f.funda_score == 0

    def test_all_good_metrics(self, config):
        fmp = self._mock_fmp(
            growth={"revenueGrowth": 0.20, "epsgrowth": 0.25},
            metrics={
                "roeTTM": 0.25,
                "debtToEquityTTM": 0.3,
                "netIncomePerShareTTM": 5.0,
                "revenuePerShareTTM": 20.0,
            },
        )
        f = _analyze_fundamental("TEST", fmp, config)
        # revenue +5, EPS +5, ROE +5, D/E +5, net margin +5 = 25
        assert f.funda_score >= 20


# ============================================================================
# Insider Trading Tests
# ============================================================================

class TestInsiderTrading:
    def test_net_buys(self, config):
        insider_data = [
            {"transactionDate": "2099-01-01", "acquistionOrDisposition": "A"},
            {"transactionDate": "2099-01-02", "acquistionOrDisposition": "A"},
            {"transactionDate": "2099-01-03", "acquistionOrDisposition": "D"},
        ]
        score = _calculate_insider_score(insider_data, config)
        assert score == 1  # 2 buys - 1 sell

    def test_net_sells(self, config):
        insider_data = [
            {"transactionDate": "2099-01-01", "acquistionOrDisposition": "D"},
            {"transactionDate": "2099-01-02", "acquistionOrDisposition": "D"},
        ]
        score = _calculate_insider_score(insider_data, config)
        assert score == -2

    def test_no_data_returns_zero(self, config):
        assert _calculate_insider_score(None, config) == 0
        assert _calculate_insider_score([], config) == 0

    def test_old_trades_excluded(self, config):
        # Trades from 2020 should be outside 30-day lookback
        insider_data = [
            {"transactionDate": "2020-01-01", "acquistionOrDisposition": "A"},
        ]
        score = _calculate_insider_score(insider_data, config)
        assert score == 0

    def test_strong_buy_multiplier(self, config):
        # insider_strong_buy_threshold = 3
        mult = _insider_multiplier(5, config)
        assert mult == 1.25

    def test_strong_sell_multiplier(self, config):
        # insider_strong_sell_threshold = -3
        mult = _insider_multiplier(-5, config)
        assert mult == 0.75

    def test_neutral_multiplier(self, config):
        mult = _insider_multiplier(1, config)
        assert mult == 1.0

    def test_exact_threshold_stays_neutral(self, config):
        # Threshold is > 3, not >= 3
        assert _insider_multiplier(3, config) == 1.0
        assert _insider_multiplier(-3, config) == 1.0


# ============================================================================
# Combined Score Tests
# ============================================================================

class TestCombinedScore:
    def test_neutral_base_score(self, config):
        """All neutral → flow=50, funda=50, tech=0 → combined=35."""
        tech = TechnicalAnalysis(price=100, sma_200=90, sma_20=95,
                                 rsi_14=50, atr_14=2.0, trend_pass=True, rsi_score=0)
        flow = FlowAnalysis(rvol_score=0)
        funda = FundamentalScoring(funda_score=0, insider_multiplier=1.0)

        combined = _calculate_combined_score(tech, flow, funda, 0, config)
        # flow=50, funda=50, tech=0 → 0.4*50 + 0.3*50 + 0.3*0 = 35.0
        assert combined == 35.0

    def test_sector_adjustment_added(self, config):
        tech = TechnicalAnalysis(price=100, sma_200=90, sma_20=95,
                                 rsi_14=50, atr_14=2.0, trend_pass=True, rsi_score=0)
        flow = FlowAnalysis(rvol_score=0)
        funda = FundamentalScoring(funda_score=0, insider_multiplier=1.0)

        combined = _calculate_combined_score(tech, flow, funda, 15, config)
        assert combined == 50.0  # 35 + 15

    def test_insider_multiplier_applied(self, config):
        tech = TechnicalAnalysis(price=100, sma_200=90, sma_20=95,
                                 rsi_14=50, atr_14=2.0, trend_pass=True, rsi_score=0)
        flow = FlowAnalysis(rvol_score=0)
        funda = FundamentalScoring(funda_score=0, insider_multiplier=1.25)

        combined = _calculate_combined_score(tech, flow, funda, 0, config)
        assert combined == 43.75  # 35 * 1.25

    def test_weighted_scoring(self, config):
        """Verify weights: 0.4 flow + 0.3 funda + 0.3 tech."""
        tech = TechnicalAnalysis(price=100, sma_200=90, sma_20=95,
                                 rsi_14=50, atr_14=2.0, trend_pass=True,
                                 rsi_score=5, sma50_bonus=0, rs_spy_score=0)
        flow = FlowAnalysis(rvol_score=15)
        funda = FundamentalScoring(funda_score=10, insider_multiplier=1.0)

        combined = _calculate_combined_score(tech, flow, funda, 0, config)
        # tech_score = 0+5+0+0=5, flow_score = 50+15=65, funda_score = 50+10=60
        # 0.4*65 + 0.3*60 + 0.3*5 = 26 + 18 + 1.5 = 45.5
        assert combined == 45.5


# ============================================================================
# Phase 4 Integration Tests
# ============================================================================

class TestPhase4Integration:
    def _make_polygon(self, bars):
        polygon = MagicMock()
        polygon.get_aggregates.return_value = bars
        polygon.get_options_snapshot.return_value = None
        return polygon

    def _make_fmp(self):
        fmp = MagicMock()
        fmp.get_financial_growth.return_value = None
        fmp.get_key_metrics.return_value = None
        fmp.get_insider_trading.return_value = None
        return fmp

    def _make_sector_scores(self):
        return [
            SectorScore(etf="XLK", sector_name="Technology",
                        classification=MomentumClassification.LEADER,
                        score_adjustment=15),
        ]

    def _make_universe(self, count=3):
        return [
            Ticker(symbol=f"TICK{i}", sector="Technology")
            for i in range(count)
        ]

    def test_full_flow(self, config, logger):
        # Create bars where price > SMA200 → passes trend filter
        # Rising prices → score should be above min
        closes = [90 + i * 0.5 for i in range(200)]
        # Last few bars ramp up for higher RVOL
        closes[-1] = 200
        bars = []
        for c in closes:
            bars.append({"o": c, "h": c + 2, "l": c - 2, "c": c, "v": 1000})
        bars[-1]["v"] = 3000  # High RVOL last bar

        polygon = self._make_polygon(bars)
        fmp = self._make_fmp()
        tickers = self._make_universe(2)
        sectors = self._make_sector_scores()

        result = run_phase4(config, logger, polygon, fmp, None,
                            tickers, sectors, StrategyMode.LONG)

        assert len(result.analyzed) == 2
        assert result.excluded_count + len(result.passed) == len(result.analyzed)

    def test_tech_filter_excludes(self, config, logger):
        # Price below SMA200 in LONG mode → excluded
        closes = [200 - i * 0.5 for i in range(200)]  # Downtrend
        bars = [{"o": c, "h": c + 1, "l": c - 1, "c": c, "v": 1000} for c in closes]

        polygon = self._make_polygon(bars)
        fmp = self._make_fmp()
        tickers = self._make_universe(1)

        result = run_phase4(config, logger, polygon, fmp, None,
                            tickers, [], StrategyMode.LONG)

        assert result.tech_filter_count == 1
        assert result.analyzed[0].exclusion_reason == "tech_filter"

    def test_clipping_skip(self, config, logger):
        # Create bars that would produce a high combined score (>90)
        # Rising prices for SMA50 bonus (+30) and RS vs SPY (+40)
        closes = [50 + i * 0.5 for i in range(200)]
        bars = []
        for c in closes:
            bars.append({"o": c, "h": c + 2, "l": c - 2, "c": c, "v": 1000})
        bars[-1]["v"] = 5000  # High RVOL

        polygon = MagicMock()
        polygon.get_aggregates.return_value = bars
        # Options data with bullish PCR + OTM calls for high flow score
        polygon.get_options_snapshot.return_value = [
            {"details": {"contract_type": "call", "strike_price": 200.0},
             "day": {"volume": 5000}},
            {"details": {"contract_type": "put", "strike_price": 100.0},
             "day": {"volume": 500}},
        ]

        # FMP returning all strong metrics + insider buys to push score high
        fmp = MagicMock()
        fmp.get_financial_growth.return_value = {
            "revenueGrowth": 0.50, "epsgrowth": 0.50,
        }
        fmp.get_key_metrics.return_value = {
            "roeTTM": 0.30,
            "debtToEquityTTM": 0.2,
            "interestCoverageTTM": 10.0,
            "netIncomePerShareTTM": 10.0,
            "revenuePerShareTTM": 30.0,
        }
        fmp.get_insider_trading.return_value = [
            {"transactionDate": "2099-01-01", "acquistionOrDisposition": "A",
             "reportingCik": f"CIK{i}", "securitiesTransacted": 5000, "price": 50.0}
            for i in range(5)
        ]

        tickers = self._make_universe(1)
        # Large sector bonus to push above 90
        sectors = [SectorScore(etf="XLK", sector_name="Technology",
                               score_adjustment=15,
                               classification=MomentumClassification.LEADER)]

        result = run_phase4(config, logger, polygon, fmp, None,
                            tickers, sectors, StrategyMode.LONG)

        # Score should be high enough to clip (>95)
        assert result.clipped_count > 0, "Expected at least one clipped ticker"
        clipped = [a for a in result.analyzed if a.exclusion_reason == "clipping"]
        assert len(clipped) == result.clipped_count
        assert clipped[0].combined_score > 95

    def test_insufficient_data_skipped(self, config, logger):
        # Only 10 bars → skip
        bars = _make_bars([100] * 10)
        polygon = self._make_polygon(bars)
        fmp = self._make_fmp()
        tickers = self._make_universe(1)

        result = run_phase4(config, logger, polygon, fmp, None,
                            tickers, [], StrategyMode.LONG)

        assert len(result.analyzed) == 0

    def test_no_data_from_polygon_skipped(self, config, logger):
        polygon = MagicMock()
        polygon.get_aggregates.return_value = None
        fmp = self._make_fmp()
        tickers = self._make_universe(1)

        result = run_phase4(config, logger, polygon, fmp, None,
                            tickers, [], StrategyMode.LONG)

        assert len(result.analyzed) == 0
