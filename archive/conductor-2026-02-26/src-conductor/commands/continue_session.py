"""CONDUCTOR /continue — Resume with full context."""

import json
from pathlib import Path

from conductor.memory.context import ContextLoader
from conductor.memory.db import MemoryDB
from conductor.memory.session import SessionManager


def run(project_dir: Path) -> str:
    """Execute /continue and return JSON output."""
    db_path = project_dir / ".conductor" / "memory" / "project.db"

    if not db_path.exists():
        return json.dumps({"error": "CONDUCTOR not initialized. Run: python -m conductor init"})

    db = MemoryDB(db_path)
    try:
        loader = ContextLoader(db)
        session_mgr = SessionManager(db)

        # Load context from previous sessions
        context = loader.load_session_context()

        # Start a new session (auto-pauses any active one)
        new_session = session_mgr.start_session()

        result = {
            "last_session": context["last_session"],
            "open_tasks": context["open_tasks"],
            "active_decisions": context["active_decisions"],
            "rules": context["rules"],
            "new_session": {
                "id": new_session["id"],
                "started": new_session["started_at"],
            },
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
    finally:
        db.close()
