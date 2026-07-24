"""Global test configuration — shared fixtures and environment setup."""

import os
import tempfile

# Disable trading day guard in all tests (production guard exits on NYSE holidays)
os.environ["IFDS_SKIP_TRADING_DAY_GUARD"] = "1"

# Redirect the paper-trading event log away from production logs/ (test-env-hygiene P1,
# 2026-07-23 review §6). scripts/paper_trading/*.py instantiate a module-level
# ``evt = PTEventLogger()`` at *import* time, so this must be set before collection —
# a session-scope fixture runs too late. setdefault preserves an explicit override.
os.environ.setdefault(
    "IFDS_PT_EVENT_DIR", tempfile.mkdtemp(prefix="ifds_pt_events_")
)
