"""Tests for scoring_validation.py SPY-cache auto-fetch + merge (2026-06-13)."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "analysis" / "scoring_validation.py"


def _load():
    spec = importlib.util.spec_from_file_location("scoring_validation", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


sv = _load()


def _bar(y: int, m: int, d: int, close: float) -> dict:
    ts = int(datetime(y, m, d, 12, 0, tzinfo=timezone.utc).timestamp() * 1000)
    return {"t": ts, "c": close}


def _mock_polygon(monkeypatch, bars):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_key")
    fake_client = MagicMock()
    fake_client.get_aggregates.return_value = bars
    fake_module = MagicMock()
    fake_module.PolygonClient.return_value = fake_client
    monkeypatch.setitem(sys.modules, "ifds.data.polygon", fake_module)


def test_fetch_merges_with_existing_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(sv, "OUT_DIR", tmp_path)
    monkeypatch.setattr(sv, "SPY_CACHE", tmp_path / "spy_returns.json")
    # 6/3 pad close → returns computed for 6/4, 6/5
    _mock_polygon(
        monkeypatch, [_bar(2026, 6, 3, 100.0), _bar(2026, 6, 4, 101.0), _bar(2026, 6, 5, 102.0)]
    )

    existing = {"2026-06-01": 0.5}
    merged = sv.fetch_and_cache_spy_returns(["2026-06-05"], merge_with=existing)

    # existing day preserved + new days added
    assert merged["2026-06-01"] == 0.5
    assert merged["2026-06-04"] == pytest.approx(1.0)  # (101-100)/100*100
    assert merged["2026-06-05"] == pytest.approx((102 - 101) / 101 * 100)
    # cache file written with the merge
    on_disk = json.loads((tmp_path / "spy_returns.json").read_text())
    assert set(on_disk) == {"2026-06-01", "2026-06-04", "2026-06-05"}


def test_empty_fetch_keeps_existing_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(sv, "OUT_DIR", tmp_path)
    monkeypatch.setattr(sv, "SPY_CACHE", tmp_path / "spy_returns.json")
    _mock_polygon(monkeypatch, [])  # no bars returned

    existing = {"2026-06-01": 0.5}
    merged = sv.fetch_and_cache_spy_returns(["2026-06-05"], merge_with=existing)
    assert merged == existing  # cache not clobbered on a failed/empty fetch


def test_load_returns_empty_when_no_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(sv, "SPY_CACHE", tmp_path / "missing.json")
    assert sv.load_spy_returns() == {}
