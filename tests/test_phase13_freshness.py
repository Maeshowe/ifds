"""Tests — Task #E Phase 1-3 weekly freshness check.

Pure-function tests for ``classify_freshness`` — no Telegram, no IO mocking
beyond ``Path.stat()``.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest


@pytest.fixture
def classify():
    """Load classify_freshness without executing main()."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "check_phase13_freshness",
        "scripts/check_phase13_freshness.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.classify_freshness


def test_phase13_freshness_missing_file(tmp_path, classify):
    """File NEM létezik → status='missing'."""
    missing = tmp_path / "absent.json.gz"
    status, detail = classify(missing, datetime.now())
    assert status == "missing"
    assert "not found" in detail


def test_phase13_freshness_stale_file(tmp_path, classify):
    """File mtime > 1h → status='stale'."""
    ctx = tmp_path / "phase13_ctx.json.gz"
    ctx.write_bytes(b"x" * 10)
    # Force mtime to 2 hours ago
    two_hours_ago = (datetime.now() - timedelta(hours=2)).timestamp()
    import os

    os.utime(ctx, (two_hours_ago, two_hours_ago))

    status, detail = classify(ctx, datetime.now(), max_age_hours=1.0)
    assert status == "stale"
    assert "age" in detail


def test_phase13_freshness_fresh_file(tmp_path, classify):
    """File mtime < 1h → status='fresh'."""
    ctx = tmp_path / "phase13_ctx.json.gz"
    ctx.write_bytes(b"x" * 10)
    # mtime: 15 minutes ago
    fifteen_min_ago = (datetime.now() - timedelta(minutes=15)).timestamp()
    import os

    os.utime(ctx, (fifteen_min_ago, fifteen_min_ago))

    status, detail = classify(ctx, datetime.now(), max_age_hours=1.0)
    assert status == "fresh"


def test_phase13_freshness_just_over_threshold(tmp_path, classify):
    """File mtime = threshold + 1s → status='stale' (edge case)."""
    ctx = tmp_path / "phase13_ctx.json.gz"
    ctx.write_bytes(b"x" * 10)
    one_hour_one_sec_ago = (datetime.now() - timedelta(hours=1, seconds=1)).timestamp()
    import os

    os.utime(ctx, (one_hour_one_sec_ago, one_hour_one_sec_ago))

    status, _ = classify(ctx, datetime.now(), max_age_hours=1.0)
    assert status == "stale"


def test_phase13_freshness_just_under_threshold(tmp_path, classify):
    """File mtime = threshold - 1s → status='fresh' (edge case)."""
    ctx = tmp_path / "phase13_ctx.json.gz"
    ctx.write_bytes(b"x" * 10)
    one_hour_minus_30s_ago = (datetime.now() - timedelta(minutes=59, seconds=30)).timestamp()
    import os

    os.utime(ctx, (one_hour_minus_30s_ago, one_hour_minus_30s_ago))

    status, _ = classify(ctx, datetime.now(), max_age_hours=1.0)
    assert status == "fresh"
