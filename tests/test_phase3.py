"""Tests for Phase 3: Sector Rotation & Momentum."""

import pytest
from unittest.mock import MagicMock

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import (
    MacroRegime,
    MarketVolatilityRegime,
    MomentumClassification,
    Phase3Result,
    SectorBMIRegime,
    SectorScore,
    SectorTrend,
    StrategyMode,
)
from ifds.phases.phase3_sectors import (
    SECTOR_ETFS,
    run_phase3,
    _calculate_sector_scores,
    _rank_sectors,
    _apply_sector_bmi,
    _apply_veto_matrix,
    _apply_rate_sensitivity,
)


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    return Config()


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-phase3")


def _make_sector_data(close_today=100.0, close_5d_ago=98.0, sma20=99.0):
    """Create mock sector data dict."""
    return {
        "close_today": close_today,
        "close_period_ago": close_5d_ago,
        "sma20": sma20,
        "bars": [{"c": close_today}],
    }


def _make_scores_for_ranking(n=11):
    """Create N sector scores with varying momentum for ranking tests."""
    scores = []
    for i, (etf, name) in enumerate(SECTOR_ETFS.items()):
        score = SectorScore(
            etf=etf,
            sector_name=name,
            momentum_5d=float(n - i),  # Descending: 11, 10, 9, ...
        )
        scores.append(score)
    return scores


class TestSectorETFs:
    def test_has_11_sectors(self):
        assert len(SECTOR_ETFS) == 11

    def test_known_etfs_present(self):
        assert "XLK" in SECTOR_ETFS
        assert "XLF" in SECTOR_ETFS
        assert "XLRE" in SECTOR_ETFS
        assert "XLU" in SECTOR_ETFS


class TestCalculateSectorScores:
    def test_momentum_calculation(self, config):
        data = {"XLK": _make_sector_data(close_today=105.0, close_5d_ago=100.0)}
        scores = _calculate_sector_scores(data, config)
        assert len(scores) == 1
        assert scores[0].momentum_5d == pytest.approx(5.0, abs=0.01)

    def test_negative_momentum(self, config):
        data = {"XLE": _make_sector_data(close_today=95.0, close_5d_ago=100.0)}
        scores = _calculate_sector_scores(data, config)
        assert scores[0].momentum_5d == pytest.approx(-5.0, abs=0.01)

    def test_trend_up(self, config):
        data = {"XLK": _make_sector_data(close_today=105.0, sma20=100.0)}
        scores = _calculate_sector_scores(data, config)
        assert scores[0].trend == SectorTrend.UP

    def test_trend_down(self, config):
        data = {"XLK": _make_sector_data(close_today=95.0, sma20=100.0)}
        scores = _calculate_sector_scores(data, config)
        assert scores[0].trend == SectorTrend.DOWN

    def test_trend_at_sma_is_down(self, config):
        """Price = SMA20 → DOWN (<=)."""
        data = {"XLK": _make_sector_data(close_today=100.0, sma20=100.0)}
        scores = _calculate_sector_scores(data, config)
        assert scores[0].trend == SectorTrend.DOWN


class TestRankSectors:
    def test_top_3_are_leaders(self, config):
        scores = _make_scores_for_ranking()
        _rank_sectors(scores, config)
        leaders = [s for s in scores if s.classification == MomentumClassification.LEADER]
        assert len(leaders) == 3

    def test_bottom_3_are_laggards(self, config):
        scores = _make_scores_for_ranking()
        _rank_sectors(scores, config)
        laggards = [s for s in scores if s.classification == MomentumClassification.LAGGARD]
        assert len(laggards) == 3

    def test_middle_are_neutral(self, config):
        scores = _make_scores_for_ranking()
        _rank_sectors(scores, config)
        neutrals = [s for s in scores if s.classification == MomentumClassification.NEUTRAL]
        assert len(neutrals) == 5

    def test_leader_bonus(self, config):
        scores = _make_scores_for_ranking()
        _rank_sectors(scores, config)
        leaders = [s for s in scores if s.classification == MomentumClassification.LEADER]
        for leader in leaders:
            assert leader.score_adjustment == 15

    def test_laggard_penalty(self, config):
        scores = _make_scores_for_ranking()
        _rank_sectors(scores, config)
        laggards = [s for s in scores if s.classification == MomentumClassification.LAGGARD]
        for laggard in laggards:
            assert laggard.score_adjustment == -20

    def test_rank_order(self, config):
        scores = _make_scores_for_ranking()
        _rank_sectors(scores, config)
        sorted_by_rank = sorted(scores, key=lambda s: s.rank)
        for i in range(len(sorted_by_rank) - 1):
            assert sorted_by_rank[i].momentum_5d >= sorted_by_rank[i + 1].momentum_5d


