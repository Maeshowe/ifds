"""Tests for Phase 0: System Diagnostics."""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import (
    APIHealthResult,
    APIStatus,
    MarketVolatilityRegime,
)
from ifds.phases.phase0_diagnostics import (
    run_phase0,
    _classify_vix,
    _calculate_vix_multiplier,
    _assess_macro_regime,
    _fetch_vix,
)


@pytest.fixture
def config(monkeypatch):
    """Config with test API keys."""
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    monkeypatch.setenv("IFDS_ASYNC_ENABLED", "false")
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
            APIHealthResult(
                "unusual_whales", "/api/darkpool", APIStatus.OK, 150, is_critical=False
            ),
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
            APIHealthResult(
                "polygon", "/v2/aggs", APIStatus.DOWN, error="Timeout", is_critical=True
            ),
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
            APIHealthResult(
                "unusual_whales",
                "/api/darkpool",
                APIStatus.DOWN,
                error="Timeout",
                is_critical=False,
            ),
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
        cb_file.write_text(
            json.dumps(
                {
                    "is_active": True,
                    "daily_drawdown_pct": 4.5,
                    "message": "Drawdown limit exceeded",
                }
            )
        )
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
    """Test VIX source: FMP ^VIX → FRED VIXCLS → default 20.0.

    Was Polygon I:VIX until 2026-10-23. The Indices subscription that served it is
    cancelled; on settled days FMP agrees with Polygon and FRED to the cent.
    """

    def test_fmp_vix_success(self, config, logger):
        """FMP ^VIX previousClose is valid → used as primary source."""
        mock_fmp = MagicMock()
        mock_fmp.get_index_quote.return_value = {"price": 20.24, "previousClose": 18.5}

        mock_fred = MagicMock()

        vix, source = _fetch_vix(mock_fmp, mock_fred, logger)

        assert vix == 18.5
        assert source == "fmp"
        mock_fmp.get_index_quote.assert_called_once()
        mock_fred.get_series.assert_not_called()

    def test_the_macro_assessment_can_actually_reach_the_fmp_client(self, config, logger):
        """Guard for a scope bug the mocked unit tests could not see.

        When the VIX source moved to FMP, `_fetch_vix(fmp, ...)` was called from
        `_assess_macro_regime` while `fmp` was not one of its parameters — a NameError
        on every production run, and the whole suite stayed green because every test
        exercised `_fetch_vix` directly. This test calls the ENCLOSING function.
        """
        mock_polygon = MagicMock()
        mock_polygon.get_aggregates.return_value = []
        mock_fmp = MagicMock()
        mock_fmp.get_index_quote.return_value = {"previousClose": 17.25}
        mock_fred = MagicMock()
        mock_fred.get_tnx.return_value = []
        mock_fred.get_series.return_value = []
        mock_fred.get_yield_curve_2s10s.return_value = None

        macro = _assess_macro_regime(config, mock_polygon, mock_fmp, mock_fred, logger)

        assert macro.vix_value == pytest.approx(17.25)
        mock_fmp.get_index_quote.assert_called_once()

    def test_fmp_fail_fred_fallback(self, config, logger):
        """FMP returns no usable quote → falls back to FRED VIXCLS.

        Was written against `mock_polygon.get_vix`. After the 2026-10-23 source swap that
        method is never called, so the mock configured a path the code no longer takes and
        the test passed for the wrong reason — it must mock the FMP client it now receives.
        """
        mock_fmp = MagicMock()
        mock_fmp.get_index_quote.return_value = None

        mock_fred = MagicMock()
        mock_fred.VIX_SERIES = "VIXCLS"
        mock_fred.get_series.return_value = [
            {"date": "2026-02-07", "value": "22.30"},
        ]

        vix, source = _fetch_vix(mock_fmp, mock_fred, logger)

        assert vix == pytest.approx(22.30)
        assert source == "fred"
        mock_fred.get_series.assert_called_once_with("VIXCLS", limit=5)

    def test_fmp_exception_fred_fallback(self, config, logger):
        """FMP raises → falls back to FRED VIXCLS."""
        mock_fmp = MagicMock()
        mock_fmp.get_index_quote.side_effect = ConnectionError("FMP down")

        mock_fred = MagicMock()
        mock_fred.VIX_SERIES = "VIXCLS"
        mock_fred.get_series.return_value = [
            {"date": "2026-02-07", "value": "19.50"},
        ]

        vix, source = _fetch_vix(mock_fmp, mock_fred, logger)

        assert vix == pytest.approx(19.50)
        assert source == "fred"

    def test_both_fail_default(self, config, logger):
        """Both Polygon and FRED fail → default 20.0."""
        mock_fmp = MagicMock()
        mock_fmp.get_index_quote.return_value = None

        mock_fred = MagicMock()
        mock_fred.VIX_SERIES = "VIXCLS"
        mock_fred.get_series.return_value = None

        vix, source = _fetch_vix(mock_fmp, mock_fred, logger)

        assert vix == 20.0
        assert source == "default"

    def test_out_of_range_quote_triggers_fallback(self, config, logger):
        """A VIX outside the [5, 100] sanity band is rejected → FRED fallback.

        The band is enforced by `_validate_vix`, so this exercises the guard rather than
        the client: a vendor that answers 250.0 must not set the regime.
        """
        mock_fmp = MagicMock()
        mock_fmp.get_index_quote.return_value = {"previousClose": 250.0}

        mock_fred = MagicMock()
        mock_fred.VIX_SERIES = "VIXCLS"
        mock_fred.get_series.return_value = [
            {"date": "2026-02-07", "value": "25.00"},
        ]

        vix, source = _fetch_vix(mock_fmp, mock_fred, logger)

        assert vix == 25.0
        assert source == "fred"

    def test_fred_missing_dot_values(self, config, logger):
        """FRED returns all '.' values → falls through to default."""
        mock_fmp = MagicMock()
        mock_fmp.get_index_quote.return_value = None

        mock_fred = MagicMock()
        mock_fred.VIX_SERIES = "VIXCLS"
        mock_fred.get_series.return_value = [
            {"date": "2026-02-07", "value": "."},
            {"date": "2026-02-06", "value": "."},
        ]

        vix, source = _fetch_vix(mock_fmp, mock_fred, logger)

        assert vix == 20.0
        assert source == "default"


