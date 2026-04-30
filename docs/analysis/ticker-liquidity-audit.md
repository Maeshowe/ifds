# Ticker Universe Liquidity Audit (First Iteration)

**Generated:** from 43 snapshots (2026-02-19 → 2026-04-17)
**Unique tickers seen:** 1265

## Limitation

This audit measures **data presence + stability** only. Dollar-weighted signal strength (dp_volume, venue_entropy, GEX metrics) is NOT captured because the Phase 4 snapshot does not currently persist these fields. See `docs/tasks/2026-04-XX-phase4-snapshot-enrichment.md` for the follow-up task.

## Category Distribution

| Category | Meaning | Ticker Count | % of Universe |
|----------|---------|--------------|---------------|
| **A** | Signal-rich: stable DP + options + persistent | 2 | 0.2% |
| **B** | Partial: one signal strong, other present | 3 | 0.2% |
| **C** | Noisy: intermittent signal | 1240 | 98.0% |
| **D** | Unusable: rare appearance | 20 | 1.6% |

## Category A — Top 50 by persistence

Tickers that consistently produce institutional data, sorted by number of days seen.

| Ticker | Sector | Days Seen | DP Coverage | Opt Coverage | Avg DP% | Avg Blocks |
|--------|--------|-----------|-------------|--------------|---------|------------|
| LITE | Technology | 26 | 81% | 100% | 0.2% | 2.9 |
| SNDK | Technology | 22 | 95% | 100% | 0.3% | 16.4 |

## Category D — Sample of 30

Tickers where the Phase 4 filter passed them at least once, but institutional data is essentially absent.

| Ticker | Sector | Days Seen | DP Days | Opt Days |
|--------|--------|-----------|---------|----------|
| QMMM | Communication Services | 32 | 0 | 0 |
| AXIA | Utilities | 16 | 0 | 0 |
| SUNC | Energy | 14 | 0 | 0 |
| CEF | Financial Services | 7 | 0 | 0 |
| SOMN | Utilities | 4 | 0 | 0 |
| IX | Financial Services | 4 | 0 | 0 |
| EXG | Financial Services | 3 | 0 | 0 |
| CSAN | Energy | 3 | 0 | 0 |
| TLK | Communication Services | 3 | 0 | 0 |
| NAD | Financial Services | 3 | 0 | 0 |
| BWLP | Industrials | 3 | 0 | 0 |
| ELPC | Utilities | 3 | 0 | 0 |
| RERE | Consumer Cyclical | 2 | 0 | 0 |
| NZF | Financial Services | 2 | 0 | 0 |
| FIHL | Financial Services | 2 | 0 | 0 |
| DNP | Financial Services | 2 | 0 | 0 |
| FLOC | Energy | 2 | 0 | 0 |
| AERO | Industrials | 1 | 0 | 0 |
| IHG | Consumer Cyclical | 1 | 0 | 0 |
| UTF | Financial Services | 1 | 0 | 0 |

## Sector Distribution — Category A

| Sector | Count |
|--------|-------|
| Technology | 2 |

## Recommendation

The **Institutional Relevance Filter** for BC24 should consider restricting the scoring universe to **Category A + B** (5 tickers) from the current ~1700-1800 Phase 2 universe. Category C/D tickers add noise to the scoring without providing reliable institutional signal.

Next step: extend snapshot enrichment to capture dp_volume ($), venue_entropy, and GEX metrics → enables dollar-weighted re-categorization in W18-W19.
