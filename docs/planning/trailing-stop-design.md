# Trailing Stop Design — IFDS Paper Trading

**Dátum:** 2026-03-07
**Státusz:** Design fázis — implementáció BC17/BC18 scope
**Előfeltétel:** EOD fix (`2026-03-05-eod-report-moc-orderref-fix.md`) kész kell legyen

---

## Motiváció

**LION (2026-03-05):** Entry ~$9.50, TP1 $10.00 teljesült (177 db). Maradék 360 db
nuke-olva $9.99-n (márc 6 piacnyitás). MOC lett volna $10.67 → elveszett potenciál: ~$243.

A jelenlegi bracket struktúra statikus: TP1 + TP2 limit + SL stop. TP1 teljesülése
után a Bracket B-n nincs nyereségvédelem — az ár visszajöhet az entry alá és az
eredeti SL üt.

---

## A két szcenárió

### Szcenárió A — TP1 limit TELJESÜL napközben

```
Entry $9.50, TP1 $10.00 → fill, 177 db (33%) zárt
Marad: 360 db Bracket B, eredeti SL $8.90

Trail aktiválás: TP1 fill detektálása után azonnal
Trail distance: eredeti SL távolság = $9.50 - $8.90 = $0.60
Trail scope: csak Bracket B (360 db)

Példa menet:
  TP1 fill @ $10.00 → trail SL = $9.40 (min: breakeven $9.50, tehát $9.50)
  Ár megy $10.30   → trail SL = $9.70
  Ár megy $10.67   → trail SL = $10.07
  Ár visszajön $10.07 → SELL 360 db @ $10.07
  P&L: +$207 (vs. nuke $9.99 → +$176, vs. eredeti SL $8.90 → -$216)
```

**Breakeven protection:** Az első trail SL értéke minimum az entry ár:
```python
initial_trail_sl = max(entry_price, current_high - sl_distance)
```

### Szcenárió B — TP1 NEM teljesül, nap közepe után nyereséges pozíció

```
Entry $43.70 (SDRL), TP1 $45.00 limit order él
19:00 CET-kor az ár $44.20 → pozíció nyereséges (+$57.50)

Trail aktiválás: 19:00 CET + pozíció nyereséges (current_price > entry_price)
Trail scope: TELJES pozíció (Bracket A + Bracket B)
Trail distance: eredeti SL távolság = $43.70 - $40.91 = $2.79
Trail indul: $44.20 - $2.79 = $41.41 (breakeven fölött)

Ha az ár $41.41-re esik → SELL teljes pozíció
Ha az ár $45.00-re megy → TP1 limit tölt, majd Szcenárió A lép be
```

**Szcenárió B logikája:** Nap végén a nyereséges de TP1-et el nem ért pozíciókat
nagyobb kockázatnak tesszük ki (MOC-ig tartjuk). A 19:00 CET trail aktiválás
nyereségvédelmet biztosít: ha a piac visszafordul, nem adjuk vissza a teljes
napközbeni nyereséget.

**Szcenárió B kritikus különbsége:** Az eredeti Bracket A TP1 limit order **még él**
amikor a trail aktiválódik — ez kívánatos! Ha az ár eléri a TP1-et, a limit tölt
(Szcenárió A-ba vált). Ha nem éri el és visszafordul, a trail SL zár.

**Szcenárió B aktiváláskor NEM kell cancelálni a bracket ordereket** — a TP1 limit
és a trail SL egyszerre él. Az eredeti bracket SL-t azonban le kell cserélni a trail
SL-re (különben dupla védelmi szint lenne).

---

## Implementációs architektúra

### Miért nem natív IBKR TrailStopOrder?

Az IBKR `TrailStopOrder` Szcenárió A-ra alkalmas lenne, de:
1. Szcenárió B időalapú aktiválása (19:00 CET) nem kezelhető natívan
2. A trail SL frissítés és az `eod_report.py` orderRef='' probléma összeütközne
3. A monitoring script úgyis szükséges → egységes megközelítés egyszerűbb

**Döntés: aktív monitoring script (`pt_monitor.py`)** — 5 percenként fut napközben.

### `pt_monitor.py` architektúra

```
Crontab: */5 9-20 * * 1-5
Utolsó futás: 20:55 UTC (21:55 CET) — 5 perccel pt_close.py előtt
```

