"""Universe regimes and the D-U3 rule: a new attempt uses ONE regime only.

Why. The swing era ran on three different universe definitions and nothing recorded
it, so nine weeks of a silently substituted population went unnoticed. G5 forbids
pooling across eras; this was the same hazard INSIDE one era.

Tamás's decision (2026-10-20) was the strict option of two: a new attempt may draw
only on regime-3 data (`index_union_plus_liquidity_floor`, the first deterministic
one). The alternative — permit mixtures with a declared blend ratio — is weaker,
because an attempt spanning regimes is not comparable to one that does not, whatever
ratio is reported.

The price is deliberate and was measured before the rule was written: T_eff = n_days/h
must reach 6.0 and the forward return consumes h more sessions, so h=5 becomes testable
on 2026-12-08 and h=10 on 2027-01-29. Until then a failing attempt PARKs on power, it
does not KILL.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "research"))

import frl_config as cfg  # noqa: E402

REGIME_1 = cfg.UNIVERSE_REGIME_INTERSECT
REGIME_2 = cfg.UNIVERSE_REGIME_SCREENER
REGIME_3 = cfg.UNIVERSE_REGIME_FLOOR


class TestRegimeBoundaries:
    @pytest.mark.parametrize(
        "day,expected",
        [
            (date(2026, 5, 18), REGIME_1),   # swing era opens on the intersection
            (date(2026, 8, 14), REGIME_1),   # last day before the silent fallback
            (date(2026, 8, 16), REGIME_2),   # the membership source had died on 08-12
            (date(2026, 10, 19), REGIME_2),  # last degraded day
            (date(2026, 10, 20), REGIME_3),  # the floor goes live
            (date(2027, 1, 1), REGIME_3),    # open-ended
        ],
    )
    def test_the_three_boundaries(self, day, expected):
        assert cfg.universe_regime_of(day) == expected

    def test_before_the_era_is_None_not_a_guess(self):
        """A caller must not be able to treat pre-era data as the current regime."""
        assert cfg.universe_regime_of(date(2026, 5, 17)) is None
        assert cfg.universe_regime_of(date(2026, 2, 11)) is None

    def test_the_current_regime_is_a_named_constant_not_a_derived_value(self):
        """Same reasoning as DAY63_GATE_PASSED: a computed "latest" would silently
        follow a future regime change nobody approved."""
        assert cfg.CURRENT_UNIVERSE_REGIME == REGIME_3
        assert cfg.regime_start(cfg.CURRENT_UNIVERSE_REGIME) == date(2026, 10, 20)

    def test_an_unknown_regime_name_has_no_start(self):
        assert cfg.regime_start("not_a_regime") is None

    def test_the_regimes_are_sorted_and_distinct(self):
        starts = [start for start, _ in cfg.UNIVERSE_REGIMES]
        labels = [label for _, label in cfg.UNIVERSE_REGIMES]
        assert starts == sorted(starts)
        assert len(set(labels)) == len(labels)


class TestRegimeSpan:
    def test_it_reports_a_blend(self):
        span = cfg.regime_span([date(2026, 6, 1), date(2026, 9, 1), date(2026, 10, 21)])
        assert span == {REGIME_1: 1, REGIME_2: 1, REGIME_3: 1}

    def test_a_clean_panel_still_reports_its_single_regime(self):
        """"I checked and it was clean" must not look like "nobody checked"."""
        span = cfg.regime_span([date(2026, 10, 20), date(2026, 10, 21)])
        assert span == {REGIME_3: 2}

    def test_pre_era_days_are_labelled_not_dropped(self):
        span = cfg.regime_span([date(2026, 3, 1), date(2026, 10, 21)])
        assert span == {"pre_era": 1, REGIME_3: 1}

    def test_an_empty_panel_is_an_empty_span(self):
        assert cfg.regime_span([]) == {}


class TestTheBatchNarrowsToTheCurrentRegime:
    def test_the_swing_panel_starts_at_the_regime_not_at_the_era(self, monkeypatch):
        """The D-U3 rule, enforced where the panel is built.

        Narrowed rather than refused: narrowing implements the decision literally and
        keeps the engine producing honest, power-gated results, where refusing would
        produce nothing at all.
        """
        import run_frl_batch

        seen: list[tuple] = []

        class _Panel:
            days = [date(2026, 10, 20)]
            missing_days: list = []
            unexpected_missing: list = []
            anomalies: dict = {}

        def _spy(start, end):
            seen.append((start, end))
            return _Panel()

        monkeypatch.setattr(run_frl_batch.loader, "load_panel", _spy)
        windows = type("W", (), {"dev_end": date(2026, 10, 31)})()
        run_frl_batch._era_panels(windows)

        legacy_call, swing_call = seen
        assert legacy_call[0] == cfg.LEGACY_START, "the legacy era is untouched"
        assert swing_call[0] == date(2026, 10, 20), (
            "the swing panel must start at the current regime, not at SWING_START — "
            "otherwise the attempt mixes three universe definitions"
        )
        assert swing_call[0] > cfg.SWING_START

    def test_the_price_of_the_rule_is_recorded_where_the_rule_is(self):
        """The adequacy dates are in the config comment so they cannot be lost.

        Measured against the NYSE calendar, MIN_ADEQUATE_T_EFF and the h-session
        forward-return cost — not estimated.
        """
        source = (
            Path(__file__).resolve().parent.parent / "scripts" / "research" / "frl_config.py"
        ).read_text()
        assert "2026-12-08" in source, "the h=5 adequacy date must stay in the record"
        assert "2027-01-29" in source, "the h=10 adequacy date must stay in the record"
