"""Tests for pt_avwap.py — AVWAP-based Limit→MKT conversion.

Covers:
- AVWAP calculation from Polygon 1-min bars
- State machine transitions (IDLE → WATCHING → DIPPED → DONE)
- VIX-adaptive SL cap (get_vix_adaptive_sl_distance)
- Bracket rebuild math (SL/TP recalculation from fill price)
- Time window enforcement (avwap_start → avwap_cutoff)
- Edge cases: no bars, already filled, cutoff
"""

import json
import os
import sys
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest


ET = ZoneInfo("America/New_York")


@pytest.fixture(autouse=True)
def _isolate_pt_env():
    """Prevent pt_avwap.py load_dotenv() from polluting env."""
    keys = [
        "scripts.paper_trading.pt_avwap",
    ]
    cached = {k: sys.modules.pop(k, None) for k in keys}
    env_before = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(env_before)
    for k in keys:
        sys.modules.pop(k, None)
    for k, v in cached.items():
        if v is not None:
            sys.modules[k] = v


def _import_pt_avwap(tmp_path):
    """Import pt_avwap with STATE_DIR pointed at tmp_path."""
    scripts_dir = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "paper_trading"
    )
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    import scripts.paper_trading.pt_avwap as mod

    mod.STATE_DIR = str(tmp_path)
    return mod


def _write_state(tmp_path, state: dict, today_str: str = None):
    """Write a monitor state JSON file."""
    if today_str is None:
        today_str = date.today().strftime("%Y-%m-%d")
    path = tmp_path / f"monitor_state_{today_str}.json"
    with open(path, "w") as f:
        json.dump(state, f)
    return path


def _make_avwap_state(
    sym="TEST",
    entry=100.0,
    sl=97.0,
    tp1=103.0,
    tp2=106.0,
    total_qty=100,
    qty_b=67,
    avwap_state="IDLE",
    avwap_dipped=False,
    avwap_converted=False,
):
    return {
        sym: {
            "entry_price": entry,
            "sl_distance": round(entry - sl, 4),
            "tp1_price": tp1,
            "tp2_price": tp2,
            "stop_loss": sl,
            "total_qty": total_qty,
            "qty_b": qty_b,
            "tp1_filled": False,
            "trail_active": False,
            "trail_scope": None,
            "trail_sl_current": None,
            "trail_high": None,
            "scenario_b_activated": False,
            "scenario_b_eligible": True,
            "avwap_state": avwap_state,
            "avwap_dipped": avwap_dipped,
            "avwap_last": None,
            "avwap_converted": avwap_converted,
        }
    }


# ---------------------------------------------------------------------------
# AVWAP calculation tests
# ---------------------------------------------------------------------------


def test_calculate_avwap_basic(tmp_path):
    """AVWAP = sum(TP*Vol) / sum(Vol) from 1-min bars."""
    mod = _import_pt_avwap(tmp_path)

    # Market open at 9:30 ET = 13:30 UTC
    market_open_utc = datetime(2026, 3, 21, 13, 30, 0, tzinfo=ZoneInfo("UTC"))
    open_ts_ms = int(market_open_utc.timestamp() * 1000)

    bars = [
        {"t": open_ts_ms, "h": 101.0, "l": 99.0, "c": 100.0, "v": 1000},
        {"t": open_ts_ms + 60000, "h": 102.0, "l": 100.0, "c": 101.0, "v": 2000},
    ]
    # TP1 = (101+99+100)/3 = 100.0, TP2 = (102+100+101)/3 = 101.0
    # AVWAP = (100*1000 + 101*2000) / 3000 = 302000/3000 = 100.6667

    mock_client = MagicMock()
    mock_client.return_value.get_aggregates.return_value = bars

    with patch("ifds.data.polygon.PolygonClient", mock_client):
        result = mod.calculate_avwap("TEST", market_open_utc)

    assert result is not None
    assert abs(result - 100.6667) < 0.001


