# Dark Pool % Retrospective Audit — Live UW Per-Ticker (2026-04-20 → 2026-05-08)

> Read-only. Bypasses production batch provider — fetches `/api/darkpool/{ticker}?date=YYYY-MM-DD` per trade.

## Summary

- Trades audited: **60** (merged by date+ticker)
- With UW data: 60 | no data: 0
- dp_pct range: 1.84% – 31.93%, mean 10.15%, median 8.96%
- Realized P&L range: $-988.00 – $+758.08, mean $-15.36

## Correlation

| Pair | Pearson r (p) | Spearman ρ (p) |
|------|---------------|----------------|
| dp_pct ↔ P&L (\$) | -0.140 (p=0.285) | -0.229 (p=0.078) |
| dp_pct ↔ P&L per share | -0.265 (p=0.041) | -0.327 (p=0.011) |

### Verdict

**Inconclusive** (|r|=0.140, p=0.285) — directional but below significance at n=60. Larger sample needed.

## Quintile breakdown

| Quintile | Range | N | Avg P&L | Median P&L | Win rate |
|----------|-------|---|---------|------------|----------|
| Q1 | 1.84–4.59% | 12 | $+79.09 | $+34.09 | 58% |
| Q2 | 4.60–7.55% | 12 | $-61.92 | $+14.09 | 58% |
| Q3 | 7.80–10.34% | 12 | $+15.92 | $+87.87 | 67% |
| Q4 | 11.33–15.62% | 12 | $-26.03 | $-24.00 | 42% |
| Q5 | 15.74–31.93% | 12 | $-83.86 | $-86.98 | 25% |

**Q5 − Q1 spread**: $-162.95

## Per-trade detail

