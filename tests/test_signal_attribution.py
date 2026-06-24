"""Tests for scripts/analysis/signal_attribution.py (spec 2026-06-10)."""

from __future__ import annotations

import gzip
import importlib.util
import json
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


# ---------------------------------------------------------------------------
# Data loader — spec §6.1 three pinned invariants
# ---------------------------------------------------------------------------


def _build_state(tmp_path: Path) -> Path:
    """A minimal trading-state tree the loader reads (read-only)."""
    state = tmp_path / "state"
    for sub in ("pending_exits", "daily_metrics", "phase4_snapshots"):
        (state / sub).mkdir(parents=True)
    return state


def _write_pending(state: Path, date: str, records: list[dict]) -> None:
    (state / "pending_exits" / f"{date}.json").write_text(json.dumps(records))


def _write_metrics(state: Path, date: str, day_number: int, details: list[dict]) -> None:
    payload = {"day_number": day_number, "trades": {"details": details}}
    (state / "daily_metrics" / f"{date}.json").write_text(json.dumps(payload))


def _write_snapshot(state: Path, date: str, rows: list[dict]) -> None:
    with gzip.open(state / "phase4_snapshots" / f"{date}.json.gz", "wt") as fh:
        json.dump(rows, fh)


def _load(state: Path):
    return sa.load_closed_trades(
        state / "pending_exits", state / "daily_metrics", state / "phase4_snapshots"
    )


def test_loader_happy_path_realized_return(tmp_path):
    state = _build_state(tmp_path)
    _write_pending(
        state,
        "2026-06-12",
        [{"ticker": "AAA", "entry_price": 100.0, "entry_date": "2026-06-09",
          "qty": 10, "exit_type": "TP1", "sector": "Technology", "entry_score": 88.0}],
    )
    _write_metrics(state, "2026-06-09", 9, [])  # entry-day metrics → entry_day_number
    _write_metrics(state, "2026-06-12", 12, [{"ticker": "AAA", "pnl": 50.0}])
    loaded, excl = _load(state)
    assert excl == []
    assert len(loaded) == 1
    t = loaded[0].trade
    assert t.entry_score == 88.0
    assert t.exit_type == "TP1"
    assert t.realized_r == pytest.approx(50.0 / (100.0 * 10))  # pnl / (entry*qty)
    assert loaded[0].entry_day_number == 9
    assert loaded[0].exit_day_number == 12


def test_loader_aggregates_multi_leg_position(tmp_path):
    # One position, two legs (TP1 then TP2) → ONE trade, blended return (cond. b).
    state = _build_state(tmp_path)
    _write_pending(state, "2026-06-09",
                   [{"ticker": "VNO", "entry_price": 50.0, "entry_date": "2026-06-03",
                     "qty": 60, "exit_type": "TP1", "sector": "Real Estate", "entry_score": 74.0}])
    _write_pending(state, "2026-06-10",
                   [{"ticker": "VNO", "entry_price": 50.0, "entry_date": "2026-06-03",
                     "qty": 40, "exit_type": "TP2", "sector": "Real Estate", "entry_score": 74.0}])
    _write_metrics(state, "2026-06-03", 9, [])
    _write_metrics(state, "2026-06-09", 13, [{"ticker": "VNO", "pnl": 120.0}])  # TP1 leg
    _write_metrics(state, "2026-06-10", 14, [{"ticker": "VNO", "pnl": 80.0}])   # TP2 leg
    loaded, excl = _load(state)
    assert excl == []
    assert len(loaded) == 1  # blended, NOT two per-leg points
    lt = loaded[0]
    # Σpnl / (entry × Σqty) = 200 / (50 × 100)
    assert lt.trade.realized_r == pytest.approx(200.0 / (50.0 * 100))
    assert lt.trade.exit_type == "TP2"  # final-leg label
    assert lt.exit_day_number == 14  # final leg
    assert lt.entry_day_number == 9


def test_loader_excludes_position_if_any_leg_pnl_missing(tmp_path):
    # Multi-leg position where the first (early) leg lacks broker detail → excluded.
    state = _build_state(tmp_path)
    _write_pending(state, "2026-06-03",
                   [{"ticker": "AKAM", "entry_price": 140.0, "entry_date": "2026-05-26",
                     "qty": 8, "exit_type": "TP1", "sector": "Technology", "entry_score": 61.0}])
    _write_pending(state, "2026-06-04",
                   [{"ticker": "AKAM", "entry_price": 140.0, "entry_date": "2026-05-26",
                     "qty": 9, "exit_type": "TIME_STOP", "sector": "Technology", "entry_score": 61.0}])
    _write_metrics(state, "2026-06-03", 8, [])  # TP1 leg detail MISSING
    _write_metrics(state, "2026-06-04", 9, [{"ticker": "AKAM", "pnl": 30.0}])
    loaded, excl = _load(state)
    assert loaded == []  # cannot blend a partial position → whole position dropped
    assert len(excl) == 1
    assert "≥1 leg" in excl[0].reason


