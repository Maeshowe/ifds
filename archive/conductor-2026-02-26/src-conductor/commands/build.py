"""CONDUCTOR /build — Technical Layer: plan, execute, and track builds."""

import json
from pathlib import Path

from conductor.memory.db import MemoryDB


def run(project_dir: Path, action: str, args) -> str:
    """Execute /build subcommands."""
    db_path = project_dir / ".conductor" / "memory" / "project.db"

    if not db_path.exists():
        return json.dumps({"error": "CONDUCTOR not initialized. Run: python -m conductor init"})

    db = MemoryDB(db_path)
    try:
        if action == "plan":
            return _plan(db, args.brief_id, args.data)
        elif action == "list":
            return _list(db, args.status, getattr(args, "brief_id", None))
        elif action == "status":
            return _update_status(db, args.id, args.new_status)
        elif action == "step":
            return _update_step(db, args.id, args.step, args.status, getattr(args, "notes", None))
        elif action == "get":
            return _get(db, args.id)
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    finally:
        db.close()


def _plan(db: MemoryDB, brief_id: int, data_json: str) -> str:
    """Create a build plan from a brief."""
    try:
        data = json.loads(data_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON data: {e}"})

    # Validate brief exists and is ready
    brief = db.get_brief(brief_id)
    if not brief:
        return json.dumps({"error": f"Brief with id={brief_id} not found."})
    if brief["status"] != "ready":
        return json.dumps({"error": f"Brief status is '{brief['status']}', expected 'ready'."})

    # Get active session ID if available
    active_session = db.get_active_session()
    session_id = active_session["id"] if active_session else None

    plan = db.create_build_plan(
        title=data.get("title", brief["title"]),
        brief_id=brief_id,
        description=data.get("description"),
        approach=data.get("approach"),
        steps=data.get("steps"),
        files_to_create=data.get("files_to_create"),
        files_to_modify=data.get("files_to_modify"),
        acceptance_criteria=data.get("acceptance_criteria"),
        estimated_complexity=data.get("estimated_complexity"),
        status="draft",
        session_id=session_id,
    )

    # Auto-update brief to handed_off
    db.update_brief(brief_id, status="handed_off")

    return json.dumps({
        "plan_saved": {
            "id": plan["id"],
            "title": plan["title"],
            "status": plan["status"],
            "brief_id": plan["brief_id"],
            "step_count": len(data.get("steps", [])),
        },
        "brief_updated": {
            "id": brief_id,
            "new_status": "handed_off",
        },
    }, indent=2, ensure_ascii=False)


def _list(db: MemoryDB, status: str, brief_id: int | None = None) -> str:
    """List build plans."""
    if brief_id:
        plans = db.get_build_plans_by_brief(brief_id)
    elif status == "all":
        plans = db.get_all_build_plans()
    else:
        plans = db.get_build_plans_by_status(status)

    items = []
    for p in plans:
        steps = json.loads(p["steps"]) if p["steps"] else []
        done_count = sum(1 for s in steps if s.get("status") == "done")
        items.append({
            "id": p["id"],
            "title": p["title"],
            "status": p["status"],
            "brief_id": p["brief_id"],
            "created_at": p["created_at"],
            "progress": f"{done_count}/{len(steps)}",
        })

    return json.dumps({"plans": items, "count": len(items)}, indent=2, ensure_ascii=False)


def _update_status(db: MemoryDB, plan_id: int, new_status: str) -> str:
    """Update a build plan's status."""
    existing = db.get_build_plan(plan_id)
    if not existing:
        return json.dumps({"error": f"Build plan with id={plan_id} not found."})

    updated = db.update_build_plan(plan_id, status=new_status)
    return json.dumps({
        "plan_updated": {
            "id": updated["id"],
            "title": updated["title"],
            "old_status": existing["status"],
            "new_status": updated["status"],
        }
    }, indent=2, ensure_ascii=False)


def _update_step(db: MemoryDB, plan_id: int, step_order: int, new_status: str, notes: str | None) -> str:
    """Update a single step within a build plan."""
    plan = db.get_build_plan(plan_id)
    if not plan:
        return json.dumps({"error": f"Build plan with id={plan_id} not found."})

    steps = json.loads(plan["steps"]) if plan["steps"] else []
    if not steps:
        return json.dumps({"error": "Build plan has no steps."})

    # Find step by order number
    step_found = False
    for step in steps:
        if step.get("order") == step_order:
            step["status"] = new_status
            if notes:
                step["notes"] = notes
            step_found = True
            break

    if not step_found:
        return json.dumps({"error": f"Step with order={step_order} not found."})

    # Update steps in DB
    db.update_build_plan(plan_id, steps=steps)

    # Check if all steps are done → auto-complete plan
    all_done = all(s.get("status") in ("done", "skipped") for s in steps)
    plan_status = plan["status"]
    if all_done and plan_status == "in_progress":
        db.update_build_plan(plan_id, status="completed")
        plan_status = "completed"

    done_count = sum(1 for s in steps if s.get("status") == "done")

    return json.dumps({
        "step_updated": {
            "order": step_order,
            "new_status": new_status,
            "notes": notes,
        },
        "plan_status": plan_status,
        "progress": f"{done_count}/{len(steps)}",
    }, indent=2, ensure_ascii=False)


def _get(db: MemoryDB, plan_id: int) -> str:
    """Get full plan details including linked brief."""
    plan = db.get_build_plan(plan_id)
    if not plan:
        return json.dumps({"error": f"Build plan with id={plan_id} not found."})

    result = dict(plan)
    # Parse JSON fields for readability
    for field in ("steps", "files_to_create", "files_to_modify", "acceptance_criteria"):
        if result[field]:
            result[field] = json.loads(result[field])

    # Include linked brief info
    if plan["brief_id"]:
        brief = db.get_brief(plan["brief_id"])
        if brief:
            result["brief"] = {
                "id": brief["id"],
                "title": brief["title"],
                "status": brief["status"],
            }

    return json.dumps(result, indent=2, ensure_ascii=False)
