"""Tests — Task #D state/IBKR reconciliation.

Pure-function tests for ``compute_divergence`` and the Telegram body
formatter. Integration with the IBKR client is glue-level and not
unit-tested here.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture
def mod():
    """Load reconcile_state without executing main()."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "paper_trading"))
    spec = importlib.util.spec_from_file_location(
        "reconcile_state", "scripts/paper_trading/reconcile_state.py",
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_reconcile_no_divergence(mod):
    """state == ibkr → empty diffs."""
    a, b = mod.compute_divergence({"LBRT", "MASI", "EC"}, {"LBRT", "MASI", "EC"})
    assert a == set() and b == set()


def test_reconcile_state_has_ibkr_doesnt(mod):
    """state: {LBRT, MASI}, ibkr: {LBRT} → in_state_not_ibkr={MASI}."""
    a, b = mod.compute_divergence({"LBRT", "MASI"}, {"LBRT"})
    assert a == {"MASI"}
    assert b == set()


def test_reconcile_ibkr_has_state_doesnt(mod):
    """state: {LBRT}, ibkr: {LBRT, EC} → in_ibkr_not_state={EC}."""
    a, b = mod.compute_divergence({"LBRT"}, {"LBRT", "EC"})
    assert a == set()
    assert b == {"EC"}


def test_reconcile_avdl_cvr_orphan_ignored(mod):
    """ibkr: {LBRT, AVDL.CVR}, state: {LBRT} → AVDL.CVR excluded from divergence."""
    a, b = mod.compute_divergence({"LBRT"}, {"LBRT", "AVDL.CVR"})
    assert a == set()
    assert b == set()


def test_reconcile_both_diverge(mod):
    """state: {LBRT, OLD}, ibkr: {LBRT, NEW, AVDL.CVR} → two-way diff."""
    a, b = mod.compute_divergence({"LBRT", "OLD"}, {"LBRT", "NEW", "AVDL.CVR"})
    assert a == {"OLD"}
    assert b == {"NEW"}


def test_reconcile_telegram_format_state_side(mod):
    """Telegram body lists 'State has, IBKR doesn't' side."""
    body = mod.format_divergence_telegram(
        {"MASI"}, set(), "2026-05-19",
    )
    assert "MASI" in body
    assert "State has, IBKR doesn't" in body
    assert "2026-05-19" in body


def test_reconcile_telegram_format_both_sides(mod):
    """Both sides in the message when both have diffs."""
    body = mod.format_divergence_telegram(
        {"OLDSTATE"}, {"NEWIBKR"}, "2026-05-19",
    )
    assert "OLDSTATE" in body and "NEWIBKR" in body
    assert "State has" in body and "IBKR has" in body
