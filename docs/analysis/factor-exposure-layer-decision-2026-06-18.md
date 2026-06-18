# Decision — Factor-Exposure Layer: KILL (opportunity cost)

**Date:** 2026-06-18
**Status:** DECIDED — do **not** build the factor-exposure layer now (Option C)
**Type:** Negative result, logged as a legitimate deliverable ("test, don't confirm")
**Owner:** Chat (strategy) decided; CC ran the read-only data audit + this record
**Context:** IFDS parameter freeze (Day 18→63); IC Phase A still open

> **Correction note (supersedes the first revision, commit `33bea4e`).** The first
> revision justified the kill partly on a *data-impossibility* frame ("only 8 Phase 4
> snapshots 06-08…06-17", "~6 thin overlapping dates", "the test can't be run
> cheaply"). **Those facts were wrong** — they came from `ls … | tail -N` truncating
> the directory listing, reported as if complete. Re-audited below. The direction
> (don't build now) holds, but the rationale is re-based on **opportunity cost**, the
> argument that never depended on the data. This revision corrects the record so it
> can be the reliable later reference.

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

## Primary rationale — opportunity cost (data-independent)

The strongest kill argument never depended on the data: the rack is
**descriptive, not predictive**. A precise characterisation of a signal-weak book
(IFDS, by its own description) carries a direct alpha contribution near zero. The
one component with *decision* value is the DIVERGENCE flag (book exposure measured
**against** the MID regime); the rest is descriptive dressing.

During a parameter **freeze**, with **IC Phase A still open**, spending build
effort on a ~zero-alpha descriptive layer — even the cheap partial probe, let alone
the eventual full layer + its as-of data channel + the MID-label mapping — loses to
finishing IC Phase A. That is the decision: **opportunity cost**, not data
impossibility.

## Secondary — the real (narrower) data blockers, corrected

A read-only audit of the persisted stack (2026-06-18, full listings) found the
data picture is **better** than the first revision claimed — which is exactly why
the headline is re-based off it:

- **History is ample, not thin.** `state/phase4_snapshots/` = **85 dates,
  2026-02-19 → 06-17**. `state/mid_bundles/` = **42 dates, 2026-04-27 → 06-17**.
  Their intersection = **36 common dates, 2026-04-27 → 06-17 (~7 weeks)** — late
  April to mid-June, i.e. a window that *does* carry real regime variance. The
  "too short to decide" argument does **not** hold.
- **A partial proxy probe IS cheaply runnable today.** The snapshots already carry
  `rs_vs_spy` (a momentum proxy) and `atr_14`/`price` (a vol proxy) plus `sector`.
  A momentum+vol DIVERGENCE probe over the 36 dates needs no new fetch.
- **The genuine blockers are narrow:**
  1. **`ep` (E/P) and `size`/market-cap are not persisted**, and there is no clean
     proxy in the snapshot (it holds IFDS's own scoring chars — `roe`, `net_margin`,
     `eps_growth_yoy`, `rs_vs_spy`, `atr_14`, `rvol`, `sector` — verified by
     decompressing the 06-17 snapshot). A **full** 4-factor probe needs historical
     as-of fetches (FMP/Polygon; as-of correctness fiddly, rate-limit-sensitive —
     cf. the `9a169b9` lesson).
  2. **The MID regime is a rich multi-dimensional taxonomy, not a flat
     `risk_off`/`rates_up` label** (verified: `gip.regime=Late_Cycle`,
     `cross_asset.sb_regime_label=positive_stagflationary`,
     `catalyst.active_regime=stagflation`, `positioning.gex_regime=negative`,
     `yield_curve.regime=bull_flattener`). The `divergence()` rules need a
     **deliberate MID-label → factor-condition mapping** — a modelling/strategy
     decision (MID territory), not wiring.

These are real, but they are *narrower* than "can't run it" — they bound the
*full* probe, not the existence of a test. They do not change the verdict; the
verdict rests on opportunity cost.

## Revisit condition (the only way this reopens)

Reopen **only if** the freeze has lifted **and** IC Phase A is closed **and** either
(a) a clean `ep / size` (ideally also `short_interest`, `13F_crowding`) data channel
gets built **for another reason**, or (b) you deliberately choose to spend the
half-day on the partial momentum+vol proxy probe over the 36 dates as a cheap
empirical pre-check. Absent that, the descriptive payoff does not earn the build.
Do **not** source any future "Quant Sentiment"-style factor from `morning_news` NLP
(MID-contamination of IC claims — keep it price/fundamentals-based).

## Reference — the aspirational "full version" (attachment, Q4 2025 → Q1 2026)

The "Situational Awareness LP — Portfolio Factor Exposures" chart the user attached
is the *target* shape this layer would produce. It lists **20 factors** (Q1 2026
values, z-score units):

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

Note: this 20-factor view mixes two distinct mathematical objects on one rack —
**(A)** cross-sectional style factors (characteristics z-scored across the universe,
position-weighted) and **(B)** time-series macro betas (`Rates Beta`, `Oil Beta`
= regression coefficients of book return on MID factor streams). The IFDS stack can
cheaply reproduce a *partial* (A) today (momentum + vol proxies) but not the full
(A) (no `ep`/`size`) nor (B) (needs the MID time-series regression).

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
