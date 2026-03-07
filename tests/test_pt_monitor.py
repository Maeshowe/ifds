"""Tests for pt_monitor.py — Trailing Stop Monitor (Scenario A).

Covers:
- State file init from submit_orders.py
- TP1 fill detection -> trail activation
- Breakeven protection on trail init
- Trail SL upward tracking
- Trail SL not lowered on price drop
- Trail SL hit -> SELL order
- TP2 order not cancelled
- No state file -> clean exit
- TP1 not filled -> no trail
"""

import json
import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch, call

import pytest


@pytest.fixture(autouse=True)
def _isolate_pt_env():
    """Prevent pt_monitor.py load_dotenv() from polluting env."""
    keys = [
        "scripts.paper_trading.pt_monitor",
        "scripts.paper_trading.submit_orders",
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


def _import_pt_monitor(tmp_path):
    """Import pt_monitor with STATE_DIR pointed at tmp_path."""
    scripts_dir = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "paper_trading"
    )
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    import scripts.paper_trading.pt_monitor as mod

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


def _make_state(
    sym="LION",
    entry=9.50,
    sl=8.90,
    tp1=10.00,
    tp2=11.50,
    total_qty=537,
    qty_b=360,
    tp1_filled=False,
    trail_active=False,
    trail_sl=None,
    trail_high=None,
):
    return {
        sym: {
            "entry_price": entry,
            "sl_distance": round(entry - sl, 4),
            "tp1_price": tp1,
            "tp2_price": tp2,
            "total_qty": total_qty,
            "qty_b": qty_b,
            "tp1_filled": tp1_filled,
            "trail_active": trail_active,
            "trail_scope": "bracket_b" if trail_active else None,
            "trail_sl_current": trail_sl,
            "trail_high": trail_high,
            "scenario_b_activated": False,
            "scenario_b_eligible": not trail_active,
        }
    }


# ---------------------------------------------------------------------------
# State file init tests (submit_orders.py logic)
# ---------------------------------------------------------------------------


def test_state_fields_correct():
    """sl_distance = limit_price - stop_loss, calculated correctly."""
    entry = 9.50
    sl = 8.90
    state = _make_state(entry=entry, sl=sl)
    assert state["LION"]["sl_distance"] == round(entry - sl, 4)
    assert state["LION"]["sl_distance"] == 0.6
    assert state["LION"]["tp1_filled"] is False
    assert state["LION"]["trail_active"] is False
    assert state["LION"]["qty_b"] == 360


# ---------------------------------------------------------------------------
# pt_monitor Scenario A tests
# ---------------------------------------------------------------------------


def test_no_state_file_exits_cleanly(tmp_path):
    """No state file -> exits without error, no IBKR connection."""
    mod = _import_pt_monitor(tmp_path)

    with patch("lib.connection.connect") as mock_connect:
        mod.main()

    mock_connect.assert_not_called()


def test_tp1_not_filled_no_trail(tmp_path):
    """TP1 not yet filled -> trail not activated."""
    _write_state(tmp_path, _make_state())
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()
    mock_ib.positions.return_value = []

    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "tp1_was_filled", return_value=False), patch.object(
        mod, "send_telegram"
    ) as mock_tg:
        mod.main()

    mock_tg.assert_not_called()
    # State should remain unchanged
    state = mod.load_state(date.today().strftime("%Y-%m-%d"))
    assert state["LION"]["tp1_filled"] is False
    assert state["LION"]["trail_active"] is False


def test_scenario_a_trail_activation(tmp_path):
    """TP1 fill detected -> trail_active=True, SL cancel called, Telegram sent."""
    _write_state(tmp_path, _make_state())
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()

    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "tp1_was_filled", return_value=True), patch.object(
        mod, "get_last_price", return_value=10.20
    ), patch.object(
        mod, "cancel_bracket_b_sl", return_value=True
    ) as mock_cancel, patch.object(
        mod, "send_telegram"
    ) as mock_tg:
        mod.main()

    mock_cancel.assert_called_once_with(mock_ib, "LION")
    mock_tg.assert_called_once()
    msg = mock_tg.call_args[0][0]
    assert "Trail active" in msg
    assert "LION" in msg

    # State should be updated
    state = mod.load_state(date.today().strftime("%Y-%m-%d"))
    assert state["LION"]["tp1_filled"] is True
    assert state["LION"]["trail_active"] is True
    assert state["LION"]["trail_scope"] == "bracket_b"


