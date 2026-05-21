# SimEngine Level 2 — Tervezési Dokumentum

**Dátum:** 2026-02-18
**Státusz:** APPROVED — döntések véglegesítve
**Tervezett BC:** BC19 (március — L1-re épít, BC17/18-tól független), BC20 (április)
**Előfeltétel:** SIM-L1 első futtatás ~feb 19, Paper Trading 21 nap (márc 9)

---

## 1. Célkitűzés

A SIM-L2 célja: **stratégia variánsok objektív összehasonlítása** historikus execution plan adaton, mielőtt production-be kerülnének. Az L1 egyetlen konfigurációval validál — az L2 lehetővé teszi, hogy két (vagy több) konfigurációt egymás mellett futtassunk és mérhető különbséget kapjunk.

**Konkrét use case-ek:**
- T10: Freshness Alpha vs WOW Signals A/B teszt
- T7: New Kid + Repeat bónusz logika validálása
- TP/SL ATR multiplier optimalizáció (pl. 1.5/2.0/3.0 vs 2.0/3.0/4.0)
- GEX regime multiplier sensitivity
- Score küszöb vizsgálat (70 vs 75 vs 80)

---

## 2. Architektúra

### 2.1 L1 → L2: Mi változik?

| Aspektus | SIM-L1 | SIM-L2 |
|----------|--------|--------|
| Input | Execution plan CSV (fix) | Execution plan CSV + **config override** |
| Config | Egyetlen pipeline config | **Variáns config-ok** (A/B/C) |
| Futtatás | Egyszer | Többször, variánsonként |
| Output | 1 summary | **Párhuzamos summary-k + delta riport** |
| Scoring | Fix (CSV-ből) | **Opcionálisan újraszámolt** (re-score) |

### 2.2 Két mód

**Mód 1 — Parameter Sweep (egyszerű):**
Csak a bracket order paramétereket változtatja (ATR multipliers, hold days, fill window). Nem szükséges a scoring pipeline újrafuttatása — az execution plan CSV-ből dolgozik, csak a TP/SL/sizing paramétereket írja felül.

```
Input: execution_plan_*.csv + override_config
Override: {stop_loss_atr_multiple: 2.0, tp1_atr_multiple: 3.0, ...}
→ Újraszámolt TP/SL az eredeti entry + ATR alapján
→ broker_sim.py futtatás az új paraméterekkel
→ ValidationSummary
```

**Mód 2 — Re-Score (komplex, T10/T7 validáláshoz):**
A scoring logikát is újrafuttatja módosított paraméterekkel. Ehhez kell a nyers adat (bars, flow, fundamentals) — vagy az L1 CSV-t kiegészítő adatok.

```
Input: Phase 4 intermediate data + override_config
Override: {freshness_bonus: 1.0, freshness_wow_bonus: 2.0, ...}
→ Újraszámolt score
→ Új execution plan (más tickers/qty lehetnek!)
→ broker_sim.py futtatás
→ ValidationSummary
```

**DÖNTÉS:** Mód 1-gyel indulunk (BC19, március), Mód 2 BC20-ban (április). BC19 independent BC17/18-tól.

### 2.3 Fájl struktúra

```
src/ifds/sim/
├── __init__.py
├── models.py          # L1 ✅ — L2: + SimVariant, ComparisonReport
├── broker_sim.py      # L1 ✅ — változatlan
├── validator.py       # L1 ✅ — változatlan (egyetlen variáns futtatása)
├── report.py          # L1 ✅ — L2: + comparison report
├── replay.py          # ÚJ — L2: parameter override + multi-run orchestrátor
└── comparison.py      # ÚJ — L2: delta riport, stat. szignifikancia
```

---

## 3. Adatmodellek

### 3.1 SimVariant

```python
@dataclass
class SimVariant:
    """Egyetlen konfiguráció variáns egy A/B teszthez."""
    name: str                          # "baseline", "wow_signals", "atr_2x3x"
    description: str = ""
    
    # Parameter overrides (csak a módosított értékek)
    overrides: dict = field(default_factory=dict)
    
    # Results (validator tölti)
    trades: list[Trade] = field(default_factory=list)
    summary: ValidationSummary = field(default_factory=ValidationSummary)
```

