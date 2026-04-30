# BC23 Cleanup — 3 Bug Fix

**Status:** OPEN
**Updated:** 2026-04-14
**Priority:** P2 — nem blokkoló, de idegesítő
**Effort:** ~1.5h CC

---

## Bug 1: nuke.py NameError (`_log_path`)

**Probléma:** A `nuke.py` futtatásakor `NameError: name '_log_path' is not defined` (sor 57). Valószínűleg a napi log rotáció bevezetésekor törött el.

**Hatás:** A CRGY és AAPL pozíciókat nem lehet automatikusan zárni. Manuális IBKR Desktop close szükséges.

**Fix:** A `_log_path` változó definiálása a `main()` elején, a többi PT script mintájára:
```python
_log_path = f"logs/pt_nuke_{date.today().isoformat()}.log"
```

**Teszt:** `nuke.py --dry-run` nem dob NameError-t.

**Fájl:** `scripts/paper_trading/nuke.py`

---

## Bug 2: FRED API HALT-olja a Phase 1-3-at

**Probléma:** 2026-04-13 22:00-kor a FRED API timeout (7514ms) → `HALT: Critical API(s) down: fred`. A Phase 1-3 nem futott, a `phase13_ctx.json.gz` nem frissült. Másnap manuális Phase 1-3 futtatás kellett.

**Hatás:** Ha a FRED 22:00-kor lassú/elérhetetlen, a másnapi Phase 4-6 stale ctx-ből dolgozik. A FRED-ből csak a TNX (backup — Polygon is adja) és a yield curve shadow jön.

**Fix:** A FRED-et CRITICAL-ról **OPTIONAL**-ra minősíteni a Phase 0 health check-ben. Ha a FRED nem elérhető:
- TNX fallback: Polygon I:TNX (már implementálva)
- Yield curve: skip (shadow mód, nem hat a sizing-ra)
- A pipeline NE HALT-oljon FRED nélkül

**Implementáció:** `src/ifds/phases/phase0_diagnostics.py` — a FRED health check `is_critical=False` legyen:
```python
# RÉGI:
fred_result = fred.check_health()  # is_critical=True
# ÚJ:
fred_result = fred.check_health()
fred_result.is_critical = False  # FRED is optional — TNX comes from Polygon
```

Vagy a `FREDClient.check_health()` metódusban:
```python
def check_health(self) -> APIHealthResult:
    return self.health_check(self.HEALTH_CHECK_ENDPOINT, is_critical=False)
```

**Teszt:** 
- `test_pipeline_continues_without_fred` — FRED timeout → pipeline nem HALT-ol
- `test_tnx_fallback_polygon` — TNX érték Polygon-ból jön ha FRED nem elérhető

**Fájl:** `src/ifds/data/fred.py` vagy `src/ifds/phases/phase0_diagnostics.py`

---

## Bug 3: LION/SDRL/DELL/DOCN phantom a 22:00 utáni monitor ciklusban

**Probléma:** A `pt_monitor.py` minden 22:00 utáni ciklusban (20:00+ UTC) futtatja a LION/SDRL teljes trail lifecycle-t (tp1_detected → trail_activated → trail_hit → loss_exit), és a DELL/DOCN phantom_filtered-et logol. Az archiválás (monitor_state márc/ápr fájlok áthelyezése) nem oldotta meg — a `grep -l LION` üres, tehát a forrás NEM a state fájlok.

**Hatás:** Log noise — minden nap 20+ phantom event. Nem okoz P&L hibát, de elnyomja a valódi WARNING-okat.

**Vizsgálandó:** Honnan olvassa a `pt_monitor.py` a LION/SDRL adatokat? Lehetséges források:
1. Az `ib.executions()` vagy `ib.fills()` régi adatot ad vissza (IBKR cache)
2. Egy nem-dátumos state fájl valahol (nem a `monitor_state_YYYY-MM-DD.json` pattern)
3. Az `ib.positions()` régi phantom pozíciókat mutat (de a monitor_positions script nem talál LION-t)

**Debug lépések:**
1. A `pt_monitor.py` `main()` függvényében logolni melyik fájlból/forrásból töltötte a LION/SDRL state-et
2. A `load_state()` visszatérési értékét logolni: `logger.info(f"Loaded state: {list(state.keys())}")`
3. Ha a state üres (nincs LION) de a monitor mégis futtatja → a LION az `ib.executions()` alapú `tp1_was_filled()` hívásból jön

**Fix:** Ha az `ib.executions()` a forrás → a `tp1_was_filled()` függvényben szűrni a mai dátumra (már szűr, de ellenőrizni hogy a szűrés működik-e IBKR paper account-on 22:00 UTC után, ami technikailag a következő nap).

**Teszt:** 22:00 utáni monitor ciklus → nincs LION/SDRL event a pt_events JSONL-ben

**Fájl:** `scripts/paper_trading/pt_monitor.py`

---

## Commit

```
fix(cleanup): BC23 cleanup — nuke.py, FRED optional, phantom investigation

1. nuke.py: fix NameError on _log_path (log rotation compatibility)
2. FRED API: downgrade from CRITICAL to OPTIONAL — pipeline continues
   without FRED (TNX fallback from Polygon, yield curve is shadow-only)
3. pt_monitor: investigate and fix phantom LION/SDRL events in post-market
   monitor cycles (source is not monitor_state files)
```
