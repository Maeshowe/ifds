"""Tests for scripts/analysis/signal_attribution.py (spec 2026-06-10)."""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "analysis" / "signal_attribution.py"


def _load():
    spec = importlib.util.spec_from_file_location("signal_attribution", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so @dataclass can resolve cls.__module__ in sys.modules.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


sa = _load()


# --- return measures ---


def test_forward_return():
    assert sa.forward_return(100.0, 110.0) == pytest.approx(0.10)
    assert sa.forward_return(100.0, 95.0) == pytest.approx(-0.05)
    with pytest.raises(ValueError):
        sa.forward_return(0.0, 110.0)


def test_sector_and_beta_residual():
    # stock +10%, sector +4% → selection residual +6%
    assert sa.sector_residual(0.10, 0.04) == pytest.approx(0.06)
    # stock +10%, SPY +5%, beta 1.2 → +10% - 6% = +4%
    assert sa.beta_adjusted(0.10, 0.05, 1.2) == pytest.approx(0.04)


# --- statistics ---


def test_pearson_perfect_and_known():
    assert sa.pearson(np.array([1, 2, 3]), np.array([2, 4, 6])) == pytest.approx(1.0)
    assert sa.pearson(np.array([1, 2, 3]), np.array([6, 4, 2])) == pytest.approx(-1.0)
    assert math.isnan(sa.pearson(np.array([1, 1, 1]), np.array([1, 2, 3])))  # zero variance


def test_spearman_monotone_nonlinear():
    x = np.array([1, 2, 3, 4, 5])
    y = np.array([1, 4, 9, 16, 25])  # monotone but non-linear
    assert sa.spearman(x, y) == pytest.approx(1.0)  # perfect rank correlation
    assert sa.pearson(x, y) < 1.0  # Pearson penalised by curvature


def test_spearman_handles_ties():
    x = np.array([1, 2, 2, 3])
    y = np.array([10, 20, 20, 30])
    assert sa.spearman(x, y) == pytest.approx(1.0, abs=1e-9)


def test_fisher_z_ci_excludes_zero_for_strong_r():
    lo, hi = sa.fisher_z_ci(0.8, 30)
    assert lo > 0 and hi < 1.0
    # weak r on small n → CI straddles 0
    lo2, hi2 = sa.fisher_z_ci(0.1, 10)
    assert lo2 < 0 < hi2
    # undefined cases
    assert all(math.isnan(v) for v in sa.fisher_z_ci(0.5, 3))


def test_correlate_with_ci_excludes_zero_flag():
    x = np.arange(1, 31, dtype=float)
    y = x.copy()
    y[14], y[15] = y[15], y[14]  # one rank inversion → strong but <1.0 Spearman
    c = sa.correlate_with_ci(x, y, "spearman")
    assert c["excludes_zero"] is True
    assert 0.9 < c["r"] < 1.0 and c["n"] == 30


def test_correlate_ci_undefined_small_n():
    # n<4 → Fisher-z CI undefined → excludes_zero flag must be False (not significant).
    c = sa.correlate_with_ci(np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0]), "spearman")
    assert math.isnan(c["ci_low"]) and c["excludes_zero"] is False


def test_quintile_monotone():
    scores = np.arange(1, 26, dtype=float)
    returns = scores / 100.0  # monotone increasing
    table = sa.quintile_table(scores, returns, q=5)
    means = [b["mean_return"] for b in table]
    assert means == sorted(means)  # monotone increasing across quintiles
    assert len(table) == 5
    assert sum(b["n"] for b in table) == 25


# --- S_j recovery ---


def test_recover_entry_score():
    snap = [
        {"ticker": "MASI", "combined_score": 89.57, "sector": "Healthcare"},
        {"ticker": "VNO", "combined_score": 72.0, "sector": "Real Estate"},
    ]
    assert sa.recover_entry_score(snap, "MASI") == pytest.approx(89.57)
    assert sa.recover_entry_score(snap, "ZZZ") is None
    assert sa.recover_entry_score([], "MASI") is None


# --- orchestrator ---


def _trade(ticker, score, realized_r, exit_type="TP1", date="2026-06-09"):
    return sa.Trade(
        ticker=ticker,
        entry_date=date,
        entry_price=100.0,
        entry_score=score,
        sector="Tech",
        exit_type=exit_type,
        realized_r=realized_r,
    )


def test_run_attribution_primary_metric_present():
    # 6 trades: score correlated with sector-relative forward return
    trades = [_trade(f"T{i}", score=50 + i * 5, realized_r=0.01 * i) for i in range(6)]
    fwd = {}
    for i, t in enumerate(trades):
        for h in sa.HORIZONS:
            # stock fwd return grows with score; sector flat → residual grows
            fwd[(t.ticker, t.entry_date, h)] = {
                "stock": 0.01 * i,
                "sector": 0.002,
                "spy": 0.003,
                "beta": 1.0,
            }
    rep = sa.run_attribution(trades, fwd)
    assert rep["n_total"] == 6
    assert rep["primary"]["metric"] == "L2_sector_spearman"
    assert rep["primary"]["horizon"] == 5
    # monotone construction → strong positive L2 Spearman
    assert rep["primary"]["r"] > 0.9
    # L0 + L1/L2 present
    assert "pearson" in rep["L0"] and 5 in rep["horizons"]
    assert "L2_sector" in rep["horizons"][5]


def test_run_attribution_skips_horizon_with_few_points():
    trades = [_trade(f"T{i}", 50 + i, 0.01 * i) for i in range(6)]
    # only 2 trades have h=5 forward returns → that horizon skipped (n<4)
    fwd = {}
    for h in (1, 3):
        for t in trades:
            fwd[(t.ticker, t.entry_date, h)] = {"stock": 0.01, "sector": 0.0, "spy": 0.0}
    for t in trades[:2]:
        fwd[(t.ticker, t.entry_date, 5)] = {"stock": 0.01, "sector": 0.0, "spy": 0.0}
    rep = sa.run_attribution(trades, fwd)
    assert rep["horizons"][5]["note"].startswith("n<4")
    assert rep["primary"] is None  # no primary when h=5 unavailable


def test_render_report_smoke_label():
    trades = [_trade(f"T{i}", 50 + i, 0.01 * i) for i in range(6)]
    fwd = {
        (t.ticker, t.entry_date, h): {"stock": 0.01, "sector": 0.0, "spy": 0.0}
        for t in trades
        for h in sa.HORIZONS
    }
    rep = sa.run_attribution(trades, fwd)
    md = sa.render_report(rep, "2026-06-10", smoke=True)
    assert "PLUMBING VALIDATION ONLY" in md
    assert "NOT EVIDENCE" in md
