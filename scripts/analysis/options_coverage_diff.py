#!/usr/bin/env python3
"""Did the options feed quietly thin out? Compare a day against a recorded baseline.

Why this is the primary check for the Options plan downgrade, and the tolerance guard in
phase5_mms is only the secondary one: ``day.volume`` never reaches a degeneracy guard at
all. If a cheaper plan stopped serving it, the chain is

    day.volume absent
      -> phase4_stocks pcr = None, otm_call_ratio = None, for EVERY ticker
      -> both percentile universes empty
      -> compute_percentile_score returns a hard-coded 0.5
      -> every swing raw score collapses to an identical 0.0

with no None, no exception and no log line. No tolerance protects against that; only
measuring coverage does.

Read-only: reads state/, writes nothing. Run it the morning after any options plan change
(and clear the options cache before that run — ``get_options_snapshot`` caches under
YESTERDAY's date, so a degraded first response would be served for the rest of the run).
"""

from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import statistics
from dataclasses import dataclass
from datetime import date

#: Non-null rates measured on production (Mac Mini) on 2026-10-23, over the swing era.
#: These are the comparison point, pinned here so the check cannot drift with the data
#: it is checking — the same reason the regime and scoring-era registries are named
#: constants rather than computed "latest" values.
BASELINE: dict[str, float] = {
    "pcr": 0.998,
    "otm_call_ratio": 0.998,
    "gex": 0.996,
    "dex": 0.996,
    "iv_rank": 0.931,
    "iv_skew": 0.917,
}

#: A feature is REPORTED as degraded below this fraction of its baseline rate. Chosen
#: from the baseline spread, not from the day under test: the lowest baseline is 0.917
#: and the highest 0.998, so a 0.80 factor clears normal variation on every feature while
#: still catching the failure this exists for — a universe-wide drop to ~0.
DEGRADED_FACTOR = 0.80

#: Dispersion floor. A feed that returns a CONSTANT value is present but useless, and
#: coverage alone cannot see it. Tolerance-based, never `== 0`.
MIN_DISPERSION = 1e-12


@dataclass(frozen=True)
class FeatureReading:
    name: str
    n: int
    non_null: int
    dispersion: float

    @property
    def rate(self) -> float:
        return (self.non_null / self.n) if self.n else 0.0

    @property
    def degraded(self) -> bool:
        baseline = BASELINE.get(self.name)
        if baseline is None:
            return False
        return self.rate < baseline * DEGRADED_FACTOR

    @property
    def constant(self) -> bool:
        return self.non_null > 1 and self.dispersion <= MIN_DISPERSION


def _values(rows: list[dict], field: str) -> list[float]:
    out: list[float] = []
    for row in rows:
        value = row.get(field)
        if value is None:
            continue
        try:
            out.append(float(value))
        except (TypeError, ValueError):
            continue
    return out


def read_feature(rows: list[dict], field: str) -> FeatureReading:
    present = _values(rows, field)
    non_zero = [v for v in present if v != 0.0]
    dispersion = statistics.pstdev(present) if len(present) > 1 else 0.0
    return FeatureReading(field, len(rows), len(non_zero), dispersion)


def load_mms(day: str, root: str = "state/mms") -> list[dict]:
    """One row per ticker for ``day`` from the MMS store."""
    rows: list[dict] = []
    for path in sorted(glob.glob(os.path.join(root, "*.json"))):
        try:
            with open(path) as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        entries = payload if isinstance(payload, list) else payload.get("observations", [])
        for entry in entries:
            if isinstance(entry, dict) and str(entry.get("date", ""))[:10] == day:
                rows.append(entry)
    return rows


def load_snapshot(day: str, root: str = "state/phase4_snapshots") -> list[dict]:
    path = os.path.join(root, f"{day}.json.gz")
    if not os.path.exists(path):
        return []
    try:
        with gzip.open(path, "rt") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []
    return payload if isinstance(payload, list) else payload.get("analyses", [])


def report(day: str) -> tuple[list[FeatureReading], bool]:
    mms_rows = load_mms(day)
    snap_rows = load_snapshot(day)
    readings = [read_feature(mms_rows, f) for f in ("gex", "dex", "iv_rank", "iv_skew")]
    readings += [read_feature(snap_rows, f) for f in ("pcr", "otm_call_ratio")]
    failed = any(r.degraded or r.constant for r in readings)
    return readings, failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    readings, failed = report(args.date)
    print(f"Options feature coverage — {args.date}")
    print(f"{'feature':16} {'n':>6} {'non-zero':>9} {'rate':>8} {'baseline':>9} {'spread':>12}  flag")
    for r in readings:
        base = BASELINE.get(r.name)
        flag = "DEGRADED" if r.degraded else ("CONSTANT" if r.constant else "ok")
        print(
            f"{r.name:16} {r.n:6d} {r.non_null:9d} {r.rate:8.3f} "
            f"{(base if base is not None else float('nan')):9.3f} {r.dispersion:12.3e}  {flag}"
        )
    if failed:
        print("\nFAIL — at least one feature thinned out or went constant.")
        print("Check whether the options plan change dropped a field. The highest-impact")
        print("case is day.volume: pcr and otm_call_ratio depend on it alone, and their")
        print("universe-wide loss collapses every swing score to an identical 0.0 silently.")
        return 1
    print("\nOK — every feature within its baseline, and none constant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
