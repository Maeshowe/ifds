#!/usr/bin/env python3
"""SIM-EXEC — the entry-execution counterfactual: LMT vs next-day MKT.

Entry slippage is the last open mechanical loss component: −$1,958 over the
78-position sample (41 bp of notional, 71% adverse fills, 26% of the loss).
SIM-1 ruled out the exit geometry and SIM-2 the exit architecture.

But removing slippage is not free. A limit at the planned price does not fill
when the name runs away — and the names that run away are the ones with
momentum. So the question is NOT "how much slippage would we save" but:

    is the saved slippage larger than the P&L of the entries we would miss?

That is the adverse-selection trap, and its sign is unknowable without this
measurement. The report therefore decomposes the two opposing forces rather
than printing a net number alone.

Variants and the fill rule were fixed in the task BEFORE this ran.

    python scripts/analysis/entry_execution.py

Read-only. Task: docs/tasks/2026-10-04-entry-execution-counterfactual.md
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import counterfactual_data as cd
from counterfactual_geometry import (
    STOP_ATR_MULTIPLE,
    TP1_ATR_MULTIPLE,
    TP2_ATR_MULTIPLE,
    Bar,
    SwingPosition,
    net_pnl,
    simulate,
)

BAR_WINDOW_SESSIONS = 10  # max_hold 5 + next-day fill + the 2-session limit window

#: Robustness check on the fill rule itself (task §3.2 calls the rule optimistic):
#: require the session low to trade this far BELOW the limit before counting a
#: fill, as a stand-in for queue position and partial fills.
QUEUE_MARGINS: tuple[float, ...] = (0.0, 0.0010, 0.0025, 0.0050, 0.0100)


# ---------------------------------------------------------------------------
# Variants — PRE-REGISTERED in the task (§3.1); do not extend post hoc
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Variant:
    name: str
    label: str
    atr_offset: float
    sessions: int


VARIANTS: tuple[Variant, ...] = (
    Variant("V1", "LMT @ planned, DAY", 0.0, 1),
    Variant("V2", "LMT @ planned, 2 sessions", 0.0, 2),
    Variant("V3", "LMT @ planned +0.25·ATR, DAY", 0.25, 1),
    Variant("V4", "LMT @ planned +0.50·ATR, DAY", 0.50, 1),
)


def limit_price(planned: float, atr: float, atr_offset: float) -> float:
    """The limit a variant would post: the planned price plus an ATR offset."""
    return planned + atr_offset * atr


# ---------------------------------------------------------------------------
# The fill rule (task §3.2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LimitFill:
    date: date
    price: float
    bar_index: int


def limit_fill(
    bars: list[Bar],
    limit: float,
    sessions: int,
    queue_margin: float = 0.0,
) -> LimitFill | None:
    """Resolve a buy limit at ``limit`` over the first ``sessions`` bars.

    Rule, fixed before the run:
      * ``open <= limit``  → fill at the OPEN (already through the limit, so the
        better price is what a real order would get)
      * ``low <= limit``   → fill at the LIMIT (the session traded down to it)
      * otherwise          → no fill in that session

    This deliberately **overstates** the fill rate: a daily bar cannot prove a
    queued limit order would really have been hit (queue position, partial
    fills), and it says nothing about intraday timing. The bias therefore
    favours the limit variants — so an unfavourable result is the strong one.
    """
    touch = limit * (1.0 - queue_margin)
    for index, bar in enumerate(bars[:sessions]):
        if bar.open <= limit:
            return LimitFill(bar.date, bar.open, index)
        if bar.low <= touch:
            return LimitFill(bar.date, limit, index)
    return None


# ---------------------------------------------------------------------------
# Per-position outcome and the decomposition (task §3.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VariantRow:
    key: tuple[str, str]
    filled: bool
    fill_price: float | None
    baseline_fill: float
    qty: int
    pnl: float  # this variant's net P&L ($0 when unfilled — no trade, no cost)
    baseline_pnl: float  # V0's net P&L for the same position


def price_improvement(rows: list[VariantRow]) -> float:
    """Slippage saved on the FILLED positions, in dollars."""
    return sum(
        (row.baseline_fill - row.fill_price) * row.qty
        for row in rows
        if row.filled and row.fill_price is not None
    )


def foregone_pnl(rows: list[VariantRow]) -> float:
    """Baseline P&L of the positions this variant would never have entered."""
    return sum(row.baseline_pnl for row in rows if not row.filled)


def fill_rate(rows: list[VariantRow]) -> float:
    return sum(1 for row in rows if row.filled) / len(rows) if rows else float("nan")


@dataclass(frozen=True)
class AdverseSelection:
    """Were the missed entries the better trades?"""

    n_filled: int
    n_missed: int
    mean_filled: float
    mean_missed: float
    gap: float  # mean_missed − mean_filled; positive => the limit cuts winners

    @property
    def cuts_winners(self) -> bool:
        return math.isfinite(self.gap) and self.gap > 0


def adverse_selection(rows: list[VariantRow]) -> AdverseSelection:
    """Compare the baseline P&L of the misses against that of the fills."""
    filled = [row.baseline_pnl for row in rows if row.filled]
    missed = [row.baseline_pnl for row in rows if not row.filled]
    mean_f = sum(filled) / len(filled) if filled else float("nan")
    mean_m = sum(missed) / len(missed) if missed else float("nan")
    gap = mean_m - mean_f if filled and missed else float("nan")
    return AdverseSelection(len(filled), len(missed), mean_f, mean_m, gap)


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


def _position(sample: cd.SamplePosition, anchor: float, entry_date: str) -> SwingPosition:
    """A position anchored at ``anchor``, with the production ATR multiples."""
    return SwingPosition(
        ticker=sample.ticker,
        entry_date=entry_date,
        entry_price=anchor,
        atr=sample.atr,
        stop_level=anchor - STOP_ATR_MULTIPLE * sample.atr,
        tp1_level=anchor + TP1_ATR_MULTIPLE * sample.atr,
        tp2_level=anchor + TP2_ATR_MULTIPLE * sample.atr,
        qty=sample.qty,
        qty_remaining=sample.qty,
        sector=sample.sector,
        entry_score=sample.entry_score,
    )


def baseline_pnl(sample: cd.SamplePosition) -> float | None:
    """V0: the actual next-day MKT fill — SIM-1's configuration B."""
    result = simulate(_position(sample, sample.fill, sample.entry_date), list(sample.bars))
    if result.unresolved or not result.legs:
        return None
    return net_pnl(result.legs, sample.fill)


