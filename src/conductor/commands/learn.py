"""CONDUCTOR /learn — Record discovery or correction."""

import json
from pathlib import Path

from conductor.memory.db import MemoryDB

VALID_CATEGORIES = ("rule", "discovery", "correction")


def run(project_dir: Path, content: str, category: str) -> str:
    """Execute /learn and return JSON output."""
    db_path = project_dir / ".conductor" / "memory" / "project.db"

    if not db_path.exists():
        return json.dumps({"error": "CONDUCTOR not initialized. Run: python -m conductor init"})

    if category not in VALID_CATEGORIES:
        return json.dumps({
            "error": f"Invalid category: {category}. Must be one of: {', '.join(VALID_CATEGORIES)}"
        })

    db = MemoryDB(db_path)
    try:
        learning = db.create_learning(content=content, category=category, source="cli")
        total = db.count_learnings()

        # If category is 'rule', also persist to central rules.json
        if category == "rule":
            _add_to_central_rules(content)

        result = {
            "learning_saved": {
                "id": learning["id"],
                "category": learning["category"],
                "content": learning["content"],
            },
            "total_learnings": total,
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
    finally:
        db.close()


def _add_to_central_rules(rule: str) -> None:
    """Add a rule to ~/.conductor/rules.json."""
    rules_path = Path.home() / ".conductor" / "rules.json"
    if not rules_path.exists():
        return

    with open(rules_path) as f:
        data = json.load(f)

    rules = data.get("rules", [])
    if rule not in rules:
        rules.append(rule)
        data["rules"] = rules
        with open(rules_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
