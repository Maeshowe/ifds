"""Integration tests for the Phase 0 MID bundle hook.

The hook must be **non-blocking** under all failure modes — Phase 0
must continue normally if MID is unavailable, has a bad key, or the
client raises an unexpected exception.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def fake_logger() -> MagicMock:
    """Logger stub matching the EventLogger surface used in Phase 0."""
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


@pytest.fixture
def config_no_mid_key() -> MagicMock:
    cfg = MagicMock()
    cfg.get_api_key = MagicMock(return_value=None)
    cfg.runtime = {"api_timeout_mid": 10}
    return cfg


@pytest.fixture
def config_with_mid_key() -> MagicMock:
    cfg = MagicMock()
    cfg.get_api_key = MagicMock(return_value="fake-key")
    cfg.runtime = {"api_timeout_mid": 10}
    return cfg


class TestPhase0MidHookGracefulFailure:

    def test_no_key_skips_silently(self, config_no_mid_key, fake_logger):
        """No MID_API_KEY → DEBUG log, no exception, no snapshot saved."""
        from ifds.phases.phase0_diagnostics import _save_mid_bundle_if_configured

        # Should return without raising
        _save_mid_bundle_if_configured(config_no_mid_key, fake_logger)

        # Logged once at DEBUG level
        assert fake_logger.log.call_count == 1
        call = fake_logger.log.call_args
        # Severity is the second positional arg
        severity = call.args[1]
        assert "DEBUG" in str(severity).upper()

    def test_empty_bundle_warns_and_continues(self, config_with_mid_key, fake_logger):
        """MID returns {} → WARNING log, no snapshot saved, no raise."""
        from ifds.phases import phase0_diagnostics

        with patch.object(phase0_diagnostics, "_save_mid_bundle_if_configured",
                          wraps=phase0_diagnostics._save_mid_bundle_if_configured):
            with patch("ifds.data.mid_client.MIDClient") as mock_client_cls:
                mock_inst = MagicMock()
                mock_inst.get_bundle.return_value = {}
                mock_client_cls.return_value = mock_inst

                phase0_diagnostics._save_mid_bundle_if_configured(
                    config_with_mid_key, fake_logger,
                )

        # At least one WARNING was logged
        warnings = [
            c for c in fake_logger.log.call_args_list
            if "WARNING" in str(c.args[1]).upper()
        ]
        assert warnings, "expected a WARNING log when bundle is empty"

    def test_unexpected_exception_is_swallowed(self, config_with_mid_key, fake_logger):
        """Random error inside MIDClient → WARNING log, no raise."""
        from ifds.phases import phase0_diagnostics

        with patch("ifds.data.mid_client.MIDClient",
                   side_effect=RuntimeError("boom")):
            # Must not raise
            phase0_diagnostics._save_mid_bundle_if_configured(
                config_with_mid_key, fake_logger,
            )

        warnings = [
            c for c in fake_logger.log.call_args_list
            if "WARNING" in str(c.args[1]).upper()
        ]
        assert warnings, "expected a WARNING when MIDClient raises"

    def test_successful_save_logs_info(self, config_with_mid_key, fake_logger,
                                       tmp_path):
        """Happy path: bundle fetched, saved, INFO log mentions the path."""
        from ifds.phases import phase0_diagnostics
        from ifds.data import mid_bundle_snapshot

        sample = {"flat": {"regime": "STAGFLATION"}}

        with patch("ifds.data.mid_client.MIDClient") as mock_client_cls, \
             patch.object(mid_bundle_snapshot, "SNAPSHOT_DIR", tmp_path):
            mock_inst = MagicMock()
            mock_inst.get_bundle.return_value = sample
            mock_client_cls.return_value = mock_inst

            phase0_diagnostics._save_mid_bundle_if_configured(
                config_with_mid_key, fake_logger,
            )

        # File exists in tmp_path
        gz_files = list(tmp_path.glob("*.json.gz"))
        assert len(gz_files) == 1

        # An INFO log mentions the saved path
        infos = [
            c for c in fake_logger.log.call_args_list
            if "INFO" in str(c.args[1]).upper()
        ]
        assert infos, "expected an INFO log on successful save"
        info_msg = " ".join(
            str(c.kwargs.get("message", "")) for c in infos
        )
        assert "MID bundle saved" in info_msg
