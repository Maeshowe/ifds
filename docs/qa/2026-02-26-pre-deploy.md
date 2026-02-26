# QA Audit — Pre-Deploy Gate

**Date:** 2026-02-26
**Auditor:** QA Layer (CC desktop.app)
**Scope:** deploy_daily.sh, cron setup, IBKR connection, environment, data safety, config validation
**Mode:** READ-ONLY
**Verdict:** CONDITIONAL PASS

---

## 1. deploy_daily.sh

### Finding F-01 — [CRITICAL] No tests run before deploy

**File:** `scripts/deploy_daily.sh`
**Description:** The deploy script does not execute `python -m pytest tests/ -q` before running the pipeline. CLAUDE.md states "Tesztek MINDIG futnak commit előtt" but the deploy script skips this entirely.
**Risk:** A broken commit deployed to production with no automated test gate.
**CC task:** Add pre-flight test step:
```bash
python -m pytest tests/ -q >> "$LOG" 2>&1
if [ $? -ne 0 ]; then
    echo "=== TESTS FAILED — ABORTING ===" >> "$LOG"
    exit 1
fi
```

### Finding F-02 — [MEDIUM] No rollback mechanism

**File:** `scripts/deploy_daily.sh`
**Description:** No rollback logic. If the pipeline writes corrupt state or partially completes, previous known-good state cannot be restored.
**CC task:** Back up `state/` before each run, restore on non-zero exit.

### Finding F-03 — [MEDIUM] No concurrent execution guard / PID lock

**File:** `scripts/deploy_daily.sh`
**Description:** No flock, PID file, or mechanism to prevent overlapping cron runs. If pipeline takes longer than expected, next cron could start.
**CC task:** Add flock:
```bash
LOCKFILE="/tmp/ifds_deploy.lock"
exec 200>"$LOCKFILE"
flock -n 200 || { echo "Already running"; exit 0; }
```

### Finding F-04 — [MEDIUM] No Telegram alert on pipeline failure

**File:** `scripts/deploy_daily.sh`
**Description:** Non-zero exit is logged but no Telegram alert sent. Operator learns about failures only from cron logs.
**CC task:** Add failure notification before `exit $EXIT_CODE`.

### Finding F-05 — [STYLE] No explicit config validation step

Separate pre-flight validation (`--dry-run`) would give cleaner failure mode.

---

## 2. Cron Setup

### Finding F-06 — [STYLE] Timezone not explicit in script

22:00 CET schedule set in crontab, but script has no `export TZ="Europe/Budapest"`. DST transitions could shift execution window.

### Finding F-07 — [MEDIUM] Potential overlap between cron jobs

Paper trading scripts and main pipeline could overlap. Different IBKR client IDs prevent socket conflicts, but state file access (cumulative_pnl.json) is shared.

---

## 3. IBKR Connection Hardening

### Finding F-08 — ✅ PASS: Well-implemented

- Port constants defined once (`PAPER_PORT = 7497`, `LIVE_PORT = 7496`)
- Retry logic: configurable `CONNECT_MAX_RETRIES` (3), `CONNECT_RETRY_DELAY` (5s), `CONNECT_TIMEOUT` (15s)
- Telegram alert on all retries exhausted
- Telegram failure isolation (try/except with pass)
- Dedicated client IDs per script (10=submit, 11=close, 12=eod, 13=nuke)

### Finding F-09 — [STYLE] nuke.py hardcodes port

Uses `PORT = 7497` instead of importing from `lib.connection`.

### Finding F-10 — [MEDIUM] Circuit breaker warns but continues trading

Cross-reference with Pipeline Output PT1. Same finding.

---

## 4. Environment Dependencies

### Finding F-11 — [STYLE] .env.example missing IFDS_CACHE_ENABLED

Loader supports `IFDS_CACHE_ENABLED` (default False). New deployment might miss enabling cache.

### Finding F-12 — ✅ PASS: API health checks at startup (Phase 0)

Comprehensive pre-flight: Polygon, FMP, FRED (critical), Unusual Whales (non-critical, has fallback). VIX 3-level fallback chain.

### Finding F-13 — ✅ PASS: Per-provider circuit breaker

Sliding window (50-call, 30% threshold, 60s cooldown). State machine CLOSED → OPEN → HALF_OPEN.

### Finding F-14 — [STYLE] No Python version check at startup

