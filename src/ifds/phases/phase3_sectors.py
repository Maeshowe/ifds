"""Phase 3: Sector Rotation & Momentum.

Analyzes the 11 SPDR sector ETFs to determine:
1. Momentum ranking (5-day relative performance)
2. Trend (Price vs SMA20)
3. Leader / Neutral / Laggard classification
4. Sector BMI with per-sector oversold/overbought thresholds
5. Veto Matrix for LONG strategy
6. TNX rate sensitivity for Tech/Real Estate

The veto matrix (LONG strategy):
| Momentum | Sector BMI   | Decision          | Score adj |
|----------|-------------|-------------------|-----------|
| Leader   | Any         | ALLOWED           | +15       |
| Neutral  | NEUTRAL     | ALLOWED           | 0         |
| Neutral  | OVERSOLD    | ALLOWED           | 0         |
| Neutral  | OVERBOUGHT  | VETO              | —         |
| Laggard  | OVERSOLD    | ALLOWED (MR)      | -5        |
| Laggard  | NEUTRAL     | VETO              | —         |
| Laggard  | OVERBOUGHT  | VETO              | —         |
"""

import time
from datetime import date, timedelta

from ifds.config.loader import Config
from ifds.data.polygon import PolygonClient
from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity
from ifds.models.market import (
    MacroRegime,
    MomentumClassification,
    Phase3Result,
    SectorBMIRegime,
    SectorScore,
    SectorTrend,
    StrategyMode,
)

# ETF → Sector Name mapping
SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLV": "Healthcare",
    "XLI": "Industrials",
    "XLP": "Consumer Defensive",
    "XLY": "Consumer Cyclical",
    "XLB": "Basic Materials",
    "XLC": "Communication Services",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
}


def run_phase3(config: Config, logger: EventLogger,
               polygon: PolygonClient,
               strategy_mode: StrategyMode,
               macro: MacroRegime | None = None,
               sector_bmi_values: dict[str, float] | None = None) -> Phase3Result:
    """Execute Phase 3: Sector Rotation analysis.

    Args:
        config: Validated IFDS configuration.
        logger: Event logger for audit trail.
        polygon: Polygon client for ETF price data.
        strategy_mode: LONG or SHORT from Phase 1.
        macro: Macro regime from Phase 0 (for TNX rate sensitivity).

    Returns:
        Phase3Result with sector scores, vetoes, and active sectors.
    """
    start_time = time.monotonic()
    logger.phase_start(3, "Sector Rotation")

    try:
        momentum_period = config.tuning["sector_momentum_period"]
        sma_period = config.core["sma_short_period"]  # SMA20

        # Fetch price data for all sector ETFs
        sector_data = _fetch_sector_data(polygon, momentum_period, sma_period)

        # Calculate momentum and trend for each sector
        scores = _calculate_sector_scores(sector_data, config)

        # Populate sector BMI from Phase 1 data
        if sector_bmi_values:
            for score in scores:
                if score.etf in sector_bmi_values:
                    score.sector_bmi = sector_bmi_values[score.etf]

        # Rank and classify (Leader / Neutral / Laggard)
        _rank_sectors(scores, config)

        # Apply sector BMI regimes
        _apply_sector_bmi(scores, config)

        # Apply veto matrix (only for LONG strategy)
        if strategy_mode == StrategyMode.LONG:
            _apply_veto_matrix(scores, config, logger)

        # Apply TNX rate sensitivity
        rate_sensitive = False
        if macro and macro.tnx_rate_sensitive:
            rate_sensitive = True
            _apply_rate_sensitivity(scores, config, logger)

        # Build result
        vetoed = [s.etf for s in scores if s.vetoed]
        active = [s.etf for s in scores if not s.vetoed]

        result = Phase3Result(
            sector_scores=scores,
            vetoed_sectors=vetoed,
            active_sectors=active,
            rate_sensitive_penalty=rate_sensitive,
        )

        # Log summary
        logger.log(
            EventType.PHASE_COMPLETE, Severity.INFO, phase=3,
            message=(
                f"Sectors: {len(active)} active, {len(vetoed)} vetoed"
                f"{', rate_sensitive' if rate_sensitive else ''}"
            ),
            data={
                "active_count": len(active),
                "vetoed_count": len(vetoed),
                "vetoed_sectors": vetoed,
                "leaders": [s.etf for s in scores
                            if s.classification == MomentumClassification.LEADER],
                "laggards": [s.etf for s in scores
                             if s.classification == MomentumClassification.LAGGARD],
                "rate_sensitive_penalty": rate_sensitive,
            },
        )

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.phase_complete(3, "Sector Rotation", duration_ms=duration_ms)

        return result

    except Exception as e:
        logger.phase_error(3, "Sector Rotation", str(e))
        raise


