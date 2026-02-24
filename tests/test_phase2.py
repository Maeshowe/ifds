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
        filtered, excluded, _, _ = _exclude_earnings(tickers, fmp, 5, logger)
        assert len(filtered) == 2
        assert "NVDA" in excluded
        assert all(t.symbol != "NVDA" for t in filtered)

    def test_no_exclusion_when_no_earnings(self, logger):
        tickers = [Ticker(symbol="AAPL"), Ticker(symbol="NVDA")]
        fmp = MagicMock()
        fmp.get_earnings_calendar.return_value = []
        fmp.get_next_earnings_date.return_value = None  # Pass 2: no earnings
        filtered, excluded, _, _ = _exclude_earnings(tickers, fmp, 5, logger)
        assert len(filtered) == 2
        assert len(excluded) == 0

    def test_no_exclusion_when_api_fails(self, logger):
        tickers = [Ticker(symbol="AAPL")]
        fmp = MagicMock()
        fmp.get_earnings_calendar.return_value = None
        fmp.get_next_earnings_date.return_value = None  # Pass 2: no earnings
        filtered, excluded, _, _ = _exclude_earnings(tickers, fmp, 5, logger)
        assert len(filtered) == 1
        assert len(excluded) == 0

    def test_empty_tickers_returns_empty(self, logger):
        fmp = MagicMock()
        filtered, excluded, _, _ = _exclude_earnings([], fmp, 5, logger)
        assert filtered == []
        assert excluded == []

    def test_case_insensitive_matching(self, logger):
        tickers = [Ticker(symbol="aapl")]
        fmp = MagicMock()
        fmp.get_earnings_calendar.return_value = [{"symbol": "AAPL"}]
        filtered, excluded, _, _ = _exclude_earnings(tickers, fmp, 5, logger)
        assert len(filtered) == 0
        assert "aapl" in excluded


