---
Status: DONE
Updated: 2026-03-21
Note: Implemented — pt_avwap.py + submit_orders.py avwap fields + 15 tests
---

# Feature: AVWAP-alapú Limit→MKT konverzió (pt_avwap.py)

## Összefoglalás

Ha egy entry limit order az első 15 percben nem tölt be, a rendszer elkezdi
figyelni az anchored VWAP-ot. Ha az ár AVWAP alá esik majd visszaemelkedik
fölé, a limit order MKT-re konvertálódik, és a bracket (SL/TP) újraszámítódik
a tényleges fill ár alapján.

---

## Pontos logika

### Időzítés

```
14:30 CET (DST: 13:30 UTC) — Piacnyitás, limit order beküldve
14:45 CET (DST: 13:45 UTC) — AVWAP figyelés indul (T+15 perc, ha unfilled)
16:30 CET (DST: 15:30 UTC) — Cutoff: AVWAP konverzió utána nem fut
                               (piacnyitás + 2 óra, zoneinfo alapú DST-aware)
```

Cutoff után az unfilled limit orderek MOC-ig érvényben maradnak (a
`close_positions.py` kezeli őket).

### AVWAP kalkuláció

```
Anchor: piacnyitás első zárható bar (13:30:00 UTC)
AVWAP  = Σ(TP_i × Volume_i) / Σ(Volume_i)
         ahol TP_i = (High_i + Low_i + Close_i) / 3

Adatforrás: Polygon /v2/aggs/{ticker}/1/{from}/{to} — 1 perces bars
```

### Állapotgép (tickerenként)

```
IDLE          → (T+15 perc, unfilled) →      WATCHING
WATCHING      → (ár <= AVWAP)         →      DIPPED
DIPPED        → (ár > AVWAP)          →      CONVERTING
CONVERTING    → (MKT fill visszajelzés) →    BRACKET_REBUILD
BRACKET_REBUILD → (bracket elküldve)  →      DONE
```

### Aktiválási feltétel

Az ár **AVWAP fölé keresztez** (close > AVWAP az adott 1 perces barra) →
azonnal MKT konverzió. Nincs várakozás, nincs toleranciasáv.

### Részleges fill kezelés

Ha a limit order részben már töltött (pl. 50/100sh):
- Ha a maradék ár AVWAP +0.1%-on belül van → MKT konverzió a maradékra
- Ha ez technikai overhead (pl. split bracket, OCA conflict) → **skip**,
  a részlegesen töltött részt a `close_positions.py` zárja MOC-on

Implementálás során derül ki a complexitás — skip fallback elfogadható.

---

## Bracket újraszámítás MKT fill után

Az eredeti limit ár feltételezi a sl_distance és tp_distance-t.
MKT fill esetén a fill ár eltérhet → az eredeti SL/TP irrelevánssá válik.

### Folyamat

```
1. IBKR limit order → cancel
2. Új MKT order küldése (ugyanarra a contractra, ugyanolyan qty)
3. execDetails callback: fill_price megvárása
4. Eredeti child bracket orderek cancel (SL + TP1 + TP2)
5. Új bracket újraküldés fill_price alapján:
     new_sl  = fill_price - sl_distance
     new_tp1 = fill_price + tp1_distance
     new_tp2 = fill_price + tp2_distance
6. monitor_state frissítés: entry_price = fill_price, sl_distance megmarad
```

### Szükséges adatok a monitor_state-ben

Az `submit_orders.py` jelenleg nem tárolja az IBKR orderId-kat.
Új mezők szükségesek:

```json
{
  "entry_order_id_a": 1001,
  "entry_order_id_b": 1002,
  "tp1_order_id": 1003,
  "tp2_order_id": 1004,
  "sl_order_id_a": 1005,
  "sl_order_id_b": 1006,
  "avwap_state": "IDLE",
  "avwap_dipped": false,
  "avwap_last": null,
  "avwap_converted": false
}
```

### sl_distance és tp_distance számítása

```python
sl_distance  = entry_price - stop_loss
tp1_distance = take_profit_1 - entry_price
tp2_distance = take_profit_2 - entry_price
```

Ezek az execution plan CSV-ből olvashatók — már megvannak a monitor_state-ben.

---

