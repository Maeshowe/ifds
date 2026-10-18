"""Round-trip cost — the exit side, measured on the same convention as the entry.

The engine charges 2c, i.e. it assumes an exit costs what an entry costs. That was
never measured. Measuring it naively would repeat the 2026-10-04 estimand error:
the entry's 83.5 bp is decision-price-to-fill, while SIM-1's exit figures (MOC
6.6 bp, MKT-at-open 61.2 bp) are order-type-reference-to-fill. Different estimands.

So three separately named metrics per side:
  implementation shortfall = |fill - decision price|      (the cost model input)
  execution slippage       = |fill - order-type reference| (the venue's cost)
  delay cost               = shortfall - execution slippage

Read-only. Task: docs/tasks/2026-10-18-true-roundtrip-cost.md
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "analysis"))

import roundtrip_cost as rc  # noqa: E402


class TestDecisionSession:
    """Derived from the crontab + swing_positions.py, pinned here so a later cron
    change cannot silently invalidate every cost number."""

    SESSIONS = [date(2026, 9, 21), date(2026, 9, 22), date(2026, 9, 23), date(2026, 9, 24)]

    def test_the_decision_price_is_the_close_before_the_fill_session(self):
        """Uniform across exit types — see the task's §3 derivation."""
        assert rc.decision_session(date(2026, 9, 23), self.SESSIONS) == date(2026, 9, 22)

    def test_the_first_session_has_no_predecessor(self):
        assert rc.decision_session(date(2026, 9, 21), self.SESSIONS) is None

    def test_a_fill_date_outside_the_calendar_is_unresolved(self):
        assert rc.decision_session(date(2026, 12, 25), self.SESSIONS) is None


class TestOrderTypeReference:
    """What price did the order type PROMISE? MOC promises the close; a market
    order sent at the opening bell promises the open."""

    BAR = rc.Bar(date=date(2026, 9, 23), open=10.0, high=10.5, low=9.5, close=10.2)

    def test_a_time_stop_is_priced_against_the_close(self):
        assert rc.order_type_reference("TIME_STOP", self.BAR) == pytest.approx(10.2)

    @pytest.mark.parametrize("et", ["TP1", "TP2", "MENTAL_SL", "TRAIL_SL", "HARD_SL"])
    def test_next_day_legs_are_priced_against_the_open(self, et):
        assert rc.order_type_reference(et, self.BAR) == pytest.approx(10.0)

    def test_an_unknown_exit_type_is_unresolved_not_guessed(self):
        assert rc.order_type_reference("SOMETHING_NEW", self.BAR) is None


class TestCostMetrics:
    """A SELL leg: an adverse fill is BELOW the reference."""

    def test_shortfall_is_signed_adverse_positive(self):
        # decision 100, filled 99 -> we lost 100 bp selling
        assert rc.slippage_bps(fill=99.0, reference=100.0) == pytest.approx(100.0)

    def test_a_favourable_fill_is_negative(self):
        assert rc.slippage_bps(fill=101.0, reference=100.0) == pytest.approx(-100.0)

    def test_a_zero_or_negative_reference_is_unresolved(self):
        assert rc.slippage_bps(fill=10.0, reference=0.0) is None
        assert rc.slippage_bps(fill=10.0, reference=-1.0) is None

    def test_delay_is_the_part_the_venue_did_not_cause(self):
        leg = rc.LegCost(ticker="X", exit_type="TIME_STOP", fill_date=date(2026, 9, 23),
                         qty=10, fill=99.0, decision_price=100.0, order_reference=99.5)
        assert leg.shortfall_bps == pytest.approx(100.0)
        assert leg.execution_bps == pytest.approx(50.251, abs=0.01)  # 0.5/99.5
        assert leg.delay_bps == pytest.approx(leg.shortfall_bps - leg.execution_bps)


class TestSummary:
    """The report must never collapse the two conventions into one number."""

    LEGS = [
        rc.LegCost("A", "TIME_STOP", date(2026, 9, 23), 10, 99.0, 100.0, 99.5),
        rc.LegCost("B", "TIME_STOP", date(2026, 9, 24), 10, 98.0, 100.0, 98.5),
        rc.LegCost("C", "TP1", date(2026, 9, 24), 10, 101.0, 100.0, 100.5),
    ]

    def test_medians_are_reported_on_absolute_slippage(self):
        """Signed prints carry drift in both directions; |.| is the unbiased
        per-side cost estimator (the convention frl_cost already uses)."""
        s = rc.summarise(self.LEGS)
        assert s["n"] == 3
        assert s["shortfall_median_bps"] == pytest.approx(100.0)

    def test_the_breakdown_is_kept_per_exit_type(self):
        s = rc.summarise(self.LEGS)
        assert set(s["by_exit_type"]) == {"TIME_STOP", "TP1"}
        assert s["by_exit_type"]["TIME_STOP"]["n"] == 2

    def test_an_empty_sample_does_not_crash(self):
        s = rc.summarise([])
        assert s["n"] == 0 and s["shortfall_median_bps"] != s["shortfall_median_bps"]


def test_module_is_read_only():
    src = Path(rc.__file__).read_text()
    for forbidden in ("atomic_write_json", "save_swing_positions", "confirm_decision"):
        assert forbidden not in src
