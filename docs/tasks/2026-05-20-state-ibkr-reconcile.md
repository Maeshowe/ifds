# Task: State/IBKR Reconciliation Script

**Status:** DONE
**Priority:** P2
**Created:** 2026-05-19
**Updated:** 2026-05-19 (commit `952c7fe`, 7 új teszt, cron 22:15 Mac Mini-n élesítve, smoke OK)
**Owner:** Claude Code
**Estimated effort:** ~45 min CC + 2-3 unit teszt

**Source**: [`docs/master-reference/04-risks-and-open-questions.md`](../master-reference/04-risks-and-open-questions.md) §8.1.2.

---

## 1. A probléma

A swing system két source-of-truth-tal — `state/swing_positions.json` (mental stop / TP1 / TP2 levels) és IBKR positions (actual holdings) — **csendben divergálni tud**. A 2026-05-18 Day 1 példa:

- 14:34 pre-market submit → 14:42 manuális state reset (state üres, IBKR-ben MASI volt)
- 15:30 NYSE open → mind a 3 ticker (LBRT, MASI, EC) filled
- `state/swing_positions.json` üres → 3 pozíció **"elveszett" a swing system számára**
- 22:00 EOD eval üres state-en futott volna (NULL exit logic) — **csak Tamás-féle A opció rekonstrukció mentette meg**

**Strukturális kockázat**: bármilyen jövőbeli IBKR connection-bug, manuális state reset, vagy `nuke.py` invokáció ugyanezt a divergenciát hozhatja létre.

## 2. Megoldás

Új script `scripts/paper_trading/reconcile_state.py` + crontab entry 22:15 CEST (5 perccel az EOD eval után, mielőtt a 22:30+ Tamás review jön):

```python
#!/usr/bin/env python
"""State/IBKR reconciliation — divergencia detect + Telegram WARNING."""

import json
import os
import sys
from pathlib import Path
import requests
from ib_insync import IB

STATE_PATH = Path("state/swing_positions.json")

def main():
    # 1. Load state
    state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
    state_tickers = set(state.keys())

    # 2. Load IBKR positions
    ib = IB()
    ib.connect("127.0.0.1", 7497, clientId=99, timeout=10)
    ibkr_positions = {p.contract.symbol: p.position for p in ib.positions()}
    ib.disconnect()
    ibkr_tickers = set(ibkr_positions.keys())

    # 3. Compute divergence
    in_state_not_ibkr = state_tickers - ibkr_tickers
    in_ibkr_not_state = ibkr_tickers - state_tickers - {"AVDL.CVR"}  # AVDL.CVR permanent orphan

    if not in_state_not_ibkr and not in_ibkr_not_state:
        # No divergence — silent success
        sys.exit(0)

    # 4. Telegram WARNING — NEM auto-fix, Tamás dönt
    message = f"⚠️ State/IBKR divergence detected at {now_cest():%H:%M}\n\n"
    if in_state_not_ibkr:
        message += f"State has, IBKR doesn't: {sorted(in_state_not_ibkr)}\n"
    if in_ibkr_not_state:
        message += f"IBKR has, state doesn't: {sorted(in_ibkr_not_state)}\n"
    message += "\nTamás: review + decide reconstruction (A) vs nuke (C)."

    send_telegram(message)
    sys.exit(1)

def send_telegram(message: str):
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

**Fontos**: a script **NEM auto-fix**. Csak detect + alert. Tamás dönti el a választ (rekonstrukció A vs nuke C).

## 3. Crontab entry

```
# State/IBKR reconciliation — 22:15 (5 perccel az EOD eval után)
15 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/reconcile_state.py >> logs/cron_reconcile_$(date +\%Y\%m\%d).log 2>&1
```

## 4. Tesztek

```python
def test_reconcile_no_divergence_silent_exit():
    """state==ibkr → sys.exit(0), no Telegram."""

def test_reconcile_state_has_ibkr_doesnt():
    """state: {LBRT, MASI}, ibkr: {LBRT} → Telegram WARNING + exit(1)."""

def test_reconcile_ibkr_has_state_doesnt():
    """state: {LBRT}, ibkr: {LBRT, EC} → Telegram WARNING + exit(1)."""

def test_reconcile_avdl_cvr_orphan_ignored():
    """ibkr: {LBRT, AVDL.CVR}, state: {LBRT} → no divergence (AVDL.CVR excluded)."""

def test_reconcile_ibkr_connection_failure_alerts():
    """Ha IBKR connect fail → Telegram alert + exit(1)."""
```

## 5. Commit message

```
feat(reconciliation): daily state/IBKR divergence detection

Day 1 (2026-05-18) showed structural divergence risk:
14:42 manual state reset → 15:30 IBKR fills → state empty,
IBKR holds 3 positions. Swing system would have evaluated
on EMPTY state at 22:00 EOD (NULL exit logic) without manual
A-option reconstruction.

New script: scripts/paper_trading/reconcile_state.py
- Cron 22:15 (5min after EOD eval)
- Detects: state-has-not-IBKR, IBKR-has-not-state
- AVDL.CVR orphan excluded (permanent §8.3.1)
- Telegram WARNING, NEM auto-fix — Tamás decides

Tests: 5 (no-div, state>ibkr, ibkr>state, AVDL ignored, conn-fail).

Refs: docs/master-reference/04-risks-and-open-questions.md §8.1.2
```

## 6. Kapcsolódó

- `state/swing_positions.json`
- `scripts/paper_trading/reconcile_state.py` (új fájl)
- `scripts/crontab.md` (entry hozzáadás)
- `04-risks` §8.1.2
