"""Tests for IFDS configuration layer."""

import os
import pytest

from ifds.config.defaults import CORE, TUNING, RUNTIME
from ifds.config.loader import Config
from ifds.config.validator import ConfigValidationError, validate_config


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure API key env vars are clean for each test."""
    for key in ["IFDS_POLYGON_API_KEY", "IFDS_FMP_API_KEY", "IFDS_UW_API_KEY",
                "IFDS_FRED_API_KEY", "IFDS_ACCOUNT_EQUITY", "IFDS_MAX_POSITIONS"]:
        monkeypatch.delenv(key, raising=False)


def _set_required_keys(monkeypatch):
    """Set all required API keys for tests."""
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")


class TestDefaults:
    def test_core_has_required_keys(self):
        assert "weight_flow" in CORE
        assert "weight_fundamental" in CORE
        assert "weight_technical" in CORE
        assert CORE["weight_flow"] + CORE["weight_fundamental"] + CORE["weight_technical"] == 1.0

    def test_tuning_has_bmi_thresholds(self):
        assert TUNING["bmi_green_threshold"] < TUNING["bmi_red_threshold"]

    def test_runtime_api_keys_default_none(self):
        assert RUNTIME["polygon_api_key"] is None
        assert RUNTIME["unusual_whales_api_key"] is None
        assert RUNTIME["fmp_api_key"] is None
        assert RUNTIME["fred_api_key"] is None


class TestValidation:
    def test_fails_without_api_keys(self):
        with pytest.raises(ConfigValidationError, match="IFDS_POLYGON_API_KEY"):
            Config()

    def test_fails_with_only_polygon_key(self, monkeypatch):
        monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test")
        with pytest.raises(ConfigValidationError, match="IFDS_FMP_API_KEY"):
            Config()

    def test_fails_without_fred_key(self, monkeypatch):
        monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test")
        monkeypatch.setenv("IFDS_FMP_API_KEY", "test")
        with pytest.raises(ConfigValidationError, match="IFDS_FRED_API_KEY"):
            Config()

    def test_passes_with_required_keys(self, monkeypatch):
        _set_required_keys(monkeypatch)
        config = Config()
        assert config.get_api_key("polygon") == "test_poly"
        assert config.get_api_key("fmp") == "test_fmp"
        assert config.get_api_key("fred") == "test_fred"
        assert config.get_api_key("unusual_whales") is None  # Optional


class TestEnvOverrides:
    def test_account_equity_override(self, monkeypatch):
        _set_required_keys(monkeypatch)
        monkeypatch.setenv("IFDS_ACCOUNT_EQUITY", "250000")
        config = Config()
        assert config.runtime["account_equity"] == 250000.0

    def test_max_positions_override(self, monkeypatch):
        _set_required_keys(monkeypatch)
        monkeypatch.setenv("IFDS_MAX_POSITIONS", "5")
        config = Config()
        assert config.runtime["max_positions"] == 5

    def test_invalid_env_var_type_raises(self, monkeypatch):
        _set_required_keys(monkeypatch)
        monkeypatch.setenv("IFDS_ACCOUNT_EQUITY", "not_a_number")
        with pytest.raises(ConfigValidationError, match="IFDS_ACCOUNT_EQUITY"):
            Config()


class TestConfigFile:
    def test_loads_from_json_file(self, monkeypatch, tmp_path):
        _set_required_keys(monkeypatch)
        config_file = tmp_path / "config.json"
        config_file.write_text('{"runtime": {"account_equity": 500000}}')
        config = Config(config_path=str(config_file))
        assert config.runtime["account_equity"] == 500000

    def test_missing_file_raises(self, monkeypatch):
        _set_required_keys(monkeypatch)
        with pytest.raises(FileNotFoundError):
            Config(config_path="/nonexistent/config.json")

    def test_unknown_key_warns(self, monkeypatch, tmp_path, capsys):
        _set_required_keys(monkeypatch)
        config_file = tmp_path / "config.json"
        config_file.write_text('{"runtime": {"unknown_param": 42}}')
        Config(config_path=str(config_file))
        captured = capsys.readouterr()
        assert "Unknown key 'unknown_param'" in captured.err
