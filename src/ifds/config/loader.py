"""Configuration loader — merges defaults with env vars and optional config file."""

import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from ifds.config.defaults import CORE, TUNING, RUNTIME
from ifds.config.validator import ConfigValidationError, validate_config


class Config:
    """Layered configuration for IFDS.

    Priority (highest wins):
        1. Environment variables (IFDS_*)
        2. Config file (if provided)
        3. Built-in defaults
    """

    def __init__(self, config_path: str | None = None):
        self.core: dict[str, Any] = deepcopy(CORE)
        self.tuning: dict[str, Any] = deepcopy(TUNING)
        self.runtime: dict[str, Any] = deepcopy(RUNTIME)

        # Layer 2: Config file overrides
        if config_path:
            self._load_file(config_path)

        # Layer 3: Env var overrides (highest priority)
        self._load_env_vars()

        # Validate the final merged config
        validate_config(self)

    def _load_file(self, path: str) -> None:
        """Load overrides from a JSON config file."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(config_path) as f:
            data = json.load(f)

        # Warn on unrecognized keys (Warning #6)
        known_sections = {"core": self.core, "tuning": self.tuning, "runtime": self.runtime}
        for section_name, section_defaults in known_sections.items():
            for key in data.get(section_name, {}):
                if key not in section_defaults:
                    print(
                        f"[CONFIG WARNING] Unknown key '{key}' in "
                        f"config file section '{section_name}' — ignored.",
                        file=sys.stderr,
                    )

        for key, value in data.get("core", {}).items():
            if key in self.core:
                self.core[key] = value

        for key, value in data.get("tuning", {}).items():
            if key in self.tuning:
                self.tuning[key] = value

        for key, value in data.get("runtime", {}).items():
            if key in self.runtime:
                self.runtime[key] = value

    def _load_env_vars(self) -> None:
        """Load runtime values from environment variables."""
        env_mapping = {
            "IFDS_POLYGON_API_KEY": "polygon_api_key",
            "IFDS_UW_API_KEY": "unusual_whales_api_key",
            "IFDS_FMP_API_KEY": "fmp_api_key",
            "IFDS_FRED_API_KEY": "fred_api_key",
            "IFDS_ACCOUNT_EQUITY": ("account_equity", float),
            "IFDS_RISK_PER_TRADE_PCT": ("risk_per_trade_pct", float),
            "IFDS_MAX_POSITIONS": ("max_positions", int),
            "IFDS_OUTPUT_DIR": "output_dir",
            "IFDS_LOG_DIR": "log_dir",
            "IFDS_CIRCUIT_BREAKER_LIMIT": ("circuit_breaker_drawdown_limit_pct", float),
            "IFDS_ASYNC_ENABLED": ("async_enabled", lambda v: v.lower() in ("true", "1", "yes")),
            "IFDS_CACHE_ENABLED": ("cache_enabled", lambda v: v.lower() in ("true", "1", "yes")),
            "IFDS_CACHE_DIR": "cache_dir",
        }

        for env_key, target in env_mapping.items():
            value = os.environ.get(env_key)
            if value is None:
                continue

            if isinstance(target, tuple):
                key, type_fn = target
                try:
                    self.runtime[key] = type_fn(value)
                except (ValueError, TypeError):
                    raise ConfigValidationError(
                        f"Invalid value for {env_key}: '{value}' "
                        f"(expected {type_fn.__name__})"
                    )
            else:
                self.runtime[target] = value

    def get_api_key(self, provider: str) -> str | None:
        """Get API key for a provider."""
        key_map = {
            "polygon": "polygon_api_key",
            "unusual_whales": "unusual_whales_api_key",
            "fmp": "fmp_api_key",
            "fred": "fred_api_key",
        }
        return self.runtime.get(key_map.get(provider))

    def __repr__(self) -> str:
        return (
            f"Config(core={len(self.core)} params, "
            f"tuning={len(self.tuning)} params, "
            f"runtime={len(self.runtime)} params)"
        )
