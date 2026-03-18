# IFDS Journal — Trailing Stop Engine: Scenario A + B
**Dátum:** 2026-03-07
**BC:** BC17 — Phase_17C (Scenario A) + Phase_17D (Scenario B)
**Commitok:** `7df6a76` (Scenario A) + folyamatban (Scenario B)
**Tesztek:** 926 passing, 0 failure

---

## Háttér és motiváció

A paper trading fázis (Day 14/21) megmutatta, hogy a bracket order rendszer
önmagában nem védi meg a nyereséget a nap folyamán. Két konkrét probléma
indokolta a Trailing Stop Engine megépítését:

**Scenario A motivációja:**
TP1 fill után a Bracket B SL az eredeti stop szinten marad. Ha az ár TP1 után
visszafordul, a papíron már "nyertes" pozíció veszteséggel zárul. Nincs mechanizmus
ami a nyereséget megvédi TP1 és TP2 között.

**Scenario B motivációja (SDRL, 2026-03-06):**
Entry $43.70, TP1 $45.00 — az ár $44.20-ig ment (+$57.50 papíron), de TP1 nem
teljesült. MOC exit $41.97 → -$198.95 veszteség. Ha 19:00 CET-kor ($44.20) trail
SL aktiválódott volna ($41.41), a MOC-os zárás ennél nem lett volna rosszabb,
de a lefelé húzódó trail megvédte volna a nyereség egy részét.

---

## Architektúra

### State fájl: `monitor_state_YYYY-MM-DD.json`

A `pt_submit.py` hozza létre bracket submission után, tickerenként:

```json
{
  "AAPL": {
    "entry_price": 220.50,
    "total_qty": 45,
    "qty_b": 30,
    "sl_distance": 3.30,
    "tp1_price": 224.10,
    "tp2_price": 226.80,
    "tp1_filled": false,
    "trail_active": false,
    "trail_scope": null,
    "trail_sl_current": null,
    "trail_high": null,
    "scenario_b_activated": false,
    "scenario_b_eligible": true
  }
}
```

**Kulcs mezők:**
- `sl_distance` = `entry_price - original_sl_price` → trail távolság, végig konstans
- `trail_scope` = `"bracket_b"` (Scenario A) | `"full"` (Scenario B)
- `scenario_b_eligible` = False ha Scenario A már aktív

### `pt_monitor.py` — 5 percenként fut (09:00-19:55 UTC)
**clientId:** 15 (dedikált)
**Crontab:** `*/5 9-19 * * 1-5`

---

## Scenario A — TP1 fill → Bracket B trail

### Logika

```
TP1 fill detektálva (reqExecutions, orderRef=IFDS_{sym}_A_TP)
  → Bracket B SL cancel (IFDS_{sym}_B_SL)
  → Trail SL init: max(entry_price, current_price - sl_distance)  ← breakeven védelem
  → trail_scope = 'bracket_b', qty = qty_b
  → TP2 limit megmarad (természetes felső cap)
  → Telegram: "TARGET {sym}: Trail active (Scenario A)"
```

### Breakeven védelem
Trail SL aktiváláskor: `initial_sl = max(entry_price, current_price - sl_distance)`

Ha az ár TP1 fill után azonnal visszafordul, a trail SL **legalább entry áron** indul —
nem lehet veszteséges a Bracket B pozíció.

### OrderRef konvenció
Trail SL ütésekor: `IFDS_{sym}_B_TRAIL` — EOD report látja, MOC fallback nem ütközik.

---

## Scenario B — 19:00 CET időalapú, teljes pozíció

### Logika

```
19:00 CET (UTC-ban automatikus CET/CEST számítás)
  + current_price > entry_price * 1.005  ← +0.5% küszöb
  + Scenario A NEM aktív
  → cancel_all_sl_orders()  ← Bracket A SL + Bracket B SL mind cancel
  → Trail SL init: current_price - sl_distance
  → trail_scope = 'full', qty = total_qty
  → TP1 + TP2 limit orderek MEGMARADNAK
  → Telegram: "CLOCK {sym}: Trail active (Scenario B)"
```

### CEST váltás kezelése (2026-03-29)
```python
CET = ZoneInfo("Europe/Budapest")

def get_scenario_b_hour_utc() -> int:
    now_cet = datetime.now(CET)
    target_cet = now_cet.replace(hour=19, minute=0, second=0, microsecond=0)
    return target_cet.astimezone(ZoneInfo("UTC")).hour
# CET (téli): 18 UTC | CEST (nyári): 17 UTC — automatikus, nincs manuális módosítás
```

### +0.5% küszöb indoklása
Zajszűrés: ha az ár pontosan entry körül van 19:00-kor, ne aktiválódjon
véletlenszerűen. A küszöb aszimmetrikus — veszteséges napon nem aktivál,
csak akkor, ha van mit megvédeni.

