# IFDS API Map — Adatfolyam Dokumentáció

> Generálva a `src/ifds/` forráskódból.
> Frissitve: 2026-02-10 (BC12 utan, 563 teszt)
> Ez a dokumentum a **ténylegesen implementált** API hívásokat, adatfolyamokat és fallback logikát írja le.

---

## 1. Adatfolyam Térkép (Phase → API → Endpoint)

### Phase 0 — System Diagnostics

| Provider | Endpoint | Paraméterek | Visszaadott adat | Kritikus? |
|----------|----------|-------------|-------------------|-----------|
| Polygon | `GET /v2/aggs/grouped/locale/us/market/stocks/{date}` | `adjusted=true` | Health check (van-e adat?) | IGEN |
| Polygon | `GET /v3/snapshot/options/SPY` | `limit=250` | Options chain health check | IGEN |
| Polygon | `GET /v2/aggs/ticker/I:VIX/range/1/day/{from}/{to}` | `adjusted=true, sort=asc` | VIX érték — elsődleges forrás (real-time) | IGEN |
| FMP | `GET /stable/company-screener` | `marketCapMoreThan=1e12, limit=1` | Screener health check | IGEN |
| FRED | `GET /fred/series/observations` | `series_id=VIXCLS, limit=5, sort_order=desc` | VIX érték — fallback (1 nap késés) | IGEN |
| FRED | `GET /fred/series/observations` | `series_id=DGS10, limit=25, sort_order=desc` | TNX értékek (list[float]) | IGEN |
| UW | `GET /api/darkpool/SPY` | — | Dark pool health check | **NEM** |

**Phase 0 kimenet**: `DiagnosticsResult` — VIX regime, VIX multiplier, VIX source, TNX SMA20, UW elérhetőség.

**BC11**: VIX sanity check — [5.0, 100.0] tartomány validálás, kívül → WARNING + default 20.0.
**BC12**: VIX EXTREME — VIX > 50 → EXTREME regime, multiplier 0.10.

---

### Phase 1 — Market Regime (BMI)

| Provider | Endpoint | Paraméterek | Visszaadott adat |
|----------|----------|-------------|-------------------|
| Polygon | `GET /v2/aggs/grouped/locale/us/market/stocks/{date}` | `adjusted=true` | Napi összes ticker: `{T, o, h, l, c, v}` |

- **Lookback**: 75 naptári nap (~50 kereskedési nap, volume warmup=20 + SMA25 ablak)
- **Hívások száma**: 75 db (naponta 1 grouped request)
- **Per-sector BMI** (BC8): FMP sector mapping → per-sector buy/sell counts → SMA25 per sector
- **Kimenet**: `Phase1Result` → `StrategyMode.LONG` vagy `SHORT`, BMI érték (0–100), sector_bmi_values

---

### Phase 2 — Universe Building

| Provider | Endpoint | Paraméterek | Visszaadott adat |
|----------|----------|-------------|-------------------|
| FMP | `GET /stable/company-screener` | LONG: `marketCapMoreThan=2e9, priceMoreThan=5, volumeMoreThan=500000, isEtf=false, limit=10000` | `[{symbol, sector, marketCap, price, volume}]` |
| FMP | `GET /stable/company-screener` | SHORT: `marketCapMoreThan=5e8, volumeMoreThan=500000` + D/E > 3.0 szűrő | Zombie ticker lista |
| FMP | `GET /stable/earnings-calendar` | `from=today, to=today+5d` | `[{symbol, date}]` — kizárásra (binary event) |

- **Hívások száma**: 1–2 screener + 1 earnings calendar
- **Kimenet**: `Phase2Result` → szűrt `list[Ticker]` (~1400 LONG / ~200 SHORT)

---

### Phase 3 — Sector Rotation & Momentum

| Provider | Endpoint | Paraméterek | Visszaadott adat |
|----------|----------|-------------|-------------------|
| Polygon | `GET /v2/aggs/ticker/{ETF}/range/1/day/{from}/{to}` | `adjusted=true, sort=asc` | OHLCV bárok az elmúlt 25 napra |

- **ETF-ek**: XLK, XLF, XLE, XLV, XLI, XLP, XLY, XLB, XLC, XLRE, XLU (11 db)
- **Hívások száma**: 11 (ETF-enként 1)
- **BC8**: Per-sector BMI values → sector_bmi_regime populálás
- **Kimenet**: `Phase3Result` → `list[SectorScore]` ranggal, momentum-mal, vétóval

