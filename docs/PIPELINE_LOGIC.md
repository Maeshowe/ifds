# IFDS Pipeline Logic — Képletek és Küszöbértékek

> Generálva a `src/ifds/` forráskódból, 2026-02-11.
> Minden képlet, küszöbérték és logika a **ténylegesen implementált kódból** van kiolvasva.
> Konfigurációs értékek forrása: `src/ifds/config/defaults.py`
> Frissítve: AGG Telegram fix után (817 teszt)

---

## Phase 0 — System Diagnostics

**Forrás**: `src/ifds/phases/phase0_diagnostics.py`

### Mit csinál?

Pre-flight ellenőrzések a pipeline futtatás előtt:

1. **API Health Check** — Polygon, FMP, FRED kritikusak; UW opcionális
2. **Per-provider Circuit Breaker** — API error rate monitoring (BC11)
3. **Drawdown Circuit Breaker** — napi drawdown ellenőrzés (`state/circuit_breaker.json`)
4. **Macro Regime** — VIX és TNX feldolgozás

**Input**: Config, API kulcsok
**Output**: `DiagnosticsResult` (macro regime, VIX multiplier, UW elérhetőség)

### Per-provider Circuit Breaker (BC11)

```
ProviderCircuitBreaker (src/ifds/data/circuit_breaker.py):

  Állapotok:
    CLOSED  → normál működés, minden hívás átmegy
    OPEN    → error rate > 30% → összes hívás blokkolva
    HALF_OPEN → cooldown (60s) után 1 próba hívás

  Átmenetek:
    CLOSED → OPEN:     ha error_count / window_size > error_threshold
    OPEN → HALF_OPEN:  ha elapsed > cooldown_seconds
    HALF_OPEN → CLOSED: ha próba hívás sikeres
    HALF_OPEN → OPEN:   ha próba hívás sikertelen

  Integrálva: BaseAPIClient._get() és AsyncBaseAPIClient._get()
  4 példány: polygon, fmp, uw, fred — megosztva minden phase között
```

- Konfig: `cb_window_size=50`, `cb_error_threshold=0.3`, `cb_cooldown_seconds=60`

### VIX Forrás — 3 szintű Fallback

```
_get_vix_value(polygon, fred, config):
  1. polygon.get_index_value("I:VIX")
     → GET /v2/aggs/ticker/I:VIX/range/1/day/{from}/{to}
     → Siker → (vix_value, source="polygon")

  2. Ha Polygon None → fred.get_series("VIXCLS", limit=5)
     → _get_latest_fred_value() → (vix_value, source="fred")

  3. Ha FRED is None → (20.0, source="default")
```

- Polygon I:VIX: real-time, intraday VIX érték
- FRED VIXCLS: 1 nappal késleltetett záró VIX
- Default 20.0: konzervatív — NORMAL regime, 1.0 multiplier
- A forrás a `DiagnosticsResult.vix_source` mezőben (`"polygon"`, `"fred"`, `"default"`)

### VIX Sanity Check (BC11)

```
_validate_vix(vix):
  ha vix < 5.0 VAGY vix > 100.0:
    WARNING log → return 20.0 (default)
  egyébként:
    return vix
```

- Mindkét forrásra (Polygon és FRED) alkalmazva
- Tartomány: [5.0, 100.0]

### VIX Klasszifikáció

```
_classify_vix(vix, config):
  ha vix > 50  → EXTREME    (BC12)
  ha vix > 30  → PANIC
  ha vix > 20  → ELEVATED
  ha vix > 15  → NORMAL
  egyébként    → LOW
```

Konfig: `vix_low=15`, `vix_normal=20`, `vix_elevated=30`, `vix_extreme_threshold=50`

### VIX Multiplier Képlet

```
_calculate_vix_multiplier(vix, config):
  ha vix > 50:  return 0.10                          (EXTREME — BC12)
  ha vix <= 20: return 1.0
  egyébként:    return max(0.25, 1.0 - (vix - 20) × 0.02)
```

Konfig: `vix_penalty_start=20`, `vix_penalty_rate=0.02`, `vix_multiplier_floor=0.25`, `vix_extreme_threshold=50`, `vix_extreme_multiplier=0.10`

| VIX | Multiplier | Regime |
|-----|-----------|--------|
| 12 | 1.0 | LOW |
| 18 | 1.0 | NORMAL |
| 25 | 0.90 | ELEVATED |
| 30 | 0.80 | ELEVATED |
| 40 | 0.60 | PANIC |
| 50 | 0.40 | PANIC |
| 51 | **0.10** | **EXTREME** |
| 65 | **0.10** | **EXTREME** |

### TNX Rate Sensitivity

```
tnx_rate_sensitive = tnx_value > tnx_sma20 × (1 + 5/100)
```

- TNX SMA20 az utolsó 20 érvényes FRED `DGS10` értékből
- Ha `tnx_rate_sensitive=True`: Technology és Real Estate szektorok -10 büntetést kapnak Phase 3-ban
- Konfig: `tnx_sensitivity_pct=5`, `tnx_sensitive_sectors=["Technology", "Real Estate"]`

### Drawdown Circuit Breaker

```
HALT ha: daily_drawdown_pct > circuit_breaker_drawdown_limit_pct
```

- Konfig: `circuit_breaker_drawdown_limit_pct=3.0`
- State file: `state/circuit_breaker.json`
- Manuális reset szükséges

---

## Phase 1 — Market Regime (BMI)

**Forrás**: `src/ifds/phases/phase1_regime.py`

### Mit csinál?

Intézményi pénzáramlás elemzése → LONG vagy SHORT stratégia.

**Input**: Polygon grouped daily bars (75 naptári nap, vagy 330 ha breadth enabled — BC14)
**Output**: `Phase1Result` → `StrategyMode` (LONG/SHORT), BMI érték (0–100), per-sector BMI, grouped_daily_bars (BC14)

### Async Path (BC16)

```
Ha async_enabled=True:
  _run_phase1_async():
    _fetch_daily_history_async() — asyncio.gather ~235 grouped daily calls
    Semaphore: polygon=10

  Pure computation unchanged (szinkron):
    _calculate_daily_ratios, _calculate_sector_bmi, _classify_bmi, _detect_divergence
```

### Volume Spike Detekció

```
Minden tickerre, minden napra:
  mean_vol = SMA(volume, 20 nap)
  sigma_vol = sqrt(variance(volume, 20 nap))
  threshold = mean_vol + k × sigma_vol

  ha volume > threshold:
    ha close > open → BUY signal
    ha close < open → SELL signal
```

- Konfig: `bmi_volume_spike_sigma (k) = 2.0`, `bmi_volume_avg_period = 20`

### BMI Számítás

```
daily_ratio = buy_count / (buy_count + sell_count) × 100
  (ha nincs signal: 50.0)

BMI = SMA(daily_ratio, 25 nap)
```

- Konfig: `bmi_sma_period = 25`

### Per-Sector BMI (BC8)

```
FMP get_sector_mapping() → {ticker: sector} → sector → ETF mapping
Minden szektorra:
  sector_daily_ratio = sector_buy / (sector_buy + sector_sell) × 100
  sector_BMI = SMA(sector_daily_ratio, 25 nap)

Minimum: sector_bmi_min_signals=5 buy+sell/nap/szektor
```

- Konfig: `sector_bmi_min_signals=5`, `lookback_calendar_days=75`
- Output: `Phase1Result.sector_bmi_values: dict[str, float]` (ETF → BMI%)

### BMI Regime Klasszifikáció

```
ha BMI <= 25  → GREEN  (agresszív LONG)
ha BMI >= 80  → RED    (SHORT/defenzív)
egyébként     → YELLOW (normál LONG)
```

- Konfig: `bmi_green_threshold=25`, `bmi_red_threshold=80`
- **Stratégia**: RED → `StrategyMode.SHORT`, egyébként → `StrategyMode.LONG`

### Divergencia Detekció

```
Bearish divergencia ha:
  SPY 5 napos változás > +1%
  ÉS BMI 5 napos változás < -2 pont
```

- Konfig: `bmi_divergence_spy_change_pct=1.0`, `bmi_divergence_bmi_change_pts=-2.0`

### Fallback

Ha kevesebb mint 25 nap adat: BMI=50.0, YELLOW regime, LONG stratégia.

---

## Phase 2 — Universe Building

**Forrás**: `src/ifds/phases/phase2_universe.py`

### Mit csinál?

FMP Screener alapján szűri a piacot kereskedhető univerzumra.

**Input**: FMP screener + earnings calendar, StrategyMode
**Output**: `Phase2Result` → `list[Ticker]`

### LONG Universe Szűrők

| Szűrő | Küszöb | Konfig kulcs |
|--------|--------|--------------|
| Market cap | > $2,000,000,000 | `universe_min_market_cap` |
| Ár | > $5.00 | `universe_min_price` |
| Átlagos forgalom | > 500,000 db/nap | `universe_min_avg_volume` |
| ETF | Nem | `isEtf=False` |
| Aktívan kereskedett | Igen | `universe_require_options` |

Eredmény: ~3,000 ticker

### SHORT (Zombie) Universe Szűrők

| Szűrő | Küszöb | Konfig kulcs |
|--------|--------|--------------|
| Market cap | > $500,000,000 | `zombie_min_market_cap` |
| Átlagos forgalom | > 500,000 db/nap | `zombie_min_avg_volume` |
| Debt/Equity | > 3.0 | `zombie_min_debt_equity` |
| Net margin | < 0% (negatív) | `zombie_max_net_margin` |
| Interest coverage | < 1.5 (ha elérhető) | `zombie_max_interest_coverage` |

Eredmény: ~200 ticker

### Zombie Hunter (Earnings Kizárás)

Kétlépcsős ellenőrzés:

```
Pass 1 (Bulk): /stable/earnings-calendar → gyors, lefedi a legtöbb tickert
Pass 2 (Ticker-specific): /stable/earnings?symbol= → survivor-okra fut,
         elkapja az ADR-eket és kisebb részvényeket (ThreadPoolExecutor, max 20 worker)
Ha bármelyik pass-ban a ticker earnings-je a következő N napon belül van → KIZÁR
API hiba → fail-open (ticker átengedett, WARNING log)
```