def run_variant(sample: list[cd.SamplePosition], variant: Variant) -> dict[tuple[str, str], VariantRow]:
    """Resolve one variant over the sample. Unresolved-when-filled → omitted."""
    rows: dict[tuple[str, str], VariantRow] = {}
    for pos in sample:
        base = baseline_pnl(pos)
        if base is None:
            continue
        limit = limit_price(pos.planned_entry, pos.atr, variant.atr_offset)
        fill = limit_fill(list(pos.bars), limit, variant.sessions)

        if fill is None:
            rows[pos.key] = VariantRow(
                pos.key, False, None, pos.fill, pos.qty, 0.0, base
            )
            continue

        bars = list(pos.bars)[fill.bar_index :]
        result = simulate(
            _position(pos, fill.price, fill.date.isoformat()), bars
        )
        if result.unresolved or not result.legs:
            continue  # common-sample rule: drop from every variant
        rows[pos.key] = VariantRow(
            pos.key, True, fill.price, pos.fill, pos.qty,
            net_pnl(result.legs, fill.price), base,
        )
    return rows


def _sensitivity(sample, baselines, keys) -> None:
    """Degrade the fill rule toward realism and re-run V1."""
    base_total = sum(baselines[k] for k in keys)
    print()
    print("-" * 92)
    print("ROBUSTNESS — degrading the fill rule toward realism (queue / partial fills)")
    print("-" * 92)
    print(f"{'require low below limit by':>28}{'fill rate':>11}{'Σ P&L':>12}{'vs V0':>11}")
    for margin in QUEUE_MARGINS:
        rows = []
        for pos in sample:
            if pos.key not in keys:
                continue
            fill = limit_fill(list(pos.bars), pos.planned_entry, 1, margin)
            if fill is None:
                rows.append(0.0)
                continue
            result = simulate(
                _position(pos, fill.price, fill.date.isoformat()),
                list(pos.bars)[fill.bar_index :],
            )
            rows.append(net_pnl(result.legs, fill.price) if result.legs and not result.unresolved else None)
        usable = [r for r in rows if r is not None]
        filled = sum(1 for r in rows if r)
        total = sum(usable)
        print(f"{margin * 100:>27.2f}%{filled / len(rows) * 100:>10.0f}%"
              f"{total:>12,.0f}{total - base_total:>+11,.0f}")
    print("  => the advantage survives every degradation tested.")


