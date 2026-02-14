# IFDS API Stack — 2026-02-12

## Összesítés

| Szolgáltató | Tier | Havi ár | Rate limit |
|---|---|---|---|
| Polygon/Massive Stocks | **Advanced** | $199 | Unlimited, real-time |
| Polygon/Massive Options | **Developer** | $79 | Unlimited, 15min delayed |
| Polygon/Massive Indices | **Starter** | $49 | Unlimited, 15min delayed |
| FMP | **Ultimate** | $139 | 3000 req/min (50/s), 150GB/30d |
| Unusual Whales | **Basic** | $150 | ? |
| FRED | **Free** | $0 | Nincs limit |
| **Összesen** | | **$616/hó** | |

## Polygon/Massive — Stocks Advanced ($199/hó)

**Előfizetés dátuma:** 2026-02-12 (upgrade Developer → Advanced)

**Elérhető:**
- All US Stocks Tickers
- Unlimited API Calls
- **20+ Years Historical Data**
- **Real-time Data**
- Unlimited File Downloads
- Reference Data, Corporate Actions
- Technical Indicators
- Minute, Second Aggregates
- WebSockets, Snapshot
- **Trades** (egyedi kötések — dark pool TRF szűréshez)
- **Quotes** (bid/ask real-time)
- **Financials & Ratios** (income statement, balance sheet, ratios — FMP-vel átfedő!)

**Használat az IFDS-ben:**
- Phase 1: Grouped daily bars (BMI) — `GET /v2/aggs/grouped/locale/us/market/stocks/{date}`
- Phase 3: Sector ETF bars — `GET /v2/aggs/ticker/{ETF}/range/1/day/...`
- Phase 4: Individual stock bars (SMA200, ATR, RSI, RVOL) — `GET /v2/aggs/ticker/{ticker}/range/1/day/...`
- SIM-L1: Validation bars
- **TERVEZETT (Q2 BC19):** Dark pool enrichment — `GET /v3/trades/{ticker}` + TRF exchange filter
- **TERVEZETT (Q3 BC24):** Real-time WebSocket IBKR auto-execution

**Kihasználatlan de elérhető:**
- Financials & Ratios → Phase 4 FMP dependency csökkentés (Q2 evaluáció)
- Real-time data → BC24 IBKR auto-execution
- 20Y history → SimEngine Level 3 backtest
- Quotes → intraday spread monitoring (nem tervezett)

## Polygon/Massive — Options Developer ($79/hó)

**Előfizetés dátuma:** 2026-02-12 (upgrade Starter → Developer)

**Elérhető:**
- All US Options Tickers
- Unlimited API Calls
- **4 Years Historical Data** (was 2Y)
- 15-minute Delayed Data
- Greeks, IV, & Open Interest
- Minute, Second Aggregates
- WebSockets, Snapshot
- **Trades** (egyedi opciós kötések)

**Használat az IFDS-ben:**
- Phase 5: Options snapshot (GEX számítás) — `GET /v3/snapshot/options/{ticker}`
- Phase 5: OBSIDIAN feature store (IV, OI, Greeks)
- **TERVEZETT (Q2):** Options trades → saját block/sweep detector (UW dependency csökkentés)
- **TERVEZETT (Q2):** 4Y historikus options data → SimEngine Level 3

**Kihasználatlan:**
- Options Trades endpoint → flow scoring saját implementáció (Q2 evaluáció)
- 4Y history → backtest depth

## Polygon/Massive — Indices Starter ($49/hó)

**Használat:** Phase 0 VIX fallback, Phase 3 sector ETF referencia
**Megjegyzés:** A VIX elsődlegesen FRED-ből jön (ingyenes). A Polygon indices a fallback.

## FMP Ultimate ($139/hó)

**Rate limit:** 3000 req/min (50 req/s)
**Bandwidth:** 150GB / 30 nap rolling

**Használat az IFDS-ben:**
- Phase 2: Stock screener — `GET /stable/stock-screener`
- Phase 2: Earnings calendar — `GET /stable/earning-calendar`
- Phase 4: Income statement — `GET /stable/income-statement/{ticker}`
- Phase 4: Balance sheet — `GET /stable/balance-sheet/{ticker}`
- Phase 4: Ratios TTM — `GET /stable/ratios-ttm/{ticker}`
- Phase 4: Institutional holders — `GET /stable/institutional-holder/{ticker}`
- Phase 4: Insider trading — `GET /stable/insider-trading/{ticker}`
- **BC17:** Shares float (short interest) — `GET /stable/shares-float/{ticker}`

**Kihasználatlan de elérhető (Ultimate tier):**
- **Bulk endpoints** → Phase 4 optimalizálás: ~3000 hívás → ~5 hívás (PERF-1, Q2)
- **Analyst estimates** → Score-Implied μ, Black-Litterman views (Q3 BC23)
- **Sector P/E ratios** → relatív value faktor (Q3)
- **Earnings transcripts** → NLP sentiment (Q4 opcionális)
- **WebSocket** — nem használt, nem tervezett

**FONTOS:** A 429-es hibák NEM a tier limit miatt jöttek — dev testing burst (3× futtatás cache nélkül). Production (napi 1 futtatás) biztonságos.

## Unusual Whales Basic ($150/hó)

**Használat az IFDS-ben:**
- Phase 4: Dark pool % — `GET /api/darkpool/ticker/{ticker}`
- Phase 4: Options flow (block trades, sweeps, buy pressure)
- Phase 5: GEX fallback (ritkán aktiválódik)

**Nem pótolható más API-ból:**
- Aggregált options flow kategorizálás (block vs sweep vs retail)
- Buy pressure / sell pressure arány
- Előre számolt dark pool %

**Review tervezett:** Q2 — ha a Polygon Options Trades-ből épített saját flow detector
hasonló eredményt ad, az UW Basic ($150/hó) potenciálisan kiváltható.

## FRED (Free)

- Phase 0: VIX — `GET /series/observations?series_id=VIXCLS`
- Phase 0: TNX — `GET /series/observations?series_id=DGS10`
- Stabil, nincs limit, nincs tervezett változás

## Upgrade Path

```
2026 Q1 (most):  ✅ Stocks Advanced + Options Developer (megtörtént)
2026 Q2:         FMP Bulk API átállás (PERF-1) — kód változás, nem tier
2026 Q2:         UW dependency review — saját flow detector evaluáció
2026 Q3:         Options Advanced ($79→$199) — ha real-time GEX kell (opcionális)
2026 Q3:         FMP analyst estimates használatba vétel (BC23)
```

## Éves API költség becslés

```
Jelenlegi: $616/hó × 12 = $7,392/év
Ha Options Advanced (Q3): +$120/hó × 6 = +$720 → $8,112/év
Ha UW kiváltható (Q2): -$150/hó × 8 = -$1,200 → $6,912/év
```
