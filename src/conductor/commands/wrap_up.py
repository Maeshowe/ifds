"""CONDUCTOR /wrap-up — End session, save state."""

import json
from pathlib import Path

from conductor.memory.db import MemoryDB
from conductor.memory.session import SessionManager


def run(project_dir: Path, summary: str) -> str:
    """Execute /wrap-up and return JSON output. Summary is mandatory."""
    db_path = project_dir / ".conductor" / "memory" / "project.db"

    if not db_path.exists():
        return json.dumps({"error": "CONDUCTOR not initialized. Run: python -m conductor init"})

    db = MemoryDB(db_path)
    try:
        session_mgr = SessionManager(db)
        closed = session_mgr.end_session(summary)

        if not closed:
            return json.dumps({"error": "No active session to wrap up."})

        # Snapshot of current state
        open_tasks = db.get_open_tasks()
        active_decisions = db.get_active_decisions()

        task_counts = {}
        for t in db.conn.execute("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status").fetchall():
            task_counts[t["status"]] = t["cnt"]

        result = {
            "session_closed": {
                "id": closed["id"],
                "started": closed["started_at"],
                "ended": closed["ended_at"],
                "summary": closed["summary"],
            },
            "tasks_snapshot": task_counts,
            "decisions_snapshot": {"active": len(active_decisions)},
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
    finally:
        db.close()
