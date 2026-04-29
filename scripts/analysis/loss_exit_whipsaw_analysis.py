#!/usr/bin/env python3
"""LOSS_EXIT Whipsaw Cost Retrospective Audit.

Read-only analysis script. Does NOT modify any pipeline state.

Question:
    Does the -2% LOSS_EXIT rule help or hurt on average?

For every historical LOSS_EXIT trade since BC23 deploy (2026-04-13), the
script computes the counterfactual P&L assuming the position had been held
to MOC (using Polygon's daily close as the MOC fill proxy):

    counterfactual_moc_pnl = (moc_close - entry_price) * qty
    whipsaw_cost           = actual_pnl - counterfactual_moc_pnl

Whipsaw cost interpretation:
    < 0  → LOSS_EXIT made it worse (whipsaw — stop hit, price recovered)
    > 0  → LOSS_EXIT saved money (price kept falling after stop)
    ≈ 0  → neutral (stop level matched MOC)

Inputs:
    - scripts/paper_trading/logs/trades_YYYY-MM-DD.csv  (per-day trade rows)
    - Polygon daily aggregates (cached)

Outputs:
    - docs/analysis/loss-exit-whipsaw-analysis.md (markdown report)
    - state/loss_exit_whipsaw_cache.json (Polygon close cache)

Usage:
    python scripts/analysis/loss_exit_whipsaw_analysis.py
    python scripts/analysis/loss_exit_whipsaw_analysis.py \\
        --start 2026-04-13 --end 2026-04-29 \\
        --output docs/analysis/loss-exit-whipsaw-analysis.md
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import logging
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import mean, median

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("whipsaw")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRADES_DIR = PROJECT_ROOT / "scripts" / "paper_trading" / "logs"
CACHE_FILE = PROJECT_ROOT / "state" / "loss_exit_whipsaw_cache.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "analysis" / "loss-exit-whipsaw-analysis.md"
DEFAULT_START = "2026-04-13"  # BC23 deploy


# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LossExit:
    date: str
    ticker: str
    sector: str
    score: float
    entry_price: float
    exit_price: float
    qty: int
    actual_pnl: float
    actual_pnl_pct: float


@dataclass(frozen=True)
class WhipsawRow:
    loss_exit: LossExit
    moc_close: float | None
    counterfactual_pnl: float | None
    whipsaw_cost: float | None  # actual_pnl - counterfactual_pnl

    @property
    def regret(self) -> str:
        """Verbal label of the whipsaw outcome."""
        if self.whipsaw_cost is None:
            return "no_data"
        if self.whipsaw_cost < -10:
            return "stop_hurt"
        if self.whipsaw_cost > 10:
            return "stop_saved"
        return "neutral"


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_loss_exits(start: str, end: str, trades_dir: Path = TRADES_DIR) -> list[LossExit]:
    """Read LOSS_EXIT rows from trades_*.csv files in [start, end] inclusive."""
    out: list[LossExit] = []
    pattern = str(trades_dir / "trades_*.csv")
    for path in sorted(glob.glob(pattern)):
        trade_date = Path(path).stem.replace("trades_", "")
        if not (start <= trade_date <= end):
            continue
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                if row.get("exit_type") != "LOSS_EXIT":
                    continue
                try:
                    out.append(LossExit(
                        date=row["date"],
                        ticker=row["ticker"],
                        sector=row.get("sector", ""),
                        score=float(row.get("score", 0) or 0),
                        entry_price=float(row["entry_price"]),
                        exit_price=float(row["exit_price"]),
                        qty=int(row["exit_qty"]),
                        actual_pnl=float(row["pnl"]),
                        actual_pnl_pct=float(row["pnl_pct"]),
                    ))
                except (KeyError, ValueError):
                    continue
    return out


def aggregate_split_orders(events: list[LossExit]) -> list[LossExit]:
    """Sum split orders for the same ticker on the same day into one row.

    Some trades fire multiple LOSS_EXIT rows (split fills). The whipsaw
    audit is more readable when those collapse into a single per-ticker
    per-day position.
    """
    bucket: dict[tuple[str, str], list[LossExit]] = defaultdict(list)
    for ev in events:
        bucket[(ev.date, ev.ticker)].append(ev)

    merged: list[LossExit] = []
    for (d, t), rows in bucket.items():
        total_qty = sum(r.qty for r in rows)
        total_pnl = sum(r.actual_pnl for r in rows)
        # Weighted entry/exit by qty
        wavg_entry = sum(r.entry_price * r.qty for r in rows) / total_qty
        wavg_exit = sum(r.exit_price * r.qty for r in rows) / total_qty
        merged.append(LossExit(
            date=d,
            ticker=t,
            sector=rows[0].sector,
            score=rows[0].score,
            entry_price=round(wavg_entry, 4),
            exit_price=round(wavg_exit, 4),
            qty=total_qty,
            actual_pnl=round(total_pnl, 2),
            actual_pnl_pct=round(total_pnl / (wavg_entry * total_qty) * 100, 2),
        ))
    return sorted(merged, key=lambda e: (e.date, e.ticker))


# ---------------------------------------------------------------------------
# Polygon close fetch (with on-disk cache)
# ---------------------------------------------------------------------------


class CloseCache:
    """Tiny key/value cache for (ticker, date) → close_price."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._data: dict[str, float] = {}
        if path.exists():
            try:
                with open(path) as f:
                    self._data = json.load(f)
            except (OSError, json.JSONDecodeError):
                self._data = {}

    @staticmethod
    def _key(ticker: str, date_str: str) -> str:
        return f"{ticker}@{date_str}"

    def get(self, ticker: str, date_str: str) -> float | None:
        return self._data.get(self._key(ticker, date_str))

    def put(self, ticker: str, date_str: str, value: float) -> None:
        self._data[self._key(ticker, date_str)] = value

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2, sort_keys=True)


