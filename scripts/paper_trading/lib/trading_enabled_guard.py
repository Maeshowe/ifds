"""Trading-enabled guard for paper trading scripts (gate-protocol §D8).

Sibling of :func:`lib.trading_day_guard.check_trading_day`. Call
``check_trading_enabled()`` at the start of the ``main()`` of every script that
places orders or connects to IBKR. Exits cleanly when trading is paused, so the
remaining pipeline phases (Phase 1-3, Phase 4-6, snapshots, event store) keep
running and the research data stream is unaffected.

Why a state file rather than commented-out crontab lines (Tamás, 2026-10-03):
a commented cron line is undocumented production state — in two months nobody
knows what was changed or why, and re-enabling is error-prone. The crontab stays
as the record of INTENDED behaviour; this switch records the deviation.

Why a file rather than an env var: the Mini's cron entries do not all
``source .env``, so an env var would not reach every job.

Switch semantics (``state/trading_enabled.json``):

* file absent          → **enabled** (unchanged behaviour; a missing switch is
  not a pause, so a fresh clone behaves normally)
* ``{"enabled": true}``  → enabled
* ``{"enabled": false}`` → paused, clean ``exit(0)``
* unreadable / malformed / missing or non-bool ``enabled``
  → **paused** (fail CLOSED): a truncated or half-written switch must never be
  read as "trading is fine".

Set ``IFDS_SKIP_TRADING_ENABLED_GUARD=1`` to bypass, or
``IFDS_TRADING_SWITCH_PATH`` to point at a different switch (tests only).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

#: Production switch location, resolved relative to the repo root.
DEFAULT_STATE_PATH: Path = Path(__file__).resolve().parents[3] / "state" / "trading_enabled.json"

_ENV_SKIP = "IFDS_SKIP_TRADING_ENABLED_GUARD"
#: Override the switch location (tests, and callers without a ``state_path`` arg).
_ENV_PATH = "IFDS_TRADING_SWITCH_PATH"


def _log(logger, level: str, msg: str) -> None:
    target = logger or logging.getLogger("trading_enabled_guard")
    getattr(target, level)(msg)


def read_switch(state_path: Path | None = None) -> tuple[bool, str]:
    """Return ``(enabled, reason)`` for the switch at ``state_path``.

    Never raises: any problem reading or interpreting the file yields
    ``(False, <why>)`` so the caller fails closed.
    """
    if state_path is not None:
        path = Path(state_path)
    elif os.environ.get(_ENV_PATH):
        path = Path(os.environ[_ENV_PATH])
    else:
        path = DEFAULT_STATE_PATH

    if not path.exists():
        return True, "no switch file — trading enabled (default)"

    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"switch file unreadable ({exc}) — failing CLOSED"

    if not isinstance(payload, dict) or "enabled" not in payload:
        return False, "switch file has no 'enabled' key — failing CLOSED"

    enabled = payload["enabled"]
    if not isinstance(enabled, bool):
        return False, f"'enabled' is not a bool ({enabled!r}) — failing CLOSED"

    return enabled, str(payload.get("reason") or "no reason recorded")


def check_trading_enabled(logger=None, state_path: Path | None = None) -> None:
    """Exit cleanly (code 0) if trading is paused. No Telegram, one log line."""
    if os.environ.get(_ENV_SKIP):
        return

    enabled, reason = read_switch(state_path)
    if enabled:
        return

    _log(logger, "info", f"Trading disabled — exiting cleanly. Reason: {reason}")
    sys.exit(0)
