"""Unit tests for ifds.scoring.contradiction_signal."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from ifds.scoring.contradiction_signal import (
    CONSENSUS_OVERSHOOT_THRESHOLD,
    EARNINGS_BEAT_RATIO_THRESHOLD,
    RECENT_DOWNGRADES_THRESHOLD,
    compute_contradiction_signal,
)


# ---------------------------------------------------------------------------
# Clean data — no flags
# ---------------------------------------------------------------------------


class TestNoContradiction:

    def test_clean_data_yields_no_flag(self) -> None:
        """Price under consensus, all beats, no downgrades → no flag."""
        result = compute_contradiction_signal(
            price=100.0,
            target_consensus=110.0,
            target_high=120.0,
            earnings_history=[
                {"date": "2026-01-01", "epsActual": 1.0, "epsEstimated": 0.9},
                {"date": "2025-10-01", "epsActual": 0.95, "epsEstimated": 0.9},
                {"date": "2025-07-01", "epsActual": 1.10, "epsEstimated": 1.0},
                {"date": "2025-04-01", "epsActual": 0.85, "epsEstimated": 0.80},
            ],
            analyst_grades_recent=[],
        )
        assert result.is_contradicted is False
        assert result.reasons == ()

    def test_missing_data_returns_no_contradiction(self) -> None:
        """Defensive default — no FMP data, no flag."""
        result = compute_contradiction_signal(price=100.0)
        assert result.is_contradicted is False
        assert result.reasons == ()


# ---------------------------------------------------------------------------
# Earnings beat ratio
# ---------------------------------------------------------------------------


class TestEarningsBeatRatio:

    def test_one_of_four_beats_triggers(self) -> None:
        """1/4 beats (25%) < 50% threshold → flag."""
        result = compute_contradiction_signal(
            price=100.0,
            target_consensus=110.0,
            target_high=120.0,
            earnings_history=[
                {"date": "2026-01-01", "epsActual": 0.7, "epsEstimated": 0.9},
                {"date": "2025-10-01", "epsActual": 0.7, "epsEstimated": 0.9},
                {"date": "2025-07-01", "epsActual": 0.7, "epsEstimated": 0.9},
                {"date": "2025-04-01", "epsActual": 1.0, "epsEstimated": 0.9},
            ],
        )
        assert result.is_contradicted is True
        assert any("earnings_beats_below_half" in r for r in result.reasons)
        assert result.detail["earnings_beats"] == "1/4"

    def test_two_of_four_beats_does_not_trigger(self) -> None:
        """2/4 beats (50%) is NOT below the threshold (strict <)."""
        result = compute_contradiction_signal(
            price=100.0,
            earnings_history=[
                {"date": "2026-01-01", "epsActual": 1.0, "epsEstimated": 0.9},
                {"date": "2025-10-01", "epsActual": 1.0, "epsEstimated": 0.9},
                {"date": "2025-07-01", "epsActual": 0.7, "epsEstimated": 0.9},
                {"date": "2025-04-01", "epsActual": 0.7, "epsEstimated": 0.9},
            ],
        )
        assert result.is_contradicted is False

    def test_skips_quarters_missing_actuals(self) -> None:
        """Upcoming earnings (epsActual=None) are excluded from the ratio."""
        result = compute_contradiction_signal(
            price=100.0,
            earnings_history=[
                {"date": "2026-08-04", "epsActual": None, "epsEstimated": 1.5},
                {"date": "2026-04-30", "epsActual": 1.95, "epsEstimated": 1.98},
                {"date": "2026-02-17", "epsActual": 1.65, "epsEstimated": 1.54},
                {"date": "2025-10-30", "epsActual": 2.25, "epsEstimated": 2.11},
            ],
        )
        # 2 BEATs and 1 MISS (last 3 actuals) → 67% → not flagged
        assert result.is_contradicted is False
        assert result.detail["earnings_beats"] == "2/3"


# ---------------------------------------------------------------------------
# Price vs consensus target
# ---------------------------------------------------------------------------


class TestPriceVsConsensus:

    def test_price_above_consensus_2pct_triggers(self) -> None:
        """Price 2.5% above consensus → flag (CARG W17 case)."""
        result = compute_contradiction_signal(
            price=102.5,
            target_consensus=100.0,
            target_high=120.0,
        )
        assert result.is_contradicted is True
        assert any("price_above_consensus" in r for r in result.reasons)

    def test_price_just_at_threshold_does_not_trigger(self) -> None:
        """Strict > threshold — exactly 2.0% should not trigger."""
        result = compute_contradiction_signal(
            price=102.0,
            target_consensus=100.0,
            target_high=120.0,
        )
        # 2.0% / 100% = 0.02 == threshold (strict >, so no flag)
        assert result.is_contradicted is False


# ---------------------------------------------------------------------------
# Price vs analyst HIGH target
# ---------------------------------------------------------------------------


class TestPriceVsHighTarget:

    def test_price_above_analyst_high_triggers(self) -> None:
        """Price strictly above HIGH target → flag (GFS W17 case)."""
        result = compute_contradiction_signal(
            price=125.0,
            target_consensus=100.0,
            target_high=120.0,
        )
        assert result.is_contradicted is True
        assert "price_above_analyst_high" in result.reasons


# ---------------------------------------------------------------------------
# Recent downgrades
# ---------------------------------------------------------------------------


class TestRecentDowngrades:

    def test_two_recent_downgrades_triggers(self) -> None:
        """2 downgrades in last 30 days → flag (SKM W17 case)."""
        today = date(2026, 5, 1)
        result = compute_contradiction_signal(
            price=100.0,
            target_consensus=110.0,
            analyst_grades_recent=[
                {"date": (today - timedelta(days=1)).isoformat(),
                 "action": "downgraded"},
                {"date": (today - timedelta(days=7)).isoformat(),
                 "action": "down"},
            ],
            today=today,
        )
        assert result.is_contradicted is True
        assert any("recent_downgrades_2" in r for r in result.reasons)

    def test_old_downgrades_do_not_count(self) -> None:
        """Downgrades > 30 days outside the window are ignored."""
        today = date(2026, 5, 1)
        old = (today - timedelta(days=60)).isoformat()
        result = compute_contradiction_signal(
            price=100.0,
            analyst_grades_recent=[
                {"date": old, "action": "downgraded"},
                {"date": old, "action": "downgraded"},
            ],
            today=today,
        )
        assert result.is_contradicted is False

    def test_maintain_action_does_not_count(self) -> None:
        """Maintain/upgrade actions are not downgrades."""
        today = date(2026, 5, 1)
        result = compute_contradiction_signal(
            price=100.0,
            analyst_grades_recent=[
                {"date": today.isoformat(), "action": "maintain"},
                {"date": today.isoformat(), "action": "upgraded"},
                {"date": today.isoformat(), "action": "downgraded"},
            ],
            today=today,
        )
        # Only 1 downgrade → below threshold of 2
        assert result.is_contradicted is False


# ---------------------------------------------------------------------------
# Combined / detail
# ---------------------------------------------------------------------------


class TestCombinedAndDetail:

    def test_multiple_flags_combine_in_reasons(self) -> None:
        """Hitting consensus + high + earnings reports all reasons."""
        result = compute_contradiction_signal(
            price=125.0,
            target_consensus=100.0,
            target_high=120.0,
            earnings_history=[
                {"date": "2026-01-01", "epsActual": 0.7, "epsEstimated": 0.9},
            ],
        )
        assert result.is_contradicted is True
        # ≥2 flags: earnings + consensus + high
        assert len(result.reasons) >= 2

    def test_thresholds_recorded_in_detail(self) -> None:
        """Detail must always carry the thresholds dict for audit/replay."""
        result = compute_contradiction_signal(price=100.0)
        thresholds = result.detail["thresholds"]
        assert thresholds["consensus_overshoot"] == CONSENSUS_OVERSHOOT_THRESHOLD
        assert thresholds["earnings_beat_ratio"] == EARNINGS_BEAT_RATIO_THRESHOLD
        assert thresholds["recent_downgrades"] == RECENT_DOWNGRADES_THRESHOLD


# ---------------------------------------------------------------------------
# Immutability (frozen dataclass)
# ---------------------------------------------------------------------------


class TestImmutability:

    def test_result_is_frozen(self) -> None:
        result = compute_contradiction_signal(price=100.0)
        with pytest.raises(Exception):
            result.is_contradicted = True  # type: ignore[misc]
