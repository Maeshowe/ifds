# Part A — Ledger forward-fix (P0 §0.11) — LOCKED SPEC for clean-session implementation

**Status**: OPEN (design locked 2026-05-29, implementation pending in a fresh CC session)
**Priority**: P0 — realized P&L tracking gap forward-fix
**Why a separate spec**: the 2026-05-29 session degraded (API 400 "thinking blocks" + corrupted file reads — "20:48" leaking into line numbers, garbled content). Implementation of live trading scripts (`close_positions.py`, `eod_report.py`) was halted to avoid a corrupted edit breaking the live MOC SELL. All decisions below are FINAL — a fresh session executes directly.

## Context (verified this session)

- Guard-fixes deployed: `0b2ddaa` (days_held trading-day), `4f2f8c0` (ATR band). Live, working (ST+ROIV entered clean Day 9).
- Part B canonical reconstruction deployed: `7f031e6` — `cumulative_pnl.json` = **-$651.10**, trading_days 8 (Day 1-8). Mac Mini applied.
- **Gap reproduced Day 9 (5/28)**: AMH TIME_STOP MOC SELL 249 @ 21:40 (fill 22:00). `eod_report.py` 22:05 logged **"Trades: 0"**, no trades CSV, cumulative 5/28 entry = pnl=0. AMH realized still MISSING.
- **Root cause**: `eod_report.py` uses `ib.fills()` (clientId=12). The MOC was placed by `close_positions.py` (clientId=11). `ib.fills()` is client-scoped → does NOT see the cross-client MOC fill; also at 22:05 the close-auction fill hasn't propagated. So eod_report records pnl=0 and (via its idempotency guard) locks it.

## Locked design decisions (user-approved 2026-05-29)

1. **`record_pending_exits()` is the SOLE cumulative_pnl.json writer** for swing exits. Lives in `daily_metrics.py`, called in `main()` BEFORE `build_daily_metrics` aggregation (so build reads the updated cumulative). Runs at 22:10 cron (after MOC settles).
2. **`eod_report.py::update_cumulative_pnl` cumulative WRITE is turned OFF** — eod_report keeps trade-report + daily CSV + Telegram (display only), no longer writes cumulative_pnl.json.
3. **eod_report WARNING defensive**: if the existing Day N cumulative entry has `pnl==0` AND eod_report sees an exit-trade for that day → send Telegram WARNING (so a silent 0-pnl day never repeats unnoticed).
4. **Day 9 AMH backfill via Part A itself**: `record_pending_exits` supports a `--date` flag / lookback so the first deploy run captures Day 9 AMH from the ledger (idempotent). Do NOT run a separate canonical re-run — single ledger-native mechanism, validates Part A in live smoke at deploy.
5. Keeps `-$651.10` baseline integrity; Day 9 AMH enters from ONE source (ledger), not two.

## Implementation pieces

### 1. Move pure helpers to `scripts/paper_trading/lib/ibkr_reconciliation.py` (DRY, from `scripts/admin/retroactive_reconcile_w21.py`)
- `update_cumulative_history_entry(cum_data, target_date, *, pnl_delta, commission_delta, trades_delta, filled_delta, counter_increments)` — find-or-create date entry, add deltas, keep history sorted. (NOTE: retroactive copy has a typo `"TIt ME_STOP"` in `append_trade_to_daily_metrics.key_map` — fix to `"TIME_STOP"` when moving.)
- `recompute_cumulative_pnl(cum_data)` — sum daily_history `pnl` (net) → cumulative_pnl + pct + trading_days. (Canonical impl already mirrored in `scripts/admin/canonical_pnl_reconstruction.py::recompute`.)
- Re-point `retroactive_reconcile_w21.py` to import from lib (back-compat: its tests must still pass).

### 2. Ledger module — `scripts/paper_trading/lib/pending_exits.py`
- `append_pending_exit(exit_record, *, ledger_dir="state/pending_exits", today=None)` — append to `{ledger_dir}/{date}.json`. Record: `{key, ticker, entry_price, entry_date, qty, exit_type, sector, submitted_at, processed: false}`. `key = f"{ticker}_{exit_type}_{date}"` (idempotency).
- `load_pending_exits(date, ledger_dir=...)` -> list[dict].
- `mark_processed(date, keys, ledger_dir=...)` — set processed=true for given keys (atomic write).
- All pure/file-only, unit-testable.

