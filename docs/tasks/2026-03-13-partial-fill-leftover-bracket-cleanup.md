---
Status: DONE
Updated: 2026-03-13
---

# Fix: Részleges entry fill esetén nyitott bracket orderek nem törlődnek MOC előtt

## Probléma

Ha egy ticker entry ordere **részlegesen töltődik be** (pl. IRDM: 190sh tervezett,
127sh ténylegesen BOT), az IBKR-ben a maradék qty-ra vonatkozó bracket orderek
(SL, TP1, TP2) nyitva maradnak. A `close_positions.py` csak a ténylegesen
megnyílt pozíciókat zárja MOC-kal — a soha be nem töltött bracket ordereket
nem törli.

**Konkrét eset (2026-03-12, IRDM):**
- Tervezett: 190sh (Bracket A: 63sh, Bracket B: 127sh)
- Ténylegesen BOT: 127sh (Bracket A: 63sh, Bracket B: 127sh — de B csak részben)
- IRDM Bracket A TP1 fillelt: 63sh @$25.00 ✅
- IRDM MOC: 64sh (127 - 63 = 64) ✅ — `get_net_open_qty` fix helyesen működött
- Maradék: 63sh bracket order IBKR-ben nyitva → leftover

**A `get_net_open_qty` fix NEM hibás** — az pontosan a Bracket A TP1 fill-t
vonta le. A probléma az, hogy a Bracket B unfilled részeire vonatkozó bracket
orderek (SL/TP2) soha nem törlődtek.

## Gyökérok

`close_positions.py` a MOC előtt csak az `IFDS_` orderRef-es **unfilled bracket
ordereket** törli:

```python
ifds_orders = [o for o in open_orders
               if hasattr(o, 'orderRef') and o.orderRef
               and o.orderRef.startswith('IFDS_')]
if ifds_orders:
    for order in ifds_orders:
        ib.cancelOrder(order)
```

Ez helyesnek tűnik, de a részlegesen töltött pozíciónál a Bracket B
SL/TP2 orderek **már nem `IFDS_` orderRef-el futnak** ha az OCA group
módosult, VAGY a cancel nem érte el az összes ordert a timing miatt.

**Alternatív magyarázat:** A 63sh unfilled Bracket B rész bracket orderei
nem IFDS_ orderRef-el jöttek létre (pl. a split leg miatt más clientId/orderRef),
ezért a cancel loop kihagyta őket.

## Vizsgálandó

1. A `submit_orders.py`-ban hogyan jönnek létre a split bracket orderek —
   minden leg kap `IFDS_` orderRef-et?
2. A pt_submit.log-ban mik az IRDM bracket orderek orderRef-jei?
3. A `close_positions.py` cancel loop valóban minden ordert elért?
   (`No unfilled IFDS orders to cancel` üzenet volt — ez gyanús)

## Fix iránya

### Opció A — Robusztus cancel: orderRef nélkül is töröljük

A cancel loop ne csak `IFDS_` orderRef-es ordereket töröljön, hanem
**minden nyitott ordert** a managed accounton (paper trading, ez biztonságos):

```python
open_orders = ib.openOrders()
if open_orders:
    for order in open_orders:
        ib.cancelOrder(order)
    ib.sleep(2)
    logger.info(f"Cancelled {len(open_orders)} open orders before MOC")
```

**Kockázat:** Ha valaha nem-IFDS order él a paper accounton, azt is törli.
Paper trading-nél ez elfogadható.

### Opció B — OCA group cancel

A bracket orderek OCA group-ban vannak — az OCA group cancel az egész
groupot törli, beleértve a részlegesen unfilled részeket is.

### Javasolt implementáció

**Opció A** — paper trading accounton biztonságos, egyszerűbb, robosztusabb.
A `IFDS_` filter helyett: cancel ALL open orders + log.

## Tesztelés

1. Unit test: részlegesen töltött pozíció szimulálása — cancel loop
   minden ordert töröl-e (IFDS_ és non-IFDS_ egyaránt)
2. pt_submit.log manuális ellenőrzés: IRDM bracket orderek orderRef-jei
3. Meglévő tesztek: 943 passing — regresszió

## Kapcsolódó

- `fix(close_positions)`: `get_net_open_qty` fix — 2026-03-11 ✅ DONE
- `submit_orders.py` — bracket order létrehozás split logika

## Commit üzenet

```
fix(close_positions): cancel all open orders before MOC, not just IFDS_ refs

Partial entry fills leave residual bracket orders (SL/TP2) that are
not always tagged with IFDS_ orderRef (e.g. split legs, OCA groups).
The previous IFDS_-only cancel filter missed these orders, causing
leftover positions.

Fix: cancel ALL open orders on the account before MOC submission.
Safe for paper trading account (DUH118657) where only IFDS orders exist.

Observed: 2026-03-12 IRDM 63sh leftover (127sh filled of 190sh planned,
Bracket B residual orders not cancelled).
```

## Fájlok

- `scripts/paper_trading/close_positions.py` — cancel loop módosítás
- `tests/paper_trading/test_close_positions.py` — cancel all orders teszt
