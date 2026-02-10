"""Tests for BMI and sector history tracking."""

import json
from datetime import date
from unittest.mock import patch

import pytest

from ifds.state.history import BMIHistory, SectorHistory


class TestBMIHistory:
    def test_append_and_load(self, tmp_path):
        h = BMIHistory(state_dir=str(tmp_path))
        h.append(49.8, "yellow")
        entries = h.load()
        assert len(entries) == 1
        assert entries[0]["bmi"] == 49.8
        assert entries[0]["regime"] == "yellow"
        assert entries[0]["date"] == date.today().isoformat()

    def test_dedup_same_day(self, tmp_path):
        h = BMIHistory(state_dir=str(tmp_path))
        h.append(49.8, "yellow")
        h.append(50.2, "yellow")
        entries = h.load()
        assert len(entries) == 1
        assert entries[0]["bmi"] == 50.2

    def test_get_previous_returns_none_first_day(self, tmp_path):
        h = BMIHistory(state_dir=str(tmp_path))
        h.append(49.8, "yellow")
        assert h.get_previous() is None

    def test_get_previous_returns_yesterday(self, tmp_path):
        h = BMIHistory(state_dir=str(tmp_path))
        # Manually write a previous entry
        entries = [
            {"date": "2025-01-01", "bmi": 45.0, "regime": "yellow"},
        ]
        path = tmp_path / "bmi_history.json"
        path.write_text(json.dumps(entries))
        h.append(49.8, "yellow")

        prev = h.get_previous()
        assert prev is not None
        assert prev["bmi"] == 45.0

    def test_max_entries_trimmed(self, tmp_path):
        h = BMIHistory(state_dir=str(tmp_path))
        # Write 95 entries manually
        entries = [{"date": f"2024-{i:03d}", "bmi": float(i), "regime": "yellow"}
                   for i in range(95)]
        path = tmp_path / "bmi_history.json"
        path.write_text(json.dumps(entries))

        h.append(99.0, "red")
        loaded = h.load()
        assert len(loaded) <= BMIHistory.MAX_ENTRIES

    def test_empty_file_handled(self, tmp_path):
        h = BMIHistory(state_dir=str(tmp_path))
        (tmp_path / "bmi_history.json").write_text("")
        assert h.load() == []

    def test_corrupt_json_handled(self, tmp_path):
        h = BMIHistory(state_dir=str(tmp_path))
        (tmp_path / "bmi_history.json").write_text("{invalid")
        assert h.load() == []


class TestSectorHistory:
    def test_append_and_load(self, tmp_path):
        h = SectorHistory(state_dir=str(tmp_path))
        h.append({"XLK": 2.5, "XLE": -1.2})
        entries = h.load()
        assert len(entries) == 1
        assert entries[0]["sectors"]["XLK"] == 2.5

    def test_dedup_same_day(self, tmp_path):
        h = SectorHistory(state_dir=str(tmp_path))
        h.append({"XLK": 2.5})
        h.append({"XLK": 3.0})
        entries = h.load()
        assert len(entries) == 1
        assert entries[0]["sectors"]["XLK"] == 3.0

    def test_get_previous_returns_none_first_day(self, tmp_path):
        h = SectorHistory(state_dir=str(tmp_path))
        h.append({"XLK": 2.5})
        assert h.get_previous() is None

    def test_get_previous_returns_yesterday(self, tmp_path):
        h = SectorHistory(state_dir=str(tmp_path))
        entries = [
            {"date": "2025-01-01", "sectors": {"XLK": 1.0, "XLE": -0.5}},
        ]
        path = tmp_path / "sector_history.json"
        path.write_text(json.dumps(entries))
        h.append({"XLK": 2.5})

        prev = h.get_previous()
        assert prev is not None
        assert prev["XLK"] == 1.0

    def test_empty_file_handled(self, tmp_path):
        h = SectorHistory(state_dir=str(tmp_path))
        (tmp_path / "sector_history.json").write_text("")
        assert h.load() == []
