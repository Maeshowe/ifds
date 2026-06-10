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
import math
from dataclasses import dataclass

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


def render_report(report: dict, as_of: str, smoke: bool) -> str:
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
    L.append(
        "_Spec: docs/foundational/strategic-review/2026-06-10-signal-isolating-attribution-spec.md_"
    )
    return "\n".join(L)


def main() -> None:  # pragma: no cover — I/O orchestration, runs at Day 63
    parser = argparse.ArgumentParser(description="Signal-isolating attribution test")
    parser.add_argument("--as-of", default="today", help="evaluation date label")
    parser.add_argument("--smoke", action="store_true", help="n=14 plumbing run")
    parser.parse_args()
    raise SystemExit(
        "Data-loading (ledger + Phase 4 snapshots + Polygon bars) wires in at Day 63; "
        "the tested pure-computation core (run_attribution/correlate_with_ci/...) is ready now."
    )


if __name__ == "__main__":
    main()