- Konfig: `earnings_exclusion_days=7`
- FMP endpoints: `/stable/earnings-calendar` (bulk) + `/stable/earnings?symbol=` (per-ticker)

### Survivorship Bias Protection (BC13)

```
_save_universe_snapshot(tickers, config, logger):

  1. Mentés: state/universe_snapshots/{date}.json
     → [{symbol, market_cap, sector}, ...]

  2. Diff előző nappal:
     → removed = prev_symbols - curr_symbols
     → added = curr_symbols - prev_symbols
     → "[SURVIVORSHIP] Removed from universe: [TSLA, ...]"  (WARNING)
     → "[SURVIVORSHIP] New in universe: [NVDA, ...]"        (INFO)
     → "[SURVIVORSHIP] Universe unchanged"                   (DEBUG)

  3. Pruning: max survivorship_max_snapshots (30) file megőrzés
```

- Konfig: `survivorship_snapshot_dir="state/universe_snapshots"`, `survivorship_max_snapshots=30`
- Non-blocking: try/except, hiba → CONFIG_WARNING log

---

## Phase 3 — Sector Rotation

**Forrás**: `src/ifds/phases/phase3_sectors.py`

### Mit csinál?

11 SPDR szektori ETF momentum-elemzése, rangsorolás, vétó mátrix.

**Input**: Polygon OHLCV (11 ETF × 25 nap), MacroRegime, sector_bmi_values (Phase 1-ből), grouped_daily_bars (Phase 1-ből, BC14), FMP client (BC14)
**Output**: `Phase3Result` → `list[SectorScore]` + vetoed/active szektorok

### ETF-ek

```
XLK (Technology), XLF (Financials), XLE (Energy), XLV (Healthcare),
XLI (Industrials), XLP (Consumer Defensive), XLY (Consumer Cyclical),
XLB (Basic Materials), XLC (Communication Services), XLRE (Real Estate),
XLU (Utilities)
```

### Momentum Számítás

```
momentum_5d = ((close_today - close_5d_ago) / close_5d_ago) × 100
```

- Konfig: `sector_momentum_period=5`

### Trend Meghatározás

```
SMA20 = SMA(close, 20 nap)

ha close_today > SMA20 → SectorTrend.UP
egyébként              → SectorTrend.DOWN
```

### Rangsorolás és Klasszifikáció

A 11 ETF momentum alapján rendezve:

| Rang | Klasszifikáció | Score Adjustment |
|------|----------------|------------------|
| 1–3 (top) | LEADER | **+15** |
| 4–8 (közép) | NEUTRAL | **0** |
| 9–11 (alsó) | LAGGARD | **-20** |

- Konfig: `sector_leader_count=3`, `sector_laggard_count=3`, `sector_leader_bonus=15`, `sector_laggard_penalty=-20`

### Sector BMI Regime

Per-szektori BMI küszöbök (oversold, overbought):

| ETF | Oversold < | Overbought > |
|-----|-----------|--------------|
| XLK (Technology) | 12 | 85 |
| XLF (Financials) | 10 | 80 |
| XLE (Energy) | 10 | 75 |
| XLV (Healthcare) | 12 | 80 |
| XLI (Industrials) | 12 | 80 |
| XLP (Consumer Defensive) | 15 | 75 |
| XLY (Consumer Cyclical) | 9 | 80 |
| XLB (Basic Materials) | 12 | 80 |
| XLC (Communication) | 12 | 80 |
| XLRE (Real Estate) | 9 | 85 |
| XLU (Utilities) | 15 | 75 |

### Vétó Mátrix (csak LONG stratégia)

| Momentum | Sector BMI | Döntés | Score Adj |
|----------|-----------|--------|-----------|
| Leader | Bármelyik | **ENGEDÉLYEZVE** | +15 |
| Neutral | NEUTRAL | **ENGEDÉLYEZVE** | 0 |
| Neutral | OVERSOLD | **ENGEDÉLYEZVE** | 0 |
| Neutral | OVERBOUGHT | **VÉTÓ** | — |
| Laggard | OVERSOLD | **ENGEDÉLYEZVE** (MR) | **-5** |
| Laggard | NEUTRAL | **VÉTÓ** | — |
| Laggard | OVERBOUGHT | **VÉTÓ** | — |

- A Laggard+OVERSOLD a "Mean Reversion" lehetőség, enyhébb büntetéssel (-5 vs -20)
- Konfig: `sector_laggard_mr_penalty=-5`

### TNX Rate Sensitivity Büntetés

```
Ha tnx_rate_sensitive (Phase 0-ból):
  Technology szektor: score_adjustment -= 10
  Real Estate szektor: score_adjustment -= 10
```

### Sector Breadth Analysis (BC14)

**Forrás**: `_calculate_sector_breadth()` in `phase3_sectors.py`

A Phase 1 grouped daily bars (330 nap) újrafelhasználásával per-szektor breadth metrikákat számol.

#### Breadth Számítás

```
Minden szektor ETF-re:
  1. FMP get_etf_holdings(etf) → constituent ticker lista (cached)
  2. _build_ticker_close_history(grouped_bars, holdings) → {ticker: [closes]}
  3. Per ticker: price > SMA(period) → count_above

  pct_above_sma20  = count_above_20 / total_with_data × 100
  pct_above_sma50  = count_above_50 / total_with_data × 100
  pct_above_sma200 = count_above_200 / total_with_data × 100

  breadth_score = 0.20 × pct_above_sma20 + 0.50 × pct_above_sma50 + 0.30 × pct_above_sma200
```

- Konfig: `breadth_composite_weights=(0.20, 0.50, 0.30)`, `breadth_min_constituents=10`
- AGG (bond ETF): automatikusan skippelve, breadth nem alkalmazható

#### 7 Breadth Regime Klasszifikáció

```
_classify_breadth_regime(pct_sma50, pct_sma200):

  ha b50 > 70 ÉS b200 > 70     → STRONG
  ha b50 > 70 ÉS 30 ≤ b200 ≤ 70 → EMERGING
  ha 30 ≤ b50 ≤ 70 ÉS b200 > 70 → CONSOLIDATING
  ha 30 ≤ b50 ≤ 70 ÉS 30 ≤ b200 ≤ 70 → NEUTRAL
  ha b50 < 30 ÉS 30 ≤ b200 ≤ 70 → WEAKENING
  ha b50 < 30 ÉS b200 < 30     → WEAK
  ha b50 > 50 ÉS b200 < 30     → RECOVERY
  egyébként                     → NEUTRAL (catch-all)
```

#### Breadth Momentum és Divergencia Detekció

```
breadth_momentum = pct_sma50_today - pct_sma50_5d_ago

_detect_breadth_divergence(etf_momentum_5d, breadth_momentum):
  Bearish: ETF 5d > +2% ÉS breadth_momentum < -5 pont
  Bullish: ETF 5d < -2% ÉS breadth_momentum > +5 pont
```

- Konfig: `breadth_divergence_etf_threshold=2.0`, `breadth_divergence_breadth_threshold=5.0`

#### Score Adjustment

| Feltétel | Adjustment | Konfig |
|----------|-----------|--------|
| breadth_score > 70 | **+5** | `breadth_strong_bonus=5` |
| breadth_score < 50 | **-5** | `breadth_weak_penalty=-5` |
| breadth_score < 30 | **-15** | `breadth_very_weak_penalty=-15` |
| Bearish divergence | **-10** (stackelődik) | `breadth_divergence_penalty=-10` |

- A breadth score_adj hozzáadódik a szektor `score_adjustment`-hez (befolyásolja a sector rankinget: leader/neutral/laggard)
- **FONTOS**: A breadth adj NEM propagálódik a Phase 4 ticker score-ba. A `sector_adj_map` kiszűri: `s.score_adjustment - s.breadth_score_adj` — így a ticker CSAK a momentum-alapú adj-t kapja (+15 leader, -20 laggard, 0 neutral, -5 MR) + TNX sensitivity.
- Sorrend: sector momentum → sector BMI → **breadth** → veto matrix

---

## Phase 4 — Individual Stock Analysis

**Forrás**: `src/ifds/phases/phase4_stocks.py`

### Mit csinál?

Minden tickert 3 dimenzió mentén pontozza (Technical, Flow, Fundamental), kombinált score-ral szűr.

**Input**: Polygon OHLCV + FMP fundamentals + UW dark pool + Polygon options snapshot, list[Ticker], list[SectorScore]
**Output**: `Phase4Result` → `list[StockAnalysis]` combined score-ral

### Alap Score

Minden dimenzió **bázis** score-ral indul, az adjustmentek ezt tolják fel/le.

```python
# Flow és Fundamental: 50-es bázis
_BASE_SCORE = 50
# Technical: 0 bázis (nincs base, BC9 — max 100)
```

---

### 4.1 Technical Analysis

#### SMA (Simple Moving Average)

```
SMA(period) = sum(closes[-period:]) / period
```

- `SMA200`: trend filter (CORE `sma_long_period=200`)
- `SMA50`: mid-term bonus (CORE `sma_mid_period=50`)
- `SMA20`: short-term reference (CORE `sma_short_period=20`)

#### RSI (Relative Strength Index)

```
changes[i] = close[i] - close[i-1]
gains[i] = max(change, 0)
losses[i] = max(-change, 0)

avg_gain = SMA(gains, 14)
avg_loss = SMA(losses, 14)

RS = avg_gain / avg_loss
RSI = 100 - 100 / (1 + RS)
```

- Ha avg_loss = 0 és avg_gain > 0: RSI = 100
- Ha kevesebb mint 15 bár: RSI = 50 (neutral)
- Konfig: `rsi_period=14`

#### ATR (Average True Range)

```
TR[i] = max(H[i] - L[i], |H[i] - C[i-1]|, |L[i] - C[i-1]|)
ATR = SMA(TR, 14)
```

- Konfig: `atr_period=14`

#### SMA200 Trend Filter

```
LONG:  trend_pass = (price > SMA200)
SHORT: trend_pass = (price < SMA200)
```

Ha `SMA200 <= 0` (nincs adat): automatikusan átmegy.

