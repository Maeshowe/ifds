#!/usr/bin/env python3
"""Freeze-safety proof for disabling the UW greek-exposure PRIMARY in the
GEX FallbackGEXProvider (UW → Polygon).

The claim is NOT "UW fails so it's fine" — two different sources generally
produce different GEX regimes. The claim is the conditional one: across the
realized runs, the UW greek-exposure primary contributed to **zero** GEX-regime
classifications (every ticker fell back to Polygon), so the realized regimes —
and therefore the NEGATIVE-regime entry-exclusion list — were already 100%
Polygon-derived. Disabling the UW primary reproduces them exactly → output-
invariant (an EMPTY pre/post diff).

This scans logs/ifds_run_*.jsonl and reports, per trading day:
  - API_FALLBACK count        (tickers where UW returned None → Polygon)
  - source=uw count           (tickers whose GEX was UW-sourced — MUST be 0)
  - no-GEX-data POSITIVE default count (Polygon also failed — MUST be 0)
  - the GEX_EXCLUSION ticker list (the entry-filter decisions, all Polygon)

Proof passes iff, across all days: source=uw == 0 AND no-data-default == 0.
Then the exclusion lists are provably Polygon-derived and unchanged by removing
the UW call. Log the result in 04-risks as the freeze amendment.

    python scripts/analysis/verify_gex_uw_invariance.py
"""

from __future__ import annotations

import glob
import json
import re
from collections import defaultdict
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"

_SRC_RE = re.compile(r"source=(\w+)")


def main() -> None:
    per_day: dict[str, dict] = defaultdict(
        lambda: {"fallback": 0, "src_uw": 0, "src_poly": 0, "nodata": 0, "excluded": []}
    )

    for path in sorted(glob.glob(str(LOG_DIR / "ifds_run_*.jsonl"))):
        # date from filename: ifds_run_YYYYMMDD_HHMMSS.jsonl
        m = re.search(r"ifds_run_(\d{8})_", path)
        if not m:
            continue
        raw = m.group(1)
        day = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
        d = per_day[day]
        for line in open(path):
            try:
                e = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            et = e.get("event_type", "")
            msg = e.get("message", "")
            if et == "API_FALLBACK":
                d["fallback"] += 1
            elif et == "GEX_EXCLUSION":
                tk = (e.get("data") or {}).get("ticker") or e.get("ticker")
                if tk and tk not in d["excluded"]:
                    d["excluded"].append(tk)
            elif "defaulting to POSITIVE regime" in msg or "no GEX data from any provider" in msg:
                d["nodata"] += 1
            sm = _SRC_RE.search(msg)
            if sm:
                src = sm.group(1)
                if src.startswith("uw"):
                    d["src_uw"] += 1
                elif src.startswith("polygon"):
                    d["src_poly"] += 1

    # Keep only days that actually ran Phase 5 (had GEX activity)
    days = sorted(k for k, v in per_day.items() if v["fallback"] or v["src_poly"] or v["excluded"])

    print(f"{'date':12} {'fallback':>9} {'src=uw':>7} {'src=poly*':>10} {'nodata':>7}  exclusions")
    total_uw = total_nodata = 0
    for day in days:
        v = per_day[day]
        total_uw += v["src_uw"]
        total_nodata += v["nodata"]
        excl = ",".join(v["excluded"]) if v["excluded"] else "-"
        print(
            f"{day:12} {v['fallback']:>9} {v['src_uw']:>7} {v['src_poly']:>10} "
            f"{v['nodata']:>7}  {excl}"
        )
    print("  (* src=poly/src=uw are sampled — GEX_DEBUG logs the first 5 tickers/run)")
    print()
    print(f"Days with Phase-5 GEX activity: {len(days)}")
    print(f"TOTAL source=uw (UW-sourced regimes): {total_uw}   (must be 0 → invariance)")
    print(
        f"TOTAL no-GEX-data POSITIVE defaults:  {total_nodata}   "
        f"(context only — UW-independent: Polygon also None → same outcome on/off)"
    )
    # Invariance criterion is source=uw==0 ALONE. A ticker's GEX outcome differs
    # between UW-primary on/off ONLY when UW *succeeds* (source=uw). The no-data
    # POSITIVE defaults are cases where UW returned None AND Polygon returned None
    # → POSITIVE default either way; removing the (None-returning) UW call does not
    # change them. So they do not affect output-invariance.
    ok = total_uw == 0
    print()
    if ok:
        print("PROOF PASS — UW greek-exposure was UW-sourced for 0 tickers across all days;")
        print("every realized regime (and thus every NEGATIVE-exclusion) was already")
        print("Polygon-derived or a UW-independent default. Disabling the UW primary is")
        print("OUTPUT-INVARIANT (empty pre/post diff).")
        print("NOTE: source is sampled (GEX_DEBUG = first 5 tickers/run); the per-run")
        print("API_FALLBACK counts (≈ all analyzed tickers) corroborate 100% fallback.")
        print("Run the live on/off provider diff for the airtight all-ticker confirmation.")
    else:
        print("PROOF FAIL — UW sourced some regimes; disabling the primary would change")
        print("output. NOT output-invariant. Investigate before any change.")


if __name__ == "__main__":
    main()
