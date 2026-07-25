"""FRL-2 holdout tests — windows/purge, one-touch, PROMOTE/PARK, transition."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

_RESEARCH_DIR = str(Path(__file__).resolve().parents[1] / "scripts" / "research")
if _RESEARCH_DIR not in sys.path:
    sys.path.insert(0, _RESEARCH_DIR)

import factors.base as fb  # noqa: E402
import frl_config as cfg  # noqa: E402
import frl_holdout as holdout  # noqa: E402


def _summary(mean_ic, bar, inconclusive=None, t_eff=20.0):
    if inconclusive is None:
        inconclusive = abs(mean_ic) < bar
    return {"mean_ic": mean_ic, "era_bar": bar, "inconclusive": inconclusive, "t_eff": t_eff}


class TestWindows:
    def test_dev_purge_holdout_do_not_overlap(self):
        w = holdout.compute_windows(date(2026, 7, 20), first_day=date(2026, 5, 18))
        assert w.dev_end < w.purge_start <= w.purge_end < w.holdout_start
        assert w.holdout_end == date(2026, 7, 20)

    def test_purge_is_five_trading_days(self):
        from ifds.utils.trading_calendar import trading_days_between

        w = holdout.compute_windows(date(2026, 7, 20), first_day=date(2026, 5, 18))
        purge_days = trading_days_between(w.purge_start, w.purge_end)
        assert len(purge_days) == cfg.HOLDOUT_PURGE_DAYS

    def test_holdout_spans_four_weeks(self):
        w = holdout.compute_windows(date(2026, 7, 20), first_day=date(2026, 5, 18))
        assert (w.holdout_end - w.holdout_start).days >= 25  # 4 weeks of trading days

    def test_window_rolls_forward_with_the_last_day(self):
        earlier = holdout.compute_windows(date(2026, 7, 13), first_day=date(2026, 5, 18))
        later = holdout.compute_windows(date(2026, 7, 20), first_day=date(2026, 5, 18))
        assert later.holdout_start > earlier.holdout_start
        assert later.dev_end > earlier.dev_end  # rolled-out days join dev


class TestOneTouch:
    def test_untouched_hypothesis_passes(self):
        holdout.assert_untouched("HYP-004", [{"hyp_id": "HYP-001", "holdout_touched": True}])

    def test_second_touch_is_a_hard_error(self):
        entries = [{"hyp_id": "HYP-004", "holdout_touched": True}]
        with pytest.raises(holdout.HoldoutTouchError, match="G6"):
            holdout.assert_untouched("HYP-004", entries)

    def test_congestion_counts_distinct_hypotheses_on_the_current_window(self):
        entries = [
            {
                "hyp_id": "HYP-001",
                "holdout_touched": True,
                "dev_window": {"holdout": ["2026-06-22", "2026-07-20"]},
            },
            {
                "hyp_id": "HYP-002",
                "holdout_touched": True,
                "dev_window": {"holdout": ["2026-06-22", "2026-07-20"]},
            },
            {
                "hyp_id": "HYP-003",
                "holdout_touched": True,
                "dev_window": {"holdout": ["2026-05-18", "2026-06-15"]},
            },  # older window
        ]
        assert holdout.holdout_congestion(entries, date(2026, 6, 22)) == 2


class TestPromoteVerdict:
    def test_strong_swing_with_matching_sign_promotes(self):
        verdict = holdout.promote_verdict(
            {cfg.ERA_SWING: _summary(0.06, 0.04), cfg.ERA_LEGACY: _summary(0.05, 0.02)},
            expected_sign=1,
            bh_pass=True,
        )
        assert verdict.decision == "PROMOTE"

    def test_legacy_only_strength_never_promotes(self):
        verdict = holdout.promote_verdict(
            {cfg.ERA_SWING: _summary(0.01, 0.05), cfg.ERA_LEGACY: _summary(0.08, 0.02)},
            expected_sign=1,
            bh_pass=True,
        )
        assert verdict.decision == "PARK_UNTIL_SWING_POWER"
        assert any("legacy-only" in r or "legacy supports" in r for r in verdict.reasons)

    def test_swing_sign_contradiction_kills(self):
        verdict = holdout.promote_verdict(
            {cfg.ERA_SWING: _summary(-0.09, 0.04), cfg.ERA_LEGACY: _summary(-0.08, 0.02)},
            expected_sign=1,
            bh_pass=True,
        )
        assert verdict.decision == "KILL"

    def test_failed_bh_cannot_promote_even_with_a_big_ic(self):
        verdict = holdout.promote_verdict(
            {cfg.ERA_SWING: _summary(0.20, 0.04)}, expected_sign=1, bh_pass=False
        )
        assert verdict.decision != "PROMOTE"

    def test_missing_swing_era_is_not_a_promote(self):
        verdict = holdout.promote_verdict(
            {cfg.ERA_LEGACY: _summary(0.09, 0.02)}, expected_sign=1, bh_pass=True
        )
        assert verdict.decision == "PARK_UNTIL_SWING_POWER"


class TestSwingOnlyParkPath:
    """A swing-only factor (no legacy leg) must be able to PARK, not just KILL.

    HYP-005 exposed the gap: legacy_supports is always False for a swing-only
    factor, so the old logic could only PROMOTE or KILL — contradicting the
    hypothesis's own pre-reg criterion (c) 'T_eff elégtelen → PARK'.
    """

    def test_swing_only_underpowered_correct_sign_parks(self):
        """HYP-005 h=5 shape: sign correct, |IC|>=bar, but T_eff inadequate, BH fail."""
        verdict = holdout.promote_verdict(
            {cfg.ERA_SWING: _summary(0.0435, 0.0367, inconclusive=False, t_eff=4.6)},
            expected_sign=1,
            bh_pass=False,
        )
        assert verdict.decision == "PARK_UNTIL_SWING_POWER"
        assert any("underpowered" in r or "pre-reg c" in r for r in verdict.reasons)

    def test_swing_only_adequate_teff_clean_fail_kills(self):
        """HYP-005 h=1 shape: T_eff ample (23), IC tiny, sign ok — a genuine null."""
        verdict = holdout.promote_verdict(
            {cfg.ERA_SWING: _summary(0.0079, 0.0311, inconclusive=True, t_eff=23.0)},
            expected_sign=1,
            bh_pass=False,
        )
        assert verdict.decision == "KILL"
        assert any("pre-reg a" in r or "genuine null" in r for r in verdict.reasons)

    def test_swing_only_sign_contradiction_is_terminal(self):
        verdict = holdout.promote_verdict(
            {cfg.ERA_SWING: _summary(-0.05, 0.03, inconclusive=False, t_eff=4.0)},
            expected_sign=1,
            bh_pass=False,
        )
        assert verdict.decision == "KILL"
        assert any("contradiction" in r for r in verdict.reasons)

    def test_adequacy_threshold_is_the_pivot(self):
        """Same IC and sign; only T_eff crossing the floor flips PARK <-> KILL."""
        below = holdout.promote_verdict(
            {
                cfg.ERA_SWING: _summary(
                    0.03, 0.02, inconclusive=False, t_eff=cfg.MIN_ADEQUATE_T_EFF - 1
                )
            },
            expected_sign=1,
            bh_pass=False,
        )
        at = holdout.promote_verdict(
            {cfg.ERA_SWING: _summary(0.03, 0.02, inconclusive=False, t_eff=cfg.MIN_ADEQUATE_T_EFF)},
            expected_sign=1,
            bh_pass=False,
        )
        assert below.decision == "PARK_UNTIL_SWING_POWER"
        assert at.decision == "KILL"

    def test_legacy_adequate_fail_still_kills_a_factor_with_a_weak_swing(self):
        """HYP-004 shape: legacy T_eff adequate and fails -> terminal, even if the
        swing leg is underpowered. Preserves the confirmed HYP-004 KILL."""
        verdict = holdout.promote_verdict(
            {
                cfg.ERA_LEGACY: _summary(-0.0298, 0.0393, inconclusive=True, t_eff=11.8),
                cfg.ERA_SWING: _summary(-0.0950, 0.0749, inconclusive=False, t_eff=3.8),
            },
            expected_sign=-1,
            bh_pass=False,
        )
        assert verdict.decision == "KILL"


class TestParkAutoRetest:
    def test_park_becomes_due_exactly_when_the_bar_is_cleared(self):
        parked = {"decision": "PARK_UNTIL_SWING_POWER", "hyp_id": "HYP-003"}
        assert holdout.retest_due(parked, _summary(0.03, 0.05)) is False
        assert holdout.retest_due(parked, _summary(0.05, 0.05)) is True

    def test_bar_falls_as_the_swing_sample_grows_so_a_park_wakes_up(self):
        """Same IC, more days -> lower bar -> the parked family becomes testable."""
        import numpy as np
        import pandas as pd

        import frl_ic

        rng = np.random.default_rng(3)
        long_series = pd.Series(rng.normal(0.04, 0.08, 400))
        short_series = long_series.iloc[:12]

        bar_short = frl_ic.era_bar(short_series, 5)
        bar_long = frl_ic.era_bar(long_series, 5)
        assert bar_short > bar_long, "the bar must fall as the sample grows"

        # An IC between the two bars: too weak for the small sample, enough once
        # the swing weeks accumulate — exactly the auto-retest trigger point.
        ic = (bar_short + bar_long) / 2
        parked = {"decision": "PARK_UNTIL_SWING_POWER"}
        assert holdout.retest_due(parked, _summary(ic, bar_short)) is False
        assert holdout.retest_due(parked, _summary(ic, bar_long)) is True

    def test_non_parked_entries_are_never_due(self):
        assert holdout.retest_due({"decision": "KILL"}, _summary(0.9, 0.01)) is False


class TestHoldoutTransition:
    def test_all_three_conditions_met_passes(self):
        v = holdout.holdout_verdict(ic_dev=0.06, ic_holdout=0.04, family_p=0.03, expected_sign=1)
        assert v.passed is True

    def test_half_magnitude_rule_blocks_a_faded_signal(self):
        v = holdout.holdout_verdict(ic_dev=0.10, ic_holdout=0.02, family_p=0.01, expected_sign=1)
        assert v.passed is False
        assert any("0.5*" in r for r in v.reasons)

    def test_sign_flip_in_holdout_fails(self):
        v = holdout.holdout_verdict(ic_dev=0.08, ic_holdout=-0.07, family_p=0.01, expected_sign=1)
        assert v.passed is False

    def test_weak_family_p_fails(self):
        v = holdout.holdout_verdict(ic_dev=0.08, ic_holdout=0.07, family_p=0.20, expected_sign=1)
        assert v.passed is False


class TestSanityGate:
    def setup_method(self):
        fb.clear_registry()

    def teardown_method(self):
        fb.clear_registry()

    def _factor(self, name, expected_sign, compute):
        return fb.Factor(
            name=name,
            hyp_id="HYP-TEST",
            data_lane="v1",
            expected_sign=expected_sign,
            compute=compute,
            sanity_panel=fb.linear_sanity_panel("raw", sign=1),
            description="test factor",
        )

    def test_correct_factor_passes_sanity(self):
        f = self._factor("good", 1, lambda panel: panel["raw"])
        result = fb.run_sanity(f)
        assert result.passed is True
        assert result.observed_ic == pytest.approx(1.0)

    def test_sign_flipped_factor_fails_sanity(self):
        """A bugged implementation must never reach the attempt stage (R1#6)."""
        f = self._factor("flipped", 1, lambda panel: -panel["raw"])
        result = fb.run_sanity(f)
        assert result.passed is False
        assert "sign mismatch" in result.detail
        assert "SANITY_FAIL" in result.line()

    def test_constant_factor_fails_sanity(self):
        f = self._factor("dead", 1, lambda panel: panel["raw"] * 0.0)
        assert fb.run_sanity(f).passed is False

    def test_raising_factor_fails_closed(self):
        def boom(panel):
            raise KeyError("missing_column")

        result = fb.run_sanity(self._factor("boom", 1, boom))
        assert result.passed is False
        assert "KeyError" in result.detail

    def test_negative_expected_sign_is_honoured(self):
        f = self._factor("inverse", -1, lambda panel: -panel["raw"])
        assert fb.run_sanity(f).passed is True

    def test_invalid_lane_or_sign_is_rejected_at_construction(self):
        with pytest.raises(ValueError, match="data_lane"):
            fb.Factor("x", "HYP-1", "v3", 1, lambda p: p, lambda: None)
        with pytest.raises(ValueError, match="expected_sign"):
            fb.Factor("x", "HYP-1", "v1", 0, lambda p: p, lambda: None)

    def test_registry_rejects_duplicates(self):
        f = self._factor("dup", 1, lambda panel: panel["raw"])
        fb.register(f)
        with pytest.raises(ValueError, match="duplicate"):
            fb.register(f)
