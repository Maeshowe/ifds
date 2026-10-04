"""HYP-006/007/008 — the S_j block decomposition (Flow / Funda / Tech, v1).

Registered hypotheses:
  docs/design/frl/hypotheses/HYP-006-flow-block.md
  docs/design/frl/hypotheses/HYP-007-funda-block.md
  docs/design/frl/hypotheses/HYP-008-tech-block.md
Pre-registration: docs/planning/2026-10-04-component-decomposition-preregistration.md

The aggregate S_j is a confirmed null on all four horizons (A-0005..A-0010,
2026-10-04). An aggregate null cannot distinguish two very different worlds:

  (i)  no component carries cross-sectional signal, or
  (ii) components carry signal that CANCELS in the fixed 0.60/0.10/0.30 mix.

The observed +0.0130 is equally consistent with both — e.g. Flow +0.04 with
Tech -0.03 produces 0.60(0.04) + 0.30(-0.03) = +0.015. So each weighted block is
registered as its own hypothesis and measured separately.

**The Total_Score != 0 filter is the point of this module** (pre-reg §4.1).
In unscored rows the Flow and Funda columns sit at their DEFAULT 50 — verified on
36,557 real swing-era rows, where ~100% of unscored rows carry exactly 50.0.
Including them would inject a 43% constant mass into the daily cross-sectional
ranking: the mirror image of the dp_pct structural-zero bug, where a broken field
read as "no signal". The filter is tolerance-based, never ``== 0`` (ifds-rules).

**Swing era only**, for the same reason as HYP-005: the legacy Total_Score is a
different formula on an incompatible scale, so legacy rows are masked rather than
pooled (G5).
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

import factors.base as base
import frl_config as cfg

#: A row counts as scored when |Total_Score| exceeds this. Tolerance-based:
#: float arithmetic on a degenerate input leaves a ~1e-16 residue, not 0.0, and
#: an ``== 0`` guard would silently let those rows through (ifds-rules).
SCORED_EPS = 1e-9

SCORE_COLUMN = "score"  # the loader's name for Total_Score


def _block_factor(panel: pd.DataFrame, column: str) -> pd.Series:
    """One block score, masked to NaN wherever it is not a real observation.

    Two masks, both mandatory:
      * ``era == swing`` — the legacy formula is incompatible (G5).
      * ``|Total_Score| > SCORED_EPS`` — otherwise the block columns are at
        their defaults, not at measured values (pre-reg §4.1).
    """
    for required in (column, SCORE_COLUMN, "era"):
        if required not in panel.columns:
            raise KeyError(
                f"{required} missing — the block factors need the block column, "
                f"the canonical {SCORE_COLUMN} column (for the §4.1 scored filter) "
                "and 'era' (swing-only guard)"
            )

    values = pd.to_numeric(panel[column], errors="coerce")
    total = pd.to_numeric(panel[SCORE_COLUMN], errors="coerce")
    scored = total.notna() & (total.abs() > SCORED_EPS)
    return values.where((panel["era"] == cfg.ERA_SWING) & scored)


def _sanity_panel(column: str, low: float, high: float):
    """Build a synthetic swing-era panel where a higher block precedes a higher return.

    Deliberately swing-era AND with a non-zero ``score``: either mask alone would
    reduce the panel to all-NaN and the sanity check would pass vacuously on an
    empty series. ``TestSanityIsNotVacuous`` pins that.
    """

    def build() -> pd.DataFrame:
        rows = []
        start = date(2026, 6, 1)
        span = high - low
        for d in range(6):
            day = start + timedelta(days=d)
            for sector in ("Tech", "Health"):
                for i in range(8):
                    value = low + span * i / 7.0
                    rows.append(
                        {
                            "date": day,
                            "ticker": f"{sector[:2]}{i}",
                            "sector": sector,
                            "era": cfg.ERA_SWING,
                            SCORE_COLUMN: 42.0,  # non-zero: passes the §4.1 filter
                            column: value,
                            "fwd_ret_5": (value - low) * 0.001,  # positive relation
                        }
                    )
        return pd.DataFrame(rows)

    return build


# ---------------------------------------------------------------------------
# Registration — exactly three, as pre-registered. Do not extend post hoc.
# ---------------------------------------------------------------------------

FLOW = base.register(
    base.Factor(
        name="flow_block",
        hyp_id="HYP-006",
        data_lane="v1",
        expected_sign=1,
        compute=lambda panel: _block_factor(panel, "flow_score"),
        sanity_panel=_sanity_panel("flow_score", 10.0, 100.0),
        description=(
            "Flow block of S_j (weight 0.60): clip(50 + rvol_score, 0, 100), where "
            "rvol_score is itself a 7-term sum. Swing era only, scored rows only."
        ),
    )
)

FUNDA = base.register(
    base.Factor(
        name="funda_block",
        hyp_id="HYP-007",
        data_lane="v1",
        expected_sign=1,
        compute=lambda panel: _block_factor(panel, "funda_score"),
        sanity_panel=_sanity_panel("funda_score", 40.0, 60.0),
        description=(
            "Fundamentals block of S_j (weight 0.10): 50 + funda_score. Slow factor "
            "(measured half-life ~800 days). Swing era only, scored rows only."
        ),
    )
)

TECH = base.register(
    base.Factor(
        name="tech_block",
        hyp_id="HYP-008",
        data_lane="v1",
        expected_sign=1,
        compute=lambda panel: _block_factor(panel, "tech_score"),
        sanity_panel=_sanity_panel("tech_score", 0.0, 75.0),
        description=(
            "Technical block of S_j (weight 0.30): rsi_score + sma50_bonus + "
            "rs_spy_score. Swing era only, scored rows only."
        ),
    )
)
