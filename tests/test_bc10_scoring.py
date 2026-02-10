"""BC10 Scoring Tests — dp_pct fix (Polygon volume) + Buy Pressure VWAP scoring.

~15 tests covering the two P1 features:
1. dp_pct recalculated using Polygon daily volume as denominator
2. Buy Pressure (close position in bar range) + VWAP accumulation/distribution signal
"""

import pytest

from ifds.phases.phase4_stocks import (
    _analyze_flow_from_data,
)
from ifds.config.loader import Config
from ifds.models.market import DarkPoolSignal


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    return Config()


# ============================================================================
# Helpers
# ============================================================================

def _make_bar(close, high=None, low=None, volume=1000, open_price=None, vw=None):
    """Create a mock OHLCV bar, optionally with VWAP (vw) field."""
    if high is None:
        high = close + 1
    if low is None:
        low = close - 1
    if open_price is None:
        open_price = close
    bar = {"o": open_price, "h": high, "l": low, "c": close, "v": volume}
    if vw is not None:
        bar["vw"] = vw
    return bar


def _make_bars(closes, volume=1000):
    return [_make_bar(c, volume=volume) for c in closes]


def _make_dp_data(dp_volume=0, signal="BULLISH"):
    """Create dp_data dict mimicking _aggregate_dp_records output."""
    return {
        "dp_volume": dp_volume,
        "total_volume": 0,  # UW volume field — unreliable
        "dp_pct": 0.0,       # This is the broken value we override
        "dp_buys": dp_volume // 2,
        "dp_sells": dp_volume // 2,
        "signal": signal,
        "source": "unusual_whales",
        "block_trade_count": 0,
    }


# ============================================================================
# TestDarkPoolPercentage — 6 tests
# ============================================================================

class TestDarkPoolPercentage:
    """dp_pct is recalculated using Polygon daily volume, not UW volume field."""

    def test_dp_pct_from_polygon_volume(self, config):
        """dp_volume=500K, bars[-1].v=1M → dp_pct=50% → dp_pct_score=+10."""
        dp_data = _make_dp_data(dp_volume=500_000, signal="BULLISH")
        bars = _make_bars([100.0] * 30, volume=1_000_000)
        flow = _analyze_flow_from_data("TEST", bars, dp_data, config)
        assert flow.dark_pool_pct == 50.0
        assert flow.dp_pct_score == 10

    def test_dp_pct_high_threshold(self, config):
        """dp_volume=700K, daily_volume=1M → dp_pct=70% → dp_pct_score=+15."""
        dp_data = _make_dp_data(dp_volume=700_000, signal="BULLISH")
        bars = _make_bars([100.0] * 30, volume=1_000_000)
        flow = _analyze_flow_from_data("TEST", bars, dp_data, config)
        assert flow.dark_pool_pct == 70.0
        assert flow.dp_pct_score == 15

    def test_dp_pct_below_threshold(self, config):
        """dp_volume=300K, daily_volume=1M → dp_pct=30% → dp_pct_score=0."""
        dp_data = _make_dp_data(dp_volume=300_000, signal="BULLISH")
        bars = _make_bars([100.0] * 30, volume=1_000_000)
        flow = _analyze_flow_from_data("TEST", bars, dp_data, config)
        assert flow.dark_pool_pct == 30.0
        assert flow.dp_pct_score == 0

    def test_dp_pct_zero_daily_volume(self, config):
        """daily_volume=0 → dp_pct stays 0.0."""
        dp_data = _make_dp_data(dp_volume=500_000, signal="BULLISH")
        bars = _make_bars([100.0] * 30, volume=0)
        flow = _analyze_flow_from_data("TEST", bars, dp_data, config)
        assert flow.dark_pool_pct == 0.0
        assert flow.dp_pct_score == 0

    def test_dp_signal_activates(self, config):
        """dp_pct > 40% → DarkPoolSignal activates."""
        dp_data = _make_dp_data(dp_volume=500_000, signal="BULLISH")
        bars = _make_bars([100.0] * 30, volume=1_000_000)
        flow = _analyze_flow_from_data("TEST", bars, dp_data, config)
        assert flow.dark_pool_signal == DarkPoolSignal.BULLISH

    def test_dp_signal_no_data(self, config):
        """dp_data=None → dp_pct=0.0, signal=None."""
        bars = _make_bars([100.0] * 30)
        flow = _analyze_flow_from_data("TEST", bars, None, config)
        assert flow.dark_pool_pct == 0.0
        assert flow.dark_pool_signal is None
        assert flow.dp_pct_score == 0


# ============================================================================
# TestBuyPressureVWAP — 7 tests
# ============================================================================