Project requires 3.12+ but no explicit check in entry point or deploy script.

---

## 5. Data Safety

### Finding F-15 — ✅ PASS: Atomic writes in core state files

FileCache, SignalDedup, ObsidianStore, BMIHistory, SectorHistory all use `tempfile.mkstemp() + os.replace()`.

### Finding F-16 — [MEDIUM] Phase 6 counter + Phase 2 snapshot non-atomic

**Files:**
- `src/ifds/phases/phase6_sizing.py` lines 672-679 (`_save_daily_counter`)
- `src/ifds/phases/phase2_universe.py` lines 350-353 (universe snapshot)

Plain `open(file, "w")` + `json.dump()` — crash mid-write = corrupt JSON.
**CC task:** Apply tempfile + os.replace pattern.

### Finding F-17 — [MEDIUM] Phase 4 snapshot non-atomic gzip write

**File:** `src/ifds/data/phase4_snapshot.py` line 36
Cross-reference with Pipeline Output PH1. Same finding.

### Finding F-18 — [MEDIUM] No file-level locking for concurrent state access

No fcntl.flock or filelock anywhere. Mitigated by single-cron schedule, but manual runs could corrupt.

### Finding F-19 — [MEDIUM] No backup strategy for state files

`state/` directory contains irreplaceable data (OBSIDIAN store 9 days accumulated, cumulative PnL, circuit breaker). No rotation, no pre-run snapshot.
**CC task:** Add to deploy_daily.sh:
```bash
cp -r state/ state_backup_$(date +%Y%m%d)/ 2>/dev/null || true
find state_backup_* -maxdepth 0 -mtime +7 -exec rm -rf {} + 2>/dev/null || true
```

### Finding F-20 — ✅ PASS: CONDUCTOR SQLite WAL mode

---

## 6. Config Validation

### Finding F-21 — ✅ PASS: Validation on every startup

`Config.__init__()` calls `validate_config(self)` after merging all layers.

### Finding F-22 — [STYLE] No Telegram config warning

If one of telegram_bot_token/telegram_chat_id is set without the other, no startup warning.

### Finding F-23 — [MEDIUM] OBSIDIAN regime multiplier keys not validated

`obsidian_regime_multipliers` dict (8 regime keys) not checked for completeness. Missing key → runtime KeyError in Phase 6.
**CC task:** Add validation for all 8 required regime keys.

### Finding F-24 — [STYLE] sector_bmi_thresholds not validated

### Finding F-25 — [STYLE] Async semaphore ranges not validated

A value of 0 or negative would crash asyncio.Semaphore.

### Finding F-26 — [STYLE] Scoring weights can be negative

Validator checks sum=1.0 but individual weights can be negative, inverting scoring logic.

---

## Summary

| Severity | Count | Key Findings |
|----------|-------|-------------|
| **CRITICAL** | 1 | F-01: No tests before deploy |
| **MEDIUM** | 10 | F-02, F-03, F-04, F-07, F-10, F-16, F-17, F-18, F-19, F-23 |
| **STYLE** | 8 | F-05, F-06, F-09, F-11, F-14, F-22, F-24, F-25, F-26 |
| **PASS** | 5 | F-08, F-12, F-13, F-15, F-20, F-21 |

## Priority Task List for CC

### Immediate (CRITICAL)
1. ☐ **Add pytest to deploy_daily.sh** — abort on failure (~2 lines)

### Next session (MEDIUM — deploy hardening)
2. ☐ Add flock to deploy_daily.sh — prevent concurrent runs (~3 lines)
3. ☐ Add Telegram failure notification to deploy_daily.sh (~5 lines)
4. ☐ Add state/ backup before each run (~3 lines)
5. ☐ Phase 6 counter atomic write — `phase6_sizing.py` lines 672-679
6. ☐ Phase 2 snapshot atomic write — `phase2_universe.py` lines 350-353
7. ☐ Phase 4 snapshot atomic write — `phase4_snapshot.py` line 36
8. ☐ OBSIDIAN regime multiplier keys validation — `validator.py`

### Backlog (STYLE)
9. ☐ Timezone assertion in deploy_daily.sh
10. ☐ Python version check in entry point
11. ☐ .env.example cache config
12. ☐ Telegram config warning at startup
13. ☐ Async semaphore validation
14. ☐ Scoring weights non-negative check
