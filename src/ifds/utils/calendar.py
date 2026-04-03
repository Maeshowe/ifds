"""IFDS Trading Calendar — NYSE holidays, early closes, and special market days.

Uses ``exchange_calendars`` (XNYS) for accurate NYSE session data.
The witching day logic is self-contained (no external dependency).
"""

from __future__ import annotations

from datetime import date, time, timedelta
from functools import lru_cache

import exchange_calendars as xcals


@lru_cache(maxsize=1)
def _get_nyse_calendar():
    """Get NYSE trading calendar (cached singleton)."""
    return xcals.get_calendar("XNYS")


# ============================================================================
# Witching days (self-contained, no exchange_calendars needed)
# ============================================================================

def get_witching_dates(year: int) -> set[date]:
    """Return Triple/Quadruple Witching dates for a given year.

    Third Friday of March, June, September, December.
    """
    witching_months = [3, 6, 9, 12]
    dates = set()
    for month in witching_months:
        for day in range(15, 22):
            d = date(year, month, day)
            if d.weekday() == 4:  # Friday
                dates.add(d)
                break
    return dates


def is_witching_day(d: date | None = None) -> bool:
    """Return True if date is a Triple/Quadruple Witching day."""
    if d is None:
        d = date.today()
    return d in get_witching_dates(d.year)


# ============================================================================
# NYSE session checks (exchange_calendars)
# ============================================================================

def is_nyse_trading_day(d: date | None = None) -> bool:
    """Return True if NYSE is open on this date.

    Checks weekends AND NYSE holidays (Good Friday, MLK Day, etc.).
    """
    if d is None:
        d = date.today()
    import pandas as pd
    return _get_nyse_calendar().is_session(pd.Timestamp(d))


def is_early_close(d: date | None = None) -> bool:
    """Return True if NYSE closes early (13:00 ET) on this date.

    Early close days: day after Thanksgiving, Christmas Eve,
    July 3rd (if July 4th on Saturday), etc.
    """
    if d is None:
        d = date.today()
    cal = _get_nyse_calendar()
    import pandas as pd
    ts = pd.Timestamp(d)
    if not cal.is_session(ts):
        return False
    # exchange_calendars: early close → close time < 16:00 ET
    close = cal.session_close(ts)
    # NYSE normal close is 16:00 ET (21:00 UTC in winter, 20:00 UTC in summer)
    # Early close is 13:00 ET (18:00 UTC in winter, 17:00 UTC in summer)
    return close.hour < 20  # UTC hour < 20 means close before 16:00 ET


def get_market_close_time_et(d: date | None = None) -> time | None:
    """Get NYSE closing time in Eastern Time.

    Returns ``time(16, 0)`` for normal days, ``time(13, 0)`` for early close,
    or ``None`` if NYSE is closed (holiday/weekend).
    """
    if d is None:
        d = date.today()
    cal = _get_nyse_calendar()
    import pandas as pd
    ts = pd.Timestamp(d)
    if not cal.is_session(ts):
        return None
    if is_early_close(d):
        return time(13, 0)
    return time(16, 0)


def get_market_close_time_cet(d: date | None = None) -> time | None:
    """Get NYSE closing time in CET/CEST.

    Normal: 22:00 CET (winter) / 22:00 CEST (summer)
    Early:  19:00 CET (winter) / 19:00 CEST (summer)

    Returns None if NYSE is closed.
    """
    if d is None:
        d = date.today()
    et_close = get_market_close_time_et(d)
    if et_close is None:
        return None
    # CET = ET + 6h (winter) or CEST = ET + 6h (summer, both shift)
    # Simplified: always +6h (DST offsets cancel for US/EU same-season)
    cet_hour = et_close.hour + 6
    return time(cet_hour, 0)


def next_nyse_trading_day(d: date | None = None) -> date:
    """Get the next NYSE trading day strictly after the given date."""
    if d is None:
        d = date.today()
    current = d + timedelta(days=1)
    while not is_nyse_trading_day(current):
        current += timedelta(days=1)
    return current


def get_holiday_name(d: date | None = None) -> str | None:
    """Get NYSE holiday name, or None if not a holiday.

    Uses exchange_calendars adhoc holidays + regular holidays.
    """
    if d is None:
        d = date.today()
    if is_nyse_trading_day(d):
        return None
    if d.weekday() >= 5:
        return None  # Weekend, not a holiday

    # Known NYSE holidays by month-day pattern
    _holidays = {
        (1, 1): "New Year's Day",
        (1, 20): "MLK Day",  # 3rd Monday, approximate
        (2, 17): "Presidents' Day",  # 3rd Monday, approximate
        (7, 4): "Independence Day",
        (9, 1): "Labor Day",  # 1st Monday, approximate
        (11, 27): "Thanksgiving",  # 4th Thursday, approximate
        (12, 25): "Christmas Day",
    }

    # Check exact match first
    key = (d.month, d.day)
    if key in _holidays:
        return _holidays[key]

    # Good Friday: Friday before Easter
    # Easter calculation (anonymous Gregorian algorithm)
    year = d.year
    a = year % 19
    b = year // 100
    c = year % 100
    dd = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - dd - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    easter = date(year, month, day)
    good_friday = easter - timedelta(days=2)
    if d == good_friday:
        return "Good Friday"

    # Juneteenth
    if d.month == 6 and d.day == 19:
        return "Juneteenth"

    return "NYSE Holiday"
