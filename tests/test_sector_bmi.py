"""BC8: Per-Sector BMI + MAP-IT Activation tests.

Tests for:
- FMP sector mapping (get_sector_mapping)
- FMP_SECTOR_TO_ETF mapping constant
- Per-sector daily ratio tracking
- Sector BMI calculation (_calculate_sector_bmi)
- Phase 1 integration (sector_bmi_values in result)
- Phase 3 integration (sector BMI populates SectorScore)
- Veto matrix activation with real BMI values
"""

from unittest.mock import MagicMock, patch

import pytest

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import (
    BMIData,
    BMIRegime,
    MacroRegime,
    MarketVolatilityRegime,
    MomentumClassification,
    Phase1Result,
    Phase3Result,
    SectorBMIRegime,
    SectorScore,
    SectorTrend,
    StrategyMode,
)
from ifds.phases.phase1_regime import (
    FMP_SECTOR_TO_ETF,
    _calculate_daily_ratios,
    _calculate_sector_bmi,
    run_phase1,
)
from ifds.phases.phase3_sectors import (
    SECTOR_ETFS,
    _apply_sector_bmi,
    _apply_veto_matrix,
    run_phase3,
)


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
    return EventLogger(log_dir=str(tmp_path), run_id="test-sector-bmi")


# ============================================================================
# Helpers
# ============================================================================

def _make_bar(ticker, open_price, close, volume):
    return {"T": ticker, "o": open_price, "c": close, "v": volume,
            "h": close + 1, "l": open_price - 1}


def _make_daily_data(days_count, tickers_per_day=50, base_volume=1000):
    """Create mock grouped daily data."""
    daily_data = []
    for day_idx in range(days_count):
        bars = []
        for t in range(tickers_per_day):
            ticker = f"T{t:03d}"
            bars.append(_make_bar(ticker, 100.0, 100.0, base_volume))
        daily_data.append({"date": f"2026-01-{day_idx + 1:02d}", "bars": bars})
    return daily_data


def _make_daily_data_with_spikes(days_count, sector_mapping, spike_tickers,
                                  spike_direction="buy"):
    """Create daily data where specific tickers have volume spikes.

    spike_tickers: list of ticker names that will spike every day
    spike_direction: "buy" (close > open) or "sell" (close < open)
    All other tickers have flat volume at 1000 (no spikes possible).

    Volume spike = 1_000_000 (1000x base) to ensure detection even with
    rolling stats that include prior spike days in the 20-day window.
    """
    daily_data = []
    all_tickers = list(set(list(sector_mapping.keys()) + spike_tickers))

    for day_idx in range(days_count):
        bars = []
        for ticker in all_tickers:
            if day_idx >= 20 and ticker in spike_tickers:
                vol = 1_000_000  # 1000x base → always > mean + 2*sigma
                open_p = 100.0
                close_p = 105.0 if spike_direction == "buy" else 95.0
            else:
                vol = 1000
                open_p = 100.0
                close_p = 100.0  # Flat — no signal
            bars.append(_make_bar(ticker, open_p, close_p, vol))
        daily_data.append({"date": f"2026-01-{day_idx + 1:02d}", "bars": bars})
    return daily_data


# ============================================================================
# FMP Sector Mapping Tests
# ============================================================================

class TestFMPSectorMapping:
    def test_get_sector_mapping_returns_dict(self):
        """get_sector_mapping() should return {ticker: sector}."""
        from ifds.data.fmp import FMPClient

        client = FMPClient(api_key="test")
        mock_screener_result = [
            {"symbol": "AAPL", "sector": "Technology"},
            {"symbol": "JPM", "sector": "Financial Services"},
            {"symbol": "XOM", "sector": "Energy"},
            {"symbol": "NOSECTOR"},  # Missing sector — should be skipped
        ]
        with patch.object(client, "screener", return_value=mock_screener_result):
            mapping = client.get_sector_mapping()

        assert mapping == {
            "AAPL": "Technology",
            "JPM": "Financial Services",
            "XOM": "Energy",
        }
        client.close()

    def test_get_sector_mapping_cached(self):
        """Cached result should skip API call."""
        from ifds.data.fmp import FMPClient

        cache = MagicMock()
        cache.get.return_value = {"AAPL": "Technology"}
        client = FMPClient(api_key="test", cache=cache)
        with patch.object(client, "screener") as mock_screener:
            mapping = client.get_sector_mapping()

        assert mapping == {"AAPL": "Technology"}
        mock_screener.assert_not_called()
        client.close()

    def test_get_sector_mapping_empty(self):
        """Screener returning None → empty dict."""
        from ifds.data.fmp import FMPClient

        client = FMPClient(api_key="test")
        with patch.object(client, "screener", return_value=None):
            mapping = client.get_sector_mapping()

        assert mapping == {}
        client.close()


