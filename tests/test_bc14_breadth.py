"""BC14 Feature Tests — Sector Breadth Analysis.

~30 tests covering: BreadthRegime enum, SMA computation, ticker close history
extraction, breadth calculation, regime classification, divergence detection,
score adjustment, FMP ETF holdings, and Phase 3 integration.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import (
    BreadthRegime,
    MomentumClassification,
    Phase3Result,
    SectorBMIRegime,
    SectorBreadth,
    SectorScore,
    SectorTrend,
    StrategyMode,
)
from ifds.phases.phase3_sectors import (
    _apply_breadth_score_adjustment,
    _build_ticker_close_history,
    _calculate_breadth,
    _classify_breadth_regime,
    _compute_pct_above_sma_n_days_ago,
    _compute_sma,
    _detect_breadth_divergence,
    _calculate_sector_breadth,
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
    return EventLogger(log_dir=str(tmp_path), run_id="test-bc14")


def _make_grouped_bars(num_days=250, tickers=None):
    """Create fake grouped daily bars with predictable closes.

    For each ticker, close = 100 + day_index * 0.1 (uptrend).
    Uses "bars" key matching Phase 1 _fetch_daily_history format.
    """
    if tickers is None:
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    daily_data = []
    for day_idx in range(num_days):
        day_bars = []
        for t in tickers:
            close = 100.0 + day_idx * 0.1
            day_bars.append({
                "T": t,
                "o": close - 0.5,
                "h": close + 1.0,
                "l": close - 1.0,
                "c": close,
                "v": 1000000,
            })
        daily_data.append({
            "date": f"2025-01-{day_idx + 1:02d}",
            "bars": day_bars,
            "_buy_count": 3,
            "_sell_count": 2,
            "_ticker_count": len(tickers),
        })
    return daily_data


def _make_sector_score(etf="XLK", sector_name="Technology",
                       momentum_5d=1.5) -> SectorScore:
    """Create a basic SectorScore for testing."""
    return SectorScore(
        etf=etf,
        sector_name=sector_name,
        momentum_5d=momentum_5d,
        trend=SectorTrend.UP,
        classification=MomentumClassification.LEADER,
        score_adjustment=15,
    )


# ============================================================================
# TestBreadthRegimeEnum
# ============================================================================

class TestBreadthRegimeEnum:
    def test_has_7_values(self):
        assert len(BreadthRegime) == 7

    def test_lowercase_strings(self):
        assert BreadthRegime.STRONG.value == "strong"
        assert BreadthRegime.EMERGING.value == "emerging"
        assert BreadthRegime.CONSOLIDATING.value == "consolidating"
        assert BreadthRegime.NEUTRAL.value == "neutral"
        assert BreadthRegime.WEAKENING.value == "weakening"
        assert BreadthRegime.WEAK.value == "weak"
        assert BreadthRegime.RECOVERY.value == "recovery"


# ============================================================================
# TestComputeSMA
# ============================================================================

class TestComputeSMA:
    def test_basic_sma(self):
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        assert _compute_sma(prices, 3) == pytest.approx(40.0)  # (30+40+50)/3

    def test_insufficient_data_returns_none(self):
        assert _compute_sma([10.0, 20.0], 5) is None

    def test_uses_last_n_values(self):
        prices = [1.0, 2.0, 3.0, 100.0, 200.0]
        # SMA2 = (100 + 200) / 2 = 150
        assert _compute_sma(prices, 2) == pytest.approx(150.0)


# ============================================================================
# TestBuildTickerCloseHistory
# ============================================================================

class TestBuildTickerCloseHistory:
    def test_extracts_closes(self):
        bars = _make_grouped_bars(num_days=30, tickers=["AAPL", "MSFT"])
        histories = _build_ticker_close_history(bars, {"AAPL", "MSFT"})
        assert "AAPL" in histories
        assert "MSFT" in histories
        assert len(histories["AAPL"]) == 30

    def test_filters_insufficient_data(self):
        bars = _make_grouped_bars(num_days=10, tickers=["AAPL"])
        histories = _build_ticker_close_history(bars, {"AAPL"})
        # 10 data points < 20 minimum
        assert "AAPL" not in histories

    def test_ignores_untracked_tickers(self):
        bars = _make_grouped_bars(num_days=30, tickers=["AAPL", "MSFT"])
        histories = _build_ticker_close_history(bars, {"AAPL"})
        assert "AAPL" in histories
        assert "MSFT" not in histories


# ============================================================================
# TestCalculateBreadth
# ============================================================================

class TestCalculateBreadth:
    def test_all_above_sma(self):
        """All tickers in uptrend → 100% above all SMAs."""
        bars = _make_grouped_bars(num_days=250, tickers=["A", "B", "C"])
        histories = _build_ticker_close_history(bars, {"A", "B", "C"})
        # All tickers trend up (100 + idx*0.1), so last close > any SMA
        cfg = MagicMock()
        cfg.core = {
            "breadth_sma_periods": [20, 50, 200],
            "breadth_composite_weights": (0.20, 0.50, 0.30),
        }
        breadth = _calculate_breadth("XLK", ["A", "B", "C"], histories, cfg)
        assert breadth.pct_above_sma20 == pytest.approx(100.0)
        assert breadth.pct_above_sma50 == pytest.approx(100.0)
        assert breadth.pct_above_sma200 == pytest.approx(100.0)
        assert breadth.breadth_score == pytest.approx(100.0)

    def test_no_data_returns_zeros(self):
        """No matching tickers → all percentages 0."""
        cfg = MagicMock()
        cfg.core = {
            "breadth_sma_periods": [20, 50, 200],
            "breadth_composite_weights": (0.20, 0.50, 0.30),
        }
        breadth = _calculate_breadth("XLK", ["NONE1", "NONE2"], {}, cfg)
        assert breadth.pct_above_sma20 == 0.0
        assert breadth.breadth_score == 0.0
        assert breadth.constituent_count == 0

    def test_mixed_results(self):
        """Some above, some below."""
        # Create histories where A is above SMA20 but B is below
        histories = {
            "A": [100.0] * 19 + [200.0],  # Last price 200 > SMA20(~105.x)
            "B": [200.0] * 19 + [100.0],  # Last price 100 < SMA20(~195.x)
        }
        cfg = MagicMock()
        cfg.core = {
            "breadth_sma_periods": [20],
            "breadth_composite_weights": (1.0,),
        }
        breadth = _calculate_breadth("XLK", ["A", "B"], histories, cfg)
        assert breadth.pct_above_sma20 == pytest.approx(50.0)

    def test_default_regime_is_neutral(self):
        cfg = MagicMock()
        cfg.core = {
            "breadth_sma_periods": [20, 50, 200],
            "breadth_composite_weights": (0.20, 0.50, 0.30),
        }
        breadth = _calculate_breadth("XLK", [], {}, cfg)
        assert breadth.breadth_regime == BreadthRegime.NEUTRAL


# ============================================================================
# TestClassifyBreadthRegime — all 7 states
# ============================================================================

class TestClassifyBreadthRegime:
    def test_strong(self):
        b = SectorBreadth(etf="XLK", pct_above_sma50=80.0, pct_above_sma200=80.0)
        _classify_breadth_regime(b, pct_sma50_5d_ago=75.0)
        assert b.breadth_regime == BreadthRegime.STRONG
        assert b.breadth_momentum == pytest.approx(5.0)

    def test_emerging(self):
        b = SectorBreadth(etf="XLK", pct_above_sma50=75.0, pct_above_sma200=50.0)
        _classify_breadth_regime(b, pct_sma50_5d_ago=70.0)
        assert b.breadth_regime == BreadthRegime.EMERGING

    def test_consolidating(self):
        b = SectorBreadth(etf="XLK", pct_above_sma50=50.0, pct_above_sma200=80.0)
        _classify_breadth_regime(b, pct_sma50_5d_ago=55.0)
        assert b.breadth_regime == BreadthRegime.CONSOLIDATING

    def test_neutral(self):
        b = SectorBreadth(etf="XLK", pct_above_sma50=50.0, pct_above_sma200=50.0)
        _classify_breadth_regime(b, pct_sma50_5d_ago=50.0)
        assert b.breadth_regime == BreadthRegime.NEUTRAL

    def test_weakening(self):
        b = SectorBreadth(etf="XLK", pct_above_sma50=20.0, pct_above_sma200=50.0)
        _classify_breadth_regime(b, pct_sma50_5d_ago=25.0)
        assert b.breadth_regime == BreadthRegime.WEAKENING

    def test_weak(self):
        b = SectorBreadth(etf="XLK", pct_above_sma50=20.0, pct_above_sma200=20.0)
        _classify_breadth_regime(b, pct_sma50_5d_ago=25.0)
        assert b.breadth_regime == BreadthRegime.WEAK

    def test_recovery(self):
        b = SectorBreadth(etf="XLK", pct_above_sma50=55.0, pct_above_sma200=20.0)
        _classify_breadth_regime(b, pct_sma50_5d_ago=50.0)
        assert b.breadth_regime == BreadthRegime.RECOVERY

    def test_no_previous_data(self):
        b = SectorBreadth(etf="XLK", pct_above_sma50=50.0, pct_above_sma200=50.0)
        _classify_breadth_regime(b, pct_sma50_5d_ago=None)
        assert b.breadth_regime == BreadthRegime.NEUTRAL
        assert b.breadth_momentum == 0.0


# ============================================================================
# TestBreadthDivergence
# ============================================================================

class TestBreadthDivergence:
    def test_bearish_divergence(self, config):
        # ETF up >2%, breadth down <-5
        detected, div_type = _detect_breadth_divergence(3.0, -6.0, config)
        assert detected is True
        assert div_type == "bearish"

    def test_bullish_divergence(self, config):
        # ETF down <-2%, breadth up >5
        detected, div_type = _detect_breadth_divergence(-3.0, 6.0, config)
        assert detected is True
        assert div_type == "bullish"

    def test_no_divergence(self, config):
        detected, div_type = _detect_breadth_divergence(1.0, 2.0, config)
        assert detected is False
        assert div_type is None


# ============================================================================
# TestBreadthScoreAdjustment
# ============================================================================

class TestBreadthScoreAdjustment:
    def test_strong_bonus(self, config):
        b = SectorBreadth(etf="XLK", breadth_score=75.0)
        _apply_breadth_score_adjustment(b, config)
        assert b.score_adjustment == 5

    def test_weak_penalty(self, config):
        b = SectorBreadth(etf="XLK", breadth_score=45.0)
        _apply_breadth_score_adjustment(b, config)
        assert b.score_adjustment == -5

    def test_very_weak_penalty(self, config):
        b = SectorBreadth(etf="XLK", breadth_score=25.0)
        _apply_breadth_score_adjustment(b, config)
        assert b.score_adjustment == -15

    def test_neutral_no_adjustment(self, config):
        b = SectorBreadth(etf="XLK", breadth_score=55.0)
        _apply_breadth_score_adjustment(b, config)
        assert b.score_adjustment == 0

    def test_bearish_divergence_stacks(self, config):
        b = SectorBreadth(etf="XLK", breadth_score=75.0,
                          divergence_detected=True, divergence_type="bearish")
        _apply_breadth_score_adjustment(b, config)
        # +5 (strong) + (-10 divergence) = -5
        assert b.score_adjustment == -5

    def test_bullish_divergence_no_extra_penalty(self, config):
        b = SectorBreadth(etf="XLK", breadth_score=75.0,
                          divergence_detected=True, divergence_type="bullish")
        _apply_breadth_score_adjustment(b, config)
        # Only strong bonus, no divergence penalty for bullish
        assert b.score_adjustment == 5


# ============================================================================
# TestFMPGetEtfHoldings
# ============================================================================

class TestFMPGetEtfHoldings:
    def test_sync_get_etf_holdings(self):
        from ifds.data.fmp import FMPClient

        mock_response = [{"asset": "AAPL"}, {"asset": "MSFT"}]
        client = FMPClient(api_key="test_key")
        with patch.object(client, "_get", return_value=mock_response):
            result = client.get_etf_holdings("XLK")
        assert result == mock_response
        client.close()

    def test_sync_get_etf_holdings_cached(self):
        from ifds.data.fmp import FMPClient
        from ifds.data.cache import FileCache

        cache = MagicMock(spec=FileCache)
        cached_data = [{"asset": "AAPL"}]
        cache.get.return_value = cached_data

        client = FMPClient(api_key="test_key", cache=cache)
        result = client.get_etf_holdings("XLK")
        assert result == cached_data
        cache.get.assert_called_once()
        client.close()


# ============================================================================
# TestComputePctAboveSmaNDaysAgo
# ============================================================================

class TestComputePctAboveSmaNDaysAgo:
    def test_basic_recomputation(self):
        # 60 data points, all trending up
        hist_a = [100.0 + i * 0.5 for i in range(60)]
        hist_b = [200.0 - i * 0.5 for i in range(60)]  # trending down
        histories = {"A": hist_a, "B": hist_b}
        # 5 days ago, A was still trending up → above SMA50
        # B was trending down → could be below
        result = _compute_pct_above_sma_n_days_ago(
            ["A", "B"], histories, period=50, days_ago=5,
        )
        assert result is not None
        assert 0.0 <= result <= 100.0

    def test_returns_none_insufficient_data(self):
        histories = {"A": [100.0] * 30}
        result = _compute_pct_above_sma_n_days_ago(
            ["A"], histories, period=50, days_ago=5,
        )
        assert result is None


# ============================================================================
# TestCalculateSectorBreadth (integration)
# ============================================================================

class TestCalculateSectorBreadth:
    def test_breadth_attached_to_scores(self, config, logger):
        scores = [_make_sector_score("XLK", "Technology")]
        bars = _make_grouped_bars(num_days=250, tickers=["AAPL", "MSFT", "GOOGL"])

        mock_fmp = MagicMock()
        mock_fmp.get_etf_holdings.return_value = [
            {"asset": "AAPL"}, {"asset": "MSFT"}, {"asset": "GOOGL"},
        ]

        # Override min_constituents to 1 for test
        config.tuning["breadth_min_constituents"] = 1

        _calculate_sector_breadth(scores, bars, mock_fmp, config, logger)
        assert scores[0].breadth is not None
        assert scores[0].breadth.etf == "XLK"
        assert scores[0].breadth.constituent_count > 0
        assert scores[0].breadth.breadth_score > 0

    def test_no_holdings_skips(self, config, logger):
        scores = [_make_sector_score("XLK", "Technology")]
        bars = _make_grouped_bars(num_days=250)

        mock_fmp = MagicMock()
        mock_fmp.get_etf_holdings.return_value = None

        _calculate_sector_breadth(scores, bars, mock_fmp, config, logger)
        assert scores[0].breadth is None

    def test_score_adjustment_applied(self, config, logger):
        scores = [_make_sector_score("XLK", "Technology")]
        bars = _make_grouped_bars(num_days=250, tickers=["A", "B", "C"])

        mock_fmp = MagicMock()
        mock_fmp.get_etf_holdings.return_value = [
            {"asset": "A"}, {"asset": "B"}, {"asset": "C"},
        ]
        config.tuning["breadth_min_constituents"] = 1

        _calculate_sector_breadth(scores, bars, mock_fmp, config, logger)
        # All tickers in uptrend → high breadth → +10 bonus
        assert scores[0].breadth is not None
        assert scores[0].breadth_score_adj == scores[0].breadth.score_adjustment


# ============================================================================
# TestPhase3BreadthIntegration
# ============================================================================

class TestPhase3BreadthIntegration:
    @patch("ifds.phases.phase3_sectors._fetch_sector_data")
    def test_breadth_enabled_calls_engine(self, mock_fetch, config, logger):
        """When breadth enabled + data provided, breadth is calculated."""
        mock_fetch.return_value = {
            "XLK": {
                "bars": [{"c": 100}] * 10,
                "close_today": 105.0,
                "close_period_ago": 100.0,
                "sma20": 102.0,
            },
        }
        bars = _make_grouped_bars(num_days=250, tickers=["AAPL", "MSFT", "GOOGL"])

        mock_fmp = MagicMock()
        mock_fmp.get_etf_holdings.return_value = [
            {"asset": "AAPL"}, {"asset": "MSFT"}, {"asset": "GOOGL"},
        ]

        config.tuning["breadth_min_constituents"] = 1
        mock_polygon = MagicMock()
        result = run_phase3(config, logger, mock_polygon, StrategyMode.LONG,
                            grouped_daily_bars=bars, fmp=mock_fmp)
        xlk_score = next(s for s in result.sector_scores if s.etf == "XLK")
        assert xlk_score.breadth is not None

    @patch("ifds.phases.phase3_sectors._fetch_sector_data")
    def test_breadth_disabled_skips(self, mock_fetch, config, logger):
        """When breadth disabled, no breadth data attached."""
        mock_fetch.return_value = {
            "XLK": {
                "bars": [{"c": 100}] * 10,
                "close_today": 105.0,
                "close_period_ago": 100.0,
                "sma20": 102.0,
            },
        }
        config.tuning["breadth_enabled"] = False
        mock_polygon = MagicMock()
        result = run_phase3(config, logger, mock_polygon, StrategyMode.LONG)
        xlk_score = next(s for s in result.sector_scores if s.etf == "XLK")
        assert xlk_score.breadth is None

    @patch("ifds.phases.phase3_sectors._fetch_sector_data")
    def test_no_fmp_skips(self, mock_fetch, config, logger):
        """When fmp not provided, breadth is skipped."""
        mock_fetch.return_value = {
            "XLK": {
                "bars": [{"c": 100}] * 10,
                "close_today": 105.0,
                "close_period_ago": 100.0,
                "sma20": 102.0,
            },
        }
        bars = _make_grouped_bars(num_days=250)
        mock_polygon = MagicMock()
        result = run_phase3(config, logger, mock_polygon, StrategyMode.LONG,
                            grouped_daily_bars=bars, fmp=None)
        xlk_score = next(s for s in result.sector_scores if s.etf == "XLK")
        assert xlk_score.breadth is None


# ============================================================================
# TestPhase1GroupedBars
# ============================================================================

class TestPhase1GroupedBars:
    @patch("ifds.phases.phase1_regime._fetch_daily_history")
    def test_breadth_enabled_increases_lookback(self, mock_fetch, config, logger):
        """When breadth_enabled=True, lookback increases to 290."""
        from ifds.phases.phase1_regime import run_phase1

        mock_fetch.return_value = _make_grouped_bars(num_days=200)
        run_phase1(config, logger, MagicMock())
        # Check the lookback_calendar_days argument
        call_kwargs = mock_fetch.call_args
        assert call_kwargs[1]["lookback_calendar_days"] == 330

    @patch("ifds.phases.phase1_regime._fetch_daily_history")
    def test_breadth_disabled_keeps_75(self, mock_fetch, config, logger):
        """When breadth_enabled=False, lookback stays at 75."""
        from ifds.phases.phase1_regime import run_phase1

        config.tuning["breadth_enabled"] = False
        mock_fetch.return_value = _make_grouped_bars(num_days=50)
        run_phase1(config, logger, MagicMock())
        call_kwargs = mock_fetch.call_args
        assert call_kwargs[1]["lookback_calendar_days"] == 75

    @patch("ifds.phases.phase1_regime._fetch_daily_history")
    def test_grouped_bars_stored_in_result(self, mock_fetch, config, logger):
        """Phase1Result contains grouped_daily_bars when breadth enabled."""
        from ifds.phases.phase1_regime import run_phase1

        bars = _make_grouped_bars(num_days=200)
        mock_fetch.return_value = bars
        result = run_phase1(config, logger, MagicMock())
        assert result.grouped_daily_bars == bars

    @patch("ifds.phases.phase1_regime._fetch_daily_history")
    def test_grouped_bars_empty_when_disabled(self, mock_fetch, config, logger):
        """Phase1Result has empty grouped_daily_bars when breadth disabled."""
        from ifds.phases.phase1_regime import run_phase1

        config.tuning["breadth_enabled"] = False
        mock_fetch.return_value = _make_grouped_bars(num_days=50)
        result = run_phase1(config, logger, MagicMock())
        assert result.grouped_daily_bars == []