def test_loader_invariant1_snapshot_recovery_for_missing_score(tmp_path):
    # entry_score None (legacy) and 0.0 (sentinel) → recovered from the snapshot.
    state = _build_state(tmp_path)
    _write_pending(
        state,
        "2026-06-12",
        [
            {"ticker": "NONE_TK", "entry_price": 50.0, "entry_date": "2026-06-08",
             "qty": 4, "exit_type": "TP1", "sector": "Energy", "entry_score": None},
            {"ticker": "ZERO_TK", "entry_price": 20.0, "entry_date": "2026-06-08",
             "qty": 5, "exit_type": "TIME_STOP", "sector": "Energy", "entry_score": 0.0},
        ],
    )
    _write_metrics(state, "2026-06-12", 12,
                   [{"ticker": "NONE_TK", "pnl": 4.0}, {"ticker": "ZERO_TK", "pnl": -2.0}])
    _write_snapshot(state, "2026-06-08",
                    [{"ticker": "NONE_TK", "combined_score": 71.0},
                     {"ticker": "ZERO_TK", "combined_score": 64.5}])
    loaded, excl = _load(state)
    assert excl == []
    scores = {lt.trade.ticker: lt.trade.entry_score for lt in loaded}
    assert scores == {"NONE_TK": 71.0, "ZERO_TK": 64.5}


def test_loader_invariant1_excludes_when_unrecoverable(tmp_path):
    # Sentinel score AND snapshot lacks the ticker → excluded, never leaks as 0.0.
    state = _build_state(tmp_path)
    _write_pending(
        state,
        "2026-06-12",
        [{"ticker": "GHOST", "entry_price": 30.0, "entry_date": "2026-06-08",
          "qty": 3, "exit_type": "TP1", "sector": "Energy", "entry_score": 0.0}],
    )
    _write_metrics(state, "2026-06-12", 12, [{"ticker": "GHOST", "pnl": 1.0}])
    _write_snapshot(state, "2026-06-08", [{"ticker": "OTHER", "combined_score": 80.0}])
    loaded, excl = _load(state)
    assert loaded == []
    assert len(excl) == 1
    assert excl[0].ticker == "GHOST"
    assert "entry_score" in excl[0].reason


def test_loader_invariant2_exit_type_from_ledger_not_daily_metrics(tmp_path):
    # Real-world SJM: ledger=MENTAL_SL, daily_metrics=TP1. Ledger must win.
    state = _build_state(tmp_path)
    _write_pending(
        state,
        "2026-06-23",
        [{"ticker": "SJM", "entry_price": 115.99, "entry_date": "2026-06-17",
          "qty": 49, "exit_type": "MENTAL_SL", "sector": "Consumer Defensive",
          "entry_score": 77.41}],
    )
    _write_metrics(state, "2026-06-23", 25,
                   [{"ticker": "SJM", "pnl": -330.91, "exit_type": "TP1"}])
    loaded, excl = _load(state)
    assert excl == []
    assert loaded[0].trade.exit_type == "MENTAL_SL"  # NOT the daily_metrics "TP1"


def test_loader_excludes_when_realized_pnl_missing(tmp_path):
    state = _build_state(tmp_path)
    _write_pending(
        state,
        "2026-06-12",
        [{"ticker": "AAA", "entry_price": 100.0, "entry_date": "2026-06-09",
          "qty": 10, "exit_type": "TP1", "sector": "Technology", "entry_score": 88.0}],
    )
    _write_metrics(state, "2026-06-12", 12, [])  # no detail for AAA
    loaded, excl = _load(state)
    assert loaded == []
    assert "realized pnl unavailable" in excl[0].reason