class TestSectorBMI:
    def test_oversold(self, config):
        score = SectorScore(etf="XLK", sector_name="Technology", sector_bmi=10.0)
        _apply_sector_bmi([score], config)
        # XLK threshold is (12, 85), BMI=10 < 12 → OVERSOLD
        assert score.sector_bmi_regime == SectorBMIRegime.OVERSOLD

    def test_neutral(self, config):
        score = SectorScore(etf="XLK", sector_name="Technology", sector_bmi=50.0)
        _apply_sector_bmi([score], config)
        assert score.sector_bmi_regime == SectorBMIRegime.NEUTRAL

    def test_overbought(self, config):
        score = SectorScore(etf="XLK", sector_name="Technology", sector_bmi=90.0)
        _apply_sector_bmi([score], config)
        # XLK threshold is (12, 85), BMI=90 > 85 → OVERBOUGHT
        assert score.sector_bmi_regime == SectorBMIRegime.OVERBOUGHT

    def test_per_sector_thresholds(self, config):
        """XLE has different thresholds (10, 75) than XLK (12, 85)."""
        score_xle = SectorScore(etf="XLE", sector_name="Energy", sector_bmi=76.0)
        _apply_sector_bmi([score_xle], config)
        # XLE threshold is (10, 75), BMI=76 > 75 → OVERBOUGHT
        assert score_xle.sector_bmi_regime == SectorBMIRegime.OVERBOUGHT

    def test_no_bmi_stays_neutral(self, config):
        """If sector_bmi is None, regime stays at default NEUTRAL."""
        score = SectorScore(etf="XLK", sector_name="Technology", sector_bmi=None)
        _apply_sector_bmi([score], config)
        assert score.sector_bmi_regime == SectorBMIRegime.NEUTRAL


class TestVetoMatrix:
    """Test all veto matrix combinations per IDEA.md spec."""

    def test_leader_neutral_bmi_allowed(self, config, logger):
        score = SectorScore(
            etf="XLK", sector_name="Technology",
            classification=MomentumClassification.LEADER,
            sector_bmi_regime=SectorBMIRegime.NEUTRAL,
            score_adjustment=15,
        )
        _apply_veto_matrix([score], config, logger)
        assert score.vetoed is False

    def test_leader_overbought_allowed(self, config, logger):
        """Leaders pass even with OVERBOUGHT sector."""
        score = SectorScore(
            etf="XLK", sector_name="Technology",
            classification=MomentumClassification.LEADER,
            sector_bmi_regime=SectorBMIRegime.OVERBOUGHT,
            score_adjustment=15,
        )
        _apply_veto_matrix([score], config, logger)
        assert score.vetoed is False

    def test_leader_oversold_allowed(self, config, logger):
        score = SectorScore(
            etf="XLK", sector_name="Technology",
            classification=MomentumClassification.LEADER,
            sector_bmi_regime=SectorBMIRegime.OVERSOLD,
            score_adjustment=15,
        )
        _apply_veto_matrix([score], config, logger)
        assert score.vetoed is False

    def test_neutral_neutral_bmi_allowed(self, config, logger):
        score = SectorScore(
            etf="XLI", sector_name="Industrials",
            classification=MomentumClassification.NEUTRAL,
            sector_bmi_regime=SectorBMIRegime.NEUTRAL,
        )
        _apply_veto_matrix([score], config, logger)
        assert score.vetoed is False

    def test_neutral_oversold_allowed(self, config, logger):
        score = SectorScore(
            etf="XLI", sector_name="Industrials",
            classification=MomentumClassification.NEUTRAL,
            sector_bmi_regime=SectorBMIRegime.OVERSOLD,
        )
        _apply_veto_matrix([score], config, logger)
        assert score.vetoed is False

    def test_neutral_overbought_vetoed(self, config, logger):
        score = SectorScore(
            etf="XLI", sector_name="Industrials",
            classification=MomentumClassification.NEUTRAL,
            sector_bmi_regime=SectorBMIRegime.OVERBOUGHT,
        )
        _apply_veto_matrix([score], config, logger)
        assert score.vetoed is True
        assert "Overbought" in score.veto_reason

    def test_laggard_oversold_mean_reversion(self, config, logger):
        """Laggard + Oversold = allowed (Mean Reversion), -5 penalty."""
        score = SectorScore(
            etf="XLU", sector_name="Utilities",
            classification=MomentumClassification.LAGGARD,
            sector_bmi_regime=SectorBMIRegime.OVERSOLD,
            score_adjustment=-20,
        )
        _apply_veto_matrix([score], config, logger)
        assert score.vetoed is False
        assert score.score_adjustment == -5  # Mean reversion penalty replaces laggard penalty

    def test_laggard_neutral_bmi_vetoed(self, config, logger):
        score = SectorScore(
            etf="XLU", sector_name="Utilities",
            classification=MomentumClassification.LAGGARD,
            sector_bmi_regime=SectorBMIRegime.NEUTRAL,
        )
        _apply_veto_matrix([score], config, logger)
        assert score.vetoed is True

    def test_laggard_overbought_vetoed(self, config, logger):
        score = SectorScore(
            etf="XLU", sector_name="Utilities",
            classification=MomentumClassification.LAGGARD,
            sector_bmi_regime=SectorBMIRegime.OVERBOUGHT,
        )
        _apply_veto_matrix([score], config, logger)
        assert score.vetoed is True

    def test_veto_logs_event(self, config, logger):
        score = SectorScore(
            etf="XLB", sector_name="Basic Materials",
            classification=MomentumClassification.LAGGARD,
            sector_bmi_regime=SectorBMIRegime.NEUTRAL,
        )
        _apply_veto_matrix([score], config, logger)
        veto_events = [e for e in logger.events if e["event_type"] == "SECTOR_VETO"]
        assert len(veto_events) == 1
        assert veto_events[0]["data"]["etf"] == "XLB"


