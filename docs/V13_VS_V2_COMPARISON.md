# IFDS v13 vs v2.0 — Feature Comparison

> Generálva a `reference/` (v13) és `src/ifds/` (v2.0) forráskódból.
> Frissitve: 2026-02-11 (BC14 utan, 636 teszt)

---

## Összefoglaló

| Szempont | v13 (`reference/`) | v2.0 (`src/ifds/`) |
|----------|--------------------|--------------------|
| **Fájlok** | 16 Python + 1 YAML config | 30+ Python moduláris struktúra |
| **Sorok** | ~10,800 | ~8,000 |
| **Architekturális minta** | Monolitikus orchestrator (`signal_generator.py` = 83K) | Phase-alapú pipeline (phase0→6, runner.py) |
| **Config** | YAML (`settings.yaml`, 784 sor) | Python dict (`config/defaults.py`) |
| **Tesztek** | Nincs (manuális validáció) | 636 unit test (pytest) |
| **Async** | Natív `asyncio`/`aiohttp` végig | Opcionális (`IFDS_ASYNC_ENABLED=true`), sync default |
| **V13 feature lefedettség** | — | ~96% (BC14 után) |

---

## 1. Konfiguráció

| Szempont | v13 | v2.0 | Megjegyzés |
|----------|-----|------|------------|
| **Formátum** | YAML (`settings.yaml`) | Python dict (`defaults.py`) | v2.0 egyszerűbb, IDE autocomplete |
| **Env var substitúció** | `${VAR_NAME:default}` regex | `os.environ.get()` direkt | v13 elegánsabb de törékennyebb |
| **Singleton** | `ConfigManager` osztály | Modul-szintű CORE/TUNING/RUNTIME dict | v2.0 nincs singleton overhead |
| **Validáció** | `config.validate()` metódus | Nincs explicit | v13 ellenőrzi hogy a súlyok = 1.0 |

---

## 2. API Providerek

| Provider | v13 Endpoint | v2.0 Endpoint | Különbség |
|----------|-------------|---------------|-----------|
| **Polygon OHLCV** | `/v2/aggs/ticker/.../range` | Ugyanaz | Azonos |
| **Polygon Grouped** | `/v2/aggs/grouped/locale/us/market/stocks` | Ugyanaz | Azonos |
| **Polygon Options** | `/v3/snapshot/options/{symbol}` | Ugyanaz + DTE filter (BC12) | v2.0: ≤90 DTE szűrő |
| **Polygon I:VIX** | `/v2/aggs/ticker/I:VIX/...` | Ugyanaz | Azonos |
| **FMP Screener** | `/stable/company-screener` | Ugyanaz | Azonos |
| **FMP Fundamentals** | `/stable/financial-growth`, `/stable/key-metrics` | Ugyanaz | Azonos |
| **FMP Insider** | `/stable/insider-trading/search` | Ugyanaz | Azonos |
| **FMP Inst Ownership** | Nincs | `/stable/institutional-ownership/latest` | v2.0 újdonság (BC12) |
| **FMP ETF Holdings** | Nincs | `/stable/etf/holdings` | v2.0 újdonság (BC14, breadth) |
| **FRED VIX** | `VIXCLS` (fallback) | `VIXCLS` (fallback) | Mindkettőben fallback |
| **FRED TNX** | `DGS10` | `DGS10` | Azonos |
| **UW Dark Pool** | `/api/darkpool/{symbol}` | `/api/darkpool/recent` (batch) | v2.0: batch prefetch (BC6) |
| **UW GEX** | Nem használja | `/api/stock/{symbol}/greek-exposure/strike` | v2.0 UW elsődleges GEX |

---

## 3. VIX Kezelés

