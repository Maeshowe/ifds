"""BC9 Scoring Tests — RSI ideal zone, SMA50, RS vs SPY, PCR, OTM, Block Trades, Shark Detector.

~30 tests covering the new scoring features introduced in BC9.
"""

import pytest
from datetime import date, timedelta

from ifds.phases.phase4_stocks import (
    _score_rsi,
    _analyze_technical,
    _analyze_flow_from_data,
    _analyze_fundamental_from_data,
    _detect_shark,
    _calculate_combined_score,
    _calculate_sma,
    _BASE_SCORE,
)
from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import (
    FlowAnalysis,
    FundamentalScoring,
    TechnicalAnalysis,
    StrategyMode,
)
from ifds.data.adapters import _aggregate_dp_records


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    return Config()


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-bc9")


# ============================================================================
# Helpers
# ============================================================================

def _make_bar(close, high=None, low=None, volume=1000, open_price=None):
    if high is None:
        high = close + 1
    if low is None:
        low = close - 1
    if open_price is None:
        open_price = close
    return {"o": open_price, "h": high, "l": low, "c": close, "v": volume}


def _make_bars(closes, volume=1000):
    return [_make_bar(c, volume=volume) for c in closes]


# ============================================================================
# TestRSIIdealZone — 6 tests
# ============================================================================

class TestRSIIdealZone:
    """Test _score_rsi ideal zone gradient scoring.

    Inner zone [45-65] -> +30, outer [35-45)/(65-75] -> +15, outside -> 0.
    """

    def test_inner_zone_center(self, config):
        """RSI=55 falls in inner zone [45-65] -> +30."""
        assert _score_rsi(55, config) == 30

    def test_inner_zone_boundary_low(self, config):
        """RSI=45 is inclusive lower bound of inner zone -> +30."""
        assert _score_rsi(45, config) == 30

    def test_inner_zone_boundary_high(self, config):
        """RSI=65 is inclusive upper bound of inner zone -> +30."""
        assert _score_rsi(65, config) == 30

    def test_outer_zone_low(self, config):
        """RSI=40 falls in outer zone [35, 45) -> +15."""
        assert _score_rsi(40, config) == 15

    def test_outer_zone_high(self, config):
        """RSI=70 falls in outer zone (65, 75] -> +15."""
        assert _score_rsi(70, config) == 15

    def test_outside_zone(self, config):
        """RSI=25 is outside both zones -> 0."""
        assert _score_rsi(25, config) == 0


# ============================================================================
# TestSMA50AndRSvsSPY — 5 tests
# ============================================================================

class TestSMA50AndRSvsSPY:
    """Test SMA50 bonus and Relative Strength vs SPY in _analyze_technical."""

    def _rising_bars(self, n=100, start=80.0, step=0.5):
        """Generate n bars with steadily rising closes (price > SMA50)."""
        closes = [start + i * step for i in range(n)]
        return _make_bars(closes)

    def _falling_end_bars(self, n=100, start=120.0, step=-0.8):
        """Generate n bars that start high then fall sharply (price < SMA50)."""
        # First half stable, second half dropping fast
        half = n // 2
        closes = [start] * half + [start + (i - half) * step for i in range(half, n)]
        return _make_bars(closes)

    def test_sma50_bonus_above(self, config):
        """Price > SMA50 > 0 -> sma50_bonus = 30."""
        bars = self._rising_bars(100)
        tech = _analyze_technical(bars, StrategyMode.LONG, config)
        # With rising prices, current price (last bar) > SMA50 of last 50 closes
        assert tech.sma50_bonus == 30
        assert tech.sma_50 > 0

    def test_sma50_no_bonus_below(self, config):
        """Price < SMA50 -> sma50_bonus = 0."""
        bars = self._falling_end_bars(100)
        tech = _analyze_technical(bars, StrategyMode.LONG, config)
        # With falling end prices, current price < SMA50
        assert tech.sma50_bonus == 0

    def test_rs_vs_spy_outperforming(self, config):
        """Ticker 3m return > spy 3m return -> rs_spy_score = 40."""
        # Create 100 bars with strong upward trend
        # close[-1] significantly higher than close[-63]
        closes = [100.0 + i * 1.0 for i in range(100)]
        bars = _make_bars(closes)
        # Ticker 3m return: (closes[-1] - closes[-63]) / closes[-63]
        # = (199 - 137) / 137 = 0.4526 (45.3%)
        spy_3m_return = 0.05  # SPY only returned 5%
        tech = _analyze_technical(bars, StrategyMode.LONG, config,
                                  spy_3m_return=spy_3m_return)
        assert tech.rs_spy_score == 40
        assert tech.rs_vs_spy is not None
        assert tech.rs_vs_spy > 0

    def test_rs_vs_spy_underperforming(self, config):
        """Ticker 3m return < spy 3m return -> rs_spy_score = 0."""
        # Create 100 bars with flat/slightly declining prices
        closes = [100.0 - i * 0.01 for i in range(100)]
        bars = _make_bars(closes)
        # Ticker 3m return: (closes[-1] - closes[-63]) / closes[-63]
        # = (99.01 - 99.37) / 99.37 < 0 (negative)
        spy_3m_return = 0.05  # SPY returned 5%
        tech = _analyze_technical(bars, StrategyMode.LONG, config,
                                  spy_3m_return=spy_3m_return)
        assert tech.rs_spy_score == 0
        assert tech.rs_vs_spy is not None
        assert tech.rs_vs_spy < 0

    def test_rs_vs_spy_none_when_no_spy_data(self, config):
        """spy_3m_return=None -> rs_vs_spy=None, rs_spy_score=0."""
        closes = [100.0 + i * 0.5 for i in range(100)]
        bars = _make_bars(closes)
        tech = _analyze_technical(bars, StrategyMode.LONG, config,
                                  spy_3m_return=None)
        assert tech.rs_vs_spy is None
        assert tech.rs_spy_score == 0


