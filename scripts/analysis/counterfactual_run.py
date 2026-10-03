#!/usr/bin/env python3
"""SIM-1 — run the §11.20 counterfactual and print the report.

Two configurations of the SAME production exit logic:
  A  planned-price anchor  — how it actually ran (the defect)
  B  real-fill anchor      — how it should have run

Credibility gate FIRST: configuration A must reproduce the ledger's actual
exits. If it does not, the B number is not reported — the simulator would be
the broken thing, not production.

    python scripts/analysis/counterfactual_run.py

Read-only. Task: docs/tasks/2026-10-03-sim-counterfactual-geometry.md
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import counterfactual_data as cd
from counterfactual_geometry import (
    SwingPosition,
    derive_atr,
    net_pnl,
    rebase_levels,
    simulate,
)
from ifds.utils.trading_calendar import trading_days_between

SWING_ERA_START = date(2026, 5, 18)
BAR_WINDOW_SESSIONS = 9  # max_hold is 5 sessions + a next-day fill; 9 is slack
FILL_IN_BAR_TOLERANCE = 0.005  # 0.5% — guards ticker/adjustment mismatches
BOOTSTRAP_RESAMPLES = 20_000
BOOTSTRAP_SEED = 20261003


@dataclass(frozen=True)
class Outcome:
    ticker: str
    entry_date: str
    planned_entry: float
    fill: float
    slippage_pct: float
    qty: int
    atr: float
    actual_types: tuple[str, ...]
    actual_pnl: float
    sim_a_types: tuple[str, ...]
    sim_a_pnl: float
    sim_a_unresolved: bool
    sim_b_types: tuple[str, ...]
    sim_b_pnl: float
    sim_b_unresolved: bool


def _position(ticker, entry_date, sector, score, anchor, atr, qty) -> SwingPosition:
    stop, tp1, tp2 = rebase_levels(anchor, atr)
    return SwingPosition(
        ticker=ticker,
        entry_date=entry_date,
        entry_price=anchor,
        atr=atr,
        stop_level=stop,
        tp1_level=tp1,
        tp2_level=tp2,
        qty=qty,
        qty_remaining=qty,
        sector=sector,
        entry_score=score,
    )


def _window(entry: date, sessions: dict[date, dict]) -> list[date]:
    days = sorted(d for d in sessions if d >= entry)
    return days[: BAR_WINDOW_SESSIONS + 1]


def main(fill_at_close: bool = False) -> int:
    ledger = cd.load_ledger_positions()
    plans = cd.load_execution_plans()
    fills = cd.load_entry_fills()
    realized = cd.load_realized()

    era = [p for p in ledger if date.fromisoformat(p.entry_date) >= SWING_ERA_START]
    tickers = {p.ticker for p in era}
    calendar = trading_days_between(SWING_ERA_START, date(2026, 10, 2))
    sessions = cd.load_bars(tickers, calendar)

    outcomes: list[Outcome] = []
    excluded: list[tuple[str, str, str]] = []

    for pos in era:
        tag = (pos.ticker, pos.entry_date)
        plan = plans.get(pos.entry_date, {}).get(pos.ticker)
        if plan is None:
            excluded.append((*tag, "no execution-plan row"))
            continue
        atr = derive_atr(
            float(plan["limit_price"]),
            float(plan["stop_loss"]),
            float(plan["take_profit_1"]),
            float(plan["take_profit_2"]),
        )
        if atr is None:
            excluded.append((*tag, "plan row not ATR-consistent"))
            continue
        fill = fills.get(pos.entry_date, {}).get(pos.ticker)
        if fill is None:
            excluded.append((*tag, "no entry-fill record (slippage_per_ticker absent)"))
            continue

        entry = date.fromisoformat(pos.entry_date)
        window = _window(entry, sessions)
        bars = [sessions[d][pos.ticker] for d in window if pos.ticker in sessions.get(d, {})]
        if len(bars) < 2 or bars[0].date != entry:
            excluded.append((*tag, f"insufficient bars ({len(bars)})"))
            continue

        entry_bar = bars[0]
        lo = entry_bar.low * (1 - FILL_IN_BAR_TOLERANCE)
        hi = entry_bar.high * (1 + FILL_IN_BAR_TOLERANCE)
        if not lo <= fill <= hi:
            excluded.append(
                (*tag, f"fill {fill:.2f} outside entry bar [{entry_bar.low:.2f},{entry_bar.high:.2f}]")
            )
            continue

        planned = float(plan["limit_price"])
        if fill_at_close:
            # Sensitivity: price every next-day exit at that session's CLOSE
            # instead of its OPEN — a maximally different execution assumption.
            bars = [replace(bar, open=bar.close) for bar in bars]
        a = simulate(
            _position(pos.ticker, pos.entry_date, pos.sector, pos.entry_score, planned, atr, pos.qty),
            bars,
        )
        b = simulate(
            _position(pos.ticker, pos.entry_date, pos.sector, pos.entry_score, fill, atr, pos.qty),
            bars,
        )

        actual = sum(realized.get((d, pos.ticker), 0.0) for d in set(pos.exit_dates))
        outcomes.append(
            Outcome(
                ticker=pos.ticker,
                entry_date=pos.entry_date,
                planned_entry=planned,
                fill=fill,
                slippage_pct=(fill / planned - 1) * 100 if planned else 0.0,
                qty=pos.qty,
                atr=atr,
                actual_types=pos.exit_types,
                actual_pnl=actual,
                sim_a_types=tuple(leg.exit_type for leg in a.legs),
                sim_a_pnl=net_pnl(a.legs, fill),
                sim_a_unresolved=a.unresolved,
                sim_b_types=tuple(leg.exit_type for leg in b.legs),
                sim_b_pnl=net_pnl(b.legs, fill),
                sim_b_unresolved=b.unresolved,
            )
        )

    _report(outcomes, excluded, len(era))
    return 0


def _report(outcomes, excluded, era_total) -> None:
    print("=" * 78)
    print("SIM-1 — §11.20 counterfactual exit geometry")
    print("=" * 78)
    print(f"swing-era closed positions: {era_total}")
    print(f"in sample:                  {len(outcomes)}")
    print(f"excluded:                   {len(excluded)}")
    for ticker, entry, reason in excluded:
        print(f"    - {ticker:<6} {entry}  {reason}")

    gate = [o for o in outcomes if not o.sim_a_unresolved and o.actual_pnl != 0.0]
    print()
    print("-" * 78)
    print(f"CREDIBILITY GATE — configuration A vs the ledger (n={len(gate)})")
    print("-" * 78)
    if not gate:
        print("  no comparable positions — cannot validate; B not reported")
        return
    type_match = sum(1 for o in gate if o.sim_a_types == o.actual_types)
    first_match = sum(1 for o in gate if o.sim_a_types[:1] == o.actual_types[:1])
    deltas = [o.sim_a_pnl - o.actual_pnl for o in gate]
    abs_deltas = sorted(abs(d) for d in deltas)
    print(f"  exit-type sequence identical : {type_match}/{len(gate)} ({type_match/len(gate)*100:.0f}%)")
    print(f"  first exit type identical    : {first_match}/{len(gate)} ({first_match/len(gate)*100:.0f}%)")
    print(f"  P&L delta  median |Δ|        : ${statistics.median(abs_deltas):,.2f}")
    print(f"             p90    |Δ|        : ${abs_deltas[int(0.9*(len(abs_deltas)-1))]:,.2f}")
    print(f"  Σ sim A = ${sum(o.sim_a_pnl for o in gate):,.2f}   Σ actual = ${sum(o.actual_pnl for o in gate):,.2f}")

    print()
    print("-" * 78)
    print("A vs B — the counterfactual")
    print("-" * 78)
    both = [o for o in outcomes if not o.sim_a_unresolved and not o.sim_b_unresolved]
    print(f"  resolved in both configurations: n={len(both)}")
    sum_a = sum(o.sim_a_pnl for o in both)
    sum_b = sum(o.sim_b_pnl for o in both)
    print(f"  Σ A (planned anchor, as it ran) : ${sum_a:,.2f}")
    print(f"  Σ B (fill anchor, corrected)    : ${sum_b:,.2f}")
    print(f"  Σ B − Σ A                       : ${sum_b - sum_a:,.2f}")
    improved = sum(1 for o in both if o.sim_b_pnl > o.sim_a_pnl)
    print(f"  positions improved by the fix   : {improved}/{len(both)}")

    print()
    print("  exit-type mix (first leg):")
    for label, key in (("A", "sim_a_types"), ("B", "sim_b_types")):
        mix: dict[str, int] = {}
        for o in both:
            first = getattr(o, key)[:1]
            mix[first[0] if first else "—"] = mix.get(first[0] if first else "—", 0) + 1
        print(f"    {label}: " + "  ".join(f"{k}={v}" for k, v in sorted(mix.items())))

    deltas = [o.sim_b_pnl - o.sim_a_pnl for o in both]
    changed = [d for d in deltas if abs(d) >= 0.01]
    print(f"  exits completely unchanged      : {len(both) - len(changed)}/{len(both)}")
    lo, hi = _bootstrap_sum_ci(deltas)
    print(f"  bootstrap 95% CI on Σ B−Σ A     : [${lo:,.0f}, ${hi:,.0f}]")

    print()
    print("-" * 78)
    print("LOSS DECOMPOSITION over the same sample")
    print("-" * 78)
    notional = sum(o.fill * o.qty for o in outcomes)
    slippage = sum((o.fill - o.planned_entry) * o.qty for o in outcomes)
    adverse = [o for o in outcomes if o.fill > o.planned_entry]
    actual_total = sum(o.actual_pnl for o in outcomes)
    print(f"  notional deployed               : ${notional:,.0f}")
    print(f"  actual realized (this sample)   : ${actual_total:,.2f}")
    print(f"  entry slippage cost             : ${slippage:,.0f}  "
          f"({slippage / notional * 10_000:.0f} bp of notional)")
    print(f"    adverse fills                 : {len(adverse)}/{len(outcomes)} "
          f"({len(adverse) / len(outcomes) * 100:.0f}%)")
    print(f"  §11.20 geometry fix recovers    : ${sum(deltas):,.0f}")

    unresolved = [o for o in outcomes if o.sim_a_unresolved or o.sim_b_unresolved]
    if unresolved:
        print()
        print(f"  unresolved (bar window exhausted): {len(unresolved)}")
        for o in unresolved:
            flags = ("A" if o.sim_a_unresolved else "") + ("B" if o.sim_b_unresolved else "")
            print(f"    - {o.ticker:<6} {o.entry_date}  [{flags}]")


def _bootstrap_sum_ci(values: list[float], alpha: float = 0.05) -> tuple[float, float]:
    """Percentile bootstrap CI for the SUM of the paired per-position deltas."""
    if len(values) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(BOOTSTRAP_SEED)
    sums = sorted(
        sum(rng.choices(values, k=len(values))) for _ in range(BOOTSTRAP_RESAMPLES)
    )
    return (
        sums[int(alpha / 2 * (len(sums) - 1))],
        sums[int((1 - alpha / 2) * (len(sums) - 1))],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fill-at-close",
        action="store_true",
        help="sensitivity: price next-day exits at the session CLOSE, not the OPEN",
    )
    args = parser.parse_args()
    raise SystemExit(main(fill_at_close=args.fill_at_close))
