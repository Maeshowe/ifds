Status: DONE
Updated: 2026-03-31
Note: Implemented — shadow log + Telegram alert + jsonl state, 9 tests

# Skip Day Shadow Guard — VIX+BMI combo

## Cél

Shadow módban logolni, ha a piaci feltételek alapján a rendszernek nem kellene kereskednie. Nem avatkozik be — a pipeline normálisan fut és kereskedik, de a logban és a Telegram reportban megjelenik, hogy "ha éles lenne, ma skip day lenne."

30 nap shadow adat után kiértékeljük: hány napot mentett volna, mekkora P&L különbséggel.

## Kontextus

Az utolsó 8 kereskedési napon (márc 20 — ápr 1) a BMI folyamatosan csökkent (49.9→45.9), VIX 30+ panic szintre ment, breadth 11/11 weakening volt. A rendszer mégis minden nap 4-5 LONG pozíciót nyitott és ~$1,850-t veszített. Egy "skip day" guard ezen napok nagy részét kihagyta volna.

## Aktiválási feltétel

```python
skip_day_shadow = (
    macro.vix_value >= vix_threshold          # default: 28
    AND bmi_consecutive_decline >= min_days    # default: 5
)
```

Config kulcsok (config.tuning):
- `skip_day_shadow_enabled`: bool, default True
- `skip_day_vix_threshold`: float, default 28.0
- `skip_day_bmi_decline_days`: int, default 5

## Implementáció

### 1. Új függvény: `phase6_sizing.py`

```python
def check_skip_day_shadow(
    macro: MacroRegime,
    bmi_history: list[dict],
    config: Config,
) -> tuple[bool, dict]:
    """Check if skip-day conditions are met (shadow mode only).
    
    Returns (would_skip, details_dict).
    """
    if not config.tuning.get("skip_day_shadow_enabled", True):
        return False, {}
    
    vix_threshold = config.tuning.get("skip_day_vix_threshold", 28.0)
    min_days = config.tuning.get("skip_day_bmi_decline_days", 5)
    
    vix_triggered = macro.vix_value >= vix_threshold
    
    # Count consecutive BMI decline days (reuse logic from get_bmi_momentum_guard)
    consecutive_decline = 0
    if len(bmi_history) >= 2:
        for i in range(len(bmi_history) - 1, 0, -1):
            if bmi_history[i]["bmi"] < bmi_history[i - 1]["bmi"]:
                consecutive_decline += 1
            else:
                break
    
    bmi_triggered = consecutive_decline >= min_days
    would_skip = vix_triggered and bmi_triggered
    
    details = {
        "vix_value": macro.vix_value,
        "vix_threshold": vix_threshold,
        "vix_triggered": vix_triggered,
        "bmi_consecutive_decline": consecutive_decline,
        "bmi_min_days": min_days,
        "bmi_triggered": bmi_triggered,
        "would_skip": would_skip,
    }
    return would_skip, details
```

### 2. Hívás: `runner.py` — Phase 6 előtt, a BMI Momentum Guard blokk után

```python
# Skip Day Shadow Guard — log only, does not block
from ifds.phases.phase6_sizing import check_skip_day_shadow
would_skip, skip_details = check_skip_day_shadow(ctx.macro, entries, config)
if would_skip:
    logger.log(EventType.PHASE_DIAGNOSTIC, Severity.WARNING, phase=6,
               message=f"[SKIP DAY SHADOW] Would skip today — "
                       f"VIX={skip_details['vix_value']:.1f} >= {skip_details['vix_threshold']}, "
                       f"BMI declining {skip_details['bmi_consecutive_decline']} days >= {skip_details['bmi_min_days']}",
               data=skip_details)
    # Telegram shadow alert
    try:
        from ifds.output.telegram import _send_message
        _token = config.runtime.get("telegram_bot_token")
        _chat = config.runtime.get("telegram_chat_id")
        if _token and _chat:
            _send_message(
                _token, _chat,
                f"👻 <b>SKIP DAY SHADOW</b> — ha éles lenne, ma 0 pozíció\n"
                f"VIX={skip_details['vix_value']:.1f} (küszöb: {skip_details['vix_threshold']})\n"
                f"BMI {skip_details['bmi_consecutive_decline']} napja csökken (küszöb: {skip_details['bmi_min_days']})",
                timeout=10,
            )
    except Exception:
        pass
# Pipeline continues normally — shadow does NOT block
```

### 3. Shadow log state fájl (kiértékeléshez)

Minden nap mentsd el: `state/skip_day_shadow.jsonl` (append)

```python
import json
shadow_file = config.runtime.get("skip_day_shadow_file", "state/skip_day_shadow.jsonl")
with open(shadow_file, "a") as f:
    f.write(json.dumps({
        "date": date.today().isoformat(),
        "would_skip": would_skip,
        **skip_details,
    }) + "\n")
```

30 nap után összehasonlítjuk: a skip day napok P&L-je vs a nem-skip napok P&L-je a cumulative_pnl.json-ból.

## Tesztelés

- Teszt: VIX >= 28 ÉS BMI 5+ napja csökken → would_skip=True
- Teszt: VIX >= 28 DE BMI nem csökken → would_skip=False
- Teszt: VIX < 28 ÉS BMI csökken → would_skip=False
- Teszt: shadow_enabled=False → would_skip=False
- Teszt: a pipeline továbbra is normálisan fut (shadow NEM blokkolja Phase 6-ot)
- `pytest` all green

## Commit

```
feat(phase6): add skip-day shadow guard for VIX+BMI combo

Shadow mode only — logs and sends Telegram alert when conditions
suggest skipping the trading day (VIX >= 28 AND BMI declining 5+
days), but does NOT block the pipeline. Saves daily state to
skip_day_shadow.jsonl for later evaluation.
```

## Kiértékelés (30 nap múlva, manuális)

```python
# Join skip_day_shadow.jsonl with cumulative_pnl.json
# Compare: sum(pnl where would_skip=True) vs total pnl
# Ha a skip napok P&L < -$X → érdemes élesíteni
```
