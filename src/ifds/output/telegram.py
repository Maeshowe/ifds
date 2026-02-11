"""Telegram daily report — unified pipeline summary (BC13, updated BC15+).

Sends a single merged daily report to Telegram via Bot API.
Only active when both IFDS_TELEGRAM_BOT_TOKEN and IFDS_TELEGRAM_CHAT_ID are set.
Non-blocking: failures are logged but never halt the pipeline.
"""

from __future__ import annotations

from datetime import date

import requests

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity
from ifds.models.market import BaselineState, PipelineContext


def send_daily_report(ctx: PipelineContext, config: Config,
                      logger: EventLogger, duration: float) -> bool:
    """Send unified pipeline daily report to Telegram.

    Single message combining health + exec plan. Always sends (even 0 positions).

    Args:
        ctx: Pipeline context with all phase results.
        config: Pipeline config.
        logger: Event logger.
        duration: Pipeline wall-clock duration in seconds.

    Returns:
        True if sent successfully, False otherwise.
    """
    token = config.runtime.get("telegram_bot_token")
    chat_id = config.runtime.get("telegram_chat_id")
    timeout = config.runtime.get("telegram_timeout", 5)

    if not token or not chat_id:
        logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                   message="Telegram disabled (no credentials)")
        return False

    try:
        text = _format_success(ctx, duration, config)
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()

        logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                   message="Telegram daily report sent")
        return True

    except Exception as e:
        logger.log(EventType.CONFIG_WARNING, Severity.WARNING,
                   message=f"Telegram daily report failed: {e}")
        return False


def send_failure_report(error: str, config: Config,
                        logger: EventLogger, duration: float) -> bool:
    """Send pipeline failure notification to Telegram.

    Args:
        error: Exception message.
        config: Pipeline config.
        logger: Event logger.
        duration: Pipeline wall-clock duration in seconds.

    Returns:
        True if sent successfully, False otherwise.
    """
    token = config.runtime.get("telegram_bot_token")
    chat_id = config.runtime.get("telegram_chat_id")
    timeout = config.runtime.get("telegram_timeout", 5)

    if not token or not chat_id:
        return False

    try:
        text = (
            f"\U0001f6a8 *IFDS FAILED* \u2014 {date.today().isoformat()}\n"
            f"Error: `{error}`\n"
            f"Duration: {duration:.1f}s"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()

        logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                   message="Telegram failure report sent")
        return True

    except Exception as e:
        logger.log(EventType.CONFIG_WARNING, Severity.WARNING,
                   message=f"Telegram failure report failed: {e}")
        return False


def _format_success(ctx: PipelineContext, duration: float,
                    config: Config) -> str:
    """Format the unified success report."""
    lines = [f"\U0001f4ca *IFDS Daily Report* \u2014 {date.today().isoformat()}"]
    lines.append(f"Pipeline: \u2705 OK ({duration:.1f}s)")

    # Phase 1: BMI + Strategy
    if ctx.bmi_value is not None:
        regime = ctx.bmi_regime.value if ctx.bmi_regime else "?"
        strategy = ctx.strategy_mode.value if ctx.strategy_mode else "?"
        lines.append(f"BMI: {regime} ({ctx.bmi_value:.1f}%) \u2192 {strategy}")

    # Phase 3: Sectors
    if ctx.sector_scores:
        leaders = sum(1 for s in ctx.sector_scores if not s.vetoed and s.classification.value == "leader")
        laggards = sum(1 for s in ctx.sector_scores if not s.vetoed and s.classification.value == "laggard")
        neutrals = sum(1 for s in ctx.sector_scores if not s.vetoed) - leaders - laggards
        vetoed = len(ctx.vetoed_sectors)
        lines.append(f"Sectors: {leaders} leader / {neutrals} neutral / {laggards} laggard ({vetoed} vetoed)")

    # Phase 3: Breadth
    if ctx.sector_scores:
        breadth_sectors = [s for s in ctx.sector_scores if s.breadth is not None]
        if breadth_sectors:
            regime_counts: dict[str, int] = {}
            for s in breadth_sectors:
                r = s.breadth.breadth_regime.value
                regime_counts[r] = regime_counts.get(r, 0) + 1
            dominant = max(regime_counts, key=regime_counts.get)  # type: ignore[arg-type]
            lines.append(f"Breadth: {dominant} ({len(breadth_sectors)}/11)")

    # Phase 4: Scanned
    if ctx.phase4:
        lines.append(f"Scanned: {len(ctx.phase4.analyzed)} \u2192 {len(ctx.phase4.passed)} accepted")

    # Phase 5: GEX
    if ctx.phase5:
        lines.append(f"GEX: {len(ctx.phase5.passed)} passed / {ctx.phase5.excluded_count} excluded")

    # Phase 5: OBSIDIAN
    if ctx.phase5 and ctx.obsidian_analyses:
        obsidian_enabled = config.tuning.get("obsidian_enabled", False)
        status = "ENABLED" if obsidian_enabled else "collect-only"
        states = {"complete": 0, "partial": 0, "empty": 0}
        for o in ctx.obsidian_analyses:
            states[o.baseline_state.value] = states.get(o.baseline_state.value, 0) + 1
        n_tickers = len(ctx.obsidian_analyses)
        if states["complete"] > 0:
            day_est = "21+"
        elif states["partial"] > 0:
            day_est = "~10"
        else:
            day_est = "1"
        min_periods = config.core.get("obsidian_min_periods", 21)
        lines.append(f"OBSIDIAN: {status} (day {day_est}/{min_periods})")
        lines.append(f"  Store: {n_tickers} tickers updated")
        lines.append(
            f"  Baseline: {states['complete']} complete / "
            f"{states['partial']} partial / {states['empty']} empty"
        )

    # Phase 6: Exec Plan
    positions = ctx.phase6.positions if ctx.phase6 else []
    if positions:
        total_risk = sum(p.risk_usd for p in positions)
        lines.append(f"\nExec Plan: {len(positions)} positions (${total_risk:,.0f} risk)")
        # Max 4 tickers per line
        for i in range(0, len(positions), 4):
            batch = positions[i:i + 4]
            lines.append(" | ".join(f"{p.ticker} ${p.risk_usd:.0f}" for p in batch))
    else:
        lines.append("\n_No positions today._")

    return "\n".join(lines)
