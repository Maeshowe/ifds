"""Tests for Correlation Guard — sector group limits (BC21 Phase_21A).

Tests the _apply_position_limits integration with sector groups.
"""

from unittest.mock import MagicMock

import pytest

from ifds.models.market import PositionSizing


def _make_position(ticker: str, sector: str, score: float = 80.0) -> PositionSizing:
    return PositionSizing(
        ticker=ticker,
        sector=sector,
        direction="BUY",
        entry_price=100.0,
        quantity=10,
        stop_loss=95.0,
        take_profit_1=103.0,
        take_profit_2=106.0,
        risk_usd=50.0,
        combined_score=score,
        gex_regime="neutral",
        multiplier_total=1.0,
    )


@pytest.fixture()
def mock_config():
    """Config with correlation guard enabled."""
    config = MagicMock()
    config.runtime = {
        "max_positions": 20,
        "max_single_position_risk_pct": 5.0,
        "max_gross_exposure": 1_000_000,
        "max_single_ticker_exposure": 50_000,
        "account_equity": 100_000,
    }
    config.tuning = {
        "max_positions_per_sector": 3,
        "correlation_guard_enabled": True,
        "sector_group_max_cyclical": 5,
        "sector_group_max_defensive": 4,
        "sector_group_max_financial": 3,
        "sector_group_max_commodity": 3,
    }
    return config


@pytest.fixture()
def mock_logger():
    return MagicMock()


class TestCorrelationGuard:

    def test_6_cyclical_5_accepted(self, mock_config, mock_logger):
        """6 cyclical positions → 5 accepted, 1 filtered."""
        from ifds.phases.phase6_sizing import _apply_position_limits

        positions = [
            _make_position("AAPL", "Technology", 90),
            _make_position("MSFT", "Technology", 88),
            _make_position("AMZN", "Consumer Cyclical", 86),
            _make_position("CAT", "Industrials", 84),
            _make_position("NUE", "Basic Materials", 82),
            _make_position("SHOP", "Technology", 80),  # 6th cyclical → blocked
        ]
        accepted, counts = _apply_position_limits(positions, mock_config, mock_logger)

        assert len(accepted) == 5
        assert counts["correlation"] == 1

    def test_mixed_groups_all_pass(self, mock_config, mock_logger):
        """3 defensive + 2 financial → all pass (different groups)."""
        from ifds.phases.phase6_sizing import _apply_position_limits

        positions = [
            _make_position("JNJ", "Healthcare", 90),
            _make_position("PG", "Consumer Defensive", 88),
            _make_position("NEE", "Utilities", 86),
            _make_position("JPM", "Financial Services", 84),
            _make_position("AMT", "Real Estate", 82),
        ]
        accepted, counts = _apply_position_limits(positions, mock_config, mock_logger)

        assert len(accepted) == 5
        assert counts["correlation"] == 0

    def test_commodity_limit_3(self, mock_config, mock_logger):
        """4 commodity positions → 3 accepted."""
        from ifds.phases.phase6_sizing import _apply_position_limits

        positions = [
            _make_position("XOM", "Energy", 90),
            _make_position("CVX", "Energy", 88),
            _make_position("NUE", "Basic Materials", 86),  # Also in cyclical group
            _make_position("SLB", "Energy", 84),  # 4th commodity → blocked
        ]
        accepted, counts = _apply_position_limits(positions, mock_config, mock_logger)

        assert len(accepted) == 3
        assert counts["correlation"] == 1

    def test_disabled_no_filtering(self, mock_config, mock_logger):
        """correlation_guard_enabled=False → no correlation filtering."""
        from ifds.phases.phase6_sizing import _apply_position_limits

        mock_config.tuning["correlation_guard_enabled"] = False
        positions = [_make_position(f"T{i}", "Technology", 90 - i) for i in range(8)]
        accepted, counts = _apply_position_limits(positions, mock_config, mock_logger)

        # Only limited by max_positions_per_sector (3)
        assert counts["correlation"] == 0

    def test_empty_positions(self, mock_config, mock_logger):
        from ifds.phases.phase6_sizing import _apply_position_limits

        accepted, counts = _apply_position_limits([], mock_config, mock_logger)
        assert len(accepted) == 0

    def test_basic_materials_in_both_groups(self, mock_config, mock_logger):
        """Basic Materials is in BOTH cyclical AND commodity groups."""
        from ifds.phases.phase6_sizing import _apply_position_limits

        mock_config.tuning["sector_group_max_commodity"] = 2
        positions = [
            _make_position("XOM", "Energy", 90),
            _make_position("CVX", "Energy", 88),
            _make_position("NUE", "Basic Materials", 86),  # 3rd commodity → blocked
        ]
        accepted, counts = _apply_position_limits(positions, mock_config, mock_logger)

        assert len(accepted) == 2
        assert counts["correlation"] == 1
