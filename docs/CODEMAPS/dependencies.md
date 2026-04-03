<!-- Generated: 2026-04-03 | Files scanned: 64 src + 20 scripts | Token estimate: ~700 -->

# Dependencies & Integrations

## External APIs

| Service | Purpose | Auth | Rate Limit |
|---------|---------|------|------------|
| Polygon.io | Bars, options, aggregates, ETF data | API key (.env) | Sem=10 |
| FMP | Screener, fundamentals, insider, earnings | API key (.env) | Sem=8 |
| Unusual Whales | Dark pool, GEX, flow, options | API key (.env) | Sem=5 |
| FRED | VIX, TNX, T10Y2Y yield curve | API key (.env) | Low |
| IBKR TWS/Gateway | Paper trading orders | Port 4002 | clientId |
| Telegram Bot API | Macro snapshot + trading plan | Bot token (.env) | — |

## Python Dependencies

| Package | Purpose |
|---------|---------|
| aiohttp | Async HTTP client |
| requests | Sync HTTP client |
| colorama | CLI dashboard colors |
| exchange_calendars | NYSE trading calendar (holidays, early close) |
| scipy | Paired t-test (SIM-L2 comparison) |
| pyyaml | SIM variant config loading |
| ib_insync | IBKR TWS/Gateway connection (PT scripts only) |
| pandas (optional) | Freshness alpha, EWMA, parquet I/O |

## Paper Trading Scripts

| Script | ClientId | Cron (Budapest) | Purpose |
|--------|----------|-----------------|---------|
| check_gateway.py | 17 | 15:30 | IBKR health check |
| deploy_intraday.sh | — | 15:45 | Phase 4-6 + submit_orders |
| pt_monitor.py | 15 | */5 16-21 | Trail SL + TP1 detection |
| close_positions.py | 11 | 21:40 (+ 18:40 early) | Swing management |
| eod_report.py | 12 | 22:05 | P&L + Telegram |
| monitor_positions.py | 14 | 10:10 | Leftover check |
| nuke.py | 13 | manual | Emergency close all |

**Removed from cron (2026-04-06):**
- submit_orders.py (standalone) → merged into deploy_intraday.sh
- pt_avwap.py → MKT entry, VWAP guard in Phase 6

## Config Structure

`src/ifds/config/defaults.py` (~450 lines):
- **CORE**: Weights, ATR multiples, freshness params (algorithm constants)
- **TUNING**: Thresholds, multipliers, guards, cross-asset, correlation, VaR (operator-adjustable)
- **RUNTIME**: API keys, account equity, async flags, file paths (environment-specific)

Key env vars: `IFDS_POLYGON_API_KEY`, `IFDS_FMP_API_KEY`, `IFDS_UW_API_KEY`, `IFDS_ASYNC_ENABLED`

## Key Metrics

| Metric | Value |
|--------|-------|
| Source files | 64 (src/ifds/) |
| Source lines | ~16K |
| Test files | 81 |
| Tests passing | 1291 |
| API providers | 4 + IBKR + Telegram |
| Pipeline phases | 7 (0-6, split) |
| Async phases | 1, 4, 5 |
| SIM modes | bracket + swing |
| Risk layers | cross-asset + corr guard + VaR |
