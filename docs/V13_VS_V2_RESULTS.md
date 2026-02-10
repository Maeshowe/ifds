# V13 vs V2.0 — Eredmeny Osszehasonlitas (2026-02-10, BC12 utan)

> V13: `reference/execution_plan.csv` (2026-02-09, 15 pozicio)
> V2.0: `output/execution_plan_run_20260210_*.csv` (2026-02-10, 8 pozicio)
> Frissitve: BC12 utan (563 test, GEX sign fix, 6 uj feature)

---

## 1. Universe Meretek

| | V13 | V2.0 (BC12) | Diff |
|--|-----|-------------|------|
| FMP Screened | ~1400 | 1688 | +288 |
| Earnings excluded | ? | 270 | |
| Final universe | ~1400 | 1418 | +18 |

**Javitas BC9-ban**: `isEtf: False` (Python boolean) → `"false"` (string) fix.
**BC12**: DTE filter (90 nap) + institutional ownership nem valtoztatja a universe meretet.

---

## 2. V2.0 Execution Plan (8 pozicio)

```
Rank | Ticker | Score | Flow | Funda | Tech | Sector          | Mult   | GEX      | Flags
-----|--------|-------|------|-------|------|-----------------|--------|----------|------
1    | GNL    | 100.0 | 100  |   65  | 100  | Real Estate     | 1.040  | positive | FRESH
2    | USAS   | 92.5  |  80  |   55  | 100  | Basic Materials | 0.575  | positive |
3    | ORLA   | 91.0  |  75  |   60  | 100  | Basic Materials | 1.040  | positive |
4    | SSRM   | 90.5  |  75  |   55  | 100  | Basic Materials | 0.575  | positive |
5    | PECO   | 90.0  |  85  |   50  | 100  | Real Estate     | 0.525  | positive |
6    | NFG    | 89.5  |  75  |   55  | 100  | Energy          | 0.575  | positive |
7    | DLR    | 89.0  |  80  |   50  |  85  | Real Estate     | 1.035  | positive |
8    | YPF    | 88.5  |  65  |   60  | 100  | Energy          | 1.040  | positive |
```

Score range: 88.5-100.0 (GNL = FRESH capped at 100)

---

## 3. V13 Top 15 Ticker — V2.0 Statusz (2026-02-10 adat, BC12 utan)

```
Ticker | V13    | V2.0   | V2 Statusz            | Megjegyzes
-------|--------|--------|-----------------------|----------------------------------
CNX    |  89.0  |  89.0  | ACCEPTED              | Mindket rendszerben
ENPH   |  88.5  |  88.5  | ACCEPTED              | Mindket rendszerben
SDRL   |  87.5  |  87.5  | ACCEPTED              | Sector/position limit
CDE    |  89.0  |  89.0  | ACCEPTED              | Sector limit (Basic Materials)
PAAS   |  89.0  |  89.0  | ACCEPTED              | Sector limit (Basic Materials)
EQR    |  83.0  |  83.0  | ACCEPTED              | Position limit
NEM    |  89.0  |  89.0  | ACCEPTED              | Sector limit (Basic Materials)
KGC    |  89.0  |  89.0  | ACCEPTED              | Sector limit (Basic Materials)
HP     |  90.0  |  90.0  | ACCEPTED              | Sector limit (Energy)
NSC    |   —    |  62.0  | REJECTED              | Score < 70
GTLS   |   —    |  59.5  | REJECTED              | Score < 70
HOLX   |   —    |  47.5  | REJECTED              | Score < 70
BBVA   |   —    |  60.0  | REJECTED              | Score < 70
ATMU   |   —    |   —    | NOT IN UNIVERSE       |
INCY   |   —    |   —    | NOT IN UNIVERSE       |
```

**Atfedes BC12 utan: 9/15 ACCEPTED (60%)** — BC9: 6/15 (40%), BC9 elott: 1/15 (6.7%).

---

## 4. Phase 4 Breakdown (1418 analyzed)

| Statusz | Szam | % |
|---------|------|---|
| ACCEPTED | 391 | 27.6% |
| Score < 70 | 612 | 43.2% |
| Tech Filter (SMA200) | 376 | 26.5% |
| Crowded (>95) | 39 | 2.7% |

**Fejlodes**:
- BC9 elott: 16 ACCEPTED (1.2%)
- BC9 utan: 236 ACCEPTED (23.2%)
- BC10 utan: ~350 ACCEPTED (~25%)
- **BC12 utan: 391 ACCEPTED (27.6%)**

Novekedes oka: dp_pct fix (+10-15 flow), Buy Pressure/VWAP (+10-25 flow), institutional ownership (+10 funda).

---

## 5. GEX Impact (BC12 GEX Sign Fix)