#### RSI Ideal Zone Score (BC9 — régi ±5 helyett)

| RSI tartomány | Score | Konfig kulcsok |
|---------------|-------|----------------|
| [45–65] (inner zone) | **+30** | `rsi_ideal_inner_low=45`, `rsi_ideal_inner_high=65`, `rsi_ideal_inner_bonus=30` |
| [35–45) vagy (65–75] (outer zone) | **+15** | `rsi_ideal_outer_low=35`, `rsi_ideal_outer_high=75`, `rsi_ideal_outer_bonus=15` |
| < 35 vagy > 75 | **0** | — |

#### SMA50 Bonus (BC9)

```
ha price > SMA50 → +30
egyébként        → 0
```

- Konfig: `sma50_bonus=30`

#### RS vs SPY (BC9)

```
spy_return_3mo = (spy_close_today - spy_close_63d_ago) / spy_close_63d_ago
ticker_return_3mo = (close_today - close_63d_ago) / close_63d_ago

ha ticker_return_3mo > spy_return_3mo → +40
egyébként                            → 0
```

- SPY return egyszer lekérdezve a ticker loop előtt, minden tickerre újrafelhasználva
- Konfig: `rs_spy_bonus=40`

#### Tech Sub-Score

```
tech_score = rsi_ideal_bonus + sma50_bonus + rs_spy_bonus
tech_score = min(100, tech_score)
```

Tartomány: **0–100** (max: 30+30+40=100)

---

### 4.2 Flow Analysis

#### RVOL (Relative Volume)

```
volume_sma_20 = SMA(volumes, 20)
RVOL = volume_today / volume_sma_20
```

#### RVOL Score

| RVOL tartomány | Score Adjustment | Konfig kulcs |
|----------------|------------------|--------------|
| < 0.5 (alacsony) | **-10** | `rvol_low_penalty` |
| 0.5–1.0 (normál) | **0** | — |
| 1.0–1.5 (emelkedett) | **+5** | `rvol_elevated_bonus` |
| > 1.5 (szignifikáns) | **+15** | `rvol_significant_bonus` |

Konfig: `rvol_low=0.5`, `rvol_normal=1.0`, `rvol_elevated=1.5`

#### Spread Analysis

```
spread_today = high - low
spread_sma_10 = SMA(spreads, 10)
spread_ratio = spread_today / spread_sma_10
```

#### Squat Bar Detekció

```
squat = (RVOL > 2.0) ÉS (spread_ratio < 0.9)
squat_bonus = 10 ha squat, egyébként 0
```

Jelentése: Magas forgalom DE szűk ár-tartomány → nagy intézményi akkumuláció.

Konfig: `squat_bar_rvol_min=2.0`, `squat_bar_spread_ratio_max=0.9`, `squat_bar_bonus=10`

#### Dark Pool Signal

```
Ha dp_data elérhető ÉS dp_pct > 40%:
  Ha dp_buys > dp_sells → BULLISH
  Ha dp_sells > dp_buys → BEARISH
  Egyébként              → NEUTRAL
```

- A dp_pct küszöb: `dark_pool_volume_threshold_pct=40`
- Ha nincs UW adat: `dp_pct=0.0`, `signal=None` (nincs büntetés)

#### dp_pct Számítás (BC10 — Polygon volume mint nevező)

```
dp_volume = sum(record["volume"] for record in dp_records)
polygon_volume = bars[-1]["v"]   (legutolsó Polygon napi volume)

dp_pct = dp_volume / polygon_volume × 100
```

- **Fontos**: Polygon daily volume a nevező (nem UW volume) — megbízhatóbb referencia

#### dp_pct Score (BC10)

| dp_pct tartomány | Score | Konfig |
|------------------|-------|--------|
| > 60% | **+15** | `dp_pct_high_threshold=60`, `dp_pct_high_bonus=15` |
| > 40% | **+10** | `dp_pct_bonus=10` |
| ≤ 40% | **0** | — |

#### Buy Pressure Score (BC10)

```
buy_pressure = (close - low) / (high - low)
```

| Buy Pressure | Score | Konfig |
|-------------|-------|--------|
| > 0.7 (erős) | **+15** | `buy_pressure_strong_bonus=15` |
| < 0.3 (gyenge) | **-15** | `buy_pressure_weak_penalty=-15` |
| 0.3–0.7 | **0** | — |

#### VWAP Score (BC10)

```
VWAP = Polygon "vw" mező (volume-weighted average price)
       ha nincs vw → fallback: (H + L + C) / 3
```

| Feltétel | Score | Konfig |
|----------|-------|--------|
| close > VWAP ÉS (close - VWAP) / VWAP > 1% (erős) | **+15** | `vwap_accumulation_bonus=10` + 5 |
| close > VWAP | **+10** | `vwap_accumulation_bonus=10` |
| close == VWAP | **0** | — (neutral) |
| close < VWAP | **-5** | `vwap_distribution_penalty=-5` |

#### Options Flow — Front-Month DTE Filter (BC12)

```
max_dte = config.tuning["gex_max_dte"]  (90)

Minden opció szűrve: expiration_date - today <= max_dte
  Ha rossz dátum formátum → include (graceful fallback)
  Ha szűrés után < 5 kontraktus → összes opció használva (fallback)
```

A DTE filter alkalmazva a PCR, OTM ratio és dp_pct számításokra is.

#### PCR (Put/Call Ratio) Score (BC9)

```
puts = count(options ahol type == "put" ÉS DTE ≤ 90)
calls = count(options ahol type == "call" ÉS DTE ≤ 90)
PCR = puts / calls
```

| PCR | Score | Konfig |
|-----|-------|--------|
| < 0.7 (bullish) | **+15** | `pcr_bullish_threshold=0.7`, `pcr_bullish_bonus=15` |
| > 1.3 (bearish) | **-10** | `pcr_bearish_threshold=1.3`, `pcr_bearish_penalty=-10` |
| 0.7–1.3 | **0** | — |

#### OTM Call Ratio Score (BC9)

```
otm_calls = count(call options ahol strike > current_price ÉS DTE ≤ 90)
total_calls = count(call options ahol DTE ≤ 90)
otm_ratio = otm_calls / total_calls

ha otm_ratio > 0.4 → +10
```

- Konfig: `otm_call_ratio_threshold=0.4`, `otm_call_bonus=10`

#### Block Trade Score (BC9)

```
block_trade_count = count(dp_records ahol notional ≥ $500K)
```

| Block Trades | Score | Konfig |
|-------------|-------|--------|
| > 20 | **+15** | `block_trade_very_high=20`, `block_trade_very_high_bonus=15` |
| > 5 | **+10** | `block_trade_significant=5`, `block_trade_significant_bonus=10` |
| ≤ 5 | **0** | — |

#### Flow Sub-Score

```
flow_score = 50 + rvol_score + squat_bonus
           + dp_pct_score + buy_pressure_score + vwap_score
           + pcr_score + otm_score + block_trade_score

flow_score = min(100, max(0, flow_score))    ← cap [0, 100]
```

Tartomány: **0–100** (cap alkalmazva)

---

### 4.3 Fundamental Scoring

#### Metrikák és Küszöbök

| Metrika | Jó küszöb | Rossz küszöb | Bónusz | Büntetés |
|---------|-----------|-------------|--------|----------|
| Revenue Growth YoY | > 10% | < -10% | +5 | -5 |
| EPS Growth YoY | > 15% | < -15% | +5 | -5 |
| Net Margin | > 15% | < 0% | +5 | -5 |
| ROE | > 15% | < 5% | +5 | -5 |
| Debt/Equity | < 0.5 | > 2.0 | +5 | **-10** |
| Interest Coverage | — | < 1.5 | — | **-10** |

- Alap bónusz/büntetés: `funda_score_bonus=5`, `funda_score_penalty=-5`
- Debt büntetés erősebb: `funda_debt_penalty=-10`
- Revenue/EPS küszöbök %-ban vannak a config-ban, de a kód `/100`-zal konvertálja

#### Insider Activity

```
30 napos lookback, FMP insider-trading adatból:
  "A" (Acquisition) → +1
  "D" (Disposition) → -1

net_score = sum(transactions)
```

#### Insider Multiplier

```
ha net_score > 3  → 1.25 (erős vétel)
ha net_score < -3 → 0.75 (erős eladás)
egyébként         → 1.0
```

- Konfig: `insider_lookback_days=30`, `insider_strong_buy_threshold=3`, `insider_strong_sell_threshold=-3`
- Konfig: `insider_buy_multiplier=1.25`, `insider_sell_multiplier=0.75`

#### Shark Detector (BC9)

```
_detect_shark(insider_data):
  recent_buys = acquisitions az elmúlt 10 napban
  unique_buyers = egyedi insider nevek száma
  total_value = sum(tranzakció értékek)

  ha unique_buyers >= 2 ÉS total_value >= $100,000:
    shark_detected = True → +10 funda bonus
```

- Konfig: `shark_min_unique_insiders=2`, `shark_lookback_days=10`, `shark_min_total_value=100000`, `shark_score_bonus=10`
- `FundamentalScoring.shark_detected` mező → SHARK flag a trade_plan CSV-ben

#### Institutional Ownership Trend (BC12)

```
FMP /stable/institutional-ownership/latest (symbol={ticker}, limit=2)

Graceful degradation:
  AAPL probe a ticker loop előtt
  Ha 404 / None → inst_ownership_available=False → skip minden további hívás

Ha 2+ negyedév adat:
  recent = inst_data[0]["totalInvested"]
  previous = inst_data[1]["totalInvested"]
  change_pct = (recent - previous) / previous

  Ha change_pct > +2%  → "increasing" → +10 funda
  Ha change_pct < -2%  → "decreasing" → -5 funda
  Egyébként            → "stable"     → 0
```

- `FundamentalScoring.inst_ownership_trend`: "increasing" / "decreasing" / "stable" / "unknown"
- `FundamentalScoring.inst_ownership_score`: +10 / -5 / 0

#### Funda Sub-Score

```
funda_score = 50 + (metrika adjustmentek összege) + shark_bonus + inst_ownership_score
```

Tartomány: 50 + (-40 to +25) + 10 + 10 = **10–95**

---

