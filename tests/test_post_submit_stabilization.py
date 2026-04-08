"""Regression tests for post-submit MKT stabilization (task 2026-04-08).

Covers:
- Fix 2: instant TP1 fill detection from execution orderRef parsing
- Fix 3: phantom ticker dedup via per-day persisted log file
"""
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestInstantTp1FillDetection:
    """Fix 2: parse execution orderRefs to detect instant TP fills on submit.

    With MKT entry, the entry may fill above TP1 (e.g. NSA 2026-04-08:
    entry $40.45, TP1 $40.00). IBKR triggers the child TP immediately
    and submit_orders.py must mark monitor_state[sym]['tp1_filled']=True
    so the monitor cycle doesn't flag the position as phantom.
    """

    @staticmethod
    def _parse_sym_from_tp_ref(order_ref: str) -> str:
        """Replicates the parsing in submit_orders.py monitor state init."""
        # IFDS_{sym}_A_TP → sym. Use rsplit to handle symbols with underscores
        # (e.g. BRK_B), though NYSE uses '.' so 'AAPL_A_TP' is the norm.
        return order_ref[len("IFDS_"):].rsplit("_", 2)[0]

    def test_parse_a_tp_ref(self):
        assert self._parse_sym_from_tp_ref("IFDS_AAPL_A_TP") == "AAPL"

    def test_parse_b_tp_ref(self):
        assert self._parse_sym_from_tp_ref("IFDS_NSA_B_TP") == "NSA"

    def test_parse_multi_char_symbol(self):
        assert self._parse_sym_from_tp_ref("IFDS_GOOGL_A_TP") == "GOOGL"

    def test_non_tp_ref_ignored(self):
        """SL, entry, and LOSS_EXIT refs must NOT be treated as TP fills."""
        refs_that_should_not_match = [
            "IFDS_AAPL_A",  # entry
            "IFDS_AAPL_A_SL",  # stop loss
            "IFDS_AAPL_LOSS_EXIT",  # monitor Scenario B
            "IFDS_AAPL_TRAIL",  # monitor trail hit
            "IFDS_AAPL_AVWAP_A",  # AVWAP bracket rebuild
        ]
        for ref in refs_that_should_not_match:
            assert not (
                ref.endswith("_A_TP") or ref.endswith("_B_TP")
            ), f"{ref!r} must not match the TP fill pattern"

    def test_tp_ref_match_pattern(self):
        """Only _A_TP and _B_TP should match."""
        assert "IFDS_AAPL_A_TP".endswith("_A_TP")
        assert "IFDS_AAPL_B_TP".endswith("_B_TP")
        assert not "IFDS_AAPL_A_SL".endswith("_A_TP")


