# QA Audit — Pipeline Output Validation

**Date:** 2026-02-26
**Auditor:** QA Layer (CC desktop.app)
**Scope:** Telegram, OBSIDIAN store, Paper Trading scripts, CSV execution plan, Phase 4 snapshots
**Mode:** READ-ONLY

---

## 1. Telegram Output (`src/ifds/output/telegram.py`)

### Finding T1 — [MEDIUM] Part 2 silent failure (line 59-65)

When `part1` sends OK but `part2` fails, the function returns `True` and logs "daily report sent". The part2 return value is discarded:
```python
ok = _send_message(token, chat_id, part1, timeout)
if ok and part2:
    _send_message(token, chat_id, part2, timeout)  # return value discarded
```
**CC task:** Capture part2 result, log warning if it fails.

### Finding T2 — [MEDIUM] EARN column edge case (line 423)

`full_date[5:]` slices without length validation. If `full_date` is an empty string `""` (truthy but too short), produces blank EARN column.
```python
earn_str = full_date[5:] if full_date else "N/A"
```
**CC task:** Add length check: `full_date and len(full_date) >= 10`

### Finding T3 — [STYLE] Sequential earnings date API calls (lines 297-303)

8 synchronous HTTP calls for 8 positions. Correct error handling but adds latency.
**CC task:** Consider batching in future BC.

### ✅ Positive: Non-blocking behavior confirmed (double try/except safety net)
### ✅ Positive: All 7 phases included in report (Phase 0-6)
### ✅ Positive: HTML escaping correct via `_esc()`

---

## 2. OBSIDIAN Store (`src/ifds/data/obsidian_store.py` + `phase5_obsidian.py`)

### ✅ Positive: Atomic writes via tempfile + os.replace
### ✅ Positive: Duplicate date deduplication correct
### ✅ Positive: Corrupt data handling (JSONDecodeError, OSError → returns `[]`)
### ✅ Positive: Graceful degradation UNDETERMINED → PARTIAL → COMPLETE
### ✅ Positive: >=21 threshold correctly enforced via `min_periods`

### Finding O1 — [STYLE] Single-process assumption (line 605)

Between load and save, no file locking. Safe in current single-cron architecture but would need locking for concurrent access.

---

## 3. Paper Trading Scripts (`scripts/paper_trading/`)

### Finding PT1 — [CRITICAL] Circuit breaker does NOT halt order submission (submit_orders.py, lines 211-215)

The circuit breaker detects cumulative P&L below -$5,000 threshold, sends Telegram alert, logs warning, then **continues to submit orders**. The log literally says "Continuing."

```python
if cb_alert:
    msg = f"... Continuing."
    logger.warning(msg)
    send_telegram(msg)
# Execution continues to dry-run or live mode
```

**Impact:** In a financial system requiring human-in-the-loop, a circuit breaker that warns but does not halt defeats its purpose.

**CC task:** Either `sys.exit(1)` after alert, or require `--override-circuit-breaker` flag:
```python
if cb_alert and not args.override_cb:
    logger.error("Circuit breaker triggered. Use --override-circuit-breaker to proceed.")
    sys.exit(1)
```

### Finding PT2 — [CRITICAL] Cumulative P&L double-counting (eod_report.py, lines 216-264)

