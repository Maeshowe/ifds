"""Tests for scripts/paper_trading/lib/log_setup.py — daily-rotated logger."""

import logging
import sys
from datetime import date
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _ensure_lib_importable():
    """Add scripts/paper_trading to sys.path so ``from lib.log_setup`` works."""
    pt_dir = str(Path(__file__).resolve().parent.parent / "scripts" / "paper_trading")
    added = pt_dir not in sys.path
    if added:
        sys.path.insert(0, pt_dir)
    yield
    if added:
        sys.path.remove(pt_dir)


@pytest.fixture()
def _clean_logger():
    """Remove handlers after each test to avoid handler accumulation."""
    yield
    for name in ("test_script", "test_dup"):
        lgr = logging.getLogger(name)
        lgr.handlers.clear()


class TestSetupPtLogger:
    """setup_pt_logger creates file + console handlers with daily rotation."""

    def test_creates_log_file(self, tmp_path, _clean_logger):
        from lib.log_setup import setup_pt_logger

        logger = setup_pt_logger("test_script", log_dir=str(tmp_path))
        logger.info("hello")

        today = date.today().strftime("%Y-%m-%d")
        log_file = tmp_path / f"pt_test_script_{today}.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "hello" in content

    def test_file_has_date_in_timestamp(self, tmp_path, _clean_logger):
        from lib.log_setup import setup_pt_logger

        logger = setup_pt_logger("test_script", log_dir=str(tmp_path))
        logger.info("timestamp check")

        today = date.today().strftime("%Y-%m-%d")
        log_file = tmp_path / f"pt_test_script_{today}.log"
        first_line = log_file.read_text().strip().splitlines()[0]
        # File format: "YYYY-MM-DD HH:MM:SS [INFO] ..."
        assert first_line.startswith(today)

    def test_has_file_and_console_handlers(self, tmp_path, _clean_logger):
        from lib.log_setup import setup_pt_logger

        logger = setup_pt_logger("test_script", log_dir=str(tmp_path))
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "FileHandler" in handler_types
        assert "StreamHandler" in handler_types

    def test_no_duplicate_handlers(self, tmp_path, _clean_logger):
        from lib.log_setup import setup_pt_logger

        logger = setup_pt_logger("test_dup", log_dir=str(tmp_path))
        count_first = len(logger.handlers)
        setup_pt_logger("test_dup", log_dir=str(tmp_path))
        assert len(logger.handlers) == count_first

    def test_creates_log_dir(self, tmp_path, _clean_logger):
        from lib.log_setup import setup_pt_logger

        nested = tmp_path / "sub" / "logs"
        setup_pt_logger("test_script", log_dir=str(nested))
        assert nested.is_dir()
