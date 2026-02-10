"""Signal hash deduplication to prevent duplicate trades on re-run."""

import hashlib
import json
import os
import tempfile
from datetime import date
from pathlib import Path


class SignalDedup:
    """SHA256-based signal deduplication with 24h TTL.

    Hash: SHA256(f"{ticker}|{direction}|{date}")[:16]
    State: state/signal_hashes.json (date-scoped, auto-cleanup)
    """

    def __init__(self, state_file: str = "state/signal_hashes.json"):
        self._path = Path(state_file)
        self._hashes: dict[str, str] = {}  # hash → ticker
        self._load()

    def _load(self) -> None:
        """Load and cleanup expired hashes (only keep today's)."""
        if not self._path.exists():
            return
        try:
            with open(self._path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        today = date.today().isoformat()
        if data.get("date") == today:
            self._hashes = data.get("hashes", {})

    def is_duplicate(self, ticker: str, direction: str) -> bool:
        """Check if this signal was already generated today."""
        h = self._compute_hash(ticker, direction)
        return h in self._hashes

    def record(self, ticker: str, direction: str) -> None:
        """Record a signal hash."""
        h = self._compute_hash(ticker, direction)
        self._hashes[h] = ticker

    def save(self) -> None:
        """Persist to disk (atomic write via tempfile + os.replace)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "date": date.today().isoformat(),
            "hashes": self._hashes,
        }
        fd, tmp = tempfile.mkstemp(dir=str(self._path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, str(self._path))
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    @staticmethod
    def _compute_hash(ticker: str, direction: str) -> str:
        """SHA256(ticker|direction|date)[:16]."""
        today = date.today().isoformat()
        raw = f"{ticker}|{direction}|{today}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def count(self) -> int:
        """Number of recorded hashes."""
        return len(self._hashes)
