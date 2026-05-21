Status: DONE
Updated: 2026-03-07
Note: Implementálva — 5 teszt, 916 passing

# Task: monitor_positions.py — Leftover position warning (10:10 CET)

**Dátum:** 2026-03-07
**Prioritás:** 🟡 BC17 ELŐTT
**Érintett fájlok:**
- `scripts/paper_trading/monitor_positions.py` (ÚJ)
- crontab — 1 új entry

---

## Probléma

Ha egy bracket order a `pt_close.py` futása (21:40 UTC) UTÁN tölt, a pozíció
nyitva marad másnap reggelig. A `pt_submit.py` `get_existing_symbols()` véd az
újabb order küldéstől, de nincs aktív figyelmeztetés — csak az EOD logból derül ki.

**Konkrét eset:** CRGY 2026-03-06, fill 21:48 UTC, pt_close 21:40 UTC → 672 db
nyitva maradt overnight, manuális nuke szükséges.

---

## Fix

Új script: `scripts/paper_trading/monitor_positions.py`
Crontab: **09:10 UTC (10:10 CET)** — pipeline lefutott (~10:05), IBKR szinkronizált.

### Logika

1. IBKR csatlakozás (clientId=14 — dedikált)
2. `ib.positions()` lekérése
3. Mai execution plan CSV-ből tickerek beolvasása (`output/execution_plan_run_YYYYMMDD_*.csv`)
4. Ha pozíció nincs a mai planben → Telegram WARNING + log
5. Ha minden rendben → csak INFO log, nincs Telegram
6. Disconnect

### Implementáció

```python
#!/usr/bin/env python3
"""IFDS Paper Trading — Leftover position monitor.

Runs at 10:10 CET (09:10 UTC) after the daily pipeline.
Detects open positions not in today's execution plan and sends Telegram alert.

Usage:
    python scripts/paper_trading/monitor_positions.py
"""
import csv
import glob
import logging
import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('monitor_positions')

EXECUTION_PLAN_DIR = 'output'


def send_telegram(message: str) -> None:
    import requests
    token = os.getenv('IFDS_TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('IFDS_TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        return
    try:
        requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f'Telegram send failed: {e}')


def get_todays_plan_symbols() -> set:
    """Load ticker symbols from today's execution plan CSV."""
    today = date.today().strftime('%Y%m%d')
    pattern = f'{EXECUTION_PLAN_DIR}/execution_plan_run_{today}_*.csv'
    files = sorted(glob.glob(pattern))
    if not files:
        logger.warning('No execution plan CSV found for today')
        return set()
    symbols = set()
    with open(files[-1], newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbols.add(row['instrument_id'])
    return symbols


def main() -> None:
    from lib.connection import connect, disconnect

    today_str = date.today().strftime('%Y-%m-%d')
    logger.info(f'Leftover position monitor — {today_str}')

    plan_symbols = get_todays_plan_symbols()
    logger.info(f"Today's plan: {sorted(plan_symbols) if plan_symbols else 'none found'}")

    ib = connect(client_id=14)
    ib.sleep(3)

    positions = [
        p for p in ib.positions()
        if p.position != 0
        and '.CVR' not in p.contract.symbol
        and p.contract.secType == 'STK'
    ]

    leftover = [
        p for p in positions
        if p.contract.symbol not in plan_symbols
    ]

    if leftover:
        lines = [f'⚠️ LEFTOVER POSITIONS — {today_str}']
        for p in leftover:
            lines.append(f'  {p.contract.symbol}: {p.position:+.0f} shares (NOT in today plan)')
        lines.append('Action: nuke.py before market open or manual close in IBKR.')
        msg = '\n'.join(lines)
        logger.warning(msg)
        send_telegram(msg)
    else:
        logger.info('No leftover positions — all clear.')

    disconnect(ib)


if __name__ == '__main__':
    main()
```

---

## Crontab entry

```
10 9 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/monitor_positions.py >> logs/pt_monitor_positions.log 2>&1
```

**Fontos:** 2026-03-29-től (CEST, UTC+2) ez `8 8 * * 1-5`-re változik.

---

## Tesztelés (`tests/paper_trading/test_monitor_positions.py`)

- `test_no_leftover` — minden pozíció a mai planben → nincs Telegram, INFO log
- `test_leftover_detected` — CRGY nyitva, nincs a planben → Telegram warning tartalmazza a tickert és qty-t
- `test_no_plan_found` — nincs mai CSV → WARNING log, nem crashel, nincs Telegram
- `test_cvr_skipped` — AVDL.CVR pozíció → nem jelenik meg leftoverként
- `test_zero_position_skipped` — position=0 → nem jelenik meg

---

## Git commit

```
feat(paper_trading): add monitor_positions.py for leftover position detection

New script runs at 09:10 UTC (10:10 CET) after daily pipeline.
Detects open IBKR positions not in today's execution plan CSV,
sends Telegram WARNING with ticker + qty details.

Motivation: CRGY 2026-03-06 filled 21:48 UTC after pt_close.py
ran at 21:40 UTC, leaving 672 shares open overnight undetected.

Client ID: 14 (dedicated). Log: logs/pt_monitor_positions.log
Crontab: 10 9 * * 1-5
```
