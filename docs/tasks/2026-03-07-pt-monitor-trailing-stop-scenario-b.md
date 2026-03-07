Status: OPEN
Updated: 2026-03-07
Note: BC18 scope

# Task: pt_monitor.py — Trailing Stop Szcenárió B (19:00 CET időalapú)

**Dátum:** 2026-03-07
**Prioritás:** 🟡 BC18 SCOPE
**Érintett fájlok:**
- `scripts/paper_trading/pt_monitor.py` — Szcenárió B logika hozzáadása (módosítás)
- `scripts/paper_trading/logs/monitor_state_YYYY-MM-DD.json` — 2 új mező

**Előfeltétel:**
- `2026-03-07-pt-monitor-trailing-stop-scenario-a.md` implementálva és tesztelve
- `2026-03-05-eod-report-moc-orderref-fix.md` implementálva

**Design doc:** `docs/planning/trailing-stop-design.md`

---

## Motiváció

Szcenárió A csak TP1 fill esetén aktiválódik. Ha a pozíció napközben nyereséges
de TP1 nem teljesül (pl. az ár $44.20-ig ment de $45.00-t nem érte el), a teljes
nyereség elveszhet MOC-ra. A 19:00 CET időalapú trail nyereségvédelmet biztosít
ezekre az esetekre is.

**Példa (SDRL, márc 6):** Entry $43.70, TP1 $45.00, MOC exit $41.97 (-$198.95).
Ha 19:00 CET-kor az ár $44.20 lett volna (+$57.50 nyereség), a trail SL $41.41
lett volna → a $41.97 MOC-os zárás elkerülhető (trail zár $41.41-nél, nem rosszabb).
Veszteséges napon (ár $43.70 alatt 19:00-kor) nem aktiválódik — az eredeti SL véd.

---

## State fájl kiegészítés

A `pt_submit.py` által írt state fájlhoz 2 új mező kerül.

### Módosítás: `pt_submit.py` monitor state init blokkban

```python
monitor_state[t['symbol']] = {
    # ... meglévő mezők változatlanul ...
    'tp1_filled': False,
    'trail_active': False,
    'trail_scope': None,
    'trail_sl_current': None,
    'trail_high': None,
    # ÚJ mezők Szcenárió B-hez:
    'scenario_b_activated': False,   # időalapú trail már aktiválódott-e
    'scenario_b_eligible': True,     # False ha Szcenárió A már aktív (felesleges lenne)
}
```

---

## `pt_monitor.py` módosítás — Szcenárió B blokk hozzáadása

### Hol kerül a kódba

A meglévő `main()` függvény `for sym in active_tickers:` ciklusában, a
**Szcenárió A trail SL frissítés blokk ELŐTT**, de csak ha Szcenárió A
trail **nem aktív**:

```python
        # --- Szcenárió B: időalapú aktiválás (19:00 CET, nyereséges) ---
        if (not s.get('trail_active')
                and not s.get('scenario_b_activated')
                and s.get('scenario_b_eligible', True)):

            now_utc = datetime.now(timezone.utc)
            # 19:00 CET = 18:00 UTC (téli idő) / 17:00 UTC (nyári idő, CEST márc 29-től)
            # Egyszerű megközelítés: 18:00 UTC küszöb egész évre, CEST-re frissítendő
            scenario_b_hour_utc = 18  # CET=UTC+1 → 19:00 CET = 18:00 UTC

            if now_utc.hour >= scenario_b_hour_utc:
                current_price = get_last_price(ib, sym)
                if current_price is None:
                    logger.warning(f'{sym}: Cannot get price for Szcenárió B check')
                    continue

                # 0.5% küszöb: ne aktiválódjon zajra
                threshold = s['entry_price'] * 1.005
                if current_price > threshold:
                    # Cancel eredeti SL orderek (A és B bracket SL)
                    cancel_all_sl_orders(ib, sym)

                    trail_sl = round(current_price - s['sl_distance'], 4)
                    s['trail_active'] = True
                    s['trail_scope'] = 'full'
                    s['trail_sl_current'] = trail_sl
                    s['trail_high'] = round(current_price, 4)
                    s['scenario_b_activated'] = True
                    s['scenario_b_eligible'] = False
                    state_changed = True

                    msg = (f'⏰ {sym}: Trail aktív (Szcenárió B)\n'
                           f'19:00 CET — pozíció nyereséges\n'
                           f'Ár: ${current_price:.2f} > küszöb: ${threshold:.2f}\n'
                           f'Trail SL: ${trail_sl:.2f}\n'
                           f'TP1/TP2 limit orderek megmaradnak')
                    logger.info(msg)
                    send_telegram(msg)
                else:
                    logger.info(
                        f'{sym}: Szcenárió B — nem aktivál '
                        f'(ár ${current_price:.2f} ≤ küszöb ${threshold:.2f})'
                    )
```

