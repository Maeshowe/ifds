"""Tests for Phase 1: Market Regime (BMI)."""

import pytest
from unittest.mock import MagicMock, patch

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import BMIRegime, StrategyMode
from ifds.phases.phase1_regime import (
    run_phase1,
    _classify_bmi,
    _calculate_daily_ratios,
    _detect_divergence,
    _find_spy_close,
)


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    return Config()


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-phase1")


def _make_bar(ticker, open_price, close, volume):
    """Create a mock bar dict."""
    return {"T": ticker, "o": open_price, "c": close, "v": volume, "h": close + 1, "l": open_price - 1}


def _make_daily_data(days_count, tickers_per_day=50, base_volume=1000):
    """Create mock grouped daily data with predictable volume spikes."""
    daily_data = []
    for day_idx in range(days_count):
        bars = []
        for t in range(tickers_per_day):
            ticker = f"T{t:03d}"
            # Normal volume with occasional spikes
            vol = base_volume
            open_p = 100.0
            close_p = 100.0
            bars.append(_make_bar(ticker, open_p, close_p, vol))
        daily_data.append({"date": f"2026-01-{day_idx + 1:02d}", "bars": bars})
    return daily_data


class TestBMIClassification:
    def test_green(self, config):
        assert _classify_bmi(20.0, config) == BMIRegime.GREEN

    def test_green_boundary(self, config):
        assert _classify_bmi(25.0, config) == BMIRegime.GREEN

    def test_yellow(self, config):
        assert _classify_bmi(50.0, config) == BMIRegime.YELLOW

    def test_red(self, config):
        assert _classify_bmi(85.0, config) == BMIRegime.RED

    def test_red_boundary(self, config):
        assert _classify_bmi(80.0, config) == BMIRegime.RED

    def test_yellow_lower_boundary(self, config):
        assert _classify_bmi(25.1, config) == BMIRegime.YELLOW

    def test_yellow_upper_boundary(self, config):
        assert _classify_bmi(79.9, config) == BMIRegime.YELLOW


class TestDailyRatios:
    def test_no_spikes_returns_neutral(self, config):
        """When no volume spikes detected, ratios are 50% (neutral)."""
        daily = _make_daily_data(25)
        ratios = _calculate_daily_ratios(daily, config)
        # First vol_period days have no stats yet, so they'll be 50 (no signals)
        assert all(r == 50.0 for r in ratios)

    def test_all_buys_returns_100(self, config):
        """When all spikes are buys, ratio = 100."""
        daily_data = _make_daily_data(25, tickers_per_day=5, base_volume=100)
        # On the last day, add massive volume with close > open for all
        for bar in daily_data[-1]["bars"]:
            bar["v"] = 100000  # Way above mean + 2*sigma
            bar["c"] = 200.0   # Close > open (buy signal)
            bar["o"] = 100.0
        ratios = _calculate_daily_ratios(daily_data, config)
        assert ratios[-1] == 100.0

    def test_all_sells_returns_0(self, config):
        """When all spikes are sells, ratio = 0."""
        daily_data = _make_daily_data(25, tickers_per_day=5, base_volume=100)
        for bar in daily_data[-1]["bars"]:
            bar["v"] = 100000
            bar["c"] = 50.0    # Close < open (sell signal)
            bar["o"] = 100.0
        ratios = _calculate_daily_ratios(daily_data, config)
        assert ratios[-1] == 0.0

    def test_mixed_signals(self, config):
        """Mix of buys and sells produces intermediate ratio."""
        daily_data = _make_daily_data(25, tickers_per_day=4, base_volume=100)
        bars = daily_data[-1]["bars"]
        # 3 buys, 1 sell
        for i, bar in enumerate(bars):
            bar["v"] = 100000
            if i < 3:
                bar["c"] = 200.0
                bar["o"] = 100.0
            else:
                bar["c"] = 50.0
                bar["o"] = 100.0
        ratios = _calculate_daily_ratios(daily_data, config)
        assert ratios[-1] == 75.0  # 3 / (3+1) * 100


