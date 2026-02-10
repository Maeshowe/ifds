"""CONDUCTOR /analyze-idea — BA Bridge: save, list, and manage briefs."""

import json
from pathlib import Path

from conductor.memory.db import MemoryDB


def run(project_dir: Path, action: str, args) -> str:
    """Execute /analyze-idea subcommands."""
    db_path = project_dir / ".conductor" / "memory" / "project.db"

    if not db_path.exists():
        return json.dumps({"error": "CONDUCTOR not initialized. Run: python -m conductor init"})

    db = MemoryDB(db_path)
    try:
        if action == "save":
            return _save(db, args.title, args.data)
        elif action == "list":
            return _list(db, args.status)
        elif action == "status":
            return _update_status(db, args.id, args.new_status)
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    finally:
        db.close()


def _save(db: MemoryDB, title: str, data_json: str) -> str:
    """Save a structured brief from JSON data."""
    try:
        data = json.loads(data_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON data: {e}"})

    # Get active session ID if available
    active_session = db.get_active_session()
    session_id = active_session["id"] if active_session else None

    brief = db.create_brief(
        title=title,
        raw_idea=data.get("raw_idea", ""),
        problem=data.get("problem"),
        target_user=data.get("target_user"),
        scope_essential=data.get("scope_essential"),
        scope_nice_to_have=data.get("scope_nice_to_have"),
        scope_out=data.get("scope_out"),
        constraints=data.get("constraints"),
        first_version=data.get("first_version"),
        brief_text=data.get("brief_text"),
        status=data.get("status", "draft"),
        session_id=session_id,
    )

    return json.dumps({
        "brief_saved": {
            "id": brief["id"],
            "title": brief["title"],
            "status": brief["status"],
        },
        "total_briefs": len(db.get_all_briefs()),
    }, indent=2, ensure_ascii=False)


def _list(db: MemoryDB, status: str) -> str:
    """List briefs, optionally filtered by status."""
    if status == "all":
        briefs = db.get_all_briefs()
    else:
        briefs = db.get_briefs_by_status(status)

    items = []
    for b in briefs:
        items.append({
            "id": b["id"],
            "title": b["title"],
            "status": b["status"],
            "created_at": b["created_at"],
            "has_brief_text": b["brief_text"] is not None,
        })

    return json.dumps({"briefs": items, "count": len(items)}, indent=2, ensure_ascii=False)


def _update_status(db: MemoryDB, brief_id: int, new_status: str) -> str:
    """Update a brief's status."""
    existing = db.get_brief(brief_id)
    if not existing:
        return json.dumps({"error": f"Brief with id={brief_id} not found."})

    updated = db.update_brief(brief_id, status=new_status)
    return json.dumps({
        "brief_updated": {
            "id": updated["id"],
            "title": updated["title"],
            "old_status": existing["status"],
            "new_status": updated["status"],
        }
    }, indent=2, ensure_ascii=False)
