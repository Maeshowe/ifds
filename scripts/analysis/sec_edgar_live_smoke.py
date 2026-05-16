"""Live SEC EDGAR smoke test — Fázis 1, Task #3 deploy guard.

Enforces the [ifds-rules.md] "Rate-limit live-smoke" rule before commit.
Uses the real universe snapshot from `state/universe_snapshots/{date}.json` to
hit data.sec.gov at production-equivalent load and verifies the 3 metrics:

    - Success rate (200 / total)   target: >= 95%
    - Hard error rate (429 + exc)  target: <= 5%
    - Wall-clock                   target: <= 5 min (full universe)

CLI:
    python scripts/analysis/sec_edgar_live_smoke.py --universe 2026-05-15 [--sample 200]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Make src/ importable when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ifds.data.sec_edgar import SecEdgarClient, SecEdgarError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", default="2026-05-15",
                        help="Date string for state/universe_snapshots/{date}.json")
    parser.add_argument("--sample", type=int, default=0,
                        help="Limit to first N tickers (0 = full universe)")
    parser.add_argument("--cache-dir", default="state/sec_cache_smoke",
                        help="Isolated cache dir for the smoke run")
    args = parser.parse_args()

    snap_path = Path(f"state/universe_snapshots/{args.universe}.json")
    if not snap_path.exists():
        print(f"ERROR: snapshot not found: {snap_path}", file=sys.stderr)
        return 1
    tickers = [row["symbol"] for row in json.loads(snap_path.read_text())]
    if args.sample > 0:
        tickers = tickers[:args.sample]
    print(f"smoke set: {len(tickers)} tickers from {snap_path}")

    ua = os.environ.get("IFDS_SEC_EDGAR_USER_AGENT")
    if not ua or "<set" in ua:
        print("ERROR: IFDS_SEC_EDGAR_USER_AGENT env var not set", file=sys.stderr)
        return 1

    client = SecEdgarClient(cache_dir=Path(args.cache_dir), user_agent=ua)
    # Force CIK map fetch upfront so per-ticker timing is just submissions
    t0_map = time.monotonic()
    client._load_or_fetch_cik_map()
    map_secs = time.monotonic() - t0_map
    print(f"CIK map: {len(client._cik_map)} entries in {map_secs:.1f}s")

    success = 0
    not_found = 0
    hard_err = 0
    exc_count = 0
    excluded = 0
    t0 = time.monotonic()

    for i, ticker in enumerate(tickers, 1):
        try:
            cik = client.ticker_to_cik(ticker)
            if cik is None:
                not_found += 1
                continue
            # has_upcoming_10q_or_10k goes through get_recent_filings → _http_get_json
            flagged = client.has_upcoming_10q_or_10k(ticker, lookahead_days=10)
            success += 1
            if flagged:
                excluded += 1
        except SecEdgarError as exc:
            if "429" in str(exc):
                hard_err += 1
            else:
                exc_count += 1
        except Exception as exc:  # noqa: BLE001
            exc_count += 1
            print(f"  unexpected: {ticker}: {type(exc).__name__}: {exc}", file=sys.stderr)

        if i % 25 == 0 or i == len(tickers):
            elapsed = time.monotonic() - t0
            print(f"  [{i}/{len(tickers)}] success={success} not_found={not_found} "
                  f"hard_err={hard_err} exc={exc_count} flagged={excluded} "
                  f"elapsed={elapsed:.1f}s")

    elapsed = time.monotonic() - t0
    total_checked = success + hard_err + exc_count  # not_found doesn't count
    success_rate = 100 * success / total_checked if total_checked else 0
    hard_err_rate = 100 * (hard_err + exc_count) / total_checked if total_checked else 0

    print("\n=== SUMMARY ===")
    print(f"tickers tested        : {len(tickers)}")
    print(f"CIK not found         : {not_found} (not counted toward rates)")
    print(f"success               : {success}")
    print(f"hard errors (429)     : {hard_err}")
    print(f"other exceptions      : {exc_count}")
    print(f"flagged (10-Q upcoming): {excluded}")
    print(f"success rate          : {success_rate:.1f}% (target >= 95%)")
    print(f"hard error rate       : {hard_err_rate:.1f}% (target <= 5%)")
    print(f"wall clock            : {elapsed:.1f}s ({elapsed/60:.1f} min, target <= 5min for full)")

    gate_pass = success_rate >= 95.0 and hard_err_rate <= 5.0
    print(f"GATE                  : {'PASS' if gate_pass else 'FAIL'}")
    return 0 if gate_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
