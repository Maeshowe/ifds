Status: DONE
Updated: 2026-04-03
Note: BC20 Phase_20A — SIM-L2 Mód 2 Re-Score Engine

# BC20 Phase_20A — SIM-L2 Mód 2 Re-Score Engine

## Cél

Re-Score engine ami a Phase 4 snapshot-okból (~31 nap, feb 19 – ápr 2) újraszámolja
a Phase 6 scoring-ot eltérő config-okkal. Ez teszi lehetővé, hogy tudományosan
mérjük az EWMA, MMS, M_target, BMI guard stb. hatását.

## Háttér

A Mód 1 (BC19, `replay.py`) a kész execution plan CSV-kből indul és csak a bracket
paramétereket (TP/SL ATR multiples, max_hold_days) variálja. A Mód 2 **visszamegy
a Phase 4 intermediate data-ig** és újraszámolja a scoring-ot + sizing-ot is.

## Scope

### 1. `src/ifds/sim/rescore.py` — Új fájl

```python
def rescore_snapshot(
    snapshot_records: list[dict],     # Phase 4 snapshot (load_phase4_snapshot output)
    config_overrides: dict,           # TUNING/CORE override-ok
    macro_override: dict | None,      # VIX, TNX felülírás (opcionális)
    gex_data: dict | None,           # {ticker: GEXAnalysis-like dict} (ha nincs → mock)
    mms_data: dict | None,           # {ticker: MMSAnalysis-like dict}
) -> list[PositionSizing]:
    """Re-score Phase 4 snapshot data with different config.
    
    1. Rebuild StockAnalysis objects from snapshot dicts
    2. Apply config overrides (EWMA enabled/disabled, weights, thresholds)
    3. Recalculate combined_score with new weights/bonuses
    4. Run Phase 6 sizing logic with overridden config
    5. Return sized positions
    """
```

### 2. Snapshot → StockAnalysis konverzió

A `phase4_snapshot.py` `_stock_to_dict()` output-ját vissza kell konvertálni:

```python
def snapshot_to_stock_analysis(record: dict) -> StockAnalysis:
    """Reconstruct StockAnalysis from Phase 4 snapshot dict."""
    # Build TechnicalAnalysis, FlowAnalysis, FundamentalAnalysis
    # from flat dict fields (price, sma_200, rvol, etc.)
```

### 3. Score újraszámolás

A jelenlegi scoring logika `phase4_stocks.py` `_calculate_combined_score()`-ban van.
A rescore engine-nek ezt kell reprodukálnia, de override-olható paraméterekkel:

- `weight_flow`, `weight_fundamental`, `weight_technical`
- `ewma_enabled`, `ewma_span`
- `target_overshoot_enabled`, `target_overshoot_threshold`
- `crowdedness_shadow_enabled` → élesítés szimuláció
- `mms_regime_multipliers` → más multiplier értékek

### 4. `replay.py` bővítés — Mód 2 branch

```python
def run_mode2_comparison(
    variants: list[SimVariant],
    snapshot_dir: str = "state/phase4_snapshots",
    polygon_api_key: str | None = None,
    cache_dir: str | None = None,
) -> ComparisonReport:
    """Run Mode 2: re-score snapshots with different configs, then simulate.
    
    For each variant:
      1. Load all snapshots
      2. For each day: rescore → sized positions → Trade objects
      3. Fetch bars + simulate brackets
      4. Aggregate results
    """
```

### 5. Variáns config YAML

```yaml
# sim/configs/mode2_baseline_vs_ewma.yaml
variants:
  - name: "baseline_no_ewma"
    description: "Pre-BC18: no EWMA, no MMS, no M_target"
    overrides:
      ewma_enabled: false
      mms_enabled: false
      target_overshoot_enabled: false
      bmi_momentum_guard_enabled: false
  
  - name: "current_config"
    description: "Current production config (EWMA + MMS + M_target + BMI guard)"
    overrides: {}  # use defaults
  
  - name: "aggressive_mms"
    description: "Tighter MMS multipliers"
    overrides:
      mms_regime_multipliers:
        gamma_positive: 1.75
        gamma_negative: 0.15
        dark_dominant: 1.5
```

## GEX/MMS adat probléma

A Phase 4 snapshot nem tartalmaz GEX/MMS adatot (Phase 5 output).
Opciók:
- **A) Mock GEX** — `gex_multiplier=1.0`, `gex_regime="neutral"` minden ticker-nek.
  Ez izoláltan méri a scoring változás hatását, GEX nélkül.
- **B) Phase 5 snapshot is menteni** — új `phase5_snapshot.py`. Több adat, de
  retroaktívan nincs (csak az új napokra).

**Javaslat:** Approach A (mock GEX) most — a scoring hatás a lényeg.
Approach B a BC20A SimEngine scope-ba illeszthető.

## Tesztelés

- `test_rescore.py`:
  - snapshot_to_stock_analysis round-trip: dict → StockAnalysis → dict == eredeti
  - rescore_snapshot: ewma_enabled=True vs False → eltérő score-ok
  - rescore_snapshot: mms_enabled=True, gamma_negative ticker → kisebb pozíció
  - run_mode2_comparison: 2 variáns, 3 nap snapshot → ComparisonReport non-empty
- Meglévő SIM tesztek: `pytest tests/sim/` all green

## Fájlok

| Fájl | Változás |
|------|---------|
| `src/ifds/sim/rescore.py` | ÚJ — rescore engine |
| `src/ifds/sim/replay.py` | Mód 2 branch hozzáadás |
| `src/ifds/sim/models.py` | SimVariant.mode field (opcionális) |
| `src/ifds/data/phase4_snapshot.py` | `snapshot_to_stock_analysis()` hozzáadás |
| `sim/configs/mode2_*.yaml` | Variáns config fájlok |
| `tests/sim/test_rescore.py` | ÚJ — rescore tesztek |

## Commit

```
feat(sim): add SIM-L2 Mode 2 re-score engine

Re-score Phase 4 snapshots with different config overrides
(EWMA, MMS, M_target, BMI guard) to measure feature impact
scientifically. 31 days of snapshot data available (Feb 19 - Apr 2).
Mock GEX used for isolated scoring analysis.
```
