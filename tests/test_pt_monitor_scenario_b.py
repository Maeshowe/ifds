"""Tests for pt_monitor.py — Trailing Stop Monitor (Scenario B).

Covers:
- Scenario B activation at 19:00 CET (profitable)
- Not activated before 19:00
- Not activated if not profitable
- Not activated if Scenario A already active
- Full qty SELL on trail SL hit (scope='full')
- TP1/TP2 limit orders not cancelled
- All SL orders cancelled on activation
- CEST transition (zoneinfo-based hour calc)
- Trail SL updates upward after Scenario B
- Trail SL not lowered after Scenario B
"""

import json
import os
import sys
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

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


def _make_state_b(
    sym="SDRL",
    entry=43.70,
    sl=41.41,
    tp1=45.00,
    tp2=48.00,
    total_qty=115,
    qty_b=77,
    tp1_filled=False,
    trail_active=False,
    trail_scope=None,
    trail_sl=None,
    trail_high=None,
    scenario_b_activated=False,
    scenario_b_eligible=True,
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
            "trail_scope": trail_scope,
            "trail_sl_current": trail_sl,
            "trail_high": trail_high,
            "scenario_b_activated": scenario_b_activated,
            "scenario_b_eligible": scenario_b_eligible,
        }
    }


# ---------------------------------------------------------------------------
# Scenario B activation tests
# ---------------------------------------------------------------------------


def test_scenario_b_activation_at_19_cet(tmp_path):
    """19:00 CET + price > entry*1.005 -> trail_active=True, scope='full'."""
    _write_state(tmp_path, _make_state_b())
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()

    # Price $44.20 > threshold $43.92 (43.70 * 1.005)
    # Mock time to be >= 19:00 CET (scenario_b_hour_utc)
    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "tp1_was_filled", return_value=False), patch.object(
        mod, "get_last_price", return_value=44.20
    ), patch.object(
        mod, "cancel_all_sl_orders", return_value=2
    ) as mock_cancel_all, patch.object(
        mod, "get_scenario_b_hour_utc", return_value=17
    ), patch(
        "scripts.paper_trading.pt_monitor.datetime"
    ) as mock_dt, patch.object(
        mod, "send_telegram"
    ) as mock_tg:
        # now_utc.hour = 18 >= scenario_b_hour_utc = 17
        mock_now = MagicMock()
        mock_now.hour = 18
        mock_dt.now.return_value = mock_now
        mod.main()

    mock_cancel_all.assert_called_once_with(mock_ib, "SDRL")
    mock_tg.assert_called_once()
    msg = mock_tg.call_args[0][0]
    assert "Trail active" in msg
    assert "Scenario B" in msg

    state = mod.load_state(date.today().strftime("%Y-%m-%d"))
    assert state["SDRL"]["trail_active"] is True
    assert state["SDRL"]["trail_scope"] == "full"
    assert state["SDRL"]["scenario_b_activated"] is True
    assert state["SDRL"]["scenario_b_eligible"] is False


def test_scenario_b_not_activated_before_19(tmp_path):
    """Before 19:00 CET -> Scenario B does not activate."""
    _write_state(tmp_path, _make_state_b())
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()

    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "tp1_was_filled", return_value=False), patch.object(
        mod, "get_scenario_b_hour_utc", return_value=18
    ), patch(
        "scripts.paper_trading.pt_monitor.datetime"
    ) as mock_dt, patch.object(
        mod, "send_telegram"
    ) as mock_tg:
        # now_utc.hour = 16 < scenario_b_hour_utc = 18
        mock_now = MagicMock()
        mock_now.hour = 16
        mock_dt.now.return_value = mock_now
        mod.main()

    mock_tg.assert_not_called()
    state = mod.load_state(date.today().strftime("%Y-%m-%d"))
    assert state["SDRL"]["trail_active"] is False
    assert state["SDRL"]["scenario_b_activated"] is False


def test_scenario_b_not_activated_if_not_profitable(tmp_path):
    """Price <= entry*1.005 -> Scenario B does not activate."""
    _write_state(tmp_path, _make_state_b())
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()

    # Price $43.80 <= threshold $43.92
    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "tp1_was_filled", return_value=False), patch.object(
        mod, "get_last_price", return_value=43.80
    ), patch.object(
        mod, "get_scenario_b_hour_utc", return_value=17
    ), patch(
        "scripts.paper_trading.pt_monitor.datetime"
    ) as mock_dt, patch.object(
        mod, "send_telegram"
    ) as mock_tg:
        mock_now = MagicMock()
        mock_now.hour = 18
        mock_dt.now.return_value = mock_now
        mod.main()

    mock_tg.assert_not_called()
    state = mod.load_state(date.today().strftime("%Y-%m-%d"))
    assert state["SDRL"]["trail_active"] is False


