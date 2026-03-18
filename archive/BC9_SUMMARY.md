# BC9 Summary — Options Flow + Shark Detector + Tech Scoring + Post-BC9 Fixes

**Date**: 2026-02-10
**Tests**: 477 passed, 0 failed (6 skipped — pandas not in test env)

---

## Modified Files (BC9 + Post-BC9 Fixes)

### Source (`src/ifds/`)

| File | Changes |
|------|---------|
| `config/defaults.py` | +22 TUNING params (PCR, OTM, block, shark, RSI zones, SMA50, RS SPY); clipping 120→90; sector limit 2→3 |
| `models/market.py` | +fields: TechnicalAnalysis (sma_50, sma50_bonus, rs_vs_spy, rs_spy_score), FlowAnalysis (pcr, pcr_score, otm_call_ratio, otm_score, block_trade_count, block_trade_score), FundamentalScoring (shark_detected), StockAnalysis (shark_detected), PositionSizing (shark_detected) |
| `data/fmp.py` | +screener URL debug logging (stderr, API key redacted); +`get_sector_mapping()` exchange param removed |
| `data/polygon.py` | +`get_options_snapshot()` with FileCache support |
| `data/adapters.py` | +`_aggregate_dp_records()` returns `block_trade_count`; +options snapshot adapter |
| `data/async_clients.py` | +`AsyncPolygonClient.get_options_snapshot()`; async gather 5 calls (growth, metrics, insider, dp, options) |
| `data/async_adapters.py` | +async options snapshot adapter; +block_trade_count in DP aggregation |
| `phases/phase2_universe.py` | `isEtf: False` → `"false"` (string); +screener request/response debug logging; +isActivelyTrading filter logging; +earnings calendar count logging |
| `phases/phase4_stocks.py` | +PCR scoring, +OTM call ratio, +block trade scoring, +shark detector, +RSI ideal zone (replaces old ±5), +SMA50 bonus, +RS vs SPY scoring, +tech score debug logging (sync+async); tech score = rsi+sma50+rs (no base 50) |
| `phases/phase6_sizing.py` | freshness cap `min(100.0, ...)` restored; sort by `original_score`; +shark_detected on PositionSizing |
| `output/execution_plan.py` | clipping reason text updated; tech_score = no base 50; +SHARK flag in trade_plan |
| `output/console.py` | clipping display updated to 90 |

### Tests (`tests/`)

| File | Changes |
|------|---------|
| `test_bc9_scoring.py` | 30 new tests: PCR, OTM, block trades, shark detector, RSI zones, SMA50, RS SPY, combined score |
| `test_phase4.py` | Combined score assertions updated (tech base 50 removed); clipping >120→>90 |
| `test_phase6.py` | Freshness cap restored to 100; +ranking preservation test; sector limit 2→3 |
| `test_phase2.py` | `isEtf` assertion `is False` → `== "false"` |
| `test_monitoring_csv.py` | Clipping reason text; tech sub-score no base |

---

## New Features (BC9)

1. **Options Flow Scoring** (Phase 4 flow score extension)
   - PCR < 0.7 → +15, PCR > 1.3 → -10
   - OTM Call Ratio > 40% → +10
   - Block trades ($500K+): >5 → +10, >20 → +15

2. **Shark Detector** (Phase 4 funda score extension)
   - 2+ unique insiders bought within 10 days, $100K+ total → +10
   - SHARK flag in trade_plan CSV

3. **Tech Scoring Overhaul**
   - RSI Ideal Zone: [45-65] → +30, [35-45)/(65-75] → +15, else → 0
   - SMA50: price > SMA50 → +30
   - RS vs SPY: ticker 3-month return > SPY 3-month return → +40
   - Tech score range: 0-100 (no base 50)

4. **isEtf Bug Fix** — `False` (boolean) → `"false"` (string) for FMP API
5. **Sector Limit** — 2 → 3 positions per sector
6. **Score Differentiation** — sort by `original_score` (pre-freshness), cap at 100
7. **Clipping Threshold** — 120 → 90 (crowded trade filter)
8. **Debug Logging** — FMP screener URL, request params, response counts, tech score breakdown

---

## Known Open Issues

1. **Universe Size Gap**: FMP screener returns ~660 tickers (v2) vs ~1400 (v13 historical). The `isEtf` fix recovered from 389→660, but the gap to 1400 remains. Likely FMP API-side data change or v13 had different timing. The `isActivelyTrading` post-filter currently removes 0 tickers.

2. **Tech Score = 100 Prevalence**: Most ACCEPTED tickers have tech=100 (SMA50+RSI+RS all maxed). This is expected for bull-market uptrend stocks — a ticker above SMA200 (trend filter) is likely also above SMA50, in RSI sweet spot, and outperforming SPY. Need to verify RS vs SPY calculation is working correctly (not always returning true).

3. **RS vs SPY Debug Needed**: The `rs_spy_score` may always be +40 if the 3-month return comparison is too broad. Tech score debug logging added (Phase 4 async path) but not yet verified in live run output.

4. **Clipping = 0**: With tech base removed, combined scores dropped ~15 points. Clipping threshold 90 now never triggers (max practical score ~90). May need threshold recalibration to 80-85.

5. **Score < 70 = 241**: Many tickers fall below minimum. The 70 threshold may need adjustment to 55-60 given the new score range.

---

## V13 Overlap Status

From live run comparison with v13 reference output:

- **SDRL**: Match — appears in both v13 and v2 output
- **CDE, PAAS, ENPH**: ACCEPTED in Phase 4 but excluded by sector limit (3 per sector) or position limit (max 8)
- **Technology sector**: Vetoed (laggard) — v13 tech stocks excluded
- **Score ranges**: v2 range 78-90 vs v13 range 70-95 — tighter due to tech score normalization

---

## Next Steps

1. **RS vs SPY verification**: Check log output — is `rs_spy_score=40` on every ticker? If yes, the 3-month return comparison may need fixing.
2. **Threshold recalibration**: `combined_score_minimum` 70→55-60, `clipping_threshold` 90→80-85 given new score range.
3. **Circuit breaker per-provider**: Auto-halt on >20% error rate (UW 429s visible in live runs).
4. **FileCache enablement**: Test with `IFDS_CACHE_ENABLED=true` for production runs.
5. **Pandas installation**: Enable freshness tests (6 currently skipped).
