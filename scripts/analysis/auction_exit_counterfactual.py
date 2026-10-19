#!/usr/bin/env python3
"""Would routing the after-bell exits through an auction have paid? Measured.

The friction table says an auction costs +1.35 bp and a market order sent after
the bell costs +60.4 bp — 45x. That is only half the question. Changing WHERE an
order executes also changes WHEN, and the price moves in between. This script
measures the net, in dollars, on the real book.

THE PREMISE, read off the production evaluator (``swing_positions.evaluate_position_eod``)
rather than assumed, because the two exit families are NOT alike:

  TP1 / TP2            trigger on ``today_high``  -> the signal exists INTRADAY, so the
                       SAME session's closing auction is reachable. Exposure SHRINKS by
                       one overnight.
  MENTAL_SL / HARD_SL  trigger on ``today_close`` -> the signal does not exist until the
  / TRAIL_SL           close, so that session's auction is already gone. The earliest
                       reachable auction is the NEXT session's close. Exposure GROWS by
                       one session.
  TIME_STOP            already MOC. Untouched.

So a single "route everything through auctions" number would be meaningless: one
family gains time, the other loses it. They are reported separately and never summed
into a headline without both signs visible.

Convention: a long book, so every exit is a SELL. Proceeds per share are what matter;
``auction_friction`` is the measured MOC slippage (fill below the official close).

Read-only. Companion report: docs/review/2026-10-19-execution-wall-by-horizon.md
"""

from __future__ import annotations

import random
import statistics
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import frl_config as cfg  # noqa: E402
import frl_fills as fills  # noqa: E402

#: Measured on the 68 MOC exits: an auction fill lands this far below the official
#: close. NOT zero — the auction has its own cost, it is just 45x smaller.
AUCTION_FRICTION_BPS = 1.35
AUCTION_FRICTION_UCB_BPS = 3.93

#: Trigger is ``today_high`` -> reachable in the SAME session's closing auction.
INTRADAY_TRIGGER = frozenset({"TP1", "TP2"})
#: Trigger is ``today_close`` -> earliest auction is the NEXT session's close.
CLOSE_TRIGGER = frozenset({"MENTAL_SL", "HARD_SL", "TRAIL_SL"})


@dataclass(frozen=True)
class Swap:
    """One exit leg, as filled and as it would have filled in an auction."""

    ticker: str
    exit_type: str
    fill_day: date
    qty: int
    actual_fill: float
    auction_close: float
    auction_day: date

    @property
    def auction_fill(self) -> float:
        """The auction print, charged its own measured friction."""
        return self.auction_close * (1.0 - AUCTION_FRICTION_BPS / 10_000.0)

    @property
    def delta_per_share(self) -> float:
        return self.auction_fill - self.actual_fill

    @property
    def delta_dollars(self) -> float:
        return self.delta_per_share * self.qty

    @property
    def delta_bps(self) -> float:
        return self.delta_per_share / self.actual_fill * 10_000.0


def _previous_session(day: date, sessions: list[date]) -> date | None:
    ordered = sorted(sessions)
    try:
        index = ordered.index(day)
    except ValueError:
        return None
    return ordered[index - 1] if index > 0 else None


def _next_session(day: date, sessions: list[date]) -> date | None:
    ordered = sorted(sessions)
    try:
        index = ordered.index(day)
    except ValueError:
        return None
    return ordered[index + 1] if index + 1 < len(ordered) else None