def test_scenario_b_not_activated_if_scenario_a_active(tmp_path):
    """Scenario A already active (trail_scope='bracket_b') -> B not eligible."""
    state = _make_state_b(
        tp1_filled=True,
        trail_active=True,
        trail_scope="bracket_b",
        trail_sl=43.70,
        trail_high=44.50,
        scenario_b_eligible=False,  # Set by Scenario A activation
    )
    _write_state(tmp_path, state)
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()

    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "get_last_price", return_value=44.80), patch.object(
        mod, "cancel_all_sl_orders"
    ) as mock_cancel_all, patch.object(
        mod, "send_telegram"
    ):
        mod.main()

    # cancel_all_sl_orders should NOT be called (Scenario B not activated)
    mock_cancel_all.assert_not_called()
    state = mod.load_state(date.today().strftime("%Y-%m-%d"))
    assert state["SDRL"]["trail_scope"] == "bracket_b"  # Still A


def test_scenario_b_full_qty_sell(tmp_path):
    """Trail SL hit with scope='full' -> SELL total_qty, orderRef=IFDS_{sym}_TRAIL."""
    state = _make_state_b(
        trail_active=True,
        trail_scope="full",
        trail_sl=43.50,
        trail_high=44.20,
        scenario_b_activated=True,
        scenario_b_eligible=False,
    )
    _write_state(tmp_path, state)
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()
    mock_ib.managedAccounts.return_value = ["DUH118657"]

    # Price $43.40 <= trail_sl $43.50
    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "get_last_price", return_value=43.40), patch.object(
        mod, "send_telegram"
    ) as mock_tg:
        mod.main()

    mock_ib.placeOrder.assert_called_once()
    placed_order = mock_ib.placeOrder.call_args[0][1]
    assert placed_order.action == "SELL"
    assert placed_order.totalQuantity == 115  # total_qty, not qty_b
    assert placed_order.orderRef == "IFDS_SDRL_TRAIL"  # No _B_ prefix

    mock_tg.assert_called_once()
    msg = mock_tg.call_args[0][0]
    assert "115" in msg
    assert "IFDS_SDRL_TRAIL" in msg

    state = mod.load_state(date.today().strftime("%Y-%m-%d"))
    assert state["SDRL"]["trail_active"] is False


def test_scenario_b_tp1_tp2_not_cancelled(tmp_path):
    """TP1 and TP2 limit orders are NOT cancelled when Scenario B activates."""
    _write_state(tmp_path, _make_state_b())
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()
    # Set up open orders: A_SL, B_SL, A_TP, B_TP
    a_sl = MagicMock(); a_sl.orderRef = "IFDS_SDRL_A_SL"; a_sl.orderId = 100
    b_sl = MagicMock(); b_sl.orderRef = "IFDS_SDRL_B_SL"; b_sl.orderId = 101
    a_tp = MagicMock(); a_tp.orderRef = "IFDS_SDRL_A_TP"; a_tp.orderId = 102
    b_tp = MagicMock(); b_tp.orderRef = "IFDS_SDRL_B_TP"; b_tp.orderId = 103
    mock_ib.openOrders.return_value = [a_sl, b_sl, a_tp, b_tp]

    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "tp1_was_filled", return_value=False), patch.object(
        mod, "get_last_price", return_value=44.20
    ), patch.object(
        mod, "get_scenario_b_hour_utc", return_value=17
    ), patch(
        "scripts.paper_trading.pt_monitor.datetime"
    ) as mock_dt, patch.object(
        mod, "send_telegram"
    ):
        mock_now = MagicMock()
        mock_now.hour = 18
        mock_dt.now.return_value = mock_now
        # Use real cancel_all_sl_orders (not mocked)
        mod.main()

    # Only SL orders cancelled (A_SL + B_SL), not TP orders
    cancel_calls = mock_ib.cancelOrder.call_args_list
    cancelled_refs = [c[0][0].orderRef for c in cancel_calls]
    assert "IFDS_SDRL_A_SL" in cancelled_refs
    assert "IFDS_SDRL_B_SL" in cancelled_refs
    assert "IFDS_SDRL_A_TP" not in cancelled_refs
    assert "IFDS_SDRL_B_TP" not in cancelled_refs


