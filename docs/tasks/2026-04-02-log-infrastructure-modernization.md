Status: WIP
Updated: 2026-04-03
Note: KIEMELT PRIORITÁS — az üzleti döntések a logok elemzésére épülnek

# Log Infrastruktúra Modernizáció — Teljes terv

## Kontextus

A jelenlegi log infrastruktúra akadályozza az üzleti elemzést:
- pt_monitor.log 89 MB, egyetlen fájl feb 17 óta, 95% zaj
- 7 PT script 7 külön log fájlba ír, nincs közös formátum
- Nincs dátum a PT log fájlnevekben és a log sorok timestamp-jében
- Az üzleti event-ek (fill, exit, P&L) elszórva 5-7 fájlban
- A napi review 5-7 fájl cross-reference-t igényel
- A CF tripla fill (04-02) félreértelmezése ebből a szétszórtságból fakadt

## Fázisok — mind AZONNAL implementálandó

---

### Fázis 1: PT logok napi rotáció + dátum formátum (~1h CC)

**Minden PT script** log fájlja legyen napi rotációjú:

RÉGI: `logs/pt_monitor.log` (append-only, határtalan)
ÚJ: `logs/pt_monitor_YYYY-MM-DD.log` (napi fájl)

**Érintett scriptek:**
- `scripts/paper_trading/submit_orders.py` → `pt_submit_YYYY-MM-DD.log`
- `scripts/paper_trading/pt_avwap.py` → `pt_avwap_YYYY-MM-DD.log`
- `scripts/paper_trading/pt_monitor.py` → `pt_monitor_YYYY-MM-DD.log`
- `scripts/paper_trading/monitor_positions.py` → `pt_monitor_positions_YYYY-MM-DD.log`
- `scripts/paper_trading/close_positions.py` → `pt_close_YYYY-MM-DD.log`
- `scripts/paper_trading/eod_report.py` → `pt_eod_YYYY-MM-DD.log`
- `scripts/paper_trading/pt_gateway.py` (ha van) → `pt_gateway_YYYY-MM-DD.log`

**Közös helper:**
```python
# scripts/paper_trading/lib/log_setup.py
import logging
from datetime import date

def setup_pt_logger(script_name: str, log_dir: str = "logs") -> logging.Logger:
    """Setup daily-rotated logger for paper trading scripts."""
    today = date.today().strftime('%Y-%m-%d')
    log_file = f"{log_dir}/pt_{script_name}_{today}.log"
    
    logger = logging.getLogger(script_name)
    logger.setLevel(logging.INFO)
    
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(handler)
    
    # Also keep console output
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    ))
    logger.addHandler(console)
    
    return logger
```

**Timestamp formátum:**
- RÉGI: `10:05:01 [INFO] No monitor state file found`
- ÚJ: `2026-04-02 10:05:01 [INFO] No monitor state file found`

**Migráció:** a régi fájlokat (pt_monitor.log stb.) NE töröld — a meglévő logok maradnak referenciaként. Az új futások az új fájlneveket használják.

**A review prompt (v4) és a sync_from_mini.sh is frissítendő** az új fájlnevekhez.

---

### Fázis 2: pt_monitor.log zaj csökkentése (~30min CC)

A pt_monitor.py és pt_avwap.py logolási szintjei:

**DEBUG-ra csökkenteni (nem jelenik meg INFO szinten):**
- `"No monitor state file found — nothing to monitor."`
- `"Outside AVWAP window (09:45-11:30 ET). Exiting."`
- `"No tickers need AVWAP monitoring."`
- Scenario B `"not activated"` normál logolás (csak az első alkalommal INFO, utána DEBUG)

**INFO-n marad (üzletileg fontos):**
- Trail aktiválás (Scenario A/B)
- Loss exit trigger
- SL módosítás
- Trail SL frissítés
- TP1 fill detektálás
- Minden ERROR/WARNING

Ez a pt_monitor.log napi méretét ~89 MB / 34 nap ≈ 2.6 MB/nap → becslés ~50-100 KB/nap-ra csökkenti.

---

### Fázis 3: Napi pt_events JSONL — közös üzleti event log (~3h CC)

Új fájl: `logs/pt_events_YYYY-MM-DD.jsonl`

Minden PT script a saját logja MELLETT egy közös JSONL-be is írja az üzletileg fontos event-eket. Ez az **egyetlen igazságforrás** a napi kereskedési tevékenységhez.