### 3.2 ComparisonReport

```python
@dataclass
class ComparisonReport:
    """A/B összehasonlítás két vagy több variáns között."""
    variants: list[SimVariant]
    
    # Delta metrics (baseline vs challenger)
    pnl_delta: float = 0.0
    win_rate_delta: float = 0.0
    sharpe_delta: float = 0.0
    
    # Stat significance
    p_value: float | None = None       # Paired t-test on per-trade P&L
    is_significant: bool = False        # p < 0.05
    
    # Per-trade deltas
    trade_deltas: list[dict] = field(default_factory=list)
```

---

## 4. replay.py — Központi orchestrátor

```python
def run_comparison(
    variants: list[SimVariant],
    output_dir: str = "output",
    polygon_api_key: str | None = None,
    max_hold_days: int = 10,
) -> ComparisonReport:
    """Futtasson minden variánst ugyanazon az adaton és hasonlítsa össze."""
    
    # 1. Betölti az execution plan CSV-ket (egyszer)
    base_trades = load_execution_plans(output_dir)
    
    # 2. Polygon adatot is egyszer fetch-eli
    bars_data = fetch_bars(...)  # közös, cached
    
    # 3. Minden variánshoz:
    for variant in variants:
        trades_copy = deep_copy(base_trades)
        
        # Parameter override alkalmazása
        if "stop_loss_atr_multiple" in variant.overrides:
            recalculate_stops(trades_copy, variant.overrides)
        if "tp1_atr_multiple" in variant.overrides:
            recalculate_tps(trades_copy, variant.overrides)
        if "max_hold_days" in variant.overrides:
            max_hold = variant.overrides["max_hold_days"]
        
        # Szimuláció
        variant.trades, variant.summary = validate_trades_with_bars(
            trades_copy, bars_data, max_hold=max_hold
        )
    
    # 4. Összehasonlítás
    return compare_variants(variants)
```

**Fontos:** A Polygon fetch egyszer történik, nem variánsonként — ez cache-friendly és API-barát.

---

## 5. comparison.py — Statisztikai összehasonlítás

### 5.1 Delta metrikák

Minden `(baseline, challenger)` párra:

| Metrika | Számítás |
|---------|----------|
| ΔP&L | challenger.total_pnl - baseline.total_pnl |
| ΔWin Rate | challenger.leg1_win_rate - baseline.leg1_win_rate |
| ΔAvg P&L/trade | challenger.avg_pnl_per_trade - baseline.avg_pnl_per_trade |
| ΔHolding Days | challenger.avg_holding_days - baseline.avg_holding_days |
| ΔFill Rate | challenger.filled/total - baseline.filled/total |

### 5.2 Statisztikai szignifikancia

**Paired t-test** a per-trade P&L-en (ugyanaz a ticker, ugyanaz a nap → párosított):
```python
from scipy import stats

baseline_pnls = [t.total_pnl for t in baseline.trades if t.filled]
challenger_pnls = [t.total_pnl for t in challenger.trades if t.filled]
t_stat, p_value = stats.ttest_rel(baseline_pnls, challenger_pnls)
```

**Minimális sample:** ≥30 párosított trade a p-value érvényességéhez. Ha kevesebb, jelezni a riportban ("insufficient data for significance test").

**scipy mandatory dependency** — telepítve van mind a fejlesztői, mind a prod rendszeren. Egzakt p-value-val döntünk, nincs fallback.

---

## 6. Parameter Override — Mód 1 Részletek

### 6.1 Bracket paraméterek újraszámolása

Az execution plan CSV tartalmazza az ATR értéket (implicit: `stop_loss = entry - k * ATR` → `ATR = (entry - stop_loss) / k`). Az override-nak visszaszámolnia kell az ATR-t, majd az új multiplier-ekkel újraszámolni TP/SL:

