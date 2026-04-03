"""Shared daily-rotated logging setup for paper trading scripts.

Every PT script calls ``setup_pt_logger("script_name")`` once at import time.
Log files: ``logs/pt_{script_name}_{YYYY-MM-DD}.log`` (project root).
Console output preserved for cron job monitoring.
"""

import logging
import os
from datetime import date


def setup_pt_logger(
    script_name: str,
    log_dir: str = "logs",
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
    level:
        Logging level (default ``INFO``).

    Returns
    -------
    logging.Logger
        Configured logger with file + console handlers.
    """
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
