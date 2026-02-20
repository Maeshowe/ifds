"""IBKR Paper Trading — Connection Manager"""
import asyncio
import logging
import sys

# Python 3.14+: event loop must exist before importing ib_insync
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from ib_insync import IB

logger = logging.getLogger(__name__)

PAPER_PORT = 7497
DEFAULT_CLIENT_ID = 10


def connect(host='127.0.0.1', port=PAPER_PORT, client_id=DEFAULT_CLIENT_ID):
    """Connect to IBKR Gateway. Exits on failure."""
    ib = IB()
    try:
        ib.connect(host, port, clientId=client_id)
        ib.sleep(2)  # Wait for initial synchronization
        logger.info(f"Connected to IBKR: {host}:{port} (clientId={client_id})")
        return ib
    except Exception as e:
        logger.error(f"IBKR connection FAILED (clientId={client_id}): {e}")
        sys.exit(1)


def get_account(ib):
    """Get paper trading account (starts with 'D')."""
    accounts = ib.managedAccounts()
    target = next((a for a in accounts if a.startswith('D')), accounts[0])
    logger.info(f"Account: {target}")
    return target


def disconnect(ib):
    """Safely disconnect from IBKR."""
    try:
        ib.disconnect()
    except Exception:
        pass