class TestEarningsExclusionPass2:
    """Test two-pass earnings exclusion (ticker-specific fallback)."""

    def test_ticker_specific_catch(self, logger):
        """Ticker not in bulk calendar but caught by ticker-specific endpoint."""
        tickers = [Ticker(symbol="ALC"), Ticker(symbol="GE")]
        fmp = MagicMock()
        # Bulk calendar misses ALC
        fmp.get_earnings_calendar.return_value = []
        # Ticker-specific catches ALC (within 7-day window)
        fmp.get_next_earnings_date.side_effect = lambda t: {
            "ALC": "2026-02-24",  # today or within window
            "GE": "2026-04-22",   # far out — not excluded
        }.get(t)

        with patch("ifds.phases.phase2_universe.date") as mock_date:
            mock_date.today.return_value = date(2026, 2, 24)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            filtered, excluded, _, _ = _exclude_earnings(tickers, fmp, 7, logger)

        assert "ALC" in excluded
        assert len(filtered) == 1
        assert filtered[0].symbol == "GE"

    def test_bulk_catches_ticker_specific_skips(self, logger):
        """Ticker caught by bulk → not checked again in Pass 2."""
        tickers = [Ticker(symbol="NVDA"), Ticker(symbol="AAPL")]
        fmp = MagicMock()
        fmp.get_earnings_calendar.return_value = [{"symbol": "NVDA"}]
        # Pass 2 should only check AAPL (NVDA already excluded)
        fmp.get_next_earnings_date.return_value = None

        filtered, excluded, _, _ = _exclude_earnings(tickers, fmp, 5, logger)

        assert "NVDA" in excluded
        assert len(filtered) == 1
        # NVDA should NOT have been checked in Pass 2
        calls = [c[0][0] for c in fmp.get_next_earnings_date.call_args_list]
        assert "NVDA" not in calls
        assert "AAPL" in calls

    def test_ticker_specific_error_passthrough(self, logger):
        """API error on ticker-specific → fail-open, ticker passes through."""
        tickers = [Ticker(symbol="BADAPI")]
        fmp = MagicMock()
        fmp.get_earnings_calendar.return_value = []
        fmp.get_next_earnings_date.side_effect = Exception("FMP timeout")

        filtered, excluded, _, _ = _exclude_earnings(tickers, fmp, 5, logger)

        assert len(filtered) == 1
        assert filtered[0].symbol == "BADAPI"
        assert len(excluded) == 0

    def test_both_passes_miss(self, logger):
        """Neither bulk nor ticker-specific has earnings → ticker passes."""
        tickers = [Ticker(symbol="SAFE")]
        fmp = MagicMock()
        fmp.get_earnings_calendar.return_value = []
        fmp.get_next_earnings_date.return_value = None

        filtered, excluded, _, _ = _exclude_earnings(tickers, fmp, 5, logger)

        assert len(filtered) == 1
        assert len(excluded) == 0

    def test_ticker_specific_date_outside_window(self, logger):
        """Ticker-specific returns date beyond the exclusion window → passes."""
        tickers = [Ticker(symbol="FAR")]
        fmp = MagicMock()
        fmp.get_earnings_calendar.return_value = []
        fmp.get_next_earnings_date.return_value = "2026-06-15"

        with patch("ifds.phases.phase2_universe.date") as mock_date:
            mock_date.today.return_value = date(2026, 2, 24)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            filtered, excluded, _, _ = _exclude_earnings(tickers, fmp, 7, logger)

        assert len(filtered) == 1
        assert len(excluded) == 0

    def test_log_summary_counts(self, logger):
        """Summary log contains correct bulk and ticker-specific counts."""
        tickers = [
            Ticker(symbol="BULK"),
            Ticker(symbol="ADR"),
            Ticker(symbol="SAFE"),
        ]
        fmp = MagicMock()
        # BULK caught by bulk calendar
        fmp.get_earnings_calendar.return_value = [{"symbol": "BULK"}]
        # ADR caught by ticker-specific
        fmp.get_next_earnings_date.side_effect = lambda t: {
            "ADR": "2026-02-25",
            "SAFE": "2026-05-01",
        }.get(t)

        with patch("ifds.phases.phase2_universe.date") as mock_date:
            mock_date.today.return_value = date(2026, 2, 24)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            filtered, excluded, bulk_n, ticker_n = _exclude_earnings(tickers, fmp, 7, logger)

        assert len(excluded) == 2
        assert "BULK" in excluded
        assert "ADR" in excluded
        assert bulk_n == 1
        assert ticker_n == 1
        assert len(filtered) == 1

        # Check summary log
        summary_logs = [
            e for e in logger.events
            if "Earnings exclusion:" in e.get("message", "")
        ]
        assert len(summary_logs) == 1
        data = summary_logs[0]["data"]
        assert data["total_excluded"] == 2
        assert data["bulk_excluded"] == 1
        assert data["ticker_specific_excluded"] == 1
        assert data["ticker_specific_catches"] == ["ADR"]


class TestPhase2Integration:
    def test_long_mode_full_flow(self, config, logger):
        fmp = MagicMock()
        fmp.screener.return_value = [
            _make_fmp_ticker("AAPL"),
            _make_fmp_ticker("NVDA"),
            _make_fmp_ticker("MSFT"),
        ]
        fmp.get_earnings_calendar.return_value = [{"symbol": "MSFT"}]
        fmp.get_next_earnings_date.return_value = None  # Pass 2: no extra catch

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
        fmp.get_next_earnings_date.return_value = None

        result = run_phase2(config, logger, fmp, StrategyMode.SHORT)

        assert result.strategy_mode == StrategyMode.SHORT
        assert len(result.tickers) == 1
        assert result.tickers[0].symbol == "ZOMBIE1"

    def test_logs_universe_built(self, config, logger):
        fmp = MagicMock()
        fmp.screener.return_value = [_make_fmp_ticker("AAPL")]
        fmp.get_earnings_calendar.return_value = []
        fmp.get_next_earnings_date.return_value = None

        run_phase2(config, logger, fmp, StrategyMode.LONG)

        universe_events = [e for e in logger.events if e["event_type"] == "UNIVERSE_BUILT"]
        assert len(universe_events) == 1
        assert universe_events[0]["data"]["ticker_count"] == 1
