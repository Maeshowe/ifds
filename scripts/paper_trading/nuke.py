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
import sys
import time

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from ib_insync import IB, MarketOrder

HOST = '127.0.0.1'
PORT = 7497
CLIENT_ID = 99  # Dedicated for nuke script


def main():
    parser = argparse.ArgumentParser(description="Cancel all orders & close all positions")
    parser.add_argument('--orders', action='store_true', help='Cancel orders only')
    parser.add_argument('--positions', action='store_true', help='Close positions only')
    parser.add_argument('--dry-run', action='store_true', help='Show what would happen')
    args = parser.parse_args()

    # Default: do both
    do_orders = args.orders or (not args.orders and not args.positions)
    do_positions = args.positions or (not args.orders and not args.positions)

    ib = IB()
    try:
        ib.connect(HOST, PORT, clientId=CLIENT_ID)
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}IBKR Paper Trading — Nuke\n")

    # Show current state
    positions = ib.positions()
    open_orders = ib.reqAllOpenOrders()

    print(f"  Open positions: {len(positions)}")
    for pos in positions:
        print(f"    {pos.contract.symbol}: {pos.position} shares")

    print(f"  Open orders: {len(open_orders)}")

    if args.dry_run:
        print("\n  [DRY RUN] No action taken.")
        ib.disconnect()
        return

    # Cancel orders
    if do_orders and open_orders:
        print(f"\n  Cancelling {len(open_orders)} orders...")
        ib.reqGlobalCancel()
        ib.sleep(2)
        remaining = ib.reqAllOpenOrders()
        print(f"  Done. Remaining orders: {len(remaining)}")

    # Close positions
    if do_positions and positions:
        print(f"\n  Closing {len(positions)} positions at MARKET...")
        for pos in positions:
            symbol = pos.contract.symbol
            con_id = pos.contract.conId

            # Skip non-tradable contracts (e.g. CVR, warrants)
            if '.CVR' in symbol or pos.contract.secType != 'STK':
                print(f"    {symbol}: SKIP (non-tradable)")
                continue

            # Create fresh contract with SMART routing
            from ib_insync import Stock
            contract = Stock(conId=con_id, exchange='SMART')
            ib.qualifyContracts(contract)

            action = 'SELL' if pos.position > 0 else 'BUY'
            qty = abs(pos.position)

            order = MarketOrder(action, qty)
            order.tif = 'DAY'
            ib.placeOrder(contract, order)
            print(f"    {symbol}: {action} {qty} shares (MKT via SMART)")

        ib.sleep(2)

    # Final state
    print(f"\n  Final positions: {len(ib.positions())}")
    print(f"  Final orders: {len(ib.reqAllOpenOrders())}")
    print("  Done.\n")

    ib.disconnect()


if __name__ == "__main__":
    main()
