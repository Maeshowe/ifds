#!/usr/bin/env python3
"""Company Intelligence — AI-powered post-pipeline ticker briefs.

Reads the latest execution plan CSV and generates intelligence briefs
for each ticker using FMP data + Anthropic Sonnet API.

Usage:
    python scripts/company_intel.py              # CLI only
    python scripts/company_intel.py --telegram   # CLI + Telegram
    python scripts/company_intel.py --file path  # Specific CSV
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FMP_BASE = "https://financialmodelingprep.com"
ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
TELEGRAM_CHAR_LIMIT = 4096
TRANSCRIPT_MAX_CHARS = 3000


def _env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


# ---------------------------------------------------------------------------
# FMP API helpers
# ---------------------------------------------------------------------------

def _fmp_get(endpoint: str, params: dict, api_key: str) -> list | None:
    """GET from FMP stable API. Returns parsed JSON or None on error."""
    import requests

    params["apikey"] = api_key
    url = f"{FMP_BASE}{endpoint}"
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        return [data] if isinstance(data, dict) else None
    except Exception as e:
        print(f"  [WARN] FMP {endpoint} failed: {e}")
        return None


def fetch_transcript(symbol: str, api_key: str) -> str | None:
    """Fetch latest earnings transcript excerpt."""
    # Step 1: get transcript dates
    dates = _fmp_get("/stable/earning-call-transcript-dates",
                     {"symbol": symbol}, api_key)
    if not dates:
        return None

    latest = dates[0]
    year = latest.get("fiscalYear") or latest.get("year")
    quarter = latest.get("quarter")
    if not year or not quarter:
        return None

    # Step 2: get transcript content
    transcripts = _fmp_get("/stable/earning-call-transcript",
                           {"symbol": symbol, "year": year, "quarter": quarter},
                           api_key)
    if not transcripts:
        return None

    content = transcripts[0].get("content", "")
    return content[:TRANSCRIPT_MAX_CHARS] if content else None


def fetch_price_target(symbol: str, api_key: str) -> dict | None:
    """Fetch analyst price target consensus."""
    data = _fmp_get("/stable/price-target-consensus",
                    {"symbol": symbol}, api_key)
    if data:
        return data[0]
    return None


def fetch_earnings_surprises(symbol: str, api_key: str) -> list:
    """Fetch last 4 quarters of earnings data with beat/miss calculation."""
    data = _fmp_get("/stable/earnings",
                    {"symbol": symbol}, api_key)
    if not data:
        return []

    results = []
    for item in data[:4]:
        actual = item.get("epsActual")
        estimated = item.get("epsEstimated")
        surprise_pct = None
        if isinstance(actual, (int, float)) and isinstance(estimated, (int, float)) and estimated != 0:
            surprise_pct = (actual - estimated) / abs(estimated) * 100
        results.append({
            "date": item.get("date", "?"),
            "actualEarningResult": actual,
            "estimatedEarning": estimated,
            "surprisePct": surprise_pct,
        })
    return results


# ---------------------------------------------------------------------------
# Anthropic API
# ---------------------------------------------------------------------------

def generate_brief(symbol: str, sector: str, score: float, price: float,
                   stop_loss: float, take_profit: float,
                   target: dict | None, surprises: list,
                   transcript: str | None) -> str | None:
    """Generate intelligence brief using Anthropic Sonnet."""
    try:
        import anthropic
    except ImportError:
        print("  [ERROR] anthropic package not installed")
        return None

    # Format earnings surprises
    if surprises:
        lines = []
        for s in surprises:
            actual = s.get("actualEarningResult", "?")
            est = s.get("estimatedEarning", "?")
            dt = s.get("date", "?")
            pct = s.get("surprisePct")
            beat = "BEAT" if isinstance(actual, (int, float)) and isinstance(est, (int, float)) and actual >= est else "MISS"
            pct_str = f" ({pct:+.1f}%)" if pct is not None else ""
            lines.append(f"  {dt}: Actual={actual}, Est={est} → {beat}{pct_str}")
        earnings_text = "\n".join(lines)
    else:
        earnings_text = "  Nincs elérhető adat"

    # Format target
    tc = target.get("targetConsensus", "N/A") if target else "N/A"
    tl = target.get("targetLow", "N/A") if target else "N/A"
    th = target.get("targetHigh", "N/A") if target else "N/A"

    # Format transcript
    transcript_section = f"\nLegutóbbi earnings transcript (kivonat, max 3000 karakter):\n{transcript}" if transcript else "\nNincs elérhető earnings transcript."

    prompt = f"""Te egy részvényelemző vagy. Az alábbi adatforrásokból készíts tömör intelligence brief-et MAGYARUL.

