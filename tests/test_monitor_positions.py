"""Tests for monitor_positions.py — Leftover position detection.

Covers:
- No leftover: all positions in today's plan → no Telegram
- Leftover detected: position not in plan → Telegram warning
- No plan found: no CSV for today → warning log, no crash
- CVR positions skipped
- Zero positions skipped
"""

import csv
import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _isolate_monitor_env():
    """Prevent monitor_positions.py load_dotenv() from polluting env."""
    mod_key = "scripts.paper_trading.monitor_positions"
    cached = sys.modules.pop(mod_key, None)
    env_before = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(env_before)
    sys.modules.pop(mod_key, None)
    if cached is not None:
        sys.modules[mod_key] = cached


def _make_position(symbol, qty, sec_type="STK"):
    """Build a mock ib_insync Position."""
    pos = MagicMock()
    pos.contract.symbol = symbol
    pos.contract.secType = sec_type
    pos.position = qty
    return pos


def _write_execution_plan(tmp_path, symbols):
    """Write a minimal execution plan CSV with given symbols."""
    today = date.today().strftime("%Y%m%d")
    csv_path = tmp_path / f"execution_plan_run_{today}_2200.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["instrument_id", "direction", "quantity"])
        for s in symbols:
            writer.writerow([s, "BUY", 100])
    return csv_path


def _import_module(tmp_path):
    """Import monitor_positions with EXECUTION_PLAN_DIR pointed at tmp_path."""
    # Add scripts/paper_trading to path for lib.connection import
    scripts_dir = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "paper_trading"
    )
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    import scripts.paper_trading.monitor_positions as mod

    mod.EXECUTION_PLAN_DIR = str(tmp_path)
    return mod


def test_no_leftover(tmp_path):
    """All positions in today's plan → no Telegram, INFO log."""
    _write_execution_plan(tmp_path, ["AAPL", "MSFT"])
    mod = _import_module(tmp_path)

    mock_ib = MagicMock()
    mock_ib.positions.return_value = [
        _make_position("AAPL", 100),
        _make_position("MSFT", 200),
    ]

    with patch.object(mod, "send_telegram") as mock_tg, patch(
        "lib.connection.connect", return_value=mock_ib
    ), patch("lib.connection.disconnect"):
        mod.main()

    mock_tg.assert_not_called()


def test_leftover_detected(tmp_path):
    """CRGY open but not in plan → Telegram warning with ticker and qty."""
    _write_execution_plan(tmp_path, ["AAPL"])
    mod = _import_module(tmp_path)

    mock_ib = MagicMock()
    mock_ib.positions.return_value = [
        _make_position("AAPL", 100),
        _make_position("CRGY", 672),
    ]

    with patch.object(mod, "send_telegram") as mock_tg, patch(
        "lib.connection.connect", return_value=mock_ib
    ), patch("lib.connection.disconnect"):
        mod.main()

    mock_tg.assert_called_once()
    msg = mock_tg.call_args[0][0]
    assert "CRGY" in msg
    assert "+672" in msg
    assert "LEFTOVER" in msg


def test_no_plan_found(tmp_path):
    """No execution plan CSV for today → warning log, no crash, no Telegram."""
    # tmp_path is empty — no CSV
    mod = _import_module(tmp_path)

    mock_ib = MagicMock()
    mock_ib.positions.return_value = [_make_position("AAPL", 100)]

    with patch.object(mod, "send_telegram") as mock_tg, patch(
        "lib.connection.connect", return_value=mock_ib
    ), patch("lib.connection.disconnect"):
        mod.main()

    # No plan → all positions are leftover
    mock_tg.assert_called_once()
    msg = mock_tg.call_args[0][0]
    assert "AAPL" in msg


def test_cvr_skipped(tmp_path):
    """AVDL.CVR position should not appear as leftover."""
    _write_execution_plan(tmp_path, ["AAPL"])
    mod = _import_module(tmp_path)

    mock_ib = MagicMock()
    mock_ib.positions.return_value = [
        _make_position("AAPL", 100),
        _make_position("AVDL.CVR", 50),
    ]

    with patch.object(mod, "send_telegram") as mock_tg, patch(
        "lib.connection.connect", return_value=mock_ib
    ), patch("lib.connection.disconnect"):
        mod.main()

    mock_tg.assert_not_called()


def test_zero_position_skipped(tmp_path):
    """position=0 should not appear as leftover."""
    _write_execution_plan(tmp_path, ["AAPL"])
    mod = _import_module(tmp_path)

    mock_ib = MagicMock()
    mock_ib.positions.return_value = [
        _make_position("AAPL", 100),
        _make_position("CRGY", 0),  # closed, qty=0
    ]

    with patch.object(mod, "send_telegram") as mock_tg, patch(
        "lib.connection.connect", return_value=mock_ib
    ), patch("lib.connection.disconnect"):
        mod.main()

    mock_tg.assert_not_called()
