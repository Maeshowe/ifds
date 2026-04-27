"""Unit tests for MID bundle snapshot save/load."""
from __future__ import annotations

import gzip
import json
from datetime import date
from pathlib import Path

import pytest


@pytest.fixture
def sample_bundle() -> dict:
    return {
        "flat": {"regime": "STAGFLATION", "tpi": 43},
        "etf_xray": {
            "sectors": [
                {"etf": "XLK", "consensus_state": "OVERWEIGHT"},
            ],
        },
    }


class TestSaveBundleSnapshot:

    def test_roundtrip(self, tmp_path: Path, sample_bundle: dict) -> None:
        from ifds.data.mid_bundle_snapshot import (
            load_bundle_snapshot,
            save_bundle_snapshot,
        )

        target = date(2026, 4, 27)
        out = save_bundle_snapshot(sample_bundle, target, tmp_path)
        assert out is not None
        assert out.exists()
        assert out.name == "2026-04-27.json.gz"

        loaded = load_bundle_snapshot(target, tmp_path)
        assert loaded == sample_bundle

    def test_empty_bundle_returns_none(self, tmp_path: Path) -> None:
        from ifds.data.mid_bundle_snapshot import save_bundle_snapshot

        assert save_bundle_snapshot({}, date(2026, 4, 27), tmp_path) is None
        assert not list(tmp_path.iterdir())

    def test_non_dict_returns_none(self, tmp_path: Path) -> None:
        from ifds.data.mid_bundle_snapshot import save_bundle_snapshot

        assert save_bundle_snapshot("not a dict", date(2026, 4, 27), tmp_path) is None  # type: ignore[arg-type]

    def test_creates_directory(self, tmp_path: Path,
                               sample_bundle: dict) -> None:
        from ifds.data.mid_bundle_snapshot import save_bundle_snapshot

        nested = tmp_path / "nested" / "subdir"
        out = save_bundle_snapshot(sample_bundle, date(2026, 4, 27), nested)
        assert out is not None
        assert nested.is_dir()

    def test_gzip_compression(self, tmp_path: Path,
                              sample_bundle: dict) -> None:
        """File must be valid gzip + JSON."""
        from ifds.data.mid_bundle_snapshot import save_bundle_snapshot

        out = save_bundle_snapshot(sample_bundle, date(2026, 4, 27), tmp_path)
        assert out is not None
        with gzip.open(out, "rt", encoding="utf-8") as f:
            assert json.load(f) == sample_bundle


class TestLoadBundleSnapshot:

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        from ifds.data.mid_bundle_snapshot import load_bundle_snapshot

        assert load_bundle_snapshot(date(2026, 4, 27), tmp_path) is None

    def test_corrupt_gzip_returns_none(self, tmp_path: Path) -> None:
        from ifds.data.mid_bundle_snapshot import load_bundle_snapshot

        bad = tmp_path / "2026-04-27.json.gz"
        bad.write_bytes(b"not gzip data")
        assert load_bundle_snapshot(date(2026, 4, 27), tmp_path) is None

    def test_non_dict_returns_none(self, tmp_path: Path) -> None:
        from ifds.data.mid_bundle_snapshot import load_bundle_snapshot

        path = tmp_path / "2026-04-27.json.gz"
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(["a", "list"], f)
        assert load_bundle_snapshot(date(2026, 4, 27), tmp_path) is None
