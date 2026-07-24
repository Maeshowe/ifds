"""Global test configuration — shared fixtures and environment setup."""

import os
import tempfile

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

# Redirect the paper-trading event log away from production logs/ (test-env-hygiene P1,
# 2026-07-23 review §6). scripts/paper_trading/*.py instantiate a module-level
# ``evt = PTEventLogger()`` at *import* time, so this must be set before collection —
# a session-scope fixture runs too late. setdefault preserves an explicit override.
os.environ.setdefault(
    "IFDS_PT_EVENT_DIR", tempfile.mkdtemp(prefix="ifds_pt_events_")
)