# ============================================================================
# TestPCRScoring — 4 tests
# ============================================================================

class TestPCRScoring:
    """Test Put/Call Ratio scoring in _analyze_flow_from_data."""

    def _basic_bars(self, n=30):
        """Generate n simple bars at price=100."""
        return _make_bars([100.0] * n)

    def test_pcr_bullish(self, config):
        """Many calls, few puts -> PCR < 0.7 -> pcr_score = +15."""
        options_data = [
            {"details": {"contract_type": "call", "strike_price": 105.0},
             "day": {"volume": 5000}},
            {"details": {"contract_type": "put", "strike_price": 95.0},
             "day": {"volume": 500}},
        ]
        bars = self._basic_bars()
        flow = _analyze_flow_from_data("TEST", bars, None, config,
                                       options_data=options_data)
        assert flow.pcr is not None
        assert flow.pcr < 0.7
        assert flow.pcr_score == 15

    def test_pcr_bearish(self, config):
        """Few calls, many puts -> PCR > 1.3 -> pcr_score = -10."""
        options_data = [
            {"details": {"contract_type": "call", "strike_price": 105.0},
             "day": {"volume": 500}},
            {"details": {"contract_type": "put", "strike_price": 95.0},
             "day": {"volume": 5000}},
        ]
        bars = self._basic_bars()
        flow = _analyze_flow_from_data("TEST", bars, None, config,
                                       options_data=options_data)
        assert flow.pcr is not None
        assert flow.pcr > 1.3
        assert flow.pcr_score == -10

    def test_pcr_neutral(self, config):
        """PCR between 0.7 and 1.3 -> pcr_score = 0."""
        options_data = [
            {"details": {"contract_type": "call", "strike_price": 105.0},
             "day": {"volume": 1000}},
            {"details": {"contract_type": "put", "strike_price": 95.0},
             "day": {"volume": 1000}},
        ]
        bars = self._basic_bars()
        flow = _analyze_flow_from_data("TEST", bars, None, config,
                                       options_data=options_data)
        assert flow.pcr is not None
        assert 0.7 <= flow.pcr <= 1.3
        assert flow.pcr_score == 0

    def test_no_options_data(self, config):
        """options_data=None -> pcr=None, pcr_score=0."""
        bars = self._basic_bars()
        flow = _analyze_flow_from_data("TEST", bars, None, config,
                                       options_data=None)
        assert flow.pcr is None
        assert flow.pcr_score == 0


# ============================================================================
# TestOTMCallRatio — 3 tests
# ============================================================================

class TestOTMCallRatio:
    """Test OTM call ratio scoring in _analyze_flow_from_data."""

    def _basic_bars(self, n=30):
        return _make_bars([100.0] * n)

    def test_otm_above_threshold(self, config):
        """>40% OTM calls -> otm_score = +10."""
        # Current price = 100. OTM calls have strike > 100.
        # 3000 OTM call volume out of 4000 total call volume = 75%
        options_data = [
            {"details": {"contract_type": "call", "strike_price": 110.0},
             "day": {"volume": 3000}},
            {"details": {"contract_type": "call", "strike_price": 95.0},
             "day": {"volume": 1000}},
        ]
        bars = self._basic_bars()
        flow = _analyze_flow_from_data("TEST", bars, None, config,
                                       options_data=options_data)
        assert flow.otm_call_ratio is not None
        assert flow.otm_call_ratio > 0.4
        assert flow.otm_score == 10

    def test_otm_below_threshold(self, config):
        """<40% OTM calls -> otm_score = 0."""
        # 500 OTM call volume out of 5000 total call volume = 10%
        options_data = [
            {"details": {"contract_type": "call", "strike_price": 110.0},
             "day": {"volume": 500}},
            {"details": {"contract_type": "call", "strike_price": 90.0},
             "day": {"volume": 4500}},
        ]
        bars = self._basic_bars()
        flow = _analyze_flow_from_data("TEST", bars, None, config,
                                       options_data=options_data)
        assert flow.otm_call_ratio is not None
        assert flow.otm_call_ratio < 0.4
        assert flow.otm_score == 0

    def test_no_call_volume_safe(self, config):
        """0 call volume -> no division error, otm_call_ratio=None."""
        # Only puts, no calls
        options_data = [
            {"details": {"contract_type": "put", "strike_price": 90.0},
             "day": {"volume": 5000}},
        ]
        bars = self._basic_bars()
        flow = _analyze_flow_from_data("TEST", bars, None, config,
                                       options_data=options_data)
        assert flow.otm_call_ratio is None
        assert flow.otm_score == 0


