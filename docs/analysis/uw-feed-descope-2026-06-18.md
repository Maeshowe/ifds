# UW feed de-scope + darkpool-shadow retrospective (Day-21 dead-feed audit)

**Date:** 2026-06-18 (executed a few days early — this IS the edge-audit §4.2/7
Day-21 dead-feed audit). **Status:** de-scope DECIDED (strategy-confirmed by Chat);
UW subscription **cancellable** — but the cancellation GO is tied to the post-flip
Polygon-only verification (see runbook). Read-only doc; no production change here.

## Verdict

The Unusual Whales feed has **≈ zero live decision value** on the current stack.
De-scope its only remaining justification (the Day-90 darkpool shadow audit) and
recommend cancellation, gated on the GEX flip post-verify.

## What UW actually feeds (verified 2026-06-18)

UW is called for exactly two things — `/api/darkpool/*` and
`/api/stock/{t}/greek-exposure[/strike]`. Mapped to live value:

| UW use | Status | Live value |
|---|---|---|
| greek-exposure → **M_gex sizing** | `uw_gex_sizing_enabled=False` → M_GEX forced 1.0 | none |
| greek-exposure → **GEX regime → NEGATIVE-exclusion** | active entry filter, but **Polygon-sourced** (UW 429s 100%; source=uw==0 / 92 days) | regime needed, **UW call not** (Polygon covers) |
| darkpool → **shadow** | dp_pct scoring deactivated; shadow-only for a Day-90 audit | see retrospective ↓ |
| **PCR / OTM** | **Polygon-sourced** (`phase4_stocks.py:856`), NOT UW | no UW dependency |

So GEX (the regime that matters) comes from Polygon; M_gex sizing is off; PCR/OTM
are Polygon; only the darkpool shadow remains — and it is not viable (below).

## Darkpool-shadow retrospective — honest closure of the pre-registered loop

The darkpool shadow was kept (edge-audit §4.2/7) "shadow-bound for the Day-90
Bayesian recalibration audit (n≈150–180, ~2026-08-26)". The data says that audit
is **not reachable**:

- **23 shadow days** (2026-05-18 → 2026-06-18), `state/uw_shadow/`.
- **Exactly 3 tickers/day, every single day** (min=max=mean=3.0) → **n=69 total**. This
  is a structural cap, not sparse data.
- The audit needs n≈150–180 → **~55 more trading days at 3/day** — i.e. ~Day 76+,
  **past the Day-63 go-live gate**. Not viable within the experiment.
- Even if reachable, dp_pct is a **deactivated contraindicator** (retrospective audit
  ρ = −0.265, p=0.041; `docs/analysis/dp-pct-retrospective-audit.md`) — we will not
  resurrect it ("don't multiply indicators"), and the strategic direction is the
  **MID regime overlay** (edge-audit §3.b), not darkpool.

**Therefore:** we looked at darkpool honestly, this is what we found, and we stop.
A future iteration can revisit if the strategy ever turns toward microstructure.

## §4.2/7 amendment (Day-21 audit outcome)

The protective reason recorded in edge-audit §4.2/7 — *"UW stays, shadow-bound to
the Day-90 audit"* — **no longer holds**: the audit is not reachable (n=69 after 23
days, 3/day cap), dp_pct is a deactivated contraindicator, and UW's other live use
(GEX) is fully Polygon-covered. The UW line is **de-scoped**. This is **not** a
gate move: the Day-63 / Day-126 go-live gates are untouched; this de-scopes a
side-investigation whose output would not have changed any decision.

## Cost calibration (expectation management)

The May review put the **UW line at ~$50/mo** (the $665 figure was the *whole*
stack). Tamás to confirm the current invoice. Even at ~$50/mo this is a **hygiene
gain (~0.6% of $100k per year), not a material drag reduction** — exactly as
§4.2/7 pre-stated ("the catch is small"). The dominant cost (Polygon) **stays** —
PCR/OTM/GEX-regime all come from there. **No urgency** on cancellation.

## Recommendation (GO gated on the flip post-verify)

1. Flip `uw_gex_fetch_enabled` OFF (two-step config-layer runbook,
   `docs/handoff/2026-06-18-uw-gex-flip-runbook.md`). Tamás executes.
2. **After** the flip post-verify confirms Polygon-only GEX with regime + exclusion
   unchanged → UW's live value is *demonstrated* zero (GEX no longer even called;
   darkpool shadow de-scoped) → **then** cancel the UW subscription (Tamás's
   real-world action). Do not run ahead of the flip confirmation.
3. Keep the 69-row shadow dataset (`state/uw_shadow/`) as the closed retrospective
   artifact — do not delete; a future microstructure iteration may reference it.