**Event típusok:**

```python
# scripts/paper_trading/lib/event_logger.py
import json
from datetime import datetime, timezone

class PTEventLogger:
    """Unified business event logger for paper trading."""
    
    def __init__(self, log_dir: str = "logs"):
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        self.path = f"{log_dir}/pt_events_{today}.jsonl"
    
    def log(self, script: str, event: str, **data):
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "script": script,
            "event": event,
            **data,
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
```

**Minden scriptbe integrálni:**

| Script | Event-ek |
|--------|----------|
| submit_orders.py | `order_submitted`, `order_filled`, `witching_skip`, `circuit_breaker`, `existing_skip` |
| pt_avwap.py | `avwap_fill`, `avwap_bracket_rebuild`, `avwap_sl_cap`, `avwap_tp1_recalc` |
| pt_monitor.py | `trail_activated_a`, `trail_activated_b`, `loss_exit`, `trail_sl_update`, `trail_hit`, `tp1_detected` |
| close_positions.py | `moc_submitted`, `qty_adjusted`, `position_skipped`, `leftover_detected` |
| eod_report.py | `trade_closed`, `daily_pnl`, `cumulative_update`, `leftover_warning` |
| monitor_positions.py | `leftover_found`, `no_leftover` |
| nuke.py | `nuke_executed` |

**Példa napi JSONL (CF 04-02 teljes életciklusa):**
```jsonl
{"ts":"2026-04-02T13:35:08Z","script":"submit","event":"order_submitted","ticker":"CF","qty":34,"limit":127.98,"sl":117.27,"tp1":145.00,"tp2":149.39,"bracket_a_qty":11,"bracket_b_qty":23}
{"ts":"2026-04-02T13:50:22Z","script":"avwap","event":"avwap_fill","ticker":"CF","qty":34,"fill_price":134.46,"plan_price":127.98,"slippage_pct":5.07}
{"ts":"2026-04-02T13:50:23Z","script":"avwap","event":"avwap_bracket_rebuild","ticker":"CF","new_sl":131.77,"new_tp1":151.48,"new_tp2":155.87,"tp1_source":"call_wall_shifted","vix":24.5}
{"ts":"2026-04-02T14:08:15Z","script":"avwap","event":"order_filled","ticker":"CF","orderRef":"IFDS_CF_AVWAP_A","qty":11,"price":134.46}
{"ts":"2026-04-02T14:08:15Z","script":"avwap","event":"order_filled","ticker":"CF","orderRef":"IFDS_CF_AVWAP_B","qty":23,"price":134.46}
{"ts":"2026-04-02T14:36:30Z","script":"avwap","event":"bracket_sl_hit","ticker":"CF","orderRef":"IFDS_CF_AVWAP_A_SL","qty":11,"exit_price":131.16,"entry_price":134.46,"pnl":-36.30}
{"ts":"2026-04-02T14:36:30Z","script":"avwap","event":"bracket_sl_hit","ticker":"CF","orderRef":"IFDS_CF_AVWAP_B_SL","qty":23,"exit_price":131.16,"entry_price":134.46,"pnl":-75.90}
{"ts":"2026-04-02T17:00:21Z","script":"monitor","event":"loss_exit","ticker":"CF","qty":34,"exit_price":130.44,"entry_price":134.46,"pnl":-136.68,"loss_pct":-2.99}
{"ts":"2026-04-02T22:05:03Z","script":"eod","event":"daily_pnl","pnl":-292.61,"cumulative":-1405.77,"cum_pct":-1.41,"day":34,"leftover":["EVRG:235"]}
```

Egyetlen fájl → a CF teljes napi története 8 sor. A napi review egyetlen `cat` parancs.

---

### Fázis 4: SQLite import + query (~2h CC)

Napi cron job: `pt_events_YYYY-MM-DD.jsonl` → SQLite.

