#!/usr/bin/env python3
"""Import pt_events JSONL files into SQLite for structured querying.

Usage:
    python scripts/tools/events_to_sqlite.py              # Import all unprocessed JSONL
    python scripts/tools/events_to_sqlite.py --reindex     # Drop and reimport everything
    python scripts/tools/events_to_sqlite.py --query "SELECT * FROM events WHERE event='loss_exit'"

Crontab (Mac Mini):
    45 22 * * 1-5  cd ~/SSH-Services/ifds && python scripts/tools/events_to_sqlite.py
"""

import argparse
import glob
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = "state/pt_events.db"
EVENTS_DIR = "logs"


def init_db(conn: sqlite3.Connection) -> None:
    """Create events table and indexes if they don't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            date TEXT NOT NULL,
            script TEXT NOT NULL,
            event TEXT NOT NULL,
            ticker TEXT,
            qty INTEGER,
            price REAL,
            pnl REAL,
            data TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_date ON events(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ticker ON events(ticker)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_event ON events(event)")
    conn.commit()


def import_jsonl(conn: sqlite3.Connection, jsonl_path: str) -> int:
    """Import a single JSONL file into the events table.

    Returns the number of rows imported (0 if already imported).
    """
    date_str = Path(jsonl_path).stem.replace("pt_events_", "")

    # Skip if already imported
    existing = conn.execute(
        "SELECT COUNT(*) FROM events WHERE date=?", (date_str,)
    ).fetchone()[0]
    if existing > 0:
        return 0

    count = 0
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            conn.execute(
                "INSERT INTO events (ts, date, script, event, ticker, qty, price, pnl, data) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry["ts"],
                    date_str,
                    entry["script"],
                    entry["event"],
                    entry.get("ticker"),
                    entry.get("qty"),
                    entry.get("fill_price") or entry.get("exit_price") or entry.get("price"),
                    entry.get("pnl"),
                    json.dumps(entry),
                ),
            )
            count += 1
    conn.commit()
    return count


def import_all(reindex: bool = False) -> None:
    """Import all pt_events JSONL files into SQLite."""
    conn = sqlite3.connect(DB_PATH)

    if reindex:
        conn.execute("DROP TABLE IF EXISTS events")
        print("Dropped existing events table.")

    init_db(conn)

    pattern = f"{EVENTS_DIR}/pt_events_*.jsonl"
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"No JSONL files found matching {pattern}")
        conn.close()
        return

    total = 0
    for f in files:
        count = import_jsonl(conn, f)
        if count > 0:
            date_str = Path(f).stem.replace("pt_events_", "")
            print(f"  {date_str}: {count} events imported")
            total += count

    row_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    print(f"\nTotal: {total} new events imported. Database has {row_count} events.")
    conn.close()


def run_query(sql: str) -> None:
    """Execute a read-only SQL query and print results."""
    if not sql.strip().upper().startswith("SELECT"):
        print("Error: only SELECT queries are permitted.", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        if not rows:
            print("No results.")
            return

        # Print header
        columns = rows[0].keys()
        print("\t".join(columns))
        print("-" * (len(columns) * 16))

        # Print rows
        for row in rows:
            print("\t".join(str(row[c]) for c in columns))

        print(f"\n({len(rows)} rows)")
    except sqlite3.OperationalError as e:
        print(f"SQL error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import pt_events JSONL into SQLite")
    parser.add_argument("--reindex", action="store_true", help="Drop and reimport all events")
    parser.add_argument("--query", type=str, help="Run a SQL query against the events table")
    args = parser.parse_args()

    if args.query:
        run_query(args.query)
    else:
        import_all(reindex=args.reindex)


if __name__ == "__main__":
    main()