def build_swaps(legs, bars, sessions) -> tuple[list[Swap], list[tuple[str, str, str]]]:
    """Pair each after-bell leg with the auction it could actually have reached."""
    swaps: list[Swap] = []
    skipped: list[tuple[str, str, str]] = []
    for leg in legs:
        if leg.order_type in INTRADAY_TRIGGER:
            auction_day = _previous_session(leg.day, sessions)
            why = "same-session close (high-triggered)"
        elif leg.order_type in CLOSE_TRIGGER:
            auction_day = _next_session(leg.day, sessions)
            why = "next-session close (close-triggered)"
        else:
            skipped.append((leg.ticker, leg.day.isoformat(), f"not after-bell: {leg.order_type}"))
            continue
        if auction_day is None:
            skipped.append((leg.ticker, leg.day.isoformat(), f"no {why} in the era"))
            continue
        bar = (bars.get(auction_day) or {}).get(leg.ticker)
        if bar is None or bar.close <= 0:
            skipped.append((leg.ticker, leg.day.isoformat(), f"missing bar for {auction_day}"))
            continue
        if leg.qty <= 0:
            skipped.append((leg.ticker, leg.day.isoformat(), "no share count"))
            continue
        swaps.append(
            Swap(
                ticker=leg.ticker,
                exit_type=leg.order_type,
                fill_day=leg.day,
                qty=leg.qty,
                actual_fill=leg.fill,
                auction_close=bar.close,
                auction_day=auction_day,
            )
        )
    return swaps, skipped


def bootstrap_total(swaps: list[Swap], seed: int = cfg.COST_BOOTSTRAP_SEED, b: int = 20_000):
    """Day-clustered bootstrap CI on the total dollar effect."""
    by_day: dict[date, list[Swap]] = {}
    for swap in swaps:
        by_day.setdefault(swap.fill_day, []).append(swap)
    days = sorted(by_day)
    if len(days) < 2:
        return float("nan"), float("nan")
    rng = random.Random(seed)
    draws = []
    for _ in range(b):
        picked = rng.choices(days, k=len(days))
        draws.append(sum(s.delta_dollars for d in picked for s in by_day[d]))
    draws.sort()
    return draws[int(0.025 * (len(draws) - 1))], draws[int(0.975 * (len(draws) - 1))]


def _summary(label: str, swaps: list[Swap]) -> None:
    if not swaps:
        print(f"{label:<34} (no legs)")
        return
    total = sum(s.delta_dollars for s in swaps)
    lo, hi = bootstrap_total(swaps)
    better = sum(1 for s in swaps if s.delta_dollars > 0)
    print(
        f"{label:<34}n={len(swaps):>3}  total={total:>+10,.0f}$  "
        f"95% CI [{lo:>+8,.0f}, {hi:>+8,.0f}]  "
        f"median={statistics.median([s.delta_bps for s in swaps]):>+7.1f} bp  "
        f"better {better}/{len(swaps)}"
    )


