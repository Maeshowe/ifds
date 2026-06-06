"""Tests for weekly_metrics.py — aggregation logic."""

import json
from pathlib import Path

import pytest


def _make_daily(
    date_str: str,
    pnl: float = 0.0,
    positions: int = 3,
    commission: float = 15.0,
    spy_pct: float = 0.0,
    tp1: int = 0,
    sl: int = 0,
    moc: int = 3,
    loss_exit: int = 0,
    trail: int = 0,
) -> dict:
    """Build a minimal daily metrics JSON matching the real schema."""
    return {
        "date": date_str,
        "day_number": 41,
        "positions": {
            "opened": positions,
            "qualified_above_threshold": 6,
            "threshold": 85,
            "max_allowed": 5,
        },
        "market": {"spy_return_pct": spy_pct, "vix_close": None, "strategy": "LONG"},
        "scoring": {
            "avg_score": 91.0,
            "min_score": 88.0,
            "max_score": 94.0,
            "scores": {"AAPL": 91.0, "MSFT": 92.0, "GOOG": 90.0},
        },
        "execution": {
            "avg_fill_slippage_pct": 0.3,
            "slippage_per_ticker": {
                "AAPL": {"planned": 150.0, "filled": 150.45, "slippage_pct": 0.3},
            },
            "commission_total": commission,
        },
        "exits": {
            "tp1": tp1,
            "tp2": 0,
            "sl": sl,
            "loss_exit": loss_exit,
            "trail": trail,
            "moc": moc,
        },
        "pnl": {
            "gross": pnl,
            "commission": commission,
            "net": pnl - commission,
            "cumulative": -2000 + pnl,
            "cumulative_pct": (-2000 + pnl) / 100_000 * 100,
        },
        "excess_return": {
            "portfolio_return_pct": pnl / 100_000 * 100,
            "spy_return_pct": spy_pct,
            "excess_pct": pnl / 100_000 * 100 - spy_pct,
        },
        "trades": {
            "best": (
                {"ticker": "AAPL", "pnl": abs(pnl) / 2, "pnl_pct": 0.5, "exit_type": "TP1"}
                if pnl > 0
                else None
            ),
            "worst": (
                {"ticker": "MSFT", "pnl": -abs(pnl) / 2, "pnl_pct": -0.5, "exit_type": "SL"}
                if pnl < 0
                else None
            ),
            "details": [
                {
                    "ticker": "AAPL",
                    "score": 91.0,
                    "entry": 150.0,
                    "exit": 152.0,
                    "pnl": pnl / 3,
                    "exit_type": "TP1",
                },
                {
                    "ticker": "MSFT",
                    "score": 92.0,
                    "entry": 300.0,
                    "exit": 298.0,
                    "pnl": pnl / 3,
                    "exit_type": "MOC",
                },
                {
                    "ticker": "GOOG",
                    "score": 90.0,
                    "entry": 170.0,
                    "exit": 169.0,
                    "pnl": pnl / 3,
                    "exit_type": "MOC",
                },
            ],
        },
    }


def _write_daily(metrics_dir: Path, daily: dict) -> None:
    metrics_dir.mkdir(parents=True, exist_ok=True)
    path = metrics_dir / f"{daily['date']}.json"
    with open(path, "w") as f:
        json.dump(daily, f)


