"""Tests for SIM-L1: Forward validation engine with bracket order simulation."""

import csv
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from ifds.sim.broker_sim import compute_qty_split, simulate_bracket_order
from ifds.sim.models import Trade, ValidationSummary
from ifds.sim.report import write_validation_trades, write_validation_summary
from ifds.sim.validator import (
    aggregate_summary,
    load_execution_plans,
    validate_trades_with_bars,
    _parse_run_date,
)


# ============================================================================
# Helpers
# ============================================================================

def _make_trade(ticker="AAPL", entry=100.0, stop=95.0, tp1=108.0, tp2=115.0,
                qty=100, score=85.0, gex_regime="positive",
                run_date=None, direction="BUY") -> Trade:
    """Create a test trade with sensible defaults."""
    if run_date is None:
        run_date = date(2026, 2, 1)
    qty_tp1, qty_tp2 = compute_qty_split(qty)
    return Trade(
        run_id="run_20260201_120000_abc123",
        run_date=run_date,
        ticker=ticker,
        score=score,
        gex_regime=gex_regime,
        multiplier=1.2,
        entry_price=entry,
        quantity=qty,
        direction=direction,
        stop_loss=stop,
        tp1=tp1,
        tp2=tp2,
        qty_tp1=qty_tp1,
        qty_tp2=qty_tp2,
    )


def _make_bars(days=10, start_date=None, base_price=100.0,
               daily_range=3.0, trend=0.0) -> list[dict]:
    """Create mock daily OHLCV bars.

    Args:
        days: Number of bars.
        start_date: First bar date.
        base_price: Starting close price.
        daily_range: H-L spread (symmetric around close).
        trend: Daily price drift.
    """
    if start_date is None:
        start_date = date(2026, 2, 2)  # Day after default run_date

    bars = []
    price = base_price
    for i in range(days):
        d = start_date + timedelta(days=i)
        # Skip weekends
        if d.weekday() >= 5:
            continue
        c = price + trend * i
        bars.append({
            "date": d.isoformat(),
            "o": c - 0.5,
            "h": c + daily_range / 2,
            "l": c - daily_range / 2,
            "c": c,
            "v": 1000000,
        })
    return bars


