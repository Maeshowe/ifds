---
Status: DONE
Updated: 2026-03-18
---

# Feature: cumulative_pnl.json — napi commission tárolása

## Döntés

`cumulative_pnl` értéke **gross marad** (jutalék nélkül) — ez az eod_report.py
jelenlegi viselkedése, ne változzon.

A napi commission összesítőt azonban tároljuk el minden daily_history entry-ben,
hogy a nettó P&L utólag kiszámolható legyen.

## Jelenlegi állapot

A `build_trade_report()` függvény minden trade-hez kiszámolja a commission-t
és eltárolja a `trades` listában. Az `update_cumulative_pnl()` azonban csak
az összesített gross P&L-t írja a JSON-ba — a commission nem kerül bele.

A `daily_history` entry jelenlegi struktúrája:
```json
{
  "date": "2026-03-17",
  "pnl": -76.04,
  "trades": 8,
  "filled": 7,
  "tp1_hits": 1,
  "tp2_hits": 0,
  "sl_hits": 0,
  "moc_exits": 6
}
```

## Kért változtatás

Adjunk hozzá egy `commission` mezőt minden daily_history entry-hez,
amely az aznapi összes trade commission összegét tartalmazza:

```json
{
  "date": "2026-03-17",
  "pnl": -76.04,
  "commission": 9.55,
  "trades": 8,
  "filled": 7,
  "tp1_hits": 1,
  "tp2_hits": 0,
  "sl_hits": 0,
  "moc_exits": 6
}
```

Ebből a nettó P&L bármikor kiszámolható: `pnl - commission`.

## Implementáció

### `update_cumulative_pnl()` — `eod_report.py`

A trades listából összesítjük a commission-t:

```python
daily_commission = round(sum(t.get('commission', 0.0) for t in trades), 4)
```

Majd az entry dict-be belekerül:

```python
entry = {
    'date': today_str,
    'pnl': round(daily_pnl, 2),
    'commission': daily_commission,
    'trades': total_trades,
    ...
}
```

### Visszamenőleges adat

A meglévő daily_history entry-kben nincs `commission` mező — ez elfogadható,
az új entry-ktől kezdve lesz jelen. Nem kell visszamenőleg pótolni.

## Tesztelés

1. Unit test: `test_eod_report.py` — `update_cumulative_pnl()` commission
   mező ellenőrzése a daily entry-ben
2. Unit test: nulla commission eset (pl. paper trading fee-mentes napok)
3. Meglévő tesztek: 951 passing — regresszió

## Commit üzenet

```
feat(eod_report): store daily commission in cumulative_pnl.json

cumulative_pnl remains gross (no change in calculation).
Add 'commission' field to each daily_history entry so net P&L
can be derived: pnl - commission.

Applies from next run forward; no backfill needed for existing entries.
```

## Érintett fájlok

- `scripts/paper_trading/eod_report.py` — `update_cumulative_pnl()` módosítás
- `tests/paper_trading/test_eod_report.py` — commission mező tesztek
