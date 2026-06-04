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
        self._write_event(log, event_type="MACRO_REGIME", phase=0, data={"vix_value": 17.0})
        self._write_event(log, event_type="MACRO_REGIME", phase=0, data={"vix_value": 18.5})

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
                json.dumps({"event_type": "MACRO_REGIME", "phase": 0, "data": {"vix_value": 18.68}})
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
        self._write_event(log, event_type="API_HEALTH_CHECK", phase=0, data={"vix_value": 99.0})

        assert _load_phase0_vix("2026-04-28", logs_dir=tmp_path) is None


class TestVixCloseInOutput:
    """Integration: build_daily_metrics populates market.vix_close + delta."""

    def test_vix_close_populated_from_phase0_log(self, tmp_path, monkeypatch):
        from scripts.paper_trading.daily_metrics import build_daily_metrics

        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.CUM_PNL_FILE",
            tmp_path / "nonexistent_pnl.json",
        )
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.TRADES_DIR", tmp_path)
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.EXEC_PLAN_DIR", tmp_path)
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.PHASE4_DIR", tmp_path)
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.METRICS_DIR", tmp_path)
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
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.TRADES_DIR", tmp_path)
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.EXEC_PLAN_DIR", tmp_path)
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.PHASE4_DIR", tmp_path)
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.METRICS_DIR", tmp_path)
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

    def test_vix_close_falls_back_to_polygon_when_log_missing(self, tmp_path, monkeypatch):
        from scripts.paper_trading.daily_metrics import build_daily_metrics

        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.CUM_PNL_FILE",
            tmp_path / "nonexistent_pnl.json",
        )
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.TRADES_DIR", tmp_path)
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.EXEC_PLAN_DIR", tmp_path)
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.PHASE4_DIR", tmp_path)
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.METRICS_DIR", tmp_path)
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
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.TRADES_DIR", tmp_path)
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.EXEC_PLAN_DIR", tmp_path)
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.PHASE4_DIR", tmp_path)
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics._fetch_spy_return",
            lambda d: None,
        )

        metrics = build_daily_metrics("2026-04-02")

        required_keys = {
            "date",
            "day_number",
            "positions",
            "market",
            "scoring",
            "execution",
            "exits",
            "pnl",
            "excess_return",
            "trades",
            "uw_shadow_summary",  # Day 63 §3.2 — UW shadow log integration
            "swing_state",  # Task #5 — swing portfolio snapshot
        }
        assert required_keys == set(metrics.keys())

    def test_swing_state_includes_sector_cap_pct(self, tmp_path, monkeypatch):
        """sector_cap_pct must be explicit in swing_state (post-rename clarity).

        Regression for 2026-05-21 sector-metric-clarity task. The Day 3
        Log Review chat false-positive arose because the old sector_max_pct
        field was confused with a config cap. The rename + new explicit
        sector_cap_pct field disambiguates these:

          * sector_observed_max_pct — max sector share seen today (display)
          * sector_cap_pct         — swing_sector_cap_pct × 100 (config)

        Refs: docs/tasks/2026-05-21-sector-metric-clarity.md
              docs/tasks/2026-05-21-sector-cap-hotfix.md (REJECTED)
        """
        from scripts.paper_trading.daily_metrics import build_daily_metrics

        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.CUM_PNL_FILE",
            tmp_path / "nonexistent_pnl.json",
        )
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.TRADES_DIR", tmp_path)
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.EXEC_PLAN_DIR", tmp_path)
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.PHASE4_DIR", tmp_path)
        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics._fetch_spy_return",
            lambda d: None,
        )

        metrics = build_daily_metrics("2026-04-02")
        swing_state = metrics["swing_state"]

        # Both disambiguated keys must be present
        assert (
            "sector_observed_max_pct" in swing_state
        ), "Display metric must be named sector_observed_max_pct"
        assert "sector_cap_pct" in swing_state, "Config cap must be explicit as sector_cap_pct"

        # The deprecated combined key must NOT be present (regression guard)
        assert "sector_max_pct" not in swing_state, (
            "Deprecated sector_max_pct key must be removed to prevent "
            "confusion with config cap (see Day 3 2026-05-20 false-positive)"
        )

        # sector_cap_pct should reflect Day 63 decision §3.11 (30%) by default
        # — verifies the config wiring works end-to-end.
        assert swing_state["sector_cap_pct"] == 30.0, (
            "Default swing_sector_cap_pct=0.30 must surface as 30.0 " "(per Day 63 decision §3.11)"
        )

    def test_no_trades_produces_valid_output(self, tmp_path, monkeypatch):
        """When there are no trades, metrics should still be valid JSON."""
        from scripts.paper_trading.daily_metrics import build_daily_metrics

        monkeypatch.setattr(
            "scripts.paper_trading.daily_metrics.CUM_PNL_FILE",
            tmp_path / "nonexistent.json",
        )
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.TRADES_DIR", tmp_path)
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.EXEC_PLAN_DIR", tmp_path)
        monkeypatch.setattr("scripts.paper_trading.daily_metrics.PHASE4_DIR", tmp_path)
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


