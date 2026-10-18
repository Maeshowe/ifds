"""Market-data epoch timestamps must be read in UTC, never in the host's zone.

Polygon stamps a daily aggregate at ET midnight. ``date.fromtimestamp(t/1000)``
reads that through the host's local zone, so the same bar resolves to a
different calendar day on a host far enough from UTC — a silent off-by-one-day
in a return series. Caught 2026-10-19 by running the suite under TZ=UTC+14.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = REPO_ROOT / "scripts" / "analysis" / "scoring_validation.py"

# Call sites that legitimately read a *local* clock: both convert a file's
# mtime for a human-facing freshness check, not a market-data timestamp.
_LOCAL_CLOCK_ALLOWED = {
    ("scripts/check_phase13_freshness.py", "datetime.fromtimestamp"),
    ("scripts/paper_trading/pt_monitor.py", "date.fromtimestamp"),
}


def _load_scoring_validation():
    spec = importlib.util.spec_from_file_location("scoring_validation_tz", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def _utc_plus_14(monkeypatch):
    """Force a host zone 14 hours ahead, where local date != UTC date."""
    monkeypatch.setenv("TZ", "Pacific/Kiritimati")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


def test_spy_returns_keyed_by_utc_date_not_host_date(tmp_path, monkeypatch, _utc_plus_14):
    """A bar stamped 12:00 UTC on 6/4 is a 6/4 return on every host."""
    sv = _load_scoring_validation()
    monkeypatch.setattr(sv, "OUT_DIR", tmp_path)
    monkeypatch.setattr(sv, "SPY_CACHE", tmp_path / "spy_returns.json")
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_key")

    def _bar(day: int, close: float) -> dict:
        ts = datetime(2026, 6, day, 12, 0, tzinfo=timezone.utc).timestamp()
        return {"t": int(ts * 1000), "c": close}

    fake_client = MagicMock()
    fake_client.get_aggregates.return_value = [_bar(3, 100.0), _bar(4, 101.0)]
    fake_module = MagicMock()
    fake_module.PolygonClient.return_value = fake_client
    monkeypatch.setitem(sys.modules, "ifds.data.polygon", fake_module)

    returns = sv.fetch_and_cache_spy_returns(["2026-06-04"])

    assert "2026-06-04" in returns, f"bar date shifted with the host zone: {sorted(returns)}"
    assert "2026-06-05" not in returns


def _naked_fromtimestamp_calls(path: Path) -> list[tuple[int, str]]:
    """Every ``*.fromtimestamp(...)`` in `path` that passes no tz argument."""
    tree = ast.parse(path.read_text())
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "fromtimestamp"):
            continue
        has_tz = any(kw.arg == "tz" for kw in node.keywords) or len(node.args) > 1
        if has_tz:
            continue
        owner = func.value.id if isinstance(func.value, ast.Name) else "?"
        hits.append((node.lineno, f"{owner}.fromtimestamp"))
    return hits


def test_no_naked_fromtimestamp_outside_the_allowlist():
    """Close the gap, not the instance: no new local-zone epoch conversions."""
    offenders: list[str] = []
    for root in ("src/ifds", "scripts"):
        for path in sorted((REPO_ROOT / root).rglob("*.py")):
            rel = path.relative_to(REPO_ROOT).as_posix()
            for lineno, call in _naked_fromtimestamp_calls(path):
                if (rel, call) in _LOCAL_CLOCK_ALLOWED:
                    continue
                offenders.append(f"{rel}:{lineno} {call}(...) — pass tz=timezone.utc")
    assert not offenders, "local-zone epoch conversion:\n  " + "\n  ".join(offenders)
