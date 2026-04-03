"""Pipeline runner — orchestrates phase execution."""

import sys
import time
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

    pipeline_t0 = time.monotonic()

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

        _t = time.monotonic()
        diag = run_phase0(config, logger)
        logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                   message=f"Phase 0 completed in {time.monotonic() - _t:.1f}s")
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

        # === Sector mapping for per-sector BMI + Phase 1 ===
        sector_mapping = None
        _t = time.monotonic()
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
            logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                       message=f"Phase 1 completed in {time.monotonic() - _t:.1f}s")

        # === Phase 2: Universe Building ===
        _t = time.monotonic()
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
            logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                       message=f"Phase 2 completed in {time.monotonic() - _t:.1f}s")

        # === Phase 3: Sector Rotation ===
        _t = time.monotonic()
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

                ctx.agg_benchmark = agg_benchmark
                print_sector_table(phase3, prev_sectors=prev_sectors,
                                   benchmark=agg_benchmark)
            finally:
                polygon3.close()
                if fmp3:
                    fmp3.close()
                # Memory cleanup: free grouped daily bars (BC14)
                ctx.grouped_daily_bars = []
            logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                       message=f"Phase 3 completed in {time.monotonic() - _t:.1f}s")

        # --- Context persistence: save after Phase 3, load before Phase 4 ---
        if isinstance(phase, tuple) and phase[1] <= 3:
            from ifds.pipeline.context_persistence import save_phase13_context
            save_phase13_context(ctx)
            logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                       message="Phase 1-3 context saved to state/phase13_ctx.json.gz")

        if isinstance(phase, tuple) and phase[0] >= 4 and ctx.macro is None:
            from ifds.pipeline.context_persistence import load_phase13_context
            if load_phase13_context(ctx):
                logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                           message="Phase 1-3 context loaded from state/phase13_ctx.json.gz")
            else:
                logger.log(EventType.PHASE_DIAGNOSTIC, Severity.WARNING,
                           message="Phase 1-3 context not found — Phase 4-6 may fail")

        # === Phase 4: Individual Stock Analysis ===
        _t = time.monotonic()
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
                logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                           message=f"Phase 4 completed in {time.monotonic() - _t:.1f}s")

        # === Phase 5: GEX Analysis ===
        _t = time.monotonic()
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
                    # Pass polygon5 for MMS (BC15) — cached bars/options
                    mms_on = config.tuning.get("mms_enabled", False)
                    always_collect = config.tuning.get("mms_store_always_collect", True)
                    pass_polygon = polygon5 if (mms_on or always_collect) else None
                    phase5 = run_phase5(
                        config, logger, gex_provider, ctx.stock_analyses, strategy,
                        polygon=pass_polygon,
                    )
                    ctx.phase5 = phase5
                    ctx.gex_analyses = phase5.passed
                    ctx.mms_analyses = phase5.mms_analyses
                    print_gex_summary(phase5)
                finally:
                    polygon5.close()
                    if uw5 is not None:
                        uw5.close()
                logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                           message=f"Phase 5 completed in {time.monotonic() - _t:.1f}s")

        # === Phase 6: Position Sizing & Risk Management ===
        _t = time.monotonic()
        if _should_run(phase, 6):
            if not ctx.gex_analyses or not ctx.stock_analyses:
                logger.log(EventType.PHASE_SKIP, Severity.WARNING, phase=6,
                           message="No candidates from Phase 4/5 — skipping Phase 6")
            else:
                from ifds.phases.phase6_sizing import get_bmi_momentum_guard, run_phase6
                from ifds.output.execution_plan import write_execution_plan

                # BMI Momentum Guard — reduce max_positions on declining BMI trend
                bmi_guard_active = False
                original_max_positions = config.runtime["max_positions"]
                if config.tuning.get("bmi_momentum_guard_enabled", True):
                    entries = bmi_history.load()
                    guard_active, reduced, total_delta = get_bmi_momentum_guard(entries, config)
                    if guard_active:
                        min_days = config.tuning.get("bmi_momentum_days", 3)
                        logger.log(EventType.PHASE_DIAGNOSTIC, Severity.WARNING, phase=6,
                                   message=f"[BMI GUARD] BMI declining {min_days}+ days "
                                           f"(delta={total_delta:+.1f}) → max_positions: "
                                           f"{original_max_positions} → {reduced}",
                                   data={"total_delta": total_delta, "reduced": reduced})
                        config.runtime["max_positions"] = reduced
                        bmi_guard_active = True
                        # Telegram alert
                        try:
                            from ifds.output.telegram import _send_message, _pipeline_timestamp
                            _token = config.runtime.get("telegram_bot_token")
                            _chat = config.runtime.get("telegram_chat_id")
                            if _token and _chat:
                                _send_message(
                                    _token, _chat,
                                    f"{_pipeline_timestamp()}\n"
                                    f"⚠️ <b>BMI MOMENTUM GUARD aktív</b>\n"
                                    f"BMI {min_days}+ napja csökken (delta={total_delta:+.1f})\n"
                                    f"Max pozíciók: {original_max_positions} → {reduced}",
                                    timeout=10,
                                )
                        except Exception:
                            pass

                # Cross-Asset Regime — position/score overrides (BC21)
                original_min_score = config.tuning.get("combined_score_minimum", 70)
                if ctx.macro and ctx.macro.cross_asset_regime != "NORMAL":
                    ca_regime = ctx.macro.cross_asset_regime
                    if ca_regime == "CRISIS":
                        ca_max = config.tuning.get("cross_asset_crisis_max_positions", 4)
                        ca_min_score = config.tuning.get("cross_asset_crisis_min_score", 80)
                    elif ca_regime == "RISK_OFF":
                        ca_max = config.tuning.get("cross_asset_risk_off_max_positions", 6)
                        ca_min_score = config.tuning.get("cross_asset_risk_off_min_score", 75)
                    else:
                        ca_max = None
                        ca_min_score = None

                    if ca_max is not None:
                        config.runtime["max_positions"] = min(config.runtime["max_positions"], ca_max)
                    if ca_min_score is not None:
                        config.tuning["combined_score_minimum"] = ca_min_score

                    logger.log(EventType.PHASE_DIAGNOSTIC, Severity.WARNING, phase=6,
                               message=f"[CROSS-ASSET] {ca_regime}: "
                                       f"max_positions={config.runtime['max_positions']}, "
                                       f"min_score={config.tuning.get('combined_score_minimum', 70)}, "
                                       f"VIX threshold={ctx.macro.vix_threshold_adjusted:.0f}")

                    try:
                        from ifds.output.telegram import _send_message, _pipeline_timestamp
                        _token = config.runtime.get("telegram_bot_token")
                        _chat = config.runtime.get("telegram_chat_id")
                        _emojis = {"CAUTIOUS": "\u26a0\ufe0f", "RISK_OFF": "\U0001f534", "CRISIS": "\U0001f6a8"}
                        if _token and _chat:
                            _send_message(
                                _token, _chat,
                                f"{_pipeline_timestamp()}\n"
                                f"{_emojis.get(ca_regime, '')} <b>CROSS-ASSET: {ca_regime}</b>\n"
                                f"Votes: {ctx.macro.cross_asset_votes:.1f}\n"
                                f"Max pozíciók: {config.runtime['max_positions']} | "
                                f"Min score: {config.tuning.get('combined_score_minimum', 70)}\n"
                                f"VIX threshold: {ctx.macro.vix_threshold_adjusted:.0f}",
                                timeout=10,
                            )
                    except Exception:
                        pass

                # Skip Day Shadow Guard — log only, does NOT block pipeline
                from ifds.phases.phase6_sizing import check_skip_day_shadow
                if not config.tuning.get("bmi_momentum_guard_enabled", True):
                    entries = bmi_history.load()
                would_skip, skip_details = check_skip_day_shadow(ctx.macro, entries, config)
                if would_skip:
                    logger.log(EventType.PHASE_DIAGNOSTIC, Severity.WARNING, phase=6,
                               message=f"[SKIP DAY SHADOW] Would skip today — "
                                       f"VIX={skip_details['vix_value']:.1f} >= {skip_details['vix_threshold']}, "
                                       f"BMI declining {skip_details['bmi_consecutive_decline']} days "
                                       f">= {skip_details['bmi_min_days']}",
                               data=skip_details)
                    try:
                        from ifds.output.telegram import _send_message, _pipeline_timestamp
                        _token = config.runtime.get("telegram_bot_token")
                        _chat = config.runtime.get("telegram_chat_id")
                        if _token and _chat:
                            _send_message(
                                _token, _chat,
                                f"{_pipeline_timestamp()}\n"
                                f"\U0001f47b <b>SKIP DAY SHADOW</b> — ha éles lenne, ma 0 pozíció\n"
                                f"VIX={skip_details['vix_value']:.1f} (küszöb: {skip_details['vix_threshold']})\n"
                                f"BMI {skip_details['bmi_consecutive_decline']} napja csökken "
                                f"(küszöb: {skip_details['bmi_min_days']})",
                                timeout=10,
                            )
                    except Exception:
                        pass
                # Save shadow state for later evaluation
                try:
                    import json as _json
                    from datetime import date as _date
                    _shadow_file = config.runtime.get("skip_day_shadow_file",
                                                       "state/skip_day_shadow.jsonl")
                    with open(_shadow_file, "a") as _f:
                        _f.write(_json.dumps({
                            "date": _date.today().isoformat(),
                            "would_skip": would_skip,
                            **skip_details,
                        }) + "\n")
                except OSError:
                    pass

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
                    mms_analyses=ctx.mms_analyses,
                    bmi_value=ctx.bmi_value,
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

                # Restore original max_positions and min_score after guard overrides
                config.runtime["max_positions"] = original_max_positions
                config.tuning["combined_score_minimum"] = original_min_score

                print_final_summary(phase6, ctx)
                logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                           message=f"Phase 6 completed in {time.monotonic() - _t:.1f}s")

        duration = time.monotonic() - pipeline_t0
        logger.log(EventType.PIPELINE_END, Severity.INFO,
                   message=f"Pipeline run complete in {duration:.1f}s.")

        # Phase 4 Snapshot (BC19 — SIM-L2 data prep)
        if config.runtime.get("phase4_snapshot_enabled", True) and ctx.stock_analyses:
            try:
                from ifds.data.phase4_snapshot import save_phase4_snapshot
                snap_dir = config.runtime.get("phase4_snapshot_dir",
                                              "state/phase4_snapshots")
                snap_path = save_phase4_snapshot(ctx.stock_analyses, snap_dir)
                logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                           message=f"Phase 4 snapshot saved: {snap_path}")
            except Exception as e:
                logger.log(EventType.CONFIG_WARNING, Severity.WARNING,
                           message=f"Phase 4 snapshot error: {e}")

        log_file = str(logger.log_file)
        print_pipeline_result(ctx, log_file, config=config)

        # Telegram — only on full pipeline runs (not --phase N or dry_run)
        if phase is None and not dry_run:
            try:
                from ifds.output.telegram import send_daily_report
                from ifds.data.fmp import FMPClient as FMPTelegram
                fmp_tg = FMPTelegram(
                    api_key=config.get_api_key("fmp"),
                    timeout=config.runtime["api_timeout_fmp"],
                    max_retries=config.runtime["api_max_retries"],
                    cache=cache,
                    circuit_breaker=cb_fmp,
                )
                try:
                    send_daily_report(ctx, config, logger, duration, fmp=fmp_tg)
                finally:
                    fmp_tg.close()
            except Exception as e:
                logger.log(EventType.CONFIG_WARNING, Severity.WARNING,
                           message=f"Telegram error: {e}")

        return PipelineResult(
            success=True,
            message="Pipeline complete.",
            context=ctx,
            log_file=log_file,
        )

    finally:
        logger.close()