### Új helper: `cancel_all_sl_orders()`

Szcenárió B-ben a teljes pozíciót védi a trail → mindkét bracket (A és B) SL
ordereit cancelálni kell. A TP1 és TP2 limit orderek **megmaradnak** — ha az ár
bármelyiket eléri, az tölt és a monitor következő futásán a trail deaktiválódik.

```python
def cancel_all_sl_orders(ib, sym: str) -> int:
    """Cancel all SL orders for a ticker. Returns count of cancelled orders."""
    open_orders = ib.openOrders()
    cancelled = 0
    for order in open_orders:
        ref = getattr(order, 'orderRef', '')
        if ref.startswith(f'IFDS_{sym}') and ref.endswith('_SL'):
            ib.cancelOrder(order)
            ib.sleep(0.5)
            logger.info(f'{sym}: SL cancelled — {ref} (orderId={order.orderId})')
            cancelled += 1
    if cancelled == 0:
        logger.warning(f'{sym}: No SL orders found for cancellation')
    return cancelled
```

### Trail SL ütés — full scope kezelés

A meglévő trail SL ütés blokkban a `trail_scope` alapján kell a helyes qty-t
küldeni. Szcenárió B-ben `trail_scope = 'full'` → `total_qty` db SELL:

```python
            # Trail SL ütés (meglévő blokk módosítása)
            if current_price <= s['trail_sl_current']:
                # scope alapján qty
                if s.get('trail_scope') == 'full':
                    qty = s['total_qty']
                    order_ref_suffix = 'TRAIL'
                else:  # 'bracket_b'
                    qty = s['qty_b']
                    order_ref_suffix = 'B_TRAIL'

                logger.warning(
                    f'{sym}: Trail SL hit @ ${current_price:.2f} '
                    f'— SELL {qty} shares (scope: {s["trail_scope"]})'
                )

                from ib_insync import Stock, MarketOrder
                contract = Stock(sym, 'SMART', 'USD')
                ib.qualifyContracts(contract)
                order = MarketOrder('SELL', qty)
                order.tif = 'DAY'
                order.orderRef = f'IFDS_{sym}_{order_ref_suffix}'
                order.account = ib.managedAccounts()[0]
                ib.placeOrder(contract, order)

                s['trail_active'] = False
                state_changed = True

                msg = (f'🛑 {sym}: Trail SL ütve\n'
                       f'Ár: ${current_price:.2f} ≤ SL: ${s["trail_sl_current"]:.2f}\n'
                       f'SELL {qty} shares (scope: {s["trail_scope"]})\n'
                       f'orderRef: IFDS_{sym}_{order_ref_suffix}')
                logger.warning(msg)
                send_telegram(msg)
```

### Szcenárió A → B interakció: megelőzés

Ha Szcenárió A már aktív (TP1 teljesült, `trail_scope='bracket_b'`), a
Szcenárió B nem aktiválódik — `scenario_b_eligible=False` beállítva aktiváláskor.

Ha Szcenárió A **nem** aktiválódott de az ár 19:00-kor már TP1 felett van és
a TP1 limit order épp töltés alatt van → ütközés lehetséges. Védelem:

```python
        # Szcenárió B ellenőrzés előtt: ha TP1 most töltött, A-t aktiváljuk
        # (a TP1 fill detektálás blokk fut először a ciklusban → rendben)
        if s.get('trail_active') and s.get('trail_scope') == 'bracket_b':
            s['scenario_b_eligible'] = False  # A már aktív, B felesleges
```

---

## CEST váltás (2026-03-29)

A 19:00 CET küszöb UTC-ben:
- Téli idő (CET = UTC+1): `scenario_b_hour_utc = 18`
- Nyári idő (CEST = UTC+2): `scenario_b_hour_utc = 17`

