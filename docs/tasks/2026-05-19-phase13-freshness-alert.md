# Task: Phase 1-3 Vasárnap Heartbeat Alert

**Status:** DONE
**Priority:** P1 (sürgős — vasárnap 2026-05-24 22:00 ELŐTT deploy)
**Created:** 2026-05-19
**Updated:** 2026-05-19 (5 új teszt, cron Sunday 23:00 élesítve, smoke OK)
**Owner:** Claude Code
**Estimated effort:** ~20 min CC

**Source**: [`docs/master-reference/04-risks-and-open-questions.md`](../master-reference/04-risks-and-open-questions.md) §8.2.3 (A megoldás).

---

## 1. A probléma

A swing pivot új cron-architektúra szerint a Phase 1-3 (BMI + Universe + Sector rotation) **heti** vasárnap esti generáció:

```
0 22 * * 0 /Users/safrtam/SSH-Services/ifds/scripts/deploy_daily.sh --phases 1-3
```

A hét egészében a Phase 4-6 a vasárnap esti `state/phase13_ctx.json.gz`-ből dolgozik. **Ha a vasárnapi cron silent fail-el** (pl. a `_exclude_earnings` thread hang §8.2.3 miatt), **a teljes következő hét stale sector context-tel** dolgozik, **NO Telegram alert**.

## 2. Megoldás

Új script `scripts/check_phase13_freshness.py` + crontab entry vasárnap 23:00 CEST (1 óra time-window a 22:00 cronnak).

```python
#!/usr/bin/env python
"""Phase 1-3 freshness check — heti vasárnap esti rebalance verifikáció."""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import requests

CONTEXT_PATH = Path("state/phase13_ctx.json.gz")
MAX_AGE_HOURS = 1  # vasárnap 23:00 - vasárnap 22:00 = 1 óra

def main():
    if not CONTEXT_PATH.exists():
        send_alert("❌ Phase 1-3 context file NEM LÉTEZIK — vasárnapi cron NEM futott")
        sys.exit(1)

    mtime = datetime.fromtimestamp(CONTEXT_PATH.stat().st_mtime)
    age = datetime.now() - mtime

    if age > timedelta(hours=MAX_AGE_HOURS):
        send_alert(
            f"⚠️ Phase 1-3 context STALE — mtime {mtime:%Y-%m-%d %H:%M}, "
            f"age {age.total_seconds() / 3600:.1f}h. "
            f"Vasárnapi cron silent fail gyanú. Manuális futtatás javasolt: "
            f"./scripts/deploy_daily.sh --phases 1-3"
        )
        sys.exit(1)
    else:
        # Heartbeat siker — opcionális Telegram (csak ha env-konfigolt)
        if os.getenv("IFDS_HEARTBEAT_VERBOSE"):
            send_alert(f"✓ Phase 1-3 context fresh (mtime {mtime:%H:%M})")
        sys.exit(0)

def send_alert(message: str):
    token = os.getenv("IFDS_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("IFDS_TELEGRAM_CHAT_ID")
    if token and chat_id:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )

if __name__ == "__main__":
    main()
```

## 3. Crontab entry

```
# Phase 1-3 heartbeat — vasárnap 23:00 (1 óra time-window a 22:00 cronnak)
0 23 * * 0 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/check_phase13_freshness.py >> logs/cron_phase13_heartbeat_$(date +\%Y\%m\%d).log 2>&1
```

## 4. Tesztek

```python
def test_phase13_freshness_alerts_on_missing_file():
    """Ha NINCS state/phase13_ctx.json.gz → Telegram alert + sys.exit(1)."""

def test_phase13_freshness_alerts_on_stale_file():
    """mtime > 1h → Telegram alert + sys.exit(1)."""

def test_phase13_freshness_silent_on_fresh_file():
    """mtime < 1h → no alert, sys.exit(0)."""
```

## 5. Commit message

```
feat(monitoring): Phase 1-3 weekly rebalance freshness alert

The swing pivot architecture moved Phase 1-3 from daily 22:00 to
weekly Sunday 22:00 cron. If the Sunday cron silent-fails (e.g.,
_exclude_earnings thread hang per §8.2.3), the entire following week
operates on stale sector context.

New script: scripts/check_phase13_freshness.py
- Sunday 23:00 cron (1h time-window after the rebalance)
- Telegram WARNING if state/phase13_ctx.json.gz mtime > 1h
- Telegram alert if file missing entirely

Tests: 3 (missing, stale, fresh).

Refs: docs/master-reference/04-risks-and-open-questions.md §8.2.3
```

## 6. Kapcsolódó

- `04-risks` §8.2.3
- `scripts/crontab.md` (entry hozzáadása + dokumentáció)
- `scripts/check_phase13_freshness.py` (új fájl)
