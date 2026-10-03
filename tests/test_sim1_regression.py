"""SIM-1 regression pin — the published numbers must not drift.

``docs/review/2026-10-03-sim1-counterfactual-geometry.md`` and §11.20 of
``04-risks`` quote these figures, and ``docs/CHANGELOG.md`` records them. Any
refactor of the shared sample assembly or the simulator must reproduce them
exactly, or the published artifact silently becomes false.

This test reads the real production artifacts (ledger, plans, metrics, bar
cache). Those are not in a fresh clone — and ``research/cache`` is gitignored —
so it SKIPS when they are absent rather than passing vacuously or firing live
API calls (ifds-rules: hermetic tests).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ANALYSIS = Path(__file__).resolve().parents[1] / "scripts" / "analysis"
sys.path.insert(0, str(ANALYSIS))

import counterfactual_data as cd  # noqa: E402
from counterfactual_geometry import net_pnl, rebase_levels, simulate  # noqa: E402
from ifds.state.swing_positions import SwingPosition  # noqa: E402

REQUIRED = (
    cd.PENDING_EXITS_DIR,
    cd.DAILY_METRICS_DIR,
    cd.PLANS_DIR,
    cd.BARS_DIR,
)

pytestmark = pytest.mark.skipif(
    not all(path.exists() for path in REQUIRED),
    reason="SIM-1 source artifacts absent (fresh clone / CI) — nothing to regress against",
)

# Published in the SIM-1 report, §11.20 and the CHANGELOG.
PUBLISHED_SAMPLE_SIZE = 78
PUBLISHED_EXCLUSIONS = 15
PUBLISHED_SUM_A = -5_349.83
PUBLISHED_SUM_B = -5_357.89
PUBLISHED_ACTUAL = -7_657.43


@pytest.fixture(scope="module")
def simulated():
    sample, excluded = cd.build_sample(9)
    rows = []
    for pos in sample:
        bars = list(pos.bars)
        legs = {}
        for label, anchor in (("a", pos.planned_entry), ("b", pos.fill)):
            stop, tp1, tp2 = rebase_levels(anchor, pos.atr)
            result = simulate(
                SwingPosition(
                    ticker=pos.ticker,
                    entry_date=pos.entry_date,
                    entry_price=anchor,
                    atr=pos.atr,
                    stop_level=stop,
                    tp1_level=tp1,
                    tp2_level=tp2,
                    qty=pos.qty,
                    qty_remaining=pos.qty,
                    sector=pos.sector,
                    entry_score=pos.entry_score,
                ),
                bars,
            )
            legs[label] = net_pnl(result.legs, pos.fill)
        rows.append((pos, legs["a"], legs["b"]))
    return rows, excluded


def test_sample_size_is_unchanged(simulated):
    rows, excluded = simulated
    assert len(rows) == PUBLISHED_SAMPLE_SIZE
    assert len(excluded) == PUBLISHED_EXCLUSIONS


def test_configuration_sums_are_unchanged(simulated):
    rows, _ = simulated
    assert sum(a for _, a, _ in rows) == pytest.approx(PUBLISHED_SUM_A, abs=0.01)
    assert sum(b for _, _, b in rows) == pytest.approx(PUBLISHED_SUM_B, abs=0.01)


def test_the_headline_geometry_effect_is_unchanged(simulated):
    """Σ B − Σ A = −$8.06 — the number the whole SIM-1 conclusion rests on."""
    rows, _ = simulated
    delta = sum(b for _, _, b in rows) - sum(a for _, a, _ in rows)
    assert delta == pytest.approx(-8.06, abs=0.01)


def test_actual_realized_over_the_sample_is_unchanged(simulated):
    rows, _ = simulated
    assert sum(p.actual_pnl for p, _, _ in rows) == pytest.approx(PUBLISHED_ACTUAL, abs=0.01)