## Architektúra — miért külön script?

A `pt_monitor.py` 5 perces polling ciklussal fut — ez durva az 1 perces
AVWAP követéshez. Az IBKR fill callback (execDetails) szinkron kezelése
sem illeszkedik a jelenlegi monitor struktúrájába.

**Megoldás: `pt_avwap.py`** — önálló script:

```
Futtatás: percenként (*/1 9-14 * * 1-5 UTC cron)
         14:45–15:30 UTC között (piacnyitás +15 perc → cutoff)
clientId: 16 (új, ütközésmentes)
Log:      logs/pt_avwap.log
```

### Polygon hívások száma

Max 8 ticker × 1 hívás/perc = 8 hívás/perc. Polygon Advanced tier:
unlimited calls — rendben. Csak WATCHING/DIPPED állapotú tickerekre hív.

---

## Implementáció fázisok

### Fázis 1 — submit_orders.py kiegészítés

A bracket submission után tárolja el az IBKR orderId-kat a monitor_state-be:

```python
monitor_state[sym]["entry_order_id_a"] = bracket_a[0].order.orderId
monitor_state[sym]["entry_order_id_b"] = bracket_b[0].order.orderId
monitor_state[sym]["tp1_order_id"]     = bracket_a[1].order.orderId
monitor_state[sym]["tp2_order_id"]     = bracket_b[1].order.orderId
monitor_state[sym]["sl_order_id_a"]    = bracket_a[2].order.orderId
monitor_state[sym]["sl_order_id_b"]    = bracket_b[2].order.orderId
monitor_state[sym]["avwap_state"]      = "IDLE"
monitor_state[sym]["avwap_dipped"]     = False
monitor_state[sym]["avwap_last"]       = None
monitor_state[sym]["avwap_converted"]  = False
```

### Fázis 2 — pt_avwap.py implementáció

```python
def main():
    # 1. Időellenőrzés: WATCHING ablak aktív-e?
    now_et = datetime.now(ZoneInfo("America/New_York"))
    market_open = now_et.replace(hour=9, minute=30, second=0)
    avwap_start = market_open + timedelta(minutes=15)
    avwap_cutoff = market_open + timedelta(hours=2)

    if not (avwap_start <= now_et <= avwap_cutoff):
        return

    # 2. Monitor state betöltés
    state = load_state(today_str)

    # 3. WATCHING tickerek szűrése
    watching = [
        sym for sym, s in state.items()
        if not s.get("avwap_converted")
        and not s.get("tp1_filled")
        and s.get("avwap_state") in ("IDLE", "WATCHING", "DIPPED")
    ]

    if not watching:
        return

    ib = connect(client_id=16)

    for sym in watching:
        s = state[sym]

        # IDLE → WATCHING: T+15 perc letelt
        if s["avwap_state"] == "IDLE":
            # Ellenőrzés: valóban unfilled-e?
            if is_position_open(ib, sym):
                # Már van pozíció → skip
                s["avwap_converted"] = True
                continue
            s["avwap_state"] = "WATCHING"

        # AVWAP számítás Polygon 1m bars-ból
        avwap = calculate_avwap(sym, anchor=market_open)
        if avwap is None:
            continue

        s["avwap_last"] = round(avwap, 4)
        current_price = get_last_price(ib, sym)
        if current_price is None:
            continue

        # WATCHING → DIPPED
        if s["avwap_state"] == "WATCHING" and current_price <= avwap:
            s["avwap_state"] = "DIPPED"
            s["avwap_dipped"] = True

        # DIPPED → CONVERTING: ár visszaemelkedett AVWAP fölé
        if s["avwap_state"] == "DIPPED" and current_price > avwap:
            convert_to_market(ib, sym, s, state)
            s["avwap_state"] = "DONE"
            s["avwap_converted"] = True

    save_state(today_str, state)
    disconnect(ib)
```

### Fázis 3 — convert_to_market()