# ---------------------------------------------------------------------------
# Swing-era metadata-sync (P0 §0.11 #3b)
# ---------------------------------------------------------------------------


class TestSwingMetadataSync:
    """When no trades CSV exists (swing exits produce none), build_daily_metrics
    derives exits/commission/opened/P&L from the cumulative daily_history entry
    that record_pending_exits populates + swing_state."""

    def _patch_dirs(self, tmp_path, monkeypatch, cum_file):
        dm = "scripts.paper_trading.daily_metrics"
        monkeypatch.setattr(f"{dm}.CUM_PNL_FILE", cum_file)
        monkeypatch.setattr(f"{dm}.TRADES_DIR", tmp_path)  # no trades_{date}.csv → empty
        monkeypatch.setattr(f"{dm}.EXEC_PLAN_DIR", tmp_path)
        monkeypatch.setattr(f"{dm}.PHASE4_DIR", tmp_path)
        monkeypatch.setattr(f"{dm}.METRICS_DIR", tmp_path)
        monkeypatch.setattr(f"{dm}.UW_SHADOW_DIR", tmp_path)
        monkeypatch.setattr(f"{dm}._fetch_spy_return", lambda d: None)
        monkeypatch.setattr(f"{dm}._load_phase0_vix", lambda d, logs_dir=None: None)
        monkeypatch.setattr(f"{dm}._fetch_vix_close", lambda d: None)
        monkeypatch.setattr(f"{dm}._build_swing_state", lambda d, p, s: {"new_entries_today": 1})

    def test_exits_commission_opened_from_daily_entry(self, tmp_path, monkeypatch):
        from scripts.paper_trading.daily_metrics import build_daily_metrics

        cum_file = tmp_path / "cumulative_pnl.json"
        cum_file.write_text(
            json.dumps(
                {
                    "initial_capital": 100000,
                    "cumulative_pnl": -258.48,
                    "cumulative_pnl_pct": -0.26,
                    "trading_days": 10,
                    "daily_history": [
                        {
                            "date": "2026-06-02",
                            "pnl": 434.82,  # NET (broker realized, Option B)
                            "commission": 2.12,
                            "trades": 1,
                            "filled": 1,
                            "tp2_hits": 1,
                            "moc_exits": 0,
                        }
                    ],
                }
            )
        )
        self._patch_dirs(tmp_path, monkeypatch, cum_file)

        m = build_daily_metrics("2026-06-02")

        # exits derived from daily_history counters (NOT the empty trades CSV)
        assert m["exits"]["tp2"] == 1
        assert m["exits"]["moc"] == 0
        # commission + opened derived from daily entry + swing_state
        assert m["execution"]["commission_total"] == pytest.approx(2.12)
        assert m["positions"]["opened"] == 1
        # daily.pnl is NET; gross reconstructed as net + commission
        assert m["pnl"]["net"] == pytest.approx(434.82)
        assert m["pnl"]["gross"] == pytest.approx(436.94)
        assert m["pnl"]["commission"] == pytest.approx(2.12)

    def test_empty_when_no_daily_entry_and_no_trades(self, tmp_path, monkeypatch):
        from scripts.paper_trading.daily_metrics import build_daily_metrics

        cum_file = tmp_path / "cumulative_pnl.json"
        cum_file.write_text(json.dumps({"initial_capital": 100000, "daily_history": []}))
        self._patch_dirs(tmp_path, monkeypatch, cum_file)

        m = build_daily_metrics("2026-06-02")
        assert m["exits"]["tp2"] == 0
        assert m["positions"]["opened"] == 1  # swing_state new_entries_today
        assert m["pnl"]["net"] == pytest.approx(0.0)

    def test_exits_from_cumulative_even_when_trades_csv_present(self, tmp_path, monkeypatch):
        """Day 14 fix: cumulative counters win over an eod trades CSV.

        The 2026-06-03 incident: eod wrote a trades CSV labelling AKAM+ST TP1
        exits as MOC (and missing EOG), so the exits block showed moc:2. The
        recorder's cumulative daily_history (tp1_hits=2, moc_exits=1) is the
        authoritative source — build_daily_metrics must use it regardless of
        the CSV's presence/labels.
        """
        from scripts.paper_trading.daily_metrics import build_daily_metrics

        cum_file = tmp_path / "cumulative_pnl.json"
        cum_file.write_text(
            json.dumps(
                {
                    "initial_capital": 100000,
                    "cumulative_pnl": -43.92,
                    "cumulative_pnl_pct": -0.04,
                    "trading_days": 11,
                    "daily_history": [
                        {
                            "date": "2026-06-03",
                            "pnl": 229.84,
                            "commission": 3.22,
                            "trades": 3,
                            "filled": 3,
                            "tp1_hits": 2,
                            "moc_exits": 1,
                        }
                    ],
                }
            )
        )
        # eod-style trades CSV with the WRONG labels (all MOC, EOG missing)
        (tmp_path / "trades_2026-06-03.csv").write_text(
            "date,ticker,score,entry_price,exit_price,pnl,pnl_pct,exit_type,sector,commission\n"
            "2026-06-03,AKAM,0,146.59,156.0,75.30,6.4,MOC,Technology,1.03\n"
            "2026-06-03,ST,0,50.25,52.51,106.07,4.5,MOC,Technology,1.06\n"
        )
        self._patch_dirs(tmp_path, monkeypatch, cum_file)

        m = build_daily_metrics("2026-06-03")
        # exits from cumulative counters, NOT the CSV's moc:2
        assert m["exits"]["tp1"] == 2
        assert m["exits"]["moc"] == 1
        # P&L + commission from cumulative (net), gross = net + commission
        assert m["pnl"]["net"] == pytest.approx(229.84)
        assert m["pnl"]["commission"] == pytest.approx(3.22)
        assert m["pnl"]["gross"] == pytest.approx(233.06)


# ---------------------------------------------------------------------------
# Telegram-finomítás §1 — NYSE trading-day Day-N
# ---------------------------------------------------------------------------


class TestTradingDayNumber:
    """compute_trading_day_number = NYSE trading days in [start, target]."""

    def test_start_day_is_one(self):
        from scripts.paper_trading.daily_metrics import compute_trading_day_number

        assert compute_trading_day_number("2026-05-18", "2026-05-18") == 1

    def test_memorial_day_excluded(self):
        from scripts.paper_trading.daily_metrics import compute_trading_day_number

        # 5/18..6/1 = 5/18,19,20,21,22,(25 Memorial Day skip),26,27,28,29,6/1 = 10
        assert compute_trading_day_number("2026-06-01", "2026-05-18") == 10
        # 6/2 = 11
        assert compute_trading_day_number("2026-06-02", "2026-05-18") == 11

    def test_default_start_date(self):
        from scripts.paper_trading.daily_metrics import compute_trading_day_number

        assert compute_trading_day_number("2026-06-01") == 10  # default start 2026-05-18
