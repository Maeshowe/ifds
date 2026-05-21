Status: DONE
Updated: 2026-04-06
Note: P0 — phantom tickerek és dupla futások

# Fix: monitor_state dátum validáció + monitor_positions idempotency

## Probléma

### 1. Phantom tickerek a monitor-ban (LION, SDRL)
A pt_monitor.py régi monitor_state fájlokat olvas be és phantom event-eket generál. Ma (04-06) LION trail és SDRL loss_exit event-ek jelentek meg a pt_events-ben, holott ezek NEM mai tickerek. A monitor a korábbi napok state fájljait is betölti.

### 2. monitor_positions 5× fut egymás után
A monitor_positions.py 14:00-kor és 22:00-kor is 5 párhuzamos futást mutat. Valószínűleg a crontab-on több entry van rá, vagy a log modernizáció során több cron entry keletkezett.

### 3. CRGY/AAPL phantom pozíciók
A monitor_positions CRGY 672sh és AAPL 100sh pozíciókat detektált, de az IBKR-ben ezek nem léteznek. Valószínűleg a 14:00-ás teszt futás mellékhatása volt.

## Megoldás

### 1. pt_monitor.py — monitor_state dátum validáció

A monitor CSAK a mai dátumú state fájlt fogadja el:

```python
# pt_monitor.py — state betöltés
today_str = date.today().strftime('%Y-%m-%d')
state_path = f'{LOG_DIR}/monitor_state_{today_str}.json'

if not os.path.exists(state_path):
    logger.debug("No monitor state file for today — nothing to monitor.")
    sys.exit(0)

# Extra guard: ellenőrizd, hogy a fájl ma készült
import os
file_mtime = datetime.fromtimestamp(os.path.getmtime(state_path))
if file_mtime.date() != date.today():
    logger.warning(f"Monitor state file is stale (mtime: {file_mtime.date()}). Skipping.")
    sys.exit(0)
```

**NE** keress más dátumú state fájlokat fallback-ként.

### 2. monitor_positions — idempotency guard

A monitor_positions egyszer fusson naponta per cron trigger. Ha mégis többször fut, ne logoljon dupla event-eket:

```python
# monitor_positions.py — idempotency
if evt:
    # Check if we already logged for this trigger time
    trigger_key = datetime.now().strftime('%Y-%m-%d_%H')  # hour-level dedup
    # ... vagy egyszerűbben: a script egyszer fusson, a crontab-ot javítsd
```

**A valódi megoldás: crontab javítás a Mac Mini-n.** Ellenőrizd, hogy nincs-e duplikált entry a monitor_positions-re.

### 3. monitor_positions — IBKR pozíció filter

Adj hozzá egy szűrőt ami kiszűri a nem-STK és a .CVR pozíciókat:

```python
positions = [
    p for p in ib.positions()
    if p.position != 0
    and p.contract.secType == 'STK'
    and '.CVR' not in p.contract.symbol
]
```

Ez már a close_positions.py-ben megvan — a monitor_positions.py-ben is kellene.

## Tesztelés

- pt_monitor.py nem tölt be tegnapi state fájlt
- monitor_positions nem detektál phantom pozíciókat (secType != 'STK')
- Ha nincs mai state fájl, a monitor csendben kilép (DEBUG log, nem WARNING)
- `pytest` all green

## Commit

```
fix(monitor): add date validation to monitor_state and filter phantom positions

pt_monitor.py now only loads today's monitor_state file, preventing
phantom trail/loss_exit events from stale state files (LION/SDRL).
monitor_positions.py filters to secType='STK' only, preventing
phantom detection of non-stock positions.
```
