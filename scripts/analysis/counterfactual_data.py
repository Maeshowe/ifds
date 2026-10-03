#!/usr/bin/env python3
"""SIM-1 — data loaders for the §11.20 counterfactual measurement.

Read-only. Every quantity is traced to one authoritative source:

  closed positions (leg level)  state/pending_exits/*.json
  planned price + levels        output/execution_plan_run_YYYYMMDD_*.csv
  REAL entry fill               state/daily_metrics/{entry}.json
                                  → execution.slippage_per_ticker[T].filled
  actual realized P&L           state/daily_metrics/{exit}.json → trades.details[]
  daily OHLC                    research/cache/api/polygon/grouped_daily/{d}/ALL.json

Task: docs/tasks/2026-10-03-sim-counterfactual-geometry.md
"""

from __future__ import annotations

import csv
import json
import os
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from counterfactual_geometry import Bar

ROOT = Path(__file__).resolve().parents[2]
PENDING_EXITS_DIR = ROOT / "state" / "pending_exits"
DAILY_METRICS_DIR = ROOT / "state" / "daily_metrics"
PLANS_DIR = ROOT / "output"
BARS_DIR = ROOT / "research" / "cache" / "api" / "polygon" / "grouped_daily"


@dataclass(frozen=True)
class LedgerPosition:
    """A closed position as the broker-authoritative ledger records it."""

    ticker: str
    entry_date: str
    planned_entry: float
    qty: int
    sector: str
    entry_score: float
    exit_types: tuple[str, ...]  # in ledger (exit-date) order
    exit_dates: tuple[str, ...]


def load_ledger_positions(pending_exits_dir: Path = PENDING_EXITS_DIR) -> list[LedgerPosition]:
    """Group exit legs into positions by (ticker, entry_date), discovery-ordered."""
    groups: OrderedDict[tuple[str, str], list[dict]] = OrderedDict()
    for path in sorted(pending_exits_dir.glob("*.json")):
        try:
            records = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(records, list):
            continue
        for rec in records:
            key = (rec.get("ticker", ""), rec.get("entry_date", ""))
            groups.setdefault(key, []).append({**rec, "_exit_date": path.stem[:10]})

    positions: list[LedgerPosition] = []
    for (ticker, entry_date), legs in groups.items():
        legs = sorted(legs, key=lambda leg: leg["_exit_date"])
        positions.append(
            LedgerPosition(
                ticker=ticker,
                entry_date=entry_date,
                planned_entry=float(legs[0].get("entry_price") or 0.0),
                qty=sum(int(leg.get("qty") or 0) for leg in legs),
                sector=legs[0].get("sector", ""),
                entry_score=float(legs[0].get("entry_score") or 0.0),
                exit_types=tuple(leg.get("exit_type", "") for leg in legs),
                exit_dates=tuple(leg["_exit_date"] for leg in legs),
            )
        )
    return positions


def load_execution_plans(plans_dir: Path = PLANS_DIR) -> dict[str, dict[str, dict]]:
    """``{entry_date: {ticker: plan_row}}`` from the execution-plan CSVs."""
    plans: dict[str, dict[str, dict]] = defaultdict(dict)
    for path in plans_dir.glob("execution_plan_run_*.csv"):
        stamp = os.path.basename(path).split("_")[3]
        iso = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"
        try:
            with path.open() as handle:
                for row in csv.DictReader(handle):
                    plans[iso][row["instrument_id"]] = row
        except (OSError, KeyError):
            continue
    return dict(plans)


def load_entry_fills(metrics_dir: Path = DAILY_METRICS_DIR) -> dict[str, dict[str, float]]:
    """``{entry_date: {ticker: filled_price}}`` — the REAL MKT entry fills."""
    fills: dict[str, dict[str, float]] = {}
    for path in sorted(metrics_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        per_ticker = (payload.get("execution") or {}).get("slippage_per_ticker") or {}
        day = payload.get("date") or path.stem[:10]
        day_fills: dict[str, float] = {}
        for ticker, entry in per_ticker.items():
            value = (entry or {}).get("filled")
            if value is None:
                continue
            try:
                day_fills[ticker] = float(value)
            except (TypeError, ValueError):
                continue
        if day_fills:
            fills[str(day)] = day_fills
    return fills


def load_realized(metrics_dir: Path = DAILY_METRICS_DIR) -> dict[tuple[str, str], float]:
    """``{(exit_date, ticker): net pnl}`` — broker-authoritative realized P&L."""
    realized: dict[tuple[str, str], float] = {}
    for path in sorted(metrics_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        day = str(payload.get("date") or path.stem[:10])
        for detail in ((payload.get("trades") or {}).get("details") or []):
            ticker, pnl = detail.get("ticker"), detail.get("pnl")
            if ticker and pnl is not None:
                realized[(day, ticker)] = realized.get((day, ticker), 0.0) + float(pnl)
    return realized


def load_bars(tickers: set[str], days: list[date], bars_dir: Path = BARS_DIR) -> dict[date, dict[str, Bar]]:
    """``{session: {ticker: Bar}}`` for the given tickers, from the grouped cache.

    Only the requested tickers are retained — a full session is ~12,400 rows and
    the whole window would otherwise be hundreds of MB in memory.
    """
    out: dict[date, dict[str, Bar]] = {}
    for day in days:
        path = bars_dir / day.isoformat() / "ALL.json"
        if not path.exists():
            continue
        try:
            rows = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        session: dict[str, Bar] = {}
        for row in rows:
            ticker = row.get("T")
            if ticker not in tickers:
                continue
            try:
                session[ticker] = Bar(
                    date=day,
                    open=float(row["o"]),
                    high=float(row["h"]),
                    low=float(row["l"]),
                    close=float(row["c"]),
                )
            except (KeyError, TypeError, ValueError):
                continue
        out[day] = session
    return out
