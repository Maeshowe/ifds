#!/usr/bin/env python3
"""Live API integration test — validates all IFDS v2.0 API clients against real endpoints.

Usage: python tests/live_api_test.py
Requires: .env with IFDS_POLYGON_API_KEY, IFDS_FMP_API_KEY, IFDS_FRED_API_KEY, IFDS_UW_API_KEY
"""

import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# Load .env manually (no dotenv dependency)
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ[key.strip()] = val.strip().strip('"')

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ifds.data.polygon import PolygonClient
from ifds.data.fmp import FMPClient
from ifds.data.fred import FREDClient
from ifds.data.unusual_whales import UnusualWhalesClient
from ifds.data.adapters import (
    UWGEXProvider, PolygonGEXProvider, UWDarkPoolProvider,
    FallbackGEXProvider, FallbackDarkPoolProvider,
)

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SKIP = "\033[93mSKIP\033[0m"
BOLD = "\033[1m"
RESET = "\033[0m"

results = {"pass": 0, "fail": 0, "skip": 0}


def report(name: str, ok: bool, detail: str = "", skip: bool = False):
    if skip:
        results["skip"] += 1
        print(f"  {SKIP} {name}: {detail}")
    elif ok:
        results["pass"] += 1
        print(f"  {PASS} {name}: {detail}")
    else:
        results["fail"] += 1
        print(f"  {FAIL} {name}: {detail}")


def test_polygon(api_key: str):
    print(f"\n{BOLD}=== POLYGON ==={RESET}")
    client = PolygonClient(api_key=api_key, timeout=15)

    # Health check
    health = client.check_health()
    report("Health check", health.status.value == "ok",
           f"status={health.status.value} time={health.response_time_ms:.0f}ms")

    # Grouped daily
    yesterday = (date.today() - timedelta(days=3)).isoformat()
    bars = client.get_grouped_daily(yesterday)
    report("Grouped daily", bars is not None and len(bars) > 0,
           f"{len(bars)} tickers" if bars else "None returned")

    # AAPL aggregates (90 days)
    from_date = (date.today() - timedelta(days=90)).isoformat()
    to_date = date.today().isoformat()
    aggs = client.get_aggregates("AAPL", from_date, to_date)
    report("AAPL aggregates (90d)", aggs is not None and len(aggs) > 0,
           f"{len(aggs)} bars" if aggs else "None returned")

    # Options snapshot
    opts = client.get_options_snapshot("AAPL")
    report("AAPL options snapshot", opts is not None and len(opts) > 0,
           f"{len(opts)} contracts" if opts else "None returned")

    if opts and len(opts) > 0:
        sample = opts[0]
        has_greeks = "greeks" in sample
        has_details = "details" in sample
        has_oi = "open_interest" in sample or "open_interest" in sample.get("day", {})
        report("  → has greeks", has_greeks, f"keys: {list(sample.get('greeks', {}).keys())[:5]}")
        report("  → has details", has_details, f"keys: {list(sample.get('details', {}).keys())[:5]}")
        report("  → has open_interest", has_oi,
               f"root={sample.get('open_interest')}, day={sample.get('day', {}).get('open_interest')}")

    client.close()


def test_fmp(api_key: str):
    print(f"\n{BOLD}=== FMP ==={RESET}")
    client = FMPClient(api_key=api_key, timeout=15)

    # Health check
    health = client.check_health()
    report("Health check", health.status.value == "ok",
           f"status={health.status.value} time={health.response_time_ms:.0f}ms")

    # Company screener
    screener = client.screener({"marketCapMoreThan": 100_000_000_000, "limit": 5})
    report("Company screener", screener is not None and len(screener) > 0,
           f"{len(screener)} companies" if screener else "None returned")

    if screener and len(screener) > 0:
        sample = screener[0]
        report("  → sample fields", True, f"{list(sample.keys())[:8]}")

    # Earnings calendar
    from_d = date.today().isoformat()
    to_d = (date.today() + timedelta(days=14)).isoformat()
    earnings = client.get_earnings_calendar(from_d, to_d)
    report("Earnings calendar", earnings is not None,
           f"{len(earnings)} entries" if earnings else "None returned")

    # Insider trading
    insiders = client.get_insider_trading("AAPL")
    report("Insider trading (AAPL)", insiders is not None and len(insiders) > 0,
           f"{len(insiders)} trades" if insiders else "None returned")

    if insiders and len(insiders) > 0:
        sample = insiders[0]
        report("  → sample fields", True, f"{list(sample.keys())[:8]}")

    # Key metrics
    metrics = client.get_key_metrics("AAPL")
    report("Key metrics (AAPL)", metrics is not None,
           f"keys: {list(metrics.keys())[:6]}" if metrics else "None returned")

    # Financial growth
    growth = client.get_financial_growth("AAPL")
    report("Financial growth (AAPL)", growth is not None,
           f"keys: {list(growth.keys())[:6]}" if growth else "None returned")

    client.close()


