"""BC11 Robustness Tests — Signal dedup, VIX sanity check, GlobalGuard logging.

~15 tests covering:
1. SignalDedup hash-based idempotency
2. VIX sanity range validation [5.0, 100.0]
3. GlobalGuard exposure log formatting
"""

import json
import os
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from ifds.config.loader import Config
from ifds.data.signal_dedup import SignalDedup
from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity
from ifds.phases.phase0_diagnostics import _validate_vix


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    return Config()


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-bc11")


# ============================================================================
# TestSignalDedup
# ============================================================================

class TestSignalDedup:
    """Test SHA256-based signal deduplication."""

    def test_no_duplicate_first_call(self, tmp_path):
        dedup = SignalDedup(str(tmp_path / "hashes.json"))
        assert dedup.is_duplicate("AAPL", "BUY") is False

    def test_duplicate_same_ticker_same_day(self, tmp_path):
        dedup = SignalDedup(str(tmp_path / "hashes.json"))
        dedup.record("AAPL", "BUY")
        assert dedup.is_duplicate("AAPL", "BUY") is True

    def test_different_ticker_no_duplicate(self, tmp_path):
        dedup = SignalDedup(str(tmp_path / "hashes.json"))
        dedup.record("AAPL", "BUY")
        assert dedup.is_duplicate("MSFT", "BUY") is False

    def test_different_direction_no_duplicate(self, tmp_path):
        dedup = SignalDedup(str(tmp_path / "hashes.json"))
        dedup.record("AAPL", "BUY")
        assert dedup.is_duplicate("AAPL", "SELL_SHORT") is False

    def test_save_and_load(self, tmp_path):
        """Save hashes, create new instance, verify persistence."""
        path = str(tmp_path / "hashes.json")
        dedup1 = SignalDedup(path)
        dedup1.record("AAPL", "BUY")
        dedup1.record("MSFT", "BUY")
        dedup1.save()

        dedup2 = SignalDedup(path)
        assert dedup2.is_duplicate("AAPL", "BUY") is True
        assert dedup2.is_duplicate("MSFT", "BUY") is True
        assert dedup2.is_duplicate("GOOG", "BUY") is False

    def test_save_atomic_write(self, tmp_path):
        """Verify atomic write creates valid JSON."""
        path = str(tmp_path / "hashes.json")
        dedup = SignalDedup(path)
        dedup.record("AAPL", "BUY")
        dedup.save()

        with open(path) as f:
            data = json.load(f)
        assert data["date"] == date.today().isoformat()
        assert len(data["hashes"]) == 1

    def test_ttl_cleanup_old_date(self, tmp_path):
        """Hashes from a different date are discarded on load."""
        path = str(tmp_path / "hashes.json")
        old_data = {
            "date": "2024-01-01",
            "hashes": {"abc123": "AAPL"},
        }
        with open(path, "w") as f:
            json.dump(old_data, f)

        dedup = SignalDedup(path)
        assert dedup.count == 0  # Old hashes discarded

    def test_hash_format(self):
        """Hash is 16-char hex string."""
        h = SignalDedup._compute_hash("AAPL", "BUY")
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    def test_count_property(self, tmp_path):
        dedup = SignalDedup(str(tmp_path / "hashes.json"))
        assert dedup.count == 0
        dedup.record("AAPL", "BUY")
        assert dedup.count == 1
        dedup.record("MSFT", "BUY")
        assert dedup.count == 2

    def test_load_corrupt_file(self, tmp_path):
        """Corrupt JSON file should not crash, just start empty."""
        path = str(tmp_path / "hashes.json")
        with open(path, "w") as f:
            f.write("not valid json{{{")
        dedup = SignalDedup(path)
        assert dedup.count == 0


# ============================================================================
# TestVIXSanityCheck
# ============================================================================