def _fetch_sector_data(polygon: PolygonClient,
                       momentum_period: int,
                       sma_period: int,
                       etf_override: dict[str, str] | None = None) -> dict[str, dict]:
    """Fetch OHLCV data for sector ETFs (or custom ETF list).

    Args:
        etf_override: If set, fetch only these ETFs instead of SECTOR_ETFS.

    Returns dict: etf -> {bars: [...], close_today, close_5d_ago, sma20}
    """
    today = date.today()
    # Need enough calendar days to cover trading days for SMA20
    lookback = max(momentum_period, sma_period) + 15  # Buffer for weekends/holidays
    from_date = (today - timedelta(days=lookback)).isoformat()
    to_date = today.isoformat()

    sector_data = {}
    etf_list = etf_override or SECTOR_ETFS

    for etf in etf_list:
        bars = polygon.get_aggregates(etf, from_date, to_date)
        if not bars or len(bars) < momentum_period + 1:
            continue

        closes = [b["c"] for b in bars if "c" in b]
        if len(closes) < momentum_period + 1:
            continue

        close_today = closes[-1]
        close_period_ago = closes[-(momentum_period + 1)]

        # SMA20
        sma20 = None
        if len(closes) >= sma_period:
            sma20 = sum(closes[-sma_period:]) / sma_period

        sector_data[etf] = {
            "bars": bars,
            "close_today": close_today,
            "close_period_ago": close_period_ago,
            "sma20": sma20,
        }

    return sector_data


def _calculate_sector_scores(sector_data: dict[str, dict],
                             config: Config,
                             name_override: dict[str, str] | None = None) -> list[SectorScore]:
    """Calculate momentum and trend for each sector.

    Args:
        name_override: If set, use these names instead of SECTOR_ETFS lookup.
    """
    scores = []
    names = name_override or SECTOR_ETFS

    for etf, data in sector_data.items():
        close_today = data["close_today"]
        close_ago = data["close_period_ago"]
        sma20 = data["sma20"]

        # Momentum = 5d relative performance %
        if close_ago > 0:
            momentum = ((close_today - close_ago) / close_ago) * 100
        else:
            momentum = 0.0

        # Trend = UP if price > SMA20
        if sma20 and sma20 > 0:
            trend = SectorTrend.UP if close_today > sma20 else SectorTrend.DOWN
        else:
            trend = SectorTrend.UP  # Default

        score = SectorScore(
            etf=etf,
            sector_name=names.get(etf, etf),
            momentum_5d=round(momentum, 3),
            trend=trend,
        )
        scores.append(score)

    return scores


def _rank_sectors(scores: list[SectorScore], config: Config) -> None:
    """Rank sectors by momentum and classify as Leader/Neutral/Laggard."""
    leader_count = config.tuning["sector_leader_count"]
    laggard_count = config.tuning["sector_laggard_count"]
    leader_bonus = config.tuning["sector_leader_bonus"]
    laggard_penalty = config.tuning["sector_laggard_penalty"]

    # Sort by momentum descending
    sorted_scores = sorted(scores, key=lambda s: s.momentum_5d, reverse=True)

    for rank, score in enumerate(sorted_scores, 1):
        score.rank = rank

        if rank <= leader_count:
            score.classification = MomentumClassification.LEADER
            score.score_adjustment = leader_bonus
        elif rank > len(sorted_scores) - laggard_count:
            score.classification = MomentumClassification.LAGGARD
            score.score_adjustment = laggard_penalty
        else:
            score.classification = MomentumClassification.NEUTRAL
            score.score_adjustment = 0


