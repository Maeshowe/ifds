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
            "sector_max_pct": 0.0,
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
    """Zero entries / exits → 'Új entry today: 0' és 'Exit today: 0'."""
    metrics = _base_metrics()
    out = format_swing_compact_telegram(metrics)
    assert "Új entry today:  0" in out
    assert "Exit today:      0" in out


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
    save_swing_positions(state_file, [
        SwingPosition(
            ticker="A", entry_date="2026-05-19", entry_price=100.0, atr=2.0,
            stop_level=96.0, tp1_level=103.0, tp2_level=106.0,
            qty=50, qty_remaining=50, sector="XLK",
        ),
        SwingPosition(
            ticker="B", entry_date="2026-05-19", entry_price=200.0, atr=4.0,
            stop_level=192.0, tp1_level=206.0, tp2_level=212.0,
            qty=20, qty_remaining=20, sector="XLF",
        ),
    ])

    # Monkey-patch Config to point at the temp state file
    import sys as _sys
    _sys.path.insert(0, "scripts/paper_trading")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "daily_metrics", "scripts/paper_trading/daily_metrics.py",
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


def test_daily_metrics_swing_state_empty_state(tmp_path, monkeypatch):
    """No swing state file → swing_state has zero fields, no crash."""
    import sys as _sys
    _sys.path.insert(0, "scripts/paper_trading")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "daily_metrics", "scripts/paper_trading/daily_metrics.py",
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
