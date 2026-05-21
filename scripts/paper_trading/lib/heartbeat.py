"""IBKR Paper Trading — Submit heartbeat (file-based dead-man switch).

The `submit_orders.py` script writes a heartbeat at start (`submit_attempt`)
and at successful completion (`submit_success`). An independent monitor
cron job compares the two: if `attempt > success` by more than a threshold,
or if `attempt` is older than 26h on a trading day, the monitor fires a
Telegram alert.

This sits OUTSIDE the `connect()` Telegram path so that if the in-band
alert silently fails (env var missing, HTTP 4xx, network), the heartbeat
monitor still catches the regression.

Fázis 1 task: docs/tasks/2026-05-19-ibkr-gateway-monitoring.md §10 Fix C.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_STATE_DIR = Path(os.getenv("IFDS_STATE_DIR", "state"))


def _resolve_dir(state_dir: Path | None) -> Path:
    return state_dir if state_dir is not None else DEFAULT_STATE_DIR


def state_path(event: str, state_dir: Path | None = None) -> Path:
    """Return the heartbeat file path for the given event."""
    return _resolve_dir(state_dir) / f"last_{event}.json"


def touch(
    event: str, label: str | None = None, state_dir: Path | None = None, extra: dict | None = None
) -> Path:
    """Write a heartbeat marker for `event` (e.g. 'submit_attempt').

    Uses UTC ISO 8601 timestamps and atomic write (tmp + rename).
    Failures are logged at WARNING and never raise — heartbeat must
    never block the calling script.

    Returns the path that was written (or attempted).
    """
    base = _resolve_dir(state_dir)
    target = base / f"last_{event}.json"
    payload = {
        "event": event,
        "label": label,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "epoch": int(time.time()),
    }
    if extra:
        payload.update(extra)
    try:
        base.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2))
        tmp.replace(target)
    except Exception as e:
        logger.warning(f"Heartbeat write failed for {event}: {e}")
    return target


def read(event: str, state_dir: Path | None = None) -> dict | None:
    """Read a heartbeat marker. Returns None if missing or unreadable."""
    target = state_path(event, state_dir)
    if not target.exists():
        return None
    try:
        return json.loads(target.read_text())
    except Exception as e:
        logger.warning(f"Heartbeat read failed for {event}: {e}")
        return None