`update_cumulative_pnl` has NO idempotency guard. Running EOD script twice on the same day:
1. Increments `trading_days` again (double-counting)
2. Adds `daily_pnl` to `cumulative_pnl` again (doubling the day's P&L)
3. Appends duplicate entry to `daily_history`

No check for whether `today_str` already exists in `daily_history`.

**CC task:** Add idempotency check:
```python
existing_dates = {d['date'] for d in data.get('daily_history', [])}
if today_str in existing_dates:
    logger.warning(f"Day {today_str} already in cumulative P&L -- skipping update")
    return data, 0.0
```

### Finding PT3 — [MEDIUM] IBKR commission MAX_FLOAT sentinel (eod_report.py, line 126)

IBKR's `commissionReport.commission` may be `1.7976931348623157e+308` (MAX_FLOAT) when not yet reported. This would produce wildly incorrect commission values.

**CC task:** Add sanity check: `if comm > 1e6: comm = 0.0`

### Finding PT4 — [MEDIUM] Gross P&L excludes commissions (eod_report.py, lines 159-160)

P&L calculation: `pnl = (sell['price'] - avg_entry) * sell['qty']` — commissions not subtracted. Cumulative P&L therefore overstates actual returns.

**CC task:** Either compute net P&L or document explicitly that `pnl` is gross.

### Finding PT5 — [MEDIUM] No CSV found exits with code 0 (submit_orders.py, lines 199-200)

`sys.exit(0)` when no CSV found — tells cron the run was successful. Should be `sys.exit(1)` or Telegram alert.

### Finding PT6 — [MEDIUM] Relative paths depend on CWD (submit_orders.py, lines 75-92)

`find_todays_csv()` uses relative `output/` directory. Must run from project root or paths break.

**CC task:** Resolve relative to script location: `Path(__file__).resolve().parent.parent.parent`

### Finding PT7 — [MEDIUM] cumulative_pnl.json no file locking (eod_report.py, lines 220-262)

Read-write without `fcntl.flock()`. If submit_orders (reads for circuit breaker) and eod_report (writes) overlap, data loss possible. Current 5-minute cron gap makes this unlikely but not impossible.

### Finding PT8 — [MEDIUM] nuke.py skips connection retry logic (nuke.py, lines 39-44)

Direct `IB().connect()` without shared `lib/connection.py` retry logic.

**CC task:** Use `from lib.connection import connect`.

---

## 4. CSV Execution Plan (`src/ifds/output/execution_plan.py`)

### Finding EP1 — [MEDIUM] Null attribute risk in full_scan_matrix (lines 147-149)

Sub-score calculations assume `stock.flow`, `stock.fundamental`, `stock.technical` are always populated. If any is `None` (unlikely for passed stocks, possible for early-excluded), raises `AttributeError`.

**CC task:** Add null checks or try/except per row.

---

## 5. Phase 4 Snapshot (`src/ifds/data/phase4_snapshot.py`)

### Finding PH1 — [MEDIUM] Non-atomic write (lines 36-37)

Direct `gzip.open` write — no tempfile + os.replace pattern. Process kill mid-write = corrupt `.json.gz`.

**CC task:** Apply same atomic write pattern as `ObsidianStore._atomic_write`.

### Finding PH2 — [MEDIUM] No corrupt snapshot recovery (lines 52-67)

Corrupt gzip files propagate exceptions to caller. No try/except fallback.

**CC task:** Wrap in try/except, return `[]` on corruption (mirror ObsidianStore.load pattern).

---

## Summary

| Severity | Count | Key Findings |
|----------|-------|-------------|
| **CRITICAL** | 2 | PT1: Circuit breaker non-halt, PT2: PnL double-counting |
| **MEDIUM** | 9 | T1, T2, PT3-PT8, EP1, PH1, PH2 |
| **STYLE** | 3 | T3, O1, sequential earnings calls |

## Priority Task List for CC

### Immediate (CRITICAL — financial risk)
1. ☐ **Circuit breaker must halt** — `submit_orders.py` line 211-215: exit(1) or require --override flag
2. ☐ **EOD idempotency guard** — `eod_report.py` line 216-264: check if date already in history before appending

### Next session (MEDIUM)
3. ☐ IBKR commission MAX_FLOAT check — `eod_report.py` line 126
4. ☐ Telegram part2 return value capture — `telegram.py` line 59-65
5. ☐ EARN column length validation — `telegram.py` line 423
6. ☐ Phase 4 snapshot atomic write — `phase4_snapshot.py` lines 36-37
7. ☐ Phase 4 snapshot corrupt recovery — `phase4_snapshot.py` lines 52-67
8. ☐ submit_orders exit code fix — line 199-200
9. ☐ submit_orders absolute paths — lines 75-92
10. ☐ nuke.py use shared connection — lines 39-44

### Backlog (STYLE)
11. ☐ Batch earnings date API calls
12. ☐ cumulative_pnl.json file locking
13. ☐ Document gross vs net P&L convention
