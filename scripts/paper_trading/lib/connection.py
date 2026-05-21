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


class IBKRConnectionExhausted(Exception):
    """Raised by ``connect(raise_on_exhaust=True)`` when all internal
    retry attempts are exhausted.

    The default behaviour of :func:`connect` is backwards-compatible:
    ``sys.exit(1)`` after a Telegram alert. Callers that need to wrap
    the connect call in an outer retry loop (e.g. the swing submit
    orchestrator on Day 3-style Gateway-down windows) pass
    ``raise_on_exhaust=True`` and catch this exception.

    Refs: docs/tasks/2026-05-21-submit-retry-storm.md
    """

    def __init__(self, message: str, last_error: Exception | None = None):
        super().__init__(message)
        self.last_error = last_error


def _send_telegram_alert(message: str) -> None:
    """Send Telegram alert on connection failure. Non-blocking.

    Failures are logged at WARNING level (never raised) so the calling
    `connect()` can still `sys.exit(1)`. The previous `except: pass` made
    Telegram outages invisible — see ifds-rules.md (2026-05-19 monitoring
    task §11).
    """
    token = os.getenv("IFDS_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("IFDS_TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.warning(
            "Telegram alert NOT sent: IFDS_TELEGRAM_BOT_TOKEN or "
            "IFDS_TELEGRAM_CHAT_ID env var missing (cron env mismatch?)"
        )
        return
    try:
        import requests

        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=5,
        )
        if response.status_code >= 400:
            logger.warning(
                f"Telegram alert send failed: HTTP {response.status_code} — "
                f"{response.text[:200]}"
            )
    except Exception as e:
        logger.warning(f"Telegram alert send failed: {e}")


def connect(
    host: str = "127.0.0.1",
    port: int = PAPER_PORT,
    client_id: int = DEFAULT_CLIENT_ID,
    max_retries: int = CONNECT_MAX_RETRIES,
    retry_delay: float = CONNECT_RETRY_DELAY,
    timeout: float = CONNECT_TIMEOUT,
    context_label: str = "Paper trading script",
    raise_on_exhaust: bool = False,
) -> IB:
    """Connect to IBKR Gateway with retry logic.

    Retries up to max_retries times with retry_delay seconds between attempts.
    Sends Telegram alert on all retries failing.

    Args:
        host: Gateway host (default: 127.0.0.1)
        port: Gateway port (default: PAPER_PORT 7497)
        client_id: IBKR client ID
        max_retries: Number of connection attempts (default: 3)
        retry_delay: Seconds between retries (default: 5.0)
        timeout: Connection timeout in seconds (default: 15.0)
        raise_on_exhaust: If True, raise IBKRConnectionExhausted after all
            retries fail (caller responsible for outer retry / cleanup).
            Default False preserves the legacy ``sys.exit(1)`` behaviour
            used by the bulk of the paper-trading scripts.

    Returns:
        Connected IB instance.

    Raises:
        SystemExit(1) if all retries fail and ``raise_on_exhaust=False``.
        IBKRConnectionExhausted if all retries fail and ``raise_on_exhaust=True``.
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
            logger.info(f"Connected to IBKR: {host}:{port} (clientId={client_id})")
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
        f"\U0001f6a8 <b>IBKR CONNECTION FAILED</b> — {context_label}\n"
        f"Host: {host}:{port} | ClientId: {client_id}\n"
        f"Attempts: {max_retries}/{max_retries}\n"
        f"Last error: {last_error}\n"
        f"<b>{context_label} aborted — manual intervention required.</b>"
    )
    logger.error(
        f"IBKR connection FAILED after {max_retries} attempts "
        f"(clientId={client_id}): {last_error}"
    )
    try:
        _send_telegram_alert(error_msg)
    except Exception:
        pass  # Telegram failure must never prevent exit
    if raise_on_exhaust:
        raise IBKRConnectionExhausted(
            f"All {max_retries} attempts failed (clientId={client_id}, "
            f"host={host}:{port}): {last_error}",
            last_error=last_error,
        )
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
