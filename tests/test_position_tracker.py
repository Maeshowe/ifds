"""Tests for PositionTracker (BC20A Phase_20A_2).

Covers:
- CRUD: add, get, remove, update, count
- increment_hold_days
- get_expired (max_hold_days)
- get_earnings_risk
- JSON round-trip (_save + _load)
- Empty/missing state file
- Duplicate ticker handling
"""

import json
from datetime import date

import pytest

from ifds.state.position_tracker import OpenPosition, PositionTracker


def _make_pos(ticker: str = "AAPL", **overrides) -> OpenPosition:
    defaults = {
        "ticker": ticker,
        "entry_date": "2026-04-01",
        "entry_price": 150.0,
        "total_qty": 100,
        "remaining_qty": 100,
        "hold_days": 0,
        "max_hold_days": 5,
        "sector": "Technology",
    }
    return OpenPosition(**{**defaults, **overrides})


class TestCRUD:

    def test_add_and_get(self, tmp_path):
        tracker = PositionTracker(str(tmp_path / "pos.json"))
        pos = _make_pos("AAPL")
        tracker.add_position(pos)

        assert tracker.count == 1
        assert tracker.get_position("AAPL") is not None
        assert tracker.get_position("AAPL").entry_price == 150.0

    def test_remove(self, tmp_path):
        tracker = PositionTracker(str(tmp_path / "pos.json"))
        tracker.add_position(_make_pos("AAPL"))
        tracker.add_position(_make_pos("MSFT"))

        removed = tracker.remove_position("AAPL")
        assert removed is not None
        assert removed.ticker == "AAPL"
        assert tracker.count == 1
        assert tracker.get_position("AAPL") is None

    def test_remove_nonexistent(self, tmp_path):
        tracker = PositionTracker(str(tmp_path / "pos.json"))
        assert tracker.remove_position("XYZ") is None

    def test_update(self, tmp_path):
        tracker = PositionTracker(str(tmp_path / "pos.json"))
        tracker.add_position(_make_pos("AAPL"))

        assert tracker.update_position("AAPL", tp1_triggered=True, remaining_qty=50)
        pos = tracker.get_position("AAPL")
        assert pos.tp1_triggered is True
        assert pos.remaining_qty == 50

    def test_update_nonexistent(self, tmp_path):
        tracker = PositionTracker(str(tmp_path / "pos.json"))
        assert tracker.update_position("XYZ", hold_days=3) is False

    def test_get_all(self, tmp_path):
        tracker = PositionTracker(str(tmp_path / "pos.json"))
        tracker.add_position(_make_pos("AAPL"))
        tracker.add_position(_make_pos("MSFT"))

        all_pos = tracker.get_all()
        assert len(all_pos) == 2
        tickers = {p.ticker for p in all_pos}
        assert tickers == {"AAPL", "MSFT"}

    def test_duplicate_ticker_replaces(self, tmp_path):
        tracker = PositionTracker(str(tmp_path / "pos.json"))
        tracker.add_position(_make_pos("AAPL", entry_price=100.0))
        tracker.add_position(_make_pos("AAPL", entry_price=200.0))

        assert tracker.count == 1
        assert tracker.get_position("AAPL").entry_price == 200.0


class TestHoldDays:

    def test_increment(self, tmp_path):
        tracker = PositionTracker(str(tmp_path / "pos.json"))
        tracker.add_position(_make_pos("AAPL", hold_days=0))
        tracker.add_position(_make_pos("MSFT", hold_days=2))

        tracker.increment_hold_days()

        assert tracker.get_position("AAPL").hold_days == 1
        assert tracker.get_position("MSFT").hold_days == 3

    def test_get_expired(self, tmp_path):
        tracker = PositionTracker(str(tmp_path / "pos.json"))
        tracker.add_position(_make_pos("AAPL", hold_days=5, max_hold_days=5))
        tracker.add_position(_make_pos("MSFT", hold_days=3, max_hold_days=5))

        expired = tracker.get_expired()
        assert len(expired) == 1
        assert expired[0].ticker == "AAPL"


class TestEarningsRisk:

    def test_earnings_tomorrow(self, tmp_path):
        tracker = PositionTracker(str(tmp_path / "pos.json"))
        tracker.add_position(_make_pos("AAPL"))

        tomorrow = date.today().isoformat()  # Same day = 0 days = at risk
        at_risk = tracker.get_earnings_risk({"AAPL": tomorrow})
        assert len(at_risk) == 1

    def test_no_earnings(self, tmp_path):
        tracker = PositionTracker(str(tmp_path / "pos.json"))
        tracker.add_position(_make_pos("AAPL"))

        at_risk = tracker.get_earnings_risk({})
        assert len(at_risk) == 0

    def test_earnings_far_away(self, tmp_path):
        tracker = PositionTracker(str(tmp_path / "pos.json"))
        tracker.add_position(_make_pos("AAPL"))

        at_risk = tracker.get_earnings_risk({"AAPL": "2026-12-31"})
        assert len(at_risk) == 0


class TestPersistence:

    def test_save_and_reload(self, tmp_path):
        path = str(tmp_path / "pos.json")

        # Write
        t1 = PositionTracker(path)
        t1.add_position(_make_pos("AAPL", hold_days=3, tp1_triggered=True))
        t1.add_position(_make_pos("MSFT"))

        # Reload
        t2 = PositionTracker(path)
        assert t2.count == 2
        aapl = t2.get_position("AAPL")
        assert aapl.hold_days == 3
        assert aapl.tp1_triggered is True

    def test_empty_state_file(self, tmp_path):
        path = tmp_path / "pos.json"
        path.write_text("{}")

        tracker = PositionTracker(str(path))
        assert tracker.count == 0

    def test_missing_state_file(self, tmp_path):
        tracker = PositionTracker(str(tmp_path / "nonexistent.json"))
        assert tracker.count == 0

    def test_corrupt_json(self, tmp_path):
        path = tmp_path / "pos.json"
        path.write_text("not valid json {{{")

        tracker = PositionTracker(str(path))
        assert tracker.count == 0

    def test_state_has_last_updated(self, tmp_path):
        path = tmp_path / "pos.json"
        tracker = PositionTracker(str(path))
        tracker.add_position(_make_pos("AAPL"))

        data = json.loads(path.read_text())
        assert "last_updated" in data
        assert "positions" in data
