#!/usr/bin/env python3
"""IFDS Paper Trading — Trailing Stop Monitor (Scenario A + B).

Runs every 5 minutes (10:00-20:55 CET).
Detects TP1 fills and activates trailing stop on Bracket B (Scenario A).
At 19:00 CET, activates trail on full position if profitable (Scenario B).

Scenario A: TP1 fill -> trail Bracket B (qty_b)
  - Cancel Bracket B SL order
  - Keep TP2 limit order (upper cap)
  - Trail distance = entry_price - original_sl_price
  - Breakeven protection: trail_sl >= entry_price on activation

Scenario B: 19:00 CET + profitable (>0.5%) -> trail full position
  - Cancel ALL SL orders (Bracket A + B)
  - Keep TP1 and TP2 limit orders (natural caps)
  - Trail scope: 'full' (total_qty)
  - Does NOT activate if Scenario A already active

State file: scripts/paper_trading/logs/monitor_state_YYYY-MM-DD.json
  (written by submit_orders.py after bracket submission)

Usage:
    python scripts/paper_trading/pt_monitor.py
"""
import json
import os
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

try:
    from lib.log_setup import setup_pt_logger
    logger = setup_pt_logger("monitor")
except ModuleNotFoundError:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    logger = logging.getLogger('monitor')

STATE_DIR = "scripts/paper_trading/logs"


def send_telegram(message: str) -> None:
    """Send message via Telegram Bot API with CET timestamp header."""
    from lib.telegram_helper import telegram_header
    from lib.telegram_helper import send_telegram as _send
    _send(f"{telegram_header('MONITOR')}\n{message}")


def load_state(today_str: str) -> dict:
    path = f"{STATE_DIR}/monitor_state_{today_str}.json"
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def save_state(today_str: str, state: dict) -> None:
    path = f"{STATE_DIR}/monitor_state_{today_str}.json"
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def tp1_was_filled(ib, sym: str) -> bool:
    """Check if Bracket A TP order was filled today via executions."""
    from ib_insync import ExecutionFilter

    today = date.today().strftime("%Y%m%d")
    fills = ib.reqExecutions(ExecutionFilter(time=f"{today} 00:00:00"))
    for fill in fills:
        if fill.execution.orderRef == f"IFDS_{sym}_A_TP":
            return True
    return False


def get_last_price(ib, sym: str) -> float | None:
    """Get last traded price via snapshot market data."""
    from ib_insync import Stock

    contract = Stock(sym, "SMART", "USD")
    details = ib.reqContractDetails(contract)
    if not details:
        return None
    ticker = ib.reqMktData(details[0].contract, "", True, False)
    ib.sleep(2)
    price = ticker.last or ticker.close
    ib.cancelMktData(details[0].contract)
    return price if price and price > 0 else None


def cancel_bracket_b_sl(ib, sym: str) -> bool:
    """Cancel Bracket B SL order. Returns True if found and cancelled."""
    open_orders = ib.openOrders()
    for order in open_orders:
        if getattr(order, "orderRef", "") == f"IFDS_{sym}_B_SL":
            ib.cancelOrder(order)
            ib.sleep(1)
            logger.info(f"{sym}: Bracket B SL cancelled (orderId={order.orderId})")
            return True
    logger.warning(f"{sym}: Bracket B SL order not found for cancellation")
    return False


def cancel_all_sl_orders(ib, sym: str) -> int:
    """Cancel all SL orders for a ticker. Returns count of cancelled orders."""
    open_orders = ib.openOrders()
    cancelled = 0
    for order in open_orders:
        ref = getattr(order, "orderRef", "")
        if ref.startswith(f"IFDS_{sym}") and ref.endswith("_SL"):
            ib.cancelOrder(order)
            ib.sleep(0.5)
            logger.info(f"{sym}: SL cancelled — {ref} (orderId={order.orderId})")
            cancelled += 1
    if cancelled == 0:
        logger.warning(f"{sym}: No SL orders found for cancellation")
    return cancelled


def cancel_all_orders(ib, sym: str) -> int:
    """Cancel ALL IFDS orders for a ticker (SL + TP). Returns count cancelled."""
    open_orders = ib.openOrders()
    cancelled = 0
    for order in open_orders:
        ref = getattr(order, "orderRef", "")
        if ref.startswith(f"IFDS_{sym}"):
            ib.cancelOrder(order)
            ib.sleep(0.5)
            logger.info(f"{sym}: Cancelled — {ref} (orderId={order.orderId})")
            cancelled += 1
    if cancelled == 0:
        logger.warning(f"{sym}: No orders found for cancellation")
    return cancelled