class TestRateSensitivity:
    def test_tech_penalized(self, config, logger):
        score = SectorScore(
            etf="XLK", sector_name="Technology",
            score_adjustment=15,
        )
        _apply_rate_sensitivity([score], config, logger)
        assert score.score_adjustment == 5  # 15 - 10

    def test_real_estate_penalized(self, config, logger):
        score = SectorScore(
            etf="XLRE", sector_name="Real Estate",
            score_adjustment=0,
        )
        _apply_rate_sensitivity([score], config, logger)
        assert score.score_adjustment == -10

    def test_non_sensitive_sector_unchanged(self, config, logger):
        score = SectorScore(
            etf="XLE", sector_name="Energy",
            score_adjustment=15,
        )
        _apply_rate_sensitivity([score], config, logger)
        assert score.score_adjustment == 15  # Unchanged

    def test_vetoed_sector_not_penalized(self, config, logger):
        score = SectorScore(
            etf="XLK", sector_name="Technology",
            score_adjustment=0,
            vetoed=True,
        )
        _apply_rate_sensitivity([score], config, logger)
        assert score.score_adjustment == 0  # Not penalized since vetoed


class TestPhase3Integration:
    def test_full_flow(self, config, logger):
        polygon = MagicMock()
        # Return aggregates for all 11 ETFs
        def mock_aggregates(ticker, from_date, to_date):
            return [{"c": 95.0 + i} for i in range(25)]
        polygon.get_aggregates.side_effect = mock_aggregates

        result = run_phase3(config, logger, polygon, StrategyMode.LONG)

        assert isinstance(result, Phase3Result)
        assert len(result.sector_scores) == 11
        assert len(result.active_sectors) + len(result.vetoed_sectors) == 11

    def test_rate_sensitivity_with_macro(self, config, logger):
        polygon = MagicMock()
        def mock_aggregates(ticker, from_date, to_date):
            return [{"c": 100.0 + i * 0.5} for i in range(25)]
        polygon.get_aggregates.side_effect = mock_aggregates

        macro = MacroRegime(
            vix_value=18.0,
            vix_regime=MarketVolatilityRegime.NORMAL,
            vix_multiplier=1.0,
            tnx_value=4.5,
            tnx_sma20=4.0,
            tnx_rate_sensitive=True,  # TNX > SMA20 * 1.05
        )

        result = run_phase3(config, logger, polygon, StrategyMode.LONG, macro=macro)
        assert result.rate_sensitive_penalty is True

    def test_no_rate_sensitivity_without_macro(self, config, logger):
        polygon = MagicMock()
        polygon.get_aggregates.return_value = [{"c": 100.0 + i} for i in range(25)]

        result = run_phase3(config, logger, polygon, StrategyMode.LONG, macro=None)
        assert result.rate_sensitive_penalty is False
