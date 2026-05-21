# CC Prompt: 2026-02-15 — Company Intelligence Script

## Kontextus
Olvasd el: `docs/journal/2026-02-13-session-moneyflows-analysis.md`
Ez egy post-pipeline intelligence script — a napi futás 8 tickerére earnings transcript + analyst data + AI összefoglalást generál.

## Feladat: `scripts/company_intel.py` — Önálló script

### Leírás
A script beolvassa a legfrissebb execution plan CSV-t az `output/` mappából, és minden tickerre:
1. FMP-ből lehúz: earnings transcript, price target consensus, earnings surprises
2. Anthropic Sonnet API-val generál egy tömör magyar nyelvű intelligence brief-et
3. CLI-re kiírja szépen formázva
4. `--telegram` flag-gel Telegram-ra is elküldi

### Input
A legfrissebb `output/execution_plan_run_*.csv` fájl. Oszlopok:
```
instrument_id,direction,order_type,limit_price,quantity,stop_loss,take_profit_1,take_profit_2,risk_usd,score,gex_regime,sector,multiplier_total,mult_vix,mult_utility,sector_bmi,sector_regime,is_mean_reversion
```
Releváns oszlopok: `instrument_id` (ticker), `limit_price` (price), `score`, `sector`, `stop_loss`, `take_profit_1`

### FMP API hívások (stable endpoints!)

**FONTOS: A FMP /api/v3/ endpointok kivezetésre kerültek. Kizárólag /stable/ endpointokat használj!**

FMP base URL: `https://financialmodelingprep.com`
Auth: `?apikey={FMP_API_KEY}` query parameter

1. **Transcript dates** — legutóbbi quarter meghatározás
   ```
   GET /stable/earning-call-transcript-dates?symbol={SYMBOL}&apikey={KEY}
   ```
   Response: `[{"quarter": 4, "fiscalYear": 2025, "date": "2025-10-30"}, ...]`
   → Vedd az elsőt (legfrissebb) → year + quarter

2. **Earnings transcript** — a legutóbbi transcript teljes szövege
   ```
   GET /stable/earning-call-transcript?symbol={SYMBOL}&year={YEAR}&quarter={QUARTER}&apikey={KEY}
   ```
   Response: `[{"symbol": "WEC", "quarter": 4, "year": 2025, "date": "...", "content": "Operator: Good afternoon..."}]`
   → `content` mező — **max első 3000 karakter** (Sonnet token limit kezelés)

3. **Price target consensus** — analyst árcél
   ```
   GET /stable/price-target-consensus?symbol={SYMBOL}&apikey={KEY}
   ```
   Response: `[{"symbol": "WEC", "targetHigh": 120, "targetLow": 85, "targetConsensus": 105.5, "targetMedian": 108}]`

4. **Earnings surprises** — beat/miss history
   ```
   GET /stable/earnings-surprises?symbol={SYMBOL}&apikey={KEY}
   ```
   Response: list of `{"date": "...", "actualEarningResult": 1.5, "estimatedEarning": 1.4, ...}`
   → Utolsó 4 quarter-t mutasd

### Anthropic API hívás

Model: `claude-sonnet-4-5-20250929`
API Key: `ANTHROPIC_API_KEY` env var (a .env-ből töltődik)

```python
import anthropic

client = anthropic.Anthropic()  # automatikusan olvassa az ANTHROPIC_API_KEY env var-t

message = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=500,
    messages=[
        {"role": "user", "content": prompt}
    ]
)
brief = message.content[0].text
```

**Prompt tickerenként:**
```python
prompt = f"""Te egy részvényelemző vagy. Az alábbi adatok alapján készíts tömör intelligence brief-et MAGYARUL.

Ticker: {symbol} — {sector}
IFDS Combined Score: {score}
Jelenlegi ár: ${price} | Stop Loss: ${stop_loss} | Take Profit: ${take_profit}
Analyst Consensus Target: ${target_consensus} (Low: ${target_low}, High: ${target_high})

Earnings Beat/Miss (utolsó 4Q):
{earnings_surprises_text}

Legutóbbi earnings transcript (kivonat, max 3000 karakter):
{transcript_excerpt}

Válaszolj PONTOSAN ebben a formátumban (max 150 szó összesen):

DRIVER: [Mi hajtja most az üzletet? 1-2 mondat]
KOCKÁZAT: [Mi a legnagyobb kockázat a következő 30 napban? 1-2 mondat]
ELLENTMONDÁS: [Van-e bármi ami ellentmond az IFDS scoring-nak? Ha nincs, írd: "Nincs azonosított ellentmondás." 1 mondat]
CATALYST: [Következő események: earnings dátum, product launch, regulatory, stb. Felsorolás.]
"""
```

