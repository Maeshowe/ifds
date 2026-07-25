#!/usr/bin/env python3
"""Pre-registered STOP-trigger monitor — read-only, advisory.

Gate protocol §4 (`docs/planning/2026-07-25-gate-protocol-preregistration.md`).
The halt criteria were pre-registered on 2026-05-14 (decision outcome §3.14) but
nothing computed them, so a breach could only ever be discovered retroactively.
This module closes that gap.

    - 10-day excess vs SPY  < -1.0%
    - 15-day excess vs SPY  < -1.0%
    - 30-day cumulative     < -3.0%

It FLAGS and never acts: halting the paper run is a Tamás decision
(human-in-the-loop). It writes nothing to production state.

Two pre-registered readings are deliberately left open and BOTH are reported
(the wording "10 napi excess … átlag" admits a mean or a windowed sum) — see
the D3/D4 decisions in the protocol. A monitor that silently picked one could
miss a breach under the other.

Measurement caveat (surfaced, not resolved here): ``excess_return.excess_pct``
in ``daily_metrics`` is **realized-only** — on the ~38% of swing days with no
exit it equals ``-SPY``, which measures index direction, not strategy skill. The
mark-to-market variant (NetLiq day-over-day − SPY) is computed alongside as a
diagnostic wherever ``daily_equity`` covers the window.

Usage:
    python scripts/analysis/stop_trigger_monitor.py
    python scripts/analysis/stop_trigger_monitor.py --review-line
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Iterable, Mapping, Sequence

# --- pre-registered thresholds (2026-05-14 §3.14) — NOT tunable -------------
EXCESS_THRESHOLD_PCT: Final[float] = -1.0
CUM_THRESHOLD_PCT: Final[float] = -3.0
EXCESS_WINDOWS: Final[tuple[int, ...]] = (10, 15)
CUM_WINDOW: Final[int] = 30
CAPITAL_BASE: Final[float] = 100_000.0

# --- readings (the open D4 ambiguity — both are reported) -------------------
READING_MEAN: Final[str] = "mean"
READING_SUM: Final[str] = "sum"

# --- paths ------------------------------------------------------------------
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
METRICS_DIR: Final[Path] = PROJECT_ROOT / "state" / "daily_metrics"
EQUITY_PATH: Final[Path] = PROJECT_ROOT / "state" / "daily_equity.json"
CUM_PNL_PATH: Final[Path] = (
    PROJECT_ROOT / "scripts" / "paper_trading" / "logs" / "cumulative_pnl.json"
)
SWING_ERA_START: Final[str] = "2026-05-18"


@dataclass(frozen=True)
class DayRecord:
    """One trading day's return figures. Outage days simply have no record."""

    date: str
    excess_realized_pct: float
    spy_return_pct: float
    portfolio_return_pct: float
    equity: float | None


@dataclass(frozen=True)
class TriggerResult:
    name: str
    window: int
    reading: str
    value: float
    threshold: float
    breached: bool
    n_days: int
    sufficient: bool


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> Any:
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def load_equity(path: Path | None = None) -> dict[str, float]:
    """Day -> NetLiq. Missing/unreadable file degrades to an empty mapping."""
    data = _read_json(Path(path) if path is not None else EQUITY_PATH)
    return data if isinstance(data, dict) else {}


def load_day_records(
    metrics_dir: Path | None = None,
    equity: Mapping[str, float] | None = None,
    era_start: str = SWING_ERA_START,
) -> tuple[DayRecord, ...]:
    """Load the era's daily records, ascending by date.

    Days with no ``daily_metrics`` file (outages, holidays) are **absent** —
    never interpolated, per the sample-integrity rule.
    """
    directory = Path(metrics_dir) if metrics_dir is not None else METRICS_DIR
    equity_map = dict(equity) if equity is not None else load_equity()

    records: list[DayRecord] = []
    for path in sorted(directory.glob("*.json")):
        day = path.stem[:10]
        if day < era_start:
            continue
        payload = _read_json(path)
        if not isinstance(payload, dict):
            continue
        excess_block = payload.get("excess_return") or {}
        if "excess_pct" not in excess_block:
            continue
        records.append(
            DayRecord(
                date=day,
                excess_realized_pct=float(excess_block.get("excess_pct", 0.0)),
                spy_return_pct=float((payload.get("market") or {}).get("spy_return_pct", 0.0)),
                portfolio_return_pct=float(excess_block.get("portfolio_return_pct", 0.0)),
                equity=equity_map.get(day),
            )
        )
    return tuple(records)


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------


def _aggregate(values: Sequence[float], reading: str) -> float:
    total = sum(values)
    if reading == READING_SUM:
        return total
    return total / len(values) if values else 0.0


