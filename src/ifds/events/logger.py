"""Structured JSON event logger for IFDS pipeline.

Every decision, phase transition, and error is logged as a structured JSON event.
This provides a complete audit trail of why the pipeline made each decision.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ifds.events.types import EventType, Severity


class EventLogger:
    """Structured event logger that writes JSON events to file and stdout.

    Each event is a single JSON line (JSONL format) for easy parsing.
    """

    def __init__(self, log_dir: str = "logs", run_id: str = ""):
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._run_id = run_id
        self._events: list[dict] = []

        # Log file: logs/ifds_run_YYYYMMDD_HHMMSS.jsonl
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._log_file = self._log_dir / f"ifds_run_{timestamp}.jsonl"
        self._file_handle = open(self._log_file, "a")

    def log(self, event_type: EventType, severity: Severity = Severity.INFO,
            phase: int | None = None, ticker: str | None = None,
            data: dict[str, Any] | None = None, message: str = "") -> None:
        """Log a structured event.

        Args:
            event_type: Category of event.
            severity: Importance level.
            phase: Pipeline phase number (0-6) if applicable.
            ticker: Stock ticker if applicable.
            data: Additional structured data.
            message: Human-readable message.
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": self._run_id,
            "event_type": event_type.value,
            "severity": severity.value,
            "message": message,
        }

        if phase is not None:
            event["phase"] = phase

        if ticker:
            event["ticker"] = ticker

        if data:
            event["data"] = data

        self._events.append(event)
        self._write_event(event)

    def phase_start(self, phase: int, name: str, input_count: int | None = None) -> None:
        """Log the start of a pipeline phase."""
        data = {"phase_name": name}
        if input_count is not None:
            data["input_count"] = input_count
        self.log(
            EventType.PHASE_START, Severity.INFO,
            phase=phase, message=f"Phase {phase} started: {name}", data=data,
        )

    def phase_complete(self, phase: int, name: str, output_count: int | None = None,
                       duration_ms: float | None = None) -> None:
        """Log the completion of a pipeline phase."""
        data = {"phase_name": name}
        if output_count is not None:
            data["output_count"] = output_count
        if duration_ms is not None:
            data["duration_ms"] = round(duration_ms, 1)
        self.log(
            EventType.PHASE_COMPLETE, Severity.INFO,
            phase=phase, message=f"Phase {phase} complete: {name}", data=data,
        )

    def phase_error(self, phase: int, name: str, error: str) -> None:
        """Log a phase error."""
        self.log(
            EventType.PHASE_ERROR, Severity.ERROR,
            phase=phase, message=f"Phase {phase} error: {error}",
            data={"phase_name": name, "error": error},
        )

    def halt(self, reason: str) -> None:
        """Log a pipeline halt."""
        self.log(
            EventType.PIPELINE_HALT, Severity.CRITICAL,
            message=f"PIPELINE HALT: {reason}", data={"reason": reason},
        )

    def api_health(self, provider: str, endpoint: str, status: str,
                   response_time_ms: float | None = None,
                   error: str | None = None) -> None:
        """Log an API health check result."""
        data = {"provider": provider, "endpoint": endpoint, "status": status}
        if response_time_ms is not None:
            data["response_time_ms"] = round(response_time_ms, 1)
        if error:
            data["error"] = error
        severity = Severity.INFO if status == "ok" else Severity.WARNING
        self.log(
            EventType.API_HEALTH_CHECK, severity,
            phase=0, message=f"API {provider}: {status}", data=data,
        )

    def api_fallback(self, primary: str, fallback: str, reason: str) -> None:
        """Log an API fallback (e.g., UW → Polygon)."""
        self.log(
            EventType.API_FALLBACK, Severity.WARNING,
            message=f"Fallback: {primary} → {fallback} ({reason})",
            data={"primary": primary, "fallback": fallback, "reason": reason},
        )

    def _write_event(self, event: dict) -> None:
        """Write event to log file (JSONL) and print summary to stderr.

        Only ERROR and CRITICAL are printed to stderr.
        All events (including DEBUG/INFO/WARNING) are always written to JSONL.
        """
        line = json.dumps(event, ensure_ascii=False)
        self._file_handle.write(line + "\n")
        self._file_handle.flush()

        # Only print ERROR and CRITICAL to stderr — rest goes to JSONL only
        severity = event["severity"]
        if severity in ("error", "critical"):
            prefix = f"[{severity}]"
            phase_str = f"[P{event['phase']}]" if "phase" in event else ""
            ticker_str = f"[{event['ticker']}]" if "ticker" in event else ""
            print(f"  {prefix} {phase_str}{ticker_str} {event['message']}", file=sys.stderr)

    @property
    def log_file(self) -> Path:
        """Path to the current log file."""
        return self._log_file

    @property
    def event_count(self) -> int:
        """Number of events logged."""
        return len(self._events)

    @property
    def events(self) -> list[dict]:
        """All logged events."""
        return self._events.copy()

    def close(self) -> None:
        """Close the log file handle."""
        if self._file_handle and not self._file_handle.closed:
            self._file_handle.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
