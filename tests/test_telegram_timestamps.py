"""Tests for Telegram timestamp headers (pipeline + PT scripts)."""

import re
from unittest.mock import patch, MagicMock
from datetime import datetime

import pytest

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]


class TestPipelineTimestamp:
    """Tests for _pipeline_timestamp() in telegram.py."""

    def test_format(self):
        from ifds.output.telegram import _pipeline_timestamp
        result = _pipeline_timestamp()
        # Should match [YYYY-MM-DD HH:MM CET] PIPELINE
        assert re.match(r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2} CET\] PIPELINE", result)

    def test_contains_pipeline_label(self):
        from ifds.output.telegram import _pipeline_timestamp
        assert "PIPELINE" in _pipeline_timestamp()


class TestTelegramHelper:
    """Tests for telegram_header() in PT lib."""

    def test_format(self):
        import sys
        import os
        # Ensure scripts/paper_trading/lib is importable
        pt_lib = os.path.join(os.path.dirname(__file__), "..",
                              "scripts", "paper_trading")
        if pt_lib not in sys.path:
            sys.path.insert(0, os.path.abspath(pt_lib))

        from lib.telegram_helper import telegram_header
        result = telegram_header("SUBMIT")
        assert re.match(r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2} CET\] SUBMIT", result)

    def test_different_script_names(self):
        import sys
        import os
        pt_lib = os.path.join(os.path.dirname(__file__), "..",
                              "scripts", "paper_trading")
        if pt_lib not in sys.path:
            sys.path.insert(0, os.path.abspath(pt_lib))

        from lib.telegram_helper import telegram_header
        for name in ["SUBMIT", "CLOSE", "MONITOR", "EOD", "AVWAP", "LEFTOVER"]:
            result = telegram_header(name)
            assert name in result
            assert "CET" in result

    def test_uses_cet_timezone(self):
        import sys
        import os
        pt_lib = os.path.join(os.path.dirname(__file__), "..",
                              "scripts", "paper_trading")
        if pt_lib not in sys.path:
            sys.path.insert(0, os.path.abspath(pt_lib))

        from lib.telegram_helper import telegram_header
        result = telegram_header("TEST")
        # Should use CET/CEST (Europe/Budapest)
        assert "CET" in result
