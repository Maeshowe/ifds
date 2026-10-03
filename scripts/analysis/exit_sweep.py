#!/usr/bin/env python3
"""SIM-2 — exit-architecture sweep over the fixed real entries.

SIM-1 ruled the §11.20 geometry out (effect −$8, CI [−707, +649]) and left the
residual ~72% of the loss as "direction / selection". This sweep tests the
EXIT-ARCHITECTURE branch of that residual: holding the entries fixed (same
tickers, same dates, same real fills, same ATR, same size), would a different
``max_hold`` / TP1 threshold have changed the outcome?

The entries are deliberately frozen. A Mode-2 re-score would also change WHICH
tickers get picked, and then the difference could not be attributed to the exit.

The grid is PRE-REGISTERED in the task file — 5 max_hold × 3 TP1 = 15 cells,
14 comparisons, Šidák α_per = 0.00366. Post-hoc grid expansion is forbidden.

    python scripts/analysis/exit_sweep.py

Read-only. Task: docs/tasks/2026-10-03-sim2-exit-architecture-sweep.md
"""

from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from scipy import stats as scipy_stats

import counterfactual_data as cd
from counterfactual_geometry import (
    PRODUCTION_TUNING,
    STOP_ATR_MULTIPLE,
    TP2_ATR_MULTIPLE,
    SwingPosition,
    net_pnl,
    simulate,
)

# ---------------------------------------------------------------------------
# The PRE-REGISTERED grid (task §3) — do not extend without a new pre-reg
# ---------------------------------------------------------------------------

MAX_HOLD_VALUES: tuple[int, ...] = (3, 5, 7, 10, 15)
TP1_MULTIPLE_VALUES: tuple[float, ...] = (1.0, 1.5, 2.0)
BASELINE: tuple[int, float] = (5, 1.5)  # the production configuration

ALPHA = 0.05
BOOTSTRAP_RESAMPLES = 20_000
BOOTSTRAP_SEED = 20261003
LIVE_MAX_CONCURRENT = 12  # swing_state.max_concurrent — the feasibility ceiling


def grid() -> list[tuple[int, float]]:
    """Every (max_hold, tp1_multiple) cell, in pre-registered order."""
    return [(hold, tp1) for hold in MAX_HOLD_VALUES for tp1 in TP1_MULTIPLE_VALUES]


COMPARISONS = len(grid()) - 1


def sidak_alpha(comparisons: int, alpha: float = ALPHA) -> float:
    """Per-test significance level under Šidák correction for ``comparisons``."""
    if comparisons < 1:
        raise ValueError("comparisons must be >= 1")
    return 1.0 - (1.0 - alpha) ** (1.0 / comparisons)


# ---------------------------------------------------------------------------
# Common sample and paired statistics
# ---------------------------------------------------------------------------


def common_keys(per_cell: dict[object, dict[object, float]]) -> set:
    """Keys resolvable in EVERY cell.

    Without this rule a longer ``max_hold`` would look better merely by shedding
    the most recent positions (which it cannot resolve) — a selection artifact
    rather than an exit effect.
    """
    if not per_cell:
        return set()
    sets = [set(cell) for cell in per_cell.values()]
    return set.intersection(*sets) if sets else set()


@dataclass(frozen=True)
class PairedStats:
    """Paired comparison of one cell against the baseline."""

    n: int
    total: float
    mean: float
    p_value: float
    ci_low: float
    ci_high: float


def paired_stats(deltas: list[float]) -> PairedStats:
    """Paired t-test plus a bootstrap CI on the SUM of the per-position deltas.

    P&L deltas are strongly non-normal (a few large movers among many exact
    zeros), so the bootstrap CI is the reportable interval and the t-test is
    only a reference. Fewer than two observations yields NaN rather than a
    fabricated result.
    """
    n = len(deltas)
    total = float(sum(deltas))
    if n < 2:
        return PairedStats(n, total, total / n if n else 0.0, float("nan"), float("nan"), float("nan"))

    if all(abs(d) < 1e-12 for d in deltas):
        p_value = 1.0
    else:
        p_value = float(scipy_stats.ttest_1samp(deltas, 0.0).pvalue)

    rng = random.Random(BOOTSTRAP_SEED)
    sums = sorted(sum(rng.choices(deltas, k=n)) for _ in range(BOOTSTRAP_RESAMPLES))
    lo = sums[int(ALPHA / 2 * (len(sums) - 1))]
    hi = sums[int((1 - ALPHA / 2) * (len(sums) - 1))]
    return PairedStats(n, total, total / n, p_value, lo, hi)


