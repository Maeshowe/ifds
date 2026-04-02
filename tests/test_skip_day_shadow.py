"""Tests for skip-day shadow guard (VIX + BMI combo).

Shadow mode only — logs when conditions suggest skipping the trading day,
but does NOT block the pipeline.
"""

import pytest

from ifds.config.loader import Config
from ifds.models.market import MacroRegime, MarketVolatilityRegime
from ifds.phases.phase6_sizing import check_skip_day_shadow


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    monkeypatch.setenv("IFDS_ASYNC_ENABLED", "false")
    return Config()


def _make_macro(vix: float = 18.0) -> MacroRegime:
    regime = MarketVolatilityRegime.PANIC if vix >= 30 else (
        MarketVolatilityRegime.ELEVATED if vix > 20 else MarketVolatilityRegime.NORMAL
    )
    return MacroRegime(
        vix_value=vix, vix_regime=regime, vix_multiplier=1.0,
        tnx_value=4.2, tnx_sma20=4.1, tnx_rate_sensitive=False,
    )


def _make_bmi_history(values: list[float]) -> list[dict]:
    """Create BMI history from a list of BMI values (oldest to newest)."""
    return [{"date": f"2026-03-{i+1:02d}", "bmi": v} for i, v in enumerate(values)]


class TestSkipDayShadow:

    def test_both_triggered_would_skip(self, config):
        """VIX >= 28 AND BMI declining 5+ days → would_skip=True."""
        macro = _make_macro(vix=30.5)
        # 6 declining days: 55, 53, 51, 49, 47, 45
        history = _make_bmi_history([55, 53, 51, 49, 47, 45])
        would_skip, details = check_skip_day_shadow(macro, history, config)
        assert would_skip is True
        assert details["vix_triggered"] is True
        assert details["bmi_triggered"] is True
        assert details["bmi_consecutive_decline"] == 5

    def test_vix_high_bmi_not_declining(self, config):
        """VIX >= 28 but BMI not declining → would_skip=False."""
        macro = _make_macro(vix=32.0)
        history = _make_bmi_history([45, 47, 49, 51, 53])
        would_skip, details = check_skip_day_shadow(macro, history, config)
        assert would_skip is False
        assert details["vix_triggered"] is True
        assert details["bmi_triggered"] is False

    def test_vix_low_bmi_declining(self, config):
        """VIX < 28 but BMI declining → would_skip=False."""
        macro = _make_macro(vix=22.0)
        history = _make_bmi_history([55, 53, 51, 49, 47, 45])
        would_skip, details = check_skip_day_shadow(macro, history, config)
        assert would_skip is False
        assert details["vix_triggered"] is False
        assert details["bmi_triggered"] is True

    def test_disabled(self, config):
        """shadow_enabled=False → would_skip=False, empty details."""
        config.tuning["skip_day_shadow_enabled"] = False
        macro = _make_macro(vix=35.0)
        history = _make_bmi_history([55, 53, 51, 49, 47, 45])
        would_skip, details = check_skip_day_shadow(macro, history, config)
        assert would_skip is False
        assert details == {}

    def test_insufficient_history(self, config):
        """Not enough BMI history → bmi_triggered=False."""
        macro = _make_macro(vix=30.0)
        history = _make_bmi_history([50])  # Only 1 entry
        would_skip, details = check_skip_day_shadow(macro, history, config)
        assert would_skip is False
        assert details["bmi_consecutive_decline"] == 0

    def test_empty_history(self, config):
        """Empty BMI history → bmi_triggered=False."""
        macro = _make_macro(vix=30.0)
        would_skip, details = check_skip_day_shadow(macro, [], config)
        assert would_skip is False
        assert details["bmi_consecutive_decline"] == 0

    def test_exactly_at_vix_threshold(self, config):
        """VIX exactly at threshold (28.0) → vix_triggered=True."""
        macro = _make_macro(vix=28.0)
        history = _make_bmi_history([55, 53, 51, 49, 47, 45])
        would_skip, details = check_skip_day_shadow(macro, history, config)
        assert would_skip is True
        assert details["vix_triggered"] is True

    def test_bmi_decline_interrupted(self, config):
        """BMI decline interrupted by uptick → counts only consecutive tail."""
        macro = _make_macro(vix=30.0)
        # 55→53→51→52(uptick)→50→48→46 = only 3 consecutive declining at tail
        history = _make_bmi_history([55, 53, 51, 52, 50, 48, 46])
        would_skip, details = check_skip_day_shadow(macro, history, config)
        assert would_skip is False
        assert details["bmi_consecutive_decline"] == 3

    def test_custom_thresholds(self, config):
        """Custom VIX threshold and BMI decline days."""
        config.tuning["skip_day_vix_threshold"] = 25.0
        config.tuning["skip_day_bmi_decline_days"] = 3
        macro = _make_macro(vix=26.0)
        history = _make_bmi_history([55, 53, 51, 49])  # 3 declining days
        would_skip, details = check_skip_day_shadow(macro, history, config)
        assert would_skip is True
