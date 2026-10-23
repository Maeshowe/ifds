"""Bar-series helpers shared by the scoring phases.

One function so far, and it exists because of a measured calendar fact: the Phase 4-6 cron
runs at 14:30 Budapest, which `scripts/crontab.md` describes as 08:30 ET — pre-market, so
the newest daily bar is yesterday's and complete. Europe leaves DST on 2026-10-25 and the
US only on 2026-11-01, so for 2026-10-26…10-30 that same slot lands at **09:30 ET, exactly
on the opening bell**, and the vendor can already be serving a partial bar for the session
in progress.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Sequence


def drop_open_session(bars: Sequence[dict] | None, run_date: date) -> list[dict]:
    """Bars with the still-open session (and anything later) removed.

    Every scoring consumer takes the NEWEST bar — ``closes[-1]`` for the price and the
    3-month return, ``bars[-1]["v"]`` for volume, ``bars[-1]["c"]`` as the PCR/OTM
    reference. A partial first-minutes bar in any of them is a WRONG number, not a
    missing one, which is the failure mode this repo has been burned by twice.

    Guarding here rather than at each consumer closes the gap instead of four instances,
    and it is a NO-OP whenever the vendor has not opened a bar for ``run_date`` — which is
    every ordinary pre-market run. That matters beyond tidiness: a guard that changed the
    score on ordinary days would retroactively redefine the 2026-10-26 scoring era.

    A row whose timestamp cannot be read is KEPT. Dropping it would silently shorten the
    history on a vendor hiccup, and a short series is harder to notice than a loud one.

    The epoch conversion is UTC-anchored on purpose: Polygon's ``t`` is ET midnight in
    milliseconds, and a local-zone conversion shifts the whole series by a day on a
    far-enough host (.claude/rules/ifds-rules.md, 2026-10-19). ``tests/
    test_timestamp_timezone.py`` forbids the tz-less form outright.
    """
    out: list[dict] = []
    for bar in bars or []:
        ts = bar.get("t")
        if ts is None:
            out.append(bar)
            continue
        try:
            bar_date = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date()
        except (TypeError, ValueError, OSError, OverflowError):
            out.append(bar)
            continue
        if bar_date < run_date:
            out.append(bar)
    return out
