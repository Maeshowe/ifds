"""FRL factor library.

Import a factor module for its side effect (registration), then look it up via
``factors.base.get(name)``. The batch imports every module listed in
``LOADABLE`` so that a factor cannot be tested without being registered.
"""

from __future__ import annotations

import importlib

# Factor modules the batch loads. Adding a factor means adding it here, which
# keeps the registry explicit and reviewable.
LOADABLE: tuple[str, ...] = ("reversal", "sj_live")


def load_all() -> None:
    """Import every registered factor module (idempotent)."""
    for module in LOADABLE:
        importlib.import_module(f"factors.{module}")
