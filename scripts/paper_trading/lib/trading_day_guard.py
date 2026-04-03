"""Trading day guard for paper trading scripts.

Call ``check_trading_day()`` at the start of every PT script's ``main()``.
Exits cleanly if NYSE is closed today (holiday or weekend).
"""

import os
import sys


def check_trading_day(logger=None) -> None:
    """Exit if today is not a NYSE trading day.

    Skipped if ``IFDS_SKIP_TRADING_DAY_GUARD=1`` env var is set (for testing).
    Falls back gracefully if exchange_calendars is not installed.
    """
    if os.environ.get("IFDS_SKIP_TRADING_DAY_GUARD"):
        return

    try:
        from ifds.utils.calendar import is_nyse_trading_day, get_holiday_name
    except ImportError:
        return  # Package not available — skip guard

    from datetime import date
    today = date.today()

    if not is_nyse_trading_day(today):
        holiday = get_holiday_name(today)
        msg = f"NYSE closed today{f' ({holiday})' if holiday else ''}. Exiting."
        if logger:
            logger.info(msg)
        else:
            print(msg)
        sys.exit(0)
