#!/usr/bin/env python3
"""IBKR Paper Trading — Close remaining positions at market close (MOC).

Runs at 21:45 CET (15:45 ET) — 5 min before NYSE MOC deadline.
Submits Market-on-Close SELL orders for any open positions.

Usage:
    python scripts/paper_trading/close_positions.py
"""
import logging
import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('close_positions')

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------


def send_telegram(message):
    """Send message via Telegram Bot API."""
    import requests

    token = os.getenv('IFDS_TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('IFDS_TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    from lib.connection import connect, get_account, disconnect
    from lib.orders import create_moc_order

    today_str = date.today().strftime('%Y-%m-%d')
    print(f"\nMOC Close — {today_str}")

    ib = connect()
    account = get_account(ib)

    from ib_insync import Stock

    # Cancel unfilled IFDS bracket orders to prevent late fills after MOC cutoff
    open_orders = ib.openOrders()
    ifds_orders = [o for o in open_orders
                   if hasattr(o, 'orderRef') and o.orderRef
                   and o.orderRef.startswith('IFDS_')]
    if ifds_orders:
        for order in ifds_orders:
            ib.cancelOrder(order)
        ib.sleep(2)
        print(f"  Cancelled {len(ifds_orders)} unfilled IFDS bracket orders")
    else:
        print("  No unfilled IFDS orders to cancel")

    # Get open positions (long and short, skip non-tradable)
    positions = [p for p in ib.positions()
                 if p.position != 0
                 and '.CVR' not in p.contract.symbol
                 and p.contract.secType == 'STK']

    if not positions:
        print("No positions to close")
        disconnect(ib)
        return

    moc_submitted = []

    for pos in positions:
        sym = pos.contract.symbol
        con_id = pos.contract.conId

        # Create fresh contract with SMART routing (avoids Error 10311)
        contract = Stock(conId=con_id, exchange='SMART')
        ib.qualifyContracts(contract)

        action = 'SELL' if pos.position > 0 else 'BUY'
        qty = int(abs(pos.position))
        order = create_moc_order(qty, account, action=action)
        ib.placeOrder(contract, order)
        moc_submitted.append((sym, qty, action))
        print(f"  {sym}: MOC {action} {qty} shares")

    ib.sleep(1)  # Let orders propagate

    print(f"MOC submitted: {len(moc_submitted)} positions")

    # Telegram notification
    if moc_submitted:
        lines = [f"🔔 PAPER TRADING MOC — {today_str}",
                 f"Closing {len(moc_submitted)} remaining positions at market close:"]
        for sym, qty, action in moc_submitted:
            lines.append(f"{sym}: {action} {qty} shares")
        send_telegram("\n".join(lines))

    disconnect(ib)


if __name__ == '__main__':
    main()
