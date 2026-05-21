"""Regression tests — scripts/paper_trading/lib/log_setup.py test isolation.

Background
----------
The 2026-05-18 `logs/pt_monitor_2026-05-18.log` and 2026-05-19 daily logs
contained legacy LION/SDRL Trail SL / LOSS_EXIT replay events at exactly
the timestamps when manual `deploy_daily.sh --phases 1-3` ran on Mac Mini.
Root cause: ``setup_pt_logger("monitor")`` (called at module-import time)
bound a FileHandler to ``logs/pt_monitor_YYYY-MM-DD.log`` (the production
file), and the test fixtures in ``test_pt_monitor*.py`` invoked logger
methods through the imported module — leaking test output into the live
production log.

Fix
---
``_resolve_log_dir`` in ``log_setup.py`` redirects to a temp dir when
``PYTEST_CURRENT_TEST`` is set (or honors ``IFDS_PT_LOG_DIR`` override).

Refs:
- docs/review/2026-05-18-daily-review.md §6 Anomália #1
- docs/tasks/2026-05-19-pt-monitor-replay-diagnosis.md
- docs/master-reference/04-risks-and-open-questions.md §8.1.6
"""

import logging
import os
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _reset_logger_cache():
    """Ensure each test gets a fresh logger by clearing the cache."""
    yield
    # Reset the loggers created during the test
    for name in ("test_iso_monitor", "test_iso_submit", "test_iso_eod"):
        log = logging.getLogger(name)
        for handler in list(log.handlers):
            log.removeHandler(handler)
            handler.close()


def _import_setup_pt_logger():
    """Import setup_pt_logger from scripts.paper_trading.lib.log_setup."""
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts", "paper_trading")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    # Re-import to get latest module state
    sys.modules.pop("lib.log_setup", None)
    from lib.log_setup import setup_pt_logger

    return setup_pt_logger


def test_log_file_redirected_to_tempdir_under_pytest():
    """Under pytest, FileHandler should NOT write to project ./logs/.

    PYTEST_CURRENT_TEST is auto-set by pytest. The setup_pt_logger function
    must detect this and redirect log_dir to a temp directory.
    """
    assert "PYTEST_CURRENT_TEST" in os.environ, "Sanity: pytest must set this"

    setup_pt_logger = _import_setup_pt_logger()
    logger = setup_pt_logger("test_iso_monitor")

    file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
    assert file_handlers, "Expected at least one FileHandler"

    for fh in file_handlers:
        path = Path(fh.baseFilename).resolve()
        assert not str(path).startswith(str(Path.cwd().resolve() / "logs")), (
            f"FileHandler wrote to production logs/ directory: {path}. "
            "Test log emissions would pollute production cron logs."
        )


def test_log_dir_honors_ifds_pt_log_dir_override(monkeypatch, tmp_path):
    """IFDS_PT_LOG_DIR env var should override the default tmp redirect."""
    monkeypatch.setenv("IFDS_PT_LOG_DIR", str(tmp_path))

    setup_pt_logger = _import_setup_pt_logger()
    logger = setup_pt_logger("test_iso_submit")

    file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
    assert file_handlers, "Expected at least one FileHandler"

    for fh in file_handlers:
        path = Path(fh.baseFilename).resolve()
        assert str(path).startswith(
            str(tmp_path.resolve())
        ), f"FileHandler wrote to {path}, expected under {tmp_path}"


def test_log_dir_default_tmp_path_when_pytest_no_override(monkeypatch):
    """Default temp redirect should land in system tmpdir/ifds_pt_logs_test."""
    monkeypatch.delenv("IFDS_PT_LOG_DIR", raising=False)

    setup_pt_logger = _import_setup_pt_logger()
    logger = setup_pt_logger("test_iso_eod")

    file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
    assert file_handlers, "Expected at least one FileHandler"

    expected_prefix = os.path.join(tempfile.gettempdir(), "ifds_pt_logs_test")
    for fh in file_handlers:
        path = Path(fh.baseFilename).resolve()
        assert str(path).startswith(
            str(Path(expected_prefix).resolve())
        ), f"FileHandler wrote to {path}, expected under {expected_prefix}"


def test_resolve_log_dir_returns_original_outside_pytest(monkeypatch):
    """When PYTEST_CURRENT_TEST is unset, original log_dir must be returned.

    This protects production cron behavior — the redirect must ONLY engage
    inside the pytest process.
    """
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("IFDS_PT_LOG_DIR", raising=False)

    sys.modules.pop("lib.log_setup", None)
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts", "paper_trading")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from lib.log_setup import _resolve_log_dir

    assert _resolve_log_dir("logs") == "logs"
    assert _resolve_log_dir("/some/abs/path") == "/some/abs/path"


def test_setup_pt_logger_does_not_create_logs_dir_under_pytest(monkeypatch, tmp_path):
    """Verify os.makedirs(log_dir) target points to tmp, not ./logs/."""
    monkeypatch.setenv("IFDS_PT_LOG_DIR", str(tmp_path / "redirected"))

    setup_pt_logger = _import_setup_pt_logger()
    setup_pt_logger("test_iso_monitor")

    assert (tmp_path / "redirected").exists(), "Redirected dir should be created"
