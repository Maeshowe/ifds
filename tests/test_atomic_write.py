"""Tests for atomic file write helpers (F-16/17)."""

import json
import pytest

from ifds.utils.io import atomic_write_json


class TestAtomicWriteJson:

    def test_creates_file(self, tmp_path):
        path = tmp_path / "test.json"
        atomic_write_json(path, {"key": "value"})
        assert path.exists()
        assert json.loads(path.read_text()) == {"key": "value"}

    def test_overwrites_existing(self, tmp_path):
        path = tmp_path / "existing.json"
        path.write_text('{"original": true}')
        atomic_write_json(path, {"new": "data"})
        assert json.loads(path.read_text()) == {"new": "data"}

    def test_no_leftover_tmp_files(self, tmp_path):
        path = tmp_path / "clean.json"
        atomic_write_json(path, [1, 2, 3])
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "file.json"
        atomic_write_json(path, {"nested": True})
        assert path.exists()
        assert json.loads(path.read_text()) == {"nested": True}

    def test_list_data(self, tmp_path):
        path = tmp_path / "list.json"
        atomic_write_json(path, [{"a": 1}, {"b": 2}])
        assert json.loads(path.read_text()) == [{"a": 1}, {"b": 2}]


try:
    import pandas as pd
    _PANDAS_AVAILABLE = True
except ImportError:
    _PANDAS_AVAILABLE = False

_skip_no_pandas = pytest.mark.skipif(not _PANDAS_AVAILABLE, reason="pandas not installed")


@_skip_no_pandas
class TestAtomicWriteParquet:

    def test_creates_parquet(self, tmp_path):
        from ifds.utils.io import atomic_write_parquet
        df = pd.DataFrame({"ticker": ["AAPL"], "date": ["2026-01-01"]})
        path = tmp_path / "test.parquet"
        atomic_write_parquet(path, df)
        result = pd.read_parquet(path)
        assert list(result["ticker"]) == ["AAPL"]

    def test_no_leftover_tmp(self, tmp_path):
        from ifds.utils.io import atomic_write_parquet
        df = pd.DataFrame({"x": [1, 2, 3]})
        path = tmp_path / "clean.parquet"
        atomic_write_parquet(path, df)
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0
