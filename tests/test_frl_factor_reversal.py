"""HYP-004 factor tests — sector-relative 5d reversal, look-ahead boundary."""

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
import factors.reversal as reversal  # noqa: E402
import frl_ic  # noqa: E402
import frl_returns  # noqa: E402


class TestCompute:
    def test_sector_demeaning_removes_the_sector_level(self):
        panel = pd.DataFrame(
            [
                {"date": date(2026, 6, 1), "ticker": "T1", "sector": "Tech", "past_ret_5": 0.10},
                {"date": date(2026, 6, 1), "ticker": "T2", "sector": "Tech", "past_ret_5": 0.06},
                {"date": date(2026, 6, 1), "ticker": "H1", "sector": "Health", "past_ret_5": 0.00},
                {"date": date(2026, 6, 1), "ticker": "H2", "sector": "Health", "past_ret_5": -0.04},
            ]
        )
        values = reversal.compute(panel)
        assert values.tolist() == pytest.approx([0.02, -0.02, 0.02, -0.02])

    def test_demeaning_is_per_day_not_pooled(self):
        panel = pd.DataFrame(
            [
                {"date": date(2026, 6, 1), "ticker": "T1", "sector": "Tech", "past_ret_5": 0.10},
                {"date": date(2026, 6, 1), "ticker": "T2", "sector": "Tech", "past_ret_5": 0.00},
                {"date": date(2026, 6, 2), "ticker": "T1", "sector": "Tech", "past_ret_5": 0.50},
                {"date": date(2026, 6, 2), "ticker": "T2", "sector": "Tech", "past_ret_5": 0.40},
            ]
        )
        values = reversal.compute(panel)
        assert values.tolist() == pytest.approx([0.05, -0.05, 0.05, -0.05])

    def test_missing_input_column_is_a_clear_error(self):
        panel = pd.DataFrame([{"date": date(2026, 6, 1), "ticker": "T1", "sector": "Tech"}])
        with pytest.raises(KeyError, match="past_ret_5"):
            reversal.compute(panel)

    def test_nan_input_propagates_as_nan_not_zero(self):
        panel = pd.DataFrame(
            [
                {"date": date(2026, 6, 1), "ticker": "T1", "sector": "Tech", "past_ret_5": None},
                {"date": date(2026, 6, 1), "ticker": "T2", "sector": "Tech", "past_ret_5": 0.02},
            ]
        )
        values = reversal.compute(panel)
        assert pd.isna(values.iloc[0])


class TestSanityGate:
    def test_registered_factor_passes_its_own_sanity(self):
        result = fb.run_sanity(reversal.FACTOR)
        assert result.passed, result.line()
        assert result.observed_ic < 0, "reversal must produce a NEGATIVE IC"

    def test_declared_metadata_matches_the_hypothesis(self):
        assert reversal.FACTOR.hyp_id == "HYP-004"
        assert reversal.FACTOR.expected_sign == -1
        assert reversal.FACTOR.data_lane == "v1"

    def test_a_momentum_sign_error_would_fail_the_gate(self):
        """Guard the guard: flipping the sign must be caught, not tolerated."""
        flipped = fb.Factor(
            name="reversal_flipped_probe",
            hyp_id="HYP-004",
            data_lane="v1",
            expected_sign=-1,
            compute=lambda panel: -reversal.compute(panel),
            sanity_panel=reversal._sanity_panel,
        )
        assert fb.run_sanity(flipped).passed is False


class TestLookAheadBoundary:
    def test_factor_reads_no_forward_column(self):
        source = (Path(_RESEARCH_DIR) / "factors" / "reversal.py").read_text()
        code = "\n".join(line for line in source.splitlines() if not line.strip().startswith("#"))
        assert 'fwd_ret_5"]' not in code and "panel['fwd_ret" not in code

    def test_trailing_return_window_ends_at_t(self):
        closes = pd.DataFrame(
            {"AAA": [100.0, 110.0, 121.0]},
            index=[date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3)],
        )
        past = frl_returns.trailing_returns(closes, lookbacks=(1, 2))
        row = past[past.date == date(2026, 6, 3)].iloc[0]
        assert row["past_ret_1"] == pytest.approx(0.10)
        assert row["past_ret_2"] == pytest.approx(0.21)
        first = past[past.date == date(2026, 6, 1)].iloc[0]
        assert pd.isna(first["past_ret_1"])  # no history yet -> NaN, not 0

    def test_past_and_forward_returns_do_not_overlap(self):
        closes = pd.DataFrame(
            {"AAA": [100.0, 110.0, 121.0, 133.1]},
            index=[date(2026, 6, d) for d in (1, 2, 3, 4)],
        )
        past = frl_returns.trailing_returns(closes, lookbacks=(1,))
        fwd = frl_returns.forward_returns(closes, horizons=(1,))
        joined = past.merge(fwd, on=["date", "ticker"])
        day2 = joined[joined.date == date(2026, 6, 2)].iloc[0]
        assert day2["past_ret_1"] == pytest.approx(0.10)  # 6-01 -> 6-02
        assert day2["fwd_ret_1"] == pytest.approx(0.10)  # 6-02 -> 6-03, disjoint


class TestEndToEndOnSyntheticPanel:
    def test_known_reversal_yields_negative_ic(self):
        panel = reversal._sanity_panel()
        panel["_factor"] = reversal.compute(panel)
        ic = frl_ic.daily_ic(panel, "_factor", "fwd_ret_5", min_sector_n=3)
        assert ic.mean() == pytest.approx(-1.0)
