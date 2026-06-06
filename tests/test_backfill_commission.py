"""Tests for scripts/maintenance/backfill_commission.py (data-quality fix #4)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parent.parent / "scripts" / "maintenance" / "backfill_commission.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("backfill_commission", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def cum_file(tmp_path):
    path = tmp_path / "cumulative_pnl.json"
    path.write_text(
        json.dumps(
            {
                "initial_capital": 100000,
                "cumulative_pnl": 245.25,
                "daily_history": [
                    {"date": "2026-06-03", "pnl": 229.84, "commission": 3.22},
                    {"date": "2026-06-04", "pnl": 225.34, "commission": 0.0},
                    {"date": "2026-06-05", "pnl": 63.83, "commission": 0.0},
                ],
            }
        )
    )
    return path


def test_dry_run_does_not_write(cum_file):
    mod = _load_module()
    before = cum_file.read_text()
    changed = mod.backfill(cum_file, {"2026-06-04": 3.92, "2026-06-05": 4.39}, apply=False)
    assert changed == 2
    assert cum_file.read_text() == before  # untouched


def test_apply_sets_commission_and_backs_up(cum_file):
    mod = _load_module()
    changed = mod.backfill(cum_file, {"2026-06-04": 3.92, "2026-06-05": 4.39}, apply=True)
    assert changed == 2
    data = json.loads(cum_file.read_text())
    by_date = {e["date"]: e for e in data["daily_history"]}
    assert by_date["2026-06-04"]["commission"] == 3.92
    assert by_date["2026-06-05"]["commission"] == 4.39
    # pnl (NET) is untouched — commission is informational only
    assert by_date["2026-06-05"]["pnl"] == 63.83
    assert data["cumulative_pnl"] == 245.25
    # a backup was written
    assert list(cum_file.parent.glob("*.bak.pre_commission_backfill.*"))


def test_idempotent(cum_file):
    mod = _load_module()
    cmap = {"2026-06-03": 3.22}  # already matches
    assert mod.backfill(cum_file, cmap, apply=True) == 0


def test_missing_entry_skipped(cum_file):
    mod = _load_module()
    changed = mod.backfill(cum_file, {"2026-05-01": 1.50}, apply=True)
    assert changed == 0  # no daily_history entry for that date


def test_default_map_loads_and_excludes_note():
    mod = _load_module()
    cmap = mod._load_map(mod.DEFAULT_MAP)
    assert "_note" not in cmap
    assert cmap["2026-06-05"] == 4.39
    assert all(isinstance(v, float) for v in cmap.values())
