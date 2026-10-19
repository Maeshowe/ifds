"""FRL — per-side execution friction measured from real fills (pre-reg D-C1).

The cost model used to charge ``2 * median(|entry slippage|)``, which made two
assumptions nobody had measured: that an exit costs what an entry costs, and
that the half-width of SYMMETRIC decision-to-fill drift is a cost. Both are
wrong. This module measures the thing that is actually a cost — the fill against
the price the trade could have had at the moment it traded — separately on each
side, and the engine adds the two.

    entry (BUY)   adverse = filling ABOVE the open   -> (fill - open) / open
    exit  (SELL)  adverse = filling BELOW the order  -> (ref - fill) / ref

The exit reference is set by the ORDER TYPE: a market-on-close order is promised
the official close, a market order sent at the bell is promised the open. An
unclassified exit action returns no reference rather than defaulting, so a new
action has to be classified deliberately.

Everything here is injectable. The loaders take explicit paths and the estimators
take already-built legs, so a test never has to reach production state — the
third occurrence of the "prod-state must not make the test green" rule was caught
in exactly this surface (ERRATA §E-8/D-E3).

Pre-reg: docs/planning/2026-10-19-cost-estimator-amendment.md, §5 and its ERRATA
§E-1..§E-7 (D-E1..D-E6, approved 2026-10-19).
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import frl_config as cfg

#: Exit actions executed as a next-day market order at the bell — they get the open.
NEXT_DAY_MARKET: frozenset[str] = frozenset(
    {"TP1", "TP2", "MENTAL_SL", "TRAIL_SL", "HARD_SL"}
)
#: Exit actions executed as a same-day market-on-close order — they get the close.
MARKET_ON_CLOSE: frozenset[str] = frozenset({"TIME_STOP"})

ENTRY: str = "entry"
EXIT: str = "exit"

#: Where a leg's fill price came from, so the report can separate the two sources.
SOURCE_METRICS: str = "daily_metrics"
SOURCE_BACKFILL: str = "broker_backfill"


@dataclass(frozen=True)
class Bar:
    """One session's OHLC for one ticker."""

    day: date
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class Leg:
    """One executed leg priced against the reference its order type promised."""

    side: str
    ticker: str
    day: date
    qty: int
    fill: float
    reference: float
    source: str
    order_type: str = ""

    @property
    def friction_bps(self) -> float:
        """Adverse-positive friction in basis points.

        A BUY filling above its reference and a SELL filling below its reference
        both cost money, so both come out POSITIVE.
        """
        if self.reference <= 0:
            return float("nan")
        signed = (
            self.fill - self.reference if self.side == ENTRY else self.reference - self.fill
        )
        return signed / self.reference * 10_000.0

    @property
    def notional(self) -> float:
        """Reference notional — the weight for a portfolio-level first moment."""
        return self.reference * max(self.qty, 0)


# ---------------------------------------------------------------------------
# Loaders — every path injectable, nothing resolved implicitly
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> object | None:
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _parse_day(raw: object, fallback: str) -> date | None:
    try:
        return date.fromisoformat(str(raw or fallback))
    except (TypeError, ValueError):
        return None


def load_entry_fills(
    metrics_dir: Path, era: str | None = cfg.ERA_SWING
) -> list[tuple[date, str, float, int | None]]:
    """``(day, ticker, fill, qty)`` for every recorded entry fill.

    ``qty`` is None when the row predates the writer emitting it — a MISSING
    field, which is not a zero. The two are kept distinct here precisely because
    conflating them produced a pre-registered rule that matched nothing
    (ERRATA §E-1).
    """
    rows: list[tuple[date, str, float, int | None]] = []
    if not metrics_dir.exists():
        return rows
    for path in sorted(metrics_dir.glob("*.json")):
        payload = _read_json(path)
        if not isinstance(payload, dict):
            continue
        day = _parse_day(payload.get("date"), path.stem[:10])
        if day is None or (era is not None and cfg.era_of(day) != era):
            continue
        per_ticker = (payload.get("execution") or {}).get("slippage_per_ticker") or {}
        for ticker, entry in per_ticker.items():
            if not entry or entry.get("filled") is None:
                continue
            try:
                fill = float(entry["filled"])
            except (TypeError, ValueError):
                continue
            qty = int(float(entry["qty"])) if "qty" in entry else None
            rows.append((day, ticker, fill, qty))
    return rows


