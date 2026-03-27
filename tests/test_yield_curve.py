"""Tests for 2s10s yield curve spread shadow log (Phase 0 BC18 follow-up).

Covers:
- get_yield_curve_2s10s() — positive (normal), negative (inverted), API error
- curve_status classification (NORMAL / FLATTENING / INVERTED)
- MacroRegime.yield_curve_2s10s optional field
- Config key exists
"""

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# fred.get_yield_curve_2s10s() tests
# ---------------------------------------------------------------------------


def test_yield_curve_positive(monkeypatch):
    """Positive spread returns float value."""
    from ifds.data.fred import FREDClient

    client = FREDClient.__new__(FREDClient)
    client.get_series = MagicMock(return_value=[
        {"date": "2026-03-27", "value": "0.35"},
        {"date": "2026-03-26", "value": "0.33"},
    ])
    result = client.get_yield_curve_2s10s()
    assert result == pytest.approx(0.35)


def test_yield_curve_negative_inverted(monkeypatch):
    """Negative spread (inverted curve) returns negative float."""
    from ifds.data.fred import FREDClient

    client = FREDClient.__new__(FREDClient)
    client.get_series = MagicMock(return_value=[
        {"date": "2026-03-27", "value": "-0.50"},
    ])
    result = client.get_yield_curve_2s10s()
    assert result == pytest.approx(-0.50)


def test_yield_curve_api_error_returns_none(monkeypatch):
    """API error or empty response → None, no exception raised."""
    from ifds.data.fred import FREDClient

    client = FREDClient.__new__(FREDClient)
    client.get_series = MagicMock(return_value=None)
    result = client.get_yield_curve_2s10s()
    assert result is None


def test_yield_curve_missing_data_dot_returns_none(monkeypatch):
    """FRED '.' missing data marker → None."""
    from ifds.data.fred import FREDClient

    client = FREDClient.__new__(FREDClient)
    client.get_series = MagicMock(return_value=[
        {"date": "2026-03-27", "value": "."},
    ])
    result = client.get_yield_curve_2s10s()
    assert result is None


# ---------------------------------------------------------------------------
# curve_status classification tests
# ---------------------------------------------------------------------------


def _classify(spread: float) -> str:
    """Helper: replicate the classification logic from phase0_diagnostics."""
    if spread < 0:
        return "INVERTED"
    elif spread < 0.20:
        return "FLATTENING"
    else:
        return "NORMAL"


def test_curve_status_normal():
    assert _classify(0.35) == "NORMAL"
    assert _classify(0.20) == "NORMAL"
    assert _classify(1.50) == "NORMAL"


def test_curve_status_flattening():
    assert _classify(0.10) == "FLATTENING"
    assert _classify(0.0) == "FLATTENING"
    assert _classify(0.19) == "FLATTENING"


def test_curve_status_inverted():
    assert _classify(-0.01) == "INVERTED"
    assert _classify(-0.50) == "INVERTED"
    assert _classify(-2.0) == "INVERTED"


# ---------------------------------------------------------------------------
# MacroRegime dataclass field tests
# ---------------------------------------------------------------------------


def test_macro_regime_yield_curve_optional():
    """yield_curve_2s10s and curve_status are optional with defaults."""
    from ifds.models.market import (
        MacroRegime, MarketVolatilityRegime,
    )
    macro = MacroRegime(
        vix_value=18.0,
        vix_regime=MarketVolatilityRegime.NORMAL,
        vix_multiplier=1.0,
        tnx_value=4.2,
        tnx_sma20=4.1,
        tnx_rate_sensitive=False,
    )
    assert macro.yield_curve_2s10s is None
    assert macro.curve_status == "UNKNOWN"


def test_macro_regime_yield_curve_set():
    """yield_curve_2s10s and curve_status can be set explicitly."""
    from ifds.models.market import (
        MacroRegime, MarketVolatilityRegime,
    )
    macro = MacroRegime(
        vix_value=18.0,
        vix_regime=MarketVolatilityRegime.NORMAL,
        vix_multiplier=1.0,
        tnx_value=4.2,
        tnx_sma20=4.1,
        tnx_rate_sensitive=False,
        yield_curve_2s10s=0.35,
        curve_status="NORMAL",
    )
    assert macro.yield_curve_2s10s == pytest.approx(0.35)
    assert macro.curve_status == "NORMAL"


# ---------------------------------------------------------------------------
# Config key test
# ---------------------------------------------------------------------------


def test_yield_curve_shadow_config_key_exists():
    """yield_curve_shadow_enabled exists in TUNING config."""
    from ifds.config.defaults import TUNING
    assert "yield_curve_shadow_enabled" in TUNING
    assert TUNING["yield_curve_shadow_enabled"] is True