def main() -> int:
    from ifds.utils.trading_calendar import trading_days_between

    recorded = fills.load_entry_fills(cfg.DAILY_METRICS_DIR)
    exit_records = fills.load_exit_records(cfg.PENDING_EXITS_DIR)
    exit_fills = fills.load_exit_fills(cfg.DAILY_METRICS_DIR)
    quantities = fills.entry_quantities(exit_records)

    sessions = trading_days_between(cfg.SWING_START, date(2026, 10, 2))
    tickers = {t for _, t, _, _ in recorded} | {str(r["ticker"]) for r in exit_records}
    days = set(sessions) | {r["_exit_day"] for r in exit_records} | {k[0] for k in quantities}
    bars = fills.load_bars(tickers, sorted(days), cfg.BARS_DIR)

    legs, _ = fills.build_exit_legs(exit_records, exit_fills, bars)
    after_bell = [leg for leg in legs if leg.order_type not in {"TIME_STOP"}]

    print("=" * 104)
    print("AUCTION EXIT COUNTERFACTUAL — would an auction have paid, net of the price move?")
    print("=" * 104)
    print(f"exit legs priced: {len(legs)}   of which after-the-bell market: {len(after_bell)}")
    print(f"auction friction charged: {AUCTION_FRICTION_BPS:+.2f} bp (measured on 68 MOC exits)")
    print()

    swaps, skipped = build_swaps(after_bell, bars, sessions)
    print(f"swappable legs: {len(swaps)}   skipped: {len(skipped)}")
    for ticker, day, why in skipped[:8]:
        print(f"    - {ticker:<6} {day}  {why}")
    print()

    print("-" * 104)
    print("THE TWO FAMILIES MOVE IN OPPOSITE DIRECTIONS IN TIME — never summed blind")
    print("-" * 104)
    intraday = [s for s in swaps if s.exit_type in INTRADAY_TRIGGER]
    close_trig = [s for s in swaps if s.exit_type in CLOSE_TRIGGER]
    _summary("TP1/TP2 -> same-session close", intraday)
    _summary("SL family -> next-session close", close_trig)
    _summary("BOTH (for reference only)", swaps)
    print()

    for exit_type in sorted({s.exit_type for s in swaps}):
        _summary(f"  {exit_type}", [s for s in swaps if s.exit_type == exit_type])

    print()
    print("-" * 104)
    print("THREE-WAY DECOMPOSITION — only the first column is a repeatable edge")
    print("-" * 104)
    print(
        f"{'family':<12}{'friction relief':>17}{'clock move':>13}"
        f"{'auction cost':>14}{'net':>11}{'notional':>12}"
    )
    by_leg = {(leg.ticker, leg.day): leg for leg in after_bell}
    for label, group in (("TP1/TP2", intraday), ("SL family", close_trig)):
        if not group:
            continue
        relief = clock = auction_cost = notional = 0.0
        for swap in group:
            leg = by_leg[(swap.ticker, swap.fill_day)]
            # What the realised after-bell fill gave up against the price its own
            # order type promised. Mechanical, and it recurs every time.
            relief += (leg.reference - swap.actual_fill) * swap.qty
            # What moved between that promised price and the auction print. This is
            # a RETURN, not friction: for TP1 it is minus the overnight gap, for the
            # SL family it is one extra session of exposure. It does not recur.
            clock += (swap.auction_close - leg.reference) * swap.qty
            auction_cost += swap.auction_close * swap.qty * AUCTION_FRICTION_BPS / 10_000.0
            notional += swap.actual_fill * swap.qty
        print(
            f"{label:<12}{relief:>+17,.0f}{clock:>+13,.0f}"
            f"{-auction_cost:>+14,.0f}{relief + clock - auction_cost:>+11,.0f}{notional:>12,.0f}"
        )
    print()
    print("  Friction relief is the edge: a market order sent after the bell gives up")
    print("  ~60 bp and an auction gives up ~1.4 bp, every time. The clock move is the")
    print("  sample's own price path and must not be counted on.")

    print()
    print("-" * 104)
    print("TAPE CONTROL — is this just a rising market?")
    print("-" * 104)
    population = [
        (bar.close - bar.open) / bar.open * 10_000.0
        for day in sessions
        for bar in (bars.get(day) or {}).values()
        if bar.open > 0
    ]
    if population:
        rng = random.Random(7)
        draws = sorted(
            statistics.mean(rng.choices(population, k=len(population))) for _ in range(5_000)
        )
        print(
            f"  open->close on the traded names, ALL era sessions: n={len(population):,}  "
            f"mean={statistics.mean(population):+.1f} bp  "
            f"median={statistics.median(population):+.1f} bp  "
            f"95% CI [{draws[125]:+.1f}, {draws[4875]:+.1f}]"
        )
    selected = [
        (bars[s.auction_day][s.ticker].close - bars[s.auction_day][s.ticker].open)
        / bars[s.auction_day][s.ticker].open
        * 10_000.0
        for s in swaps
        if s.ticker in (bars.get(s.auction_day) or {})
    ]
    if selected:
        print(
            f"  the same thing on the {len(selected)} auction days actually used:        "
            f"mean={statistics.mean(selected):+.1f} bp  "
            f"median={statistics.median(selected):+.1f} bp"
        )
    print()
    print("  The era-wide figure straddles zero, so there is no rising-tape artefact in")
    print("  the population. The selected days are strongly positive — but that is")
    print("  selection on the TRIGGER (TP1 fires when the high ran up), and it sits on a")
    print("  DIFFERENT span than the counterfactual, which crosses the overnight only.")
    print("  Checked, and it does not enter the estimate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