def _should_run(requested_phase: int | tuple[int, int] | None, current_phase: int) -> bool:
    """Check if a phase should run given the --phase or --phases flag.

    Args:
        requested_phase: Single phase (int), range tuple (start, end), or None (all).
        current_phase: Phase number being checked.
    """
    if requested_phase is None:
        return True  # Run all phases
    if isinstance(requested_phase, tuple):
        return requested_phase[0] <= current_phase <= requested_phase[1]
    return requested_phase == current_phase


def parse_phase_range(phases_str: str) -> tuple[int, int]:
    """Parse phase range string like ``"1-3"`` or ``"4-6"``.

    Returns:
        (start, end) tuple of phase numbers.

    Raises:
        ValueError: If format is invalid.
    """
    if "-" not in phases_str:
        n = int(phases_str)
        return (n, n)
    parts = phases_str.split("-", 1)
    start, end = int(parts[0]), int(parts[1])
    if not (0 <= start <= 6) or not (0 <= end <= 6) or start > end:
        raise ValueError(f"Invalid phase range: {phases_str} (must be 0-6)")
    return (start, end)


def check_system(config_path: str | None = None) -> PipelineResult:
    """Validate configuration and API connectivity (Phase 0 only)."""
    return run_pipeline(phase=0, dry_run=True, config_path=config_path)
