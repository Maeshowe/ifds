"""Tests for output generation (execution_plan.csv)."""

import csv
import pytest

from ifds.events.logger import EventLogger
from ifds.models.market import PositionSizing
from ifds.output.execution_plan import write_execution_plan, COLUMNS


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path / "logs"), run_id="test-output")


def _make_position(ticker="AAPL", direction="BUY", score=80.0):
    return PositionSizing(
        ticker=ticker, sector="Technology", direction=direction,
        entry_price=150.0, quantity=100, stop_loss=145.5,
        take_profit_1=156.0, take_profit_2=159.0,
        risk_usd=500.0, combined_score=score,
        gex_regime="POSITIVE", multiplier_total=1.0,
    )


class TestExecutionPlan:
    def test_csv_written_to_correct_path(self, tmp_path, logger):
        positions = [_make_position()]
        path = write_execution_plan(positions, str(tmp_path / "out"),
                                    "run_123", logger)
        assert "execution_plan_run_123.csv" in path
        assert (tmp_path / "out" / "execution_plan_run_123.csv").exists()

    def test_csv_columns_match_spec(self, tmp_path, logger):
        positions = [_make_position()]
        path = write_execution_plan(positions, str(tmp_path), "test", logger)

        with open(path) as f:
            reader = csv.DictReader(f)
            assert list(reader.fieldnames) == COLUMNS

    def test_csv_sorted_by_score_descending(self, tmp_path, logger):
        positions = [
            _make_position("LOW", score=60.0),
            _make_position("HIGH", score=90.0),
            _make_position("MID", score=75.0),
        ]
        # Pre-sort (as run_phase6 would)
        positions.sort(key=lambda p: p.combined_score, reverse=True)
        path = write_execution_plan(positions, str(tmp_path), "test", logger)

        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert rows[0]["instrument_id"] == "HIGH"
            assert rows[1]["instrument_id"] == "MID"
            assert rows[2]["instrument_id"] == "LOW"

    def test_csv_direction_values(self, tmp_path, logger):
        positions = [
            _make_position("LONG", direction="BUY"),
            _make_position("SHORT", direction="SELL_SHORT"),
        ]
        path = write_execution_plan(positions, str(tmp_path), "test", logger)

        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert rows[0]["direction"] == "BUY"
            assert rows[1]["direction"] == "SELL_SHORT"

    def test_csv_order_type_always_limit(self, tmp_path, logger):
        positions = [_make_position(), _make_position("MSFT")]
        path = write_execution_plan(positions, str(tmp_path), "test", logger)

        with open(path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                assert row["order_type"] == "LIMIT"

    def test_empty_positions_writes_header(self, tmp_path, logger):
        path = write_execution_plan([], str(tmp_path), "test", logger)

        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 0
            assert list(reader.fieldnames) == COLUMNS
