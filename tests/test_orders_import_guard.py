"""Regression: lib/orders.py must cold-import without a current event loop.

lib/orders.py imports ib_insync at module level. On Python 3.14+,
`asyncio.get_event_loop()` no longer auto-creates a loop on the main thread —
it raises RuntimeError — and ib_insync's package import calls it. Without a
guard, `import lib.orders` crashes when it is the first ib_insync import in the
process (i.e. imported before lib/connection.py runs its own guard).

This runs in a fresh subprocess with the current event loop cleared, so it
reproduces the loop-less main-thread condition. On 3.14 it fails if the guard
is removed; on <3.14 it is a clean-import smoke. The Mac Mini deploy pre-flight
runs pytest on 3.14, so this catches a real production regression there.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_PT_DIR = Path(__file__).resolve().parent.parent / "scripts" / "paper_trading"


def test_orders_cold_imports_without_event_loop():
    snippet = (
        "import asyncio; asyncio.set_event_loop(None); "
        "import lib.orders; "
        "print('ORDERS_IMPORT_OK')"
    )
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        cwd=str(_PT_DIR),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"lib.orders failed to cold-import (guard regression?).\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "ORDERS_IMPORT_OK" in result.stdout
