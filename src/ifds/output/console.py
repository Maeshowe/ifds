"""CLI dashboard output for IFDS pipeline.

Colorized terminal output for each pipeline phase.
Based on v13 signal_generator.py dashboard format (lines 118-302).
"""

from __future__ import annotations

import sys
from typing import Any, TYPE_CHECKING

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    _HAS_COLOR = True
except ImportError:
    _HAS_COLOR = False

    # Stub replacements so code runs without colorama
    class _Stub:
        def __getattr__(self, _: str) -> str:
            return ""

    Fore = _Stub()  # type: ignore[assignment]
    Style = _Stub()  # type: ignore[assignment]

if TYPE_CHECKING:
    from ifds.config.loader import Config
    from ifds.models.market import (
        DiagnosticsResult,
        MacroRegime,
        Phase1Result,
        Phase2Result,
        Phase3Result,
        Phase4Result,
        Phase5Result,
        Phase6Result,
        PipelineContext,
        SectorScore,
    )

_SEP = "-" * 105

# Abbreviation maps for fixed-width columns
_SECTOR_SHORT = {
    "Communication Services": "Comm Svc",
}
_BREADTH_SHORT = {
    "CONSOLIDATING": "CONSOL",
}


def _cw(text: str, width: int, color: str = "") -> str:
    """Pad *text* to exactly *width* visible chars, then wrap with color."""
    padded = f"{text:<{width}}"[:width]
    if color:
        return f"{color}{padded}{Style.RESET_ALL}"
    return padded


def print_phase_header(step: int, title: str, goal: str,
                       logic: str, source: str) -> None:
    """Print a standardised phase header block."""
    print(Fore.CYAN + f"\n[ {step}/6 ] {title}")
    print(f"   Cel:    {goal}")
    print(f"   Logika: {logic}")
    print(f"   Forras: {source}")
    print(_SEP)


# =========================================================================
# Phase 0 — Diagnostics
# =========================================================================

def print_diagnostics(diag: DiagnosticsResult) -> None:
    """Print Phase 0 diagnostics summary."""
    print_phase_header(
        0, "System Diagnostics",
        "API connectivity + macro regime",
        "Health check all providers, fetch VIX/TNX",
        "Polygon, FMP, UW, FRED",
    )

    for h in diag.api_health:
        if h.status.value == "ok":
            color = Fore.GREEN
            sym = "OK"
        elif h.status.value == "skipped":
            color = Fore.YELLOW
            sym = "SKIP"
        else:
            color = Fore.RED
            sym = "DOWN"
        ms = f"{h.response_time_ms:.0f}ms" if h.response_time_ms else ""
        crit = " [CRITICAL]" if h.is_critical else ""
        print(f"  {color}{sym:>4}{Style.RESET_ALL}  {h.provider:<18} {h.endpoint:<35} {ms:>8}{crit}")

    if diag.macro:
        m = diag.macro
        vix_color = Fore.GREEN if m.vix_regime.value == "low" else (
            Fore.YELLOW if m.vix_regime.value == "normal" else Fore.RED)
        print(f"\n  Macro: VIX={vix_color}{m.vix_value:.2f}{Style.RESET_ALL}"
              f" ({m.vix_regime.value})  TNX={m.tnx_value:.2f}%"
              f"  Rate-sensitive={m.tnx_rate_sensitive}")

    if diag.pipeline_can_proceed:
        print(Fore.GREEN + "  => Pipeline CAN proceed")
    else:
        print(Fore.RED + f"  => HALT: {diag.halt_reason}")
    print(_SEP)


# =========================================================================
# Phase 1 — BMI / Market Regime
# =========================================================================

def print_phase1(result: Phase1Result,
                 prev_bmi: dict[str, Any] | None = None) -> None:
    """Print Phase 1 BMI result with optional day-over-day change."""
    print_phase_header(
        1, "Market Regime (BMI)",
        "Determine LONG / SHORT strategy",
        "Big Money Index (SMA25 of daily buy/sell ratio)",
        "Polygon grouped daily bars",
    )

    bmi = result.bmi
    regime_color = {
        "green": Fore.GREEN, "yellow": Fore.YELLOW, "red": Fore.RED,
    }.get(bmi.bmi_regime.value, Fore.WHITE)

    # BMI change vs previous day
    change_str = ""
    if prev_bmi and "bmi" in prev_bmi:
        delta = bmi.bmi_value - prev_bmi["bmi"]
        arrow = "+" if delta >= 0 else ""
        chg_color = Fore.GREEN if delta > 0 else (Fore.RED if delta < 0 else Fore.WHITE)
        change_str = f"  [{chg_color}{arrow}{delta:.1f} vs tegnap{Style.RESET_ALL}]"

    print(f"  BMI = {regime_color}{bmi.bmi_value:.1f}%{Style.RESET_ALL}"
          f"  Regime = {regime_color}{bmi.bmi_regime.value.upper()}{Style.RESET_ALL}"
          f"  Strategy = {result.strategy_mode.value.upper()}"
          f"  Tickers used = {result.ticker_count_for_bmi}"
          f"{change_str}")
    if bmi.divergence_detected:
        print(Fore.YELLOW + f"  ! Divergence: {bmi.divergence_type}")
    print(_SEP)


