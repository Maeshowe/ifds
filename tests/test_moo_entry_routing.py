"""The swing entry goes into the opening auction — and fails closed when it can't.

Measured on the swing era: a market order sent after the bell gives up +60.4 bp,
an auction order +1.35 bp (``docs/review/2026-10-19-execution-wall-by-horizon.md``).
The entry decision comes from the previous close, so the auction executes the same
decision earlier and better.

The hazard this guards is real and documented, not theoretical: the US and EU
daylight-saving switches are a week apart (2026: EU Oct 25, US Nov 1), and inside
that week a Budapest cron slot lands an hour LATER in ET. ``scripts/crontab.md``
says the mitigation is a manual edit; these tests make sure the code does not
depend on that edit happening.

Hermetic: no IBKR connection, no network, no clock dependence — every case passes
an explicit instant.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "paper_trading"))

from ifds.utils.calendar import ET, MOO_CUTOFF_ET, is_before_moo_cutoff  # noqa: E402

BUDAPEST = ZoneInfo("Europe/Budapest")

#: 2026-10-19 is a Monday and both zones are still on summer time (ET = BP - 6h).
NORMAL_DAY = 2026, 10, 19
#: 2026-10-28 is a Wednesday inside the one-week gap: EU already on winter time,
#: the US still on summer time, so ET = BP - 5h and every slot shifts an hour.
DST_GAP_DAY = 2026, 10, 28


def _bp(day: tuple[int, int, int], hour: int, minute: int) -> datetime:
    return datetime(*day, hour, minute, tzinfo=BUDAPEST)


class TestTheCutoffGuard:
    def test_the_cutoff_is_the_exchange_rule_not_a_round_number(self):
        assert (MOO_CUTOFF_ET.hour, MOO_CUTOFF_ET.minute) == (9, 28)

    def test_a_slot_before_the_cutoff_is_open(self):
        assert is_before_moo_cutoff(_bp(NORMAL_DAY, 15, 20)) is True

    def test_todays_slot_is_already_too_late(self):
        """15:31 Budapest = 09:31 ET — one minute after the bell, three past the cutoff.

        This is the production slot as of 2026-10-19 and the entire reason the
        entry cost +48 bp. Moving it is part of this change.
        """
        assert is_before_moo_cutoff(_bp(NORMAL_DAY, 15, 31)) is False

    def test_the_dst_gap_week_closes_the_window_at_the_same_budapest_slot(self):
        """The whole point: an identical cron slot, a different answer."""
        assert is_before_moo_cutoff(_bp(NORMAL_DAY, 15, 20)) is True
        assert is_before_moo_cutoff(_bp(DST_GAP_DAY, 15, 20)) is False
        # ...and an hour earlier is what works that week.
        assert is_before_moo_cutoff(_bp(DST_GAP_DAY, 14, 20)) is True

    @pytest.mark.parametrize("day", [(2026, 10, 24), (2026, 10, 25)])  # Sat, Sun
    def test_a_non_session_fails_closed(self, day):
        assert is_before_moo_cutoff(_bp(day, 15, 20)) is False

    def test_the_guard_reads_eastern_time_not_the_host_zone(self):
        """Same instant, three host zones — one answer."""
        instant = _bp(NORMAL_DAY, 15, 20)
        answers = {
            is_before_moo_cutoff(instant.astimezone(zone))
            for zone in (ET, BUDAPEST, ZoneInfo("UTC"), ZoneInfo("Asia/Tokyo"))
        }
        assert answers == {True}


class TestTheEntryOrder:
    def _order(self, moment):
        from lib.orders import create_swing_entry_order

        return create_swing_entry_order(
            qty=10, account="DUH118657", ticker="AAPL", now=moment
        )

    def test_inside_the_window_it_is_an_opening_auction_order(self):
        from lib.orders import ROUTE_MOO

        order, route = self._order(_bp(NORMAL_DAY, 15, 20))
        assert route == ROUTE_MOO
        # IBKR has no distinct MOO type for stocks: it is MKT with TIF=OPG.
        assert order.orderType == "MKT"
        assert order.tif == "OPG"
        assert order.outsideRth is False, "an opening-auction order is RTH by definition"
        assert order.orderRef == "IFDS_SWING_AAPL"
        assert order.totalQuantity == 10

    def test_outside_the_window_it_is_exactly_the_old_behaviour(self):
        """The fallback must be the status quo, not something new and untested."""
        from lib.orders import ROUTE_MKT_FALLBACK

        order, route = self._order(_bp(NORMAL_DAY, 15, 31))
        assert route == ROUTE_MKT_FALLBACK
        assert order.orderType == "MKT"
        assert order.tif == "DAY", "the 'Error 10349 preset' lesson — never leave TIF unset"
        assert order.outsideRth is True

    def test_the_fallback_is_loud(self):
        """A silent downgrade would cost 59 bp per leg and nobody would know."""

        class _Spy:
            def __init__(self):
                self.warnings = []

            def warning(self, message):
                self.warnings.append(message)

        from lib.orders import create_swing_entry_order

        spy = _Spy()
        create_swing_entry_order(
            qty=10,
            account="DUH118657",
            ticker="AAPL",
            now=_bp(NORMAL_DAY, 15, 31),
            logger=spy,
        )
        assert spy.warnings, "the fallback must warn"
        assert "09:28" in spy.warnings[0] and "DST" in spy.warnings[0]

        spy_ok = _Spy()
        create_swing_entry_order(
            qty=10,
            account="DUH118657",
            ticker="AAPL",
            now=_bp(NORMAL_DAY, 15, 20),
            logger=spy_ok,
        )
        assert not spy_ok.warnings, "the happy path must stay quiet"

    def test_gtc_is_never_used(self):
        """Day 3 lesson: GTC is limit-only; with MKT the paper account cancels it."""
        for moment in (_bp(NORMAL_DAY, 15, 20), _bp(NORMAL_DAY, 15, 31)):
            order, _ = self._order(moment)
            assert order.tif != "GTC"
