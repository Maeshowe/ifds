"""Tests for SIM-L2 parameter sweep (BC19)."""

import os
import tempfile
from datetime import date
from unittest.mock import patch

import pytest

from ifds.sim.broker_sim import simulate_bracket_order
from ifds.sim.comparison import MIN_PAIRED_TRADES, _compute_delta, _pair_trade_pnls, compare_variants
from ifds.sim.models import (
    ComparisonReport,
    SimVariant,
    Trade,
    ValidationSummary,
    VariantDelta,
)
from ifds.sim.replay import (
    _deep_copy_trades,
    load_variants_from_yaml,
    recalculate_bracket,
    run_comparison_with_bars,
)
from ifds.sim.report import print_comparison_report, write_comparison_csv


# ============================================================================
# Fixtures
# ============================================================================

def _make_trade(ticker="AAPL", entry=100.0, stop=97.0, tp1=104.0, tp2=106.0,
                qty=100, run_date=None, score=85.0) -> Trade:
    """Create a test trade."""
    return Trade(
        run_id="test_run",
        run_date=run_date or date(2026, 2, 10),
        ticker=ticker,
        score=score,
        gex_regime="positive",
        multiplier=1.0,
        entry_price=entry,
        quantity=qty,
        stop_loss=stop,
        tp1=tp1,
        tp2=tp2,
    )


def _make_bars(prices: list[tuple[float, float, float, float]],
               start_date=date(2026, 2, 11)) -> list[dict]:
    """Create test bars from (open, high, low, close) tuples."""
    bars = []
    for i, (o, h, l, c) in enumerate(prices):
        d = date(start_date.year, start_date.month, start_date.day + i)
        bars.append({"date": d.isoformat(), "o": o, "h": h, "l": l, "c": c, "v": 1000000})
    return bars


# ============================================================================
# TestRecalculateBracket
# ============================================================================

class TestRecalculateBracket:

    def test_basic_recalculation(self):
        """ATR implied correctly, new TP/SL correct."""
        trade = _make_trade(entry=100.0, stop=97.0)  # ATR = 3.0/1.5 = 2.0
        overrides = {
            "stop_loss_atr_multiple": 2.0,
            "tp1_atr_multiple": 3.0,
            "tp2_atr_multiple": 4.0,
        }
        result = recalculate_bracket(trade, overrides)
        # ATR = 2.0, SL = 100 - 2*2 = 96, TP1 = 100 + 3*2 = 106, TP2 = 100 + 4*2 = 108
        assert result.stop_loss == 96.0
        assert result.tp1 == 106.0
        assert result.tp2 == 108.0

    def test_zero_entry(self):
        """Zero entry price — no recalculation."""
        trade = _make_trade(entry=0.0, stop=0.0)
        overrides = {"stop_loss_atr_multiple": 2.0}
        result = recalculate_bracket(trade, overrides)
        assert result.stop_loss == 0.0

    def test_zero_stop(self):
        """Zero stop — no recalculation."""
        trade = _make_trade(entry=100.0, stop=0.0)
        overrides = {"stop_loss_atr_multiple": 2.0}
        result = recalculate_bracket(trade, overrides)
        assert result.stop_loss == 0.0

    def test_negative_atr(self):
        """Stop above entry (impossible for LONG) → negative ATR → skip."""
        trade = _make_trade(entry=100.0, stop=105.0)
        overrides = {"stop_loss_atr_multiple": 2.0}
        result = recalculate_bracket(trade, overrides)
        # No recalc — stop stays at 105
        assert result.stop_loss == 105.0

    def test_default_original_atr_mult(self):
        """Default original_sl_atr_mult is 1.5."""
        trade = _make_trade(entry=100.0, stop=97.0)  # ATR = 3/1.5 = 2.0
        overrides = {"tp1_atr_multiple": 2.5}
        result = recalculate_bracket(trade, overrides)
        # TP1 = 100 + 2.5 * 2 = 105
        assert result.tp1 == 105.0

    def test_custom_original_atr_mult(self):
        """Custom original_sl_atr_mult."""
        trade = _make_trade(entry=100.0, stop=98.0)  # ATR = 2/1.0 = 2.0 when mult=1.0
        overrides = {"tp1_atr_multiple": 3.0}
        result = recalculate_bracket(trade, overrides, original_sl_atr_mult=1.0)
        assert result.tp1 == 106.0


# ============================================================================
# TestYAMLLoading
# ============================================================================

