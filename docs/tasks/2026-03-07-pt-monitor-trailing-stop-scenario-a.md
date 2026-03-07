Status: DONE
Updated: 2026-03-07
Note: Implementálva — 10 teszt, 926 passing

# Task: pt_monitor.py — Trailing Stop Szcenárió A + pt_submit.py state init

**Dátum:** 2026-03-07
**Prioritás:** 🟡 BC17 SCOPE
**Érintett fájlok:**
- `scripts/paper_trading/submit_orders.py` — state fájl írás (módosítás)
- `scripts/paper_trading/pt_monitor.py` (ÚJ)
- crontab — 1 új entry

**Előfeltétel:** `2026-03-05-eod-report-moc-orderref-fix.md` implementálva kell legyen
**Design doc:** `docs/planning/trailing-stop-design.md`

---

## Motiváció

**LION (2026-03-05):** Entry ~$9.50, TP1 $10.00 teljesült (177 db). Maradék 360 db
nuke-olva $9.99-n márc 6-án. MOC lett volna $10.67 → ~$243 elveszett potenciál.

A jelenlegi bracket statikus: TP1 fill után a Bracket B eredeti SL-je ($8.90) él
tovább — az ár visszajöhet az entry alá és a teljes napközbeni nyereség elvész.

---

## Rész 1: `pt_submit.py` módosítás — monitor state fájl inicializálás

A bracket submission után írja a monitor state fájlt. Ha a `pt_submit.py` nem
futott (circuit breaker, kapcsolat hiba), a state fájl nem jön létre → a monitor
tudja, hogy nincs mit figyelni.

### Módosítás helye

`scripts/paper_trading/submit_orders.py` — a Telegram notification blokk UTÁN,
a `disconnect(ib)` ELŐTT:

```python
    # --- Monitor state initialization ---
    if submitted > 0:
        monitor_state = {}
        for t in [tk for tk in tickers if tk['symbol'] in submitted_tickers]:
            monitor_state[t['symbol']] = {
                'entry_price': t['limit_price'],
                'sl_distance': round(t['limit_price'] - t['stop_loss'], 4),
                'tp1_price': t['take_profit_1'],
                'tp2_price': t['take_profit_2'],
                'total_qty': t['total_qty'],
                'qty_b': t['qty_tp2'],
                'tp1_filled': False,
                'trail_active': False,
                'trail_scope': None,
                'trail_sl_current': None,
                'trail_high': None,
            }
        state_path = f'{LOG_DIR}/monitor_state_{today_str}.json'
        with open(state_path, 'w') as f:
            json.dump(monitor_state, f, indent=2)
        logger.info(f'Monitor state written: {state_path} ({len(monitor_state)} tickers)')
```

**State fájl helye:** `scripts/paper_trading/logs/monitor_state_YYYY-MM-DD.json`

**Példa kimenet (LION napján):**
```json
{
  "LION": {
    "entry_price": 9.5,
    "sl_distance": 0.6,
    "tp1_price": 10.0,
    "tp2_price": 11.5,
    "total_qty": 537,
    "qty_b": 360,
    "tp1_filled": false,
    "trail_active": false,
    "trail_scope": null,
    "trail_sl_current": null,
    "trail_high": null
  }
}
```

---

## Rész 2: `pt_monitor.py` — Szcenárió A implementáció

### Szcenárió A logika

```
TP1 fill detektálva → Bracket B eredeti SL cancelálása
                    → TP2 limit order MEGMARAD (felső korlát)
                    → trail_sl = max(entry_price, current_price - sl_distance)
                    → trail követ felfelé 5 percenként
                    → ha current_price <= trail_sl → SELL qty_b MKT
```

### Crontab

```
*/5 9-19 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/pt_monitor.py >> logs/pt_monitor.log 2>&1
```

Utolsó futás: **19:55 UTC (20:55 CET)** — bőven a `pt_close.py` 21:40 UTC előtt.

### Implementáció