# ============================================================================
# FMP_SECTOR_TO_ETF Mapping Tests
# ============================================================================

class TestFMPSectorToETF:
    def test_covers_all_sector_etfs(self):
        """FMP_SECTOR_TO_ETF values should cover all 11 SECTOR_ETFS."""
        etf_values = set(FMP_SECTOR_TO_ETF.values())
        sector_etfs = set(SECTOR_ETFS.keys())
        assert etf_values == sector_etfs

    def test_financial_services_maps_to_xlf(self):
        """FMP uses 'Financial Services', Phase 3 uses 'Financials' (XLF)."""
        assert FMP_SECTOR_TO_ETF["Financial Services"] == "XLF"


# ============================================================================
# Per-Sector Daily Ratios Tests
# ============================================================================

class TestDailyRatiosWithSectors:
    def test_daily_ratios_with_sector_mapping(self, config):
        """Sector buy/sell counts should be recorded on day dicts."""
        sector_mapping = {"T000": "Technology", "T001": "Technology",
                          "T002": "Energy"}
        daily = _make_daily_data_with_spikes(
            30, sector_mapping, ["T000", "T001"], spike_direction="buy")

        ratios = _calculate_daily_ratios(daily, config,
                                          sector_mapping=sector_mapping)

        # Check day 20 — the FIRST spike day. After that, persistent spikes
        # inflate the rolling sigma and are no longer detected as anomalies.
        day_20 = daily[20]
        assert "_sector_buys" in day_20
        assert "_sector_sells" in day_20
        # T000 and T001 mapped to Technology → should have buy signals
        assert day_20["_sector_buys"].get("XLK", 0) >= 1

    def test_daily_ratios_without_sector_mapping(self, config):
        """Without sector_mapping, sector data should be empty dicts."""
        daily = _make_daily_data(30)
        _calculate_daily_ratios(daily, config, sector_mapping=None)

        day_25 = daily[25]
        assert day_25.get("_sector_buys") == {}
        assert day_25.get("_sector_sells") == {}

    def test_unmapped_tickers_ignored(self, config):
        """Tickers not in sector_mapping should not appear in sector data."""
        # Only map T000, leave T001-T049 unmapped
        sector_mapping = {"T000": "Technology"}
        daily = _make_daily_data_with_spikes(
            30, sector_mapping, ["T000", "T001"], spike_direction="buy")

        _calculate_daily_ratios(daily, config, sector_mapping=sector_mapping)

        day_25 = daily[25]
        # T001 spikes but is unmapped → should NOT appear in sector data
        all_etfs = set(day_25["_sector_buys"].keys()) | set(day_25["_sector_sells"].keys())
        # Only XLK (Technology) should appear
        for etf in all_etfs:
            assert etf == "XLK"


# ============================================================================
# Sector BMI Calculation Tests
# ============================================================================

