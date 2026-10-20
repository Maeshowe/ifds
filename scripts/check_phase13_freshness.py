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

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )
    logger = logging.getLogger("phase13_freshness")


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


def classify_provenance(path: Path) -> tuple[str, str]:
    """Classify the context's UNIVERSE provenance (D-U1/F-5, 2026-10-20).

    Age is not the only way a context can be wrong. Between 2026-08-16 and 10-19 the
    context was FRESH every week and built on a silently substituted population: the
    membership source had died and Phase 2 fell open to the FMP screener, swapping
    377 of 730 names (52%) for non-members. This heartbeat watched the mtime and saw
    nothing wrong, because the mtime was fine.

    Returns ``("ok" | "degraded" | "unknown", detail)``.
    """
    import gzip
    import json

    try:
        with gzip.open(path, "rt") as handle:
            prov = (json.load(handle) or {}).get("universe_provenance") or {}
    except (OSError, json.JSONDecodeError, EOFError) as exc:
        return "unknown", f"context unreadable: {exc}"

    if not prov:
        return "unknown", "no universe_provenance recorded (context predates 2026-10-20)"

    definition = prov.get("universe_definition", "?")
    membership = prov.get("membership") or {}
    bits = [
        f"definition={definition}",
        f"built={prov.get('built', '?')}",
        f"membership={membership.get('count', '?')} via {membership.get('source', '?')}",
    ]
    if prov.get("degraded") or "degraded" in str(definition):
        return "degraded", ", ".join(bits)
    if membership.get("degraded_stale"):
        bits.append(f"membership STALE {membership.get('age_days')}d")
        return "degraded", ", ".join(bits)
    return "ok", ", ".join(bits)


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

    # Fresh by age — now also check WHAT it was built on (F-5).
    prov_status, prov_detail = classify_provenance(CONTEXT_PATH)
    logger.info(f"Provenance: {prov_status} ({prov_detail})")

    if prov_status == "degraded":
        send_telegram(
            f"🔴 Phase 1-3 context DEGRADED UNIVERSE — {prov_detail}\n\n"
            f"A context FRISS, de nem a tervezett univerzumon épült. "
            f"2026-08-16 és 10-19 között ez 9 hétig észrevétlen maradt, mert a "
            f"heartbeat csak a KORT nézte.\n"
            f"Ellenőrizd a membership-forrást és a `breadth_enabled` kulcsot."
        )
        return 1

    if prov_status == "unknown":
        send_telegram(
            f"⚠️ Phase 1-3 context PROVENANCE UNKNOWN — {prov_detail}\n\n"
            f"A kor rendben ({detail}), de nem tudjuk, milyen univerzumon épült."
        )
        return 1

    # Fresh and built on the intended universe — optional heartbeat
    if os.getenv("IFDS_HEARTBEAT_VERBOSE", "").lower() in ("1", "true", "yes"):
        send_telegram(f"✓ Phase 1-3 context fresh ({detail}; {prov_detail})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
