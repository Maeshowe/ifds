"""Tests for BC18-prep: Trading Calendar, Danger Zone Filter, Cache TTL Fix."""

from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import pytest

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import FundamentalScoring, Phase4Result


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    return Config()


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-bc18-prep")


# ============================================================================
# D1: Trading Calendar
# ============================================================================


class TestTradingCalendar:
    """Test NYSE trading calendar utilities."""

    def test_is_trading_day_weekday(self):
        from ifds.utils.trading_calendar import is_trading_day
        # 2026-02-17 is a Tuesday (regular trading day)
        assert is_trading_day(date(2026, 2, 17)) is True

    def test_is_trading_day_weekend(self):
        from ifds.utils.trading_calendar import is_trading_day
        # 2026-02-14 is a Saturday
        assert is_trading_day(date(2026, 2, 14)) is False
        # 2026-02-15 is a Sunday
        assert is_trading_day(date(2026, 2, 15)) is False

    def test_is_trading_day_presidents_day(self):
        from ifds.utils.trading_calendar import is_trading_day
        # Presidents' Day 2026 = Feb 16 (Monday)
        assert is_trading_day(date(2026, 2, 16)) is False

    def test_next_trading_day_simple(self):
        from ifds.utils.trading_calendar import next_trading_day
        # From Thursday Feb 12 → next trading day = Friday Feb 13
        assert next_trading_day(date(2026, 2, 12)) == date(2026, 2, 13)

    def test_next_trading_day_skips_weekend(self):
        from ifds.utils.trading_calendar import next_trading_day
        # From Friday Feb 13 → next trading day = Tuesday Feb 17 (skip sat, sun, Presidents' Day)
        assert next_trading_day(date(2026, 2, 13)) == date(2026, 2, 17)

    def test_next_trading_day_n(self):
        from ifds.utils.trading_calendar import next_trading_day
        # From Feb 12 (Thu), +3 trading days = Feb 13 (Fri), Feb 17 (Tue), Feb 18 (Wed)
        assert next_trading_day(date(2026, 2, 12), n=3) == date(2026, 2, 18)

    def test_prev_trading_day_simple(self):
        from ifds.utils.trading_calendar import prev_trading_day
        # From Wednesday Feb 18 → prev = Tuesday Feb 17
        assert prev_trading_day(date(2026, 2, 18)) == date(2026, 2, 17)

    def test_prev_trading_day_skips_holiday(self):
        from ifds.utils.trading_calendar import prev_trading_day
        # From Tuesday Feb 17 → prev = Friday Feb 13 (skip Presidents' Day + weekend)
        assert prev_trading_day(date(2026, 2, 17)) == date(2026, 2, 13)

    def test_trading_days_between(self):
        from ifds.utils.trading_calendar import trading_days_between
        # Feb 12-18, 2026: Thu(12), Fri(13), Sat(14-skip), Sun(15-skip),
        # Mon(16-Presidents Day-skip), Tue(17), Wed(18) = 4 trading days
        days = trading_days_between(date(2026, 2, 12), date(2026, 2, 18))
        assert len(days) == 4
        assert days[0] == date(2026, 2, 12)
        assert days[1] == date(2026, 2, 13)
        assert days[2] == date(2026, 2, 17)
        assert days[3] == date(2026, 2, 18)

    def test_add_trading_days_positive(self):
        from ifds.utils.trading_calendar import add_trading_days
        # From Feb 12, +3 trading days = Feb 18
        assert add_trading_days(date(2026, 2, 12), 3) == date(2026, 2, 18)

    def test_add_trading_days_negative(self):
        from ifds.utils.trading_calendar import add_trading_days
        # From Feb 18, -3 trading days = Feb 12
        assert add_trading_days(date(2026, 2, 18), -3) == date(2026, 2, 12)

    def test_add_trading_days_zero(self):
        from ifds.utils.trading_calendar import add_trading_days
        # 0 trading days = same date
        assert add_trading_days(date(2026, 2, 18), 0) == date(2026, 2, 18)

    def test_count_trading_days(self):
        from ifds.utils.trading_calendar import count_trading_days
        # From Feb 12 to Feb 18 (exclusive start, inclusive end)
        # = Feb 13, Feb 17, Feb 18 = 3 trading days
        assert count_trading_days(date(2026, 2, 12), date(2026, 2, 18)) == 3

    def test_next_trading_day_invalid_n(self):
        from ifds.utils.trading_calendar import next_trading_day
        with pytest.raises(ValueError):
            next_trading_day(date(2026, 2, 12), n=0)

    def test_christmas_not_trading_day(self):
        from ifds.utils.trading_calendar import is_trading_day
        # Christmas 2025 = Thursday Dec 25
        assert is_trading_day(date(2025, 12, 25)) is False


