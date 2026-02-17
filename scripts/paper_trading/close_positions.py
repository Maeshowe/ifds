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

    # Get open positions
    positions = [p for p in ib.positions() if p.position > 0]

    if not positions:
        print("No positions to close")
        disconnect(ib)
        return

    moc_submitted = []

    for pos in positions:
        sym = pos.contract.symbol
        qty = int(pos.position)
        order = create_moc_order(qty, account)
        ib.placeOrder(pos.contract, order)
        moc_submitted.append((sym, qty))
        print(f"  {sym}: MOC SELL {qty} shares")

    ib.sleep(1)  # Let orders propagate

    print(f"MOC submitted: {len(moc_submitted)} positions")

    # Telegram notification
    if moc_submitted:
        lines = [f"🔔 PAPER TRADING MOC — {today_str}",
                 f"Closing {len(moc_submitted)} remaining positions at market close:"]
        for sym, qty in moc_submitted:
            lines.append(f"{sym}: {qty} shares")
        send_telegram("\n".join(lines))

    disconnect(ib)


if __name__ == '__main__':
    main()