def test_loader_is_read_only(tmp_path):
    # The loader must not create or modify anything under state/ (spec §6.1/3).
    state = _build_state(tmp_path)
    _write_pending(
        state,
        "2026-06-12",
        [{"ticker": "AAA", "entry_price": 100.0, "entry_date": "2026-06-09",
          "qty": 10, "exit_type": "TP1", "sector": "Technology", "entry_score": 88.0}],
    )
    _write_metrics(state, "2026-06-12", 12, [{"ticker": "AAA", "pnl": 50.0}])
    before = {p: p.stat().st_mtime_ns for p in state.rglob("*") if p.is_file()}
    _load(state)
    after = {p: p.stat().st_mtime_ns for p in state.rglob("*") if p.is_file()}
    assert before == after  # same files, same mtimes → nothing written


def test_split_samples_invariant3_entry_based_clean(tmp_path):
    # EARLY: entry Day 4 (distorted predictor) exit Day 11.
    # LATE:  entry Day 9 (clean) exit Day 12.
    # Entry-based clean keeps only LATE; the exit-based diagnostic keeps both.
    state = _build_state(tmp_path)
    _write_pending(state, "2026-06-05",
                   [{"ticker": "EARLY", "entry_price": 10.0, "entry_date": "2026-05-29",
                     "qty": 5, "exit_type": "TP1", "sector": "Energy", "entry_score": 70.0}])
    _write_pending(state, "2026-06-12",
                   [{"ticker": "LATE", "entry_price": 10.0, "entry_date": "2026-06-09",
                     "qty": 5, "exit_type": "TP1", "sector": "Energy", "entry_score": 80.0}])
    _write_metrics(state, "2026-05-29", 4, [])   # EARLY entry → Day 4 (pre-clean)
    _write_metrics(state, "2026-06-05", 11, [{"ticker": "EARLY", "pnl": 1.0}])  # EARLY exit Day 11
    _write_metrics(state, "2026-06-09", 9, [])   # LATE entry → Day 9 (clean)
    _write_metrics(state, "2026-06-12", 12, [{"ticker": "LATE", "pnl": 2.0}])
    loaded, _ = _load(state)
    samples = sa.split_samples(loaded)
    assert {t.ticker for t in samples["full"]} == {"EARLY", "LATE"}
    assert {t.ticker for t in samples["clean"]} == {"LATE"}  # entry Day 9+ only (primary)
    assert {t.ticker for t in samples["clean_exit"]} == {"EARLY", "LATE"}  # exit Day 9+ diag


# ---------------------------------------------------------------------------
# Forward returns
# ---------------------------------------------------------------------------


def test_horizon_return_uses_trading_day_offset():
    bars = [
        {"date": "2026-06-09", "close": 100.0},
        {"date": "2026-06-10", "close": 101.0},
        {"date": "2026-06-11", "close": 103.0},
    ]
    assert sa._horizon_return(bars, "2026-06-09", 1) == pytest.approx(0.01)
    assert sa._horizon_return(bars, "2026-06-09", 2) == pytest.approx(0.03)
    assert sa._horizon_return(bars, "2026-06-09", 5) is None  # not enough bars


def test_fetch_forward_returns_with_mock_fetcher():
    trade = sa.Trade(
        ticker="AAA", entry_date="2026-06-09", entry_price=100.0, entry_score=80.0,
        sector="Technology", exit_type="TP1", realized_r=0.02,
    )
    series = {
        "AAA": [{"date": "2026-06-09", "close": 100.0}, {"date": "2026-06-10", "close": 110.0}],
        "XLK": [{"date": "2026-06-09", "close": 50.0}, {"date": "2026-06-10", "close": 51.0}],
        "SPY": [{"date": "2026-06-09", "close": 400.0}, {"date": "2026-06-10", "close": 404.0}],
    }

    def fetcher(symbol, from_date, to_date):
        return series.get(symbol)

    fwd = sa.fetch_forward_returns([trade], fetcher, horizons=(1,))
    key = ("AAA", "2026-06-09", 1)
    assert fwd[key]["stock"] == pytest.approx(0.10)
    assert fwd[key]["sector"] == pytest.approx(0.02)  # XLK 50→51
    assert fwd[key]["spy"] == pytest.approx(0.01)  # SPY 400→404


def test_fetch_forward_returns_skips_horizon_without_bars():
    trade = sa.Trade(
        ticker="AAA", entry_date="2026-06-09", entry_price=100.0, entry_score=80.0,
        sector="Technology", exit_type="TP1", realized_r=0.02,
    )

    def fetcher(symbol, from_date, to_date):
        return [{"date": "2026-06-09", "close": 100.0}]  # only entry bar, no +h

    fwd = sa.fetch_forward_returns([trade], fetcher, horizons=(1, 3, 5))
    assert fwd == {}  # every horizon lacks a forward bar → omitted
