"""Telegram daily report — full pipeline summary (BC13, rewritten BC15+).

Sends the complete pipeline output to Telegram via Bot API,
mirroring the console dashboard structure with HTML formatting.
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

# Telegram message size limit
_MAX_MSG_LEN = 4096

# Breadth regime abbreviations (same as console.py)
_BREADTH_SHORT = {
    "CONSOLIDATING": "CONSOL",
}


def send_daily_report(ctx: PipelineContext, config: Config,
                      logger: EventLogger, duration: float) -> bool:
    """Send full pipeline daily report to Telegram.

    Mirrors console dashboard structure with HTML formatting.
    Splits into 2 messages if >4096 chars.

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
        part1, part2 = _format_success(ctx, duration, config)

        ok = _send_message(token, chat_id, part1, timeout)
        if ok and part2:
            _send_message(token, chat_id, part2, timeout)

        logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                   message="Telegram daily report sent")
        return ok

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
            f"\U0001f6a8 <b>IFDS FAILED</b> \u2014 {date.today().isoformat()}\n"
            f"Error: {_esc(str(error))}\n"
            f"Duration: {duration:.1f}s"
        )
        ok = _send_message(token, chat_id, text, timeout)

        logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                   message="Telegram failure report sent")
        return ok

    except Exception as e:
        logger.log(EventType.CONFIG_WARNING, Severity.WARNING,
                   message=f"Telegram failure report failed: {e}")
        return False


# ============================================================================
# Formatting
# ============================================================================