**State fájl:** `scripts/paper_trading/logs/monitor_state_YYYY-MM-DD.json`
```json
{
  "LION": {
    "entry_price": 9.50,
    "sl_distance": 0.60,
    "tp1_price": 10.00,
    "total_qty": 537,
    "qty_b": 360,
    "tp1_filled": true,
    "trail_active": true,
    "trail_scope": "bracket_b",
    "trail_sl_current": 10.07,
    "trail_high": 10.67
  },
  "SDRL": {
    "entry_price": 43.70,
    "sl_distance": 2.79,
    "tp1_price": 45.00,
    "total_qty": 115,
    "qty_b": 77,
    "tp1_filled": false,
    "trail_active": true,
    "trail_scope": "full",
    "trail_sl_current": 41.41,
    "trail_high": 44.20
  }
}
```

**Futási logika (minden 5 percben):**

```python
for ticker in open_positions:
    state = load_state(ticker)
    current_price = get_last_price(ticker)
    now_cet = datetime.now(CET)

    # --- Szcenárió A: TP1 fill detektálása ---
    if not state['tp1_filled'] and tp1_was_filled_today(ticker):
        state['tp1_filled'] = True
        state['trail_active'] = True
        state['trail_scope'] = 'bracket_b'
        state['trail_high'] = current_price
        # Breakeven protection: min entry_price
        state['trail_sl_current'] = max(
            state['entry_price'],
            current_price - state['sl_distance']
        )
        cancel_bracket_b_sl(ticker)   # eredeti statikus SL cancelálása
        log_and_telegram(f"{ticker}: Trail aktív (Szcenárió A) SL={state['trail_sl_current']:.2f}")

    # --- Szcenárió B: időalapú aktiválás ---
    elif (not state['tp1_filled']
          and not state['trail_active']
          and now_cet.hour >= 19
          and current_price > state['entry_price']):
        state['trail_active'] = True
        state['trail_scope'] = 'full'
        state['trail_high'] = current_price
        state['trail_sl_current'] = current_price - state['sl_distance']
        cancel_original_sl(ticker)    # bracket A+B eredeti SL cancelálása
        log_and_telegram(f"{ticker}: Trail aktív (Szcenárió B) SL={state['trail_sl_current']:.2f}")

    # --- Trail SL frissítése ---
    if state['trail_active']:
        if current_price > state['trail_high']:
            state['trail_high'] = current_price
            new_sl = current_price - state['sl_distance']
            if new_sl > state['trail_sl_current']:
                state['trail_sl_current'] = new_sl
                log(f"{ticker}: Trail SL frissítve → {new_sl:.2f}")

        # --- Trail SL ütés detektálása ---
        if current_price <= state['trail_sl_current']:
            qty = state['qty_b'] if state['trail_scope'] == 'bracket_b' else state['total_qty']
            send_market_sell(ticker, qty, orderRef=f"IFDS_{ticker}_TRAIL")
            state['trail_active'] = False
            log_and_telegram(f"{ticker}: Trail SL ütve @ {current_price:.2f}, SELL {qty} db")

    save_state(ticker, state)
```

### Order management részletek

**Szcenárió A — bracket_b SL cancel:**
```python
open_orders = ib.openOrders()
sl_order = next((o for o in open_orders
                 if o.orderRef == f'IFDS_{sym}_B_SL'), None)
if sl_order:
    ib.cancelOrder(sl_order)
```
A Bracket B TP2 limit order **megmarad** — ha az ár eléri, az zár felül.

**Szcenárió B — full SL cancel:**
```python
open_orders = ib.openOrders()
for order in open_orders:
    if (hasattr(order, 'orderRef')
            and order.orderRef.startswith(f'IFDS_{sym}')
            and order.orderRef.endswith('_SL')):
        ib.cancelOrder(order)
```
A TP1 és TP2 limit orderek **megmaradnak** — ha az ár TP1-et üt, tölt és
Szcenárió A-ba vált. Ha TP2-t üt (valószínűtlen Szcenárió B-ben), az is tölt.

---

## Trail distance kalkuláció

```python
sl_distance = entry_price - original_sl_price
```

Ez az ATR-alapú stop distance amit a Phase 6 már kiszámolt — konzisztens a
scoring logikával. Az execution plan CSV tartalmazza: `limit_price` és `stop_loss`.

---

## pt_close.py interakció

A `pt_close.py` 21:40 UTC-kor fut. A monitor utolsó futása **20:55 UTC (21:55 CET)**
— azaz a monitor fut a pt_close UTÁN is egyszer. Ez potenciális konfliktus.

