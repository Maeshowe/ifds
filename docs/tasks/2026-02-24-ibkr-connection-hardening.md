# Task: IBKR Connection Hardening

**Date:** 2026-02-24  
**Priority:** HIGH  
**Scope:** `scripts/paper_trading/lib/connection.py`  
**Trigger:** A paper trading scriptek (submit_orders.py, close_positions.py) cron-ból futnak — ha az IBKR gateway elakad vagy timeout-ol, csendben fail-elnek (`sys.exit(1)`). Nincs retry, nincs Telegram alert, nincs graceful error. OBSIDIAN adatintegritási kockázat.

---

## Jelenlegi állapot

```python
def connect(host='127.0.0.1', port=PAPER_PORT, client_id=DEFAULT_CLIENT_ID):
    ib = IB()
    try:
        ib.connect(host, port, clientId=client_id)
        ib.sleep(2)
        logger.info(f"Connected to IBKR: {host}:{port} (clientId={client_id})")
        return ib
    except Exception as e:
        logger.error(f"IBKR connection FAILED (clientId={client_id}): {e}")
        sys.exit(1)   # ← csendesen meghal, nincs retry, nincs alert
```

**Problémák:**
1. Egyetlen próbálkozás — ha az IBKR gateway épp újraindul (ami reggel megtörténhet), azonnal fail
2. `sys.exit(1)` — a cron process meghal, de semmi nem jelzi ezt Telegramon
3. Timeout nincs konfigurálva — `ib_insync` default timeout (pl. 10s) érvényesül, nem kontrollált
4. Port konstans (`PAPER_PORT = 7497`) a connection.py-ban van, de a hívó script-ek hardcode-olhatnak másik értéket — ellenőrzendő

---

## Implementáció

### `scripts/paper_trading/lib/connection.py` — teljes csere

```python
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

# Port konstansok — egyetlen helyen definiálva
PAPER_PORT = 7497
LIVE_PORT = 7496
DEFAULT_CLIENT_ID = 10

# Retry konfiguráció — környezeti változóból override-olható
CONNECT_MAX_RETRIES = int(os.getenv("IBKR_CONNECT_MAX_RETRIES", "3"))
CONNECT_RETRY_DELAY = float(os.getenv("IBKR_CONNECT_RETRY_DELAY", "5.0"))  # másodperc
CONNECT_TIMEOUT = float(os.getenv("IBKR_CONNECT_TIMEOUT", "15.0"))  # másodperc


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
        pass  # Telegram failure soha nem blokkolhat


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
        max_retries: Number of connection attempts (default: 3, env: IBKR_CONNECT_MAX_RETRIES)
        retry_delay: Seconds between retries (default: 5.0, env: IBKR_CONNECT_RETRY_DELAY)
        timeout: Connection timeout in seconds (default: 15.0, env: IBKR_CONNECT_TIMEOUT)

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
        f"🚨 <b>IBKR CONNECTION FAILED</b>\n"
        f"Host: {host}:{port} | ClientId: {client_id}\n"
        f"Attempts: {max_retries}/{max_retries}\n"
        f"Last error: {last_error}\n"
        f"<b>Paper trading script aborted — manual intervention required.</b>"
    )
    logger.error(
        f"IBKR connection FAILED after {max_retries} attempts "
        f"(clientId={client_id}): {last_error}"
    )
    _send_telegram_alert(error_msg)
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
```

---

## Hívó script-ek — nincs változtatás szükséges

A `connect()` szignatúra backward compatible — a hívók (`submit_orders.py`, `close_positions.py`) változatlanul működnek:

```python
# submit_orders.py — változatlan hívás
ib = connect(client_id=10)

# close_positions.py — változatlan hívás  
ib = connect(client_id=11)
```

A retry/timeout/alert automatikusan aktív. Ha szükséges, environment variable-lal override-olható:
```bash
IBKR_CONNECT_MAX_RETRIES=5 IBKR_CONNECT_RETRY_DELAY=10 python submit_orders.py
```

---

## Tesztelés

