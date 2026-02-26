# Task: submit_orders.py — circuit breaker halt + --override flag

**Date:** 2026-02-26
**Priority:** CRITICAL — financial risk
**Source:** QA Audit `2026-02-26-pipeline-output.md` Finding PT1
**Feedback:** `2026-02-26-feedback-circuit-breaker.md`
**Scope:** `scripts/paper_trading/submit_orders.py`, lines 211-215

---

## A probléma

A circuit breaker kumulatív P&L küszöb alatt figyelmeztet, de **folytatja az order submissiont**:

```python
if cb_alert:
    msg = f"... Continuing."
    logger.warning(msg)
    send_telegram(msg)
# Execution continues — orders submitted anyway
```

## Design döntés

A nyers `sys.exit(1)` nem megfelelő — paper trading fázisban előfordulhat hogy tudatosan akarunk override-olni (pl. manuális futtatás után nagy veszteségnapon). Az `--override-circuit-breaker` flag megőrzi a biztonságot miközben lehetővé teszi a tudatos döntést.

---

## Fix

### 1. Argument parser bővítése

```python
parser.add_argument(
    '--override-circuit-breaker',
    action='store_true',
    help='Override circuit breaker and submit orders anyway (use with caution)'
)
```

### 2. Circuit breaker logika módosítása

```python
# ELŐTTE
if cb_alert:
    msg = f"⚠️ CIRCUIT BREAKER: ... Continuing."
    logger.warning(msg)
    send_telegram(msg)

# UTÁNA
if cb_alert:
    if args.override_circuit_breaker:
        msg = f"⚠️ CIRCUIT BREAKER TRIGGERED — override flag used, continuing.\n{cb_detail}"
        logger.warning(msg)
        send_telegram(msg)
    else:
        msg = f"🛑 CIRCUIT BREAKER TRIGGERED — order submission HALTED.\n{cb_detail}\nUse --override-circuit-breaker to proceed."
        logger.error(msg)
        send_telegram(msg)
        sys.exit(1)
```

---

## Tesztelés

```python
def test_circuit_breaker_halts_without_flag():
    """Circuit breaker trigger → sys.exit(1) ha nincs --override flag."""
    with pytest.raises(SystemExit) as exc_info:
        run_submit(args=[], cumulative_pnl=-6000)
    assert exc_info.value.code == 1

def test_circuit_breaker_continues_with_override_flag():
    """Circuit breaker trigger → folytatódik --override-circuit-breaker flaggel."""
    result = run_submit(args=['--override-circuit-breaker'], cumulative_pnl=-6000)
    assert result == 'submitted'

def test_circuit_breaker_telegram_alert_on_halt():
    """Halt esetén Telegram üzenet tartalmazza a 'HALTED' szót."""
    ...
```

---

## Git

```bash
git add scripts/paper_trading/submit_orders.py tests/test_submit_orders.py
git commit -m "fix: circuit breaker halts order submission unless --override-circuit-breaker

Previously circuit breaker warned but continued trading.
Now: sys.exit(1) on trigger, unless --override-circuit-breaker flag given.
Telegram alert distinguishes HALTED vs override.
3 new tests.

Design decision: --override preferred over bare sys.exit(1) to allow
conscious manual override without blocking the day.
Ref: docs/qa/2026-02-26-feedback-circuit-breaker.md

QA Finding: 2026-02-26-pipeline-output.md PT1 [CRITICAL]"
git push
```