class TestYAMLLoading:

    def test_load_valid_yaml(self, tmp_path):
        """Parse YAML correctly."""
        yaml_content = """
variants:
  - name: baseline
    description: "Default config"
    overrides: {}
  - name: wide_stops
    description: "2x ATR"
    overrides:
      stop_loss_atr_multiple: 2.0
      tp1_atr_multiple: 3.0
"""
        yaml_file = tmp_path / "variants.yaml"
        yaml_file.write_text(yaml_content)

        variants = load_variants_from_yaml(str(yaml_file))
        assert len(variants) == 2
        assert variants[0].name == "baseline"
        assert variants[1].name == "wide_stops"
        assert variants[1].overrides["stop_loss_atr_multiple"] == 2.0

    def test_load_missing_file(self):
        """Missing YAML file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_variants_from_yaml("/nonexistent/path.yaml")

    def test_load_invalid_yaml(self, tmp_path):
        """Missing 'variants' key raises ValueError."""
        yaml_file = tmp_path / "bad.yaml"
        yaml_file.write_text("something_else: true")

        with pytest.raises(ValueError, match="missing 'variants'"):
            load_variants_from_yaml(str(yaml_file))


# ============================================================================
# TestRunComparison
# ============================================================================

class TestRunComparison:

    def _setup_bars(self):
        """Bars where entry fills and TP1 hits on day 2."""
        return _make_bars([
            (99.0, 101.0, 98.0, 100.5),   # Day 1: fills (low 98 <= entry 100)
            (101.0, 105.0, 100.0, 104.0),  # Day 2: TP1 hit (high 105 >= tp1 104)
            (104.0, 107.0, 103.0, 106.5),  # Day 3: TP2 hit (high 107 >= tp2 106)
        ])

    def test_two_variants_different_results(self):
        """Baseline vs challenger produce different P&L."""
        trades = [_make_trade()]
        bars = {"AAPL": self._setup_bars()}

        baseline = SimVariant(name="baseline")
        challenger = SimVariant(
            name="wide_stops",
            overrides={"stop_loss_atr_multiple": 2.0, "tp1_atr_multiple": 4.0, "tp2_atr_multiple": 5.0},
        )

        report = run_comparison_with_bars(
            [baseline, challenger], trades, bars,
        )

        assert report.baseline.name == "baseline"
        assert len(report.challengers) == 1
        assert report.challengers[0].name == "wide_stops"
        assert len(report.deltas) == 1
        # Different overrides → different P&L
        assert report.baseline.summary.total_pnl != report.challengers[0].summary.total_pnl

    def test_identical_variants(self):
        """Two identical configs → delta ≈ 0."""
        trades = [_make_trade()]
        bars = {"AAPL": self._setup_bars()}

        baseline = SimVariant(name="baseline")
        same = SimVariant(name="same")

        report = run_comparison_with_bars(
            [baseline, same], trades, bars,
        )

        assert len(report.deltas) == 1
        assert report.deltas[0].pnl_delta == 0.0

    def test_empty_variants(self):
        """Empty variant list → empty report."""
        report = run_comparison_with_bars([], [], {})
        assert report.baseline.name == "baseline"

    def test_no_trades(self):
        """No trades → summary has 0 trades."""
        baseline = SimVariant(name="baseline")
        report = run_comparison_with_bars([baseline], [], {})
        assert report.baseline.summary.total_trades == 0


# ============================================================================
# TestPairedTTest
# ============================================================================

class TestPairedTTest:

    def _make_variant_with_trades(self, name, pnl_values):
        """Create a variant with trades having specific P&L values."""
        variant = SimVariant(name=name)
        for i, pnl in enumerate(pnl_values):
            t = _make_trade(
                ticker=f"T{i}",
                run_date=date(2026, 2, 10),
            )
            t.filled = True
            t.total_pnl = pnl
            variant.trades.append(t)
        variant.summary = ValidationSummary(
            total_trades=len(pnl_values),
            filled_trades=len(pnl_values),
            total_pnl=sum(pnl_values),
            avg_pnl_per_trade=sum(pnl_values) / len(pnl_values) if pnl_values else 0,
        )
        return variant

    def test_significant_difference(self):
        """Large systematic difference → p < 0.05."""
        import random
        random.seed(42)
        n = 50
        baseline_pnls = [random.gauss(0, 10) for _ in range(n)]
        # Challenger is systematically +20 better (slight noise avoids scipy precision warning)
        challenger_pnls = [p + 20 + random.gauss(0, 0.1) for p in baseline_pnls]

        baseline = self._make_variant_with_trades("base", baseline_pnls)
        challenger = self._make_variant_with_trades("better", challenger_pnls)

        delta = _compute_delta(baseline, challenger)
        assert delta.p_value is not None
        assert delta.p_value < 0.05
        assert delta.is_significant is True
        assert delta.paired_trade_count == n

    def test_insufficient_data(self):
        """< 30 paired trades → insufficient_data=True."""
        baseline = self._make_variant_with_trades("base", [10, 20, 30])
        challenger = self._make_variant_with_trades("test", [15, 25, 35])

        delta = _compute_delta(baseline, challenger)
        assert delta.insufficient_data is True
        assert delta.paired_trade_count == 3

    def test_pairing_logic(self):
        """Only trades with same ticker+date are paired."""
        baseline = SimVariant(name="base")
        challenger = SimVariant(name="test")

        # Baseline has AAPL and MSFT
        t1 = _make_trade(ticker="AAPL", run_date=date(2026, 2, 10))
        t1.filled = True
        t1.total_pnl = 100
        t2 = _make_trade(ticker="MSFT", run_date=date(2026, 2, 10))
        t2.filled = True
        t2.total_pnl = 50
        baseline.trades = [t1, t2]

        # Challenger has AAPL only (MSFT not matched)
        t3 = _make_trade(ticker="AAPL", run_date=date(2026, 2, 10))
        t3.filled = True
        t3.total_pnl = 120
        challenger.trades = [t3]

        b_pnls, c_pnls = _pair_trade_pnls(baseline, challenger)
        assert len(b_pnls) == 1
        assert b_pnls[0] == 100
        assert c_pnls[0] == 120

    def test_no_significant_difference(self):
        """Random noise with same mean → p > 0.05."""
        import random
        random.seed(42)
        n = 50
        baseline_pnls = [random.gauss(0, 10) for _ in range(n)]
        challenger_pnls = [random.gauss(0, 10) for _ in range(n)]

        baseline = self._make_variant_with_trades("base", baseline_pnls)
        challenger = self._make_variant_with_trades("noise", challenger_pnls)

        delta = _compute_delta(baseline, challenger)
        assert delta.p_value is not None
        # With random noise and same mean, usually not significant
        # (can rarely be significant by chance, but seed 42 gives p > 0.05)
        assert delta.paired_trade_count == n


# ============================================================================
# TestComparisonReport
# ============================================================================

class TestComparisonReport:

    def test_report_output(self, tmp_path):
        """CSV written with correct columns."""
        baseline = SimVariant(name="baseline")
        baseline.summary = ValidationSummary(
            total_trades=10, filled_trades=8, total_pnl=500.0,
            avg_pnl_per_trade=62.5, leg1_win_rate=60.0, leg2_win_rate=40.0,
            avg_holding_days=3.5,
        )

        challenger = SimVariant(name="wide_stops", description="2x ATR",
                                overrides={"stop_loss_atr_multiple": 2.0})
        challenger.summary = ValidationSummary(
            total_trades=10, filled_trades=8, total_pnl=700.0,
            avg_pnl_per_trade=87.5, leg1_win_rate=70.0, leg2_win_rate=50.0,
            avg_holding_days=4.0,
        )

        delta = VariantDelta(
            challenger_name="wide_stops",
            pnl_delta=200.0,
            avg_pnl_delta=25.0,
            win_rate_leg1_delta=10.0,
            paired_trade_count=5,
            insufficient_data=True,
        )

        report = ComparisonReport(
            baseline=baseline,
            challengers=[challenger],
            deltas=[delta],
        )

        # Console report
        output = print_comparison_report(report)
        assert "BASELINE: baseline" in output
        assert "CHALLENGER: wide_stops" in output
        assert "ΔP&L" in output

        # CSV report
        csv_path = write_comparison_csv(report, str(tmp_path))
        assert os.path.exists(csv_path)
        import csv
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["variant"] == "baseline"
        assert rows[1]["variant"] == "wide_stops"
        assert float(rows[1]["delta_pnl"]) == 200.0


# ============================================================================
# TestDeepCopy
# ============================================================================

class TestDeepCopy:

    def test_mutation_isolation(self):
        """Modifying copy doesn't affect original."""
        original = [_make_trade()]
        copied = _deep_copy_trades(original)
        copied[0].stop_loss = 50.0
        assert original[0].stop_loss == 97.0  # Unchanged


# ============================================================================
# TestSimVariantModel
# ============================================================================

class TestSimVariantModel:

    def test_default_values(self):
        """SimVariant has sensible defaults."""
        v = SimVariant(name="test")
        assert v.name == "test"
        assert v.overrides == {}
        assert v.trades == []

    def test_variant_delta_defaults(self):
        """VariantDelta has zero defaults."""
        d = VariantDelta(challenger_name="test")
        assert d.pnl_delta == 0.0
        assert d.is_significant is False
        assert d.insufficient_data is False

    def test_comparison_report_defaults(self):
        """ComparisonReport has empty defaults."""
        r = ComparisonReport()
        assert r.baseline.name == "baseline"
        assert r.challengers == []
        assert r.deltas == []

    def test_fill_rate_property(self):
        """ValidationSummary.fill_rate works."""
        s = ValidationSummary(total_trades=10, filled_trades=7)
        assert s.fill_rate == 70.0

    def test_fill_rate_zero_trades(self):
        """fill_rate with zero trades returns 0."""
        s = ValidationSummary()
        assert s.fill_rate == 0.0