def test_scenario_a_breakeven_protection(tmp_path):
    """Entry $9.50, TP1 fill @ $9.55 -> trail_sl = $9.50 (not $8.95)."""
    _write_state(tmp_path, _make_state(entry=9.50, sl=8.90))
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()

    # current_price = 9.55, sl_distance = 0.60
    # new_sl = 9.55 - 0.60 = 8.95 < entry 9.50
    # breakeven protection -> trail_sl = max(9.50, 8.95) = 9.50
    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "tp1_was_filled", return_value=True), patch.object(
        mod, "get_last_price", return_value=9.55
    ), patch.object(
        mod, "cancel_bracket_b_sl", return_value=True
    ), patch.object(
        mod, "send_telegram"
    ):
        mod.main()

    state = mod.load_state(date.today().strftime("%Y-%m-%d"))
    assert state["LION"]["trail_sl_current"] == 9.50


def test_scenario_a_trail_update(tmp_path):
    """Price rises -> trail_sl moves up."""
    # Start with trail already active
    state = _make_state(
        entry=9.50, sl=8.90, tp1_filled=True, trail_active=True,
        trail_sl=9.60, trail_high=10.20,
    )
    _write_state(tmp_path, state)
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()

    # Price rose to 10.80 -> new_sl = 10.80 - 0.60 = 10.20 > current 9.60
    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "get_last_price", return_value=10.80), patch.object(
        mod, "send_telegram"
    ):
        mod.main()

    state = mod.load_state(date.today().strftime("%Y-%m-%d"))
    assert state["LION"]["trail_sl_current"] == 10.20
    assert state["LION"]["trail_high"] == 10.80


def test_scenario_a_trail_sl_not_lowered(tmp_path):
    """Price drops -> trail_sl stays the same (only moves up)."""
    state = _make_state(
        entry=9.50, sl=8.90, tp1_filled=True, trail_active=True,
        trail_sl=10.20, trail_high=10.80,
    )
    _write_state(tmp_path, state)
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()

    # Price dropped to 10.40 -> new_sl = 10.40 - 0.60 = 9.80 < current 10.20
    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "get_last_price", return_value=10.40), patch.object(
        mod, "send_telegram"
    ) as mock_tg:
        mod.main()

    state = mod.load_state(date.today().strftime("%Y-%m-%d"))
    assert state["LION"]["trail_sl_current"] == 10.20  # unchanged
    assert state["LION"]["trail_active"] is True
    mock_tg.assert_not_called()  # no trail SL hit


def test_scenario_a_trail_sl_hit(tmp_path):
    """current_price <= trail_sl -> SELL order placed with IFDS_{sym}_B_TRAIL."""
    state = _make_state(
        entry=9.50, sl=8.90, tp1_filled=True, trail_active=True,
        trail_sl=10.20, trail_high=10.80,
    )
    _write_state(tmp_path, state)
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()
    mock_ib.managedAccounts.return_value = ["DUH118657"]

    # Price dropped to 10.15 <= trail_sl 10.20 -> SELL
    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "get_last_price", return_value=10.15), patch.object(
        mod, "send_telegram"
    ) as mock_tg:
        mod.main()

    # Verify SELL order placed
    mock_ib.placeOrder.assert_called_once()
    placed_order = mock_ib.placeOrder.call_args[0][1]
    assert placed_order.action == "SELL"
    assert placed_order.totalQuantity == 360
    assert placed_order.orderRef == "IFDS_LION_B_TRAIL"

    # Telegram sent
    mock_tg.assert_called_once()
    msg = mock_tg.call_args[0][0]
    assert "Trail SL hit" in msg
    assert "LION" in msg
    assert "360" in msg

    # Trail deactivated
    state = mod.load_state(date.today().strftime("%Y-%m-%d"))
    assert state["LION"]["trail_active"] is False


def test_scenario_a_tp2_not_cancelled(tmp_path):
    """TP2 limit order is NOT cancelled when trail activates."""
    _write_state(tmp_path, _make_state())
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()
    # Set up open orders: B_SL and B_TP
    sl_order = MagicMock()
    sl_order.orderRef = "IFDS_LION_B_SL"
    sl_order.orderId = 100
    tp_order = MagicMock()
    tp_order.orderRef = "IFDS_LION_B_TP"
    tp_order.orderId = 101
    mock_ib.openOrders.return_value = [sl_order, tp_order]

    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "tp1_was_filled", return_value=True), patch.object(
        mod, "get_last_price", return_value=10.20
    ), patch.object(
        mod, "send_telegram"
    ):
        # Use real cancel_bracket_b_sl (not mocked)
        mod.main()

    # Only B_SL should be cancelled, not B_TP
    mock_ib.cancelOrder.assert_called_once_with(sl_order)


def test_all_resolved_monitor_idle(tmp_path):
    """All tickers tp1_filled=True and trail_active=False -> no IBKR connection."""
    state = _make_state(tp1_filled=True, trail_active=False)
    # Mark Scenario B as resolved too
    state["LION"]["scenario_b_eligible"] = False
    state["LION"]["scenario_b_activated"] = True
    _write_state(tmp_path, state)
    mod = _import_pt_monitor(tmp_path)

    with patch("lib.connection.connect") as mock_connect:
        mod.main()

    mock_connect.assert_not_called()