### 4.4 Combined Score Képlet

```
tech_score  = rsi_ideal + sma50 + rs_spy           (0–100)
flow_score  = min(100, max(0, 50 + flow_adj))      (0–100)
funda_score = 50 + funda_adjustments                (10–95)

combined = 0.40 × flow_score
         + 0.30 × funda_score
         + 0.30 × tech_score
         + sector_adjustment

combined *= insider_multiplier
```

- `sector_adjustment` = `SectorScore.score_adjustment - SectorScore.breadth_score_adj` (breadth adj kiszűrve — BC14)
- Konfig: `weight_flow=0.40`, `weight_fundamental=0.30`, `weight_technical=0.30`

#### Tipikus Combined Score Példák

| Eset | Flow | Funda | Tech | Sector | Insider | Combined |
|------|------|-------|------|--------|---------|----------|
| Átlagos (nincs signal) | 50 | 50 | 0 | 0 | 1.0 | 35.0 |
| Jó RVOL + jó funda + RSI ideal | 65 | 65 | 30 | +15 | 1.0 | 69.5 |
| Max flow + leader + SMA50+RS | 100 | 65 | 100 | +15 | 1.0 | 104.5 |
| Shark + strong insider | 80 | 75 | 60 | +15 | 1.25 | **106.3** |
| Rossz funda + laggard | 50 | 30 | 0 | -20 | 0.75 | 12.0 |

---

### 4.5 Szűrők

| Szűrő | Feltétel | Konfig | Hatás |
|--------|----------|--------|-------|
| **SMA200 Trend** | LONG: price <= SMA200 | `sma_long_period=200` | Kizár (tech_filter) |
| **Danger Zone** | D/E>5 + margin<-10% + IC<1.0 (2+) | `danger_zone_*` (TUNING) | Kizár (danger_zone) |
| **Minimum Score** | combined < 70 | `combined_score_minimum=70` | Kizár (min_score) |
| **Clipping** | combined > 95 | `clipping_threshold=95` | Kizár (crowded trade) |
| **Insufficient Data** | < 50 bár | Hardcoded | Skip (nincs analysis) |

---

## Phase 5 — GEX Analysis + OBSIDIAN MM

**Forrás**: `src/ifds/phases/phase5_gex.py`, `src/ifds/phases/phase5_obsidian.py`, `src/ifds/data/adapters.py`

### Mit csinál?

Gamma Exposure elemzés a Phase 4-ből átjutott tickerekre (top 100), opcionálisan OBSIDIAN MM mikrostruktúra diagnózissal kiegészítve (BC15).

**Input**: list[StockAnalysis] (top 100 by combined_score), UW per-strike GEX / Polygon options chain, Polygon client (OBSIDIAN-hoz)
**Output**: `Phase5Result` → `list[GEXAnalysis]` regime-mel és multiplierrel, `list[ObsidianAnalysis]` (ha enabled/collect)

### Adatforrás — Fallback Lánc

```
FallbackGEXProvider:
  1. UWGEXProvider (elsődleges)
     → GET /api/stock/{symbol}/greek-exposure/strike
     → Pre-computed dollar GEX per strike
     → call_gamma (pozitív), put_gamma (negatív) — stringek!
     → source: "unusual_whales"

  2. PolygonGEXProvider (fallback)
     → GET /v3/snapshot/options/{symbol}
     → Nyers options chain → gamma × OI × 100 × spot² × 0.01
     → DTE filter: ≤90 DTE kontraktusok (BC12)
     → source: "polygon_calculated"
```

### DTE Filter (BC12)

```
Polygon GEX számításnál:
  max_dte = config.tuning["gex_max_dte"]  (90)

  Minden opció szűrve: expiration_date - today <= max_dte
    Ha rossz dátum formátum → include (graceful)
    Ha szűrés után < 5 kontraktus → összes opció használva (fallback)
```

- UW adatnál nincs DTE filter (UW már pre-filterel)
- Konfig: `gex_max_dte=90`

### GEX Számítás

#### UW útvonal (elsődleges)
Az UW per-strike endpoint **pre-computed dollar GEX** értékeket ad:
```
call_gamma, put_gamma = _safe_float(string) konverzió
net_gex_per_strike = call_gamma + put_gamma  (put_gamma már negatív)
```

#### Polygon útvonal (fallback)
```
Minden kontraktus:
  gex = Gamma × OpenInterest × 100 × Spot² × 0.01
  ha call: gex_by_strike[strike] += gex
  ha put:  gex_by_strike[strike] -= gex    ← signed (BC12 fix)
```

- **GEX Sign Fix (BC12)**: Put GEX **kivonva** a gex_by_strike-ból (korábban hozzáadva → hamis NEGATIVE regime mindenhol)
- Konfig: `gex_contract_size=100`, `gex_normalization_factor=0.01`

### Aggregált GEX Értékek (mindkét útvonal)

```
net_gex    = sum(gex_by_strike.values())        [UW]
             sum(call_gex) - sum(put_gex)        [Polygon]
call_wall  = strike ahol a call GEX maximális
put_wall   = strike ahol a |put GEX| maximális
zero_gamma = _find_zero_gamma(gex_by_strike)
```

### Zero Gamma Lineáris Interpoláció (BC12)

```
_find_zero_gamma(gex_by_strike):
  ha üres → return 0.0

  cumulative = 0.0
  prev_strike = 0.0

  Minden strike (rendezett):
    prev_cum = cumulative
    cumulative += gex_by_strike[strike]

    Ha előjel-váltás: (prev_cum < 0 ÉS cumulative >= 0)
                  VAGY (prev_cum > 0 ÉS cumulative <= 0):

      denom = cumulative - prev_cum
      ha denom ≠ 0 ÉS prev_strike > 0:
        zero = prev_strike + (strike - prev_strike) × (-prev_cum / denom)
        return round(zero, 2)    ← interpolált érték
      return strike              ← fallback: exact strike

  return 0.0   ← nincs crossover (safe default: POSITIVE regime)
```

- `zero_gamma=0.0` → `_classify_gex_regime` returns POSITIVE (safe default)
- Megosztott függvény: `adapters.py`-ban definiálva, `async_adapters.py` importálja

### Call Wall ATR Filter (BC12)

```
Phase 5 loop-ban (sync és async):
  atr = stock.technical.atr_14
  max_dist = config.tuning["call_wall_max_atr_distance"]  (5.0)

  ha call_wall > 0 ÉS atr > 0:
    ha |call_wall - current_price| > atr × max_dist:
      call_wall = 0.0    ← túl messze → TP1 ATR fallback Phase 6-ban
```

- Konfig: `call_wall_max_atr_distance=5.0`
- Hatás: Phase 6-ban `TP1 = entry + 2 × ATR` (ATR fallback) call_wall helyett

### GEX Regime Klasszifikáció

```
_classify_gex_regime(current_price, zero_gamma, net_gex):

  ha zero_gamma <= 0:         → POSITIVE (nincs adat)

  distance_pct = |price - zero_gamma| / zero_gamma × 100

  ha distance_pct <= 2.0:     → HIGH_VOL (átmeneti zóna)
  ha price > zero_gamma ÉS net_gex > 0: → POSITIVE
  ha price < zero_gamma:      → NEGATIVE
  egyébként:                  → HIGH_VOL (price > ZG de net_gex <= 0)
```

### GEX Multiplier

| Regime | Multiplier | Konfig kulcs |
|--------|-----------|--------------|
| POSITIVE | **1.0** | `gex_positive_multiplier` |
| HIGH_VOL | **0.6** | `gex_high_vol_multiplier` |
| NEGATIVE | **0.5** | `gex_negative_multiplier` |

### GEX Filter (csak LONG)

```
Ha regime == NEGATIVE ÉS strategy == LONG:
  ticker KIZÁRVA (excluded=True, reason="negative_gex_long")
```

### Nincs GEX adat esetén

```
Ha sem UW, sem Polygon nem ad adatot:
  regime = POSITIVE (default)
  multiplier = 1.0
  data_source = "none"
  ticker ÁTMEGY
```

### OBSIDIAN MM — Market Microstructure Diagnostic (BC15)

**Forrás**: `src/ifds/phases/phase5_obsidian.py`, `src/ifds/data/obsidian_store.py`

OBSIDIAN a 3-regime GEX multipliert (POSITIVE/NEGATIVE/HIGH_VOL) lecseréli 7-regime mikrostruktúra diagnózisra. A GEX strukturális adatok (call_wall, put_wall, zero_gamma) megmaradnak a Phase 6 TP targetekhez.

#### Aktiváció

```
obsidian_enabled = False (default) → GEX-only mód (BC14 kompatibilis)
obsidian_store_always_collect = True → feature store akkumuláció MINDIG fut
```

- Ha `obsidian_enabled=False` ÉS `always_collect=True`: GEX multiplier használva, de feature store írva (cold start eliminálás)
- Ha `obsidian_enabled=True`: OBSIDIAN multiplier felülírja `gex_analysis.gex_multiplier`-t

#### Feature Extraction (no new API calls)

| Feature | Forrás | Típus |
|---------|--------|-------|
| DarkShare | `flow.dark_pool_pct / 100` | Microstructure (store) |
| GEX | `gex_data["net_gex"]` | Microstructure (store) |
| DEX | Polygon options `Σ(delta × OI × 100)` call - put | Microstructure (store) |
| Block Intensity | `flow.block_trade_count` | Microstructure (store) |
| IV Rank | Polygon options ATM IV (strike ±5% of price) | Microstructure (store) |
| Efficiency | `(H - L) / V` from bars (250d) | Price-based (bars) |
| Impact | `|C - O| / V` from bars (250d) | Price-based (bars) |
| Daily Return | `(C - C_prev) / C_prev` | Price-based (bars) |
| Venue Mix | ✗ NOT available (permanently excluded) | — |

#### Feature Store

```
state/obsidian/{TICKER}.json — per-ticker JSON array
  [{date, dark_share, gex, dex, block_count, iv_rank, efficiency, impact, daily_return, raw_score}, ...]

Max 100 entry, atomic write (tempfile + os.replace)
Date dedup: ugyanaz a dátum → replace
```

#### Z-Score Számítás

