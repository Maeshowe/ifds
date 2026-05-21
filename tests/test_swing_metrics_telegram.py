"""Tests — Task #5 swing daily metrics + compact Telegram template."""

from __future__ import annotations

from ifds.output.swing_telegram import format_swing_compact_telegram


def _base_metrics(**overrides) -> dict:
    base = {
        "date": "2026-05-19",
        "day_number": 1,
        "pnl": {"net": 0.0, "gross": 0.0, "cumulative": 0.0, "cumulative_pct": 0.0},
        "market": {"vix_close": 18.5, "vix_delta_pct": 2.1, "spy_return_pct": 0.5},
        "swing_state": {
            "open_positions": 0,
            "max_concurrent": 12,
            "new_entries_today": 0,
            "new_entries_tickers": [],
            "total_notional": 0.0,
            "sector_distribution": {},
            "sector_observed_max_pct": 0.0,
            "sector_cap_pct": 30.0,
            "avg_days_held": 0.0,
            "max_days_held": 0,
            "exits_today": {},
            "next_day_planned": {"exits_at_1530": [], "time_stops_at_2140": []},
            "swing_score_distribution": {
                "qualifying_threshold_50": 0,
                "selected_for_entry": 0,
                "top_3_scores": [],
            },
        },
        "uw_shadow_summary": {},
    }
    for k, v in overrides.items():
        base[k] = v
    return base


def test_telegram_template_compact_format():
    """Compact Telegram template < 800 chars (mobile-friendly)."""
    metrics = _base_metrics(
        swing_state={
            **_base_metrics()["swing_state"],
            "open_positions": 8,
            "new_entries_today": 2,
            "new_entries_tickers": ["NVDA", "JPM"],
            "exits_today": {"TP1": 1, "MENTAL_SL": 1, "TIME_STOP": 1},
            "next_day_planned": {
                "exits_at_1530": ["AAPL_TP1", "MSFT_MENTAL_SL"],
                "time_stops_at_2140": [],
            },
            "swing_score_distribution": {
                "qualifying_threshold_50": 173,
                "selected_for_entry": 2,
                "top_3_scores": [
                    {"ticker": "NVDA", "S_j": 78.4, "sector": "XLK"},
                    {"ticker": "JPM", "S_j": 71.8, "sector": "XLF"},
                    {"ticker": "XOM", "S_j": 68.2, "sector": "XLE"},
                ],
            },
        },
    )
    output = format_swing_compact_telegram(metrics)
    assert len(output) < 800, f"Telegram body too long: {len(output)} chars"
    assert "Day 1" in output and "NVDA" in output and "MENTAL_SL" in output


def test_telegram_template_renders_zero_entries():
    """Zero entries / exits → 'Új entry today: 0' és 'Triggered exits: 0'."""
    metrics = _base_metrics()
    out = format_swing_compact_telegram(metrics)
    assert "Új entry today:  0" in out
    assert "Triggered exits: 0" in out


def test_telegram_template_pnl_block_with_unrealized():
    """Task #T §3.4: realized + unrealized + cumulative séparálva."""
    metrics = _base_metrics(
        pnl={
            "net": 84.0,
            "gross": 84.0,
            "cumulative": 219.0,
            "cumulative_pct": 0.219,
            "unrealized": 105.09,
            "closed_trades_today": 1,
            "circuit_breaker_threshold": -5000.0,
        }
    )
    out = format_swing_compact_telegram(metrics)
    assert "Realized today:   $+84.00" in out
    assert "(1 closed)" in out
    assert "Unrealized:" in out
    assert "+105.09" in out
    assert "Cumulative:       $+219" in out


def test_telegram_template_sector_breakdown_when_open():
    """Open positions present → sector breakdown sor."""
    swing = _base_metrics()["swing_state"]
    swing["open_positions"] = 3
    swing["total_notional"] = 23570.0
    swing["total_notional_pct_equity"] = 23.57
    swing["sector_distribution"] = {"Energy": 8575.0, "Healthcare": 14995.0}
    metrics = _base_metrics(swing_state=swing)
    out = format_swing_compact_telegram(metrics)
    assert "Open book:" in out and "23,570" in out
    assert "Sectors:" in out
    assert "Healthcare 15.0%" in out
    assert "Energy 8.6%" in out