def fetch_moc_close(ticker: str, date_str: str, cache: CloseCache) -> float | None:
    """Polygon daily close ('c') for ticker on date_str. Cached by ticker/date."""
    cached = cache.get(ticker, date_str)
    if cached is not None:
        return cached

    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from ifds.data.polygon import PolygonClient
    except ImportError:
        logger.warning("Polygon client not importable; skipping live fetch")
        return None

    api_key = os.environ.get("IFDS_POLYGON_API_KEY")
    if not api_key:
        logger.warning("IFDS_POLYGON_API_KEY missing; skipping live fetch")
        return None

    try:
        client = PolygonClient(api_key)
        bars = client.get_aggregates(ticker, date_str, date_str, timespan="day")
    except Exception as e:
        logger.warning(f"Polygon fetch failed for {ticker} {date_str}: {e}")
        return None

    if not bars:
        return None

    close = bars[0].get("c")
    if close is None:
        return None
    value = float(close)
    cache.put(ticker, date_str, value)
    return value


# ---------------------------------------------------------------------------
# Whipsaw computation
# ---------------------------------------------------------------------------


def compute_whipsaw_cost(
    entry_price: float, qty: int, actual_pnl: float, moc_close: float
) -> float:
    """whipsaw_cost = actual_pnl - counterfactual_moc_pnl. Negative = stop hurt."""
    counterfactual_pnl = (moc_close - entry_price) * qty
    return actual_pnl - counterfactual_pnl