```
Price features (Efficiency, Impact):
  Z = (X_today - mean(bar_series[-63:])) / std(bar_series[-63:])
  → 250 bar elérhető Day 1 → z-score AZONNAL aktív

Microstructure features (GEX, DEX, DarkShare, Block, IV):
  Z = (X_today - mean(store_history[-63:])) / std(store_history[-63:])
  → min_periods = 21 kell → z-score CSAK ~21 futás után aktív
  → std == 0 → z_score = None (skip)
```

#### Baseline State

```
EMPTY:    nincs store history → UND regime
PARTIAL:  néhány feature-nek van z-score, néhánynak nincs
COMPLETE: minden feature-nek van ≥ min_periods history
```

#### 8 Regime Klasszifikáció (prioritás sorrend — első match nyer)

| # | Regime | Szabály | Multiplier |
|---|--------|---------|-----------|
| 0 | **VOLATILE** (BC16) | σ_gex > 2× median ÉS σ_dex > 2× median | **0.60** |
| 1 | **Γ⁺** (gamma_positive) | Z_GEX > +1.5 ÉS efficiency < median(63d) | **1.50** |
| 2 | **Γ⁻** (gamma_negative) | Z_GEX < -1.5 ÉS impact > median(63d) | **0.25** |
| 3 | **DD** (dark_dominant) | dark_share > 0.70 ÉS Z_block > +1.0 | **1.25** |
| 4 | **ABS** (absorption) | Z_DEX < -1.0 ÉS return ≥ -0.5% ÉS dark_share > 0.50 | **1.00** |
| 5 | **DIST** (distribution) | Z_DEX > +1.0 ÉS return ≤ +0.5% | **0.50** |
| 6 | **NEU** (neutral) | Nincs szabály match | **1.00** |
| 7 | **UND** (undetermined) | Baseline EMPTY | **0.75** |

- VOLATILE fires first — factor volatility framework (BC16), needs `factor_volatility_enabled=True`
- Γ⁻ + LONG → ticker KIZÁRVA (replaces GEX NEGATIVE exclusion)
- Konfig: `obsidian_regime_multipliers` dict TUNING-ban

#### Factor Volatility Framework (BC16)

```
factor_volatility_enabled = False (default)

_compute_factor_volatility(entries, window=20):
  → rolling σ per feature (gex, dex, dark_share, block_count, iv_rank)
  → Returns {feature: σ_value_or_None}

_compute_median_rolling_sigmas(entries, window=20):
  → median of rolling σ windows across history
  → Returns {feature: median_σ}

_compute_regime_confidence(factor_vol, median_sigmas, floor=0.6):
  → confidence = 1.0 - min(1.0, σ_gex / median_σ_gex)
  → max(floor, confidence)
  → Missing data → 1.0 (assume stable)

Final multiplier = base_regime_mult × max(floor, confidence)
```

- VOLATILE trigger: `σ_gex > 2× median_σ_gex` ÉS `σ_dex > 2× median_σ_dex`
- Unusualness σ_20 weighting: `S = Σ(w × |z| × (1 + σ_20_norm))` — volatile features amplified
- Konfig: `factor_volatility_enabled=False`, `factor_volatility_window=20`, `factor_volatility_confidence_floor=0.6`

#### Unusualness Score

```
S = Σ(w_k × |z_k|) ahol k = valid features (venue_mix excluded)
U = PercentileRank(S | historical raw_scores) × 100
Ha nincs history: U = min(S × 20, 100) (linear mapping)
```

- U ∈ [0, 100], stored on PositionSizing.unusualness_score
- Max effective weight = 0.80 (venue_mix 0.20 excluded, NO renormalization)

#### Cold Start Viselkedés

```
Day 1-20: Baseline EMPTY → UND (mult 0.75)
  Price features (efficiency, impact) z-score aktív (250 bars)
  Microstructure features z-score = None
  DD rule tüzelhet (absolute dark_share > 0.70 threshold)

Day 21+: Baseline PARTIAL/COMPLETE → full classification
  Minden z-score aktív → Γ⁺/Γ⁻/ABS/DIST rules tüzelhetnek
```

#### Async OBSIDIAN (Phase 5 async path)

```
async_enabled=True → _run_phase5_async(run_obsidian=True):

  Phase 1: GEX gather (concurrent)
    → asyncio.gather(*[gex_provider.get_gex(ticker) for ticker in top100])

  Phase 2: OBSIDIAN data gather (concurrent)
    → asyncio.gather(*[polygon.get_aggregates(ticker, 365d) + get_options_snapshot(ticker)])
    → obs_data_map: {ticker: (bars, options)}

  Phase 3: Sync processing loop
    → GEX classify + OBSIDIAN run_obsidian_analysis() per ticker
    → Feature store write, multiplier override, exclusion logic

  FileCache wired: AsyncPolygonClient(cache=file_cache)
    → Reuses Phase 4 cached bars/options when available
```

---

## Phase 6 — Position Sizing & Risk Management

**Forrás**: `src/ifds/phases/phase6_sizing.py`

### Mit csinál?

Scored kandidátokat méretezett pozíciókká alakít: kockázat, darabszám, SL/TP szintek.

**Input**: list[StockAnalysis] + list[GEXAnalysis] + MacroRegime + config
**Output**: `Phase6Result` → `list[PositionSizing]` + `execution_plan.csv`

---

### 6.0 Signal Deduplication (BC11)

```
SignalDedup (src/ifds/data/signal_dedup.py):

  Hash: SHA256(ticker|direction|date)[:16]
  State file: state/signal_hashes.json
  TTL: 24 óra

  Phase 6 elején:
    Betöltés → lejárt hashek törlése
  Minden ticker:
    Ha hash létezik → SKIP (excluded_dedup += 1)
    Ha új → sizing után hash rögzítve
  Phase 6 végén:
    State mentése
```

- Konfig: `signal_hash_file="state/signal_hashes.json"`
- `Phase6Result.excluded_dedup`: kizárt tickerek száma

### 6.0b Max Daily Trades (BC13)

```
_load_daily_counter("state/daily_trades.json"):
  → {"date": "2026-02-11", "count": 7}
  → Ha date != today → reset count = 0

Phase 6 ciklusban (dedup UTÁN, sizing ELŐTT):
  Ha daily_trades["count"] >= max_daily_trades (20):
    → "[GLOBALGUARD] Daily trade limit reached (20/20), skip remaining"
    → daily_trade_excluded += 1
    → continue
```

- Konfig: `max_daily_trades=20`, `daily_trades_file="state/daily_trades.json"`
- `Phase6Result.excluded_daily_trade_limit`: kizárt tickerek száma
- State mentés Phase 6 végén: `_save_daily_counter()`

### 6.0c Notional Limits (BC13)

```
Per-pozíció notional cap:
  pos_notional = quantity × entry_price
  Ha pos_notional > max_position_notional ($25,000):
    capped_qty = floor(max_position_notional / entry_price)
    → "[GLOBALGUARD] Position notional capped: NVDA $38000 → $25000"
    → _replace_quantity(pos, capped_qty)

Napi összesített notional cap:
  Ha daily_notional["count"] + pos_notional > max_daily_notional ($200,000):
    → "[GLOBALGUARD] Daily notional limit reached: $185000/$200000"
    → notional_excluded += 1
    → continue
```

- Konfig: `max_daily_notional=200000`, `max_position_notional=25000`, `daily_notional_file="state/daily_notional.json"`
- `Phase6Result.excluded_notional_limit`: kizárt tickerek száma
- Sorrend: dedup → daily trade limit → sizing → notional cap → position limits

### 6.0d Telegram Unified Daily Report (BC13+BC15)

```
Pipeline végén (runner.py):
  duration = time.monotonic() - pipeline_t0
  try:
    send_daily_report(ctx, config, logger, duration)
  except:
    logger.log(CONFIG_WARNING, "Telegram error: ...")

Hiba esetén:
  send_failure_report(error, config, logger, duration)

send_daily_report():
  Ha token és chat_id nincs → return False (disabled)
  Egyetlen üzenet: BMI, sectors, breadth, scanned, GEX, OBSIDIAN stats, exec plan
  Szektortábla: 11 SPDR szektor + AGG benchmark sor szeparátorral (ctx.agg_benchmark)
  POST https://api.telegram.org/bot{token}/sendMessage
    → HTML format, max 4 ticker/sor az exec planben
    → timeout=5s

send_failure_report():
  🚨 IFDS FAILED — {date}
  Error: `{error}`
  Duration: {duration}s
```

- Konfig: `telegram_bot_token=None`, `telegram_chat_id=None`, `telegram_timeout=5`
- Non-blocking: exception → log, soha nem állítja meg a pipeline-t
- Per-phase timing: `time.monotonic()` minden phase előtt/után, PHASE_DIAGNOSTIC log

---

### 6.1 Freshness Alpha (opcionális, pandas szükséges)

```
Ha a ticker NEM szerepel az elmúlt 90 nap signal_history.parquet-jában:
  combined_score = original_score × 1.5 (freshness bonus, UNCAPPED)
```

- **Uncapped**: `combined_score` mehet 100 fölé (max: 95 × 1.5 = 142.5) — a clipping (95) már szűrt előtte
- Korábban `min(100.0, ...)` cap volt → üres history-val minden ticker FRESH → azonos 100 → M_utility differenciálatlan
- Konfig: `freshness_lookback_days=90`, `freshness_bonus=1.5`
- History file: `state/signal_history.parquet`
- Ha pandas nincs telepítve: freshness kihagyva (6 teszt skipped)

---

### 6.2 Multiplier-ek (6 db)

#### M_flow — Flow Strength

```
flow_score = stock.flow.rvol_score (composite — includes all flow bonuses)

ha flow_score > 80 → M_flow = 1.25
egyébként          → M_flow = 1.0
```

- Konfig: `multiplier_flow_threshold=80`, `multiplier_flow_value=1.25`

#### M_insider — Insider Activity

```
M_insider = stock.fundamental.insider_multiplier
  = 1.25 (net_score > 3)
  = 0.75 (net_score < -3)
  = 1.0  (egyébként)
```

#### M_funda — Fundamental Quality

