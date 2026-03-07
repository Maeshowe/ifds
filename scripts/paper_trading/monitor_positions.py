#!/usr/bin/env python3
"""IFDS Paper Trading — Leftover position monitor.

Runs at 09:10 UTC (10:10 CET) after the daily pipeline.
Detects open IBKR positions not in today's execution plan CSV
and sends Telegram WARNING with ticker + qty details.

Usage:
    python scripts/paper_trading/monitor_positions.py
"""
import csv
import glob
import logging
import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("monitor_positions")

EXECUTION_PLAN_DIR = "output"


def send_telegram(message: str) -> None:
    import requests

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


def get_todays_plan_symbols() -> set:
    """Load ticker symbols from today's execution plan CSV."""
    today = date.today().strftime("%Y%m%d")
    pattern = f"{EXECUTION_PLAN_DIR}/execution_plan_run_{today}_*.csv"
    files = sorted(glob.glob(pattern))
    if not files:
        logger.warning("No execution plan CSV found for today")
        return set()
    symbols = set()
    with open(files[-1], newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbols.add(row["instrument_id"])
    return symbols


def main() -> None:
    from lib.connection import connect, disconnect

    today_str = date.today().strftime("%Y-%m-%d")
    logger.info(f"Leftover position monitor — {today_str}")

    plan_symbols = get_todays_plan_symbols()
    logger.info(
        f"Today's plan: {sorted(plan_symbols) if plan_symbols else 'none found'}"
    )

    ib = connect(client_id=14)
    ib.sleep(3)

    positions = [
        p
        for p in ib.positions()
        if p.position != 0
        and ".CVR" not in p.contract.symbol
        and p.contract.secType == "STK"
    ]

    leftover = [p for p in positions if p.contract.symbol not in plan_symbols]

    if leftover:
        lines = [f"LEFTOVER POSITIONS — {today_str}"]
        for p in leftover:
            lines.append(
                f"  {p.contract.symbol}: {p.position:+.0f} shares (NOT in today plan)"
            )
        lines.append("Action: nuke.py before market open or manual close in IBKR.")
        msg = "\n".join(lines)
        logger.warning(msg)
        send_telegram(msg)
    else:
        logger.info("No leftover positions — all clear.")

    disconnect(ib)


if __name__ == "__main__":
    main()