class TestNoLiveMidCalls:
    """The suite must never make a live MID call or write a production bundle.

    Measured on 2026-10-04: ``TestPhase0Integration::test_all_ok`` and
    ``::test_uw_down_continues`` each fetched a real 28 kB MID bundle and wrote
    ``state/mid_bundles/{today}.json.gz``, because the ``config`` fixture
    monkeypatched the IFDS_* keys but never cleared ``MID_API_KEY`` — which
    ``.env`` exports and ``deploy_daily.sh`` sources before its pytest pre-flight.
    """

    def test_mid_api_key_is_absent_from_the_test_environment(self):
        import os

        assert os.environ.get("MID_API_KEY") in (None, ""), (
            "MID_API_KEY is set during tests — run_phase0 will make a LIVE call "
            "and overwrite state/mid_bundles/{today}.json.gz"
        )

    def test_conftest_uses_the_empty_sentinel_not_a_pop(self):
        """``pop`` is not enough: ``load_dotenv()`` re-reads ``.env``.

        Measured — after a pop the production bundle was STILL rewritten.
        ``load_dotenv`` defaults to ``override=False``, so a present-but-empty
        variable survives it while an absent one does not.

        Pinned on the conftest SOURCE, not the runtime env, so the guard cannot
        be satisfied by whatever happened to clear the variable.
        """
        from pathlib import Path

        source = (Path(__file__).parent / "conftest.py").read_text()
        assert 'os.environ["MID_API_KEY"] = ""' in source
