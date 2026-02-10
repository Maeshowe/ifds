"""Tests for FileCache — file-based API response caching."""

import json
import os
import time
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from ifds.data.cache import FileCache


@pytest.fixture
def cache(tmp_path):
    return FileCache(cache_dir=str(tmp_path / "cache"))


class TestFileCacheGet:
    def test_cache_miss_returns_none(self, cache):
        """Non-existent file → None."""
        assert cache.get("polygon", "aggregates", "2026-02-08", "AAPL") is None

    def test_today_always_returns_none(self, cache):
        """Today's date is never cached."""
        today = date.today().isoformat()
        # Even if file exists, should return None for today
        cache.put("polygon", "aggregates", "2026-01-01", "AAPL", {"results": [1]})
        assert cache.get("polygon", "aggregates", today, "AAPL") is None

    def test_cache_hit_returns_data(self, cache):
        """Put then get → returns same data."""
        data = {"results": [{"c": 150.0}]}
        cache.put("polygon", "aggregates", "2026-02-07", "AAPL", data)
        result = cache.get("polygon", "aggregates", "2026-02-07", "AAPL")
        assert result == data

    def test_cache_hit_list_data(self, cache):
        """Cache works with list responses too."""
        data = [{"ticker": "AAPL", "size": "500"}]
        cache.put("fmp", "insider-trading", "2026-02-07", "AAPL", data)
        result = cache.get("fmp", "insider-trading", "2026-02-07", "AAPL")
        assert result == data

    def test_corrupt_json_returns_none(self, cache):
        """Corrupted cache file → None (not exception)."""
        path = cache._path("polygon", "aggregates", "2026-02-07", "AAPL")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write("not valid json{{{")
        assert cache.get("polygon", "aggregates", "2026-02-07", "AAPL") is None


class TestFileCachePut:
    def test_put_none_is_noop(self, cache):
        """put(data=None) should not create a file."""
        cache.put("polygon", "aggregates", "2026-02-07", "AAPL", None)
        path = cache._path("polygon", "aggregates", "2026-02-07", "AAPL")
        assert not path.exists()

    def test_put_today_is_noop(self, cache):
        """put() for today's date should not create a file."""
        today = date.today().isoformat()
        cache.put("polygon", "aggregates", today, "AAPL", {"data": 1})
        path = cache._path("polygon", "aggregates", today, "AAPL")
        assert not path.exists()

    def test_atomic_write_creates_file(self, cache):
        """put() creates valid JSON file at correct path."""
        data = {"results": [1, 2, 3]}
        cache.put("fmp", "key-metrics", "2026-02-07", "NVDA", data)
        path = cache._path("fmp", "key-metrics", "2026-02-07", "NVDA")
        assert path.exists()
        with open(path) as f:
            assert json.load(f) == data

    def test_endpoint_sanitization(self, cache):
        """Endpoint slashes are replaced with underscores."""
        cache.put("polygon", "/v2/aggs/ticker", "2026-02-07", "AAPL", {"x": 1})
        path = cache._path("polygon", "/v2/aggs/ticker", "2026-02-07", "AAPL")
        # Path should contain "v2_aggs_ticker" not literal slashes
        assert "v2_aggs_ticker" in str(path)
        assert path.exists()

    def test_symbol_with_colon(self, cache):
        """Symbols like I:VIX should be sanitized."""
        cache.put("polygon", "aggregates", "2026-02-07", "I:VIX", {"c": 20.0})
        result = cache.get("polygon", "aggregates", "2026-02-07", "I:VIX")
        assert result == {"c": 20.0}


class TestFileCacheCleanup:
    def test_cleanup_deletes_old_files(self, cache):
        """Files older than max_age_days are deleted."""
        # Create a cache file
        cache.put("polygon", "aggregates", "2026-01-01", "AAPL", {"data": 1})
        path = cache._path("polygon", "aggregates", "2026-01-01", "AAPL")

        # Set mtime to 10 days ago
        old_time = time.time() - (10 * 86400)
        os.utime(str(path), (old_time, old_time))

        deleted = cache.cleanup(max_age_days=7)
        assert deleted == 1
        assert not path.exists()

    def test_cleanup_keeps_recent_files(self, cache):
        """Files newer than max_age_days are kept."""
        cache.put("polygon", "aggregates", "2026-02-07", "AAPL", {"data": 1})
        deleted = cache.cleanup(max_age_days=7)
        assert deleted == 0
        assert cache.get("polygon", "aggregates", "2026-02-07", "AAPL") is not None

    def test_cleanup_empty_cache_dir(self, cache):
        """Cleanup on non-existent dir returns 0."""
        assert cache.cleanup() == 0

    def test_cleanup_removes_empty_dirs(self, cache):
        """After deleting files, empty directories are cleaned up."""
        cache.put("polygon", "aggregates", "2026-01-01", "AAPL", {"data": 1})
        path = cache._path("polygon", "aggregates", "2026-01-01", "AAPL")

        old_time = time.time() - (10 * 86400)
        os.utime(str(path), (old_time, old_time))

        cache.cleanup(max_age_days=7)
        # The date directory should be removed
        assert not path.parent.exists()


class TestFileCacheDifferentProviders:
    def test_same_symbol_different_providers(self, cache):
        """Same symbol cached separately per provider."""
        cache.put("polygon", "aggregates", "2026-02-07", "AAPL", {"source": "polygon"})
        cache.put("fmp", "aggregates", "2026-02-07", "AAPL", {"source": "fmp"})

        r1 = cache.get("polygon", "aggregates", "2026-02-07", "AAPL")
        r2 = cache.get("fmp", "aggregates", "2026-02-07", "AAPL")
        assert r1["source"] == "polygon"
        assert r2["source"] == "fmp"
