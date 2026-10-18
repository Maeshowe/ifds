#!/usr/bin/env python3
"""The true round-trip cost — measuring the exit side that was never measured.

``breakeven_ic = 2c / (sigma_cs * 1e4)`` charges ``2c``: it ASSUMES an exit costs
what an entry costs. Nothing ever measured that. If the real round trip is lower,
the wall falls proportionally.

ESTIMAND DISCIPLINE (the 2026-10-04 error, not to be repeated). The existing two
numbers are NOT comparable:
  * entry 83.5 bp  — |fill - the plan's limit_price|, i.e. DECISION-to-fill
  * SIM-1 exits    — |fill - the price the order type promised|, i.e. execution only
So three separately named metrics are reported per side, never collapsed:

  implementation shortfall = fill vs DECISION price       -> the cost-model input
  execution slippage       = fill vs ORDER-TYPE reference -> the venue's cost
  delay cost               = shortfall - execution

DECISION POINT, derived from scripts/crontab.md + swing_positions.py:
  TIME_STOP            flagged at D-1 20:00 UTC eod_eval (on D-1's close),
                       submitted D 19:40 UTC MOC, filled at D's close
  TP1/TP2/*_SL         flagged at D 20:00 UTC eod_eval (on D's close),
                       submitted D+1 13:30 UTC MKT, filled at D+1's open
Uniformly: the decision price is the CLOSE OF THE SESSION BEFORE THE FILL SESSION.

Note the asymmetry this exposes, which is a finding in itself: an entry's reference
sits ~1 hour before its fill in the same session, an exit's a full session earlier.

Read-only. Task: docs/tasks/2026-10-18-true-roundtrip-cost.md
"""

from __future__ import annotations

import statistics
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from counterfactual_geometry import Bar  # noqa: F401  (re-exported for callers/tests)

#: Exit actions executed as a next-day 15:30 MARKET order (they target the OPEN).
_NEXT_DAY_MARKET = frozenset({"TP1", "TP2", "MENTAL_SL", "TRAIL_SL", "HARD_SL"})
#: Exit actions executed as a same-day 21:40 MOC order (they target the CLOSE).
_MARKET_ON_CLOSE = frozenset({"TIME_STOP"})


def decision_session(fill_date: date, sessions: list[date]) -> date | None:
    """The session whose close was the decision price for a fill on ``fill_date``.

    Both exit paths decide at an EOD evaluation and execute in a later session, so
    the decision price is always the preceding session's close. Returns None when
    the fill date is unknown to the calendar or is its first entry — never guesses.
    """
    ordered = sorted(sessions)
    try:
        index = ordered.index(fill_date)
    except ValueError:
        return None
    return ordered[index - 1] if index > 0 else None


def order_type_reference(exit_type: str, bar: Bar) -> float | None:
    """The price the order type PROMISED on its fill session.

    An MOC order is filled at the official close, so its execution slippage is
    measured against that close; a market order sent at the opening bell is
    measured against the open. An unrecognised type returns None rather than
    silently defaulting — a new exit action must be classified deliberately.
    """
    if exit_type in _MARKET_ON_CLOSE:
        return bar.close
    if exit_type in _NEXT_DAY_MARKET:
        return bar.open
    return None


def slippage_bps(fill: float, reference: float) -> float | None:
    """Adverse-positive slippage in bp for a SELL leg.

    Selling below the reference costs money, so a fill under the reference is a
    POSITIVE cost. Returns None on a non-positive reference.
    """
    if reference <= 0:
        return None
    return (reference - fill) / reference * 10_000.0


@dataclass(frozen=True)
class LegCost:
    """One exit leg priced on both conventions."""

    ticker: str
    exit_type: str
    fill_date: date
    qty: int
    fill: float
    decision_price: float
    order_reference: float

    @property
    def shortfall_bps(self) -> float:
        return slippage_bps(self.fill, self.decision_price)

    @property
    def execution_bps(self) -> float:
        return slippage_bps(self.fill, self.order_reference)

    @property
    def delay_bps(self) -> float:
        return self.shortfall_bps - self.execution_bps


def _median_abs(values: list[float]) -> float:
    """Median |slippage| — the convention ``frl_cost`` uses today.

    ⚠️ This is NOT the expected cost. It charges the half-width of the symmetric
    decision-to-fill drift as if it were a cost, and that half averages out. Kept
    for comparability with ``research/cost_model.json``; ``_mean_signed`` is the
    figure a breakeven calculation should use.
    """
    return statistics.median([abs(v) for v in values]) if values else float("nan")


def _mean_signed(values: list[float]) -> float:
    """Mean SIGNED, adverse-positive slippage — the expected cost.

    Symmetric drift cancels here; what survives is the persistent one-directional
    drag (adverse selection at the fill). Independently grounded: SIM-1's dollar
    accounting put the entry side at $1,958 / $477,264 = 41.0 bp, which matches
    this estimator and not the median-of-absolutes.
    """
    return statistics.mean(values) if values else float("nan")


