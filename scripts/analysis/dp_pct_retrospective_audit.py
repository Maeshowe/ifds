#!/usr/bin/env python3
"""Dark Pool % Retrospective Audit (read-only).

Live UW per-ticker dark-pool fetch on the *historical entry dates* of every
W17-W19 trade, with `date=YYYY-MM-DD` query parameter. Computes dp_pct from
the raw records and correlates against realized P&L. Bypasses the production
batch provider (which is known to under-cover individual tickers).

Strategic question this answers:

    Is the UW dark-pool % a useful predictor of paper-trading P&L when fed
    accurate (per-ticker) data?

If yes → keep UW (the $150/mo subscription has measurable signal).
If no  → UW kannibalizáció becomes a real option.

Inputs:
    scripts/paper_trading/logs/trades_YYYY-MM-DD.csv  (per-day trade rows)

Outputs:
    docs/analysis/dp-pct-retrospective-audit.md       (markdown report)
    state/dp_pct_audit_cache.json                     (UW response cache)

Usage:
    python scripts/analysis/dp_pct_retrospective_audit.py
    python scripts/analysis/dp_pct_retrospective_audit.py --start 2026-04-20 --end 2026-05-08
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import logging
import math
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
logger = logging.getLogger("dp_audit")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRADES_DIR = PROJECT_ROOT / "scripts" / "paper_trading" / "logs"
CACHE_FILE = PROJECT_ROOT / "state" / "dp_pct_audit_cache.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "analysis" / "dp-pct-retrospective-audit.md"
DEFAULT_START = "2026-04-20"  # W17 start


# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Trade:
    date: str
    ticker: str
    sector: str
    score: float
    qty: int
    actual_pnl: float


@dataclass(frozen=True)
class AuditRow:
    trade: Trade
    dp_pct: float | None       # dp_volume / total_volume * 100
    dp_records: int            # number of UW records on that date
    dp_volume: int             # aggregated dark-pool volume (shares)
    total_volume: int          # max stock day volume seen in records


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_trades(start: str, end: str, trades_dir: Path = TRADES_DIR) -> list[Trade]:
    """Load all trades in [start, end] inclusive, merging split orders by (date, ticker)."""
    bucket: dict[tuple[str, str], list[dict]] = defaultdict(list)
    pattern = str(trades_dir / "trades_*.csv")
    for path in sorted(glob.glob(pattern)):
        trade_date = Path(path).stem.replace("trades_", "")
        if not (start <= trade_date <= end):
            continue
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                try:
                    bucket[(row["date"], row["ticker"])].append(row)
                except KeyError:
                    continue

    out: list[Trade] = []
    for (d, t), rows in bucket.items():
        try:
            qty = sum(int(r["entry_qty"]) for r in rows)
            pnl = sum(float(r["pnl"]) for r in rows)
            score = float(rows[0].get("score", 0) or 0)
            sector = rows[0].get("sector", "")
        except (KeyError, ValueError):
            continue
        out.append(Trade(date=d, ticker=t, sector=sector, score=score,
                         qty=qty, actual_pnl=round(pnl, 2)))
    return sorted(out, key=lambda t: (t.date, t.ticker))


# ---------------------------------------------------------------------------
# UW per-ticker historical fetch (with on-disk cache)
# ---------------------------------------------------------------------------


class DPCache:
    """JSON cache for (ticker, date) → aggregated dict."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._data: dict[str, dict] = {}
        if path.exists():
            try:
                with open(path) as f:
                    self._data = json.load(f)
            except (OSError, json.JSONDecodeError):
                self._data = {}

    @staticmethod
    def _key(ticker: str, date_str: str) -> str:
        return f"{ticker}@{date_str}"

    def get(self, ticker: str, date_str: str) -> dict | None:
        return self._data.get(self._key(ticker, date_str))

    def put(self, ticker: str, date_str: str, value: dict) -> None:
        self._data[self._key(ticker, date_str)] = value

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2, sort_keys=True)


