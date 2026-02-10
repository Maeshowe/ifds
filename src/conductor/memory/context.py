"""Context loading for CONDUCTOR — what gets loaded at session start."""

import json
from pathlib import Path

from conductor.memory.central import CentralDB
from conductor.memory.db import MemoryDB


class ContextLoader:
    """Loads the smart subset of memory for session start."""

    def __init__(
        self,
        db: MemoryDB,
        central_db: CentralDB | None = None,
        central_dir: Path | None = None,
    ):
        self.db = db
        self.central_db = central_db
        self.central_dir = central_dir or Path.home() / ".conductor"

    def load_session_context(self) -> dict:
        """Load context for /continue: last session + active decisions + open tasks + rules + briefs + plans."""
        context = {
            "last_session": self.db.get_last_session(),
            "active_decisions": self.db.get_active_decisions(),
            "open_tasks": self.db.get_open_tasks(),
            "rules": self.load_rules(),
            "active_briefs": self.db.get_briefs_by_status("draft") + self.db.get_briefs_by_status("ready"),
            "active_build_plans": (
                self.db.get_build_plans_by_status("draft")
                + self.db.get_build_plans_by_status("approved")
                + self.db.get_build_plans_by_status("in_progress")
            ),
        }
        if self.central_db:
            context["central_decisions"] = self.central_db.get_active_decisions()
        return context

    def load_orientation(self) -> dict:
        """Load context for /where-am-i: active session + tasks + decisions + learnings + briefs + plans."""
        orientation = {
            "active_session": self.db.get_active_session(),
            "active_decisions": self.db.get_active_decisions(),
            "open_tasks": self.db.get_open_tasks(),
            "recent_learnings": self.db.get_recent_learnings(limit=5),
            "active_briefs": self.db.get_briefs_by_status("draft") + self.db.get_briefs_by_status("ready"),
            "active_build_plans": (
                self.db.get_build_plans_by_status("draft")
                + self.db.get_build_plans_by_status("approved")
                + self.db.get_build_plans_by_status("in_progress")
            ),
            "recent_test_run": self.db.get_recent_test_runs(limit=1),
        }
        if self.central_db:
            orientation["central_decisions"] = self.central_db.get_active_decisions()
        return orientation

    def load_rules(self) -> list[str]:
        """Load permanent rules from ~/.conductor/rules.json."""
        rules_path = self.central_dir / "rules.json"
        if not rules_path.exists():
            return []
        with open(rules_path) as f:
            data = json.load(f)
        if isinstance(data.get("rules"), list):
            return data["rules"]
        return []

    def search(self, query: str) -> list[dict]:
        """FTS5 search across project + central memory."""
        results = self.db.search(query)
        if self.central_db:
            results.extend(self.central_db.search(query))
            results.sort(key=lambda r: r.get("rank", 0))
        return results
