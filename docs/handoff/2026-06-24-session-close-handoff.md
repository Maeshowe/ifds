# Handoff — 2026-06-24 (UW-GEX flip executed + UW 07-04 deadline assessed)

## State in one line
UW greek-exposure flip **executed** (Polygon-only GEX live on the Mini); UW now has
**zero decision impact** in IFDS; the shared UW sub dies **2026-07-04** and IFDS is
**proven safe** against it. Freeze active to Day 63. **1969 passing.**

## What happened this session (2026-06-23 → 06-24)
- **Sync + verify** (06-22, 06-23 data): runs clean. ⚠️ **Drawdown** — cumulative
  1716 → **555** in four trading days (06-22 −$398, 06-23 −$331). P&L reality, for
  the daily reviews; not a flip issue.
- **UW-GEX flip — DONE** (two-step config-layer runbook):
  - **STEP 1** (`7c3fd55`, pushed): `deploy_intraday.sh` conditional `--config`
    (dormant-safe) + Mini-local `state/prod_overrides.json={}` (gitignored). The
    06-23 14:30 run validated the config-layer (empty override = invariant; proven
    `Config({}) tuning == base`).
  - **STEP 2** (06-24 AM): pre-checks all green (06-23 run clean, `source=uw==0`
    incl. 06-23, **live on/off diff PASS** — UW non-None=0 on the 44-ticker
    universe, regime+exclusion bit-identical). Flipped:
    `state/prod_overrides.json = {"tuning":{"uw_gex_fetch_enabled":false}}` →
    merged config `uw_gex_fetch_enabled=False` (only that key) → dry-run
    "Pipeline CAN proceed". **GEX is Polygon-only from the next run.**
  - **Note:** the 06-22/06-23 `0× greek-exposure 429` was a red herring (different
    failure mode, NOT UW recovery — `source=uw==0` held, live diff PASS). The
    `verify_gex_uw_invariance.py` hard-stop caught exactly this "is UW alive?" gap.
- **UW 07-04 assessment** (de-scope doc updated): the cancelled sub is **shared
  with MID**, dies 07-04 for IFDS too. **IFDS won't break** — validator UW=optional,
  phase0 UW=non-critical, runner gates on `uw_available`; airtight dry-run with a
  blanked key → "Pipeline CAN proceed". UW is non-decision post-flip.

## PENDING / next actions
1. **Flip post-verify** (the only open IFDS item): after **today's (06-24) 14:30
   CEST intraday run**, confirm on the Mini:
   - 0× UW greek-exposure call/429 in `logs/cron_intraday_20260624_*.log`
   - `gex_live_onoff_diff.py` still PASS (flag-independent re-check)
   - Phase 5 normal ticker count, `M_gex` unchanged 1.0, regime+exclusion vs the
     invariant baseline
   Then **log the flip-close in 04-risks §11.6** (currently §11.6 records the flag
   as dormant + the Mini flip as the gated deploy — update it to "flip executed +
   post-verified 06-24").
2. **07-04: remove `IFDS_UW_API_KEY` from the Mini prod `.env`** (Tamás, no code
   change) — clean close, stops the daily dead-UW health-check noise. See the de-scope
   doc "07-04 deadline" section. Not required for safety (graceful), but the clean step.
3. **Next CC work item (freeze-safe):** `signal_attribution` data-loader wiring —
   spec §6.1 pins the 3 invariants (S_j<=0 → snapshot-recovery → else exclude;
   exit-type from `pending_exits` only; read-only + dual sample). Day-63 prep.

## Freeze status
Production code **frozen to Day 63**. The UW-GEX flip is the last prod-behaviour
change (output-invariant, proven). The 07-04 `.env` key removal is config + deadline-
required (not new churn). Churn counter: S_j-capture → UW-flag → STOP.

## Revert (if ever needed)
`rm state/prod_overrides.json` (or set back to `{}`) on the Mini → instant rollback
to UW→Polygon fallback, no code change.

## Not IFDS (context only)
MID is doing its own UW decommission (`mid/docs/tasks/2026-06-24-uw-decommission`) —
MID CC owns it; no IFDS action.