```python
#!/usr/bin/env python3
"""IFDS Paper Trading — Trailing Stop Monitor (Szcenárió A).

Runs every 5 minutes (09:00-19:55 UTC / 10:00-20:55 CET).
Detects TP1 fills and activates trailing stop on Bracket B.

Szcenárió A: TP1 fill → trail Bracket B (qty_b)
  - Cancel Bracket B SL order
  - Keep TP2 limit order (upper cap)
  - Trail distance = entry_price - original_sl_price
  - Breakeven protection: trail_sl >= entry_price on activation
  - Telegram on activation and SL hit

State file: scripts/paper_trading/logs/monitor_state_YYYY-MM-DD.json
  (written by pt_submit.py after bracket submission)

Usage:
    python scripts/paper_trading/pt_monitor.py
"""
import json
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
logger = logging.getLogger('pt_monitor')

STATE_DIR = 'scripts/paper_trading/logs'


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


def load_state(today_str: str) -> dict:
    path = f'{STATE_DIR}/monitor_state_{today_str}.json'
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def save_state(today_str: str, state: dict) -> None:
    path = f'{STATE_DIR}/monitor_state_{today_str}.json'
    with open(path, 'w') as f:
        json.dump(state, f, indent=2)


def tp1_was_filled(ib, sym: str) -> bool:
    """Check if Bracket A TP order was filled today via executions."""
    from ib_insync import ExecutionFilter
    today = date.today().strftime('%Y%m%d')
    fills = ib.reqExecutions(ExecutionFilter(time=f'{today} 00:00:00'))
    for fill in fills:
        if fill.execution.orderRef == f'IFDS_{sym}_A_TP':
            return True
    return False


def get_last_price(ib, sym: str) -> float | None:
    """Get last traded price via snapshot market data."""
    from ib_insync import Stock
    contract = Stock(sym, 'SMART', 'USD')
    details = ib.reqContractDetails(contract)
    if not details:
        return None
    ticker = ib.reqMktData(details[0].contract, '', True, False)
    ib.sleep(2)
    price = ticker.last or ticker.close
    ib.cancelMktData(details[0].contract)
    return price if price and price > 0 else None


def cancel_bracket_b_sl(ib, sym: str) -> bool:
    """Cancel Bracket B SL order. Returns True if found and cancelled."""
    open_orders = ib.openOrders()
    for order in open_orders:
        if getattr(order, 'orderRef', '') == f'IFDS_{sym}_B_SL':
            ib.cancelOrder(order)
            ib.sleep(1)
            logger.info(f'{sym}: Bracket B SL cancelled (orderId={order.orderId})')
            return True
    logger.warning(f'{sym}: Bracket B SL order not found for cancellation')
    return False


def main() -> None:
    from lib.connection import connect, disconnect

    today_str = date.today().strftime('%Y-%m-%d')
    state = load_state(today_str)

    if not state:
        logger.info('No monitor state file found — nothing to monitor.')
        return

    active_tickers = [sym for sym, s in state.items() if not s.get('tp1_filled') or s.get('trail_active')]
    if not active_tickers:
        logger.info('All positions resolved — monitor idle.')
        return

    logger.info(f'Monitoring {len(active_tickers)} tickers: {active_tickers}')

    ib = connect(client_id=15)  # Dedicated client ID for pt_monitor
    ib.sleep(3)

    state_changed = False

    for sym in active_tickers:
        s = state[sym]

        # --- Szcenárió A: TP1 fill detektálás ---
        if not s['tp1_filled']:
            if tp1_was_filled(ib, sym):
                s['tp1_filled'] = True
                state_changed = True
                logger.info(f'{sym}: TP1 fill detected')

                # Get current price for trail initialization
                current_price = get_last_price(ib, sym)
                if current_price is None:
                    logger.warning(f'{sym}: Cannot get price for trail init — skipping')
                    continue

                # Cancel Bracket B SL, keep TP2 limit
                cancel_bracket_b_sl(ib, sym)

                # Breakeven protection: trail_sl >= entry_price
                initial_sl = max(
                    s['entry_price'],
                    current_price - s['sl_distance']
                )
                s['trail_active'] = True
                s['trail_scope'] = 'bracket_b'
                s['trail_sl_current'] = round(initial_sl, 4)
                s['trail_high'] = round(current_price, 4)

                msg = (f'🎯 {sym}: Trail aktív (Szcenárió A)\n'
                       f'TP1 fill detektálva\n'
                       f'Trail SL: ${initial_sl:.2f} (entry: ${s["entry_price"]:.2f})\n'
                       f'TP2 limit megmarad: ${s["tp2_price"]:.2f}')
                logger.info(msg)
                send_telegram(msg)

        # --- Trail SL frissítés + ütés detektálás ---
        if s.get('trail_active'):
            current_price = get_last_price(ib, sym)
            if current_price is None:
                logger.warning(f'{sym}: Cannot get price for trail update')
                continue

            # Trail SL felfelé követés
            new_sl = round(current_price - s['sl_distance'], 4)
            if new_sl > s['trail_sl_current']:
                s['trail_sl_current'] = new_sl
                s['trail_high'] = round(max(current_price, s['trail_high']), 4)
                state_changed = True
                logger.info(f'{sym}: Trail SL updated → ${new_sl:.2f} (price: ${current_price:.2f})')

            # Trail SL ütés
            if current_price <= s['trail_sl_current']:
                qty = s['qty_b']
                logger.warning(f'{sym}: Trail SL hit @ ${current_price:.2f} — SELL {qty} shares')

                from ib_insync import Stock, MarketOrder
                contract = Stock(sym, 'SMART', 'USD')
                ib.qualifyContracts(contract)
                order = MarketOrder('SELL', qty)
                order.tif = 'DAY'
                order.orderRef = f'IFDS_{sym}_B_TRAIL'
                order.account = ib.managedAccounts()[0]
                ib.placeOrder(contract, order)

                s['trail_active'] = False
                state_changed = True

                msg = (f'🛑 {sym}: Trail SL ütve\n'
                       f'Ár: ${current_price:.2f} ≤ SL: ${s["trail_sl_current"]:.2f}\n'
                       f'SELL {qty} shares (Bracket B)\n'
                       f'orderRef: IFDS_{sym}_B_TRAIL')
                logger.warning(msg)
                send_telegram(msg)

    if state_changed:
        save_state(today_str, state)

    disconnect(ib)


if __name__ == '__main__':
    main()
```