def _apply_sector_bmi(scores: list[SectorScore], config: Config) -> None:
    """Apply sector-specific BMI thresholds.

    Note: Full sector BMI calculation requires per-ticker volume data
    within each sector. For now, we use the sector ETF's momentum
    as a proxy for sector health. When sector BMI is set externally
    (e.g., from a pre-calculated data source), it overrides this.
    """
    thresholds = config.tuning["sector_bmi_thresholds"]

    for score in scores:
        if score.sector_bmi is not None:
            # Use pre-calculated sector BMI
            bounds = thresholds.get(score.etf, (12, 80))
            oversold_threshold, overbought_threshold = bounds

            if score.sector_bmi < oversold_threshold:
                score.sector_bmi_regime = SectorBMIRegime.OVERSOLD
            elif score.sector_bmi > overbought_threshold:
                score.sector_bmi_regime = SectorBMIRegime.OVERBOUGHT
            else:
                score.sector_bmi_regime = SectorBMIRegime.NEUTRAL


def _apply_veto_matrix(scores: list[SectorScore], config: Config,
                       logger: EventLogger) -> None:
    """Apply the LONG strategy veto matrix.

    Rules:
    - Leader + Any BMI regime → ALLOWED (+15)
    - Neutral + NEUTRAL/OVERSOLD → ALLOWED (0)
    - Neutral + OVERBOUGHT → VETO
    - Laggard + OVERSOLD → ALLOWED (Mean Reversion, -5)
    - Laggard + NEUTRAL → VETO
    - Laggard + OVERBOUGHT → VETO
    """
    mr_penalty = config.tuning["sector_laggard_mr_penalty"]

    for score in scores:
        cls = score.classification
        bmi = score.sector_bmi_regime

        if cls == MomentumClassification.LEADER:
            # Leaders always pass
            score.vetoed = False

        elif cls == MomentumClassification.NEUTRAL:
            if bmi == SectorBMIRegime.OVERBOUGHT:
                score.vetoed = True
                score.veto_reason = "Neutral + Overbought"
            else:
                score.vetoed = False

        elif cls == MomentumClassification.LAGGARD:
            if bmi == SectorBMIRegime.OVERSOLD:
                # Mean Reversion opportunity
                score.vetoed = False
                score.score_adjustment = mr_penalty
                score.veto_reason = None
            else:
                score.vetoed = True
                score.veto_reason = f"Laggard + {bmi.value}"

        if score.vetoed:
            logger.log(
                EventType.SECTOR_VETO, Severity.INFO, phase=3,
                message=f"Sector VETO: {score.etf} ({score.sector_name}) — {score.veto_reason}",
                data={
                    "etf": score.etf,
                    "classification": cls.value,
                    "sector_bmi_regime": bmi.value,
                    "reason": score.veto_reason,
                },
            )


def _apply_rate_sensitivity(scores: list[SectorScore], config: Config,
                            logger: EventLogger) -> None:
    """Apply TNX rate sensitivity penalty to sensitive sectors.

    When TNX > SMA20 * 1.05, Technology and Real Estate get additional penalty.
    """
    sensitive_sectors = config.tuning["tnx_sensitive_sectors"]

    for score in scores:
        if score.sector_name in sensitive_sectors and not score.vetoed:
            score.score_adjustment -= 10  # Rate sensitivity penalty
            logger.log(
                EventType.SECTOR_VETO, Severity.INFO, phase=3,
                message=f"Rate sensitivity: {score.etf} ({score.sector_name}) -10 penalty",
                data={
                    "etf": score.etf,
                    "sector_name": score.sector_name,
                    "penalty": -10,
                    "reason": "TNX rate sensitivity",
                },
            )
