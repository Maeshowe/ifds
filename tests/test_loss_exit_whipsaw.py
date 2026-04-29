"""Tests for scripts/analysis/loss_exit_whipsaw_analysis.py."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# compute_whipsaw_cost — pure logic
# ---------------------------------------------------------------------------


class TestComputeWhipsawCost:

    def test_negative_when_moc_better_than_stop(self) -> None:
        """Stop hit at -2%, but price recovered → MOC is better than stop fill."""
        from scripts.analysis.loss_exit_whipsaw_analysis import compute_whipsaw_cost

        # Entry 100, qty 10, actual -20 (stop at 98), MOC 99 → counterfactual -10
        result = compute_whipsaw_cost(
            entry_price=100.0, qty=10, actual_pnl=-20.0, moc_close=99.0
        )
        assert result == pytest.approx(-10.0)

    def test_positive_when_moc_worse_than_stop(self) -> None:
        """Stop hit at -2%, price kept falling → MOC worse, stop saved money."""
        from scripts.analysis.loss_exit_whipsaw_analysis import compute_whipsaw_cost

        # Entry 100, qty 10, actual -20 (stop at 98), MOC 95 → counterfactual -50
        result = compute_whipsaw_cost(
            entry_price=100.0, qty=10, actual_pnl=-20.0, moc_close=95.0
        )
        assert result == pytest.approx(30.0)

    def test_zero_when_moc_matches_stop(self) -> None:
        """MOC exactly equals stop fill price → whipsaw cost is 0."""
        from scripts.analysis.loss_exit_whipsaw_analysis import compute_whipsaw_cost

        result = compute_whipsaw_cost(
            entry_price=100.0, qty=10, actual_pnl=-20.0, moc_close=98.0
        )
        assert result == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# load_loss_exits — CSV parsing
# ---------------------------------------------------------------------------


class TestLoadLossExits:

    def _write_trades_csv(self, path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "date", "ticker", "direction", "entry_price", "entry_qty",
            "exit_price", "exit_qty", "exit_type", "pnl", "pnl_pct",
            "commission", "score", "sector", "sl_price", "tp1_price", "tp2_price",
        ]
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)

    def test_filters_only_loss_exit_rows(self, tmp_path) -> None:
        from scripts.analysis.loss_exit_whipsaw_analysis import load_loss_exits

        self._write_trades_csv(tmp_path / "trades_2026-04-20.csv", [
            self._row("SKM", "LOSS_EXIT", -148.5),
            self._row("AAPL", "TP1", 50.0),
            self._row("MSFT", "MOC", -10.0),
        ])

        out = load_loss_exits("2026-04-20", "2026-04-20", trades_dir=tmp_path)
        assert len(out) == 1
        assert out[0].ticker == "SKM"
        assert out[0].actual_pnl == pytest.approx(-148.5)

    def test_respects_date_window(self, tmp_path) -> None:
        from scripts.analysis.loss_exit_whipsaw_analysis import load_loss_exits

        self._write_trades_csv(tmp_path / "trades_2026-04-20.csv", [
            self._row("SKM", "LOSS_EXIT", -148.5),
        ])
        self._write_trades_csv(tmp_path / "trades_2026-04-12.csv", [
            self._row("OLD", "LOSS_EXIT", -200.0),
        ])

        out = load_loss_exits("2026-04-13", "2026-04-29", trades_dir=tmp_path)
        assert {e.ticker for e in out} == {"SKM"}

    def _row(self, ticker: str, exit_type: str, pnl: float) -> dict:
        return {
            "date": "2026-04-20",
            "ticker": ticker,
            "direction": "LONG",
            "entry_price": "100.0",
            "entry_qty": "10",
            "exit_price": "98.0",
            "exit_qty": "10",
            "exit_type": exit_type,
            "pnl": str(pnl),
            "pnl_pct": "-2.0",
            "commission": "1.0",
            "score": "90.0",
            "sector": "Tech",
            "sl_price": "97.0",
            "tp1_price": "103.0",
            "tp2_price": "105.0",
        }


# ---------------------------------------------------------------------------
# aggregate_split_orders — merge same-ticker same-day rows
# ---------------------------------------------------------------------------


class TestAggregateSplitOrders:

    def test_merges_split_orders_into_single_row(self) -> None:
        from scripts.analysis.loss_exit_whipsaw_analysis import (
            LossExit, aggregate_split_orders,
        )

        # GME 2026-04-21: 4 split rows, total qty 514, total pnl -286.84
        rows = [
            LossExit("2026-04-21", "GME", "Cyc", 92.5, 25.29, 24.74, 100, -55.0, -2.17),
            LossExit("2026-04-21", "GME", "Cyc", 92.5, 25.29, 24.73, 107, -59.92, -2.21),
            LossExit("2026-04-21", "GME", "Cyc", 92.5, 25.29, 24.73, 114, -63.84, -2.21),
            LossExit("2026-04-21", "GME", "Cyc", 92.5, 25.29, 24.73, 193, -108.08, -2.21),
        ]

        merged = aggregate_split_orders(rows)
        assert len(merged) == 1
        assert merged[0].qty == 514
        assert merged[0].actual_pnl == pytest.approx(-286.84, abs=0.01)
        assert merged[0].entry_price == pytest.approx(25.29, abs=1e-3)


# ---------------------------------------------------------------------------
# CloseCache — JSON persistence
# ---------------------------------------------------------------------------


class TestCloseCache:

    def test_round_trip_persistence(self, tmp_path) -> None:
        from scripts.analysis.loss_exit_whipsaw_analysis import CloseCache

        cache_path = tmp_path / "cache.json"
        c1 = CloseCache(cache_path)
        c1.put("NIO", "2026-04-28", 6.37)
        c1.put("CRWV", "2026-04-28", 110.50)
        c1.save()

        c2 = CloseCache(cache_path)
        assert c2.get("NIO", "2026-04-28") == pytest.approx(6.37)
        assert c2.get("CRWV", "2026-04-28") == pytest.approx(110.50)
        assert c2.get("UNSEEN", "2026-04-28") is None

    def test_handles_missing_file_gracefully(self, tmp_path) -> None:
        from scripts.analysis.loss_exit_whipsaw_analysis import CloseCache

        c = CloseCache(tmp_path / "does_not_exist.json")
        assert c.get("NIO", "2026-04-28") is None

    def test_fetch_moc_close_uses_cache_without_api_call(self, tmp_path, monkeypatch) -> None:
        """Cache hit short-circuits before touching PolygonClient."""
        from scripts.analysis.loss_exit_whipsaw_analysis import CloseCache, fetch_moc_close

        cache = CloseCache(tmp_path / "cache.json")
        cache.put("NIO", "2026-04-28", 6.37)

        # If PolygonClient is referenced, blow up — the cache must take over
        monkeypatch.setenv("IFDS_POLYGON_API_KEY", "should-not-be-used")
        called = {"flag": False}

        def boom(*a, **k):
            called["flag"] = True
            raise AssertionError("PolygonClient should not be constructed on cache hit")

        monkeypatch.setattr(
            "ifds.data.polygon.PolygonClient", boom, raising=False
        )

        result = fetch_moc_close("NIO", "2026-04-28", cache)
        assert result == pytest.approx(6.37)
        assert called["flag"] is False