# ============================================================================
# D2: Danger Zone Filter
# ============================================================================


class TestDangerZone:
    """Test Bottom 10 danger zone filter."""

    def test_danger_zone_high_debt_negative_margin(self, config):
        """D/E=8 + margin=-15% → 2 signals → filtered."""
        from ifds.phases.phase4_stocks import _is_danger_zone
        funda = FundamentalScoring(
            debt_equity=8.0,
            net_margin=-0.15,
            interest_coverage=2.0,  # OK
        )
        assert _is_danger_zone(funda, config) is True

    def test_danger_zone_all_three_signals(self, config):
        """D/E=10 + margin=-20% + IC=0.5 → 3 signals → filtered."""
        from ifds.phases.phase4_stocks import _is_danger_zone
        funda = FundamentalScoring(
            debt_equity=10.0,
            net_margin=-0.20,
            interest_coverage=0.5,
        )
        assert _is_danger_zone(funda, config) is True

    def test_danger_zone_single_signal_passes(self, config):
        """D/E=8 only → 1 signal → NOT filtered (need 2+)."""
        from ifds.phases.phase4_stocks import _is_danger_zone
        funda = FundamentalScoring(
            debt_equity=8.0,
            net_margin=0.10,  # OK
            interest_coverage=5.0,  # OK
        )
        assert _is_danger_zone(funda, config) is False

    def test_danger_zone_low_debt_passes(self, config):
        """D/E=1.5, margin=10% → healthy company → passes."""
        from ifds.phases.phase4_stocks import _is_danger_zone
        funda = FundamentalScoring(
            debt_equity=1.5,
            net_margin=0.10,
            interest_coverage=5.0,
        )
        assert _is_danger_zone(funda, config) is False

    def test_danger_zone_none_values(self, config):
        """None fields → not counted as danger signals → passes."""
        from ifds.phases.phase4_stocks import _is_danger_zone
        funda = FundamentalScoring(
            debt_equity=None,
            net_margin=None,
            interest_coverage=None,
        )
        assert _is_danger_zone(funda, config) is False

    def test_danger_zone_config_override(self, config):
        """Custom thresholds from config."""
        from ifds.phases.phase4_stocks import _is_danger_zone
        # Override to very strict thresholds
        config.tuning["danger_zone_debt_equity"] = 2.0
        config.tuning["danger_zone_net_margin"] = 0.0
        config.tuning["danger_zone_min_signals"] = 2

        funda = FundamentalScoring(
            debt_equity=3.0,   # > 2.0 → danger
            net_margin=-0.01,  # < 0.0 → danger
            interest_coverage=5.0,
        )
        assert _is_danger_zone(funda, config) is True

    def test_danger_zone_disabled(self, config):
        """danger_zone_enabled=False → never filters."""
        from ifds.phases.phase4_stocks import _is_danger_zone
        config.tuning["danger_zone_enabled"] = False
        funda = FundamentalScoring(
            debt_equity=10.0,
            net_margin=-0.30,
            interest_coverage=0.1,
        )
        assert _is_danger_zone(funda, config) is False

    def test_danger_zone_boundary_values(self, config):
        """Exact boundary: D/E=5.0, margin=-0.10 → NOT triggered (need >5.0, <-0.10)."""
        from ifds.phases.phase4_stocks import _is_danger_zone
        funda = FundamentalScoring(
            debt_equity=5.0,   # NOT > 5.0
            net_margin=-0.10,  # NOT < -0.10
            interest_coverage=1.0,  # NOT < 1.0
        )
        assert _is_danger_zone(funda, config) is False

    def test_phase4_result_has_danger_zone_count(self):
        """Phase4Result includes danger_zone_count field."""
        result = Phase4Result(danger_zone_count=3)
        assert result.danger_zone_count == 3


