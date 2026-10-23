"""Scoring eras: a score-definition change is a panel boundary, like a universe change.

D-U3 closed the UNIVERSE axis — a new attempt may draw only on regime-3 days, because a
silently substituted population is not comparable to the one before it. The 2026-10-23
schema fixes opened the same hazard on the MEASUREMENT axis, and the registry below
closes it the same way.

Three of the four fixes move ``Total_Score``, the column ``frl_loader`` maps to ``score``
and the HYP-005 factor consumes:

* the breadth term stopped being charged to every ticker in its sector on the weekday
  reload (``score_adjustment - breadth_score_adj`` had been subtracting 0). Measured on
  the live Phase 1-3 context: 9 of 11 sectors carry a non-zero breadth term, -5 to -15,
  and 828 of 1535 scored rows (53.9%) sit in an affected sector;
* four of six fundamental branches started firing for the first time
  (roe / net_margin / debt_equity / interest_coverage were null in 0 of 16,425
  ticker-days before, because the scorer read legacy v3 field names);
* institutional ownership stopped being a constant zero.

None of that is reversible by re-reading the stored panel: the scan matrix records the
score, not its inputs. So the boundary has to be declared, not reconstructed.

The timing is the cheapest it will ever be. Regime 3 opened on 2026-10-20, so the panel
being invalidated is THREE trading days long. The same break in December would cost
seven weeks and push h=5 past its adequacy date.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "research"))

import frl_config as cfg  # noqa: E402


class TestTheRegistry:
    def test_the_current_era_is_a_named_constant_not_a_derived_value(self) -> None:
        """Same reason as CURRENT_UNIVERSE_REGIME: a computed "latest" would follow a
        future scoring change nobody approved."""
        assert cfg.CURRENT_SCORING_ERA == cfg.SCORING_ERA_SCHEMA_FIXED
        assert cfg.scoring_era_start(cfg.CURRENT_SCORING_ERA) == date(2026, 10, 23)

    @pytest.mark.parametrize(
        "day,expected",
        [
            (date(2026, 5, 18), cfg.SCORING_ERA_LEGACY_SCHEMA),
            (date(2026, 10, 22), cfg.SCORING_ERA_LEGACY_SCHEMA),  # last broken day
            (date(2026, 10, 23), cfg.SCORING_ERA_SCHEMA_FIXED),   # the fixes land
            (date(2027, 6, 1), cfg.SCORING_ERA_SCHEMA_FIXED),
        ],
    )
    def test_the_boundary(self, day, expected) -> None:
        assert cfg.scoring_era_of(day) == expected

    def test_before_the_swing_era_there_is_no_scoring_era(self) -> None:
        assert cfg.scoring_era_of(date(2026, 2, 11)) is None

    def test_an_unknown_era_has_no_start(self) -> None:
        assert cfg.scoring_era_start("not_an_era") is None

    def test_the_eras_are_sorted_and_distinct(self) -> None:
        starts = [s for s, _ in cfg.SCORING_ERAS]
        labels = [label for _, label in cfg.SCORING_ERAS]
        assert starts == sorted(starts)
        assert len(set(labels)) == len(labels)


class TestTheBatchHonoursBothAxes:
    def test_the_swing_panel_starts_at_the_LATER_of_the_two_boundaries(self, monkeypatch):
        """Universe regime and scoring era are independent constraints; the panel has to
        satisfy both, so the start is the max — not whichever was declared last."""
        import run_frl_batch

        seen: list[tuple] = []

        class _Panel:
            days = [date(2026, 10, 23)]
            missing_days: list = []
            unexpected_missing: list = []
            anomalies: dict = {}

        def _spy(start, end):
            seen.append((start, end))
            return _Panel()

        monkeypatch.setattr(run_frl_batch.loader, "load_panel", _spy)
        run_frl_batch._era_panels(type("W", (), {"dev_end": date(2026, 10, 31)})())

        legacy_call, swing_call = seen
        assert legacy_call[0] == cfg.LEGACY_START, "the legacy era stays untouched"
        assert swing_call[0] == date(2026, 10, 23), (
            "the swing panel must start at the scoring-era boundary (2026-10-23), which "
            "is later than the universe-regime boundary (2026-10-20) — otherwise the "
            "attempt pools three days scored on a broken fundamental schema with days "
            "scored on a fixed one"
        )
        assert swing_call[0] >= cfg.regime_start(cfg.CURRENT_UNIVERSE_REGIME)

    def test_the_price_of_the_boundary_is_written_down_where_the_boundary_is(self) -> None:
        """Three days lost, and the adequacy dates move with them. In the config, so the
        next person reads the cost at the same moment as the rule."""
        source = (
            Path(__file__).resolve().parent.parent / "scripts" / "research" / "frl_config.py"
        ).read_text()
        assert "2026-12-11" in source, "the recomputed h=5 adequacy date must be recorded"
        assert "2027-02-03" in source, "the recomputed h=10 adequacy date must be recorded"