**Megoldás: monitor crontab módosítás**
```
*/5 9-19 * * 1-5   →  utolsó futás 19:55 UTC (20:55 CET)
```
A pt_close 21:40 UTC-kor fut → 1 óra 45 perc résluég. Ebben az ablakban a trail
nem frissül, de a pt_close MOC-on lezárja a maradék pozíciót — ez elfogadható,
a trail már megvédte a korábbi nyereséget.

**Alternatíva:** A pt_close.py tudatában van a trail state-nek — ha trail aktív,
nem küld MOC-t, hanem hagyja a trail-t zárni. Ez komplexebb és BC18 scope.

---

## EOD report integráció

Trail orderRef: `IFDS_{sym}_TRAIL` vagy `IFDS_{sym}_B_TRAIL`
→ Az EOD report **látni fogja** ezeket az IFDS_ prefix alapján (az EOD fix után).

A `monitor_state_YYYY-MM-DD.json` fájlból az EOD report kiolvashatja:
- Melyik zárás volt trail-alapú
- Mi volt a trail csúcs és a záró SL szint

---

## Kockázatok és korlátok

| Kockázat | Valószínűség | Kezelés |
|---|---|---|
| Monitor crash → trail nem frissül | Alacsony | State fájl perzisztens, Telegram alert |
| Szcenárió B: pozíció veszteséges 19:00-kor | Normál | Nem aktiválódik, eredeti SL él |
| Trail SL és pt_close MOC dupla sell | Alacsony | Monitor leáll 19:55 UTC-kor |
| IBKR paper fill delay → trail SL ütve de nem tölt | Alacsony | MOC fallback a pt_close-ban |
| Trail aktív pozíció nuke előtt | Ritka | Nuke cancelál minden ordert, MKT zár |

---

## SIM-L2 kompatibilitás

A SIM engine jelenleg statikus bracket logikát szimulál. A trailing stop bevezetése
után a SIM-L2-t is frissíteni kell — ez **BC20 scope** (SIM-L2 Mód 2). Addig a
paper trading trailing stop és a SIM eredmények **nem lesznek összehasonlíthatók**
— dokumentálni kell a paper trading naplóban melyik naptól aktív a trail.

---

## Implementációs sorrend

1. ✅ **EOD fix** (`eod-report-moc-orderref-fix.md`) — alap
2. ✅ **`close_positions.py` TP/SL awareness** — alap
3. 🆕 **`monitor_positions.py`** — leftover warning, 10:10 CET (egyszerű, BC17 előtt)
4. 🆕 **`pt_monitor.py` Szcenárió A** — TP1 fill → Bracket B trail (BC17)
5. 🆕 **`pt_monitor.py` Szcenárió B** — 19:00 CET nyereséges → full trail (BC18)
6. 🆕 **SIM-L2 trail szimulációs támogatás** — BC20

---

## Döntések (lezárva 2026-03-07)

1. **Szcenárió B threshold:** `current_price > entry_price * 1.005` — 0.5% minimum
   nyereség küszöb, hogy ne aktiválódjon zajra. ✅

2. **Monitor leállási idő:** `*/5 9-19 * * 1-5` — utolsó futás 19:55 UTC (20:55 CET),
   bőven a pt_close.py 21:40 UTC előtt. ✅

3. **Monitor state inicializálás:** a `pt_submit.py` írja a state fájlt közvetlenül
   a bracket submission után. Ha pt_submit nem futott (circuit breaker), state fájl
   nem jön létre → monitor tudja hogy nincs mit figyelni. ✅

   ```python
   # pt_submit.py — submission után
   monitor_state = {}
   for t in submitted_tickers_data:
       monitor_state[t['symbol']] = {
           'entry_price': t['limit_price'],
           'sl_distance': round(t['limit_price'] - t['stop_loss'], 4),
           'tp1_price': t['take_profit_1'],
           'tp2_price': t['take_profit_2'],
           'total_qty': t['total_qty'],
           'qty_b': t['qty_tp2'],
           'tp1_filled': False,
           'trail_active': False,
           'trail_scope': None,
           'trail_sl_current': None,
           'trail_high': None,
       }
   state_path = f'scripts/paper_trading/logs/monitor_state_{today_str}.json'
   with open(state_path, 'w') as f:
       json.dump(monitor_state, f, indent=2)
   ```

4. **TP2 limit megmarad Szcenárió A-ban:** a trail nem fut szabadon felső korlát
   nélkül. Ha az ár eléri TP2-t, a limit order zár felül — ez jobb exit mint a
   trail SL. ✅

5. **Telegram értesítések:** trail aktiváláskor és trail SL ütésekor — igen mindkét
   esetben, ezek fontos eseményei a kereskedési napnak. ✅