# =========================================================================
# Phase 2 — Universe
# =========================================================================

def print_phase2(result: Phase2Result) -> None:
    """Print Phase 2 universe summary."""
    print_phase_header(
        2, "Universe Building",
        "Screen tradeable tickers",
        "FMP screener + earnings exclusion",
        "FMP Financial Modeling Prep",
    )

    print(f"  Screened: {result.total_screened}"
          f"  Passed: {len(result.tickers)}"
          f"  Earnings excluded: {len(result.earnings_excluded)}")
    print(_SEP)


# =========================================================================
# Phase 3 — Sector Rotation
# =========================================================================

def _sector_change_arrow(etf: str, prev: dict[str, float] | None,
                         current_mom: float) -> str:
    """Return change arrow vs previous day's momentum."""
    if not prev or etf not in prev:
        return ""
    prev_mom = prev[etf]
    if current_mom > prev_mom + 0.01:
        return Fore.GREEN + " ^" + Style.RESET_ALL
    elif current_mom < prev_mom - 0.01:
        return Fore.RED + " v" + Style.RESET_ALL
    return " >"


def print_sector_table(result: Phase3Result,
                       prev_sectors: dict[str, float] | None = None,
                       benchmark: SectorScore | None = None) -> None:
    """Print Phase 3 sector rotation table with change arrows and benchmark."""
    print_phase_header(
        3, "Sector Rotation",
        "Rank sectors, apply VETO logic",
        "Momentum + BMI + MAP-IT per sector",
        "Polygon sector ETF bars",
    )

    # Header — fixed-width columns
    hdr = (f"  {'ETF':<6}| {'SECTOR':<22}| {'SCORE':<6}| "
           f"{'MOMENTUM':<12}| {'STATUS':<10}| {'TREND':<6}| "
           f"{'BMI':<6}| {'REGIME':<10}| "
           f"{'B.SCORE':<7}| {'B.REGIME':<14}| {'VETO':<4}")
    if prev_sectors:
        hdr += "| CHG"
    print(hdr)
    row_width = 6+2+22+2+6+2+12+2+10+2+6+2+6+2+10+2+7+2+14+2+4  # 115
    if prev_sectors:
        row_width += 5
    print("  " + "-" * row_width)

    sectors_sorted = sorted(result.sector_scores,
                            key=lambda s: s.momentum_5d, reverse=True)

    for s in sectors_sorted:
        _print_sector_row(s, prev_sectors)

    # AGG benchmark row (info only, not scored/vetoed)
    if benchmark:
        bm_width = 6+2+22+2+6+2+12+2+10+2+6+2+6+2+10+2+7+2+14+2+4
        if prev_sectors:
            bm_width += 5
        print("  " + "-" * bm_width)
        _print_sector_row(benchmark, prev_sectors, is_benchmark=True)

    vetoed = result.vetoed_sectors
    if vetoed:
        print(Fore.RED + f"\n  Vetoed sectors: {', '.join(vetoed)}")
    print(_SEP)


