"""IBKR Paper Trading — Connection Manager"""
import asyncio
import logging
import os
import sys
import time

# Python 3.14+: event loop must exist before importing ib_insync
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from ib_insync import IB

logger = logging.getLogger(__name__)

# Port constants — defined in one place
PAPER_PORT = 7497
LIVE_PORT = 7496
DEFAULT_CLIENT_ID = 10

# Retry configuration — overridable via environment variables
CONNECT_MAX_RETRIES = int(os.getenv("IBKR_CONNECT_MAX_RETRIES", "3"))
CONNECT_RETRY_DELAY = float(os.getenv("IBKR_CONNECT_RETRY_DELAY", "5.0"))
CONNECT_TIMEOUT = float(os.getenv("IBKR_CONNECT_TIMEOUT", "15.0"))


def _send_telegram_alert(message: str) -> None:
    """Send Telegram alert on connection failure. Non-blocking."""
    try:
        import requests
        token = os.getenv("IFDS_TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("IFDS_TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            return
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=5,
        )
    except Exception:
        pass  # Telegram failure must never block


def connect(
    host: str = "127.0.0.1",
    port: int = PAPER_PORT,
    client_id: int = DEFAULT_CLIENT_ID,
    max_retries: int = CONNECT_MAX_RETRIES,
    retry_delay: float = CONNECT_RETRY_DELAY,
    timeout: float = CONNECT_TIMEOUT,
) -> IB:
    """Connect to IBKR Gateway with retry logic.

    Retries up to max_retries times with retry_delay seconds between attempts.
    Sends Telegram alert on all retries failing.
    Exits with sys.exit(1) only after all retries exhausted.

    Args:
        host: Gateway host (default: 127.0.0.1)
        port: Gateway port (default: PAPER_PORT 7497)
        client_id: IBKR client ID
        max_retries: Number of connection attempts (default: 3)
        retry_delay: Seconds between retries (default: 5.0)
        timeout: Connection timeout in seconds (default: 15.0)

    Returns:
        Connected IB instance.

    Raises:
        SystemExit(1) if all retries fail.
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        ib = IB()
        try:
            logger.info(
                f"IBKR connect attempt {attempt}/{max_retries}: "
                f"{host}:{port} (clientId={client_id}, timeout={timeout}s)"
            )
            ib.connect(host, port, clientId=client_id, timeout=timeout)
            ib.sleep(2)  # Wait for initial synchronization
            logger.info(
                f"Connected to IBKR: {host}:{port} (clientId={client_id})"
            )
            return ib

        except Exception as e:
            last_error = e
            logger.warning(
                f"IBKR connection attempt {attempt}/{max_retries} FAILED "
                f"(clientId={client_id}): {e}"
            )
            try:
                ib.disconnect()
            except Exception:
                pass

            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)

    # All retries exhausted
    error_msg = (
        f"\U0001f6a8 <b>IBKR CONNECTION FAILED</b>\n"
        f"Host: {host}:{port} | ClientId: {client_id}\n"
        f"Attempts: {max_retries}/{max_retries}\n"
        f"Last error: {last_error}\n"
        f"<b>Paper trading script aborted — manual intervention required.</b>"
    )
    logger.error(
        f"IBKR connection FAILED after {max_retries} attempts "
        f"(clientId={client_id}): {last_error}"
    )
    try:
        _send_telegram_alert(error_msg)
    except Exception:
        pass  # Telegram failure must never prevent exit
    sys.exit(1)


def get_account(ib: IB) -> str:
    """Get paper trading account (starts with 'D')."""
    accounts = ib.managedAccounts()
    target = next((a for a in accounts if a.startswith("D")), accounts[0])
    logger.info(f"Account: {target}")
    return target


def disconnect(ib: IB) -> None:
    """Safely disconnect from IBKR."""
    try:
        ib.disconnect()
    except Exception:
        pass
