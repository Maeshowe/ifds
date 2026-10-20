"""Universe provenance: F-2 (recorded) and F-5 (watched). Approved 2026-10-20.

Why these exist. Between 2026-08-16 and 2026-10-19 the Phase 1-3 context was FRESH
every single week and built on a silently substituted population: the membership
source had died and Phase 2 fell open to the FMP screener, swapping 377 of 730 names
(52%) for non-members. Two things let that run for nine weeks — nothing recorded WHAT
the context was built on, and the freshness heartbeat watched only the mtime, which
was fine the whole time.

Hermetic: no network, no production state, no clock dependence.
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))


def _write_context(path: Path, provenance: dict | None) -> None:
    payload = {
        "macro": None,
        "strategy_mode": "long",
        "bmi_regime": "yellow",
        "bmi_value": 44.0,
        "sector_bmi_values": {},
        "universe": [],
        "sector_scores": [],
        "vetoed_sectors": [],
        "agg_benchmark": None,
        "uw_available": False,
    }
    if provenance is not None:
        payload["universe_provenance"] = provenance
    with gzip.open(path, "wt") as handle:
        json.dump(payload, handle)


OK_PROVENANCE = {
    "universe_definition": "index_union_plus_liquidity_floor",
    "built": 898,
    "membership": {
        "source": "wikipedia",
        "count": 1027,
        "age_days": 0.0,
        "degraded_stale": False,
    },
    "floor": {"passed": 909, "excluded": 118},
}


class TestTheContextCarriesProvenance:
    def test_it_round_trips_through_save_and_load(self, tmp_path):
        from ifds.pipeline.context_persistence import load_phase13_context, save_phase13_context

        class _Ctx:
            macro = None
            strategy_mode = None
            bmi_regime = None
            bmi_value = 44.0
            sector_bmi_values: dict = {}
            universe: list = []
            sector_scores: list = []
            vetoed_sectors: list = []
            agg_benchmark = None
            uw_available = False
            universe_provenance = OK_PROVENANCE

        path = tmp_path / "ctx.json.gz"
        save_phase13_context(_Ctx(), path=str(path))
        with gzip.open(path, "rt") as handle:
            assert json.load(handle)["universe_provenance"] == OK_PROVENANCE

        restored = _Ctx()
        restored.universe_provenance = {}
        load_phase13_context(restored, path=str(path))
        assert restored.universe_provenance == OK_PROVENANCE

    def test_a_context_without_provenance_loads_as_empty_not_as_an_error(self, tmp_path):
        """Contexts written before 2026-10-20 must still load."""
        from ifds.pipeline.context_persistence import load_phase13_context

        class _Empty:
            universe_provenance = {"stale": "value"}

        path = tmp_path / "ctx.json.gz"
        _write_context(path, None)
        ctx = _Empty()
        load_phase13_context(ctx, path=str(path))
        assert ctx.universe_provenance == {}


class TestTheHeartbeatWatchesProvenance:
    def _classify(self, tmp_path, provenance):
        from check_phase13_freshness import classify_provenance

        path = tmp_path / "ctx.json.gz"
        _write_context(path, provenance)
        return classify_provenance(path)

    def test_the_intended_universe_is_ok(self, tmp_path):
        status, detail = self._classify(tmp_path, OK_PROVENANCE)
        assert status == "ok"
        assert "index_union_plus_liquidity_floor" in detail

    def test_the_degraded_definition_is_flagged(self, tmp_path):
        """This is the exact shape that ran unnoticed for nine weeks."""
        status, detail = self._classify(
            tmp_path,
            {
                "universe_definition": "screener_intersect_membership_degraded",
                "degraded": True,
                "built": 520,
                "membership": {"source": "cache", "count": 1027},
            },
        )
        assert status == "degraded"
        assert "degraded" in detail

    def test_stale_membership_is_flagged_even_when_the_context_is_fresh(self, tmp_path):
        """Age of the CONTEXT and age of the MEMBERSHIP are different questions."""
        provenance = {
            **OK_PROVENANCE,
            "membership": {
                "source": "cache",
                "count": 1018,
                "age_days": 64.0,
                "degraded_stale": True,
            },
        }
        status, detail = self._classify(tmp_path, provenance)
        assert status == "degraded"
        assert "64" in detail

    def test_a_missing_record_is_unknown_not_ok(self, tmp_path):
        """Silence must not read as health — that is how nine weeks passed."""
        status, detail = self._classify(tmp_path, None)
        assert status == "unknown"
        assert "no universe_provenance" in detail

    def test_an_unreadable_context_is_unknown_not_a_crash(self, tmp_path):
        from check_phase13_freshness import classify_provenance

        path = tmp_path / "ctx.json.gz"
        path.write_bytes(b"not gzip at all")
        status, _ = classify_provenance(path)
        assert status == "unknown"

    @pytest.mark.parametrize("definition", ["index_union_plus_liquidity_floor"])
    def test_ok_requires_both_a_good_definition_and_fresh_membership(
        self, tmp_path, definition
    ):
        status, _ = self._classify(
            tmp_path,
            {
                "universe_definition": definition,
                "built": 898,
                "membership": {"source": "wikipedia", "count": 1027, "degraded_stale": False},
            },
        )
        assert status == "ok"
