"""The (e) gate under the two-sided cost estimator — and a proof that can fail.

The invariance evidence originally planned for the 2026-10-19 estimator change
was: "replay all 23 ledger rows under the old and the new cost model, show 0/23
verdicts move". Measured with an ``EconomicView`` that raises on every attribute
read, **0 of 23 rows ever touch the cost model**: every one exits
``promote_verdict`` before the ``if not reasons:`` branch. The 0/23 result is
therefore true for ANY cost numbers — NaN, negative, an exploding sentinel — and
carries no information about the thing being changed. That is the "test mocked
itself out" shape one level deeper, and the house rule exists to prevent it.

The pre-reg also gave the wrong REASON. It said the arms die at the era bar;
four of them clear it (A-0003, A-0004, A-0007, A-0008) and are stopped by
``bh_pass`` alone. ERRATA §E-6 records both corrections.

So this file proves three separate things instead:
  1. the historical verdicts are preserved (companion #3), pinned inline rather
     than read from the live ledger, so the test is hermetic AND specific;
  2. the gate IS reachable and the cost model DOES move verdicts when it is
     reached — a positive control, without which (1) proves nothing;
  3. the new band is strictly looser than the old one, stated as a measured
     fact rather than left for a reader to discover.

Pre-reg: docs/planning/2026-10-19-cost-estimator-amendment.md D-C1..D-C4 and
ERRATA D-E1..D-E6 (approved 2026-10-19); the gate itself is governed by
docs/planning/2026-10-04-economic-gate-preregistration.md §3.1, amended in §9.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "research"))

import frl_config as cfg  # noqa: E402
import frl_holdout as holdout  # noqa: E402
import frl_ic  # noqa: E402

# --- the wall, before and after ---------------------------------------------
SIGMA_CS_H5 = 0.06
OLD_ROUND_TRIP_BPS = 167.0  # 2 x median(|fill - plan limit|) = 2 x 83.5
NEW_ROUND_TRIP_POINT_BPS = 63.52  # entry +40.32 (open-anchored) + exit +23.20
NEW_ROUND_TRIP_BOUND_BPS = 84.73  # one-sided 95% UCB on each side, summed


def _band(round_trip_point: float, round_trip_bound: float) -> holdout.EconomicView:
    """Build the (e) gate's two thresholds the way run_frl_batch does."""

    def breakeven(round_trip: float) -> float:
        cost = frl_ic.as_traded_cost_bps(5, round_trip)
        return frl_ic.costed_view(0.0, SIGMA_CS_H5, 5, cost).breakeven_ic

    return holdout.EconomicView(
        breakeven_median=breakeven(round_trip_point),
        breakeven_p75=breakeven(round_trip_bound),
    )


OLD_BAND = _band(OLD_ROUND_TRIP_BPS, 2 * 136.0)
NEW_BAND = _band(NEW_ROUND_TRIP_POINT_BPS, NEW_ROUND_TRIP_BOUND_BPS)


class _Exploding:
    """Any read proves the (e) gate was reached."""

    def __getattr__(self, name: str):  # pragma: no cover - raises by design
        raise AssertionError(f"the (e) gate read {name!r}")


# --- the four ledger rows that clear the era bar ------------------------------
# Pinned INLINE, not read from research/attempt_ledger.jsonl: that file is live
# research state, and a test that reads it would be green or red depending on
# this machine. Values copied from the ledger on 2026-10-19; all four verdicts
# are human-confirmed and terminal.
# ``today`` is what the CURRENT engine returns, which is the quantity a
# cost-invariance test can legitimately pin. It is NOT always the ledger's stored
# decision, and that is correct, not a bug: all four rows carry
# ``decision_source: human``, and the T_eff adequacy gate (079e4a1, 2026-07-25)
# postdates their closure on 07-21/07-24. The ledger is never re-run for verdict
# generation (house-rule companion #4), so old rows keep old verdicts.
BAR_CLEARING_ROWS = [
    # attempt, mean_ic, era_bar, expected_sign, t_eff, today, stored (human)
    ("A-0003", -0.0950, 0.0749, -1, 3.8, "PARK_UNTIL_SWING_POWER", "KILL"),
    ("A-0004", -0.1087, 0.0647, -1, 2.7, "PARK_UNTIL_SWING_POWER", "KILL"),
    ("A-0007", +0.0435, 0.0367, +1, 4.6, "PARK_UNTIL_SWING_POWER", "PARK_UNTIL_SWING_POWER"),
    ("A-0008", +0.0522, 0.0295, +1, 3.3, "PARK_UNTIL_SWING_POWER", "PARK_UNTIL_SWING_POWER"),
]


def _summaries(mean_ic: float, era_bar: float, t_eff: float = 4.0) -> dict:
    return {
        cfg.ERA_SWING: {
            "mean_ic": mean_ic,
            "era_bar": era_bar,
            "inconclusive": abs(mean_ic) < era_bar,
            "t_eff": t_eff,
        }
    }


