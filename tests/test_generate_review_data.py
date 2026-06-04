"""Tests for generate_review_data.py — autonomous review pipeline 1a.

Deterministic local aggregator: computed fields + local anomaly flags.
Path constants monkeypatched to tmp_path so production state is untouched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _pt_path():
    pt = str(Path(__file__).resolve().parent.parent / "scripts" / "paper_trading")
    added = pt not in sys.path
    if added:
        sys.path.insert(0, pt)
    yield
    if added:
        sys.path.remove(pt)


def _grd():
    import importlib

    import generate_review_data as m

    return importlib.reload(m)


def _setup(tmp_path, monkeypatch, *, cum=None, metrics=None, swing=None, uw=None, reconcile=None):
    m = _grd()
    (tmp_path / "logs").mkdir(exist_ok=True)
    (tmp_path / "dm").mkdir(exist_ok=True)
    (tmp_path / "uw").mkdir(exist_ok=True)
    cum_file = tmp_path / "cumulative_pnl.json"
    cum_file.write_text(json.dumps(cum or {}))
    if metrics is not None:
        (tmp_path / "dm" / "2026-06-03.json").write_text(json.dumps(metrics))
    swing_file = tmp_path / "swing_positions.json"
    swing_file.write_text(json.dumps(swing or {}))
    if uw is not None:
        (tmp_path / "uw" / "2026-06-03.json").write_text(json.dumps(uw))
    if reconcile is not None:
        (tmp_path / "logs" / "pt_reconcile_2026-06-03.log").write_text(reconcile)
    monkeypatch.setattr(m, "CUM_PNL_FILE", cum_file)
    monkeypatch.setattr(m, "DAILY_METRICS_DIR", tmp_path / "dm")
    monkeypatch.setattr(m, "SWING_STATE_FILE", swing_file)
    monkeypatch.setattr(m, "UW_SHADOW_DIR", tmp_path / "uw")
    monkeypatch.setattr(m, "LOGS_DIR", tmp_path / "logs")
    return m


def _cum():
    return {
        "cumulative_pnl": -43.92,
        "cumulative_pnl_pct": -0.04,
        "trading_days": 11,
        "daily_history": [
            {
                "date": "2026-06-03",
                "pnl": 229.84,
                "commission": 3.22,
                "tp1_hits": 2,
                "moc_exits": 1,
            },
        ],
    }


class TestCoreFields:
    def test_day_number_pnl_exits(self, tmp_path, monkeypatch):
        m = _setup(tmp_path, monkeypatch, cum=_cum())
        d = m.build_review_data("2026-06-03")
        # 5/18..6/03 NYSE trading days (Memorial Day 5/25 excluded) = 12
        assert d["day_number"]["nyse_trading"] == 12
        assert d["pnl"]["realized_today"] == 229.84
        assert d["pnl"]["cumulative"] == -43.92
        assert d["exits"]["tp1"] == 2 and d["exits"]["moc"] == 1

    def test_positions_and_sector_distribution(self, tmp_path, monkeypatch):
        swing = {
            "positions": [
                {
                    "ticker": "JHG",
                    "entry_price": 51.84,
                    "qty_remaining": 289,
                    "atr": 1.5,
                    "sector": "Financial Services",
                    "entry_date": "2026-05-29",
                    "days_held": 4,
                    "next_action": "HOLD",
                    "stop_level": 48.0,
                },
            ]
        }
        m = _setup(tmp_path, monkeypatch, cum=_cum(), swing=swing)
        d = m.build_review_data("2026-06-03")
        assert d["positions"]["open_count"] == 1
        assert d["positions"]["sector_distribution"]["Financial Services"] == pytest.approx(
            51.84 * 289, abs=1
        )
        ep = d["positions"]["detail"][0]
        assert ep["ticker"] == "JHG"
        assert ep["atr_pct"] == pytest.approx(1.5 / 51.84, abs=0.001)


class TestFlags:
    def test_single_position_concentration_flag(self, tmp_path, monkeypatch):
        swing = {
            "positions": [
                {
                    "ticker": "JHG",
                    "entry_price": 51.84,
                    "qty_remaining": 289,
                    "atr": 1.5,
                    "sector": "Financial Services",
                    "entry_date": "2026-05-29",
                    "days_held": 4,
                }
            ]
        }  # 289*51.84 = 14,982 = 14.98% > 12%
        m = _setup(tmp_path, monkeypatch, cum=_cum(), swing=swing)
        flags = m.build_review_data("2026-06-03")["flags"]
        assert any(
            f["flag"] == "single_position_concentration" and f["ticker"] == "JHG" for f in flags
        )

    def test_atr_floor_and_ceiling(self, tmp_path, monkeypatch):
        swing = {
            "positions": [
                {
                    "ticker": "LOW",
                    "entry_price": 100.0,
                    "qty_remaining": 10,
                    "atr": 0.3,
                    "sector": "X",
                    "entry_date": "2026-06-03",
                    "days_held": 0,
                },  # 0.3% < 0.5%
                {
                    "ticker": "HIGH",
                    "entry_price": 100.0,
                    "qty_remaining": 10,
                    "atr": 6.0,
                    "sector": "Y",
                    "entry_date": "2026-06-03",
                    "days_held": 0,
                },  # 6% > 5%
            ]
        }
        m = _setup(tmp_path, monkeypatch, cum=_cum(), swing=swing)
        flags = m.build_review_data("2026-06-03")["flags"]
        assert any(f["flag"] == "atr_floor_breach" and f["ticker"] == "LOW" for f in flags)
        assert any(f["flag"] == "atr_ceiling_breach" and f["ticker"] == "HIGH" for f in flags)

    def test_days_held_calendar_bug_regression_only(self, tmp_path, monkeypatch):
        # REGRESSION: stored days_held=7 (calendar-inflated) while the expected
        # trading-day hold from 5/27 is 5 → flag. A correct stored value (=5)
        # must NOT flag (trading-vs-calendar difference is normal).
        bug = {
            "ticker": "EOG",
            "entry_price": 140.0,
            "qty_remaining": 10,
            "atr": 3.0,
            "sector": "Energy",
            "entry_date": "2026-05-27",
            "days_held": 7,
        }
        m = _setup(tmp_path, monkeypatch, cum=_cum(), swing={"positions": [bug]})
        flags = m.build_review_data("2026-06-03")["flags"]
        assert any(f["flag"] == "days_held_calendar_bug" and f["ticker"] == "EOG" for f in flags)

        ok = {**bug, "days_held": 5}  # correct trading-day hold → no flag
        m2 = _setup(tmp_path, monkeypatch, cum=_cum(), swing={"positions": [ok]})
        flags2 = m2.build_review_data("2026-06-03")["flags"]
        assert not any(f["flag"] == "days_held_calendar_bug" for f in flags2)

    def test_reconcile_silent_ok_positive(self, tmp_path, monkeypatch):
        m = _setup(
            tmp_path,
            monkeypatch,
            cum=_cum(),
            reconcile="22:15 Reconciliation OK — state and IBKR match (silent exit).",
        )
        flags = m.build_review_data("2026-06-03")["flags"]
        assert any(
            f["flag"] == "reconcile_silent_ok" and f["priority"] == "positive" for f in flags
        )

    def test_no_flags_clean_day(self, tmp_path, monkeypatch):
        swing = {
            "positions": [
                {
                    "ticker": "OK",
                    "entry_price": 100.0,
                    "qty_remaining": 10,
                    "atr": 2.0,
                    "sector": "X",
                    "entry_date": "2026-06-02",
                    "days_held": 1,
                }  # 2% atr, 1% notional
            ]
        }
        m = _setup(tmp_path, monkeypatch, cum=_cum(), swing=swing)
        flags = m.build_review_data("2026-06-03")["flags"]
        assert flags == []


class TestGracefulDegradation:
    def test_missing_everything_returns_valid(self, tmp_path, monkeypatch):
        m = _setup(tmp_path, monkeypatch)  # all empty
        d = m.build_review_data("2026-06-03")
        assert d["date"] == "2026-06-03"
        assert d["positions"]["open_count"] == 0
        assert d["flags"] == []
        assert d["pnl"]["cumulative"] is None
