# Task: Fix Paper Trading ClientID Collision + MOC Reliability

**Date:** 2026-02-20
**Priority:** HIGH (paper trading Day 4 runs today, fix must be deployed before 15:35 CET submit)
**Scope:** ClientID separation + MOC robustness, no new features

---

## Problem

On 2026-02-19, `close_positions.py` (21:45 CET) failed to close 4 positions (BLCO 181, LH 15, MRNA 55, NOV 196). These were Bracket B (67%) positions where TP2 was not hit during the day. The positions carried overnight and had to be nuke'd manually on 2026-02-20.

### Root Cause: ClientID Collision

All three paper trading scripts use the same `CLIENT_ID = 10` in `scripts/paper_trading/lib/connection.py`:

```python
CLIENT_ID = 10
```

The cron schedule:
```
15:35 CET — submit_orders.py (clientId=10)
21:45 CET — close_positions.py (clientId=10)
22:05 CET — eod_report.py (clientId=10)
```

If a previous script's connection is not fully cleaned up (IBKR Gateway keeps the session alive briefly), the next script's `connect()` fails silently or gets stale state.

### Evidence from logs

```
MOC Close — 2026-02-19          ← header printed BEFORE connect()
22:05:01 [INFO] Connecting...    ← this is eod_report.py, NOT close_positions.py
```

The close_positions.py printed its header, then the `connect()` call either failed (clientId=10 already in use) or raised an exception that was swallowed. No MOC orders were submitted. The eod_report.py at 22:05 successfully connected, cancelled orders, but doesn't submit MOC (not its job).

### Secondary Issue: Print before connect

In `close_positions.py`, the header `print(f"\nMOC Close — {today_str}")` executes BEFORE `connect()`. If connect fails, the log shows the header but no error — making it look like the script ran successfully.

---

## Fix Required

### 1. Separate ClientIDs

In `scripts/paper_trading/lib/connection.py`, change:

```python
# Before
CLIENT_ID = 10

# After — remove single constant, let each script specify its own
DEFAULT_CLIENT_ID = 10
```

Each script should use a unique clientId:

| Script | ClientID | Rationale |
|--------|----------|-----------|
| submit_orders.py | 10 | Entry orders — primary |
| close_positions.py | 11 | MOC closing — must not conflict |
| eod_report.py | 12 | Report — read-only + cancel |
| nuke.py | 13 | Emergency cleanup |

Modify `connect()` signature — it already accepts `client_id` parameter, so no change needed there.

Modify each script's `main()` to pass its own clientId:
- `submit_orders.py`: `ib = connect(client_id=10)`
- `close_positions.py`: `ib = connect(client_id=11)`
- `eod_report.py`: `ib = connect(client_id=12)`
- `nuke.py`: `ib = connect(client_id=13)`

### 2. Move print after connect in close_positions.py

Move the header print AFTER successful connection so that if connect fails, the log shows an error, not a false success.

```python
# Before
today_str = date.today().strftime('%Y-%m-%d')
print(f"\nMOC Close — {today_str}")
ib = connect()

# After
today_str = date.today().strftime('%Y-%m-%d')
ib = connect(client_id=11)
print(f"\nMOC Close — {today_str}")
```

### 3. Add ib.sleep(3) after connect for synchronization

The IBKR API needs time to synchronize positions and orders after connection. Without this, `ib.positions()` may return empty.

In `close_positions.py`, after `connect()`:

```python
ib = connect(client_id=11)
ib.sleep(3)  # Wait for position/order synchronization
print(f"\nMOC Close — {today_str}")
```

### 4. Shift cron timing: 21:45 → 21:40

Give close_positions.py 10 minutes before market close (15:50 ET = 21:50 CET) instead of 5. This provides more buffer for connection, order cancellation, and MOC submission.

```
# Before
45 21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/close_positions.py >> logs/paper_trading.log 2>&1

# After
40 21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/close_positions.py >> logs/paper_trading.log 2>&1
```

**Note:** The cron change must be done manually by the user (`crontab -e`). The CC task only modifies Python files.

### 5. Add error logging on connect failure

The current `connect()` in `lib/connection.py` calls `sys.exit(1)` on failure. This is fine, but the error message should be more visible:

```python
def connect(host='127.0.0.1', port=PAPER_PORT, client_id=DEFAULT_CLIENT_ID):
    """Connect to IBKR Gateway. Exits on failure."""
    ib = IB()
    try:
        ib.connect(host, port, clientId=client_id)
        ib.sleep(2)  # Wait for initial synchronization
        logger.info(f"Connected to IBKR: {host}:{port} (clientId={client_id})")
        return ib
    except Exception as e:
        logger.error(f"IBKR connection FAILED (clientId={client_id}): {e}")
        sys.exit(1)
```

---

## Files to modify

1. `scripts/paper_trading/lib/connection.py` — clientId default rename, add sleep after connect, log clientId
2. `scripts/paper_trading/close_positions.py` — use client_id=11, move print after connect, add ib.sleep(3)
3. `scripts/paper_trading/eod_report.py` — use client_id=12
4. `scripts/paper_trading/submit_orders.py` — explicit client_id=10
5. `scripts/paper_trading/nuke.py` — use client_id=13

## Validation

- `pytest tests/ -q` — all 817 tests must pass (no test changes expected, these are scripts not in the test suite)
- Manual verification: run `close_positions.py` and `eod_report.py` in sequence — both should connect without conflict
- Check logs after next cron run (today 21:40 CET) for "Connected to IBKR" with correct clientId

## Cron Change (MANUAL — user must do this)

```bash
crontab -e
# Change:
# 45 21 * * 1-5 ... close_positions.py ...
# To:
# 40 21 * * 1-5 ... close_positions.py ...
```

## Out of scope

- Swing hybrid exit implementation (BC20A)
- Bracket A/B split logic changes (that's a design decision, not a bug)
- AVDL.CVR cleanup (non-tradable, ignore)