def fetch_dp_for_date(ticker: str, date_str: str, cache: DPCache,
                      uw_client) -> dict | None:
    """UW per-ticker DP fetch for a specific historical date. Returns aggregated dict.

    The aggregated dict mirrors what ``_aggregate_dp_records`` produces:
    ``{"dp_volume": int, "total_volume": int, "dp_pct": float, "n_records": int}``.
    """
    cached = cache.get(ticker, date_str)
    if cached is not None:
        return cached

    endpoint = f"/api/darkpool/{ticker}"
    raw = uw_client._get(endpoint, params={"limit": 500, "date": date_str},
                         headers=uw_client._auth_headers())
    if raw is None:
        return None
    if isinstance(raw, dict) and raw.get("data"):
        records = raw["data"]
    elif isinstance(raw, list):
        records = raw
    else:
        records = []

    dp_volume = 0
    total_volume = 0
    for r in records:
        try:
            dp_volume += int(r.get("size", 0) or 0)
        except (ValueError, TypeError):
            pass
        try:
            v = int(r.get("volume", 0) or 0)
        except (ValueError, TypeError):
            v = 0
        if v > total_volume:
            total_volume = v

    dp_pct = round((dp_volume / total_volume) * 100, 4) if total_volume > 0 else 0.0
    agg = {
        "dp_volume": dp_volume,
        "total_volume": total_volume,
        "dp_pct": dp_pct,
        "n_records": len(records),
    }
    cache.put(ticker, date_str, agg)
    return agg


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def pearson(x: list[float], y: list[float]) -> tuple[float, float] | None:
    """Pearson r and two-tailed p-value (from scipy if available)."""
    if len(x) < 3 or len(x) != len(y):
        return None
    try:
        from scipy.stats import pearsonr
        r, p = pearsonr(x, y)
        return float(r), float(p)
    except ImportError:
        return None


def spearman(x: list[float], y: list[float]) -> tuple[float, float] | None:
    if len(x) < 3 or len(x) != len(y):
        return None
    try:
        from scipy.stats import spearmanr
        rho, p = spearmanr(x, y)
        return float(rho), float(p)
    except ImportError:
        return None


