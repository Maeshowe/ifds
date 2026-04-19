#!/usr/bin/env python3
"""UW Quick Wins — Before/After Verification.

Compares the OLD (limit=200, no UW-CLIENT-API-ID header) vs NEW
(limit=500, full headers) behavior of the UW dark pool endpoint for a
small set of top-liquidity tickers. Produces a markdown summary of the
data-richness delta.

Run with live API key. Output: docs/analysis/uw-quick-wins-verification.md.

Usage:
    set -a && source .env && set +a
    python scripts/analysis/uw_quick_wins_verification.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = PROJECT_ROOT / "docs" / "analysis" / "uw-quick-wins-verification.md"

# Top 10 from ticker_liquidity_audit_v2 (high-DP-coverage liquid names)
TICKERS = ["LITE", "SNDK", "MU", "INTC", "NVDA", "TSM", "AAOI", "WDC", "AMD", "XOM"]

UW_BASE = "https://api.unusualwhales.com"


def _fetch(ticker: str, api_key: str, *, new_mode: bool) -> dict:
    """Returns {records: list, status: int, error: str|None}."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "PythonClient",
    }
    if new_mode:
        headers["UW-CLIENT-API-ID"] = "100001"
        headers["Accept"] = "application/json"

    params = {"limit": 500 if new_mode else 200}
    url = f"{UW_BASE}/api/darkpool/{ticker}"
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code != 200:
            return {"records": [], "status": r.status_code,
                    "error": r.text[:200]}
        payload = r.json()
        records = payload.get("data", []) if isinstance(payload, dict) else []
        return {"records": records, "status": r.status_code, "error": None}
    except Exception as e:
        return {"records": [], "status": 0, "error": str(e)}


def _summarize(records: list[dict]) -> dict:
    """Compute comparable stats on the raw DP record list."""
    if not records:
        return {"count": 0, "total_size": 0, "total_dollars": 0.0,
                "with_premium": 0}
    total_size = 0
    total_dollars = 0.0
    with_premium = 0
    for r in records:
        try:
            total_size += int(float(r.get("size", 0)))
        except (TypeError, ValueError):
            pass
        premium = r.get("premium")
        if premium is not None:
            with_premium += 1
            try:
                total_dollars += float(premium)
            except (TypeError, ValueError):
                pass
    return {
        "count": len(records),
        "total_size": total_size,
        "total_dollars": total_dollars,
        "with_premium": with_premium,
    }


def main() -> None:
    api_key = os.environ.get("IFDS_UW_API_KEY")
    if not api_key:
        print("ERROR: IFDS_UW_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    print(f"Verifying {len(TICKERS)} tickers: {TICKERS}")
    lines: list[str] = []
    lines.append("# UW Client Quick Wins — Verification")
    lines.append("")
    lines.append("Compares OLD (limit=200, no UW-CLIENT-API-ID) vs "
                 "NEW (limit=500, UW-CLIENT-API-ID: 100001 + Accept).")
    lines.append("")
    lines.append("| Ticker | OLD count | NEW count | Δ | OLD $ | NEW $ | OLD prem-coverage | NEW prem-coverage |")
    lines.append("|--------|-----------|-----------|---|-------|-------|-------------------|-------------------|")

    totals_old = {"count": 0, "size": 0, "dollars": 0.0}
    totals_new = {"count": 0, "size": 0, "dollars": 0.0}

    for t in TICKERS:
        print(f"  {t}...", end="", flush=True)
        old = _fetch(t, api_key, new_mode=False)
        time.sleep(0.3)
        new = _fetch(t, api_key, new_mode=True)
        time.sleep(0.3)

        if old["error"] or new["error"]:
            print(f" ERROR (old={old['error']}, new={new['error']})")
            lines.append(f"| {t} | ERR | ERR | — | — | — | — | — |")
            continue

        so = _summarize(old["records"])
        sn = _summarize(new["records"])
        totals_old["count"] += so["count"]
        totals_old["size"] += so["total_size"]
        totals_old["dollars"] += so["total_dollars"]
        totals_new["count"] += sn["count"]
        totals_new["size"] += sn["total_size"]
        totals_new["dollars"] += sn["total_dollars"]

        old_prem_cov = f"{so['with_premium']}/{so['count']}" if so["count"] else "0/0"
        new_prem_cov = f"{sn['with_premium']}/{sn['count']}" if sn["count"] else "0/0"
        delta = sn["count"] - so["count"]
        lines.append(
            f"| {t} | {so['count']} | {sn['count']} | {delta:+d} "
            f"| ${so['total_dollars']:,.0f} | ${sn['total_dollars']:,.0f} "
            f"| {old_prem_cov} | {new_prem_cov} |"
        )
        print(f" old={so['count']}, new={sn['count']} ({delta:+d})")

    lines.append("")
    lines.append("## Totals")
    lines.append("")
    lines.append(f"- OLD: {totals_old['count']} records, "
                 f"{totals_old['size']:,} shares, "
                 f"${totals_old['dollars']:,.0f}")
    lines.append(f"- NEW: {totals_new['count']} records, "
                 f"{totals_new['size']:,} shares, "
                 f"${totals_new['dollars']:,.0f}")
    if totals_old["count"] > 0:
        uplift = totals_new["count"] / totals_old["count"] - 1
        lines.append(f"- Record count uplift: {uplift:+.0%}")

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- `NEW count > OLD count` → `limit=500` delivers more DP records per ticker")
    lines.append("- `NEW $ > OLD $` → `premium` aggregation now captures true dollar volume")
    lines.append("- `prem-coverage` — premium field presence per record (should be 100% of records)")
    lines.append("")
    lines.append("---")
    lines.append("*Generated by `scripts/analysis/uw_quick_wins_verification.py`*")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        f.write("\n".join(lines))
    print(f"\nReport: {OUT_PATH}")


if __name__ == "__main__":
    main()
