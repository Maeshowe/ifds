"""Daily MID bundle snapshot persistence.

Saves the MID bundle JSON gzipped to ``state/mid_bundles/YYYY-MM-DD.json.gz``
following the same pattern as ``state/phase4_snapshots/`` (see
``src/ifds/data/phase4_snapshot.py`` for the reference implementation).

Used by Phase 0 Diagnostics for shadow-mode data collection and by the
offline ``scripts/analysis/mid_vs_ifds_sector_comparison.py`` script.
"""
from __future__ import annotations

import gzip
import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = Path("state/mid_bundles")


def save_bundle_snapshot(
    bundle: dict[str, Any],
    target_date: date | None = None,
    snapshot_dir: Path | str | None = None,
) -> Path | None:
    """Save a MID bundle dict to ``<snapshot_dir>/YYYY-MM-DD.json.gz``.

    Args:
        bundle: The full MID bundle (must be a non-empty dict).
        target_date: Date to use in filename. Defaults to today.
        snapshot_dir: Override the destination directory (used in tests).

    Returns:
        Path on success, ``None`` on failure or when ``bundle`` is empty.
        Failure is non-fatal — the caller should treat ``None`` as
        "snapshot skipped" and continue.
    """
    if not bundle or not isinstance(bundle, dict):
        return None

    out_dir = Path(snapshot_dir) if snapshot_dir is not None else SNAPSHOT_DIR
    target = target_date or date.today()
    out_path = out_dir / f"{target.isoformat()}.json.gz"

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        with gzip.open(out_path, "wt", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False)
    except (OSError, IOError, TypeError, ValueError) as e:
        logger.warning(
            f"Failed to save MID bundle snapshot to {out_path}: "
            f"{type(e).__name__}: {e}"
        )
        return None

    return out_path


def load_bundle_snapshot(
    target_date: date,
    snapshot_dir: Path | str | None = None,
) -> dict[str, Any] | None:
    """Load a previously saved MID bundle snapshot.

    Args:
        target_date: Date of the snapshot to load.
        snapshot_dir: Override the source directory (used in tests).

    Returns:
        The bundle dict on success, ``None`` if the file does not exist
        or is corrupt.
    """
    in_dir = Path(snapshot_dir) if snapshot_dir is not None else SNAPSHOT_DIR
    in_path = in_dir / f"{target_date.isoformat()}.json.gz"

    if not in_path.exists():
        return None

    try:
        with gzip.open(in_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, IOError, json.JSONDecodeError) as e:
        logger.warning(
            f"Failed to load MID bundle snapshot from {in_path}: "
            f"{type(e).__name__}: {e}"
        )
        return None

    return data if isinstance(data, dict) else None
