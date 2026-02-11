"""Pipeline runner — orchestrates phase execution."""

import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ifds.config.loader import Config
from ifds.config.validator import ConfigValidationError
from ifds.data.circuit_breaker import ProviderCircuitBreaker
from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity
from ifds.models.market import PipelineContext, StrategyMode


@dataclass
class PipelineResult:
    """Result of a pipeline run."""
    success: bool
    message: str
    phase_results: list = field(default_factory=list)
    context: PipelineContext | None = None
    log_file: str | None = None


def run_pipeline(phase: int | None = None, dry_run: bool = False,
                 config_path: str | None = None) -> PipelineResult:
    """Run the IFDS trading signal pipeline.

    Args:
        phase: Run only a specific phase (0-6), or None for all.
        dry_run: If True, only validate config and API health.
        config_path: Path to custom config file.

    Returns:
        PipelineResult with success status and details.
    """
    print("IFDS Pipeline v2.0")
    print("=" * 40)

    # --- Load and validate configuration ---
    try:
        config = Config(config_path=config_path)
    except ConfigValidationError as e:
        print(f"\n[HALT] {e}", file=sys.stderr)
        return PipelineResult(success=False, message=str(e))

    # --- Initialize cache ---
    cache = None
    if config.runtime.get("cache_enabled", False):
        from ifds.data.cache import FileCache
        cache = FileCache(cache_dir=config.runtime.get("cache_dir", "data/cache"))

    # --- Initialize per-provider circuit breakers ---
    cb_window = config.runtime.get("cb_window_size", 50)
    cb_threshold = config.runtime.get("cb_error_threshold", 0.3)
    cb_cooldown = config.runtime.get("cb_cooldown_seconds", 60)
    cb_polygon = ProviderCircuitBreaker("polygon", cb_window, cb_threshold, cb_cooldown)
    cb_fmp = ProviderCircuitBreaker("fmp", cb_window, cb_threshold, cb_cooldown)
    cb_uw = ProviderCircuitBreaker("uw", cb_window, cb_threshold, cb_cooldown)
    cb_fred = ProviderCircuitBreaker("fred", cb_window, cb_threshold, cb_cooldown)

    # --- Initialize logging ---
    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    logger = EventLogger(log_dir=config.runtime["log_dir"], run_id=run_id)

    logger.log(EventType.PIPELINE_START, Severity.INFO,
               message=f"Pipeline started (run_id={run_id})",
               data={"dry_run": dry_run, "single_phase": phase})

    # --- Build pipeline context (Info #12: snapshot config) ---
    ctx = PipelineContext(
        run_id=run_id,
        started_at=datetime.now(timezone.utc),
        config_snapshot={
            "account_equity": config.runtime["account_equity"],
            "risk_per_trade_pct": config.runtime["risk_per_trade_pct"],
            "max_positions": config.runtime["max_positions"],
            "uw_configured": config.get_api_key("unusual_whales") is not None,
        },
    )

    try:
        # === Phase 0: System Diagnostics (always runs — mandatory safety check) ===
        from ifds.phases.phase0_diagnostics import run_phase0

        diag = run_phase0(config, logger)
        ctx.diagnostics = diag
        ctx.macro = diag.macro
        ctx.uw_available = diag.uw_available

        from ifds.output.console import (
            print_diagnostics, print_phase1, print_phase2,
            print_sector_table, print_scan_summary, print_gex_summary,
            print_final_summary, print_pipeline_result,
        )
        from ifds.state.history import BMIHistory, SectorHistory
        bmi_history = BMIHistory(state_dir=config.runtime.get("state_dir", "state"))
        sector_history = SectorHistory(state_dir=config.runtime.get("state_dir", "state"))

        print_diagnostics(diag)

        if not diag.pipeline_can_proceed:
            logger.log(EventType.PIPELINE_END, Severity.ERROR,
                       message=f"Pipeline halted: {diag.halt_reason}")
            return PipelineResult(
                success=False,
                message=f"HALT: {diag.halt_reason}",
                context=ctx,
                log_file=str(logger.log_file),
            )

        if dry_run:
            logger.log(EventType.PIPELINE_END, Severity.INFO,
                       message="Dry run complete — all checks passed.")
            return PipelineResult(
                success=True,
                message="Dry run complete — all diagnostics passed.",
                context=ctx,
                log_file=str(logger.log_file),
            )

        # === Sector mapping for per-sector BMI ===
        sector_mapping = None
        if _should_run(phase, 1):
            from ifds.data.fmp import FMPClient as FMPClient1
            fmp1 = FMPClient1(
                api_key=config.get_api_key("fmp"),
                timeout=config.runtime["api_timeout_fmp"],
                max_retries=config.runtime["api_max_retries"],
                cache=cache,
                circuit_breaker=cb_fmp,
            )
            try:
                sector_mapping = fmp1.get_sector_mapping()
            finally:
                fmp1.close()

        # === Phase 1: Market Regime (BMI) ===
        if _should_run(phase, 1):
            from ifds.phases.phase1_regime import run_phase1
            from ifds.data.polygon import PolygonClient

            polygon = PolygonClient(
                api_key=config.get_api_key("polygon"),
                timeout=config.runtime["api_timeout_polygon"],
                max_retries=config.runtime["api_max_retries"],
                cache=cache,
                circuit_breaker=cb_polygon,
            )
            try:
                phase1 = run_phase1(config, logger, polygon,
                                    sector_mapping=sector_mapping)
                ctx.phase1 = phase1
                ctx.strategy_mode = phase1.strategy_mode
                ctx.bmi_regime = phase1.bmi.bmi_regime
                ctx.bmi_value = phase1.bmi.bmi_value
                ctx.sector_bmi_values = phase1.sector_bmi_values
                ctx.grouped_daily_bars = phase1.grouped_daily_bars  # BC14
                prev_bmi = bmi_history.get_previous()
                bmi_history.append(phase1.bmi.bmi_value, phase1.bmi.bmi_regime.value)
                print_phase1(phase1, prev_bmi=prev_bmi)
            finally:
                polygon.close()

        # === Phase 2: Universe Building ===
        if _should_run(phase, 2):
            from ifds.phases.phase2_universe import run_phase2
            from ifds.data.fmp import FMPClient

            strategy = ctx.strategy_mode or StrategyMode.LONG
            fmp = FMPClient(
                api_key=config.get_api_key("fmp"),
                timeout=config.runtime["api_timeout_fmp"],
                max_retries=config.runtime["api_max_retries"],
                cache=cache,
                circuit_breaker=cb_fmp,
            )
            try:
                phase2 = run_phase2(config, logger, fmp, strategy)
                ctx.phase2 = phase2
                ctx.universe = phase2.tickers
                print_phase2(phase2)
            finally:
                fmp.close()

        # === Phase 3: Sector Rotation ===
        if _should_run(phase, 3):
            from ifds.phases.phase3_sectors import run_phase3
            from ifds.data.polygon import PolygonClient as PolygonClient3

            polygon3 = PolygonClient3(
                api_key=config.get_api_key("polygon"),
                timeout=config.runtime["api_timeout_polygon"],
                max_retries=config.runtime["api_max_retries"],
                cache=cache,
                circuit_breaker=cb_polygon,
            )
            # FMP client for breadth analysis (BC14)
            fmp3 = None
            breadth_enabled = config.tuning.get("breadth_enabled", False)
            if breadth_enabled and ctx.grouped_daily_bars:
                from ifds.data.fmp import FMPClient as FMPClient3
                fmp3 = FMPClient3(
                    api_key=config.get_api_key("fmp"),
                    timeout=config.runtime["api_timeout_fmp"],
                    max_retries=config.runtime["api_max_retries"],
                    cache=cache,
                    circuit_breaker=cb_fmp,
                )

            try:
                strategy = ctx.strategy_mode or StrategyMode.LONG
                phase3 = run_phase3(config, logger, polygon3, strategy, ctx.macro,
                                     sector_bmi_values=ctx.sector_bmi_values or None,
                                     grouped_daily_bars=ctx.grouped_daily_bars or None,
                                     fmp=fmp3)
                ctx.phase3 = phase3
                ctx.sector_scores = phase3.sector_scores
                ctx.vetoed_sectors = phase3.vetoed_sectors

                # Sector history: save + get previous for change arrows
                sector_mom = {s.etf: s.momentum_5d for s in phase3.sector_scores}
                prev_sectors = sector_history.get_previous()
                sector_history.append(sector_mom)

                # AGG benchmark: fetch but do NOT include in scoring/veto
                from ifds.phases.phase3_sectors import _fetch_sector_data, _calculate_sector_scores
                agg_data = _fetch_sector_data(polygon3, config.tuning["sector_momentum_period"],
                                              config.core["sma_short_period"],
                                              etf_override={"AGG": "Bonds (Benchmark)"})
                agg_benchmark = None
                if agg_data:
                    agg_scores = _calculate_sector_scores(agg_data, config,
                                                          name_override={"AGG": "Bonds (Benchmark)"})
                    agg_benchmark = agg_scores[0] if agg_scores else None

                print_sector_table(phase3, prev_sectors=prev_sectors,
                                   benchmark=agg_benchmark)
            finally:
                polygon3.close()
                if fmp3:
                    fmp3.close()
                # Memory cleanup: free grouped daily bars (BC14)
                ctx.grouped_daily_bars = []

        # === Phase 4: Individual Stock Analysis ===
        if _should_run(phase, 4):
            if not ctx.universe:
                logger.log(EventType.PHASE_SKIP, Severity.WARNING, phase=4,
                           message="No tickers from Phase 2 — skipping Phase 4")
            else:
                from ifds.phases.phase4_stocks import run_phase4
                from ifds.data.polygon import PolygonClient as PolygonClient4
                from ifds.data.fmp import FMPClient as FMPClient4
                from ifds.data.adapters import FallbackDarkPoolProvider

                polygon4 = PolygonClient4(
                    api_key=config.get_api_key("polygon"),
                    timeout=config.runtime["api_timeout_polygon"],
                    max_retries=config.runtime["api_max_retries"],
                    cache=cache,
                    circuit_breaker=cb_polygon,
                )
                fmp4 = FMPClient4(
                    api_key=config.get_api_key("fmp"),
                    timeout=config.runtime["api_timeout_fmp"],
                    max_retries=config.runtime["api_max_retries"],
                    cache=cache,
                    circuit_breaker=cb_fmp,
                )

                # Dark Pool provider: batch prefetch if UW available
                dp_provider = None
                uw_client = None
                if ctx.uw_available:
                    from ifds.data.unusual_whales import UnusualWhalesClient
                    uw_client = UnusualWhalesClient(
                        api_key=config.get_api_key("unusual_whales"),
                        timeout=config.runtime["api_timeout_uw"],
                        max_retries=config.runtime["api_max_retries"],
                        cache=cache,
                        circuit_breaker=cb_uw,
                    )
                    from ifds.data.adapters import UWBatchDarkPoolProvider
                    batch_dp = UWBatchDarkPoolProvider(
                        uw_client, logger=logger,
                        max_pages=config.runtime.get("dp_batch_max_pages", 15),
                        page_delay=config.runtime.get("dp_batch_page_delay", 0.5),
                    )
                    batch_dp.prefetch()
                    dp_provider = FallbackDarkPoolProvider(
                        batch_dp, logger=logger,
                    )

                try:
                    strategy = ctx.strategy_mode or StrategyMode.LONG
                    phase4 = run_phase4(
                        config, logger, polygon4, fmp4, dp_provider,
                        ctx.universe, ctx.sector_scores, strategy,
                    )
                    ctx.phase4 = phase4
                    ctx.stock_analyses = phase4.passed

                    # Write full scan matrix CSV
                    from ifds.output.execution_plan import write_full_scan_matrix
                    write_full_scan_matrix(
                        phase4.analyzed, ctx.sector_scores or [],
                        (ctx.strategy_mode or StrategyMode.LONG).value,
                        config.runtime["output_dir"], run_id, logger,
                    )
                    print_scan_summary(phase4)
                finally:
                    polygon4.close()
                    fmp4.close()
                    if uw_client:
                        uw_client.close()

        # === Phase 5: GEX Analysis ===
        if _should_run(phase, 5):
            if not ctx.stock_analyses:
                logger.log(EventType.PHASE_SKIP, Severity.WARNING, phase=5,
                           message="No stocks from Phase 4 — skipping Phase 5")
            else:
                from ifds.phases.phase5_gex import run_phase5
                from ifds.data.adapters import (
                    FallbackGEXProvider, UWGEXProvider, PolygonGEXProvider,
                )
                from ifds.data.polygon import PolygonClient as PolygonClient5

                polygon5 = PolygonClient5(
                    api_key=config.get_api_key("polygon"),
                    timeout=config.runtime["api_timeout_polygon_options"],
                    max_retries=config.runtime["api_max_retries"],
                    cache=cache,
                    circuit_breaker=cb_polygon,
                )

                # GEX provider: UW primary → Polygon fallback
                max_dte = config.tuning.get("gex_max_dte", 35)
                uw5 = None
                if ctx.uw_available:
                    from ifds.data.unusual_whales import UnusualWhalesClient as UW5
                    uw5 = UW5(
                        api_key=config.get_api_key("unusual_whales"),
                        timeout=config.runtime["api_timeout_uw"],
                        max_retries=config.runtime["api_max_retries"],
                        cache=cache,
                        circuit_breaker=cb_uw,
                    )
                    gex_provider = FallbackGEXProvider(
                        UWGEXProvider(uw5),
                        PolygonGEXProvider(polygon5, max_dte=max_dte),
                        logger=logger,
                    )
                else:
                    gex_provider = PolygonGEXProvider(polygon5, max_dte=max_dte)

                try:
                    strategy = ctx.strategy_mode or StrategyMode.LONG
                    # Pass polygon5 for OBSIDIAN (BC15) — cached bars/options
                    obsidian_on = config.tuning.get("obsidian_enabled", False)
                    always_collect = config.tuning.get("obsidian_store_always_collect", True)
                    pass_polygon = polygon5 if (obsidian_on or always_collect) else None
                    phase5 = run_phase5(
                        config, logger, gex_provider, ctx.stock_analyses, strategy,
                        polygon=pass_polygon,
                    )
                    ctx.phase5 = phase5
                    ctx.gex_analyses = phase5.passed
                    ctx.obsidian_analyses = phase5.obsidian_analyses
                    print_gex_summary(phase5)
                finally:
                    polygon5.close()
                    if uw5 is not None:
                        uw5.close()

        # === Phase 6: Position Sizing & Risk Management ===
        if _should_run(phase, 6):
            if not ctx.gex_analyses or not ctx.stock_analyses:
                logger.log(EventType.PHASE_SKIP, Severity.WARNING, phase=6,
                           message="No candidates from Phase 4/5 — skipping Phase 6")
            else:
                from ifds.phases.phase6_sizing import run_phase6
                from ifds.output.execution_plan import write_execution_plan

                strategy = ctx.strategy_mode or StrategyMode.LONG
                phase6 = run_phase6(
                    config, logger,
                    ctx.stock_analyses,
                    ctx.gex_analyses,
                    ctx.macro,
                    strategy,
                    signal_history_path=config.runtime["signal_history_file"],
                    sector_scores=ctx.sector_scores,
                    signal_hash_file=config.runtime.get("signal_hash_file"),
                    obsidian_analyses=ctx.obsidian_analyses,
                )
                ctx.phase6 = phase6
                ctx.positions = phase6.positions

                # Output generation
                if phase6.positions:
                    plan_path = write_execution_plan(
                        phase6.positions,
                        config.runtime["output_dir"],
                        run_id,
                        logger,
                    )
                    ctx.execution_plan_path = plan_path

                    # Write trade plan CSV
                    from ifds.output.execution_plan import write_trade_plan
                    write_trade_plan(
                        phase6.positions, ctx.stock_analyses,
                        config.runtime["output_dir"], run_id, logger,
                    )

                print_final_summary(phase6, ctx)

                # Telegram alerts (BC13) — non-blocking, optional
                try:
                    from ifds.output.telegram import send_trade_alerts
                    send_trade_alerts(
                        phase6.positions, strategy.value, config, logger,
                    )
                except Exception as e:
                    logger.log(EventType.CONFIG_WARNING, Severity.WARNING,
                               message=f"Telegram module error: {e}")

        logger.log(EventType.PIPELINE_END, Severity.INFO,
                   message="Pipeline run complete.")

        log_file = str(logger.log_file)
        print_pipeline_result(ctx, log_file, config=config)

        return PipelineResult(
            success=True,
            message="Pipeline complete.",
            context=ctx,
            log_file=log_file,
        )

    finally:
        logger.close()


def _should_run(requested_phase: int | None, current_phase: int) -> bool:
    """Check if a phase should run given the --phase flag."""
    if requested_phase is None:
        return True  # Run all phases
    return requested_phase == current_phase


def check_system(config_path: str | None = None) -> PipelineResult:
    """Validate configuration and API connectivity (Phase 0 only)."""
    return run_pipeline(phase=0, dry_run=True, config_path=config_path)