def build_whipsaw_rows(
    events: list[LossExit], cache: CloseCache
) -> list[WhipsawRow]:
    rows: list[WhipsawRow] = []
    for ev in events:
        moc = fetch_moc_close(ev.ticker, ev.date, cache)
        if moc is None:
            rows.append(WhipsawRow(ev, None, None, None))
            continue
        counterfactual = round((moc - ev.entry_price) * ev.qty, 2)
        whipsaw = round(ev.actual_pnl - counterfactual, 2)
        rows.append(WhipsawRow(ev, round(moc, 4), counterfactual, whipsaw))
    return rows


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def render_report(rows: list[WhipsawRow], start: str, end: str) -> str:
    """Build the markdown report body."""
    out: list[str] = []
    out.append(f"# LOSS_EXIT Whipsaw Cost Audit — BC23 ({start} → {end})\n")
    out.append("> Read-only retrospective. **No pipeline behavior is changed.**\n")

    valid = [r for r in rows if r.whipsaw_cost is not None]
    no_data = [r for r in rows if r.whipsaw_cost is None]

    total_actual = sum(r.loss_exit.actual_pnl for r in valid)
    total_counterfactual = sum((r.counterfactual_pnl or 0.0) for r in valid)
    total_whipsaw = sum((r.whipsaw_cost or 0.0) for r in valid)
    avg_whipsaw = mean([r.whipsaw_cost for r in valid]) if valid else 0.0
    med_whipsaw = median([r.whipsaw_cost for r in valid]) if valid else 0.0
    n_hurt = sum(1 for r in valid if (r.whipsaw_cost or 0.0) < -10)
    n_saved = sum(1 for r in valid if (r.whipsaw_cost or 0.0) > 10)
    n_neutral = len(valid) - n_hurt - n_saved

    if total_whipsaw < -50:
        verdict = (
            f"**LOSS_EXIT cost the account ${-total_whipsaw:,.0f} "
            f"vs holding to MOC.** The rule, in this sample, hurt more than helped."
        )
    elif total_whipsaw > 50:
        verdict = (
            f"**LOSS_EXIT saved ${total_whipsaw:,.0f} vs holding to MOC.** "
            f"The rule, in this sample, protected against larger losses."
        )
    else:
        verdict = (
            f"**Net whipsaw cost ${total_whipsaw:+,.0f} — statistically neutral** "
            f"in this sample."
        )

    out.append("## Summary\n")
    out.append(f"- LOSS_EXIT events (per ticker/day, split orders merged): **{len(rows)}**")
    out.append(f"- Events with MOC data: {len(valid)} / no data: {len(no_data)}")
    out.append(f"- Total actual P&L: **${total_actual:+,.2f}**")
    out.append(f"- Total counterfactual MOC P&L: ${total_counterfactual:+,.2f}")
    out.append(f"- **Net whipsaw cost: ${total_whipsaw:+,.2f}** "
               f"(negative = stop hurt, positive = stop saved)")
    out.append(f"- Mean whipsaw / event: ${avg_whipsaw:+,.2f}, "
               f"median ${med_whipsaw:+,.2f}")
    out.append(f"- Stop hurt: {n_hurt} | Stop saved: {n_saved} | Neutral: {n_neutral}")
    out.append("")
    out.append(f"### Verdict\n\n{verdict}\n")

    out.append("## Per-event detail\n")
    out.append("| Date | Ticker | Sector | Score | Entry | Stop fill | MOC close | Qty | "
               "Actual P&L | Counterfactual MOC P&L | Whipsaw | Verdict |")
    out.append("|------|--------|--------|-------|-------|-----------|-----------|-----|"
               "-----------|------------------------|---------|---------|")
    for r in rows:
        ev = r.loss_exit
        if r.moc_close is None:
            moc_str = "—"
            cf_str = "—"
            whipsaw_str = "—"
        else:
            moc_str = f"${r.moc_close:.2f}"
            cf_str = f"${r.counterfactual_pnl:+,.2f}"
            whipsaw_str = f"${r.whipsaw_cost:+,.2f}"
        out.append(
            f"| {ev.date} | {ev.ticker} | {ev.sector or '—'} | {ev.score:.1f} | "
            f"${ev.entry_price:.2f} | ${ev.exit_price:.2f} | {moc_str} | {ev.qty} | "
            f"${ev.actual_pnl:+,.2f} | {cf_str} | {whipsaw_str} | {r.regret} |"
        )
    out.append("")

    # Ticker rollup
    by_ticker: dict[str, list[WhipsawRow]] = defaultdict(list)
    for r in valid:
        by_ticker[r.loss_exit.ticker].append(r)
    if by_ticker:
        out.append("## By ticker\n")
        out.append("| Ticker | Events | Σ actual P&L | Σ whipsaw cost | Avg whipsaw |")
        out.append("|--------|--------|--------------|----------------|-------------|")
        for ticker, rs in sorted(by_ticker.items(),
                                  key=lambda kv: sum(x.whipsaw_cost or 0 for x in kv[1])):
            total_a = sum(r.loss_exit.actual_pnl for r in rs)
            total_w = sum(r.whipsaw_cost or 0 for r in rs)
            avg_w = total_w / len(rs)
            out.append(
                f"| {ticker} | {len(rs)} | ${total_a:+,.2f} | "
                f"${total_w:+,.2f} | ${avg_w:+,.2f} |"
            )
        out.append("")

    out.append("## Methodology\n")
    out.append("- **MOC proxy:** Polygon daily close (`c` from /v2/aggs/ticker/{T}/range/1/day/{D}/{D}).")
    out.append("  This is the official 16:00 ET close, which is a close (≤0.1%) approximation")
    out.append("  to a real `MarketOnClose` fill price.")
    out.append("- **Split orders merged:** when one logical position fired multiple LOSS_EXIT")
    out.append("  rows in the trades CSV (split fills), they are summed by qty/P&L.")
    out.append("- **Whipsaw verdict:** `actual_pnl - counterfactual_moc_pnl`.")
    out.append("  - `< -$10` → `stop_hurt` (whipsaw)")
    out.append("  - `> +$10` → `stop_saved` (continued decline avoided)")
    out.append("  - `[-10, +10]` → `neutral`")
    out.append("- **No simulation** of trail/SL/TP1 paths — the only counterfactual is")
    out.append("  *holding to MOC instead of stopping out at -2%*.")
    out.append("")

    out.append("## Caveats\n")
    out.append("- The Polygon daily close differs slightly from a real-time MOC fill.")
    out.append("- This audit only models the LOSS_EXIT rule, not interaction with TP1,")
    out.append("  trail-stop, or other exits. It does not predict net portfolio P&L if")
    out.append("  the rule were removed, only how it scored on past triggers.")
    out.append("- Sample size is small (BC23 deploy 2026-04-13). Treat the verdict as")
    out.append("  *directional*, not statistically conclusive.")
    out.append("")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="LOSS_EXIT whipsaw cost audit")
    parser.add_argument("--start", default=DEFAULT_START, help="YYYY-MM-DD")
    parser.add_argument("--end", default=date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Markdown output path")
    parser.add_argument("--cache", default=str(CACHE_FILE), help="Polygon close cache path")
    args = parser.parse_args()

    logger.info(f"Whipsaw audit — {args.start} → {args.end}")

    raw_events = load_loss_exits(args.start, args.end)
    events = aggregate_split_orders(raw_events)
    logger.info(
        f"LOSS_EXIT rows: {len(raw_events)} → merged unique events: {len(events)}"
    )

    cache = CloseCache(Path(args.cache))
    rows = build_whipsaw_rows(events, cache)
    cache.save()

    report = render_report(rows, args.start, args.end)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        f.write(report)

    logger.info(f"Report written: {out_path}")


if __name__ == "__main__":
    main()