### TP1/TP2 megmaradása
A teljes pozíció trail-el fut, de ha az ár mégis eléri TP1-et vagy TP2-t,
a limit orderek tölteni fognak. A monitor következő 5 perces futásán
a trail deaktiválódik (nincs mit trail-elni).

---

## A↔B interakció

| Időpont | Esemény | Eredmény |
|---------|---------|----------|
| 14:30 | TP1 fill | Scenario A aktív, `scenario_b_eligible=False` |
| 19:00 | Scenario B check | `scenario_b_eligible=False` → skip, A fut tovább |
| 14:30 előtt 19:00 | Scenario B check | A még nem aktív, B aktiválódik ha nyereséges |
| 19:00 után TP1 fill | TP1 fill | A aktiválódik, B már `scenario_b_activated=True` → nincs ütközés |

**Prioritás:** Scenario A mindig megelőzi B-t.

---

## Trail SL frissítés és ütés

Minden 5 perces futásban, ha `trail_active=True`:

```
new_sl = current_price - sl_distance
if new_sl > trail_sl_current:
    trail_sl_current = new_sl  ← csak felfelé mozog

if current_price <= trail_sl_current:
    SELL qty shares (scope-alapú)
    orderRef: IFDS_{sym}_TRAIL (full) | IFDS_{sym}_B_TRAIL (bracket_b)
    trail_active = False
```

**Scope-aware qty:**
- `bracket_b`: `qty_b` db (tipikusan 67% a pozícióból)
- `full`: `total_qty` db (100%)

---

## Telegram üzenetek

| Esemény | Prefix | Tartalom |
|---------|--------|----------|
| Scenario A aktiválás | `TARGET` | TP1 fill, trail SL, TP2 limit |
| Scenario B aktiválás | `CLOCK` | 19:00 CET, ár vs küszöb, trail SL |
| Trail SL ütés | `STOP` | Ár, SL szint, qty, orderRef |

---

## Tesztelés

**Scenario A tesztek** (`tests/paper_trading/test_pt_monitor.py`):
- TP1 fill detektálás, trail init, breakeven védelem
- Bracket B SL cancel, TP2 megmaradása
- Trail SL frissítés (csak felfelé)
- Trail SL ütés (qty_b, orderRef B_TRAIL)

**Scenario B tesztek** (`tests/paper_trading/test_pt_monitor_scenario_b.py`):
- Aktiválás 18:00 UTC-kor + nyereséges pozíció
- Nem aktivál 17:59 UTC előtt
- Nem aktivál ha ár ≤ entry * 1.005
- Nem aktivál ha Scenario A már aktív
- Full qty SELL, orderRef TRAIL
- TP1/TP2 limit orderek nem cancelálódnak
- Bracket A SL + Bracket B SL mindkettő cancelálva
- CEST váltás: CET vs CEST UTC óra
- Trail SL felfelé követi az árat
- Trail SL nem csökken

---

## Tanulságok

1. **State fájl mint egyetlen igazságforrás** — az IBKR order állapot és a
   monitor state szinkronban kell legyen. Az `sl_distance` konstans marad az
   egész nap folyamán, csak az aktuális ár változik.

2. **Breakeven védelem kritikus Scenario A-ban** — TP1 fill pillanatában az ár
   lehet nagyon közel az entry-hez (partial fill, gyors visszafordulás). A
   `max(entry_price, ...)` guard megakadályozza a negatív initial trail-t.

3. **CEST kezelés zoneinfo-val** — a crontab marad `*/5 9-19 * * 1-5` UTC-ben,
   de a 19:00 CET check automatikusan igazodik. Nincs manuális módosítás
   szükséges márc 29-én.

4. **cancel_all_sl_orders() vs cancel_bracket_b_sl()** — Scenario B-ben az
   összes SL-t canceljük (A + B bracket), mert a full trail átveszi a védelmet.
   Scenario A-ban csak a B bracket SL-t canceljük, az A bracket SL megmarad
   mint backup (TP1 fill esetén az A bracket már töltött, de a SL gyerek
   automatikusan is törlődik az OCA miatt).

---

## Következő lépések

- **Phase_18A** (BC18): EWMA smoothing + Crowdedness shadow mode
  - Design döntés szükséges: `docs/planning/crowdedness-decision-prep.md`
- **Phase_18B** (BC18): MMS factor volatility aktiválás (~márc 20, 21 nap baseline)
- **Paper Trading Day 15-21**: pt_monitor.py élesen fut, első trail aktiválások várhatók

---

## Commitok

| Commit | Phase | Tartalom |
|--------|-------|----------|
| `7df6a76` | Phase_17C | pt_monitor.py Scenario A + submit_orders.py state init |
| `00c943c` | Phase_17D | pt_monitor.py Scenario B + 10 új teszt, submit_orders.py 2 új mező |

**Tesztek:** 926 → 936 passing (+10), 0 failure
**BC17 státusz:** Phase_17A/B/C/D — mind ✅ DONE
