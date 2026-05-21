"""Tests for monitor_positions.py — Leftover position detection (swing-aware).

Covers (Task #T §3.5 — 2026-05-19 refactor):
- No leftover: all IBKR positions in swing state → no Telegram (swing carry-over normal)
- True leftover detected: IBKR pos NOT in swing state → TRUE LEFTOVER Telegram
- Empty swing state: every IBKR pos becomes true_leftover
- AVDL.CVR permanent orphan: excluded even when not in swing state
- Zero position IBKR entries skipped
"""

import os
import sys
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
    """All IBKR positions present in swing state → no Telegram (carry-over normal)."""
    mod = _import_module(tmp_path)

    mock_ib = MagicMock()
    mock_ib.positions.return_value = [
        _make_position("AAPL", 100),
        _make_position("MSFT", 200),
    ]

    with patch.object(mod, "load_swing_state_tickers", return_value={"AAPL", "MSFT"}), \
         patch.object(mod, "send_telegram") as mock_tg, \
         patch("lib.connection.connect", return_value=mock_ib), \
         patch("lib.connection.disconnect"):
        mod.main()

    mock_tg.assert_not_called()


def test_leftover_detected(tmp_path):
    """CRGY open but not in swing state → TRUE LEFTOVER Telegram."""
    mod = _import_module(tmp_path)

    mock_ib = MagicMock()
    mock_ib.positions.return_value = [
        _make_position("AAPL", 100),
        _make_position("CRGY", 672),
    ]

    with patch.object(mod, "load_swing_state_tickers", return_value={"AAPL"}), \
         patch.object(mod, "send_telegram") as mock_tg, \
         patch("lib.connection.connect", return_value=mock_ib), \
         patch("lib.connection.disconnect"):
        mod.main()

    mock_tg.assert_called_once()
    msg = mock_tg.call_args[0][0]
    assert "CRGY" in msg
    assert "+672" in msg
    assert "TRUE LEFTOVER" in msg


def test_no_swing_state_all_leftover(tmp_path):
    """Empty swing state → every IBKR pos is true_leftover."""
    mod = _import_module(tmp_path)

    mock_ib = MagicMock()
    mock_ib.positions.return_value = [_make_position("AAPL", 100)]

    with patch.object(mod, "load_swing_state_tickers", return_value=set()), \
         patch.object(mod, "send_telegram") as mock_tg, \
         patch("lib.connection.connect", return_value=mock_ib), \
         patch("lib.connection.disconnect"):
        mod.main()

    mock_tg.assert_called_once()
    msg = mock_tg.call_args[0][0]
    assert "AAPL" in msg


def test_cvr_permanent_orphan_excluded(tmp_path):
    """AVDL.CVR is a permanent orphan → never true_leftover even if not in swing state."""
    mod = _import_module(tmp_path)

    mock_ib = MagicMock()
    mock_ib.positions.return_value = [
        _make_position("AAPL", 100),
        _make_position("AVDL.CVR", 50),
    ]

    with patch.object(mod, "load_swing_state_tickers", return_value={"AAPL"}), \
         patch.object(mod, "send_telegram") as mock_tg, \
         patch("lib.connection.connect", return_value=mock_ib), \
         patch("lib.connection.disconnect"):
        mod.main()

    mock_tg.assert_not_called()


def test_zero_position_skipped(tmp_path):
    """position=0 IBKR entry filter-elve a raw_positions loopban."""
    mod = _import_module(tmp_path)

    mock_ib = MagicMock()
    mock_ib.positions.return_value = [
        _make_position("AAPL", 100),
        _make_position("CRGY", 0),  # closed, qty=0
    ]

    with patch.object(mod, "load_swing_state_tickers", return_value={"AAPL"}), \
         patch.object(mod, "send_telegram") as mock_tg, \
         patch("lib.connection.connect", return_value=mock_ib), \
         patch("lib.connection.disconnect"):
        mod.main()

    mock_tg.assert_not_called()
