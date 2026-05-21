"""UW Dark Pool / GEX Shadow Log tests (Day 63 outcome §3.2).

Covers:
  * Phase 4 dp_pct bonus gating via ``uw_dark_pool_scoring_enabled``
    (live path + Pass-2 enrichment via ``_recompute_dp_pct_score``).
  * Phase 6 M_GEX gating via ``uw_gex_sizing_enabled``.
  * ``src/ifds/data/uw_shadow.py`` snapshot build, write/load, and summary.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ifds.config.loader import Config
from ifds.data.uw_shadow import (
    _gex_multiplier_for_regime,
    _recompute_dp_pct_score as shadow_recompute_dp_pct_score,
    build_shadow_snapshot,
    load_shadow_snapshot,
    summarize_shadow_snapshot,
    write_shadow_snapshot,
)
from ifds.models.market import (
    FlowAnalysis,
    FundamentalScoring,
    GEXAnalysis,
    GEXRegime,
    MacroRegime,
    MarketVolatilityRegime,
    PositionSizing,
    StockAnalysis,
    TechnicalAnalysis,
)
from ifds.phases.phase4_stocks import (
    _analyze_flow_from_data,
    _recompute_dp_pct_score as phase4_recompute_dp_pct_score,
)
from ifds.phases.phase6_sizing import _calculate_multiplier_total

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    monkeypatch.setenv("IFDS_ASYNC_ENABLED", "false")
    return Config()


@pytest.fixture
def macro():
    return MacroRegime(
        vix_value=18.0,
        vix_regime=MarketVolatilityRegime.NORMAL,
        vix_multiplier=1.0,
        tnx_value=4.2,
        tnx_sma20=4.1,
        tnx_rate_sensitive=False,
    )


def _make_bar(close=100.0, volume=1_000_000):
    return {
        "o": close,
        "h": close + 1.0,
        "l": close - 1.0,
        "c": close,
        "v": volume,
        "vw": close,
    }


def _make_dp_data(dp_volume: int, signal: str = "BULLISH") -> dict:
    return {
        "dp_volume": dp_volume,
        "total_volume": 0,
        "dp_pct": 0.0,
        "dp_buys": dp_volume // 2,
        "dp_sells": dp_volume // 2,
        "signal": signal,
        "source": "unusual_whales",
        "block_trade_count": 0,
    }


def _make_stock(
    ticker: str,
    *,
    combined_score: float = 90.0,
    dp_pct: float = 14.2,
    dp_score: int = 0,
) -> StockAnalysis:
    return StockAnalysis(
        ticker=ticker,
        sector="Technology",
        technical=TechnicalAnalysis(
            price=150.0,
            sma_200=140.0,
            sma_20=148.0,
            rsi_14=55.0,
            atr_14=3.0,
            trend_pass=True,
        ),
        flow=FlowAnalysis(dark_pool_pct=dp_pct, dp_pct_score=dp_score),
        fundamental=FundamentalScoring(funda_score=15, insider_multiplier=1.0),
        combined_score=combined_score,
    )


def _make_gex(
    ticker: str,
    *,
    regime: GEXRegime = GEXRegime.POSITIVE,
    multiplier: float = 1.0,
    net_gex: float = 1.23e9,
) -> GEXAnalysis:
    return GEXAnalysis(
        ticker=ticker,
        net_gex=net_gex,
        call_wall=160.0,
        put_wall=140.0,
        zero_gamma=148.0,
        current_price=150.0,
        gex_regime=regime,
        gex_multiplier=multiplier,
    )


def _make_position(ticker: str) -> PositionSizing:
    return PositionSizing(
        ticker=ticker,
        sector="Technology",
        direction="BUY",
        entry_price=150.0,
        quantity=10,
        stop_loss=140.0,
        take_profit_1=160.0,
        take_profit_2=170.0,
        risk_usd=100.0,
        combined_score=90.0,
        gex_regime=GEXRegime.POSITIVE.value,
        multiplier_total=1.0,
    )


# ---------------------------------------------------------------------------
# Phase 4: dp_pct bonus gating
# ---------------------------------------------------------------------------


class TestPhase4DpPctGating:
    """dp_pct bonus must be 0 when uw_dark_pool_scoring_enabled is False
    (default), and must apply the sign-flipped penalty when re-enabled."""

    def test_dp_pct_bonus_disabled_by_default(self, config):
        # Default flag is False per defaults.py (Day 63 §3.2)
        assert config.tuning["uw_dark_pool_scoring_enabled"] is False

        dp_data = _make_dp_data(dp_volume=140_000)
        bars = [_make_bar() for _ in range(30)]
        flow = _analyze_flow_from_data("TEST", bars, dp_data, config)
        assert flow.dark_pool_pct == 14.0  # Raw value preserved
        assert flow.dp_pct_score == 0  # Bonus gated off

    def test_dp_pct_bonus_active_when_scoring_enabled(self, config):
        config.tuning["uw_dark_pool_scoring_enabled"] = True

        dp_data = _make_dp_data(dp_volume=140_000)
        bars = [_make_bar() for _ in range(30)]
        flow = _analyze_flow_from_data("TEST", bars, dp_data, config)
        assert flow.dark_pool_pct == 14.0
        assert flow.dp_pct_score == -10  # Sign-flipped penalty restored

    def test_pass2_recompute_disabled_returns_zero(self, config):
        # Pass-2 enrichment path used by _apply_dp_enrichment
        assert phase4_recompute_dp_pct_score(22.0, config) == 0

    def test_pass2_recompute_enabled_returns_high_penalty(self, config):
        config.tuning["uw_dark_pool_scoring_enabled"] = True
        assert phase4_recompute_dp_pct_score(22.0, config) == -15


# ---------------------------------------------------------------------------
# Phase 6: M_GEX gating
# ---------------------------------------------------------------------------


class TestPhase6MGexGating:
    """M_GEX must be 1.0 when uw_gex_sizing_enabled is False (default), and
    must propagate gex.gex_multiplier when re-enabled."""

    def test_m_gex_forced_to_one_by_default(self, config, macro):
        assert config.tuning["uw_gex_sizing_enabled"] is False

        stock = _make_stock("AAPL")
        gex = _make_gex("AAPL", regime=GEXRegime.NEGATIVE, multiplier=0.5)
        m_total, multipliers = _calculate_multiplier_total(stock, gex, macro, config)
        assert multipliers["m_gex"] == 1.0

    def test_m_gex_propagates_when_sizing_enabled(self, config, macro):
        config.tuning["uw_gex_sizing_enabled"] = True

        stock = _make_stock("AAPL")
        gex = _make_gex("AAPL", regime=GEXRegime.HIGH_VOL, multiplier=0.6)
        m_total, multipliers = _calculate_multiplier_total(stock, gex, macro, config)
        assert multipliers["m_gex"] == 0.6


# ---------------------------------------------------------------------------
# Shadow log: build / write / load
# ---------------------------------------------------------------------------


class TestShadowSnapshotBuild:
    def test_snapshot_per_passed_ticker(self, config):
        stocks = [
            _make_stock("AAPL", dp_pct=14.2, combined_score=78.0),
            _make_stock("MSFT", dp_pct=5.0, combined_score=82.0),
        ]
        gexes = [
            _make_gex("AAPL", regime=GEXRegime.POSITIVE, multiplier=1.0, net_gex=1.23e9),
            _make_gex("MSFT", regime=GEXRegime.NEGATIVE, multiplier=0.5, net_gex=-2.1e8),
        ]
        positions = [_make_position("AAPL")]  # Only AAPL sized in Phase 6

        snap = build_shadow_snapshot(
            trading_date="2026-05-26",
            stock_analyses=stocks,
            gex_analyses=gexes,
            positions=positions,
            tuning=config.tuning,
        )

        assert snap["date"] == "2026-05-26"
        assert set(snap["tickers"].keys()) == {"AAPL", "MSFT"}

        aapl = snap["tickers"]["AAPL"]
        # AAPL: dp_pct 14.2 → would-have-been -10 even though flag is off
        assert aapl["dp_pct"] == 14.2
        assert aapl["dp_score_would_have_been"] == -10
        assert aapl["gex_regime"] == "positive"
        assert aapl["gex_value"] == pytest.approx(1.23e9)
        assert aapl["m_gex_would_have_been"] == 1.0
        assert aapl["phase4_passed"] is True
        assert aapl["phase6_sized"] is True
        assert aapl["combined_score"] == 78.0

        msft = snap["tickers"]["MSFT"]
        assert msft["dp_pct"] == 5.0
        assert msft["dp_score_would_have_been"] == 0  # Below threshold
        assert msft["gex_regime"] == "negative"
        assert msft["m_gex_would_have_been"] == 0.5
        assert msft["phase6_sized"] is False

    def test_snapshot_handles_missing_gex(self, config):
        # Stock without matching GEX entry (rare race) — must not crash
        stocks = [_make_stock("XYZ", dp_pct=20.0)]
        snap = build_shadow_snapshot(
            trading_date="2026-05-26",
            stock_analyses=stocks,
            gex_analyses=[],
            positions=[],
            tuning=config.tuning,
        )
        xyz = snap["tickers"]["XYZ"]
        assert xyz["gex_regime"] is None
        assert xyz["gex_value"] is None
        assert xyz["dp_pct"] == 20.0
        assert xyz["dp_score_would_have_been"] == -15  # ≥18% → high penalty

    def test_snapshot_empty_stock_list(self, config):
        snap = build_shadow_snapshot(
            trading_date="2026-05-26",
            stock_analyses=[],
            gex_analyses=[],
            positions=[],
            tuning=config.tuning,
        )
        assert snap == {"date": "2026-05-26", "tickers": {}}


class TestShadowSnapshotIO:
    def test_write_creates_directory_and_file(self, tmp_path):
        shadow_dir = tmp_path / "uw_shadow"
        snapshot = {"date": "2026-05-26", "tickers": {"AAPL": {"dp_pct": 7.5}}}

        path = write_shadow_snapshot(shadow_dir, "2026-05-26", snapshot)

        assert path.exists()
        assert path.name == "2026-05-26.json"
        payload = json.loads(path.read_text())
        assert payload["date"] == "2026-05-26"
        assert payload["tickers"]["AAPL"]["dp_pct"] == 7.5
        assert "captured_at" in payload  # ISO-8601 UTC stamp

    def test_load_returns_none_for_missing(self, tmp_path):
        shadow_dir = tmp_path / "uw_shadow"
        shadow_dir.mkdir()
        assert load_shadow_snapshot(shadow_dir, "2026-01-01") is None

    def test_round_trip(self, tmp_path):
        shadow_dir = tmp_path / "uw_shadow"
        snapshot = {"date": "2026-05-26", "tickers": {"AAPL": {"dp_pct": 7.5}}}
        write_shadow_snapshot(shadow_dir, "2026-05-26", snapshot)
        loaded = load_shadow_snapshot(shadow_dir, "2026-05-26")
        assert loaded is not None
        assert loaded["date"] == "2026-05-26"
        assert loaded["tickers"]["AAPL"]["dp_pct"] == 7.5


# ---------------------------------------------------------------------------
# Shadow log: summary helper for daily_metrics
# ---------------------------------------------------------------------------


class TestShadowSummary:
    def test_summary_aggregates_counts_and_averages(self):
        snapshot = {
            "date": "2026-05-26",
            "tickers": {
                "A": {
                    "dp_pct": 14.2,
                    "dp_score_would_have_been": -10,
                    "gex_regime": "positive",
                    "m_gex_would_have_been": 1.0,
                },
                "B": {
                    "dp_pct": 22.0,
                    "dp_score_would_have_been": -15,
                    "gex_regime": "negative",
                    "m_gex_would_have_been": 0.5,
                },
                "C": {
                    "dp_pct": 5.0,
                    "dp_score_would_have_been": 0,
                    "gex_regime": "positive",
                    "m_gex_would_have_been": 1.0,
                },
            },
        }
        summary = summarize_shadow_snapshot(snapshot)

        assert summary["tickers_logged"] == 3
        assert summary["avg_dp_pct"] == pytest.approx((14.2 + 22.0 + 5.0) / 3, abs=0.01)
        assert summary["would_have_been_penalty_count"] == 2
        assert summary["gex_regime_distribution"] == {"positive": 2, "negative": 1}
        assert summary["m_gex_avg_would_have_been"] == pytest.approx(
            (1.0 + 0.5 + 1.0) / 3,
            abs=0.001,
        )

    def test_summary_empty_snapshot(self):
        summary = summarize_shadow_snapshot({"date": "2026-05-26", "tickers": {}})
        assert summary["tickers_logged"] == 0
        assert summary["avg_dp_pct"] == 0.0
        assert summary["would_have_been_penalty_count"] == 0


# ---------------------------------------------------------------------------
# Shadow helpers (independent of pipeline objects)
# ---------------------------------------------------------------------------


class TestShadowHelpers:
    def test_recompute_dp_pct_score_boundaries(self, config):
        # The shadow helper ignores the gating flag — always returns what
        # the active scoring rule would have produced.
        assert shadow_recompute_dp_pct_score(11.9, config.tuning) == 0
        assert shadow_recompute_dp_pct_score(12.0, config.tuning) == -10
        assert shadow_recompute_dp_pct_score(17.9, config.tuning) == -10
        assert shadow_recompute_dp_pct_score(18.0, config.tuning) == -15
        assert shadow_recompute_dp_pct_score(25.0, config.tuning) == -15

    def test_gex_multiplier_mapping(self, config):
        assert _gex_multiplier_for_regime("positive", config.tuning) == 1.0
        assert _gex_multiplier_for_regime("negative", config.tuning) == 0.5
        assert _gex_multiplier_for_regime("high_vol", config.tuning) == 0.6
        assert _gex_multiplier_for_regime("", config.tuning) == 1.0  # fallback


# ---------------------------------------------------------------------------
# Config flags (defaults must match Day 63 outcome §3.2)
# ---------------------------------------------------------------------------


class TestConfigDefaults:
    def test_uw_flags_present_with_expected_defaults(self, config):
        assert config.tuning["uw_dark_pool_scoring_enabled"] is False
        assert config.tuning["uw_gex_sizing_enabled"] is False
        assert config.tuning["uw_shadow_logging_enabled"] is True
        assert config.tuning["uw_shadow_dir"] == "state/uw_shadow"
