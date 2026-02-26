# Task: eod_report.py — idempotency guard

**Date:** 2026-02-26
**Priority:** CRITICAL — financial data integrity
**Source:** QA Audit `2026-02-26-pipeline-output.md` Finding PT2
**Scope:** `scripts/paper_trading/eod_report.py`, lines 216-264

---

## A probléma

`update_cumulative_pnl()` nem ellenőrzi, hogy az adott nap már szerepel-e a `daily_history`-ban. Ha az EOD script kétszer fut ugyanazon a napon (cron bug, manuális újrafuttatás):

1. `trading_days` duplán nő
2. `cumulative_pnl` duplán növekszik (a napi P&L kétszer adódik hozzá)
3. `daily_history`-ban duplikált entry keletkezik

**Valós kockázat:** Ma a KMI manuális frissítés miatt kézzel futtatjuk az EOD scriptet — idempotency guard nélkül ez pontosan ezt a hibát okozná.

---

## Fix

A `update_cumulative_pnl()` függvény elején add hozzá:

```python
def update_cumulative_pnl(pnl_file: Path, today_str: str, daily_pnl: float, ...):
    # Load existing data
    data = _load_pnl_file(pnl_file)
    
    # IDEMPOTENCY GUARD
    existing_dates = {d['date'] for d in data.get('daily_history', [])}
    if today_str in existing_dates:
        logger.warning(f"EOD idempotency: {today_str} already in history — skipping update")
        return data, 0.0
    
    # ... rest of function unchanged
```

---

## Tesztelés

```python
def test_eod_idempotency_second_run_skipped():
    """Ha az EOD kétszer fut ugyanazon a napon, a második futás nem módosít semmit."""
    # First run
    data, _ = update_cumulative_pnl(pnl_file, "2026-02-25", 136.81, ...)
    cumulative_after_first = data['cumulative_pnl']
    days_after_first = data['trading_days']
    
    # Second run — same date
    data2, _ = update_cumulative_pnl(pnl_file, "2026-02-25", 136.81, ...)
    assert data2['cumulative_pnl'] == cumulative_after_first  # nem duplázódott
    assert data2['trading_days'] == days_after_first          # nem nőtt
    assert len(data2['daily_history']) == len(data['daily_history'])  # nincs duplikált entry

def test_eod_different_days_both_recorded():
    """Két különböző nap mindkettő bekerül."""
    ...
```

---

## Git

```bash
git add scripts/paper_trading/eod_report.py tests/test_eod_report.py
git commit -m "fix: EOD idempotency guard — skip if date already in history

Running eod_report.py twice on the same day doubled cumulative P&L
and trading_days count. Added guard: if today_str in existing_dates,
log warning and return without modification.
2 new tests.

QA Finding: 2026-02-26-pipeline-output.md PT2 [CRITICAL]"
git push
```