### CLI Output formátum

```
📋 COMPANY INTELLIGENCE — 2026-02-14

━━━ WEC Energy Group (WEC) — Utilities ━━━
  Score: 92.5 | Price: $115.79 | Target: $105.50 (Low: $85, High: $120)
  Stop: $112.26 | TP: $120.49 | Risk: $334
  Earnings: 4/4 beat (last 4Q)
  
  DRIVER: Regulated utility, stable cash flow...
  KOCKÁZAT: Rising rates compress utility P/E...
  ELLENTMONDÁS: Analyst target below current price — possible overvaluation signal
  CATALYST: Q1 earnings Apr 28, rate case decision expected May

━━━ Century Aluminum (CENX) — Materials ━━━
  Score: 91.0 | Price: $46.04 | Target: $52.00 (Low: $38, High: $65)
  ...

⏱ Generálva: 45.2s | Anthropic API: 8 hívás | FMP API: 32 hívás
```

### Telegram Output

Ugyanez HTML formátumban. A Telegram 4096 karakter limites — ha a teljes brief túl hosszú, 2 üzenetre bontsd (4 ticker / üzenet).

```python
def send_telegram(text: str, token: str, chat_id: str):
    import requests
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    r = requests.post(url, json=payload, timeout=10)
    return r.ok
```

Telegram env vars: `IFDS_TELEGRAM_BOT_TOKEN`, `IFDS_TELEGRAM_CHAT_ID` (a .env-ben megvannak, chat_id: `-1003660205525`)

### Használat

```bash
# Csak CLI output
python scripts/company_intel.py

# CLI + Telegram
python scripts/company_intel.py --telegram

# Specifikus execution plan fájl
python scripts/company_intel.py --file output/execution_plan_run_20260212_124947_039452.csv

# Help
python scripts/company_intel.py --help
```

### Error handling
- Ha egy ticker FMP hívása sikertelen → skip, logolj warning, folytasd a többivel
- Ha az Anthropic API hívás sikertelen → skip, nyomtasd ki amit az FMP adott (target, earnings)
- Ha nincs transcript (kicsi cég) → a prompt-ból hagyd ki a transcript részt, a többi adatot még használd
- Ha nincs execution plan CSV → hiba üzenet, exit 1
- `.env` fájl betöltés: használd a `python-dotenv` package-et (`from dotenv import load_dotenv`)

### Dependencies
- `anthropic` — pip install anthropic (ha nincs)
- `python-dotenv` — pip install python-dotenv (ha nincs)
- `requests` — már megvan

Ellenőrizd: `pip list | grep -i anthropic` és `pip list | grep -i dotenv`
Ha hiányzik: `pip install anthropic python-dotenv --break-system-packages`

### Tesztelés
1. Futtasd a legutóbbi execution plan-ra: `python scripts/company_intel.py`
2. Ellenőrizd hogy minden tickerre generálódik brief
3. Futtasd `--telegram` flag-gel: `python scripts/company_intel.py --telegram`
4. Ellenőrizd a Telegram channel-en hogy megérkezett

### Fájlok amiket módosítanod / létrehoznod kell
- `scripts/company_intel.py` — **ÚJ** (fő script, ~200-250 sor)
- NE módosítsd a pipeline kódot (`src/ifds/`) — ez egy önálló post-pipeline script

### Journal frissítés
Add hozzá a `docs/journal/2026-02-13-session-moneyflows-analysis.md`-hez:

T11 sor a táblázatba:
| T11 | Company Intelligence Phase 7 | Anthropic use-case | Standalone script (ma), Pipeline integration BC20-21 | Azonnali |

### Commit
```
feat: company intelligence script — AI-powered ticker briefs

- scripts/company_intel.py: post-pipeline intelligence brief generator
- FMP stable endpoints: transcript, price target, earnings surprises
- Anthropic Sonnet 4.5 API: magyar nyelvű ticker analysis
- CLI output + optional Telegram delivery (--telegram flag)
- Roadmap: T11 Company Intelligence Phase 7 (BC20-21 full integration)
```