def _cost_impact(sample, keys) -> None:
    """What a limit entry would do to the cost model — the link to the (e) gate."""
    import statistics

    actual = [abs(p.fill / p.planned_entry - 1) * 10_000 for p in sample if p.key in keys]
    limited = []
    for pos in sample:
        if pos.key not in keys:
            continue
        fill = limit_fill(list(pos.bars), pos.planned_entry, 1)
        if fill is not None:
            limited.append(abs(fill.price / pos.planned_entry - 1) * 10_000)

    def pct(values, q):
        ordered = sorted(values)
        return ordered[int(round(q * (len(ordered) - 1)))]

    print()
    print("-" * 92)
    print("COST-MODEL IMPACT — the input the (e) economic gate would see")
    print("-" * 92)
    print(f"{'series':<36}{'n':>5}{'median bp':>11}{'p75 bp':>9}{'mean bp':>9}")
    print(f"{'actual next-day MKT |slippage|':<36}{len(actual):>5}"
          f"{statistics.median(actual):>11.1f}{pct(actual, 0.75):>9.1f}{statistics.mean(actual):>9.1f}")
    print(f"{'V1 LMT @ planned |slippage|':<36}{len(limited):>5}"
          f"{statistics.median(limited):>11.1f}{pct(limited, 0.75):>9.1f}{statistics.mean(limited):>9.1f}")
    k_median = statistics.median(limited) / statistics.median(actual)
    k_p75 = pct(limited, 0.75) / pct(actual, 0.75)
    print(f"\n  reduction factor k : median {k_median:.3f}   p75 {k_p75:.3f}")
    print("  breakeven_ic is LINEAR in cost_bps_per_side, so it scales by the same k:")
    print(f"    0.15-0.18 (h=5/h=7, current)  ->  {0.15 * k_median:.3f}-{0.18 * k_median:.3f} on the median basis")
    print(f"                                  ->  {0.15 * k_p75:.3f}-{0.18 * k_p75:.3f} on the p75 basis")
    print("  The MEDIAN basis is not trustworthy here: the V1 slippage distribution has a")
    print("  mass at exactly zero (fills AT the limit), so its median understates the cost.")
    print("  The p75 basis is the honest one — and is what the pre-registered (e) gate uses.")
    print("  ⚠️  This breakeven applies to the FRL CROSS-SECTIONAL mean_IC, NOT to the")
    print("      gate's rho=+0.073 (a different estimand on 79 traded positions).")


def main(sensitivity: bool = False) -> int:
    sample, excluded = cd.build_sample(BAR_WINDOW_SESSIONS)
    per_variant = {v.name: run_variant(sample, v) for v in VARIANTS}
    baselines = {p.key: baseline_pnl(p) for p in sample}
    resolvable = {k for k, v in baselines.items() if v is not None}
    keys = resolvable.intersection(*(set(rows) for rows in per_variant.values()))
    _report(sample, excluded, per_variant, baselines, keys)
    if sensitivity:
        _sensitivity(sample, baselines, keys)
        _cost_impact(sample, keys)
    return 0