def _write_test_csv(tmp_path, run_id="run_20260201_120000_abc123",
                    rows=None) -> str:
    """Write a test execution_plan CSV."""
    file_path = tmp_path / f"execution_plan_{run_id}.csv"

    if rows is None:
        rows = [{
            "instrument_id": "AAPL",
            "direction": "BUY",
            "order_type": "LIMIT",
            "limit_price": "100.00",
            "quantity": "100",
            "stop_loss": "95.00",
            "take_profit_1": "108.00",
            "take_profit_2": "115.00",
            "risk_usd": "500.00",
            "score": "85.50",
            "gex_regime": "positive",
            "sector": "Technology",
            "multiplier_total": "1.2000",
            "mult_vix": "1.0000",
            "mult_utility": "1.1000",
            "sector_bmi": "45.00",
            "sector_regime": "neutral",
            "is_mean_reversion": "False",
        }]

    fieldnames = [
        "instrument_id", "direction", "order_type", "limit_price",
        "quantity", "stop_loss", "take_profit_1", "take_profit_2",
        "risk_usd", "score", "gex_regime", "sector", "multiplier_total",
        "mult_vix", "mult_utility", "sector_bmi", "sector_regime", "is_mean_reversion",
    ]

    with open(file_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    return str(tmp_path)


# ============================================================================
# test_bracket_fill_on_day1
# ============================================================================

class TestBracketFill:
    def test_bracket_fill_on_day1(self):
        """Low <= entry on D+1 -> filled @ entry price."""
        trade = _make_trade(entry=100.0)
        # Day 1 low = 98.5 (below entry 100) -> fill
        bars = _make_bars(days=12, base_price=99.0, daily_range=3.0)

        result = simulate_bracket_order(trade, bars)

        assert result.filled is True
        assert result.fill_price == 100.0
        assert result.fill_date is not None

    def test_bracket_no_fill(self):
        """Low > entry on all days within fill window -> unfilled."""
        trade = _make_trade(entry=90.0)  # Entry at 90, but bars start at 100+
        bars = _make_bars(days=12, base_price=105.0, daily_range=3.0)
        # Lowest bar: 105 - 1.5 = 103.5 > 90? No wait, 105-1.5=103.5.
        # Actually entry=90, bars have low ~103.5 → never fills
        result = simulate_bracket_order(trade, bars, fill_window_days=1)

        assert result.filled is False
        assert result.fill_date is None
        assert result.total_pnl == 0.0


# ============================================================================
# test_tp1_hit_before_stop / test_stop_hit_before_tp1
# ============================================================================

class TestLegExits:
    def test_tp1_hit_before_stop(self):
        """High >= TP1 before stop -> leg1 win."""
        trade = _make_trade(entry=100.0, stop=95.0, tp1=105.0, tp2=110.0)
        # Fill bar: low=98.5 < 100 -> fill
        # Then bars trend up: close goes to 106 -> high reaches 107.5 > TP1(105)
        bars = [
            {"date": "2026-02-02", "o": 99.5, "h": 101.0, "l": 98.5, "c": 100.0, "v": 1e6},  # Fill
            {"date": "2026-02-03", "o": 101.0, "h": 103.0, "l": 100.0, "c": 102.0, "v": 1e6},
            {"date": "2026-02-04", "o": 102.0, "h": 106.0, "l": 101.0, "c": 105.5, "v": 1e6},  # TP1 hit
        ]

        result = simulate_bracket_order(trade, bars)

        assert result.filled is True
        assert result.leg1_exit_reason == "tp1"
        assert result.leg1_exit_price == 105.0
        assert result.leg1_pnl > 0

    def test_stop_hit_before_tp1(self):
        """Low <= stop before TP1 -> leg1 loss."""
        trade = _make_trade(entry=100.0, stop=95.0, tp1=108.0, tp2=115.0)
        bars = [
            {"date": "2026-02-02", "o": 99.5, "h": 101.0, "l": 98.5, "c": 100.0, "v": 1e6},  # Fill
            {"date": "2026-02-03", "o": 99.0, "h": 100.0, "l": 94.0, "c": 95.0, "v": 1e6},   # Stop hit
        ]

        result = simulate_bracket_order(trade, bars)

        assert result.filled is True
        assert result.leg1_exit_reason == "stop"
        assert result.leg1_exit_price == 95.0
        assert result.leg1_pnl < 0


# ============================================================================
# test_same_day_tp_and_stop
# ============================================================================

class TestSameDayAmbiguity:
    def test_same_day_tp_and_stop(self):
        """Both TP and stop triggered same day -> conservative: stop."""
        trade = _make_trade(entry=100.0, stop=95.0, tp1=106.0, tp2=115.0)
        bars = [
            {"date": "2026-02-02", "o": 99.5, "h": 101.0, "l": 98.5, "c": 100.0, "v": 1e6},  # Fill
            # Day with both: high=107 >= TP1(106), low=94 <= stop(95)
            {"date": "2026-02-03", "o": 100.0, "h": 107.0, "l": 94.0, "c": 100.0, "v": 1e6},
        ]

        result = simulate_bracket_order(trade, bars)

        assert result.filled is True
        assert result.leg1_exit_reason == "stop"  # Conservative: stop wins
        assert result.leg1_exit_price == 95.0


# ============================================================================
# test_expired_no_exit
# ============================================================================

class TestExpired:
    def test_expired_no_exit(self):
        """10 days, neither TP nor stop hit -> expired @ close of last day."""
        trade = _make_trade(entry=100.0, stop=90.0, tp1=120.0, tp2=130.0)
        # Bars that fill but never reach TP or stop (tight range around 100)
        bars = [
            {"date": "2026-02-02", "o": 99.5, "h": 101.0, "l": 98.5, "c": 100.0, "v": 1e6},  # Fill
        ]
        # 10 more days of sideways (never reach stop=90 or tp1=120)
        for i in range(10):
            d = date(2026, 2, 3) + timedelta(days=i)
            if d.weekday() >= 5:
                continue
            bars.append({
                "date": d.isoformat(),
                "o": 100.0, "h": 102.0, "l": 98.0, "c": 101.0, "v": 1e6,
            })

        result = simulate_bracket_order(trade, bars, max_hold_days=10)

        assert result.filled is True
        assert result.leg1_exit_reason == "expired"
        assert result.leg2_exit_reason == "expired"
        # Expired at close of last bar
        assert result.leg1_exit_price == 101.0
        assert result.leg2_exit_price == 101.0


# ============================================================================
# test_leg1_tp1_leg2_stop — mixed P&L
# ============================================================================

class TestMixedPnL:
    def test_leg1_tp1_leg2_stop(self):
        """Leg1 hits TP1, Leg2 hits stop -> mixed P&L."""
        trade = _make_trade(entry=100.0, stop=95.0, tp1=105.0, tp2=115.0, qty=100)
        bars = [
            {"date": "2026-02-02", "o": 99.5, "h": 101.0, "l": 98.5, "c": 100.0, "v": 1e6},  # Fill
            # Day 2: TP1 hit (high=106 >= 105), but not TP2 (115), stop not hit
            {"date": "2026-02-03", "o": 101.0, "h": 106.0, "l": 99.0, "c": 104.0, "v": 1e6},
            # Day 3: Drop to stop (low=94 <= 95)
            {"date": "2026-02-04", "o": 103.0, "h": 104.0, "l": 94.0, "c": 95.0, "v": 1e6},
        ]

        result = simulate_bracket_order(trade, bars)

        assert result.filled is True
        assert result.leg1_exit_reason == "tp1"
        assert result.leg2_exit_reason == "stop"

        # Leg1: 33 shares * (105 - 100) = +165
        assert result.leg1_pnl == pytest.approx(33 * 5, abs=1)
        # Leg2: 67 shares * (95 - 100) = -335
        assert result.leg2_pnl == pytest.approx(67 * -5, abs=1)
        # Total: 165 - 335 = -170
        assert result.total_pnl == pytest.approx(result.leg1_pnl + result.leg2_pnl, abs=0.01)


# ============================================================================
# test_qty_split_33_66
# ============================================================================

class TestQtySplit:
    def test_qty_split_33_66(self):
        """qty_tp1 + qty_tp2 == quantity, with 33/66 split."""
        qty_tp1, qty_tp2 = compute_qty_split(100)
        assert qty_tp1 == 33
        assert qty_tp2 == 67
        assert qty_tp1 + qty_tp2 == 100

    def test_qty_split_small(self):
        """Small quantity: still sums correctly."""
        qty_tp1, qty_tp2 = compute_qty_split(3)
        assert qty_tp1 + qty_tp2 == 3

    def test_qty_split_one(self):
        """Quantity=1: one leg gets 0, other gets 1."""
        qty_tp1, qty_tp2 = compute_qty_split(1)
        assert qty_tp1 + qty_tp2 == 1


# ============================================================================
# test_multiple_csv_loading
# ============================================================================

class TestCSVLoading:
    def test_multiple_csv_loading(self, tmp_path):
        """Multiple execution_plan CSVs are loaded and merged."""
        # Plan 1: Feb 1
        _write_test_csv(tmp_path, run_id="run_20260201_120000_abc123",
                        rows=[{
                            "instrument_id": "AAPL", "direction": "BUY",
                            "order_type": "LIMIT", "limit_price": "100.00",
                            "quantity": "50", "stop_loss": "95.00",
                            "take_profit_1": "108.00", "take_profit_2": "115.00",
                            "risk_usd": "250.00", "score": "85.00",
                            "gex_regime": "positive", "sector": "Technology",
                            "multiplier_total": "1.2000",
                            "mult_vix": "1.0", "mult_utility": "1.1",
                            "sector_bmi": "45.00", "sector_regime": "neutral",
                            "is_mean_reversion": "False",
                        }])

        # Plan 2: Feb 3
        _write_test_csv(tmp_path, run_id="run_20260203_120000_def456",
                        rows=[{
                            "instrument_id": "MSFT", "direction": "BUY",
                            "order_type": "LIMIT", "limit_price": "350.00",
                            "quantity": "20", "stop_loss": "340.00",
                            "take_profit_1": "365.00", "take_profit_2": "380.00",
                            "risk_usd": "200.00", "score": "78.00",
                            "gex_regime": "high_vol", "sector": "Technology",
                            "multiplier_total": "0.9000",
                            "mult_vix": "0.8", "mult_utility": "1.0",
                            "sector_bmi": "50.00", "sector_regime": "neutral",
                            "is_mean_reversion": "False",
                        }])

        trades = load_execution_plans(str(tmp_path))
        assert len(trades) == 2
        tickers = {t.ticker for t in trades}
        assert tickers == {"AAPL", "MSFT"}
        assert trades[0].run_date == date(2026, 2, 1)
        assert trades[1].run_date == date(2026, 2, 3)

    def test_skip_today_csv(self, tmp_path):
        """CSVs from today are skipped (no post-plan data yet)."""
        today = date.today()
        run_id = f"run_{today.strftime('%Y%m%d')}_120000_abc123"
        _write_test_csv(tmp_path, run_id=run_id)

        trades = load_execution_plans(str(tmp_path))
        assert len(trades) == 0

    def test_empty_output_dir(self, tmp_path):
        """Empty output dir returns empty list."""
        trades = load_execution_plans(str(tmp_path))
        assert trades == []

    def test_nonexistent_dir(self):
        """Nonexistent dir returns empty list."""
        trades = load_execution_plans("/nonexistent/path")
        assert trades == []


# ============================================================================
# test_validation_summary_aggregation
# ============================================================================

class TestValidationSummaryAggregation:
    def test_summary_correct(self):
        """Summary aggregates trade results correctly."""
        trades = []
        # Trade 1: filled, leg1=tp1, leg2=stop
        t1 = _make_trade("AAPL", score=85.0, gex_regime="positive")
        t1.filled = True
        t1.fill_price = 100.0
        t1.fill_date = date(2026, 2, 2)
        t1.qty_tp1 = 33
        t1.qty_tp2 = 67
        t1.leg1_exit_reason = "tp1"
        t1.leg1_exit_price = 108.0
        t1.leg1_exit_date = date(2026, 2, 5)
        t1.leg1_pnl = 33 * 8  # +264
        t1.leg2_exit_reason = "stop"
        t1.leg2_exit_price = 95.0
        t1.leg2_exit_date = date(2026, 2, 4)
        t1.leg2_pnl = 67 * -5  # -335
        t1.total_pnl = t1.leg1_pnl + t1.leg2_pnl  # -71
        t1.total_pnl_pct = t1.total_pnl / (100 * 100) * 100
        t1.holding_days = 3
        trades.append(t1)

        # Trade 2: unfilled
        t2 = _make_trade("MSFT", score=72.0, gex_regime="high_vol")
        t2.filled = False
        trades.append(t2)

        # Trade 3: filled, both legs TP
        t3 = _make_trade("GOOG", score=92.0, gex_regime="positive")
        t3.filled = True
        t3.fill_price = 150.0
        t3.fill_date = date(2026, 2, 2)
        t3.qty_tp1 = 33
        t3.qty_tp2 = 67
        t3.leg1_exit_reason = "tp1"
        t3.leg1_exit_price = 158.0
        t3.leg1_exit_date = date(2026, 2, 4)
        t3.leg1_pnl = 33 * 8  # +264
        t3.leg2_exit_reason = "tp2"
        t3.leg2_exit_price = 165.0
        t3.leg2_exit_date = date(2026, 2, 6)
        t3.leg2_pnl = 67 * 15  # +1005
        t3.total_pnl = t3.leg1_pnl + t3.leg2_pnl  # +1269
        t3.total_pnl_pct = t3.total_pnl / (100 * 150) * 100
        t3.holding_days = 4
        trades.append(t3)

        summary = aggregate_summary(trades)

        assert summary.total_trades == 3
        assert summary.filled_trades == 2
        assert summary.unfilled_trades == 1

        assert summary.leg1_tp_hits == 2
        assert summary.leg1_stop_hits == 0
        assert summary.leg1_win_rate == 100.0  # 2/2

        assert summary.leg2_tp_hits == 1
        assert summary.leg2_stop_hits == 1
        assert summary.leg2_win_rate == 50.0  # 1/2

        assert summary.total_pnl == pytest.approx(t1.total_pnl + t3.total_pnl, abs=0.01)
        assert summary.best_trade_ticker == "GOOG"
        assert summary.worst_trade_ticker == "AAPL"
        assert summary.avg_holding_days == 3.5  # (3+4)/2

    def test_empty_trades(self):
        """Empty trade list produces zero summary."""
        summary = aggregate_summary([])
        assert summary.total_trades == 0
        assert summary.filled_trades == 0


# ============================================================================
# test_pnl_by_gex_regime
# ============================================================================

class TestPnlByGexRegime:
    def test_gex_regime_breakdown(self):
        """GEX regime breakdown correctly groups trades."""
        t1 = _make_trade("A", gex_regime="positive")
        t1.filled = True
        t1.fill_price = 100.0
        t1.total_pnl = 200.0

        t2 = _make_trade("B", gex_regime="positive")
        t2.filled = True
        t2.fill_price = 100.0
        t2.total_pnl = -50.0

        t3 = _make_trade("C", gex_regime="high_vol")
        t3.filled = True
        t3.fill_price = 100.0
        t3.total_pnl = 100.0

        summary = aggregate_summary([t1, t2, t3])

        assert "positive" in summary.pnl_by_gex_regime
        assert summary.pnl_by_gex_regime["positive"]["trades"] == 2
        assert summary.pnl_by_gex_regime["positive"]["pnl"] == 150.0  # 200 - 50
        assert summary.pnl_by_gex_regime["positive"]["win_rate"] == 50.0  # 1/2

        assert "high_vol" in summary.pnl_by_gex_regime
        assert summary.pnl_by_gex_regime["high_vol"]["trades"] == 1
        assert summary.pnl_by_gex_regime["high_vol"]["win_rate"] == 100.0


# ============================================================================
# test_score_bucket_win_rate
# ============================================================================

class TestScoreBucketWinRate:
    def test_score_buckets(self):
        """Score buckets correctly classify and compute win rates."""
        t1 = _make_trade("A", score=92.0)
        t1.filled = True
        t1.fill_price = 100.0
        t1.total_pnl = 500.0

        t2 = _make_trade("B", score=83.0)
        t2.filled = True
        t2.fill_price = 100.0
        t2.total_pnl = -100.0

        t3 = _make_trade("C", score=75.0)
        t3.filled = True
        t3.fill_price = 100.0
        t3.total_pnl = 50.0

        t4 = _make_trade("D", score=71.0)
        t4.filled = True
        t4.fill_price = 100.0
        t4.total_pnl = -30.0

        summary = aggregate_summary([t1, t2, t3, t4])

        assert summary.win_rate_by_score_bucket["90+"] == 100.0  # 1/1
        assert summary.win_rate_by_score_bucket["80-90"] == 0.0   # 0/1
        assert summary.win_rate_by_score_bucket["70-80"] == 50.0   # 1/2


# ============================================================================
# test_report_output
# ============================================================================

class TestReportOutput:
    def test_write_trades_csv(self, tmp_path):
        """Validation trades CSV is written correctly."""
        trade = _make_trade("AAPL")
        trade.filled = True
        trade.fill_price = 100.0
        trade.fill_date = date(2026, 2, 2)
        trade.leg1_exit_reason = "tp1"
        trade.leg1_exit_price = 108.0
        trade.leg1_pnl = 264.0
        trade.total_pnl = 264.0

        path = write_validation_trades([trade], str(tmp_path))
        assert Path(path).exists()

        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["ticker"] == "AAPL"
        assert rows[0]["filled"] == "True"

    def test_write_summary_json(self, tmp_path):
        """Validation summary JSON is written correctly."""
        summary = ValidationSummary(
            total_trades=10, filled_trades=8, unfilled_trades=2,
            total_pnl=1500.0, avg_pnl_per_trade=187.5,
            plan_count=3,
        )

        path = write_validation_summary(summary, str(tmp_path))
        assert Path(path).exists()

        with open(path) as f:
            data = json.load(f)
        assert data["total_trades"] == 10
        assert data["pnl"]["total"] == 1500.0
        assert data["plan_count"] == 3


# ============================================================================
# test_validate_trades_with_bars (integration without Polygon)
# ============================================================================

class TestValidateWithBars:
    def test_full_flow(self):
        """Full validation flow with pre-provided bars."""
        trades = [
            _make_trade("AAPL", entry=100.0, stop=95.0, tp1=105.0, tp2=110.0, qty=100),
            _make_trade("MSFT", entry=350.0, stop=340.0, tp1=360.0, tp2=370.0, qty=20),
        ]

        # AAPL: fills, hits TP1 on day 3
        aapl_bars = [
            {"date": "2026-02-02", "o": 99.5, "h": 101.0, "l": 98.5, "c": 100.0, "v": 1e6},
            {"date": "2026-02-03", "o": 101.0, "h": 103.0, "l": 100.0, "c": 102.0, "v": 1e6},
            {"date": "2026-02-04", "o": 102.0, "h": 106.0, "l": 101.0, "c": 105.0, "v": 1e6},
            {"date": "2026-02-05", "o": 105.0, "h": 111.0, "l": 104.0, "c": 110.5, "v": 1e6},
        ]

        # MSFT: fills, hits stop
        msft_bars = [
            {"date": "2026-02-02", "o": 349.0, "h": 351.0, "l": 348.0, "c": 350.0, "v": 1e6},
            {"date": "2026-02-03", "o": 348.0, "h": 349.0, "l": 339.0, "c": 340.0, "v": 1e6},
        ]

        bars_by_ticker = {"AAPL": aapl_bars, "MSFT": msft_bars}
        result_trades, summary = validate_trades_with_bars(trades, bars_by_ticker)

        assert len(result_trades) == 2
        assert summary.filled_trades == 2

        aapl = next(t for t in result_trades if t.ticker == "AAPL")
        assert aapl.filled is True
        assert aapl.leg1_exit_reason == "tp1"

        msft = next(t for t in result_trades if t.ticker == "MSFT")
        assert msft.filled is True
        assert msft.leg1_exit_reason == "stop"


# ============================================================================
# test_parse_run_date
# ============================================================================

class TestParseRunDate:
    def test_valid_run_id(self):
        assert _parse_run_date("run_20260201_120000_abc123") == date(2026, 2, 1)

    def test_invalid_run_id(self):
        assert _parse_run_date("invalid_run_id") is None

    def test_bad_date(self):
        assert _parse_run_date("run_20261301_120000_abc123") is None  # Month 13
