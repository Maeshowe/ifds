"""Tests for NYSE Trading Calendar extensions (BC20A follow-up).

Covers:
- is_nyse_trading_day: holidays, weekends, normal days
- is_early_close: day after Thanksgiving, Christmas Eve
- get_market_close_time_et: normal 16:00, early 13:00, holiday None
- next_nyse_trading_day: across weekends and holidays
- get_holiday_name: known holidays
- is_witching_day: still works (existing)
"""

from datetime import date, time

import pytest

from ifds.utils.calendar import (
    get_holiday_name,
    get_market_close_time_et,
    is_early_close,
    is_nyse_trading_day,
    is_witching_day,
    next_nyse_trading_day,
    trading_days_between,
)


class TestIsNyseTradingDay:

    def test_good_friday_closed(self):
        assert not is_nyse_trading_day(date(2026, 4, 3))

    def test_christmas_closed(self):
        assert not is_nyse_trading_day(date(2026, 12, 25))

    def test_normal_thursday(self):
        assert is_nyse_trading_day(date(2026, 4, 2))

    def test_saturday_closed(self):
        assert not is_nyse_trading_day(date(2026, 4, 4))

    def test_sunday_closed(self):
        assert not is_nyse_trading_day(date(2026, 4, 5))

    def test_normal_monday(self):
        assert is_nyse_trading_day(date(2026, 4, 6))


class TestTradingDaysBetween:
    """§9.2 trading-day holding period — weekends/holidays must not inflate."""

    def test_consecutive_trading_days(self):
        # Mon 5/18 → Tue 5/19 = 1 trading day held
        assert trading_days_between(date(2026, 5, 18), date(2026, 5, 19)) == 1

    def test_full_week(self):
        # Mon 5/18 → Fri 5/22 = 4 (5/19,5/20,5/21,5/22)
        assert trading_days_between(date(2026, 5, 18), date(2026, 5, 22)) == 4

    def test_excludes_memorial_day_and_weekend(self):
        # Mon 5/18 → Tue 5/26: 5/19,5/20,5/21,5/22,5/26 (5/25 Memorial Day) = 5
        assert trading_days_between(date(2026, 5, 18), date(2026, 5, 26)) == 5

    def test_thursday_entry_across_holiday(self):
        # WMB case — Thu 5/21 → Wed 5/27: 5/22,5/26,5/27 = 3 (NOT calendar 6)
        assert trading_days_between(date(2026, 5, 21), date(2026, 5, 27)) == 3

    def test_friday_entry_to_wednesday(self):
        # Fri 5/15 → Wed 5/20: 5/18,5/19,5/20 = 3 (NOT calendar 5)
        assert trading_days_between(date(2026, 5, 15), date(2026, 5, 20)) == 3

    def test_same_day_is_zero(self):
        assert trading_days_between(date(2026, 5, 18), date(2026, 5, 18)) == 0

    def test_end_before_start_is_zero(self):
        assert trading_days_between(date(2026, 5, 20), date(2026, 5, 18)) == 0

    def test_entry_on_friday_weekend_only(self):
        # Fri 5/15 → Mon 5/18 = 1 (weekend in between excluded)
        assert trading_days_between(date(2026, 5, 15), date(2026, 5, 18)) == 1


class TestIsEarlyClose:

    def test_day_after_thanksgiving(self):
        # 2026 Thanksgiving = Nov 26, day after = Nov 27
        assert is_early_close(date(2026, 11, 27))

    def test_christmas_eve(self):
        assert is_early_close(date(2026, 12, 24))

    def test_normal_day_not_early(self):
        assert not is_early_close(date(2026, 4, 2))

    def test_holiday_not_early(self):
        # Holiday = market closed, not early close
        assert not is_early_close(date(2026, 4, 3))


class TestGetMarketCloseTimeEt:

    def test_normal_day(self):
        assert get_market_close_time_et(date(2026, 4, 2)) == time(16, 0)

    def test_early_close_day(self):
        assert get_market_close_time_et(date(2026, 11, 27)) == time(13, 0)

    def test_holiday_none(self):
        assert get_market_close_time_et(date(2026, 4, 3)) is None


class TestNextNyseTradingDay:

    def test_friday_holiday_to_monday(self):
        # Good Friday → next trading = Monday Apr 6
        assert next_nyse_trading_day(date(2026, 4, 3)) == date(2026, 4, 6)

    def test_normal_weekday(self):
        assert next_nyse_trading_day(date(2026, 4, 1)) == date(2026, 4, 2)

    def test_saturday_to_monday(self):
        assert next_nyse_trading_day(date(2026, 4, 4)) == date(2026, 4, 6)


class TestGetHolidayName:

    def test_good_friday(self):
        assert get_holiday_name(date(2026, 4, 3)) == "Good Friday"

    def test_normal_day_none(self):
        assert get_holiday_name(date(2026, 4, 2)) is None

    def test_weekend_none(self):
        # Weekend is not a "holiday"
        assert get_holiday_name(date(2026, 4, 4)) is None

    def test_christmas(self):
        assert get_holiday_name(date(2026, 12, 25)) == "Christmas Day"


class TestWitchingStillWorks:

    def test_witching_march_2026(self):
        assert is_witching_day(date(2026, 3, 20))

    def test_non_witching(self):
        assert not is_witching_day(date(2026, 4, 2))
