Status: DONE
Updated: 2026-04-03
Note: P1 — az NYSE naptár hiánya leftover-t és felesleges futásokat okozhat

# NYSE Trading Calendar integráció — exchange_calendars package

## Kontextus

A rendszer jelenleg **nem ismeri az NYSE ünnepnapokat és early close napokat**. Csak a witching day-t kezeli (`utils/calendar.py`). Ez három problémát okoz:

1. **Ünnepnapokon a pipeline feleslegesen fut** — nincs piac, az orderek nem teljesülnek
2. **Early close napokon a close_positions.py túl későn fut** — a piac 13:00 ET-kor zár, de a MOC 15:40 ET-kor megy → leftover marad
3. **A pt_monitor.py Scenario B időzítése fix 19:00 CET** — early close napon ez 6 órával a zárás UTÁN

Konkrét példa: 2026-04-03 (Good Friday) — NYSE zárva, de a cron fut.

## Megoldás: exchange_calendars package

A `exchange_calendars` (vagy `pandas_market_calendars`) package az NYSE teljes naptárát tartalmazza: ünnepnapok, early close napok, speciális zárások. Nem kell karbantartani — a package fejlesztői frissítik.

**Előny a BC20A-hoz:** a Swing Hybrid Exit design-ban a hold day számoláshoz is ez a package kell. Ha most bevezetjük, a BC20A-nak nem kell újra implementálnia.

```bash
pip install exchange_calendars
```

## Implementáció

### 1. Bővítsd a `src/ifds/utils/calendar.py`-t

Új függvények a meglévő witching logika mellé:

- `is_trading_day(date)` — True ha NYSE nyitva (nem hétvége, nem ünnepnap)
- `is_early_close(date)` — True ha NYSE korábban zár (13:00 ET)
- `get_market_close_time_et(date)` — záróidő Eastern Time-ban (16:00 ET vagy 13:00 ET)
- `get_market_close_time_cet(date)` — záróidő CET/CEST-ben (crontab-hoz)
- `next_trading_day(date)` — következő kereskedési nap
- `trading_days_between(start, end)` — kereskedési napok száma két dátum között
- `get_holiday_name(date)` — ünnepnap neve (Telegram üzenetekhez)

Az `exchange_calendars` package-et használd (`xcals.get_calendar("XNYS")`). A witching logika marad a jelenlegi.

### 2. Pipeline guard — runner.py

Phase 0 ELEJÉN, a pytest pre-flight UTÁN:

```python
from ifds.utils.calendar import is_trading_day, get_holiday_name

if not is_trading_day(today):
    holiday = get_holiday_name(today)
    # Log + Telegram: "NYSE zárva, pipeline skip"
    sys.exit(0)
```

### 3. PT scriptek — is_trading_day guard

Minden PT script main() elején:
- `submit_orders.py`
- `pt_avwap.py`
- `pt_monitor.py`
- `close_positions.py`
- `eod_report.py`
- `monitor_positions.py`

```python
from ifds.utils.calendar import is_trading_day
if not is_trading_day():
    logger.info("Market closed today. Exiting.")
    sys.exit(0)
```

### 4. close_positions.py — early close kezelés

A close_positions.py-nek a MOC ordert a zárás ELŐTT kell elküldenie.

**A) Script ellenőrzés (a crontab marad fix):**
```python
from ifds.utils.calendar import is_early_close, get_market_close_time_cet

if is_early_close():
    close_cet = get_market_close_time_cet()
    now_cet = datetime.now(ZoneInfo("Europe/Budapest")).time()
    if now_cet > close_cet:
        logger.error(f"EARLY CLOSE DAY — market already closed at {close_cet}!")
        send_telegram(f"🔴 EARLY CLOSE — piac {close_cet}-kor zárt, MOC túl késő!")
        sys.exit(1)
```