```python
def recalculate_bracket(trade: Trade, overrides: dict, 
                         original_atr_mult: float = 1.5) -> Trade:
    """Recalculate TP/SL from overrides using implied ATR."""
    # Implied ATR from original stop
    atr = (trade.entry_price - trade.stop_loss) / original_atr_mult
    
    new_sl_mult = overrides.get("stop_loss_atr_multiple", original_atr_mult)
    new_tp1_mult = overrides.get("tp1_atr_multiple", 2.0)
    new_tp2_mult = overrides.get("tp2_atr_multiple", 3.0)
    
    trade.stop_loss = trade.entry_price - new_sl_mult * atr
    trade.tp1 = trade.entry_price + new_tp1_mult * atr
    trade.tp2 = trade.entry_price + new_tp2_mult * atr
    
    return trade
```

### 6.2 Max hold days + Fill window override

Egyszerű — a `simulate_bracket_order()` már paraméteres.

---

## 7. CLI Interface

```bash
# L1 (meglévő)
python -m ifds validate --days 10

# L2: A/B összehasonlítás
python -m ifds compare \
  --baseline "default" \
  --challenger "wide_stops" \
  --override-sl-atr 2.0 \
  --override-tp1-atr 3.0 \
  --override-tp2-atr 4.0 \
  --days 10

# L2: Config file alapú (több variáns)
python -m ifds compare --config sim_variants.yaml
```

### 7.1 sim_variants.yaml formátum

```yaml
variants:
  - name: baseline
    description: "Current production config"
    overrides: {}
    
  - name: wide_stops
    description: "2x ATR stop, 3x/4x TP"
    overrides:
      stop_loss_atr_multiple: 2.0
      tp1_atr_multiple: 3.0
      tp2_atr_multiple: 4.0
      
  - name: tight_stops
    description: "1x ATR stop, 1.5x/2x TP"
    overrides:
      stop_loss_atr_multiple: 1.0
      tp1_atr_multiple: 1.5
      tp2_atr_multiple: 2.0
      
  - name: longer_hold
    description: "15 day hold instead of 10"
    overrides:
      max_hold_days: 15
```

---

## 8. T10: Freshness Alpha vs WOW Signals — Terv

Ez Mód 2 (re-score), tehát BC20 scope. De az előkészítés BC19-ben megtörténik:

### 8.1 Freshness Alpha jelenlegi logika
```
signal_history.parquet-ból: hányszor jelent meg az elmúlt 90 napban
penalty = repetition_count × freshness_penalty_factor
adjusted_score = score × (1 - penalty)
```

### 8.2 WOW Signals hipotézis (U-alakú)
```
1-2 nap: New Kid bónusz (+15%)
3-5 nap, score ≥ 80: WOW Signal bónusz (+10%)
6+ nap, score nem nőtt: Stale penalty (-20%)
6+ nap, score nőtt: Persistent strength (+5%)
```

### 8.3 A/B teszt terv
- **Variáns A (baseline):** Jelenlegi lineáris freshness penalty
- **Variáns B (WOW):** U-alakú logika
- **Mérés:** 30+ trade párosított P&L, win rate, és score→return korreláció
- **Döntési küszöb:** p < 0.05, VAGY ΔP&L > +$500 és ΔWR > +5% ugyanazon időszakon

---

## 9. Cross-Validation: Paper Trading vs SimEngine

A Paper Trading (Mac Mini, IBKR) és SimEngine (Polygon bars) párhuzamosan fut. Az összehasonlítás manuális a következő dimenziókon:

| Dimenzió | Paper Trading | SimEngine |
|----------|---------------|-----------|
| Fill rate | IBKR Adaptive algo | low ≤ entry → fill |
| Fill price | Market (slippage) | Exact limit price |
| Same-day TP+SL | Market order | Pessimistic (stop) |
| Exit timing | MOC order | Bar close |

**Mérőszám:** Fill rate delta (PT fills / SIM fills), P&L correlation (per-ticker daily). Ha a korreláció > 0.7, a SimEngine megbízható proxy.

---

## 10. Implementációs Terv

### BC19 (Mód 1 — Parameter Sweep)

