"""Tests for scripts/maintenance/backfill_portfolio_return.py (data-quality fix #6)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "maintenance"
    / "backfill_portfolio_return.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("backfill_portfolio_return", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_metrics(metrics_dir: Path, date_str: str, portfolio_pct, spy_pct, excess_pct) -> Path:
    metrics_dir.mkdir(parents=True, exist_ok=True)
    path = metrics_dir / f"{date_str}.json"
    path.write_text(
        json.dumps(
            {
                "date": date_str,
                "excess_return": {
                    "portfolio_return_pct": portfolio_pct,
                    "spy_return_pct": spy_pct,
                    "excess_pct": excess_pct,
                },
            }
        )
    )
    return path


@pytest.fixture
def setup(tmp_path, monkeypatch):
    mod = _load_module()
    metrics_dir = tmp_path / "daily_metrics"
    eq = tmp_path / "daily_equity.json"
    eq.write_text(json.dumps({"2026-06-04": 101273.85, "2026-06-05": 100675.60}))
    monkeypatch.setattr(mod, "METRICS_DIR", metrics_dir)
    # The helper reads daily_metrics.DAILY_EQUITY_FILE — point it at our fixture.
    import daily_metrics as dm  # importable: the script inserts scripts/paper_trading on sys.path

    monkeypatch.setattr(dm, "DAILY_EQUITY_FILE", eq)
    return mod, metrics_dir


def test_corrects_portfolio_return_and_excess(setup):
    from datetime import date

    mod, metrics_dir = setup
    # Day 15 6/5: stale realized-based -0.01 / excess 2.57 → NetLiq -0.59 / 1.99.
    p = _write_metrics(metrics_dir, "2026-06-05", -0.01, -2.58, 2.57)
    changed = mod.backfill(date(2026, 6, 5), date(2026, 6, 5), apply=True)
    assert changed == 1
    block = json.loads(p.read_text())["excess_return"]
    assert block["portfolio_return_pct"] == pytest.approx(-0.59, abs=0.01)
    assert block["excess_pct"] == pytest.approx(1.99, abs=0.01)


def test_skips_day_without_equity_pair(setup):
    from datetime import date

    mod, metrics_dir = setup
    # 6/4 has no prior equity in the fixture → left as realized estimate.
    p = _write_metrics(metrics_dir, "2026-06-04", 0.24, 0.37, -0.13)
    changed = mod.backfill(date(2026, 6, 4), date(2026, 6, 4), apply=True)
    assert changed == 0
    block = json.loads(p.read_text())["excess_return"]
    assert block["portfolio_return_pct"] == 0.24  # untouched


def test_dry_run_does_not_write(setup):
    from datetime import date

    mod, metrics_dir = setup
    p = _write_metrics(metrics_dir, "2026-06-05", -0.01, -2.58, 2.57)
    before = p.read_text()
    changed = mod.backfill(date(2026, 6, 5), date(2026, 6, 5), apply=False)
    assert changed == 1
    assert p.read_text() == before  # untouched
