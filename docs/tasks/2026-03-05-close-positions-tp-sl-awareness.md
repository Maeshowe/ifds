Status: DONE
Updated: 2026-03-07
Note: Implementálva — kód ellenőrizve 2026-03-07

# Task: close_positions.py — TP/SL fill-aware MOC mennyiség kalkuláció

**Dátum:** 2026-03-05
**Prioritás:** 🔴 CRITICAL
**Érintett fájl:** `scripts/paper_trading/close_positions.py`
**Trigger:** Mar 5 EOD — LION -177 inadvertent short pozíció keletkezett paper accountban

---

## Azonnali teendő (Tamás — mar 6 15:30 CET előtt)

```bash
python scripts/paper_trading/nuke.py
```

Ez lezárja a LION -177 short pozíciót piaci áron. A nuke.py `action = 'BUY' if pos.position < 0` logikát használ — a negatív pozíciót helyesen BUY-jal zárja.

---

## Probléma

### Mi történt (mar 5)?

1. Pipeline LION 537 db-ot méretezett (FRESH, score 142.5)
2. `pt_submit.py` beküldte a bracket ordereket
3. **Napon belül: LION Bracket A TP1 ($10.00) teljesült — 177 db zárt**
4. 21:40-kor `pt_close.py` csatlakozik → `ib.positions()` visszaadja: **LION position=537**

**Ez a bug.** Az `ib.positions()` az eredeti teljes pozíciót adja vissza (537), nem a TP1 fill utáni maradékot (537 - 177 = 360). Ennek oka: az IBKR a pozíciót **nettóan** számolja — a 177 db már zárult TP1-en, de a fennmaradó 360 db-ot a `position` értéke már 360-nak kellene mutatnia. Azonban a `close_positions.py` **nem vár elég ideig a szinkronizációra** (csak 3 másodpercet), és a pozíció frissülése késhet.

**Következmény:** `pt_close.py` eladott 500+37=537 db-ot, miközben csak 360 db volt nyitva → 537 - 360 = **-177 short keletkezett**.

### Kód — a probléma helye

```python
# close_positions.py:56
ib = connect(client_id=11)
ib.sleep(3)  # ← ELÉGTELEN: 3 mp nem elég a TP/SL fill utáni pozíció szinkronizálásához
```

```python
# close_positions.py:80
positions = [p for p in ib.positions()
             if p.position != 0
             and '.CVR' not in p.contract.symbol
             and p.contract.secType == 'STK']
# ↑ NEM veszi figyelembe, hogy a pozíció mérete már változhatott intraday TP/SL miatt
```

---

## Fix

### 1. Szinkronizációs várakozás növelése

```python
ib = connect(client_id=11)
ib.sleep(3)

# Kényszerített pozíció-frissítés: reqPositions() + várakozás
ib.reqPositions()
ib.sleep(5)  # 3s → 8s összesen, elegendő az IBKR szinkronizáláshoz
```

### 2. Pozíció validáció — executed fills ellenőrzése

A `ib.executions()` visszaadja az aznapi fill-eket. A MOC mennyiség kalkuláció előtt le kell kérdezni és levonni a már zárt mennyiséget:

```python
from ib_insync import ExecutionFilter
from datetime import date, timezone
import datetime

def get_net_open_qty(ib, con_id: int, gross_position: float) -> int:
    """
    Kiszámolja a ténylegesen nyitott mennyiséget az aznapi fill-ek figyelembevételével.
    Visszaadja a nettó nyitott qty-t (signed).
    """
    today = date.today().strftime('%Y%m%d')
    exec_filter = ExecutionFilter(time=today + ' 00:00:00')
    fills = ib.reqExecutions(exec_filter)

    # Összegyűjti az aznapi fill-eket erre a contractra
    net_filled = 0
    for fill in fills:
        if fill.contract.conId == con_id:
            qty = fill.execution.shares
            if fill.execution.side == 'SLD':
                net_filled += qty   # eladott (záró LONG vagy nyitó SHORT)
            else:
                net_filled -= qty   # vett (záró SHORT vagy nyitó LONG)

    # A pozíció ib.positions()-ból + fill korrekció
    # Normál eset: gross_position már nettó az IBKR-ban, de ha delay van:
    net_position = gross_position + net_filled
    return int(net_position)
```

**Megjegyzés:** Ha az IBKR szinkronizáció rendben van (pozíció már tükrözi a TP/SL fill-et), `net_filled` nulla lesz és a számítás nem változtat. Ha delay van, korrigál.

