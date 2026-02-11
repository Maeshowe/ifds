"""OBSIDIAN feature store — per-ticker JSON persistence (BC15).

Stores daily microstructure features for z-score computation.
One JSON file per ticker: state/obsidian/{TICKER}.json
Atomic writes via tempfile + os.replace (same pattern as FileCache).
"""

import json
import os
import tempfile
from pathlib import Path


class ObsidianStore:
    """Per-ticker feature history for OBSIDIAN z-score computation.

    Each ticker's file is a JSON array of daily entries:
    [{"date": "2026-02-09", "dark_share": 0.42, "gex": 1200000, ...}, ...]
    """

    def __init__(self, store_dir: str = "state/obsidian", max_entries: int = 100):
        self._store_dir = Path(store_dir)
        self._max_entries = max_entries

    def load(self, ticker: str) -> list[dict]:
        """Load feature history for a ticker. Returns [] if not found."""
        path = self._path(ticker)
        if not path.exists():
            return []
        try:
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return []
        except (json.JSONDecodeError, OSError):
            return []

    def append_and_save(self, ticker: str, entry: dict,
                        existing: list[dict] | None = None) -> None:
        """Append today's entry and save. Trims to max_entries."""
        entries = existing if existing is not None else self.load(ticker)

        # Deduplicate by date: remove existing entry for same date
        entry_date = entry.get("date", "")
        entries = [e for e in entries if e.get("date") != entry_date]

        entries.append(entry)

        # Trim oldest if over limit
        if len(entries) > self._max_entries:
            entries = entries[-self._max_entries:]

        self._atomic_write(ticker, entries)

    def get_feature_series(self, entries: list[dict], feature_name: str) -> list[float]:
        """Extract a single feature's values from history entries."""
        values = []
        for e in entries:
            v = e.get(feature_name)
            if v is not None:
                try:
                    values.append(float(v))
                except (ValueError, TypeError):
                    pass
        return values

    def _path(self, ticker: str) -> Path:
        """Build file path for a ticker."""
        safe = ticker.replace("/", "_").replace(":", "_")
        return self._store_dir / f"{safe}.json"

    def _atomic_write(self, ticker: str, entries: list[dict]) -> None:
        """Write entries atomically via tempfile + os.replace."""
        path = self._path(ticker)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(entries, f)
            os.replace(tmp, str(path))
        except Exception:
            # Cleanup temp file on failure
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