def test_fred(api_key: str):
    print(f"\n{BOLD}=== FRED ==={RESET}")
    client = FREDClient(api_key=api_key, timeout=15)

    # Health check
    health = client.check_health()
    report("Health check", health.status.value == "ok",
           f"status={health.status.value} time={health.response_time_ms:.0f}ms")

    # VIX
    vix = client.get_vix(limit=5)
    report("VIX data", vix is not None and len(vix) > 0,
           f"{len(vix)} obs, latest={vix[0]}" if vix else "None returned")

    # TNX (10Y yield)
    tnx = client.get_tnx(limit=5)
    report("TNX (10Y yield)", tnx is not None and len(tnx) > 0,
           f"{len(tnx)} obs, latest={tnx[0]}" if tnx else "None returned")

    client.close()


def test_unusual_whales(api_key: str):
    print(f"\n{BOLD}=== UNUSUAL WHALES ==={RESET}")
    client = UnusualWhalesClient(api_key=api_key, timeout=15)

    # Health check
    health = client.check_health()
    report("Health check", health.status.value == "ok",
           f"status={health.status.value} time={health.response_time_ms:.0f}ms")

    # Dark Pool
    dp = client.get_dark_pool("SPY")
    report("Dark Pool (SPY)", dp is not None and len(dp) > 0,
           f"{len(dp)} records" if dp else "None returned")

    if dp and len(dp) > 0:
        sample = dp[0]
        report("  → sample fields", True, f"{list(sample.keys())[:8]}")
        has_nbbo = "nbbo_ask" in sample and "nbbo_bid" in sample
        report("  → has NBBO fields", has_nbbo,
               f"nbbo_ask={sample.get('nbbo_ask')}, nbbo_bid={sample.get('nbbo_bid')}")

    # Greek Exposure
    greeks = client.get_greeks("SPY")
    report("Greek Exposure (SPY)", greeks is not None,
           f"keys: {list(greeks.keys())[:8]}" if greeks else "None returned")

    if greeks:
        has_gamma = "call_gamma" in greeks or "put_gamma" in greeks
        report("  → has gamma fields", has_gamma,
               f"call_gamma={greeks.get('call_gamma')}, put_gamma={greeks.get('put_gamma')}")

    client.close()
    return client


def test_adapters(polygon_key: str, uw_key: str):
    print(f"\n{BOLD}=== ADAPTERS (Fallback Chain) ==={RESET}")
    polygon = PolygonClient(api_key=polygon_key, timeout=15)
    uw = UnusualWhalesClient(api_key=uw_key, timeout=15)

    # GEX fallback: UW → Polygon
    uw_gex = UWGEXProvider(uw)
    poly_gex = PolygonGEXProvider(polygon)
    fallback_gex = FallbackGEXProvider(uw_gex, poly_gex)

    gex_result = fallback_gex.get_gex("AAPL")
    report("FallbackGEX (AAPL)", gex_result is not None,
           f"source={gex_result.get('source')}, net_gex={gex_result.get('net_gex', 0):.0f}, "
           f"call_wall={gex_result.get('call_wall')}, put_wall={gex_result.get('put_wall')}, "
           f"zero_gamma={gex_result.get('zero_gamma')}"
           if gex_result else "None — both providers failed")

    if gex_result and gex_result.get("gex_by_strike"):
        report("  → gex_by_strike", True,
               f"{len(gex_result['gex_by_strike'])} strikes")

    # Dark Pool fallback
    uw_dp = UWDarkPoolProvider(uw)
    fallback_dp = FallbackDarkPoolProvider(uw_dp)

    dp_result = fallback_dp.get_dark_pool("SPY")
    report("FallbackDP (SPY)", dp_result is not None,
           f"signal={dp_result.get('signal')}, dp_volume={dp_result.get('dp_volume')}, "
           f"buys={dp_result.get('dp_buys')}, sells={dp_result.get('dp_sells')}"
           if dp_result else "None — no dark pool data")

    polygon.close()
    uw.close()


def main():
    print(f"{BOLD}IFDS v2.0 — Live API Integration Test{RESET}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    poly_key = os.environ.get("IFDS_POLYGON_API_KEY")
    fmp_key = os.environ.get("IFDS_FMP_API_KEY")
    fred_key = os.environ.get("IFDS_FRED_API_KEY")
    uw_key = os.environ.get("IFDS_UW_API_KEY")

    if poly_key:
        test_polygon(poly_key)
    else:
        print(f"\n{SKIP} POLYGON: No API key")

    if fmp_key:
        test_fmp(fmp_key)
    else:
        print(f"\n{SKIP} FMP: No API key")

    if fred_key:
        test_fred(fred_key)
    else:
        print(f"\n{SKIP} FRED: No API key")

    if uw_key:
        test_unusual_whales(uw_key)
    else:
        print(f"\n{SKIP} UW: No API key")

    if poly_key and uw_key:
        test_adapters(poly_key, uw_key)
    else:
        print(f"\n{SKIP} ADAPTERS: Missing Polygon or UW key")

    # Summary
    total = results["pass"] + results["fail"] + results["skip"]
    print(f"\n{BOLD}{'='*50}{RESET}")
    print(f"  {PASS}: {results['pass']}  |  {FAIL}: {results['fail']}  |  {SKIP}: {results['skip']}  |  Total: {total}")
    print(f"{'='*50}")

    return 0 if results["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
