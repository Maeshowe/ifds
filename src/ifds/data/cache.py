"""File-based cache for API responses.

Directory structure: {cache_dir}/{provider}/{endpoint}/{date}/{symbol}.json
Rules: skip today (data still changing), atomic write, cleanup old files.
"""

import json
import os
import tempfile
import time
from datetime import date
from pathlib import Path


class FileCache:
    """File-based cache for API responses.

    Caches API responses as JSON files organized by provider/endpoint/date/symbol.
    Today's date is never cached (data is still changing during market hours).
    Uses atomic writes (tempfile + os.replace) to prevent corruption.
    """

    def __init__(self, cache_dir: str = "data/cache"):
        self._cache_dir = Path(cache_dir)

    def _path(self, provider: str, endpoint: str, date_str: str, symbol: str) -> Path:
        """Build cache file path with sanitized endpoint."""
        safe_endpoint = endpoint.strip("/").replace("/", "_")
        safe_symbol = symbol.replace("/", "_").replace(":", "_")
        return self._cache_dir / provider / safe_endpoint / date_str / f"{safe_symbol}.json"

    def get(self, provider: str, endpoint: str, date_str: str, symbol: str) -> dict | list | None:
        """Read cached data. Returns None if not cached or date is today."""
        if date_str == date.today().isoformat():
            return None

        path = self._path(provider, endpoint, date_str, symbol)
        if not path.exists():
            return None

        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def put(self, provider: str, endpoint: str, date_str: str, symbol: str,
            data: dict | list | None) -> None:
        """Write data to cache. No-op if data is None or date is today."""
        if data is None:
            return
        if date_str == date.today().isoformat():
            return

        path = self._path(provider, endpoint, date_str, symbol)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file then rename
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f)
            os.replace(tmp_path, str(path))
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def cleanup(self, max_age_days: int = 7) -> int:
        """Delete cache files older than max_age_days. Returns count of deleted files."""
        if not self._cache_dir.exists():
            return 0

        cutoff = time.time() - (max_age_days * 86400)
        deleted = 0

        for dirpath, _dirnames, filenames in os.walk(str(self._cache_dir)):
            for fn in filenames:
                if not fn.endswith(".json"):
                    continue
                fp = os.path.join(dirpath, fn)
                try:
                    if os.path.getmtime(fp) < cutoff:
                        os.unlink(fp)
                        deleted += 1
                except OSError:
                    pass

        # Remove empty directories
        for dirpath, dirnames, filenames in os.walk(str(self._cache_dir), topdown=False):
            if not dirnames and not filenames and dirpath != str(self._cache_dir):
                try:
                    os.rmdir(dirpath)
                except OSError:
                    pass

        return deleted
