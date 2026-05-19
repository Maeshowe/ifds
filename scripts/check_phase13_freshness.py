#!/usr/bin/env python3
"""Phase 1-3 weekly freshness check — heti vasárnap esti rebalance verifikáció.

Runs at Sunday 23:00 CEST via cron (1h time-window az 22:00 heti macro
pipeline-nak). Detects:

- ``state/phase13_ctx.json.gz`` missing → Telegram alert (silent fail az
  egész heti context generálása)
- ``state/phase13_ctx.json.gz`` mtime > ``MAX_AGE_HOURS`` órás → Telegram
  alert (silent fail variant — pl. _exclude_earnings thread hang
  per `04-risks` §8.2.3)
- Egyébként silent exit 0 (verbose mode esetén heartbeat)

A swing pivot architektúrában a Phase 4-6 daily futások a vasárnap esti
context-ből dolgoznak — ha az silent-fail-el, a teljes következő hét
stale sector context-tel megy.

Usage:
    python scripts/check_phase13_freshness.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

try:
    from lib.log_setup import setup_pt_logger
    logger = setup_pt_logger("phase13_freshness")
except ModuleNotFoundError:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    logger = logging.getLogger('phase13_freshness')


CONTEXT_PATH = Path("state/phase13_ctx.json.gz")
MAX_AGE_HOURS = 1.0


# ---------------------------------------------------------------------------
# Pure helper (testable without IO)
# ---------------------------------------------------------------------------

def classify_freshness(
    context_path: Path,
    now: datetime,
    max_age_hours: float = MAX_AGE_HOURS,
) -> tuple[str, str]:
    """Classify the Phase 1-3 context freshness.

    Returns ``(status, detail)`` where status is one of:
      - ``"missing"`` — file does not exist
      - ``"stale"`` — file exists but mtime > max_age_hours
      - ``"fresh"`` — file exists and mtime within window
    """
    if not context_path.exists():
        return "missing", f"file not found at {context_path}"
    mtime = datetime.fromtimestamp(context_path.stat().st_mtime)
    age = now - mtime
    age_hours = age.total_seconds() / 3600.0
    if age > timedelta(hours=max_age_hours):
        return "stale", f"mtime {mtime:%Y-%m-%d %H:%M}, age {age_hours:.1f}h"
    return "fresh", f"mtime {mtime:%Y-%m-%d %H:%M}, age {age_hours:.2f}h"


# ---------------------------------------------------------------------------
# Telegram helper
# ---------------------------------------------------------------------------

def send_telegram(message: str) -> None:
    """Send message via Telegram Bot API with CET timestamp header."""
    try:
        sys.path.insert(0, str(Path(__file__).parent / "paper_trading"))
        from lib.telegram_helper import telegram_header
        from lib.telegram_helper import send_telegram as _send
        _send(f"{telegram_header('PHASE13')}\n{message}")
    except Exception as exc:
        logger.error(f"Telegram send failed: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    logger.info(f"Phase 1-3 freshness check — {datetime.now():%Y-%m-%d %H:%M:%S CEST}")
    status, detail = classify_freshness(CONTEXT_PATH, datetime.now())
    logger.info(f"Status: {status} ({detail})")

    if status == "missing":
        send_telegram(
            f"❌ Phase 1-3 context FILE MISSING — {detail}\n\n"
            f"A vasárnapi 22:00 heti macro cron silent-failed.\n"
            f"Manuális futtatás: ./scripts/deploy_daily.sh --phases 1-3"
        )
        return 1

    if status == "stale":
        send_telegram(
            f"⚠️ Phase 1-3 context STALE — {detail}\n\n"
            f"A vasárnapi 22:00 heti macro cron silent-fail gyanú.\n"
            f"Manuális futtatás: ./scripts/deploy_daily.sh --phases 1-3"
        )
        return 1

    # Fresh — optional heartbeat
    if os.getenv("IFDS_HEARTBEAT_VERBOSE", "").lower() in ("1", "true", "yes"):
        send_telegram(f"✓ Phase 1-3 context fresh ({detail})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