def _print_sector_row(s: SectorScore,
                      prev_sectors: dict[str, float] | None = None,
                      is_benchmark: bool = False) -> None:
    """Print a single sector row with fixed-width columns."""
    mom = s.momentum_5d
    mom_color = Fore.GREEN if mom > 0 else (Fore.RED if mom < 0 else Fore.WHITE)
    arrow = "^" if mom > 0 else "v"

    if is_benchmark:
        status_str = "Benchmark"
        status_color = Fore.CYAN
        score_str = "--"
        veto_str = ""
    else:
        status_str = s.classification.value.capitalize()
        status_color = (Fore.GREEN if status_str == "Leader"
                        else (Fore.RED if status_str == "Laggard" else Fore.WHITE))
        score_str = f"{s.score_adjustment:+d}"
        veto_str = "YES" if s.vetoed else ""

    trend_color = Fore.GREEN if s.trend.value == "up" else Fore.RED

    bmi_str = f"{s.sector_bmi:.0f}%" if s.sector_bmi is not None else "N/A"
    regime = s.sector_bmi_regime.value.upper()
    regime_color = (Fore.GREEN if regime == "OVERSOLD"
                    else (Fore.RED if regime == "OVERBOUGHT" else Fore.WHITE))

    # Breadth columns (BC14)
    if s.breadth is not None:
        b_score_str = f"{s.breadth.breadth_score:.0f}"
        raw_regime = s.breadth.breadth_regime.value.upper()
        b_regime_str = _BREADTH_SHORT.get(raw_regime, raw_regime)
        b_color = (Fore.GREEN if s.breadth.breadth_score > 70
                   else (Fore.RED if s.breadth.breadth_score < 30 else Fore.WHITE))
        if s.breadth.divergence_detected:
            b_regime_str += " !"
    else:
        b_score_str = "N/A"
        b_regime_str = "N/A"
        b_color = Fore.WHITE

    # Sector name abbreviation
    sector_name = _SECTOR_SHORT.get(s.sector_name, s.sector_name)

    chg = _sector_change_arrow(s.etf, prev_sectors, mom) if prev_sectors else ""

    veto_color = Fore.RED if veto_str else ""
    mom_str = f"{arrow} {mom:+.2f}%"

    line = (f"  {_cw(s.etf, 6)}"
            f"| {_cw(sector_name, 22)}"
            f"| {_cw(score_str, 6)}"
            f"| {_cw(mom_str, 12, mom_color)}"
            f"| {_cw(status_str, 10, status_color)}"
            f"| {_cw(s.trend.value.upper(), 6, trend_color)}"
            f"| {_cw(bmi_str, 6, regime_color)}"
            f"| {_cw(regime, 10, regime_color)}"
            f"| {_cw(b_score_str, 7, b_color)}"
            f"| {_cw(b_regime_str, 14, b_color)}"
            f"| {_cw(veto_str, 4, veto_color)}")
    if chg:
        line += f"| {chg}"
    print(line)


# =========================================================================
# Phase 4 — Scan Summary
# =========================================================================

def print_scan_summary(result: Phase4Result) -> None:
    """Print Phase 4 scan summary — accepted / rejected breakdown."""
    print_phase_header(
        4, "Individual Stock Analysis",
        "Score each ticker (flow + funda + tech)",
        "Multi-factor scoring with sector adjustment",
        "Polygon, FMP, UW dark pool",
    )

    total = len(result.analyzed)
    passed = len(result.passed)
    print(f"  Analyzed: {total}  |  "
          f"{Fore.GREEN}Passed: {passed}{Style.RESET_ALL}  |  "
          f"{Fore.RED}Excluded: {result.excluded_count}{Style.RESET_ALL}")
    print(f"  Breakdown — Tech filter: {result.tech_filter_count}"
          f"  Score < 70: {result.min_score_count}"
          f"  Crowded (>{result.clipping_threshold}): {result.clipped_count}")
    print(_SEP)


# =========================================================================
# Phase 5 — GEX
# =========================================================================

def print_gex_summary(result: Phase5Result) -> None:
    """Print Phase 5 GEX analysis summary."""
    print_phase_header(
        5, "GEX Analysis",
        "Gamma exposure regime per ticker",
        "UW strike-level GEX -> fallback Polygon options",
        "Unusual Whales, Polygon options",
    )

    total = len(result.analyzed)
    passed = len(result.passed)
    print(f"  Analyzed: {total}  |  "
          f"{Fore.GREEN}Passed: {passed}{Style.RESET_ALL}  |  "
          f"{Fore.RED}Excluded (NEGATIVE regime): {result.negative_regime_count}{Style.RESET_ALL}")

    # OBSIDIAN MM regime distribution (BC15)
    if result.obsidian_analyses:
        regime_counts: dict[str, int] = {}
        for o in result.obsidian_analyses:
            regime_counts[o.mm_regime.value] = regime_counts.get(o.mm_regime.value, 0) + 1
        parts = [f"{k}={v}" for k, v in sorted(regime_counts.items())]
        label = "OBSIDIAN" if result.obsidian_enabled else "OBSIDIAN (collect-only)"
        print(f"  {label}: {' | '.join(parts)}")

    print(_SEP)


# =========================================================================
# Phase 6 — Final Summary
# =========================================================================