class TestWeeklyAggregation:
    """Test aggregate_week with synthetic daily metrics."""

    def test_5_day_aggregation(self, tmp_path, monkeypatch):
        from scripts.analysis.weekly_metrics import aggregate_week, _load_week_metrics

        monkeypatch.setattr("scripts.analysis.weekly_metrics.METRICS_DIR", tmp_path)

        # Week: Mon-Fri, alternating P&L
        for i, pnl in enumerate([50, -30, 80, -20, 40]):
            d = _make_daily(f"2026-04-1{4+i}", pnl=pnl, spy_pct=0.1 * (i + 1))
            _write_daily(tmp_path, d)

        from datetime import date

        days = _load_week_metrics(date(2026, 4, 14))
        assert len(days) == 5

        agg = aggregate_week(days)
        assert agg["trading_days"] == 5
        assert agg["total_positions"] == 15  # 3/day * 5
        assert agg["gross_pnl"] == pytest.approx(120.0)  # 50-30+80-20+40
        assert agg["win_days"] == 3  # days with pnl > 0

    def test_slippage_qty_weighted_and_worst_by_abs(self, tmp_path, monkeypatch):
        """Fix #5: qty-weighted avg across ALL entries + worst by abs magnitude."""
        from scripts.analysis.weekly_metrics import _load_week_metrics, aggregate_week

        monkeypatch.setattr("scripts.analysis.weekly_metrics.METRICS_DIR", tmp_path)

        # W23-style: 4 entries spread across 2 days, with qty.
        d1 = _make_daily("2026-06-02", pnl=10.0)
        d1["execution"]["slippage_per_ticker"] = {
            "MSM": {"planned": 117.0, "filled": 112.6, "slippage_pct": -3.77, "qty": 58},
            "BEN": {"planned": 31.0, "filled": 30.4, "slippage_pct": -1.99, "qty": 100},
        }
        d2 = _make_daily("2026-06-03", pnl=10.0)
        d2["execution"]["slippage_per_ticker"] = {
            "VNO": {"planned": 34.0, "filled": 33.7, "slippage_pct": -0.79, "qty": 101},
            "FFIV": {"planned": 408.0, "filled": 408.0, "slippage_pct": 0.01, "qty": 12},
        }
        _write_daily(tmp_path, d1)
        _write_daily(tmp_path, d2)

        from datetime import date

        days = _load_week_metrics(date(2026, 6, 1))
        agg = aggregate_week(days)
        # qty-weighted: (-3.77*58 -1.99*100 -0.79*101 +0.01*12) / 271 = -1.84%
        assert agg["avg_slippage_pct"] == pytest.approx(-1.84, abs=0.01)
        # worst = most UNFAVORABLE by magnitude (not max() which would pick +0.01)
        assert agg["worst_slippage_pct"] == pytest.approx(-3.77)

    def test_slippage_unweighted_fallback_without_qty(self, tmp_path, monkeypatch):
        """No qty on entries → unweighted mean (backward compatible)."""
        from scripts.analysis.weekly_metrics import _load_week_metrics, aggregate_week

        monkeypatch.setattr("scripts.analysis.weekly_metrics.METRICS_DIR", tmp_path)
        d = _make_daily("2026-06-02", pnl=10.0)
        d["execution"]["slippage_per_ticker"] = {
            "A": {"planned": 10.0, "filled": 10.2, "slippage_pct": 2.0},
            "B": {"planned": 10.0, "filled": 9.6, "slippage_pct": -4.0},
        }
        _write_daily(tmp_path, d)

        from datetime import date

        agg = aggregate_week(_load_week_metrics(date(2026, 6, 1)))
        assert agg["avg_slippage_pct"] == pytest.approx(-1.0)  # mean(2, -4)
        assert agg["worst_slippage_pct"] == pytest.approx(-4.0)  # max abs

    def test_no_data(self, tmp_path, monkeypatch):
        from scripts.analysis.weekly_metrics import _load_week_metrics

        monkeypatch.setattr("scripts.analysis.weekly_metrics.METRICS_DIR", tmp_path)

        from datetime import date

        days = _load_week_metrics(date(2026, 4, 14))
        assert days == []

    def test_partial_week(self, tmp_path, monkeypatch):
        """Only 3 trading days (e.g. holiday week)."""
        from scripts.analysis.weekly_metrics import aggregate_week, _load_week_metrics

        monkeypatch.setattr("scripts.analysis.weekly_metrics.METRICS_DIR", tmp_path)

        for i, pnl in enumerate([100, -50, 30]):
            d = _make_daily(f"2026-04-1{4+i}", pnl=pnl, spy_pct=0.2)
            _write_daily(tmp_path, d)

        from datetime import date

        days = _load_week_metrics(date(2026, 4, 14))
        assert len(days) == 3

        agg = aggregate_week(days)
        assert agg["trading_days"] == 3
        assert agg["gross_pnl"] == pytest.approx(80.0)
        assert agg["avg_positions_per_day"] == pytest.approx(3.0)


class TestMarkdownGeneration:
    """Test that markdown output is well-formed."""

    def test_generates_header(self, tmp_path, monkeypatch):
        from datetime import date

        from scripts.analysis.weekly_metrics import aggregate_week, generate_markdown

        monkeypatch.setattr("scripts.analysis.weekly_metrics.METRICS_DIR", tmp_path)

        d = _make_daily("2026-04-14", pnl=50, spy_pct=0.3)
        _write_daily(tmp_path, d)

        agg = aggregate_week([d])
        md = generate_markdown(date(2026, 4, 14), agg)

        assert "IFDS Weekly Report" in md
        assert "2026-W16" in md
        assert "Apr 14" in md


class TestTelegramSummary:
    """Test Telegram summary format."""

    def test_contains_key_fields(self):
        from datetime import date

        from scripts.analysis.weekly_metrics import aggregate_week, telegram_summary

        d = _make_daily("2026-04-14", pnl=50, commission=15, spy_pct=0.3)
        agg = aggregate_week([d])
        tg = telegram_summary(date(2026, 4, 14), agg)

        assert "IFDS WEEKLY" in tg
        assert "Net P&L" in tg
        assert "Excess vs SPY" in tg
        assert "TP1" in tg
        assert "Commission" in tg
