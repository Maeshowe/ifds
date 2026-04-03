<!-- Generated: 2026-04-03 | Files scanned: 15 data + 4 state | Token estimate: ~800 -->

# Data Layer

## API Clients

```
BaseAPIClient (base.py)              AsyncBaseAPIClient (async_base.py)
  ├─ PolygonClient (polygon.py)       ├─ AsyncPolygonClient
  ├─ FMPClient (fmp.py)               ├─ AsyncFMPClient
  ├─ UnusualWhalesClient (uw.py)      ├─ AsyncUWClient
  └─ FREDClient (fred.py)             └─ AsyncFREDClient
                                       (async_clients.py)
```

## API Provider Map

| Provider | Data | Used In | Semaphore |
|----------|------|---------|-----------|
| Polygon | Bars, options, aggregates, VIX, ETF bars | Phase 0/1/3/4/5, SIM, VWAP | 10 |
| FMP | Screener, fundamentals, insider, earnings | Phase 2/4 | 8 |
| Unusual Whales | Dark pool, GEX, flow, options | Phase 4/5 | 5 |
| FRED | VIX (VIXCLS), TNX, T10Y2Y yield curve | Phase 0 | low |

## Persistence

| Store | Path | Format | Purpose |
|-------|------|--------|---------|
| FileCache | `data/cache/` | JSON | API response TTL cache |
| MMS Store | `state/mms/{ticker}.json` | JSON | Per-ticker MMS features (rolling 63d) |
| Phase4 Snapshot | `state/phase4_snapshots/{date}.json.gz` | gzipped JSON | SIM-L2 Mode 2 rescore input |
| Phase 1-3 Context | `state/phase13_ctx.json.gz` | gzipped JSON | Pipeline split bridge |
| EWMA State | `state/ewma_scores.json` | JSON | Score smoothing persistence |
| Signal Dedup | `state/signal_hashes.json` | JSON | Daily dedup (BC11) |
| Signal History | `state/signal_history.parquet` | Parquet | Freshness alpha lookback |
| PositionTracker | `state/open_positions.json` | JSON | Swing position state |
| BMI History | `state/bmi_history.json` | JSON | BMI momentum guard |
| Skip Day Shadow | `state/skip_day_shadow.jsonl` | JSONL | Shadow guard log |
| Cumulative PnL | `scripts/paper_trading/logs/cumulative_pnl.json` | JSON | PT running totals |

## Logging

| Type | Path | Format |
|------|------|--------|
| Pipeline events | `logs/ifds_run_*.jsonl` | Structured JSONL |
| PT script logs | `logs/pt_{name}_{YYYY-MM-DD}.log` | Daily rotated text |
| PT business events | `logs/pt_events_{YYYY-MM-DD}.jsonl` | Unified JSONL |
| Event database | `state/pt_events.db` | SQLite (daily import) |
| Cron logs | `logs/cron_*.log` | Text |

## Key Data Transforms

```
Phase 4 snapshot: StockAnalysis → _stock_to_dict() → 38-field flat dict → JSON
                  reverse: snapshot_to_stock_analysis() → StockAnalysis

Phase 1-3 context: PipelineContext → save_phase13_context() → gzipped JSON
                   reverse: load_phase13_context() → PipelineContext fields

Cross-asset ratios: Polygon ETF bars → {hyg_ief: [ratios], rsp_spy: [...]}
                    → calculate_cross_asset_regime() → CrossAssetResult
```
