"""SIM-2 — tests for the exit-architecture sweep.

The sweep re-runs the SIM-1 harness (production ``evaluate_position_eod``) over
a PRE-REGISTERED grid of max_hold x TP1 multiples, on the same fixed real
entries. These tests pin the units the sweep adds: the common-sample rule, the
paired statistics, the Sidak correction and the slot-concurrency calculation.

Read-only. Task: docs/tasks/2026-10-03-sim2-exit-architecture-sweep.md
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "analysis"))

import exit_sweep as es  # noqa: E402


# ---------------------------------------------------------------------------
# Multiplicity
# ---------------------------------------------------------------------------


class TestSidak:
    def test_matches_the_preregistered_alpha_for_14_comparisons(self):
        """The task pre-registers m=14 -> alpha_per = 0.00366."""
        assert es.sidak_alpha(14) == pytest.approx(0.00366, abs=1e-5)

    def test_one_comparison_leaves_alpha_untouched(self):
        assert es.sidak_alpha(1) == pytest.approx(0.05)

    def test_more_comparisons_tighten_the_threshold(self):
        assert es.sidak_alpha(50) < es.sidak_alpha(14) < es.sidak_alpha(2)


# ---------------------------------------------------------------------------
# The common-sample rule
# ---------------------------------------------------------------------------


class TestCommonSample:
    def test_keeps_only_keys_resolvable_in_every_cell(self):
        """A position unresolvable in ANY cell is dropped from ALL cells.

        Otherwise a longer max_hold would look better merely by shedding the
        most recent positions — a selection artifact, not an exit effect.
        """
        per_cell = {
            "a": {"X": 10.0, "Y": 20.0, "Z": 30.0},
            "b": {"X": 11.0, "Y": 21.0},  # Z unresolvable here
        }
        keys = es.common_keys(per_cell)
        assert keys == {"X", "Y"}

    def test_an_empty_cell_empties_the_common_sample(self):
        assert es.common_keys({"a": {"X": 1.0}, "b": {}}) == set()

    def test_no_cells_means_no_common_sample(self):
        assert es.common_keys({}) == set()


# ---------------------------------------------------------------------------
# Paired statistics
# ---------------------------------------------------------------------------


class TestPairedStats:
    def test_identical_series_gives_zero_effect(self):
        stats = es.paired_stats([0.0, 0.0, 0.0, 0.0, 0.0])
        assert stats.total == pytest.approx(0.0)
        assert stats.p_value == pytest.approx(1.0) or stats.p_value != stats.p_value

    def test_a_consistent_positive_shift_is_detected(self):
        stats = es.paired_stats([100.0, 110.0, 90.0, 105.0, 95.0, 100.0])
        assert stats.total == pytest.approx(600.0)
        assert stats.p_value < 0.001
        assert stats.ci_low > 0

    def test_a_noisy_zero_mean_shift_is_not_detected(self):
        stats = es.paired_stats([500.0, -480.0, 300.0, -310.0, 20.0, -30.0])
        assert stats.p_value > 0.05
        assert stats.ci_low < 0 < stats.ci_high

    def test_bootstrap_ci_is_deterministic(self):
        """A fixed seed keeps the reported CI reproducible across runs."""
        deltas = [12.0, -4.0, 33.0, -18.0, 7.0, 2.0, -9.0]
        assert es.paired_stats(deltas).ci_low == es.paired_stats(deltas).ci_low

    def test_too_few_observations_yields_no_inference(self):
        stats = es.paired_stats([5.0])
        assert stats.p_value != stats.p_value  # NaN


# ---------------------------------------------------------------------------
# Slot concurrency — the feasibility constraint
# ---------------------------------------------------------------------------


class TestConcurrency:
    def test_counts_overlapping_positions_on_the_busiest_session(self):
        spans = [
            (date(2026, 9, 14), date(2026, 9, 18)),
            (date(2026, 9, 15), date(2026, 9, 21)),
            (date(2026, 9, 16), date(2026, 9, 17)),
        ]
        sessions = [date(2026, 9, d) for d in (14, 15, 16, 17, 18, 21)]
        # 09-16 and 09-17 both carry all three
        assert es.max_concurrent(spans, sessions) == 3

    def test_non_overlapping_positions_never_exceed_one(self):
        spans = [
            (date(2026, 9, 14), date(2026, 9, 15)),
            (date(2026, 9, 16), date(2026, 9, 17)),
        ]
        sessions = [date(2026, 9, d) for d in (14, 15, 16, 17)]
        assert es.max_concurrent(spans, sessions) == 1

    def test_a_position_occupies_its_slot_on_the_exit_session(self):
        """Conservative by design: the slot is counted as busy on exit day.

        Overstating occupancy is the safe direction for a capacity caveat.
        """
        spans = [(date(2026, 9, 14), date(2026, 9, 15))]
        assert es.max_concurrent(spans, [date(2026, 9, 15)]) == 1

    def test_no_positions_means_no_occupancy(self):
        assert es.max_concurrent([], [date(2026, 9, 14)]) == 0


# ---------------------------------------------------------------------------
# Grid definition — pinned to the task's pre-registration
# ---------------------------------------------------------------------------


class TestPreregisteredGrid:
    def test_grid_matches_the_task_exactly(self):
        """Guard against silent post-hoc grid expansion (forking paths)."""
        assert es.MAX_HOLD_VALUES == (3, 5, 7, 10, 15)
        assert es.TP1_MULTIPLE_VALUES == (1.0, 1.5, 2.0)
        assert len(es.grid()) == 15

    def test_baseline_is_in_the_grid_and_is_the_production_config(self):
        assert es.BASELINE == (5, 1.5)
        assert es.BASELINE in es.grid()

    def test_comparison_count_drives_the_sidak_m(self):
        assert es.COMPARISONS == len(es.grid()) - 1 == 14
