"""Tests — Task #T §3.5 LEFTOVER swing-aware refactor.

Pure-function tests for ``classify_positions`` — no IBKR connection,
no Telegram. Validates the 3-way split: true_leftover / swing_carry_over /
permanent_orphan.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture
def classify():
    """Load monitor_positions.classify_positions without running main()."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "paper_trading"))
    spec = importlib.util.spec_from_file_location(
        "monitor_positions",
        "scripts/paper_trading/monitor_positions.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.classify_positions


def test_leftover_only_true_leftovers_alerts(classify):
    """IBKR-ben pozíció DE NEM swing state → true_leftover."""
    ibkr = {"OLDPOS", "ZOMBIE"}
    swing = {"LBRT", "MASI"}
    true_left, carry, orphan = classify(ibkr, swing)
    assert true_left == {"OLDPOS", "ZOMBIE"}
    assert carry == set()
    assert orphan == set()


def test_leftover_swing_carry_over_silent(classify):
    """IBKR-ben ÉS swing state-ben → swing_carry_over (NEM leftover)."""
    ibkr = {"LBRT", "MASI", "EC"}
    swing = {"LBRT", "MASI", "EC"}
    true_left, carry, orphan = classify(ibkr, swing)
    assert true_left == set()
    assert carry == {"LBRT", "MASI", "EC"}
    assert orphan == set()


def test_leftover_avdl_cvr_excluded(classify):
    """AVDL.CVR permanent orphan, sose true_leftover."""
    ibkr = {"LBRT", "AVDL.CVR"}
    swing = {"LBRT"}
    true_left, carry, orphan = classify(ibkr, swing)
    assert true_left == set()
    assert carry == {"LBRT"}
    assert orphan == {"AVDL.CVR"}


def test_leftover_mixed_case(classify):
    """3-way mixed: swing carry + true leftover + permanent orphan együtt."""
    ibkr = {"LBRT", "MASI", "OLDPOS", "AVDL.CVR"}
    swing = {"LBRT", "MASI"}
    true_left, carry, orphan = classify(ibkr, swing)
    assert true_left == {"OLDPOS"}
    assert carry == {"LBRT", "MASI"}
    assert orphan == {"AVDL.CVR"}


def test_leftover_empty_swing_state_all_leftover(classify):
    """Üres swing state (Day 0 vagy state corruption) → minden tradable leftover."""
    ibkr = {"LBRT", "MASI", "AVDL.CVR"}
    swing = set()
    true_left, carry, orphan = classify(ibkr, swing)
    assert true_left == {"LBRT", "MASI"}
    assert carry == set()
    assert orphan == {"AVDL.CVR"}


def test_leftover_empty_ibkr_no_alert(classify):
    """IBKR teljesen üres (Day 1 előtt vagy nuke után) → semmi sem riaszt."""
    ibkr = set()
    swing = {"LBRT"}  # state has stale entry but no IBKR pos
    true_left, carry, orphan = classify(ibkr, swing)
    assert true_left == set()
    assert carry == set()
    assert orphan == set()
