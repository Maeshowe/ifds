"""CONDUCTOR /review — Technical Layer: code review management."""

import json
from pathlib import Path

from conductor.memory.db import MemoryDB


def run(project_dir: Path, action: str, args) -> str:
    """Execute /review subcommands."""
    db_path = project_dir / ".conductor" / "memory" / "project.db"

    if not db_path.exists():
        return json.dumps({"error": "CONDUCTOR not initialized. Run: python -m conductor init"})

    db = MemoryDB(db_path)
    try:
        if action == "create":
            return _create(db, args)
        elif action == "list":
            return _list(db, getattr(args, "plan_id", None), getattr(args, "verdict", None))
        elif action == "update":
            return _update(db, args)
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    finally:
        db.close()


def _create(db: MemoryDB, args) -> str:
    """Create a new review."""
    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON data: {e}"})

    plan_id = getattr(args, "plan_id", None)
    brief_id = getattr(args, "brief_id", None)
    review_type = getattr(args, "type", "code")

    # Get active session ID if available
    active_session = db.get_active_session()
    session_id = active_session["id"] if active_session else None

    review = db.create_review(
        build_plan_id=plan_id,
        brief_id=brief_id,
        review_type=review_type,
        scope=data.get("scope"),
        findings=data.get("findings"),
        verdict=data.get("verdict", "pending"),
        summary=data.get("summary"),
        session_id=session_id,
    )

    result = {
        "review_saved": {
            "id": review["id"],
            "verdict": review["verdict"],
            "review_type": review["review_type"],
            "build_plan_id": review["build_plan_id"],
        }
    }

    # If approved and brief_id given, auto-complete the brief
    if review["verdict"] == "approved" and brief_id:
        brief = db.get_brief(brief_id)
        if brief and brief["status"] != "completed":
            db.update_brief(brief_id, status="completed")
            result["brief_completed"] = {"id": brief_id, "new_status": "completed"}

    return json.dumps(result, indent=2, ensure_ascii=False)


def _list(db: MemoryDB, plan_id: int | None, verdict: str | None) -> str:
    """List reviews."""
    if plan_id:
        reviews = db.get_reviews_by_plan(plan_id)
    elif verdict:
        reviews = db.get_reviews_by_verdict(verdict)
    else:
        # All reviews — query directly
        rows = db.conn.execute("SELECT * FROM reviews ORDER BY id DESC").fetchall()
        reviews = [dict(r) for r in rows]

    items = []
    for r in reviews:
        items.append({
            "id": r["id"],
            "review_type": r["review_type"],
            "verdict": r["verdict"],
            "build_plan_id": r["build_plan_id"],
            "created_at": r["created_at"],
            "has_summary": r["summary"] is not None,
        })

    return json.dumps({"reviews": items, "count": len(items)}, indent=2, ensure_ascii=False)


def _update(db: MemoryDB, args) -> str:
    """Update a review's verdict and/or findings."""
    review_id = args.id
    existing = db.get_review(review_id)
    if not existing:
        return json.dumps({"error": f"Review with id={review_id} not found."})

    kwargs = {}
    if getattr(args, "verdict", None):
        kwargs["verdict"] = args.verdict
    if getattr(args, "data", None):
        try:
            data = json.loads(args.data)
            if "findings" in data:
                kwargs["findings"] = data["findings"]
            if "summary" in data:
                kwargs["summary"] = data["summary"]
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON data: {e}"})

    if not kwargs:
        return json.dumps({"error": "No update fields provided."})

    updated = db.update_review(review_id, **kwargs)
    return json.dumps({
        "review_updated": {
            "id": updated["id"],
            "old_verdict": existing["verdict"],
            "new_verdict": updated["verdict"],
        }
    }, indent=2, ensure_ascii=False)
