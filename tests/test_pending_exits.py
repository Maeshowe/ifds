"""Tests for scripts/paper_trading/lib/pending_exits.py — P0 §0.11 Part A.

Covers the pure/file-only ledger helpers (no IBKR API):
- append_pending_exit — key generation, idempotency, required fields
- load_pending_exits — missing/empty/corrupt file handling
- mark_processed — flag flip, atomicity, no-op cases
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _ensure_lib_importable():
    pt_dir = str(Path(__file__).resolve().parent.parent / "scripts" / "paper_trading")
    added = pt_dir not in sys.path
    if added:
        sys.path.insert(0, pt_dir)
    yield
    if added:
        sys.path.remove(pt_dir)


def _mod():
    import importlib

    import lib.pending_exits as m

    return importlib.reload(m)


def _record(**overrides):
    base = {
        "ticker": "AMH",
        "entry_price": 32.11,
        "entry_date": "2026-05-21",
        "qty": 249,
        "exit_type": "TIME_STOP",
        "sector": "Real Estate",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# make_key
# ---------------------------------------------------------------------------


class TestMakeKey:
    def test_format(self):
        m = _mod()
        assert m.make_key("AMH", "TIME_STOP", "2026-05-28") == "AMH_TIME_STOP_2026-05-28"


# ---------------------------------------------------------------------------
# append_pending_exit
# ---------------------------------------------------------------------------


class TestAppend:
    def test_append_creates_file_and_record(self, tmp_path):
        m = _mod()
        res = m.append_pending_exit(_record(), ledger_dir=tmp_path, today="2026-05-28")
        assert res == {"key": "AMH_TIME_STOP_2026-05-28", "appended": True}

        records = m.load_pending_exits("2026-05-28", tmp_path)
        assert len(records) == 1
        r = records[0]
        assert r["key"] == "AMH_TIME_STOP_2026-05-28"
        assert r["ticker"] == "AMH"
        assert r["qty"] == 249
        assert r["exit_type"] == "TIME_STOP"
        assert r["sector"] == "Real Estate"
        assert r["processed"] is False
        assert "submitted_at" in r

    def test_idempotent_same_key_not_duplicated(self, tmp_path):
        m = _mod()
        m.append_pending_exit(_record(), ledger_dir=tmp_path, today="2026-05-28")
        res = m.append_pending_exit(_record(), ledger_dir=tmp_path, today="2026-05-28")
        assert res == {"key": "AMH_TIME_STOP_2026-05-28", "appended": False}
        assert len(m.load_pending_exits("2026-05-28", tmp_path)) == 1

    def test_distinct_exit_types_coexist(self, tmp_path):
        m = _mod()
        m.append_pending_exit(_record(exit_type="TP1", qty=83), ledger_dir=tmp_path, today="2026-05-28")
        m.append_pending_exit(_record(exit_type="TIME_STOP"), ledger_dir=tmp_path, today="2026-05-28")
        records = m.load_pending_exits("2026-05-28", tmp_path)
        assert {r["key"] for r in records} == {
            "AMH_TP1_2026-05-28",
            "AMH_TIME_STOP_2026-05-28",
        }

    def test_today_defaults_to_date_today(self, tmp_path):
        m = _mod()
        m.append_pending_exit(_record(), ledger_dir=tmp_path)
        today = date.today().isoformat()
        records = m.load_pending_exits(today, tmp_path)
        assert len(records) == 1
        assert records[0]["key"] == f"AMH_TIME_STOP_{today}"

    def test_today_accepts_date_object(self, tmp_path):
        m = _mod()
        m.append_pending_exit(_record(), ledger_dir=tmp_path, today=date(2026, 5, 28))
        assert len(m.load_pending_exits("2026-05-28", tmp_path)) == 1

    def test_explicit_submitted_at_preserved(self, tmp_path):
        m = _mod()
        m.append_pending_exit(
            _record(submitted_at="2026-05-28T19:40:03+00:00"),
            ledger_dir=tmp_path,
            today="2026-05-28",
        )
        r = m.load_pending_exits("2026-05-28", tmp_path)[0]
        assert r["submitted_at"] == "2026-05-28T19:40:03+00:00"

    def test_missing_required_field_raises(self, tmp_path):
        m = _mod()
        bad = _record()
        del bad["entry_price"]
        with pytest.raises(ValueError, match="entry_price"):
            m.append_pending_exit(bad, ledger_dir=tmp_path, today="2026-05-28")

    def test_sector_optional_defaults_empty(self, tmp_path):
        m = _mod()
        rec = _record()
        del rec["sector"]
        m.append_pending_exit(rec, ledger_dir=tmp_path, today="2026-05-28")
        assert m.load_pending_exits("2026-05-28", tmp_path)[0]["sector"] == ""


# ---------------------------------------------------------------------------
# load_pending_exits
# ---------------------------------------------------------------------------


class TestLoad:
    def test_missing_file_returns_empty(self, tmp_path):
        m = _mod()
        assert m.load_pending_exits("2099-01-01", tmp_path) == []

    def test_corrupt_file_returns_empty(self, tmp_path):
        m = _mod()
        (tmp_path / "2026-05-28.json").write_text("{not json")
        assert m.load_pending_exits("2026-05-28", tmp_path) == []

    def test_non_list_returns_empty(self, tmp_path):
        m = _mod()
        (tmp_path / "2026-05-28.json").write_text('{"key": "x"}')
        assert m.load_pending_exits("2026-05-28", tmp_path) == []


# ---------------------------------------------------------------------------
# mark_processed
# ---------------------------------------------------------------------------


class TestMarkProcessed:
    def test_flips_flag(self, tmp_path):
        m = _mod()
        m.append_pending_exit(_record(), ledger_dir=tmp_path, today="2026-05-28")
        changed = m.mark_processed("2026-05-28", {"AMH_TIME_STOP_2026-05-28"}, tmp_path)
        assert changed == 1
        assert m.load_pending_exits("2026-05-28", tmp_path)[0]["processed"] is True

    def test_idempotent_already_processed(self, tmp_path):
        m = _mod()
        m.append_pending_exit(_record(), ledger_dir=tmp_path, today="2026-05-28")
        m.mark_processed("2026-05-28", {"AMH_TIME_STOP_2026-05-28"}, tmp_path)
        again = m.mark_processed("2026-05-28", {"AMH_TIME_STOP_2026-05-28"}, tmp_path)
        assert again == 0

    def test_empty_keys_noop(self, tmp_path):
        m = _mod()
        m.append_pending_exit(_record(), ledger_dir=tmp_path, today="2026-05-28")
        assert m.mark_processed("2026-05-28", set(), tmp_path) == 0

    def test_missing_ledger_noop(self, tmp_path):
        m = _mod()
        assert m.mark_processed("2099-01-01", {"X_TP1_2099-01-01"}, tmp_path) == 0

    def test_unknown_key_noop(self, tmp_path):
        m = _mod()
        m.append_pending_exit(_record(), ledger_dir=tmp_path, today="2026-05-28")
        assert m.mark_processed("2026-05-28", {"NOPE_TP1_2026-05-28"}, tmp_path) == 0
