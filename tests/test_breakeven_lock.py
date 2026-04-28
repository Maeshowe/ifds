"""Regression tests for the 19:00 CEST Breakeven Lock (B bracket soft floor).

The breakeven lock is a risk-control mechanism that fires once per day in
the 19:00:00–19:04:59 CEST window on positions whose B bracket trail is
already active. It applies a *soft floor* on the trail SL:

    - price > entry      → floor = entry             (profit_breakeven)
    - price <= entry     → floor = entry × 0.99      (loss_capped_minus_1pct)
    - effective_sl       = max(trail_sl, floor)      (never lowers the trail)

Mathematical guarantee: ``max(x, y) >= x`` ⇒ the lock never produces a worse
SL than the existing trail mechanism. The change is strictly risk-reducing.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

CET = ZoneInfo("Europe/Budapest")


# ---------------------------------------------------------------------------
# compute_breakeven_lock — pure logic
# ---------------------------------------------------------------------------


class TestComputeBreakevenLock:

    def test_profit_above_entry_uses_entry_as_floor(self) -> None:
        """Position in profit at 19:00 → floor at entry, lock_type=profit_breakeven."""
        from scripts.paper_trading.pt_monitor import compute_breakeven_lock

        entry = 105.59
        current = 106.04  # +0.43% profit
        trail_sl = 102.03  # -3.4% below entry (POST 2026-04-27 case)

        new_sl, lock_type = compute_breakeven_lock(entry, current, trail_sl)

        assert new_sl == pytest.approx(105.59, abs=1e-4)
        assert lock_type == "profit_breakeven"

    def test_loss_below_entry_caps_at_minus_1pct(self) -> None:
        """Position below entry at 19:00 → floor at entry × 0.99."""
        from scripts.paper_trading.pt_monitor import compute_breakeven_lock

        entry = 100.0
        current = 99.50  # -0.5% below entry, between LOSS_EXIT and breakeven
        trail_sl = 95.0  # well below floor

        new_sl, lock_type = compute_breakeven_lock(entry, current, trail_sl)

        assert new_sl == pytest.approx(99.0, abs=1e-4)
        assert lock_type == "loss_capped_minus_1pct"

    def test_at_entry_treats_as_loss_path(self) -> None:
        """current == entry → loss_capped path (price > entry is strict)."""
        from scripts.paper_trading.pt_monitor import compute_breakeven_lock

        new_sl, lock_type = compute_breakeven_lock(100.0, 100.0, 90.0)

        assert lock_type == "loss_capped_minus_1pct"
        assert new_sl == pytest.approx(99.0, abs=1e-4)

    def test_soft_floor_does_not_lower_existing_trail(self) -> None:
        """If trail is already above the floor, the trail wins (max())."""
        from scripts.paper_trading.pt_monitor import compute_breakeven_lock

        entry = 100.0
        current = 110.0  # +10% — trail well above entry
        trail_sl = 107.5  # already above entry → floor would lower it

        new_sl, lock_type = compute_breakeven_lock(entry, current, trail_sl)

        # max(107.5, 100.0) = 107.5 — trail unchanged
        assert new_sl == pytest.approx(107.5, abs=1e-4)
        assert lock_type == "profit_breakeven"

    def test_loss_floor_does_not_lower_existing_trail(self) -> None:
        """Loss path: if trail somehow above floor, trail still wins."""
        from scripts.paper_trading.pt_monitor import compute_breakeven_lock

        entry = 100.0
        current = 99.50
        trail_sl = 99.20  # tighter than the -1% floor

        new_sl, _ = compute_breakeven_lock(entry, current, trail_sl)

        # max(99.20, 99.0) = 99.20
        assert new_sl == pytest.approx(99.20, abs=1e-4)

    def test_post_case_retroactive_savings(self) -> None:
        """Retro-calc on POST 2026-04-27: SL would have been entry instead of MOC drift."""
        from scripts.paper_trading.pt_monitor import compute_breakeven_lock

        # POST 2026-04-27 19:00 CEST snapshot
        entry = 105.59
        current = 106.04
        trail_sl = 102.03

        new_sl, lock_type = compute_breakeven_lock(entry, current, trail_sl)

        # Stop would have been at $105.59 instead of MOC $103.87 → ~$1.72/share saving
        assert new_sl == pytest.approx(105.59, abs=1e-4)
        assert lock_type == "profit_breakeven"
        # Confirm the saving is positive: new_sl > MOC fill of $103.87
        assert new_sl > 103.87


# ---------------------------------------------------------------------------
# is_breakeven_lock_window — time gate
# ---------------------------------------------------------------------------


class TestBreakevenLockWindow:

    def test_19_00_inside_window(self) -> None:
        from scripts.paper_trading.pt_monitor import is_breakeven_lock_window

        t = datetime(2026, 4, 28, 19, 0, 0, tzinfo=CET)
        assert is_breakeven_lock_window(t) is True

    def test_19_04_inside_window(self) -> None:
        """Last second of window — 19:04:59."""
        from scripts.paper_trading.pt_monitor import is_breakeven_lock_window

        t = datetime(2026, 4, 28, 19, 4, 59, tzinfo=CET)
        assert is_breakeven_lock_window(t) is True

    def test_18_55_before_window(self) -> None:
        from scripts.paper_trading.pt_monitor import is_breakeven_lock_window

        t = datetime(2026, 4, 28, 18, 55, 0, tzinfo=CET)
        assert is_breakeven_lock_window(t) is False

    def test_19_05_after_window(self) -> None:
        """19:05 is just outside — next cron tick won't re-trigger."""
        from scripts.paper_trading.pt_monitor import is_breakeven_lock_window

        t = datetime(2026, 4, 28, 19, 5, 0, tzinfo=CET)
        assert is_breakeven_lock_window(t) is False

    def test_19_10_after_window(self) -> None:
        from scripts.paper_trading.pt_monitor import is_breakeven_lock_window

        t = datetime(2026, 4, 28, 19, 10, 0, tzinfo=CET)
        assert is_breakeven_lock_window(t) is False

    def test_other_hours_outside(self) -> None:
        from scripts.paper_trading.pt_monitor import is_breakeven_lock_window

        for hour in (0, 8, 16, 18, 20, 22):
            t = datetime(2026, 4, 28, hour, 2, 0, tzinfo=CET)
            assert is_breakeven_lock_window(t) is False, (
                f"hour {hour} should NOT be in the window"
            )


