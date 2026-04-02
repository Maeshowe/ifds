"""Shared Telegram message formatting helpers for paper trading scripts."""

import os
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]


CET = ZoneInfo("Europe/Budapest")


def telegram_header(script_name: str) -> str:
    """Return standardized Telegram message header with CET timestamp.

    Format: [YYYY-MM-DD HH:MM CET] SCRIPT_NAME
    Example: [2026-04-02 15:35 CET] SUBMIT
    """
    now = datetime.now(CET)
    return f"[{now.strftime('%Y-%m-%d %H:%M')} CET] {script_name}"


def send_telegram(message: str) -> None:
    """Send message via Telegram Bot API (shared implementation)."""
    import logging
    import requests

    logger = logging.getLogger("telegram_helper")
    token = os.getenv("IFDS_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("IFDS_TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")
