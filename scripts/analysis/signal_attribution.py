#!/usr/bin/env python3
"""Signal-isolating attribution test (spec 2026-06-10).

Separates the SIGNAL's predictive power from the exit architecture and from
market/sector drift, on the closed swing trades. Read-only analysis — touches
no trading state. Freeze-compatible (measurement, not trading behaviour).

Three isolation levels per trade (entry score S_j vs a return measure):
  L0  rho(S_j, realized_R)         — "did we make money" (exit+market+sector+signal)
  L1  rho(S_j, R_fixed(h))         — exit-isolated: forward return over horizon h
  L2  rho(S_j, R_fixed_resid(h))   — selection-isolated: sector-relative forward return

Primary decision metric (per the edge-audit §4.2/3a): **L2 Spearman, h=5,
sector-relative**. Stratification by exit type is DESCRIPTIVE only. Day 63 reads
are DIRECTION only (power < small effect); Day 126 is the first real read.

    python scripts/analysis/signal_attribution.py --as-of 2026-08-15
    python scripts/analysis/signal_attribution.py --smoke   # n=14 plumbing check
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import numpy as np

HORIZONS = (1, 3, 5)
PRIMARY_HORIZON = 5


# ---------------------------------------------------------------------------
# Trade record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Trade:
    ticker: str
    entry_date: str
    entry_price: float
    entry_score: float  # S_j — the Phase 4 combined_score at entry
    sector: str
    exit_type: str
    realized_r: float  # realized return fraction (broker per-trade pnl / (entry*qty))


# ---------------------------------------------------------------------------
# Pure return measures
# ---------------------------------------------------------------------------


def forward_return(entry_price: float, fwd_close: float) -> float:
    """L1: exit-independent forward return from the entry fill to the +h close."""
    if entry_price <= 0:
        raise ValueError("entry_price must be positive")
    return fwd_close / entry_price - 1.0


def sector_residual(stock_ret: float, sector_ret: float) -> float:
    """L2 (primary): stock return minus its sector-ETF return over the same window."""
    return stock_ret - sector_ret


def beta_adjusted(stock_ret: float, spy_ret: float, beta: float) -> float:
    """L2 (secondary): stock return minus beta * SPY return."""
    return stock_ret - beta * spy_ret


# ---------------------------------------------------------------------------
# Pure statistics (numpy only — scipy not available in this env)
# ---------------------------------------------------------------------------


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def _rank(a: np.ndarray) -> np.ndarray:
    """Average ranks (ties get the mean of their rank positions)."""
    a = np.asarray(a, dtype=float)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=float)
    ranks[order] = np.arange(1, len(a) + 1, dtype=float)
    # average ties
    _, inv, counts = np.unique(a, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts))
    np.add.at(sums, inv, ranks)
    return (sums / counts)[inv]


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman rank correlation = Pearson on average ranks."""
    if len(x) < 2:
        return float("nan")
    return pearson(_rank(np.asarray(x)), _rank(np.asarray(y)))


