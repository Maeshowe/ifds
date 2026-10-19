"""IFDS Trading Calendar — NYSE holidays, early closes, and special market days.

Uses ``exchange_calendars`` (XNYS) for accurate NYSE session data.
The witching day logic is self-contained (no external dependency).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

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


def session_close_et(d: date | None = None) -> datetime | None:
    """The session's real close, as an aware ``America/New_York`` datetime.

    Read from the exchange calendar, never derived from an offset: this is the
    anchor every auction deadline below is measured against.
    """
    if d is None:
        d = date.today()
    cal = _get_nyse_calendar()
    import pandas as pd

    ts = pd.Timestamp(d)
    if not cal.is_session(ts):
        return None
    return cal.session_close(ts).tz_convert(ET).to_pydatetime()


def get_market_close_time_cet(d: date | None = None) -> time | None:
    """NYSE closing time expressed in Europe/Budapest local time.

    Converted through the actual zones, NOT by adding a fixed offset. The old
    implementation hard-coded ``ET + 6h`` with the comment "DST offsets cancel
    for US/EU same-season" — which is false for the two weeks a year when the
    switches are a week apart (2026: EU Oct 25, US Nov 1; EU Mar 29, US Mar 8).
    In those weeks the gap is 5h, so the old version reported the close an hour
    LATE — and its one caller uses it to decide whether an MOC order is already
    too late to submit.

    Returns None if NYSE is closed.
    """
    close_et = session_close_et(d)
    if close_et is None:
        return None
    return close_et.astimezone(ZoneInfo("Europe/Budapest")).timetz().replace(tzinfo=None)


#: NYSE stops accepting Market-on-Close orders 10 minutes before the close
#: (Rule 7.35A: 15:50 ET for a 16:00 close, 12:50 ET on a 13:00 early close).
#: Expressed as a lead time, not a clock time, so early closes are handled by
#: construction rather than by a second constant that can drift.
MOC_SUBMISSION_LEAD = timedelta(minutes=10)


def is_before_moc_cutoff(now: datetime | None = None) -> bool:
    """True when an MOC order placed *now* can still reach today's closing auction.

    Anchored on the exchange calendar and ``America/New_York``, never on the host
    clock or a cron slot — the mirror of :func:`is_before_moo_cutoff`, and needed
    for the same reason. Measured over 2026-10-19..12-31, the production 21:40
    Budapest slot lands AFTER the close on **seven** trading sessions: Oct 26-30
    (the week when the EU is already on winter time and the US is not, so the slot
    is 16:40 ET) and Nov 27 / Dec 24 (early closes, where it is 160 minutes late).

    Fails CLOSED outside a session, so a caller that cannot submit simply does
    not submit — leaving the position flagged for the next session, which is a
    worse fill but an honest one. The alternative is an order the exchange will
    not execute plus a state file that says it was sold.
    """
    moment = datetime.now(ET) if now is None else now.astimezone(ET)
    close_et = session_close_et(moment.date())
    if close_et is None:
        return False
    return moment < close_et - MOC_SUBMISSION_LEAD


#: Exchange timezone. Every auction deadline is defined here and nowhere else.
ET = ZoneInfo("America/New_York")

#: NYSE stops accepting Market-on-Open orders (MKT + TIF=OPG) at 09:28 ET.
#: Source: NYSE Rule 7.35 / IBKR order-type reference. Two minutes of margin
#: before the 09:30 auction, and it does NOT move on early-close days — those
#: shorten the session's end, not its start.
MOO_CUTOFF_ET: time = time(9, 28)


def is_before_moo_cutoff(now: datetime | None = None) -> bool:
    """True when an OPG order placed *now* can still reach today's opening auction.

    Anchored on ``America/New_York``, never on the host clock and never on a cron
    slot. The US and EU daylight-saving switches are a week apart (2026: EU on
    Oct 25, US on Nov 1), and inside that week a Budapest cron slot lands an hour
    LATER in ET than the crontab's comment claims. The documented mitigation for
    that window is a manual crontab edit; an OPG order submitted after 09:28 ET
    is rejected or deferred to the next session, so this guard must not depend on
    the edit having happened.

    Returns False outside a trading session, so it fails CLOSED: the caller then
    keeps today's plain market entry rather than placing an order that cannot fill.
    """
    moment = datetime.now(ET) if now is None else now.astimezone(ET)
    if not is_nyse_trading_day(moment.date()):
        return False
    return moment.timetz().replace(tzinfo=None) < MOO_CUTOFF_ET


def next_nyse_trading_day(d: date | None = None) -> date:
    """Get the next NYSE trading day strictly after the given date."""
    if d is None:
        d = date.today()
    current = d + timedelta(days=1)
    while not is_nyse_trading_day(current):
        current += timedelta(days=1)
    return current


def trading_days_between(start: date, end: date) -> int:
    """Count NYSE trading sessions strictly after ``start``, up to and including ``end``.

    Used for the trading-day-based holding period (``days_held``) so weekends and
    holidays do not inflate the count. ``start`` is the entry date; it is excluded
    from the count (the entry day itself is day 0), while ``end`` is included when
    it is a session. Returns 0 when ``end <= start``.

    Example: entry on Fri, evaluated the next Wed after a Mon holiday →
    sessions are {Fri, Tue, Wed}; excluding the Fri entry day → 2.
    """
    if end <= start:
        return 0
    import pandas as pd

    cal = _get_nyse_calendar()
    sessions = cal.sessions_in_range(pd.Timestamp(start), pd.Timestamp(end))
    count = len(sessions)
    if cal.is_session(pd.Timestamp(start)):
        count -= 1  # entry day does not count toward days held
    return count


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