def quintile_table(rows: list[AuditRow]) -> list[dict]:
    """Sort rows by dp_pct, split into 5 quintiles, return per-bucket stats."""
    valid = [r for r in rows if r.dp_pct is not None]
    if len(valid) < 5:
        return []
    valid_sorted = sorted(valid, key=lambda r: r.dp_pct or 0.0)
    n = len(valid_sorted)
    bucket_size = n // 5
    out = []
    for q in range(5):
        lo = q * bucket_size
        hi = (q + 1) * bucket_size if q < 4 else n
        chunk = valid_sorted[lo:hi]
        if not chunk:
            continue
        pcts = [r.dp_pct or 0.0 for r in chunk]
        pnls = [r.trade.actual_pnl for r in chunk]
        wins = sum(1 for p in pnls if p > 0)
        out.append({
            "quintile": q + 1,
            "range": f"{min(pcts):.2f}–{max(pcts):.2f}",
            "n": len(chunk),
            "avg_pnl": round(mean(pnls), 2),
            "median_pnl": round(median(pnls), 2),
            "win_rate": round(wins / len(chunk), 2),
        })
    return out


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def render_report(rows: list[AuditRow], start: str, end: str,
                  no_data: list[Trade]) -> str:
    out: list[str] = []
    out.append(f"# Dark Pool % Retrospective Audit — Live UW Per-Ticker ({start} → {end})\n")
    out.append("> Read-only. Bypasses production batch provider — fetches "
               "`/api/darkpool/{ticker}?date=YYYY-MM-DD` per trade.\n")

    valid = [r for r in rows if r.dp_pct is not None]
    if not valid:
        out.append("**No valid audit rows.**")
        return "\n".join(out)

    pcts = [r.dp_pct or 0.0 for r in valid]
    pnls = [r.trade.actual_pnl for r in valid]
    qtys = [r.trade.qty for r in valid]
    pnl_per_share = [p / q if q > 0 else 0.0 for p, q in zip(pnls, qtys)]

    out.append("## Summary\n")
    out.append(f"- Trades audited: **{len(rows)}** (merged by date+ticker)")
    out.append(f"- With UW data: {len(valid)} | no data: {len(no_data) + (len(rows) - len(valid))}")
    out.append(f"- dp_pct range: {min(pcts):.2f}% – {max(pcts):.2f}%, "
               f"mean {mean(pcts):.2f}%, median {median(pcts):.2f}%")
    out.append(f"- Realized P&L range: ${min(pnls):+,.2f} – ${max(pnls):+,.2f}, "
               f"mean ${mean(pnls):+,.2f}")
    out.append("")

    pr = pearson(pcts, pnls)
    sp = spearman(pcts, pnls)
    pr_pps = pearson(pcts, pnl_per_share)
    sp_pps = spearman(pcts, pnl_per_share)

    out.append("## Correlation\n")
    out.append("| Pair | Pearson r (p) | Spearman ρ (p) |")
    out.append("|------|---------------|----------------|")
    out.append(
        f"| dp_pct ↔ P&L (\\$) | "
        f"{pr[0]:+.3f} (p={pr[1]:.3f}) | "
        f"{sp[0]:+.3f} (p={sp[1]:.3f}) |"
        if pr and sp else "| dp_pct ↔ P&L | — (scipy missing) | — |"
    )
    out.append(
        f"| dp_pct ↔ P&L per share | "
        f"{pr_pps[0]:+.3f} (p={pr_pps[1]:.3f}) | "
        f"{sp_pps[0]:+.3f} (p={sp_pps[1]:.3f}) |"
        if pr_pps and sp_pps else "| dp_pct ↔ P&L/share | — | — |"
    )
    out.append("")

    if pr:
        n = len(valid)
        crit = 0.22 if n <= 80 else (0.20 if n <= 100 else 0.15)
        if abs(pr[0]) > crit and pr[1] < 0.05:
            verdict = (
                f"**Statistically significant correlation** (|r|={abs(pr[0]):.3f} > "
                f"{crit:.2f}, p={pr[1]:.3f}) — UW dark-pool % carries signal at this sample size."
            )
        elif abs(pr[0]) < 0.10 and pr[1] > 0.20:
            verdict = (
                f"**Effectively zero correlation** (|r|={abs(pr[0]):.3f}, "
                f"p={pr[1]:.3f}). UW dark-pool % does not predict P&L on this sample."
            )
        else:
            verdict = (
                f"**Inconclusive** (|r|={abs(pr[0]):.3f}, p={pr[1]:.3f}) — "
                f"directional but below significance at n={n}. Larger sample needed."
            )
        out.append("### Verdict\n")
        out.append(verdict)
        out.append("")

    # Quintile table
    qt = quintile_table(rows)
    if qt:
        out.append("## Quintile breakdown\n")
        out.append("| Quintile | Range | N | Avg P&L | Median P&L | Win rate |")
        out.append("|----------|-------|---|---------|------------|----------|")
        for row in qt:
            out.append(
                f"| Q{row['quintile']} | {row['range']}% | {row['n']} | "
                f"${row['avg_pnl']:+,.2f} | ${row['median_pnl']:+,.2f} | "
                f"{row['win_rate']*100:.0f}% |"
            )
        spread = qt[-1]["avg_pnl"] - qt[0]["avg_pnl"]
        out.append("")
        out.append(f"**Q5 − Q1 spread**: ${spread:+,.2f}")
        out.append("")

    out.append("## Per-trade detail\n")
    out.append("| Date | Ticker | Sector | Score | Qty | dp_pct | n_rec | dp_vol | total_vol | P&L |")
    out.append("|------|--------|--------|-------|-----|--------|-------|--------|-----------|-----|")
    for r in sorted(rows, key=lambda x: (x.trade.date, x.trade.ticker)):
        t = r.trade
        if r.dp_pct is None:
            dp_s = "—"
            n_rec = "—"
            dpv = "—"
            tv = "—"
        else:
            dp_s = f"{r.dp_pct:.2f}%"
            n_rec = str(r.dp_records)
            dpv = f"{r.dp_volume:,}"
            tv = f"{r.total_volume:,}"
        out.append(
            f"| {t.date} | {t.ticker} | {t.sector or '—'} | {t.score:.1f} | {t.qty} | "
            f"{dp_s} | {n_rec} | {dpv} | {tv} | ${t.actual_pnl:+,.2f} |"
        )
    out.append("")

    out.append("## Methodology\n")
    out.append("- Trades merged by `(date, ticker)`; split orders summed by qty/P&L.")
    out.append("- UW endpoint `/api/darkpool/{ticker}?limit=500&date=YYYY-MM-DD` —")
    out.append("  filtered server-side to the entry day, **not** the most-recent batch.")
    out.append("- `dp_pct = max(record.size_sum) / max(record.volume) * 100`. "
               "The `volume` field on each DP record is the stock's full-day volume.")
    out.append("- Significance threshold: |r|>0.22 at n≈80, p<0.05.")
    out.append("")

    out.append("## Caveats\n")
    out.append("- Sample is whatever IBKR paper-trading actually executed in the window — "
               "biased toward IFDS-qualified tickers (score ≥85), not the full market.")
    out.append("- `dp_pct` here uses raw aggregate from the per-ticker endpoint. "
               "Production uses a different (broken) batch path; this audit measures the "
               "*ceiling* of dp_pct's predictive power if the production pipeline were fixed.")
    out.append("- Polygon close ≠ MOC fill — irrelevant for this audit (no counterfactual).")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Dark Pool % retrospective audit")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=date.today().isoformat())
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--cache", default=str(CACHE_FILE))
    args = parser.parse_args()

    api_key = os.environ.get("IFDS_UW_API_KEY")
    if not api_key:
        print("ERROR: IFDS_UW_API_KEY missing", file=sys.stderr)
        return 1

    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from ifds.data.unusual_whales import UnusualWhalesClient

    trades = load_trades(args.start, args.end)
    logger.info(f"Loaded {len(trades)} unique trades in [{args.start}, {args.end}]")
    if not trades:
        print("ERROR: no trades found", file=sys.stderr)
        return 1

    cache = DPCache(Path(args.cache))
    client = UnusualWhalesClient(api_key=api_key)

    rows: list[AuditRow] = []
    no_data: list[Trade] = []
    for i, t in enumerate(trades, 1):
        agg = fetch_dp_for_date(t.ticker, t.date, cache, client)
        if agg is None or agg.get("total_volume", 0) <= 0:
            rows.append(AuditRow(trade=t, dp_pct=None,
                                  dp_records=0, dp_volume=0, total_volume=0))
            no_data.append(t)
            logger.info(f"  {i:>3}/{len(trades)} {t.ticker:<6} {t.date} → no data")
            continue
        rows.append(AuditRow(
            trade=t,
            dp_pct=agg["dp_pct"],
            dp_records=agg["n_records"],
            dp_volume=agg["dp_volume"],
            total_volume=agg["total_volume"],
        ))
        logger.info(f"  {i:>3}/{len(trades)} {t.ticker:<6} {t.date} → "
                    f"dp_pct={agg['dp_pct']:.2f}% n={agg['n_records']}")

    cache.save()

    report = render_report(rows, args.start, args.end, no_data)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        f.write(report)

    logger.info(f"Report written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
