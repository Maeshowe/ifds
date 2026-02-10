"""CONDUCTOR /setup-env — Environment inspection and documentation."""

import json
import sys
from pathlib import Path

from conductor.memory.db import MemoryDB


def run(project_dir: Path, action: str, args) -> str:
    """Execute /setup-env subcommands."""
    if action == "check":
        return _check(project_dir)
    elif action == "save":
        return _save(project_dir, args)
    else:
        return json.dumps({"error": f"Unknown action: {action}"})


def _check(project_dir: Path) -> str:
    """Inspect and report the current environment."""
    # Python info
    python_version = sys.version.split()[0]
    platform = sys.platform

    # Venv detection
    in_venv = sys.prefix != sys.base_prefix
    venv_path = sys.prefix if in_venv else None

    # Project dependencies from pyproject.toml
    dependencies = []
    pyproject_path = project_dir / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        # Simple parser for dependencies (no toml lib in stdlib)
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("dependencies"):
                in_deps = True
                continue
            if in_deps:
                if stripped == "]":
                    in_deps = False
                elif stripped.startswith('"') or stripped.startswith("'"):
                    dep = stripped.strip('",\' ')
                    if dep:
                        dependencies.append(dep)

    # Conductor status
    conductor_initialized = (project_dir / ".conductor" / "memory" / "project.db").exists()

    result = {
        "python": python_version,
        "platform": platform,
        "in_venv": in_venv,
        "venv_path": venv_path,
        "project_dir": str(project_dir),
        "dependencies": dependencies,
        "conductor_initialized": conductor_initialized,
    }

    return json.dumps(result, indent=2, ensure_ascii=False)


def _save(project_dir: Path, args) -> str:
    """Save environment snapshot as a learning entry."""
    db_path = project_dir / ".conductor" / "memory" / "project.db"

    if not db_path.exists():
        return json.dumps({"error": "CONDUCTOR not initialized. Run: python -m conductor init"})

    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON data: {e}"})

    db = MemoryDB(db_path)
    try:
        content = json.dumps(data, ensure_ascii=False)
        learning = db.create_learning(
            content=f"Environment snapshot: {content}",
            category="environment",
            source="setup-env",
        )
        return json.dumps({
            "environment_saved": {
                "learning_id": learning["id"],
                "category": learning["category"],
            }
        }, indent=2, ensure_ascii=False)
    finally:
        db.close()