def load_exit_records(pending_exits_dir: Path, era: str | None = cfg.ERA_SWING) -> list[dict]:
    """One record per EXIT LEG, dated by the file it was written into.

    ``state/pending_exits/<day>.json`` is the broker-authoritative record of the
    legs that exited that session, so the filename IS the exit date — the same
    convention ``counterfactual_data.load_ledger_positions`` uses, kept identical
    so the research engine and the 2026-10-18 report price the same sample.
    """
    records: list[dict] = []
    if not pending_exits_dir.exists():
        return records
    for path in sorted(pending_exits_dir.glob("*.json")):
        exit_day = _parse_day(path.stem[:10], "")
        if exit_day is None or (era is not None and cfg.era_of(exit_day) != era):
            continue
        payload = _read_json(path)
        if not isinstance(payload, list):
            continue
        for row in payload:
            if not isinstance(row, dict) or not row.get("ticker"):
                continue
            records.append({**row, "_exit_day": exit_day})
    return records


def entry_quantities(exit_records: Sequence[Mapping]) -> dict[tuple[date, str], int]:
    """``{(entry day, ticker): shares}`` — a position's size is its legs summed.

    This is the only place the recovered backfill legs can get a share count:
    the backfill map carries prices only, and the rows that predate the writer
    emitting ``qty`` carry none either (ERRATA §E-1, §E-4).
    """
    totals: dict[tuple[date, str], int] = {}
    for row in exit_records:
        entry_day = _parse_day(row.get("entry_date"), "")
        ticker = row.get("ticker")
        if entry_day is None or not ticker:
            continue
        totals[(entry_day, ticker)] = totals.get((entry_day, ticker), 0) + int(row.get("qty") or 0)
    return totals


def load_exit_fills(metrics_dir: Path) -> dict[tuple[date, str], dict]:
    """``{(fill day, ticker): detail}`` — the broker-authoritative exit prints."""
    fills: dict[tuple[date, str], dict] = {}
    if not metrics_dir.exists():
        return fills
    for path in sorted(metrics_dir.glob("*.json")):
        payload = _read_json(path)
        if not isinstance(payload, dict):
            continue
        day = _parse_day(payload.get("date"), path.stem[:10])
        if day is None:
            continue
        for detail in (payload.get("trades") or {}).get("details") or []:
            if detail.get("ticker") and detail.get("exit") is not None:
                fills[(day, detail["ticker"])] = detail
    return fills


def load_backfill_fills(path: Path) -> dict[tuple[date, str], float]:
    """Broker-authoritative IBKR BUY fills recovered for the recorder's dead window.

    The entry recorder emitted nothing for the first 13 swing sessions, so the
    entry and exit samples covered DIFFERENT populations (ERRATA §E-4). These
    rows restore the alignment; ``_note`` is metadata, not a date.
    """
    payload = _read_json(path)
    out: dict[tuple[date, str], float] = {}
    if not isinstance(payload, dict):
        return out
    for raw_day, per_ticker in payload.items():
        day = _parse_day(raw_day, "")
        if day is None or not isinstance(per_ticker, dict):
            continue
        for ticker, price in per_ticker.items():
            try:
                out[(day, ticker)] = float(price)
            except (TypeError, ValueError):
                continue
    return out


def load_bars(tickers: set[str], days: Iterable[date], bars_dir: Path) -> dict[date, dict[str, Bar]]:
    """``{session: {ticker: Bar}}`` from the grouped daily cache, requested names only."""
    out: dict[date, dict[str, Bar]] = {}
    for day in days:
        rows = _read_json(bars_dir / day.isoformat() / "ALL.json")
        if not isinstance(rows, list):
            continue
        session: dict[str, Bar] = {}
        for row in rows:
            ticker = row.get("T") if isinstance(row, dict) else None
            if ticker not in tickers:
                continue
            try:
                session[ticker] = Bar(
                    day=day,
                    open=float(row["o"]),
                    high=float(row["h"]),
                    low=float(row["l"]),
                    close=float(row["c"]),
                )
            except (KeyError, TypeError, ValueError):
                continue
        if session:
            out[day] = session
    return out


# ---------------------------------------------------------------------------
# Leg construction
# ---------------------------------------------------------------------------


