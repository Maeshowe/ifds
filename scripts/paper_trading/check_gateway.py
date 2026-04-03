#!/usr/bin/env python3
"""IBKR Gateway pre-flight health check.

Runs 5 minutes before submit_orders.py (e.g. 15:30 CET).
Quick connection test with short timeout — sends Telegram alert if Gateway is down.

Usage:
    python scripts/paper_trading/check_gateway.py
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()

try:
    from lib.log_setup import setup_pt_logger
    logger = setup_pt_logger("gateway")
except ModuleNotFoundError:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    logger = logging.getLogger('gateway')

# Short timeout for health check — fail fast
HEALTH_CHECK_TIMEOUT = 3.0
HEALTH_CHECK_RETRIES = 1
HEALTH_CHECK_RETRY_DELAY = 2.0


def main() -> None:
    from lib.connection import connect, disconnect

    logger.info("IBKR Gateway health check starting...")

    ib = connect(
        client_id=17,
        max_retries=HEALTH_CHECK_RETRIES,
        retry_delay=HEALTH_CHECK_RETRY_DELAY,
        timeout=HEALTH_CHECK_TIMEOUT,
    )

    # If we reach here, connection succeeded (connect() calls sys.exit on failure)
    logger.info("Gateway OK — connection successful")
    disconnect(ib)


if __name__ == "__main__":
    main()