def _esc(text: str) -> str:
    """Escape HTML special characters for Telegram."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _format_success(ctx: PipelineContext, duration: float,
                    config: Config) -> tuple[str, str]:
    """Format the full pipeline report in HTML.

    Returns (part1, part2). part2 is empty string if message fits in one.
    If total > 4096, part1 = Phase 0-4, part2 = Phase 5-6.
    """
    lines_04 = _format_phases_0_to_4(ctx, duration, config)
    lines_56 = _format_phases_5_to_6(ctx, config)

    full = lines_04 + "\n" + lines_56
    if len(full) <= _MAX_MSG_LEN:
        return full, ""

    # Split: Phase 0-4 in first message, Phase 5-6 in second
    return lines_04, lines_56


def _format_phases_0_to_4(ctx: PipelineContext, duration: float,
                          config: Config) -> str:
    """Format Phase 0 through Phase 4."""
    lines: list[str] = []

    # Header
    lines.append(
        f"\U0001f4ca <b>IFDS Daily Report</b> \u2014 {date.today().isoformat()}"
    )

    # Phase 0: System Diagnostics
    lines.append("")
    lines.append(f"<b>[ 0/6 ] System Diagnostics</b>")
    lines.append(f"Pipeline: \u2705 OK ({duration:.1f}s)")
    if ctx.macro:
        m = ctx.macro
        lines.append(
            f"Macro: VIX={m.vix_value:.2f} ({m.vix_regime.value})"
            f"  TNX={m.tnx_value:.2f}%"
            f"  Rate-sensitive={m.tnx_rate_sensitive}"
        )

    # Phase 1: BMI
    lines.append("")
    lines.append(f"<b>[ 1/6 ] Market Regime (BMI)</b>")
    if ctx.phase1:
        bmi = ctx.phase1.bmi
        lines.append(
            f"BMI = {bmi.bmi_value:.1f}%"
            f"  Regime = {bmi.bmi_regime.value.upper()}"
            f"  Strategy = {ctx.phase1.strategy_mode.value.upper()}"
            f"  Tickers used = {ctx.phase1.ticker_count_for_bmi}"
        )
    elif ctx.bmi_value is not None:
        regime = ctx.bmi_regime.value.upper() if ctx.bmi_regime else "?"
        strategy = ctx.strategy_mode.value.upper() if ctx.strategy_mode else "?"
        lines.append(f"BMI = {ctx.bmi_value:.1f}%  Regime = {regime}  Strategy = {strategy}")

    # Phase 2: Universe
    lines.append("")
    lines.append(f"<b>[ 2/6 ] Universe Building</b>")
    if ctx.phase2:
        lines.append(
            f"Screened: {ctx.phase2.total_screened}"
            f"  Passed: {len(ctx.phase2.tickers)}"
            f"  Earnings excluded: {len(ctx.phase2.earnings_excluded)}"
        )

    # Phase 3: Sector Rotation
    lines.append("")
    lines.append(f"<b>[ 3/6 ] Sector Rotation</b>")
    if ctx.sector_scores:
        lines.append(_format_sector_table(ctx.sector_scores, benchmark=ctx.agg_benchmark))
        if ctx.vetoed_sectors:
            lines.append(f"Vetoed sectors: {', '.join(ctx.vetoed_sectors)}")

    # Phase 4: Stock Analysis
    lines.append("")
    lines.append(f"<b>[ 4/6 ] Individual Stock Analysis</b>")
    if ctx.phase4:
        p4 = ctx.phase4
        lines.append(
            f"Analyzed: {len(p4.analyzed)}"
            f"  |  Passed: {len(p4.passed)}"
            f"  |  Excluded: {p4.excluded_count}"
        )
        lines.append(
            f"Breakdown \u2014 Tech filter: {p4.tech_filter_count}"
            f"  Score &lt; 70: {p4.min_score_count}"
            f"  Crowded (&gt;{p4.clipping_threshold}): {p4.clipped_count}"
        )

    return "\n".join(lines)


def _format_phases_5_to_6(ctx: PipelineContext, config: Config) -> str:
    """Format Phase 5 and Phase 6."""
    lines: list[str] = []

    # Phase 5: GEX Analysis
    lines.append(f"<b>[ 5/6 ] GEX Analysis</b>")
    if ctx.phase5:
        p5 = ctx.phase5
        lines.append(
            f"Analyzed: {len(p5.analyzed)}"
            f"  |  Passed: {len(p5.passed)}"
            f"  |  Excluded (NEGATIVE regime): {p5.negative_regime_count}"
        )

        # Breadth summary
        if ctx.sector_scores:
            breadth_sectors = [s for s in ctx.sector_scores if s.breadth is not None]
            if breadth_sectors:
                regime_counts: dict[str, int] = {}
                for s in breadth_sectors:
                    r = s.breadth.breadth_regime.value
                    regime_counts[r] = regime_counts.get(r, 0) + 1
                dominant = max(regime_counts, key=regime_counts.get)  # type: ignore[arg-type]
                lines.append(f"Breadth: {dominant} ({len(breadth_sectors)}/11)")

        # OBSIDIAN
        if ctx.obsidian_analyses:
            obsidian_enabled = config.tuning.get("obsidian_enabled", False)
            status = "ENABLED" if obsidian_enabled else "collect-only"

            regime_counts_obs: dict[str, int] = {}
            for o in ctx.obsidian_analyses:
                regime_counts_obs[o.mm_regime.value] = regime_counts_obs.get(o.mm_regime.value, 0) + 1
            parts = [f"{k}={v}" for k, v in sorted(regime_counts_obs.items())]
            label = "OBSIDIAN" if obsidian_enabled else "OBSIDIAN (collect-only)"
            lines.append(f"{label}: {' '.join(parts)}")

            # Day estimation and baseline
            states = {"complete": 0, "partial": 0, "empty": 0}
            for o in ctx.obsidian_analyses:
                states[o.baseline_state.value] = states.get(o.baseline_state.value, 0) + 1
            if ctx.obsidian_analyses:
                max_days = max(o.baseline_days for o in ctx.obsidian_analyses)
            else:
                max_days = 0
            min_periods = config.core.get("obsidian_min_periods", 21)
            lines.append(f"OBSIDIAN: {status} (day {max_days}/{min_periods})")
            lines.append(
                f"Baseline: {states['complete']} complete"
                f" / {states['partial']} partial"
                f" / {states['empty']} empty"
            )

    # Phase 6: Position Sizing
    lines.append("")
    lines.append(f"<b>[ 6/6 ] Position Sizing</b>")
    if ctx.phase6:
        p6 = ctx.phase6
        positions = p6.positions
        lines.append(
            f"Positions: {len(positions)}"
            f"  |  Risk: ${p6.total_risk_usd:,.0f}"
            f"  |  Exposure: ${p6.total_exposure_usd:,.0f}"
        )
        lines.append(
            f"Excluded \u2014 sector limit: {p6.excluded_sector_limit}"
            f"  position limit: {p6.excluded_position_limit}"
            f"  risk limit: {p6.excluded_risk_limit}"
            f"  exposure limit: {p6.excluded_exposure_limit}"
        )
        if p6.freshness_applied_count:
            lines.append(f"Freshness Alpha applied to {p6.freshness_applied_count} ticker(s)")

        if positions:
            lines.append(_format_exec_table(positions))
        else:
            lines.append("<i>No positions today.</i>")

    return "\n".join(lines)


def _format_sector_table(sector_scores: list, benchmark=None) -> str:
    """Format sector table as monospace <pre> block."""
    rows: list[str] = []
    header = (
        f"{'ETF':<5}"
        f"{'MOMENTUM':>9} "
        f"{'STATUS':<9}"
        f"{'TREND':<6}"
        f"{'BMI':<5}"
        f"{'REGIME':<9}"
        f"{'B.SCR':<6}"
        f"{'B.REGIME':<8}"
    )
    rows.append(header)

    sorted_scores = sorted(sector_scores, key=lambda s: s.momentum_5d, reverse=True)

    for s in sorted_scores:
        mom = s.momentum_5d
        arrow = "^" if mom > 0 else "v"
        mom_str = f"{arrow} {mom:+.2f}%"
        status = s.classification.value.capitalize()
        trend = s.trend.value.upper()

        bmi_str = f"{s.sector_bmi:.0f}%" if s.sector_bmi is not None else "N/A"
        regime = s.sector_bmi_regime.value.upper()

        if s.breadth is not None:
            b_score_str = f"{s.breadth.breadth_score:.0f}"
            raw_regime = s.breadth.breadth_regime.value.upper()
            b_regime_str = _BREADTH_SHORT.get(raw_regime, raw_regime)
        else:
            b_score_str = "N/A"
            b_regime_str = "N/A"

        row = (
            f"{s.etf:<5}"
            f"{mom_str:>9} "
            f"{status:<9}"
            f"{trend:<6}"
            f"{bmi_str:<5}"
            f"{regime:<9}"
            f"{b_score_str:<6}"
            f"{b_regime_str:<8}"
        )
        rows.append(row)

    if benchmark is not None:
        rows.append("-" * len(header))

        mom = benchmark.momentum_5d
        arrow = "^" if mom > 0 else "v"
        mom_str = f"{arrow} {mom:+.2f}%"

        bmi_str = f"{benchmark.sector_bmi:.0f}%" if benchmark.sector_bmi is not None else "N/A"
        regime = benchmark.sector_bmi_regime.value.upper()

        if benchmark.breadth is not None:
            b_score_str = f"{benchmark.breadth.breadth_score:.0f}"
            raw_regime = benchmark.breadth.breadth_regime.value.upper()
            b_regime_str = _BREADTH_SHORT.get(raw_regime, raw_regime)
        else:
            b_score_str = "N/A"
            b_regime_str = "N/A"

        row = (
            f"{benchmark.etf:<5}"
            f"{mom_str:>9} "
            f"{'Benchmark':<9}"
            f"{'--':<6}"
            f"{bmi_str:<5}"
            f"{regime:<9}"
            f"{b_score_str:<6}"
            f"{b_regime_str:<8}"
        )
        rows.append(row)

    return "<pre>" + "\n".join(rows) + "</pre>"


def _format_exec_table(positions: list) -> str:
    """Format execution plan table as monospace <pre> block."""
    rows: list[str] = []
    header = (
        f"{'TICKER':<7}"
        f"{'QTY':>4} "
        f"{'ENTRY':>8} "
        f"{'STOP':>8} "
        f"{'TP1':>8} "
        f"{'TP2':>8} "
        f"{'RISK$':>6}"
    )
    rows.append(header)

    for p in positions:
        row = (
            f"{p.ticker:<7}"
            f"{p.quantity:>4} "
            f"${p.entry_price:>7.2f} "
            f"${p.stop_loss:>7.2f} "
            f"${p.take_profit_1:>7.2f} "
            f"${p.take_profit_2:>7.2f} "
            f"${p.risk_usd:>5.0f}"
        )
        rows.append(row)

    return "<pre>" + "\n".join(rows) + "</pre>"


# ============================================================================
# HTTP helper
# ============================================================================

def _send_message(token: str, chat_id: str, text: str,
                  timeout: int = 5) -> bool:
    """Send a single Telegram message via Bot API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    return True
