#!/usr/bin/env python3
"""Live on/off diff — airtight all-ticker freeze-safety proof for flipping
uw_gex_fetch_enabled OFF (Polygon-only GEX).

The 92-day log scan (verify_gex_uw_invariance.py) proves source=uw==0 but is
SAMPLED (GEX_DEBUG = first 5 tickers/run). This closes the sampling gap: it runs
the GEX providers on the FULL current universe both ways and confirms the
per-ticker GEX regime is identical UW-primary ON vs OFF.

HARD STOP (the one thing this adds over the unit tests): it calls UW live for
every ticker today. If UW returns **non-None** for ANY ticker — i.e. UW is not
100% dead today and would contribute a regime — then flipping OFF is NOT output-
invariant for that ticker. The script reports it and the verdict becomes STOP.

Read-only: fetches GEX, classifies, diffs. Changes no production state.

    source .env && python scripts/analysis/gex_live_onoff_diff.py
"""

from __future__ import annotations

import gzip
import json
import os
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SNAP_DIR = REPO / "state" / "phase4_snapshots"


def _load_today_universe() -> list[dict]:
    today = date.today().isoformat()
    path = SNAP_DIR / f"{today}.json.gz"
    if not path.exists():
        # fall back to the most recent snapshot
        snaps = sorted(SNAP_DIR.glob("*.json.gz"))
        if not snaps:
            raise SystemExit("No phase4 snapshot found.")
        path = snaps[-1]
    recs = json.load(gzip.open(path))
    if isinstance(recs, dict):
        recs = list(recs.values())
    print(f"universe: {path.name}  ({len(recs)} tickers)")
    return recs


def main() -> None:
    from ifds.config.loader import Config
    from ifds.data.adapters import PolygonGEXProvider, UWGEXProvider
    from ifds.data.polygon import PolygonClient
    from ifds.data.unusual_whales import UnusualWhalesClient
    from ifds.models.market import GEXRegime, StrategyMode
    from ifds.phases.phase5_gex import _classify_gex_regime

    cfg = Config()
    max_dte = cfg.tuning.get("gex_max_dte", 35)
    strategy = StrategyMode.LONG  # the realized paper strategy

    polygon = PolygonClient(api_key=os.environ["IFDS_POLYGON_API_KEY"])
    uw = UnusualWhalesClient(
        api_key=os.environ["IFDS_UW_API_KEY"],
        timeout=cfg.runtime["api_timeout_uw"],
        max_retries=cfg.runtime["api_max_retries"],
    )
    uw_gex = UWGEXProvider(uw)
    poly_gex = PolygonGEXProvider(polygon, max_dte=max_dte)

    recs = _load_today_universe()

    uw_nonnone = []  # HARD STOP trigger
    regime_diffs = []
    excl_on, excl_off = [], []

    def classify(price, gex):
        if not gex:
            return GEXRegime.POSITIVE  # no-data default (phase5 line ~109)
        return _classify_gex_regime(price, gex.get("zero_gamma", 0.0), gex.get("net_gex", 0.0))

    for r in recs:
        t = r.get("ticker")
        price = r.get("price") or 0.0
        if not t or price <= 0:
            continue
        uw_raw = uw_gex.get_gex(t)
        poly_raw = poly_gex.get_gex(t)
        if uw_raw is not None:
            uw_nonnone.append(t)
        # ON (fallback): UW if present else Polygon. OFF: Polygon only.
        on = uw_raw if uw_raw is not None else poly_raw
        off = poly_raw
        r_on = classify(price, on)
        r_off = classify(price, off)
        if r_on != r_off:
            regime_diffs.append((t, r_on.value, r_off.value))
        if r_on == GEXRegime.NEGATIVE and strategy == StrategyMode.LONG:
            excl_on.append(t)
        if r_off == GEXRegime.NEGATIVE and strategy == StrategyMode.LONG:
            excl_off.append(t)

    print()
    print(f"UW non-None (HARD STOP if > 0): {len(uw_nonnone)}  {uw_nonnone or ''}")
    print(f"regime diffs ON vs OFF: {len(regime_diffs)}  {regime_diffs or ''}")
    print(f"NEGATIVE-exclusion list ON:  {sorted(excl_on)}")
    print(f"NEGATIVE-exclusion list OFF: {sorted(excl_off)}")
    print(f"exclusion-list identical: {sorted(excl_on) == sorted(excl_off)}")
    print()
    empty_diff = not regime_diffs and sorted(excl_on) == sorted(excl_off)
    uw_dead = len(uw_nonnone) == 0
    if empty_diff and uw_dead:
        print("VERDICT: PASS — UW None for all tickers today; regime + exclusion bit-identical")
        print("ON vs OFF across the FULL universe. Flip uw_gex_fetch_enabled=False is")
        print("output-invariant. Safe to flip (in the holiday window, with post-verify).")
    elif not uw_dead:
        print("VERDICT: STOP — UW returned non-None for some ticker(s) today. UW is NOT 100%")
        print("dead → flipping is NOT output-invariant for those tickers. DO NOT FLIP; report.")
    else:
        print("VERDICT: STOP — regime/exclusion diff is non-empty. Investigate before flipping.")


if __name__ == "__main__":
    main()