def test_telegram_template_cb_buffer_safe():
    """Pozitív cumulative → CB buffer = 100%+ (alatta a -5k küszöbnek)."""
    metrics = _base_metrics(
        pnl={
            "net": 0,
            "gross": 0,
            "cumulative": 200.0,
            "cumulative_pct": 0.2,
            "circuit_breaker_threshold": -5000.0,
        }
    )
    out = format_swing_compact_telegram(metrics)
    assert "CB buffer:" in out
    assert "$+200 / $-5,000" in out


def test_telegram_template_cb_triggered():
    """Cumulative < -5k → CIRCUIT BREAKER TRIGGERED."""
    metrics = _base_metrics(
        pnl={
            "net": -500,
            "gross": -500,
            "cumulative": -5200.0,
            "cumulative_pct": -5.2,
            "circuit_breaker_threshold": -5000.0,
        }
    )
    out = format_swing_compact_telegram(metrics)
    assert "CIRCUIT BREAKER" in out and "TRIGGERED" in out


def test_telegram_template_renders_max_entries():
    """3 új entry + 12/12 cap → nincs overflow, helyes formátum."""
    swing = _base_metrics()["swing_state"]
    swing["open_positions"] = 12
    swing["max_concurrent"] = 12
    swing["new_entries_today"] = 3
    swing["new_entries_tickers"] = ["NVDA", "JPM", "XOM"]
    metrics = _base_metrics(swing_state=swing)
    out = format_swing_compact_telegram(metrics)
    assert "12 nyitva / 12 cap" in out
    assert "3 (NVDA, JPM, XOM)" in out
    assert len(out) < 800


def test_telegram_template_omits_top_scores_when_empty():
    """Üres top_3_scores → 'Top S_j today' section nincs."""
    metrics = _base_metrics()
    out = format_swing_compact_telegram(metrics)
    assert "Top S_j today" not in out


def test_daily_metrics_sector_distribution_sums_to_total(tmp_path, monkeypatch):
    """A `_build_swing_state` sector_distribution értékösszege = total_notional."""
    # Set up a fake swing_positions.json
    from ifds.state.swing_positions import SwingPosition, save_swing_positions

    state_file = tmp_path / "swing.json"
    save_swing_positions(
        state_file,
        [
            SwingPosition(
                ticker="A",
                entry_date="2026-05-19",
                entry_price=100.0,
                atr=2.0,
                stop_level=96.0,
                tp1_level=103.0,
                tp2_level=106.0,
                qty=50,
                qty_remaining=50,
                sector="XLK",
            ),
            SwingPosition(
                ticker="B",
                entry_date="2026-05-19",
                entry_price=200.0,
                atr=4.0,
                stop_level=192.0,
                tp1_level=206.0,
                tp2_level=212.0,
                qty=20,
                qty_remaining=20,
                sector="XLF",
            ),
        ],
    )

    # Monkey-patch Config to point at the temp state file
    import sys as _sys

    _sys.path.insert(0, "scripts/paper_trading")
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "daily_metrics",
        "scripts/paper_trading/daily_metrics.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class FakeCfg:
        tuning = {
            "swing_positions_state_file": str(state_file),
            "swing_max_concurrent": 12,
            "swing_score_threshold": 50.0,
        }
        runtime = {"account_equity": 100_000.0}

    def _fake_config():
        return FakeCfg()

    import ifds.config.loader as _loader

    monkeypatch.setattr(_loader, "Config", _fake_config)

    swing_state = mod._build_swing_state("2026-05-19", planned={}, snapshot=[])

    # Σ sector_distribution should equal total_notional
    assert swing_state["total_notional"] == 100.0 * 50 + 200.0 * 20  # 5000 + 4000 = 9000
    sd_sum = sum(swing_state["sector_distribution"].values())
    assert sd_sum == swing_state["total_notional"]
    assert swing_state["new_entries_today"] == 2
    assert set(swing_state["new_entries_tickers"]) == {"A", "B"}


