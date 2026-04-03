"""Tests for Pipeline Split (BC20A Phase_20A_3).

Covers:
- _should_run with range tuples
- parse_phase_range
- Context persistence (save/load round-trip)
"""

import gzip
import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from ifds.pipeline.runner import _should_run, parse_phase_range


class TestShouldRun:

    def test_none_runs_all(self):
        for i in range(7):
            assert _should_run(None, i) is True

    def test_single_phase(self):
        assert _should_run(3, 3) is True
        assert _should_run(3, 4) is False

    def test_range_tuple(self):
        assert _should_run((1, 3), 0) is False
        assert _should_run((1, 3), 1) is True
        assert _should_run((1, 3), 2) is True
        assert _should_run((1, 3), 3) is True
        assert _should_run((1, 3), 4) is False

    def test_range_4_6(self):
        assert _should_run((4, 6), 3) is False
        assert _should_run((4, 6), 4) is True
        assert _should_run((4, 6), 5) is True
        assert _should_run((4, 6), 6) is True

    def test_single_range(self):
        """Range (3, 3) = only phase 3."""
        assert _should_run((3, 3), 2) is False
        assert _should_run((3, 3), 3) is True
        assert _should_run((3, 3), 4) is False


class TestParsePhaseRange:

    def test_range(self):
        assert parse_phase_range("1-3") == (1, 3)
        assert parse_phase_range("4-6") == (4, 6)

    def test_single(self):
        assert parse_phase_range("3") == (3, 3)

    def test_full_range(self):
        assert parse_phase_range("0-6") == (0, 6)

    def test_invalid_range(self):
        with pytest.raises(ValueError):
            parse_phase_range("5-2")  # start > end

    def test_out_of_bounds(self):
        with pytest.raises(ValueError):
            parse_phase_range("0-7")


class TestContextPersistence:

    def test_save_and_load_round_trip(self, tmp_path):
        from ifds.models.market import (
            BMIRegime,
            MacroRegime,
            MarketVolatilityRegime,
            MomentumClassification,
            SectorBMIRegime,
            SectorScore,
            StrategyMode,
            Ticker,
        )
        from ifds.pipeline.context_persistence import (
            load_phase13_context,
            save_phase13_context,
        )

        # Minimal mock context
        @dataclass
        class FakeCtx:
            macro: MacroRegime | None = None
            strategy_mode: StrategyMode | None = None
            bmi_regime: BMIRegime | None = None
            bmi_value: float | None = None
            sector_bmi_values: dict = field(default_factory=dict)
            universe: list = field(default_factory=list)
            sector_scores: list = field(default_factory=list)
            vetoed_sectors: list = field(default_factory=list)
            agg_benchmark: object = None
            uw_available: bool = False

        ctx = FakeCtx(
            macro=MacroRegime(
                vix_value=25.0,
                vix_regime=MarketVolatilityRegime.ELEVATED,
                vix_multiplier=0.90,
                tnx_value=4.5,
                tnx_sma20=4.3,
                tnx_rate_sensitive=True,
            ),
            strategy_mode=StrategyMode.LONG,
            bmi_regime=BMIRegime.YELLOW,
            bmi_value=52.0,
            universe=[Ticker(symbol="AAPL", sector="Technology")],
            sector_scores=[SectorScore(
                etf="XLK", sector_name="Technology",
                momentum_5d=1.5,
                score_adjustment=15,
                classification=MomentumClassification.LEADER,
                sector_bmi=55.0,
                sector_bmi_regime=SectorBMIRegime.NEUTRAL,
            )],
            vetoed_sectors=["Real Estate"],
            uw_available=True,
        )

        path = str(tmp_path / "ctx.json.gz")
        save_phase13_context(ctx, path)
        assert Path(path).exists()

        # Load into fresh context
        ctx2 = FakeCtx()
        result = load_phase13_context(ctx2, path)
        assert result is True

        assert ctx2.macro.vix_value == 25.0
        assert ctx2.macro.vix_multiplier == 0.90
        assert ctx2.strategy_mode == StrategyMode.LONG
        assert ctx2.bmi_value == 52.0
        assert len(ctx2.universe) == 1
        assert ctx2.universe[0].symbol == "AAPL"
        assert len(ctx2.sector_scores) == 1
        assert ctx2.sector_scores[0].sector_name == "Technology"
        assert ctx2.vetoed_sectors == ["Real Estate"]
        assert ctx2.uw_available is True

    def test_load_missing_file(self, tmp_path):
        from ifds.pipeline.context_persistence import load_phase13_context

        @dataclass
        class FakeCtx:
            macro: object = None

        ctx = FakeCtx()
        assert load_phase13_context(ctx, str(tmp_path / "missing.json.gz")) is False
