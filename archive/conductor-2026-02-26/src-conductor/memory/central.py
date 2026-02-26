"""Central DB for cross-project CONDUCTOR memory (~/.conductor/central.db)."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from conductor.memory.schema import (
    CENTRAL_FTS_SQL,
    CENTRAL_FTS_TRIGGERS_SQL,
    CENTRAL_TABLES_SQL,
    SCHEMA_VERSION,
)


class CentralDB:
    """Cross-project memory: project registry, shared decisions and learnings."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or (Path.home() / ".conductor" / "central.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def init_schema(self) -> None:
        """Initialize central DB schema."""
        cursor = self.conn.cursor()
        cursor.executescript(CENTRAL_TABLES_SQL)
        cursor.executescript(CENTRAL_FTS_SQL)
        cursor.executescript(CENTRAL_FTS_TRIGGERS_SQL)
        cursor.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value) VALUES (?, ?)",
            ("version", str(SCHEMA_VERSION)),
        )
        self.conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # --- Projects ---

    def register_project(self, name: str, path: str) -> dict:
        """Register a project. Updates last_accessed if already exists."""
        now = _now()
        existing = self.conn.execute(
            "SELECT * FROM projects WHERE path=?", (path,)
        ).fetchone()
        if existing:
            self.conn.execute(
                "UPDATE projects SET last_accessed=?, name=? WHERE path=?",
                (now, name, path),
            )
            self.conn.commit()
            row = self.conn.execute(
                "SELECT * FROM projects WHERE path=?", (path,)
            ).fetchone()
            return dict(row)
        cursor = self.conn.execute(
            "INSERT INTO projects (name, path, created_at, last_accessed) VALUES (?, ?, ?, ?)",
            (name, path, now, now),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM projects WHERE id=?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)

    def get_projects(self) -> list[dict]:
        """Get all registered projects."""
        rows = self.conn.execute(
            "SELECT * FROM projects ORDER BY last_accessed DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Cross-project Decisions ---

    def create_decision(
        self,
        title: str,
        description: str | None = None,
        alternatives: list | None = None,
        rationale: str | None = None,
        tags: list | None = None,
        source_project: str | None = None,
    ) -> dict:
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO decisions (created_at, title, description, alternatives, rationale, tags, source_project) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                now,
                title,
                description,
                json.dumps(alternatives) if alternatives else None,
                rationale,
                json.dumps(tags) if tags else None,
                source_project,
            ),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM decisions WHERE id=?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)

    def get_active_decisions(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM decisions WHERE status='active' ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Cross-project Learnings ---

    def create_learning(
        self,
        content: str,
        category: str,
        source: str | None = None,
        source_project: str | None = None,
    ) -> dict:
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO learnings (created_at, content, category, source, source_project) "
            "VALUES (?, ?, ?, ?, ?)",
            (now, content, category, source, source_project),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM learnings WHERE id=?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)

    def get_recent_learnings(self, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM learnings ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Search ---

    def search(self, query: str) -> list[dict]:
        """Search across central FTS5 indexes."""
        results = []
        for table, fts_table, label in [
            ("decisions", "decisions_fts", "central_decision"),
            ("learnings", "learnings_fts", "central_learning"),
        ]:
            rows = self.conn.execute(
                f"SELECT {table}.*, rank FROM {fts_table} "
                f"JOIN {table} ON {table}.id = {fts_table}.rowid "
                f"WHERE {fts_table} MATCH ? ORDER BY rank LIMIT 10",
                (query,),
            ).fetchall()
            for row in rows:
                result = dict(row)
                result["_type"] = label
                results.append(result)
        results.sort(key=lambda r: r.get("rank", 0))
        return results


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
