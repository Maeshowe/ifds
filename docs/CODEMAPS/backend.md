<!-- Generated: 2026-03-29 | Files scanned: 55 | Token estimate: ~950 -->

# Backend — Pipeline & Phases

## Pipeline Orchestrator

`src/ifds/pipeline/runner.py` (542 lines)
```
run_pipeline(phase?, dry_run?, config_path?)
  → Config(config_path) → validate
  → Phase 0: run_phase0(config, logger) → DiagnosticsResult
  → Phase 1: run_phase1(config, logger, vix, tnx) → Phase1Result
  → Phase 2: run_phase2(config, logger, bmi_regime) → Phase2Result
  → Phase 3: run_phase3(config, logger, tickers, vix, tnx) → Phase3Result
  → Phase 4: run_phase4(config, logger, tickers, sectors) → Phase4Result
  → Phase 5: run_phase5(config, logger, stocks, macro) → Phase5Result
  → Phase 6: run_phase6(config, logger, stocks, gex, macro, sectors) → Phase6Result
  → Output: CSVs + Telegram + Console
```

## Phase Details

| Phase | File (lines) | Input | Output | Async |
|-------|-------------|-------|--------|-------|
| 0 | phase0_diagnostics.py (411) | config | DiagnosticsResult (VIX, TNX, macro) | no |
| 1 | phase1_regime.py (561) | config, VIX, TNX | Phase1Result (BMI, regime) | yes |
| 2 | phase2_universe.py (398) | config, BMI regime | Phase2Result (Ticker[]) | no |
| 3 | phase3_sectors.py (652) | config, tickers | Phase3Result (SectorScore[], breadth) | no |
| 4 | phase4_stocks.py (1147) | config, tickers, sectors | Phase4Result (StockAnalysis[]) | yes |
| 5-GEX | phase5_gex.py (638) | config, stocks, macro | Phase5Result (GEXAnalysis[]) | yes |
| 5-MMS | phase5_mms.py (718) | store history, bars, options | MMSAnalysis (regime, unusualness) | no |
| 6 | phase6_sizing.py (822) | config, stocks, GEX, macro | Phase6Result (PositionSizing[]) | no |

## Key Phase Functions

**Phase 4** (largest — 1147 lines):
- `run_phase4()` → per-ticker: flow + funda + tech scoring
- `_calculate_combined_score()`: 0.40×flow + 0.30×funda + 0.30×tech + sector_adj + insider_mult
- `_calculate_rsi()`, `_calculate_atr()`, `_calculate_sma()`
- `_calculate_insider_score()` — insider transaction analysis

**Phase 5 MMS** (Market Microstructure Scorer):
- 8 regimes: VOLATILE, Γ⁺, Γ⁻, DD, ABS, DIST, NEU, UND
- `_compute_z_scores()` → 63-day rolling, min 21 obs
- `_compute_factor_volatility()` → σ_20 weighting
- `_compute_unusualness()` → U ∈ [0,100]

**Phase 6** (Position Sizing):
- `_calculate_multiplier_total()`: M_flow × M_insider × M_funda × M_gex × M_vix × M_utility [0.25, 2.0]
- `_apply_freshness_alpha()` → uncapped freshness bonus
- `_calculate_position()` → qty, bracket (entry/stop/TP1/TP2)
- `_apply_position_limits()` → max exposure, BMI momentum guard

## Simulation Engine

`src/ifds/sim/` (6 files, ~1300 lines total):
```
validator.py:   validate_execution_plans() → load CSVs → fetch bars → simulate
broker_sim.py:  bracket simulation (33/66% TP1/TP2 split)
replay.py:      L2 parameter sweep over historical snapshots
comparison.py:  paired t-test between baseline vs challenger
models.py:      Trade, ValidationSummary, SimVariant, ComparisonReport
report.py:      console + CSV + JSON output
```

## CLI Commands

`src/ifds/cli.py` (181 lines):
```
python -m ifds run [--phase N] [--dry-run]
python -m ifds validate [--days N]
python -m ifds compare --config sim_variants_test.yaml
```
