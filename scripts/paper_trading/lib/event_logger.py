"""Unified business event logger for paper trading.

Every PT script writes structured JSONL events to a shared daily file:
``logs/pt_events_{YYYY-MM-DD}.jsonl``

This is the **single source of truth** for daily trading activity.
Each script also keeps its own rotating text log (via log_setup.py).
"""

import json
import os
from datetime import datetime, timezone


class PTEventLogger:
    """Append-only JSONL writer for business events."""

    def __init__(self, log_dir: str = "logs") -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.path = os.path.join(log_dir, f"pt_events_{today}.jsonl")
        os.makedirs(log_dir, exist_ok=True)

    def log(self, script: str, event: str, **data: object) -> None:
        """Write one event line.

        Parameters
        ----------
        script:
            Short identifier (``"submit"``, ``"monitor"``, ...).
        event:
            Event name (``"order_submitted"``, ``"trail_activated_a"``, ...).
        **data:
            Arbitrary key-value pairs (ticker, qty, pnl, ...).
        """
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "script": script,
            "event": event,
            **data,
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
