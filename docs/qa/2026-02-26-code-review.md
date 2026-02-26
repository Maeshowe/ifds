# QA Audit — Code Review

**Date:** 2026-02-26
**Auditor:** QA Layer (CC desktop.app)
**Scope:** src/ifds/ (all Python source)
**Mode:** READ-ONLY

---

## Finding F1 — [CRITICAL] asyncio.gather without return_exceptions (phase1_regime.py:203)

**File:** `src/ifds/phases/phase1_regime.py`, line 203

```python
results = await asyncio.gather(
    *[polygon.get_grouped_daily(day_str) for day_str in days]
)
```

Fires ~40 concurrent requests without `return_exceptions=True`. A single API failure (429, timeout) **cancels all remaining tasks** and crashes Phase 1. All other gather calls in the codebase (phase4:970, phase4:1024, phase5:411, phase5:417, validator:164) correctly use `return_exceptions=True`.

**Impact:** Production risk — a transient Polygon error kills the entire daily pipeline run.
**CC task:** Add `return_exceptions=True`, filter `BaseException` results in the loop below.

---

## Finding F2 — [MEDIUM] PositionSizing copy drops mm_regime + unusualness_score (phase6_sizing.py)

**File:** `src/ifds/phases/phase6_sizing.py`, lines 622-645 and 682-707

Both `_replace_quantity()` and inline `PositionSizing(...)` in `_apply_position_limits()` omit `mm_regime` and `unusualness_score`. These default to `""` and `0.0`, silently dropping OBSIDIAN metadata.

**Impact:** When OBSIDIAN activates (BC17+), any position whose quantity gets capped loses its MM regime and unusualness score in the execution plan and Telegram report.
**CC task:** Use `dataclasses.replace(pos, quantity=new_qty)` instead of manual field copying. This prevents future field drift.

---

## Finding F3 — [MEDIUM] Hardcoded +5 VWAP bonus not from config (phase4_stocks.py:547)

**File:** `src/ifds/phases/phase4_stocks.py`, line 547

```python
if (close - vwap) / vwap > 0.01:
    buy_pressure_score += 5
```

All other scoring bonuses come from `config.tuning[...]`. This `+5` and `0.01` threshold are hardcoded, breaking single-source-of-truth and making them invisible to SIM-L2 parameter sweeps.

**CC task:** Add `vwap_strong_accumulation_bonus` and `vwap_strong_accumulation_threshold` to `defaults.py`.

---

## Finding F4 — [MEDIUM] Hardcoded institutional ownership scores (phase4_stocks.py:791-796)

**File:** `src/ifds/phases/phase4_stocks.py`, lines 791-796

```python
if change_pct > 0.02:
    inst_score = 10
elif change_pct < -0.02:
    inst_score = -5
```

Scores `+10`/`-5` and thresholds `0.02`/`-0.02` are hardcoded. Inconsistent with all other fundamental scoring factors from `config.tuning`.

**CC task:** Add `funda_inst_increasing_bonus`, `funda_inst_decreasing_penalty`, `funda_inst_change_threshold` to `defaults.py`.

---

## Finding F5 — [MEDIUM] except Exception: pass without logging (9 locations)

| File | Line | Context |
|------|------|---------|
| `phases/phase5_gex.py` | 118, 469 | OBSIDIAN analysis failures — **most concerning**, zero audit trail |
| `data/obsidian_store.py` | 82 | Store persistence failure |
| `data/signal_dedup.py` | 59 | Atomic write tempfile cleanup |
| `data/cache.py` | 64 | Cache write failure |
| `state/history.py` | 72, 132 | History persistence failures |
| `sim/comparison.py` | 68 | T-test failure |
| `output/telegram.py` | 302 | Earnings date lookup |
| `phases/phase2_universe.py` | 276, 285 | Earnings check failures (fail-open) |

**Impact:** If OBSIDIAN systematically fails for all tickers, there is no log trail at all.
**CC task:** Add `logger.log(...)` or `logging.debug(...)` in each except block, especially Phase 5 OBSIDIAN paths.

---

## Finding F6 — [MEDIUM] open() without context manager (events/logger.py:31)

**File:** `src/ifds/events/logger.py`, line 31

```python
self._file_handle = open(self._log_file, "a")
```

Not wrapped in `with` statement. While `__enter__/__exit__` exist and `runner.py:493` calls `close()` in `finally`, any other usage could leak the file handle.

