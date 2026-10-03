"""Tests for the trading-enabled guard (D8 — adatgyűjtési mód).

Sibling of ``check_trading_day()``: lets us suspend IBKR order placement and the
IBKR-connecting jobs while every other pipeline phase keeps running, without
commenting out crontab lines (which would be undocumented production state).

Decision: gate-protocol §D8 / 04-risks §11.22 (Tamás, 2026-10-03).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_GUARD = (
    Path(__file__).resolve().parent.parent
    / "scripts" / "paper_trading" / "lib" / "trading_enabled_guard.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("trading_enabled_guard", _GUARD)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


teg = _load()


@pytest.fixture(autouse=True)
def _guard_active(monkeypatch):
    """Re-arm the guard inside this module.

    ``conftest.py`` disables it globally (so the production pause switch cannot
    short-circuit every ``main()``-calling test). These tests exercise the guard
    itself, so they need it live — same pattern as
    ``test_runner_skip_path.py`` does for ``IFDS_SKIP_TRADING_DAY_GUARD``.
    """
    monkeypatch.delenv("IFDS_SKIP_TRADING_ENABLED_GUARD", raising=False)


def _write(tmp_path: Path, payload) -> Path:
    p = tmp_path / "trading_enabled.json"
    p.write_text(payload if isinstance(payload, str) else json.dumps(payload))
    return p


# --- the pause switch ---------------------------------------------------------


def test_disabled_exits_cleanly(tmp_path):
    """enabled:false → clean exit(0), never a crash and never a Telegram."""
    path = _write(tmp_path, {"enabled": False, "reason": "D8 adatgyűjtési mód"})
    with pytest.raises(SystemExit) as exc:
        teg.check_trading_enabled(state_path=path)
    assert exc.value.code == 0


def test_enabled_returns_and_does_not_exit(tmp_path):
    path = _write(tmp_path, {"enabled": True})
    teg.check_trading_enabled(state_path=path)  # must not raise


def test_missing_file_means_enabled(tmp_path):
    """A missing switch is NOT a pause — behaviour stays unchanged for anyone
    who has never heard of the file (and for a fresh clone)."""
    teg.check_trading_enabled(state_path=tmp_path / "does-not-exist.json")


# --- the safe asymmetry -------------------------------------------------------


def test_malformed_file_fails_CLOSED(tmp_path):
    """If we cannot determine the state, do NOT trade.

    Fail-open on a missing file (deliberate, see above) but fail-CLOSED on a file
    we cannot parse: a truncated or half-written switch must never be read as
    'trading is fine'.
    """
    path = _write(tmp_path, "{not valid json")
    with pytest.raises(SystemExit) as exc:
        teg.check_trading_enabled(state_path=path)
    assert exc.value.code == 0


def test_missing_enabled_key_fails_CLOSED(tmp_path):
    path = _write(tmp_path, {"reason": "valaki elfelejtette az enabled kulcsot"})
    with pytest.raises(SystemExit) as exc:
        teg.check_trading_enabled(state_path=path)
    assert exc.value.code == 0


def test_non_bool_enabled_fails_CLOSED(tmp_path):
    """'false' as a string must not be truthy-read as enabled."""
    path = _write(tmp_path, {"enabled": "false"})
    with pytest.raises(SystemExit) as exc:
        teg.check_trading_enabled(state_path=path)
    assert exc.value.code == 0


# --- test escape hatch (mirrors IFDS_SKIP_TRADING_DAY_GUARD) ------------------


def test_env_escape_hatch_skips_the_guard(tmp_path, monkeypatch):
    monkeypatch.setenv("IFDS_SKIP_TRADING_ENABLED_GUARD", "1")
    path = _write(tmp_path, {"enabled": False})
    teg.check_trading_enabled(state_path=path)  # must not raise


# --- the reason reaches the log ----------------------------------------------


def test_reason_is_logged(tmp_path, caplog):
    path = _write(tmp_path, {"enabled": False, "reason": "D8 adatgyűjtési mód"})
    with caplog.at_level("INFO"):
        with pytest.raises(SystemExit):
            teg.check_trading_enabled(state_path=path)
    assert "D8 adatgyűjtési mód" in caplog.text


def test_default_state_path_points_at_the_repo_state_dir():
    """The production default must be state/trading_enabled.json, not a tmp path."""
    assert teg.DEFAULT_STATE_PATH.name == "trading_enabled.json"
    assert teg.DEFAULT_STATE_PATH.parent.name == "state"


# --- test-env hygiene (ifds-rules: hermetikus teszt) -------------------------


def test_conftest_insulates_the_suite_from_the_production_switch():
    """The suite must not depend on ``state/trading_enabled.json``.

    Inverse of the usual hygiene failure: a paused production switch would make
    every ``main()``-calling test exit(0) before its assertions. ``conftest.py``
    sets the escape hatch globally; this test fails loudly if that is removed.
    """
    conftest = (Path(__file__).resolve().parent / "conftest.py").read_text()

    assert 'os.environ["IFDS_SKIP_TRADING_ENABLED_GUARD"] = "1"' in conftest, (
        "conftest.py must set IFDS_SKIP_TRADING_ENABLED_GUARD=1 — otherwise the "
        "production pause switch silently short-circuits main()-calling tests."
    )
