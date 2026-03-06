"""
IFDS Paper Trading — Cancel All Orders & Close All Positions

Usage:
    python scripts/paper_trading/nuke.py              # Cancel + close all
    python scripts/paper_trading/nuke.py --orders     # Cancel orders only
    python scripts/paper_trading/nuke.py --positions   # Close positions only
    python scripts/paper_trading/nuke.py --dry-run     # Show what would happen
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import date

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from ib_insync import IB, MarketOrder

HOST = '127.0.0.1'
PORT = 7497
CLIENT_ID = 13  # Dedicated for nuke script
MAX_ORDER_SIZE = 500  # IBKR precautionary size limit
LOG_DIR = 'scripts/paper_trading/logs'

os.makedirs(LOG_DIR, exist_ok=True)
_log_path = f"{LOG_DIR}/nuke_{date.today().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(_log_path),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger('nuke')


def main():
    parser = argparse.ArgumentParser(description="Cancel all orders & close all positions")
    parser.add_argument('--orders', action='store_true', help='Cancel orders only')
    parser.add_argument('--positions', action='store_true', help='Close positions only')
    parser.add_argument('--dry-run', action='store_true', help='Show what would happen')
    args = parser.parse_args()

    # Default: do both
    do_orders = args.orders or (not args.orders and not args.positions)
    do_positions = args.positions or (not args.orders and not args.positions)

    logger.info(f"Log: {_log_path}")

    ib = IB()
    try:
        ib.connect(HOST, PORT, clientId=CLIENT_ID)
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        sys.exit(1)

    logger.info(f"{'[DRY RUN] ' if args.dry_run else ''}IBKR Paper Trading — Nuke")

    # Show current state
    positions = ib.positions()
    open_orders = ib.reqAllOpenOrders()

    logger.info(f"Open positions: {len(positions)}")
    for pos in positions:
        logger.info(f"  {pos.contract.symbol}: {pos.position} shares")

    logger.info(f"Open orders: {len(open_orders)}")

    if args.dry_run:
        logger.info("[DRY RUN] No action taken.")
        ib.disconnect()
        return

    # Cancel orders
    if do_orders and open_orders:
        logger.info(f"Cancelling {len(open_orders)} orders...")
        ib.reqGlobalCancel()
        ib.sleep(2)
        remaining = ib.reqAllOpenOrders()
        logger.info(f"Done. Remaining orders: {len(remaining)}")

    # Close positions
    if do_positions and positions:
        logger.info(f"Closing {len(positions)} positions at MARKET...")
        for pos in positions:
            symbol = pos.contract.symbol
            con_id = pos.contract.conId

            # Skip non-tradable contracts (e.g. CVR, warrants)
            if '.CVR' in symbol or pos.contract.secType != 'STK':
                logger.info(f"  {symbol}: SKIP (non-tradable)")
                continue

            # Create fresh contract with SMART routing
            from ib_insync import Stock
            contract = Stock(conId=con_id, exchange='SMART')
            ib.qualifyContracts(contract)

            action = 'SELL' if pos.position > 0 else 'BUY'
            qty = int(abs(pos.position))

            if qty <= MAX_ORDER_SIZE:
                order = MarketOrder(action, qty)
                order.tif = 'DAY'
                ib.placeOrder(contract, order)
                logger.info(f"  {symbol}: {action} {qty} shares (MKT via SMART)")
            else:
                remaining = qty
                leg = 1
                total_legs = -(-qty // MAX_ORDER_SIZE)
                while remaining > 0:
                    leg_qty = min(remaining, MAX_ORDER_SIZE)
                    order = MarketOrder(action, leg_qty)
                    order.tif = 'DAY'
                    ib.placeOrder(contract, order)
                    logger.info(f"  {symbol}: {action} {leg_qty} shares (MKT via SMART, leg {leg}/{total_legs})")
                    remaining -= leg_qty
                    leg += 1
                    ib.sleep(0.5)

        ib.sleep(2)

    # Final state
    logger.info(f"Final positions: {len(ib.positions())}")
    logger.info(f"Final orders: {len(ib.reqAllOpenOrders())}")
    logger.info("Done.")

    ib.disconnect()


if __name__ == "__main__":
    main()
