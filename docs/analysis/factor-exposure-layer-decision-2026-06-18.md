# Decision — Factor-Exposure Layer: KILL (data grounds)

**Date:** 2026-06-18
**Status:** DECIDED — do **not** build the factor-exposure layer (Option C)
**Type:** Negative result, logged as a legitimate deliverable ("test, don't confirm")
**Owner:** Chat (strategy) decided; CC ran the read-only data audit + this record
**Context:** IFDS parameter freeze (Day 18→63); IC Phase A still open

---

## Decision

The "Portfolio Factor Exposures" layer (a Barra-style cross-sectional style-factor
+ time-series macro-beta decomposition of the IFDS book, characterised against the
MID regime) is **not built now**. The idea is closed, not parked as a third
half-finished thread. Revisit only under the explicit condition below.

## Pre-registered criterion (written BEFORE looking at any result)

> Keep the factor layer **if and only if** — run across several historical rebalance
> dates — the DIVERGENCE flag would have caught **at least once** a real
> misalignment / drawdown that the eye did **not** already see. If it only restates
> what was already known → kill, log the negative result, move on.

The throwaway probe (`factor_check.py`, ~30-line core: `zscore` / `exposures` /
`divergence`; reproduced in the appendix) was written to run this test cheaply,
**before** committing any architecture. No CC task-file, no IC phase was opened —
deliberately, to avoid pre-committing to the build.

## Why KILL — the test could not even be run cheaply (3 verified data gaps)

A read-only audit of the persisted stack (2026-06-18) found the pre-registered
test is **not runnable** on existing data without first investing in new
infrastructure — and that investment, for a layer whose payoff is *descriptive,
not predictive* (≈ zero direct alpha), does not clear the bar.

1. **The Barra-style raw inputs are not persisted.** The Phase 4 snapshots
   (`state/phase4_snapshots/{date}.json.gz`, 8 dates 06-08…06-17) hold IFDS's
   **own** scoring characteristics (`roe`, `net_margin`, `eps_growth_yoy`,
   `rs_vs_spy`, `atr_14`, `rvol`, `sector`, …) — **not** `ep` (E/P),
   `mom_12_1` (12M−1M total return), realised `vol`, or `log_mktcap`. Running the
   probe needs either historical **as-of** re-fetches (FMP/Polygon, ≈40 tickers ×
   8 dates ≈ 320 calls, as-of correctness fiddly, rate-limit-sensitive — cf. the
   `9a169b9` lesson) or **proxies** (`rs_vs_spy` ≈ momentum, `atr/price` ≈ vol),
   with **no clean proxy for `ep` or `size`**.

2. **MID emits no flat `risk_off` / `rates_up` label.** The bundle
   (`state/mid_bundles/{date}.json.gz`) is a rich, multi-dimensional taxonomy —
   e.g. `gip.regime=Late_Cycle`, `cross_asset.sb_regime_label=positive_stagflationary`,
   `catalyst.active_regime=stagflation`, `positioning.gex_regime=negative`,
   `yield_curve.regime=bull_flattener`. The `divergence()` rules would need a
   **deliberate MID-label → factor-condition mapping** — a modelling/strategy
   decision (MID territory), not wiring.

3. **The test bed is too thin.** Only **~6 dates** (06-11…06-17) have *both* a book
   snapshot *and* a MID bundle, all recent and **low regime-variance**. A clean
   "no divergence" over 6 such dates is **not evidence** either way — too short to
   be the kill-or-keep arbiter.

**Conclusion:** the cost to merely *run* the pre-registered test (as-of factor
fetch + MID-label mapping + a longer history) is itself the signal. For a
descriptive, ~zero-alpha layer, during a freeze, with IC Phase A still open, the
disciplined call is **C — kill on data grounds**.

## What stays true (the one part that had decision value)

The only component with *decision* value was the **DIVERGENCE flag** (book
exposure measured **against** the MID regime), not the descriptive rack itself.
That idea is preserved here as a revisit hook — but it does **not** justify the
full factor layer on its own.