def test_daily_metrics_swing_state_snapshot_dict_shape(tmp_path, monkeypatch):
    """Phase 4 snapshot arrives as {ticker: data} from _load_phase4_snapshot.

    Regression: an earlier version iterated the dict's keys (strings) and
    crashed with ``'str' object has no attribute 'get'`` at 22:10 CEST on
    Day 1. Fixed by detecting dict-shaped snapshot and pulling ``.values()``.
    """
    import sys as _sys

    _sys.path.insert(0, "scripts/paper_trading")
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "daily_metrics",
        "scripts/paper_trading/daily_metrics.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class FakeCfg:
        tuning = {
            "swing_positions_state_file": str(tmp_path / "absent.json"),
            "swing_max_concurrent": 12,
            "swing_score_threshold": 50.0,
        }
        runtime = {"account_equity": 100_000.0}

    import ifds.config.loader as _loader

    monkeypatch.setattr(_loader, "Config", lambda: FakeCfg())

    # The production shape: {ticker: row_dict}
    snapshot_dict = {
        "AAPL": {"ticker": "AAPL", "combined_score": 82.5, "sector": "Technology"},
        "MSFT": {"ticker": "MSFT", "combined_score": 71.0, "sector": "Technology"},
        "TSLA": {"ticker": "TSLA", "combined_score": 45.0, "sector": "Consumer Cyclical"},
    }

    swing_state = mod._build_swing_state("2026-05-19", planned={}, snapshot=snapshot_dict)

    top = swing_state["swing_score_distribution"]["top_3_scores"]
    assert [t["ticker"] for t in top] == ["AAPL", "MSFT", "TSLA"]
    # Only AAPL and MSFT pass threshold 50.0
    assert swing_state["swing_score_distribution"]["qualifying_threshold_50"] == 2


def test_daily_metrics_swing_state_empty_state(tmp_path, monkeypatch):
    """No swing state file → swing_state has zero fields, no crash."""
    import sys as _sys

    _sys.path.insert(0, "scripts/paper_trading")
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "daily_metrics",
        "scripts/paper_trading/daily_metrics.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class FakeCfg:
        tuning = {
            "swing_positions_state_file": str(tmp_path / "absent.json"),
            "swing_max_concurrent": 12,
            "swing_score_threshold": 50.0,
        }
        runtime = {"account_equity": 100_000.0}

    import ifds.config.loader as _loader

    monkeypatch.setattr(_loader, "Config", lambda: FakeCfg())

    swing_state = mod._build_swing_state("2026-05-19", planned={}, snapshot=[])

    assert swing_state["open_positions"] == 0
    assert swing_state["total_notional"] == 0.0
    assert swing_state["sector_distribution"] == {}
    assert swing_state["new_entries_today"] == 0


# ---------------------------------------------------------------------------
# Task #T §3.3 — pt_monitor EOD Telegram formatter
# ---------------------------------------------------------------------------

from datetime import date as _date
from ifds.output.swing_telegram import format_pt_monitor_eod_telegram
from ifds.state.swing_positions import SwingPosition as _SwingPos


def _pos(ticker, sector="Energy", qty_remaining=100, entry_price=10.0, days_held=0):
    return _SwingPos(
        ticker=ticker,
        entry_date="2026-05-18",
        entry_price=entry_price,
        atr=1.0,
        stop_level=entry_price - 2.0,
        tp1_level=entry_price + 1.5,
        tp2_level=entry_price + 3.0,
        qty=qty_remaining,
        qty_remaining=qty_remaining,
        sector=sector,
        days_held=days_held,
    )


def test_pt_monitor_telegram_with_3_positions_1_tp1():
    """3 nyitott pozíció, 1 TP1 flag → eval rows + sectors + market context."""
    positions = [
        _pos("EC", sector="Energy", qty_remaining=332, entry_price=13.08),
        _pos("LBRT", sector="Energy", qty_remaining=127, entry_price=33.34),
        _pos("MASI", sector="Healthcare", qty_remaining=84, entry_price=178.51),
    ]
    ohlc = {
        "EC": {"close": 13.59, "high": 13.86, "low": 13.05, "open": 13.10},
        "LBRT": {"close": 33.30, "high": 33.40, "low": 33.10, "open": 33.20},
        "MASI": {"close": 178.65, "high": 178.95, "low": 178.40, "open": 178.50},
    }
    exits = [("EC", "TP1")]
    out = format_pt_monitor_eod_telegram(
        positions,
        ohlc,
        exits,
        _date(2026, 5, 18),
        day_number=1,
        market={"vix_close": 18.54, "vix_delta_pct": 2.3, "spy_return_pct": -0.07},
    )
    assert "Day 1/63" in out
    assert "EC" in out and "TP1" in out and "✅" in out
    assert "LBRT" in out and "⏸" in out
    assert "Energy" in out and "Healthcare" in out
    assert "VIX 18.5" in out and "SPY -0.07%" in out


