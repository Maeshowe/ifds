"""SIM-1 — tests for the §11.20 counterfactual exit-geometry harness.

The harness re-runs the PRODUCTION exit logic
(``ifds.state.swing_positions.evaluate_position_eod``) on historical bars with
two anchors: the planned price (configuration A — how it actually ran) and the
real fill (configuration B — how it should have run). These tests pin the pure
units the harness adds on top of that production function: ATR recovery from a
plan row, level rebasing, and the day-by-day execution model.

Read-only analysis module: it must never write trading state.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "analysis"))

import counterfactual_geometry as cg  # noqa: E402


# ---------------------------------------------------------------------------
# ATR recovery from an execution-plan row
# ---------------------------------------------------------------------------


class TestDeriveAtr:
    def test_recovers_the_atr_from_a_consistent_plan_row(self):
        """MANH 2026-09-14 — the §11.20 worked example. ATR = 6.953."""
        atr = cg.derive_atr(entry=201.82, stop=187.92, tp1=212.25, tp2=222.68)
        assert atr == pytest.approx(6.953, abs=1e-3)

    def test_tolerates_cent_rounding_in_the_plan(self):
        """JHG 2026-05-27: levels rounded to the cent on a ~$5 stock.

        The three implied ATRs differ (0.0900 / 0.0867 / 0.0900) purely from
        rounding. A relative tolerance would reject this row; the harness must
        accept it, because the row IS internally consistent to the cent.
        """
        atr = cg.derive_atr(entry=5.20, stop=5.02, tp1=5.33, tp2=5.47)
        assert atr == pytest.approx(0.09, abs=1e-3)

    def test_rejects_a_genuinely_inconsistent_row(self):
        """A row whose levels cannot come from one ATR must return None.

        Fail LOUD, never silently invent an ATR — a wrong ATR would propagate
        into every counterfactual level for that position.
        """
        assert cg.derive_atr(entry=100.0, stop=90.0, tp1=130.0, tp2=140.0) is None

    def test_uses_a_tolerance_not_exact_equality(self):
        """Degeneracy/consistency checks are tolerance-based (ifds-rules)."""
        # One cent of noise on each level must still resolve.
        assert cg.derive_atr(entry=50.0, stop=46.99, tp1=52.26, tp2=54.50) is not None


# ---------------------------------------------------------------------------
# Rebasing the levels onto the real fill
# ---------------------------------------------------------------------------


class TestRebase:
    def test_preserves_the_atr_multiples_at_the_new_anchor(self):
        stop, tp1, tp2 = cg.rebase_levels(anchor=207.69, atr=6.953)
        assert stop == pytest.approx(207.69 - 2.0 * 6.953)
        assert tp1 == pytest.approx(207.69 + 1.5 * 6.953)
        assert tp2 == pytest.approx(207.69 + 3.0 * 6.953)

    def test_an_adverse_fill_restores_the_planned_risk_reward(self):
        """The §11.20 mechanism, stated as a property.

        Planned R:R is 1.5/2.0 = 0.75. Anchored to the PLANNED price while
        filling 2.91% higher, the realized R:R collapses to ~0.23. Rebasing to
        the fill must restore 0.75 exactly.
        """
        atr, fill = 6.953, 207.69
        stop_b, tp1_b, _ = cg.rebase_levels(anchor=fill, atr=atr)
        rr_b = (tp1_b - fill) / (fill - stop_b)
        assert rr_b == pytest.approx(0.75, abs=1e-6)

        # And the factual (planned-anchored) geometry is the degraded one.
        rr_a = (212.25 - fill) / (fill - 187.92)
        assert rr_a == pytest.approx(0.23, abs=0.01)


# ---------------------------------------------------------------------------
# The day-by-day execution model
# ---------------------------------------------------------------------------


def _bars(*rows: tuple[str, float, float, float, float]) -> list[cg.Bar]:
    return [
        cg.Bar(date=date.fromisoformat(d), open=o, high=h, low=lo, close=c)
        for d, o, h, lo, c in rows
    ]


def _pos(**kw) -> cg.SwingPosition:
    base = dict(
        ticker="TEST",
        entry_date="2026-09-14",
        entry_price=100.0,
        atr=5.0,
        stop_level=90.0,
        tp1_level=107.5,
        tp2_level=115.0,
        qty=100,
        qty_remaining=100,
    )
    base.update(kw)
    return cg.SwingPosition(**base)


class TestSimulate:
    def test_time_stop_closes_the_remainder_at_that_days_close(self):
        """days_held >= 5 → SAME-day 21:40 MOC → the exit price is that close."""
        bars = _bars(
            ("2026-09-14", 100.0, 101.0, 99.0, 100.0),
            ("2026-09-15", 100.0, 101.0, 99.0, 100.0),
            ("2026-09-16", 100.0, 101.0, 99.0, 100.0),
            ("2026-09-17", 100.0, 101.0, 99.0, 100.0),
            ("2026-09-18", 100.0, 101.0, 99.0, 100.0),
            ("2026-09-21", 100.0, 101.0, 99.0, 102.5),  # 5th session → TIME_STOP
        )
        result = cg.simulate(_pos(), bars)
        assert result.unresolved is False
        assert [leg.exit_type for leg in result.legs] == ["TIME_STOP"]
        assert result.legs[0].exit_price == pytest.approx(102.5)
        assert result.legs[0].exit_date == date(2026, 9, 21)
        assert result.legs[0].qty == 100

    def test_mental_sl_triggers_on_the_close_and_fills_the_next_open(self):
        bars = _bars(
            ("2026-09-14", 100.0, 101.0, 89.0, 89.5),  # close < stop_level 90
            ("2026-09-15", 88.0, 90.0, 87.0, 88.5),  # fill at THIS open
        )
        result = cg.simulate(_pos(), bars)
        assert [leg.exit_type for leg in result.legs] == ["MENTAL_SL"]
        assert result.legs[0].exit_price == pytest.approx(88.0)
        assert result.legs[0].exit_date == date(2026, 9, 15)

    def test_tp1_sells_half_at_the_next_open_and_keeps_evaluating(self):
        """TP1 is a PARTIAL leg — the remainder stays open under the trail."""
        bars = _bars(
            ("2026-09-14", 100.0, 108.0, 99.0, 107.0),  # high >= tp1 107.5
            ("2026-09-15", 107.0, 107.5, 106.0, 107.0),  # TP1 fills at 107.0
            ("2026-09-16", 107.0, 107.0, 100.0, 100.0),  # close < trail → TRAIL_SL
            ("2026-09-17", 99.5, 100.0, 99.0, 99.5),  # trail fills here
        )
        result = cg.simulate(_pos(), bars)
        assert [leg.exit_type for leg in result.legs] == ["TP1", "TRAIL_SL"]
        assert result.legs[0].qty == 50
        assert result.legs[0].exit_price == pytest.approx(107.0)
        assert result.legs[1].qty == 50
        assert result.legs[1].exit_price == pytest.approx(99.5)

    def test_tp2_wins_over_tp1_in_the_same_session(self):
        bars = _bars(
            ("2026-09-14", 100.0, 116.0, 99.0, 115.5),  # high >= tp2 115
            ("2026-09-15", 114.0, 115.0, 113.0, 114.0),
        )
        result = cg.simulate(_pos(), bars)
        assert [leg.exit_type for leg in result.legs] == ["TP2"]
        assert result.legs[0].qty == 100

    def test_a_next_day_action_without_a_following_bar_is_unresolved(self):
        """Never silently close at a price we do not have.

        A trigger on the last available bar has no next session to fill in — the
        position must be reported UNRESOLVED, not closed at an invented price.
        """
        bars = _bars(("2026-09-14", 100.0, 101.0, 89.0, 89.5))  # MENTAL_SL, no next bar
        result = cg.simulate(_pos(), bars)
        assert result.unresolved is True
        assert result.legs == ()

    def test_running_out_of_bars_before_any_exit_is_unresolved(self):
        bars = _bars(
            ("2026-09-14", 100.0, 101.0, 99.0, 100.0),
            ("2026-09-15", 100.0, 101.0, 99.0, 100.0),
        )
        result = cg.simulate(_pos(), bars)
        assert result.unresolved is True

    def test_does_not_mutate_the_input_position(self):
        """Immutability: the caller's position is reused across configurations A/B."""
        pos = _pos()
        before = (pos.qty_remaining, pos.tp1_hit, pos.trail_sl, pos.days_held)
        bars = _bars(
            ("2026-09-14", 100.0, 108.0, 99.0, 107.0),
            ("2026-09-15", 107.0, 107.5, 106.0, 107.0),
            ("2026-09-16", 107.0, 107.0, 100.0, 100.0),
            ("2026-09-17", 99.5, 100.0, 99.0, 99.5),
        )
        cg.simulate(pos, bars)
        assert (pos.qty_remaining, pos.tp1_hit, pos.trail_sl, pos.days_held) == before

    def test_uses_the_production_evaluator(self, monkeypatch):
        """Guard: the harness must call evaluate_position_eod, not a local copy.

        If a future refactor re-implements the exit rules here, this test fails
        loudly — the whole credibility of the measurement rests on reusing the
        production function.
        """
        calls = []
        real = cg.evaluate_position_eod

        def spy(*args, **kwargs):
            calls.append(args[0].ticker)
            return real(*args, **kwargs)

        monkeypatch.setattr(cg, "evaluate_position_eod", spy)
        cg.simulate(_pos(), _bars(("2026-09-14", 100.0, 101.0, 99.0, 100.0)))
        assert calls == ["TEST"]


