"""Tests for BC18A — EWMA score smoothing.

Covers:
- _ewma_score() pure function calculation
- No history (prev=None) → raw score returned
- EWMA state file load/save roundtrip
- EWMA disabled → scores unchanged
- EWMA enabled → scores smoothed
"""

import json
import os
from datetime import date, timedelta

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
    assert TUNING["ewma_enabled"] is False
    assert TUNING["ewma_span"] == 10