# ============================================================================
# D3: Cache TTL Fix (to_date cap)
# ============================================================================


class TestCacheTTLFix:
    """Test that to_date is capped at today in validator."""

    def test_to_date_capped_at_today(self):
        """to_date should never exceed today for cache correctness."""
        from ifds.sim.validator import _fetch_bars_for_trades
        from ifds.sim.models import Trade
        from ifds.sim.broker_sim import compute_qty_split
        import asyncio

        # Create a trade from yesterday — to_date should be capped at today
        yesterday = date.today() - timedelta(days=1)
        qty_tp1, qty_tp2 = compute_qty_split(100)
        trade = Trade(
            run_id="run_20260217_120000_abc",
            run_date=yesterday,
            ticker="AAPL",
            score=85.0,
            gex_regime="positive",
            multiplier=1.0,
            entry_price=150.0,
            quantity=100,
            direction="BUY",
            stop_loss=145.0,
            tp1=158.0,
            tp2=165.0,
            qty_tp1=qty_tp1,
            qty_tp2=qty_tp2,
        )

        captured_calls = []

        async def mock_get_aggregates(ticker, from_d, to_d):
            captured_calls.append((ticker, from_d, to_d))
            return []

        async def mock_close():
            pass

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockClient:
            instance = MagicMock()
            instance.get_aggregates = mock_get_aggregates
            instance.close = mock_close
            MockClient.return_value = instance

            asyncio.run(_fetch_bars_for_trades(
                [trade], "fake_key", max_hold_days=10, fill_window_days=1,
            ))

        # Verify to_date was capped at today
        assert len(captured_calls) == 1
        _, _, to_date_str = captured_calls[0]
        to_date = date.fromisoformat(to_date_str)
        assert to_date <= date.today()

    def test_to_date_old_trade_not_capped(self):
        """For old trades where calculated to_date < today, no capping needed."""
        from ifds.sim.validator import _fetch_bars_for_trades
        from ifds.sim.models import Trade
        from ifds.sim.broker_sim import compute_qty_split
        import asyncio

        # Create a trade from 30 days ago — calculated to_date should be in the past
        old_date = date.today() - timedelta(days=30)
        qty_tp1, qty_tp2 = compute_qty_split(100)
        trade = Trade(
            run_id="run_20260118_120000_abc",
            run_date=old_date,
            ticker="AAPL",
            score=85.0,
            gex_regime="positive",
            multiplier=1.0,
            entry_price=150.0,
            quantity=100,
            direction="BUY",
            stop_loss=145.0,
            tp1=158.0,
            tp2=165.0,
            qty_tp1=qty_tp1,
            qty_tp2=qty_tp2,
        )

        captured_calls = []

        async def mock_get_aggregates(ticker, from_d, to_d):
            captured_calls.append((ticker, from_d, to_d))
            return []

        async def mock_close():
            pass

        with patch("ifds.data.async_clients.AsyncPolygonClient") as MockClient:
            instance = MagicMock()
            instance.get_aggregates = mock_get_aggregates
            instance.close = mock_close
            MockClient.return_value = instance

            asyncio.run(_fetch_bars_for_trades(
                [trade], "fake_key", max_hold_days=10, fill_window_days=1,
            ))

        assert len(captured_calls) == 1
        _, _, to_date_str = captured_calls[0]
        to_date = date.fromisoformat(to_date_str)
        # For 30-day-old trade, to_date should be well in the past
        assert to_date < date.today()
