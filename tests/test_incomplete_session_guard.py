"""No scoring input may contain the bar of a session that is still open.

The DST gap week made this urgent rather than theoretical. The Phase 4-6 cron is
14:30 Budapest, which the crontab comment describes as 08:30 ET — pre-market, so the
newest daily bar is yesterday's, complete. But Europe leaves DST on 2026-10-25 and the
US only on 2026-11-01, so for 2026-10-26…10-30 that same slot is **09:30 ET, exactly on
the opening bell**. Measured, not assumed.

Every bar consumer in the scoring path took the newest bar blind:
``closes[-1]`` for the price and the 3-month return, ``bars[-1]["v"]`` for volume,
``bars[-1]["c"]`` for the PCR/OTM reference. A partial first-minutes bar in any of them
is a wrong number, not a missing one — the same shape as the SPY-return defect, and the
same shape the repo has been burned by twice.

Why this guard and not a cron edit: the cron edit fixes the week, this fixes the gap, and
it needs no manual revert on 11-02 (a revert that, if forgotten, leaves the wrong slot in
place silently). It is also a NO-OP on every ordinary day, which is what keeps it from
retroactively redefining the 2026-10-26 scoring era.

MMS makes it irreversible, which is why Phase 5 is covered too: a degraded observation is
appended unconditionally to the rolling 100-entry store that feeds tomorrow's z-scores.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ifds.utils.bars import drop_open_session  # noqa: E402

RUN_DAY = date(2026, 10, 26)


def _bar(day: date, close: float) -> dict:
    return {
        "t": int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1000),
        "c": close,
        "o": close,
        "h": close,
        "l": close,
        "v": 1_000_000,
    }


def _series(last: date, n: int = 5) -> list[dict]:
    return [_bar(last - timedelta(days=n - 1 - i), 100.0 + i) for i in range(n)]


class TestTheOpenSessionIsDropped:
    def test_a_bar_dated_today_is_removed(self) -> None:
        bars = _series(RUN_DAY)
        kept = drop_open_session(bars, RUN_DAY)
        assert len(kept) == len(bars) - 1
        assert kept[-1]["c"] == 103.0, "the newest COMPLETE bar must become the last"

    def test_the_price_consumers_then_see_yesterday(self) -> None:
        """What the defect actually changed: closes[-1]."""
        bars = _series(RUN_DAY)
        assert [b["c"] for b in bars][-1] == 104.0          # the open session
        assert [b["c"] for b in drop_open_session(bars, RUN_DAY)][-1] == 103.0

    def test_a_future_dated_bar_is_dropped_too(self) -> None:
        """A clock-skewed vendor row must not become the price either."""
        bars = _series(RUN_DAY) + [_bar(RUN_DAY + timedelta(days=1), 999.0)]
        assert all(b["c"] != 999.0 for b in drop_open_session(bars, RUN_DAY))


class TestItIsANoOpOnAnOrdinaryDay:
    """The property that keeps the 2026-10-26 scoring era honest: on a pre-market run
    there is no open-session bar, so nothing moves and no past day is redefined."""

    def test_nothing_is_removed_when_the_newest_bar_is_yesterday(self) -> None:
        bars = _series(RUN_DAY - timedelta(days=1))
        assert drop_open_session(bars, RUN_DAY) == bars

    def test_the_list_is_returned_unchanged_not_rebuilt(self) -> None:
        bars = _series(RUN_DAY - timedelta(days=1))
        assert drop_open_session(bars, RUN_DAY) == bars

    @pytest.mark.parametrize("payload", [None, []])
    def test_empty_input_is_not_an_error(self, payload) -> None:
        assert drop_open_session(payload, RUN_DAY) == []

    def test_a_bar_without_a_timestamp_is_kept_not_guessed(self) -> None:
        """Dropping an unparseable row would silently shorten the history."""
        bars = [{"c": 100.0}, _bar(RUN_DAY - timedelta(days=1), 101.0)]
        assert len(drop_open_session(bars, RUN_DAY)) == 2


class TestTheConversionIsUtcAnchored:
    """Polygon's `t` is epoch ms at ET midnight; a local conversion shifts the whole
    series by a day on a far-enough host (.claude/rules/ifds-rules.md, 2026-10-19)."""

    def test_the_boundary_holds_in_an_extreme_zone(self, monkeypatch) -> None:
        import importlib
        import os
        import time as _time

        monkeypatch.setenv("TZ", "Pacific/Kiritimati")
        _time.tzset()
        try:
            import ifds.utils.bars as bars_mod

            importlib.reload(bars_mod)
            series = _series(RUN_DAY)
            assert len(bars_mod.drop_open_session(series, RUN_DAY)) == len(series) - 1
        finally:
            monkeypatch.delenv("TZ", raising=False)
            _time.tzset()
            os.environ.pop("TZ", None)


class TestEveryScoringBarReadIsGuarded:
    """Close the gap, not the instance: four consumers, two phases, one helper."""

    @pytest.mark.parametrize(
        "module,label",
        [("phases/phase4_stocks.py", "Phase 4"), ("phases/phase5_gex.py", "Phase 5 / MMS")],
    )
    def test_the_phase_guards_every_aggregates_result(self, module: str, label: str) -> None:
        source = (ROOT / "src" / "ifds" / module).read_text()
        calls = source.count("get_aggregates(")
        guards = source.count("drop_open_session(")
        assert guards >= calls, (
            f"{label}: {calls} get_aggregates call(s) but only {guards} guard(s) — an "
            "unguarded one can hand the open session's partial bar to the scorer"
        )

    def test_phase5_is_covered_because_its_damage_is_irreversible(self) -> None:
        """A degraded MMS observation is appended unconditionally to a rolling
        100-entry store that feeds tomorrow's z-scores; re-subscribing cannot undo it."""
        source = (ROOT / "src" / "ifds" / "phases" / "phase5_gex.py").read_text()
        assert "drop_open_session" in source
