"""Telegram alerts — optional trade signal notifications (BC13).

Sends trade plan summary to a Telegram chat via Bot API.
Only active when both IFDS_TELEGRAM_BOT_TOKEN and IFDS_TELEGRAM_CHAT_ID are set.
Non-blocking: failures are logged but never halt the pipeline.
"""

import requests

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity
from ifds.models.market import PositionSizing


def send_trade_alerts(positions: list[PositionSizing], strategy: str,
                      config: Config, logger: EventLogger) -> bool:
    """Send trade plan summary to Telegram.

    Args:
        positions: Sized positions from Phase 6.
        strategy: "long" or "short".
        config: Pipeline config (telegram_bot_token, telegram_chat_id).
        logger: Event logger.

    Returns:
        True if sent successfully, False otherwise.
    """
    token = config.runtime.get("telegram_bot_token")
    chat_id = config.runtime.get("telegram_chat_id")
    timeout = config.runtime.get("telegram_timeout", 5)

    if not token or not chat_id:
        logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                   message="Telegram alerts disabled (no credentials)")
        return False

    if not positions:
        logger.log(EventType.PHASE_DIAGNOSTIC, Severity.DEBUG,
                   message="Telegram: no positions to send")
        return False

    try:
        text = _format_message(positions, strategy)
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()

        logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO,
                   message=f"Telegram alert sent: {len(positions)} positions")
        return True

    except Exception as e:
        logger.log(EventType.CONFIG_WARNING, Severity.WARNING,
                   message=f"Telegram alert failed: {e}")
        return False


def _format_message(positions: list[PositionSizing], strategy: str) -> str:
    """Format positions into a Telegram message."""
    lines = [f"*IFDS Trade Plan* ({strategy.upper()}, {len(positions)} positions)\n"]
    for pos in positions:
        lines.append(
            f"`{pos.ticker}` {pos.direction} | "
            f"Score: {pos.combined_score:.1f} | "
            f"{pos.sector}\n"
            f"  Stop: ${pos.stop_loss:.2f} | TP1: ${pos.take_profit_1:.2f}"
        )
    return "\n".join(lines)