```
funda_score = 50 + stock.fundamental.funda_score

ha funda_score < 60 → M_funda = 0.50 (gyenge fundamentumok → félméret)
egyébként           → M_funda = 1.0
```

- Konfig: `multiplier_funda_threshold=60`, `multiplier_funda_value=0.50`
- funda_score < 60 azt jelenti, hogy funda_adjustments < +10 (nincsenek pozitív jelek)

#### M_gex — GEX Regime

```
M_gex = gex.gex_multiplier
  = 1.0 (POSITIVE)
  = 0.6 (HIGH_VOL)
  = 0.5 (NEGATIVE)
```

#### M_vix — Macro Volatility

```
M_vix = macro.vix_multiplier
  = 0.10 (VIX > 50, EXTREME — BC12)
  = 1.0  (VIX <= 20)
  = max(0.25, 1.0 - (VIX - 20) × 0.02)  (VIX > 20)
```

#### M_utility — Score-Based Bonus

```
ha combined_score > 85:
  M_utility = min(1.3, 1.0 + (combined_score - 85) / 100)
egyébként:
  M_utility = 1.0
```

- Konfig: `multiplier_utility_threshold=85`, `multiplier_utility_max=1.3`
- Példa: score=90 → M_utility = 1.05, score=95 → M_utility = 1.1

#### M_total Képlet

```
M_total = M_flow × M_insider × M_funda × M_gex × M_vix × M_utility
M_total = clamp(M_total, 0.25, 2.0)
```

#### Multiplier Példák

| Eset | M_flow | M_insider | M_funda | M_gex | M_vix | M_util | M_total |
|------|--------|-----------|---------|-------|-------|--------|---------|
| Ideális | 1.25 | 1.25 | 1.0 | 1.0 | 1.0 | 1.1 | 1.72 |
| Átlagos | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | **1.0** |
| Magas VIX | 1.0 | 1.0 | 1.0 | 1.0 | 0.6 | 1.0 | 0.6 |
| VIX EXTREME | 1.0 | 1.0 | 1.0 | 1.0 | **0.10** | 1.0 | **0.10→0.25** |
| Rossz funda + neg GEX | 1.0 | 1.0 | 0.5 | 0.5 | 1.0 | 1.0 | **0.25** |
| Insider sell + high vol | 1.0 | 0.75 | 1.0 | 0.6 | 0.8 | 1.0 | 0.36 |

---

### 6.3 Position Sizing Képlet

```
base_risk = account_equity × risk_per_trade_pct / 100
          = 100,000 × 0.5 / 100
          = $500

adjusted_risk = base_risk × M_total

stop_distance = stop_loss_atr_multiple × ATR14
              = 1.5 × ATR14

quantity = floor(adjusted_risk / stop_distance)
```

- Konfig: `account_equity=100000`, `risk_per_trade_pct=0.5`, `stop_loss_atr_multiple=1.5`

#### Fat Finger Protection (BC12)

```
_calculate_position() védelmek:

  1. NaN guard: ha not (atr > 0) → return None
     (NaN összehasonlítás mindig False → fogja)

  2. Max quantity cap:
     quantity = min(quantity, max_order_quantity)      (5000)

  3. Max value cap:
     max_value_qty = floor(max_single_ticker_exposure / entry)
     quantity = min(quantity, max_value_qty)           ($20,000 / entry)

  4. Ha quantity <= 0 → return None
```

- Konfig: `max_order_quantity=5000` (RUNTIME), `max_single_ticker_exposure=20000` (RUNTIME)

#### Példa

```
ATR14 = $0.48, M_total = 1.0, entry = $45.00

base_risk = $500
adjusted_risk = $500 × 1.0 = $500
stop_distance = 1.5 × $0.48 = $0.72
quantity = floor($500 / $0.72) = 694 db

Fat finger checks:
  694 < 5000 → OK (max qty)
  694 × $45 = $31,230 > $20,000 → reduced: floor($20,000 / $45) = 444 db
```

---

### 6.4 Stop-Loss és Take-Profit Szintek

#### LONG Pozíció

| Szint | Képlet | Konfig |
|-------|--------|--------|
| **Stop Loss** | `entry - 1.5 × ATR14` | `stop_loss_atr_multiple=1.5` |
| **TP1** | `call_wall` (ha > entry), egyébként `entry + 2 × ATR14` | `tp1_atr_multiple=2.0` |
| **TP2** | `entry + 3 × ATR14` | `tp2_atr_multiple=3.0` |
| **Scale-out** | `entry + 2 × ATR14` → 33% pozíció zárása | `scale_out_atr_multiple=2.0`, `scale_out_pct=0.33` |

- **TP1 megjegyzés**: Ha call_wall ATR filterrel nullázva (BC12), automatikusan ATR fallback

#### SHORT Pozíció

| Szint | Képlet |
|-------|--------|
| **Stop Loss** | `entry + 1.5 × ATR14` |
| **TP1** | `put_wall` (ha < entry), egyébként `entry - 2 × ATR14` |
| **TP2** | `entry - 3 × ATR14` |
| **Scale-out** | `entry - 2 × ATR14` → 33% zárás |

---

### 6.5 Position Limits (prioritás sorrendben)

A pozíciók combined_score desc rendezettek — a legjobb score-ú kap helyet először.

| # | Limit | Érték | Konfig kulcs | Hatás |
|---|-------|-------|-------------|-------|
| 1 | Max pozíció szám | **8** | `max_positions` | Skip (position_limit) |
| 2 | Max pozíció/szektor | **3** | `max_positions_per_sector` | Skip (sector_limit) |
| 3 | Max egyedi kockázat | **1.5%** equity ($1,500) | `max_single_position_risk_pct` | Skip (risk_limit) |
| 4 | Max bruttó kitettség | **$100,000** | `max_gross_exposure` | Skip (exposure_limit) |
| 5 | Max ticker kitettség | **$20,000** | `max_single_ticker_exposure` | **Csökkenti a quantity-t** |

Az 5. limit nem kizárja a tickert, hanem csökkenti a darabszámot:
```
ha quantity × entry_price > $20,000:
  reduced_qty = floor($20,000 / entry_price)
```

### 6.6 GlobalGuard Logging (BC11)

```
Exposure elutasítások logolva `[GLOBALGUARD]` prefix-szel:
  Gross exposure: "[GLOBALGUARD] {ticker} removed: gross exposure ${X} > ${Y}"
  Single ticker:  "[GLOBALGUARD] {ticker} reduced: exposure ${X} > ${Y}"
```

---

## Teljes Pipeline Folyam

```
Phase 0: Diagnostics
  │ API health ✓, Per-provider Circuit Breaker (CB) init
  │ VIX (Polygon → FRED → default 20.0) → sanity [5–100] → regime + multiplier
  │ VIX > 50 → EXTREME (0.10 multiplier)
  │ TNX → rate sensitivity flag
  ↓
Phase 1: BMI (async: BC16, semaphore: polygon=10)
  │ 75 nap Polygon grouped daily (330 nap ha breadth enabled — BC14)
  │ Volume spike → Big Money B/S ratio → SMA25
  │ BMI <= 25: GREEN → LONG
  │ BMI >= 80: RED → SHORT
  │ Per-sector BMI (FMP sector mapping)
  ↓ StrategyMode + sector_bmi_values + grouped_daily_bars (BC14)
Phase 2: Universe
  │ FMP screener → ~3000 (LONG) / ~200 (SHORT) ticker
  │ Earnings exclusion (2-pass: bulk calendar + per-ticker) → kizár ha <7 napra earnings
  ↓ list[Ticker]
Phase 3: Sector Rotation
  │ 11 ETF × Polygon OHLCV
  │ 5d momentum → rank → Leader/Neutral/Laggard
  │ Per-sector BMI → Oversold/Neutral/Overbought regime
  │ Sector Breadth (BC14): FMP ETF holdings → SMA20/50/200 %-above
  │   → 7 regime (STRONG/EMERGING/CONSOLIDATING/NEUTRAL/WEAKENING/WEAK/RECOVERY)
  │   → Score adj: +5 (strong), -5 (weak), -15 (very weak), -10 (bearish divergence)
  │ Vétó mátrix (LONG): Laggard+Neutral/OB → VÉTÓ
  │ TNX rate sensitivity → Tech/RE -10
  ↓ list[SectorScore] + vetoed sectors
Phase 4: Stock Analysis (szinkron: ~12 min, async: ~2 min, semaphore: polygon=10, fmp=8, uw=5, max_tickers=10)
  │ Per ticker: Polygon bars + FMP funda + UW dark pool + Polygon options
  │ Technical: SMA200 filter, RSI ideal zone (+30), SMA50 (+30), RS vs SPY (+40)
  │ Flow: RVOL + squat + dp_pct + buy_pressure + VWAP + PCR + OTM + block
  │        DTE filter (≤90), flow cap [0, 100]
  │ Fundamental: 6 metrika + insider + shark detector + inst ownership
  │ Combined = 0.40×flow + 0.30×funda + 0.30×tech + sector_adj × insider_mult
  │ Szűrők: SMA200, min_score=70, clipping=95
  ↓ list[StockAnalysis] (passed, score 70–95)
Phase 5: GEX + OBSIDIAN MM
  │ Top 100 ticker × UW per-strike GEX (→ Polygon fallback, DTE ≤90)
  │ Per-strike GEX → net_gex, call_wall, put_wall, zero_gamma (interpolált)
  │ Put GEX signed (negatív — BC12 fix)
  │ Call wall ATR filter: |CW - price| > 5×ATR → zeroed
  │ GEX Regime: POSITIVE (1.0) / HIGH_VOL (0.6) / NEGATIVE (0.5)
  │ OBSIDIAN MM (BC15+BC16, ha enabled/always_collect):
  │   Feature extraction → z-score → 8-regime classification
  │   VOLATILE(0.6)/Γ⁺(1.5)/Γ⁻(0.25)/DD(1.25)/ABS(1.0)/DIST(0.5)/NEU(1.0)/UND(0.75)
  │   Override: gex_multiplier ← obsidian_regime_multiplier
  │   Γ⁻ + LONG → KIZÁR (replaces NEGATIVE exclusion)
  │   Feature store always accumulates (cold start elimination)
  ↓ list[GEXAnalysis] + list[ObsidianAnalysis]
Phase 2: Universe (cont.)
  │ Survivorship Bias (BC13): universe snapshot mentés + diff logging
  ↓
Phase 6: Position Sizing
  │ Stock ⋈ GEX inner join
  │ Signal dedup (SHA256, 24h TTL — BC11)
  │ Max daily trades limit (20 — BC13)
  │ Freshness Alpha (opcionális, ×1.5, uncapped — score mehet 100+)
  │ M_total = M_flow × M_insider × M_funda × M_gex × M_vix × M_utility
  │ quantity = floor(base_risk × M_total / (1.5 × ATR))
  │ Fat finger: NaN guard, max qty 5000, max value $20K (BC12)
  │ Notional cap: per-position $25K, daily $200K (BC13)
  │ SL/TP/Scale-out szintek
  │ Position limits (8 max, 3/szektor, $100K gross)
  │ [GLOBALGUARD] exposure logging
  ↓ execution_plan_{run_id}.csv
Telegram: Unified daily report (opcionális, non-blocking — BC15)
  │ Siker: BMI + sectors + breadth + scanned + GEX + OBSIDIAN + exec plan
  │ Hiba: 🚨 IFDS FAILED + error + duration
```

