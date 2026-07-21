"""HYP-004 — 5-day sector-relative reversal (pure v1, OHLCV only).

Registered hypothesis: ``docs/design/frl/hypotheses/HYP-004-sector-relative-reversal.md``.

Factor value = the trailing 5-trading-day return, demeaned inside its sector on
that day. Expected IC is NEGATIVE: past relative winners underperform over the
next few days, because the liquidity provider who absorbed the uninformed push
gets paid on the snap-back.

Look-ahead boundary: the input is ``past_ret_5`` (window ENDING at t), never a
``fwd_ret_*`` column. The sector demeaning is explicit even though ``daily_ic``
ranks within sector anyway — it keeps the factor honest to the hypothesis if the
IC definition ever changes.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

import factors.base as base

INPUT_COLUMN = "past_ret_5"


def compute(panel: pd.DataFrame) -> pd.Series:
    """Sector-demeaned trailing 5-day return, aligned to ``panel``'s index."""
    if INPUT_COLUMN not in panel.columns:
        raise KeyError(
            f"{INPUT_COLUMN} missing — the return matrix must be merged into the "
            "panel before the factor is computed"
        )
    values = pd.to_numeric(panel[INPUT_COLUMN], errors="coerce")
    if "sector" not in panel.columns or "date" not in panel.columns:
        raise KeyError("panel must carry 'date' and 'sector' columns")

    sector_mean = values.groupby([panel["date"], panel["sector"]]).transform("mean")
    return values - sector_mean


def _sanity_panel() -> pd.DataFrame:
    """Synthetic panel with a *known* reversal: fwd return = −past return.

    Deliberately not `linear_sanity_panel`: this factor consumes a return column
    and demeans by sector, so the check must exercise both — including a sector
    level offset that the demeaning has to remove.
    """
    rows = []
    start = date(2026, 6, 1)
    for d in range(6):
        day = start + timedelta(days=d)
        for sector, offset in (("Tech", 0.05), ("Health", -0.03)):
            for i in range(8):
                past = (i - 3.5) * 0.01 + offset  # sector offset must not matter
                rows.append(
                    {
                        "date": day,
                        "ticker": f"{sector[:2]}{i}",
                        "sector": sector,
                        INPUT_COLUMN: past,
                        # pure reversal: what went up comes back down
                        "fwd_ret_5": -((i - 3.5) * 0.01),
                    }
                )
    return pd.DataFrame(rows)


FACTOR = base.register(
    base.Factor(
        name="sector_relative_reversal_5d",
        hyp_id="HYP-004",
        data_lane="v1",
        expected_sign=-1,
        compute=compute,
        sanity_panel=_sanity_panel,
        description="Trailing 5d return demeaned within sector; expected negative IC.",
    )
)
