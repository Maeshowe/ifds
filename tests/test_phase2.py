"""Tests for Phase 2: Universe Building."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import date

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import StrategyMode, Ticker
from ifds.phases.phase2_universe import (
    run_phase2,
    _screen_long_universe,
    _screen_short_universe,
    _exclude_earnings,
    _fmp_to_ticker,
)


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    return Config()


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-phase2")


def _make_fmp_ticker(symbol, market_cap=5e9, price=50.0, volume=1e6,
                     is_etf=False, sector="Technology",
                     debt_equity=None, net_margin=None, interest_coverage=None):
    """Create a mock FMP screener result."""
    result = {
        "symbol": symbol,
        "companyName": f"{symbol} Inc",
        "sector": sector,
        "marketCap": market_cap,
        "price": price,
        "volume": volume,
        "isEtf": is_etf,
        "isActivelyTrading": True,
    }
    if debt_equity is not None:
        result["debtToEquity"] = debt_equity
    if net_margin is not None:
        result["netIncomeMargin"] = net_margin
    if interest_coverage is not None:
        result["interestCoverage"] = interest_coverage
    return result


class TestFMPToTicker:
    def test_basic_conversion(self):
        raw = _make_fmp_ticker("NVDA", market_cap=1e12, price=900, volume=50e6)
        ticker = _fmp_to_ticker(raw)
        assert ticker.symbol == "NVDA"
        assert ticker.market_cap == 1e12
        assert ticker.price == 900
        assert ticker.sector == "Technology"

    def test_handles_missing_fields(self):
        ticker = _fmp_to_ticker({"symbol": "TEST"})
        assert ticker.symbol == "TEST"
        assert ticker.market_cap == 0
        assert ticker.price == 0


class TestLongUniverseScreening:
    def test_returns_tickers(self, config, logger):
        fmp = MagicMock()
        fmp.screener.return_value = [
            _make_fmp_ticker("AAPL"),
            _make_fmp_ticker("NVDA"),
            _make_fmp_ticker("MSFT"),
        ]
        tickers = _screen_long_universe(fmp, config, logger)
        assert len(tickers) == 3
        assert tickers[0].symbol == "AAPL"

    def test_empty_screener_returns_empty(self, config, logger):
        fmp = MagicMock()
        fmp.screener.return_value = None
        tickers = _screen_long_universe(fmp, config, logger)
        assert len(tickers) == 0

    def test_filters_inactive_tickers(self, config, logger):
        fmp = MagicMock()
        inactive = _make_fmp_ticker("DEAD")
        inactive["isActivelyTrading"] = False
        fmp.screener.return_value = [
            _make_fmp_ticker("AAPL"),
            inactive,
        ]
        tickers = _screen_long_universe(fmp, config, logger)
        assert len(tickers) == 1
        assert tickers[0].symbol == "AAPL"

    def test_passes_correct_params(self, config, logger):
        fmp = MagicMock()
        fmp.screener.return_value = []
        _screen_long_universe(fmp, config, logger)
        call_params = fmp.screener.call_args[0][0]
        assert call_params["marketCapMoreThan"] == 2_000_000_000
        assert call_params["priceMoreThan"] == 5.0
        assert call_params["volumeMoreThan"] == 500_000
        assert call_params["isEtf"] == "false"


class TestShortUniverseScreening:
    def test_zombie_criteria_filter(self, config, logger):
        fmp = MagicMock()
        fmp.screener.return_value = [
            # True zombie: D/E > 3, negative margin, low IC
            _make_fmp_ticker("ZOMBIE", debt_equity=5.0, net_margin=-0.15,
                             interest_coverage=0.8),
            # Not zombie: healthy company
            _make_fmp_ticker("HEALTHY", debt_equity=0.5, net_margin=0.20,
                             interest_coverage=10.0),
            # Not zombie: low D/E
            _make_fmp_ticker("LOWDE", debt_equity=1.0, net_margin=-0.10,
                             interest_coverage=0.5),
        ]
        tickers = _screen_short_universe(fmp, config, logger)
        assert len(tickers) == 1
        assert tickers[0].symbol == "ZOMBIE"
        assert tickers[0].debt_equity == 5.0

    def test_requires_negative_margin(self, config, logger):
        fmp = MagicMock()
        fmp.screener.return_value = [
            _make_fmp_ticker("HIGH_DE", debt_equity=5.0, net_margin=0.05,
                             interest_coverage=0.8),
        ]
        tickers = _screen_short_universe(fmp, config, logger)
        assert len(tickers) == 0

    def test_empty_screener_returns_empty(self, config, logger):
        fmp = MagicMock()
        fmp.screener.return_value = None
        tickers = _screen_short_universe(fmp, config, logger)
        assert len(tickers) == 0


class TestEarningsExclusion:
    def test_excludes_tickers_with_earnings(self, logger):
        tickers = [
            Ticker(symbol="AAPL"),
            Ticker(symbol="NVDA"),
            Ticker(symbol="MSFT"),
        ]
        fmp = MagicMock()
        fmp.get_earnings_calendar.return_value = [
            {"symbol": "NVDA", "date": "2026-02-10"},
        ]
        filtered, excluded = _exclude_earnings(tickers, fmp, 5, logger)
        assert len(filtered) == 2
        assert "NVDA" in excluded
        assert all(t.symbol != "NVDA" for t in filtered)

    def test_no_exclusion_when_no_earnings(self, logger):
        tickers = [Ticker(symbol="AAPL"), Ticker(symbol="NVDA")]
        fmp = MagicMock()
        fmp.get_earnings_calendar.return_value = []
        filtered, excluded = _exclude_earnings(tickers, fmp, 5, logger)
        assert len(filtered) == 2
        assert len(excluded) == 0

    def test_no_exclusion_when_api_fails(self, logger):
        tickers = [Ticker(symbol="AAPL")]
        fmp = MagicMock()
        fmp.get_earnings_calendar.return_value = None
        filtered, excluded = _exclude_earnings(tickers, fmp, 5, logger)
        assert len(filtered) == 1
        assert len(excluded) == 0

    def test_empty_tickers_returns_empty(self, logger):
        fmp = MagicMock()
        filtered, excluded = _exclude_earnings([], fmp, 5, logger)
        assert filtered == []
        assert excluded == []

    def test_case_insensitive_matching(self, logger):
        tickers = [Ticker(symbol="aapl")]
        fmp = MagicMock()
        fmp.get_earnings_calendar.return_value = [{"symbol": "AAPL"}]
        filtered, excluded = _exclude_earnings(tickers, fmp, 5, logger)
        assert len(filtered) == 0
        assert "aapl" in excluded


class TestPhase2Integration:
    def test_long_mode_full_flow(self, config, logger):
        fmp = MagicMock()
        fmp.screener.return_value = [
            _make_fmp_ticker("AAPL"),
            _make_fmp_ticker("NVDA"),
            _make_fmp_ticker("MSFT"),
        ]
        fmp.get_earnings_calendar.return_value = [{"symbol": "MSFT"}]

        result = run_phase2(config, logger, fmp, StrategyMode.LONG)

        assert result.strategy_mode == StrategyMode.LONG
        assert result.total_screened == 3
        assert len(result.tickers) == 2  # MSFT excluded by earnings
        assert "MSFT" in result.earnings_excluded

    def test_short_mode_flow(self, config, logger):
        fmp = MagicMock()
        fmp.screener.return_value = [
            _make_fmp_ticker("ZOMBIE1", debt_equity=5.0, net_margin=-0.15,
                             interest_coverage=0.8),
        ]
        fmp.get_earnings_calendar.return_value = []

        result = run_phase2(config, logger, fmp, StrategyMode.SHORT)

        assert result.strategy_mode == StrategyMode.SHORT
        assert len(result.tickers) == 1
        assert result.tickers[0].symbol == "ZOMBIE1"

    def test_logs_universe_built(self, config, logger):
        fmp = MagicMock()
        fmp.screener.return_value = [_make_fmp_ticker("AAPL")]
        fmp.get_earnings_calendar.return_value = []

        run_phase2(config, logger, fmp, StrategyMode.LONG)

        universe_events = [e for e in logger.events if e["event_type"] == "UNIVERSE_BUILT"]
        assert len(universe_events) == 1
        assert universe_events[0]["data"]["ticker_count"] == 1
