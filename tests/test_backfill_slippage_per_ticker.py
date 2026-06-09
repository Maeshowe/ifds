"""Tests for scripts/maintenance/backfill_slippage_per_ticker.py (task 2026-06-09 #1)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "maintenance"
    / "backfill_slippage_per_ticker.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("backfill_slippage_per_ticker", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_metrics(metrics_dir: Path, date_str: str, slip: dict) -> Path:
    metrics_dir.mkdir(parents=True, exist_ok=True)
    path = metrics_dir / f"{date_str}.json"
    path.write_text(
        json.dumps(
            {
                "date": date_str,
                "execution": {"avg_fill_slippage_pct": 0.0, "slippage_per_ticker": slip},
            }
        )
    )
    return path


@pytest.fixture
def setup(tmp_path, monkeypatch):
    mod = _load_module()
    metrics_dir = tmp_path / "daily_metrics"
    monkeypatch.setattr(mod, "METRICS_DIR", metrics_dir)
    return mod, metrics_dir


def test_sets_filled_and_recomputes_slippage(setup):
    mod, metrics_dir = setup
    # TKR 6/8: planned 131.83, filled was state 131.83 (slip 0) → IBKR fill 133.71.
    p = _write_metrics(
        metrics_dir,
        "2026-06-08",
        {
            "TKR": {"planned": 131.83, "filled": 131.83, "slippage_pct": 0.0, "qty": 39},
            "NSA": {"planned": 43.43, "filled": 43.43, "slippage_pct": 0.0, "qty": 188},
        },
    )
    changed = mod.backfill({"2026-06-08": {"TKR": 133.71, "NSA": 43.41}}, apply=True)
    assert changed == 2
    slip = json.loads(p.read_text())["execution"]["slippage_per_ticker"]
    assert slip["TKR"]["filled"] == pytest.approx(133.71)
    assert slip["TKR"]["slippage_pct"] == pytest.approx(1.43, abs=0.01)
    assert slip["NSA"]["slippage_pct"] == pytest.approx(-0.05, abs=0.01)
    # qty-weighted avg recomputed: (39*1.43 + 188*-0.05)/227 ≈ +0.21
    avg = json.loads(p.read_text())["execution"]["avg_fill_slippage_pct"]
    assert avg == pytest.approx(0.21, abs=0.02)


def test_idempotent(setup):
    mod, metrics_dir = setup
    _write_metrics(
        metrics_dir,
        "2026-06-08",
        {"TKR": {"planned": 131.83, "filled": 133.71, "slippage_pct": 1.43, "qty": 39}},
    )
    assert mod.backfill({"2026-06-08": {"TKR": 133.71}}, apply=True) == 0


def test_skips_ticker_not_in_file(setup):
    mod, metrics_dir = setup
    _write_metrics(
        metrics_dir, "2026-06-08", {"TKR": {"planned": 131.83, "filled": 131.83, "qty": 39}}
    )
    # ZZZ not in the file's slippage_per_ticker → skipped.
    assert mod.backfill({"2026-06-08": {"ZZZ": 10.0}}, apply=True) == 0


def test_dry_run_does_not_write(setup):
    mod, metrics_dir = setup
    p = _write_metrics(
        metrics_dir,
        "2026-06-08",
        {"TKR": {"planned": 131.83, "filled": 131.83, "slippage_pct": 0.0, "qty": 39}},
    )
    before = p.read_text()
    assert mod.backfill({"2026-06-08": {"TKR": 133.71}}, apply=False) == 1
    assert p.read_text() == before


def test_default_map_loads_and_excludes_note():
    mod = _load_module()
    m = mod._load_map(mod.DEFAULT_MAP)
    assert "_note" not in m
    assert m["2026-06-08"]["TKR"] == 133.71
