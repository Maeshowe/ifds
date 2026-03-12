---
Status: DONE
Updated: 2026-03-12
---

# Fix: close_positions.py MOC qty helytelen számítás TP1+trail esetén

## Probléma

A `get_net_open_qty()` függvény minden `IFDS_` orderRef-el SLD fill-t levon a
gross pozícióból — beleértve a Bracket A TP1 fill-t is. Ez helytelen, mert a
Bracket A és Bracket B IBKR-ben külön pozícióként él.

**Konkrét eset (2026-03-11, LASR):**
- `total_qty=52`: Bracket A=17sh, Bracket B=35sh
- TP1 fillelt intraday: `IFDS_LASR_A_TP` → 17sh SLD
- `pos.position` = 35sh (Bracket B, IBKR-ben külön pozíció)
- `get_net_open_qty`: `35 - 17 = 18` → 18sh MOC-ra küldve
- Eredmény: **17sh leftover**, manuális nuke szükséges

**Gyökérok:** Az `IFDS_LASR_A_TP` fill a Bracket A-hoz tartozik — az a 17sh
már nem szerepel a `pos.position=35`-ben. A levonás ezért duplikált és hibás.

## A helyes logika

`get_net_open_qty()` csak olyan IFDS SLD fill-eket vonjon le, amelyek
**ugyanolyan típusú pozíciót** érinttek mint ami jelenleg open (Bracket B
SL/trail fill-ek). A Bracket A TP1 fill-t NEM szabad levonni, mert az
IBKR már külön kezeli.

## Fix iránya

### Opció A — Egyszerű: orderRef filter szűkítése

Ne vonjuk le az `_A_TP` fill-eket. Csak `_B_SL`, `_TRAIL`, `_B_TRAIL`
orderRef-eket vonjon le.

```python
BRACKET_B_REFS = {"_B_SL", "_B_TRAIL", "_TRAIL"}

def get_net_open_qty(symbol, con_id, gross_qty, todays_fills):
    bracket_sold = sum(
        int(fill.execution.shares)
        for fill in todays_fills
        if fill.contract.conId == con_id
        and fill.execution.side == 'SLD'
        and any(
            (getattr(fill.execution, 'orderRef', '') or '').endswith(suffix)
            for suffix in BRACKET_B_REFS
        )
    )
    ...
```

**Kockázat:** Ha valaha Bracket A TP1 fill NEM kerül az IBKR-be külön
pozícióként (pl. fill delay), akkor a Bracket A qty benne maradhat
`pos.position`-ban és oversell-t okozhat. De ez IBKR papír trading viselkedés
alapján nem fordult elő.

### Opció B — Robusztus: monitor_state alapú qty

A monitor_state-ből olvassa ki hogy egy tickernek van-e aktív trail
(`trail_active=True`, `trail_scope='bracket_b'`) — ha igen, a `qty_b`-t
használja közvetlenül a gross_qty helyett.

```python
def get_net_open_qty(symbol, con_id, gross_qty, todays_fills, state=None):
    if state and symbol in state:
        s = state[symbol]
        if s.get("trail_active") and s.get("trail_scope") == "bracket_b":
            # Bracket B open: csak trail fill-eket vonjunk le
            ...
```

**Előny:** Explicit state-alapú, nem fill-számolás.
**Hátrány:** monitor_state dependency — close_positions.py-ba be kell tölteni.

## Javasolt implementáció

**Opció A** — egyszerűbb, a fill orderRef-ek jól definiáltak, és a valódi
probléma az `_A_TP` téves levonása volt.

## Tesztelés

1. Unit test: `test_close_positions.py` — mock todays_fills ahol `_A_TP` fill
   van, ellenőrizni hogy `get_net_open_qty` NEM vonja le
2. Unit test: `_B_SL` és `_TRAIL` fill-eket IGEN levonja
3. Meglévő tesztek: 936 passing — regresszió ellenőrzés

## Commit üzenet

```
fix(close_positions): exclude Bracket A TP1 fills from MOC qty deduction

get_net_open_qty() was subtracting IFDS_*_A_TP fills from Bracket B
pos.position, causing undersized MOC orders when TP1 hit intraday.
Bracket A and B are separate IBKR positions — A_TP fills must not be
deducted from B qty.

Observed: 2026-03-11 LASR 17sh leftover (35sh Bracket B, 18sh MOC sent).

Fix: only deduct _B_SL, _TRAIL, _B_TRAIL orderRef fills.
```

## Fájlok

- `scripts/paper_trading/close_positions.py` — `get_net_open_qty()` módosítás
- `tests/paper_trading/test_close_positions.py` — új unit tesztek