class TestDivergenceDetection:
    def test_no_divergence_when_insufficient_data(self, config):
        daily = _make_daily_data(3)
        ratios = [50.0, 50.0, 50.0]
        assert _detect_divergence(daily, ratios, config) is None

    def test_bearish_divergence(self, config):
        """SPY up > 1%, BMI down > 2 pts → bearish divergence."""
        daily = _make_daily_data(7, tickers_per_day=2)
        # Add SPY to bars
        for i, d in enumerate(daily):
            spy_close = 450.0 + (i * 2)  # SPY going up
            d["bars"].append(_make_bar("SPY", 450.0, spy_close, 50000000))

        # BMI ratios declining
        ratios = [60.0, 59.0, 58.0, 57.0, 56.0, 55.0, 54.0]
        # SPY change: (462 - 450) / 450 * 100 ≈ 2.67% > 1%
        # BMI change: 54 - 60 = -6 < -2
        result = _detect_divergence(daily, ratios, config)
        assert result == "bearish"

    def test_no_divergence_when_both_up(self, config):
        """SPY up and BMI up → no divergence."""
        daily = _make_daily_data(7, tickers_per_day=2)
        for i, d in enumerate(daily):
            d["bars"].append(_make_bar("SPY", 450.0, 450.0 + i * 2, 50000000))
        ratios = [50.0, 51.0, 52.0, 53.0, 54.0, 55.0, 56.0]
        assert _detect_divergence(daily, ratios, config) is None


class TestFindSPYClose:
    def test_finds_spy(self):
        day = {"bars": [_make_bar("AAPL", 100, 105, 1000), _make_bar("SPY", 450, 455, 9000000)]}
        assert _find_spy_close(day) == 455

    def test_returns_none_when_no_spy(self):
        day = {"bars": [_make_bar("AAPL", 100, 105, 1000)]}
        assert _find_spy_close(day) is None


class TestPhase1Integration:
    @patch("ifds.phases.phase1_regime._fetch_daily_history")
    def test_insufficient_data_returns_fallback(self, mock_fetch, config, logger):
        """When not enough data, return conservative YELLOW/LONG."""
        mock_fetch.return_value = []

        polygon = MagicMock()
        result = run_phase1(config, logger, polygon)

        assert result.bmi.bmi_regime == BMIRegime.YELLOW
        assert result.strategy_mode == StrategyMode.LONG
        assert result.bmi.bmi_value == 50.0

    @patch("ifds.phases.phase1_regime._calculate_daily_ratios")
    @patch("ifds.phases.phase1_regime._fetch_daily_history")
    def test_green_regime_selects_long(self, mock_fetch, mock_ratios, config, logger):
        """GREEN BMI → LONG strategy (low buy ratio → BMI ≤ 25%)."""
        mock_fetch.return_value = _make_daily_data(30)
        # All sell-dominated days → ratio ≈ 10% → BMI ≤ 25 → GREEN
        mock_ratios.return_value = [10.0] * 30

        polygon = MagicMock()
        result = run_phase1(config, logger, polygon)

        assert result.bmi.bmi_regime == BMIRegime.GREEN
        assert result.strategy_mode == StrategyMode.LONG

    @patch("ifds.phases.phase1_regime._calculate_daily_ratios")
    @patch("ifds.phases.phase1_regime._fetch_daily_history")
    def test_red_regime_selects_short(self, mock_fetch, mock_ratios, config, logger):
        """RED BMI → SHORT strategy (high buy ratio → BMI ≥ 80%)."""
        mock_fetch.return_value = _make_daily_data(30)
        # All buy-dominated days → ratio ≈ 90% → BMI ≥ 80 → RED
        mock_ratios.return_value = [90.0] * 30

        polygon = MagicMock()
        result = run_phase1(config, logger, polygon)

        assert result.bmi.bmi_regime == BMIRegime.RED
        assert result.strategy_mode == StrategyMode.SHORT

    @patch("ifds.phases.phase1_regime._fetch_daily_history")
    def test_logs_regime_decision(self, mock_fetch, config, logger):
        """Phase 1 should log a REGIME_DECISION event."""
        mock_fetch.return_value = _make_daily_data(30)

        polygon = MagicMock()
        run_phase1(config, logger, polygon)

        regime_events = [e for e in logger.events if e["event_type"] == "REGIME_DECISION"]
        assert len(regime_events) == 1
        assert "bmi_value" in regime_events[0]["data"]
        assert "strategy_mode" in regime_events[0]["data"]