class TestCalculateSectorBMI:
    def test_basic_sector_bmi(self, config):
        """25+ days with sector data → valid BMI computed."""
        # Build 30 days with sector buy/sell data
        daily_data = []
        for i in range(30):
            daily_data.append({
                "date": f"2026-01-{i + 1:02d}",
                "_sector_buys": {"XLK": 10, "XLE": 8},
                "_sector_sells": {"XLK": 5, "XLE": 12},
            })

        result = _calculate_sector_bmi(daily_data, config)

        assert "XLK" in result
        assert "XLE" in result
        # XLK: B=10, S=5, ratio = 10/15*100 = 66.67% every day → BMI ≈ 66.67
        assert result["XLK"] == pytest.approx(66.67, abs=0.1)
        # XLE: B=8, S=12, ratio = 8/20*100 = 40.0% every day → BMI ≈ 40.0
        assert result["XLE"] == pytest.approx(40.0, abs=0.1)

    def test_insufficient_days(self, config):
        """< 25 days → sector not in result."""
        daily_data = []
        for i in range(20):  # Only 20 days, need 25
            daily_data.append({
                "date": f"2026-01-{i + 1:02d}",
                "_sector_buys": {"XLK": 10},
                "_sector_sells": {"XLK": 5},
            })

        result = _calculate_sector_bmi(daily_data, config)
        assert "XLK" not in result

    def test_low_signal_days_use_neutral(self, config):
        """Days with < min_signals (5) should use 50.0 neutral ratio."""
        daily_data = []
        for i in range(30):
            daily_data.append({
                "date": f"2026-01-{i + 1:02d}",
                # Only 3 total signals (< 5 min) → should default to 50.0
                "_sector_buys": {"XLK": 2},
                "_sector_sells": {"XLK": 1},
            })

        result = _calculate_sector_bmi(daily_data, config)

        assert "XLK" in result
        # All days use neutral 50.0 → BMI = 50.0
        assert result["XLK"] == pytest.approx(50.0, abs=0.1)

    def test_multiple_sectors_independent(self, config):
        """Multiple sectors computed independently."""
        daily_data = []
        for i in range(30):
            daily_data.append({
                "date": f"2026-01-{i + 1:02d}",
                "_sector_buys": {"XLK": 15, "XLE": 3, "XLF": 10},
                "_sector_sells": {"XLK": 5, "XLE": 17, "XLF": 10},
            })

        result = _calculate_sector_bmi(daily_data, config)

        assert len(result) == 3
        # XLK: 15/20 = 75%, XLE: 3/20 = 15%, XLF: 10/20 = 50%
        assert result["XLK"] == pytest.approx(75.0, abs=0.1)
        assert result["XLE"] == pytest.approx(15.0, abs=0.1)
        assert result["XLF"] == pytest.approx(50.0, abs=0.1)


# ============================================================================
# Phase 1 Integration Tests
# ============================================================================

class TestPhase1SectorBMI:
    @patch("ifds.phases.phase1_regime._calculate_sector_bmi")
    @patch("ifds.phases.phase1_regime._fetch_daily_history")
    def test_with_sector_mapping(self, mock_fetch, mock_sector_bmi,
                                  config, logger):
        """run_phase1 with sector_mapping → returns sector_bmi_values."""
        mock_fetch.return_value = _make_daily_data(30)
        mock_sector_bmi.return_value = {"XLK": 55.0, "XLE": 30.0}

        polygon = MagicMock()
        mapping = {"AAPL": "Technology", "XOM": "Energy"}
        result = run_phase1(config, logger, polygon,
                           sector_mapping=mapping)

        assert result.sector_bmi_values == {"XLK": 55.0, "XLE": 30.0}
        mock_sector_bmi.assert_called_once()

    @patch("ifds.phases.phase1_regime._fetch_daily_history")
    def test_without_sector_mapping(self, mock_fetch, config, logger):
        """run_phase1 without sector_mapping → empty dict (backward compat)."""
        mock_fetch.return_value = _make_daily_data(30)

        polygon = MagicMock()
        result = run_phase1(config, logger, polygon)

        assert result.sector_bmi_values == {}


# ============================================================================
# Phase 3 Integration Tests
# ============================================================================

