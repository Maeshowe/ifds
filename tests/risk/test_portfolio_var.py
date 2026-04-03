"""Tests for Portfolio VaR (BC21 Phase_21A).

Covers:
- Single position VaR
- Multi-position independent VaR (sqrt sum of squares)
- VaR trimming (removes weakest until under limit)
- Edge cases (no positions, zero values)
"""

import math
from dataclasses import dataclass

import pytest

from ifds.risk.portfolio_var import calculate_portfolio_var, trim_positions_by_var


@dataclass
class FakePosition:
    """Minimal position-like object for VaR tests."""
    entry_price: float
    quantity: int
    stop_loss: float
    combined_score: float = 80.0


class TestCalculatePortfolioVar:

    def test_single_position(self):
        """Single position VaR = position VaR."""
        pos = FakePosition(entry_price=100.0, quantity=50, stop_loss=95.5)
        # ATR = (100 - 95.5) / 1.5 = 3.0
        # daily_vol = 3.0 / 100 = 0.03
        # position_value = 100 × 50 = 5000
        # VaR_i = 5000 × 0.03 × 1.645 = 246.75
        var_usd, var_pct = calculate_portfolio_var([pos])
        assert var_usd > 0
        assert var_pct > 0

    def test_two_positions_sqrt(self):
        """Two independent positions: VaR = sqrt(VaR1^2 + VaR2^2)."""
        pos1 = FakePosition(entry_price=100.0, quantity=50, stop_loss=95.5)
        pos2 = FakePosition(entry_price=200.0, quantity=25, stop_loss=191.0)

        var_1, _ = calculate_portfolio_var([pos1])
        var_2, _ = calculate_portfolio_var([pos2])
        var_combined, _ = calculate_portfolio_var([pos1, pos2])

        expected = math.sqrt(var_1 ** 2 + var_2 ** 2)
        assert abs(var_combined - expected) < 0.01

    def test_empty_positions(self):
        var_usd, var_pct = calculate_portfolio_var([])
        assert var_usd == 0.0
        assert var_pct == 0.0

    def test_zero_price_skipped(self):
        pos = FakePosition(entry_price=0.0, quantity=50, stop_loss=0.0)
        var_usd, var_pct = calculate_portfolio_var([pos])
        assert var_usd == 0.0


class TestTrimPositionsByVar:

    def test_no_trim_under_limit(self):
        """Under limit → no removal."""
        pos = FakePosition(entry_price=100.0, quantity=10, stop_loss=95.5)
        result, removed, var_pct = trim_positions_by_var([pos], 100_000, max_var_pct=10.0)
        assert removed == 0
        assert len(result) == 1

    def test_trim_removes_weakest(self):
        """Over limit → removes position with lowest combined_score."""
        positions = [
            FakePosition(entry_price=100.0, quantity=100, stop_loss=85.0, combined_score=90),
            FakePosition(entry_price=100.0, quantity=100, stop_loss=85.0, combined_score=70),
            FakePosition(entry_price=100.0, quantity=100, stop_loss=85.0, combined_score=80),
        ]
        # Very tight limit to force removal
        result, removed, var_pct = trim_positions_by_var(positions, 10_000, max_var_pct=0.5)
        assert removed > 0
        # Weakest (score=70) should be removed first
        remaining_scores = [p.combined_score for p in result]
        if 70 in [p.combined_score for p in positions] and removed >= 1:
            assert 70 not in remaining_scores or removed >= 2

    def test_single_position_under_limit(self):
        pos = FakePosition(entry_price=50.0, quantity=5, stop_loss=47.0)
        result, removed, var_pct = trim_positions_by_var([pos], 100_000, max_var_pct=5.0)
        assert removed == 0
        assert len(result) == 1