## Revisit condition (the only way this reopens)

Reopen **only if** a clean `ep / mom_12_1 / vol / log_mktcap` (and ideally
`short_interest`, `13F_crowding`) data channel gets built **for another reason**,
**and** the freeze has lifted **and** there is a longer history (≥1–2 quarters of
book snapshots) to make the pre-registered test meaningful. Absent all three, the
descriptive payoff does not earn the build. Do **not** source any future
"Quant Sentiment"-style factor from `morning_news` NLP (MID-contamination of IC
claims — keep it price/fundamentals-based).

## Reference — the aspirational "full version" (attachment, Q4 2025 → Q1 2026)

The "Situational Awareness LP — Portfolio Factor Exposures" chart the user attached
is the *target* shape this layer would produce. Recorded here so the dead-end is
documented with its reference (Q1 2026 values, z-score units):

| Factor | Exp. | Factor | Exp. |
|---|---:|---|---:|
| Animal Spirits | +2.86 | Size (Large−Small) | +0.59 |
| Earnings Yield | −1.61 | Liquidity | +0.69 |
| Book-to-Price | −1.29 | Rates Beta | +0.63 |
| Growth | +0.76 | Oil Beta | +0.20 |
| Earnings Revisions | +0.75 | 13F Crowding | +0.28 |
| Profitability | +0.64 | Short Interest | +0.88 |
| Leverage | −0.48 | Quant Sentiment | −0.73 |
| Dividend Yield | +0.51 | Momentum (3M) | +1.13 |
| Momentum (12M−1M) | +1.75 | Momentum (12M) | +0.97 |
| Volatility | +1.41 | Reversal (1M) | +0.13 |

Note: this 21-factor view mixes two distinct mathematical objects on one rack —
**(A)** cross-sectional style factors (characteristics z-scored across the universe,
position-weighted) and **(B)** time-series macro betas (`Rates Beta`, `Oil Beta`
= regression coefficients of book return on MID factor streams). The IFDS stack can
cheaply reproduce *neither* today (gap #1 for A; MID time-series regression for B).

---

## Appendix — the throwaway probe (`factor_check.py`, reference only, NOT in the codebase)

Kept here for reproducibility if the revisit condition is ever met. It is **not**
promoted to a module — it is the disposable test, by design.

```python
# factor_check.py — throwaway factor-exposure probe for IFDS positions.
# Pre-reg criterion: keep the layer iff, across several historical rebalance
# dates, DIVERGENCE would have flagged a real misalignment the eye did NOT see.
# Data (US-only, existing stack): ep (FMP), mom_12_1 (Polygon), vol (Polygon),
# log_mktcap (FMP/Polygon), sector (FMP). Rates/Oil beta = separate MID regression.
import numpy as np
import pandas as pd

FACTORS = ["ep", "mom_12_1", "neg_vol", "size"]

def zscore(s, winsor=3.0):
    z = (s - s.mean()) / s.std(ddof=0)
    return z.clip(-winsor, winsor)

def exposures(pos, chars, sector_neutral=True):
    df = pos.merge(chars, on="ticker").dropna()
    df["neg_vol"] = -df["vol"]
    df["size"] = df["log_mktcap"]
    out = {}
    for f in FACTORS:
        z = df.groupby("sector")[f].transform(zscore) if sector_neutral else zscore(df[f])
        out[f] = float(np.dot(df["signed_weight"].values, z.values))  # E_f = Σ w_i·z_i,f
    return out

def divergence(exp, regime):  # regime: MID label
    f = []
    if regime in ("risk_off", "rates_up") and exp["neg_vol"] > 0.5: f.append("high-vol in risk-off")
    if regime == "risk_off" and exp["ep"] < -0.5: f.append("value-short in risk-off")
    if regime == "risk_off" and exp["mom_12_1"] > 1.0: f.append("aggressive momentum in risk-off")
    return f
```
