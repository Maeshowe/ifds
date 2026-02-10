"""Tests for EventLogger structured JSON output."""

import json
import pytest

from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity


@pytest.fixture
def logger(tmp_path):
    """Event logger writing to temp directory."""
    return EventLogger(log_dir=str(tmp_path), run_id="test-001")


class TestEventLogger:
    def test_writes_valid_jsonl(self, logger):
        """Each event line must be valid JSON."""
        logger.log(EventType.PIPELINE_START, Severity.INFO, message="start")
        logger.log(EventType.PHASE_START, Severity.INFO, phase=0, message="phase 0")
        logger.close()

        with open(logger.log_file) as f:
            lines = f.readlines()

        assert len(lines) == 2
        for line in lines:
            event = json.loads(line)  # Must not raise
            assert "timestamp" in event
            assert "event_type" in event
            assert "severity" in event
            assert "message" in event
            assert "run_id" in event

    def test_event_count(self, logger):
        logger.log(EventType.PIPELINE_START, Severity.INFO, message="a")
        logger.log(EventType.PIPELINE_END, Severity.INFO, message="b")
        assert logger.event_count == 2

    def test_events_list_is_copy(self, logger):
        logger.log(EventType.PIPELINE_START, Severity.INFO, message="a")
        events = logger.events
        events.clear()
        assert logger.event_count == 1  # Original not affected

    def test_phase_fields(self, logger):
        logger.phase_start(0, "Diagnostics", input_count=10000)
        event = logger.events[0]
        assert event["phase"] == 0
        assert event["data"]["phase_name"] == "Diagnostics"
        assert event["data"]["input_count"] == 10000

    def test_phase_complete_with_duration(self, logger):
        logger.phase_complete(0, "Diagnostics", output_count=3000, duration_ms=1250.7)
        event = logger.events[0]
        assert event["data"]["output_count"] == 3000
        assert event["data"]["duration_ms"] == 1250.7

    def test_api_health_event(self, logger):
        logger.api_health("polygon", "/v2/aggs", "ok", response_time_ms=150.3)
        event = logger.events[0]
        assert event["data"]["provider"] == "polygon"
        assert event["data"]["status"] == "ok"
        assert event["severity"] == "INFO"

    def test_api_health_down_is_warning(self, logger):
        logger.api_health("fmp", "/screener", "down", error="Timeout")
        event = logger.events[0]
        assert event["severity"] == "WARNING"
        assert event["data"]["error"] == "Timeout"

    def test_api_fallback_event(self, logger):
        logger.api_fallback("unusual_whales", "polygon", "UW down")
        event = logger.events[0]
        assert event["event_type"] == "API_FALLBACK"
        assert event["data"]["primary"] == "unusual_whales"
        assert event["data"]["fallback"] == "polygon"

    def test_halt_event(self, logger):
        logger.halt("Circuit breaker active")
        event = logger.events[0]
        assert event["event_type"] == "PIPELINE_HALT"
        assert event["severity"] == "CRITICAL"

    def test_ticker_field(self, logger):
        logger.log(EventType.TICKER_SCORED, Severity.INFO,
                    ticker="NVDA", message="scored", data={"score": 85})
        event = logger.events[0]
        assert event["ticker"] == "NVDA"
        assert event["data"]["score"] == 85

    def test_context_manager(self, tmp_path):
        with EventLogger(log_dir=str(tmp_path), run_id="ctx-test") as log:
            log.log(EventType.PIPELINE_START, Severity.INFO, message="start")
            log_file = log.log_file

        # File should exist and be readable after close
        with open(log_file) as f:
            assert len(f.readlines()) == 1

    def test_close_is_idempotent(self, logger):
        logger.close()
        logger.close()  # Should not raise
