<!-- Generated: 2026-04-03 | Files scanned: 64 src + 20 scripts | Token estimate: ~950 -->

# IFDS Architecture

## System Overview

6-phase quant trading pipeline (US equities, swing trading, 5-day hold).
Split execution: Phase 1-3 at close (22:00), Phase 4-6 at open (15:45 Budapest).

```
MacBook (dev)                    Mac Mini (prod)
├── VSCode + Claude Code         ├── Cron scheduler (scripts/crontab.md)
├── git push ──────────────────→ ├── Pipeline (Phase 0-6, split)
└── tests (1291 passing)         ├── IBKR Gateway (paper: DUH118657)
                                 ├── PT scripts (submit, monitor, close, eod)
                                 └── Telegram (macro snapshot + trading plan)
```

## Pipeline Flow

```
22:00 Budapest (market close):
  Phase 0: Diagnostics → VIX, TNX, 2s10s, Cross-Asset Regime, API health
  Phase 1: BMI Regime   → Big Money Index, strategy mode
  Phase 2: Universe     → FMP screener, earnings exclusion
  Phase 3: Sectors      → ETF momentum, breadth, VETO
  ── save context → state/phase13_ctx.json.gz ──
  ── Telegram: MACRO SNAPSHOT ──

15:45 Budapest (market open + 15min):
  ── load context ──
  Phase 4: Stock Analysis → Multi-factor scoring (flow/funda/tech)
  Phase 5: GEX + MMS      → Gamma, microstructure (8 regimes)
  Phase 6: Sizing          → 7 multipliers, VWAP guard, corr guard, VaR
  ── Telegram: TRADING PLAN → MKT order submission ──

21:40 Budapest:
  Swing close → hold_days++, breakeven, trail, max hold D+5 MOC
```

## Key Modules (src/ifds/, 64 files)

| Module | Purpose | Files |
|--------|---------|-------|
| config/ | CORE/TUNING/RUNTIME defaults, validation | 4 |
| data/ | API clients (Polygon, FMP, UW, FRED), cache | 15 |
| phases/ | Phase 0-6 + VWAP module | 10 |
| risk/ | Cross-asset regime, corr guard, portfolio VaR | 3 |
| sim/ | Bracket + swing sim, rescore, replay, comparison | 9 |
| state/ | PositionTracker, swing manager, history | 4 |
| output/ | Telegram (macro+trading), console, CSV | 4 |
| pipeline/ | Runner, context persistence | 3 |
| models/ | All dataclasses (market.py: 40+ types) | 2 |

## Entry Points

| Entry | Command | What |
|-------|---------|------|
| Full | `python -m ifds run` | Phase 0-6 + full Telegram |
| Split AM | `deploy_daily.sh --phases 1-3` | BMI + sectors + save context |
| Split PM | `deploy_intraday.sh` | Phase 4-6 + submit |
| SIM-L2 | `python -m ifds compare --config X.yaml` | A/B sweep |
| SIM-L1 | `python -m ifds validate --days N` | Forward validation |

## State Files

| File | Writer | Reader |
|------|--------|--------|
| `state/phase13_ctx.json.gz` | Phase 1-3 | Phase 4-6 |
| `state/open_positions.json` | submit, close | swing_manager |
| `state/ewma_scores.json` | Phase 6 | Phase 6 (next day) |
| `state/mms/*.json` | Phase 5 MMS | Phase 5 MMS |
| `state/phase4_snapshots/*.json.gz` | Phase 4 | SIM-L2 rescore |
| `logs/pt_events_*.jsonl` | All PT scripts | events_to_sqlite |
| `state/pt_events.db` | events_to_sqlite | Query tool |
