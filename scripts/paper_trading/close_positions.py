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
# Constants
# ---------------------------------------------------------------------------

MAX_ORDER_SIZE = 500  # IBKR precautionary size limit (Global Configuration/Presets)

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
# Net position helper
# ---------------------------------------------------------------------------


BRACKET_B_SUFFIXES = ('_B_SL', '_B_TRAIL', '_TRAIL')


def get_net_open_qty(symbol: str, con_id: int, gross_qty: int, todays_fills) -> int:
    """Return safe MOC qty after accounting for intraday Bracket B fills.

    Only subtracts Bracket B SLD fills (_B_SL, _B_TRAIL, _TRAIL) from
    gross_qty.  Bracket A TP1 fills (_A_TP) are NOT subtracted because
    IBKR already removes A qty from pos.position when the TP fills —
    subtracting them again would cause undersized MOC orders and leftovers.

    If positions() is already synced, this conservatively undersells
    (leaving shares open until next day) but never creates an inadvertent short.
    Primary protection: reqPositions() + 5s sleep before reading positions().
    """
    bracket_sold = sum(
        int(fill.execution.shares)
        for fill in todays_fills
        if fill.contract.conId == con_id
        and fill.execution.side == 'SLD'
        and any(
            (getattr(fill.execution, 'orderRef', '') or '').endswith(suffix)
            for suffix in BRACKET_B_SUFFIXES
        )
    )
    if bracket_sold > 0:
        logger.info(
            f"{symbol}: {bracket_sold} shares closed intraday via bracket TP/SL — "
            f"adjusting MOC qty {gross_qty} → {max(0, gross_qty - bracket_sold)}"
        )
    return max(0, gross_qty - bracket_sold)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    from lib.connection import connect, get_account, disconnect
    from lib.orders import create_moc_order

    today_str = date.today().strftime('%Y-%m-%d')

    ib = connect(client_id=11)
    ib.sleep(3)  # Initial sync
    # Force fresh position data: reqPositions ensures intraday TP/SL fills are reflected
    ib.reqPositions()
    ib.sleep(5)  # Wait for IBKR to push updated positions (total: 8s)

    print(f"\nMOC Close — {today_str}")
    account = get_account(ib)

    from ib_insync import Stock, ExecutionFilter

    # Cancel ALL open orders to prevent late fills after MOC cutoff.
    # Covers: IFDS_ bracket orders + residual split-leg orders without IFDS_ tag
    # (e.g. partial entry fills leaving orphaned SL/TP2 from OCA groups).
    # Safe on paper account (DUH118657) where only IFDS orders exist.
    open_orders = ib.openOrders()
    if open_orders:
        for order in open_orders:
            ib.cancelOrder(order)
        ib.sleep(2)
        print(f"  Cancelled {len(open_orders)} open orders before MOC")
    else:
        print("  No open orders to cancel")

    # Fetch today's executions once for bracket fill detection (used by get_net_open_qty)
    todays_fills = ib.reqExecutions(
        ExecutionFilter(time=date.today().strftime('%Y%m%d') + ' 00:00:00')
    )

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

        # Compute net open qty after intraday bracket TP/SL fills
        gross_qty = int(abs(pos.position))
        net_qty = get_net_open_qty(sym, con_id, gross_qty, todays_fills)

        if net_qty == 0:
            logger.info(f"{sym}: position fully closed intraday (TP/SL), skipping MOC")
            print(f"  {sym}: SKIP — already closed (intraday TP/SL)")
            continue

        if net_qty != gross_qty:
            print(f"  {sym}: qty adjusted {gross_qty} → {net_qty} (intraday partial fill)")

        # Create fresh contract with SMART routing (avoids Error 10311)
        contract = Stock(conId=con_id, exchange='SMART')
        ib.qualifyContracts(contract)

        action = 'SELL' if pos.position > 0 else 'BUY'
        qty = net_qty

        if qty <= MAX_ORDER_SIZE:
            order = create_moc_order(qty, account, action=action)
            ib.placeOrder(contract, order)
            moc_submitted.append((sym, qty, action))
            print(f"  {sym}: MOC {action} {qty} shares")
        else:
            # Split into multiple legs to stay under IBKR size limit
            remaining = qty
            leg = 1
            total_legs = -(-qty // MAX_ORDER_SIZE)  # ceil division
            while remaining > 0:
                leg_qty = min(remaining, MAX_ORDER_SIZE)
                order = create_moc_order(leg_qty, account, action=action)
                ib.placeOrder(contract, order)
                moc_submitted.append((sym, leg_qty, action))
                print(f"  {sym}: MOC {action} {leg_qty} shares (leg {leg}/{total_legs})")
                remaining -= leg_qty
                leg += 1

    ib.sleep(1)  # Let orders propagate

    print(f"MOC submitted: {len(moc_submitted)} positions")

    # Telegram notification — aggregate split legs per ticker
    if moc_submitted:
        ticker_totals = {}
        for sym, leg_qty, action in moc_submitted:
            if sym not in ticker_totals:
                ticker_totals[sym] = (0, action)
            ticker_totals[sym] = (ticker_totals[sym][0] + leg_qty, action)

        lines = [f"🔔 PAPER TRADING MOC — {today_str}",
                 f"Closing {len(ticker_totals)} positions at market close:"]
        for sym, (total_qty, action) in ticker_totals.items():
            lines.append(f"{sym}: {action} {total_qty} shares")
        send_telegram("\n".join(lines))

    disconnect(ib)


if __name__ == '__main__':
    main()
