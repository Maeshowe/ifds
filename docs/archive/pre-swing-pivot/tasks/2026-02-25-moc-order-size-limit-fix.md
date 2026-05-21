Status: DONE
Updated: 2026-03-07
Note: Implementálva — kód ellenőrizve 2026-03-07

# Task: close_positions.py — MOC order size limit fix

**Date:** 2026-02-25
**Priority:** HIGH — ma este előfordult, holnap is előfordulhat
**Scope:** `scripts/paper_trading/close_positions.py`
**Trigger:** KMI MOC SELL 611 shares → Error 383 (IBKR precautionary size limit 500 db). A pozíció nem zárt, EOD: `Still 2 open positions! KMI: 611.0`

---

## A probléma

Az IBKR paper trading accounton precautionary size limit = 500 db / order. Ha egy pozíció mérete > 500, egyetlen MOC order elutasítva. A `close_positions.py` nem kezeli ezt az esetet.

**Error 383:** `The following order "ID:38" size exceeds the Size Limit of 500. Restriction is specified in Precautionary Settings of Global Configuration/Presets.`

---

## Megoldás

Ha `abs(position) > 500`, a MOC zárást **két részletben** kell leadni:
- Leg 1: 500 db
- Leg 2: maradék (`abs(position) - 500`)

Mindkét leg ugyanarra a kontraktusra, ugyanolyan MOC order típussal.

---

## Implementáció

### `scripts/paper_trading/close_positions.py`

A MOC order loop-ban a jelenlegi:

```python
action = 'SELL' if pos.position > 0 else 'BUY'
qty = int(abs(pos.position))
order = create_moc_order(qty, account, action=action)
ib.placeOrder(contract, order)
moc_submitted.append((sym, qty, action))
print(f"  {sym}: MOC {action} {qty} shares")
```

Cseréld le erre:

```python
action = 'SELL' if pos.position > 0 else 'BUY'
qty = int(abs(pos.position))

MAX_ORDER_SIZE = 500  # IBKR precautionary size limit

if qty <= MAX_ORDER_SIZE:
    order = create_moc_order(qty, account, action=action)
    ib.placeOrder(contract, order)
    moc_submitted.append((sym, qty, action))
    print(f"  {sym}: MOC {action} {qty} shares")
else:
    # Split into multiple legs
    remaining = qty
    leg = 1
    while remaining > 0:
        leg_qty = min(remaining, MAX_ORDER_SIZE)
        order = create_moc_order(leg_qty, account, action=action)
        ib.placeOrder(contract, order)
        moc_submitted.append((sym, leg_qty, action))
        print(f"  {sym}: MOC {action} {leg_qty} shares (leg {leg}/{-(-qty // MAX_ORDER_SIZE)})")
        remaining -= leg_qty
        leg += 1
```

### `MAX_ORDER_SIZE` konstans

Add hozzá a fájl tetejéhez a többi konstans mellé:

```python
MAX_ORDER_SIZE = 500  # IBKR precautionary size limit (Global Configuration/Presets)
```

### Telegram üzenet — split esetén jelezze

A Telegram notification blokkban a split pozíciók összesítve jelenjenek meg (nem leg-enként):

```python
# Összesített qty per ticker a Telegram üzenethez
ticker_totals = {}
for sym, leg_qty, action in moc_submitted:
    if sym not in ticker_totals:
        ticker_totals[sym] = (0, action)
    ticker_totals[sym] = (ticker_totals[sym][0] + leg_qty, action)

lines = [f"🔔 PAPER TRADING MOC — {today_str}",
         f"Closing {len(ticker_totals)} positions at market close:"]
for sym, (total_qty, action) in ticker_totals.items():
    lines.append(f"{sym}: {action} {total_qty} shares")
send_telegram("\n".join(lines))
```

---

## Tesztelés

```python
# tests/test_close_positions_split.py

def test_moc_small_position_single_order():
    """400 db pozíció → egyetlen MOC order."""
    ...

def test_moc_exact_limit_single_order():
    """500 db pozíció → egyetlen MOC order (határérték)."""
    ...

def test_moc_large_position_split_two():
    """611 db pozíció → két leg: 500 + 111."""
    ...

def test_moc_very_large_position_split_three():
    """1200 db pozíció → három leg: 500 + 500 + 200."""
    ...

def test_moc_split_telegram_aggregated():
    """Split pozíció Telegram üzenetben összesítve jelenik meg."""
    ...
```

---

## Git

```bash
git add scripts/paper_trading/close_positions.py tests/test_close_positions_split.py
git commit -m "fix: MOC order split ha pozíció > 500 db (IBKR size limit)

Error 383: KMI 611 db MOC SELL elutasítva 2026-02-25.
close_positions.py: ha abs(position) > MAX_ORDER_SIZE (500),
több leg-ben adja le a MOC ordert (500, 500, ..., maradék).
Telegram üzenet összesítve mutatja a ticker teljes qty-t.
5 unit teszt.

Fixes: KMI nem zárt MOC-kal 2026-02-25"
git push
```