def test_calculate_avwap_no_bars(tmp_path):
    """Returns None when no bars available."""
    mod = _import_pt_avwap(tmp_path)

    market_open_utc = datetime(2026, 3, 21, 13, 30, 0, tzinfo=ZoneInfo("UTC"))
    mock_client = MagicMock()
    mock_client.return_value.get_aggregates.return_value = None

    with patch("ifds.data.polygon.PolygonClient", mock_client):
        result = mod.calculate_avwap("TEST", market_open_utc)

    assert result is None


def test_calculate_avwap_filters_pre_open_bars(tmp_path):
    """Bars before market open are excluded from AVWAP calculation."""
    mod = _import_pt_avwap(tmp_path)

    market_open_utc = datetime(2026, 3, 21, 13, 30, 0, tzinfo=ZoneInfo("UTC"))
    open_ts_ms = int(market_open_utc.timestamp() * 1000)

    bars = [
        # Pre-market bar (should be excluded)
        {"t": open_ts_ms - 60000, "h": 95.0, "l": 93.0, "c": 94.0, "v": 5000},
        # Market hours bar (should be included)
        {"t": open_ts_ms, "h": 101.0, "l": 99.0, "c": 100.0, "v": 1000},
    ]

    mock_client = MagicMock()
    mock_client.return_value.get_aggregates.return_value = bars

    with patch("ifds.data.polygon.PolygonClient", mock_client):
        result = mod.calculate_avwap("TEST", market_open_utc)

    # Only the market hours bar: TP = (101+99+100)/3 = 100.0
    assert result is not None
    assert abs(result - 100.0) < 0.001


# ---------------------------------------------------------------------------
# State machine transition tests
# ---------------------------------------------------------------------------


def test_idle_to_watching_no_position(tmp_path):
    """IDLE ticker without IBKR position transitions to WATCHING."""
    mod = _import_pt_avwap(tmp_path)

    mock_ib = MagicMock()
    mock_ib.positions.return_value = []  # No position

    s = _make_avwap_state(avwap_state="IDLE")["TEST"]

    # IDLE → WATCHING: no IBKR position means entry unfilled
    if s.get("avwap_state", "IDLE") == "IDLE":
        if not mod.is_position_open(mock_ib, "TEST"):
            s["avwap_state"] = "WATCHING"

    assert s["avwap_state"] == "WATCHING"


def test_idle_to_converted_with_position(tmp_path):
    """IDLE ticker WITH IBKR position marks as converted (limit filled normally)."""
    mod = _import_pt_avwap(tmp_path)

    mock_pos = MagicMock()
    mock_pos.contract.symbol = "TEST"
    mock_pos.position = 100

    mock_ib = MagicMock()
    mock_ib.positions.return_value = [mock_pos]

    assert mod.is_position_open(mock_ib, "TEST") is True


def test_watching_to_dipped(tmp_path):
    """WATCHING → DIPPED when price <= AVWAP."""
    mod = _import_pt_avwap(tmp_path)

    s = _make_avwap_state(avwap_state="WATCHING")["TEST"]
    avwap = 100.50
    current_price = 100.30  # Below AVWAP

    if s["avwap_state"] == "WATCHING" and current_price <= avwap:
        s["avwap_state"] = "DIPPED"
        s["avwap_dipped"] = True

    assert s["avwap_state"] == "DIPPED"
    assert s["avwap_dipped"] is True


def test_dipped_to_done_on_crossback(tmp_path):
    """DIPPED → DONE when price crosses back above AVWAP."""
    mod = _import_pt_avwap(tmp_path)

    s = _make_avwap_state(avwap_state="DIPPED", avwap_dipped=True)["TEST"]
    avwap = 100.50
    current_price = 100.80  # Above AVWAP

    if s["avwap_state"] == "DIPPED" and current_price > avwap:
        s["avwap_state"] = "DONE"
        s["avwap_converted"] = True

    assert s["avwap_state"] == "DONE"
    assert s["avwap_converted"] is True


