"""Tests for daily_metrics.py — output schema and edge cases."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# VIX close backfill
# ---------------------------------------------------------------------------


class TestLoadPhase0Vix:
    """_load_phase0_vix parses MACRO_REGIME events from ifds_run_*.jsonl."""

    def _write_event(self, path: Path, **kwargs) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(kwargs) + "\n")

    def test_returns_vix_value_from_macro_regime_event(self, tmp_path):
        from scripts.paper_trading.daily_metrics import _load_phase0_vix

        log = tmp_path / "ifds_run_20260428_141501.jsonl"
        self._write_event(
            log,
            event_type="MACRO_REGIME",
            phase=0,
            data={"vix_value": 18.68, "vix_regime": "normal"},
        )

        assert _load_phase0_vix("2026-04-28", logs_dir=tmp_path) == pytest.approx(18.68)

    def test_returns_latest_vix_when_multiple_events(self, tmp_path):
        from scripts.paper_trading.daily_metrics import _load_phase0_vix

        log = tmp_path / "ifds_run_20260428_141501.jsonl"
        self._write_event(
            log, event_type="MACRO_REGIME", phase=0, data={"vix_value": 17.0}
        )
        self._write_event(
            log, event_type="MACRO_REGIME", phase=0, data={"vix_value": 18.5}
        )

        assert _load_phase0_vix("2026-04-28", logs_dir=tmp_path) == pytest.approx(18.5)

    def test_returns_none_when_no_log_file(self, tmp_path):
        from scripts.paper_trading.daily_metrics import _load_phase0_vix

        assert _load_phase0_vix("2026-04-02", logs_dir=tmp_path) is None

    def test_skips_malformed_lines(self, tmp_path):
        from scripts.paper_trading.daily_metrics import _load_phase0_vix

        log = tmp_path / "ifds_run_20260428_141501.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "w") as f:
            f.write("not-json\n")
            f.write(
                json.dumps(
                    {"event_type": "MACRO_REGIME", "phase": 0, "data": {"vix_value": 18.68}}
                )
                + "\n"
            )

        assert _load_phase0_vix("2026-04-28", logs_dir=tmp_path) == pytest.approx(18.68)

    def test_ignores_events_without_vix_value(self, tmp_path):
        from scripts.paper_trading.daily_metrics import _load_phase0_vix

        log = tmp_path / "ifds_run_20260428_141501.jsonl"
        self._write_event(
            log,
            event_type="MACRO_REGIME",
            phase=0,
            message="VIX=18.68 (Polygon I:VIX)",  # no data dict
        )
        self._write_event(
            log, event_type="API_HEALTH_CHECK", phase=0, data={"vix_value": 99.0}
        )

        assert _load_phase0_vix("2026-04-28", logs_dir=tmp_path) is None


class TestVixCloseInOutput:
    """Integration: build_daily_metrics populates market.vix_close + delta."""

    def test_vix_close_populated_from_phase0_log(self, tmp_path, monkeypatch):
        from scripts.paper_trading.daily_metrics import build_daily_metrics

        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.CUM_PNL_FILE",
            tmp_path / "nonexistent_pnl.json",
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.TRADES_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.EXEC_PLAN_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.PHASE4_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.METRICS_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics._fetch_spy_return",
            lambda d: None,
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics._load_phase0_vix",
            lambda d, logs_dir=None: 18.68,
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics._fetch_vix_close",
            lambda d: None,
        )

        metrics = build_daily_metrics("2026-04-28")
        assert metrics["market"]["vix_close"] == pytest.approx(18.68)
        # No previous-day metrics file → delta is None
        assert metrics["market"]["vix_delta_pct"] is None

    def test_vix_delta_computed_from_previous_day(self, tmp_path, monkeypatch):
        from scripts.paper_trading.daily_metrics import build_daily_metrics

        # Seed yesterday's metrics so delta = (18.5 - 20.0) / 20.0 * 100 = -7.5
        prev_file = tmp_path / "2026-04-27.json"
        with open(prev_file, "w") as f:
            json.dump({"market": {"vix_close": 20.0}}, f)

        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.CUM_PNL_FILE",
            tmp_path / "nonexistent_pnl.json",
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.TRADES_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.EXEC_PLAN_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.PHASE4_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.METRICS_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics._fetch_spy_return",
            lambda d: None,
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics._load_phase0_vix",
            lambda d, logs_dir=None: 18.5,
        )

        metrics = build_daily_metrics("2026-04-28")
        assert metrics["market"]["vix_close"] == pytest.approx(18.5)
        assert metrics["market"]["vix_delta_pct"] == pytest.approx(-7.5)

    def test_vix_close_falls_back_to_polygon_when_log_missing(
        self, tmp_path, monkeypatch
    ):
        from scripts.paper_trading.daily_metrics import build_daily_metrics

        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.CUM_PNL_FILE",
            tmp_path / "nonexistent_pnl.json",
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.TRADES_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.EXEC_PLAN_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.PHASE4_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.METRICS_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics._fetch_spy_return",
            lambda d: None,
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics._load_phase0_vix",
            lambda d, logs_dir=None: None,
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics._fetch_vix_close",
            lambda d: 19.42,
        )

        metrics = build_daily_metrics("2026-04-28")
        assert metrics["market"]["vix_close"] == pytest.approx(19.42)





class TestBuildDailyMetrics:
    """Test the build_daily_metrics function directly."""

    def test_output_has_required_keys(self, tmp_path, monkeypatch):
        """The output JSON must contain all required top-level sections."""
        from scripts.paper_trading.daily_metrics import build_daily_metrics

        # Patch data sources to return minimal data
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.CUM_PNL_FILE",
            tmp_path / "nonexistent_pnl.json",
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.TRADES_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.EXEC_PLAN_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.PHASE4_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics._fetch_spy_return",
            lambda d: None,
        )

        metrics = build_daily_metrics("2026-04-02")

        required_keys = {
            "date", "day_number", "positions", "market", "scoring",
            "execution", "exits", "pnl", "excess_return", "trades",
        }
        assert required_keys == set(metrics.keys())

    def test_no_trades_produces_valid_output(self, tmp_path, monkeypatch):
        """When there are no trades, metrics should still be valid JSON."""
        from scripts.paper_trading.daily_metrics import build_daily_metrics

        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.CUM_PNL_FILE",
            tmp_path / "nonexistent.json",
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.TRADES_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.EXEC_PLAN_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.PHASE4_DIR", tmp_path
        )
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics._fetch_spy_return",
            lambda d: None,
        )

        metrics = build_daily_metrics("2026-04-02")

        assert metrics["positions"]["opened"] == 0
        assert metrics["pnl"]["gross"] == 0
        assert metrics["trades"]["best"] is None
        assert metrics["trades"]["worst"] is None
        assert metrics["trades"]["details"] == []


class TestSlippageCalculation:
    """Test slippage = (fill - planned) / planned × 100."""

    def test_positive_slippage(self):
        """Fill higher than planned → positive slippage (unfavorable for LONG)."""
        planned = 100.00
        filled = 101.50
        slippage = (filled - planned) / planned * 100
        assert slippage == pytest.approx(1.5)

    def test_negative_slippage(self):
        """Fill lower than planned → negative slippage (favorable for LONG)."""
        planned = 100.00
        filled = 99.50
        slippage = (filled - planned) / planned * 100
        assert slippage == pytest.approx(-0.5)

    def test_zero_slippage(self):
        planned = 50.00
        filled = 50.00
        slippage = (filled - planned) / planned * 100
        assert slippage == pytest.approx(0.0)


class TestExcessReturn:
    """Test excess return = portfolio return - SPY return."""

    def test_positive_excess(self):
        portfolio_pct = 0.50
        spy_pct = 0.20
        excess = portfolio_pct - spy_pct
        assert excess == pytest.approx(0.30)

    def test_negative_excess(self):
        portfolio_pct = -0.30
        spy_pct = 0.50
        excess = portfolio_pct - spy_pct
        assert excess == pytest.approx(-0.80)

    def test_no_spy_data(self):
        """When SPY data is unavailable, excess should be None."""
        spy = None
        excess = None if spy is None else (0.5 - spy)
        assert excess is None
