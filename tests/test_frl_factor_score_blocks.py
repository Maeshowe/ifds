"""HYP-006/007/008 — the S_j block decomposition factors.

Pre-registration: docs/planning/2026-10-04-component-decomposition-preregistration.md

The aggregate S_j is a KILLed null on all four horizons (A-0005..A-0010). That
cannot distinguish "no component has signal" from "the components cancel", so
each weighted block is registered as its own hypothesis.

The single most important thing these tests pin is the ``Total_Score != 0``
filter (pre-reg §4.1): in unscored rows the Flow and Funda columns sit at their
DEFAULT 50, which would inject a 43% constant mass into the daily ranking — the
mirror image of the dp_pct structural-zero bug.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

_RESEARCH_DIR = str(Path(__file__).resolve().parents[1] / "scripts" / "research")
if _RESEARCH_DIR not in sys.path:
    sys.path.insert(0, _RESEARCH_DIR)

import factors.base as fb  # noqa: E402
import factors.score_blocks as blocks  # noqa: E402
import frl_config as cfg  # noqa: E402

#: The Factor objects are taken from the MODULE, not from the registry: other
#: FRL test modules call ``fb.clear_registry()`` in an autouse fixture, so a
#: registry lookup here passes in isolation and fails in the full suite. The
#: sj_live tests use the same module-object pattern for the same reason.
BLOCKS = (
    (blocks.FLOW, "HYP-006", "flow_score"),
    (blocks.FUNDA, "HYP-007", "funda_score"),
    (blocks.TECH, "HYP-008", "tech_score"),
)
BLOCK_IDS = [f.name for f, _, _ in BLOCKS]


@pytest.fixture
def registry():
    """A registry that definitely holds the three blocks, whoever cleared it."""
    for factor in (blocks.FLOW, blocks.FUNDA, blocks.TECH):
        try:
            fb.register(factor)
        except ValueError:
            pass  # already registered — fine either way
    return fb


def _row(day, ticker, column, value, score=42.0, era=cfg.ERA_SWING):
    base = {
        "date": day,
        "ticker": ticker,
        "sector": "Tech",
        "era": era,
        "score": score,
        "flow_score": 50.0,
        "funda_score": 50.0,
        "tech_score": 30.0,
        "fwd_ret_5": 0.0,
    }
    base[column] = value
    return base


# ---------------------------------------------------------------------------
# Registration — pinned to the pre-registration
# ---------------------------------------------------------------------------


class TestRegistration:
    @pytest.mark.parametrize("factor,hyp_id,_col", BLOCKS, ids=BLOCK_IDS)
    def test_each_block_is_registered_under_its_own_hypothesis(self, factor, hyp_id, _col, registry):
        assert registry.get(factor.name) is factor
        assert factor.hyp_id == hyp_id
        assert factor.data_lane == "v1"

    @pytest.mark.parametrize("factor,_hyp,_col", BLOCKS, ids=BLOCK_IDS)
    def test_expected_sign_is_positive_as_registered(self, factor, _hyp, _col):
        """All three mechanisms predict a POSITIVE IC (pre-reg §5)."""
        assert factor.expected_sign == 1

    def test_exactly_three_blocks_are_registered(self, registry):
        """Guard against silent post-hoc component expansion (pre-reg §3)."""
        registered = {f.name for f in registry.all_factors() if f.hyp_id in
                      {"HYP-006", "HYP-007", "HYP-008"}}
        assert registered == {"flow_block", "funda_block", "tech_block"}


# ---------------------------------------------------------------------------
# The Total_Score != 0 filter — pre-reg §4.1, the structural-default trap
# ---------------------------------------------------------------------------


class TestScoredFilter:
    @pytest.mark.parametrize("factor,_hyp,column", BLOCKS, ids=BLOCK_IDS)
    def test_unscored_rows_are_masked_to_nan(self, factor, _hyp, column):
        """Total_Score == 0 means the row was never scored.

        Flow and Funda then sit at their DEFAULT 50 (verified on 36,557 real
        rows). Including them would inject a constant mass into the ranking.
        """
        day = date(2026, 6, 1)
        panel = pd.DataFrame([
            _row(day, "A", column, 70.0, score=42.0),
            _row(day, "B", column, 50.0, score=0.0),  # unscored -> default block value
        ])
        out = factor.compute(panel)
        assert out.iloc[0] == pytest.approx(70.0)
        assert pd.isna(out.iloc[1])

    @pytest.mark.parametrize("factor,_hyp,column", BLOCKS, ids=BLOCK_IDS)
    def test_the_filter_is_tolerance_based_not_exact_equality(self, factor, _hyp, column):
        """ifds-rules: degeneracy checks never use ``== 0``.

        A float residue of ~1e-16 must still count as unscored; a genuinely
        small-but-real score must not be dropped.
        """
        day = date(2026, 6, 1)
        panel = pd.DataFrame([
            _row(day, "A", column, 70.0, score=1e-16),  # float residue -> unscored
            _row(day, "B", column, 60.0, score=-0.5),  # real negative score -> kept
        ])
        out = factor.compute(panel)
        assert pd.isna(out.iloc[0])
        assert out.iloc[1] == pytest.approx(60.0)

    @pytest.mark.parametrize("factor,_hyp,column", BLOCKS, ids=BLOCK_IDS)
    def test_a_missing_score_is_treated_as_unscored(self, factor, _hyp, column):
        day = date(2026, 6, 1)
        panel = pd.DataFrame([_row(day, "A", column, 70.0, score=float("nan"))])
        assert pd.isna(factor.compute(panel).iloc[0])


# ---------------------------------------------------------------------------
# Era guard
# ---------------------------------------------------------------------------


class TestEraGuard:
    @pytest.mark.parametrize("factor,_hyp,column", BLOCKS, ids=BLOCK_IDS)
    def test_legacy_rows_are_masked(self, factor, _hyp, column):
        """The legacy Total_Score is a different formula on an incompatible scale."""
        day = date(2026, 3, 2)
        panel = pd.DataFrame([
            _row(day, "A", column, 70.0, era=cfg.ERA_LEGACY),
            _row(date(2026, 6, 1), "B", column, 60.0, era=cfg.ERA_SWING),
        ])
        out = factor.compute(panel)
        assert pd.isna(out.iloc[0])
        assert out.iloc[1] == pytest.approx(60.0)


# ---------------------------------------------------------------------------
# Fail loud
# ---------------------------------------------------------------------------


class TestFailLoud:
    @pytest.mark.parametrize("factor,_hyp,column", BLOCKS, ids=BLOCK_IDS)
    def test_a_missing_block_column_raises(self, factor, _hyp, column):
        day = date(2026, 6, 1)
        panel = pd.DataFrame([_row(day, "A", column, 70.0)]).drop(columns=[column])
        with pytest.raises(KeyError, match=column):
            factor.compute(panel)

    @pytest.mark.parametrize("factor,_hyp,column", BLOCKS, ids=BLOCK_IDS)
    def test_a_missing_score_column_raises(self, factor, _hyp, column):
        """Without Total_Score the §4.1 filter cannot be applied — never proceed."""
        day = date(2026, 6, 1)
        panel = pd.DataFrame([_row(day, "A", column, 70.0)]).drop(columns=["score"])
        with pytest.raises(KeyError, match="score"):
            factor.compute(panel)

    @pytest.mark.parametrize("factor,_hyp,column", BLOCKS, ids=BLOCK_IDS)
    def test_a_missing_era_column_raises(self, factor, _hyp, column):
        day = date(2026, 6, 1)
        panel = pd.DataFrame([_row(day, "A", column, 70.0)]).drop(columns=["era"])
        with pytest.raises(KeyError, match="era"):
            factor.compute(panel)


# ---------------------------------------------------------------------------
# The sanity contract must not pass vacuously
# ---------------------------------------------------------------------------


class TestSanityIsNotVacuous:
    @pytest.mark.parametrize("factor,_hyp,_col", BLOCKS, ids=BLOCK_IDS)
    def test_the_sanity_panel_survives_both_masks(self, factor, _hyp, _col):
        """A panel masked to all-NaN would make sanity() pass on an empty series.

        That is the trap the sj_live docstring warns about: the synthetic panel
        must be swing-era AND carry a non-zero Total_Score, or the check proves
        nothing.
        """
        out = factor.compute(factor.sanity_panel())
        assert out.notna().sum() >= 20, "sanity panel is masked away — vacuous check"

    @pytest.mark.parametrize("factor,_hyp,_col", BLOCKS, ids=BLOCK_IDS)
    def test_sanity_detects_the_registered_relation(self, factor, _hyp, _col):
        result = fb.run_sanity(factor)
        assert result.passed, result.line()