**B) Extra crontab entry early close napokra:**
```crontab
# Early close days: MOC at 18:40 CET (12:40 ET)
40 18 * * 1-5 cd ~/SSH-Services/ifds && python3 -c "from ifds.utils.calendar import is_early_close; exit(0 if is_early_close() else 1)" && python3 scripts/paper_trading/close_positions.py >> logs/pt_close_$(date +\%Y-\%m-\%d).log 2>&1
```

**Javaslat:** A + B kombinálva. A korai crontab futtatja early close napokon, a normál crontab a rendes napokon. A script mindkét esetben ellenőrzi.

### 5. pt_monitor.py — Scenario B early close

A Scenario B jelenleg fix 19:00 CET-kor aktiválódik. Early close napon a zárás ~19:00 CET (~13:00 ET) → a Scenario B az early close ELŐTT kell fusson.

```python
from ifds.utils.calendar import is_early_close

if is_early_close():
    scenario_b_hour_utc = 16  # 12:00 ET = 16:00 UTC (1 óra zárás előtt)
else:
    scenario_b_hour_utc = get_scenario_b_hour_utc()  # jelenlegi logika
```

### 6. Earnings exclusion (opcionális javítás)

A Phase 2 earnings exclusion jelenleg 7 naptári napot használ. A `trading_days_between()` függvénnyel pontosabb lenne — 5 kereskedési napra szűrni. Ez opcionális, de pontosabb.

## Érintett fájlok

| Fájl | Változás |
|------|----------|
| `src/ifds/utils/calendar.py` | Bővítés: is_trading_day, is_early_close, get_market_close_time, stb. |
| `src/ifds/pipeline/runner.py` | Phase 0 elején trading day guard |
| `scripts/paper_trading/submit_orders.py` | is_trading_day guard |
| `scripts/paper_trading/pt_avwap.py` | is_trading_day guard |
| `scripts/paper_trading/pt_monitor.py` | is_trading_day guard + Scenario B early close |
| `scripts/paper_trading/close_positions.py` | is_trading_day guard + early close ellenőrzés |
| `scripts/paper_trading/eod_report.py` | is_trading_day guard |
| `scripts/paper_trading/monitor_positions.py` | is_trading_day guard |
| `requirements.txt` / `pyproject.toml` | `exchange_calendars` dependency |
| Crontab (Mac Mini) | Early close entry hozzáadása |

## Tesztelés

```python
# test_calendar.py
from ifds.utils.calendar import *
from datetime import date, time

# Holidays
assert not is_trading_day(date(2026, 4, 3))    # Good Friday
assert not is_trading_day(date(2026, 12, 25))   # Christmas
assert is_trading_day(date(2026, 4, 2))         # Normal Thursday

# Early close
assert is_early_close(date(2026, 11, 27))       # Day after Thanksgiving
assert is_early_close(date(2026, 12, 24))        # Christmas Eve
assert not is_early_close(date(2026, 4, 2))      # Normal day

# Close times
assert get_market_close_time_et(date(2026, 4, 2)) == time(16, 0)
assert get_market_close_time_et(date(2026, 11, 27)) == time(13, 0)
assert get_market_close_time_et(date(2026, 4, 3)) is None  # Holiday

# Next trading day
assert next_trading_day(date(2026, 4, 3)) == date(2026, 4, 6)  # Fri holiday → Mon

# Trading days between
assert trading_days_between(date(2026, 4, 1), date(2026, 4, 6)) == 2

# Weekend
assert not is_trading_day(date(2026, 4, 4))  # Saturday

# Witching (existing, must still work)
assert is_witching_day(date(2026, 3, 20))

# Holiday name
assert get_holiday_name(date(2026, 4, 3)) == "Good Friday"
assert get_holiday_name(date(2026, 4, 2)) is None
```

## Commit

```
feat(calendar): add NYSE trading calendar with exchange_calendars

Add is_trading_day(), is_early_close(), get_market_close_time_et/cet(),
next_trading_day(), trading_days_between() to utils/calendar.py using
the exchange_calendars package. All PT scripts and the pipeline runner
now skip execution on NYSE holidays. close_positions.py detects early
close days and adjusts MOC timing. pt_monitor.py Scenario B adjusts
activation time on early close days.
```