---

### Phase 4 — Individual Stock Analysis

| Provider | Endpoint | Paraméterek | Visszaadott adat | BC |
|----------|----------|-------------|-------------------|----|
| Polygon | `GET /v2/aggs/ticker/{symbol}/range/1/day/{365d_ago}/{today}` | `adjusted=true, sort=asc` | 200+ nap OHLCV (SMA200, SMA50, RSI14, ATR14) | BC3 |
| Polygon | `GET /v3/snapshot/options/{symbol}` | `limit=250` | Options chain (PCR, OTM, DTE filtered) | BC9 |
| FMP | `GET /stable/financial-growth` | `symbol={ticker}, limit=1` | `{revenueGrowth, epsgrowth}` | BC3 |
| FMP | `GET /stable/key-metrics` | `symbol={ticker}` | `{roeTTM, debtToEquityTTM, interestCoverageTTM, netIncomePerShareTTM}` | BC3 |
| FMP | `GET /stable/insider-trading/search` | `symbol={ticker}, limit=50` | `[{transactionDate, acquistionOrDisposition}]` | BC3 |
| FMP | `GET /stable/institutional-ownership/latest` | `symbol={ticker}, limit=2` | `[{totalInvested, date}]` — QoQ ownership trend | BC12 |
| UW | `GET /api/darkpool/recent` | `limit=100, older_than=cursor` | Batch dark pool records (15 pages) | BC6 |

- **Hívások száma per ticker**: 1 Polygon OHLCV + 1 Polygon options + 3-4 FMP + 0-1 UW = **5-7 hívás**
- **Összes hívás** (~1400 ticker): ~7000 API call (szinkron) / ~2 perc (async)
- **BC9**: Options flow scoring — PCR, OTM ratio, block trade count
- **BC10**: dp_pct (Polygon volume), buy pressure, VWAP scoring
- **BC12**: DTE filter (≤90 DTE) a PCR/OTM scoring előtt; institutional ownership QoQ trend
- **BC12**: Institutional ownership — AAPL probe az elején, ha 404 → skip all (graceful degradation)
- **BC11**: Per-provider circuit breaker — polygon, fmp, uw, fred CB instances
- **Kimenet**: `Phase4Result` → `list[StockAnalysis]` combined score-ral

---

### Phase 5 — GEX Analysis (Gamma Exposure)

| Provider | Endpoint | Paraméterek | Visszaadott adat | Szerep |
|----------|----------|-------------|-------------------|--------|
| UW | `GET /api/stock/{symbol}/greek-exposure/strike` | — | Per-strike dollar GEX: `[{strike, call_gamma, put_gamma}]` (stringek!) | **Elsődleges** |
| Polygon | `GET /v3/snapshot/options/{symbol}` | `limit=250` | Per-kontraktus: `{strike_price, gamma, open_interest, underlying_asset}` | **Fallback** |

- **Feldolgozott tickers**: Top 100 (combined_score desc)
- **Fallback lánc**: UW per-strike (elsődleges) → Polygon options snapshot (fallback)
- **UW adat**: Pre-computed dollar GEX (`call_gamma` pozitív, `put_gamma` negatív) — nem kell nyers gamma × OI × spot² számítás
- **BC12**: DTE filter — Polygon GEX: csak ≤90 DTE opciók, <5 kontraktus fallback (összes használata)
- **BC12**: Call wall ATR filter — `abs(call_wall - price) > 5×ATR` → call_wall = 0.0
- **BC12**: Zero gamma lineáris interpoláció (pontosabb szint meghatározás)
- **Post-BC12 fix**: Polygon put GEX signed convention — kivonás `gex_by_strike`-ból
- **BC12**: Debug logging — első 5 ticker GEX részletei (PHASE_DIAGNOSTIC event)
- **Hívások száma**: 100 (UW-ből, ha elérhető; Polygon fallback ha UW None)
- **Kimenet**: `Phase5Result` → `list[GEXAnalysis]` regime-mel és multiplierrel

---

### Phase 6 — Position Sizing & Output

