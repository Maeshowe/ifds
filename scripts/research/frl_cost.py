"""FRL — the empirical round-trip cost model (spec §5.3, R1#3).

Estimator, since 2026-10-19: **true friction only, measured separately per side**
(pre-reg ``docs/planning/2026-10-19-cost-estimator-amendment.md`` D-C1..D-C4, as
corrected by its own ERRATA D-E1..D-E6, both approved by Tamás on 2026-10-19).

    round_trip = c_entry + c_exit          NOT 2 * c_entry

What changed and why. The old model charged ``2 * median(|entry slippage|)`` where
the slippage was ``fill`` against the PLAN's limit price. That made two unmeasured
assumptions: that an exit costs what an entry costs (nothing had ever priced the
exit side), and that the half-width of symmetric decision-to-fill drift is a cost.
It is not — drift cancels, and what survives is the one-directional drag at the
fill. Measured, the decomposition is unambiguous: the overnight plan->open gap is
-1.5 bp (p = 0.88) while open->fill is +48.3 bp (p < 0.0001), and the exit side
independently agrees — an MOC auction costs +1.4 bp while a market order sent
after the bell costs +47 to +81 bp.

Two slots, both from the same estimator (pre-reg §4):
    median slot -> the POINT estimate
    p75 slot    -> the one-sided 95% UPPER CONFIDENCE BOUND on the mean
The p75 slot is the binding one. Replacing a per-trade quantile with a bound on
the central value is a change to the (e)-gate pre-registration, not only to §5.3;
it is recorded in ``docs/planning/2026-10-04-economic-gate-preregistration.md`` §9.

Every input path is injectable so a test never reads production state.
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from statistics import median

import frl_config as cfg
import frl_fills as fills

#: Schema version — ``load_cost_model`` refuses to hand an old model to the new
#: engine silently, because the two disagree about what ``cost_bps`` MEANS.
SCHEMA_VERSION: int = 2


def collect_slippage(
    metrics_dir: Path | None = None,
    era: str | None = cfg.ERA_SWING,
) -> list[tuple[date, str, float]]:
    """Legacy reader: ``(day, ticker, slippage_pct)`` vs the PLAN's limit price.

    Retained for ``build_legacy_abs_model`` only, which exists so the
    implementation report can price the old and the new estimator side by side.
    This series is a decision-to-fill shortfall, NOT a friction measurement.
    """
    base = Path(metrics_dir) if metrics_dir is not None else cfg.DAILY_METRICS_DIR
    observations: list[tuple[date, str, float]] = []
    if not base.exists():
        return observations

    for path in sorted(base.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        raw_date = payload.get("date") or path.stem
        try:
            day = date.fromisoformat(str(raw_date))
        except ValueError:
            continue
        if era is not None and cfg.era_of(day) != era:
            continue
        per_ticker = (payload.get("execution") or {}).get("slippage_per_ticker") or {}
        for ticker, entry in per_ticker.items():
            value = (entry or {}).get("slippage_pct")
            if value is None:
                continue
            try:
                observations.append((day, ticker, float(value)))
            except (TypeError, ValueError):
                continue
    return observations


def _percentile(sorted_values: list[float], q: float) -> float:
    """Nearest-rank percentile on an already sorted list."""
    if not sorted_values:
        return float("nan")
    idx = int(round(q * (len(sorted_values) - 1)))
    return sorted_values[idx]


def build_legacy_abs_model(
    metrics_dir: Path | None = None, era: str | None = cfg.ERA_SWING
) -> dict:
    """The PRE-2026-10-19 estimator, kept only for the side-by-side comparison."""
    observations = collect_slippage(metrics_dir, era)
    abs_bps = sorted(abs(value) * 100.0 for _, _, value in observations)
    if not abs_bps:
        return {"n": 0, "median_bps_per_side": None, "p75_bps_per_side": None}
    return {
        "n": len(abs_bps),
        "median_bps_per_side": round(median(abs_bps), 1),
        "p75_bps_per_side": round(_percentile(abs_bps, 0.75), 1),
        "round_trip_point_bps": round(2.0 * median(abs_bps), 1),
        "round_trip_bound_bps": round(2.0 * _percentile(abs_bps, 0.75), 1),
        "estimator": "2 * median(|fill - plan limit|) — superseded 2026-10-19",
    }


def _side_summary(legs, weighted: bool) -> dict:
    point = fills.point_estimate(legs, weighted=weighted)
    bound = fills.bootstrap_ucb(legs, weighted=weighted)
    return {
        "point_bps": round(point, 2) if math.isfinite(point) else None,
        "ucb95_bps": round(bound, 2) if math.isfinite(bound) else None,
        "weighted": weighted,
        "coverage": fills.coverage(legs),
        "by_order_type": fills.by_order_type(legs),
    }


def build_cost_model(
    metrics_dir: Path | None = None,
    era: str | None = cfg.ERA_SWING,
    out_path: Path | None = None,
    pending_exits_dir: Path | None = None,
    bars_dir: Path | None = None,
    backfill_path: Path | None = None,
) -> dict:
    """Measure both sides and emit the round-trip cost model.

    Weighting follows the pre-reg's letter, not a later preference: the ENTRY is
    notional-weighted (§5 says so explicitly), the EXIT is not (§5 omits it, and
    the approved table's 23.2 is the unweighted mean). The two terms are therefore
    not strictly the same estimand; the deviation is conservative, it is stated in
    the report, and the both-weighted figure is published as a named sensitivity
    (ERRATA D-E4).

    Falls back to ``FALLBACK_COST_BPS_PER_SIDE`` only when a side is empty, and
    refuses a non-positive round trip — a SIGNED mean, unlike the old
    median(|.|), has no structural floor, and a non-positive wall would open the
    (e) gate for every factor.
    """
    metrics = Path(metrics_dir) if metrics_dir is not None else cfg.DAILY_METRICS_DIR
    exits_dir = Path(pending_exits_dir) if pending_exits_dir is not None else cfg.PENDING_EXITS_DIR
    bars_base = Path(bars_dir) if bars_dir is not None else cfg.BARS_DIR
    backfill_src = Path(backfill_path) if backfill_path is not None else cfg.ENTRY_BACKFILL_PATH

    recorded = fills.load_entry_fills(metrics, era)
    exit_records = fills.load_exit_records(exits_dir, era)
    quantities = fills.entry_quantities(exit_records)
    backfill = fills.load_backfill_fills(backfill_src)
    exit_fills = fills.load_exit_fills(metrics)

    tickers = {t for _, t, _, _ in recorded} | {str(r["ticker"]) for r in exit_records}
    days = (
        {d for d, _, _, _ in recorded}
        | {key[0] for key in quantities}
        | {r["_exit_day"] for r in exit_records}
    )
    bars = fills.load_bars(tickers, sorted(days), bars_base)

    entry_legs, entry_excluded = fills.build_entry_legs(
        recorded, quantities, bars, backfill=backfill
    )
    exit_legs, exit_excluded = fills.build_exit_legs(exit_records, exit_fills, bars)

    entry = _side_summary(entry_legs, weighted=True)
    exit_side = _side_summary(exit_legs, weighted=False)

    fallback = False
    point = entry["point_bps"], exit_side["point_bps"]
    bound = entry["ucb95_bps"], exit_side["ucb95_bps"]
    if None in point or None in bound:
        fallback = True
        round_trip_point = round_trip_bound = 2.0 * cfg.FALLBACK_COST_BPS_PER_SIDE
    else:
        round_trip_point = point[0] + point[1]
        round_trip_bound = bound[0] + bound[1]

    # Degeneracy guard, tolerance-based (house rule: never `== 0`). A signed
    # estimator can in principle go non-positive; the wall would then admit every
    # factor. Empirically unreachable on this sample (0 of 20 000 day-clustered
    # resamples; minimum +4.1 bp), but the gate must not depend on that.
    if not fallback and round_trip_bound < cfg.MIN_ROUND_TRIP_BPS:
        fallback = True
        round_trip_point = round_trip_bound = 2.0 * cfg.FALLBACK_COST_BPS_PER_SIDE

    model = {
        "schema_version": SCHEMA_VERSION,
        "era": era or "all",
        "estimator": (
            "signed true friction per side: entry notional-weighted (fill - open)/open, "
            "exit unweighted (order-type reference - fill)/reference; "
            "round_trip = c_entry + c_exit"
        ),
        "pre_reg": (
            "docs/planning/2026-10-19-cost-estimator-amendment.md D-C1..D-C4 "
            "+ ERRATA D-E1..D-E6 (approved 2026-10-19)"
        ),
        "entry": entry,
        "exit": exit_side,
        "round_trip_point_bps": round(round_trip_point, 2),
        "round_trip_bound_bps": round(round_trip_bound, 2),
        "sensitivities": {
            "exit_notional_weighted": _side_summary(exit_legs, weighted=True),
            "entry_without_backfill": _side_summary(
                fills.build_entry_legs(recorded, quantities, bars, backfill=None)[0],
                weighted=True,
            ),
        },
        "excluded": {
            "entry": [list(row) for row in entry_excluded],
            "exit": [list(row) for row in exit_excluded],
        },
        "small_n_warning": len(entry_legs) < cfg.COST_MODEL_MIN_N
        or len(exit_legs) < cfg.COST_MODEL_MIN_N,
        "fallback_used": fallback,
        "bootstrap": {
            "unit": "trading day (clustered)",
            "replicates": cfg.COST_BOOTSTRAP_REPLICATES,
            "seed": cfg.COST_BOOTSTRAP_SEED,
            "confidence": cfg.COST_UCB_CONFIDENCE,
        },
        "fill_in_bar_tolerance": cfg.FILL_IN_BAR_TOLERANCE,
    }

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(model, indent=2) + "\n")
    return model


def load_cost_model(path: Path = cfg.COST_MODEL_PATH) -> dict:
    """Load the persisted model, or the fallback if it is absent or pre-schema-2.

    A v1 model on disk carries ``cost_bps_per_side``, which the current engine
    would multiply by nothing and charge as a round trip — the dangerous case of
    the same type meaning something different. It is refused, not adapted.
    """
    if not path.exists():
        return _fallback_model("cost model absent")
    try:
        model = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return _fallback_model("cost model unreadable")
    if model.get("schema_version") != SCHEMA_VERSION:
        return _fallback_model(
            f"cost model schema {model.get('schema_version')} != {SCHEMA_VERSION}"
        )
    return model


def _fallback_model(reason: str) -> dict:
    round_trip = 2.0 * cfg.FALLBACK_COST_BPS_PER_SIDE
    return {
        "schema_version": SCHEMA_VERSION,
        "era": cfg.ERA_SWING,
        "estimator": f"fallback ({reason})",
        "round_trip_point_bps": round_trip,
        "round_trip_bound_bps": round_trip,
        "small_n_warning": True,
        "fallback_used": True,
    }


def round_trip_cost_bps(model: dict, bound: bool = False) -> float:
    """The round-trip cost in bp: the point estimate, or the binding upper bound."""
    key = "round_trip_bound_bps" if bound else "round_trip_point_bps"
    value = model.get(key)
    if value is None or not math.isfinite(float(value)):
        return 2.0 * cfg.FALLBACK_COST_BPS_PER_SIDE
    return float(value)
