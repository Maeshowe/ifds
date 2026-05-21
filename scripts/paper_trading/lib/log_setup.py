"""Shared daily-rotated logging setup for paper trading scripts.

Every PT script calls ``setup_pt_logger("script_name")`` once at import time.
Log files: ``logs/pt_{script_name}_{YYYY-MM-DD}.log`` (project root).
Console output preserved for cron job monitoring.

Test isolation
--------------
When running under pytest, the FileHandler is redirected to a temp directory
(``$IFDS_PT_LOG_DIR`` or ``/tmp/ifds_pt_logs_test``).  Without this, every
test that imports a paper-trading script would bind a FileHandler to the
production ``logs/pt_*_YYYY-MM-DD.log`` file at module-import time, and any
``logger.info()`` call during the test would leak into the production log
(see ``docs/review/2026-05-18-daily-review.md`` §6 anomália #1 for the
LION/SDRL replay incident).
"""

import logging
import os
import tempfile
from datetime import date

_DEFAULT_LOG_DIR = "logs"


def _resolve_log_dir(log_dir: str) -> str:
    """Redirect default log_dir to a temp dir when running under pytest.

    Why: tests import scripts.paper_trading.pt_monitor (and others), which
    binds a FileHandler to ``logs/pt_*_YYYY-MM-DD.log`` at import time.
    Without this guard, test log emissions leak into the production log
    file and look like real cron-driven events.

    The redirect only engages when:
      1. PYTEST_CURRENT_TEST is set (i.e. running under pytest), AND
      2. log_dir is the implicit default ("logs") — explicit caller-
         supplied paths (e.g. ``tmp_path`` from a test fixture) pass
         through unchanged so existing log_setup tests still work.
    """
    if "PYTEST_CURRENT_TEST" not in os.environ:
        return log_dir
    if log_dir != _DEFAULT_LOG_DIR:
        return log_dir
    override = os.environ.get("IFDS_PT_LOG_DIR")
    if override:
        return override
    return os.path.join(tempfile.gettempdir(), "ifds_pt_logs_test")


def setup_pt_logger(
    script_name: str,
    log_dir: str = _DEFAULT_LOG_DIR,
    level: int = logging.INFO,
) -> logging.Logger:
    """Create a daily-rotated logger for a paper trading script.

    Parameters
    ----------
    script_name:
        Short identifier (e.g. ``"submit"``, ``"monitor"``).  Used in the
        log filename and as the logger name.
    log_dir:
        Directory for log files (default ``logs/`` at project root).
        Overridden to a temp dir when running under pytest.
    level:
        Logging level (default ``INFO``).

    Returns
    -------
    logging.Logger
        Configured logger with file + console handlers.
    """
    log_dir = _resolve_log_dir(log_dir)
    today = date.today().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"pt_{script_name}_{today}.log")

    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(script_name)
    logger.setLevel(level)

    # Avoid duplicate handlers on repeated calls (e.g. tests)
    if logger.handlers:
        return logger

    file_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    fh = logging.FileHandler(log_file)
    fh.setFormatter(file_fmt)
    fh.setLevel(level)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(console_fmt)
    ch.setLevel(level)
    logger.addHandler(ch)

    return logger
