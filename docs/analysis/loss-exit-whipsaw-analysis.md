# LOSS_EXIT Whipsaw Cost Audit — BC23 (2026-04-13 → 2026-04-29)

> Read-only retrospective. **No pipeline behavior is changed.**

## Summary

- LOSS_EXIT events (per ticker/day, split orders merged): **6**
- Events with MOC data: 6 / no data: 0
- Total actual P&L: **$-1,273.25**
- Total counterfactual MOC P&L: $-1,361.23
- **Net whipsaw cost: $+87.98** (negative = stop hurt, positive = stop saved)
- Mean whipsaw / event: $+14.66, median $+9.42
- Stop hurt: 3 | Stop saved: 3 | Neutral: 0

### Verdict

**LOSS_EXIT saved $88 vs holding to MOC.** The rule, in this sample, protected against larger losses.

## Per-event detail

| Date | Ticker | Sector | Score | Entry | Stop fill | MOC close | Qty | Actual P&L | Counterfactual MOC P&L | Whipsaw | Verdict |
|------|--------|--------|-------|-------|-----------|-----------|-----|-----------|------------------------|---------|---------|
| 2026-04-20 | SKM | Communication Services | 93.0 | $39.46 | $38.47 | $38.11 | 298 | $-295.02 | $-402.30 | $+107.28 | stop_saved |
| 2026-04-21 | GME | Consumer Cyclical | 92.5 | $25.29 | $24.73 | $24.46 | 514 | $-286.84 | $-426.62 | $+139.78 | stop_saved |
| 2026-04-23 | POWI | Technology | 95.0 | $74.00 | $72.29 | $72.63 | 148 | $-253.08 | $-202.76 | $-50.32 | stop_hurt |
| 2026-04-27 | ON | Technology | 89.5 | $98.89 | $97.40 | $98.04 | 44 | $-65.56 | $-37.40 | $-28.16 | stop_hurt |
| 2026-04-28 | CRWV | Technology | 95.0 | $109.14 | $106.47 | $105.53 | 50 | $-133.50 | $-180.50 | $+47.00 | stop_saved |
| 2026-04-28 | NIO | Consumer Cyclical | 85.5 | $6.43 | $6.28 | $6.36 | 1595 | $-239.25 | $-111.65 | $-127.60 | stop_hurt |

## By ticker

| Ticker | Events | Σ actual P&L | Σ whipsaw cost | Avg whipsaw |
|--------|--------|--------------|----------------|-------------|
| NIO | 1 | $-239.25 | $-127.60 | $-127.60 |
| POWI | 1 | $-253.08 | $-50.32 | $-50.32 |
| ON | 1 | $-65.56 | $-28.16 | $-28.16 |
| CRWV | 1 | $-133.50 | $+47.00 | $+47.00 |
| SKM | 1 | $-295.02 | $+107.28 | $+107.28 |
| GME | 1 | $-286.84 | $+139.78 | $+139.78 |

## Methodology

- **MOC proxy:** Polygon daily close (`c` from /v2/aggs/ticker/{T}/range/1/day/{D}/{D}).
  This is the official 16:00 ET close, which is a close (≤0.1%) approximation
  to a real `MarketOnClose` fill price.
- **Split orders merged:** when one logical position fired multiple LOSS_EXIT
  rows in the trades CSV (split fills), they are summed by qty/P&L.
- **Whipsaw verdict:** `actual_pnl - counterfactual_moc_pnl`.
  - `< -$10` → `stop_hurt` (whipsaw)
  - `> +$10` → `stop_saved` (continued decline avoided)
  - `[-10, +10]` → `neutral`
- **No simulation** of trail/SL/TP1 paths — the only counterfactual is
  *holding to MOC instead of stopping out at -2%*.

## Caveats

- The Polygon daily close differs slightly from a real-time MOC fill.
- This audit only models the LOSS_EXIT rule, not interaction with TP1,
  trail-stop, or other exits. It does not predict net portfolio P&L if
  the rule were removed, only how it scored on past triggers.
- Sample size is small (BC23 deploy 2026-04-13). Treat the verdict as
  *directional*, not statistically conclusive.