# ---------------------------------------------------------------------------
# Mathematical guarantee — exhaustive on a small grid
# ---------------------------------------------------------------------------


class TestMathematicalGuarantee:
    """``compute_breakeven_lock(...) >= trail_sl`` for all inputs.

    This is the core risk-reducing claim of the design: the lock can never
    produce an SL looser than the existing trail.
    """

    @pytest.mark.parametrize("entry", [50.0, 100.0, 500.0])
    @pytest.mark.parametrize(
        "current_offset_pct",
        [-0.10, -0.05, -0.01, 0.0, 0.005, 0.05, 0.20],
    )
    @pytest.mark.parametrize(
        "trail_offset_pct",
        [-0.10, -0.03, -0.01, 0.0, 0.05, 0.15],
    )
    def test_new_sl_never_below_trail(
        self,
        entry: float,
        current_offset_pct: float,
        trail_offset_pct: float,
    ) -> None:
        from scripts.paper_trading.pt_monitor import compute_breakeven_lock

        current = entry * (1 + current_offset_pct)
        trail_sl = entry * (1 + trail_offset_pct)
        new_sl, _ = compute_breakeven_lock(entry, current, trail_sl)

        # Allow a tiny rounding tolerance from the round(_, 4) inside.
        assert new_sl >= trail_sl - 1e-4, (
            f"breakeven lock loosened the SL: "
            f"entry={entry}, current={current}, trail={trail_sl}, new={new_sl}"
        )
