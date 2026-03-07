#!/usr/bin/env python3
"""IFDS Paper Trading — Trailing Stop Monitor (Scenario A).

Runs every 5 minutes (09:00-19:55 UTC / 10:00-20:55 CET).
Detects TP1 fills and activates trailing stop on Bracket B.

Scenario A: TP1 fill -> trail Bracket B (qty_b)
  - Cancel Bracket B SL order
  - Keep TP2 limit order (upper cap)
  - Trail distance = entry_price - original_sl_price
  - Breakeven protection: trail_sl >= entry_price on activation
  - Telegram on activation and SL hit

State file: scripts/paper_trading/logs/monitor_state_YYYY-MM-DD.json
  (written by submit_orders.py after bracket submission)

Usage:
    python scripts/paper_trading/pt_monitor.py
"""
import json
import logging
import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pt_monitor")

STATE_DIR = "scripts/paper_trading/logs"


def send_telegram(message: str) -> None:
    import requests

    token = os.getenv("IFDS_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("IFDS_TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")


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


def main() -> None:
    from lib.connection import connect, disconnect

    today_str = date.today().strftime("%Y-%m-%d")
    state = load_state(today_str)

    if not state:
        logger.info("No monitor state file found — nothing to monitor.")
        return

    # Tickers that need monitoring: TP1 not yet filled OR trail active
    active_tickers = [
        sym
        for sym, s in state.items()
        if not s.get("tp1_filled") or s.get("trail_active")
    ]
    if not active_tickers:
        logger.info("All positions resolved — monitor idle.")
        return

    logger.info(f"Monitoring {len(active_tickers)} tickers: {active_tickers}")

    ib = connect(client_id=15)
    ib.sleep(3)

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
                qty = s["qty_b"]
                logger.warning(
                    f"{sym}: Trail SL hit @ ${current_price:.2f} — SELL {qty} shares"
                )

                from ib_insync import MarketOrder, Stock

                contract = Stock(sym, "SMART", "USD")
                ib.qualifyContracts(contract)
                order = MarketOrder("SELL", qty)
                order.tif = "DAY"
                order.orderRef = f"IFDS_{sym}_B_TRAIL"
                order.account = ib.managedAccounts()[0]
                ib.placeOrder(contract, order)

                s["trail_active"] = False
                state_changed = True

                msg = (
                    f"STOP {sym}: Trail SL hit\n"
                    f"Price: ${current_price:.2f} <= SL: ${s['trail_sl_current']:.2f}\n"
                    f"SELL {qty} shares (Bracket B)\n"
                    f"orderRef: IFDS_{sym}_B_TRAIL"
                )
                logger.warning(msg)
                send_telegram(msg)

    if state_changed:
        save_state(today_str, state)

    disconnect(ib)


if __name__ == "__main__":
    main()
