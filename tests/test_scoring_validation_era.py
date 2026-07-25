"""Tests for the two biweekly-report flags raised in the 2026-07-24 review.

Flag #1 — sign-blind verdict: the §5 interpretation fired "Evidence of alpha" on
``abs(ex_r) > 0.1``, so a **negative** correlation (higher score -> lower excess,
i.e. the "high score paradox") was announced as alpha. It also used
signal-validity language that G3 forbids before Day 63.

Flag #2 — era pooling (G5): the report pooled legacy (02-09..05-15) and swing
(05-18..) trades into one correlation, mixing two different strategies.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "analysis" / "scoring_validation.py"


def _load():
    spec = importlib.util.spec_from_file_location("scoring_validation_era", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


sv = _load()


def _trade(date: str, score: float = 90.0, pnl_pct: float = 1.0):
    return sv.Trade(
        date=date,
        ticker="TEST",
        direction="LONG",
        entry_price=100.0,
        exit_price=101.0,
        exit_type="MOC",
        pnl=100.0,
        pnl_pct=pnl_pct,
        score=score,
        sector="Industrials",
    )


# ---------------------------------------------------------------------------
# Flag #2 — era classification (G5)
# ---------------------------------------------------------------------------


class TestEraClassification:
    def test_legacy_era_before_the_pivot(self):
        assert sv.classify_era("2026-02-09") == sv.ERA_LEGACY
        assert sv.classify_era("2026-05-15") == sv.ERA_LEGACY

    def test_swing_era_from_the_pivot(self):
        assert sv.classify_era("2026-05-18") == sv.ERA_SWING
        assert sv.classify_era("2026-07-24") == sv.ERA_SWING

    def test_gap_between_eras_is_not_silently_absorbed(self):
        """05-16/05-17 is the pivot weekend — must not be labelled either era."""
        assert sv.classify_era("2026-05-16") == sv.ERA_UNKNOWN

    def test_split_partitions_every_trade(self):
        trades = [_trade("2026-03-01"), _trade("2026-06-01"), _trade("2026-06-02")]
        buckets = sv.split_by_era(trades)
        assert len(buckets[sv.ERA_LEGACY]) == 1
        assert len(buckets[sv.ERA_SWING]) == 2
        assert sum(len(v) for v in buckets.values()) == len(trades)


# ---------------------------------------------------------------------------
# Flag #1 — sign-aware, G3-compliant verdict
# ---------------------------------------------------------------------------


class TestExcessVerdictSign:
    def test_negative_correlation_is_never_called_alpha(self):
        """The actual 2026-07-24 numbers: ex_r = -0.144."""
        verdict = sv.excess_verdict(raw_r=-0.108, ex_r=-0.144)
        assert "alpha" not in verdict.lower()
        assert "inverz" in verdict.lower() or "negatív" in verdict.lower()

    def test_positive_correlation_is_described_not_validated(self):
        verdict = sv.excess_verdict(raw_r=0.15, ex_r=0.20)
        # G3: descriptive only before Day 63 — no "evidence of alpha" claim
        assert "Evidence of alpha" not in verdict
        assert "pozitív" in verdict.lower()

    def test_correlation_vanishing_after_spy_removal_is_reported(self):
        verdict = sv.excess_verdict(raw_r=0.15, ex_r=0.01)
        assert "SPY" in verdict

    def test_weak_both_ways_is_inconclusive(self):
        verdict = sv.excess_verdict(raw_r=0.01, ex_r=0.01)
        assert "inconclusive" in verdict.lower() or "nincs" in verdict.lower()

    def test_nan_inputs_do_not_crash(self):
        assert sv.excess_verdict(raw_r=float("nan"), ex_r=float("nan")) == ""


class TestG3Language:
    def test_no_forbidden_signal_validity_words_in_any_verdict(self):
        forbidden = ("evidence of alpha", "validál", "bizonyít", "igazolt", "edge megerősítve")
        cases = [(-0.108, -0.144), (0.15, 0.20), (0.15, 0.01), (0.01, 0.01)]
        for raw_r, ex_r in cases:
            verdict = sv.excess_verdict(raw_r=raw_r, ex_r=ex_r).lower()
            for word in forbidden:
                assert word not in verdict, f"G3 violation: '{word}' in verdict for {ex_r}"
