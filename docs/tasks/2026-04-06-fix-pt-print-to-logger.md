Status: DONE
Updated: 2026-04-06
Note: P1 — close_positions.py és más PT scriptek print() vs logger inkonzisztencia

# Fix: PT scriptek print() → logger migráció

## Probléma

A close_positions.py (és valószínűleg más PT scriptek) a fontos üzleti outputot **print()**-tel írja, nem a logger-rel. A log modernizáció (napi rotált FileHandler) után a print() a cron stdout-ba megy, a logger a napi fájlba — de ha a crontab redirect is megváltozott, a print() output elveszhet.

### close_positions.py konkrét probléma (04-06)
- `pt_close_2026-04-06.log` **üres** — mert a MOC summary mind `print()`
- `pt_events_2026-04-06.jsonl` rendben — az event_logger működik
- A régi `pt_close.log` utolsó bejegyzése 04-02 — a crontab redirect megváltozott

### Érintett print() sorok (close_positions.py)
```python
print(f"\nMOC Close — {today_str}")           # → logger.info()
print(f"  Cancelled {len(open_orders)}...")    # → logger.info()
print("  No open orders to cancel")           # → logger.info()
print("No positions to close")                # → logger.info()
print(f"  {sym}: SKIP — already closed...")    # → logger.info() (DUPLIKÁLT — logger.info is van!)
print(f"  {sym}: qty adjusted...")             # → logger.info()
print(f"  {sym}: MOC {action} {qty} shares")  # → logger.info()
print(f"MOC submitted: {len(moc_submitted)}") # → logger.info()
```

## Megoldás

### 1. Minden PT scriptben: print() → logger cserék

A fontos üzleti output legyen `logger.info()`, nem `print()`. A logger a napi fájlba ÉS a konzolra ír (a `log_setup.py` mindkettőt beállítja), tehát a cron stdout is megkapja.

**Érintett scriptek (ellenőrizni):**
- `close_positions.py` — biztosan érintett, lásd fent
- `submit_orders.py` — valószínűleg sok print()
- `eod_report.py` — valószínűleg sok print()
- `pt_avwap.py` — ellenőrizni
- `pt_monitor.py` — ellenőrizni
- `monitor_positions.py` — ellenőrizni

### 2. Szabály

Minden PT scriptben:
- `print()` — CSAK a "formatted report" blokkok (EOD Report, MOC Summary) — ezeket is logger.info()-ra cserélni
- `logger.info()` — minden üzleti output
- `logger.debug()` — zaj (pl. "no state found", "outside window")
- `logger.warning()` — leftover, anomália
- `logger.error()` — hiba, early close miss

### 3. A crontab stdout redirect

A crontab entry-k NE a régi monolitikus fájlba redirect-eljenek. A `log_setup.py` console handler-e gondoskodik a stdout-ról, a FileHandler a napi fájlról. A crontab egyszerűen legyen:

```crontab
# RÉGI: >> logs/pt_close.log 2>&1
# ÚJ: >> /dev/null 2>&1  (vagy hagyd el — a logger mindent kezel)
40 21 * * 1-5 cd ~/SSH-Services/ifds && python3 scripts/paper_trading/close_positions.py 2>&1
```

## Tesztelés

- close_positions.py futtatása után `pt_close_YYYY-MM-DD.log` NEM üres
- A MOC summary benne van a napi logban
- A régi `pt_close.log` nem kap új bejegyzéseket
- Minden PT script napi logja tartalmaz adatot futtatás után
- `pytest` all green

## Commit

```
fix(logging): migrate PT scripts print() to logger for daily log rotation

close_positions.py and other PT scripts used print() for business
output, which went to cron stdout instead of the daily rotated log
file. Replace all business-relevant print() calls with logger.info()
so that both the daily log file and console output receive the data.
```
