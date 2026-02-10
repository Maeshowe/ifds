"""Configuration validator — type and range checks on startup."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ifds.config.loader import Config


class ConfigValidationError(Exception):
    """Raised when configuration is invalid. Pipeline must HALT."""
    pass


def validate_config(config: Config) -> None:
    """Validate all configuration parameters.

    Checks:
    - Required API keys are present
    - Numeric values are in valid ranges
    - Weights sum to expected values

    Raises:
        ConfigValidationError: If any validation fails.
    """
    errors: list[str] = []

    # --- Runtime: API keys ---
    if not config.runtime.get("polygon_api_key"):
        errors.append(
            "Missing IFDS_POLYGON_API_KEY environment variable. "
            "Set it with: export IFDS_POLYGON_API_KEY=your_key"
        )
    if not config.runtime.get("fmp_api_key"):
        errors.append(
            "Missing IFDS_FMP_API_KEY environment variable. "
            "Set it with: export IFDS_FMP_API_KEY=your_key"
        )
    if not config.runtime.get("fred_api_key"):
        errors.append(
            "Missing IFDS_FRED_API_KEY environment variable. "
            "FRED requires a free API key: https://fred.stlouisfed.org/docs/api/api_key.html "
            "Set it with: export IFDS_FRED_API_KEY=your_key"
        )
    # UW is optional (has Polygon fallback)

    # --- Runtime: Numeric ranges ---
    _check_positive(config.runtime, "account_equity", errors)
    _check_range(config.runtime, "risk_per_trade_pct", 0.1, 5.0, errors)
    _check_range(config.runtime, "max_positions", 1, 20, errors)
    _check_range(config.runtime, "circuit_breaker_drawdown_limit_pct", 0.5, 10.0, errors)

    # --- Core: Scoring weights must sum to 1.0 ---
    weight_sum = (
        config.core["weight_flow"]
        + config.core["weight_fundamental"]
        + config.core["weight_technical"]
    )
    if abs(weight_sum - 1.0) > 0.001:
        errors.append(
            f"Scoring weights must sum to 1.0, got {weight_sum:.3f} "
            f"(flow={config.core['weight_flow']}, "
            f"funda={config.core['weight_fundamental']}, "
            f"tech={config.core['weight_technical']})"
        )

    # --- Core: ATR multiples ---
    _check_positive(config.core, "stop_loss_atr_multiple", errors)
    _check_positive(config.core, "tp1_atr_multiple", errors)
    _check_positive(config.core, "tp2_atr_multiple", errors)

    if config.core["tp1_atr_multiple"] >= config.core["tp2_atr_multiple"]:
        errors.append("TP1 ATR multiple must be less than TP2 ATR multiple.")

    # --- Tuning: BMI thresholds ---
    if config.tuning["bmi_green_threshold"] >= config.tuning["bmi_red_threshold"]:
        errors.append("BMI green threshold must be less than red threshold.")

    _check_range(config.tuning, "combined_score_minimum", 0, 100, errors)
    _check_range(config.tuning, "vix_multiplier_floor", 0.1, 1.0, errors)

    # --- Report ---
    if errors:
        msg = "Configuration validation failed:\n" + "\n".join(
            f"  - {e}" for e in errors
        )
        raise ConfigValidationError(msg)


def _check_positive(d: dict, key: str, errors: list[str]) -> None:
    val = d.get(key)
    if val is None or val <= 0:
        errors.append(f"{key} must be positive, got {val}")


def _check_range(d: dict, key: str, min_val: float, max_val: float,
                 errors: list[str]) -> None:
    val = d.get(key)
    if val is None or val < min_val or val > max_val:
        errors.append(f"{key} must be between {min_val} and {max_val}, got {val}")
