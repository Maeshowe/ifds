#!/usr/bin/env python3
"""FRL — weekly batch orchestrator (spec §10).

Runs on the MacBook, weekly, after the Friday sync. Never touches the Mini and
never writes into the sync-mirrored trees.

Order of operations is load-bearing:
  1. sanity gate  — a factor that fails never becomes an attempt (R1#6)
  2. PENDING rows — written before any metric is computed (G4)
  3. metrics      — per era, never pooled (G5)
  4. deflation    — over the ledger's whole history, including old KILLs
  5. decisions    — closed onto the same ledger rows
  6. report       — research/runs/<date>/report.md

Usage:
    python scripts/research/run_frl_batch.py --hyp HYP-004
    python scripts/research/run_frl_batch.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import factors.base as factor_base  # noqa: E402
import factors  # noqa: E402
import frl_config as cfg  # noqa: E402
import frl_cost  # noqa: E402
import frl_holdout  # noqa: E402
import frl_ic  # noqa: E402
import frl_ledger as ledger  # noqa: E402
import frl_lint  # noqa: E402
import frl_loader as loader  # noqa: E402
import frl_report  # noqa: E402
import frl_returns  # noqa: E402


def _git_ref() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=cfg.PROJECT_ROOT,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _polygon_client():
    from ifds.data.polygon import PolygonClient

    api_key = os.environ.get("IFDS_POLYGON_API_KEY")
    if not api_key:
        raise RuntimeError("IFDS_POLYGON_API_KEY is not set — source .env first")
    return PolygonClient(api_key=api_key, timeout=20, cache=frl_returns.research_cache())


def _era_panels(windows: frl_holdout.Windows) -> dict[str, loader.PanelResult]:
    """Dev-window panels per era (the holdout window is never loaded here)."""
    panels: dict[str, loader.PanelResult] = {}
    legacy = loader.load_panel(cfg.LEGACY_START, cfg.LEGACY_END)
    if legacy.days:
        panels[cfg.ERA_LEGACY] = legacy
    swing = loader.load_panel(cfg.SWING_START, windows.dev_end)
    if swing.days:
        panels[cfg.ERA_SWING] = swing
    return panels


def run_batch(
    run_date: date | None = None,
    hyp_filter: str | None = None,
    factor_filter: str | None = None,
    dry_run: bool = False,
    ledger_path: Path | None = None,
    runs_dir: Path | None = None,
    returns_frame=None,
    hypothesis_dir: Path | None = None,
) -> str:
    """Execute one batch and return the rendered report.

    ``returns_frame`` lets a caller (or a test) inject the forward-return panel.
    When it is None the batch uses the parquet cache, and only reaches for the
    Polygon API if the cache is cold — never implicitly during tests, which
    always inject.
    """
    factors.load_all()
    available = loader.available_days()
    if not available:
        raise RuntimeError("no scan matrices found — nothing to test")
    run_date = run_date or available[-1]

    selected = [
        f
        for f in factor_base.all_factors()
        if (hyp_filter is None or f.hyp_id == hyp_filter)
        and (factor_filter is None or f.name == factor_filter)
    ]

    # --- 1. sanity gate + hypothesis-first gate ----------------------------
    # Order matters: a factor must both compute correctly (sanity) and serve a
    # written, registered hypothesis (lint) before it may become an attempt.
    sanity_lines: list[str] = []
    runnable = []
    for factor in selected:
        result = factor_base.run_sanity(factor)
        sanity_lines.append(result.line())
        if not result.passed:
            continue
        try:
            frl_lint.assert_runnable(factor.hyp_id, directory=hypothesis_dir)
        except frl_lint.HypothesisNotRunnable as exc:
            sanity_lines.append(f"BLOCKED {factor.name}: {exc}")
            continue
        runnable.append(factor)

    windows = frl_holdout.compute_windows(run_date, first_day=cfg.SWING_START)
    panels = _era_panels(windows)
    cost_model = frl_cost.build_cost_model(out_path=None if dry_run else cfg.COST_MODEL_PATH)

    results: list[frl_report.FactorResult] = []
    anomalies: dict[str, int] = {}
    missing: list[date] = []
    unexpected: list[date] = []
    for panel in panels.values():
        missing.extend(panel.missing_days)
        unexpected.extend(panel.unexpected_missing)
        for key, value in panel.anomalies.items():
            anomalies[key] = anomalies.get(key, 0) + value

    if returns_frame is None:
        returns_frame = frl_returns.load_cached_returns()
    if returns_frame is None and runnable and not dry_run:
        client = _polygon_client()
        try:
            first_day = min(p.days[0] for p in panels.values())
            returns_frame = frl_returns.build_return_matrix(
                first_day,
                run_date,
                client,
                tickers=sorted({t for p in panels.values() for t in p.frame["ticker"]}),
            )
        finally:
            client.close()

    code_ref = _git_ref()
    for factor in runnable:
        for horizon in cfg.IC_HORIZONS:
            era_summaries: dict[str, dict] = {}
            costed: dict[str, dict] = {}
            sigma_by_era: dict[str, float] = {}
            half_life = float("nan")

            spec = ledger.AttemptSpec(
                hyp_id=factor.hyp_id,
                variant=f"{factor.name}_h{horizon}",
                data_lane=factor.data_lane,
                dev_window={
                    era: [p.days[0].isoformat(), p.days[-1].isoformat()]
                    for era, p in panels.items()
                },
                n_days_used={era: len(p.days) for era, p in panels.items()},
                code_ref=f"factors/{factor.name}.py@{code_ref}",
                horizon=horizon,
            )
            # G4: the row exists before a single number is computed.
            attempt_id = "" if dry_run else ledger.open_attempt(spec, path=ledger_path)

            for era, panel in panels.items():
                # Returns are merged FIRST: factors may consume trailing (past_*)
                # columns, so they must be present before compute() runs.
                frame = panel.frame.copy()
                if returns_frame is not None:
                    frame = frame.merge(returns_frame, on=["date", "ticker"], how="left")
                frame["_factor"] = factor.compute(frame).to_numpy()
                return_col = f"fwd_ret_{horizon}"
                if return_col not in frame.columns:
                    continue
                ic_series = frl_ic.daily_ic(frame, "_factor", return_col)
                era_summaries[era] = frl_ic.aggregate(ic_series, horizon, era).to_dict()
                sigma_by_era[era] = frl_ic.cross_sectional_sigma(frame, return_col)
                if era == cfg.ERA_SWING:
                    half_life = frl_ic.half_life(frame, "_factor")

            cost_bps = frl_ic.implied_turnover_cost_bps(
                half_life, cost_model.get("cost_bps_per_side", cfg.FALLBACK_COST_BPS_PER_SIDE)
            )
            for era, summary in era_summaries.items():
                costed[era] = frl_ic.costed_view(
                    summary.get("mean_ic", float("nan")),
                    sigma_by_era.get(era, float("nan")),
                    horizon,
                    cost_bps,
                ).to_dict()
            results.append(
                frl_report.FactorResult(
                    factor=factor.name,
                    hyp_id=factor.hyp_id,
                    data_lane=factor.data_lane,
                    expected_sign=factor.expected_sign,
                    horizon=horizon,
                    era_summaries=era_summaries,
                    decision=ledger.PENDING,
                    half_life_days=half_life,
                    implied_cost_bps=cost_bps,
                    attempt_id=attempt_id,
                    costed=costed,
                )
            )

    # --- 4. deflation over the ledger's whole history ----------------------
    history = ledger.read_ledger(ledger_path)
    provisional = [
        {
            "hyp_id": r.hyp_id,
            "data_lane": r.data_lane,
            "decision": "PROVISIONAL",
            "metrics": {era: {"p": s.get("p_value")} for era, s in r.era_summaries.items()},
        }
        for r in results
    ]
    closed_history = [e for e in history if e.get("decision") != ledger.PENDING]
    deflation_rows = ledger.deflate(closed_history + provisional)
    bh_by_family = {
        (row["hyp_id"], row["data_lane"], row["era"]): row["bh_pass"] for row in deflation_rows
    }

    # --- 5. decisions ------------------------------------------------------
    for result in results:
        bh_pass = any(
            bh_by_family.get((result.hyp_id, result.data_lane, era), False)
            for era in result.era_summaries
        )
        verdict = frl_holdout.promote_verdict(result.era_summaries, result.expected_sign, bh_pass)
        result.decision = verdict.decision
        result.reasons = verdict.reasons
        if not dry_run:
            ledger.close_attempt(
                result.attempt_id,
                metrics=result.era_summaries,
                decision=verdict.decision,
                decision_note="; ".join(verdict.reasons),
                half_life_days=(
                    None
                    if result.half_life_days != result.half_life_days
                    else result.half_life_days
                ),
                implied_turnover_cost_bps=(
                    None
                    if result.implied_cost_bps != result.implied_cost_bps
                    else result.implied_cost_bps
                ),
                path=ledger_path,
            )

    parked_retests = [
        entry.get("hyp_id", "?")
        for entry in history
        if entry.get("decision") == "PARK_UNTIL_SWING_POWER"
        and any(
            frl_holdout.retest_due(entry, r.era_summaries.get(cfg.ERA_SWING, {}))
            for r in results
            if r.hyp_id == entry.get("hyp_id")
        )
    ]

    ctx = frl_report.BatchContext(
        run_date=run_date,
        windows_line=windows.describe(),
        cost_model=cost_model,
        panel_days={era: len(p.days) for era, p in panels.items()},
        missing_days=sorted(set(missing)),
        unexpected_missing=sorted(set(unexpected)),
        sanity_lines=sanity_lines,
        results=results,
        deflation_rows=deflation_rows,
        holdout_congestion=frl_holdout.holdout_congestion(history, windows.holdout_start),
        parked_retests=sorted(set(parked_retests)),
        anomalies=anomalies,
        notes=(
            "A swing score-oszlop EWMA(5)-simított — a half-life a simítást is méri, "
            "nem csak a nyers jel perzisztenciáját (FRL-0 #5).",
            "A dev-ablak vége max(h) trading nappal a legutolsó bar-nap előtt van.",
        ),
    )
    report = frl_report.build_report(ctx)

    if not dry_run:
        base = Path(runs_dir) if runs_dir is not None else cfg.RUNS_DIR
        out_dir = base / run_date.isoformat()
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.md").write_text(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FRL weekly batch")
    parser.add_argument("--date", type=date.fromisoformat, default=None)
    parser.add_argument("--hyp", default=None, help="restrict to one hypothesis id")
    parser.add_argument("--factor", default=None, help="restrict to one factor name")
    parser.add_argument(
        "--dry-run", action="store_true", help="compute and print, write nothing (no ledger rows)"
    )
    args = parser.parse_args(argv)

    report = run_batch(
        run_date=args.date,
        hyp_filter=args.hyp,
        factor_filter=args.factor,
        dry_run=args.dry_run,
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
