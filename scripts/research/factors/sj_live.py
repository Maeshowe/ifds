"""HYP-005 — S_j live aggregate, cross-sectional IC (transform-level, v1).

Registered hypothesis: ``docs/design/frl/hypotheses/HYP-005-sj-live-aggregate.md``.

The factor IS the live swing score: ``EWMA₅(100·(PCR_pct − OTM_pct) + sector_adj)``,
i.e. the value the pipeline actually acts on. It measures the built transform
(percentile mapping + EWMA + sector adjustment together), not the raw PCR/OTM
signals — those are the v2 lane (HYP-001b/002b), a separate attempt family.

**Swing era only.** The legacy ``Total_Score`` is a different formula on an
incompatible scale (0..108 on a .0/.5 grid vs −125..+107 continuous, FRL-0 gate
finding), so legacy rows are dropped to NaN rather than pooled. The panel-level
``require_single_era`` guard would also catch this; doing it here as well means
the factor is correct even when called on a mixed frame.

**Governance (G1, both directions).** This is the descriptive twin of the
signal_attribution gate test. Its result — positive or negative — is inadmissible
to the Day 63 deliberation.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

import factors.base as base
import frl_config as cfg

INPUT_COLUMN = "score"


def compute(panel: pd.DataFrame) -> pd.Series:
    """The live swing score, with legacy-era rows masked to NaN."""
    if INPUT_COLUMN not in panel.columns:
        raise KeyError(
            f"{INPUT_COLUMN} missing — the S_j factor consumes the loader's "
            "canonical score column"
        )
    if "era" not in panel.columns:
        raise KeyError("panel must carry an 'era' column (swing-only factor)")

    values = pd.to_numeric(panel[INPUT_COLUMN], errors="coerce")
    return values.where(panel["era"] == cfg.ERA_SWING)


def _sanity_panel() -> pd.DataFrame:
    """Synthetic swing-era panel where a higher S_j precedes a higher return.

    Deliberately swing-era: a legacy panel would be masked to NaN and the check
    would pass vacuously on an all-empty series.
    """
    rows = []
    start = date(2026, 6, 1)
    for d in range(6):
        day = start + timedelta(days=d)
        for sector in ("Tech", "Health"):
            for i in range(8):
                score = (i - 3.5) * 10.0  # spans roughly the real −35..+35 band
                rows.append(
                    {
                        "date": day,
                        "ticker": f"{sector[:2]}{i}",
                        "sector": sector,
                        "era": cfg.ERA_SWING,
                        INPUT_COLUMN: score,
                        "fwd_ret_5": score * 0.001,  # positive relation
                    }
                )
    return pd.DataFrame(rows)


FACTOR = base.register(
    base.Factor(
        name="sj_live_aggregate",
        hyp_id="HYP-005",
        data_lane="v1",
        expected_sign=1,
        compute=compute,
        sanity_panel=_sanity_panel,
        description=(
            "Live swing score EWMA5(100*(PCR_pct - OTM_pct) + sector_adj); "
            "swing era only; expected positive IC."
        ),
    )
)
