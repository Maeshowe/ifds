"""Global test configuration — shared fixtures and environment setup."""

import os
import tempfile
from pathlib import Path

import pytest

# Eager-import the numpy chain BEFORE any test runs (e2e ordering-leak fix,
# 2026-07-24). test_close_positions_split.py calls close_positions.main() inside a
# ``patch.dict("sys.modules", {...})`` block; main() lazily imports
# ifds.utils.calendar → exchange_calendars → numpy. patch.dict restores by
# clearing sys.modules and reinstating the entry snapshot, so a numpy imported
# *inside* the block gets dropped — orphaning its already-initialised C-extension
# and making a later ``import numpy`` fail ("cannot load module more than once per
# process"). Loading numpy here puts it in every patch.dict entry snapshot, so it
# survives every restore regardless of test order. See test_sys_modules_isolation.py.
import ifds.utils.calendar  # noqa: E402,F401  (→ exchange_calendars → numpy)

# Disable trading day guard in all tests (production guard exits on NYSE holidays)
os.environ["IFDS_SKIP_TRADING_DAY_GUARD"] = "1"
# Same for the trading-enabled guard (gate-protocol §D8). The production switch lives at
# ``state/trading_enabled.json``; while trading is paused it is ``{"enabled": false}``, and
# every ``main()`` that calls the guard would exit(0) before the test's assertions run.
# This is the inverse of the usual test-env-hygiene failure: here the PROD state would make
# the tests fail rather than falsely pass. Tests that exercise the guard itself inject an
# explicit ``state_path`` or clear this var via monkeypatch.
os.environ["IFDS_SKIP_TRADING_ENABLED_GUARD"] = "1"

# Redirect the paper-trading event log away from production logs/ (test-env-hygiene P1,
# 2026-07-23 review §6). scripts/paper_trading/*.py instantiate a module-level
# ``evt = PTEventLogger()`` at *import* time, so this must be set before collection —
# a session-scope fixture runs too late. setdefault preserves an explicit override.
os.environ.setdefault(
    "IFDS_PT_EVENT_DIR", tempfile.mkdtemp(prefix="ifds_pt_events_")
)

# Clear MID_API_KEY so the test suite cannot make LIVE MID API calls (test-env
# hygiene, 2026-10-04 repo audit). ``run_phase0`` unconditionally calls
# ``_save_mid_bundle_if_configured``, which resolves the key from this env var —
# and ``.env`` exports it, which ``deploy_daily.sh`` sources BEFORE its pytest
# pre-flight. Consequence, measured: two live fetches per suite run, each
# overwriting ``state/mid_bundles/{today}.json.gz`` with an off-schedule capture
# (verified: the 2026-10-03 and 2026-10-04 bundles carried test-run mtimes, not
# the 14:30 cron's). Same failure class as the phase4-snapshot overwrite that ran
# undetected for 28 days (ifds-rules, 2026-05-10) — close the gap, not the instance.
# Verified safe: no test reads MID_API_KEY from the environment; the MID tests
# pass fake keys explicitly.
#
# ⚠️ EMPTY STRING, NOT pop()/delenv(). Several scripts call ``load_dotenv()`` at
# import time, and that re-reads ``.env`` — a popped variable comes straight back
# (measured: the bundle was still rewritten after a pop). ``load_dotenv`` defaults
# to ``override=False``, so a key that is PRESENT-but-empty survives it, while an
# ABSENT key does not. The same weakness applies to every ``delenv`` guard in the
# house rules (e.g. the IFDS_TELEGRAM_* ones): prefer the empty sentinel.
os.environ["MID_API_KEY"] = ""

#: Resolved at import time, BEFORE the session chdir below.
REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def _isolate_cwd_from_production_state(tmp_path_factory):
    """Run the whole suite from a scratch CWD so relative writes miss production.

    Measured 2026-10-04 (repo audit): running three test files rewrote
    ``state/bmi_history.json``, ``state/sector_history.json``,
    ``state/skip_day_shadow.jsonl`` and ``state/ewma_scores.json``, and the suite
    also created ``state/universe_snapshots/{today}.json`` and a
    ``logs/ifds_run_*.jsonl``. Production defaults are CWD-relative
    (``"state/..."``), so every unpatched sink lands in the real research record —
    the same failure class as the phase4-snapshot overwrite that ran undetected
    for 28 days (ifds-rules, 2026-05-10).

    Patching sinks one by one has already failed twice: the ``save_phase4_snapshot``
    fix did not cover ``write_shadow_snapshot``, which then destroyed a day of UW
    shadow data. This closes the GAP instead: a relative write can no longer reach
    the repo at all, whatever new sink appears.

    Safe because nothing resolves repo files through the CWD: ``pythonpath = ["src"]``
    resolves against rootdir, and the four previously CWD-relative importlib
    loaders are now anchored on ``Path(__file__).parents[1]``.
    """
    scratch = tmp_path_factory.mktemp("ifds_cwd_isolation")
    previous = os.getcwd()
    os.chdir(scratch)
    try:
        yield scratch
    finally:
        os.chdir(previous)


def test_production_state_is_unreachable_from_the_test_cwd():
    """Guard: if a future change drops the isolation, this fails loudly."""
    assert Path.cwd() != REPO_ROOT, (
        "tests are running from the repo root — relative sinks will write "
        "production state/ and logs/"
    )