| Provider | Endpoint | Visszaadott adat |
|----------|----------|-------------------|
| *(nincs API hívás)* | — | Phase 4/5 adatokból számol |

- **Input**: StockAnalysis + GEXAnalysis + MacroRegime + SectorScores
- **BC11**: Signal dedup — SHA256 hash check sizing előtt, record után
- **BC12**: Fat finger protection — NaN guard, max_order_quantity=5000, exposure cap
- **Kimenet**: 3 CSV fájl (execution_plan, full_scan_matrix, trade_plan)

---

## 2. API Provider Összefoglaló

### Polygon.io

| Szempont | Érték |
|----------|-------|
| Base URL | `https://api.polygon.io` |
| Auth | Bearer token (`Authorization: Bearer {key}`) |
| Timeout | 10s (OHLCV), 15s (options) |
| Rate limit | ~5 req/s (free tier) |
| Retry | 3x, lineáris backoff (1s, 2s, 3s) |
| Async semaphore | 5 concurrent |
| Circuit breaker | Per-provider CB (BC11): 50 window, 30% error → OPEN, 60s cooldown |

### Financial Modeling Prep (FMP)

| Szempont | Érték |
|----------|-------|
| Base URL | `https://financialmodelingprep.com` |
| Auth | Query param (`apikey={key}`) |
| Timeout | 10s |
| Rate limit | ~10 req/s |
| Retry | 3x, lineáris backoff |
| Async semaphore | 8 concurrent |
| Circuit breaker | Per-provider CB (BC11): 50 window, 30% error → OPEN, 60s cooldown |
| BC12 endpoint | `/stable/institutional-ownership/latest` — auto-disable ha 404 (AAPL probe) |

### Unusual Whales (UW)

| Szempont | Érték |
|----------|-------|
| Base URL | `https://api.unusualwhales.com` |
| Auth | Bearer token + `User-Agent` header |
| Timeout | 10s |
| Kritikus? | **NEM** — opcionális kiegészítés |
| Retry | 3x, lineáris backoff |
| Async semaphore | 5 concurrent |
| Circuit breaker | Per-provider CB (BC11): 50 window, 30% error → OPEN, 60s cooldown |

### FRED (Federal Reserve Economic Data)

| Szempont | Érték |
|----------|-------|
| Base URL | `https://api.stlouisfed.org` |
| Auth | Query param (`api_key={key}`) |
| Timeout | 10s |
| Használt sorozatok | `VIXCLS` (VIX), `DGS10` (10Y Treasury) |
| Retry | 3x, lineáris backoff |
| Circuit breaker | Per-provider CB (BC11): 50 window, 30% error → OPEN, 60s cooldown |

---

## 3. UW Integráció Státusz

### Hol használjuk az Unusual Whales-t?

| Phase | Funkció | UW Endpoint | Ténylegesen használja? |
|-------|---------|-------------|------------------------|
| Phase 0 | Health check | `/api/darkpool/SPY` | Igen, de nem kritikus |
| Phase 4 | Dark pool signal | `/api/darkpool/recent` (batch, BC6) | **Igen** — RVOL kiegészítés |
| Phase 5 | GEX data | `/api/stock/{symbol}/greek-exposure/strike` | **Igen** — per-strike dollar GEX (elsődleges) |

### Fallback Logika

#### Dark Pool (Phase 4)

```
UWBatchDarkPoolProvider.prefetch()  (BC6)
  ↓ /api/darkpool/recent (15 pages, ~30K records)
  ↓ _aggregate_dp_records() per ticker
  ↓ dp_pct = dp_volume / Polygon_volume * 100  (BC10 fix)

get_dark_pool(symbol)
  ↓ prefetched adat van?
  ├─ IGEN → NBBO midpoint alapján BUY/SELL klasszifikáció
  │         dp_pct, dp_volume, block_trade_count, dark_pool_signal
  └─ NEM → dp_pct = 0.0, signal = None (nincs büntetés)
```

#### GEX (Phase 5)

