"""SIM-EXEC — tests for the entry-execution counterfactual.

The question is not "how much slippage would a LMT save" but whether the saving
beats the P&L of the entries it would have MISSED — the classic adverse-selection
trap. These tests pin the fill rule (fixed in the task before the run) and the
decomposition that separates the two opposing forces.

Read-only. Task: docs/tasks/2026-10-04-entry-execution-counterfactual.md
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "analysis"))

import entry_execution as ee  # noqa: E402
from counterfactual_geometry import Bar  # noqa: E402


def _bar(day: str, o: float, h: float, lo: float, c: float) -> Bar:
    return Bar(date=date.fromisoformat(day), open=o, high=h, low=lo, close=c)


# ---------------------------------------------------------------------------
# The fill rule (task §3.2)
# ---------------------------------------------------------------------------


class TestLimitFill:
    def test_an_open_below_the_limit_fills_at_the_open(self):
        """You get the better price, not the limit — the open is already through it."""
        bars = [_bar("2026-09-14", 48.0, 52.0, 47.0, 51.0)]
        fill = ee.limit_fill(bars, limit=50.0, sessions=1)
        assert fill is not None
        assert fill.price == pytest.approx(48.0)
        assert fill.date == date(2026, 9, 14)

    def test_an_open_above_the_limit_fills_at_the_limit_when_the_low_reaches_it(self):
        bars = [_bar("2026-09-14", 52.0, 53.0, 49.5, 51.0)]
        fill = ee.limit_fill(bars, limit=50.0, sessions=1)
        assert fill is not None
        assert fill.price == pytest.approx(50.0)

    def test_a_session_that_never_trades_down_to_the_limit_does_not_fill(self):
        """The gap-up case — exactly the entry a MKT order would have caught."""
        bars = [_bar("2026-09-14", 52.0, 55.0, 51.5, 54.0)]
        assert ee.limit_fill(bars, limit=50.0, sessions=1) is None

    def test_a_day_order_does_not_reach_into_the_next_session(self):
        bars = [
            _bar("2026-09-14", 52.0, 55.0, 51.5, 54.0),  # no fill
            _bar("2026-09-15", 51.0, 52.0, 49.0, 50.0),  # would fill, but DAY expired
        ]
        assert ee.limit_fill(bars, limit=50.0, sessions=1) is None

    def test_a_two_session_order_fills_on_the_second_session(self):
        bars = [
            _bar("2026-09-14", 52.0, 55.0, 51.5, 54.0),
            _bar("2026-09-15", 51.0, 52.0, 49.0, 50.0),
        ]
        fill = ee.limit_fill(bars, limit=50.0, sessions=2)
        assert fill is not None
        assert fill.price == pytest.approx(50.0)
        assert fill.date == date(2026, 9, 15)

    def test_no_bars_means_no_fill(self):
        assert ee.limit_fill([], limit=50.0, sessions=2) is None

    def test_the_rule_is_documented_as_fill_rate_optimistic(self):
        """The daily bar cannot prove a queued LMT would really have been hit.

        The task states the rule overstates the fill rate, biasing IN FAVOUR of
        the limit variants — so an unfavourable result is the strong one.
        """
        assert "overstates" in ee.limit_fill.__doc__.lower()


# ---------------------------------------------------------------------------
# Variant definitions — pinned to the task's pre-registration
# ---------------------------------------------------------------------------


class TestVariants:
    def test_variant_set_matches_the_task_exactly(self):
        """Guard against silent post-hoc variant expansion."""
        assert [v.name for v in ee.VARIANTS] == ["V1", "V2", "V3", "V4"]
        assert [(v.atr_offset, v.sessions) for v in ee.VARIANTS] == [
            (0.0, 1),
            (0.0, 2),
            (0.25, 1),
            (0.50, 1),
        ]

    def test_the_limit_price_applies_the_atr_offset(self):
        assert ee.limit_price(planned=100.0, atr=4.0, atr_offset=0.25) == pytest.approx(101.0)
        assert ee.limit_price(planned=100.0, atr=4.0, atr_offset=0.0) == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# The decomposition (task §3.3)
# ---------------------------------------------------------------------------


class TestDecomposition:
    def test_price_improvement_counts_only_the_filled_positions(self):
        rows = [
            ee.VariantRow(key=("A", "d"), filled=True, fill_price=99.0, baseline_fill=100.0,
                          qty=10, pnl=50.0, baseline_pnl=40.0),
            ee.VariantRow(key=("B", "d"), filled=False, fill_price=None, baseline_fill=100.0,
                          qty=10, pnl=0.0, baseline_pnl=-30.0),
        ]
        assert ee.price_improvement(rows) == pytest.approx(10.0)  # (100-99)*10, A only

    def test_foregone_pnl_is_the_baseline_pnl_of_the_misses(self):
        rows = [
            ee.VariantRow(("A", "d"), True, 99.0, 100.0, 10, 50.0, 40.0),
            ee.VariantRow(("B", "d"), False, None, 100.0, 10, 0.0, -30.0),
            ee.VariantRow(("C", "d"), False, None, 100.0, 10, 0.0, 120.0),
        ]
        assert ee.foregone_pnl(rows) == pytest.approx(90.0)  # -30 + 120

    def test_adverse_selection_compares_the_misses_against_the_fills(self):
        """Positive => the misses were the BETTER trades: the limit cuts winners."""
        rows = [
            ee.VariantRow(("A", "d"), True, 99.0, 100.0, 10, 10.0, 10.0),
            ee.VariantRow(("B", "d"), True, 99.0, 100.0, 10, 30.0, 30.0),
            ee.VariantRow(("C", "d"), False, None, 100.0, 10, 0.0, 200.0),
        ]
        verdict = ee.adverse_selection(rows)
        assert verdict.mean_filled == pytest.approx(20.0)
        assert verdict.mean_missed == pytest.approx(200.0)
        assert verdict.gap == pytest.approx(180.0)
        assert verdict.cuts_winners is True

    def test_adverse_selection_is_undefined_without_both_groups(self):
        rows = [ee.VariantRow(("A", "d"), True, 99.0, 100.0, 10, 10.0, 10.0)]
        verdict = ee.adverse_selection(rows)
        assert verdict.gap != verdict.gap  # NaN
        assert verdict.cuts_winners is False

    def test_fill_rate(self):
        rows = [
            ee.VariantRow(("A", "d"), True, 99.0, 100.0, 10, 0.0, 0.0),
            ee.VariantRow(("B", "d"), False, None, 100.0, 10, 0.0, 0.0),
            ee.VariantRow(("C", "d"), True, 99.0, 100.0, 10, 0.0, 0.0),
        ]
        assert ee.fill_rate(rows) == pytest.approx(2 / 3)
