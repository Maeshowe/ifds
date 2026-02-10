"""CONDUCTOR /pause — Emergency state save."""

import json
from pathlib import Path

from conductor.memory.db import MemoryDB
from conductor.memory.session import SessionManager


def run(project_dir: Path) -> str:
    """Execute /pause and return JSON output. No questions — immediate save."""
    db_path = project_dir / ".conductor" / "memory" / "project.db"

    if not db_path.exists():
        return json.dumps({"error": "CONDUCTOR not initialized. Run: python -m conductor init"})

    db = MemoryDB(db_path)
    try:
        session_mgr = SessionManager(db)
        paused = session_mgr.pause_session()

        if not paused:
            return json.dumps({
                "session_paused": None,
                "state_saved": True,
                "message": "No active session, but state is safe.",
                "resume_with": "/continue",
            })

        result = {
            "session_paused": {
                "id": paused["id"],
                "paused_at": paused["ended_at"],
            },
            "state_saved": True,
            "resume_with": "/continue",
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
    finally:
        db.close()