### BC12 elott (bugos)
- Phase 5 input: 100 ticker
- Phase 5 passed: **2** (98 NEGATIVE → excluded)
- Root cause: Polygon put GEX nem volt signed → `_find_zero_gamma()` legmagasabb strike-ot adta → minden NEGATIVE

### BC12 utan (javitott)
- Phase 5 input: 100 ticker
- Phase 5 passed: **~95** (kevesebb NEGATIVE)
- Zero gamma interpolation → pontosabb regime meghatározas
- DTE filter → kevesebb zaj a hatso honapi opciokbol

---

## 6. Score Formula Osszehasonlitas (BC12 aktualis)

```
V13:  combined = (0.40 x flow + 0.30 x funda + 0.30 x tech + sector_adj + shark_bonus)
      x freshness_multiplier(1.75)
      → cap(100)
      Clipping: > 85 → crowded
      Tech: base 50 + RSI ideal(+30) + SMA50(+30) + RS vs SPY(+40) = max 150
      Flow: base 50 + RVOL + buy_pressure(VWAP) + PCR + OTM + block_trades + dp_pct

V2.0: combined = (0.40 x flow + 0.30 x funda + 0.30 x tech + sector_adj)
      x insider_multiplier
      x freshness_multiplier(1.5)
      → cap(100)
      Clipping: > 95 → crowded
      Tech: RSI ideal(+30) + SMA50(+30) + RS vs SPY(+40) = max 100 (NO BASE)
      Flow: base 50 + RVOL + squat + PCR + OTM + block + dp_pct + buy_pressure + VWAP
      Funda: base 50 + growth/margin/ROE/D_E + insider + shark + inst_ownership
```

### Strukturalis kulonbsegek:

| Jellemzo | V13 | V2.0 (BC12) |
|----------|-----|-------------|
| Freshness multiplier | 1.75x | 1.5x |
| Clipping threshold | 85 | 95 |
| Tech base | 50 | 0 (no base) |
| Tech max | 150 | 100 |
| Flow base | 50 | 50 |
| dp_pct | UW volume | Polygon volume (BC10 fix) |
| Buy Pressure | close vs VWAP | close vs VWAP (BC10 fix) |
| Institutional ownership | Nincs | +10/-5 (BC12) |
| VIX EXTREME | Nincs | VIX > 50 → 0.10x (BC12) |
| DTE filter | 35 nap | 90 nap (BC12) |
| Call wall ATR filter | 5x ATR | 5x ATR (BC12) |
| Fat finger | max qty 5000 | max qty 5000 (BC12) |
| Circuit breaker | Per-provider | Per-provider (BC11) |
| Signal dedup | SHA256, 24h | SHA256, 24h (BC11) |
| Risk per trade | 1.5% | 0.5% |
| TP2 ratio | 4R | 3R |
| Max positions | 15 | 8 |
| Sector cap | 3 | 3 |

---

## 7. Root Cause — Maradek Elteresek

### 7.1 NSC, GTLS: Freshness Gap
- NSC (62.0), GTLS (59.5) → Score < 70 → REJECTED
- V13-ben freshness 1.75x → NSC: 62.0 × 1.75 = cap 100
- V2-ben freshness 1.5x → NSC: 62.0 × 1.5 = 93.0 → de freshness nem aktivalodik (pandas/signal_history kell)

### 7.2 HOLX: Flow Scoring Gap
- HOLX (47.5) → alacsony combined score
- V13-ben mas napi adat + valoszinuleg mas flow bonuszok

### 7.3 ATMU, INCY: Universe Gap
- Nem szerepelnek az FMP screener eredmenyekben
- Market cap, volume, vagy FMP adat hianyzik

### 7.4 BBVA: Score Gap
- BBVA (60.0) → Score < 70
- Financial Services szektor, lehetseges sector VETO hatas

---

## 8. Konkluzio

### BC9 elotti allapot:
- V13 top 15 atfedes: **1/15** (6.7%)
- V2 ACCEPTED: **16** ticker
- Score range: 50-74

### BC9 utani allapot:
- V13 top 15 atfedes: **6/15** (40%)
- V2 ACCEPTED: **236** ticker
- Score range: 70-100

### BC12 utani allapot (aktualis):
- V13 top 15 atfedes: **9/15** (60%)
- V2 ACCEPTED: **391** ticker
- Score range: 88.5-100
- 8 pozicio az exec plan-ban
- GEX sign fix: 98 NEGATIVE → ~5 NEGATIVE (valos regime)
- 563 teszt, 0 failure

### Maradek gap root cause:
1. **Freshness gap**: NSC/GTLS freshness nem aktivalodik (pandas/signal_history)
2. **Universe gap**: 2 ticker nem az FMP universe-ben (ATMU, INCY)
3. **Score gap**: HOLX (47.5), BBVA (60.0) → eltero napi adat + freshness hatar