### 3. Pozíció zero-check a MOC küldés előtt

```python
for pos in positions:
    sym = pos.contract.symbol
    con_id = pos.contract.conId

    # ÚJ: nettó pozíció ellenőrzés
    net_qty = get_net_open_qty(ib, con_id, pos.position)
    if net_qty == 0:
        logger.info(f"{sym}: pozíció már zárva (TP/SL fill), MOC kihagyva")
        print(f"  {sym}: SKIP — already closed (intraday TP/SL)")
        continue
    if abs(net_qty) != abs(pos.position):
        logger.info(f"{sym}: pozíció korrigálva {pos.position} → {net_qty} (intraday partial fill)")
        print(f"  {sym}: qty adjusted {int(abs(pos.position))} → {abs(net_qty)} (intraday fill)")

    action = 'SELL' if net_qty > 0 else 'BUY'
    qty = abs(net_qty)
    # ... rest of order placement unchanged
```

### 4. Alternatív egyszerűsített megoldás (ha az executions API megbízhatatlan)

Ha a `reqExecutions()` is késhet, a legrobusztusabb megoldás: **a szinkronizációs idő növelése + retry loop**:

```python
ib = connect(client_id=11)

# Várakozás pozíció szinkronizációra — retry loop
for attempt in range(3):
    ib.sleep(5)
    positions_raw = [p for p in ib.positions()
                     if p.position != 0
                     and '.CVR' not in p.contract.symbol
                     and p.contract.secType == 'STK']
    # Ha pozíció listán változás van (TP/SL zárt közben), stabil
    # Ennél a megközelítésnél nem kell executions API
    break
```

**Ajánlott: a 2+3. pont kombinációja** (executions-alapú korrekció + szinkronizáció növelés). Ez a legbiztonságosabb, mert nem az időzítéstől függ.

---

## Tesztelés

### Unit tesztek (új)
- `test_close_positions_tp_fill_before_moc`: Mock TP fill után a `get_net_open_qty` 0-t ad vissza → MOC nem kerül beküldésre az adott tickerre
- `test_close_positions_partial_tp_fill`: 537 db-ból 177 zárt TP1-en → `get_net_open_qty` 360-at ad vissza → MOC 360 db-ot küld, nem 537-et
- `test_close_positions_no_fills`: Nincs intraday fill → `get_net_open_qty` az eredeti pozíciót adja vissza

### Integrációs ellenőrzés
- Mar 5 replay: Ha a fix aktív lett volna, LION MOC-on 360 db-ot adott volna el (500 alatt → 1 leg), nem 537-et → nem keletkezett volna short pozíció

---

## Kapcsolódó taskok

- `2026-03-05-eod-report-moc-orderref-fix.md` — szorosan kapcsolódik: mindkét bug ugyanabból a tőből fakad (az EOD/close script nem látja az intraday IFDS fill-eket)
- CC implementálhatja egyszerre a két taskot, vagy külön — jelezze ha szétválasztandó

---

## Mellékesen: nuke.py logging hiánya

A `nuke.py` kizárólag `print()`-et használ, nem ír fájlba. Ezért nuke futtatás után nincs visszakereshető log. Adjunk hozzá alapszintű file logging-ot:

```python
import logging

log_path = f"logs/nuke_{date.today().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler(),  # stdout megmarad
    ]
)
logger = logging.getLogger('nuke')
```

A meglévő `print()` hívások `logger.info()`-ra cserélendők. Ez alacsony prioritású, de a `close_positions.py` fix mellé beleférhet ugyanabba a commitba.

---

## Git commit üzenet

```
fix(close_positions): use net position after intraday TP/SL fills for MOC qty

close_positions.py used gross position from ib.positions() without
accounting for intraday TP/SL bracket fills. If Bracket A TP1 filled
during the day, the remaining open qty is less than the original position.
Selling the full gross qty creates an inadvertent short position.

Root cause: 3s sync wait is insufficient for IBKR to reflect intraday fills.
Fix: increase sync wait + cross-check open qty against reqExecutions() fills
before placing MOC orders.

Triggered by: 2026-03-05 LION -177 short after TP1 filled 177 shares,
then close_positions.py sold 537 shares (500+37 split) = net -177 short.

Immediate remediation: nuke.py run at 2026-03-06 15:30 CET market open.
```