---

## Szcenárió B — BC18 scope

A Szcenárió B (19:00 CET időalapú aktiválás nyereséges pozícióra, 0.5% küszöb)
**nem része ennek a tasknak** — külön task lesz BC18 előtt.
Design: `docs/planning/trailing-stop-design.md`

---

## Tesztelés

### `tests/paper_trading/test_pt_monitor.py`

**submit_orders state init:**
- `test_state_written_after_submission` — submission után a state fájl létrejön
- `test_state_not_written_if_none_submitted` — ha 0 ticker tölt, nincs state fájl
- `test_state_fields_correct` — sl_distance = limit_price - stop_loss helyesen

**pt_monitor Szcenárió A:**
- `test_scenario_a_trail_activation` — TP1 fill detektálva → trail_active=True, SL cancel, Telegram
- `test_scenario_a_breakeven_protection` — entry $9.50, TP1 fill @ $9.55 → trail_sl = $9.50 (nem $8.95)
- `test_scenario_a_trail_update` — ár emelkedik → trail_sl felfelé követi
- `test_scenario_a_trail_sl_not_lowered` — ár csökken → trail_sl nem megy le
- `test_scenario_a_trail_sl_hit` — current_price <= trail_sl → SELL order, IFDS_{sym}_B_TRAIL orderRef
- `test_scenario_a_tp2_not_cancelled` — TP2 limit order megmarad
- `test_no_state_file_exits_cleanly` — nincs state fájl → kilép, nincs hiba
- `test_tp1_not_filled_no_trail` — TP1 még él → trail nem aktív

---

## Git commit

```
feat(paper_trading): trailing stop monitor Szcenárió A (pt_monitor.py)

pt_submit.py: write monitor_state_YYYY-MM-DD.json after bracket
submission with entry_price, sl_distance, tp1/tp2 prices, qty_b.

pt_monitor.py: runs every 5 min (09:00-19:55 UTC). Detects TP1
fills via reqExecutions(IFDS_{sym}_A_TP). On detection:
- Cancels Bracket B SL order (IFDS_{sym}_B_SL)
- Keeps TP2 limit order as upper cap
- Activates trail with sl_distance = entry - original_sl
- Breakeven protection: trail_sl >= entry_price on activation
- Telegram alerts on activation and SL hit
- orderRef: IFDS_{sym}_B_TRAIL (visible to eod_report.py)

Motivation: LION 2026-03-05, TP1 $10.00 filled, MOC $10.67
vs nuke $9.99 — ~$243 lost potential on 360 shares.

Client ID: 15 (dedicated). Crontab: */5 9-19 * * 1-5
Szcenárió B (time-based, 19:00 CET): BC18 scope.
Design: docs/planning/trailing-stop-design.md
```
