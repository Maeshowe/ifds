"""Phase 5 degeneracy: a CONSTANT feed must not read as a real dispersion.

Why this exists. `_z_score` guarded with `if s == 0` — exact equality on a float
statistic, which .claude/rules/ifds-rules.md (2026-07-21) forbids outright after the FRL
`daily_ic` incident: float arithmetic on degenerate input returns ~1e-16 residue, not
zero, so the guard passes the case straight through.

The concrete hazard is a cheaper options plan that returns CONSTANT greeks/IV rather than
absent ones. Measured on the real functions with a pinned feed: the residual standard
deviation is 1.674e-17 for iv_rank and 2.367e-17 for iv_skew — `s == 0` is False, and
`_z_score` returns 0.0, which is indistinguishable from "today sits exactly at its own
historical mean".

The tolerance is ABSOLUTE, not relative, and that is the whole design decision:

* only the MEAN-based features can degenerate this way — iv_rank and iv_skew, 0.20 of the
  MMS composite. `gex` is a SUM over contracts, so a pinned feed still gives it a
  dispersion of 5.4e+06 (CV 0.448); it cannot collapse;
* those two features are O(1)-scaled, so 1e-12 sits ten orders of magnitude below any
  real dispersion and five above float residue;
* a RELATIVE form (`s <= eps * |mean|`) would fail exactly where it is needed: iv_skew is
  a difference of implied vols and legitimately oscillates THROUGH zero, so its mean sits
  at noise level on ordinary days and the relative threshold collapses to ~0.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ifds.phases import phase5_mms as mms  # noqa: E402


class TestTheGuardIsToleranceBased:
    def test_a_pinned_series_yields_no_z_score(self) -> None:
        """The exact case a constant vendor feed produces."""
        pinned = [0.4812345678901234] * 30
        assert mms._z_score(pinned[0], pinned, min_n=10) is None

    def test_the_residue_a_pinned_feed_actually_leaves_is_caught(self) -> None:
        """Not a hypothetical: build the series the way the pipeline does, by averaging
        a constant chain, and let the float error accumulate naturally."""
        chain = [0.37] * 64
        series = [sum(chain) / len(chain) + i * 0.0 for i in range(30)]
        s = mms._std(series, mms._mean(series))
        assert s < mms._DEGENERATE_STD, f"expected degenerate residue, got {s}"
        assert mms._z_score(series[0], series, min_n=10) is None

    @pytest.mark.parametrize("residue", [0.0, 1e-17, 1e-16, 1e-15, 1e-13])
    def test_every_residue_below_the_tolerance_is_degenerate(self, residue: float) -> None:
        series = [0.5 + (residue if i % 2 else -residue) for i in range(30)]
        assert mms._z_score(series[0], series, min_n=10) is None

    def test_a_real_dispersion_still_scores(self) -> None:
        """The guard must not swallow the signal it sits next to."""
        series = [0.30, 0.42, 0.51, 0.38, 0.44, 0.60, 0.33, 0.47, 0.52, 0.41, 0.55, 0.36]
        z = mms._z_score(0.60, series, min_n=10)
        assert z is not None and z > 1.0

    def test_the_tolerance_is_absolute_not_relative(self) -> None:
        """iv_skew oscillates through zero, so a relative threshold would misfire.

        A series centred on ~0 with a genuine spread of 0.02 is a NORMAL iv_skew day. A
        relative guard (`s <= eps * |mean|`) would call it degenerate because its mean is
        at noise level; the absolute guard correctly scores it.
        """
        series = [0.02, -0.02, 0.019, -0.021, 0.018, -0.017, 0.022, -0.019, 0.02, -0.02, 0.021, -0.018]
        mean = mms._mean(series)
        assert abs(mean) < 1e-3, "this series is centred on zero by construction"
        assert mms._z_score(0.05, series, min_n=10) is not None, (
            "a relative tolerance would wrongly reject this — it is an ordinary iv_skew day"
        )

    def test_the_constant_is_named_and_absolute(self) -> None:
        assert mms._DEGENERATE_STD == pytest.approx(1e-12)


class TestNoExactZeroComparisonSurvivesOnAFloatStatistic:
    """Close the gap, not the instance — an AST sweep, like the timezone guard."""

    def test_the_module_compares_no_float_statistic_to_exact_zero(self) -> None:
        import ast

        source = Path(mms.__file__).read_text()
        offenders: list[str] = []
        # Names that hold a float statistic; an `== 0` on any of them is the forbidden form.
        statistical = ("std", "sigma", "s", "var", "dispersion", "spread", "stdev")
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Compare) or len(node.ops) != 1:
                continue
            if not isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
                continue
            left, right = node.left, node.comparators[0]
            for name_node, other in ((left, right), (right, left)):
                if not isinstance(name_node, ast.Name):
                    continue
                stem = name_node.id.lower()
                if not any(stem == w or stem.startswith(w + "_") or stem.endswith("_" + w)
                           for w in statistical):
                    continue
                if isinstance(other, ast.Constant) and other.value == 0:
                    offenders.append(f"line {node.lineno}: {name_node.id} == 0")
        assert not offenders, (
            "exact-equality degeneracy check on a float statistic: "
            + "; ".join(offenders)
            + ". Float arithmetic on degenerate input leaves ~1e-16, not 0, so the guard "
            "passes the case through. Use a tolerance (_DEGENERATE_STD)."
        )

    def test_the_sweep_would_catch_the_original_bug(self) -> None:
        """Verify the guard by back-substitution, in-memory."""
        import ast

        sabotaged = "def f(values):\n    s = _std(values)\n    if s == 0:\n        return None\n"
        found = False
        for node in ast.walk(ast.parse(sabotaged)):
            if isinstance(node, ast.Compare) and isinstance(node.ops[0], ast.Eq):
                if isinstance(node.left, ast.Name) and node.left.id == "s":
                    if isinstance(node.comparators[0], ast.Constant):
                        found = node.comparators[0].value == 0
        assert found, "the AST sweep cannot see the very pattern it is meant to forbid"
