# IFDS — Institutional Flow Decision Suite

Multi-factor quantitative trading system for US equities (swing trading).
Daily EOD signal generation through a 6-phase pipeline analyzing institutional flows,
gamma exposure, and fundamental quality. Outputs 5-8 sized positions with bracket orders.

## Pipeline

| Phase | Name | What it does |
|-------|------|-------------|
| 0 | Diagnostics | API health check, VIX/TNX macro regime, circuit breaker |
| 1 | Market Regime | Big Money Index (BMI) — LONG/SHORT strategy mode |
| 2 | Universe | FMP screener (~3,000 tickers), earnings exclusion, danger zone filter |
| 3 | Sectors | 11-sector rotation scoring, per-sector BMI, breadth analysis |
| 4 | Stock Analysis | Multi-factor scoring: technical + flow + fundamental (async) |
| 5 | GEX + MMS | Gamma exposure regimes, Market Microstructure Scorer (async) |
| 6 | Sizing | Risk-adjusted position sizing, 6 multipliers, sector diversification |

Output: `execution_plan.csv` + `full_scan_matrix.csv` + `trade_plan.csv` + Telegram alert.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test,freshness]"
```

### Environment variables

Create `.env` in the project root:

```bash
# Required API keys
IFDS_POLYGON_API_KEY=your_key
IFDS_FMP_API_KEY=your_key
IFDS_FRED_API_KEY=your_key

# Optional API keys
IFDS_UW_API_KEY=your_key              # Unusual Whales (has Polygon fallback)
IFDS_TELEGRAM_BOT_TOKEN=your_token    # Daily alerts
IFDS_TELEGRAM_CHAT_ID=your_chat_id

# Runtime
IFDS_ASYNC_ENABLED=true               # Async phases 1/4/5 (default: false)
IFDS_CACHE_ENABLED=true               # File-based API cache (default: false)
IFDS_CACHE_DIR=data/cache             # Cache directory

# Tuning overrides (optional)
IFDS_ACCOUNT_EQUITY=100000            # Account equity ($)
IFDS_RISK_PER_TRADE_PCT=1.0           # Risk per trade (%)
IFDS_MAX_POSITIONS=8                  # Max simultaneous positions
IFDS_CIRCUIT_BREAKER_LIMIT=5.0        # Drawdown circuit breaker (%)
IFDS_OUTPUT_DIR=output                # CSV output directory
IFDS_LOG_DIR=logs                     # Log directory
```

## Usage

```bash
source .env

# Full pipeline run
python -m ifds run

# Config + API validation only
python -m ifds run --dry-run

# Forward validation (SIM-L1)
python -m ifds validate --days 10

# Parameter sweep comparison (SIM-L2)
python -m ifds compare --config sim_variants_test.yaml
```

### Production (cron)

```bash
# Mac Mini cron 22:00 CET Mon-Fri
scripts/deploy_daily.sh
```

The deploy script runs pytest pre-flight, executes the pipeline,
and sends Telegram alerts on success or failure.

## Testing

```bash
python -m pytest tests/ -q
```

1054+ tests, 0 failures (2026-03-28). Tests are mandatory before every commit.

## Project Structure

```
src/ifds/
  config/         Config loader + validator (CORE/TUNING/RUNTIME)
  phases/         Phase 0-6 implementations
  data/           API clients (Polygon, FMP, UW, FRED), cache, adapters
  sim/            SimEngine — L1 forward validation, L2 parameter sweep
  models/         All dataclasses and enums
  output/         CSV generation, console dashboard, Telegram
  pipeline/       Pipeline orchestrator
  utils/          Atomic write helpers, trading calendar

scripts/
  deploy_daily.sh           Cron entrypoint (pytest pre-flight + pipeline)
  paper_trading/            IBKR paper trading (submit, close, eod, nuke, monitor, avwap, gateway)

tests/                      55+ test modules
docs/
  IDEA.md                   Business specification
  PIPELINE_LOGIC.md         All formulas and thresholds
  PARAMETERS.md             Full parameter reference

state/                      Persistent state (JSON, Parquet, MMS store)
output/                     Daily CSV outputs
```

## API Providers

| Provider | What | Tier |
|----------|------|------|
| Polygon | OHLCV bars, options chains | Advanced + Developer |
| FMP | Fundamentals, earnings, screener | Ultimate |
| Unusual Whales | Dark pool flows, GEX | Basic |
| FRED | VIX, Treasury yields (TNX) | Free |

## Documentation

- [IDEA.md](docs/IDEA.md) — Full business and functional specification
- [PIPELINE_LOGIC.md](docs/PIPELINE_LOGIC.md) — Phase formulas, thresholds, classification rules
- [PARAMETERS.md](docs/PARAMETERS.md) — Complete parameter reference (CORE/TUNING/RUNTIME)

## Status

- **Version**: 2.0.0a1
- **Python**: 3.11+
- **Tests**: 1054+ passing
- **Production**: Mac Mini daily cron (22:00 CET)
- **Paper trading**: IBKR paper account (DUH118657), Day 30/63
