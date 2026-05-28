"""Tests for the canonical cumulative_pnl.json reconstruction (P0 §0.11)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO / "scripts" / "admin" / "canonical_pnl_reconstruction.py"

_spec = importlib.util.spec_from_file_location("canonical_pnl_reconstruction", _SCRIPT)
canon = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(canon)


def test_canonical_cumulative_is_minus_651():
    """The canonical daily_history must sum to the IBKR-verified -$651.10."""
    cum = round(sum(e["pnl"] for e in canon.CANONICAL_HISTORY), 2)
    assert cum == pytest.approx(-651.10, abs=0.05)


def test_rebuild_replaces_history_and_recomputes():
    """rebuild() replaces daily_history wholesale and recomputes the totals."""
    stale = {
        "start_date": "2026-05-18",
        "initial_capital": 100000,
        "trading_days": 5,
        "cumulative_pnl": 39.33,  # the wrong official value
        "cumulative_pnl_pct": 0.039,
        "daily_history": [{"date": "2026-05-19", "pnl": 112.31, "commission": 1.08}],
    }
    out = canon.rebuild(stale)
    assert out["cumulative_pnl"] == pytest.approx(-651.10, abs=0.05)
    assert out["trading_days"] == len(canon.CANONICAL_HISTORY)
    # start_date + initial_capital preserved
    assert out["start_date"] == "2026-05-18"
    assert out["initial_capital"] == 100000


def test_rebuild_is_idempotent():
    """Running the rebuild twice yields identical output (full replace)."""
    stale = {"start_date": "2026-05-18", "initial_capital": 100000, "daily_history": []}
    once = canon.rebuild(stale)
    twice = canon.rebuild(once)
    assert once == twice


def test_day8_exits_present():
    """The 2026-05-27 (Day 8) entry must carry the 7 exits the gap dropped."""
    day8 = next(e for e in canon.CANONICAL_HISTORY if e["date"] == "2026-05-27")
    assert day8["pnl"] == pytest.approx(-695.79, abs=0.01)
    assert day8["tp2_hits"] == 1
    assert day8["moc_exits"] == 6
    assert day8["trades"] == 7


def test_vlo_sl_is_ibkr_canonical_not_old_approximation():
    """VLO SL day (5/21) must be the IBKR -220.69, not the old -227.06."""
    day4 = next(e for e in canon.CANONICAL_HISTORY if e["date"] == "2026-05-21")
    assert day4["pnl"] == pytest.approx(-220.69, abs=0.01)
    assert day4["sl_hits"] == 1


def test_recompute_sums_net_pnl():
    """recompute() sets cumulative to the sum of per-day net pnl."""
    data = {
        "initial_capital": 100000,
        "daily_history": [{"pnl": 100.0}, {"pnl": -250.0}, {"pnl": 50.0}],
    }
    out = canon.recompute(data)
    assert out["cumulative_pnl"] == pytest.approx(-100.0)
    assert out["trading_days"] == 3
    assert out["cumulative_pnl_pct"] == pytest.approx(-0.1, abs=1e-6)