class TestPhase3SectorBMI:
    def test_with_sector_bmi_values(self, config, logger):
        """run_phase3 with sector_bmi_values → SectorScore.sector_bmi populated."""
        polygon = MagicMock()
        polygon.get_aggregates.side_effect = lambda ticker, from_date, to_date: [
            {"c": 100.0 + i * 0.5} for i in range(25)
        ]

        sector_bmi = {"XLK": 55.0, "XLE": 8.0, "XLU": 90.0}
        result = run_phase3(config, logger, polygon, StrategyMode.LONG,
                           sector_bmi_values=sector_bmi)

        xlk_score = next(s for s in result.sector_scores if s.etf == "XLK")
        xle_score = next(s for s in result.sector_scores if s.etf == "XLE")
        xlu_score = next(s for s in result.sector_scores if s.etf == "XLU")

        assert xlk_score.sector_bmi == 55.0
        assert xle_score.sector_bmi == 8.0
        assert xlu_score.sector_bmi == 90.0

    def test_sector_bmi_triggers_veto(self, config, logger):
        """Real sector BMI values should activate veto matrix."""
        polygon = MagicMock()
        # All sectors get same rising momentum
        polygon.get_aggregates.side_effect = lambda ticker, from_date, to_date: [
            {"c": 100.0 + i * 0.5} for i in range(25)
        ]

        # XLU overbought threshold is 75 — 90% triggers OVERBOUGHT
        # If XLU is classified as Neutral, Neutral+OVERBOUGHT → VETO
        sector_bmi = {"XLU": 90.0}
        result = run_phase3(config, logger, polygon, StrategyMode.LONG,
                           sector_bmi_values=sector_bmi)

        xlu_score = next(s for s in result.sector_scores if s.etf == "XLU")
        assert xlu_score.sector_bmi_regime == SectorBMIRegime.OVERBOUGHT

        # If XLU is Neutral classification + OVERBOUGHT → should be vetoed
        if xlu_score.classification == MomentumClassification.NEUTRAL:
            assert xlu_score.vetoed is True


# ============================================================================
# Veto Matrix Activation Tests (Unit Tests)
# ============================================================================

class TestVetoMatrixActivation:
    def test_laggard_oversold_mean_reversion(self, config, logger):
        """Laggard + OVERSOLD → allowed with -5 penalty (Mean Reversion)."""
        score = SectorScore(
            etf="XLE", sector_name="Energy",
            classification=MomentumClassification.LAGGARD,
            sector_bmi=8.0,
            sector_bmi_regime=SectorBMIRegime.OVERSOLD,
            score_adjustment=-20,
        )
        _apply_veto_matrix([score], config, logger)

        assert score.vetoed is False
        assert score.score_adjustment == -5  # MR penalty override

    def test_neutral_overbought_vetoed(self, config, logger):
        """Neutral + OVERBOUGHT → VETO."""
        score = SectorScore(
            etf="XLU", sector_name="Utilities",
            classification=MomentumClassification.NEUTRAL,
            sector_bmi=90.0,
            sector_bmi_regime=SectorBMIRegime.OVERBOUGHT,
            score_adjustment=0,
        )
        _apply_veto_matrix([score], config, logger)

        assert score.vetoed is True
        assert score.veto_reason == "Neutral + Overbought"


# ============================================================================
# _apply_sector_bmi Unit Tests
# ============================================================================

class TestApplySectorBMI:
    def test_oversold_classification(self, config):
        """Sector BMI below oversold threshold → OVERSOLD regime."""
        # XLE thresholds: (10, 75) → BMI < 10 = OVERSOLD
        score = SectorScore(etf="XLE", sector_name="Energy", sector_bmi=8.0)
        _apply_sector_bmi([score], config)
        assert score.sector_bmi_regime == SectorBMIRegime.OVERSOLD

    def test_overbought_classification(self, config):
        """Sector BMI above overbought threshold → OVERBOUGHT regime."""
        # XLU thresholds: (15, 75) → BMI > 75 = OVERBOUGHT
        score = SectorScore(etf="XLU", sector_name="Utilities", sector_bmi=80.0)
        _apply_sector_bmi([score], config)
        assert score.sector_bmi_regime == SectorBMIRegime.OVERBOUGHT

    def test_neutral_classification(self, config):
        """Sector BMI between thresholds → NEUTRAL regime."""
        # XLK thresholds: (12, 85) → 50 is between = NEUTRAL
        score = SectorScore(etf="XLK", sector_name="Technology", sector_bmi=50.0)
        _apply_sector_bmi([score], config)
        assert score.sector_bmi_regime == SectorBMIRegime.NEUTRAL

    def test_none_bmi_stays_neutral(self, config):
        """sector_bmi=None → regime stays default NEUTRAL."""
        score = SectorScore(etf="XLK", sector_name="Technology", sector_bmi=None)
        _apply_sector_bmi([score], config)
        assert score.sector_bmi_regime == SectorBMIRegime.NEUTRAL