**CC task:** Document that `EventLogger` must be used as context manager, or implement lazy open.

---

## Finding F7 — [STYLE] time.time() vs time.monotonic() inconsistency (phase6_sizing.py:67)

Phase 6 uses `time.time()` for duration. All other phases use `time.monotonic()` (immune to NTP jumps).
**CC task:** Change to `time.monotonic()`.

---

## Finding F8 — [MEDIUM] funda_score unbounded while flow_score capped (phase4_stocks.py:835)

**File:** `src/ifds/phases/phase4_stocks.py`, line 835

```python
flow_score = min(100, max(0, _BASE_SCORE + flow.rvol_score))    # capped [0, 100]
funda_score = _BASE_SCORE + fundamental.funda_score               # UNBOUNDED
```

A ticker with maximum fundamental bonuses can exceed 100, pushing combined score beyond expected range. At 30% weight, this distorts the clipping threshold logic.

**Impact:** SIM-L2 comparisons may produce misleading results.
**CC task:** Add `funda_score = min(100, max(0, funda_score))`.

---

## Finding F9 — [STYLE] ~600 lines sync/async code duplication (phase5_gex.py + phase4_stocks.py)

Sync and async paths are nearly identical (~300 lines each). Bug fixes must be applied twice. Already happened: OBSIDIAN `except Exception: pass` exists in 4 locations.

**CC task:** Extract shared scoring/filtering logic into common helpers. Async path should only differ in data fetching.

---

## Finding F10 — [STYLE] date.today() called 65 times across 21 files, not pinned

If a run crosses midnight (unlikely at 22:00 CET but possible manually), different phases compute with different "today" values. `signal_dedup._compute_hash` calls `date.today()` three separate times.

**CC task:** Pin `today = date.today()` once in runner, pass to all phases.

---

## Finding F11 — [STYLE] EARN column string slice without length guard (telegram.py:423)

Cross-reference with Pipeline Output T2. Same finding.

---

## Finding F12 — [STYLE] ThreadPoolExecutor exception swallowed without logging (phase2_universe.py:279-288)

Fail-open by design, but unlogged. If FMP has systematic issues, all tickers pass through with no audit trail.

**CC task:** Add `logger.log(...)` in the exception handler.

---

## Positive Observations

- ✅ No SQL injection risk — all SQLite uses parameterized queries
- ✅ No `os.system`/`subprocess` — no command injection surface
- ✅ No `global` state — all properly scoped
- ✅ No bare `except:` — all specify at least `Exception`
- ✅ No hardcoded API keys — all from `.env`/config
- ✅ `asyncio.run()` correctly used from sync entry points only
- ✅ Atomic file writes consistent for state files
- ✅ Fat finger protection thorough (NaN/Inf guards, qty caps, notional limits)
- ✅ `return_exceptions=True` used correctly in 5/6 gather calls

---

## Summary

| Severity | Count | Key Findings |
|----------|-------|-------------|
| **CRITICAL** | 1 | F1: asyncio.gather without return_exceptions in Phase 1 |
| **MEDIUM** | 6 | F2-F6, F8: OBSIDIAN field drop, hardcoded scores, silent exceptions, unbounded funda_score |
| **STYLE** | 5 | F7, F9-F12: timing, duplication, date pinning, string safety, logging |
| **Total** | **12** | |

## Priority Task List for CC

### Immediate (CRITICAL — production risk)
1. ☐ **Fix asyncio.gather in Phase 1** — `phase1_regime.py` line 203: add `return_exceptions=True`

### Before BC17 (MEDIUM — OBSIDIAN activation)
2. ☐ Use `dataclasses.replace()` in phase6_sizing.py — prevent mm_regime/unusualness_score loss
3. ☐ Move hardcoded +5 VWAP bonus to config — phase4_stocks.py line 547
4. ☐ Move hardcoded inst ownership scores to config — phase4_stocks.py lines 791-796
5. ☐ Add logging to 9 silent `except Exception: pass` blocks — especially phase5_gex.py
6. ☐ Cap funda_score to [0, 100] — phase4_stocks.py line 835

### Backlog (STYLE)
7. ☐ EventLogger lazy open or document context manager requirement
8. ☐ time.monotonic() consistency in phase6
9. ☐ Extract sync/async shared logic (~600 lines dedup)
10. ☐ Pin date.today() once in runner
11. ☐ Thread pool exception logging in phase2
