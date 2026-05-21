Status: DONE
Updated: 2026-04-02
Note: Implemented — CET timestamps on all Telegram messages, shared helper

# Telegram üzenetek audit és javítás — teljes rendszer

## Probléma

A Telegram üzenetek jelenleg félrevezethetnek:
1. A BMI Momentum Guard "max 8→5" üzenetet küldött, de a Phase 6 mégis 8 pozíciót méretezett (a guard nem aktiválódott, az üzenet korábbi futásból jöhetett)
2. Az üzenetek nem tartalmaznak pipeline run_id-t vagy időbélyeget → nem lehet megkülönböztetni a friss és a régi üzeneteket
3. A PT scriptek (submit, monitor, close, eod) saját `send_telegram()` függvényt használnak — ezek sem tartalmaznak run kontextust

## Érintett Telegram küldő pontok

### Pipeline (runner.py + telegram.py)
1. **Daily Report** — `send_daily_report()` → `_format_phases_0_to_4()` + `_format_phases_5_to_6()` — VAN dátum header, DE nincs run_id, pipeline futás ideje
2. **BMI Momentum Guard** — runner.py ~431. sor — inline `_send_message()`, NINCS időbélyeg, NINCS hatás-megerősítés
3. **Skip Day Shadow** — runner.py ~458. sor — inline `_send_message()`, NINCS időbélyeg

### Paper Trading scriptek (scripts/paper_trading/)
4. **submit_orders.py** — witching day skip, circuit breaker, dry run summary, live submission summary — VAN dátum (`today_str`), DE nincs CET időbélyeg
5. **pt_monitor.py** — Scenario A trail aktiválás, Scenario B trail/loss exit — NINCS dátum/időbélyeg az üzenetben
6. **monitor_positions.py** — leftover warning — VAN dátum (`LEFTOVER POSITIONS — YYYY-MM-DD`), OK
7. **close_positions.py** — MOC summary — VAN dátum, DE nincs CET időbélyeg
8. **eod_report.py** — napi P&L, trade bontás, kumulatív — VAN dátum, OK
9. **pt_avwap.py** — AVWAP fill üzenetek — NINCS dátum/időbélyeg

## Javítási terv

### A) Minden Telegram üzenethez: időbélyeg + run kontextus

Minden `send_telegram()` hívás elé egységes header:
```
[YYYY-MM-DD HH:MM CET] SCRIPT_NAME
```

Példák:
- `[2026-04-02 10:02 CET] PIPELINE — BMI Momentum Guard aktív...`
- `[2026-04-02 15:35 CET] SUBMIT — 5 tickers submitted...`
- `[2026-04-02 19:20 CET] MONITOR — LOSS EXIT SOLS...`
- `[2026-04-02 21:40 CET] CLOSE — MOC 4 positions...`
- `[2026-04-02 22:05 CET] EOD — P&L today: -$8.96...`

### B) BMI Guard: hatás-megerősítés

A BMI Guard Telegram üzenet tartalmazzon tényleges hatást:
```
RÉGI:
⚠️ BMI MOMENTUM GUARD aktív
BMI 3+ napja csökken (delta=-1.3)
Max pozíciók: 8 → 5

ÚJ:
[2026-04-02 10:02 CET] PIPELINE
⚠️ BMI MOMENTUM GUARD aktív
BMI 3+ napja csökken (delta=-1.3)
Max pozíciók: 8 → 5
Phase 6 TÉNYLEGESEN 5 pozícióval fut ✅
```

Ha a guard NEM aktiválódik (delta nem éri el a küszöböt), NE küldjön Telegramot.

### C) pt_monitor.py: trail/loss exit üzenetek

```
RÉGI:
LOSS EXIT SOLS: Scenario B loss-making close
19:00 CET — position down -2.3%
Price: $73.33 < threshold: $73.53
SELL 36 shares at MKT

ÚJ:
[2026-04-02 19:20 CET] MONITOR
🔴 LOSS EXIT SOLS: Scenario B
Position down -2.3%
$73.33 < threshold $73.53
SELL 36 shares at MKT
```

### D) Közös helper függvény

Hozz létre egy közös Telegram helper-t amit minden script használ:

```python
# scripts/paper_trading/lib/telegram_helper.py
from datetime import datetime
import zoneinfo

def telegram_header(script_name: str) -> str:
    """Return standardized Telegram message header with CET timestamp."""
    cet = zoneinfo.ZoneInfo("Europe/Budapest")
    now = datetime.now(cet)
    return f"[{now.strftime('%Y-%m-%d %H:%M')} CET] {script_name}"
```

Minden script importálja és használja:
```python
from lib.telegram_helper import telegram_header
msg = f"{telegram_header('MONITOR')}\n🔴 LOSS EXIT {sym}..."
send_telegram(msg)
```

A pipeline telegram.py-ban is hasonlóan:
```python
# _format_phases_0_to_4 header-ben:
f"📊 <b>IFDS Daily Report</b> — {date.today().isoformat()} [{run_id}]"
```

## Érintett fájlok

1. `src/ifds/output/telegram.py` — daily report header + run_id
2. `src/ifds/pipeline/runner.py` — BMI guard + skip day shadow inline üzenetek
3. `scripts/paper_trading/lib/telegram_helper.py` — ÚJ: közös helper
4. `scripts/paper_trading/submit_orders.py` — header hozzáadás
5. `scripts/paper_trading/pt_monitor.py` — header hozzáadás
6. `scripts/paper_trading/close_positions.py` — header hozzáadás
7. `scripts/paper_trading/eod_report.py` — header hozzáadás (ha nincs)
8. `scripts/paper_trading/pt_avwap.py` — header hozzáadás

## Tesztelés

- Minden Telegram üzenet tartalmaz `[YYYY-MM-DD HH:MM CET]` header-t
- BMI Guard üzenet csak akkor megy, ha ténylegesen aktiválódik
- BMI Guard üzenet tartalmazza a tényleges Phase 6 hatást
- A CET/CEST váltás automatikus (zoneinfo)
- `pytest` all green

## Commit

```
feat(telegram): add timestamps and context to all Telegram messages

All Telegram messages now include [YYYY-MM-DD HH:MM CET] header and
source script name. BMI Guard message includes actual Phase 6 effect
confirmation. Shared telegram_helper.py provides consistent formatting
across pipeline and paper trading scripts.
```