def order_type_reference(exit_type: str, bar: Bar) -> float | None:
    """The price the exit's order type promised on its fill session."""
    if exit_type in MARKET_ON_CLOSE:
        return bar.close
    if exit_type in NEXT_DAY_MARKET:
        return bar.open
    return None


def _fill_is_in_bar(fill: float, bar: Bar, tolerance: float) -> bool:
    return bar.low * (1.0 - tolerance) <= fill <= bar.high * (1.0 + tolerance)


def build_entry_legs(
    recorded: Sequence[tuple[date, str, float, int | None]],
    quantities: Mapping[tuple[date, str], int],
    bars: Mapping[date, Mapping[str, Bar]],
    backfill: Mapping[tuple[date, str], float] | None = None,
    tolerance: float = cfg.FILL_IN_BAR_TOLERANCE,
) -> tuple[list[Leg], list[tuple[str, str, str]]]:
    """Price every entry against its session OPEN, recovering the dead window.

    ``quantities`` supplies the share count, which the recorded rows lack before
    2026-06-08 and the backfill map never carries. A position with no fill from
    either source, no bar, or a fill outside its own session's range is excluded
    and REPORTED — silent truncation reads as full coverage (D-E1, D-E3).
    """
    qty_by_key = {k: v for k, v in quantities.items() if v}
    recorded_by_key = {(day, ticker): (fill, qty) for day, ticker, fill, qty in recorded}
    keys = sorted(set(recorded_by_key) | set(qty_by_key))

    legs: list[Leg] = []
    excluded: list[tuple[str, str, str]] = []
    for day, ticker in keys:
        recorded_row = recorded_by_key.get((day, ticker))
        if recorded_row is not None:
            fill, row_qty = recorded_row
            source = SOURCE_METRICS
        elif backfill and (day, ticker) in backfill:
            fill, row_qty = backfill[(day, ticker)], None
            source = SOURCE_BACKFILL
        else:
            excluded.append((ticker, day.isoformat(), "no entry fill in either source"))
            continue

        qty = row_qty if row_qty else qty_by_key.get((day, ticker))
        if not qty:
            excluded.append((ticker, day.isoformat(), "no share count in any source"))
            continue

        bar = (bars.get(day) or {}).get(ticker)
        if bar is None:
            excluded.append((ticker, day.isoformat(), "missing bar"))
            continue
        if bar.open <= 0:
            excluded.append((ticker, day.isoformat(), "non-positive open"))
            continue
        if not _fill_is_in_bar(fill, bar, tolerance):
            excluded.append(
                (
                    ticker,
                    day.isoformat(),
                    f"fill {fill:.2f} outside bar [{bar.low:.2f}, {bar.high:.2f}]",
                )
            )
            continue

        legs.append(
            Leg(
                side=ENTRY,
                ticker=ticker,
                day=day,
                qty=int(qty),
                fill=fill,
                reference=bar.open,
                source=source,
                order_type="MKT_OPEN",
            )
        )
    return legs, excluded


def build_exit_legs(
    exit_records: Sequence[Mapping],
    exit_fills: Mapping[tuple[date, str], Mapping],
    bars: Mapping[date, Mapping[str, Bar]],
    tolerance: float = cfg.FILL_IN_BAR_TOLERANCE,
) -> tuple[list[Leg], list[tuple[str, str, str]]]:
    """Price every exit leg against the reference its ORDER TYPE promised.

    ``qty`` falls back to the leg's own position record when the fill detail
    omits it: a missing field is not a zero, and five real adverse TP1 partials
    carry no qty (ERRATA §E-1). Dropping them would move the estimate in the
    permissive direction, which is what the governing rule forbids.
    """
    legs: list[Leg] = []
    excluded: list[tuple[str, str, str]] = []
    for row in exit_records:
        ticker = str(row.get("ticker"))
        exit_day = row["_exit_day"]
        exit_type = str(row.get("exit_type") or "")
        record = exit_fills.get((exit_day, ticker))
        if record is None:
            excluded.append((ticker, exit_day.isoformat(), "no exit fill record"))
            continue
        bar = (bars.get(exit_day) or {}).get(ticker)
        if bar is None:
            excluded.append((ticker, exit_day.isoformat(), "missing bar"))
            continue
        reference = order_type_reference(exit_type, bar)
        if reference is None:
            excluded.append(
                (ticker, exit_day.isoformat(), f"unclassified exit type {exit_type!r}")
            )
            continue
        if reference <= 0:
            excluded.append((ticker, exit_day.isoformat(), "non-positive reference"))
            continue
        try:
            fill = float(record["exit"])
        except (KeyError, TypeError, ValueError):
            excluded.append((ticker, exit_day.isoformat(), "unparseable exit price"))
            continue
        if not _fill_is_in_bar(fill, bar, tolerance):
            excluded.append(
                (
                    ticker,
                    exit_day.isoformat(),
                    f"fill {fill:.2f} outside bar [{bar.low:.2f}, {bar.high:.2f}]",
                )
            )
            continue
        qty = record.get("qty") or row.get("qty") or 0
        legs.append(
            Leg(
                side=EXIT,
                ticker=ticker,
                day=exit_day,
                qty=int(qty),
                fill=fill,
                reference=reference,
                source=SOURCE_METRICS,
                order_type=exit_type,
            )
        )
    return legs, excluded


