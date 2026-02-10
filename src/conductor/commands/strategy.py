"""CONDUCTOR Strategy Layer — red-team, scenarios, compliance analyses."""

import json
from pathlib import Path

from conductor.memory.db import MemoryDB


def run(project_dir: Path, analysis_type: str, action: str, args) -> str:
    """Execute strategy analysis subcommands (red-team, scenarios, compliance)."""
    db_path = project_dir / ".conductor" / "memory" / "project.db"

    if not db_path.exists():
        return json.dumps({"error": "CONDUCTOR not initialized. Run: python -m conductor init"})

    db = MemoryDB(db_path)
    try:
        if action == "save":
            return _save(db, analysis_type, args)
        elif action == "list":
            return _list(db, analysis_type, getattr(args, "status", "active"))
        elif action == "get":
            return _get(db, args.id)
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    finally:
        db.close()


def _save(db: MemoryDB, analysis_type: str, args) -> str:
    """Save a strategy analysis."""
    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON data: {e}"})

    # Get active session ID if available
    active_session = db.get_active_session()
    session_id = active_session["id"] if active_session else None

    analysis = db.create_strategy_analysis(
        analysis_type=analysis_type,
        title=args.title,
        target_type=getattr(args, "target_type", None),
        target_id=getattr(args, "target_id", None),
        input_text=data.get("input_text"),
        findings=data,
        recommendation=data.get("recommendation"),
        status="active",
        session_id=session_id,
    )

    return json.dumps({
        "analysis_saved": {
            "id": analysis["id"],
            "type": analysis["analysis_type"],
            "title": analysis["title"],
            "status": analysis["status"],
            "target_type": analysis["target_type"],
            "target_id": analysis["target_id"],
        }
    }, indent=2, ensure_ascii=False)


def _list(db: MemoryDB, analysis_type: str, status: str) -> str:
    """List strategy analyses by type."""
    if status == "all":
        analyses = db.get_analyses_by_type(analysis_type)
    else:
        all_analyses = db.get_analyses_by_type(analysis_type)
        analyses = [a for a in all_analyses if a["status"] == status]

    items = []
    for a in analyses:
        items.append({
            "id": a["id"],
            "title": a["title"],
            "status": a["status"],
            "target_type": a["target_type"],
            "target_id": a["target_id"],
            "created_at": a["created_at"],
        })

    return json.dumps({"analyses": items, "count": len(items)}, indent=2, ensure_ascii=False)


def _get(db: MemoryDB, analysis_id: int) -> str:
    """Get full analysis details."""
    analysis = db.get_strategy_analysis(analysis_id)
    if not analysis:
        return json.dumps({"error": f"Strategy analysis with id={analysis_id} not found."})

    result = dict(analysis)
    # Parse JSON findings
    if result["findings"]:
        result["findings"] = json.loads(result["findings"])

    return json.dumps(result, indent=2, ensure_ascii=False)
