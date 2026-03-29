<!-- Generated: 2026-03-29 | Files scanned: 14 | Token estimate: ~800 -->

# Data Layer

## API Clients

```
BaseAPIClient (base.py, 157 lines)         AsyncBaseAPIClient (async_base.py, 160 lines)
  ├─ PolygonClient (polygon.py, 170)         ├─ AsyncPolygonClient
  ├─ FMPClient (fmp.py, 261)                 ├─ AsyncFMPClient
  ├─ UnusualWhalesClient (uw.py, 163)        ├─ AsyncUWClient
  └─ FREDClient (fred.py, 120)               └─ AsyncFREDClient
                                              (all in async_clients.py, 382 lines)
```

## API Provider Map

| Provider | Data | Used In |
|----------|------|---------|
| Polygon | Bars, options snapshot, aggregates | Phase 0/1/3/4/5, SIM |
| FMP | Screener, fundamentals, insider | Phase 2/4 |
| Unusual Whales | Dark pool, GEX, flow, options | Phase 4/5 |
| FRED | VIX (VIXCLS), TNX, T10Y2Y yield curve | Phase 0/1/6 |

## Async Semaphores

```
polygon=10, fmp=8, uw=5, max_tickers=10
```

## Adapters

`src/ifds/data/adapters.py` (491 lines) — transforms raw API responses to domain types
`src/ifds/data/async_adapters.py` (336 lines) — async versions (GEX, DarkPool batch)

## Persistence

| Store | Path | Format | Purpose |
|-------|------|--------|---------|
| FileCache | `cache/` | JSON | API response cache (TTL-based) |
| MMS Store | `state/mms/{ticker}.json` | JSON | Per-ticker MMS feature history |
| Phase4 Snapshot | `state/snapshots/{date}.json` | JSON | Daily Phase 4 data for SIM-L2 replay |
| Signal Dedup | `state/signals.json` | JSON | Signal deduplication (BC11) |
| EWMA State | `state/ewma_scores.json` | JSON | Score smoothing persistence |
| Cumulative PnL | `state/cumulative_pnl.json` | JSON | Paper trading running totals |

## Circuit Breaker

`src/ifds/data/circuit_breaker.py` — ProviderCircuitBreaker
- Per-provider failure tracking
- Trip threshold → skip provider for cooldown period

## Key Files

| File | Lines | Purpose |
|------|-------|---------|
| adapters.py | 491 | Raw API → domain type transforms |
| async_clients.py | 382 | 4 async API clients |
| async_adapters.py | 336 | Async GEX/DarkPool adapters |
| fmp.py | 261 | FMP REST client |
| polygon.py | 170 | Polygon REST client |
| unusual_whales.py | 163 | UW REST client |
| async_base.py | 160 | aiohttp + semaphore base |
| base.py | 157 | requests base client |
| mms_store.py | ~120 | MMS feature JSON store |
| cache.py | ~130 | File-based cache with TTL |
| phase4_snapshot.py | ~100 | Daily snapshot persistence |