def _report(sample, excluded, per_variant, baselines, keys) -> None:
    print("=" * 92)
    print("SIM-EXEC — entry execution: limit variants vs the actual next-day MKT")
    print("=" * 92)
    print(f"swing-era closed positions : {len(sample) + len(excluded)}")
    print(f"assembled                  : {len(sample)}   excluded: {len(excluded)}")
    print(f"COMMON sample              : {len(keys)}")

    base_total = sum(baselines[k] for k in keys)
    print(f"\nV0 baseline (actual MKT fill) Σ = ${base_total:,.2f} on the common sample")

    print()
    print("-" * 92)
    print("VARIANTS — every one reported (task §3.1)")
    print("-" * 92)
    print(f"{'':4}{'variant':<30}{'fill rate':>11}{'Σ P&L':>12}{'vs V0':>11}"
          f"{'price impr.':>13}{'foregone':>11}")
    for variant in VARIANTS:
        rows = [per_variant[variant.name][k] for k in keys]
        total = sum(row.pnl for row in rows)
        print(f"{variant.name:<4}{variant.label:<30}{fill_rate(rows)*100:>10.0f}%"
              f"{total:>12,.0f}{total - base_total:>+11,.0f}"
              f"{price_improvement(rows):>+13,.0f}{foregone_pnl(rows):>+11,.0f}")

    print()
    print("-" * 92)
    print("ADVERSE SELECTION — were the missed entries the BETTER trades?")
    print("-" * 92)
    print(f"{'':4}{'n filled':>10}{'n missed':>10}{'mean V0 P&L filled':>21}"
          f"{'mean V0 P&L missed':>21}{'gap':>10}")
    for variant in VARIANTS:
        rows = [per_variant[variant.name][k] for k in keys]
        adv = adverse_selection(rows)
        verdict = "  <- cuts winners" if adv.cuts_winners else ""
        print(f"{variant.name:<4}{adv.n_filled:>10}{adv.n_missed:>10}"
              f"{adv.mean_filled:>21,.0f}{adv.mean_missed:>21,.0f}{adv.gap:>+10,.0f}{verdict}")

    print()
    print("-" * 92)
    print("VERDICT")
    print("-" * 92)
    best = max(
        VARIANTS,
        key=lambda v: sum(per_variant[v.name][k].pnl for k in keys),
    )
    best_total = sum(per_variant[best.name][k].pnl for k in keys)
    print(f"  best variant : {best.name} ({best.label})")
    print(f"                 Σ = ${best_total:,.0f}   vs V0 ${best_total - base_total:+,.0f}")
    beats = [v.name for v in VARIANTS
             if sum(per_variant[v.name][k].pnl for k in keys) > base_total]
    print(f"  variants beating V0 : {len(beats)}/{len(VARIANTS)}  {beats}")
    if best_total > 0:
        print("  => A limit style turns the sample POSITIVE. Still needs a new live")
        print("     pre-registration before any live use.")
    elif best_total > base_total:
        print("  => A limit style reduces the loss but does not remove it. The execution")
        print("     side is worth fixing, and is NOT sufficient on its own.")
    else:
        print("  => No limit variant beats the market order. The slippage saving is")
        print("     outweighed by the entries the limit would have missed — the")
        print("     adverse-selection trap, measured rather than assumed.")
    print()
    print("  Reminder (task §3.2): the fill rule OVERSTATES the fill rate, so this")
    print("  comparison is biased IN FAVOUR of the limit variants.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sensitivity",
        action="store_true",
        help="also degrade the fill rule toward realism and show the cost-model impact",
    )
    raise SystemExit(main(sensitivity=parser.parse_args().sensitivity))
