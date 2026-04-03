"""Tests for scripts/paper_trading/lib/event_logger.py — JSONL event logger."""

import json
import sys
from datetime import date
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _ensure_lib_importable():
    """Add scripts/paper_trading to sys.path so ``from lib.event_logger`` works."""
    pt_dir = str(Path(__file__).resolve().parent.parent / "scripts" / "paper_trading")
    added = pt_dir not in sys.path
    if added:
        sys.path.insert(0, pt_dir)
    yield
    if added:
        sys.path.remove(pt_dir)


class TestPTEventLogger:
    """PTEventLogger writes structured JSONL events."""

    def test_creates_jsonl_file(self, tmp_path):
        from lib.event_logger import PTEventLogger

        el = PTEventLogger(log_dir=str(tmp_path))
        el.log("submit", "order_submitted", ticker="AAPL", qty=10)

        today = date.today().strftime("%Y-%m-%d")
        jsonl = tmp_path / f"pt_events_{today}.jsonl"
        assert jsonl.exists()

    def test_writes_valid_json_lines(self, tmp_path):
        from lib.event_logger import PTEventLogger

        el = PTEventLogger(log_dir=str(tmp_path))
        el.log("submit", "order_submitted", ticker="AAPL", qty=10)
        el.log("monitor", "tp1_detected", ticker="MSFT")

        today = date.today().strftime("%Y-%m-%d")
        jsonl = tmp_path / f"pt_events_{today}.jsonl"
        lines = jsonl.read_text().strip().splitlines()
        assert len(lines) == 2

        entry1 = json.loads(lines[0])
        assert entry1["script"] == "submit"
        assert entry1["event"] == "order_submitted"
        assert entry1["ticker"] == "AAPL"
        assert entry1["qty"] == 10
        assert "ts" in entry1

        entry2 = json.loads(lines[1])
        assert entry2["script"] == "monitor"
        assert entry2["event"] == "tp1_detected"
        assert entry2["ticker"] == "MSFT"

    def test_timestamp_is_iso_utc(self, tmp_path):
        from lib.event_logger import PTEventLogger

        el = PTEventLogger(log_dir=str(tmp_path))
        el.log("eod", "daily_pnl", pnl=-150.0)

        today = date.today().strftime("%Y-%m-%d")
        jsonl = tmp_path / f"pt_events_{today}.jsonl"
        entry = json.loads(jsonl.read_text().strip())
        # ISO format with UTC timezone info
        assert entry["ts"].endswith("+00:00") or "T" in entry["ts"]

    def test_appends_to_existing_file(self, tmp_path):
        from lib.event_logger import PTEventLogger

        el = PTEventLogger(log_dir=str(tmp_path))
        el.log("submit", "order_submitted", ticker="A")
        el.log("submit", "order_submitted", ticker="B")
        el.log("submit", "order_submitted", ticker="C")

        today = date.today().strftime("%Y-%m-%d")
        jsonl = tmp_path / f"pt_events_{today}.jsonl"
        lines = jsonl.read_text().strip().splitlines()
        assert len(lines) == 3

    def test_creates_log_dir(self, tmp_path):
        from lib.event_logger import PTEventLogger

        nested = tmp_path / "sub" / "events"
        PTEventLogger(log_dir=str(nested))
        assert nested.is_dir()

    def test_complex_data_types(self, tmp_path):
        from lib.event_logger import PTEventLogger

        el = PTEventLogger(log_dir=str(tmp_path))
        el.log(
            "eod", "leftover_warning",
            leftover=["AAPL:100", "MSFT:50"],
            count=2,
        )

        today = date.today().strftime("%Y-%m-%d")
        jsonl = tmp_path / f"pt_events_{today}.jsonl"
        entry = json.loads(jsonl.read_text().strip())
        assert entry["leftover"] == ["AAPL:100", "MSFT:50"]
        assert entry["count"] == 2
