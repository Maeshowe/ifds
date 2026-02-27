"""Atomic file write helpers — crash-safe JSON and Parquet persistence."""

import json
import os
import tempfile
from pathlib import Path


def atomic_write_json(path: str | Path, data: dict | list) -> None:
    """Write JSON atomically using temp file + os.replace.

    If the process crashes mid-write, the original file remains intact.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_parquet(path: str | Path, df) -> None:
    """Write Parquet atomically using temp file + os.replace.

    Requires pandas DataFrame with .to_parquet() method.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    os.close(fd)  # close fd so pandas can write
    try:
        df.to_parquet(tmp, index=False)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
