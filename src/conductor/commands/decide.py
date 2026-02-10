"""CONDUCTOR /decide — Decision Journal: record, list, and manage decisions."""

import json
from pathlib import Path

from conductor.memory.db import MemoryDB


def run(project_dir: Path, action: str, args) -> str:
    """Execute /decide subcommands."""
    db_path = project_dir / ".conductor" / "memory" / "project.db"

    if not db_path.exists():
        return json.dumps({"error": "CONDUCTOR not initialized. Run: python -m conductor init"})

    db = MemoryDB(db_path)
    try:
        if action == "create":
            return _create(db, args)
        elif action == "list":
            return _list(db, getattr(args, "status", "active"), getattr(args, "tag", None))
        elif action == "get":
            return _get(db, args.id)
        elif action == "archive":
            return _archive(db, args.id)
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    finally:
        db.close()


def _create(db: MemoryDB, args) -> str:
    """Create a new decision entry."""
    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON data: {e}"})

    decision = db.create_decision(
        title=args.title,
        description=data.get("description"),
        alternatives=data.get("alternatives"),
        rationale=data.get("rationale"),
        tags=data.get("tags"),
    )

    return json.dumps({
        "decision_saved": {
            "id": decision["id"],
            "title": decision["title"],
            "status": decision["status"],
        }
    }, indent=2, ensure_ascii=False)


def _list(db: MemoryDB, status: str, tag: str | None) -> str:
    """List decisions, optionally filtered by status and tag."""
    if status == "all":
        decisions = db.get_all_decisions()
    else:
        all_decisions = db.get_all_decisions()
        decisions = [d for d in all_decisions if d["status"] == status]

    # Filter by tag if provided
    if tag:
        filtered = []
        for d in decisions:
            tags = json.loads(d["tags"]) if d["tags"] else []
            if tag in tags:
                filtered.append(d)
        decisions = filtered

    items = []
    for d in decisions:
        items.append({
            "id": d["id"],
            "title": d["title"],
            "status": d["status"],
            "tags": json.loads(d["tags"]) if d["tags"] else [],
            "created_at": d["created_at"],
        })

    return json.dumps({"decisions": items, "count": len(items)}, indent=2, ensure_ascii=False)


def _get(db: MemoryDB, decision_id: int) -> str:
    """Get full decision details."""
    decision = db.get_decision(decision_id)
    if not decision:
        return json.dumps({"error": f"Decision with id={decision_id} not found."})

    result = dict(decision)
    # Parse JSON fields
    if result["alternatives"]:
        result["alternatives"] = json.loads(result["alternatives"])
    if result["tags"]:
        result["tags"] = json.loads(result["tags"])

    return json.dumps(result, indent=2, ensure_ascii=False)


def _archive(db: MemoryDB, decision_id: int) -> str:
    """Archive a decision."""
    existing = db.get_decision(decision_id)
    if not existing:
        return json.dumps({"error": f"Decision with id={decision_id} not found."})

    updated = db.update_decision(decision_id, status="archived")
    return json.dumps({
        "decision_archived": {
            "id": updated["id"],
            "title": updated["title"],
            "old_status": existing["status"],
            "new_status": updated["status"],
        }
    }, indent=2, ensure_ascii=False)
