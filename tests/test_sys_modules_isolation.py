"""Regression guard: a ``patch.dict("sys.modules", ...)`` block must not orphan
numpy's C-extension (test_pipeline_e2e ordering-leak, 2026-07-24).

Root cause (verified — NOT the config-dict hypothesis)
------------------------------------------------------
``unittest.mock._patch_dict._unpatch_dict`` restores by ``_clear_dict(sys.modules)``
+ ``update(entry_snapshot)``. So any module imported *during* a
``patch.dict("sys.modules", {...})`` block that was absent from the entry snapshot
is dropped on exit.

``scripts/paper_trading/close_positions.py::main()`` lazily imports
``ifds.utils.calendar`` (→ ``exchange_calendars`` → ``numpy``) at line ~317.
``tests/test_close_positions_split.py`` calls ``main()`` inside a
``patch.dict("sys.modules", {"lib": ..., "ib_insync": ...})`` block. When numpy is
not yet loaded (entry snapshot lacks it), the block loads it and the restore drops
``numpy._core._multiarray_umath`` — but the C-extension is already initialised in
the process. A later ``import numpy`` (e.g. ``test_pipeline_e2e`` → ``run_pipeline``
→ calendar) then fails with ``ImportError: cannot load module more than once per
process``. The full suite passes only because an earlier test happens to load numpy
first (it lands in every subsequent snapshot); the leak surfaces on specific file
subsets — an ordering-dependent flake.

Fix
---
``tests/conftest.py`` eagerly imports the numpy chain at collection time, so numpy
is present in *every* ``patch.dict("sys.modules")`` entry snapshot and can never be
orphaned — regardless of test order. Structural, behaviour-invariant, test-only
(the [[test-env-hygiene]] pattern applied to sys.modules / C-extensions).
"""

import sys
from unittest.mock import MagicMock, patch


def test_numpy_preloaded_by_conftest():
    """conftest eagerly loads numpy so patch.dict('sys.modules') snapshots contain
    it — the deterministic guard on the fix."""
    assert "numpy" in sys.modules, (
        "conftest.py must eager-import numpy so a patch.dict('sys.modules') block "
        "that lazily imports numpy cannot orphan its C-extension"
    )
    assert "numpy._core._multiarray_umath" in sys.modules


def test_patch_dict_sys_modules_does_not_orphan_numpy():
    """Reproduction: a patch.dict('sys.modules') block that lazily imports the
    calendar→numpy chain must leave numpy importable afterwards."""
    with patch.dict(
        "sys.modules",
        {"lib": MagicMock(), "lib.connection": MagicMock(), "ib_insync": MagicMock()},
    ):
        import ifds.utils.calendar  # noqa: F401  (→ exchange_calendars → numpy)

    import numpy  # raises "cannot load module more than once" if orphaned

    assert numpy.__version__
