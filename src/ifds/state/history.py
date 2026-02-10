"""BMI and sector history tracking.

Persists daily BMI values and sector momentum to JSON files in state/.
Used by the CLI dashboard to show day-over-day changes.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any


class BMIHistory:
    """Track daily BMI values in state/bmi_history.json.

    Format: list of {"date": "YYYY-MM-DD", "bmi": float, "regime": str}
    Keeps last 90 entries.
    """

    MAX_ENTRIES = 90

    def __init__(self, state_dir: str = "state"):
        self._path = Path(state_dir) / "bmi_history.json"

    def load(self) -> list[dict[str, Any]]:
        """Load history from disk."""
        if not self._path.exists():
            return []
        try:
            with open(self._path) as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
        return []

    def append(self, bmi_value: float, regime: str) -> None:
        """Append today's BMI value. Deduplicates by date."""
        today = date.today().isoformat()
        entries = self.load()

        # Replace existing entry for today, or append
        entries = [e for e in entries if e.get("date") != today]
        entries.append({"date": today, "bmi": round(bmi_value, 2), "regime": regime})

        # Keep only last MAX_ENTRIES
        entries = entries[-self.MAX_ENTRIES:]

        self._write(entries)

    def get_previous(self) -> dict[str, Any] | None:
        """Get the most recent entry BEFORE today (yesterday or last trading day)."""
        today = date.today().isoformat()
        entries = self.load()
        for entry in reversed(entries):
            if entry.get("date") != today:
                return entry
        return None

    def _write(self, entries: list[dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self._path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(entries, f, indent=2)
            os.replace(tmp, str(self._path))
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise


class SectorHistory:
    """Track daily sector momentum values in state/sector_history.json.

    Format: list of {"date": "YYYY-MM-DD", "sectors": {"XLK": 2.5, ...}}
    Keeps last 90 entries.
    """

    MAX_ENTRIES = 90

    def __init__(self, state_dir: str = "state"):
        self._path = Path(state_dir) / "sector_history.json"

    def load(self) -> list[dict[str, Any]]:
        """Load history from disk."""
        if not self._path.exists():
            return []
        try:
            with open(self._path) as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
        return []

    def append(self, sector_momentum: dict[str, float]) -> None:
        """Append today's sector momentum. Deduplicates by date."""
        today = date.today().isoformat()
        entries = self.load()

        entries = [e for e in entries if e.get("date") != today]
        # Round values
        rounded = {k: round(v, 3) for k, v in sector_momentum.items()}
        entries.append({"date": today, "sectors": rounded})

        entries = entries[-self.MAX_ENTRIES:]
        self._write(entries)

    def get_previous(self) -> dict[str, float] | None:
        """Get the most recent sector momentum BEFORE today."""
        today = date.today().isoformat()
        entries = self.load()
        for entry in reversed(entries):
            if entry.get("date") != today:
                return entry.get("sectors", {})
        return None

    def _write(self, entries: list[dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self._path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(entries, f, indent=2)
            os.replace(tmp, str(self._path))
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
