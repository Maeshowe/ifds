Status: DONE
Updated: 2026-04-03
Note: BC20 Phase_20B — T10 Freshness Alpha vs WOW Signals A/B teszt
Depends: Phase_20A (rescore engine) kész

# BC20 Phase_20B — T10 A/B Teszt: Freshness Alpha vs WOW Signals

## Cél

A/B tesztelés a Mód 2 rescore engine-nel: a jelenlegi lineáris freshness bonus
(×1.5 új signalokra) vs U-alakú WOW Signals logika (ismétlődő jó signalok kapnak
bónuszt, stale signalok büntetést).

## Háttér

Jelenleg: ha egy ticker 90 napja nem volt a pipeline-ban → `combined_score × 1.5`.
Ez egyszerű, de nem jutalmazza a **jó ismétlődő signalokat** (WOW = "World of Winners"
— ticker ami újra megjelenik mert tényleg jó, nem mert új).

## Variánsok

### Variáns A — Baseline (jelenlegi)
```python
# Lineáris freshness: 90 nap lookback, ×1.5 bonus
freshness_lookback_days: 90
freshness_bonus: 1.5
```

### Variáns B — WOW Signals (U-alakú)
```python
def wow_freshness(ticker, signal_history_df, lookback=90):
    appearances = count_appearances(ticker, signal_history_df, lookback)
    days_since_last = days_since_last_appearance(ticker, signal_history_df)
    
    if appearances == 0:
        return 1.15  # New Kid — mérsékelt bonus (nem 1.5)
    elif appearances >= 3 and days_since_last <= 5:
        return 1.10  # WOW — ismétlődő jó signal, friss
    elif appearances >= 1 and days_since_last > 30:
        return 0.80  # Stale — régen volt, most visszajön, de nem meggyőző
    elif appearances >= 5:
        return 1.05  # Persistent — gyakori, kis bonus
    else:
        return 1.00  # Neutral
```

## Implementáció

### 1. `rescore.py` bővítés — freshness override

A rescore engine-nek tudnia kell a freshness logikát is felülírni:
- `config_overrides["freshness_mode"]`: `"linear"` | `"wow"`
- `config_overrides["freshness_bonus"]`: float (lineáris módhoz)

### 2. WOW score számítás

`src/ifds/sim/wow_freshness.py` — signal_history.parquet-ből számol:
- `count_appearances(ticker, df, lookback_days)` → int
- `days_since_last_appearance(ticker, df)` → int  
- `wow_multiplier(ticker, df)` → float

### 3. Variáns YAML

```yaml
# sim/configs/mode2_freshness_ab.yaml
variants:
  - name: "linear_freshness"
    description: "Current: ×1.5 for signals not seen in 90 days"
    overrides:
      freshness_mode: "linear"
      freshness_bonus: 1.5
  
  - name: "wow_signals"
    description: "U-shaped: New Kid +15%, WOW +10%, Stale -20%, Persistent +5%"
    overrides:
      freshness_mode: "wow"
```

## Kiértékelés

Paired t-test a Mód 2 comparison engine-ből:
- **Elfogadás:** p < 0.05 VAGY ΔP&L > +$500 és ΔWR > +5%
- Ha WOW jobb → élesítés BC20A-ban
- Ha nem szignifikáns → marad linear (egyszerűbb)

## Tesztelés

- `test_wow_freshness.py`: count_appearances, days_since_last, wow_multiplier edge cases
- `test_rescore.py` bővítés: freshness_mode="wow" variant
- `pytest` all green

## Commit

```
feat(sim): add WOW Signals freshness A/B test (T10)

U-shaped freshness scoring: New Kid +15%, WOW (3+ appearances,
recent) +10%, Stale (>30 days) -20%, Persistent (5+) +5%.
Compared against current linear ×1.5 via Mode 2 re-score.
```
