# Task: eod_report.py — MOC zárások felismerése (orderRef='' bug)

**Dátum:** 2026-03-05  
**Prioritás:** 🔴 CRITICAL  
**Érintett fájl:** `scripts/paper_trading/eod_report.py`  
**Trigger:** Mar 4 EOD — 6 valós trade, +$232.46 P&L, de az EOD report "Trades: 0" mutatott

---

## Probléma

Az `eod_report.py` az `execDetails` `orderRef` mezőjét használja a trade-ek azonosítására (`IFDS_*` prefix). A MOC zárások (`pt_close.py` által küldött piaci orderek) azonban `orderRef=''` értékkel érkeznek vissza az IBKR-tól — a parser nem ismeri fel őket, így a napi trade lista üres marad.

### Bizonyíték a logból (2026-03-04 pt_eod.log)

**Tényleges executions (orderRef=''):**
```
execDetails: side='SLD', shares=304, price=37.87, orderRef=''  → AR  realizedPNL=+255.80
execDetails: side='SLD', shares=62,  price=72.48, orderRef=''  → TIGO realizedPNL=+25.51
execDetails: side='SLD', shares=96,  price=81.02, orderRef=''  → NYT  realizedPNL=-39.50
execDetails: side='SLD', shares=126, price=42.68, orderRef=''  → ENPH realizedPNL=-28.22
execDetails: side='SLD', shares=32,  price=158.49,orderRef=''  → LYV  realizedPNL=-70.21
execDetails: side='SLD', shares=151, price=53.55, orderRef=''  → TS   realizedPNL=+89.08
```

**updatePortfolio realizedPNL (napvégi állapot):**
```
AR:   realizedPNL=255.8
TIGO: realizedPNL=25.51
NYT:  realizedPNL=-39.5
ENPH: realizedPNL=-28.22
LYV:  realizedPNL=-70.21
TS:   realizedPNL=89.08
```

**EOD report output:** `Trades: 0 | P&L today: $+0.00` ← helytelen

**Helyes napi P&L:** +$232.46

---

## Fix

### 1. Elsődleges fix — `updatePortfolio` realizedPNL olvasása

A legmegbízhatóbb forrás a `updatePortfolio` callback `realizedPNL` mezője — ez az IBKR által számolt, napi szinten aggregált realized PNL per pozíció. Ha `realizedPNL != 0.0`, az adott ticker aznap zárt pozícióval rendelkezik.

```python
# Jelenlegi (hibás) logika — csak IFDS_* orderRef-et keres:
trades = [e for e in exec_details if e.orderRef.startswith('IFDS_')]

# Fix — updatePortfolio realizedPNL alapján:
daily_pnl_by_symbol = {}
for item in portfolio_items:
    if item.realizedPNL != 0.0:
        daily_pnl_by_symbol[item.contract.symbol] = item.realizedPNL
```

### 2. execDetails fallback — orderRef='' kezelése

Ha az entry fill `orderRef='IFDS_*'` alapján azonosítható (a submit logból), akkor a zárás oldal `orderRef=''` execDetails párosítható a szimbólum + qty alapján:

```python
# Zárás felismerése: orderRef üres, side=SLD, qty egyezik az entry-vel
closing_execs = [
    e for e in exec_details
    if e.orderRef == '' and e.execution.side == 'SLD'
]
```

### 3. Trade rekord összeállítása

Ha az entry fill nem érhető el (TIF=DAY, a nap végén lejárt és nem exec'd), a `updatePortfolio` adatból:

```python
TradeRecord(
    symbol=symbol,
    exit_price=exec.execution.price,
    exit_qty=exec.execution.shares,
    exit_type='MOC',  # orderRef='' → MOC close
    pnl=portfolio_item.realizedPNL,
    entry_price=None,   # nem elérhető execDetails-ből utólag
    entry_qty=exec.execution.shares,
)
```

Az `entry_price`-t a `trades_YYYY-MM-DD.csv`-ből lehet visszaolvasni (az execution plan CSV tartalmazza).

### 4. Kumulatív P&L frissítése

A kumulatív számítás jelenleg a napi trade-ek összegéből áll — ha 0 trade-et lát, 0-t ad hozzá. A fix után a `updatePortfolio` realizedPNL-ből számított napi P&L-t kell hozzáadni.

---

## Tesztelés

### Unit tesztek (új)
- `test_eod_moc_orderref_empty`: execDetails `orderRef=''` esetén a trade felismert legyen
- `test_eod_portfolio_realizedpnl`: `updatePortfolio` `realizedPNL != 0` esetén trade rekord generálódjon
- `test_eod_zero_trades_not_reported_on_moc_day`: Ha van `realizedPNL != 0` de nincs `IFDS_*` exec, a report NEM mutat 0 trade-et

### Integrációs ellenőrzés
- Mar 4 replay: A fix után az EOD script a logból visszajátszva `Trades: 6`, `P&L: +$232.46`-ot kell mutasson
- Idempotency: Kétszeri futtatás ugyanazt az eredményt adja (ez a meglévő idempotency guard scope-jába esik)

---

## Kapcsolódó backlog task

Ez a fix **részben átfed** a korábban tervezett `eod_report.py:216-264 idempotency guard` taskkal (dupla futás védelme). CC implementálja mindkettőt egyszerre, vagy jelezze ha szétválasztandó.

---

## Git commit üzenet

```
fix(eod_report): recognize MOC closes with empty orderRef

MOC close orders submitted by pt_close.py arrive with orderRef=''
from IBKR, causing the EOD parser to report 0 trades even when
positions were opened and closed successfully.

Fix: read realized P&L from updatePortfolio callback instead of
relying solely on IFDS_* orderRef matching in execDetails.
Add fallback: pair closing executions (side=SLD, orderRef='') with
entry data from the daily trades CSV.

Triggered by: 2026-03-04 EOD showing 0 trades / $0.00 P&L despite
6 real trades and +$232.46 actual realized P&L.

Fixes: eod_report.py:216-264 (partial overlap with idempotency guard)
```
