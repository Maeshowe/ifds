# CC Prompt: 2026-02-15 — Company Intel V2: Enhanced Data + English Prompt

## Context
Read: `docs/journal/2026-02-15-cc-prompt-company-intel.md` (original prompt)
The `scripts/company_intel.py` already works. This is an enhancement — more FMP data sources, better transcript handling, English prompt.

## Task: Enhance `scripts/company_intel.py`

### 1. Add 4 new FMP data fetchers

Add these functions to the script. All use `/stable/` endpoints.

**a) Company Profile**
```python
def fetch_profile(symbol: str, api_key: str) -> dict | None:
    """Fetch company profile — name, description, industry, beta, dividend."""
    data = _fmp_get("/stable/profile", {"symbol": symbol}, api_key)
    if data:
        d = data[0]
        return {
            "companyName": d.get("companyName"),
            "description": d.get("description", "")[:500],  # cap at 500 chars
            "industry": d.get("industry"),
            "beta": d.get("beta"),
            "lastDividend": d.get("lastDividend"),
            "marketCap": d.get("marketCap"),
            "range52w": d.get("range"),
        }
    return None
```

**b) Analyst Grades Consensus**
```python
def fetch_grades_consensus(symbol: str, api_key: str) -> dict | None:
    """Fetch analyst consensus — buy/hold/sell counts."""
    data = _fmp_get("/stable/grades-consensus", {"symbol": symbol}, api_key)
    if data:
        return data[0]
    return None
```

**c) Recent Analyst Grades (last 5)**
```python
def fetch_recent_grades(symbol: str, api_key: str) -> list:
    """Fetch last 5 analyst grade changes — upgrades/downgrades."""
    data = _fmp_get("/stable/grades", {"symbol": symbol, "limit": 5}, api_key)
    if not data:
        return []
    return [
        {
            "date": g.get("date"),
            "company": g.get("gradingCompany"),
            "action": g.get("action"),
            "newGrade": g.get("newGrade"),
            "previousGrade": g.get("previousGrade"),
        }
        for g in data[:5]
    ]
```

**d) Recent News (last 5)**
```python
def fetch_news(symbol: str, api_key: str) -> list:
    """Fetch last 5 news headlines."""
    data = _fmp_get("/stable/news/stock", {"symbols": symbol, "limit": 5}, api_key)
    if not data:
        return []
    return [
        {
            "date": n.get("publishedDate", "")[:10],
            "title": n.get("title"),
            "publisher": n.get("publisher"),
        }
        for n in data[:5]
    ]
```

NOTE: The news endpoint uses `symbols` (plural) not `symbol`, and the path is `/stable/news/stock`.

### 2. Fix transcript handling — first 1500 + last 1500 chars

In `fetch_transcript`, change the content truncation:

**OLD:**
```python
return content[:TRANSCRIPT_MAX_CHARS] if content else None
```

**NEW:**
```python
if not content:
    return None
if len(content) <= TRANSCRIPT_MAX_CHARS:
    return content
half = TRANSCRIPT_MAX_CHARS // 2
return content[:half] + "\n\n[...MIDDLE SECTION OMITTED...]\n\n" + content[-half:]
```

This ensures the Sonnet sees both the CEO opening remarks AND the analyst Q&A section at the end.

### 3. Rewrite the prompt — English, richer context, stronger anti-hallucination

Replace the ENTIRE prompt in `generate_brief()` with this. The function signature must be updated too:

```python
def generate_brief(symbol: str, sector: str, score: float, price: float,
                   stop_loss: float, take_profit: float,
                   target: dict | None, surprises: list,
                   transcript: str | None,
                   profile: dict | None, grades_consensus: dict | None,
                   recent_grades: list, news: list) -> str | None:
```

New prompt:

```python
    # --- Build data sections ---
    # Profile
    if profile:
        profile_section = f"""Company: {profile.get('companyName', symbol)}
Industry: {profile.get('industry', 'N/A')}
Description: {profile.get('description', 'N/A')}
Beta: {profile.get('beta', 'N/A')} | Last Dividend: ${profile.get('lastDividend', 'N/A')}
Market Cap: ${profile.get('marketCap', 'N/A'):,.0f} | 52W Range: {profile.get('range52w', 'N/A')}"""
    else:
        profile_section = f"Company: {symbol} — {sector}\nNo profile data available."

    # Earnings
    if surprises:
        lines = []
        for s in surprises:
            actual = s.get("actualEarningResult", "N/A")
            est = s.get("estimatedEarning", "N/A")
            dt = s.get("date", "?")
            pct = s.get("surprisePct")
            if isinstance(actual, (int, float)) and isinstance(est, (int, float)):
                beat = "BEAT" if actual >= est else "MISS"
            else:
                beat = "N/A"
            pct_str = f" ({pct:+.1f}%)" if pct is not None else ""
            lines.append(f"  {dt}: Actual={actual}, Est={est} → {beat}{pct_str}")
        earnings_text = "\n".join(lines)
    else:
        earnings_text = "  No earnings data available."

    # Price target
    tc = target.get("targetConsensus", "N/A") if target else "N/A"
    tl = target.get("targetLow", "N/A") if target else "N/A"
    th = target.get("targetHigh", "N/A") if target else "N/A"

    # Analyst consensus
    if grades_consensus:
        gc = grades_consensus
        consensus_section = f"Analyst Consensus: {gc.get('consensus', 'N/A')} — Strong Buy: {gc.get('strongBuy', 0)}, Buy: {gc.get('buy', 0)}, Hold: {gc.get('hold', 0)}, Sell: {gc.get('sell', 0)}, Strong Sell: {gc.get('strongSell', 0)}"
    else:
        consensus_section = "Analyst Consensus: No data available."

    # Recent grades
    if recent_grades:
        grade_lines = []
        for g in recent_grades:
            grade_lines.append(f"  {g['date']}: {g['company']} — {g['action'].upper()} → {g['newGrade']} (was: {g['previousGrade']})")
        grades_text = "\n".join(grade_lines)
    else:
        grades_text = "  No recent analyst actions."

    # News
    if news:
        news_lines = []
        for n in news:
            news_lines.append(f"  {n['date']}: [{n['publisher']}] {n['title']}")
        news_text = "\n".join(news_lines)
    else:
        news_text = "  No recent news."

    # Transcript
    transcript_section = f"\nLatest Earnings Transcript (excerpt):\n{transcript}" if transcript else "\nNo earnings transcript available."

    prompt = f"""You are a stock analyst. Generate a concise intelligence brief based ONLY on the data provided below.

CRITICAL RULES:
- Use ONLY the data provided below. Do NOT use your own knowledge about this company.
- If information is not available in the data below, state: "No data available."
- Do NOT invent dates, numbers, events, or forecasts. Only report what you see in the data.
- Treat the earnings transcript as factual. Flag if the excerpt is insufficient.

=== DATA SOURCES ===

{profile_section}

IFDS Score: {score} | Price: ${price} | Stop Loss: ${stop_loss} | Take Profit: ${take_profit}
Analyst Price Target: ${tc} (Low: ${tl}, High: ${th})

{consensus_section}

Recent Analyst Actions (last 5):
{grades_text}

Earnings History (last 4 quarters):
{earnings_text}

Recent News (last 5 headlines):
{news_text}
{transcript_section}

=== OUTPUT FORMAT ===
Respond in EXACTLY this format (max 200 words total):

DRIVER: [What is driving the business now? Based on transcript and earnings data only. 1-2 sentences.]
RISK: [Biggest risk in the next 30 days? Earnings miss trend, price vs target gap, analyst downgrades, etc. 1-2 sentences.]
CONTRADICTION: [Does anything in the data contradict the high IFDS score ({score})? E.g. serial earnings misses + high score, price above analyst target, analyst downgrades. If none: "No contradiction identified." 1 sentence.]
CATALYST: [Upcoming events from the data: earnings dates, acquisitions, analyst actions, news. List only what appears in the data above.]"""
```

### 4. Update the main loop

In `main()`, update the per-ticker processing:

```python
    for t in tickers:
        sym = t["symbol"]
        print(f"  Processing {sym}...", end=" ", flush=True)

        # FMP data
        profile = fetch_profile(sym, fmp_key)
        fmp_calls += 1

        target = fetch_price_target(sym, fmp_key)
        fmp_calls += 1

        surprises = fetch_earnings_surprises(sym, fmp_key)
        fmp_calls += 1

        grades_consensus = fetch_grades_consensus(sym, fmp_key)
        fmp_calls += 1

        recent_grades = fetch_recent_grades(sym, fmp_key)
        fmp_calls += 1

        news = fetch_news(sym, fmp_key)
        fmp_calls += 1

        transcript = fetch_transcript(sym, fmp_key)
        fmp_calls += 2  # dates + transcript

        # Anthropic brief
        brief = generate_brief(
            sym, t["sector"], t["score"], t["price"],
            t["stop_loss"], t["take_profit"],
            target, surprises, transcript,
            profile, grades_consensus, recent_grades, news,
        )
        if brief:
            anthropic_calls += 1

        print("OK" if brief else "partial")

        cli_blocks.append(format_cli_ticker(t, target, surprises, brief))
        tg_blocks.append(format_telegram_ticker(t, target, surprises, brief))
```

### 5. Update CLI and Telegram output headers

The CLI header for each ticker should show the company name if available:

In `format_cli_ticker`, add profile as parameter and show company name:
```python
def format_cli_ticker(t: dict, target: dict | None, surprises: list,
                      brief: str | None, profile: dict | None = None) -> str:
    sym = t["symbol"]
    name = profile.get("companyName", sym) if profile else sym
    # ... use name in the header line
```

Similarly for `format_telegram_ticker`.

And pass `profile` in the main loop:
```python
cli_blocks.append(format_cli_ticker(t, target, surprises, brief, profile))
tg_blocks.append(format_telegram_ticker(t, target, surprises, brief, profile))
```

### 6. Max tokens bump

Change `max_tokens=500` to `max_tokens=600` since we added more output sections and raised the word limit to 200.

### Summary of changes
- 4 new FMP fetchers: profile, grades-consensus, grades (recent 5), news/stock
- Transcript: first 1500 + last 1500 chars (instead of first 3000)
- English prompt with richer context and stronger anti-hallucination rules
- Updated function signatures and main loop
- FMP calls per ticker: 4 → 8 (still well within rate limits for 8 tickers = 64 calls)

### Testing
1. Run: `python scripts/company_intel.py`
2. Verify: briefs are in English, include analyst grades and news references
3. Run: `python scripts/company_intel.py --telegram`
4. Verify: Telegram delivery works with new format

### Commit
```
feat: company intel v2 — richer data, English prompt, anti-hallucination

- Add FMP endpoints: profile, grades-consensus, grades, news/stock
- Transcript: first+last 1500 chars (captures analyst Q&A)
- English prompt with 10 data sources, strict anti-hallucination rules
- Max 200 words output, 600 max tokens
- FMP calls: 4→8 per ticker (64 total for 8 tickers)
```
