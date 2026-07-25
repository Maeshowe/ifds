"""Tests for the pre-registered STOP-trigger monitor (gate protocol §4).

The monitor is read-only and advisory: it FLAGS breaches of the pre-registered
halt criteria (2026-05-14 decision outcome §3.14) and never acts on them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "analysis"))

import stop_trigger_monitor as stm  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _rec(date: str, excess: float, spy: float = 0.0, equity: float | None = None):
    return stm.DayRecord(
        date=date,
        excess_realized_pct=excess,
        spy_return_pct=spy,
        portfolio_return_pct=excess + spy,
        equity=equity,
    )


def _series(values: list[float]) -> tuple[stm.DayRecord, ...]:
    return tuple(_rec(f"2026-06-{i + 1:02d}", v) for i, v in enumerate(values))


# ---------------------------------------------------------------------------
# window arithmetic — both pre-reg readings
# ---------------------------------------------------------------------------


class TestWindowReadings:
    def test_mean_reading_matches_hand_calculation(self):
        records = _series([-2.0, -1.0, 0.0] + [0.0] * 7)  # 10 days, mean = -0.3
        result = stm.evaluate_window(records, window=10, reading=stm.READING_MEAN)
        assert result.n_days == 10
        assert result.value == pytest.approx(-0.3)
        assert result.sufficient is True

    def test_sum_reading_matches_hand_calculation(self):
        records = _series([-2.0, -1.0, 0.0] + [0.0] * 7)  # sum = -3.0
        result = stm.evaluate_window(records, window=10, reading=stm.READING_SUM)
        assert result.value == pytest.approx(-3.0)

    def test_window_uses_only_the_most_recent_n_days(self):
        records = _series([-9.0] * 5 + [0.0] * 10)  # the -9s fall out of a 10-day window
        result = stm.evaluate_window(records, window=10, reading=stm.READING_MEAN)
        assert result.value == pytest.approx(0.0)


class TestBreachDetection:
    def test_mean_below_threshold_breaches(self):
        records = _series([-1.5] * 10)
        result = stm.evaluate_window(records, window=10, reading=stm.READING_MEAN)
        assert result.breached is True

    def test_mean_above_threshold_does_not_breach(self):
        records = _series([-0.5] * 10)
        result = stm.evaluate_window(records, window=10, reading=stm.READING_MEAN)
        assert result.breached is False

    def test_threshold_is_exclusive_not_inclusive(self):
        """Pre-reg says '< -1.0%' — exactly -1.0 must NOT breach."""
        records = _series([-1.0] * 10)
        result = stm.evaluate_window(records, window=10, reading=stm.READING_MEAN)
        assert result.breached is False


class TestInsufficientData:
    def test_short_series_is_flagged_insufficient_and_never_breaches(self):
        records = _series([-5.0] * 4)  # deeply negative but only 4 days
        result = stm.evaluate_window(records, window=10, reading=stm.READING_MEAN)
        assert result.sufficient is False
        assert result.breached is False, "an underpowered window must not raise a halt flag"
        assert result.n_days == 4


class TestOutageGapHandling:
    def test_missing_days_are_absent_not_interpolated(self, tmp_path):
        """Outage days have no daily_metrics file — they must simply not appear."""
        metrics = tmp_path / "daily_metrics"
        metrics.mkdir()
        for day, excess in (("2026-05-18", 0.5), ("2026-05-20", -0.5)):  # 05-19 missing
            payload = {
                "date": day,
                "market": {"spy_return_pct": 0.1},
                "excess_return": {"excess_pct": excess, "portfolio_return_pct": 0.0},
            }
            (metrics / f"{day}.json").write_text(json.dumps(payload))

        records = stm.load_day_records(metrics_dir=metrics, equity={}, era_start="2026-05-18")
        assert [r.date for r in records] == ["2026-05-18", "2026-05-20"]


class TestCumulativeWindow:
    def test_30d_cumulative_is_pct_of_capital(self):
        history = [{"date": f"2026-06-{i + 1:02d}", "pnl": -100.0} for i in range(30)]
        result = stm.evaluate_cumulative(history, window=30, capital=100_000.0)
        assert result.value == pytest.approx(-3.0)  # -3000 / 100k
        assert result.breached is False, "-3.0 is not strictly below the -3.0 threshold"

    def test_cumulative_breach_below_threshold(self):
        history = [{"date": f"2026-06-{i + 1:02d}", "pnl": -150.0} for i in range(30)]
        result = stm.evaluate_cumulative(history, window=30, capital=100_000.0)
        assert result.value == pytest.approx(-4.5)
        assert result.breached is True


# ---------------------------------------------------------------------------
# mark-to-market variant — the measurement-validity diagnostic
# ---------------------------------------------------------------------------


class TestMarkToMarketVariant:
    def test_mtm_excess_uses_equity_change_not_realized(self):
        records = (
            _rec("2026-07-01", excess=0.0, spy=1.0, equity=100_000.0),
            _rec("2026-07-02", excess=-1.0, spy=1.0, equity=101_000.0),
        )
        mtm = stm.mtm_excess_series(records)
        # equity +1.0%, SPY +1.0% -> excess 0.0 (the realized-only field said -1.0)
        assert mtm[-1][1] == pytest.approx(0.0)

    def test_mtm_skips_days_without_equity(self):
        records = (
            _rec("2026-07-01", excess=0.0, spy=0.0, equity=None),
            _rec("2026-07-02", excess=0.0, spy=0.0, equity=100_000.0),
        )
        assert stm.mtm_excess_series(records) == ()


# ---------------------------------------------------------------------------
# review integration — the mandatory §5 ops-checklist line
# ---------------------------------------------------------------------------


class TestReviewLine:
    def test_clean_state_renders_a_tick(self):
        results = (
            stm.TriggerResult("excess_10d", 10, stm.READING_MEAN, -0.2, -1.0, False, 10, True),
        )
        line = stm.format_review_line(results)
        assert line.startswith("STOP-triggerek: ✓")

    def test_any_breach_renders_a_warning_with_the_value(self):
        results = (
            stm.TriggerResult("excess_10d", 10, stm.READING_MEAN, -0.2, -1.0, False, 10, True),
            stm.TriggerResult("cum_30d", 30, stm.READING_SUM, -4.5, -3.0, True, 30, True),
        )
        line = stm.format_review_line(results)
        assert line.startswith("STOP-triggerek: ⚠️")
        assert "cum_30d" in line and "-4.5" in line

    def test_insufficient_windows_are_surfaced_not_silently_passed(self):
        results = (
            stm.TriggerResult("excess_10d", 10, stm.READING_MEAN, -0.2, -1.0, False, 4, False),
        )
        line = stm.format_review_line(results)
        assert "n/a" in line or "elégtelen" in line