SCENARIO_B_LOSS_THRESHOLD = 0.98  # -2.0%

CET = ZoneInfo("Europe/Budapest")


def get_scenario_b_hour_utc() -> int:
    """Returns UTC hour equivalent of 19:00 CET/CEST."""
    now_cet = datetime.now(CET)
    target_cet = now_cet.replace(hour=19, minute=0, second=0, microsecond=0)
    return target_cet.astimezone(ZoneInfo("UTC")).hour


def main() -> None:
    from lib.connection import connect, disconnect

    today_str = date.today().strftime("%Y-%m-%d")
    state = load_state(today_str)

    if not state:
        logger.info("No monitor state file found — nothing to monitor.")
        return

    # Tickers that need monitoring:
    # - TP1 not yet filled (Scenario A candidate)
    # - trail active (A or B running)
    # - Scenario B eligible and not yet activated
    candidate_tickers = [
        sym
        for sym, s in state.items()
        if (not s.get("tp1_filled"))
        or s.get("trail_active")
        or (
            s.get("scenario_b_eligible", True)
            and not s.get("scenario_b_activated")
            and not s.get("trail_active")
        )
    ]
    if not candidate_tickers:
        logger.info("All positions resolved — monitor idle.")
        return

    ib = connect(client_id=15)
    ib.sleep(3)

    # Filter against actual IBKR positions — prevent phantom trail on unfilled entries
    ib_positions = {p.contract.symbol for p in ib.positions() if p.position != 0}
    active_tickers = [sym for sym in candidate_tickers if sym in ib_positions]
    phantom = set(candidate_tickers) - set(active_tickers)
    if phantom:
        logger.warning(
            f"Phantom tickers filtered out (no IBKR position): {sorted(phantom)}"
        )
    if not active_tickers:
        logger.info("All candidate tickers are phantom — nothing to monitor.")
        disconnect(ib)
        return

    logger.info(f"Monitoring {len(active_tickers)} tickers: {active_tickers}")

    state_changed = False

    for sym in active_tickers:
        s = state[sym]

        # --- Scenario A: TP1 fill detection ---
        if not s["tp1_filled"]:
            if tp1_was_filled(ib, sym):
                s["tp1_filled"] = True
                state_changed = True
                logger.info(f"{sym}: TP1 fill detected")

                current_price = get_last_price(ib, sym)
                if current_price is None:
                    logger.warning(
                        f"{sym}: Cannot get price for trail init — skipping"
                    )
                    continue

                # Cancel Bracket B SL, keep TP2 limit
                cancel_bracket_b_sl(ib, sym)

                # Breakeven protection: trail_sl >= entry_price
                initial_sl = max(s["entry_price"], current_price - s["sl_distance"])
                s["trail_active"] = True
                s["trail_scope"] = "bracket_b"
                s["trail_sl_current"] = round(initial_sl, 4)
                s["trail_high"] = round(current_price, 4)

                msg = (
                    f"TARGET {sym}: Trail active (Scenario A)\n"
                    f"TP1 fill detected\n"
                    f"Trail SL: ${initial_sl:.2f} (entry: ${s['entry_price']:.2f})\n"
                    f"TP2 limit stays: ${s['tp2_price']:.2f}"
                )
                logger.info(msg)
                send_telegram(msg)

                # Scenario A active -> Scenario B no longer needed
                s["scenario_b_eligible"] = False

        # --- Scenario B: time-based activation (19:00 CET, profitable) ---
        if (
            not s.get("trail_active")
            and not s.get("scenario_b_activated")
            and s.get("scenario_b_eligible", True)
        ):
            now_utc = datetime.now(timezone.utc)
            scenario_b_hour = get_scenario_b_hour_utc()

            if now_utc.hour >= scenario_b_hour:
                current_price = get_last_price(ib, sym)
                if current_price is None:
                    logger.warning(
                        f"{sym}: Cannot get price for Scenario B check"
                    )
                    continue

                threshold = s["entry_price"] * 1.005
                if current_price > threshold:
                    cancel_all_sl_orders(ib, sym)

                    trail_sl = round(current_price - s["sl_distance"], 4)
                    s["trail_active"] = True
                    s["trail_scope"] = "full"
                    s["trail_sl_current"] = trail_sl
                    s["trail_high"] = round(current_price, 4)
                    s["scenario_b_activated"] = True
                    s["scenario_b_eligible"] = False
                    state_changed = True

                    msg = (
                        f"CLOCK {sym}: Trail active (Scenario B)\n"
                        f"19:00 CET — position profitable\n"
                        f"Price: ${current_price:.2f} > threshold: ${threshold:.2f}\n"
                        f"Trail SL: ${trail_sl:.2f}\n"
                        f"TP1/TP2 limit orders stay"
                    )
                    logger.info(msg)
                    send_telegram(msg)
                elif current_price < s["entry_price"] * SCENARIO_B_LOSS_THRESHOLD:
                    # Loss-making exit: close position immediately
                    cancel_all_orders(ib, sym)

                    qty = s["total_qty"]
                    from ib_insync import MarketOrder, Stock

                    contract = Stock(sym, "SMART", "USD")
                    ib.qualifyContracts(contract)
                    order = MarketOrder("SELL", qty)
                    order.tif = "DAY"
                    order.orderRef = f"IFDS_{sym}_LOSS_EXIT"
                    order.account = ib.managedAccounts()[0]
                    ib.placeOrder(contract, order)

                    s["trail_active"] = False
                    s["scenario_b_eligible"] = False
                    s["scenario_b_activated"] = True
                    state_changed = True

                    loss_pct = ((current_price / s["entry_price"]) - 1) * 100
                    msg = (
                        f"LOSS EXIT {sym}: Scenario B loss-making close\n"
                        f"19:00 CET — position down {loss_pct:.1f}%\n"
                        f"Price: ${current_price:.2f} < threshold: "
                        f"${s['entry_price'] * SCENARIO_B_LOSS_THRESHOLD:.2f}\n"
                        f"SELL {qty} shares at MKT"
                    )
                    logger.warning(msg)
                    send_telegram(msg)
                else:
                    logger.info(
                        f"{sym}: Scenario B — not activated "
                        f"(price ${current_price:.2f}, "
                        f"profit threshold ${threshold:.2f}, "
                        f"loss threshold ${s['entry_price'] * SCENARIO_B_LOSS_THRESHOLD:.2f})"
                    )

        # --- Trail SL update + hit detection ---
        if s.get("trail_active"):
            current_price = get_last_price(ib, sym)
            if current_price is None:
                logger.warning(f"{sym}: Cannot get price for trail update")
                continue

            # Trail SL up only
            new_sl = round(current_price - s["sl_distance"], 4)
            if new_sl > s["trail_sl_current"]:
                s["trail_sl_current"] = new_sl
                s["trail_high"] = round(max(current_price, s["trail_high"]), 4)
                state_changed = True
                logger.info(
                    f"{sym}: Trail SL updated -> ${new_sl:.2f} (price: ${current_price:.2f})"
                )

            # Trail SL hit
            if current_price <= s["trail_sl_current"]:
                # Scope-aware qty and orderRef
                if s.get("trail_scope") == "full":
                    qty = s["total_qty"]
                    order_ref_suffix = "TRAIL"
                else:  # 'bracket_b'
                    qty = s["qty_b"]
                    order_ref_suffix = "B_TRAIL"

                logger.warning(
                    f"{sym}: Trail SL hit @ ${current_price:.2f} "
                    f"— SELL {qty} shares (scope: {s['trail_scope']})"
                )

                from ib_insync import MarketOrder, Stock

                contract = Stock(sym, "SMART", "USD")
                ib.qualifyContracts(contract)
                order = MarketOrder("SELL", qty)
                order.tif = "DAY"
                order.orderRef = f"IFDS_{sym}_{order_ref_suffix}"
                order.account = ib.managedAccounts()[0]
                ib.placeOrder(contract, order)

                s["trail_active"] = False
                state_changed = True

                msg = (
                    f"STOP {sym}: Trail SL hit\n"
                    f"Price: ${current_price:.2f} <= SL: ${s['trail_sl_current']:.2f}\n"
                    f"SELL {qty} shares (scope: {s['trail_scope']})\n"
                    f"orderRef: IFDS_{sym}_{order_ref_suffix}"
                )
                logger.warning(msg)
                send_telegram(msg)

    if state_changed:
        save_state(today_str, state)

    disconnect(ib)


if __name__ == "__main__":
    main()
