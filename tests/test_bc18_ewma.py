"""Tests for BC18A — EWMA score smoothing.

Covers:
- _ewma_score() pure function calculation
- No history (prev=None) → raw score returned
- EWMA state file load/save roundtrip
- EWMA disabled → scores unchanged
- EWMA enabled → scores smoothed
- EWMA shadow log (per-ticker DEBUG + aggregated INFO)
"""

import json
import os
from datetime import date, timedelta
from unittest.mock import MagicMock, call

import pytest


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


def test_ewma_no_history():
    """No previous EWMA → returns current score unchanged."""
    from ifds.phases.phase6_sizing import _ewma_score
    assert _ewma_score(85.0, None, 10) == 85.0


def test_ewma_with_history():
    """EWMA calculation: α=2/11≈0.182, smoothed towards prev."""
    from ifds.phases.phase6_sizing import _ewma_score
    alpha = 2.0 / 11  # span=10
    expected = alpha * 85.0 + (1 - alpha) * 80.0
    result = _ewma_score(85.0, 80.0, 10)
    assert abs(result - expected) < 0.001
    assert abs(result - 80.909) < 0.01


def test_ewma_same_value():
    """Same current and prev → no change."""
    from ifds.phases.phase6_sizing import _ewma_score
    assert _ewma_score(80.0, 80.0, 10) == 80.0


def test_ewma_span_1_equals_current():
    """Span=1 → α=1.0 → returns current."""
    from ifds.phases.phase6_sizing import _ewma_score
    result = _ewma_score(85.0, 70.0, 1)
    assert result == 85.0


def test_ewma_large_span_sticky():
    """Large span → slow adaptation, result closer to prev."""
    from ifds.phases.phase6_sizing import _ewma_score
    result = _ewma_score(100.0, 50.0, 100)
    # α = 2/101 ≈ 0.0198, result ≈ 50.99
    assert result < 52.0


# ---------------------------------------------------------------------------
# State file tests
# ---------------------------------------------------------------------------


def test_load_ewma_no_file(tmp_path):
    """Missing file returns empty dict."""
    from ifds.phases.phase6_sizing import _load_ewma_scores
    result = _load_ewma_scores(str(tmp_path / "nonexistent.json"))
    assert result == {}


def test_save_load_ewma_roundtrip(tmp_path):
    """Save and load EWMA scores preserves data."""
    from ifds.phases.phase6_sizing import _save_ewma_scores, _load_ewma_scores
    path = str(tmp_path / "ewma.json")

    scores = {"AAPL": 85.5, "MSFT": 72.3}
    _save_ewma_scores(path, scores)

    # Simulate next day by modifying the date in the file
    with open(path) as f:
        data = json.load(f)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    data["date"] = yesterday
    with open(path, "w") as f:
        json.dump(data, f)

    loaded = _load_ewma_scores(path)
    assert loaded == scores


def test_load_ewma_same_day_returns_empty(tmp_path):
    """Same-day EWMA file returns empty (prevent double-application)."""
    from ifds.phases.phase6_sizing import _save_ewma_scores, _load_ewma_scores
    path = str(tmp_path / "ewma.json")

    _save_ewma_scores(path, {"AAPL": 85.5})
    loaded = _load_ewma_scores(path)
    assert loaded == {}  # Same day → don't reuse


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


def test_ewma_config_keys_exist():
    """EWMA config keys exist with defaults."""
    from ifds.config.defaults import TUNING
    assert "ewma_enabled" in TUNING
    assert "ewma_span" in TUNING
    assert TUNING["ewma_enabled"] is True
    assert TUNING["ewma_span"] == 10


# ---------------------------------------------------------------------------
# Shadow log tests (BC18 follow-up)
# ---------------------------------------------------------------------------


def _make_stock(ticker, combined_score=75.0):
    """Minimal StockAnalysis for EWMA log tests."""
    from ifds.models.market import (
        StockAnalysis, TechnicalAnalysis, FlowAnalysis, FundamentalScoring,
    )
    return StockAnalysis(
        ticker=ticker, sector="Technology",
        technical=TechnicalAnalysis(
            price=150.0, sma_200=140.0, sma_20=148.0,
            rsi_14=55.0, atr_14=3.0, trend_pass=True,
        ),
        flow=FlowAnalysis(rvol_score=0),
        fundamental=FundamentalScoring(funda_score=15, insider_multiplier=1.0),
        combined_score=combined_score,
    )


def _make_gex(ticker):
    """Minimal GEXAnalysis for EWMA log tests."""
    from ifds.models.market import GEXAnalysis, GEXRegime
    return GEXAnalysis(
        ticker=ticker, net_gex=500.0, call_wall=0.0, put_wall=0.0,
        zero_gamma=140.0, current_price=150.0,
        gex_regime=GEXRegime.POSITIVE, gex_multiplier=1.0,
    )


def _setup_ewma_run(tmp_path, monkeypatch, prev_scores=None):
    """Set up config + EWMA state for log tests. Returns (config, logger_mock)."""
    from ifds.config.loader import Config
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    c = Config()
    c.tuning["ewma_enabled"] = True
    c.tuning["ewma_span"] = 10
    c.runtime["ewma_scores_file"] = str(tmp_path / "ewma.json")
    c.runtime["daily_trades_file"] = str(tmp_path / "daily_trades.json")
    c.runtime["daily_notional_file"] = str(tmp_path / "daily_notional.json")

    # Write previous EWMA state (simulating yesterday's run)
    if prev_scores:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        ewma_data = {"date": yesterday, "scores": prev_scores}
        with open(tmp_path / "ewma.json", "w") as f:
            json.dump(ewma_data, f)

    logger_mock = MagicMock()
    return c, logger_mock


