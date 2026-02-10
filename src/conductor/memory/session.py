"""Session management for CONDUCTOR memory."""

from conductor.memory.db import MemoryDB


class SessionManager:
    """Manages session lifecycle: start, pause, resume, end."""

    def __init__(self, db: MemoryDB):
        self.db = db

    def start_session(self) -> dict:
        """Start a new session. If an active session exists, pause it first."""
        active = self.db.get_active_session()
        if active:
            self.db.pause_session(active["id"])
        return self.db.create_session()

    def end_session(self, summary: str) -> dict | None:
        """End the active session with a summary. Returns None if no active session."""
        active = self.db.get_active_session()
        if not active:
            return None
        return self.db.end_session(active["id"], summary)

    def pause_session(self) -> dict | None:
        """Pause the active session (emergency save). Returns None if no active session."""
        active = self.db.get_active_session()
        if not active:
            return None
        return self.db.pause_session(active["id"])

    def get_active(self) -> dict | None:
        """Get the currently active session."""
        return self.db.get_active_session()

    def get_last(self) -> dict | None:
        """Get the last completed or paused session."""
        return self.db.get_last_session()
