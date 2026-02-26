"""CONDUCTOR /where-am-i — Instant orientation."""

import json
from pathlib import Path

from conductor.memory.context import ContextLoader
from conductor.memory.db import MemoryDB


def run(project_dir: Path) -> str:
    """Execute /where-am-i and return JSON output."""
    db_path = project_dir / ".conductor" / "memory" / "project.db"
    config_path = project_dir / ".conductor" / "config.json"

    if not db_path.exists():
        return json.dumps({"error": "CONDUCTOR not initialized. Run: python -m conductor init"})

    db = MemoryDB(db_path)
    try:
        loader = ContextLoader(db)
        orientation = loader.load_orientation()

        # Load project config
        project_name = project_dir.name
        project_phase = None
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
            project_name = config.get("project", {}).get("name", project_name)
            project_phase = config.get("project", {}).get("phase")

        # Calculate session duration if active
        session_info = None
        if orientation["active_session"]:
            session = orientation["active_session"]
            session_info = {
                "id": session["id"],
                "started": session["started_at"],
                "status": session["status"],
            }

        # Active briefs summary
        briefs_info = []
        for b in orientation.get("active_briefs", []):
            briefs_info.append({
                "id": b["id"],
                "title": b["title"],
                "status": b["status"],
            })

        # Active build plans summary
        plans_info = []
        for p in orientation.get("active_build_plans", []):
            plans_info.append({
                "id": p["id"],
                "title": p["title"],
                "status": p["status"],
                "brief_id": p.get("brief_id"),
            })

        # Last test run summary
        last_test_run = None
        recent_runs = orientation.get("recent_test_run", [])
        if recent_runs:
            r = recent_runs[0]
            last_test_run = {
                "id": r["id"],
                "status": r["status"],
                "passed": r.get("passed"),
                "failed": r.get("failed"),
                "total": r.get("total_tests"),
                "duration": r.get("duration_seconds"),
            }

        result = {
            "project": project_name,
            "phase": project_phase,
            "session": session_info,
            "active_tasks": orientation["open_tasks"],
            "active_decisions": orientation["active_decisions"],
            "recent_learnings": orientation["recent_learnings"],
            "active_briefs": briefs_info,
            "active_build_plans": plans_info,
            "last_test_run": last_test_run,
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
    finally:
        db.close()