# ---------------------------------------------------------------------------
# Slot concurrency — the feasibility constraint (task §5)
# ---------------------------------------------------------------------------


def max_concurrent(spans: list[tuple[date, date]], sessions: list[date]) -> int:
    """Peak simultaneously-open positions across ``sessions``.

    A position occupies its slot on the exit session too — overstating
    occupancy is the safe direction for a capacity caveat.
    """
    if not spans:
        return 0
    return max(
        (sum(1 for entry, exit_ in spans if entry <= day <= exit_) for day in sessions),
        default=0,
    )


# ---------------------------------------------------------------------------
# Running one cell
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CellResult:
    max_hold: int
    tp1_multiple: float
    pnl: dict[tuple[str, str], float]
    spans: dict[tuple[str, str], tuple[date, date]]
    first_legs: dict[tuple[str, str], str]


def run_cell(
    sample: list[cd.SamplePosition],
    max_hold: int,
    tp1_multiple: float,
) -> CellResult:
    """Re-simulate every position under one (max_hold, TP1) configuration.

    Anchored on the REAL FILL — there is no point designing a future exit
    architecture around the §11.20 defect, which gets fixed regardless.
    """
    config = {**PRODUCTION_TUNING, "swing_time_stop_trading_days": max_hold}
    pnl: dict[tuple[str, str], float] = {}
    spans: dict[tuple[str, str], tuple[date, date]] = {}
    first_legs: dict[tuple[str, str], str] = {}

    for pos in sample:
        position = SwingPosition(
            ticker=pos.ticker,
            entry_date=pos.entry_date,
            entry_price=pos.fill,
            atr=pos.atr,
            stop_level=pos.fill - STOP_ATR_MULTIPLE * pos.atr,
            tp1_level=pos.fill + tp1_multiple * pos.atr,
            tp2_level=pos.fill + TP2_ATR_MULTIPLE * pos.atr,
            qty=pos.qty,
            qty_remaining=pos.qty,
            sector=pos.sector,
            entry_score=pos.entry_score,
        )
        result = simulate(position, list(pos.bars), config)
        if result.unresolved or not result.legs:
            continue  # the common-sample rule drops it from every cell
        pnl[pos.key] = net_pnl(result.legs, pos.fill)
        spans[pos.key] = (date.fromisoformat(pos.entry_date), result.legs[-1].exit_date)
        first_legs[pos.key] = result.legs[0].exit_type

    return CellResult(max_hold, tp1_multiple, pnl, spans, first_legs)


#: Stage 2 (task §3): EXPLORATORY only — outside the pre-registered grid, so it
#: carries no inference. Reported as a surface, never as a result.
STAGE2_STOP_MULTIPLES: tuple[float, ...] = (1.0, 1.5, 2.0, 2.5, 3.0)


def run_stop_probe(
    sample: list[cd.SamplePosition],
    max_hold: int,
    tp1_multiple: float,
    stop_multiple: float,
) -> dict[tuple[str, str], float]:
    """One exploratory cell with a non-production stop multiple."""
    config = {**PRODUCTION_TUNING, "swing_time_stop_trading_days": max_hold}
    out: dict[tuple[str, str], float] = {}
    for pos in sample:
        position = SwingPosition(
            ticker=pos.ticker,
            entry_date=pos.entry_date,
            entry_price=pos.fill,
            atr=pos.atr,
            stop_level=pos.fill - stop_multiple * pos.atr,
            tp1_level=pos.fill + tp1_multiple * pos.atr,
            tp2_level=pos.fill + TP2_ATR_MULTIPLE * pos.atr,
            qty=pos.qty,
            qty_remaining=pos.qty,
            sector=pos.sector,
            entry_score=pos.entry_score,
        )
        result = simulate(position, list(pos.bars), config)
        if not result.unresolved and result.legs:
            out[pos.key] = net_pnl(result.legs, pos.fill)
    return out


