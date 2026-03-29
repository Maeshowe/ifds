<!-- Generated: 2026-03-29 | Files scanned: 55 | Token estimate: ~500 -->

# Dependencies & Integrations

## External APIs

| Service | Purpose | Auth | Rate Limits |
|---------|---------|------|-------------|
| Polygon.io | Bars, options, aggregates | API key (.env) | Semaphore=10 |
| Financial Modeling Prep | Screener, fundamentals, insider | API key (.env) | Semaphore=8 |
| Unusual Whales | Dark pool, GEX, flow, options | API key (.env) | Semaphore=5 |
| FRED (St. Louis Fed) | VIX, TNX, T10Y2Y | API key (.env) | Low volume |
| IBKR TWS/Gateway | Paper trading orders | Port 4002 | clientId-based |
| Telegram Bot API | Daily report delivery | Bot token (.env) | — |

## Python Dependencies (core)

| Package | Purpose |
|---------|---------|
| aiohttp | Async HTTP client |
| requests | Sync HTTP client |
| colorama | CLI dashboard colors |
| exchange_calendars | NYSE trading calendar |
| scipy | Paired t-test (SIM-L2) |
| pandas (optional) | Freshness alpha, EWMA |

## Internal Integrations

| Component | Communicates With | How |
|-----------|------------------|-----|
| Pipeline runner | All phases | Direct function calls |
| Phase 5 GEX | Phase 5 MMS | MMS overrides gex_multiplier |
| Phase 6 | Phase 4 snapshot | Reads daily snapshots for SIM |
| Paper trading | Pipeline output | Reads execution_plan.csv |
| EOD report | Telegram | Sends daily P&L summary |
| deploy_daily.sh | pytest + pipeline + telegram | Shell orchestration |

## Paper Trading Scripts

| Script | ClientId | Cron (CET) | Purpose |
|--------|----------|------------|---------|
| check_gateway.py | 17 | pre-submit | IBKR health check |
| submit_orders.py | 10 | 15:35 | Place bracket orders |
| pt_monitor.py | 14 | 15:00-21:00 | Position monitoring |
| monitor_trail.py | 15 | 15:00-21:00 | Trailing stop |
| pt_avwap.py | 16 | 15:00-17:00 | AVWAP entry conversion |
| close_positions.py | 11 | 21:40 | MOC close |
| eod_report.py | 12 | 22:05 | EOD P&L + Telegram |
| nuke.py | 13 | manual | Emergency close all |

## Config

All config in `src/ifds/config/defaults.py` (421 lines):
- CORE: API keys, endpoints
- TUNING: thresholds, weights, multipliers
- RUNTIME: async_enabled, mms_enabled, etc.

Env vars: `IFDS_POLYGON_API_KEY`, `IFDS_FMP_API_KEY`, `IFDS_UW_API_KEY`, `IFDS_ASYNC_ENABLED`, etc.
