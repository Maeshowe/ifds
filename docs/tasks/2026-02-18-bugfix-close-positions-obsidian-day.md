# Task: close_positions.py bug fix + OBSIDIAN day counter fix

**Date:** 2026-02-18
**Priority:** HIGH (paper trading runs today at 15:35 CET, fix must be deployed before 21:45 CET)
**Scope:** 2 bugs, no new features

---

## Bug 1: close_positions.py fails to close late-filling positions (BHP/EGP overnight carry)

### Problem

On 2026-02-17, `close_positions.py` ran at 21:45 CET and submitted MOC orders for 4 positions (IFF, OHI, AEE, WEC). However, BHP and EGP entry orders had NOT yet filled at 21:45 — they filled later (between 21:45 and market close). As a result:

- `close_positions.py` didn't see them as positions → no MOC submitted
- `eod_report.py` at 22:05 tried to submit MOC but it was after the 15:50 ET cutoff → IBKR cancelled the MOC orders
- BHP (51 shares) and EGP (55 shares) carried overnight, plus AVDL.CVR (69 shares, already filtered by `.CVR` check)

**Log evidence (22:05:03):**
```
[WARNING] Still 3 open positions!
[WARNING]   AVDL.CVR: 69.0 shares
[WARNING]   EGP: 55.0 shares
[WARNING]   BHP: 51.0 shares
```

### Root Cause

`close_positions.py` only checks `ib.positions()` for existing fills. If an entry order fills AFTER close_positions.py runs (between 21:45 and 22:00 CET / 15:45-16:00 ET), the position is never closed.

### Fix Required

In `close_positions.py`, BEFORE submitting MOC orders, **cancel all open IFDS bracket orders** that haven't filled yet. This prevents late fills after MOC cutoff.

Add this logic after connecting to IBKR, before the positions loop:

```python
# Cancel unfilled IFDS entry orders to prevent late fills
open_orders = ib.openOrders()
ifds_orders = [o for o in open_orders
               if hasattr(o, 'orderRef') and o.orderRef
               and o.orderRef.startswith('IFDS_')]
if ifds_orders:
    for order in ifds_orders:
        ib.cancelOrder(order)
    ib.sleep(2)
    cancelled_count = len(ifds_orders)
    print(f"  Cancelled {cancelled_count} unfilled IFDS bracket orders")
else:
    print("  No unfilled IFDS orders to cancel")
```

**Key points:**
- Cancel ALL remaining IFDS orders (entry + TP + SL children) — the `orderRef` prefix is `IFDS_`
- Do this BEFORE checking positions for MOC, so that if entry was just about to fill, it won't
- The `ib.sleep(2)` is important to let cancellations propagate
- After cancellation, THEN proceed with existing MOC logic for positions that DID fill
- Print count of cancelled orders for logging

### File to modify
`scripts/paper_trading/close_positions.py`

### Testing
- The logic should be: (1) connect → (2) cancel all IFDS orders → (3) sleep(2) → (4) query positions → (5) submit MOC for remaining positions
- Print count of cancelled orders for logging
- Verify existing tests still pass

---

## Bug 2: OBSIDIAN day counter always shows "day 1/21"

### Problem

The Telegram/console report shows:
```
OBSIDIAN: collect-only (day 1/21)
Baseline: 0 complete / 0 partial / 100 empty
```

This has shown "day 1/21" for 4 consecutive trading days (Feb 12, 16, 17, 18). The data IS being collected correctly (state/obsidian/*.json files have 4 entries each), but the day counter is wrong.

### Root Cause

In `src/ifds/output/telegram.py`, function `_format_phases_5_to_6()`, the day estimation logic:

```python
if states["complete"] > 0:
    day_est = "21+"
elif states["partial"] > 0:
    day_est = "~10"
else:
    day_est = "1"    # ← ALWAYS "1" until PARTIAL threshold
```

Since `obsidian_min_periods = 21`, ALL tickers remain EMPTY (z-scores return None when n < 21) until day 21. So the counter shows "1" for 21 straight days.

### Fix Required — Option A (minimal change):

1. **In `src/ifds/models/market.py`**, add to `ObsidianAnalysis` dataclass:
   ```python
   baseline_days: int = 0  # Number of historical entries in store
   ```

2. **In `src/ifds/phases/phase5_obsidian.py`**, in `run_obsidian_analysis()`, after `historical = store.load(ticker)`:
   ```python
   result.baseline_days = len(historical)
   ```
   Note: this should be set even in the early-return path (when bar_features is empty).

3. **In `src/ifds/output/telegram.py`**, in `_format_phases_5_to_6()`, replace the day estimation block with:
   ```python
   # Actual collection day from store entry counts
   if ctx.obsidian_analyses:
       max_days = max(o.baseline_days for o in ctx.obsidian_analyses)
   else:
       max_days = 0
   min_periods = config.core.get("obsidian_min_periods", 21)
   lines.append(f"OBSIDIAN: {status} (day {max_days}/{min_periods})")
   ```

4. **Also check `src/ifds/output/console.py`** — if it has the same day estimation pattern, apply the same fix.

### Testing
- Add test that verifies `baseline_days` is populated correctly (0, 5, 21 entries)
- Verify telegram output shows correct day count
- All existing tests must pass

---

## Files to modify

1. `scripts/paper_trading/close_positions.py` — Bug 1: cancel orders before MOC
2. `src/ifds/models/market.py` — Bug 2: add `baseline_days` field
3. `src/ifds/phases/phase5_obsidian.py` — Bug 2: populate `baseline_days`
4. `src/ifds/output/telegram.py` — Bug 2: use actual day count
5. `src/ifds/output/console.py` — Bug 2: same fix if applicable

## Validation

- `pytest` — all 752+ tests must pass
- No new dependencies
- Deploy to Mac Mini before 21:45 CET (close_positions.py cron run)

## Out of scope

- BHP/EGP cleanup (today's close_positions.py with the fix will handle them if still open)
- AVDL.CVR position (corporate action, not IFDS-related)
- SimEngine L2 planning (separate task)