# ---------------------------------------------------------------------------
# P&L accounting
# ---------------------------------------------------------------------------


class TestPnl:
    def test_gross_pnl_is_summed_over_the_legs_against_the_anchor(self):
        legs = [
            cg.ExitLeg(exit_type="TP1", exit_date=date(2026, 9, 15), exit_price=110.0, qty=50),
            cg.ExitLeg(exit_type="TRAIL_SL", exit_date=date(2026, 9, 17), exit_price=95.0, qty=50),
        ]
        # entry at the real fill: 50*(110-100) + 50*(95-100) = 500 - 250 = 250
        assert cg.gross_pnl(legs, entry_price=100.0) == pytest.approx(250.0)

    def test_commission_is_calibrated_to_the_observed_fills(self):
        """max($1.05, $0.0057/share), fitted on the 106 observed paper legs.

        NOT the IBKR published schedule — the paper account's actual prints.
        Fit quality: median abs err $0.04, p90 $0.11 (see the report).
        """
        assert cg.commission(50) == pytest.approx(1.05)  # floor dominates
        assert cg.commission(1000) == pytest.approx(5.70)


# ---------------------------------------------------------------------------
# Read-only guarantee
# ---------------------------------------------------------------------------


def test_module_contains_no_trading_state_write_path():
    """Read-only guarantee, enforced on the source (ifds-rules: hermetic tests).

    A measurement module that can write ``state/`` could corrupt the very
    ledger it measures. The ban is on the write helpers, not on reading.
    """
    src = Path(cg.__file__).read_text()
    for forbidden in ("save_swing_positions", "atomic_write_json", "save_phase4_snapshot"):
        assert forbidden not in src, f"analysis module must not import/call {forbidden}"