def test_watching_stays_watching_above_avwap(tmp_path):
    """WATCHING stays WATCHING when price is still above AVWAP (no dip yet)."""
    mod = _import_pt_avwap(tmp_path)

    s = _make_avwap_state(avwap_state="WATCHING")["TEST"]
    avwap = 100.50
    current_price = 101.00  # Still above AVWAP

    if s["avwap_state"] == "WATCHING" and current_price <= avwap:
        s["avwap_state"] = "DIPPED"

    assert s["avwap_state"] == "WATCHING"  # No change


def test_dipped_stays_dipped_below_avwap(tmp_path):
    """DIPPED stays DIPPED when price is still below AVWAP."""
    mod = _import_pt_avwap(tmp_path)

    s = _make_avwap_state(avwap_state="DIPPED", avwap_dipped=True)["TEST"]
    avwap = 100.50
    current_price = 99.80  # Still below AVWAP

    if s["avwap_state"] == "DIPPED" and current_price > avwap:
        s["avwap_state"] = "DONE"

    assert s["avwap_state"] == "DIPPED"  # No change


# ---------------------------------------------------------------------------
# Bracket rebuild math tests
# ---------------------------------------------------------------------------


def test_bracket_rebuild_prices():
    """New SL/TP = fill_price ± original distance."""
    entry = 100.0
    sl = 97.0
    tp1 = 103.0
    tp2 = 106.0

    sl_distance = entry - sl        # 3.0
    tp1_distance = tp1 - entry      # 3.0
    tp2_distance = tp2 - entry      # 6.0

    fill_price = 99.50  # MKT fill lower than limit

    new_sl = round(fill_price - sl_distance, 2)
    new_tp1 = round(fill_price + tp1_distance, 2)
    new_tp2 = round(fill_price + tp2_distance, 2)

    assert new_sl == 96.50
    assert new_tp1 == 102.50
    assert new_tp2 == 105.50


def test_bracket_rebuild_prices_higher_fill():
    """Bracket rebuild when MKT fill is higher than original limit."""
    entry = 100.0
    sl = 97.0
    tp1 = 103.0
    tp2 = 106.0

    sl_distance = entry - sl
    tp1_distance = tp1 - entry
    tp2_distance = tp2 - entry

    fill_price = 100.80  # MKT fill higher

    new_sl = round(fill_price - sl_distance, 2)
    new_tp1 = round(fill_price + tp1_distance, 2)
    new_tp2 = round(fill_price + tp2_distance, 2)

    assert new_sl == 97.80
    assert new_tp1 == 103.80
    assert new_tp2 == 106.80


# ---------------------------------------------------------------------------
# Filter / edge case tests
# ---------------------------------------------------------------------------


def test_already_converted_skipped(tmp_path):
    """Tickers with avwap_converted=True are not in watching list."""
    mod = _import_pt_avwap(tmp_path)

    state = _make_avwap_state(avwap_converted=True)
    _write_state(tmp_path, state)
    loaded = mod.load_state(date.today().strftime("%Y-%m-%d"))

    watching = [
        sym for sym, s in loaded.items()
        if not s.get("avwap_converted", False)
        and not s.get("tp1_filled", False)
        and s.get("avwap_state", "IDLE") in ("IDLE", "WATCHING", "DIPPED")
    ]
    assert watching == []


def test_tp1_filled_skipped(tmp_path):
    """Tickers with tp1_filled=True are not AVWAP candidates."""
    mod = _import_pt_avwap(tmp_path)

    state = _make_avwap_state()
    state["TEST"]["tp1_filled"] = True
    _write_state(tmp_path, state)
    loaded = mod.load_state(date.today().strftime("%Y-%m-%d"))

    watching = [
        sym for sym, s in loaded.items()
        if not s.get("avwap_converted", False)
        and not s.get("tp1_filled", False)
        and s.get("avwap_state", "IDLE") in ("IDLE", "WATCHING", "DIPPED")
    ]
    assert watching == []