def evaluate_window(
    records: Sequence[DayRecord],
    window: int,
    reading: str = READING_MEAN,
    threshold: float = EXCESS_THRESHOLD_PCT,
    name: str | None = None,
) -> TriggerResult:
    """Evaluate one rolling excess window.

    An underpowered window (fewer than ``window`` days) is reported as
    ``sufficient=False`` and **never** breaches — a halt flag must not fire on
    a window the data cannot support.
    """
    recent = list(records)[-window:]
    values = [r.excess_realized_pct for r in recent]
    sufficient = len(values) >= window
    value = _aggregate(values, reading)
    return TriggerResult(
        name=name or f"excess_{window}d",
        window=window,
        reading=reading,
        value=value,
        threshold=threshold,
        breached=bool(sufficient and value < threshold),
        n_days=len(values),
        sufficient=sufficient,
    )


def evaluate_cumulative(
    history: Iterable[Mapping[str, Any]],
    window: int = CUM_WINDOW,
    capital: float = CAPITAL_BASE,
    threshold: float = CUM_THRESHOLD_PCT,
) -> TriggerResult:
    """Rolling N-day realized P&L as a percentage of the capital base."""
    rows = list(history)[-window:]
    total = sum(float(row.get("pnl", 0.0) or 0.0) for row in rows)
    value = (total / capital) * 100.0 if capital else 0.0
    sufficient = len(rows) >= window
    return TriggerResult(
        name=f"cum_{window}d",
        window=window,
        reading=READING_SUM,
        value=value,
        threshold=threshold,
        breached=bool(sufficient and value < threshold),
        n_days=len(rows),
        sufficient=sufficient,
    )


def mtm_excess_series(records: Sequence[DayRecord]) -> tuple[tuple[str, float], ...]:
    """Mark-to-market excess: NetLiq day-over-day change minus the SPY return.

    Only consecutive day pairs where BOTH days carry an equity value are used;
    everything else is skipped rather than approximated.
    """
    out: list[tuple[str, float]] = []
    previous: DayRecord | None = None
    for record in records:
        if previous is not None and previous.equity and record.equity:
            mtm_pct = (record.equity - previous.equity) / previous.equity * 100.0
            out.append((record.date, mtm_pct - record.spy_return_pct))
        previous = record
    return tuple(out)


def evaluate_all(
    records: Sequence[DayRecord],
    history: Iterable[Mapping[str, Any]] | None = None,
) -> tuple[TriggerResult, ...]:
    """Every pre-registered trigger, under both open readings."""
    results = [
        evaluate_window(records, window=window, reading=reading, name=f"excess_{window}d_{reading}")
        for window in EXCESS_WINDOWS
        for reading in (READING_MEAN, READING_SUM)
    ]
    if history is not None:
        results.append(evaluate_cumulative(history))
    return tuple(results)


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------


def format_review_line(results: Sequence[TriggerResult]) -> str:
    """The mandatory daily-review §5 ops-checklist line."""
    breaches = [r for r in results if r.breached]
    if breaches:
        detail = ", ".join(f"{r.name} {r.value:.1f}% < {r.threshold:.1f}%" for r in breaches)
        return f"STOP-triggerek: ⚠️ BREACH — {detail}"

    insufficient = [r for r in results if not r.sufficient]
    if insufficient:
        names = ", ".join(f"{r.name} (n={r.n_days}/{r.window})" for r in insufficient)
        return f"STOP-triggerek: ✓ nincs breach | elégtelen ablak: n/a — {names}"
    return "STOP-triggerek: ✓ nincs breach (mind a pre-reg ablak kiértékelve)"


def _render_report(records: Sequence[DayRecord], results: Sequence[TriggerResult]) -> str:
    lines = [
        "STOP-trigger monitor — pre-reg halt criteria (2026-05-14 §3.14)",
        f"Swing-éra napok (outage-napok hiányoznak, nem interpolálva): {len(records)}",
        f"Utolsó nap: {records[-1].date if records else 'n/a'}",
        "",
        f"{'trigger':<24}{'érték':>10}{'küszöb':>10}{'n':>8}  státusz",
    ]
    for r in results:
        status = "⚠️ BREACH" if r.breached else ("· elégtelen" if not r.sufficient else "✓")
        lines.append(
            f"{r.name:<24}{r.value:>9.2f}%{r.threshold:>9.1f}%{r.n_days:>8}  {status}"
        )

    mtm = mtm_excess_series(records)
    if mtm:
        window = [v for _, v in mtm[-EXCESS_WINDOWS[0] :]]
        lines += [
            "",
            "Diagnosztika — mark-to-market excess (NetLiq Δ − SPY), NEM pre-reg mező:",
            f"  utolsó {len(window)} nap átlaga: {sum(window) / len(window):+.2f}%"
            f"  (a realized-only mező ~38%-ban -SPY-t mér)",
        ]
    lines += ["", format_review_line(results)]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-registered STOP-trigger monitor (read-only)")
    parser.add_argument(
        "--review-line", action="store_true", help="print only the daily-review §5 line"
    )
    args = parser.parse_args()

    records = load_day_records()
    cumulative = _read_json(CUM_PNL_PATH) or {}
    results = evaluate_all(records, cumulative.get("daily_history", []))

    print(format_review_line(results) if args.review_line else _render_report(records, results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