```
FallbackGEXProvider:
  1. UWGEXProvider.get_gex(symbol)
     → GET /api/stock/{symbol}/greek-exposure/strike
     → Per-strike dollar GEX (call_gamma, put_gamma — stringek)
     → net_gex, call_wall, put_wall, zero_gamma számítás
     → source: "unusual_whales"
  2. PolygonGEXProvider.get_gex(symbol, max_dte=90) [fallback]
     → GET /v3/snapshot/options/{symbol}
     → DTE filter: ≤90 DTE kontraktusok, <5 → fallback all (BC12)
     → GEX = Gamma × OI × 100 × Spot² × 0.01
     → Put GEX: kivonva gex_by_strike-ból (signed convention, post-BC12 fix)
     → Zero gamma: lineáris interpoláció (BC12)
     → source: "polygon_calculated"
```

---

## 4. VIX Forrás

### Honnan jön a VIX adat?

**3 szintű fallback lánc** — a legfrissebb forrástól halad a konzervatív default felé:

1. **Polygon `I:VIX`** (elsődleges) — real-time, intraday VIX
2. **FRED `VIXCLS`** (fallback) — 1 nappal késleltetett záró VIX
3. **Default 20.0** (ultimate fallback) — konzervatív NORMAL regime

### VIX Adatfolyam (teljes útvonal)

```
Phase 0 (phase0_diagnostics.py)
  │
  ├─ [1] polygon.get_index_value("I:VIX")
  │   → GET /v2/aggs/ticker/I:VIX/range/1/day/{from}/{to}
  │   → Siker → vix_value, source="polygon"
  │
  ├─ [2] Ha Polygon None → fred.get_series("VIXCLS", limit=5)
  │   → GET /fred/series/observations?series_id=VIXCLS&sort_order=desc&limit=5
  │   → [{"date": "2026-02-07", "value": "18.50"}, ...]
  │   → _get_latest_fred_value() → float, source="fred"
  │
  ├─ [3] Ha FRED is None → default 20.0, source="default"
  │
  ├─ _validate_vix(value, source, logger)  (BC11)
  │   ├─ [5.0, 100.0] range → OK
  │   └─ Kívül → WARNING + default 20.0
  │
  ├─ _classify_vix(18.50, config) → MarketVolatilityRegime
  │   ├─ > 50    → EXTREME  (BC12)
  │   ├─ > 30    → PANIC
  │   ├─ > 20    → ELEVATED
  │   ├─ > 15    → NORMAL
  │   └─ <= 15   → LOW
  │
  ├─ _calculate_vix_multiplier(18.50, config) → 1.0
  │   ├─ VIX > 50:  0.10 (EXTREME override, BC12)
  │   ├─ VIX <= 20: 1.0 (nincs büntetés)
  │   └─ VIX > 20:  max(0.25, 1.0 - (VIX - 20) × 0.02)
  │       Példák: VIX=25 → 0.90, VIX=30 → 0.80, VIX=50 → 0.40, VIX=55 → 0.10
  │
  └─ MacroRegime(vix_value=18.50, vix_regime=NORMAL, vix_multiplier=1.0, vix_source="polygon")
       │
       └─ Phase 6 → M_vix = macro.vix_multiplier
            → M_total = M_flow × M_insider × M_funda × M_gex × M_vix × M_utility
            → clamp(M_total, 0.25, 2.0)
            → adjusted_risk = base_risk × M_total
```

### TNX (10-Year Treasury) — szintén FRED

```
Phase 0 → fred.get_tnx(limit=25)
  → GET /fred/series/observations?series_id=DGS10&sort_order=desc&limit=25
  → SMA20 számítás az utolsó 20 értékből
  → Ha tnx_value > sma20 × 1.05:
      Phase 3 → Technology -10, Real Estate -10 (sector score penalty)
```

---

## 5. Circuit Breaker Integráció (BC11)

### Per-provider Circuit Breaker Állapotgép

```
CLOSED (normál működés)
  │
  ├─ record_success() → counter++
  ├─ record_failure() → counter++
  │
  ├─ Ha call_count >= 10 ÉS error_rate > 30%:
  │   └─ → OPEN (requests blocked)
  │         │
  │         ├─ allow_request() → False, "[CIRCUIT BREAKER]" log
  │         │
  │         ├─ 60s cooldown letelt?
  │         │   └─ → HALF_OPEN (probe allowed)
  │         │         │
  │         │         ├─ record_success() → CLOSED (reset)
  │         │         └─ record_failure() → OPEN (retry cooldown)
  │
  └─ Ha error_rate <= 30%:
      └─ Marad CLOSED

Runner: 4 CB instance
  ├─ cb_polygon  → Polygon client
  ├─ cb_fmp      → FMP client
  ├─ cb_uw       → UW client
  └─ cb_fred     → FRED client
```

