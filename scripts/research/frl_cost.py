"""FRL — empirical cost model from observed entry-fill slippage (spec §5.3, R1#3).

Source correction (verified 2026-07-21): the task text pointed at
``state/pending_exits/``, but those records carry no slippage field. The
authoritative slippage series is ``state/daily_metrics/<date>.json`` →
``execution.slippage_per_ticker[*].slippage_pct`` (signed %, entry-day MKT fill
vs the planned limit), written by ``scripts/paper_trading/daily_metrics.py``.

Estimator: the **median (and p75) of |slippage|**, not the extreme signed prints.
Signed prints contain overnight drift in both directions; the absolute-value
distribution is the unbiased per-side cost estimate for next-day MKT-open entries.
3 bp-class assumptions are forbidden for this execution style.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from statistics import median

import frl_config as cfg


def collect_slippage(
    metrics_dir: Path | None = None,
    era: str | None = cfg.ERA_SWING,
) -> list[tuple[date, str, float]]:
    """Collect ``(day, ticker, slippage_pct)`` observations from daily metrics.

    Args:
        metrics_dir: directory of daily metric JSONs.
        era: restrict to one era, or None for all. Defaults to the swing era —
            legacy fills used a different execution style (intraday LMT) and are
            not a valid prior for next-day MKT-open cost.
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


def build_cost_model(
    metrics_dir: Path | None = None,
    era: str | None = cfg.ERA_SWING,
    out_path: Path | None = None,
) -> dict:
    """Build the empirical per-side cost model.

    Returns a dict with the median/p75 of |slippage| in basis points, the sample
    size, the observation window, and a ``small_n_warning`` flag. Falls back to
    ``FALLBACK_COST_BPS_PER_SIDE`` (75 bp) only when the sample is empty.
    """
    observations = collect_slippage(metrics_dir, era)
    abs_bps = sorted(abs(value) * 100.0 for _, _, value in observations)

    if abs_bps:
        med = median(abs_bps)
        p75 = _percentile(abs_bps, 0.75)
        cost = med
    else:
        med = p75 = float("nan")
        cost = cfg.FALLBACK_COST_BPS_PER_SIDE

    days = [day for day, _, _ in observations]
    model = {
        "era": era or "all",
        "n": len(abs_bps),
        "median_bps_per_side": round(med, 1) if abs_bps else None,
        "p75_bps_per_side": round(p75, 1) if abs_bps else None,
        "max_bps_per_side": round(max(abs_bps), 1) if abs_bps else None,
        "cost_bps_per_side": round(cost, 1),
        "estimator": "median(|entry slippage|) from daily_metrics.execution",
        "source": "state/daily_metrics/*.json::execution.slippage_per_ticker",
        "window": {
            "start": min(days).isoformat() if days else None,
            "end": max(days).isoformat() if days else None,
        },
        "small_n_warning": len(abs_bps) < cfg.COST_MODEL_MIN_N,
        "fallback_used": not abs_bps,
    }

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(model, indent=2) + "\n")
    return model


def load_cost_model(path: Path = cfg.COST_MODEL_PATH) -> dict:
    """Load the persisted cost model, or the 75 bp fallback if absent."""
    if not path.exists():
        return {
            "era": cfg.ERA_SWING,
            "n": 0,
            "cost_bps_per_side": cfg.FALLBACK_COST_BPS_PER_SIDE,
            "small_n_warning": True,
            "fallback_used": True,
        }
    return json.loads(path.read_text())


def round_trip_cost_bps(model: dict) -> float:
    """Round-trip (entry + exit) cost in basis points."""
    return 2.0 * float(model.get("cost_bps_per_side", cfg.FALLBACK_COST_BPS_PER_SIDE))
