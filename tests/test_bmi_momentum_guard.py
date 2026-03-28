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
    def test_3_day_decline_sufficient_delta_activates(self, config):
        # 4 entries → 3 deltas, all negative, total = -1.5
        history = _history(50.0, 49.5, 49.0, 48.5)
        active, reduced, total_delta = get_bmi_momentum_guard(history, config)
        assert active is True
        assert reduced == 5
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
        # Last entry is up → consecutive_decline resets to 0
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

    def test_custom_config_thresholds(self, config):
        config.tuning["bmi_momentum_days"] = 2
        config.tuning["bmi_momentum_min_delta"] = -0.5
        config.tuning["bmi_momentum_max_positions"] = 3
        history = _history(50.0, 49.7, 49.4)  # 2 declines, total -0.6
        active, reduced, _ = get_bmi_momentum_guard(history, config)
        assert active is True
        assert reduced == 3

    def test_returns_correct_reduced_max_positions(self, config):
        history = _history(50.0, 49.0, 48.0, 47.0)
        active, reduced, _ = get_bmi_momentum_guard(history, config)
        assert active is True
        assert reduced == config.tuning["bmi_momentum_max_positions"]