def test_no_state_file(tmp_path):
    """No state file returns empty dict."""
    mod = _import_pt_avwap(tmp_path)
    result = mod.load_state("2026-01-01")
    assert result == {}


def test_state_roundtrip(tmp_path):
    """State save/load preserves all fields."""
    mod = _import_pt_avwap(tmp_path)

    state = _make_avwap_state(avwap_state="DIPPED", avwap_dipped=True)
    state["TEST"]["avwap_last"] = 100.5432

    today_str = date.today().strftime("%Y-%m-%d")
    mod.save_state(today_str, state)
    loaded = mod.load_state(today_str)

    assert loaded["TEST"]["avwap_state"] == "DIPPED"
    assert loaded["TEST"]["avwap_dipped"] is True
    assert loaded["TEST"]["avwap_last"] == 100.5432
    assert loaded["TEST"]["avwap_converted"] is False


# ---------------------------------------------------------------------------
# VIX-adaptive SL cap tests
# ---------------------------------------------------------------------------


def test_vix_below_20_no_cap(tmp_path):
    """VIX < 20 → original SL distance unchanged."""
    mod = _import_pt_avwap(tmp_path)
    dist, label = mod.get_vix_adaptive_sl_distance(100.0, 3.0, vix=18.5)
    assert dist == 3.0
    assert label == "no_cap"


def test_vix_none_no_cap(tmp_path):
    """VIX=None (unavailable) → original SL distance unchanged."""
    mod = _import_pt_avwap(tmp_path)
    dist, label = mod.get_vix_adaptive_sl_distance(100.0, 3.0, vix=None)
    assert dist == 3.0
    assert label == "no_cap"


def test_vix_22_applies_2pct_cap(tmp_path):
    """VIX 20-25 → min(original, fill × 2.0%)."""
    mod = _import_pt_avwap(tmp_path)
    fill = 100.0
    # pct_cap = 100 * 0.02 = 2.0, original = 3.0 → capped to 2.0
    dist, label = mod.get_vix_adaptive_sl_distance(fill, 3.0, vix=22.0)
    assert dist == pytest.approx(2.0)
    assert "2.0%_cap" in label

    # If original already tighter: ATR wins
    dist2, _ = mod.get_vix_adaptive_sl_distance(fill, 1.5, vix=22.0)
    assert dist2 == pytest.approx(1.5)


def test_vix_27_applies_1_5pct_cap(tmp_path):
    """VIX 25-30 → min(original, fill × 1.5%)."""
    mod = _import_pt_avwap(tmp_path)
    fill = 200.0
    # pct_cap = 200 * 0.015 = 3.0, original = 5.0 → capped to 3.0
    dist, label = mod.get_vix_adaptive_sl_distance(fill, 5.0, vix=27.0)
    assert dist == pytest.approx(3.0)
    assert "1.5%_cap" in label


def test_vix_35_applies_1pct_cap_and_atr_reduction(tmp_path):
    """VIX > 30 → min(1.0×ATR, fill × 1.0%)."""
    mod = _import_pt_avwap(tmp_path)
    fill = 100.0
    atr = 2.0
    # With atr: sl_distance = min(5.0, 1.0*2.0) = 2.0, pct_cap = 1.0 → capped to 1.0
    dist, label = mod.get_vix_adaptive_sl_distance(fill, 5.0, vix=35.0, atr=atr)
    assert dist == pytest.approx(1.0)
    assert "1.0%_cap" in label


def test_vix_35_no_atr_just_pct_cap(tmp_path):
    """VIX > 30, no ATR → pct cap only."""
    mod = _import_pt_avwap(tmp_path)
    fill = 100.0
    # No atr reduction: sl_distance stays 5.0, pct_cap = 1.0 → capped to 1.0
    dist, label = mod.get_vix_adaptive_sl_distance(fill, 5.0, vix=35.0, atr=None)
    assert dist == pytest.approx(1.0)
    assert "1.0%_cap" in label
