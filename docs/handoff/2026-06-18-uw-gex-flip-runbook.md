# Runbook — flip `uw_gex_fetch_enabled` OFF (Polygon-only GEX)

**For:** Tamás (production action on the Mac Mini). **Prepared by:** CC.
**Date:** 2026-06-18. **Status:** ready to execute — TWO STEPS, separate run cycles.

## What & why (one paragraph)

The UW greek-exposure primary has been UW-sourced for **0 tickers across 92 days**
(it 429s → Polygon is the de-facto sole GEX source; 06-17: 29/29 greek-exposure
429). Flipping `uw_gex_fetch_enabled` → False makes the GEX provider Polygon-only,
killing the 29 wasted UW calls/day **and** removing a latent confound (if UW
recovered mid-experiment the source would silently switch → different exclusions).
Proven output-invariant: `scripts/analysis/verify_gex_uw_invariance.py` (source=uw==0/92d)
+ the live on/off diff (2026-06-18, full 36-ticker universe: regime + NEGATIVE-
exclusion bit-identical, UW non-None = 0) + `tests/test_gex_uw_fetch_flag.py`.

## Mechanism: Layer-2 config override (sanctioned, revertible, no logic code change)

The config loader (`Config(config_path=...)`) merges a JSON file over the TUNING
defaults. We introduce a Mini-local `state/prod_overrides.json` and pass it via
`--config`. Empty override = behavior-invariant. Day-63 revert = delete the file
(or set the key back to `true`).

`state/prod_overrides.json` is **gitignored** (Mini-local production config; never
committed) — already added to `.gitignore` by CC.

### deploy_intraday.sh — the one-line edit (apply on the Mini)

```diff
-python -m ifds run --phases 4-6
+CFG_OVERRIDE=""
+[ -f state/prod_overrides.json ] && CFG_OVERRIDE="--config state/prod_overrides.json"
+python -m ifds run --phases 4-6 $CFG_OVERRIDE
```

Dormant-safe: with no `state/prod_overrides.json`, `$CFG_OVERRIDE` is empty and the
command is byte-identical to today's.

---

## STEP 1 — introduce the config path with an EMPTY override (validates the mechanism)

Do NOT flip the flag yet. First prove the config-layer itself is behavior-invariant.

```bash
# on the Mini, after applying the deploy_intraday.sh edit above:
cd ~/SSH-Services/ifds
echo '{}' > state/prod_overrides.json
```

**Verify after the next intraday run (Monday 2026-06-22, ~14:32 CEST):**
```bash
# (a) no config errors, run completed:
grep -iE "CONFIG WARNING|Exit:" logs/cron_intraday_20260622_*.log | tail
# (b) GEX still Polygon-sourced + regime/exclusion unchanged (UW still on under empty override):
.venv/bin/python scripts/analysis/verify_gex_uw_invariance.py | tail -6
```
Expected: run clean, `source=uw==0` continues, exclusions look normal. This proves
the `--config` path adds nothing (empty override = current behavior). **If anything
is surprising, STOP — it is the config-layer, not the flag.**

## STEP 2 — the actual flip (separate window, after STEP 1 is clean)

```bash
# on the Mini:
cd ~/SSH-Services/ifds
echo '{"tuning": {"uw_gex_fetch_enabled": false}}' > state/prod_overrides.json
```

**Verify after the following intraday run (Polygon-only post-verify):**
```bash
# (a) ZERO UW greek-exposure 429 (the whole point):
grep -c "greek-exposure.*429" logs/cron_intraday_<date>_*.log    # expect 0
# (b) GEX source still polygon, regime + exclusion list unchanged vs the prior run:
.venv/bin/python scripts/analysis/gex_live_onoff_diff.py | tail -8   # on/off now identical trivially
# (c) Phase 5 still passed a normal ticker count; M_total unaffected (M_gex was already 1.0)
```
Expected: 0 × greek-exposure 429, GEX regimes identical to STEP-1 baseline,
NEGATIVE-exclusion list unchanged. This is the flip post-verify → log in 04-risks §11.6.

## Day-63 revert
`rm state/prod_overrides.json` (or set the key back to `true`). The deploy edit is
dormant again. Clean rollback, no code change.

## Notes
- Timing: flip only in a market-closed window (after a 22:00 CEST close, before the
  next 15:30 submit). Not before a big exit day.
- The cancellation of the UW subscription is a separate decision — see
  `docs/analysis/uw-feed-descope-2026-06-18.md`; its GO is tied to STEP-2 post-verify.