---

## 6. Institutional Ownership Integráció (BC12)

### AAPL Probe + Graceful Degradation

```
Runner (before Phase 4 ticker loop):
  │
  ├─ fmp.get_institutional_ownership("AAPL")
  │   → GET /stable/institutional-ownership/latest?symbol=AAPL&limit=2
  │
  ├─ Result None?
  │   ├─ IGEN → inst_ownership_available = False
  │   │         → Skip all subsequent calls (no penalty)
  │   └─ NEM  → inst_ownership_available = True
  │             → Per-ticker calls proceed
  │
  └─ Per ticker (if available):
      → get_institutional_ownership(ticker)
      → QoQ change = (recent - previous) / previous
      ├─ > +2%  → "increasing", +10 funda
      ├─ < -2%  → "decreasing", -5 funda
      └─ else   → "stable", 0
```

---

## 7. Futtatási Útmutató

### Mikor érdemes futtatni?

| Időpont | Ajánlott? | Indoklás |
|---------|-----------|----------|
| **Pre-market (8:00–9:30 ET)** | **IGEN** — optimális | Polygon grouped daily: előző napi záró árak. FRED: friss VIX. Dark pool: előző napi tranzakciók. |
| Market hours (9:30–16:00 ET) | Lehetséges | Intraday adatok még nem zártak. |
| After hours (16:00+ ET) | Lehetséges | Aznapi adatok elérhetők. |
| **Hétvége** | **NEM** | Polygon grouped daily nem ad adatot hétvégén. |

### Hogyan futtasd?

```bash
# Teljes pipeline (szinkron, ~12 perc)
python -m ifds run

# Teljes pipeline (async, ~2-3 perc)
IFDS_ASYNC_ENABLED=true python -m ifds run

# Cache-vel (API hívás megtakarítás)
IFDS_ASYNC_ENABLED=true IFDS_CACHE_ENABLED=true python -m ifds run
```

### Szükséges környezeti változók (.env)

```bash
IFDS_POLYGON_API_KEY=your_polygon_key     # Kötelező
IFDS_FMP_API_KEY=your_fmp_key             # Kötelező
IFDS_FRED_API_KEY=your_fred_key           # Kötelező
IFDS_UW_API_KEY=your_uw_key              # Opcionális (dark pool + GEX elsődleges forrás)
IFDS_ASYNC_ENABLED=true                   # Opcionális (default: false)
IFDS_CACHE_ENABLED=true                   # Opcionális (default: false)
```

### Kimenet

3 CSV fájl a `output/` mappában:
- `execution_plan_{run_id}.csv` — 18 oszlop, top 8 pozíció
- `full_scan_matrix_{run_id}.csv` — 14 oszlop, összes ticker
- `trade_plan_{run_id}.csv` — 8 oszlop, kereskedési terv

### Pozíció limitek

| Limit | Érték | Forrás |
|-------|-------|--------|
| Max pozíció szám | 8 | `max_positions` |
| Max pozíció/szektor | 3 | `max_positions_per_sector` |
| Max egyedi kockázat | 1.5% equity | `max_single_position_risk_pct` |
| Max bruttó kitettség | $100,000 | `max_gross_exposure` |
| Max ticker kitettség | $20,000 | `max_single_ticker_exposure` |
| Max darabszám | 5,000 | `max_order_quantity` (BC12) |

---

## 8. Async vs Sync Összehasonlítás

| Szempont | Sync (default) | Async (`IFDS_ASYNC_ENABLED=true`) |
|----------|----------------|-----------------------------------|
| Phase 4 idő | ~11–12 perc | ~2–3 perc |
| Phase 5 idő | ~30 mp | ~5–10 mp |
| API hívások | Szekvenciális | 10 ticker párhuzamosan |
| Provider semaphore | Nincs | Polygon: 5, FMP: 8, UW: 5 |
| Circuit breaker | Per-provider (BC11) | Per-provider (BC11) |
| Publikus interface | `run_phase4(...)` | Ugyanaz — `asyncio.run()` belül |
| Tesztek | 563 (mind átmegy mindkét módban) | Mind átmegy mindkét módban |