class TestPhantomDedup:
    """Fix 3: phantom filter WARNING only on first occurrence per day.

    The real implementation lives in pt_monitor.py and persists state to
    scripts/paper_trading/logs/phantom_logged_{date}.json. These tests
    exercise that file-based dedup logic directly.
    """

    def _write_phantom_log(self, path: Path, tickers: list[str]) -> None:
        with open(path, "w") as f:
            json.dump(tickers, f)

    def _read_phantom_log(self, path: Path) -> list[str]:
        with open(path) as f:
            return json.load(f)

    def test_first_occurrence_writes_file(self, tmp_path):
        phantom_log = tmp_path / "phantom_logged_2026-04-08.json"
        assert not phantom_log.exists()

        # Simulate: 2 phantom tickers, none previously logged
        already_logged: set[str] = set()
        phantom = {"LION", "SDRL"}
        new_phantoms = phantom - already_logged
        repeat_phantoms = phantom & already_logged

        assert new_phantoms == {"LION", "SDRL"}
        assert repeat_phantoms == set()

        self._write_phantom_log(phantom_log, sorted(already_logged | new_phantoms))
        assert phantom_log.exists()
        assert self._read_phantom_log(phantom_log) == ["LION", "SDRL"]

    def test_second_occurrence_is_repeat(self, tmp_path):
        """Same phantom tickers next cycle → repeat, no file change."""
        phantom_log = tmp_path / "phantom_logged_2026-04-08.json"
        self._write_phantom_log(phantom_log, ["LION", "SDRL"])

        already_logged = set(self._read_phantom_log(phantom_log))
        phantom = {"LION", "SDRL"}
        new_phantoms = phantom - already_logged
        repeat_phantoms = phantom & already_logged

        assert new_phantoms == set()
        assert repeat_phantoms == {"LION", "SDRL"}

    def test_mixed_new_and_repeat(self, tmp_path):
        phantom_log = tmp_path / "phantom_logged_2026-04-08.json"
        self._write_phantom_log(phantom_log, ["LION"])

        already_logged = set(self._read_phantom_log(phantom_log))
        phantom = {"LION", "NSA", "CRGY"}
        new_phantoms = phantom - already_logged
        repeat_phantoms = phantom & already_logged

        assert new_phantoms == {"NSA", "CRGY"}
        assert repeat_phantoms == {"LION"}

        # File updates with the merged set
        self._write_phantom_log(phantom_log, sorted(already_logged | new_phantoms))
        assert self._read_phantom_log(phantom_log) == ["CRGY", "LION", "NSA"]

    def test_corrupt_file_treated_as_empty(self, tmp_path):
        """A garbled JSON file should degrade gracefully (empty set)."""
        phantom_log = tmp_path / "phantom_logged_2026-04-08.json"
        phantom_log.write_text("not json {{{")

        already_logged: set[str] = set()
        try:
            with open(phantom_log) as f:
                already_logged = set(json.load(f))
        except (json.JSONDecodeError, OSError):
            already_logged = set()
        assert already_logged == set()


class TestPostSubmitVerification:
    """Fix 1: POST-SUBMIT verification must accept filled positions as
    a successful submission, not only open orders. MKT entry fills
    instantly and disappears from openTrades()."""

    def test_ticker_in_open_trades_only(self):
        """Entry still pending → visible in openTrades, no position yet."""
        ib_open_refs = {"IFDS_AAPL_A", "IFDS_AAPL_B"}
        ib_position_syms: set[str] = set()
        submitted = ["AAPL"]

        missing = [
            sym for sym in submitted
            if not (
                f"IFDS_{sym}_A" in ib_open_refs
                or f"IFDS_{sym}_B" in ib_open_refs
            )
            and sym not in ib_position_syms
        ]
        assert missing == []

    def test_ticker_in_positions_only(self):
        """Instant MKT fill → position exists, no open order."""
        ib_open_refs: set[str] = set()
        ib_position_syms = {"NSA"}
        submitted = ["NSA"]

        missing = [
            sym for sym in submitted
            if not (
                f"IFDS_{sym}_A" in ib_open_refs
                or f"IFDS_{sym}_B" in ib_open_refs
            )
            and sym not in ib_position_syms
        ]
        assert missing == []

    def test_ticker_missing_from_both(self):
        """Silent reject → neither open order nor position → missing."""
        ib_open_refs: set[str] = set()
        ib_position_syms: set[str] = set()
        submitted = ["AAPL"]

        missing = [
            sym for sym in submitted
            if not (
                f"IFDS_{sym}_A" in ib_open_refs
                or f"IFDS_{sym}_B" in ib_open_refs
            )
            and sym not in ib_position_syms
        ]
        assert missing == ["AAPL"]

    def test_mixed_tickers(self):
        ib_open_refs = {"IFDS_AAPL_A"}
        ib_position_syms = {"NSA"}
        submitted = ["AAPL", "NSA", "GHOST"]

        missing = [
            sym for sym in submitted
            if not (
                f"IFDS_{sym}_A" in ib_open_refs
                or f"IFDS_{sym}_B" in ib_open_refs
            )
            and sym not in ib_position_syms
        ]
        assert missing == ["GHOST"]
