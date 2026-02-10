"""Phase 0: System Diagnostics.

Pre-flight checks before any analysis:
1. API Health Check — all critical endpoints must respond
2. Circuit Breaker — drawdown protection (manual reset required)
3. Macro Regime — VIX levels, TNX rate sensitivity, VIX multiplier

If any critical check fails, the pipeline HALTs.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from ifds.config.loader import Config
from ifds.data.fmp import FMPClient
from ifds.data.fred import FREDClient
from ifds.data.polygon import PolygonClient
from ifds.data.unusual_whales import UnusualWhalesClient
from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity
from ifds.models.market import (
    APIHealthResult,
    APIStatus,
    CircuitBreakerState,
    DiagnosticsResult,
    MacroRegime,
    MarketVolatilityRegime,
)


def run_phase0(config: Config, logger: EventLogger) -> DiagnosticsResult:
    """Execute Phase 0: System Diagnostics.

    Args:
        config: Validated IFDS configuration.
        logger: Event logger for audit trail.

    Returns:
        DiagnosticsResult with API health, circuit breaker, and macro regime.
    """
    start_time = time.monotonic()
    logger.phase_start(0, "System Diagnostics")

    result = DiagnosticsResult()

    # --- Step 1: API Health Checks ---
    result.api_health = _check_all_apis(config, logger)

    critical_failures = [
        h for h in result.api_health
        if h.is_critical and h.status == APIStatus.DOWN
    ]
    result.all_critical_apis_ok = len(critical_failures) == 0

    if not result.all_critical_apis_ok:
        failed_names = [f.provider for f in critical_failures]
        result.halt_reason = f"Critical API(s) down: {', '.join(failed_names)}"
        result.pipeline_can_proceed = False
        logger.halt(result.halt_reason)
        _log_phase_complete(logger, start_time)
        return result

    # --- Step 2: Circuit Breaker ---
    result.circuit_breaker = _check_circuit_breaker(config, logger)

    if result.circuit_breaker.is_active:
        result.halt_reason = (
            f"Circuit breaker active: daily drawdown "
            f"{result.circuit_breaker.daily_drawdown_pct:.1f}% "
            f"> limit {result.circuit_breaker.limit_pct:.1f}%. "
            f"Manual reset required."
        )
        result.pipeline_can_proceed = False
        logger.halt(result.halt_reason)
        _log_phase_complete(logger, start_time)
        return result

    # --- Step 3: Macro Regime ---
    polygon_macro = PolygonClient(
        api_key=config.get_api_key("polygon"),
        timeout=config.runtime["api_timeout_polygon"],
        max_retries=config.runtime["api_max_retries"],
    )
    fred = FREDClient(
        api_key=config.get_api_key("fred"),
        timeout=config.runtime["api_timeout_fred"],
        max_retries=config.runtime["api_max_retries"],
    )
    try:
        result.macro = _assess_macro_regime(config, polygon_macro, fred, logger)
    finally:
        polygon_macro.close()
        fred.close()

    # --- All checks passed ---
    result.pipeline_can_proceed = True
    _log_phase_complete(logger, start_time)

    return result


def _check_all_apis(config: Config, logger: EventLogger) -> list[APIHealthResult]:
    """Check all API endpoints and log results."""
    results: list[APIHealthResult] = []

    # Polygon — OHLCV (critical)
    polygon = PolygonClient(
        api_key=config.get_api_key("polygon"),
        timeout=config.runtime["api_timeout_polygon"],
        max_retries=config.runtime["api_max_retries"],
    )
    health = polygon.check_health()
    results.append(health)
    logger.api_health(health.provider, "aggregates", health.status.value,
                      health.response_time_ms, health.error)

    # Polygon — Options (critical)
    health_opt = polygon.check_options_health()
    results.append(health_opt)
    logger.api_health(health_opt.provider, "options", health_opt.status.value,
                      health_opt.response_time_ms, health_opt.error)

    # Unusual Whales (non-critical, has fallback)
    uw = UnusualWhalesClient(
        api_key=config.get_api_key("unusual_whales"),
        timeout=config.runtime["api_timeout_uw"],
        max_retries=config.runtime["api_max_retries"],
    )
    health_uw = uw.check_health()
    results.append(health_uw)
    logger.api_health(health_uw.provider, "darkpool/greeks", health_uw.status.value,
                      health_uw.response_time_ms, health_uw.error)

    if health_uw.status != APIStatus.OK:
        logger.api_fallback("unusual_whales", "polygon",
                            "UW unavailable — will use Polygon for GEX/Dark Pool")

    # FMP (critical)
    fmp = FMPClient(
        api_key=config.get_api_key("fmp"),
        timeout=config.runtime["api_timeout_fmp"],
        max_retries=config.runtime["api_max_retries"],
    )
    health_fmp = fmp.check_health()
    results.append(health_fmp)
    logger.api_health(health_fmp.provider, "screener", health_fmp.status.value,
                      health_fmp.response_time_ms, health_fmp.error)

    # FRED (critical)
    fred = FREDClient(
        api_key=config.get_api_key("fred"),
        timeout=config.runtime["api_timeout_fred"],
        max_retries=config.runtime["api_max_retries"],
    )
    health_fred = fred.check_health()
    results.append(health_fred)
    logger.api_health(health_fred.provider, "observations", health_fred.status.value,
                      health_fred.response_time_ms, health_fred.error)

    polygon.close()
    uw.close()
    fmp.close()
    fred.close()

    return results


def _check_circuit_breaker(config: Config, logger: EventLogger) -> CircuitBreakerState:
    """Check circuit breaker state from persistent state file.

    The circuit breaker activates when:
        DailyDrawdown > DrawdownLimit_pct

    Manual reset required to deactivate.
    """
    state_file = Path(config.runtime["circuit_breaker_state_file"])
    limit = config.runtime["circuit_breaker_drawdown_limit_pct"]

    state = CircuitBreakerState(
        is_active=False,
        limit_pct=limit,
        last_check=datetime.now(timezone.utc),
    )

    if state_file.exists():
        try:
            with open(state_file) as f:
                data = json.load(f)
            state.is_active = data.get("is_active", False)
            state.daily_drawdown_pct = data.get("daily_drawdown_pct", 0.0)
            if data.get("activated_at"):
                state.activated_at = datetime.fromisoformat(data["activated_at"])
            state.message = data.get("message", "")
        except (json.JSONDecodeError, KeyError) as e:
            state.message = f"Warning: Could not read circuit breaker state: {e}"

    logger.log(
        EventType.CIRCUIT_BREAKER_CHECK,
        Severity.WARNING if state.is_active else Severity.INFO,
        phase=0,
        message=f"Circuit breaker: {'ACTIVE' if state.is_active else 'OK'} "
                f"(drawdown={state.daily_drawdown_pct:.1f}%, limit={limit:.1f}%)",
        data={
            "is_active": state.is_active,
            "daily_drawdown_pct": state.daily_drawdown_pct,
            "limit_pct": limit,
        },
    )

    return state


def _assess_macro_regime(config: Config, polygon: PolygonClient,
                         fred: FREDClient,
                         logger: EventLogger) -> MacroRegime:
    """Assess macro environment using Polygon (primary) and FRED (fallback).

    VIX source chain: Polygon I:VIX → FRED VIXCLS → default 20.0

    VIX classification:
    - <= 15: LOW
    - 15-20: NORMAL
    - 20-30: ELEVATED (VIX penalty active)
    - > 30: PANIC (half-size positions)

    VIX multiplier: max(0.25, 1.0 - (VIX - 20) * 0.02) if VIX > 20

    TNX rate sensitivity:
    - If TNX > SMA20(TNX) * 1.05 → Technology/Real Estate sectors penalized
    """
    # --- VIX: Polygon I:VIX (primary) → FRED VIXCLS (fallback) → 20.0 ---
    vix_value, vix_source = _fetch_vix(polygon, fred, logger)

    vix_regime = _classify_vix(vix_value, config)
    vix_multiplier = _calculate_vix_multiplier(vix_value, config)

    # --- TNX ---
    tnx_observations = fred.get_tnx(limit=25)
    tnx_value = 0.0
    tnx_sma20 = 0.0
    tnx_rate_sensitive = False

    if tnx_observations:
        # Filter out "." values (FRED uses "." for missing data)
        valid_obs = [
            float(o["value"]) for o in tnx_observations
            if o.get("value") and o["value"] != "."
        ]
        if valid_obs:
            tnx_value = valid_obs[0]  # Most recent (sorted desc)
            if len(valid_obs) >= 20:
                tnx_sma20 = sum(valid_obs[:20]) / 20
                tnx_sensitivity_pct = config.tuning["tnx_sensitivity_pct"]
                tnx_rate_sensitive = tnx_value > tnx_sma20 * (1 + tnx_sensitivity_pct / 100)

    macro = MacroRegime(
        vix_value=vix_value,
        vix_regime=vix_regime,
        vix_multiplier=vix_multiplier,
        tnx_value=tnx_value,
        tnx_sma20=tnx_sma20,
        tnx_rate_sensitive=tnx_rate_sensitive,
        timestamp=datetime.now(timezone.utc),
    )

    logger.log(
        EventType.MACRO_REGIME, Severity.INFO, phase=0,
        message=(
            f"Macro: VIX={vix_value:.1f} ({vix_regime.value}, source={vix_source}), "
            f"multiplier={vix_multiplier:.2f}, "
            f"TNX={tnx_value:.2f}, rate_sensitive={tnx_rate_sensitive}"
        ),
        data={
            "vix_value": vix_value,
            "vix_regime": vix_regime.value,
            "vix_multiplier": vix_multiplier,
            "vix_source": vix_source,
            "tnx_value": tnx_value,
            "tnx_sma20": round(tnx_sma20, 3),
            "tnx_rate_sensitive": tnx_rate_sensitive,
        },
    )

    return macro


def _fetch_vix(polygon: PolygonClient, fred: FREDClient,
               logger: EventLogger) -> tuple[float, str]:
    """Fetch VIX with fallback chain: Polygon I:VIX → FRED VIXCLS → default.

    Returns:
        (vix_value, source) where source is "polygon", "fred", or "default".
    """
    # 1. Primary: Polygon I:VIX (real-time)
    try:
        vix = polygon.get_vix(days_back=10)
        if vix is not None:
            vix, valid = _validate_vix(vix, "polygon", logger)
            if valid:
                logger.log(EventType.MACRO_REGIME, Severity.INFO, phase=0,
                           message=f"VIX={vix:.2f} (Polygon I:VIX)")
                return vix, "polygon"
    except Exception as e:
        logger.log(EventType.API_ERROR, Severity.WARNING, phase=0,
                   message=f"Polygon VIX fetch failed: {e}")

    # 2. Fallback: FRED VIXCLS (1-day delayed)
    logger.log(EventType.MACRO_REGIME, Severity.INFO, phase=0,
               message="Polygon VIX unavailable, falling back to FRED VIXCLS")
    fred_vix = _get_latest_fred_value(fred, fred.VIX_SERIES)
    if fred_vix is not None:
        fred_vix, valid = _validate_vix(fred_vix, "fred", logger)
        if valid:
            logger.log(EventType.MACRO_REGIME, Severity.INFO, phase=0,
                       message=f"VIX={fred_vix:.2f} (FRED VIXCLS fallback)")
            return fred_vix, "fred"

    # 3. Default: conservative 20.0
    logger.log(EventType.MACRO_REGIME, Severity.WARNING, phase=0,
               message="VIX data unavailable from all sources, using default=20.0")
    return 20.0, "default"


def _validate_vix(vix: float, source: str, logger: EventLogger) -> tuple[float, bool]:
    """Validate VIX in range [5.0, 100.0]. Out of range → WARNING + default 20.0."""
    if 5.0 <= vix <= 100.0:
        return vix, True

    logger.log(EventType.MACRO_REGIME, Severity.WARNING, phase=0,
               message=f"VIX sanity check FAILED: {vix:.2f} from {source} "
                       f"(outside [5.0, 100.0]) — using default 20.0")
    return 20.0, False


def _get_latest_fred_value(fred: FREDClient, series_id: str) -> float | None:
    """Get the most recent non-missing value from a FRED series."""
    observations = fred.get_series(series_id, limit=5)
    if not observations:
        return None
    for obs in observations:
        val = obs.get("value")
        if val and val != ".":
            try:
                return float(val)
            except ValueError:
                continue
    return None


def _classify_vix(vix: float, config: Config) -> MarketVolatilityRegime:
    """Classify VIX into regime."""
    extreme_threshold = config.tuning.get("vix_extreme_threshold", 50)
    if vix > extreme_threshold:
        return MarketVolatilityRegime.EXTREME
    elif vix > config.tuning["vix_elevated"]:
        return MarketVolatilityRegime.PANIC
    elif vix > config.tuning["vix_normal"]:
        return MarketVolatilityRegime.ELEVATED
    elif vix > config.tuning["vix_low"]:
        return MarketVolatilityRegime.NORMAL
    else:
        return MarketVolatilityRegime.LOW


def _calculate_vix_multiplier(vix: float, config: Config) -> float:
    """Calculate VIX risk multiplier.

    Formula: max(floor, 1.0 - (VIX - threshold) * rate)
    EXTREME override: VIX > extreme_threshold → fixed extreme_multiplier.
    """
    extreme_threshold = config.tuning.get("vix_extreme_threshold", 50)
    if vix > extreme_threshold:
        return config.tuning.get("vix_extreme_multiplier", 0.10)
    threshold = config.tuning["vix_penalty_start"]
    if vix <= threshold:
        return 1.0
    rate = config.tuning["vix_penalty_rate"]
    floor = config.tuning["vix_multiplier_floor"]
    return max(floor, 1.0 - (vix - threshold) * rate)


def _log_phase_complete(logger: EventLogger, start_time: float) -> None:
    """Log phase 0 completion with duration."""
    duration_ms = (time.monotonic() - start_time) * 1000
    logger.phase_complete(0, "System Diagnostics", duration_ms=duration_ms)