### 3. `close_positions.py` ledger write (BOTH modes)
- In `run_swing_eod_flags` and `run_swing_time_stop`: just before the position is dropped from `new_state` (or right after submitting the SELL), call `append_pending_exit({ticker, entry_price, entry_date, qty: qty_remaining (or sold qty for TP1 partial), exit_type: next_action, sector})`.
- **CRITICAL**: wrap in `try/except Exception` that logs but NEVER raises — the ledger write must NOT block the actual SELL. TP1 partial: record the SOLD qty, exit_type=TP1 (position stays open with reduced qty — only the sold leg is a realized exit).

### 4. `record_pending_exits()` in `daily_metrics.py`
- Signature: `record_pending_exits(target_date, *, dry_run=False) -> dict` (summary).
- Load ledger for target_date; filter `processed==false`. If none → return early (no IBKR connect).
- Connect IBKR (own clientId — use a NEW free id, e.g. **clientId=18**; verify not colliding with submit=10/close=11/eod=12/nuke=13/monitor=14/trail=15/avwap=16/gateway=17).
- `fetch_today_executions(ib, target_date)` (already in lib) → SLD fills.
- For each unprocessed ledger entry: match SLD execution(s) by ticker, realized = `compute_pnl(entry_price, fill_price, qty) - commission` (compute_pnl already in lib; commission from execution). exit_type → counter (tp1_hits/tp2_hits/sl_hits/trail_hits/moc_exits via TIME_STOP→moc).
- `update_cumulative_history_entry(...)` per exit + `recompute_cumulative_pnl` → write cumulative_pnl.json (atomic). Mark ledger keys processed. Idempotent: re-run skips processed keys.
- Call it in `daily_metrics.main()` BEFORE `build_daily_metrics`. Add `--date` arg to main for backfill (Day 9 = 2026-05-28).
- If a ledger entry has no matching execution (e.g. fill not found): log WARNING, leave unprocessed (retry next run), do NOT fabricate P&L.

### 5. `eod_report.py` changes
- In `main()`: remove/guard the `update_cumulative_pnl(trades, today_str)` cumulative WRITE (keep building `trades`, `save_daily_csv`, Telegram). Simplest: keep computing daily_pnl for the Telegram display from `trades`, but do not persist to cumulative_pnl.json.
- Add WARNING defensive: after loading cumulative_pnl.json, if the Day N entry exists with `pnl==0` AND `len(trades) > 0` (eod_report saw exit trades) → `send_telegram` WARNING "silent 0-pnl with exits — record_pending_exits may have failed".

### 6. Tests (`tests/test_pending_exits.py`, extend `tests/test_*` for recorder)
- Ledger: append/load/mark-processed idempotency; key uniqueness.
- record_pending_exits pure path: mock executions + ledger → expected cumulative deltas; re-run idempotent (no double-count); missing-execution → unprocessed + warning.
- Helpers moved to lib: existing retroactive tests still green.
- Full suite 0 regression (baseline 1828 + Part B 6 = 1834-ish; verify current baseline first).

## Deploy sequence (clean session)
1. Implement 1-6, full suite green locally.
2. Commit: `feat(pnl): pending-exits ledger + record_pending_exits sole cumulative writer (P0 §0.11 Part A)`. Push (Tamás approval).
3. Mac Mini pull.
4. **Live smoke**: `python scripts/paper_trading/daily_metrics.py --date 2026-05-28` → captures Day 9 AMH from ledger... BUT NOTE: the ledger did NOT exist on Day 9 (close_positions wasn't writing it yet). So Day 9 AMH has NO ledger entry. → Day 9 AMH backfill must instead come from a one-off: either (a) hand-add an AMH ledger entry for 2026-05-28 from known entry ($32.11, 249sh, TIME_STOP) + let record_pending_exits match the IBKR fill, OR (b) a targeted canonical add for AMH only. DECIDE at implementation: cleanest is (a) — seed one ledger entry for AMH 2026-05-28, run `--date 2026-05-28`, verify cumulative moves by AMH realized.
5. From Day 10 (5/29) onward: close_positions writes the ledger natively → record_pending_exits auto-captures at 22:10.

## Open verification at implementation
- Confirm clientId=18 is free (grep crontab + scripts).
- Confirm `daily_metrics.main()` call order (record_pending_exits BEFORE build_daily_metrics).
- Confirm `fetch_today_executions` date post-filter works for a backfill date (not just today).

## Safety net (no data loss)
- `-$651.10` canonical baseline intact (Part B). Day 9 AMH realized is the only missing piece; captured by step 4 above. Live trading unaffected (close_positions still executes SELLs; ledger write is try/except-guarded).
