"""Tests for Swing Manager (BC20A Phase_20A_4).

Covers:
- Hold day increment
- TP1 triggered → trail activation
- Breakeven SL raise
- Max hold MOC exit
- Earnings risk early exit
- Trail update (only upward)
"""

from datetime import date

import pytest

from ifds.state.position_tracker import OpenPosition, PositionTracker
from ifds.state.swing_manager import (
    SwingAction,
    SwingDecision,
    run_swing_management,
)


def _make_pos(ticker: str = "AAPL", **overrides) -> OpenPosition:
    defaults = {
        "ticker": ticker,
        "entry_date": "2026-04-01",
        "entry_price": 150.0,
        "total_qty": 100,
        "remaining_qty": 100,
        "hold_days": 0,
        "max_hold_days": 5,
        "atr_at_entry": 3.0,
        "sector": "Technology",
    }
    return OpenPosition(**{**defaults, **overrides})


@pytest.fixture()
def tracker(tmp_path):
    return PositionTracker(str(tmp_path / "pos.json"))


class TestHoldDays:

    def test_increment(self, tracker):
        tracker.add_position(_make_pos("AAPL", hold_days=0))
        run_swing_management(tracker, {"AAPL": 151.0}, today=date(2026, 4, 2))
        assert tracker.get_position("AAPL").hold_days == 1


class TestMaxHold:

    def test_d5_moc_exit(self, tracker):
        tracker.add_position(_make_pos("AAPL", hold_days=4))  # +1 = 5 = max
        decisions = run_swing_management(tracker, {"AAPL": 155.0}, today=date(2026, 4, 6))

        moc = [d for d in decisions if d.action == SwingAction.MOC_EXIT]
        assert len(moc) == 1
        assert moc[0].reason == "max_hold"
        assert moc[0].qty == 100

    def test_d3_no_exit(self, tracker):
        tracker.add_position(_make_pos("AAPL", hold_days=2))  # +1 = 3 < 5
        decisions = run_swing_management(tracker, {"AAPL": 155.0})

        moc = [d for d in decisions if d.action == SwingAction.MOC_EXIT]
        assert len(moc) == 0


class TestBreakeven:

    def test_breakeven_triggered(self, tracker):
        """Price >= entry + 0.3×ATR → SL raised to entry."""
        # ATR=3.0, entry=150 → threshold = 150 + 0.9 = 150.9
        tracker.add_position(_make_pos("AAPL", hold_days=0))
        decisions = run_swing_management(tracker, {"AAPL": 151.0})

        sl_mods = [d for d in decisions if d.action == SwingAction.MODIFY_SL]
        assert len(sl_mods) == 1
        assert sl_mods[0].reason == "breakeven"
        assert sl_mods[0].price == 150.0

        # Verify tracker updated
        assert tracker.get_position("AAPL").breakeven_triggered is True

    def test_already_breakeven_no_action(self, tracker):
        tracker.add_position(_make_pos("AAPL", breakeven_triggered=True))
        decisions = run_swing_management(tracker, {"AAPL": 155.0})

        sl_mods = [d for d in decisions if d.action == SwingAction.MODIFY_SL and d.reason == "breakeven"]
        assert len(sl_mods) == 0

    def test_below_threshold_no_breakeven(self, tracker):
        """Price < entry + 0.3×ATR → no breakeven."""
        tracker.add_position(_make_pos("AAPL"))
        decisions = run_swing_management(tracker, {"AAPL": 150.5})  # 0.5 < 0.9

        sl_mods = [d for d in decisions if d.reason == "breakeven"]
        assert len(sl_mods) == 0