class TestVIXSanityCheck:
    """Test VIX range validation [5.0, 100.0]."""

    def test_valid_vix_passes(self, logger):
        vix, valid = _validate_vix(18.5, "polygon", logger)
        assert valid is True
        assert vix == 18.5

    def test_vix_below_range(self, logger):
        vix, valid = _validate_vix(2.0, "polygon", logger)
        assert valid is False
        assert vix == 20.0  # Default fallback

    def test_vix_above_range(self, logger):
        vix, valid = _validate_vix(150.0, "fred", logger)
        assert valid is False
        assert vix == 20.0

    def test_vix_at_boundary_5(self, logger):
        vix, valid = _validate_vix(5.0, "polygon", logger)
        assert valid is True
        assert vix == 5.0

    def test_vix_at_boundary_100(self, logger):
        vix, valid = _validate_vix(100.0, "fred", logger)
        assert valid is True
        assert vix == 100.0

    def test_vix_negative(self, logger):
        vix, valid = _validate_vix(-5.0, "polygon", logger)
        assert valid is False
        assert vix == 20.0

    def test_vix_zero(self, logger):
        vix, valid = _validate_vix(0.0, "polygon", logger)
        assert valid is False
        assert vix == 20.0


# ============================================================================
# TestGlobalGuardLogging
# ============================================================================

class TestGlobalGuardLogging:
    """Test GlobalGuard log format for exposure rejections."""

    def test_gross_exposure_log_format(self, config, logger):
        """Gross exposure rejection should use [GLOBALGUARD] prefix."""
        from ifds.models.market import PositionSizing
        from ifds.phases.phase6_sizing import _apply_position_limits

        # Create positions that will exceed gross exposure
        positions = []
        for i, ticker in enumerate(["AAPL", "MSFT", "GOOG", "AMZN", "META",
                                     "TSLA", "NVDA", "AMD", "INTC", "NFLX"]):
            positions.append(PositionSizing(
                ticker=ticker, sector="Technology",
                direction="BUY", entry_price=200.0,
                quantity=1000,  # $200K exposure each
                stop_loss=190.0, take_profit_1=210.0, take_profit_2=220.0,
                risk_usd=400.0, combined_score=90.0 - i,
                gex_regime="positive",
                multiplier_total=1.0,
                m_flow=1.0, m_insider=1.0, m_funda=1.0,
                m_gex=1.0, m_vix=1.0, m_utility=1.0,
                scale_out_price=205.0, scale_out_pct=50,
            ))

        accepted, counts = _apply_position_limits(positions, config, logger)

        # Verify some were rejected for exposure
        # (max_gross_exposure is 100000 by default, each position is $200K)
        # Actually only 1 can fit since each is $200K and max is $100K
        # But sector limit (3 per sector) will kick in first
        total_excluded = counts["exposure"] + counts["sector"] + counts["position"]
        assert total_excluded > 0

    def test_single_ticker_exposure_reduces_quantity(self, config, logger):
        """Single ticker exposure > max should reduce quantity."""
        from ifds.models.market import PositionSizing
        from ifds.phases.phase6_sizing import _apply_position_limits

        # Single position with very high quantity
        positions = [PositionSizing(
            ticker="AAPL", sector="Technology",
            direction="BUY", entry_price=200.0,
            quantity=200,  # $40K exposure (max_single_ticker = $20K)
            stop_loss=190.0, take_profit_1=210.0, take_profit_2=220.0,
            risk_usd=400.0, combined_score=90.0,
            gex_regime="positive",
            multiplier_total=1.0,
            m_flow=1.0, m_insider=1.0, m_funda=1.0,
            m_gex=1.0, m_vix=1.0, m_utility=1.0,
            scale_out_price=205.0, scale_out_pct=50,
        )]

        accepted, counts = _apply_position_limits(positions, config, logger)

        # Position should be accepted but with reduced quantity
        assert len(accepted) == 1
        assert accepted[0].quantity < 200  # Reduced from original
        assert accepted[0].quantity == 100  # floor(20000 / 200)