| Date | Ticker | Sector | Score | Qty | dp_pct | n_rec | dp_vol | total_vol | P&L |
|------|--------|--------|-------|-----|--------|-------|--------|-----------|-----|
| 2026-04-20 | CNK | Communication Services | 94.5 | 452 | 17.76% | 11 | 534,455 | 3,010,119 | $-122.04 |
| 2026-04-20 | DELL | Technology | 93.0 | 44 | 8.83% | 500 | 631,890 | 7,155,113 | $+121.00 |
| 2026-04-20 | GFS | Technology | 94.0 | 189 | 16.46% | 126 | 1,444,982 | 8,778,046 | $-83.16 |
| 2026-04-20 | SCI | Consumer Cyclical | 92.0 | 170 | 3.32% | 14 | 26,354 | 794,922 | $-35.70 |
| 2026-04-20 | SKM | Communication Services | 93.0 | 298 | 5.78% | 31 | 189,041 | 3,270,530 | $-295.02 |
| 2026-04-21 | AMD | Technology | 93.5 | 26 | 2.29% | 500 | 893,615 | 38,950,866 | $+95.16 |
| 2026-04-21 | GME | Consumer Cyclical | 92.5 | 514 | 19.20% | 89 | 1,235,852 | 6,438,173 | $-286.84 |
| 2026-04-21 | POWI | Technology | 95.0 | 206 | 8.66% | 38 | 183,358 | 2,118,163 | $+758.08 |
| 2026-04-22 | ASX | Technology | 93.0 | 499 | 6.74% | 26 | 479,142 | 7,111,468 | $+2.50 |
| 2026-04-22 | CARG | Consumer Cyclical | 93.0 | 399 | 3.78% | 6 | 20,220 | 535,541 | $-171.57 |
| 2026-04-22 | MRVL | Technology | 93.5 | 70 | 4.60% | 500 | 1,416,372 | 30,765,220 | $+242.20 |
| 2026-04-23 | ADI | Technology | 93.5 | 42 | 11.33% | 500 | 503,743 | 4,447,543 | $-26.88 |
| 2026-04-23 | ET | Energy | 91.5 | 1046 | 10.34% | 56 | 690,114 | 6,673,827 | $+31.38 |
| 2026-04-23 | POST | Consumer Defensive | 91.5 | 111 | 4.59% | 12 | 25,651 | 559,394 | $-28.86 |
| 2026-04-23 | POWI | Technology | 95.0 | 148 | 10.01% | 13 | 127,437 | 1,273,690 | $-253.08 |
| 2026-04-23 | WMT | Consumer Defensive | 91.5 | 152 | 20.44% | 500 | 3,346,124 | 16,373,476 | $+76.00 |
| 2026-04-24 | ARMK | Industrials | 88.0 | 428 | 5.04% | 11 | 107,559 | 2,133,731 | $-45.83 |
| 2026-04-24 | CSCO | Technology | 92.5 | 226 | 22.14% | 395 | 4,198,631 | 18,967,378 | $+146.90 |
| 2026-04-24 | NVDA | Technology | 93.5 | 98 | 2.59% | 500 | 5,540,552 | 214,131,755 | $+551.26 |
| 2026-04-27 | MPC | Energy | 92.5 | 58 | 13.84% | 109 | 260,585 | 1,882,239 | $-158.34 |
| 2026-04-27 | MU | Technology | 94.5 | 15 | 2.55% | 500 | 1,052,027 | 41,297,819 | $+52.72 |
| 2026-04-27 | ON | Technology | 89.5 | 44 | 17.36% | 308 | 1,716,769 | 9,891,971 | $-65.56 |
| 2026-04-27 | POST | Consumer Defensive | 91.5 | 174 | 3.48% | 10 | 17,927 | 515,072 | $-299.28 |
| 2026-04-27 | RIG | Energy | 92.0 | 1758 | 14.71% | 93 | 9,142,373 | 62,160,376 | $+140.64 |
| 2026-04-28 | CRWV | Technology | 95.0 | 50 | 5.76% | 500 | 1,598,446 | 27,758,677 | $-133.50 |
| 2026-04-28 | NIO | Consumer Cyclical | 85.5 | 1595 | 9.27% | 97 | 2,991,736 | 32,258,313 | $-239.25 |
| 2026-04-28 | NVDA | Technology | 94.5 | 81 | 2.86% | 500 | 5,150,459 | 180,274,459 | $+19.03 |
| 2026-04-28 | PAA | Energy | 90.5 | 905 | 7.80% | 42 | 437,063 | 5,605,301 | $+135.75 |
| 2026-04-28 | PBR | Energy | 91.0 | 633 | 31.93% | 171 | 5,617,322 | 17,592,795 | $-50.64 |
| 2026-04-29 | BKH | Utilities | 85.5 | 236 | 15.74% | 3 | 104,202 | 661,865 | $-261.96 |
| 2026-04-29 | CRWV | Technology | 89.5 | 31 | 8.58% | 500 | 2,379,785 | 27,752,075 | $+54.74 |
| 2026-04-29 | CVE | Energy | 92.0 | 632 | 7.92% | 55 | 928,704 | 11,728,605 | $+309.68 |
| 2026-04-29 | RNG | Technology | 87.0 | 200 | 9.21% | 6 | 85,609 | 929,747 | $+144.00 |
| 2026-04-29 | VG | Energy | 91.5 | 612 | 14.45% | 164 | 3,681,866 | 25,479,978 | $+183.60 |
| 2026-04-30 | COST | Consumer Defensive | 91.5 | 16 | 15.25% | 500 | 312,454 | 2,048,814 | $-21.12 |
| 2026-04-30 | EC | Energy | 94.5 | 742 | 8.22% | 23 | 281,714 | 3,427,582 | $+259.70 |
| 2026-04-30 | NE | Energy | 95.0 | 238 | 11.37% | 36 | 252,836 | 2,223,481 | $+35.70 |
| 2026-04-30 | TER | Technology | 88.0 | 20 | 5.40% | 500 | 423,122 | 7,829,102 | $+75.40 |
| 2026-04-30 | USFD | Consumer Defensive | 92.0 | 131 | 6.19% | 23 | 92,540 | 1,495,385 | $+75.98 |
| 2026-05-01 | CNP | Utilities | 91.5 | 378 | 16.70% | 35 | 772,659 | 4,627,540 | $-196.56 |
| 2026-05-01 | DTE | Utilities | 92.0 | 260 | 9.08% | 44 | 147,228 | 1,621,530 | $-988.00 |
| 2026-05-01 | FORM | Technology | 89.0 | 48 | 12.60% | 72 | 223,615 | 1,775,252 | $-191.52 |
| 2026-05-01 | GLNG | Energy | 93.5 | 357 | 15.62% | 15 | 215,875 | 1,381,631 | $+228.48 |
| 2026-05-01 | KLAC | Technology | 87.5 | 6 | 12.39% | 500 | 97,762 | 788,794 | $-77.34 |
| 2026-05-04 | AGNC | Real Estate | 91.0 | 1811 | 14.66% | 155 | 2,649,742 | 18,075,512 | $-380.31 |
| 2026-05-04 | BG | Consumer Defensive | 91.5 | 123 | 7.55% | 50 | 108,858 | 1,442,585 | $+178.81 |
| 2026-05-04 | NOV | Energy | 92.0 | 630 | 15.83% | 22 | 607,019 | 3,834,632 | $+88.20 |
| 2026-05-04 | OII | Energy | 93.0 | 190 | 4.94% | 11 | 45,716 | 924,530 | $+49.40 |
| 2026-05-04 | VTR | Real Estate | 93.5 | 227 | 22.25% | 175 | 1,367,597 | 6,147,267 | $-90.80 |
| 2026-05-05 | BEKE | Real Estate | 92.0 | 546 | 1.84% | 10 | 109,255 | 5,949,709 | $+49.14 |
| 2026-05-05 | BUD | Consumer Defensive | 92.0 | 246 | 13.20% | 102 | 778,207 | 5,896,869 | $-131.61 |
| 2026-05-05 | DBRG | Real Estate | 92.5 | 1284 | 5.33% | 8 | 91,404 | 1,714,510 | $+25.68 |
| 2026-05-05 | NE | Energy | 95.0 | 190 | 9.31% | 12 | 136,471 | 1,465,676 | $-143.00 |
| 2026-05-05 | PTEN | Energy | 94.0 | 599 | 5.48% | 12 | 385,062 | 7,021,598 | $-35.94 |
| 2026-05-06 | CDNS | Technology | 91.5 | 36 | 14.33% | 201 | 346,647 | 2,419,789 | $+86.40 |
| 2026-05-06 | ERIC | Technology | 92.5 | 659 | 2.67% | 10 | 179,481 | 6,729,925 | $+0.00 |
| 2026-05-06 | UEC | Energy | 91.0 | 256 | 3.54% | 33 | 388,520 | 10,970,667 | $+161.28 |
| 2026-05-07 | QCOM | Technology | 92.5 | 34 | 2.41% | 500 | 1,231,264 | 51,090,158 | $+555.90 |
| 2026-05-07 | RMBS | Technology | 93.5 | 41 | 17.64% | 87 | 391,763 | 2,220,670 | $-159.90 |
| 2026-05-07 | SQM | Basic Materials | 89.5 | 182 | 5.70% | 27 | 74,934 | 1,314,159 | $-882.70 |

## Methodology

- Trades merged by `(date, ticker)`; split orders summed by qty/P&L.
- UW endpoint `/api/darkpool/{ticker}?limit=500&date=YYYY-MM-DD` —
  filtered server-side to the entry day, **not** the most-recent batch.
- `dp_pct = max(record.size_sum) / max(record.volume) * 100`. The `volume` field on each DP record is the stock's full-day volume.
- Significance threshold: |r|>0.22 at n≈80, p<0.05.

## Caveats

- Sample is whatever IBKR paper-trading actually executed in the window — biased toward IFDS-qualified tickers (score ≥85), not the full market.
- `dp_pct` here uses raw aggregate from the per-ticker endpoint. Production uses a different (broken) batch path; this audit measures the *ceiling* of dp_pct's predictive power if the production pipeline were fixed.
- Polygon close ≠ MOC fill — irrelevant for this audit (no counterfactual).