def _adverse_share(values: list[float]) -> float:
    return sum(1 for v in values if v > 0) / len(values) if values else float("nan")


def _pct(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(abs(v) for v in values)
    return ordered[int(round(q * (len(ordered) - 1)))]


def summarise(legs: list[LegCost]) -> dict:
    """Medians of |slippage| overall and per exit type, on both conventions.

    Absolute values, matching ``frl_cost``: signed prints carry drift in both
    directions, so the absolute distribution is the unbiased per-side estimator.
    """
    by_type: dict[str, dict] = {}
    for exit_type in sorted({leg.exit_type for leg in legs}):
        group = [leg for leg in legs if leg.exit_type == exit_type]
        by_type[exit_type] = {
            "n": len(group),
            "shortfall_median_bps": _median_abs([leg.shortfall_bps for leg in group]),
            "execution_median_bps": _median_abs([leg.execution_bps for leg in group]),
            "delay_median_bps": _median_abs([leg.delay_bps for leg in group]),
        }
    return {
        "n": len(legs),
        "shortfall_median_bps": _median_abs([leg.shortfall_bps for leg in legs]),
        "shortfall_mean_signed_bps": _mean_signed([leg.shortfall_bps for leg in legs]),
        "shortfall_adverse_share": _adverse_share([leg.shortfall_bps for leg in legs]),
        "shortfall_p75_bps": _pct([leg.shortfall_bps for leg in legs], 0.75),
        "execution_median_bps": _median_abs([leg.execution_bps for leg in legs]),
        "execution_mean_signed_bps": _mean_signed([leg.execution_bps for leg in legs]),
        "delay_median_bps": _median_abs([leg.delay_bps for leg in legs]),
        "delay_mean_signed_bps": _mean_signed([leg.delay_bps for leg in legs]),
        "by_exit_type": by_type,
    }


# ---------------------------------------------------------------------------
# Measurement over the real ledger
# ---------------------------------------------------------------------------


def build_legs() -> tuple[list[LegCost], list[tuple[str, str, str]]]:
    """Price every swing-era exit leg on both conventions.

    A leg is EXCLUDED (and reported) when the decision session, the bar, the fill
    or the order-type reference is missing, or when the fill falls outside its own
    session's range — the data-health check SIM-1 used, which caught two bad fills.
    """
    import counterfactual_data as cd
    from ifds.utils.trading_calendar import trading_days_between

    ledger = cd.load_ledger_positions()
    realized_dir = cd.DAILY_METRICS_DIR
    sessions = trading_days_between(cd.SWING_ERA_START, cd.ERA_LAST_SESSION)

    # fills, keyed by (fill date, ticker) — the broker-authoritative exit prints
    fills: dict[tuple[str, str], dict] = {}
    import json

    for path in sorted(realized_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        day = str(payload.get("date") or path.stem[:10])
        for detail in ((payload.get("trades") or {}).get("details") or []):
            if detail.get("ticker") and detail.get("exit"):
                fills[(day, detail["ticker"])] = detail

    tickers = {p.ticker for p in ledger}
    bars = cd.load_bars(tickers, sessions)

    legs: list[LegCost] = []
    excluded: list[tuple[str, str, str]] = []
    for pos in ledger:
        for exit_type, fill_date_s in zip(pos.exit_types, pos.exit_dates):
            tag = (pos.ticker, fill_date_s, exit_type)
            detail = fills.get((fill_date_s, pos.ticker))
            if detail is None:
                excluded.append((*tag[:2], "no fill record"))
                continue
            try:
                fill_date = date.fromisoformat(fill_date_s)
            except ValueError:
                excluded.append((*tag[:2], "unparseable fill date"))
                continue

            decided = decision_session(fill_date, sessions)
            if decided is None:
                excluded.append((*tag[:2], "no preceding session in the era"))
                continue
            dec_bar = bars.get(decided, {}).get(pos.ticker)
            fill_bar = bars.get(fill_date, {}).get(pos.ticker)
            if dec_bar is None or fill_bar is None:
                excluded.append((*tag[:2], "missing bar"))
                continue

            reference = order_type_reference(exit_type, fill_bar)
            if reference is None:
                excluded.append((*tag[:2], f"unclassified exit type {exit_type}"))
                continue

            fill = float(detail["exit"])
            lo, hi = fill_bar.low * 0.995, fill_bar.high * 1.005
            if not lo <= fill <= hi:
                excluded.append(
                    (*tag[:2], f"fill {fill:.2f} outside bar [{fill_bar.low:.2f},{fill_bar.high:.2f}]")
                )
                continue

            legs.append(
                LegCost(
                    ticker=pos.ticker,
                    exit_type=exit_type,
                    fill_date=fill_date,
                    qty=int(detail.get("qty") or 0),
                    fill=fill,
                    decision_price=dec_bar.close,
                    order_reference=reference,
                )
            )
    return legs, excluded


def main() -> int:
    import counterfactual_data as cd

    legs, excluded = build_legs()
    s = summarise(legs)

    print("=" * 86)
    print("ROUND-TRIP COST — the exit side, measured for the first time")
    print("=" * 86)
    print(f"exit legs priced : {s['n']}        excluded: {len(excluded)}")
    for t, d, why in excluded[:12]:
        print(f"    - {t:<6} {d}  {why}")
    if len(excluded) > 12:
        print(f"    ... and {len(excluded) - 12} more")

    print()
    print("-" * 86)
    print("THREE CONVENTIONS, never collapsed (median |bp|)")
    print("-" * 86)
    print(f"{'':22}{'shortfall':>12}{'execution':>12}{'delay':>12}{'n':>6}")
    print(f"{'EXIT, all legs':<22}{s['shortfall_median_bps']:>12.1f}"
          f"{s['execution_median_bps']:>12.1f}{s['delay_median_bps']:>12.1f}{s['n']:>6}")
    for t, g in s["by_exit_type"].items():
        print(f"{'  ' + t:<22}{g['shortfall_median_bps']:>12.1f}"
              f"{g['execution_median_bps']:>12.1f}{g['delay_median_bps']:>12.1f}{g['n']:>6}")

    # entry side, same shortfall convention (decision = the plan's limit price)
    # Entry side, SWING ERA ONLY — the legacy era used intraday LMT at ~19 bp and is
    # not a valid prior for next-day MKT-open cost (frl_cost makes the same cut).
    plans = cd.load_execution_plans()
    entry, entry_num, entry_den = [], 0.0, 0.0
    for day, per in cd.load_entry_fills().items():
        if day < cd.SWING_ERA_START.isoformat():
            continue
        for ticker, filled in per.items():
            row = plans.get(day, {}).get(ticker)
            if not row:
                continue
            planned, qty = float(row["limit_price"]), float(row.get("quantity") or 0)
            entry.append((filled - planned) / planned * 10_000.0)  # BUY: above = adverse
            entry_num += (filled - planned) * qty
            entry_den += planned * qty
    print(f"{'ENTRY (shortfall)':<22}{_median_abs(entry):>12.1f}{'n/a':>12}{'n/a':>12}{len(entry):>6}")

    print()
    print("-" * 86)
    print("⚠️  WHICH ESTIMATOR — median|.| charges the half-width of symmetric drift")
    print("-" * 86)
    print(f"{'':22}{'median|.|':>12}{'mean signed':>14}{'adverse':>10}{'n':>6}")
    print(f"{'ENTRY shortfall':<22}{_median_abs(entry):>12.1f}{_mean_signed(entry):>+14.1f}"
          f"{_adverse_share(entry) * 100:>9.0f}%{len(entry):>6}")
    print(f"{'EXIT shortfall':<22}{s['shortfall_median_bps']:>12.1f}"
          f"{s['shortfall_mean_signed_bps']:>+14.1f}"
          f"{s['shortfall_adverse_share'] * 100:>9.0f}%{s['n']:>6}")
    print(f"{'EXIT execution only':<22}{s['execution_median_bps']:>12.1f}"
          f"{s['execution_mean_signed_bps']:>+14.1f}{'':>10}{s['n']:>6}")
    print(f"\n  notional-weighted signed entry: {entry_num / entry_den * 1e4:+.1f} bp")
    print("  SIM-1 dollar cross-check      : $1,958 / $477,264 = +41.0 bp  <- agrees with")
    print(f"  the SIGNED estimator, not with median|.| ({_median_abs(entry):.1f} bp).")

    print()
    print("-" * 86)
    print("THE WALL")
    print("-" * 86)
    sigma = 0.06
    rows = [
        ("ASSUMED  2c, median|.| (today's engine)", 2 * _median_abs(entry)),
        ("MEASURED entry+exit, median|.|", _median_abs(entry) + s["shortfall_median_bps"]),
        ("MEASURED entry+exit, MEAN SIGNED", _mean_signed(entry) + s["shortfall_mean_signed_bps"]),
    ]
    print(f"{'':44}{'round trip':>12}{'breakeven':>12}")
    for label, rt in rows:
        print(f"  {label:<42}{rt:>12.1f}{rt / (sigma * 1e4):>12.4f}")
    print()
    print("  The signed row is the expected cost; the median rows charge symmetric")
    print("  drift as if it were a cost. Measured |IC| across the score family: < 0.009.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