class TestBuyPressureVWAP:
    """Buy Pressure (close position in bar) + VWAP accumulation signal."""

    def test_vwap_from_polygon_field(self, config):
        """Bar has vw=95, close=100 → close > VWAP → accumulation bonus."""
        bars = _make_bars([100.0] * 29)
        # Last bar: close=100, vw=95 → close > VWAP → +10 accumulation
        # Also: (100-95)/95 = 5.3% > 1% → +5 extra (strong accumulation)
        bars.append(_make_bar(100, high=101, low=99, volume=1000, vw=95))
        flow = _analyze_flow_from_data("TEST", bars, None, config)
        assert flow.vwap == 95.0
        # buy_pos = (100-99)/(101-99) = 0.5 → no bar pressure bonus
        # VWAP: +10 (accumulation) + 5 (strong, >1%) = +15
        assert flow.buy_pressure_score == 15

    def test_vwap_fallback_typical_price(self, config):
        """No vw field → VWAP = (H+L+C)/3."""
        bars = _make_bars([100.0] * 30)
        # Default bar: H=101, L=99, C=100 → VWAP = (101+99+100)/3 = 100
        flow = _analyze_flow_from_data("TEST", bars, None, config)
        assert flow.vwap == 100.0
        # close == vwap → no VWAP bonus/penalty
        assert flow.buy_pressure_score == 0

    def test_buy_pressure_strong(self, config):
        """Close near high → buy_pos > 0.7 → +15."""
        bars = _make_bars([100.0] * 29)
        # Last bar: H=110, L=100, C=109 → buy_pos = (109-100)/10 = 0.9
        # VWAP fallback = (110+100+109)/3 ≈ 106.33, close=109 > 106.33 → +10
        # (109 - 106.33)/106.33 = 2.5% > 1% → +5 extra
        bars.append(_make_bar(109, high=110, low=100, volume=1000))
        flow = _analyze_flow_from_data("TEST", bars, None, config)
        assert flow.buy_pressure_score == 15 + 10 + 5  # bar(+15) + vwap(+10) + strong(+5)

    def test_buy_pressure_weak(self, config):
        """Close near low → buy_pos < 0.3 → -15."""
        bars = _make_bars([100.0] * 29)
        # Last bar: H=110, L=100, C=101 → buy_pos = (101-100)/10 = 0.1
        # VWAP fallback = (110+100+101)/3 ≈ 103.67, close=101 < 103.67 → -5
        bars.append(_make_bar(101, high=110, low=100, volume=1000))
        flow = _analyze_flow_from_data("TEST", bars, None, config)
        assert flow.buy_pressure_score == -15 + (-5)  # bar(-15) + vwap(-5)

    def test_vwap_strong_accumulation(self, config):
        """(close - VWAP) / VWAP > 1% → extra +5."""
        bars = _make_bars([100.0] * 29)
        # Last bar: close=105, vw=100 → (105-100)/100 = 5% > 1%
        # buy_pos: (105-99)/(106-99) = 6/7 ≈ 0.86 → +15 (strong bar)
        bars.append(_make_bar(105, high=106, low=99, volume=1000, vw=100))
        flow = _analyze_flow_from_data("TEST", bars, None, config)
        # bar(+15) + vwap(+10) + strong(+5)
        assert flow.buy_pressure_score == 30

    def test_vwap_distribution(self, config):
        """close < VWAP → -5 distribution penalty."""
        bars = _make_bars([100.0] * 29)
        # Last bar: close=98, vw=102 → distribution
        # buy_pos: (98-97)/(99-97) = 0.5 → no bar bonus
        bars.append(_make_bar(98, high=99, low=97, volume=1000, vw=102))
        flow = _analyze_flow_from_data("TEST", bars, None, config)
        assert flow.buy_pressure_score == -5

    def test_buy_pressure_in_rvol_score(self, config):
        """buy_pressure_score is included in composite rvol_score."""
        bars = _make_bars([100.0] * 29)
        # Last bar: strong buy pressure
        bars.append(_make_bar(109, high=110, low=100, volume=1000))
        flow_strong = _analyze_flow_from_data("TEST", bars, None, config)

        # Compare with neutral bars
        bars_neutral = _make_bars([100.0] * 30)
        flow_neutral = _analyze_flow_from_data("TEST", bars_neutral, None, config)

        # Strong buy pressure should give higher rvol_score
        assert flow_strong.rvol_score > flow_neutral.rvol_score
        assert flow_strong.buy_pressure_score > 0
        assert flow_neutral.buy_pressure_score == 0


# ============================================================================
# TestBC10Integration — 2 tests
# ============================================================================

class TestBC10Integration:
    """Integration tests combining dp_pct and buy pressure."""

    def test_full_flow_with_dp_and_vwap(self, config):
        """All components active: RVOL + DP + PCR + OTM + block + dp_pct + buy_pressure."""
        dp_data = _make_dp_data(dp_volume=700_000, signal="BULLISH")
        dp_data["block_trade_count"] = 10  # >5 → +10

        options_data = [
            {"details": {"contract_type": "call", "strike_price": 105.0},
             "day": {"volume": 5000}},
            {"details": {"contract_type": "put", "strike_price": 95.0},
             "day": {"volume": 500}},
        ]

        bars = _make_bars([100.0] * 29, volume=1_000_000)
        # Last bar: close near high + VWAP below close
        bars.append(_make_bar(109, high=110, low=100, volume=1_000_000, vw=102))

        flow = _analyze_flow_from_data("TEST", bars, dp_data, config,
                                       options_data=options_data)

        # dp_pct = 700K / 1M = 70% → dp_pct_score = +15 (>60%)
        assert flow.dark_pool_pct == 70.0
        assert flow.dp_pct_score == 15
        assert flow.dark_pool_signal == DarkPoolSignal.BULLISH

        # buy_pressure: buy_pos=0.9 → +15, VWAP: +10 + 5 (strong) = +15
        assert flow.buy_pressure_score == 30

        # PCR = 500/5000 = 0.1 < 0.7 → +15
        assert flow.pcr_score == 15

        # Block trade: 10 > 5 → +10
        assert flow.block_trade_score == 10

        # Composite rvol_score should include all
        assert flow.dp_pct_score in [10, 15]
        assert flow.buy_pressure_score > 0

    def test_no_dp_no_vwap_field(self, config):
        """dp_data=None, no vw field → dp_pct_score=0, VWAP uses typical price."""
        bars = _make_bars([100.0] * 30)
        flow = _analyze_flow_from_data("TEST", bars, None, config)

        assert flow.dark_pool_pct == 0.0
        assert flow.dp_pct_score == 0
        assert flow.dark_pool_signal is None
        assert flow.vwap == 100.0  # (101+99+100)/3
        assert flow.buy_pressure_score == 0  # neutral bars
