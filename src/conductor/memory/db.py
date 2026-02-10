"""SQLite + FTS5 database operations for CONDUCTOR memory."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from conductor.memory.schema import (
    BRIEFS_FTS_SQL,
    BRIEFS_FTS_TRIGGERS_SQL,
    BRIEFS_TABLE_SQL,
    BUILD_PLANS_FTS_SQL,
    BUILD_PLANS_FTS_TRIGGERS_SQL,
    BUILD_PLANS_TABLE_SQL,
    FTS_SQL,
    FTS_TRIGGERS_SQL,
    REVIEWS_FTS_SQL,
    REVIEWS_FTS_TRIGGERS_SQL,
    REVIEWS_TABLE_SQL,
    SCHEMA_VERSION,
    STRATEGY_ANALYSES_FTS_SQL,
    STRATEGY_ANALYSES_FTS_TRIGGERS_SQL,
    STRATEGY_ANALYSES_TABLE_SQL,
    TABLES_SQL,
    TEST_RUNS_FTS_SQL,
    TEST_RUNS_FTS_TRIGGERS_SQL,
    TEST_RUNS_TABLE_SQL,
)


class MemoryDB:
    """SQLite database with FTS5 full-text search for CONDUCTOR memory."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def init_schema(self) -> None:
        """Initialize database schema and FTS5 indexes."""
        cursor = self.conn.cursor()
        cursor.executescript(TABLES_SQL)
        cursor.executescript(BRIEFS_TABLE_SQL)
        cursor.executescript(BUILD_PLANS_TABLE_SQL)
        cursor.executescript(REVIEWS_TABLE_SQL)
        cursor.executescript(STRATEGY_ANALYSES_TABLE_SQL)
        cursor.executescript(TEST_RUNS_TABLE_SQL)
        cursor.executescript(FTS_SQL)
        cursor.executescript(BRIEFS_FTS_SQL)
        cursor.executescript(BUILD_PLANS_FTS_SQL)
        cursor.executescript(REVIEWS_FTS_SQL)
        cursor.executescript(STRATEGY_ANALYSES_FTS_SQL)
        cursor.executescript(TEST_RUNS_FTS_SQL)
        cursor.executescript(FTS_TRIGGERS_SQL)
        cursor.executescript(BRIEFS_FTS_TRIGGERS_SQL)
        cursor.executescript(BUILD_PLANS_FTS_TRIGGERS_SQL)
        cursor.executescript(REVIEWS_FTS_TRIGGERS_SQL)
        cursor.executescript(STRATEGY_ANALYSES_FTS_TRIGGERS_SQL)
        cursor.executescript(TEST_RUNS_FTS_TRIGGERS_SQL)
        cursor.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value) VALUES (?, ?)",
            ("version", str(SCHEMA_VERSION)),
        )
        self.conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # --- Sessions ---

    def create_session(self) -> dict:
        """Start a new session. Returns the created session as dict."""
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO sessions (started_at, status) VALUES (?, ?)",
            (now, "active"),
        )
        self.conn.commit()
        return self._get_session(cursor.lastrowid)

    def end_session(self, session_id: int, summary: str) -> dict:
        """End a session with a summary."""
        now = _now()
        self.conn.execute(
            "UPDATE sessions SET ended_at=?, status=?, summary=? WHERE id=?",
            (now, "completed", summary, session_id),
        )
        self.conn.commit()
        return self._get_session(session_id)

    def pause_session(self, session_id: int) -> dict:
        """Pause a session (emergency save)."""
        now = _now()
        self.conn.execute(
            "UPDATE sessions SET ended_at=?, status=? WHERE id=?",
            (now, "paused", session_id),
        )
        self.conn.commit()
        return self._get_session(session_id)

    def get_active_session(self) -> dict | None:
        """Get the currently active session, if any."""
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE status='active' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def get_last_session(self) -> dict | None:
        """Get the most recent completed or paused session."""
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE status IN ('completed', 'paused') "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def _get_session(self, session_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE id=?", (session_id,)
        ).fetchone()
        return dict(row)

    # --- Decisions ---

    def create_decision(
        self,
        title: str,
        description: str | None = None,
        alternatives: list | None = None,
        rationale: str | None = None,
        tags: list | None = None,
    ) -> dict:
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO decisions (created_at, title, description, alternatives, rationale, tags) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                now,
                title,
                description,
                json.dumps(alternatives) if alternatives else None,
                rationale,
                json.dumps(tags) if tags else None,
            ),
        )
        self.conn.commit()
        return self._get_decision(cursor.lastrowid)

    def get_active_decisions(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM decisions WHERE status='active' ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def _get_decision(self, decision_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM decisions WHERE id=?", (decision_id,)
        ).fetchone()
        return dict(row)

    # --- Tasks ---

    def create_task(
        self,
        title: str,
        description: str | None = None,
        session_id: int | None = None,
    ) -> dict:
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO tasks (created_at, updated_at, title, description, session_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (now, now, title, description, session_id),
        )
        self.conn.commit()
        return self._get_task(cursor.lastrowid)

    def update_task_status(self, task_id: int, status: str) -> dict:
        now = _now()
        self.conn.execute(
            "UPDATE tasks SET status=?, updated_at=? WHERE id=?",
            (status, now, task_id),
        )
        self.conn.commit()
        return self._get_task(task_id)

    def get_open_tasks(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM tasks WHERE status IN ('open', 'in_progress') ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def _get_task(self, task_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM tasks WHERE id=?", (task_id,)
        ).fetchone()
        return dict(row)

    # --- Learnings ---

    def create_learning(
        self, content: str, category: str, source: str | None = None
    ) -> dict:
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO learnings (created_at, content, category, source) VALUES (?, ?, ?, ?)",
            (now, content, category, source),
        )
        self.conn.commit()
        return self._get_learning(cursor.lastrowid)

    def get_recent_learnings(self, limit: int = 5) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM learnings ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def count_learnings(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM learnings").fetchone()
        return row["cnt"]

    def _get_learning(self, learning_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM learnings WHERE id=?", (learning_id,)
        ).fetchone()
        return dict(row)

    # --- Briefs ---

    def create_brief(
        self,
        title: str,
        raw_idea: str,
        problem: str | None = None,
        target_user: str | None = None,
        scope_essential: list | None = None,
        scope_nice_to_have: list | None = None,
        scope_out: list | None = None,
        constraints: list | None = None,
        first_version: str | None = None,
        brief_text: str | None = None,
        status: str = "draft",
        session_id: int | None = None,
    ) -> dict:
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO briefs (created_at, updated_at, title, raw_idea, problem, "
            "target_user, scope_essential, scope_nice_to_have, scope_out, constraints, "
            "first_version, brief_text, status, session_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                now, now, title, raw_idea, problem, target_user,
                json.dumps(scope_essential) if scope_essential else None,
                json.dumps(scope_nice_to_have) if scope_nice_to_have else None,
                json.dumps(scope_out) if scope_out else None,
                json.dumps(constraints) if constraints else None,
                first_version, brief_text, status, session_id,
            ),
        )
        self.conn.commit()
        return self._get_brief(cursor.lastrowid)

    def update_brief(self, brief_id: int, **kwargs) -> dict:
        """Update brief fields. Pass any column name as keyword argument."""
        now = _now()
        sets = ["updated_at=?"]
        values = [now]
        json_fields = {"scope_essential", "scope_nice_to_have", "scope_out", "constraints"}
        for key, value in kwargs.items():
            sets.append(f"{key}=?")
            if key in json_fields and isinstance(value, list):
                values.append(json.dumps(value))
            else:
                values.append(value)
        values.append(brief_id)
        self.conn.execute(
            f"UPDATE briefs SET {', '.join(sets)} WHERE id=?", values
        )
        self.conn.commit()
        return self._get_brief(brief_id)

    def get_brief(self, brief_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM briefs WHERE id=?", (brief_id,)).fetchone()
        return dict(row) if row else None

    def get_briefs_by_status(self, status: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM briefs WHERE status=? ORDER BY id DESC", (status,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_briefs(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM briefs ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

    def _get_brief(self, brief_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM briefs WHERE id=?", (brief_id,)).fetchone()
        return dict(row)

    # --- Build Plans ---

    def create_build_plan(
        self,
        title: str,
        brief_id: int | None = None,
        description: str | None = None,
        approach: str | None = None,
        steps: list | None = None,
        files_to_create: list | None = None,
        files_to_modify: list | None = None,
        acceptance_criteria: list | None = None,
        estimated_complexity: str | None = None,
        status: str = "draft",
        session_id: int | None = None,
    ) -> dict:
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO build_plans (created_at, updated_at, brief_id, title, description, "
            "approach, steps, files_to_create, files_to_modify, acceptance_criteria, "
            "estimated_complexity, status, session_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                now, now, brief_id, title, description, approach,
                json.dumps(steps) if steps else None,
                json.dumps(files_to_create) if files_to_create else None,
                json.dumps(files_to_modify) if files_to_modify else None,
                json.dumps(acceptance_criteria) if acceptance_criteria else None,
                estimated_complexity, status, session_id,
            ),
        )
        self.conn.commit()
        return self._get_build_plan(cursor.lastrowid)

    def update_build_plan(self, plan_id: int, **kwargs) -> dict:
        """Update build plan fields. Pass any column name as keyword argument."""
        now = _now()
        sets = ["updated_at=?"]
        values = [now]
        json_fields = {"steps", "files_to_create", "files_to_modify", "acceptance_criteria"}
        for key, value in kwargs.items():
            sets.append(f"{key}=?")
            if key in json_fields and isinstance(value, list):
                values.append(json.dumps(value))
            else:
                values.append(value)
        values.append(plan_id)
        self.conn.execute(
            f"UPDATE build_plans SET {', '.join(sets)} WHERE id=?", values
        )
        self.conn.commit()
        return self._get_build_plan(plan_id)

    def get_build_plan(self, plan_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM build_plans WHERE id=?", (plan_id,)).fetchone()
        return dict(row) if row else None

    def get_build_plans_by_status(self, status: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM build_plans WHERE status=? ORDER BY id DESC", (status,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_build_plans_by_brief(self, brief_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM build_plans WHERE brief_id=? ORDER BY id DESC", (brief_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_build_plans(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM build_plans ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

    def _get_build_plan(self, plan_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM build_plans WHERE id=?", (plan_id,)).fetchone()
        return dict(row)

    # --- Reviews ---

    def create_review(
        self,
        build_plan_id: int | None = None,
        brief_id: int | None = None,
        review_type: str = "code",
        scope: str | None = None,
        findings: list | None = None,
        verdict: str = "pending",
        summary: str | None = None,
        session_id: int | None = None,
    ) -> dict:
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO reviews (created_at, build_plan_id, brief_id, review_type, "
            "scope, findings, verdict, summary, session_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                now, build_plan_id, brief_id, review_type, scope,
                json.dumps(findings) if findings else None,
                verdict, summary, session_id,
            ),
        )
        self.conn.commit()
        return self._get_review(cursor.lastrowid)

    def update_review(self, review_id: int, **kwargs) -> dict:
        """Update review fields."""
        sets = []
        values = []
        json_fields = {"findings"}
        for key, value in kwargs.items():
            sets.append(f"{key}=?")
            if key in json_fields and isinstance(value, list):
                values.append(json.dumps(value))
            else:
                values.append(value)
        values.append(review_id)
        self.conn.execute(
            f"UPDATE reviews SET {', '.join(sets)} WHERE id=?", values
        )
        self.conn.commit()
        return self._get_review(review_id)

    def get_review(self, review_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
        return dict(row) if row else None

    def get_reviews_by_plan(self, plan_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM reviews WHERE build_plan_id=? ORDER BY id DESC", (plan_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_reviews_by_verdict(self, verdict: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM reviews WHERE verdict=? ORDER BY id DESC", (verdict,)
        ).fetchall()
        return [dict(r) for r in rows]

    def _get_review(self, review_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
        return dict(row)

    # --- Strategy Analyses ---

    def create_strategy_analysis(
        self,
        analysis_type: str,
        title: str,
        target_type: str | None = None,
        target_id: int | None = None,
        input_text: str | None = None,
        findings: dict | None = None,
        recommendation: str | None = None,
        status: str = "active",
        session_id: int | None = None,
    ) -> dict:
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO strategy_analyses (created_at, analysis_type, target_type, "
            "target_id, title, input_text, findings, recommendation, status, session_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                now, analysis_type, target_type, target_id, title, input_text,
                json.dumps(findings) if findings else None,
                recommendation, status, session_id,
            ),
        )
        self.conn.commit()
        return self._get_strategy_analysis(cursor.lastrowid)

    def update_strategy_analysis(self, analysis_id: int, **kwargs) -> dict:
        """Update strategy analysis fields."""
        sets = []
        values = []
        json_fields = {"findings"}
        for key, value in kwargs.items():
            sets.append(f"{key}=?")
            if key in json_fields and isinstance(value, dict):
                values.append(json.dumps(value))
            else:
                values.append(value)
        values.append(analysis_id)
        self.conn.execute(
            f"UPDATE strategy_analyses SET {', '.join(sets)} WHERE id=?", values
        )
        self.conn.commit()
        return self._get_strategy_analysis(analysis_id)

    def get_strategy_analysis(self, analysis_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM strategy_analyses WHERE id=?", (analysis_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_analyses_by_type(self, analysis_type: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM strategy_analyses WHERE analysis_type=? ORDER BY id DESC",
            (analysis_type,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_strategy_analyses(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM strategy_analyses ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def _get_strategy_analysis(self, analysis_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM strategy_analyses WHERE id=?", (analysis_id,)
        ).fetchone()
        return dict(row)

    # --- Extended Decisions ---

    def get_decision(self, decision_id: int) -> dict | None:
        """Get a decision by ID. Returns None if not found."""
        row = self.conn.execute(
            "SELECT * FROM decisions WHERE id=?", (decision_id,)
        ).fetchone()
        return dict(row) if row else None

    def update_decision(self, decision_id: int, **kwargs) -> dict:
        """Update decision fields. Pass any column name as keyword argument."""
        sets = []
        values = []
        json_fields = {"alternatives", "tags"}
        for key, value in kwargs.items():
            sets.append(f"{key}=?")
            if key in json_fields and isinstance(value, list):
                values.append(json.dumps(value))
            else:
                values.append(value)
        values.append(decision_id)
        self.conn.execute(
            f"UPDATE decisions SET {', '.join(sets)} WHERE id=?", values
        )
        self.conn.commit()
        return self._get_decision(decision_id)

    def get_all_decisions(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM decisions ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Test Runs ---

    def create_test_run(
        self,
        test_command: str,
        total_tests: int | None = None,
        passed: int | None = None,
        failed: int | None = None,
        errors: int | None = None,
        skipped: int | None = None,
        duration_seconds: float | None = None,
        output_summary: str | None = None,
        status: str = "passed",
        build_plan_id: int | None = None,
        brief_id: int | None = None,
        session_id: int | None = None,
    ) -> dict:
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO test_runs (created_at, build_plan_id, brief_id, test_command, "
            "total_tests, passed, failed, errors, skipped, duration_seconds, "
            "output_summary, status, session_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                now, build_plan_id, brief_id, test_command,
                total_tests, passed, failed, errors, skipped, duration_seconds,
                output_summary, status, session_id,
            ),
        )
        self.conn.commit()
        return self._get_test_run(cursor.lastrowid)

    def get_test_run(self, run_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM test_runs WHERE id=?", (run_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_test_runs_by_plan(self, plan_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM test_runs WHERE build_plan_id=? ORDER BY id DESC", (plan_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_test_runs_by_status(self, status: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM test_runs WHERE status=? ORDER BY id DESC", (status,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_test_runs(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM test_runs ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_recent_test_runs(self, limit: int = 5) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM test_runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def _get_test_run(self, run_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM test_runs WHERE id=?", (run_id,)
        ).fetchone()
        return dict(row)

    # --- FTS5 Search ---

    def search(self, query: str) -> list[dict]:
        """Search across all FTS5 indexes. Returns unified results."""
        results = []

        for table, fts_table, label in [
            ("sessions", "sessions_fts", "session"),
            ("decisions", "decisions_fts", "decision"),
            ("tasks", "tasks_fts", "task"),
            ("learnings", "learnings_fts", "learning"),
            ("briefs", "briefs_fts", "brief"),
            ("build_plans", "build_plans_fts", "build_plan"),
            ("reviews", "reviews_fts", "review"),
            ("strategy_analyses", "strategy_analyses_fts", "strategy_analysis"),
            ("test_runs", "test_runs_fts", "test_run"),
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
    """Current time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()
