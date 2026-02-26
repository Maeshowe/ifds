"""CONDUCTOR /test — Test runner: save results, list runs, get details."""

import json
from pathlib import Path

from conductor.memory.db import MemoryDB


def run(project_dir: Path, action: str, args) -> str:
    """Execute /test subcommands."""
    db_path = project_dir / ".conductor" / "memory" / "project.db"

    if not db_path.exists():
        return json.dumps({"error": "CONDUCTOR not initialized. Run: python -m conductor init"})

    db = MemoryDB(db_path)
    try:
        if action == "save":
            return _save(db, args)
        elif action == "list":
            return _list(db, getattr(args, "status", "all"), getattr(args, "plan_id", None))
        elif action == "get":
            return _get(db, args.id)
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    finally:
        db.close()


def _save(db: MemoryDB, args) -> str:
    """Save test run results."""
    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON data: {e}"})

    # Get active session ID if available
    active_session = db.get_active_session()
    session_id = active_session["id"] if active_session else None

    test_run = db.create_test_run(
        test_command=data.get("test_command", "python -m pytest"),
        total_tests=data.get("total_tests"),
        passed=data.get("passed"),
        failed=data.get("failed"),
        errors=data.get("errors"),
        skipped=data.get("skipped"),
        duration_seconds=data.get("duration_seconds"),
        output_summary=data.get("output_summary"),
        status=data.get("status", "passed"),
        build_plan_id=getattr(args, "plan_id", None),
        brief_id=getattr(args, "brief_id", None),
        session_id=session_id,
    )

    return json.dumps({
        "test_saved": {
            "id": test_run["id"],
            "status": test_run["status"],
            "total_tests": test_run["total_tests"],
            "passed": test_run["passed"],
            "failed": test_run["failed"],
        }
    }, indent=2, ensure_ascii=False)


def _list(db: MemoryDB, status: str, plan_id: int | None) -> str:
    """List test runs."""
    if plan_id:
        runs = db.get_test_runs_by_plan(plan_id)
    elif status == "all":
        runs = db.get_all_test_runs()
    else:
        runs = db.get_test_runs_by_status(status)

    items = []
    for r in runs:
        items.append({
            "id": r["id"],
            "status": r["status"],
            "total_tests": r["total_tests"],
            "passed": r["passed"],
            "failed": r["failed"],
            "duration_seconds": r["duration_seconds"],
            "build_plan_id": r["build_plan_id"],
            "created_at": r["created_at"],
        })

    return json.dumps({"test_runs": items, "count": len(items)}, indent=2, ensure_ascii=False)


def _get(db: MemoryDB, run_id: int) -> str:
    """Get full test run details."""
    test_run = db.get_test_run(run_id)
    if not test_run:
        return json.dumps({"error": f"Test run with id={run_id} not found."})

    return json.dumps(dict(test_run), indent=2, ensure_ascii=False)
