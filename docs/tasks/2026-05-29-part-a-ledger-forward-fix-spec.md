# Part A — Ledger forward-fix (P0 §0.11) — LOCKED SPEC for clean-session implementation

**Status**: WIP (design locked 2026-05-29; implementation + tests COMPLETE 2026-06-01, local commits done; Mac Mini push+deploy+live-smoke PENDING Tamás approval — see Deploy runbook below)
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

---

## Implementation complete — 2026-06-01 (CC, local) ✅

All six pieces implemented + tested locally. Full suite **1862 passed, 0 failure, 0 warning** (baseline 1828 → +34 Part A tests). Commits (local, awaiting Tamás push approval):

1. `refactor(lib): move pure pnl helpers from retroactive_reconcile_w21 to lib/ibkr_reconciliation`
2. `feat(pnl): pending-exits ledger module (lib/pending_exits.py)`
3. `feat(close_positions): write pending-exit ledger entries (try/except guarded)`
4. `feat(daily_metrics): record_pending_exits — sole cumulative_pnl writer + --date backfill`
5. `feat(eod_report): neutralize cumulative write + add silent-0-pnl Telegram WARNING`
6. `test(pnl): exit_type→counter mapping + commission field (Part A regression)` + style/seed commits

### Verification results (the 3 open items, now closed)
- **clientId=18 free** ✅ — grep of `scripts/paper_trading/*.py` confirms 10–17 in use (submit/close/eod/nuke/monitor/trail/avwap/gateway), 18 unassigned. Constant: `daily_metrics.RECORD_PENDING_CLIENT_ID = 18`.
- **main() call order** ✅ — `record_pending_exits(target_date)` runs BEFORE `build_daily_metrics(target_date)` in `daily_metrics.main()`, guarded by try/except (a recorder failure does not block the metrics build; ledger is idempotent → next run retries).
- **`fetch_today_executions` backfill** ✅ — the helper takes `today: date` and post-filters `exec_date != today`, so `--date 2026-05-28` filters to that date's fills. No call-site change needed.

### Day 9 AMH backfill decision: option (a) — ledger seed
The Day 9 ledger never existed (close_positions started writing it only with this deploy), so AMH 5/28 has no native ledger entry. Per spec step 4, seed ONE entry then let the recorder match the live IBKR fill. Reproducible script: `scripts/admin/seed_amh_day9_ledger.py` (idempotent; `--dry-run`/`--apply`).

AMH Day 9 leg (the 249-share TIME_STOP, NOT the 2026-05-29 re-entry):
`entry_price=32.11, qty=249, entry_date=2026-05-22, exit_type=TIME_STOP, sector="Real Estate"`.

## Deploy runbook (Mac Mini — **Tamás approval gated**, weekend = ideal, first live trial Mon 21:40)

> Push + Mac Mini pull + deploy require Tamás's explicit *"jóváhagyom a push + deploy-t"*. Until then this stays local.

```bash
# 0. (MacBook) push after approval
git push origin master

# 1. (Mac Mini) pull
ssh ifds-mini
cd ~/SSH-Services/ifds && git pull origin master

# 2. pre-flight: full suite green on Mac Mini
python -m pytest tests/ -q   # expect 1862 passed

# 3. backup cumulative (canonical -651.10 baseline)
cp scripts/paper_trading/logs/cumulative_pnl.json \
   scripts/paper_trading/logs/cumulative_pnl.json.bak.pre_partA.$(date +%Y%m%d_%H%M%S)

# 4. seed Day 9 AMH ledger + first recorder run (IBKR Gateway must be up)
python scripts/admin/seed_amh_day9_ledger.py --dry-run    # inspect
python scripts/admin/seed_amh_day9_ledger.py --apply       # writes state/pending_exits/2026-05-28.json
source .env && python scripts/paper_trading/daily_metrics.py --date 2026-05-28

# 5. verify: cumulative moved from -651.10 by AMH realized; ledger entry processed=true
python -c "import json; d=json.load(open('scripts/paper_trading/logs/cumulative_pnl.json')); print('cumulative:', d['cumulative_pnl'], 'days:', d['trading_days'])"
cat state/pending_exits/2026-05-28.json   # AMH key processed:true
```

The exact AMH realized comes from the IBKR `get_account_trades` (DAYS_30) SLD fill on 2026-05-28. After step 5 confirms, the `data(reconcile)` commit documents the new cumulative.

**If the smoke fails**: backup at `cumulative_pnl.json.bak.pre_partA.*`; delete `state/pending_exits/2026-05-28.json` to re-seed. Do NOT re-run `canonical_pnl_reconstruction.py --apply` once Part A has written (it wholesale-replaces daily_history).

### From Day 10 (5/29) onward
`close_positions` writes the ledger natively at each swing exit → `record_pending_exits` auto-captures at the 22:10 cron. No manual seed ever again.
