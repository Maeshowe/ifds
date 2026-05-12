"""Tests for BMI Momentum Guard (Phase 6)."""

import pytest
from ifds.config.loader import Config
from ifds.phases.phase6_sizing import get_bmi_momentum_guard


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    monkeypatch.setenv("IFDS_ASYNC_ENABLED", "false")
    return Config()


def _history(*bmis):
    """Build bmi_history list from BMI values (ascending dates)."""
    return [{"date": f"2026-03-{i+1:02d}", "bmi": v, "regime": "yellow"}
            for i, v in enumerate(bmis)]


class TestBmiMomentumGuard:
    def test_3_day_decline_yields_mild_tier(self, config):
        """3 days declining → mild tier (4 positions)."""
        # 4 entries → 3 declines, total = -1.5
        history = _history(50.0, 49.5, 49.0, 48.5)
        active, reduced, total_delta = get_bmi_momentum_guard(history, config)
        assert active is True
        assert reduced == 4  # mild tier (was: fixed 5, a no-op vs max_positions=5)
        assert total_delta == pytest.approx(-1.5)

    def test_only_2_days_decline_does_not_activate(self, config):
        history = _history(50.0, 50.0, 49.5, 49.0)  # flat + 2 down
        active, _, _ = get_bmi_momentum_guard(history, config)
        assert active is False

    def test_3_day_decline_delta_not_enough(self, config):
        # 3 consecutive declines but only -0.6 total (threshold is -1.0)
        history = _history(50.0, 49.8, 49.6, 49.4)
        active, _, _ = get_bmi_momentum_guard(history, config)
        assert active is False

    def test_4_days_down_then_1_up_deactivates(self, config):
        # Last entry is up → consecutive_decline (walking backward) is 0
        history = _history(50.0, 49.0, 48.0, 47.0, 47.5)
        active, _, _ = get_bmi_momentum_guard(history, config)
        assert active is False

    def test_insufficient_history_does_not_activate(self, config):
        # Need min_days+1 = 4 entries; only 3 provided
        history = _history(50.0, 49.0, 48.0)
        active, _, _ = get_bmi_momentum_guard(history, config)
        assert active is False

    def test_empty_history_does_not_activate(self, config):
        active, _, _ = get_bmi_momentum_guard([], config)
        assert active is False

    def test_guard_disabled_by_config(self, config):
        config.tuning["bmi_momentum_guard_enabled"] = False
        history = _history(50.0, 49.0, 48.0, 47.0)
        active, _, _ = get_bmi_momentum_guard(history, config)
        assert active is False


class TestBmiMomentumGuardTiered:
    """Tiered reduction (2026-05-12 recalibration).

    Boundaries: ≥3 days mild (4), ≥5 strong (3), ≥7 severe (2).
    """

    def test_5_day_decline_yields_strong_tier(self, config):
        # 6 entries → 5 declines, total = -5.0
        history = _history(50.0, 49.0, 48.0, 47.0, 46.0, 45.0)
        active, reduced, total_delta = get_bmi_momentum_guard(history, config)
        assert active is True
        assert reduced == 3  # strong tier
        assert total_delta == pytest.approx(-5.0)

    def test_7_day_decline_yields_severe_tier(self, config):
        # 8 entries → 7 declines, total = -10.5 (matches the live -10.9 case)
        history = _history(60.0, 58.5, 57.0, 55.5, 54.0, 52.5, 51.0, 49.5)
        active, reduced, total_delta = get_bmi_momentum_guard(history, config)
        assert active is True
        assert reduced == 2  # severe tier
        assert total_delta == pytest.approx(-10.5)

    def test_4_day_decline_stays_in_mild_tier(self, config):
        # 4 declines = below strong threshold (5) → mild
        history = _history(50.0, 49.0, 48.0, 47.0, 46.0)
        active, reduced, _ = get_bmi_momentum_guard(history, config)
        assert active is True
        assert reduced == 4

    def test_6_day_decline_stays_in_strong_tier(self, config):
        # 6 declines = below severe threshold (7) → strong
        history = _history(50.0, 49.0, 48.0, 47.0, 46.0, 45.0, 44.0)
        active, reduced, _ = get_bmi_momentum_guard(history, config)
        assert active is True
        assert reduced == 3

    def test_10_day_decline_caps_at_severe_tier(self, config):
        # Beyond 7 days, stays at severe (no further reduction)
        bmis = [60.0] + [60.0 - i for i in range(1, 11)]  # 11 entries, 10 declines
        history = _history(*bmis)
        active, reduced, _ = get_bmi_momentum_guard(history, config)
        assert active is True
        assert reduced == 2

    def test_custom_tier_thresholds(self, config):
        # Reconfigure tiers and verify the new boundaries are honored
        config.tuning["bmi_momentum_days"] = 2
        config.tuning["bmi_momentum_min_delta"] = -0.5
        config.tuning["bmi_momentum_mild_days"] = 2
        config.tuning["bmi_momentum_mild_max_positions"] = 4
        config.tuning["bmi_momentum_strong_days"] = 3
        config.tuning["bmi_momentum_strong_max_positions"] = 2
        history = _history(50.0, 49.0, 48.0)  # 2 declines → mild tier
        active, reduced, _ = get_bmi_momentum_guard(history, config)
        assert active is True
        assert reduced == 4
