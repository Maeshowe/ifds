#!/usr/bin/env python3
"""IBKR Paper Trading — Submit heartbeat monitor (dead-man switch).

Runs ~15 minutes after the scheduled `submit_orders.py` window
(e.g. 16:35 CEST = 5 min after the 16:20 cron window closes).

Compares `state/last_submit_attempt.json` and `state/last_submit_success.json`:

* `success` newer than `attempt` (or within STUCK_THRESHOLD)  → OK
* `attempt` newer than `success` by > STUCK_THRESHOLD          → STUCK alert
* `attempt` older than MISSING_THRESHOLD on a trading day      → MISSING alert
* Both heartbeats missing                                       → COLD_START (no alert)

The alert path goes through `lib.connection._send_telegram_alert`, which
logs failures at WARNING level (§11 fix) — so a Telegram outage on this
secondary path stays visible in the gateway log even though it cannot
itself self-report.

Fázis 1 task: docs/tasks/2026-05-19-ibkr-gateway-monitoring.md §10 Fix C.
"""
import os
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Allow `from lib.*` imports when invoked directly
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib.heartbeat import read as heartbeat_read

try:
    from lib.log_setup import setup_pt_logger
    logger = setup_pt_logger("heartbeat_monitor")
except ModuleNotFoundError:
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("heartbeat_monitor")

STUCK_THRESHOLD_S = float(os.getenv("IFDS_HEARTBEAT_STUCK_S", "900"))      # 15 min
# Threshold accommodates the lib.retry_orchestrator outer-retry budget:
# 5 attempts × exponential backoff (15s→30s→60s→120s→240s) → ~465s submit
# + per-attempt submit work (~30s × 5 = 150s) → ~10-12 min realistic worst
# case. The 900s (15 min) threshold gives a buffer before the heartbeat
# fires a STUCK alert that duplicates the orchestrator's own Telegram
# critical alert on exhaustion.
# Day 3 (2026-05-20) the old 300s threshold tripped at 15:45 while the
# orchestrator (post-fix) would still have been mid-retry — operator got
# a misleading STUCK alert on top of normal recovery in progress.
# Override: ``IFDS_HEARTBEAT_STUCK_S`` env var (e.g. 300 to revert).
MISSING_THRESHOLD_S = float(os.getenv("IFDS_HEARTBEAT_MISSING_S", str(26 * 3600)))  # 26h


def is_trading_day(today: date | None = None) -> bool:
    """True if `today` is a US equity trading day (best-effort)."""
    today = today or date.today()
    try:
        from ifds.utils.trading_calendar import is_trading_day as _is
        return _is(today)
    except Exception:
        return today.weekday() < 5


def check_heartbeat(now_epoch: float | None = None,
                    state_dir: Path | None = None,
                    stuck_threshold_s: float = STUCK_THRESHOLD_S,
                    missing_threshold_s: float = MISSING_THRESHOLD_S
                    ) -> tuple[str, str]:
    """Pure verdict — decoupled from Telegram + trading-day for testability.

    Returns (verdict, message) where verdict is one of
    'OK' | 'STUCK' | 'MISSING' | 'COLD_START'.
    """
    if now_epoch is None:
        now_epoch = time.time()

    attempt = heartbeat_read("submit_attempt", state_dir=state_dir)
    success = heartbeat_read("submit_success", state_dir=state_dir)

    if attempt is None and success is None:
        return "COLD_START", "No heartbeat history yet (first run?)"

    if attempt is None:
        return "MISSING", (
            "submit_orders DID NOT RUN: last_submit_attempt.json missing"
        )

    attempt_epoch = attempt.get("epoch", 0)
    attempt_age = now_epoch - attempt_epoch
    if attempt_age > missing_threshold_s:
        hours = attempt_age / 3600.0
        return "MISSING", (
            f"submit_orders DID NOT RUN today: last attempt {hours:.1f}h ago "
            f"({attempt.get('timestamp_utc')})"
        )

    if success is None:
        return "STUCK", (
            f"submit_orders STUCK: attempt at {attempt.get('timestamp_utc')} "
            f"but no success recorded"
        )

    success_epoch = success.get("epoch", 0)
    if success_epoch < attempt_epoch:
        delta = attempt_epoch - success_epoch
        if delta > stuck_threshold_s:
            return "STUCK", (
                f"submit_orders STUCK: attempt at {attempt.get('timestamp_utc')} "
                f"is {delta:.0f}s newer than last success at "
                f"{success.get('timestamp_utc')} (threshold {stuck_threshold_s:.0f}s)"
            )

    return "OK", (
        f"submit_orders heartbeat OK "
        f"(attempt={attempt.get('timestamp_utc')}, "
        f"success={success.get('timestamp_utc')})"
    )


def _send_alert(message: str) -> None:
    from lib.connection import _send_telegram_alert
    _send_telegram_alert(message)


def main() -> None:
    today = date.today()
    if not is_trading_day(today):
        logger.info(f"{today} is not a trading day — heartbeat check skipped")
        return

    verdict, message = check_heartbeat()
    logger.info(f"[{verdict}] {message}")

    if verdict in ("STUCK", "MISSING"):
        alert = (
            f"\U0001f6a8 <b>IBKR submit heartbeat: {verdict}</b>\n"
            f"{message}\n"
            f"<b>Manual check needed — paper trading may have silently failed.</b>"
        )
        _send_alert(alert)
        sys.exit(2)

    if verdict == "COLD_START":
        logger.info("No alert sent — cold start (no prior heartbeat history)")


if __name__ == "__main__":
    main()