def _stage2(sample, keys, anchors) -> None:
    print()
    print("-" * 86)
    print("STAGE 2 — EXPLORATORY stop-multiple probe (task §3: NO inference, NO p-values)")
    print("-" * 86)
    print("  Outside the pre-registered grid. Hypothesis-generating ONLY: a configuration")
    print("  selected here could not be promoted on this data under any circumstances.")
    print()
    header = "".join(f"{m:>12.1f}" for m in STAGE2_STOP_MULTIPLES)
    print(f"  {'max_hold/TP1':<16}{'stop x ATR ->':<2}{header}")
    for max_hold, tp1 in anchors:
        row = []
        for stop_multiple in STAGE2_STOP_MULTIPLES:
            pnl = run_stop_probe(sample, max_hold, tp1, stop_multiple)
            usable = [k for k in keys if k in pnl]
            row.append(sum(pnl[k] for k in usable))
        cells_text = "".join(f"{v:>12,.0f}" for v in row)
        print(f"  {f'{max_hold} / {tp1}':<18}{cells_text}")
    print()
    print("  (Production stop is 2.0 x ATR — the middle column.)")


def main(stage2: bool = False) -> int:
    window = max(MAX_HOLD_VALUES) + 2
    sample, excluded = cd.build_sample(window)
    cells = {cell: run_cell(sample, *cell) for cell in grid()}
    keys = common_keys({cell: result.pnl for cell, result in cells.items()})
    _report(sample, excluded, cells, keys, window)
    if stage2:
        best = max(grid(), key=lambda c: sum(cells[c].pnl[k] for k in keys))
        _stage2(sample, keys, sorted({BASELINE, best}))
    return 0