| Feladat | Fájl | Becsült effort |
|---------|------|---------------|
| SimVariant + ComparisonReport modellek | models.py | 1 óra |
| replay.py orchestrátor | replay.py | 2-3 óra |
| recalculate_bracket logika | replay.py | 1 óra |
| comparison.py delta + paired t-test | comparison.py | 2 óra |
| report.py comparison output | report.py | 1 óra |
| CLI (`ifds compare`) | __main__.py | 1 óra |
| YAML config loader | replay.py | 30 perc |
| Tesztek (15-20 új) | test_sim_replay.py | 2 óra |
| **Összesen** | | **~10-12 óra** |

### BC20 (Mód 2 — Re-Score + T10)

| Feladat | Fájl | Becsült effort |
|---------|------|---------------|
| Phase 4 intermediate data serialization | phases/ | 3 óra |
| Re-score engine (freshness override) | replay.py | 3 óra |
| WOW Signals logika implementáció | scoring/ | 2 óra |
| T10 A/B konfiguráció | sim_variants.yaml | 30 perc |
| Tesztek (10-15 új) | test_sim_rescore.py | 2 óra |
| **Összesen** | | **~10-12 óra** |

---

## 11. Előfeltételek & Függőségek

- ✅ SIM-L1 működik (BC16)
- ⏳ SIM-L1 első futtatás (feb 19 — kell 5+ nap execution plan CSV)
- ⏳ Paper Trading 21 nap (márc 9)
- ⏳ OBSIDIAN baseline complete (márc 4)
- 📦 scipy (opcionális, paired t-test) — `pip install scipy`
- 📦 pyyaml (config loader) — `pip install pyyaml`

---

## 12. Döntési pontok — VÉGLEGESÍTVE (2026-02-18)

1. **scipy mandatory.** Telepítve mindkét gépen. Egzakt p-value, nincs szemre döntés.
2. **YAML config.** Olvashatóbb, comments támogatás. pyyaml dependency.
3. **BC19 timing: OBSIDIAN aktiválás ELŐTT.** L2 Mód 1 independent BC17/18-tól, csak L1-re épít.
4. **Mód 2 scope: teljes Phase 4 re-score** a perzisztált snapshot-okból. Kompromisszum: csak a Phase 4 "passed" tickereket (~390/nap) snapshot-oljuk, nem mind az 1200-at. BC19-ben indul a snapshot gyűjtés, BC20-ban használjuk.
5. **Minimum trade count:** 30 a szignifikanciához. Feb 19-től gyűlik, márc közepére ~120-150 trade — bőven elég.

---

## 13. Phase 4 Snapshot Persistence (BC19 scope)

A pipeline végén napi snapshot a Phase 4 passed tickers nyers adataiból:

```
state/phase4_snapshots/
├── 2026-02-19.parquet   # ~390 ticker × 6 adat tábla
├── 2026-02-20.parquet
└── ...
```

**Tartalom per ticker:**
- Polygon bars (OHLCV, 250 nap)
- Polygon options snapshot (PCR, OTM, block count)
- FMP financial growth (revenue/EPS)
- FMP key metrics (ROE, D/E, margin)
- FMP insider trading (insider score, shark)
- UW dark pool (DP%, buy pressure) — fallback dp_pct=0 ha historikusan nem elérhető

**Méret:** ~2-5 MB/nap tömörítve, 30 nap = ~60-150 MB

BC19: pipeline-ba beépítjük a mentést
BC20: re-score engine a snapshot-okból dolgozik

---

## 14. Roadmap kapcsolat

```
BC17 (márc 4):    EWMA + crowdedness measurement + OBSIDIAN aktiválás
BC18 (márc 18):   Crowdedness filtering aktiválás
BC19 (március):   SIM-L2 Mód 1 (parameter sweep) + Phase 4 snapshot persistence
                  ↑ INDEPENDENT — L1-re épít, nem függ BC17/18-tól
BC20 (április):   SIM-L2 Mód 2 (re-score) + T10 A/B teszt
BC21-22 (május):  HRP allokáció + Riskfolio-Lib integráció
```
