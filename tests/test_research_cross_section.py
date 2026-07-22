"""v2 research cross-section sink — schema, gzip, era-explicit score fields."""

from __future__ import annotations

import gzip
import json
from unittest.mock import MagicMock

import pytest

from ifds.models.market import (
    FlowAnalysis,
    FundamentalScoring,
    StockAnalysis,
    TechnicalAnalysis,
)
from ifds.output import research_cross_section as rcs


def _stock(
    ticker: str = "AAPL",
    sector: str = "Technology",
    score: float = 61.42,
    excluded: bool = False,
    reason: str | None = None,
) -> StockAnalysis:
    analysis = StockAnalysis(
        ticker=ticker,
        sector=sector,
        technical=TechnicalAnalysis(
            price=180.0,
            sma_200=170.0,
            sma_20=178.0,
            rsi_14=55.0,
            atr_14=3.2,
            trend_pass=True,
            rsi_score=10,
            sma_50=175.0,
            sma50_bonus=5,
            rs_vs_spy=0.02,
            rs_spy_score=5,
        ),
        flow=FlowAnalysis(
            rvol=1.4,
            rvol_score=5,
            dark_pool_pct=12.0,
            dp_pct_score=0,
            pcr=0.62,
            pcr_score=10,
            otm_call_ratio=0.31,
            otm_score=-5,
            block_trade_count=2,
            block_trade_score=3,
            buy_pressure_score=2,
            squat_bar=False,
        ),
        fundamental=FundamentalScoring(
            revenue_growth_yoy=0.12,
            eps_growth_yoy=0.18,
            net_margin=0.24,
            roe=0.35,
            debt_equity=1.2,
            insider_score=5,
            insider_multiplier=1.0,
            funda_score=12,
            shark_detected=False,
        ),
        combined_score=score,
        sector_adjustment=3,
    )
    analysis.excluded = excluded
    analysis.exclusion_reason = reason
    return analysis


def _sector_score(name: str = "Technology", vetoed: bool = False):
    score = MagicMock()
    score.sector_name = name
    score.etf = "XLK"
    score.sector_bmi = 55.0
    score.vetoed = vetoed
    score.sector_bmi_regime = MagicMock(value="BULLISH")
    return score


class TestEraExplicitScoreFields:
    """The FRL-0 lesson encoded: one ambiguous score column cost a full audit."""

    def test_swing_mode_fills_swing_score_and_leaves_legacy_null(self):
        records = rcs.build_records([_stock(score=61.42)], swing_scoring_enabled=True)
        assert records[0]["swing_score"] == 61.42
        assert records[0]["legacy_composite"] is None
        assert records[0]["scoring_mode"] == "swing"

    def test_legacy_mode_fills_legacy_composite_and_leaves_swing_null(self):
        records = rcs.build_records([_stock(score=82.0)], swing_scoring_enabled=False)
        assert records[0]["legacy_composite"] == 82.0
        assert records[0]["swing_score"] is None
        assert records[0]["scoring_mode"] == "legacy"

    def test_combined_score_always_carries_the_live_value(self):
        swing = rcs.build_records([_stock(score=61.42)], swing_scoring_enabled=True)
        legacy = rcs.build_records([_stock(score=82.0)], swing_scoring_enabled=False)
        assert swing[0]["combined_score"] == 61.42
        assert legacy[0]["combined_score"] == 82.0


class TestUnscoredRowsAreNull:
    """dp_pct structural-zero guard at the source, not just in the loader."""

    @pytest.mark.parametrize("reason", ["tech_filter", "danger_zone"])
    def test_structurally_filtered_rows_have_null_scores(self, reason):
        stock = _stock(score=0.0, excluded=True, reason=reason)
        record = rcs.build_records([stock], swing_scoring_enabled=True)[0]
        assert record["scored"] is False
        assert record["combined_score"] is None
        assert record["swing_score"] is None
        assert record["legacy_composite"] is None

    def test_score_filtered_rows_keep_their_value(self):
        """A swing_score reject WAS scored — it just did not clear the threshold."""
        stock = _stock(score=-12.3, excluded=True, reason="swing_score")
        record = rcs.build_records([stock], swing_scoring_enabled=True)[0]
        assert record["scored"] is True
        assert record["swing_score"] == -12.3
        assert record["excluded"] is True
        assert record["exclusion_reason"] == "swing_score"

    def test_vetoed_but_scored_row_keeps_its_value(self):
        """The prod Reason-overwrite bug (04-risks §12.1) cannot reach this sink:
        veto status lives in its own field, the score is untouched."""
        records = rcs.build_records(
            [_stock(score=44.5)],
            sector_scores=[_sector_score(vetoed=True)],
            swing_scoring_enabled=True,
        )
        assert records[0]["sector_vetoed"] is True
        assert records[0]["swing_score"] == 44.5
        assert records[0]["scored"] is True