---

## SimEngine — Forward Validation (SIM-L1)

**Forrás**: `src/ifds/sim/`

### Mit csinál?

Execution plan CSV-kből bracket order szimulációt futtat historikus Polygon OHLCV adaton. Visszaméri a pipeline jelzések eredményességét.

**Input**: `output/execution_plan_*.csv` + Polygon daily bars
**Output**: Per-trade eredmények, összesített ValidationSummary, CSV + JSON export

### Architektúra (Level 1-3 tervezés)

```
Level 1 (KÉSZ): Forward Validation
  → Execution plan CSV-k beolvasása
  → Polygon bar fetch (async, FileCache)
  → Bracket order szimuláció
  → Aggregált statisztikák + export

Level 2 Mód 1 (KÉSZ — BC19): Parameter Sweep
  → Execution plan CSV-k beolvasása (egyszer)
  → Polygon bar fetch egyszer (megosztva variánsok között)
  → N variáns: deep copy + TP/SL override → szimuláció → összehasonlítás
  → Páros t-teszt (scipy) → p-value, szignifikancia

Level 2 Mód 2 (TERVEZETT — BC20): Re-score
  → Phase 4 snapshot betöltés → módosított config → újrascorolás
  → Cachelt API adatokból

Level 3 (TERVEZETT): Full Backtest
  → Multi-nap szekvenciális pipeline
  → Portfólió-szintű P&L tracking
```

### Bracket Order Szimuláció

```
broker_sim.simulate_bracket_order(trade, daily_bars, max_hold_days=10):

  1. Fill Check (D+1):
     LONG:  ha bars[1].low <= entry_price → filled @ entry_price
     SHORT: ha bars[1].high >= entry_price → filled @ entry_price
     Fill window: 1 nap (IBKR bot másnap cancel)

  2. Qty Split (IBKR logic):
     qty_tp1 = round(quantity × 0.33)    → 33% Leg 1
     qty_tp2 = quantity - qty_tp1         → 66% Leg 2

  3. Leg 1 (TP1/SL bracket):
     Minden bar D+2-től:
       ha low <= stop_loss → stop hit (leg1_exit_price = stop_loss)
       ha high >= tp1      → tp1 hit (leg1_exit_price = tp1)
       ha TP ÉS stop same day → conservative: stop hit

  4. Leg 2 (TP2/SL bracket):
     Ugyanaz mint Leg 1, de tp2 target

  5. Expired:
     Ha max_hold_days eltelt → exit @ utolsó bar close

  6. P&L:
     leg_pnl = (exit_price - entry_price) × qty  (LONG)
     total_pnl = leg1_pnl + leg2_pnl
     total_pnl_pct = total_pnl / (entry_price × quantity) × 100
```

### Validator Flow

```
validate_execution_plans(output_dir, polygon_api_key):
  1. load_execution_plans(output_dir) → list[Trade]
     → Minden execution_plan_*.csv beolvasva
     → run_date a filename-ből: run_YYYYMMDD_HHMMSS_hex
     → Mai dátumú CSV-k skip-pelve (nincs next-day bar)

  2. _fetch_bars_for_trades(trades, api_key)
     → Async Polygon fetch (semaphore=10, FileCache)
     → Per-ticker: entry_date - 1 nap → + max_hold_days + 5 nap

  3. Per-trade: simulate_bracket_order(trade, bars)

  4. aggregate_summary(trades) → ValidationSummary
     → Fill rate, leg1/leg2 TP/stop/expired, win rates
     → P&L: total, avg, best/worst ticker
     → Breakdowns: pnl_by_gex_regime, win_rate_by_score_bucket
```

### Report

```
print_validation_report(trades, summary):
  → Console output (colorama): fill rate, leg win rates, P&L, regime breakdown

write_validation_trades(trades, output_dir):
  → validation_trades.csv (28 oszlop)

write_validation_summary(summary, output_dir):
  → validation_summary.json
```

---

## SimEngine L2 — Parameter Sweep (BC19)

**Forrás**: `src/ifds/sim/replay.py`, `src/ifds/sim/comparison.py`

### Mit csinál?

Multi-variáns A/B teszt: ugyanazokat az execution plan trade-eket különböző TP/SL/hold paraméterekkel futtatja, és statisztikailag összehasonlítja az eredményeket.

**Input**: Execution plan CSV-k + Polygon bars + variant definíciók (YAML vagy CLI)
**Output**: `ComparisonReport` (delta metrikák + p-value), console report, CSV export

### ATR-Implied Recalculation

```
recalculate_bracket(trade, overrides, original_sl_atr_mult=1.5):
  ATR = (entry_price - stop_loss) / original_sl_atr_mult

  new_stop = entry - overrides["stop_loss_atr_multiple"] × ATR
  new_tp1  = entry + overrides["tp1_atr_multiple"] × ATR
  new_tp2  = entry + overrides["tp2_atr_multiple"] × ATR
```

- Guard: entry <= 0, stop <= 0, ATR <= 0 → nincs recalc
- A trade objektumot in-place módosítja (deep copy-n dolgozik)

### YAML Variáns Definíció

```yaml
variants:
  - name: baseline
    description: "Default 1.5/2.0/3.0 ATR config"
    overrides: {}
  - name: wide_stops
    description: "2× ATR stop, 3× TP1, 4× TP2"
    overrides:
      stop_loss_atr_multiple: 2.0
      tp1_atr_multiple: 3.0
      tp2_atr_multiple: 4.0
  - name: tight_exits
    description: "Tight stops, quick profit"
    overrides:
      stop_loss_atr_multiple: 1.0
      tp1_atr_multiple: 1.5
      tp2_atr_multiple: 2.0
      max_hold_days: 5
```

### Comparison Flow

```
run_comparison(variants, output_dir, polygon_api_key):
  1. load_execution_plans(output_dir) → base_trades
  2. _fetch_bars_once(base_trades, ...) → bars_by_ticker (egyszer)
  3. Minden variant-ra:
     a. deep_copy_trades(base_trades)
     b. recalculate_bracket(trade, variant.overrides) ha van override
     c. validate_trades_with_bars(trades, bars) → trades, summary
  4. compare_variants(variants) → ComparisonReport
```

### Páros t-teszt (Statisztikai Összehasonlítás)

```
compare_variants(variants):
  baseline = variants[0]
  challengers = variants[1:]

  Minden challenger-re:
    1. _pair_trade_pnls(baseline, challenger)
       → (ticker, run_date) match → paired P&L listák
    2. Ha len(pairs) < 30 → insufficient_data=True
    3. Ha len(pairs) ≥ 30 → scipy.stats.ttest_rel(base_pnls, chal_pnls)
       → p_value, is_significant = bool(p < 0.05)
```

- MIN_PAIRED_TRADES = 30 (statisztikai minimum)
- Csak `filled=True` trade-ek párosítva
- A p-value kerekítve 6 tizedesre

### CLI Használat

```bash
# YAML config
python -m ifds compare --config variants.yaml

# Inline override (baseline vs 1 challenger)
python -m ifds compare --challenger "wide_stops" --override-sl-atr 2.0 --override-tp1-atr 3.0

# Különböző output dir
python -m ifds compare --config variants.yaml --output-dir output --cache-dir data/cache
```

---

## Phase 4 Snapshot Persistence (BC19)

**Forrás**: `src/ifds/data/phase4_snapshot.py`

### Mit csinál?

Napi szinten menti a Phase 4 StockAnalysis adatokat gzipped JSON formátumban. Ez a SIM-L2 Mód 2 (re-score, BC20) előkészítése.

### Mentés

```
save_phase4_snapshot(passed_analyses, snapshot_dir):
  1. mkdir -p snapshot_dir
  2. Minden StockAnalysis → flat dict (_stock_to_dict):
     ticker, sector, combined_score, sector_adjustment,
     price, sma_200, sma_50, rsi_14, atr_14, rs_vs_spy,
     rvol, dark_pool_pct, pcr, block_trade_count, buy_pressure_score,
     revenue_growth_yoy, eps_growth_yoy, insider_score, inst_ownership_trend,
     ...
  3. gzip.open("{date}.json.gz", "wt") → json.dump(records)
```

- Idempotens: ugyanazon nap újraírja (felülírja)
- Dir automatikusan létrejön ha nem létezik

### Betöltés

```
load_phase4_snapshot(date_str, snapshot_dir):
  1. Keresés: "{date_str}.json.gz" → gzip.open
  2. Fallback: "{date_str}.json" → open
  3. Ha nem létezik → return []
```

### Pipeline Integration

```python
# runner.py — Phase 6 után, Telegram előtt:
if config.runtime.get("phase4_snapshot_enabled", True) and ctx.stock_analyses:
    save_phase4_snapshot(ctx.stock_analyses, snap_dir)
```

- Konfig: `phase4_snapshot_enabled=True`, `phase4_snapshot_dir="state/phase4_snapshots"`
- ~2-5 KB per nap (gzipped, ~8-15 ticker)

