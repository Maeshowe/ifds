---
Status: DONE
Updated: 2026-03-21
Note: Implemented — calendar.py + submit_orders.py witching check + 10 tests
---

# Feature: Quadruple Witching naptár — kereskedési kizárás

## Döntés

Quadruple/Triple Witching napokon az IFDS **nem kereskedik** — a pipeline
lefut (diagnosztika, MMS gyűjtés folytatódik), de a `submit_orders.py`
circuit breaker analógiájára `sys.exit(0)`-val leáll order submission előtt.

**Indok:** 4 nap/év (~1.9% of trading days) — elhanyagolható opportunity cost.
A Witching napi volatilitás nem irányított (nem edge), hanem noise — különösen
veszélyes a magas IV, analyst target felett kereskedő részvényeknél.

**Megfigyelt eset:** 2026-03-20 (Witching nap) — VICR −$440 nettó SL hit,
UCTT −$234 nettó, CVX late fill leftover. Kumulatív hatás: −$820 nettó,
cumulative P&L +$20-ra esett vissza.

---

## Witching naptár

Minden évben: **március, június, szeptember, december harmadik pénteke.**

### 2026
```python
WITCHING_DATES_2026 = {
    date(2026, 3, 20),   # március 20.
    date(2026, 6, 19),   # június 19.
    date(2026, 9, 18),   # szeptember 18.
    date(2026, 12, 18),  # december 18.
}
```

### Automatikus számítás (évenkénti hardcode helyett)

```python
def get_witching_dates(year: int) -> set[date]:
    """Return Triple/Quadruple Witching dates for a given year.
    
    Third Friday of March, June, September, December.
    """
    witching_months = [3, 6, 9, 12]
    dates = set()
    for month in witching_months:
        # Find third Friday: iterate days 15-21, pick the Friday
        for day in range(15, 22):
            d = date(year, month, day)
            if d.weekday() == 4:  # Friday = 4
                dates.add(d)
                break
    return dates
```

---

## Implementáció

### `submit_orders.py` — Witching check

A circuit breaker check után, order submission előtt:

```python
from ifds.utils.calendar import is_witching_day

# --- Witching day check ---
if is_witching_day(date.today()):
    msg = (
        f"📅 WITCHING DAY — order submission SKIPPED.\n"
        f"{date.today()} is a Triple/Quadruple Witching day.\n"
        f"Pipeline ran normally. No orders submitted."
    )
    logger.warning(msg)
    send_telegram(msg)
    sys.exit(0)
```

### `src/ifds/utils/calendar.py` — új modul

```python
"""IFDS Trading Calendar — special market days."""
from datetime import date


def get_witching_dates(year: int) -> set[date]:
    """Return Triple/Quadruple Witching dates for a given year.
    Third Friday of March, June, September, December.
    """
    witching_months = [3, 6, 9, 12]
    dates = set()
    for month in witching_months:
        for day in range(15, 22):
            d = date(year, month, day)
            if d.weekday() == 4:  # Friday
                dates.add(d)
                break
    return dates


def is_witching_day(d: date | None = None) -> bool:
    """Return True if date is a Triple/Quadruple Witching day."""
    if d is None:
        d = date.today()
    return d in get_witching_dates(d.year)
```

### `--override-witching` flag (opcionális)

A circuit breakerhez hasonlóan, override flag is lehetséges ha szükséges:

```python
parser.add_argument('--override-witching', action='store_true',
                    help='Submit orders on Witching day (use with caution)')
```

---

## Pipeline futás Witching napokon

A pipeline teljes egészében lefut (Phase 0–6), csak az order submission áll le.

| Komponens | Witching napon |
|---|---|
| Pipeline (Phase 0–6) | ✅ Fut — diagnosztika, scoring, MMS gyűjtés |
| Company Intel | ✅ Fut |
| `submit_orders.py` | ❌ Skip — Telegram alert, sys.exit(0) |
| `pt_monitor.py` | ❌ Nem indul (nincs pozíció) |
| `pt_avwap.py` | ❌ Nem indul (nincs pozíció) |
| `close_positions.py` | ✅ Fut (ha véletlenül van nyitott pozíció) |
| `eod_report.py` | ✅ Fut |

---

## Jövőbeli kiterjesztés (opcionális, nem most)

Ha a witching nap körüli heteket is figyelni szeretnénk:

```python
def is_witching_week(d: date | None = None) -> bool:
    """Return True if date is in a Witching week (Mon-Fri of Witching Friday)."""
    if d is None:
        d = date.today()
    witching_dates = get_witching_dates(d.year)
    for wd in witching_dates:
        week_start = wd - timedelta(days=4)  # Monday
        if week_start <= d <= wd:
            return True
    return False
```

A backtestek alapján dönthetünk hogy a hét elejét is kizárjuk-e.

---

## Tesztelés

1. Unit: `get_witching_dates(2026)` → `{date(2026,3,20), date(2026,6,19), ...}`
2. Unit: `get_witching_dates(2027)` → helyes dátumok
3. Unit: `is_witching_day(date(2026, 3, 20))` → `True`
4. Unit: `is_witching_day(date(2026, 3, 21))` → `False`
5. Integration: `submit_orders.py` Witching napon → sys.exit(0) + Telegram
6. Meglévő tesztek: 957 passing — regresszió

---

## Commit üzenet

```
feat(calendar): add witching day detection and order submission skip

Triple/Quadruple Witching days (3rd Friday of Mar/Jun/Sep/Dec) are
excluded from order submission due to elevated volatility and noise.

Pipeline runs normally for diagnostics and MMS collection.
submit_orders.py exits with sys.exit(0) and sends Telegram alert.

New module: src/ifds/utils/calendar.py
Observed cost: 2026-03-20 Witching day — VICR/UCTT SL hit, -$820 nettó.
```

---

## Érintett fájlok

- **`src/ifds/utils/calendar.py`** — új modul, `get_witching_dates()` + `is_witching_day()`
- **`scripts/paper_trading/submit_orders.py`** — Witching check + `--override-witching` flag
- **`tests/utils/test_calendar.py`** — új tesztek

---

## Prioritás

**Medium** — BC18 scope kandidáns. Egyszerű implementáció (~2 óra CC),
és megakadályozza a következő Witching napi (2026-06-19) order submissiont.
```
