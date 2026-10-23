"""Context round-trip completeness — the gap behind the dead BC14 subtraction.

Why. The production pipeline is SPLIT: Phase 1-3 runs on Sunday and writes
``state/phase13_ctx.json.gz``; Phase 4-6 reloads it every weekday. Anything the saver
writes but the loader drops silently reverts to its dataclass default on that reload.

That happened to ``breadth_score_adj``. ``_sector_score_to_dict`` saved it,
``_dict_to_sector_score`` never restored it, so after every reload it was 0 — and BC14's
deliberate exclusion of breadth from the ticker-level score
(``s.score_adjustment - s.breadth_score_adj``, phase4_stocks.py) subtracted zero. The
ticker score therefore carried the breadth term BC14 was written to remove, on every
production run since the split pipeline went live. Nothing failed; the number was simply
a different number than the design says.

So the test is not "breadth_score_adj round-trips". It is "EVERY field the saver writes
survives the load" — the gap, not the instance. A new field added to the saver and
forgotten in the loader fails here instead of silently changing a score months later.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ifds.models.market import (  # noqa: E402
    MomentumClassification,
    SectorBMIRegime,
    SectorScore,
)
from ifds.pipeline.context_persistence import (  # noqa: E402
    _dict_to_sector_score,
    _sector_score_to_dict,
)


def _a_sector() -> SectorScore:
    """A sector carrying a NON-DEFAULT value in every saved field.

    Defaults would make a dropped field indistinguishable from a restored one — the
    exact reason the original bug was invisible.
    """
    return SectorScore(
        etf="XLF",
        sector_name="Financial Services",
        momentum_5d=2.75,
        classification=MomentumClassification.LEADER,
        sector_bmi=61.5,
        sector_bmi_regime=SectorBMIRegime.OVERBOUGHT,
        score_adjustment=-15,
        breadth_score_adj=-15,
    )


class TestEverySavedFieldSurvivesTheLoad:
    @pytest.mark.parametrize(
        "field",
        sorted(_sector_score_to_dict(_a_sector()).keys()),
    )
    def test_the_field_comes_back(self, field: str) -> None:
        original = _a_sector()
        saved = _sector_score_to_dict(original)
        restored = _sector_score_to_dict(_dict_to_sector_score(saved))
        assert restored[field] == saved[field], (
            f"`{field}` is written by _sector_score_to_dict but does not survive "
            "_dict_to_sector_score — it silently reverts to its dataclass default on the "
            "weekday Phase 4-6 reload. That is how BC14's breadth exclusion was dead in "
            "production: saved, dropped, defaulted to 0, subtracted nothing."
        )

    def test_the_saver_and_the_loader_describe_the_same_object(self) -> None:
        """A field added to the saver must be added to the loader in the same change."""
        saved = _sector_score_to_dict(_a_sector())
        restored = _dict_to_sector_score(saved)
        missing = [k for k in saved if _sector_score_to_dict(restored)[k] != saved[k]]
        assert not missing, f"dropped by the loader: {missing}"


class TestTheBC14SubtractionIsLiveAfterAReload:
    def test_breadth_is_excluded_from_the_ticker_level_adjustment(self) -> None:
        """The behaviour the bug removed, asserted on the reload path.

        phase4_stocks builds ``sector_adj_map`` as ``score_adjustment - breadth_score_adj``
        so that breadth steers the SECTOR ranking without being double-counted into every
        ticker's score. With breadth_score_adj defaulted to 0 the map returned the
        breadth-inclusive number instead.
        """
        reloaded = _dict_to_sector_score(_sector_score_to_dict(_a_sector()))
        sector_adj = reloaded.score_adjustment - reloaded.breadth_score_adj
        assert reloaded.breadth_score_adj == -15, "breadth term lost on reload"
        assert sector_adj == 0, (
            "XLF carries score_adjustment -15 of which the whole -15 IS the breadth term, "
            "so the ticker-level adjustment must be 0. Getting -15 here means breadth is "
            "being charged to every ticker in the sector a second time."
        )