def _report(sample, excluded, cells, keys, window) -> None:
    alpha_per = sidak_alpha(COMPARISONS)
    sessions = sorted({d for pos in sample for d in (b.date for b in pos.bars)})

    print("=" * 86)
    print("SIM-2 — exit-architecture sweep on the fixed real entries")
    print("=" * 86)
    print(f"bar window per position     : {window} sessions")
    print(f"swing-era closed positions  : {len(sample) + len(excluded)}")
    print(f"assembled                   : {len(sample)}   excluded: {len(excluded)}")
    print(f"COMMON sample (all 15 cells): {len(keys)}")
    print(f"grid                        : max_hold {MAX_HOLD_VALUES} x TP1 {TP1_MULTIPLE_VALUES}")
    print(f"comparisons                 : {COMPARISONS}   Šidák α_per = {alpha_per:.5f}")

    baseline = cells[BASELINE]
    base_sum = sum(baseline.pnl[k] for k in keys)
    print(f"\nbaseline cell (max_hold=5, TP1=1.5) Σ = ${base_sum:,.2f} on the common sample")

    print()
    print("-" * 86)
    print("THE FULL GRID — every cell reported, not the best (task §3)")
    print("-" * 86)
    print(f"{'max_hold':>9}{'TP1':>6}{'Σ P&L':>12}{'vs base':>11}{'p (paired)':>12}"
          f"{'bootstrap 95% CI':>24}{'peak slots':>12}")
    rows = []
    for cell in grid():
        result = cells[cell]
        total = sum(result.pnl[k] for k in keys)
        deltas = [result.pnl[k] - baseline.pnl[k] for k in keys]
        st = paired_stats(deltas)
        peak = max_concurrent([result.spans[k] for k in keys], sessions)
        rows.append((cell, total, st, peak))
        flag = ""
        if cell == BASELINE:
            flag = "  <- baseline"
        elif st.p_value == st.p_value and st.p_value < alpha_per:
            flag = "  * SIGNIFICANT (Šidák)"
        if peak > LIVE_MAX_CONCURRENT:
            flag += f"  !! infeasible (> {LIVE_MAX_CONCURRENT} slots)"
        ci = f"[{st.ci_low:>+8,.0f},{st.ci_high:>+8,.0f}]"
        print(f"{cell[0]:>9}{cell[1]:>6.1f}{total:>12,.0f}{st.total:>+11,.0f}"
              f"{st.p_value:>12.4f}{ci:>24}{peak:>12}{flag}")

    print()
    print("-" * 86)
    print("VERDICT")
    print("-" * 86)
    best_cell, best_total, best_st, best_peak = max(rows, key=lambda r: r[1])
    feasible = [r for r in rows if r[3] <= LIVE_MAX_CONCURRENT]
    print(f"  best cell overall        : max_hold={best_cell[0]}, TP1={best_cell[1]}  "
          f"Σ = ${best_total:,.0f}  (peak slots {best_peak})")
    if feasible:
        fc, ft, fst, fp = max(feasible, key=lambda r: r[1])
        print(f"  best FEASIBLE cell       : max_hold={fc[0]}, TP1={fc[1]}  "
              f"Σ = ${ft:,.0f}  vs base {fst.total:+,.0f}  p={fst.p_value:.4f}  (peak slots {fp})")
    print(f"  cells beating baseline   : {sum(1 for _, _, st, _ in rows if st.total > 0)}/{len(rows) - 1}")
    print(f"  cells with Σ > 0         : {sum(1 for _, t, _, _ in rows if t > 0)}/{len(rows)}")
    significant = [r for r in rows if r[0] != BASELINE and r[2].p_value == r[2].p_value
                   and r[2].p_value < alpha_per]
    print(f"  Šidák-significant cells  : {len(significant)}/{COMPARISONS}")
    print()
    if best_total < 0:
        print("  => Even the BEST cell loses money. Per task §4.1 this direction is the")
        print("     ROBUST one: multiplicity only inflates the best cell, and it is still")
        print("     negative. The exit-architecture hypothesis does not rescue the book.")
    else:
        print("  => The best cell is positive. Per task §4.1 multiplicity now matters")
        print("     decisively: this CANNOT be promoted on this data. It needs an")
        print("     out-of-sample test under a NEW pre-registration.")

    print()
    print("-" * 86)
    print("EXPOSURE DIAGNOSTIC — does less market time simply mean less loss?")
    print("-" * 86)
    exposure, totals = [], []
    for cell in grid():
        result = cells[cell]
        held = [_held_sessions(*result.spans[k]) for k in keys]
        exposure.append(sum(held))
        totals.append(sum(result.pnl[k] for k in keys))
    r = _pearson(exposure, totals)
    slope = _ols_slope(exposure, totals)
    print(f"  Pearson r(Σ position-days, Σ P&L) = {r:+.3f}   (15 cells, SHARED positions —")
    print("    the cells are strongly correlated, so this is DESCRIPTIVE: no p-value.)")
    print(f"  OLS slope                         = ${slope:,.2f} per position-day of exposure")
    print(f"  baseline exposure                 = {exposure[grid().index(BASELINE)]} position-days")
    if r < -0.5:
        print("  => More time in the market costs money monotonically in the aggregate.")
        print("     That is the signature of negative expected drift in the ENTRIES, not")
        print("     of a mis-tuned exit. NOTE: conditional on THIS signal — it does not")
        print("     show that longer holds are wrong for a different signal.")

    print()
    print("  first-leg exit mix, baseline vs best feasible:")
    for label, cell in (("baseline", BASELINE), ("best feasible", fc if feasible else BASELINE)):
        mix: dict[str, int] = {}
        for k in keys:
            exit_type = cells[cell].first_legs[k]
            mix[exit_type] = mix.get(exit_type, 0) + 1
        print(f"    {label:<14} " + "  ".join(f"{k}={v}" for k, v in sorted(mix.items())))


def _held_sessions(entry: date, exit_: date) -> int:
    """Trading sessions held, by the same rule production uses for days_held."""
    from ifds.utils.calendar import trading_days_between

    return trading_days_between(entry, exit_)


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return float("nan")
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return cov / (sx * sy) if sx > 0 and sy > 0 else float("nan")


def _ols_slope(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom if denom > 0 else float("nan")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage2",
        action="store_true",
        help="also run the EXPLORATORY stop-multiple probe (no inference)",
    )
    raise SystemExit(main(stage2=parser.parse_args().stage2))