# ============================================================================
# TestBlockTrade — 4 tests
# ============================================================================

class TestBlockTrade:
    """Test block trade counting in _aggregate_dp_records and scoring in flow analysis."""

    def _make_dp_record(self, size, price, volume=100000):
        """Create a minimal DP trade record for _aggregate_dp_records."""
        return {
            "size": size,
            "price": price,
            "volume": volume,
            "executed_at": "2099-01-01T12:00:00",
            "tracking_timestamp": "2099-01-01 12:00:00",
            "nbbo_ask": price + 1,
            "nbbo_bid": price - 1,
        }

    def test_block_count_in_aggregate(self):
        """Verify _aggregate_dp_records counts block trades ($500K+ notional)."""
        records = [
            self._make_dp_record(10000, 100.0),   # 10000*100 = 1M > 500K -> block
            self._make_dp_record(100, 100.0),      # 100*100 = 10K < 500K -> not block
            self._make_dp_record(5000, 200.0),     # 5000*200 = 1M > 500K -> block
        ]
        result = _aggregate_dp_records(records)
        assert result["block_trade_count"] == 2

    def test_block_score_above_20(self, config):
        """block_trade_count=25 (>20) -> block_trade_score = 15."""
        dp_data = {"block_trade_count": 25, "dp_pct": 0.0}
        bars = _make_bars([100.0] * 30)
        flow = _analyze_flow_from_data("TEST", bars, dp_data, config)
        assert flow.block_trade_count == 25
        assert flow.block_trade_score == 15

    def test_block_score_above_5(self, config):
        """block_trade_count=10 (>5, <=20) -> block_trade_score = 10."""
        dp_data = {"block_trade_count": 10, "dp_pct": 0.0}
        bars = _make_bars([100.0] * 30)
        flow = _analyze_flow_from_data("TEST", bars, dp_data, config)
        assert flow.block_trade_count == 10
        assert flow.block_trade_score == 10

    def test_block_score_below_5(self, config):
        """block_trade_count=3 (<=5) -> block_trade_score = 0."""
        dp_data = {"block_trade_count": 3, "dp_pct": 0.0}
        bars = _make_bars([100.0] * 30)
        flow = _analyze_flow_from_data("TEST", bars, dp_data, config)
        assert flow.block_trade_count == 3
        assert flow.block_trade_score == 0


# ============================================================================
# TestSharkDetector — 5 tests
# ============================================================================