class TestTrailActivation:

    def test_tp1_activates_trail(self, tracker):
        """TP1 triggered + no trail yet → activate trail."""
        tracker.add_position(_make_pos("AAPL", tp1_triggered=True, remaining_qty=50))
        decisions = run_swing_management(tracker, {"AAPL": 155.0})

        trail = [d for d in decisions if d.action == SwingAction.ACTIVATE_TRAIL]
        assert len(trail) == 1
        assert trail[0].qty == 50
        # Trail amount = 1.0 × ATR = 3.0
        assert trail[0].trail_amount == 3.0
        # Trail stop = 155 - 3 = 152
        assert trail[0].price == 152.0

    def test_trail_already_active_no_reactivation(self, tracker):
        """Trail already active → no reactivation."""
        tracker.add_position(_make_pos("AAPL", tp1_triggered=True,
                                        trail_amount_usd=3.0, current_trail_stop=152.0))
        decisions = run_swing_management(tracker, {"AAPL": 155.0})

        trail = [d for d in decisions if d.action == SwingAction.ACTIVATE_TRAIL]
        assert len(trail) == 0


class TestTrailUpdate:

    def test_trail_tighten_upward(self, tracker):
        """Price rises → trail stop rises."""
        tracker.add_position(_make_pos("AAPL", tp1_triggered=True,
                                        trail_amount_usd=3.0, current_trail_stop=152.0,
                                        remaining_qty=50))
        # Price 158 → new trail = 158 - 3 = 155 > 152 → update
        decisions = run_swing_management(tracker, {"AAPL": 158.0})

        updates = [d for d in decisions if d.action == SwingAction.UPDATE_TRAIL]
        assert len(updates) == 1
        assert updates[0].price == 155.0

    def test_trail_no_update_downward(self, tracker):
        """Price drops → trail stop stays (only upward)."""
        tracker.add_position(_make_pos("AAPL", tp1_triggered=True,
                                        trail_amount_usd=3.0, current_trail_stop=155.0,
                                        remaining_qty=50))
        # Price 156 → new trail = 156 - 3 = 153 < 155 → no update
        decisions = run_swing_management(tracker, {"AAPL": 156.0})

        updates = [d for d in decisions if d.action == SwingAction.UPDATE_TRAIL]
        assert len(updates) == 0


class TestEarningsRisk:

    def test_earnings_tomorrow_exit(self, tracker):
        tracker.add_position(_make_pos("AAPL"))
        tomorrow = date(2026, 4, 2).isoformat()
        decisions = run_swing_management(
            tracker, {"AAPL": 152.0},
            earnings_dates={"AAPL": tomorrow},
            today=date(2026, 4, 1),
        )

        moc = [d for d in decisions if d.action == SwingAction.MOC_EXIT and d.reason == "earnings_risk"]
        assert len(moc) == 1

    def test_no_earnings_no_exit(self, tracker):
        tracker.add_position(_make_pos("AAPL"))
        decisions = run_swing_management(tracker, {"AAPL": 152.0})

        moc = [d for d in decisions if d.reason == "earnings_risk"]
        assert len(moc) == 0

    def test_earnings_far_away_no_exit(self, tracker):
        tracker.add_position(_make_pos("AAPL"))
        decisions = run_swing_management(
            tracker, {"AAPL": 152.0},
            earnings_dates={"AAPL": "2026-12-31"},
            today=date(2026, 4, 1),
        )

        moc = [d for d in decisions if d.reason == "earnings_risk"]
        assert len(moc) == 0


class TestMultiplePositions:

    def test_mixed_actions(self, tracker):
        """Multiple positions, different actions."""
        tracker.add_position(_make_pos("EXPIRED", hold_days=4))
        tracker.add_position(_make_pos("FRESH", hold_days=0))
        tracker.add_position(_make_pos("TRAILING", tp1_triggered=True, remaining_qty=50))

        decisions = run_swing_management(
            tracker,
            {"EXPIRED": 150.0, "FRESH": 150.5, "TRAILING": 155.0},
        )

        # EXPIRED: max_hold
        assert any(d.ticker == "EXPIRED" and d.action == SwingAction.MOC_EXIT for d in decisions)
        # TRAILING: activate trail
        assert any(d.ticker == "TRAILING" and d.action == SwingAction.ACTIVATE_TRAIL for d in decisions)