---

## Konfiguráció Referencia

### CORE (algoritmus konstansok — ne módosítsd)

| Kulcs | Érték | Használat |
|-------|-------|-----------|
| `bmi_volume_spike_sigma` | 2.0 | Volume spike detekció k-sigma |
| `bmi_sma_period` | 25 | BMI simítási periódus |
| `bmi_volume_avg_period` | 20 | Volume átlag lookback |
| `sma_long_period` | 200 | Trend filter |
| `sma_mid_period` | 50 | SMA50 bonus (BC9) |
| `sma_short_period` | 20 | Short-term SMA |
| `rsi_period` | 14 | RSI lookback |
| `atr_period` | 14 | ATR lookback |
| `gex_normalization_factor` | 0.01 | GEX formula |
| `gex_contract_size` | 100 | Options contract multiplier |
| `stop_loss_atr_multiple` | 1.5 | SL = entry ± 1.5×ATR |
| `tp1_atr_multiple` | 2.0 | TP1 = entry ± 2×ATR |
| `tp2_atr_multiple` | 3.0 | TP2 = entry ± 3×ATR |
| `scale_out_atr_multiple` | 2.0 | Scale-out trigger |
| `scale_out_pct` | 0.33 | 33% pozíció zárás |
| `sector_bmi_min_signals` | 5 | Min buy+sell/nap/szektor |
| `freshness_lookback_days` | 90 | Freshness alpha lookback |
| `freshness_bonus` | 1.5 | Score szorzó friss jelekre |
| `clipping_threshold` | 95 | Score > 95 = crowded |
| `weight_flow` | 0.40 | Flow súly a combined-ban |
| `weight_fundamental` | 0.30 | Funda súly |
| `weight_technical` | 0.30 | Tech súly |
| `breadth_sma_periods` | [20, 50, 200] | Breadth SMA periódusok (BC14) |
| `breadth_lookback_calendar_days` | 330 | Lookback ha breadth enabled (BC14) |
| `breadth_composite_weights` | (0.20, 0.50, 0.30) | SMA20/50/200 súlyok (BC14) |
| `obsidian_window` | 63 | Rolling baseline ablak (BC15) |
| `obsidian_min_periods` | 21 | Min observations z-score-hoz (BC15) |
| `obsidian_feature_weights` | {0.25, 0.25, 0.20, 0.15, 0.15} | Feature súlyok (BC15) |
| `obsidian_z_gex_threshold` | 1.5 | Γ⁺/Γ⁻ z-score küszöb (BC15) |
| `obsidian_z_dex_threshold` | 1.0 | ABS/DIST z-score küszöb (BC15) |
| `obsidian_z_block_threshold` | 1.0 | DD z-score küszöb (BC15) |
| `obsidian_dark_share_dd` | 0.70 | DD DarkShare küszöb (BC15) |
| `obsidian_dark_share_abs` | 0.50 | ABS DarkShare küszöb (BC15) |
| `obsidian_return_abs` | -0.005 | ABS return küszöb (BC15) |
| `obsidian_return_dist` | 0.005 | DIST return küszöb (BC15) |
| `factor_volatility_window` | 20 | Rolling σ ablak (BC16) |

### TUNING (operátor állítható)

| Kulcs | Érték | Használat |
|-------|-------|-----------|
| `bmi_green_threshold` | 25 | BMI <= 25 → GREEN |
| `bmi_red_threshold` | 80 | BMI >= 80 → RED |
| `combined_score_minimum` | 70 | Min combined score |
| `gex_positive_multiplier` | 1.0 | M_gex POSITIVE |
| `gex_negative_multiplier` | 0.5 | M_gex NEGATIVE |
| `gex_high_vol_multiplier` | 0.6 | M_gex HIGH_VOL |
| `vix_penalty_start` | 20 | VIX büntetés küszöb |
| `vix_penalty_rate` | 0.02 | Per VIX pont büntetés |
| `vix_multiplier_floor` | 0.25 | VIX multiplier minimum |
| `vix_extreme_threshold` | 50 | VIX EXTREME küszöb (BC12) |
| `vix_extreme_multiplier` | 0.10 | EXTREME multiplier (BC12) |
| `multiplier_flow_threshold` | 80 | M_flow trigger |
| `multiplier_flow_value` | 1.25 | M_flow boost |
| `multiplier_funda_threshold` | 60 | M_funda trigger |
| `multiplier_funda_value` | 0.50 | M_funda penalty |
| `multiplier_utility_threshold` | 85 | M_utility trigger |
| `multiplier_utility_max` | 1.3 | M_utility cap |
| `max_positions_per_sector` | 3 | Max pozíció/szektor |
| `pcr_bullish_threshold` | 0.7 | PCR bullish (BC9) |
| `pcr_bearish_threshold` | 1.3 | PCR bearish (BC9) |
| `pcr_bullish_bonus` | 15 | PCR bullish bonus (BC9) |
| `pcr_bearish_penalty` | -10 | PCR bearish penalty (BC9) |
| `otm_call_ratio_threshold` | 0.4 | OTM call ratio (BC9) |
| `otm_call_bonus` | 10 | OTM call bonus (BC9) |
| `block_trade_significant` | 5 | Block trade küszöb (BC9) |
| `block_trade_very_high` | 20 | Block trade magas (BC9) |
| `block_trade_significant_bonus` | 10 | Block bonus (BC9) |
| `block_trade_very_high_bonus` | 15 | Block nagy bonus (BC9) |
| `dp_pct_high_threshold` | 60 | dp_pct magas (BC10) |
| `dp_pct_bonus` | 10 | dp_pct > 40% bonus (BC10) |
| `dp_pct_high_bonus` | 15 | dp_pct > 60% bonus (BC10) |
| `buy_pressure_strong_bonus` | 15 | Buy pressure > 0.7 (BC10) |
| `buy_pressure_weak_penalty` | -15 | Buy pressure < 0.3 (BC10) |
| `vwap_accumulation_bonus` | 10 | close > VWAP (BC10) |
| `vwap_distribution_penalty` | -5 | close < VWAP (BC10) |
| `shark_min_unique_insiders` | 2 | Shark min insiders (BC9) |
| `shark_lookback_days` | 10 | Shark lookback (BC9) |
| `shark_min_total_value` | 100,000 | Shark min value (BC9) |
| `shark_score_bonus` | 10 | Shark bonus (BC9) |
| `rsi_ideal_inner_low` | 45 | RSI ideal zone start (BC9) |
| `rsi_ideal_inner_high` | 65 | RSI ideal zone end (BC9) |
| `rsi_ideal_outer_low` | 35 | RSI outer zone start (BC9) |
| `rsi_ideal_outer_high` | 75 | RSI outer zone end (BC9) |
| `rsi_ideal_inner_bonus` | 30 | RSI inner bonus (BC9) |
| `rsi_ideal_outer_bonus` | 15 | RSI outer bonus (BC9) |
| `sma50_bonus` | 30 | SMA50 bonus (BC9) |
| `rs_spy_bonus` | 40 | RS vs SPY bonus (BC9) |
| `call_wall_max_atr_distance` | 5.0 | Call wall ATR filter (BC12) |
| `gex_max_dte` | 90 | Max DTE opciókra (BC12) |
| `obsidian_enabled` | False | OBSIDIAN klasszifikáció (BC15) |
| `obsidian_store_always_collect` | True | Feature store mindig ír (BC15) |
| `obsidian_regime_multipliers` | {8 regime → mult} | Per-regime multiplier (BC15+BC16, inc. volatile=0.60) |
| `factor_volatility_enabled` | False | Factor volatility framework (BC16) |
| `factor_volatility_confidence_floor` | 0.6 | Min regime confidence (BC16) |

### RUNTIME (környezet-specifikus)

| Kulcs | Érték | Használat |
|-------|-------|-----------|
| `account_equity` | 100,000 | Számla méret USD |
| `risk_per_trade_pct` | 0.5 | Per-trade kockázat % |
| `max_positions` | 8 | Max pozíció szám |
| `max_positions_per_sector` (TUNING) | 3 | Max/szektor |
| `max_single_position_risk_pct` | 1.5 | Max egyedi risk % |
| `max_gross_exposure` | 100,000 | Max bruttó kitettség |
| `max_single_ticker_exposure` | 20,000 | Max ticker kitettség |
| `max_order_quantity` | 5,000 | Fat finger qty cap (BC12) |
| `async_enabled` | False | Async mode (env: IFDS_ASYNC_ENABLED) |
| `async_sem_polygon` | 10 | Polygon concurrent limit (BC16: 5→10) |
| `async_sem_fmp` | 8 | FMP concurrent limit (BC16 tuned: 429 at 12) |
| `async_sem_uw` | 5 | UW concurrent limit |
| `async_max_tickers` | 10 | Max concurrent tickers (BC16 tuned: 429 at 15) |
| `cb_window_size` | 50 | Circuit breaker window (BC11) |
| `cb_error_threshold` | 0.3 | CB error rate trigger (BC11) |
| `cb_cooldown_seconds` | 60 | CB cooldown (BC11) |
| `signal_hash_file` | state/signal_hashes.json | Signal dedup (BC11) |
| `survivorship_snapshot_dir` | state/universe_snapshots | Universe snapshot mappa (BC13) |
| `survivorship_max_snapshots` | 30 | Max megőrzött snapshot (BC13) |
| `telegram_bot_token` | None | Telegram bot token (BC13) |
| `telegram_chat_id` | None | Telegram chat ID (BC13) |
| `telegram_timeout` | 5 | Telegram HTTP timeout (BC13) |
| `max_daily_trades` | 20 | Napi trade limit (BC13) |
| `daily_trades_file` | state/daily_trades.json | Trade counter state (BC13) |
| `max_daily_notional` | 200,000 | Napi notional cap (BC13) |
| `max_position_notional` | 25,000 | Per-pozíció notional cap (BC13) |
| `daily_notional_file` | state/daily_notional.json | Notional counter state (BC13) |
| `obsidian_store_dir` | state/obsidian | Feature store mappa (BC15) |
| `obsidian_max_store_entries` | 100 | Max entry per ticker (BC15) |
