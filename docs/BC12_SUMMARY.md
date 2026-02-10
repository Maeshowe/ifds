# BC12 Summary — P3 Nice-to-have Features

> Build Cycle 12 | 2026-02-10 | 563 tests (34 new)

---

## Osszefoglalo

BC12 hat P3 feature-t implementalt, amelyek javitjak a GEX pontossagot, kockazatkezelest es fundamental scoring-ot. Emellett egy kritikus GEX sign bug is javitasra kerult.

| Metrika | Ertek |
|---------|-------|
| Uj tesztek | 34 (test_bc12_features.py) |
| Osszes teszt | 563 passed, 0 failed |
| Modositott fajlok | 11 source + 1 test |
| Uj config kulcsok | 4 TUNING + 1 RUNTIME |

---

## 6 Feature

### 1. Zero Gamma Interpolation

**Problema**: `_find_zero_gamma()` az elojelvaltas strike-jat adta vissza — pontatlan.
**Megoldas**: Linearis interpolacio a ket bracketing strike kozott.

```
Formula: prev_strike + (strike - prev_strike) * (-prev_cum / denom)
Feltetel: (prev_cum < 0 and cum >= 0) or (prev_cum > 0 and cum <= 0)
Fallback: return 0.0 ha nincs crossover (→ POSITIVE regime)
```

- Fajlok: `adapters.py` (`_find_zero_gamma()`)
- Automatikusan propagal az async utvonalra (`async_adapters.py` importalja)

### 2. DTE Filter (90 nap)

**Problema**: Hatso honapi opciok torzitjak a GEX es PCR szamitasokat.
**Megoldas**: Csak ≤90 DTE opciot hasznal GEX + PCR/OTM scoringhoz.

- Config: `gex_max_dte=90`
- <5 kontraktus fallback: ha a DTE filter kevesebb mint 5 kontraktust hagy → osszes hasznalata
- Rossz datum formatum → include (graceful fallback)
- `PolygonGEXProvider` constructor param: `max_dte` (nem a GEXProvider ABC-n)
- Fajlok: `adapters.py`, `async_adapters.py`, `phase4_stocks.py`

### 3. Call Wall ATR Filter

**Problema**: Call wall $500-on mikor az ar $100 → ertelmetlen TP1.
**Megoldas**: Ha `abs(call_wall - price) > atr × 5.0` → `call_wall = 0` (Phase 6 ATR fallback-et hasznal).

- Config: `call_wall_max_atr_distance=5.0`
- Fajlok: `phase5_gex.py` (sync + async loop)

### 4. Fat Finger Protection

**Problema**: Extrem inputok abszurd pozicio mereteket generalhatnak.
**Megoldas**: Tobbretegu vedelem a `_calculate_position()` fuggvenyben.

- NaN guard: `not (atr > 0)` — NaN osszehasonlitasok mindig False
- Quantity cap: `min(calculated, max_order_quantity=5000, max_single_ticker_exposure/entry)`
- Config: `max_order_quantity=5000` (RUNTIME)
- Fajlok: `phase6_sizing.py`

### 5. VIX EXTREME Regime

**Problema**: VIX > 50 (2020 marcius szint) erosebb pozicio csokkentes kell mint PANIC.
**Megoldas**: Uj `EXTREME` enum ertek, kulon multiplier.

- Config: `vix_extreme_threshold=50`, `vix_extreme_multiplier=0.10`
- VIX 51+ → pozicio meret × 0.10 (gyakorlatilag szuneteltet)
- `MarketVolatilityRegime.EXTREME` enum ertek
- Fajlok: `models/market.py`, `phase0_diagnostics.py`

### 6. Institutional Ownership Trend

**Problema**: Nincs intezmenyi flow signal a fundamental scoringban.
**Megoldas**: FMP institutional ownership adatbol QoQ valtozas elemzes.

- Endpoint: `GET /stable/institutional-ownership/latest?symbol={ticker}&limit=2`
- QoQ change > 2% → "increasing" +10, < -2% → "decreasing" -5, else "stable" 0
- Graceful degradation: AAPL probe futtatas elott, ha 404 → `inst_ownership_available=False`, skip all
- `FundamentalScoring`: `inst_ownership_trend`, `inst_ownership_score` mezok
- Async: 6. hivas az `asyncio.gather()`-ben (index 5)
- `_analyze_fundamental()` `skip_inst=False` param
- Fajlok: `fmp.py`, `async_clients.py`, `models/market.py`, `phase4_stocks.py`

---

