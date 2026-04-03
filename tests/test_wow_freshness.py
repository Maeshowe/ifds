"""Tests for WOW Signals freshness scoring (BC20B).

Covers:
- count_appearances with lookback window
- days_since_last_appearance
- wow_multiplier decision tree (New Kid, WOW, Stale, Persistent, Neutral)
- Edge cases (empty history, None dates)
"""

from datetime import date

import pytest

from ifds.sim.wow_freshness import (
    count_appearances,
    days_since_last_appearance,
    wow_multiplier,
)


def _history(entries: list[tuple[str, str]]) -> list[dict]:
    """Build signal history from (date, ticker) tuples."""
    return [{"date": d, "ticker": t} for d, t in entries]


REF = date(2026, 4, 1)


class TestCountAppearances:

    def test_empty_history(self):
        assert count_appearances("AAPL", [], reference_date=REF) == 0

    def test_within_lookback(self):
        h = _history([
            ("2026-03-01", "AAPL"),
            ("2026-03-15", "AAPL"),
            ("2026-02-01", "AAPL"),  # Within 90d from Apr 1
        ])
        assert count_appearances("AAPL", h, lookback_days=90, reference_date=REF) == 3

    def test_outside_lookback(self):
        h = _history([("2025-12-01", "AAPL")])  # ~4 months before REF
        assert count_appearances("AAPL", h, lookback_days=90, reference_date=REF) == 0

    def test_other_ticker_not_counted(self):
        h = _history([("2026-03-15", "MSFT")])
        assert count_appearances("AAPL", h, reference_date=REF) == 0


class TestDaysSinceLastAppearance:

    def test_never_appeared(self):
        assert days_since_last_appearance("AAPL", [], reference_date=REF) is None

    def test_appeared_recently(self):
        h = _history([("2026-03-30", "AAPL")])
        assert days_since_last_appearance("AAPL", h, reference_date=REF) == 2

    def test_most_recent_used(self):
        h = _history([
            ("2026-03-01", "AAPL"),
            ("2026-03-28", "AAPL"),
        ])
        assert days_since_last_appearance("AAPL", h, reference_date=REF) == 4


class TestWowMultiplier:

    def test_new_kid(self):
        """0 appearances → 1.15."""
        assert wow_multiplier("AAPL", [], reference_date=REF) == 1.15

    def test_wow_recurring_winner(self):
        """3+ appearances, last ≤5 days → 1.10."""
        h = _history([
            ("2026-03-28", "AAPL"),
            ("2026-03-29", "AAPL"),
            ("2026-03-30", "AAPL"),
        ])
        assert wow_multiplier("AAPL", h, reference_date=REF) == 1.10

    def test_stale_returning(self):
        """1+ appearances, last >30 days → 0.80."""
        h = _history([("2026-02-15", "AAPL")])  # 45 days before REF
        assert wow_multiplier("AAPL", h, reference_date=REF) == 0.80

    def test_persistent(self):
        """5+ appearances (but last >5 days) → 1.05."""
        h = _history([
            ("2026-03-10", "AAPL"),
            ("2026-03-12", "AAPL"),
            ("2026-03-14", "AAPL"),
            ("2026-03-16", "AAPL"),
            ("2026-03-18", "AAPL"),
        ])
        # 5 appearances, last = Mar 18 → 14 days ago (>5)
        assert wow_multiplier("AAPL", h, reference_date=REF) == 1.05

    def test_neutral(self):
        """1-2 appearances, recent (≤30 days), not WOW → 1.00."""
        h = _history([("2026-03-25", "AAPL")])  # 1 appearance, 7 days ago
        assert wow_multiplier("AAPL", h, reference_date=REF) == 1.00

    def test_wow_beats_persistent(self):
        """WOW condition (3+ recent) takes priority over Persistent (5+)."""
        h = _history([
            ("2026-03-20", "AAPL"),
            ("2026-03-25", "AAPL"),
            ("2026-03-28", "AAPL"),
            ("2026-03-29", "AAPL"),
            ("2026-03-31", "AAPL"),
        ])
        # 5 appearances, last=1 day ago → WOW wins (3+ and ≤5 days)
        assert wow_multiplier("AAPL", h, reference_date=REF) == 1.10
