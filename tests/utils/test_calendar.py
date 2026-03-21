"""Tests for IFDS special market day calendar (witching days)."""

from datetime import date

from ifds.utils.calendar import get_witching_dates, is_witching_day


class TestGetWitchingDates:
    """Test witching date calculation."""

    def test_2026_dates(self):
        dates = get_witching_dates(2026)
        assert dates == {
            date(2026, 3, 20),
            date(2026, 6, 19),
            date(2026, 9, 18),
            date(2026, 12, 18),
        }

    def test_2027_dates(self):
        dates = get_witching_dates(2027)
        assert dates == {
            date(2027, 3, 19),
            date(2027, 6, 18),
            date(2027, 9, 17),
            date(2027, 12, 17),
        }

    def test_always_four_dates(self):
        for year in range(2024, 2031):
            dates = get_witching_dates(year)
            assert len(dates) == 4, f"Expected 4 witching dates for {year}, got {len(dates)}"

    def test_all_fridays(self):
        for year in range(2024, 2031):
            for d in get_witching_dates(year):
                assert d.weekday() == 4, f"{d} is not a Friday"

    def test_all_third_week(self):
        """Witching dates are always between 15th and 21st."""
        for year in range(2024, 2031):
            for d in get_witching_dates(year):
                assert 15 <= d.day <= 21, f"{d} day not in 15-21 range"


class TestIsWitchingDay:
    """Test is_witching_day() convenience function."""

    def test_witching_day_true(self):
        assert is_witching_day(date(2026, 3, 20)) is True

    def test_witching_day_false(self):
        assert is_witching_day(date(2026, 3, 21)) is False

    def test_non_witching_friday(self):
        assert is_witching_day(date(2026, 3, 13)) is False

    def test_all_2026_witching_days(self):
        for d in [date(2026, 3, 20), date(2026, 6, 19),
                  date(2026, 9, 18), date(2026, 12, 18)]:
            assert is_witching_day(d) is True, f"{d} should be a witching day"

    def test_default_date_none(self):
        """is_witching_day(None) should not raise."""
        result = is_witching_day(None)
        assert isinstance(result, bool)