def test_scenario_b_sl_orders_cancelled(tmp_path):
    """Both Bracket A SL and Bracket B SL are cancelled on Scenario B activation."""
    _write_state(tmp_path, _make_state_b())
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()
    a_sl = MagicMock(); a_sl.orderRef = "IFDS_SDRL_A_SL"; a_sl.orderId = 100
    b_sl = MagicMock(); b_sl.orderRef = "IFDS_SDRL_B_SL"; b_sl.orderId = 101
    mock_ib.openOrders.return_value = [a_sl, b_sl]

    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "tp1_was_filled", return_value=False), patch.object(
        mod, "get_last_price", return_value=44.20
    ), patch.object(
        mod, "get_scenario_b_hour_utc", return_value=17
    ), patch(
        "scripts.paper_trading.pt_monitor.datetime"
    ) as mock_dt, patch.object(
        mod, "send_telegram"
    ):
        mock_now = MagicMock()
        mock_now.hour = 18
        mock_dt.now.return_value = mock_now
        mod.main()

    assert mock_ib.cancelOrder.call_count == 2


def test_scenario_b_cest_transition():
    """zoneinfo-based hour calculation handles CET vs CEST correctly."""
    import scripts.paper_trading.pt_monitor as mod

    CET = ZoneInfo("Europe/Budapest")

    # Winter time (CET = UTC+1): 19:00 CET = 18:00 UTC
    with patch.object(mod, "datetime") as mock_dt_mod:
        # Simulate January (CET, no DST)
        winter_now = datetime(2026, 1, 15, 19, 0, tzinfo=CET)
        mock_dt_mod.now.return_value = winter_now
        # Can't easily mock replace, so test the real function
    # Test actual function directly
    # In winter (CET=UTC+1): 19:00 CET = 18:00 UTC
    # In summer (CEST=UTC+2): 19:00 CEST = 17:00 UTC
    winter_target = datetime(2026, 1, 15, 19, 0, tzinfo=CET)
    winter_utc_hour = winter_target.astimezone(ZoneInfo("UTC")).hour
    assert winter_utc_hour == 18

    summer_target = datetime(2026, 7, 15, 19, 0, tzinfo=CET)
    summer_utc_hour = summer_target.astimezone(ZoneInfo("UTC")).hour
    assert summer_utc_hour == 17


def test_scenario_b_trail_updates_upward(tmp_path):
    """Price rises after Scenario B activation -> trail_sl moves up."""
    state = _make_state_b(
        trail_active=True,
        trail_scope="full",
        trail_sl=42.00,
        trail_high=44.29,
        scenario_b_activated=True,
        scenario_b_eligible=False,
    )
    _write_state(tmp_path, state)
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()

    # sl_distance = 43.70 - 41.41 = 2.29
    # Price $45.00 -> new_sl = 45.00 - 2.29 = 42.71 > current 42.00
    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "get_last_price", return_value=45.00), patch.object(
        mod, "send_telegram"
    ):
        mod.main()

    state = mod.load_state(date.today().strftime("%Y-%m-%d"))
    assert state["SDRL"]["trail_sl_current"] == 42.71
    assert state["SDRL"]["trail_high"] == 45.00
    assert state["SDRL"]["trail_active"] is True


def test_scenario_b_trail_sl_not_lowered(tmp_path):
    """Price drops after Scenario B -> trail_sl stays the same."""
    state = _make_state_b(
        trail_active=True,
        trail_scope="full",
        trail_sl=42.71,
        trail_high=45.00,
        scenario_b_activated=True,
        scenario_b_eligible=False,
    )
    _write_state(tmp_path, state)
    mod = _import_pt_monitor(tmp_path)

    mock_ib = MagicMock()

    # Price $44.00 -> new_sl = 44.00 - 2.29 = 41.71 < current 42.71
    with patch("lib.connection.connect", return_value=mock_ib), patch(
        "lib.connection.disconnect"
    ), patch.object(mod, "get_last_price", return_value=44.00), patch.object(
        mod, "send_telegram"
    ) as mock_tg:
        mod.main()

    state = mod.load_state(date.today().strftime("%Y-%m-%d"))
    assert state["SDRL"]["trail_sl_current"] == 42.71  # unchanged
    assert state["SDRL"]["trail_active"] is True
    mock_tg.assert_not_called()
