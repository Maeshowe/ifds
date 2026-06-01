"""Pending-exit ledger for swing close P&L tracking (P0 §0.11 Part A).

``close_positions.py`` appends a record the moment it submits a swing exit
SELL; ``daily_metrics.record_pending_exits`` later matches each record to the
IBKR ``SLD`` fill and writes the realized P&L to ``cumulative_pnl.json``.

This decouples the cross-client fill capture (close=clientId 11 submits the
MOC, the recorder connects with its own clientId 18) from the actual SELL,
and routes around the ``eod_report`` clientId-12 ``ib.fills()`` blind spot
that silently dropped the Day 9 (2026-05-28) AMH TIME_STOP realized P&L.

The ledger is the single source for swing realized P&L: one JSON file per
date under ``state/pending_exits/{date}.json`` holding a list of records::

    {
        "key": "AMH_TIME_STOP_2026-05-28",   # idempotency key
        "ticker": "AMH",
        "entry_price": 32.11,
        "entry_date": "2026-05-21",
        "qty": 249,                            # sold qty (TP1 partial = sold leg)
        "exit_type": "TIME_STOP",
        "sector": "Real Estate",
        "submitted_at": "2026-05-28T19:40:03+00:00",
        "processed": false
    }

All functions are pure/file-only (no IBKR dependency) so the recorder logic
is fully unit-testable.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("pending_exits")

DEFAULT_LEDGER_DIR = "state/pending_exits"

# The exit-record fields a caller must supply (key/submitted_at/processed are
# filled in by append_pending_exit).
_REQUIRED_FIELDS = ("ticker", "entry_price", "entry_date", "qty", "exit_type")


def make_key(ticker: str, exit_type: str, ledger_date: str) -> str:
    """Build the idempotency key for a pending-exit record."""
    return f"{ticker}_{exit_type}_{ledger_date}"


def _ledger_path(ledger_dir: str | Path, ledger_date: str) -> Path:
    return Path(ledger_dir) / f"{ledger_date}.json"


def _atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON to ``path`` atomically (temp file + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_pending_exits(
    ledger_date: str,
    ledger_dir: str | Path = DEFAULT_LEDGER_DIR,
) -> list[dict]:
    """Return the list of pending-exit records for ``ledger_date``.

    Returns an empty list if the ledger file does not exist or is
    unreadable (logged as a warning — never raises).
    """
    path = _ledger_path(ledger_dir, ledger_date)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("pending_exits ledger unreadable %s: %s", path, exc)
        return []
    return data if isinstance(data, list) else []


def append_pending_exit(
    exit_record: dict,
    *,
    ledger_dir: str | Path = DEFAULT_LEDGER_DIR,
    today: date | str | None = None,
) -> dict:
    """Append a swing-exit record to the day's ledger (idempotent by key).

    ``exit_record`` must contain ``ticker``, ``entry_price``, ``entry_date``,
    ``qty`` and ``exit_type`` (``sector`` optional). The ledger date is
    ``today`` (defaults to the current date); the record's ``key``,
    ``submitted_at`` (UTC ISO) and ``processed=False`` fields are filled in.

    If a record with the same ``key`` already exists for the date the ledger
    is left unchanged (idempotent re-submit). Returns a summary dict with
    ``key`` and ``appended`` (bool).
    """
    missing = [k for k in _REQUIRED_FIELDS if k not in exit_record]
    if missing:
        raise ValueError(f"pending exit record missing fields: {missing}")

    if today is None:
        ledger_date = date.today().isoformat()
    elif isinstance(today, date):
        ledger_date = today.isoformat()
    else:
        ledger_date = str(today)

    key = make_key(exit_record["ticker"], exit_record["exit_type"], ledger_date)
    records = load_pending_exits(ledger_date, ledger_dir)

    if any(r.get("key") == key for r in records):
        logger.info("pending_exits: key already present, skipping append: %s", key)
        return {"key": key, "appended": False}

    record = {
        "key": key,
        "ticker": exit_record["ticker"],
        "entry_price": exit_record["entry_price"],
        "entry_date": exit_record["entry_date"],
        "qty": exit_record["qty"],
        "exit_type": exit_record["exit_type"],
        "sector": exit_record.get("sector", ""),
        "submitted_at": exit_record.get("submitted_at", datetime.now(timezone.utc).isoformat()),
        "processed": False,
    }
    records.append(record)
    _atomic_write_json(_ledger_path(ledger_dir, ledger_date), records)
    logger.info("pending_exits: appended %s (qty %s)", key, record["qty"])
    return {"key": key, "appended": True}


def mark_processed(
    ledger_date: str,
    keys: set[str] | list[str],
    ledger_dir: str | Path = DEFAULT_LEDGER_DIR,
) -> int:
    """Flip ``processed=True`` for the given keys in the day's ledger.

    Returns the number of records newly marked processed. Atomic write; a
    no-op (no write) if the ledger is empty or no key matches.
    """
    key_set = set(keys)
    if not key_set:
        return 0
    records = load_pending_exits(ledger_date, ledger_dir)
    if not records:
        return 0

    changed = 0
    for r in records:
        if r.get("key") in key_set and not r.get("processed", False):
            r["processed"] = True
            changed += 1

    if changed:
        _atomic_write_json(_ledger_path(ledger_dir, ledger_date), records)
        logger.info("pending_exits: marked %d processed for %s", changed, ledger_date)
    return changed