## GEX Sign Bug Fix (Kritikus)

### Problema
BC12 utan Phase 5 csak 2/100 tickert engedett at (98 NEGATIVE). BC12 elott 100/100 passed.

### Root Cause — Ket Bug

**Bug 1: Polygon gex_by_strike sign**
- Put GEX POZITIVKENT adodott a `gex_by_strike`-hoz (kellene: NEGATIV)
- UW adat mar signed (put_gamma negativ), Polygon nem volt az
- Eredmeny: `gex_by_strike` mindig pozitiv → nincs zero crossing → `_find_zero_gamma()` nem talal crossover-t

**Bug 2: `_find_zero_gamma()` fallback**
- BC12 rewrite `return prev_strike`-ra valtoztatta a `return 0.0`-t
- Ha nincs crossover → visszaadja a legmagasabb strike-ot (pl. 500)
- $100-as reszvenynel: `price(100) < zero_gamma(500)` → NEGATIVE

### Fix
1. `adapters.py`: Put GEX **kivonasa** `gex_by_strike`-bol (`gex_by_strike[strike] -= gex`)
2. `async_adapters.py`: Ugyanaz a signed GEX fix
3. `adapters.py`: `_find_zero_gamma()` fallback → `return 0.0` (crossover nelkul)
4. `phase5_gex.py`: Debug logging az elso 5 tickerrol (sync + async)

---

## Tesztek

### test_bc12_features.py — 34 teszt, 8 osztaly

| Osztaly | Tesztek | Tartalom |
|---------|---------|----------|
| TestZeroGammaInterpolation | 4 | interpolacio, single crossover, all positive → 0.0, empty |
| TestFrontMonthFilter | 5 | DTE exclude, keep near, fallback <5, disable max_dte=0, no expiration |
| TestCallWallATRFilter | 4 | within ATR → kept, beyond ATR → zeroed, zero passthrough, no ATR skip |
| TestFatFingerProtection | 5 | max qty cap, value cap, NaN reject, Inf reject, negative reject |
| TestVIXExtreme | 4 | VIX 65 → EXTREME, VIX 50 → PANIC, multiplier 0.10, VIX 51 → EXTREME |
| TestInstitutionalOwnership | 5 | increasing +10, decreasing -5, stable 0, insufficient data, None safe |
| TestDTEFilterInPhase4Flow | 2 | PCR front-month only, OTM ratio filtered |
| TestIntegration | 4 | GEX end-to-end, Phase 5 ATR filter, fat finger in sizing, EXTREME multiplier |

### Regresszio
- 530 korabbi teszt mind atment valtozas nelkul
- Post-BC12 GEX fix: 564 osszes teszt (34 uj)

---

## Modositott Fajlok

| Fajl | Valtozas |
|------|----------|
| `src/ifds/config/defaults.py` | +4 TUNING + 1 RUNTIME kulcs |
| `src/ifds/models/market.py` | EXTREME enum, FundamentalScoring inst mezok |
| `src/ifds/data/adapters.py` | Zero gamma interpolation, DTE filter, GEX sign fix |
| `src/ifds/data/async_adapters.py` | DTE filter, GEX sign fix |
| `src/ifds/data/fmp.py` | `get_institutional_ownership()` |
| `src/ifds/data/async_clients.py` | Async `get_institutional_ownership()` |
| `src/ifds/phases/phase0_diagnostics.py` | EXTREME regime + multiplier |
| `src/ifds/phases/phase4_stocks.py` | DTE filter flow scoring, institutional ownership |
| `src/ifds/phases/phase5_gex.py` | Call wall ATR filter, debug logging |
| `src/ifds/phases/phase6_sizing.py` | Fat finger protection |
| `src/ifds/pipeline/runner.py` | Institutional ownership AAPL probe |
| `tests/test_bc12_features.py` | 34 uj teszt |

---

## Config Kulcsok

### TUNING (uj)

| Kulcs | Ertek | Hatas |
|-------|-------|-------|
| `call_wall_max_atr_distance` | 5.0 | Max ATR tavolsag call wall szureshez |
| `gex_max_dte` | 90 | Max DTE opcios filter (napokban) |
| `vix_extreme_threshold` | 50 | VIX > 50 → EXTREME regime |
| `vix_extreme_multiplier` | 0.10 | Pozicio meret × 0.1 EXTREME-ben |

### RUNTIME (uj)

| Kulcs | Ertek | Hatas |
|-------|-------|-------|
| `max_order_quantity` | 5000 | Hard cap darabszamra pozicionkent |
