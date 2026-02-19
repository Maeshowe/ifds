"""Tests for AGG benchmark in Telegram sector table.

Verifies that _format_sector_table includes the AGG benchmark row
when provided, and omits it when None.
"""

from ifds.models.market import (
    SectorBreadth,
    SectorScore,
    SectorTrend,
    SectorBMIRegime,
    MomentumClassification,
    BreadthRegime,
)
from ifds.output.telegram import _format_sector_table


def _make_sector(etf="XLK", name="Technology", momentum=1.5):
    """Minimal SectorScore for testing."""
    return SectorScore(
        etf=etf,
        sector_name=name,
        momentum_5d=momentum,
        trend=SectorTrend.UP,
        classification=MomentumClassification.LEADER,
        sector_bmi=55.0,
        sector_bmi_regime=SectorBMIRegime.OVERBOUGHT,
        breadth=SectorBreadth(etf=etf, breadth_score=72.0,
                              breadth_regime=BreadthRegime.STRONG),
    )


def _make_agg_benchmark():
    """AGG benchmark SectorScore."""
    return SectorScore(
        etf="AGG",
        sector_name="Bonds (Benchmark)",
        momentum_5d=-0.35,
        trend=SectorTrend.DOWN,
        classification=MomentumClassification.NEUTRAL,
        sector_bmi=48.0,
        sector_bmi_regime=SectorBMIRegime.NEUTRAL,
        breadth=SectorBreadth(etf="AGG", breadth_score=45.0,
                              breadth_regime=BreadthRegime.NEUTRAL),
    )


class TestSectorTableBenchmark:
    """Test _format_sector_table benchmark parameter."""

    def test_without_benchmark_no_agg_row(self):
        """When benchmark=None (default), AGG row does not appear."""
        sectors = [_make_sector("XLK", "Technology", 2.1),
                   _make_sector("XLF", "Financials", 0.8)]
        result = _format_sector_table(sectors)
        assert "AGG" not in result
        assert "Benchmark" not in result

    def test_with_benchmark_agg_row_appears(self):
        """When benchmark provided, AGG row appears after separator."""
        sectors = [_make_sector("XLK", "Technology", 2.1)]
        agg = _make_agg_benchmark()
        result = _format_sector_table(sectors, benchmark=agg)
        assert "AGG" in result
        assert "Benchmark" in result
        # Separator line before AGG
        assert "---" in result

    def test_benchmark_row_after_sectors(self):
        """AGG row comes after all sector rows."""
        sectors = [_make_sector("XLK", "Technology", 2.1)]
        agg = _make_agg_benchmark()
        result = _format_sector_table(sectors, benchmark=agg)
        lines = result.replace("<pre>", "").replace("</pre>", "").split("\n")
        # header, XLK row, separator, AGG row
        assert len(lines) == 4
        assert lines[-1].startswith("AGG")

    def test_benchmark_momentum_displayed(self):
        """AGG momentum value is formatted correctly."""
        sectors = [_make_sector()]
        agg = _make_agg_benchmark()
        result = _format_sector_table(sectors, benchmark=agg)
        assert "-0.35%" in result

    def test_benchmark_bmi_displayed(self):
        """AGG BMI and regime appear."""
        sectors = [_make_sector()]
        agg = _make_agg_benchmark()
        result = _format_sector_table(sectors, benchmark=agg)
        assert "48%" in result
        assert "NEUTRAL" in result

    def test_benchmark_no_breadth(self):
        """AGG without breadth shows N/A."""
        sectors = [_make_sector()]
        agg = SectorScore(
            etf="AGG",
            sector_name="Bonds (Benchmark)",
            momentum_5d=0.10,
            trend=SectorTrend.UP,
            classification=MomentumClassification.NEUTRAL,
            sector_bmi=50.0,
            sector_bmi_regime=SectorBMIRegime.NEUTRAL,
            breadth=None,
        )
        result = _format_sector_table(sectors, benchmark=agg)
        assert "AGG" in result
        assert "N/A" in result

    def test_existing_tests_unaffected_default_none(self):
        """Calling without benchmark param still works (backward compat)."""
        sectors = [_make_sector("XLK", "Technology", 1.0),
                   _make_sector("XLE", "Energy", -0.5)]
        result = _format_sector_table(sectors)
        assert "<pre>" in result
        assert "XLK" in result
        assert "XLE" in result
        assert "AGG" not in result
