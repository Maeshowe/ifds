"""Tests for scripts/tools/events_to_sqlite.py — JSONL→SQLite import."""

import json
import sqlite3
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _ensure_tools_importable():
    """Add scripts/tools to sys.path."""
    tools_dir = str(Path(__file__).resolve().parent.parent / "scripts" / "tools")
    added = tools_dir not in sys.path
    if added:
        sys.path.insert(0, tools_dir)
    yield
    if added:
        sys.path.remove(tools_dir)


def _write_jsonl(path: Path, events: list[dict]) -> None:
    with open(path, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


class TestEventsToSqlite:
    """events_to_sqlite imports JSONL and supports queries."""

    def test_init_db_creates_table(self, tmp_path):
        import events_to_sqlite as m

        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        m.init_db(conn)

        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        assert ("events",) in tables
        conn.close()

    def test_import_jsonl_basic(self, tmp_path):
        import events_to_sqlite as m

        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        m.init_db(conn)

        jsonl = tmp_path / "pt_events_2026-04-02.jsonl"
        _write_jsonl(jsonl, [
            {"ts": "2026-04-02T13:35:08+00:00", "script": "submit", "event": "order_submitted", "ticker": "CF", "qty": 34},
            {"ts": "2026-04-02T14:08:15+00:00", "script": "monitor", "event": "tp1_detected", "ticker": "CF"},
        ])

        count = m.import_jsonl(conn, str(jsonl))
        assert count == 2

        rows = conn.execute("SELECT * FROM events").fetchall()
        assert len(rows) == 2
        conn.close()

    def test_import_idempotent(self, tmp_path):
        import events_to_sqlite as m

        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        m.init_db(conn)

        jsonl = tmp_path / "pt_events_2026-04-02.jsonl"
        _write_jsonl(jsonl, [
            {"ts": "2026-04-02T13:35:08+00:00", "script": "submit", "event": "order_submitted", "ticker": "AAPL"},
        ])

        count1 = m.import_jsonl(conn, str(jsonl))
        count2 = m.import_jsonl(conn, str(jsonl))
        assert count1 == 1
        assert count2 == 0  # Already imported

        rows = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        assert rows == 1
        conn.close()

    def test_price_extraction(self, tmp_path):
        import events_to_sqlite as m

        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        m.init_db(conn)

        jsonl = tmp_path / "pt_events_2026-04-02.jsonl"
        _write_jsonl(jsonl, [
            {"ts": "2026-04-02T13:50:22+00:00", "script": "avwap", "event": "avwap_fill", "ticker": "CF", "fill_price": 134.46, "qty": 34},
            {"ts": "2026-04-02T17:00:21+00:00", "script": "monitor", "event": "loss_exit", "ticker": "CF", "exit_price": 130.44, "pnl": -136.68, "qty": 34},
        ])

        m.import_jsonl(conn, str(jsonl))

        # fill_price extracted
        row1 = conn.execute("SELECT price FROM events WHERE event='avwap_fill'").fetchone()
        assert row1[0] == 134.46

        # exit_price extracted
        row2 = conn.execute("SELECT price, pnl FROM events WHERE event='loss_exit'").fetchone()
        assert row2[0] == 130.44
        assert row2[1] == -136.68
        conn.close()

    def test_data_column_has_full_json(self, tmp_path):
        import events_to_sqlite as m

        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        m.init_db(conn)

        jsonl = tmp_path / "pt_events_2026-04-02.jsonl"
        original = {"ts": "2026-04-02T13:35:08+00:00", "script": "submit", "event": "order_submitted", "ticker": "CF", "qty": 34, "sl": 117.27}
        _write_jsonl(jsonl, [original])

        m.import_jsonl(conn, str(jsonl))

        data_str = conn.execute("SELECT data FROM events").fetchone()[0]
        restored = json.loads(data_str)
        assert restored["sl"] == 117.27
        assert restored["ticker"] == "CF"
        conn.close()

    def test_empty_lines_skipped(self, tmp_path):
        import events_to_sqlite as m

        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        m.init_db(conn)

        jsonl = tmp_path / "pt_events_2026-04-02.jsonl"
        with open(jsonl, "w") as f:
            f.write(json.dumps({"ts": "2026-04-02T13:00:00+00:00", "script": "s", "event": "e"}) + "\n")
            f.write("\n")
            f.write(json.dumps({"ts": "2026-04-02T14:00:00+00:00", "script": "s", "event": "e2"}) + "\n")

        count = m.import_jsonl(conn, str(jsonl))
        assert count == 2
        conn.close()
