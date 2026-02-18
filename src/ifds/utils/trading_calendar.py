"""NYSE trading calendar utilities.

Uses exchange_calendars for accurate NYSE holiday/session data.
Provides trading-day-aware date arithmetic for the pipeline and SimEngine.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

import exchange_calendars as xcals


@lru_cache(maxsize=1)
def _get_nyse_calendar():
    """Get NYSE trading calendar (cached singleton)."""
    return xcals.get_calendar("XNYS")


def is_trading_day(d: date) -> bool:
    """Check if a date is a valid NYSE trading day."""
    cal = _get_nyse_calendar()
    import pandas as pd
    ts = pd.Timestamp(d)
    return cal.is_session(ts)


def next_trading_day(d: date, n: int = 1) -> date:
    """Get the nth next trading day after date.

    Args:
        d: Reference date.
        n: Number of trading days forward (must be >= 1).

    Returns:
        The nth trading day strictly after d.
    """
    if n < 1:
        raise ValueError("n must be >= 1")

    cal = _get_nyse_calendar()
    import pandas as pd
    ts = pd.Timestamp(d)

    current = ts
    found = 0
    while found < n:
        current = current + pd.Timedelta(days=1)
        if cal.is_session(current):
            found += 1

    return current.date()


def prev_trading_day(d: date, n: int = 1) -> date:
    """Get the nth previous trading day before date.

    Args:
        d: Reference date.
        n: Number of trading days backward (must be >= 1).

    Returns:
        The nth trading day strictly before d.
    """
    if n < 1:
        raise ValueError("n must be >= 1")

    cal = _get_nyse_calendar()
    import pandas as pd
    ts = pd.Timestamp(d)

    current = ts
    found = 0
    while found < n:
        current = current - pd.Timedelta(days=1)
        if cal.is_session(current):
            found += 1

    return current.date()


def trading_days_between(start: date, end: date) -> list[date]:
    """Get list of trading days between two dates (inclusive).

    Args:
        start: Start date (inclusive).
        end: End date (inclusive).

    Returns:
        List of NYSE trading days in [start, end].
    """
    cal = _get_nyse_calendar()
    import pandas as pd
    sessions = cal.sessions_in_range(pd.Timestamp(start), pd.Timestamp(end))
    return [s.date() for s in sessions]


def add_trading_days(d: date, n: int) -> date:
    """Add n trading days to a date.

    Args:
        d: Reference date.
        n: Number of trading days to add (positive = forward, negative = backward).
           If d is a trading day, it counts as day 0.

    Returns:
        The resulting date after moving n trading days.
    """
    if n == 0:
        return d
    if n > 0:
        return next_trading_day(d, n)
    return prev_trading_day(d, -n)


def count_trading_days(start: date, end: date) -> int:
    """Count trading days between two dates (exclusive of start, inclusive of end).

    Args:
        start: Start date (exclusive).
        end: End date (inclusive).

    Returns:
        Number of trading days in (start, end].
    """
    if end <= start:
        return 0
    cal = _get_nyse_calendar()
    import pandas as pd
    # Sessions in (start, end] = sessions_in_range(start+1day, end)
    next_day = start + timedelta(days=1)
    sessions = cal.sessions_in_range(pd.Timestamp(next_day), pd.Timestamp(end))
    return len(sessions)
