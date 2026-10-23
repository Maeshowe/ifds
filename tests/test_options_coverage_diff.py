"""The coverage check that stands in for a Starter-tier trial key.

A degeneracy tolerance cannot see the failure this is for. ``day.volume`` feeds pcr and
otm_call_ratio and NOTHING else; if a cheaper options plan stops serving it, both go None
for the whole universe, both percentile universes empty, compute_percentile_score returns
its hard-coded 0.5, and every swing raw score becomes an identical 0.0 — no None, no
exception, no log. Coverage is the only detector.

Hermetic: fixture rows only, no production state, no network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "analysis"))

import options_coverage_diff as cov  # noqa: E402


def _rows(values, field="pcr"):
    return [{field: v} for v in values]


class TestAHealthyDayPasses:
    def test_full_coverage_with_spread(self) -> None:
        r = cov.read_feature(_rows([0.8, 1.2, 0.95, 1.4, 0.7]), "pcr")
        assert r.rate == 1.0
        assert not r.degraded and not r.constant

    def test_the_baseline_s_own_rate_is_not_flagged(self) -> None:
        """iv_skew runs at 0.917 normally; that must not read as a failure."""
        values = [0.03] * 917 + [None] * 83
        r = cov.read_feature(_rows(values, "iv_skew"), "iv_skew")
        assert r.rate == pytest.approx(0.917, abs=0.001)
        assert not r.degraded


class TestTheFailureThisExistsFor:
    def test_a_universe_wide_field_loss_is_caught(self) -> None:
        """day.volume gone -> pcr None for everyone."""
        r = cov.read_feature(_rows([None] * 500, "pcr"), "pcr")
        assert r.rate == 0.0
        assert r.degraded

    def test_a_partial_thinning_is_caught(self) -> None:
        values = [1.0] * 400 + [None] * 600  # 0.40 against a 0.998 baseline
        assert cov.read_feature(_rows(values), "pcr").degraded

    def test_normal_variation_is_not_caught(self) -> None:
        """0.95 against a 0.998 baseline is a quiet day, not a regression."""
        values = [1.0 + i * 0.001 for i in range(950)] + [None] * 50
        assert not cov.read_feature(_rows(values), "pcr").degraded

    def test_the_threshold_is_verdict_stable(self) -> None:
        """The chosen 0.80 sits inside a range where the verdicts do not move."""
        healthy = _rows([1.0 + i * 0.001 for i in range(950)] + [None] * 50)
        broken = _rows([None] * 1000)
        for factor in (0.70, 0.75, 0.80, 0.85, 0.90):
            cov.DEGRADED_FACTOR = factor
            assert not cov.read_feature(healthy, "pcr").degraded, factor
            assert cov.read_feature(broken, "pcr").degraded, factor
        cov.DEGRADED_FACTOR = 0.80


class TestAConstantFeedIsPresentButUseless:
    def test_a_pinned_value_is_flagged_even_at_full_coverage(self) -> None:
        r = cov.read_feature(_rows([0.9123456789] * 300), "pcr")
        assert r.rate == 1.0, "coverage alone says this day is perfect"
        assert r.constant, "but the feed carries no information at all"

    @pytest.mark.parametrize("residue", [0.0, 1e-17, 1e-15])
    def test_the_dispersion_floor_is_tolerance_based(self, residue: float) -> None:
        values = [0.9 + (residue if i % 2 else -residue) for i in range(300)]
        assert cov.read_feature(_rows(values), "pcr").constant

    def test_a_real_spread_is_not_constant(self) -> None:
        assert not cov.read_feature(_rows([0.8, 0.9, 1.1, 1.3]), "pcr").constant


class TestTheGuardCannotQuietlyStopGuarding:
    def test_every_baseline_feature_is_actually_read(self) -> None:
        """A feature in BASELINE that report() never reads would be unguarded."""
        import inspect

        source = inspect.getsource(cov.report)
        missing = [f for f in cov.BASELINE if f'"{f}"' not in source]
        assert not missing, f"in BASELINE but never read by report(): {missing}"

    def test_an_empty_day_does_not_pass_as_healthy(self) -> None:
        """Zero rows must not divide by zero into a clean bill of health."""
        r = cov.read_feature([], "pcr")
        assert r.rate == 0.0
        assert r.degraded