class TestTheGateWasNeverReached:
    """What the 23-row replay actually shows — and what it does not."""

    @pytest.mark.parametrize(
        "attempt,mean_ic,bar,sign,t_eff,today,stored", BAR_CLEARING_ROWS
    )
    def test_bh_not_the_era_bar_is_what_stops_these_rows(
        self, attempt, mean_ic, bar, sign, t_eff, today, stored
    ):
        """These four CLEAR the bar; only bh_pass stops them (ERRATA §E-6).

        The exploding view proves the claim positively: if the cost model were
        consulted on this path, this test would raise instead of asserting.
        """
        summaries = _summaries(mean_ic, bar, t_eff)
        assert summaries[cfg.ERA_SWING]["inconclusive"] is False, attempt

        verdict = holdout.promote_verdict(
            summaries, sign, bh_pass=False, economic_views={cfg.ERA_SWING: _Exploding()}
        )
        assert verdict.decision == today, f"{attempt} changed verdict"
        assert any("BH-FDR" in reason for reason in verdict.reasons)

    @pytest.mark.parametrize("band", [OLD_BAND, NEW_BAND, None])
    def test_the_verdicts_are_identical_under_every_cost_model(self, band):
        """Companion #3 — but note WHY it holds: the gate is never consulted."""
        views = None if band is None else {cfg.ERA_SWING: band}
        for attempt, mean_ic, bar, sign, t_eff, today, _stored in BAR_CLEARING_ROWS:
            verdict = holdout.promote_verdict(
                _summaries(mean_ic, bar, t_eff), sign, bh_pass=False, economic_views=views
            )
            assert verdict.decision == today, attempt

    def test_the_human_decisions_on_record_are_not_touched_by_this_change(self):
        """What Tamás actually decided stays on the record, whatever the engine says.

        A-0007/A-0008 were auto-KILL and human-PARKed on 2026-07-24; A-0003/A-0004
        were human-confirmed KILL on 07-21. The cost estimator cannot reach any of
        them, so none of these is up for revision by this commit.
        """
        stored = {attempt: row[-1] for attempt, *row in [(r[0], *r[1:]) for r in BAR_CLEARING_ROWS]}
        assert stored == {
            "A-0003": "KILL",
            "A-0004": "KILL",
            "A-0007": "PARK_UNTIL_SWING_POWER",
            "A-0008": "PARK_UNTIL_SWING_POWER",
        }


class TestThePositiveControl:
    """Without this class the file above would pass against a broken engine."""

    def test_the_gate_is_reachable_when_bh_passes(self):
        with pytest.raises(AssertionError, match="the \\(e\\) gate read"):
            holdout.promote_verdict(
                _summaries(0.20, 0.05),
                expected_sign=1,
                bh_pass=True,
                economic_views={cfg.ERA_SWING: _Exploding()},
            )

    def test_an_absurd_cost_model_does_flip_the_verdict(self):
        """The proof must be able to fail. A free book promotes; a ruinous one parks."""
        summaries = _summaries(0.20, 0.05)
        free = holdout.promote_verdict(
            summaries, 1, True, {cfg.ERA_SWING: _band(0.001, 0.002)}
        )
        ruinous = holdout.promote_verdict(
            summaries, 1, True, {cfg.ERA_SWING: _band(50_000.0, 60_000.0)}
        )
        assert free.decision == "PROMOTE"
        assert ruinous.decision == "PARK_UNECONOMIC"
        assert free.decision != ruinous.decision, "the cost model must be load-bearing"

    def test_the_real_estimator_change_moves_a_verdict_in_the_reachable_band(self):
        """|IC| = 0.12 at h=5 is FAIL on the old wall and INCONCLUSIVE on the new.

        This is the live effect of the 2026-10-19 change, isolated. No historical
        attempt sits here — but the next one might, which is the whole point.
        """
        summaries = _summaries(0.12, 0.05)
        old = holdout.promote_verdict(summaries, 1, True, {cfg.ERA_SWING: OLD_BAND})
        new = holdout.promote_verdict(summaries, 1, True, {cfg.ERA_SWING: NEW_BAND})
        assert old.decision == "PARK_UNECONOMIC"
        assert new.decision == "INCONCLUSIVE_ON_COST"


class TestTheNewBandIsLooser:
    """Stated as a measured fact, because a looser gate is the thing to watch."""

    def test_both_edges_move_down_and_the_report_must_say_so(self):
        assert NEW_BAND.breakeven_median < OLD_BAND.breakeven_median
        assert NEW_BAND.breakeven_p75 < OLD_BAND.breakeven_p75
        assert NEW_BAND.breakeven_median == pytest.approx(0.1059, abs=0.0005)
        assert NEW_BAND.breakeven_p75 == pytest.approx(0.1412, abs=0.0005)

    def test_the_band_is_still_ordered_so_the_gate_cannot_degenerate(self):
        assert NEW_BAND.breakeven_median <= NEW_BAND.breakeven_p75
        assert holdout.economic_status(0.0, NEW_BAND) == holdout.ECONOMIC_FAIL

    def test_the_measured_signal_is_nowhere_near_either_wall(self):
        """|IC| across the whole score family ran below 0.009. The relief is real
        and it does not rescue this family — a 12x gap, not a 26x one."""
        assert holdout.economic_status(0.009, NEW_BAND) == holdout.ECONOMIC_FAIL
        assert holdout.economic_status(0.009, OLD_BAND) == holdout.ECONOMIC_FAIL