KRITIKUS SZABÁLYOK:
- KIZÁRÓLAG az alább megadott adatokból dolgozz. NE használd a saját tudásodat a cégről.
- Ha egy kérdésre nincs adat az alább megadott forrásokban, írd: "Nincs elérhető adat."
- NE találj ki dátumokat, számokat, eseményeket. Csak azt írd amit az adatokban látsz.
- Az earnings transcript-et TÉNYKÉNT kezeld, de jelezd ha a kivonat nem tartalmaz elég infót.

ADATFORRÁSOK:

Ticker: {symbol} — {sector}
IFDS Combined Score: {score}
Jelenlegi ár: ${price} | Stop Loss: ${stop_loss} | Take Profit: ${take_profit}
Analyst Consensus Target: ${tc} (Low: ${tl}, High: ${th})

Earnings Beat/Miss (utolsó 4Q):
{earnings_text}
{transcript_section}

Válaszolj PONTOSAN ebben a formátumban (max 150 szó összesen):

DRIVER: [Mi hajtja most az üzletet? Csak a transcript és earnings adatok alapján. 1-2 mondat]
KOCKÁZAT: [Mi a legnagyobb kockázat a következő 30 napban? Earnings miss trend, target vs ár eltérés, stb. 1-2 mondat]
ELLENTMONDÁS: [Van-e bármi az adatokban ami ellentmond az IFDS scoring-nak? Pl. sorozatos earnings miss + magas score, vagy ár > analyst target. Ha nincs, írd: "Nincs azonosított ellentmondás." 1 mondat]
CATALYST: [Következő események CSAK az earnings adatokból. Ha nincs pontos dátum az adatokban, írd: "Nem azonosítható a megadott adatokból."]"""

    try:
        client = anthropic.Anthropic()
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        print(f"  [ERROR] Anthropic API failed for {symbol}: {e}")
        return None


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def find_latest_csv(output_dir: str = "output") -> Path | None:
    """Find the most recent execution_plan CSV."""
    p = Path(output_dir)
    files = sorted(p.glob("execution_plan_run_*.csv"), reverse=True)
    return files[0] if files else None


def load_tickers(csv_path: Path) -> list[dict]:
    """Load ticker data from execution plan CSV."""
    tickers = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tickers.append({
                "symbol": row["instrument_id"],
                "price": float(row["limit_price"]),
                "score": float(row["score"]),
                "sector": row["sector"],
                "stop_loss": float(row["stop_loss"]),
                "take_profit": float(row["take_profit_1"]),
                "risk": float(row.get("risk_usd", 0)),
            })
    return tickers


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_cli_ticker(t: dict, target: dict | None, surprises: list,
                      brief: str | None) -> str:
    """Format one ticker block for CLI."""
    sym = t["symbol"]
    sector = t["sector"]
    score = t["score"]
    price = t["price"]
    sl = t["stop_loss"]
    tp = t["take_profit"]
    risk = t["risk"]

    tc = target.get("targetConsensus", "N/A") if target else "N/A"
    tl = target.get("targetLow", "N/A") if target else "N/A"
    th = target.get("targetHigh", "N/A") if target else "N/A"

    # Earnings beat count
    beats = 0
    for s in surprises:
        a = s.get("actualEarningResult")
        e = s.get("estimatedEarning")
        if isinstance(a, (int, float)) and isinstance(e, (int, float)) and a >= e:
            beats += 1
    n = len(surprises)
    earnings_line = f"{beats}/{n} beat (last {n}Q)" if n > 0 else "N/A"

    lines = [
        f"\n{'='*60}",
        f"  {sym} — {sector}",
        f"{'='*60}",
        f"  Score: {score} | Price: ${price} | Target: ${tc} (Low: ${tl}, High: ${th})",
        f"  Stop: ${sl} | TP: ${tp} | Risk: ${risk}",
        f"  Earnings: {earnings_line}",
    ]

    if brief:
        lines.append("")
        for line in brief.strip().split("\n"):
            lines.append(f"  {line}")

    return "\n".join(lines)


def format_telegram_ticker(t: dict, target: dict | None, surprises: list,
                           brief: str | None) -> str:
    """Format one ticker block for Telegram HTML."""
    sym = t["symbol"]
    sector = t["sector"]
    score = t["score"]
    price = t["price"]
    sl = t["stop_loss"]
    tp = t["take_profit"]

    tc = target.get("targetConsensus", "N/A") if target else "N/A"
    tl = target.get("targetLow", "N/A") if target else "N/A"
    th = target.get("targetHigh", "N/A") if target else "N/A"

    beats = sum(1 for s in surprises
                if isinstance(s.get("actualEarningResult"), (int, float))
                and isinstance(s.get("estimatedEarning"), (int, float))
                and s["actualEarningResult"] >= s["estimatedEarning"])
    n = len(surprises)
    earnings_line = f"{beats}/{n} beat" if n > 0 else "N/A"

    lines = [
        f"<b>{sym} — {sector}</b>",
        f"Score: {score} | ${price} | Target: ${tc}",
        f"SL: ${sl} | TP: ${tp} | Earnings: {earnings_line}",
    ]

    if brief:
        lines.append("")
        lines.append(brief.strip())

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def send_telegram(text: str, token: str, chat_id: str) -> bool:
    """Send message via Telegram Bot API."""
    import requests

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if not r.ok:
            print(f"  [WARN] Telegram send failed: {r.status_code} — {r.text[:200]}")
        return r.ok
    except Exception as e:
        print(f"  [ERROR] Telegram error: {e}")
        return False


def send_telegram_chunked(blocks: list[str], header: str,
                          footer: str, token: str, chat_id: str) -> int:
    """Send blocks in chunks respecting Telegram's 4096 char limit."""
    messages = []
    current = header + "\n"

    for block in blocks:
        candidate = current + "\n" + block
        if len(candidate) + len(footer) + 2 > TELEGRAM_CHAR_LIMIT:
            # Flush current
            messages.append(current)
            current = block
        else:
            current = candidate

    # Last chunk with footer
    current += "\n\n" + footer
    messages.append(current)

    sent = 0
    for msg in messages:
        if send_telegram(msg, token, chat_id):
            sent += 1
        time.sleep(0.5)
    return sent


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Company Intelligence — AI ticker briefs")
    parser.add_argument("--file", help="Specific execution plan CSV path")
    parser.add_argument("--telegram", action="store_true", help="Also send to Telegram")
    args = parser.parse_args()

    # Find CSV
    if args.file:
        csv_path = Path(args.file)
    else:
        csv_path = find_latest_csv()

    if not csv_path or not csv_path.exists():
        print("[ERROR] No execution plan CSV found in output/")
        sys.exit(1)

    print(f"Reading: {csv_path.name}")

    # Load tickers
    tickers = load_tickers(csv_path)
    if not tickers:
        print("[ERROR] No tickers in CSV")
        sys.exit(1)

    # API keys
    fmp_key = _env("IFDS_FMP_API_KEY")
    if not fmp_key:
        print("[ERROR] IFDS_FMP_API_KEY not set")
        sys.exit(1)

    # Run date from filename
    run_date = csv_path.stem.replace("execution_plan_run_", "")[:8]
    run_date_fmt = f"{run_date[:4]}-{run_date[4:6]}-{run_date[6:8]}"

    t_start = time.monotonic()
    fmp_calls = 0
    anthropic_calls = 0

    cli_blocks = []
    tg_blocks = []

    print(f"\nCompany Intelligence — {run_date_fmt} ({len(tickers)} tickers)\n")

    for t in tickers:
        sym = t["symbol"]
        print(f"  Processing {sym}...", end=" ", flush=True)

        # FMP data
        target = fetch_price_target(sym, fmp_key)
        fmp_calls += 1

        surprises = fetch_earnings_surprises(sym, fmp_key)
        fmp_calls += 1

        transcript = fetch_transcript(sym, fmp_key)
        fmp_calls += 2  # dates + transcript

        # Anthropic brief
        brief = generate_brief(
            sym, t["sector"], t["score"], t["price"],
            t["stop_loss"], t["take_profit"],
            target, surprises, transcript,
        )
        if brief:
            anthropic_calls += 1

        print("OK" if brief else "partial")

        cli_blocks.append(format_cli_ticker(t, target, surprises, brief))
        tg_blocks.append(format_telegram_ticker(t, target, surprises, brief))

    elapsed = time.monotonic() - t_start

    # CLI output
    header = f"COMPANY INTELLIGENCE — {run_date_fmt}"
    print(f"\n{header}")
    for block in cli_blocks:
        print(block)

    footer = f"Generálva: {elapsed:.1f}s | Anthropic API: {anthropic_calls} hívás | FMP API: {fmp_calls} hívás"
    print(f"\n{footer}")

    # Telegram output
    if args.telegram:
        tg_token = _env("IFDS_TELEGRAM_BOT_TOKEN")
        tg_chat = _env("IFDS_TELEGRAM_CHAT_ID")
        if not tg_token or not tg_chat:
            print("\n[WARN] Telegram env vars not set, skipping")
        else:
            tg_header = f"<b>COMPANY INTELLIGENCE — {run_date_fmt}</b>"
            tg_footer = f"<i>{footer}</i>"
            sent = send_telegram_chunked(tg_blocks, tg_header, tg_footer,
                                         tg_token, tg_chat)
            print(f"\nTelegram: {sent} üzenet elküldve")


if __name__ == "__main__":
    main()