def fisher_z_ci(r: float, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Fisher-z 95% CI for a correlation. Returns (nan, nan) when undefined."""
    if n < 4 or not math.isfinite(r) or abs(r) >= 1.0:
        return (float("nan"), float("nan"))
    z = math.atanh(r)
    se = 1.0 / math.sqrt(n - 3)
    # two-sided normal quantile (alpha=0.05 -> 1.959964)
    zc = 1.959963984540054 if abs(alpha - 0.05) < 1e-9 else _norm_ppf(1 - alpha / 2)
    lo, hi = z - zc * se, z + zc * se
    return (math.tanh(lo), math.tanh(hi))


def _norm_ppf(p: float) -> float:
    """Acklam's rational approximation of the normal quantile (no scipy)."""
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00, 3.754408661907416e00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if p <= phigh:
        q = p - 0.5
        r = q * q
        return (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
            * q
            / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
        )
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
        (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
    )


def correlate_with_ci(x: np.ndarray, y: np.ndarray, method: str = "spearman") -> dict:
    n = len(x)
    r = spearman(x, y) if method == "spearman" else pearson(x, y)
    lo, hi = fisher_z_ci(r, n)
    excludes_zero = math.isfinite(lo) and math.isfinite(hi) and (lo > 0 or hi < 0)
    return {
        "method": method,
        "n": n,
        "r": r,
        "ci_low": lo,
        "ci_high": hi,
        "excludes_zero": excludes_zero,
    }


def quintile_table(scores: np.ndarray, returns: np.ndarray, q: int = 5) -> list[dict]:
    """Bin trades by score quantile; mean + SE of the return per bin (monotonicity)."""
    scores = np.asarray(scores, dtype=float)
    returns = np.asarray(returns, dtype=float)
    if len(scores) < q:
        q = max(1, len(scores))
    order = np.argsort(scores, kind="mergesort")
    bins = np.array_split(order, q)
    out = []
    for i, idx in enumerate(bins):
        rr = returns[idx]
        n = len(rr)
        mean = float(np.mean(rr)) if n else float("nan")
        se = float(np.std(rr, ddof=1) / math.sqrt(n)) if n > 1 else float("nan")
        out.append(
            {
                "bin": i + 1,
                "n": n,
                "mean_return": mean,
                "se": se,
                "score_lo": float(np.min(scores[idx])) if n else float("nan"),
                "score_hi": float(np.max(scores[idx])) if n else float("nan"),
            }
        )
    return out


# ---------------------------------------------------------------------------
# S_j recovery from the Phase 4 snapshot (read-only)
# ---------------------------------------------------------------------------


def recover_entry_score(snapshot_rows: list[dict], ticker: str) -> float | None:
    """Find a ticker's combined_score in a Phase 4 snapshot (list of dicts)."""
    for row in snapshot_rows or []:
        if row.get("ticker") == ticker and row.get("combined_score") is not None:
            return float(row["combined_score"])
    return None


# ---------------------------------------------------------------------------
# Data loader — ledger + Phase 4 snapshots → Trade objects (spec §6.1)
#
# Three pinned invariants (Chat, 2026-06-18), enforced here:
#   1. entry_score (S_j) missing (None or <= 0) → snapshot-recovery for that
#      ticker/entry_date. Still missing → trade EXCLUDED (reported). The 6
#      inherited positions' default-0.0 sentinel is NOT a real score; it must
#      not leak into ρ.
#   2. exit_type source is EXCLUSIVELY state/pending_exits/{date}.json (the
#      broker-authoritative ledger). daily_metrics::exit_type is fill-timestamp
#      based and unreliable until the P1 fix — never read it for exit_type.
#   3. read-only + report both samples: full Day 1–63 (official gate) and the
#      Day 9+ clean cut. The clean cut is ENTRY-based (cleans the S_j predictor,
#      not only the P&L output); an exit-based cut is reported as a diagnostic.
#
# Read-only: this loader writes nothing to the trading state.
# ---------------------------------------------------------------------------


CLEAN_SAMPLE_MIN_DAY = 9  # Day 9+ clean sample boundary (spec §4.2/2, §8/3)


@dataclass(frozen=True)
class LoadedTrade:
    """A closed (position-level) trade plus the bookkeeping for sample splits."""

    trade: Trade
    entry_day_number: int  # daily_metrics[entry_date].day_number — PRIMARY clean cut
    exit_date: str  # final leg's pending_exits / daily_metrics file date
    exit_day_number: int  # daily_metrics[exit_date].day_number — secondary diagnostic


@dataclass(frozen=True)
class Exclusion:
    """A closed trade dropped from the sample, with the reason (spec §6.1/1)."""

    ticker: str
    entry_date: str
    exit_date: str
    reason: str


def _read_json(path: Path) -> object | None:
    if not path.exists():
        return None
    with path.open() as fh:
        return json.load(fh)


def _read_gzip_json(path: Path) -> object | None:
    if not path.exists():
        return None
    with gzip.open(path, "rt") as fh:
        return json.load(fh)


def load_phase4_snapshot(snapshots_dir: Path, date_str: str) -> list[dict] | None:
    """Load a Phase 4 snapshot (gzipped JSON list) for S_j recovery."""
    data = _read_gzip_json(snapshots_dir / f"{date_str}.json.gz")
    return data if isinstance(data, list) else None


def resolve_entry_score(record: dict, snapshots_dir: Path) -> float | None:
    """Invariant #1: take a real entry_score, else recover from the snapshot.

    Returns None when neither the ledger nor the snapshot yields a positive
    score — the caller then EXCLUDES the trade (sentinels must not leak).
    """
    raw = record.get("entry_score")
    if raw is not None and float(raw) > 0:
        return float(raw)
    snap = load_phase4_snapshot(snapshots_dir, record.get("entry_date", ""))
    recovered = recover_entry_score(snap or [], record.get("ticker", ""))
    if recovered is not None and recovered > 0:
        return recovered
    return None


def load_realized(daily_metrics_dir: Path, exit_date: str) -> tuple[dict[str, dict], int | None]:
    """Return ({ticker: trade-detail}, day_number) from daily_metrics/{date}.json.

    Only the realized P&L (``pnl``) is taken from here — NEVER exit_type
    (invariant #2). Last detail wins on a same-day duplicate ticker.
    """
    data = _read_json(daily_metrics_dir / f"{exit_date}.json")
    if not isinstance(data, dict):
        return {}, None
    details = (data.get("trades") or {}).get("details") or []
    by_ticker = {d["ticker"]: d for d in details if d.get("ticker")}
    day_number = data.get("day_number")
    return by_ticker, (int(day_number) if day_number is not None else None)


def load_closed_trades(
    pending_exits_dir: Path,
    daily_metrics_dir: Path,
    snapshots_dir: Path,
) -> tuple[list[LoadedTrade], list[Exclusion]]:
    """Build the POSITION-LEVEL closed-trade sample from the ledger.

    A single position can close in several legs (TP1, then TP2/TIME_STOP) — the
    ledger records one ``pending_exits`` entry per leg, all sharing the same
    (ticker, entry_date). Per pre-reg condition (b), legs are aggregated into ONE
    trade: ``realized_r = Σ(leg net pnl) / (entry_price × Σ(leg qty))``. The pnl
    is broker-authoritative and NET of commission (Option B, P0 §0.11). A position
    is excluded if its entry_score is unrecoverable (inv #1) or ANY leg's realized
    P&L is unavailable (no partial-position returns leak in). Returns
    (loaded, exclusions).
    """
    # Group ledger legs by (ticker, entry_date), preserving discovery order.
    groups: dict[tuple[str, str], list[dict]] = {}
    order: list[tuple[str, str]] = []
    for path in sorted(pending_exits_dir.glob("*.json")):
        records = _read_json(path)
        if not isinstance(records, list):
            continue
        for rec in records:
            key = (rec.get("ticker", ""), rec.get("entry_date", ""))
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append({**rec, "_exit_date": path.stem})

    dm_cache: dict[str, tuple[dict[str, dict], int | None]] = {}

    def _dm(date_str: str) -> tuple[dict[str, dict], int | None]:
        if date_str not in dm_cache:
            dm_cache[date_str] = load_realized(daily_metrics_dir, date_str)
        return dm_cache[date_str]

    loaded: list[LoadedTrade] = []
    exclusions: list[Exclusion] = []

    for ticker, entry_date in order:
        legs = groups[(ticker, entry_date)]
        final_exit = max(leg["_exit_date"] for leg in legs)

        # Invariant #1: a real entry_score on any leg, else snapshot recovery.
        score = next(
            (s for s in (resolve_entry_score(leg, snapshots_dir) for leg in legs) if s),
            None,
        )
        if score is None:
            exclusions.append(
                Exclusion(ticker, entry_date, final_exit, "entry_score unrecoverable")
            )
            continue

        # Condition (b): aggregate realized P&L across ALL legs (position level).
        total_qty = 0.0
        total_pnl = 0.0
        missing_leg = False
        for leg in legs:
            by_ticker, _ = _dm(leg["_exit_date"])
            detail = by_ticker.get(ticker)
            if detail is None or detail.get("pnl") is None:
                missing_leg = True
                break
            total_qty += float(leg.get("qty") or 0.0)
            total_pnl += float(detail["pnl"])
        if missing_leg:
            exclusions.append(
                Exclusion(ticker, entry_date, final_exit, "realized pnl unavailable (≥1 leg)")
            )
            continue

        entry_price = float(legs[0].get("entry_price") or 0.0)
        notional = entry_price * total_qty
        if notional <= 0:
            exclusions.append(
                Exclusion(ticker, entry_date, final_exit, "invalid entry notional")
            )
            continue

        # exit_type labels the position by its FINAL leg (stratification is
        # DESCRIPTIVE only, spec §8/2). Drives no decision.
        final_leg = max(legs, key=lambda leg: leg["_exit_date"])
        _, entry_day = _dm(entry_date)
        _, exit_day = _dm(final_exit)

        trade = Trade(
            ticker=ticker,
            entry_date=entry_date,
            entry_price=entry_price,
            entry_score=score,
            sector=legs[0].get("sector", ""),
            exit_type=final_leg.get("exit_type", ""),  # invariant #2: ledger only
            realized_r=total_pnl / notional,
        )
        loaded.append(
            LoadedTrade(
                trade=trade,
                entry_day_number=entry_day if entry_day is not None else 0,
                exit_date=final_exit,
                exit_day_number=exit_day if exit_day is not None else 0,
            )
        )

    return loaded, exclusions


def split_samples(
    loaded: list[LoadedTrade], clean_min_day: int = CLEAN_SAMPLE_MIN_DAY
) -> dict[str, list[Trade]]:
    """Invariant #3: report both the full and the clean samples.

    - ``full``       — Day 1–63, the official pre-registered gate (bug-distorted).
    - ``clean``      — PRIMARY clean cut: ENTRY day-number ≥ 9. The early
      distortion is two-sided (it corrupts the daily P&L tracking AND the entry
      selection / S_j via stale Phase 1–3 context). Filtering on the entry day
      cleans the predictor too, and is a strict subset of an exit-based cut.
    - ``clean_exit`` — secondary diagnostic: EXIT day-number ≥ 9 (output-only).
    """
    full = [lt.trade for lt in loaded]
    clean = [lt.trade for lt in loaded if lt.entry_day_number >= clean_min_day]
    clean_exit = [lt.trade for lt in loaded if lt.exit_day_number >= clean_min_day]
    return {"full": full, "clean": clean, "clean_exit": clean_exit}


# ---------------------------------------------------------------------------
# Forward returns — Polygon daily bars (ticker, sector-ETF, SPY)
#
# Runs live only at Day 63; injected ``bar_fetcher`` keeps it unit-testable.
# A SimpleBar is {"date": "YYYY-MM-DD", "close": float}, sorted ascending.
# ---------------------------------------------------------------------------


# Reuses the production map so sector names stay in sync (spec §6 input).
SECTOR_TO_ETF = {
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Energy": "XLE",
    "Healthcare": "XLV",
    "Industrials": "XLI",
    "Consumer Defensive": "XLP",
    "Consumer Cyclical": "XLY",
    "Basic Materials": "XLB",
    "Communication Services": "XLC",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
}

SPY = "SPY"

# A fetcher maps (ticker, from_date, to_date) → ascending SimpleBars (or None).
BarFetcher = Callable[[str, str, str], "list[dict] | None"]


def _horizon_return(bars: list[dict], entry_date: str, h: int) -> float | None:
    """Return close[entry+h]/close[entry] − 1 using trading-day offsets.

    ``entry`` is the first bar on/after ``entry_date``. Returns None when the
    bars don't reach +h trading days (e.g. a very recent entry near Day 63).
    """
    if not bars:
        return None
    entry_idx = next((i for i, b in enumerate(bars) if b["date"] >= entry_date), None)
    if entry_idx is None or entry_idx + h >= len(bars):
        return None
    c0 = bars[entry_idx]["close"]
    ch = bars[entry_idx + h]["close"]
    if c0 <= 0:
        return None
    return ch / c0 - 1.0


def fetch_forward_returns(
    trades: list[Trade], bar_fetcher: BarFetcher, horizons: tuple[int, ...] = HORIZONS
) -> dict:
    """Build the ``{(ticker, entry_date, h): {stock, sector, spy, beta}}`` map.

    For each trade fetches the ticker, its sector-ETF and SPY daily bars from
    the entry date forward, then computes per-horizon returns. A horizon with
    no usable stock return is omitted (run_attribution skips it). beta=1.0
    (L2_beta is diagnostic only; per-stock beta is out of scope for Day 63).
    """
    max_h = max(horizons)
    # +10 calendar days of buffer comfortably covers max_h trading days.
    out: dict = {}
    bar_cache: dict[tuple[str, str], list[dict] | None] = {}

    def _bars(symbol: str, from_date: str) -> list[dict] | None:
        key = (symbol, from_date)
        if key not in bar_cache:
            to_date = _add_calendar_days(from_date, max_h * 2 + 10)
            bar_cache[key] = bar_fetcher(symbol, from_date, to_date)
        return bar_cache[key]

    for t in trades:
        etf = SECTOR_TO_ETF.get(t.sector)
        stock_bars = _bars(t.ticker, t.entry_date)
        sector_bars = _bars(etf, t.entry_date) if etf else None
        spy_bars = _bars(SPY, t.entry_date)
        for h in horizons:
            stock_ret = _horizon_return(stock_bars or [], t.entry_date, h)
            if stock_ret is None:
                continue
            sector_ret = _horizon_return(sector_bars or [], t.entry_date, h)
            spy_ret = _horizon_return(spy_bars or [], t.entry_date, h)
            out[(t.ticker, t.entry_date, h)] = {
                "stock": stock_ret,
                "sector": sector_ret if sector_ret is not None else 0.0,
                "spy": spy_ret if spy_ret is not None else 0.0,
                "beta": 1.0,
            }
    return out


def _add_calendar_days(date_str: str, days: int) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return (d + timedelta(days=days)).isoformat()


def polygon_bar_fetcher(client) -> BarFetcher:  # pragma: no cover — live Polygon at Day 63
    """Adapt a PolygonClient to the BarFetcher interface (SimpleBars)."""

    def _fetch(symbol: str, from_date: str, to_date: str) -> list[dict] | None:
        results = client.get_aggregates(symbol, from_date, to_date)
        if not results:
            return None
        bars = []
        for r in results:
            ts = r.get("t")
            close = r.get("c")
            if ts is None or close is None:
                continue
            d = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date().isoformat()
            bars.append({"date": d, "close": float(close)})
        bars.sort(key=lambda b: b["date"])
        return bars or None

    return _fetch


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_attribution(trades: list[Trade], fwd_returns: dict) -> dict:
    """Compute L0/L1/L2 correlations + quintile + exit-type stratification.

    ``fwd_returns``: {(ticker, entry_date, h): {"stock": r, "sector": r, "spy": r,
    "beta": b}} — the forward returns the caller fetched (injected for testability).
    Trades missing a horizon's forward return are skipped for that horizon.
    """
    scores = np.array([t.entry_score for t in trades], dtype=float)
    realized = np.array([t.realized_r for t in trades], dtype=float)

    report: dict = {"n_total": len(trades), "horizons": {}, "primary": None}

    # L0 — realized (exit+market+sector+signal), Pearson + Spearman
    report["L0"] = {
        "pearson": correlate_with_ci(scores, realized, "pearson"),
        "spearman": correlate_with_ci(scores, realized, "spearman"),
    }
    # L0 stratified by exit type (DESCRIPTIVE only)
    strat = {}
    for et in sorted({t.exit_type for t in trades}):
        idx = [i for i, t in enumerate(trades) if t.exit_type == et]
        if len(idx) >= 4:
            strat[et] = correlate_with_ci(scores[idx], realized[idx], "spearman")
        else:
            strat[et] = {"n": len(idx), "note": "n<4, not computed"}
    report["L0_by_exit_type"] = strat

    for h in HORIZONS:
        rows = [(t, fwd_returns.get((t.ticker, t.entry_date, h))) for t in trades]
        rows = [(t, fr) for t, fr in rows if fr is not None]
        if len(rows) < 4:
            report["horizons"][h] = {"n": len(rows), "note": "n<4, skipped"}
            continue
        s = np.array([t.entry_score for t, _ in rows], dtype=float)
        l1 = np.array(
            [forward_return(t.entry_price, t.entry_price * (1 + fr["stock"])) for t, fr in rows],
            dtype=float,
        )
        l2_sec = np.array([sector_residual(fr["stock"], fr["sector"]) for _, fr in rows])
        l2_beta = np.array(
            [beta_adjusted(fr["stock"], fr["spy"], fr.get("beta", 1.0)) for _, fr in rows]
        )
        report["horizons"][h] = {
            "n": len(rows),
            "L1": {
                "pearson": correlate_with_ci(s, l1, "pearson"),
                "spearman": correlate_with_ci(s, l1, "spearman"),
            },
            "L2_sector": {
                "pearson": correlate_with_ci(s, l2_sec, "pearson"),
                "spearman": correlate_with_ci(s, l2_sec, "spearman"),
            },
            "L2_beta": {"spearman": correlate_with_ci(s, l2_beta, "spearman")},
            "quintile_L2_sector": quintile_table(s, l2_sec),
        }

    # Primary decision metric: L2 sector-relative Spearman at h=5
    ph = report["horizons"].get(PRIMARY_HORIZON, {})
    if "L2_sector" in ph:
        report["primary"] = {
            "horizon": PRIMARY_HORIZON,
            "metric": "L2_sector_spearman",
            **ph["L2_sector"]["spearman"],
        }
    return report


def render_report(
    report: dict, as_of: str, smoke: bool, exclusions: list[Exclusion] | None = None
) -> str:
    L: list[str] = []
    L.append(f"# Signal-isolating attribution — {as_of}")
    L.append("")
    if smoke or report["n_total"] < 40:
        L.append(
            "> ⚠️ **PLUMBING VALIDATION ONLY — NOT EVIDENCE.** "
            f"n={report['n_total']} is far below the Day 63 power threshold "
            "(|ρ|≈0.36–0.38 detectable). This run validates the pipeline, not the signal."
        )
        L.append("")
    L.append(
        "_Realized return basis: `realized_r = Σ(leg net pnl) / (entry_price × Σ(leg qty))` "
        "— position-level aggregate (TP1/TP2 legs blended), broker-authoritative and "
        "NET of commission (Option B, P0 §0.11). Spearman primary metric → log-vs-simple "
        "and the commission basis do not move the rank correlation._"
    )
    L.append("")
    p = report.get("primary")
    if p:
        excl = "EXCLUDES 0" if p["excludes_zero"] else "contains 0"
        L.append(
            f"**Primary metric (L2 sector-relative Spearman, h=5)**: "
            f"ρ={p['r']:+.3f}, 95% CI [{p['ci_low']:+.3f}, {p['ci_high']:+.3f}] "
            f"({excl}), n={p['n']}"
        )
        L.append("")
    L.append("## L0 — realized (exit+market+sector+signal)")
    for m in ("pearson", "spearman"):
        c = report["L0"][m]
        L.append(f"- {m}: ρ={c['r']:+.3f} CI [{c['ci_low']:+.3f},{c['ci_high']:+.3f}] n={c['n']}")
    L.append("")
    L.append("## L1/L2 by horizon")
    for h, hd in report["horizons"].items():
        if "note" in hd:
            L.append(f"### h={h}: {hd['note']} (n={hd['n']})")
            continue
        l1 = hd["L1"]["spearman"]
        l2 = hd["L2_sector"]["spearman"]
        L.append(f"### h={h} (n={hd['n']})")
        L.append(
            f"- L1 (exit-isolated) Spearman: ρ={l1['r']:+.3f} "
            f"CI [{l1['ci_low']:+.3f},{l1['ci_high']:+.3f}]"
        )
        L.append(
            f"- **L2 (sector-relative) Spearman**: ρ={l2['r']:+.3f} "
            f"CI [{l2['ci_low']:+.3f},{l2['ci_high']:+.3f}]"
        )
    L.append("")
    if exclusions:
        L.append(f"## Exclusions ({len(exclusions)}) — §6.1/1")
        for e in exclusions:
            L.append(f"- {e.ticker} (entry {e.entry_date}, exit {e.exit_date}): {e.reason}")
        L.append("")
    L.append(
        "_Spec: docs/foundational/strategic-review/2026-06-10-signal-isolating-attribution-spec.md_"
    )
    return "\n".join(L)


_STATE = Path("state")
_OUT_DIR = Path("docs/analysis")


def main() -> None:  # pragma: no cover — I/O orchestration, runs at Day 63
    import os

    parser = argparse.ArgumentParser(description="Signal-isolating attribution test")
    parser.add_argument("--as-of", default="today", help="evaluation date label")
    parser.add_argument("--smoke", action="store_true", help="plumbing run (n<40 → NOT EVIDENCE)")
    parser.add_argument("--state-dir", default=str(_STATE), help="trading state root (read-only)")
    parser.add_argument("--out-dir", default=str(_OUT_DIR), help="report output directory")
    args = parser.parse_args()

    state = Path(args.state_dir)
    loaded, exclusions = load_closed_trades(
        state / "pending_exits",
        state / "daily_metrics",
        state / "phase4_snapshots",
    )
    samples = split_samples(loaded)

    api_key = os.environ.get("IFDS_POLYGON_API_KEY")
    if not api_key:
        raise SystemExit(
            f"Loaded {len(loaded)} trades ({len(exclusions)} excluded). "
            "Set IFDS_POLYGON_API_KEY to fetch forward returns and render the report."
        )

    from ifds.data.cache import FileCache
    from ifds.data.polygon import PolygonClient

    client = PolygonClient(api_key=api_key, cache=FileCache())
    fetcher = polygon_bar_fetcher(client)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for label, trades in samples.items():
        fwd = fetch_forward_returns(trades, fetcher)
        report = run_attribution(trades, fwd)
        md = render_report(report, f"{args.as_of} ({label})", args.smoke, exclusions)
        path = out_dir / f"signal-attribution-{args.as_of}-{label}.md"
        path.write_text(md)
        print(f"[{label}] n={len(trades)} → {path}")


if __name__ == "__main__":
    main()
