#!/usr/bin/env python3
"""
IFDS — FMP ETF Holdings Live Validation
========================================
Teszteli a 42 ETF /stable/etf/holdings elérhetőségét FMP-n.

Futtatás:
    source .env && python scripts/validate_etf_holdings.py

Output:
    - Konzol: összesítő + per-ETF státusz
    - docs/planning/etf_holdings_validation_YYYYMMDD.json
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp

# Load .env if running as standalone script
_env_file = Path(__file__).resolve().parents[1] / ".env"
if _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip().strip("\"'"))

ETF_UNIVERSE = [
    ("L1", "XLK", "YES"),
    ("L1", "XLF", "YES"),
    ("L1", "XLE", "YES"),
    ("L1", "XLV", "YES"),
    ("L1", "XLY", "YES"),
    ("L1", "XLP", "YES"),
    ("L1", "XLI", "YES"),
    ("L1", "XLB", "YES"),
    ("L1", "XLRE", "YES"),
    ("L1", "XLU", "YES"),
    ("L1", "XLC", "YES"),
    ("L2", "SMH", "YES"),
    ("L2", "SOXX", "YES"),
    ("L2", "XSD", "NO"),
    ("L2", "IGV", "YES"),
    ("L2", "SKYY", "CONDITIONAL"),
    ("L2", "CIBR", "YES"),
    ("L2", "HACK", "CONDITIONAL"),
    ("L2", "KRE", "YES"),
    ("L2", "KBE", "YES"),
    ("L2", "KCE", "NO"),
    ("L2", "KIE", "CONDITIONAL"),
    ("L2", "XBI", "YES"),
    ("L2", "IBB", "YES"),
    ("L2", "IHI", "YES"),
    ("L2", "XOP", "YES"),
    ("L2", "XME", "YES"),
    ("L2", "XAR", "CONDITIONAL"),
    ("L2", "ITA", "CONDITIONAL"),
    ("L2", "PAVE", "YES"),
    ("L2", "JETS", "CONDITIONAL"),
    ("L2", "XHB", "YES"),
    ("L2", "ITB", "YES"),
    ("L2", "XRT", "CONDITIONAL"),
    ("L2", "IYR", "YES"),
    ("L2", "FDN", "YES"),
    ("L2", "KWEB", "YES"),
    ("L2", "BOTZ", "YES"),
    ("L2", "TAN", "CONDITIONAL"),
    ("L2", "ICLN", "CONDITIONAL"),
    ("L2", "LIT", "CONDITIONAL"),
    ("L2", "ARKK", "YES"),
]

FMP_BASE = "https://financialmodelingprep.com/stable"
SEMAPHORE_LIMIT = 5
REQUEST_TIMEOUT = 10
RETRY_COUNT = 2
RETRY_DELAY = 2.0


async def test_etf(
    session: aiohttp.ClientSession,
    ticker: str,
    api_key: str,
    sem: asyncio.Semaphore,
) -> dict[str, Any]:
    """Egyetlen ETF holdings endpoint tesztelése."""
    url = f"{FMP_BASE}/etf/holdings"
    params = {"symbol": ticker, "apikey": api_key}

    async with sem:
        for attempt in range(RETRY_COUNT + 1):
            try:
                t0 = time.monotonic()
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                ) as resp:
                    ms = round((time.monotonic() - t0) * 1000)
                    code = resp.status

                    if code == 200:
                        data = await resp.json(content_type=None)
                        if isinstance(data, list) and data:
                            f = data[0]
                            return {
                                "ticker": ticker,
                                "status": "OK",
                                "http": 200,
                                "count": len(data),
                                "sample": f.get("asset") or f.get("symbol", "?"),
                                "weight": f.get("weightPercentage") or f.get("weight"),
                                "latency_ms": ms,
                                "error": None,
                            }
                        elif isinstance(data, list):
                            return _r(ticker, "EMPTY", 200, ms, "Empty [] — Ultimate plan?")
                        else:
                            return _r(ticker, "ERROR", 200, ms, str(data)[:80])

                    elif code == 429:
                        if attempt < RETRY_COUNT:
                            await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                            continue
                        return _r(ticker, "ERROR", 429, ms, "Rate limited")

                    elif code in (401, 403):
                        return _r(ticker, "ERROR", code, ms, "Auth error — check plan/key")

                    elif code == 404:
                        return _r(ticker, "ERROR", 404, ms, "Not found")

                    else:
                        if attempt < RETRY_COUNT:
                            await asyncio.sleep(RETRY_DELAY)
                            continue
                        return _r(ticker, "ERROR", code, ms, f"HTTP {code}")

            except asyncio.TimeoutError:
                if attempt < RETRY_COUNT:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                return _r(ticker, "ERROR", 0, 0, f"Timeout >{REQUEST_TIMEOUT}s")

            except Exception as exc:
                return _r(ticker, "ERROR", 0, 0, str(exc)[:80])

    return _r(ticker, "ERROR", 0, 0, "Max retries exceeded")


def _r(ticker: str, status: str, http: int, ms: int, error: str) -> dict:
    return {
        "ticker": ticker,
        "status": status,
        "http": http,
        "count": 0,
        "sample": None,
        "weight": None,
        "latency_ms": ms,
        "error": error,
    }


async def run_all(api_key: str) -> list[dict]:
    sem = asyncio.Semaphore(SEMAPHORE_LIMIT)
    conn = aiohttp.TCPConnector(limit=SEMAPHORE_LIMIT)
    async with aiohttp.ClientSession(connector=conn) as session:
        return list(
            await asyncio.gather(*[test_etf(session, t, api_key, sem) for _, t, _ in ETF_UNIVERSE])
        )


def build_report(raw: list[dict]) -> dict:
    umap = {t: (tier, ifds) for tier, t, ifds in ETF_UNIVERSE}
    results = []
    for r in raw:
        tier, ifds = umap.get(r["ticker"], ("?", "?"))
        results.append({**r, "tier": tier, "ifds": ifds})

    ok = [r for r in results if r["status"] == "OK"]
    empty = [r for r in results if r["status"] == "EMPTY"]
    err = [r for r in results if r["status"] == "ERROR"]

    matrix: dict[str, dict[str, int]] = {}
    for r in results:
        k = r["ifds"]
        matrix.setdefault(k, {"OK": 0, "EMPTY": 0, "ERROR": 0})
        matrix[k][r["status"]] += 1

    return {
        "validated_at": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "ok": len(ok),
            "empty": len(empty),
            "error": len(err),
            "ok_pct": round(len(ok) / len(results) * 100, 1),
            "avg_latency_ms": (round(sum(r["latency_ms"] for r in ok) / len(ok)) if ok else 0),
        },
        "pipeline_matrix": matrix,
        "results": sorted(results, key=lambda x: (x["tier"], x["status"], x["ticker"])),
    }


def print_report(report: dict) -> None:
    s = report["summary"]
    rs = report["results"]
    icon = {"OK": "✅", "EMPTY": "⚠️ ", "ERROR": "❌"}

    print(f"\n{'='*66}")
    print(f"  IFDS — FMP ETF Holdings Validation  {report['validated_at'][:19]}")
    print(f"{'='*66}")
    print(f"  Tesztelt : {s['total']} ETF")
    print(f"  ✅ OK    : {s['ok']:3d}  ({s['ok_pct']}%)")
    print(f"  ⚠️  EMPTY : {s['empty']:3d}  (endpoint él, adat nincs)")
    print(f"  ❌ ERROR : {s['error']:3d}")
    print(f"  Latencia : átl. {s['avg_latency_ms']} ms")

    print("\n  Pipeline × API:")
    print(f"  {'IFDS':<14} {'OK':>4} {'EMPTY':>6} {'ERROR':>6}")
    print(f"  {'-'*32}")
    for k, v in sorted(report["pipeline_matrix"].items()):
        print(f"  {k:<14} {v['OK']:>4} {v['EMPTY']:>6} {v['ERROR']:>6}")

    print(f"\n{'─'*66}")
    print(f"  {'Ticker':<6}  {'T':<2}  {'IFDS':<12}  {'':5}  {'N':>5}  {'ms':>5}  Info")
    print(f"{'─'*66}")
    for r in rs:
        note = r["error"] or f"sample={r['sample']}"
        note = (note[:24] + "…") if len(note or "") > 25 else (note or "")
        cnt = str(r["count"]) if r["count"] else "—"
        lat = str(r["latency_ms"]) if r["latency_ms"] else "—"
        print(
            f"  {r['ticker']:<6}  {r['tier']:<2}  {r['ifds']:<12}  "
            f"{icon.get(r['status'], '?')}  {cnt:>5}  {lat:>5}  {note}"
        )
    print(f"{'='*66}\n")

    empty_t = [r["ticker"] for r in rs if r["status"] == "EMPTY"]
    error_t = [r["ticker"] for r in rs if r["status"] == "ERROR"]

    if empty_t:
        print(f"  ⚠️  EMPTY ({len(empty_t)}): {', '.join(empty_t)}")
        print("     → FMP Ultimate plan kell, vagy: GET /api/v3/etf-holder/{TICKER}")
    if error_t:
        print(f"\n  ❌ ERROR ({len(error_t)}): {', '.join(error_t)}")
        print("     → Részletek a JSON riportban")
    print()


def save_report(report: dict, out_dir: str = "docs/planning") -> str:
    os.makedirs(out_dir, exist_ok=True)
    fname = f"etf_holdings_validation_{datetime.now().strftime('%Y%m%d')}.json"
    path = os.path.join(out_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return path


def main() -> None:
    api_key = os.environ.get("IFDS_FMP_API_KEY")
    if not api_key:
        print("❌  FMP_API_KEY nincs beállítva.")
        print("    Futtasd: source .env && python scripts/validate_etf_holdings.py")
        return

    print(f"🔍  FMP ETF Holdings validáció — {len(ETF_UNIVERSE)} ETF...")
    t0 = time.monotonic()
    raw = asyncio.run(run_all(api_key))
    print(f"    Kész {round(time.monotonic() - t0, 1)}s alatt.\n")

    report = build_report(raw)
    print_report(report)
    path = save_report(report)
    print(f"  💾  Mentve: {path}\n")


if __name__ == "__main__":
    main()
