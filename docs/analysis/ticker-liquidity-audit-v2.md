# Ticker Universe Liquidity Audit v2 (Distribution-first)

**Dataset:** 44 Phase 4 snapshots (2026-02-19 → 2026-04-19), 11791 total records, 1265 unique tickers.

**Average passes per ticker:** 9.3 (out of 44 possible days)

## Key finding

The Phase 4 ticker universe is **highly rotational**: most tickers appear only on a few days, not consistently across weeks. This alone is worth discussing for the scoring design.

## Persistence histogram (days seen out of 44)

| Days seen | Ticker count | % of universe |
|---|---|---|
| 1 day | 151 | 11.9% |
| 2-3 | 208 | 16.4% |
| 4-5 | 121 | 9.6% |
| 6-10 | 293 | 23.2% |
| 11-15 | 201 | 15.9% |
| 16-20 | 184 | 14.5% |
| 21-25 | 100 | 7.9% |
| 26-30 | 6 | 0.5% |
| 31-35 | 1 | 0.1% |
| 36-44 | 0 | 0.0% |

## DP Coverage — among persistent tickers (≥10 days seen, 538 total)

| DP coverage bucket | Ticker count | % |
|---|---|---|
| 0-10% | 497 | 92.4% |
| 10-25% | 28 | 5.2% |
| 25-50% | 7 | 1.3% |
| 50-75% | 1 | 0.2% |
| 75-90% | 2 | 0.4% |
| 90-100% | 3 | 0.6% |

## Options Coverage — among persistent tickers

| Opt coverage bucket | Ticker count | % |
|---|---|---|
| 0-10% | 3 | 0.6% |
| 10-25% | 0 | 0.0% |
| 25-50% | 1 | 0.2% |
| 50-75% | 1 | 0.2% |
| 75-90% | 1 | 0.2% |
| 90-100% | 532 | 98.9% |

## Top 50 institutional-data tickers

Ranked by `days_seen × dp_coverage × opt_coverage`. These are the tickers where the Phase 4 pipeline consistently produces both dark pool and options data.

| # | Ticker | Sector | Days | DP% | Opt% | Avg DP | Avg Blocks | Avg Score |
|---|--------|--------|------|-----|------|--------|------------|-----------|
| 1 | SNDK | Technology | 22 | 95% | 100% | 0% | 16.4 | 81.5 |
| 2 | LITE | Technology | 26 | 81% | 100% | 0% | 2.9 | 80.1 |
| 3 | MU | Technology | 18 | 100% | 100% | 0% | 15.0 | 80.3 |
| 4 | INTC | Technology | 21 | 76% | 100% | 0% | 0.0 | 77.6 |
| 5 | NVDA | Technology | 11 | 100% | 100% | 0% | 31.4 | 86.5 |
| 6 | TSM | Technology | 14 | 71% | 100% | 0% | 1.5 | 81.8 |
| 7 | AAOI | Technology | 20 | 45% | 100% | 0% | 0.0 | 84.2 |
| 8 | WDC | Technology | 21 | 38% | 100% | 0% | 5.6 | 78.8 |
| 9 | ASTS | Technology | 15 | 47% | 100% | 0% | 0.0 | 84.5 |
| 10 | AMD | Technology | 8 | 88% | 100% | 0% | 10.7 | 84.9 |
| 11 | XOM | Energy | 20 | 30% | 100% | 0% | 5.0 | 85.0 |
| 12 | NBIS | Communication Services | 23 | 26% | 100% | 0% | 0.0 | 80.8 |
| 13 | GOOGL | Technology | 9 | 67% | 100% | 0% | 2.5 | 75.3 |
| 14 | CVX | Energy | 21 | 29% | 100% | 0% | 0.0 | 83.8 |
| 15 | VRT | Industrials | 22 | 23% | 100% | 0% | 0.0 | 79.0 |
| 16 | GLW | Technology | 22 | 23% | 100% | 1% | 6.0 | 80.5 |
| 17 | PL | Industrials | 18 | 22% | 100% | 1% | 3.8 | 81.0 |
| 18 | LNG | Energy | 22 | 18% | 100% | 0% | 0.0 | 84.4 |
| 19 | LMT | Industrials | 15 | 27% | 100% | 1% | 7.5 | 83.0 |
| 20 | COHR | Technology | 22 | 18% | 100% | 0% | 0.0 | 80.4 |
| 21 | AG | Basic Materials | 20 | 20% | 100% | 0% | 0.0 | 78.5 |
| 22 | AEM | Basic Materials | 22 | 18% | 100% | 1% | 0.0 | 83.2 |
| 23 | WMT | Consumer Defensive | 16 | 19% | 100% | 0% | 0.0 | 81.4 |
| 24 | TER | Technology | 21 | 14% | 100% | 0% | 0.0 | 83.4 |
| 25 | NEM | Basic Materials | 16 | 19% | 100% | 0% | 0.0 | 80.9 |
| 26 | MRVL | Technology | 14 | 21% | 100% | 0% | 0.0 | 85.1 |
| 27 | HL | Basic Materials | 16 | 19% | 100% | 1% | 0.0 | 83.5 |
| 28 | GOOG | Technology | 9 | 33% | 100% | 0% | 0.0 | 74.5 |
| 29 | GEV | Utilities | 24 | 12% | 100% | 0% | 5.0 | 81.9 |
| 30 | FSLY | Technology | 20 | 15% | 100% | 1% | 0.0 | 82.4 |
| 31 | DELL | Technology | 19 | 16% | 100% | 1% | 10.0 | 87.2 |
| 32 | ASML | Technology | 22 | 14% | 100% | 0% | 10.0 | 83.8 |
| 33 | TSEM | Technology | 9 | 22% | 100% | 0% | 0.0 | 77.9 |
| 34 | TJX | Consumer Cyclical | 12 | 17% | 100% | 0% | 0.0 | 82.2 |
| 35 | STRC | Technology | 16 | 12% | 100% | 3% | 7.5 | 81.7 |
| 36 | RTX | Industrials | 18 | 11% | 100% | 0% | 7.5 | 79.9 |
| 37 | RKLB | Industrials | 12 | 17% | 100% | 0% | 0.0 | 80.4 |
| 38 | RIVN | Consumer Cyclical | 6 | 33% | 100% | 1% | 0.0 | 75.6 |
| 39 | PBR | Energy | 19 | 11% | 100% | 1% | 0.0 | 83.4 |
| 40 | OXY | Energy | 25 | 8% | 100% | 0% | 0.0 | 82.8 |
| 41 | ONTO | Technology | 13 | 15% | 100% | 1% | 0.0 | 78.7 |
| 42 | JNJ | Healthcare | 19 | 11% | 100% | 0% | 0.0 | 79.2 |
| 43 | C | Financial Services | 10 | 20% | 100% | 0% | 0.0 | 81.1 |
| 44 | BTG | Basic Materials | 16 | 12% | 100% | 1% | 0.0 | 79.3 |
| 45 | BCRX | Healthcare | 5 | 40% | 100% | 4% | 0.0 | 85.5 |
| 46 | AXTI | Technology | 10 | 20% | 100% | 0% | 0.0 | 84.7 |
| 47 | AMAT | Technology | 18 | 11% | 100% | 0% | 0.0 | 82.2 |
| 48 | ZETA | Technology | 7 | 14% | 100% | 1% | 0.0 | 87.1 |
| 49 | WH | Consumer Cyclical | 6 | 17% | 100% | 5% | 0.0 | 74.7 |
| 50 | WDS | Energy | 23 | 4% | 100% | 2% | 0.0 | 83.1 |
