---
Status: DONE
Updated: 2026-03-16
---

# Bug: pt_monitor.py Scenario B trail aktiválódik unfilled entry pozíciókon

## Probléma

A `pt_monitor.py` a `monitor_state_{date}.json`-ból olvassa a monitorozandó
tickereket — de nem ellenőrzi hogy az adott ticker ténylegesen **be is töltött-e**
IBKR-ben. Ha egy limit entry order nem teljesül, a monitor_state-ben mégis
benne van a ticker (a `submit_orders.py` a bracket order submission után írja),
és a pt_monitor vakon elvégzi a Scenario B logikát rajta.

**Konkrét eset (2026-03-16, DELL és DOCN):**
- DELL: limit entry $151.62 — **nem töltött be** (ár nem ment le)
- DOCN: limit entry $68.63 — **nem töltött be**
- A monitor_state mégis tartalmazta mindkettőt `tp1_filled: false` státusszal
- 19:00 CET-kor a pt_monitor Scenario B-t aktivált:
  - `CLOCK DELL: Trail active (Scenario B) — Price: $156.83 > threshold: $152.38`
  - `CLOCK DOCN: Trail active (Scenario B) — Price: $74.74 > threshold: $68.97`
- Telegram alert ment ki, trail_sl számítódott — de **nem volt valódi pozíció**
- P&L hatás: nulla (IBKR-ben nincs pozíció, nincs mit zárni)
- Félrevezető alert: a Telegram azt sugallta hogy nyitott pozíción aktiválódott trail

## Gyökérok

`submit_orders.py` a bracket orderek beküldése után azonnal írja a
monitor_state-t — **a tényleges IBKR fill visszajelzés megvárása nélkül**.
Ha a limit entry order nem tölt be (pl. az ár soha nem éri el a limit szintet),
a monitor_state-ben marad a ticker mint "aktív" pozíció.

A `pt_monitor.py` `main()` függvénye:
```python
active_tickers = [
    sym for sym, s in state.items()
    if (not s.get("tp1_filled"))
    or s.get("trail_active")
    or (s.get("scenario_b_eligible", True) and not s.get("scenario_b_activated") ...)
]
```
Ez nem kérdez rá hogy az IBKR-ben ténylegesen van-e nyitott pozíció.

## Fix iránya

### Opció A — IBKR pozíció ellenőrzés monitor induláskor (ajánlott)

A `pt_monitor.py` session elején kérje le az IBKR `ib.positions()`-t, és
szűrje ki azokat a monitor_state tickereket amelyekhez nincs tényleges pozíció:

```python
# Session elején
ib_positions = {p.contract.symbol for p in ib.positions() if p.position != 0}

active_tickers = [
    sym for sym, s in state.items()
    if sym in ib_positions  # csak valódi IBKR pozíciók
    and (
        (not s.get("tp1_filled"))
        or s.get("trail_active")
        or (s.get("scenario_b_eligible", True) and not s.get("scenario_b_activated") ...)
    )
]
```

**Előny:** Mindig a valódi IBKR állapot az igazság forrása.
**Hátrány:** Egy extra IBKR hívás session induláskor (~1-2s).

### Opció B — monitor_state cleanup submit után

A `submit_orders.py` törölje a monitor_state-ből azokat a tickereket
amelyek bracket orderei nem töltöttek be (pl. EOD-kor ellenőrzés).

**Hátrány:** A cleanup timing bonyolult — a submit és a fill között idő telik.

### Javasolt implementáció

**Opció A** — egyszerűbb, robusztusabb, az IBKR pozíció mindig az igazság.

## Mellékhatások

- Scenario B trail SL számítás phantom pozíciókon → félrevezető log + Telegram
- Ha valaha a pt_monitor trail SL hit-et detektál phantom pozíciókon és
  market SELL ordert küld → **IBKR hiba** (nincs mit eladni) vagy véletlen
  short pozíció nyílik

Ez utóbbi eset még nem fordult elő, de potenciális kockázat.

## Prioritás

**Medium** — nem okozott P&L hibát eddig, de a phantom SELL order kockázata
miatt érdemes BC18 scope-ba venni.

## Tesztelés

1. Unit test: mock IBKR positions ahol DELL/DOCN hiányzik → active_tickers
   ne tartalmazza őket
2. Integration: monitor_state tartalmaz unfilled tickert → no Scenario B alert
3. Meglévő tesztek: 943 passing — regresszió

## Commit üzenet

```
fix(pt_monitor): skip monitoring for tickers without open IBKR position

pt_monitor was activating Scenario B trail on tickers whose limit entry
orders never filled. monitor_state is written at bracket submission time,
not at fill confirmation, so unfilled entries remain in state.

Fix: filter active_tickers against ib.positions() at session start.
Only tickers with actual IBKR positions are monitored.

Observed: 2026-03-16 DELL ($156.83) and DOCN ($74.74) received phantom
Scenario B trail alerts despite never filling at entry.
```

## Érintett fájlok

- `scripts/paper_trading/pt_monitor.py` — active_tickers szűrés IBKR pozíció alapján
- `tests/paper_trading/test_pt_monitor.py` — phantom pozíció unit tesztek