def print_final_summary(result: Phase6Result, ctx: PipelineContext) -> None:
    """Print Phase 6 position sizing summary and top positions table."""
    print_phase_header(
        6, "Position Sizing & Risk Management",
        "Size positions, apply multipliers, enforce limits",
        "M_total = M_flow x M_insider x M_funda x M_gex x M_vix x M_utility",
        "All prior phases",
    )

    positions = result.positions
    n = len(positions)

    print(f"  Positions: {n}  |  "
          f"Total risk: ${result.total_risk_usd:,.0f}  |  "
          f"Total exposure: ${result.total_exposure_usd:,.0f}")
    print(f"  Excluded — sector limit: {result.excluded_sector_limit}"
          f"  position limit: {result.excluded_position_limit}"
          f"  risk limit: {result.excluded_risk_limit}"
          f"  exposure limit: {result.excluded_exposure_limit}")
    if result.freshness_applied_count:
        print(Fore.CYAN + f"  Freshness Alpha applied to {result.freshness_applied_count} ticker(s)")

    if positions:
        print(f"\n  {'#':<3} {'TICKER':<8} {'SCORE':<7} {'MULT':<7} {'QTY':<5} "
              f"{'ENTRY':<9} {'STOP':<9} {'TP1':<9} {'TP2':<9} {'RISK$':<8} {'GEX':<8} {'FLAGS'}")
        print("  " + "-" * 100)

        for i, pos in enumerate(positions[:20], 1):
            flags = []
            if pos.is_fresh:
                flags.append("FRESH")
            if pos.is_mean_reversion:
                flags.append("MR")
            flag_str = ",".join(flags)

            score_color = Fore.GREEN if pos.combined_score >= 80 else (
                Fore.YELLOW if pos.combined_score >= 70 else Fore.WHITE)

            print(f"  {i:<3} {pos.ticker:<8} "
                  f"{score_color}{pos.combined_score:<7.1f}{Style.RESET_ALL} "
                  f"{pos.multiplier_total:<7.3f} "
                  f"{pos.quantity:<5} "
                  f"${pos.entry_price:<8.2f} "
                  f"${pos.stop_loss:<8.2f} "
                  f"${pos.take_profit_1:<8.2f} "
                  f"${pos.take_profit_2:<8.2f} "
                  f"${pos.risk_usd:<7.0f} "
                  f"{pos.gex_regime:<8} "
                  f"{flag_str}")

    print(_SEP)


# =========================================================================
# Pipeline Result Banner
# =========================================================================

def print_pipeline_result(ctx: PipelineContext, log_file: str | None = None,
                          config: Config | None = None) -> None:
    """Print config summary table then final pipeline result banner."""
    # ── Config summary table (before banner) ──
    if config:
        _print_config_table(config)

    # ── Pipeline result banner ──
    n_pos = len(ctx.positions)
    strategy = (ctx.strategy_mode.value.upper() if ctx.strategy_mode else "N/A")

    print(f"\n{'=' * 105}")
    if n_pos > 0:
        print(Fore.GREEN + f"  PIPELINE COMPLETE — {n_pos} positions sized"
              f"  |  Strategy: {strategy}"
              f"  |  Run: {ctx.run_id}")
    else:
        print(Fore.YELLOW + f"  PIPELINE COMPLETE — No actionable positions"
              f"  |  Strategy: {strategy}"
              f"  |  Run: {ctx.run_id}")

    if ctx.execution_plan_path:
        print(f"  CSV: {ctx.execution_plan_path}")
    if log_file:
        print(f"  Log: {log_file}")
    print("=" * 105)


def _print_config_table(config: Config) -> None:
    """Print configuration summary as a formatted table."""
    r = config.runtime
    t = config.tuning
    c = config.core

    equity = r.get("account_equity", 100_000)
    risk_pct = r.get("risk_per_trade_pct", 0.5)
    risk_usd = equity * risk_pct / 100
    max_pos = r.get("max_positions", 8)
    max_sector = t.get("max_positions_per_sector", 2)
    min_score = t.get("combined_score_minimum", 70)
    clip = c.get("clipping_threshold", 90)
    vix_floor = t.get("vix_multiplier_floor", 0.25)
    w_flow = c.get("weight_flow", 0.40)
    w_funda = c.get("weight_fundamental", 0.30)
    w_tech = c.get("weight_technical", 0.30)
    async_on = "true" if r.get("async_enabled", False) else "false"
    cache_on = "true" if r.get("cache_enabled", False) else "false"

    line = "\u2500" * 43
    print(f"\n  {Fore.CYAN}BEALLITASOK{Style.RESET_ALL}")
    print(f"  {line}")
    print(f"  {'Account equity':<22} ${equity:,.0f}")
    print(f"  {'Risk per trade':<22} {risk_pct}% (${risk_usd:,.0f})")
    print(f"  {'Max positions':<22} {max_pos}")
    print(f"  {'Max per sector':<22} {max_sector}")
    print(f"  {'Min score':<22} {min_score}")
    print(f"  {'Clipping threshold':<22} {clip}")
    print(f"  {'VIX multiplier':<22} {vix_floor} (floor)")
    print(f"  {'Weights':<22} flow={w_flow:.2f} funda={w_funda:.2f} tech={w_tech:.2f}")
    print(f"  {'Async':<22} {async_on}")
    print(f"  {'Cache':<22} {cache_on}")
    print(f"  {line}")
