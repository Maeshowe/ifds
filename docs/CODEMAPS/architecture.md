<!-- Generated: 2026-03-29 | Files scanned: 55 src + 14 scripts | Token estimate: ~900 -->

# IFDS Architecture

## System Overview

Single-app Python 3.12 quantitative trading pipeline (swing trading, US equities).
6-phase sequential pipeline + simulation engine + paper trading scripts.

```
                    ┌──────────────────────────────┐
                    │     Mac Mini (Production)     │
                    │  cron 22:00 CET → pipeline    │
                    │  IBKR Gateway → paper trading │
                    └──────────────┬───────────────┘
                                   │
  ┌────────────────────────────────┼────────────────────────────────┐
  │                          Pipeline                               │
  │  Phase0 → Phase1 → Phase2 → Phase3 → Phase4 → Phase5 → Phase6 │
  │  diag     regime   universe sectors  stocks   GEX/MMS  sizing  │
  └────────────────────────────────┼────────────────────────────────┘
                                   │
                    ┌──────────────┴───────────────┐
                    │          Output               │
                    │  3 CSVs + Telegram + Console  │
                    └──────────────────────────────┘
```

## Entry Points

| Entry | Path | Purpose |
|-------|------|---------|
| CLI | `src/ifds/cli.py` → `__main__.py` | `python -m ifds run/validate/compare` |
| Pipeline | `src/ifds/pipeline/runner.py` | `run_pipeline()` orchestrator |
| Deploy | `scripts/deploy_daily.sh` | Cron: pytest → pipeline → telegram |
| Paper Trading | `scripts/paper_trading/*.py` | IBKR order lifecycle (8 scripts) |

## Data Flow

```
APIs (Polygon, FMP, UW, FRED)
  ↓ BaseAPIClient / AsyncBaseAPIClient
  ↓ FileCache (TTL-based)
Phase 0: VIX + TNX → MacroRegime
Phase 1: 235 ETFs → BMI ratios → BMIRegime (async)
Phase 2: FMP screener → Ticker universe (danger zone filter)
Phase 3: Sector ETFs → SectorScore + BreadthRegime
Phase 4: Per-ticker scoring (flow+funda+tech) → StockAnalysis (async)
Phase 5: GEX regime + MMS classifier → multipliers (async)
Phase 6: Position sizing → PositionSizing[] → 3 CSVs
  ↓
Output: execution_plan.csv, full_scan_matrix.csv, trade_plan.csv
Telegram: HTML daily report
```

## Key Dimensions

| Metric | Value |
|--------|-------|
| Source lines | ~13K (src/ifds/) |
| Script lines | ~2.5K (scripts/paper_trading/) |
| Test files | 55+ |
| Tests passing | 1054+ |
| API providers | 4 (Polygon, FMP, Unusual Whales, FRED) |
| Phases | 7 (0-6) |
| Async phases | 1, 4, 5 |

## Deployment

- **MacBook**: Development (VSCode + Claude Code)
- **Mac Mini**: Production (cron 22:00 CET, IBKR Gateway)
- `scripts/deploy_daily.sh`: source .env → pytest pre-flight → pipeline → telegram
- Git push policy: CC commits, user pushes manually
