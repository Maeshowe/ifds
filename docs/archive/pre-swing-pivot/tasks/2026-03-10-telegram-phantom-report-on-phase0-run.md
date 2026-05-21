# Fix: Telegram phantom report on `ifds run --phase 0` / `ifds check`

Status: DONE
Updated: 2026-03-10

---

## Probléma

Ha a pipeline `--phase 0` flaggel fut (vagy `ifds check` → `run_pipeline(phase=0, dry_run=False)`),
a `runner.py` végén a `send_daily_report` **feltétel nélkül meghívódik**, és egy üres,
félkész Telegram reportot küld ki:

```
📊 IFDS Daily Report — 2026-03-02
[ 0/6 ] System Diagnostics
Pipeline: ✅ OK (0.0s)
Macro: VIX=18.00 (normal)  TNX=4.20%  Rate-sensitive=False
[ 1/6 ] Market Regime (BMI)
[ 2/6 ] Universe Building
...
```

Phase 1–6 üres, duration=0.0s, VIX a cache-elt értéket mutatja.

### Mikor fordul elő

- `python -m ifds run --phase 0` manuális futtatásakor (pl. debug közben)
- `ifds check` CLI parancs esetén **NEM** (az `dry_run=True` → early return, Telegram nem fut)
- Márc 2-án dokumentálva: a `10:21`-es futás (`cron_20260302_102137.log`) ilyen
  `--phase 0` futást végzett debug közben → phantom report ment ki Telegramra 10:22-kor

### Bizonyíték (Telegram history)

```
10:22  [ 6/6 ] Position Sizing          ← előző futás part2 vége
10:22  ⚠️ IFDS pre-flight FAILED        ← 10:08-as futás alert
10:33  📊 IFDS Daily Report VIX=18.00   ← 10:21-es --phase 0 phantom report  ← BUG
10:35  📊 IFDS Daily Report VIX=23.58   ← 10:33-as valódi pipeline report ✅
```

---

## Root Cause

`runner.py` végén a Telegram küldés **nincs feltételhez kötve**:

```python
# runner.py — jelenlegi állapot (BUG)
duration = time.monotonic() - pipeline_t0

# Telegram — single unified daily report
try:
    from ifds.output.telegram import send_daily_report
    ...
    send_daily_report(ctx, config, logger, duration, fmp=fmp_tg)  # ← mindig fut
except Exception as e:
    ...
```

Ha `phase=0` és `dry_run=False`:
- Phase 0 lefut → `ctx.macro` feltöltve (VIX érték)
- Phase 1–6 skip → `ctx.phase1..6 = None`
- `duration ≈ 0.0s`
- `send_daily_report` elküldi az üres reportot ✗

---

## Fix

`runner.py`-ban a Telegram küldést csak akkor engedjük meg, ha **a teljes pipeline lefutott**
(nem phase-only, nem dry_run):

```python
# runner.py — javított verzió
# Telegram — csak teljes pipeline futás esetén
if phase is None and not dry_run:
    try:
        from ifds.output.telegram import send_daily_report
        from ifds.data.fmp import FMPClient as FMPTelegram
        fmp_tg = FMPTelegram(
            api_key=config.get_api_key("fmp"),
            timeout=config.runtime["api_timeout_fmp"],
            max_retries=config.runtime["api_max_retries"],
            cache=cache,
            circuit_breaker=cb_fmp,
        )
        try:
            send_daily_report(ctx, config, logger, duration, fmp=fmp_tg)
        finally:
            fmp_tg.close()
    except Exception as e:
        logger.log(EventType.CONFIG_WARNING, Severity.WARNING,
                   message=f"Telegram error: {e}")
```

**Érintett fájl:** `src/ifds/pipeline/runner.py`

A Telegram blokk a `run_pipeline` függvény végén található, közvetlenül a
`print_pipeline_result` hívás után.

---

## Tesztelés

```bash
# 1. Phase-only futás → NEM küld Telegramot
python -m ifds run --phase 0
# → Telegram: semmi

# 2. check → NEM küld (dry_run=True early return, ez már most is OK)
python -m ifds check
# → Telegram: semmi

# 3. Teljes futás → küld
python -m ifds run
# → Telegram: 📊 IFDS Daily Report teljes tartalommal

# 4. Unit test: mock send_daily_report
# Ellenőrizd hogy phase=0 esetén NEM hívódik meg
```

Meglévő tesztek: nem kell új teszt feltétlenül, de ha van `test_runner.py` vagy
`test_telegram.py`, egészítsd ki egy `phase=0` esettel hogy `send_daily_report`
nem hívódik meg.

---

## Git commit üzenet

```
fix(runner): suppress Telegram report on --phase 0 / partial runs

send_daily_report was called unconditionally at the end of run_pipeline,
causing phantom reports with empty Phase 1-6 and duration=0.0s whenever
`ifds run --phase 0` was executed manually (e.g. during debugging).

Guard the Telegram block with `if phase is None and not dry_run` so it
only fires on full pipeline runs.

Fixes phantom report observed in Telegram on 2026-03-02 10:33 CET.
```
