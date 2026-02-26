"""CONDUCTOR initialization — creates project and central structures."""

import json
from datetime import datetime, timezone
from pathlib import Path

from conductor.memory.central import CentralDB
from conductor.memory.db import MemoryDB


def init_project(project_dir: Path) -> dict:
    """Initialize CONDUCTOR in a project directory. Idempotent — only creates missing files."""
    conductor_dir = project_dir / ".conductor"
    results = {"created": [], "skipped": [], "project_dir": str(project_dir)}

    # Create directory structure
    for subdir in ["memory", "agents", "commands"]:
        path = conductor_dir / subdir
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            results["created"].append(str(path))
        else:
            results["skipped"].append(str(path))

    # Create config.json if missing
    config_path = conductor_dir / "config.json"
    if not config_path.exists():
        config = {
            "project": {
                "name": project_dir.name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "version": "0.1.0",
            }
        }
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        results["created"].append(str(config_path))
    else:
        results["skipped"].append(str(config_path))

    # Initialize project database
    db_path = conductor_dir / "memory" / "project.db"
    db_existed = db_path.exists()
    db = MemoryDB(db_path)
    db.init_schema()
    db.close()
    if not db_existed:
        results["created"].append(str(db_path))
    else:
        results["skipped"].append(str(db_path))

    # Initialize central directory + DB + register project
    central_results = init_central()
    results["central"] = central_results

    # Register project in central DB
    project_name = project_dir.name
    if config_path.exists():
        with open(config_path) as f:
            cfg = json.load(f)
        project_name = cfg.get("project", {}).get("name", project_name)

    central_db = CentralDB()
    central_db.init_schema()
    central_db.register_project(name=project_name, path=str(project_dir))
    central_db.close()
    results["registered_in_central"] = True

    return results


def init_central() -> dict:
    """Initialize ~/.conductor/ central directory + central.db. Idempotent."""
    central_dir = Path.home() / ".conductor"
    results = {"created": [], "skipped": []}

    if not central_dir.exists():
        central_dir.mkdir(parents=True, exist_ok=True)
        results["created"].append(str(central_dir))
    else:
        results["skipped"].append(str(central_dir))

    # Create rules.json if missing
    rules_path = central_dir / "rules.json"
    if not rules_path.exists():
        rules = {"rules": [], "_comment": "Permanent rules. Added via /learn --category rule"}
        with open(rules_path, "w") as f:
            json.dump(rules, f, indent=2, ensure_ascii=False)
        results["created"].append(str(rules_path))
    else:
        results["skipped"].append(str(rules_path))

    # Initialize central database
    db_path = central_dir / "central.db"
    db_existed = db_path.exists()
    central_db = CentralDB(db_path)
    central_db.init_schema()
    central_db.close()
    if not db_existed:
        results["created"].append(str(db_path))
    else:
        results["skipped"].append(str(db_path))

    return results