```python
def convert_to_market(ib, sym, s, state):
    # Cancel limit entry orderek
    cancel_order_by_id(ib, s["entry_order_id_a"])
    cancel_order_by_id(ib, s["entry_order_id_b"])
    ib.sleep(1)

    # Cancel child bracket orderek
    for key in ["tp1_order_id", "tp2_order_id", "sl_order_id_a", "sl_order_id_b"]:
        cancel_order_by_id(ib, s[key])
    ib.sleep(1)

    # MKT order küldése
    contract = get_contract(ib, sym)
    mkt_order = MarketOrder("BUY", s["total_qty"])
    mkt_order.tif = "DAY"
    mkt_order.orderRef = f"IFDS_{sym}_AVWAP"
    trade = ib.placeOrder(contract, mkt_order)

    # Fill ár megvárása (max 30s)
    fill_price = wait_for_fill(ib, trade, timeout=30)
    if fill_price is None:
        logger.warning(f"{sym}: MKT fill timeout — skip bracket rebuild")
        return

    # Bracket újraszámítás fill ár alapján
    sl_distance  = s["entry_price"] - s["stop_loss"]  # eredeti
    tp1_distance = s["tp1_price"]   - s["entry_price"]
    tp2_distance = s["tp2_price"]   - s["entry_price"]

    new_sl  = round(fill_price - sl_distance,  2)
    new_tp1 = round(fill_price + tp1_distance, 2)
    new_tp2 = round(fill_price + tp2_distance, 2)

    # Új bracket küldés
    bracket_a = create_day_bracket(
        ib, contract, "BUY", s["qty_a"],
        fill_price, new_tp1, new_sl, account,
        tag_suffix=f"{sym}_AVWAP_A"
    )
    bracket_b = create_day_bracket(
        ib, contract, "BUY", s["qty_b"],
        fill_price, new_tp2, new_sl, account,
        tag_suffix=f"{sym}_AVWAP_B"
    )
    submit_bracket(ib, contract, bracket_a)
    submit_bracket(ib, contract, bracket_b)

    # monitor_state frissítés
    s["entry_price"] = fill_price
    s["sl_distance"] = sl_distance
    s["tp1_price"]   = new_tp1
    s["tp2_price"]   = new_tp2

    msg = (
        f"📈 {sym}: AVWAP konverzió\n"
        f"Limit → MKT fill @ ${fill_price:.2f}\n"
        f"Új SL: ${new_sl:.2f} | TP1: ${new_tp1:.2f} | TP2: ${new_tp2:.2f}\n"
        f"AVWAP: ${s['avwap_last']:.2f}"
    )
    send_telegram(msg)
    logger.info(msg)
```

---

## Tesztelés

1. Unit: `calculate_avwap()` — Polygon bars-ból helyes AVWAP számítás
2. Unit: állapotgép átmenetek (IDLE→WATCHING→DIPPED→CONVERTING→DONE)
3. Unit: bracket újraszámítás — `new_sl = fill_price - sl_distance`
4. Integration: mock IBKR fill visszajelzés + bracket cancel/resend
5. Edge case: cutoff előtt 1 perccel aktiválódó konverzió
6. Edge case: fill timeout (30s) — graceful skip
7. Meglévő tesztek: 957 passing — regresszió

---

## Érintett fájlok

- **`scripts/paper_trading/pt_avwap.py`** — új script (teljes implementáció)
- **`scripts/paper_trading/submit_orders.py`** — orderId-k tárolása monitor_state-be
- **`scripts/paper_trading/lib/orders.py`** — esetleg `wait_for_fill()` helper
- **`tests/paper_trading/test_pt_avwap.py`** — új tesztek
- **Mac Mini crontab** — `*/1 13-15 * * 1-5` (UTC, DST-aware)

---

## Commit üzenetek

```
feat(submit_orders): store IBKR order IDs in monitor_state for AVWAP

feat(pt_avwap): AVWAP-based limit-to-market conversion

If entry limit order unfilled after 15 min, watch anchored VWAP.
When price dips below AVWAP then crosses back above: convert to MKT,
cancel original bracket, rebuild with fill_price-based SL/TP.

Anchor: market open (9:30 ET). Cutoff: market open + 2h.
Polygon 1m bars for AVWAP calc. clientId=16. DST-aware.
```

---

## Prioritás

**Medium** — BC18 utáni scope (BC20 kandidáns). Az AVWAP konverzió
a limit entry miss problémát kezeli (AKAM, DELL, DOCN ismétlődő unfilled
esetek), de nem blokkolja a BC18 Phase_18A/B munkát.