```python
# tests/test_ibkr_connection.py

from unittest.mock import patch, MagicMock, call
import pytest
import sys

from scripts.paper_trading.lib.connection import connect, PAPER_PORT


def test_connect_success_first_attempt():
    """Sikeres kapcsolat első próbálkozásra."""
    mock_ib = MagicMock()
    with patch("scripts.paper_trading.lib.connection.IB", return_value=mock_ib):
        result = connect(client_id=10, max_retries=3)
    mock_ib.connect.assert_called_once_with("127.0.0.1", PAPER_PORT, clientId=10, timeout=15.0)
    assert result is mock_ib


def test_connect_retry_then_success():
    """Első próba fail, második sikeres."""
    mock_ib = MagicMock()
    mock_ib.connect.side_effect = [Exception("timeout"), None]
    with patch("scripts.paper_trading.lib.connection.IB", return_value=mock_ib):
        with patch("scripts.paper_trading.lib.connection.time.sleep"):
            result = connect(client_id=10, max_retries=3, retry_delay=0)
    assert mock_ib.connect.call_count == 2
    assert result is mock_ib


def test_connect_all_retries_fail_exits():
    """Minden próba fail → sys.exit(1)."""
    mock_ib = MagicMock()
    mock_ib.connect.side_effect = Exception("connection refused")
    with patch("scripts.paper_trading.lib.connection.IB", return_value=mock_ib):
        with patch("scripts.paper_trading.lib.connection.time.sleep"):
            with patch("scripts.paper_trading.lib.connection._send_telegram_alert") as mock_tg:
                with pytest.raises(SystemExit) as exc_info:
                    connect(client_id=10, max_retries=3, retry_delay=0)
    assert exc_info.value.code == 1
    assert mock_ib.connect.call_count == 3
    mock_tg.assert_called_once()


def test_connect_telegram_alert_on_failure():
    """Telegram alert tartalmazza a helyes infót."""
    mock_ib = MagicMock()
    mock_ib.connect.side_effect = Exception("gateway down")
    with patch("scripts.paper_trading.lib.connection.IB", return_value=mock_ib):
        with patch("scripts.paper_trading.lib.connection.time.sleep"):
            with patch("scripts.paper_trading.lib.connection._send_telegram_alert") as mock_tg:
                with pytest.raises(SystemExit):
                    connect(host="127.0.0.1", port=7497, client_id=10, max_retries=2, retry_delay=0)
    alert_msg = mock_tg.call_args[0][0]
    assert "IBKR CONNECTION FAILED" in alert_msg
    assert "127.0.0.1:7497" in alert_msg
    assert "clientId: 10" in alert_msg  # vagy hasonló formátum
    assert "2/2" in alert_msg


def test_connect_telegram_failure_does_not_raise():
    """Telegram hiba nem blokkolja a sys.exit-et."""
    mock_ib = MagicMock()
    mock_ib.connect.side_effect = Exception("fail")
    with patch("scripts.paper_trading.lib.connection.IB", return_value=mock_ib):
        with patch("scripts.paper_trading.lib.connection.time.sleep"):
            with patch("scripts.paper_trading.lib.connection._send_telegram_alert",
                       side_effect=Exception("telegram down")):
                with pytest.raises(SystemExit):
                    connect(client_id=10, max_retries=1, retry_delay=0)


def test_env_override_max_retries(monkeypatch):
    """IBKR_CONNECT_MAX_RETRIES env var override."""
    monkeypatch.setenv("IBKR_CONNECT_MAX_RETRIES", "1")
    # Reimport to pick up env
    import importlib
    import scripts.paper_trading.lib.connection as conn_module
    importlib.reload(conn_module)
    assert conn_module.CONNECT_MAX_RETRIES == 1
```

---

## Git

```bash
git add scripts/paper_trading/lib/connection.py tests/test_ibkr_connection.py
git commit -m "feat: IBKR connection hardening — retry + timeout + Telegram alert (BC18)

- connect(): retry loop (default 3x, 5s delay, 15s timeout)
- Telegram alert after all retries exhausted
- Configurable via env: IBKR_CONNECT_MAX_RETRIES, IBKR_CONNECT_RETRY_DELAY,
  IBKR_CONNECT_TIMEOUT
- Backward compatible: hívó script-ek változatlanok
- 6 unit teszt

Fixes: silent cron failure when IBKR gateway hangs or restarts"
git push
```

---

## Megjegyzések

- **Timeout paraméter:** az `ib_insync` `connect()` elfogad `timeout` paramétert — ezzel kontrollált a várakozás
- **`ib.disconnect()` a retry loop-ban:** fontos, különben a következő `IB()` instance port konfliktusba futhat
- **`_send_telegram_alert` non-blocking:** bármilyen Telegram hiba csendesen elnyelve — soha nem akadályozza a `sys.exit`-et
- **Env override:** cron script-ből könnyen tesztelhető más értékekkel anélkül hogy a kódot módosítani kellene