class TestCrossSectionCoverage:
    def test_every_analyzed_row_is_persisted_not_just_winners(self):
        analyzed = [
            _stock("AAA", score=61.0),
            _stock("BBB", score=-12.0, excluded=True, reason="swing_score"),
            _stock("CCC", score=0.0, excluded=True, reason="tech_filter"),
        ]
        records = rcs.build_records(analyzed, swing_scoring_enabled=True)
        assert [r["ticker"] for r in records] == ["AAA", "BBB", "CCC"]

    def test_raw_sub_components_are_present(self):
        """The whole point of the v2 lane: raw inputs, not just the composite."""
        record = rcs.build_records([_stock()], swing_scoring_enabled=True)[0]
        for field in ("pcr", "otm_call_ratio", "rvol", "dark_pool_pct", "rsi_14", "atr_14"):
            assert field in record, f"raw field {field} missing from the v2 record"
        assert record["pcr"] == 0.62
        assert record["otm_call_ratio"] == 0.31

    def test_sector_context_is_attached(self):
        records = rcs.build_records(
            [_stock()], sector_scores=[_sector_score()], swing_scoring_enabled=True
        )
        assert records[0]["sector_etf"] == "XLK"
        assert records[0]["sector_bmi"] == 55.0
        assert records[0]["sector_regime"] == "BULLISH"

    def test_missing_sector_score_does_not_crash(self):
        records = rcs.build_records([_stock(sector="Unknown")], sector_scores=[])
        assert "sector_etf" not in records[0]


class TestWriteAndLoad:
    def test_gzipped_payload_round_trips(self, tmp_path):
        path = rcs.write_cross_section(
            [_stock("AAA"), _stock("BBB", score=-4.0, excluded=True, reason="swing_score")],
            sector_scores=[_sector_score()],
            swing_scoring_enabled=True,
            output_dir=str(tmp_path),
            trading_date="2026-07-22",
        )
        assert path.name == "2026-07-22.json.gz"

        loaded = rcs.load_cross_section("2026-07-22", output_dir=str(tmp_path))
        assert loaded["schema_version"] == rcs.SCHEMA_VERSION
        assert loaded["trading_date"] == "2026-07-22"
        assert loaded["scoring_mode"] == "swing"
        assert loaded["n_rows"] == 2
        assert loaded["n_scored"] == 2
        assert loaded["captured_at"]
        assert len(loaded["records"]) == 2

    def test_n_scored_excludes_structurally_filtered_rows(self, tmp_path):
        rcs.write_cross_section(
            [_stock("AAA"), _stock("CCC", score=0.0, excluded=True, reason="tech_filter")],
            output_dir=str(tmp_path),
            trading_date="2026-07-22",
        )
        loaded = rcs.load_cross_section("2026-07-22", output_dir=str(tmp_path))
        assert loaded["n_rows"] == 2
        assert loaded["n_scored"] == 1

    def test_file_is_actually_gzipped(self, tmp_path):
        rcs.write_cross_section([_stock()], output_dir=str(tmp_path), trading_date="2026-07-22")
        with gzip.open(tmp_path / "2026-07-22.json.gz", "rt") as fh:
            assert json.load(fh)["n_rows"] == 1

    def test_write_is_atomic_no_temp_files_left(self, tmp_path):
        rcs.write_cross_section([_stock()], output_dir=str(tmp_path), trading_date="2026-07-22")
        assert list(tmp_path.glob("*.tmp")) == []

    def test_missing_file_loads_as_none(self, tmp_path):
        assert rcs.load_cross_section("2026-01-01", output_dir=str(tmp_path)) is None

    def test_empty_analyzed_list_writes_a_valid_empty_file(self, tmp_path):
        rcs.write_cross_section([], output_dir=str(tmp_path), trading_date="2026-07-22")
        loaded = rcs.load_cross_section("2026-07-22", output_dir=str(tmp_path))
        assert loaded["n_rows"] == 0
        assert loaded["records"] == []


class TestSinkIsGuarded:
    """A sink failure must never stop a trading pipeline run."""

    def test_runner_wraps_the_sink_in_try_except(self):
        from pathlib import Path

        src = (
            Path(__file__).resolve().parents[1] / "src" / "ifds" / "pipeline" / "runner.py"
        ).read_text()
        call_index = src.index("write_cross_section(")
        preceding = src[max(0, call_index - 600) : call_index]
        assert "try:" in preceding, "the sink call must sit inside a try/except"

    def test_write_failure_surfaces_as_an_exception_not_silent_success(self, tmp_path):
        """The writer itself fails loudly; the runner is what swallows it."""
        target = tmp_path / "not_a_dir"
        target.write_text("blocking file")
        with pytest.raises(OSError):
            rcs.write_cross_section([_stock()], output_dir=str(target))