class TestSharkDetector:
    """Test _detect_shark insider cluster detection."""

    def _future_date(self, days_from_now=1):
        """Return a future date string that's always within the lookback window."""
        return (date.today() + timedelta(days=days_from_now)).isoformat()

    def _recent_date(self, days_ago=1):
        """Return a recent date string within the shark lookback window (10 days)."""
        return (date.today() - timedelta(days=days_ago)).isoformat()

    def _old_date(self, days_ago=30):
        """Return an old date outside the shark lookback window."""
        return (date.today() - timedelta(days=days_ago)).isoformat()

    def test_cluster_detected(self, config):
        """2 unique insiders, recent, total > $100K -> True."""
        insider_data = [
            {"transactionDate": self._recent_date(1),
             "acquistionOrDisposition": "A",
             "reportingCik": "CIK001",
             "securitiesTransacted": 1000, "price": 60.0},
            {"transactionDate": self._recent_date(2),
             "acquistionOrDisposition": "A",
             "reportingCik": "CIK002",
             "securitiesTransacted": 1000, "price": 60.0},
        ]
        # Total value: 1000*60 + 1000*60 = 120K > 100K, 2 unique insiders
        assert _detect_shark(insider_data, config) is True

    def test_single_insider_not_enough(self, config):
        """1 insider (even with high value) -> False."""
        insider_data = [
            {"transactionDate": self._recent_date(1),
             "acquistionOrDisposition": "A",
             "reportingCik": "CIK001",
             "securitiesTransacted": 5000, "price": 100.0},
        ]
        # Total value: 500K, but only 1 unique insider
        assert _detect_shark(insider_data, config) is False

    def test_low_value_not_enough(self, config):
        """2 insiders but total < $100K -> False."""
        insider_data = [
            {"transactionDate": self._recent_date(1),
             "acquistionOrDisposition": "A",
             "reportingCik": "CIK001",
             "securitiesTransacted": 100, "price": 10.0},
            {"transactionDate": self._recent_date(2),
             "acquistionOrDisposition": "A",
             "reportingCik": "CIK002",
             "securitiesTransacted": 100, "price": 10.0},
        ]
        # Total value: 100*10 + 100*10 = 2K < 100K
        assert _detect_shark(insider_data, config) is False

    def test_old_trades_excluded(self, config):
        """2 insiders but transactionDate is old (before cutoff) -> False."""
        insider_data = [
            {"transactionDate": self._old_date(30),
             "acquistionOrDisposition": "A",
             "reportingCik": "CIK001",
             "securitiesTransacted": 2000, "price": 100.0},
            {"transactionDate": self._old_date(25),
             "acquistionOrDisposition": "A",
             "reportingCik": "CIK002",
             "securitiesTransacted": 2000, "price": 100.0},
        ]
        # Dates are 25-30 days old, shark_lookback_days=10 -> excluded
        assert _detect_shark(insider_data, config) is False

    def test_shark_bonus_in_fundamental(self, config):
        """Fundamental scoring includes +10 shark bonus when cluster detected."""
        insider_data = [
            {"transactionDate": self._recent_date(1),
             "acquistionOrDisposition": "A",
             "reportingCik": "CIK001",
             "securitiesTransacted": 1000, "price": 60.0},
            {"transactionDate": self._recent_date(2),
             "acquistionOrDisposition": "A",
             "reportingCik": "CIK002",
             "securitiesTransacted": 1000, "price": 60.0},
        ]
        # No growth/metrics data -> base funda_score=0 before shark bonus
        funda = _analyze_fundamental_from_data("TEST", None, None,
                                               insider_data, config)
        assert funda.shark_detected is True
        assert funda.funda_score >= 10  # At least +10 from shark bonus


# ============================================================================
# TestCombinedScoreBC9 — 3 tests
# ============================================================================

class TestCombinedScoreBC9:
    """Test combined score formula includes new BC9 components."""

    def test_tech_score_includes_sma50_and_rs(self, config):
        """Tech sub-score = rsi_score + sma50_bonus + rs_spy_score (0-100, no base).

        tech=0+30+40=70, flow=50+0=50, funda=50+0=50
        combined = 0.4*50 + 0.3*50 + 0.3*70 = 20 + 15 + 21 = 56.0
        """
        tech = TechnicalAnalysis(
            price=100, sma_200=90, sma_20=95, rsi_14=55,
            atr_14=2.0, trend_pass=True, rsi_score=0,
            sma_50=95.0, sma50_bonus=30, rs_spy_score=40,
        )
        flow = FlowAnalysis(rvol_score=0)
        funda = FundamentalScoring(funda_score=0, insider_multiplier=1.0)
        combined = _calculate_combined_score(tech, flow, funda, 0, config)
        assert combined == 56.0

    def test_flow_score_includes_options_and_blocks(self, config):
        """Flow sub-score = BASE + rvol_score (which aggregates pcr+otm+block).

        tech=0, flow=50+40=90, funda=50+0=50
        combined = 0.4*90 + 0.3*50 + 0.3*0 = 36 + 15 + 0 = 51.0
        """
        tech = TechnicalAnalysis(
            price=100, sma_200=90, sma_20=95, rsi_14=55,
            atr_14=2.0, trend_pass=True, rsi_score=0,
        )
        flow = FlowAnalysis(rvol_score=40)  # e.g. 15(pcr) + 15(block) + 10(otm) = 40
        funda = FundamentalScoring(funda_score=0, insider_multiplier=1.0)
        combined = _calculate_combined_score(tech, flow, funda, 0, config)
        assert combined == 51.0

    def test_backward_compat_neutral(self, config):
        """All zeros -> flow=50, funda=50, tech=0 → combined=35."""
        tech = TechnicalAnalysis(
            price=100, sma_200=90, sma_20=95, rsi_14=50,
            atr_14=2.0, trend_pass=True, rsi_score=0,
        )
        flow = FlowAnalysis(rvol_score=0)
        funda = FundamentalScoring(funda_score=0, insider_multiplier=1.0)
        combined = _calculate_combined_score(tech, flow, funda, 0, config)
        # tech=0, flow=50, funda=50 -> 0.4*50 + 0.3*50 + 0.3*0 = 20+15+0 = 35
        assert combined == 35.0
