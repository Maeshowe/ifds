Status: DONE
Updated: 2026-03-31
Note: Fixed — net BOT-SLD calculation, 13 tests

# Fix: close_positions.py — get_net_open_qty leftover bug

## Probléma

A `close_positions.py` ismétlődően leftover pozíciókat hagy nyitva EOD-kor:

| Dátum | Ticker | Leftover | Close log üzenet |
|-------|--------|----------|------------------|
| 03-31 | CNX | 123sh | `qty adjusted 183 → 60` |
| 04-01 | EMN | 36sh | `qty adjusted 108 → 72` |
| 04-01 | CENX | 23sh | `position fully closed intraday, skipping MOC` (de mégis 23sh nyitva!) |

## Root cause

A `get_net_open_qty()` függvény a `BRACKET_B_SUFFIXES` alapján vonja le az intraday SLD fill-eket:

```python
BRACKET_B_SUFFIXES = ('_B_SL', '_B_TRAIL', '_TRAIL')
```

**Hiányzó suffix-ek:**
- `_LOSS_EXIT` — Scenario B loss exit (pt_monitor.py, clientId=15)
- `_AVWAP_A_TP` — AVWAP bracket A TP1 fill (pt_avwap.py, clientId=16)
- `_AVWAP_B_TP` — AVWAP bracket B TP2 fill

Az alap logika azt feltételezi, hogy `pos.position` (IBKR-ből) már tükrözi az intraday fill-eket. De:
1. A `reqPositions()` + 5s sleep nem mindig elég az IBKR szinkronizációhoz
2. A `gross_qty = int(abs(pos.position))` lehet, hogy elavult értéket olvas
3. Ha a `pos.position` NEM tükrözi a fill-eket, a suffix-szűrő sem vonja le → túl nagy vagy túl kicsi MOC qty

## Javasolt megoldás

**Approach A (robusztusabb):** Ne suffix-szűréssel dolgozz, hanem számold ki a nettó qty-t az összes SLD fill-ből:

```python
def get_net_open_qty(symbol, con_id, gross_qty, todays_fills):
    total_sold = sum(
        int(fill.execution.shares)
        for fill in todays_fills
        if fill.contract.conId == con_id
        and fill.execution.side == 'SLD'
    )
    total_bought = sum(
        int(fill.execution.shares)
        for fill in todays_fills
        if fill.contract.conId == con_id
        and fill.execution.side == 'BOT'
    )
    net_position = total_bought - total_sold
    moc_qty = max(0, net_position)
    return moc_qty
```

Ez a megközelítés nem függ az orderRef suffix-ektől — egyszerűen a BOT és SLD fill-ek különbségéből számol. Nem kell karbantartani a suffix listát.

**Approach B (minimális változtatás):** Bővítsd a suffix listát:

```python
INTRADAY_SELL_SUFFIXES = ('_B_SL', '_B_TRAIL', '_TRAIL', '_LOSS_EXIT', '_AVWAP_A_TP', '_AVWAP_B_TP')
```

Ez egyszerűbb, de törékeny — minden új exit típusnál bővíteni kell.

**Javaslat:** Approach A, mert suffix-független és jövőbiztos.

## Tesztelés

- Adj hozzá teszteket ahol:
  1. LOSS_EXIT fill van intraday → MOC qty helyes
  2. TP1 + Trail fill van intraday → "fully closed" és 0 MOC
  3. Nincs intraday fill → teljes qty MOC
  4. Partial fill (SL Bracket A) → maradék qty MOC
- Futtatd a meglévő close_positions teszteket
- `pytest` all green

## Commit

```
fix(close_positions): use net BOT-SLD calculation instead of suffix matching

get_net_open_qty relied on BRACKET_B_SUFFIXES to detect intraday sells,
but missed _LOSS_EXIT and _AVWAP_*_TP fills, causing leftover positions
on 3 consecutive days (CNX, EMN, CENX). Replace suffix matching with
total BOT minus total SLD calculation from reqExecutions — this is
suffix-independent and handles all current and future exit types.
```
