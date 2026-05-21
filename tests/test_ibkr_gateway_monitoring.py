"""Tests for IBKR Gateway monitoring infra.

Covers:
* §11 anti-pattern fix — `_send_telegram_alert` logs WARNING instead of
  silently swallowing failures (env-var missing, HTTP 4xx, exception).
* Fix C heartbeat — `lib.heartbeat.touch/read` + `monitor_submit_heartbeat`
  verdict logic (OK / STUCK / MISSING / COLD_START).
* `connect()` context_label propagates into the alert body.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# §11 — Telegram silent-swallow anti-pattern fix
# ---------------------------------------------------------------------------


class TestSendTelegramAlertLogging:
    def test_warns_when_env_vars_missing(self, monkeypatch, caplog):
        monkeypatch.delenv("IFDS_TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("IFDS_TELEGRAM_CHAT_ID", raising=False)
        from scripts.paper_trading.lib.connection import _send_telegram_alert

        with caplog.at_level(logging.WARNING, logger="scripts.paper_trading.lib.connection"):
            _send_telegram_alert("test message")

        assert any("Telegram alert NOT sent" in r.message for r in caplog.records)

    def test_warns_on_http_error(self, monkeypatch, caplog):
        monkeypatch.setenv("IFDS_TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.setenv("IFDS_TELEGRAM_CHAT_ID", "chat")

        mock_resp = MagicMock(status_code=403, text="forbidden")
        with (
            patch("requests.post", return_value=mock_resp),
            caplog.at_level(logging.WARNING, logger="scripts.paper_trading.lib.connection"),
        ):
            from scripts.paper_trading.lib.connection import _send_telegram_alert

            _send_telegram_alert("test message")

        joined = " ".join(r.message for r in caplog.records)
        assert "HTTP 403" in joined
        assert "forbidden" in joined

    def test_warns_on_exception(self, monkeypatch, caplog):
        monkeypatch.setenv("IFDS_TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.setenv("IFDS_TELEGRAM_CHAT_ID", "chat")

        with (
            patch("requests.post", side_effect=ConnectionError("net down")),
            caplog.at_level(logging.WARNING, logger="scripts.paper_trading.lib.connection"),
        ):
            from scripts.paper_trading.lib.connection import _send_telegram_alert

            _send_telegram_alert("test message")

        joined = " ".join(r.message for r in caplog.records)
        assert "Telegram alert send failed" in joined
        assert "net down" in joined

    def test_silent_on_success(self, monkeypatch, caplog):
        monkeypatch.setenv("IFDS_TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.setenv("IFDS_TELEGRAM_CHAT_ID", "chat")

        mock_resp = MagicMock(status_code=200, text="ok")
        with (
            patch("requests.post", return_value=mock_resp),
            caplog.at_level(logging.WARNING, logger="scripts.paper_trading.lib.connection"),
        ):
            from scripts.paper_trading.lib.connection import _send_telegram_alert

            _send_telegram_alert("test message")

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings == []


# ---------------------------------------------------------------------------
# connect() context_label
# ---------------------------------------------------------------------------


class TestConnectContextLabel:
    def test_label_propagates_into_alert_body(self):
        mock_ib = MagicMock()
        mock_ib.connect.side_effect = Exception("gateway down")
        with (
            patch("scripts.paper_trading.lib.connection.IB", return_value=mock_ib),
            patch("scripts.paper_trading.lib.connection.time.sleep"),
            patch("scripts.paper_trading.lib.connection._send_telegram_alert") as mock_tg,
        ):
            from scripts.paper_trading.lib.connection import connect

            with pytest.raises(SystemExit):
                connect(
                    client_id=17,
                    max_retries=1,
                    retry_delay=0,
                    context_label="PRE-FLIGHT Gateway health check",
                )

        alert_msg = mock_tg.call_args[0][0]
        assert "PRE-FLIGHT Gateway health check" in alert_msg


# ---------------------------------------------------------------------------
# Fix C — heartbeat lib
# ---------------------------------------------------------------------------


class TestHeartbeatTouchAndRead:
    def test_touch_writes_atomic_json(self, tmp_path: Path):
        from scripts.paper_trading.lib.heartbeat import touch, read

        touch("submit_attempt", label="2026-05-18", state_dir=tmp_path)
        payload = read("submit_attempt", state_dir=tmp_path)

        assert payload is not None
        assert payload["event"] == "submit_attempt"
        assert payload["label"] == "2026-05-18"
        assert "timestamp_utc" in payload
        assert isinstance(payload["epoch"], int)

    def test_read_returns_none_when_missing(self, tmp_path: Path):
        from scripts.paper_trading.lib.heartbeat import read

        assert read("nonexistent", state_dir=tmp_path) is None

    def test_extra_payload_persisted(self, tmp_path: Path):
        from scripts.paper_trading.lib.heartbeat import touch, read

        touch("submit_success", state_dir=tmp_path, extra={"submitted_count": 8})
        payload = read("submit_success", state_dir=tmp_path)

        assert payload["submitted_count"] == 8

    def test_touch_failure_logs_warning_does_not_raise(self, tmp_path: Path, caplog):
        from scripts.paper_trading.lib.heartbeat import touch

        bad_dir = tmp_path / "ro"
        bad_dir.mkdir()
        with (
            patch("pathlib.Path.mkdir", side_effect=OSError("read-only fs")),
            caplog.at_level(logging.WARNING, logger="scripts.paper_trading.lib.heartbeat"),
        ):
            touch("submit_attempt", state_dir=bad_dir)

        assert any("Heartbeat write failed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Fix C — monitor verdict logic
# ---------------------------------------------------------------------------


def _write_heartbeat(state_dir: Path, event: str, epoch: int) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / f"last_{event}.json"
    path.write_text(
        json.dumps(
            {
                "event": event,
                "label": "test",
                "timestamp_utc": "2026-05-18T13:35:00+00:00",
                "epoch": epoch,
            }
        )
    )


class TestHeartbeatMonitor:
    def test_cold_start_when_both_missing(self, tmp_path: Path):
        from scripts.paper_trading.monitor_submit_heartbeat import check_heartbeat

        verdict, msg = check_heartbeat(now_epoch=1_700_000_000.0, state_dir=tmp_path)
        assert verdict == "COLD_START"

    def test_ok_when_success_after_attempt(self, tmp_path: Path):
        from scripts.paper_trading.monitor_submit_heartbeat import check_heartbeat

        _write_heartbeat(tmp_path, "submit_attempt", 1_700_000_000)
        _write_heartbeat(tmp_path, "submit_success", 1_700_000_120)

        verdict, _ = check_heartbeat(now_epoch=1_700_000_300.0, state_dir=tmp_path)
        assert verdict == "OK"

    def test_stuck_when_attempt_newer_than_success(self, tmp_path: Path):
        from scripts.paper_trading.monitor_submit_heartbeat import check_heartbeat

        # Yesterday's success, today's attempt, no completion
        _write_heartbeat(tmp_path, "submit_success", 1_699_900_000)
        _write_heartbeat(tmp_path, "submit_attempt", 1_700_000_000)

        verdict, msg = check_heartbeat(
            now_epoch=1_700_000_600.0, state_dir=tmp_path, stuck_threshold_s=300
        )
        assert verdict == "STUCK"
        assert "STUCK" in msg

    def test_stuck_when_no_success_at_all(self, tmp_path: Path):
        from scripts.paper_trading.monitor_submit_heartbeat import check_heartbeat

        _write_heartbeat(tmp_path, "submit_attempt", 1_700_000_000)

        verdict, _ = check_heartbeat(now_epoch=1_700_000_600.0, state_dir=tmp_path)
        assert verdict == "STUCK"

    def test_missing_when_attempt_older_than_threshold(self, tmp_path: Path):
        from scripts.paper_trading.monitor_submit_heartbeat import check_heartbeat

        # Attempt 30h ago, success 30h ago — script ran yesterday but not today
        old_epoch = int(time.time()) - 30 * 3600
        _write_heartbeat(tmp_path, "submit_attempt", old_epoch)
        _write_heartbeat(tmp_path, "submit_success", old_epoch + 60)

        verdict, msg = check_heartbeat(state_dir=tmp_path, missing_threshold_s=26 * 3600)
        assert verdict == "MISSING"
        assert "DID NOT RUN" in msg

    def test_within_stuck_threshold_is_ok(self, tmp_path: Path):
        """If attempt is just barely newer than success but inside threshold,
        we treat it as OK (race window between disconnect and success write)."""
        from scripts.paper_trading.monitor_submit_heartbeat import check_heartbeat

        _write_heartbeat(tmp_path, "submit_success", 1_700_000_000)
        _write_heartbeat(tmp_path, "submit_attempt", 1_700_000_010)

        verdict, _ = check_heartbeat(
            now_epoch=1_700_000_100.0, state_dir=tmp_path, stuck_threshold_s=300
        )
        assert verdict == "OK"