| Szempont | v13 | v2.0 |
|----------|-----|------|
| **Elsődleges forrás** | Polygon I:VIX | Polygon I:VIX |
| **Fallback** | FRED VIXCLS | FRED VIXCLS |
| **Ultimate fallback** | Nincs (None → hiba) | Default 20.0 (NORMAL regime) |
| **Sanity check** | 5–100 tartomány | **5–100 tartomány** (BC11) |
| **EXTREME regime** | Nincs | VIX > 50 → EXTREME, mult 0.10 (BC12) |
| **Source tracking** | Nincs | `vix_source` mező |
| **Klasszifikáció** | LOW/NORMAL/ELEVATED/PANIC | LOW/NORMAL/ELEVATED/PANIC/**EXTREME** |
| **Multiplier** | `1.0 - (excess × 0.02)`, floor 0.25 | Ugyanaz + EXTREME override (0.10) |

---

## 4. GEX (Gamma Exposure)

| Szempont | v13 | v2.0 (BC12) |
|----------|-----|-------------|
| **Elsődleges forrás** | Polygon options snapshot | **UW per-strike** (`/greek-exposure/strike`) |
| **Fallback** | Nincs (csak Polygon) | Polygon options snapshot |
| **Számítási módszer** | `Gamma × OI × 100 × Spot² × 0.01` | UW: pre-computed dollar GEX |
| **Zero gamma** | Lineáris interpoláció | **Lineáris interpoláció** (BC12) |
| **Call wall szűrés** | ≤5× ATR távolság filter | **≤5× ATR távolság filter** (BC12) |
| **Expiry szűrés** | Front-month only (≤35 DTE) | **≤90 DTE** (BC12) |
| **GEX Regime** | POSITIVE / NEGATIVE / NEUTRAL / HIGH_VOL | POSITIVE / NEGATIVE / HIGH_VOL |
| **Adapter pattern** | Nincs | `FallbackGEXProvider` (UW → Polygon) |
| **GEX sign** | — | Put GEX signed (kivonva gex_by_strike-ból) |

---

## 5. Caching

| Szempont | v13 | v2.0 |
|----------|-----|------|
| **Implementáció** | File-based JSON cache | **File-based JSON cache** (BC7) |
| **TTL** | 7 nap (configurable) | 7 nap (configurable) |
| **Atomi írás** | `temp_file + os.replace()` | `temp_file + os.replace()` |
| **Cache path** | `data/fmp_cache/{endpoint}/{date}/{symbol}.json` | `data/cache/{provider}/{endpoint}/{date}/{symbol}.json` |
| **API hívás megtakarítás** | ~70% (becsült) | ~70% (becsült) |

---

## 6. Async / Párhuzamosítás

| Szempont | v13 | v2.0 |
|----------|-----|------|
| **Alapértelmezés** | Async (natív `asyncio`/`aiohttp`) | Sync (`requests` könyvtár) |
| **Async mód** | Mindig | Opcionális (`IFDS_ASYNC_ENABLED=true`) |
| **Rate limits** | Polygon: 20, FMP: 5, FRED: 1 | Polygon: 5, FMP: 8, UW: 5 |
| **Phase 4 idő** | ~2–3 perc (async) | ~11 min (sync), ~2.4 min (async) |
| **Circuit breaker** | Nincs explicit API CB | **Per-provider CB** (BC11) |

---

## 7. Scoring Rendszer

### 7.1 Súlyok és Küszöbök

| Szempont | v13 | v2.0 | Egyezik? |
|----------|-----|------|----------|
| Flow súly | 0.40 | 0.40 | Igen |
| Fundamental súly | 0.30 | 0.30 | Igen |
| Technical súly | 0.30 | 0.30 | Igen |
| Min combined score | 70 | 70 | Igen |
| Clipping threshold | 85 → score=50 | 95 → kizárás | **Eltér** |
| Freshness bonus | 1.75× | 1.5× | **Eltér** |

### 7.2 Technical Scoring

| Component | v13 | v2.0 | Státusz |
|-----------|-----|------|---------|
| RSI Ideal Zone | [45-65] → +30 | [45-65] → +30 | **Azonos** (BC9) |
| SMA50 bonus | Price > SMA50 → +30 | Price > SMA50 → +30 | **Azonos** (BC9) |
| RS vs SPY | 3mo outperf → +40 | 3mo outperf → +40 | **Azonos** (BC9) |

### 7.3 Flow Scoring

| Component | v13 | v2.0 | Státusz |
|-----------|-----|------|---------|
| PCR scoring | PCR < 0.7 → +15 | PCR < 0.7 → +15 | **Azonos** (BC9) |
| OTM call ratio | > 40% → +10 | > 40% → +10 | **Azonos** (BC9) |
| Block trades | >5: +10, >20: +15 | >5: +10, >20: +15 | **Azonos** (BC9) |
| dp_pct | dp_vol / total_vol | dp_vol / Polygon vol | **Azonos** (BC10) |
| Buy Pressure | (close-low)/(high-low) | (close-low)/(high-low) | **Azonos** (BC10) |
| VWAP | close vs VWAP | close vs VWAP (Polygon vw) | **Azonos** (BC10) |
| DTE filter (flow) | ≤35 DTE | ≤90 DTE | **Eltér** (BC12) |

### 7.4 Fundamental Scoring

| Component | v13 | v2.0 | Státusz |
|-----------|-----|------|---------|
| Shark detector | 2+ insider, $100K+ | 2+ insider, $100K+ | **Azonos** (BC9) |
| Institutional ownership | Nincs | QoQ > 2%: +10 | **v2.0 extra** (BC12) |

---

## 8. Position Sizing

| Szempont | v13 | v2.0 |
|----------|-----|------|
| **Base risk** | 1.5% ($1,500) | 0.5% ($500) |
| **Max risk** | 3.0% ($3,000) | 1.5% ($1,500) |
| **TP2** | 4R (4× risk) | 3× ATR |
| **Max positions** | 15 | 8 |
| **Max/szektor** | 3 | 3 |
| **Max gross exposure** | $35,000 | $100,000 |
| **Max ticker exposure** | $6,000 | $20,000 |
| **Fat finger** | max qty=5000 | max qty=5000 (BC12) |
| **NaN/Inf guard** | Explicit input check | `not (atr > 0)` guard (BC12) |

---

## 9. Biztonsági Funkciók

| Feature | v13 | v2.0 | Státusz |
|---------|-----|------|---------|
| **Signal idempotency** | Hash-based dedup (24h TTL) | SHA256 dedup (24h TTL) | **Azonos** (BC11) |
| **API circuit breaker** | Auto-halt > 20% error rate | Per-provider CB (30% error, 50 window) | **Azonos** (BC11) |
| **Fat finger protection** | Max qty=5000, value limit | Max qty=5000, exposure cap | **Azonos** (BC12) |
| **VIX sanity check** | 5–100 range | 5–100 range | **Azonos** (BC11) |
| **GlobalGuard logging** | Dedikált modul | [GLOBALGUARD] prefix | **Azonos** (BC11) |
| **Secret sanitization** | Logging SecretFilter | Nincs explicit | **Hiányzik** |

---

## 10. Hiányzó Feature-ök v2.0-ban (BC14 után)

### Nice-to-have (P3)

| Feature | v13 referencia | Prioritás | Státusz |
|---------|---------------|-----------|---------|
| **SimEngine (backtesting)** | `sim_engine.py` | P3 | ❌ Hiányzik |
| **Trailing Stop Engine** | `settings.yaml` | P3 | ❌ Hiányzik |
| **Survivorship Bias** | `universe_builder.py` | P3 | **DONE** (BC13) |
| **Telegram Alerts** | `signal_generator.py` | P3 | **DONE** (BC13) |
| **Max Daily Trades** | `global_guard.py` | P3 | **DONE** (BC13) |
| **Notional Limits** | `settings.yaml` | P3 | **DONE** (BC13) |
| **Sector Breadth** | `sector_engine.py` | P3 | **DONE** (BC14) |

---

## 11. v2.0 Újdonságok (v13-ban nincs)

| Feature | Leírás | BC |
|---------|--------|----|
| **UW per-strike GEX** | Pre-computed dollar GEX elsődleges forrás | BC3 |
| **3 szintű VIX fallback** | Polygon → FRED → default 20.0 | BC1 |
| **VIX EXTREME regime** | VIX > 50 → multiplier 0.10 | BC12 |
| **Dual-mode async** | Sync default + async opcionális | BC5 |
| **Phase-based pipeline** | Phase 0→6 struktúra | BC1 |
| **563 unit test** | Teljes teszt lefedettség | BC1-12 |
| **Dark Pool batch** | 882 call → 15 paginated batch | BC6 |
| **File-based cache** | Per-provider/endpoint/date/symbol cache | BC7 |
| **Per-sector BMI** | FMP sector mapping, SMA25 per sector | BC8 |
| **Institutional ownership** | FMP inst ownership QoQ trend scoring | BC12 |
| **DTE filter + fallback** | ≤90 DTE + <5 contract fallback | BC12 |
| **Survivorship Bias** | Universe snapshot + diff logging | BC13 |
| **Telegram Alerts** | Non-blocking trade alerts (env var gated) | BC13 |
| **Max Daily Trades + Notional** | Daily trade/notional limits with state persistence | BC13 |
| **Sector Breadth** | 7 regime, SMA20/50/200, divergence detection, FMP ETF holdings | BC14 |
| **CLI Dashboard** | Colorama console output | Post-BC7 |

---

## 12. Migrációs Terv — Aktuális Státusz

| BC | Terv | Státusz |
|----|------|---------|
| BC1 | Infrastructure + Phase 0 | **COMPLETE** (51 tests) |
| BC2 | Phase 1-3 (BMI, Universe, Sectors) | **COMPLETE** (123 tests) |
| BC3 | Phase 4-5 (Stock Analysis, GEX) | **COMPLETE** (213 tests) |
| BC4 | Phase 6 (Position Sizing, Output) | **COMPLETE** (266 tests) |
| BC5 | Async Migration | **COMPLETE** (299 tests) |
| BC6 | Dark Pool Batch Fetch | **COMPLETE** (340 tests) |
| BC7 | Monitoring CSVs + File Cache | **COMPLETE** (372 tests) |
| — | CLI Dashboard | **COMPLETE** (392 tests) |
| BC8 | Per-Sector BMI | **COMPLETE** (446 tests) |
| BC9 | Options Flow + Shark + Tech Scoring | **COMPLETE** (476 tests) |
| BC10 | dp_pct Fix + Buy Pressure VWAP | **COMPLETE** (492 tests) |
| BC11 | P2 Robustness (CB, Dedup, VIX, Guard) | **COMPLETE** (530 tests) |
| BC12 | P3 Nice-to-haves (6 features) | **COMPLETE** (563 tests) |
| BC13 | P3 Backlog (Survivorship, Telegram, Limits) | **COMPLETE** (593 tests) |
| BC14 | Sector Breadth Analysis | **COMPLETE** (636 tests) |

---

*Frissítve: 2026-02-11 | V13 feature lefedettség: ~96%*
