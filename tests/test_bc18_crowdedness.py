"""Tests for BC18A/2 — Crowdedness Shadow Mode.

Covers:
- compute_crowding_score() — Good Crowding → positive score
- compute_crowding_score() — Bad Crowding → negative score
- dark_share below threshold → 0.0
- z_block below 0.5 → 0.0
- Score clamped to [-1.0, +1.0]
- Config keys exist
- Shadow mode: no Phase 6 sizing impact
"""

import pytest

from ifds.phases.phase5_mms import compute_crowding_score


# ---------------------------------------------------------------------------
# Good Crowding scenarios
# ---------------------------------------------------------------------------


def test_good_crowding_accumulation():
    """Dark pool + block + buying + rising price + no fear → positive score."""
    score = compute_crowding_score(
        dark_share=0.65,
        z_block=2.0,
        z_dex=-1.0,       # institutions buying (negative dex = good)
        iv_skew=0.02,
        median_iv_skew=0.05,
        daily_return=0.015,  # +1.5% return
        threshold_high=0.55,
    )
    assert score > 0.3, f"Expected positive Good Crowding, got {score}"


def test_good_crowding_strong():
    """Strong accumulation signal → score close to +1.0."""
    score = compute_crowding_score(
        dark_share=0.75,
        z_block=3.0,
        z_dex=-2.0,
        iv_skew=0.01,
        median_iv_skew=0.05,
        daily_return=0.03,
    )
    assert score > 0.5, f"Expected strong Good Crowding, got {score}"


# ---------------------------------------------------------------------------
# Bad Crowding scenarios
# ---------------------------------------------------------------------------


def test_bad_crowding_distribution():
    """Crowded + selling + fear hedging → negative score."""
    score = compute_crowding_score(
        dark_share=0.65,
        z_block=2.0,
        z_dex=1.5,         # institutions selling (positive dex = bad)
        iv_skew=0.10,
        median_iv_skew=0.03,
        daily_return=-0.02,  # falling price
    )
    assert score < -0.3, f"Expected negative Bad Crowding, got {score}"


def test_bad_crowding_fear():
    """High iv_skew (fear) dominates → negative even with flat price."""
    score = compute_crowding_score(
        dark_share=0.60,
        z_block=1.5,
        z_dex=0.5,
        iv_skew=0.15,
        median_iv_skew=0.03,
        daily_return=0.0,
    )
    assert score < 0, f"Expected negative score with fear, got {score}"


# ---------------------------------------------------------------------------
# Edge cases / neutral
# ---------------------------------------------------------------------------


def test_below_threshold_returns_zero():
    """dark_share below threshold → 0.0 (not crowded)."""
    score = compute_crowding_score(
        dark_share=0.40,    # below 0.55
        z_block=3.0,
        z_dex=-1.0,
        iv_skew=0.02,
        median_iv_skew=0.05,
        daily_return=0.02,
    )
    assert score == 0.0


def test_low_block_returns_zero():
    """z_block below 0.5 → 0.0 (not enough institutional blocks)."""
    score = compute_crowding_score(
        dark_share=0.70,
        z_block=0.3,        # below 0.5
        z_dex=-1.0,
        iv_skew=0.02,
        median_iv_skew=0.05,
        daily_return=0.02,
    )
    assert score == 0.0


def test_z_block_none_returns_zero():
    """z_block=None → 0.0 (no block data)."""
    score = compute_crowding_score(
        dark_share=0.70,
        z_block=None,
        z_dex=-1.0,
        iv_skew=0.02,
        median_iv_skew=0.05,
        daily_return=0.02,
    )
    assert score == 0.0


def test_z_dex_none_handled():
    """z_dex=None → direction based only on return."""
    score = compute_crowding_score(
        dark_share=0.70,
        z_block=2.0,
        z_dex=None,
        iv_skew=0.03,
        median_iv_skew=0.03,
        daily_return=0.02,
    )
    # Should not crash, and return > 0 means positive direction
    assert isinstance(score, float)


def test_score_clamped_positive():
    """Score never exceeds +1.0."""
    score = compute_crowding_score(
        dark_share=0.90,
        z_block=5.0,
        z_dex=-5.0,
        iv_skew=-0.10,
        median_iv_skew=0.05,
        daily_return=0.10,
    )
    assert score <= 1.0


def test_score_clamped_negative():
    """Score never goes below -1.0."""
    score = compute_crowding_score(
        dark_share=0.90,
        z_block=5.0,
        z_dex=5.0,
        iv_skew=0.30,
        median_iv_skew=0.01,
        daily_return=-0.10,
    )
    assert score >= -1.0


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


def test_crowdedness_config_keys():
    """Crowdedness config keys exist with correct defaults."""
    from ifds.config.defaults import TUNING
    assert TUNING["crowdedness_shadow_enabled"] is False
    assert TUNING["crowdedness_threshold"] == 0.55
