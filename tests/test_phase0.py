"""Tests for Phase 0: System Diagnostics."""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import (
    APIHealthResult, APIStatus, MarketVolatilityRegime,
)
from ifds.phases.phase0_diagnostics import (
    run_phase0, _classify_vix, _calculate_vix_multiplier, _fetch_vix,
)


@pytest.fixture
def config(monkeypatch):
    """Config with test API keys."""
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    return Config()


@pytest.fixture
def logger(tmp_path):
    """Event logger writing to temp directory."""
    return EventLogger(log_dir=str(tmp_path), run_id="test-run")


class TestVIXClassification:
    def test_low(self, config):
        assert _classify_vix(12.0, config) == MarketVolatilityRegime.LOW

    def test_normal(self, config):
        assert _classify_vix(17.0, config) == MarketVolatilityRegime.NORMAL

    def test_elevated(self, config):
        assert _classify_vix(25.0, config) == MarketVolatilityRegime.ELEVATED

    def test_panic(self, config):
        assert _classify_vix(35.0, config) == MarketVolatilityRegime.PANIC

    def test_boundary_low(self, config):
        assert _classify_vix(15.0, config) == MarketVolatilityRegime.LOW

    def test_boundary_normal(self, config):
        assert _classify_vix(20.0, config) == MarketVolatilityRegime.NORMAL

    def test_boundary_elevated(self, config):
        assert _classify_vix(30.0, config) == MarketVolatilityRegime.ELEVATED


class TestVIXMultiplier:
    def test_below_threshold(self, config):
        assert _calculate_vix_multiplier(15.0, config) == 1.0

    def test_at_threshold(self, config):
        assert _calculate_vix_multiplier(20.0, config) == 1.0

    def test_above_threshold(self, config):
        # VIX=25: max(0.25, 1.0 - (25-20)*0.02) = max(0.25, 0.9) = 0.9
        assert _calculate_vix_multiplier(25.0, config) == pytest.approx(0.9)

    def test_high_vix(self, config):
        # VIX=40: max(0.25, 1.0 - (40-20)*0.02) = max(0.25, 0.6) = 0.6
        assert _calculate_vix_multiplier(40.0, config) == pytest.approx(0.6)

    def test_extreme_vix_hits_floor(self, config):
        # VIX=60 > 50 → EXTREME regime → flat 0.10 multiplier (BC12)
        assert _calculate_vix_multiplier(60.0, config) == 0.10


class TestPhase0Integration:
    @patch("ifds.phases.phase0_diagnostics._check_all_apis")
    @patch("ifds.phases.phase0_diagnostics._assess_macro_regime")
    def test_all_ok(self, mock_macro, mock_apis, config, logger):
        """All APIs OK, no circuit breaker → pipeline can proceed."""
        mock_apis.return_value = [
            APIHealthResult("polygon", "/v2/aggs", APIStatus.OK, 100, is_critical=True),
            APIHealthResult("polygon", "/v3/options", APIStatus.OK, 200, is_critical=True),
            APIHealthResult("unusual_whales", "/api/darkpool", APIStatus.OK, 150, is_critical=False),
            APIHealthResult("fmp", "/stable/screener", APIStatus.OK, 120, is_critical=True),
            APIHealthResult("fred", "/observations", APIStatus.OK, 80, is_critical=True),
        ]
        mock_macro.return_value = MagicMock(
            vix_value=18.0,
            vix_regime=MarketVolatilityRegime.NORMAL,
            vix_multiplier=1.0,
        )

        result = run_phase0(config, logger)

        assert result.pipeline_can_proceed is True
        assert result.all_critical_apis_ok is True
        assert result.halt_reason is None

    @patch("ifds.phases.phase0_diagnostics._check_all_apis")
    def test_critical_api_down_halts(self, mock_apis, config, logger):
        """Critical API down → pipeline HALT."""
        mock_apis.return_value = [
            APIHealthResult("polygon", "/v2/aggs", APIStatus.DOWN, error="Timeout", is_critical=True),
            APIHealthResult("fmp", "/stable/screener", APIStatus.OK, 120, is_critical=True),
            APIHealthResult("fred", "/observations", APIStatus.OK, 80, is_critical=True),
        ]

        result = run_phase0(config, logger)

        assert result.pipeline_can_proceed is False
        assert "polygon" in result.halt_reason

    @patch("ifds.phases.phase0_diagnostics._check_all_apis")
    @patch("ifds.phases.phase0_diagnostics._assess_macro_regime")
    def test_uw_down_continues(self, mock_macro, mock_apis, config, logger):
        """UW down (non-critical) → pipeline continues with fallback."""
        mock_apis.return_value = [
            APIHealthResult("polygon", "/v2/aggs", APIStatus.OK, 100, is_critical=True),
            APIHealthResult("polygon", "/v3/options", APIStatus.OK, 200, is_critical=True),
            APIHealthResult("unusual_whales", "/api/darkpool", APIStatus.DOWN,
                          error="Timeout", is_critical=False),
            APIHealthResult("fmp", "/stable/screener", APIStatus.OK, 120, is_critical=True),
            APIHealthResult("fred", "/observations", APIStatus.OK, 80, is_critical=True),
        ]
        mock_macro.return_value = MagicMock()

        result = run_phase0(config, logger)

        assert result.pipeline_can_proceed is True
        assert result.uw_available is False

    def test_circuit_breaker_halts(self, config, logger, tmp_path):
        """Active circuit breaker → pipeline HALT."""
        cb_file = tmp_path / "cb.json"
        cb_file.write_text(json.dumps({
            "is_active": True,
            "daily_drawdown_pct": 4.5,
            "message": "Drawdown limit exceeded",
        }))
        config.runtime["circuit_breaker_state_file"] = str(cb_file)

        with patch("ifds.phases.phase0_diagnostics._check_all_apis") as mock_apis:
            mock_apis.return_value = [
                APIHealthResult("polygon", "/v2/aggs", APIStatus.OK, 100, is_critical=True),
                APIHealthResult("fmp", "/stable/screener", APIStatus.OK, 120, is_critical=True),
                APIHealthResult("fred", "/observations", APIStatus.OK, 80, is_critical=True),
            ]

            result = run_phase0(config, logger)

        assert result.pipeline_can_proceed is False
        assert result.circuit_breaker.is_active is True
        assert "Circuit breaker" in result.halt_reason


