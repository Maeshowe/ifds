"""The SPY return: a wrong number is worse than a missing one, because it is a trigger input.

`_fetch_spy_return` took `bars_sorted[-1]` blind — no date check — while the VIX function
twenty lines above requires an exact `d == target` match and returns None otherwise. On a
15-minute-delayed market-data plan that asymmetry turns the SPY field from absent into
WRONG, silently.

It matters because `spy_return_pct` is not decoration. `scripts/analysis/
stop_trigger_monitor.py:131` reads it and :214 computes `mtm_pct - spy_return_pct` — the
excess-over-SPY series behind the PRE-REGISTERED halt trigger. A quietly wrong SPY return
moves a stopping decision.

Two guards, because one is not enough:

* the DATE match alone passes a PARTIAL bar. Measured 2026-10-23 at 09:42 ET: the
  same-day bar already existed and returned -0.484, which is not the day's return;
* so a tolerance-based completeness floor as well — volume against the trailing median.
  Verdict-stable on [0.20, 0.40) over 474 sessions, the chosen 0.25 from the interior,
  calibrated from the trailing volume distribution rather than from the guarded field.

And the consumer has to move in the same change: `float(None)` raises, while a MISSING
key reads as `0.0` — "SPY was flat" — which is the structural-zero class this repo has
been burned by twice.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "paper_trading"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import daily_metrics as dm  # noqa: E402

TARGET = "2026-10-23"
NORMAL_VOLUME = 80_000_000


def _bar(day: date, close: float, volume: float = NORMAL_VOLUME) -> dict:
    return {
        "t": int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1000),
        "c": close,
        "v": volume,
    }


def _series(target: str = TARGET, *, today_close=606.0, today_volume=NORMAL_VOLUME, with_today=True):
    """Twenty-five sessions ending at `target`, so the trailing median is well defined."""
    end = date.fromisoformat(target)
    bars = []
    day = end - timedelta(days=40)
    close = 580.0
    while day < end:
        if day.weekday() < 5:
            bars.append(_bar(day, close))
            close += 0.5
        day += timedelta(days=1)
    bars[-1] = _bar(bars[-1]["t"] and (end - timedelta(days=1)), 600.0)
    if with_today:
        bars.append(_bar(end, today_close, today_volume))
    return bars


class TestTheDateGuard:
    def test_a_real_same_date_bar_is_used(self) -> None:
        value, reason = dm.spy_return_from_bars(_series(), TARGET)
        assert reason is None
        assert value == pytest.approx((606.0 - 600.0) / 600.0 * 100, rel=1e-6)

    def test_a_missing_today_bar_returns_none_with_a_reason(self) -> None:
        """What a delayed feed does right after the close."""
        value, reason = dm.spy_return_from_bars(_series(with_today=False), TARGET)
        assert value is None
        assert reason == "no_bar_for_target_date"

    def test_it_never_silently_serves_yesterday(self) -> None:
        """The actual defect: bars_sorted[-1] with no date check."""
        bars = _series(with_today=False)
        stale = bars[-1]["c"]
        value, _ = dm.spy_return_from_bars(bars, TARGET)
        assert value is None, f"returned a value derived from the {stale} stale bar"

    def test_no_previous_bar_is_also_a_reason_not_a_crash(self) -> None:
        value, reason = dm.spy_return_from_bars([_bar(date.fromisoformat(TARGET), 606.0)], TARGET)
        assert value is None and reason == "no_previous_bar"


class TestTheCompletenessFloor:
    def test_a_partial_bar_is_rejected_even_though_its_date_matches(self) -> None:
        """Measured: a same-date bar can exist mid-session and carry a wrong close."""
        thin = _series(today_close=603.0, today_volume=NORMAL_VOLUME * 0.05)
        value, reason = dm.spy_return_from_bars(thin, TARGET)
        assert value is None
        assert reason == "partial_bar"

    def test_a_quiet_but_complete_session_still_passes(self) -> None:
        quiet = _series(today_volume=int(NORMAL_VOLUME * 0.6))
        value, reason = dm.spy_return_from_bars(quiet, TARGET)
        assert reason is None and value is not None

    @pytest.mark.parametrize("factor", [0.20, 0.25, 0.30, 0.35])
    def test_the_floor_is_verdict_stable_across_its_range(self, factor, monkeypatch) -> None:
        """The chosen value sits inside a range where no verdict moves."""
        monkeypatch.setattr(dm, "SPY_VOLUME_FLOOR_FRACTION", factor)
        complete = _series(today_volume=int(NORMAL_VOLUME * 0.6))
        partial = _series(today_volume=int(NORMAL_VOLUME * 0.05))
        assert dm.spy_return_from_bars(complete, TARGET)[1] is None, factor
        assert dm.spy_return_from_bars(partial, TARGET)[1] == "partial_bar", factor

    def test_the_floor_is_a_fraction_of_the_median_not_an_absolute_count(self) -> None:
        """Calibrated from the trailing distribution, not from the guarded value."""
        assert 0.20 <= dm.SPY_VOLUME_FLOOR_FRACTION < 0.40

    def test_a_bar_without_volume_is_not_rejected_by_the_floor(self) -> None:
        """Index bars carry v=None; the floor must not be their gate."""
        bars = _series()
        bars[-1] = {**bars[-1], "v": None}
        value, reason = dm.spy_return_from_bars(bars, TARGET)
        assert reason is None and value is not None


class TestTheConsumerMovesInTheSameChange:
    """A null spy_return must SKIP the day, never read as "SPY was flat"."""

    def _write(self, directory: Path, day: str, spy, excess) -> None:
        payload = {
            "market": {"spy_return_pct": spy},
            "excess_return": {
                "portfolio_return_pct": 0.5,
                "spy_return_pct": spy,
                "excess_pct": excess,
            },
        }
        (directory / f"{day}.json").write_text(json.dumps(payload))

    def test_a_null_spy_day_is_skipped_not_scored_as_zero(self, tmp_path) -> None:
        import stop_trigger_monitor as stm

        self._write(tmp_path, "2026-09-01", 0.4, 0.1)
        self._write(tmp_path, "2026-09-02", None, None)
        self._write(tmp_path, "2026-09-03", -0.2, 0.7)
        records = stm.load_day_records(tmp_path, equity={}, era_start="2026-01-01")
        assert [r.date for r in records] == ["2026-09-01", "2026-09-03"], (
            "the null day must be skipped: float(None) raises, and a 0.0 default would "
            "assert that SPY was flat on a day nobody measured it"
        )

    def test_it_does_not_crash_on_a_null(self, tmp_path) -> None:
        import stop_trigger_monitor as stm

        self._write(tmp_path, "2026-09-02", None, None)
        assert stm.load_day_records(tmp_path, equity={}, era_start="2026-01-01") == ()

    def test_a_healthy_day_is_unchanged(self, tmp_path) -> None:
        import stop_trigger_monitor as stm

        self._write(tmp_path, "2026-09-01", 0.4, 0.1)
        records = stm.load_day_records(tmp_path, equity={}, era_start="2026-01-01")
        assert len(records) == 1
        assert records[0].spy_return_pct == pytest.approx(0.4)
        assert records[0].excess_realized_pct == pytest.approx(0.1)
