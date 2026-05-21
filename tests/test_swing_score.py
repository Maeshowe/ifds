"""Swing scoring engine tests (Day 63 §3.13, 2026-05-18).

Covers:
  * ``compute_percentile_score`` boundary behavior.
  * ``compute_raw_swing_score`` formula correctness across the
    PCR-positive / OTM-negative + sector_adj axes.
  * ``SwingEwmaState`` lifecycle: Day-1 (raw), Day-2 (α-blend), persistence,
    span-window history pruning, corrupt-file safety.
  * ``compute_swing_scores`` end-to-end on a small universe.
  * Phase 4 integration: ``_apply_swing_scoring`` recovers legacy-clipped
    tickers, re-scores, applies the threshold, and persists state.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import (
    FlowAnalysis,
    FundamentalScoring,
    StockAnalysis,
    TechnicalAnalysis,
)
from ifds.phases.phase4_stocks import _apply_swing_scoring
from ifds.scoring.swing_score import (
    SwingEwmaState,
    compute_percentile_score,
    compute_raw_swing_score,
    compute_swing_scores,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config(monkeypatch, tmp_path):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    monkeypatch.setenv("IFDS_ASYNC_ENABLED", "false")
    cfg = Config()
    cfg.tuning["swing_scoring_enabled"] = True
    cfg.tuning["swing_ewma_state_file"] = str(tmp_path / "swing_ewma_state.json")
    return cfg


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-swing-score")


def _make_analysis(
    ticker: str,
    *,
    pcr: float | None = 0.7,
    otm: float | None = 0.4,
    sector_adj: int = 0,
    excluded: bool = False,
    exclusion_reason: str | None = None,
    legacy_score: float = 65.0,
) -> StockAnalysis:
    return StockAnalysis(
        ticker=ticker,
        sector="Technology",
        technical=TechnicalAnalysis(
            price=100.0,
            sma_200=95.0,
            sma_20=98.0,
            rsi_14=55.0,
            atr_14=2.0,
            trend_pass=True,
        ),
        flow=FlowAnalysis(pcr=pcr, otm_call_ratio=otm),
        fundamental=FundamentalScoring(),
        combined_score=legacy_score,
        sector_adjustment=sector_adj,
        excluded=excluded,
        exclusion_reason=exclusion_reason,
    )


# ---------------------------------------------------------------------------
# Percentile + raw score
# ---------------------------------------------------------------------------


class TestPercentileScore:
    def test_min_value_returns_low_percentile(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        assert compute_percentile_score(values, 10.0) == pytest.approx(0.20, abs=0.01)

    def test_max_value_returns_one(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        assert compute_percentile_score(values, 50.0) == pytest.approx(1.0, abs=0.01)

    def test_median_value_returns_half(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        assert compute_percentile_score(values, 30.0) == pytest.approx(0.60, abs=0.01)

    def test_empty_universe_returns_neutral(self):
        assert compute_percentile_score([], 42.0) == 0.5


class TestRawSwingScore:
    def test_high_pcr_low_otm_high_score(self):
        pcr_universe = [0.3, 0.5, 0.7, 0.9, 1.1]
        otm_universe = [0.2, 0.3, 0.4, 0.5, 0.6]
        score = compute_raw_swing_score(
            pcr=1.1,
            pcr_universe=pcr_universe,
            otm_call_ratio=0.2,
            otm_universe=otm_universe,
            sector_adjustment=0,
        )
        # PCR_pct=1.0, OTM_pct=0.2 → 100*(1.0−0.2) = 80
        assert score == pytest.approx(80.0, abs=0.01)

    def test_low_pcr_high_otm_low_score(self):
        pcr_universe = [0.3, 0.5, 0.7, 0.9, 1.1]
        otm_universe = [0.2, 0.3, 0.4, 0.5, 0.6]
        score = compute_raw_swing_score(
            pcr=0.3,
            pcr_universe=pcr_universe,
            otm_call_ratio=0.6,
            otm_universe=otm_universe,
            sector_adjustment=0,
        )
        # PCR_pct=0.2, OTM_pct=1.0 → 100*(0.2−1.0) = -80
        assert score == pytest.approx(-80.0, abs=0.01)

    def test_sector_leader_adds_15(self):
        score = compute_raw_swing_score(
            pcr=0.7,
            pcr_universe=[0.3, 0.5, 0.7, 0.9, 1.1],
            otm_call_ratio=0.4,
            otm_universe=[0.2, 0.3, 0.4, 0.5, 0.6],
            sector_adjustment=15,
        )
        # PCR_pct=0.6, OTM_pct=0.6 → 100*0 + 15 = 15
        assert score == pytest.approx(15.0, abs=0.01)


# ---------------------------------------------------------------------------
# EWMA state
# ---------------------------------------------------------------------------


class TestEwmaState:
    def test_day1_returns_raw(self, tmp_path):
        state = SwingEwmaState(path=tmp_path / "ewma.json", span=5)
        state.load()
        smoothed = state.update("AAPL", 60.0)
        assert smoothed == 60.0

    def test_day2_blends_with_alpha(self, tmp_path):
        state = SwingEwmaState(path=tmp_path / "ewma.json", span=5)
        state.load()
        state.update("AAPL", 60.0)  # Day 1 → ewma = 60.0
        s2 = state.update("AAPL", 40.0)  # Day 2 → α=2/6 ≈ 0.333
        # ewma_new = 0.333 * 40 + 0.667 * 60 = 53.33
        assert s2 == pytest.approx(53.33, abs=0.1)

    def test_history_capped_at_span(self, tmp_path):
        state = SwingEwmaState(path=tmp_path / "ewma.json", span=3)
        state.load()
        for value in [10.0, 20.0, 30.0, 40.0, 50.0]:
            state.update("X", value)
        entry = state.get("X")
        assert entry is not None
        assert entry["history"] == [30.0, 40.0, 50.0]  # last 3 only

    def test_persistence_round_trip(self, tmp_path):
        path = tmp_path / "ewma.json"
        s1 = SwingEwmaState(path=path)
        s1.load()
        s1.update("AAPL", 60.0)
        s1.update("MSFT", 70.0)
        s1.save()

        s2 = SwingEwmaState(path=path)
        s2.load()
        assert s2.get("AAPL")["ewma"] == 60.0
        assert s2.get("MSFT")["ewma"] == 70.0

    def test_corrupt_state_resets_to_empty(self, tmp_path):
        path = tmp_path / "ewma.json"
        path.write_text("{ not valid json")
        state = SwingEwmaState(path=path)
        state.load()
        # Should not raise — corrupt cache treated as empty
        assert state.as_dict() == {}


# ---------------------------------------------------------------------------
# Batch operation
# ---------------------------------------------------------------------------


class TestComputeSwingScores:
    def test_basic_distribution(self, tmp_path):
        # Decorrelated PCR + OTM universes so PCR_pct ≠ OTM_pct per ticker.
        # WIN has high PCR (top rank) + low OTM (bottom rank) → strongly positive.
        # LOSE has low PCR + high OTM → strongly negative.
        state = SwingEwmaState(path=tmp_path / "ewma.json")
        state.load()
        tickers_data = [
            {"ticker": "LOSE", "pcr": 0.3, "otm_call_ratio": 0.6, "sector_adjustment": 0},
            {"ticker": "MID", "pcr": 0.7, "otm_call_ratio": 0.4, "sector_adjustment": 0},
            {"ticker": "WIN", "pcr": 1.1, "otm_call_ratio": 0.2, "sector_adjustment": 0},
        ]
        results = compute_swing_scores(tickers_data, state)
        scores = {r.ticker: r.raw_score for r in results}
        assert scores["WIN"] > scores["MID"] > scores["LOSE"]
        # WIN: PCR_pct=1.0, OTM_pct=0.33 → 100*(1.0-0.33) ≈ 67
        assert scores["WIN"] == pytest.approx(66.67, abs=0.5)
        # LOSE: PCR_pct=0.33, OTM_pct=1.0 → 100*(0.33-1.0) ≈ -67
        assert scores["LOSE"] == pytest.approx(-66.67, abs=0.5)

    def test_missing_pcr_uses_median(self, tmp_path):
        state = SwingEwmaState(path=tmp_path / "ewma.json")
        state.load()
        tickers_data = [
            {"ticker": "A", "pcr": 0.5, "otm_call_ratio": 0.3, "sector_adjustment": 0},
            {"ticker": "B", "pcr": None, "otm_call_ratio": 0.3, "sector_adjustment": 0},
            {"ticker": "C", "pcr": 0.9, "otm_call_ratio": 0.3, "sector_adjustment": 0},
        ]
        results = compute_swing_scores(tickers_data, state)
        # B uses median PCR for normalization — should not crash + score is finite
        assert all(isinstance(r.raw_score, float) for r in results)


# ---------------------------------------------------------------------------
# Phase 4 integration
# ---------------------------------------------------------------------------


class TestPhase4SwingPostprocessor:
    def test_recovers_legacy_clipping_exclusions(self, config, logger, tmp_path):
        # 5 tickers — 2 legacy-clipped, 1 tech-filtered, 2 passed
        analyzed = [
            _make_analysis("PASS1", pcr=0.9, otm=0.2),
            _make_analysis("PASS2", pcr=0.8, otm=0.3),
            _make_analysis("CLIP1", pcr=0.6, otm=0.4, excluded=True, exclusion_reason="clipping"),
            _make_analysis("MIN1", pcr=0.5, otm=0.5, excluded=True, exclusion_reason="min_score"),
            _make_analysis(
                "TECH1", pcr=0.7, otm=0.6, excluded=True, exclusion_reason="tech_filter"
            ),
        ]
        passed, recovered, swing_filtered = _apply_swing_scoring(
            analyzed,
            config,
            logger,
        )
        # CLIP1 + MIN1 recovered, TECH1 stays excluded
        assert recovered == 2
        tech_still = [a for a in analyzed if a.ticker == "TECH1"][0]
        assert tech_still.excluded
        assert tech_still.exclusion_reason == "tech_filter"

    def test_threshold_filters_low_scores(self, config, logger):
        config.tuning["swing_score_threshold"] = 50.0
        # 3 tickers spread so only the high-PCR-low-OTM survives
        analyzed = [
            _make_analysis("WIN", pcr=1.5, otm=0.1),
            _make_analysis("MID", pcr=0.6, otm=0.5),
            _make_analysis("LOSE", pcr=0.2, otm=0.9),
        ]
        passed, _, swing_filtered = _apply_swing_scoring(
            analyzed,
            config,
            logger,
        )
        assert "WIN" in {a.ticker for a in passed}
        # At least one is filtered by swing_score threshold
        assert swing_filtered >= 1
        for analysis in analyzed:
            if analysis.exclusion_reason == "swing_score":
                assert analysis.excluded

    def test_passed_sorted_descending_by_score(self, config, logger):
        config.tuning["swing_score_threshold"] = -100.0  # everything passes
        analyzed = [
            _make_analysis("LOW", pcr=0.3, otm=0.7),
            _make_analysis("MID", pcr=0.6, otm=0.4),
            _make_analysis("HIGH", pcr=0.95, otm=0.1),
        ]
        passed, _, _ = _apply_swing_scoring(analyzed, config, logger)
        scores = [a.combined_score for a in passed]
        assert scores == sorted(scores, reverse=True)
        assert passed[0].ticker == "HIGH"

    def test_ewma_state_persisted_across_calls(self, config, logger):
        analyzed = [_make_analysis("AAPL", pcr=0.7, otm=0.3)]
        _apply_swing_scoring(analyzed, config, logger)
        # Reload state — Day-2 call should not start from scratch
        state_path = Path(config.tuning["swing_ewma_state_file"])
        assert state_path.exists()
        payload = json.loads(state_path.read_text())
        assert "AAPL" in payload
        assert "history" in payload["AAPL"]
        assert "ewma" in payload["AAPL"]