class TestVIXFallbackChain:
    """Test VIX source: Polygon I:VIX → FRED VIXCLS → default 20.0."""

    def test_polygon_vix_success(self, config, logger):
        """Polygon I:VIX returns valid value → used as primary source."""
        mock_polygon = MagicMock()
        mock_polygon.get_vix.return_value = 18.5

        mock_fred = MagicMock()

        vix, source = _fetch_vix(mock_polygon, mock_fred, logger)

        assert vix == 18.5
        assert source == "polygon"
        mock_polygon.get_vix.assert_called_once_with(days_back=10)
        mock_fred.get_series.assert_not_called()

    def test_polygon_fail_fred_fallback(self, config, logger):
        """Polygon returns None → falls back to FRED VIXCLS."""
        mock_polygon = MagicMock()
        mock_polygon.get_vix.return_value = None

        mock_fred = MagicMock()
        mock_fred.VIX_SERIES = "VIXCLS"
        mock_fred.get_series.return_value = [
            {"date": "2026-02-07", "value": "22.30"},
        ]

        vix, source = _fetch_vix(mock_polygon, mock_fred, logger)

        assert vix == pytest.approx(22.30)
        assert source == "fred"
        mock_fred.get_series.assert_called_once_with("VIXCLS", limit=5)

    def test_polygon_exception_fred_fallback(self, config, logger):
        """Polygon raises exception → falls back to FRED VIXCLS."""
        mock_polygon = MagicMock()
        mock_polygon.get_vix.side_effect = ConnectionError("Polygon down")

        mock_fred = MagicMock()
        mock_fred.VIX_SERIES = "VIXCLS"
        mock_fred.get_series.return_value = [
            {"date": "2026-02-07", "value": "19.50"},
        ]

        vix, source = _fetch_vix(mock_polygon, mock_fred, logger)

        assert vix == pytest.approx(19.50)
        assert source == "fred"

    def test_both_fail_default(self, config, logger):
        """Both Polygon and FRED fail → default 20.0."""
        mock_polygon = MagicMock()
        mock_polygon.get_vix.return_value = None

        mock_fred = MagicMock()
        mock_fred.VIX_SERIES = "VIXCLS"
        mock_fred.get_series.return_value = None

        vix, source = _fetch_vix(mock_polygon, mock_fred, logger)

        assert vix == 20.0
        assert source == "default"

    def test_polygon_out_of_range_triggers_fallback(self, config, logger):
        """Polygon VIX outside sanity range → returns None → FRED fallback."""
        mock_polygon = MagicMock()
        # get_vix already has sanity check (5-100), returns None if out of range
        mock_polygon.get_vix.return_value = None

        mock_fred = MagicMock()
        mock_fred.VIX_SERIES = "VIXCLS"
        mock_fred.get_series.return_value = [
            {"date": "2026-02-07", "value": "25.00"},
        ]

        vix, source = _fetch_vix(mock_polygon, mock_fred, logger)

        assert vix == 25.0
        assert source == "fred"

    def test_fred_missing_dot_values(self, config, logger):
        """FRED returns all '.' values → falls through to default."""
        mock_polygon = MagicMock()
        mock_polygon.get_vix.return_value = None

        mock_fred = MagicMock()
        mock_fred.VIX_SERIES = "VIXCLS"
        mock_fred.get_series.return_value = [
            {"date": "2026-02-07", "value": "."},
            {"date": "2026-02-06", "value": "."},
        ]

        vix, source = _fetch_vix(mock_polygon, mock_fred, logger)

        assert vix == 20.0
        assert source == "default"
