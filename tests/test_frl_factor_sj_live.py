"""HYP-005 factor tests — S_j live aggregate, swing-only era guard."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

_RESEARCH_DIR = str(Path(__file__).resolve().parents[1] / "scripts" / "research")
if _RESEARCH_DIR not in sys.path:
    sys.path.insert(0, _RESEARCH_DIR)

import factors.base as fb  # noqa: E402
import factors.sj_live as sj  # noqa: E402
import frl_config as cfg  # noqa: E402
import frl_ic  # noqa: E402


def _panel(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


class TestCompute:
    def test_returns_the_live_score_column(self):
        panel = _panel(
            [
                {
                    "date": date(2026, 6, 1),
                    "ticker": "AAA",
                    "sector": "Tech",
                    "era": cfg.ERA_SWING,
                    "score": 61.42,
                },
                {
                    "date": date(2026, 6, 1),
                    "ticker": "BBB",
                    "sector": "Tech",
                    "era": cfg.ERA_SWING,
                    "score": -12.30,
                },
            ]
        )
        assert sj.compute(panel).tolist() == [61.42, -12.30]

    def test_unscored_rows_stay_nan(self):
        """The loader already nulls them; the factor must not resurrect a 0.0."""
        panel = _panel(
            [
                {
                    "date": date(2026, 6, 1),
                    "ticker": "AAA",
                    "sector": "Tech",
                    "era": cfg.ERA_SWING,
                    "score": 61.42,
                },
                {
                    "date": date(2026, 6, 1),
                    "ticker": "CCC",
                    "sector": "Tech",
                    "era": cfg.ERA_SWING,
                    "score": float("nan"),
                },
            ]
        )
        values = sj.compute(panel)
        assert values.iloc[0] == 61.42
        assert pd.isna(values.iloc[1])

    def test_missing_score_column_is_a_clear_error(self):
        panel = _panel(
            [{"date": date(2026, 6, 1), "ticker": "AAA", "sector": "Tech", "era": cfg.ERA_SWING}]
        )
        with pytest.raises(KeyError, match="score"):
            sj.compute(panel)


class TestSwingOnlyEraGuard:
    """Pre-reg: legacy Total_Score is a different formula — it must never mix in."""

    def test_legacy_rows_are_dropped_to_nan(self):
        panel = _panel(
            [
                {
                    "date": date(2026, 4, 1),
                    "ticker": "AAA",
                    "sector": "Tech",
                    "era": cfg.ERA_LEGACY,
                    "score": 82.0,
                },
                {
                    "date": date(2026, 6, 1),
                    "ticker": "AAA",
                    "sector": "Tech",
                    "era": cfg.ERA_SWING,
                    "score": 61.42,
                },
            ]
        )
        values = sj.compute(panel)
        assert pd.isna(values.iloc[0]), "legacy composite must not enter the S_j factor"
        assert values.iloc[1] == 61.42

    def test_a_pure_legacy_panel_yields_no_usable_factor(self):
        panel = _panel(
            [
                {
                    "date": date(2026, 4, 1),
                    "ticker": t,
                    "sector": "Tech",
                    "era": cfg.ERA_LEGACY,
                    "score": s,
                }
                for t, s in (("AAA", 82.0), ("BBB", 71.0), ("CCC", 90.0))
            ]
        )
        assert sj.compute(panel).isna().all()

    def test_missing_era_column_is_a_clear_error(self):
        panel = _panel(
            [{"date": date(2026, 6, 1), "ticker": "AAA", "sector": "Tech", "score": 61.42}]
        )
        with pytest.raises(KeyError, match="era"):
            sj.compute(panel)


class TestSanityGate:
    def test_registered_factor_passes_its_own_sanity(self):
        result = fb.run_sanity(sj.FACTOR)
        assert result.passed, result.line()
        assert result.observed_ic > 0, "S_j is registered with a POSITIVE expected sign"

    def test_declared_metadata_matches_the_hypothesis(self):
        assert sj.FACTOR.hyp_id == "HYP-005"
        assert sj.FACTOR.expected_sign == 1
        assert sj.FACTOR.data_lane == "v1"

    def test_sanity_panel_is_swing_era_only(self):
        """A legacy-era sanity panel would silently test nothing (all NaN)."""
        panel = sj.FACTOR.sanity_panel()
        assert set(panel["era"].unique()) == {cfg.ERA_SWING}

    def test_a_sign_error_would_fail_the_gate(self):
        flipped = fb.Factor(
            name="sj_flipped_probe",
            hyp_id="HYP-005",
            data_lane="v1",
            expected_sign=1,
            compute=lambda panel: -sj.compute(panel),
            sanity_panel=sj.FACTOR.sanity_panel,
        )
        assert fb.run_sanity(flipped).passed is False


class TestEndToEnd:
    def test_known_positive_relation_yields_positive_ic(self):
        panel = sj.FACTOR.sanity_panel()
        panel["_factor"] = sj.compute(panel)
        ic = frl_ic.daily_ic(panel, "_factor", "fwd_ret_5", min_sector_n=3)
        assert ic.mean() == pytest.approx(1.0)

    def test_factor_reads_no_forward_column(self):
        source = (Path(_RESEARCH_DIR) / "factors" / "sj_live.py").read_text()
        code = "\n".join(ln for ln in source.splitlines() if not ln.strip().startswith("#"))
        assert (
            "fwd_ret" not in code.split("def _sanity_panel")[0]
        ), "compute() must never touch a forward-return column"