def test_pt_monitor_telegram_zero_open_positions():
    """0 nyitott → 'no open positions' fallback."""
    out = format_pt_monitor_eod_telegram(
        [],
        {},
        [],
        _date(2026, 5, 18),
        day_number=10,
    )
    assert "no open positions" in out


def test_pt_monitor_telegram_timestop_countdown():
    """days_held >= max_hold - 2 → time-stop countdown sor."""
    positions = [
        _pos("OLDPOS", qty_remaining=50, days_held=4),  # 1 day left
        _pos("NEWPOS", qty_remaining=30, days_held=0),  # 5 days left
    ]
    ohlc = {
        "OLDPOS": {"close": 11.0, "high": 11.0, "low": 10.0, "open": 10.5},
        "NEWPOS": {"close": 11.0, "high": 11.0, "low": 10.0, "open": 10.5},
    }
    out = format_pt_monitor_eod_telegram(
        positions,
        ohlc,
        [],
        _date(2026, 5, 22),
        max_hold_days=5,
    )
    assert "Time-stops:" in out
    assert "OLDPOS" in out and "1 day" in out
    # NEWPOS has 5 days left → NOT in countdown section
    assert out.count("NEWPOS") == 1  # only in EOD eval, not in time-stops


def test_pt_monitor_telegram_no_market_context_when_absent():
    """market=None → nincs VIX/SPY sor."""
    pos = [_pos("EC", sector="Energy", entry_price=13.08)]
    out = format_pt_monitor_eod_telegram(
        pos,
        {"EC": {"close": 13.5, "high": 13.6, "low": 13.0, "open": 13.1}},
        [],
        _date(2026, 5, 18),
        market=None,
    )
    assert "VIX" not in out and "SPY" not in out


# ---------------------------------------------------------------------------
# Task #T §3.1 — Trading Plan exec_table OPEN/NEW status column
# ---------------------------------------------------------------------------


def test_trading_plan_telegram_distinguishes_open_vs_new():
    """A _format_exec_table existing_swing_tickers param → OPEN/NEW status."""
    from ifds.output.telegram import _format_exec_table
    from ifds.models.market import PositionSizing

    positions = [
        PositionSizing(
            ticker="LBRT",
            sector="Energy",
            direction="BUY",
            entry_price=33.07,
            quantity=124,
            stop_loss=30.27,
            take_profit_1=35.17,
            take_profit_2=37.27,
            risk_usd=347.0,
            combined_score=101.7,
            gex_regime="positive",
            multiplier_total=1.0,
            mm_regime="undetermined",
        ),
        PositionSizing(
            ticker="PFGC",
            sector="Consumer Defensive",
            direction="BUY",
            entry_price=96.14,
            quantity=57,
            stop_loss=90.02,
            take_profit_1=100.73,
            take_profit_2=105.32,
            risk_usd=349.0,
            combined_score=92.0,
            gex_regime="positive",
            multiplier_total=1.0,
            mm_regime="undetermined",
        ),
    ]
    existing = {"LBRT", "MASI", "EC"}  # LBRT in swing state, PFGC is new

    out = _format_exec_table(positions, existing_swing_tickers=existing)
    assert "STATUS" in out
    # LBRT row should contain "OPEN", PFGC row should contain "NEW"
    lbrt_line = [l for l in out.split("\n") if l.startswith("LBRT")][0]
    pfgc_line = [l for l in out.split("\n") if l.startswith("PFGC")][0]
    assert "OPEN" in lbrt_line
    assert "NEW" in pfgc_line and "OPEN" not in pfgc_line


def test_trading_plan_exec_table_without_swing_state_no_status_column():
    """Ha existing_swing_tickers=None → STATUS oszlop nincs (legacy mode)."""
    from ifds.output.telegram import _format_exec_table
    from ifds.models.market import PositionSizing

    positions = [
        PositionSizing(
            ticker="LBRT",
            sector="Energy",
            direction="BUY",
            entry_price=33.07,
            quantity=124,
            stop_loss=30.27,
            take_profit_1=35.17,
            take_profit_2=37.27,
            risk_usd=347.0,
            combined_score=101.7,
            gex_regime="positive",
            multiplier_total=1.0,
            mm_regime="undetermined",
        ),
    ]
    out = _format_exec_table(positions, existing_swing_tickers=None)
    assert "STATUS" not in out