```python
# scripts/tools/events_to_sqlite.py
import json
import sqlite3
from pathlib import Path

DB_PATH = "state/pt_events.db"
EVENTS_DIR = "logs"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            date TEXT NOT NULL,
            script TEXT NOT NULL,
            event TEXT NOT NULL,
            ticker TEXT,
            qty INTEGER,
            price REAL,
            pnl REAL,
            data TEXT  -- full JSON for complex fields
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON events(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON events(ticker)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_event ON events(event)")
    return conn

def import_jsonl(conn, jsonl_path: str):
    date_str = Path(jsonl_path).stem.replace("pt_events_", "")
    # Skip if already imported
    existing = conn.execute(
        "SELECT COUNT(*) FROM events WHERE date=?", (date_str,)
    ).fetchone()[0]
    if existing > 0:
        return 0
    
    count = 0
    with open(jsonl_path) as f:
        for line in f:
            entry = json.loads(line)
            conn.execute(
                "INSERT INTO events (ts, date, script, event, ticker, qty, price, pnl, data) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry["ts"], date_str, entry["script"], entry["event"],
                    entry.get("ticker"), entry.get("qty"),
                    entry.get("fill_price") or entry.get("exit_price") or entry.get("price"),
                    entry.get("pnl"),
                    json.dumps(entry),
                )
            )
            count += 1
    conn.commit()
    return count
```

**Crontab:** `45 22 * * 1-5` (22:45 CET, EOD report után)

**Query példák a review-hoz:**
```sql
-- Leftoverek az utolsó 30 napban
SELECT date, data FROM events WHERE event='leftover_warning' ORDER BY date DESC;

-- Ticker-szintű loss_exit gyakoriság
SELECT ticker, COUNT(*) as cnt, SUM(pnl) as total_loss
FROM events WHERE event='loss_exit' GROUP BY ticker ORDER BY total_loss;

-- AVWAP slippage átlag szektoronként
SELECT json_extract(data, '$.sector') as sector, 
       AVG(json_extract(data, '$.slippage_pct')) as avg_slip
FROM events WHERE event='avwap_fill' GROUP BY sector;

-- Skip day shadow napok P&L-je
SELECT e.date, p.pnl
FROM events e JOIN events p ON e.date = p.date
WHERE e.event='skip_day_shadow' AND e.data LIKE '%"would_skip": true%'
AND p.event='daily_pnl';
```

---

### Fázis 5: MCP Log Query Endpoint (~5h CC, BC23C scope-ba integrálva)

Egy egyszerű MCP endpoint ami a SQLite-ból query-zik:

```
POST /logs/query
{
  "event": "loss_exit",
  "ticker": "CF",
  "date_from": "2026-03-25",
  "date_to": "2026-04-02"
}
```

Ez a review chatből és az Active chatből is elérhető lesz — a Filesystem tool helyett MCP-n keresztül. A review prompt v5 majd erre a toolra épül.

**Fontos:** ez BC23C scope — nem önálló MCP server, hanem az IFDS pipeline introspekció MCP részeként. Az MCP szerveren 3 fő endpoint:
1. `/pipeline/status` — jelenlegi STATE.md tartalom + live state
2. `/pipeline/positions` — nyitott pozíciók, trail state
3. `/logs/query` — pt_events SQLite query

---

## Implementációs sorrend

1. **Fázis 1** — log_setup.py helper, minden script átalakítás, sync_from_mini.sh frissítés
2. **Fázis 2** — pt_monitor.py + pt_avwap.py log szint csökkentés
3. **Fázis 3** — event_logger.py helper, minden script integrálás (ez a legnagyobb)
4. **Fázis 4** — events_to_sqlite.py + crontab
5. **Fázis 5** — MCP endpoint (BC23C scope-ba tervezve, implementáláskor a prompt is frissül)

**Fázis 1-4 összesen: ~6.5h CC effort, mind azonnal implementálandó.**
**Fázis 5: BC23C scope, de a design most legyen kész.**

## Tesztelés

- Fázis 1: a régi logok NE törlődjenek, az új fájlok a helyes dátummal jöjjenek létre
- Fázis 2: `grep -c "No monitor state" pt_monitor_YYYY-MM-DD.log` → 0 (DEBUG-on nem jelenik meg)
- Fázis 3: minden PT script futtatása után a pt_events JSONL tartalmazza az event-eket
- Fázis 4: `sqlite3 state/pt_events.db "SELECT COUNT(*) FROM events"` → helyes szám
- Fázis 5: MCP endpoint válaszol a query-re (BC23C tesztjei)

## Commit-ok

```
feat(logging): add daily log rotation for all PT scripts
refactor(logging): reduce pt_monitor noise — DEBUG level for non-events
feat(logging): add unified pt_events JSONL business event log
feat(logging): add SQLite import for pt_events with query support
feat(mcp): add /logs/query endpoint for pt_events SQLite (BC23C)
```