# ---------------------------------------------------------------------------
# Estimators
# ---------------------------------------------------------------------------


def point_estimate(legs: Sequence[Leg], weighted: bool) -> float:
    """Mean adverse-positive friction, notional-weighted or equally weighted."""
    usable = [leg for leg in legs if math.isfinite(leg.friction_bps)]
    if not usable:
        return float("nan")
    if not weighted:
        return sum(leg.friction_bps for leg in usable) / len(usable)
    denominator = sum(leg.notional for leg in usable)
    if denominator <= 0:
        return float("nan")
    return sum(leg.friction_bps * leg.notional for leg in usable) / denominator


def _group_by_day(legs: Sequence[Leg]) -> dict[date, list[Leg]]:
    grouped: dict[date, list[Leg]] = {}
    for leg in legs:
        if math.isfinite(leg.friction_bps):
            grouped.setdefault(leg.day, []).append(leg)
    return grouped


def bootstrap_ucb(
    legs: Sequence[Leg],
    weighted: bool,
    confidence: float = cfg.COST_UCB_CONFIDENCE,
    replicates: int = cfg.COST_BOOTSTRAP_REPLICATES,
    seed: int = cfg.COST_BOOTSTRAP_SEED,
) -> float:
    """One-sided upper confidence bound on the MEAN, clustering by session.

    Fills within a session share the day's execution conditions, so the day is
    the resampling unit; resampling individual legs would understate the spread.
    Seeded, because a persisted cost model has to be reproducible bit-for-bit.
    """
    grouped = _group_by_day(legs)
    days = sorted(grouped)
    if len(days) < 2:
        return float("nan")
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(replicates):
        picked = rng.choices(days, k=len(days))
        numerator = denominator = 0.0
        for day in picked:
            for leg in grouped[day]:
                weight = leg.notional if weighted else 1.0
                numerator += leg.friction_bps * weight
                denominator += weight
        if denominator > 0:
            draws.append(numerator / denominator)
    if not draws:
        return float("nan")
    draws.sort()
    return draws[min(len(draws) - 1, int(round(confidence * (len(draws) - 1))))]


def coverage(legs: Sequence[Leg]) -> dict:
    """Measured coverage header — never assumed, always printed (spec rule 2026-10-04)."""
    days = sorted({leg.day for leg in legs})
    by_source: dict[str, int] = {}
    for leg in legs:
        by_source[leg.source] = by_source.get(leg.source, 0) + 1
    return {
        "n_legs": len(legs),
        "n_days": len(days),
        "first_day": days[0].isoformat() if days else None,
        "last_day": days[-1].isoformat() if days else None,
        "legs_by_source": dict(sorted(by_source.items())),
        "notional": round(sum(leg.notional for leg in legs), 2),
    }


def by_order_type(legs: Sequence[Leg]) -> dict[str, dict]:
    """Per-order-type report fields. Never averaged across types — see pre-reg §4."""
    out: dict[str, dict] = {}
    for order_type in sorted({leg.order_type for leg in legs}):
        group = [leg for leg in legs if leg.order_type == order_type]
        out[order_type] = {
            "n": len(group),
            "point_bps": round(point_estimate(group, weighted=False), 2),
            "notional_share": round(
                sum(leg.notional for leg in group) / max(sum(l.notional for l in legs), 1e-9), 4
            ),
        }
    return out