def test_ewma_log_per_ticker_debug(tmp_path, monkeypatch):
    """Per-ticker DEBUG log shows raw, ewma, prev, and delta."""
    from ifds.phases.phase6_sizing import run_phase6
    from ifds.models.market import MacroRegime, MarketVolatilityRegime, StrategyMode

    config, logger = _setup_ewma_run(
        tmp_path, monkeypatch,
        prev_scores={"AAPL": 80.0, "MSFT": 70.0},
    )
    macro = MacroRegime(
        vix_value=18.0, vix_regime=MarketVolatilityRegime.NORMAL,
        vix_multiplier=1.0, tnx_value=4.2, tnx_sma20=4.1,
        tnx_rate_sensitive=False,
    )
    stocks = [_make_stock("AAPL", 85.0), _make_stock("MSFT", 75.0)]
    gex = [_make_gex("AAPL"), _make_gex("MSFT")]

    run_phase6(config, logger, stocks, gex, macro, StrategyMode.LONG)

    # Find per-ticker DEBUG log calls
    debug_calls = [
        c for c in logger.log.call_args_list
        if len(c.args) >= 2 and "[EWMA]" in str(c.kwargs.get("message", ""))
        and "tickers smoothed" not in str(c.kwargs.get("message", ""))
    ]
    assert len(debug_calls) == 2
    messages = [c.kwargs["message"] for c in debug_calls]
    # Check structure: ticker, raw=, ewma=, prev=, delta= present
    assert any("AAPL" in m and "raw=" in m and "prev=80.0" in m and "delta=" in m for m in messages)
    assert any("MSFT" in m and "raw=" in m and "prev=70.0" in m and "delta=" in m for m in messages)


def test_ewma_log_aggregated_info(tmp_path, monkeypatch):
    """Aggregated INFO log shows count, avg delta, max delta."""
    from ifds.phases.phase6_sizing import run_phase6
    from ifds.models.market import MacroRegime, MarketVolatilityRegime, StrategyMode

    config, logger = _setup_ewma_run(
        tmp_path, monkeypatch,
        prev_scores={"AAPL": 80.0, "MSFT": 70.0},
    )
    macro = MacroRegime(
        vix_value=18.0, vix_regime=MarketVolatilityRegime.NORMAL,
        vix_multiplier=1.0, tnx_value=4.2, tnx_sma20=4.1,
        tnx_rate_sensitive=False,
    )
    stocks = [_make_stock("AAPL", 85.0), _make_stock("MSFT", 75.0), _make_stock("GOOG", 90.0)]
    gex = [_make_gex("AAPL"), _make_gex("MSFT"), _make_gex("GOOG")]

    run_phase6(config, logger, stocks, gex, macro, StrategyMode.LONG)

    # Find aggregated INFO log
    info_calls = [
        c for c in logger.log.call_args_list
        if "[EWMA]" in str(c.kwargs.get("message", ""))
        and "tickers smoothed" in str(c.kwargs.get("message", ""))
    ]
    assert len(info_calls) == 1
    msg = info_calls[0].kwargs["message"]
    assert "2/3 tickers smoothed" in msg  # AAPL + MSFT have prev, GOOG doesn't
    assert "avg delta=" in msg
    assert "max delta=" in msg


def test_ewma_log_no_prev_no_log(tmp_path, monkeypatch):
    """No previous EWMA state → no per-ticker log, no aggregated log."""
    from ifds.phases.phase6_sizing import run_phase6
    from ifds.models.market import MacroRegime, MarketVolatilityRegime, StrategyMode

    config, logger = _setup_ewma_run(tmp_path, monkeypatch, prev_scores=None)
    macro = MacroRegime(
        vix_value=18.0, vix_regime=MarketVolatilityRegime.NORMAL,
        vix_multiplier=1.0, tnx_value=4.2, tnx_sma20=4.1,
        tnx_rate_sensitive=False,
    )
    stocks = [_make_stock("AAPL", 85.0)]
    gex = [_make_gex("AAPL")]

    run_phase6(config, logger, stocks, gex, macro, StrategyMode.LONG)

    ewma_calls = [
        c for c in logger.log.call_args_list
        if "[EWMA]" in str(c.kwargs.get("message", ""))
    ]
    assert len(ewma_calls) == 0


def test_ewma_phase_complete_includes_ewma_data(tmp_path, monkeypatch):
    """PHASE_COMPLETE data dict includes ewma_applied and ewma_avg_delta."""
    from ifds.phases.phase6_sizing import run_phase6
    from ifds.models.market import MacroRegime, MarketVolatilityRegime, StrategyMode
    from ifds.events.types import EventType

    config, logger = _setup_ewma_run(
        tmp_path, monkeypatch,
        prev_scores={"AAPL": 80.0},
    )
    macro = MacroRegime(
        vix_value=18.0, vix_regime=MarketVolatilityRegime.NORMAL,
        vix_multiplier=1.0, tnx_value=4.2, tnx_sma20=4.1,
        tnx_rate_sensitive=False,
    )
    stocks = [_make_stock("AAPL", 85.0)]
    gex = [_make_gex("AAPL")]

    run_phase6(config, logger, stocks, gex, macro, StrategyMode.LONG)

    complete_calls = [
        c for c in logger.log.call_args_list
        if len(c.args) >= 1 and c.args[0] == EventType.PHASE_COMPLETE
    ]
    assert len(complete_calls) == 1
    data = complete_calls[0].kwargs.get("data", {})
    assert "ewma_applied" in data
    assert data["ewma_applied"] == 1
    assert "ewma_avg_delta" in data
