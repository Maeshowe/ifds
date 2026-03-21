"""IFDS Trading Calendar — special market days."""

from __future__ import annotations

from datetime import date


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