Javasolt megoldás — automatikus pytz/zoneinfo alapú számítás:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

CET = ZoneInfo('Europe/Budapest')

def get_scenario_b_hour_utc() -> int:
    """Returns UTC hour equivalent of 19:00 CET/CEST."""
    now_cet = datetime.now(CET)
    target_cet = now_cet.replace(hour=19, minute=0, second=0, microsecond=0)
    return target_cet.astimezone(ZoneInfo('UTC')).hour
```

Ez automatikusan kezeli a CEST váltást — **nem kell kézzel módosítani márc 29-én**.

---

## OrderRef konvenciók (összefoglalás)

| Szcenárió | Trail scope | OrderRef |
|---|---|---|
| A — TP1 fill → Bracket B | `bracket_b` | `IFDS_{sym}_B_TRAIL` |
| B — időalapú → teljes pozíció | `full` | `IFDS_{sym}_TRAIL` |

Mindkét prefix `IFDS_`-sel kezdődik → az EOD report látja.

---

## Active tickers szűrő kiegészítés

A `main()` elején az `active_tickers` listát ki kell egészíteni, hogy a
Szcenárió B-re váró tickereket is beleértse (19:00 CET előtt még nem aktívak):

```python
    # Meglévő (Szcenárió A):
    # active_tickers = [sym for sym, s in state.items()
    #                   if not s.get('tp1_filled') or s.get('trail_active')]

    # Módosított (A + B):
    active_tickers = [
        sym for sym, s in state.items()
        if (not s.get('tp1_filled'))           # TP1 még él → figyelni kell
        or s.get('trail_active')               # trail fut
        or (                                   # Szcenárió B még nem aktivált
            s.get('scenario_b_eligible', True)
            and not s.get('scenario_b_activated')
            and not s.get('trail_active')
        )
    ]
```

---

## Tesztelés (`tests/paper_trading/test_pt_monitor_scenario_b.py`)

- `test_scenario_b_activation_at_19_utc` — 18:00 UTC + ár > 0.5% küszöb → trail_active=True, scope='full', Telegram
- `test_scenario_b_not_activated_before_19` — 17:59 UTC → nem aktivál
- `test_scenario_b_not_activated_if_not_profitable` — ár <= entry*1.005 → nem aktivál
- `test_scenario_b_not_activated_if_scenario_a_active` — trail_scope='bracket_b' → scenario_b_eligible=False
- `test_scenario_b_full_qty_sell` — trail SL ütve, scope='full' → total_qty db SELL, orderRef=IFDS_{sym}_TRAIL
- `test_scenario_b_tp1_tp2_not_cancelled` — TP1/TP2 limit orderek megmaradnak
- `test_scenario_b_sl_orders_cancelled` — Bracket A SL + Bracket B SL mindkettő cancelálva
- `test_scenario_b_cest_transition` — zoneinfo alapú óra számítás CET vs CEST
- `test_scenario_b_trail_updates_upward` — ár emelkedik 19 után → trail_sl követi
- `test_scenario_b_trail_sl_not_lowered` — ár csökken → trail_sl nem megy le

---

## Git commit

```
feat(paper_trading): trailing stop monitor Szcenárió B (time-based)

pt_monitor.py: adds Szcenárió B — time-based trail activation at
19:00 CET if position is profitable (current_price > entry * 1.005).

On activation:
- Cancels ALL SL orders (Bracket A + B)
- Keeps TP1 and TP2 limit orders (natural upper caps)
- Trail scope: 'full' (total_qty) vs Szcenárió A 'bracket_b' (qty_b)
- orderRef: IFDS_{sym}_TRAIL (visible to eod_report.py)
- Telegram alerts on activation and SL hit

State: 2 new fields (scenario_b_activated, scenario_b_eligible)
  written by pt_submit.py at submission time.

CEST handling: zoneinfo-based UTC hour calculation — no manual
update needed at DST transition (2026-03-29).

Interaction: Szcenárió A takes priority — if TP1 fills before
19:00, scenario_b_eligible=False, B never activates.

Prerequisite: 2026-03-07-pt-monitor-trailing-stop-scenario-a.md
Design: docs/planning/trailing-stop-design.md
```
