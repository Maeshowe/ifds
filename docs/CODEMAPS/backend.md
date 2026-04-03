<!-- Generated: 2026-04-03 | Files scanned: 64 | Token estimate: ~950 -->

# Backend — Pipeline & Phases

## Pipeline Orchestrator

`src/ifds/pipeline/runner.py` (~700 lines)
```
run_pipeline(phase?, dry_run?, config_path?)
  → Trading day guard (NYSE holiday → skip)
  → Phase 0: run_phase0() → DiagnosticsResult + MacroRegime + CrossAssetRegime
  → Phase 1: run_phase1() → Phase1Result (BMI, regime)
  → Phase 2: run_phase2() → Phase2Result (Ticker[])
  → Phase 3: run_phase3() → Phase3Result (SectorScore[], breadth)
  ── if --phases 1-3: save context + send_macro_snapshot() ──
  ── if --phases 4-6: load context ──
  → Phase 4: run_phase4() → Phase4Result (StockAnalysis[])
  → Phase 5: run_phase5() → Phase5Result (GEXAnalysis[], MMSAnalysis[])
  → Phase 6: run_phase6() → Phase6Result (PositionSizing[])
    guards: BMI momentum, cross-asset override, skip day shadow
    limits: corr guard, VaR trim
  ── send_trading_plan() or send_daily_report() ──
```

## Phase Details

| Phase | File | Lines | Async | Key Output |
|-------|------|-------|-------|------------|
| 0 | phase0_diagnostics.py | ~500 | no | MacroRegime (VIX, TNX, cross-asset) |
| 1 | phase1_regime.py | ~560 | yes | BMI, strategy mode |
| 2 | phase2_universe.py | ~400 | no | Ticker[] (screened, filtered) |
| 3 | phase3_sectors.py | ~650 | no | SectorScore[], breadth |
| 4 | phase4_stocks.py | ~1150 | yes | StockAnalysis[] (combined_score) |
| 5-GEX | phase5_gex.py | ~640 | yes | GEXAnalysis[] |
| 5-MMS | phase5_mms.py | ~720 | no | MMSAnalysis[] (8 regimes, U score) |
| 6 | phase6_sizing.py | ~900 | no | PositionSizing[] |
| VWAP | vwap.py | ~150 | yes | {ticker: vwap} entry quality |

## Phase 6 Sizing Pipeline

```
candidates (Phase 4 passed + GEX joined)
  → freshness alpha (×1.5 new signals)
  → EWMA smoothing (span=10)
  → VWAP guard (REJECT >2%, REDUCE >1%)
  → _calculate_position() per ticker:
      M_total = M_flow × M_insider × M_funda × M_gex × M_vix × M_utility × M_target
      clamped [0.25, 2.0]
      qty = floor(risk / stop_distance × M_total)
  → _apply_position_limits():
      1. max_positions (8, or BMI guard → 5, or CRISIS → 4)
      2. sector diversification (max 3/sector)
      3. sector group correlation guard (cyclical ≤5, commodity ≤3, etc.)
      4. risk cap, exposure cap
  → portfolio VaR trim (>3% → remove weakest)
```

## Simulation Engine

`src/ifds/sim/` (9 files):
```
broker_sim.py:  simulate_bracket_order() + simulate_swing_trade()
                swing: TP1 50% partial, trail, breakeven, max hold D+5
                VWAP filter, MMS VOLATILE tighter trail (0.75×ATR)
rescore.py:     Mode 2 re-score from Phase 4 snapshots (config overrides)
                _rescore_combined_score(), _calculate_sizing()
                freshness_mode: "linear" | "wow" | "none"
wow_freshness:  U-shaped: New Kid ×1.15, WOW ×1.10, Stale ×0.80
replay.py:      Mode 1 (bracket params) + Mode 2 (re-score snapshots)
comparison.py:  paired t-test between variants
validator.py:   CSV loading, Polygon bar fetch, sim_mode dispatch
models.py:      Trade (+ swing fields), SimVariant (+ mode), ComparisonReport
report.py:      console + CSV output
```

## Risk Layer

`src/ifds/risk/` (3 files):
```
cross_asset.py:  HYG/IEF + RSP/SPY + IWM/SPY(conditional) + 2s10s yield curve
                 → NORMAL / CAUTIOUS / RISK_OFF / CRISIS
                 VIX threshold shift (-1/-3/-5), max_pos override, min_score override
portfolio_var.py: parametric VaR = sqrt(sum(VaR_i²))
                  trim_positions_by_var() — remove weakest if >3%
```

## State Management

`src/ifds/state/` (4 files):
```
position_tracker.py:  OpenPosition + PositionTracker (JSON CRUD, atomic write)
                      add, remove, update, get_expired, get_earnings_risk
swing_manager.py:     run_swing_management() → list[SwingDecision]
                      breakeven (0.3×ATR), trail activation, max hold D+5 MOC
history.py:           BMI history persistence
```
