"""Tests for eod_report.load_persisted_trades_block (2026-06-17).

The 22:11 eod_report rebuilds trades.details from its own clientId-12 fills,
which miss the 21:40/cross-client MOC exits → "Trades: 0" on cross-client MOC
days (06-15 FFIV, 06-16 TKR). The fix prefers the authoritative trades block
from the persisted state/daily_metrics/{date}.json written by the 22:10
record_pending_exits cron (clientId-18). Falls back to None when absent.
"""

import json
import os
import sys
from unittest.mock import MagicMock

import pytest

_PT_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts", "paper_trading")


@pytest.fixture(autouse=True)
def _isolate_eod_env():
    mod_key = "scripts.paper_trading.eod_report"
    cached = sys.modules.pop(mod_key, None)
    env_before = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(env_before)
    sys.modules.pop(mod_key, None)
    if cached is not None:
        sys.modules[mod_key] = cached


def _import_eod():
    sys.modules["dotenv"] = MagicMock()
    if _PT_DIR not in sys.path:
        sys.path.insert(0, _PT_DIR)
    import scripts.paper_trading.eod_report as eod

    return eod


def _import_daily_metrics():
    if _PT_DIR not in sys.path:
        sys.path.insert(0, _PT_DIR)
    import daily_metrics

    return daily_metrics


def test_prefers_persisted_block_with_details(tmp_path, monkeypatch):
    eod = _import_eod()
    dm = _import_daily_metrics()
    monkeypatch.setattr(dm, "METRICS_DIR", tmp_path)
    (tmp_path / "2026-06-16.json").write_text(
        json.dumps(
            {
                "trades": {
                    "details": [{"ticker": "TKR", "exit_type": "TIME_STOP_MOC", "pnl": 134.03}],
                    "best": {"ticker": "TKR", "pnl": 134.03},
                }
            }
        )
    )
    block = eod.load_persisted_trades_block("2026-06-16")
    assert block is not None
    assert len(block["details"]) == 1
    assert block["details"][0]["ticker"] == "TKR"
    # whole block returned (best/worst preserved → consistent with details)
    assert block["best"]["ticker"] == "TKR"


def test_returns_none_when_file_missing(tmp_path, monkeypatch):
    eod = _import_eod()
    dm = _import_daily_metrics()
    monkeypatch.setattr(dm, "METRICS_DIR", tmp_path)
    assert eod.load_persisted_trades_block("2099-01-01") is None


def test_returns_none_when_details_empty(tmp_path, monkeypatch):
    """Persisted file exists but no exits → fall back to caller's own rebuild."""
    eod = _import_eod()
    dm = _import_daily_metrics()
    monkeypatch.setattr(dm, "METRICS_DIR", tmp_path)
    (tmp_path / "2026-06-16.json").write_text(json.dumps({"trades": {"details": []}}))
    assert eod.load_persisted_trades_block("2026-06-16") is None
