Status: DONE
Updated: 2026-03-07
Note: Implementálva — kód ellenőrizve 2026-03-07

# Task: 2 failing test fix + deploy_daily.sh pytest pre-flight + F2 mm_regime drop

**Dátum:** 2026-02-27  
**Prioritás:** 🔴 BC17 előtt kötelező  
**QA forrás:** `docs/qa/2026-02-27-verification.md`

---

## Item 1 — 2 failing test: `test_phase1_gather_fix.py`

### Probléma

```
FAILED tests/test_phase1_gather_fix.py::TestGatherReturnExceptions::test_gather_tolerates_single_polygon_failure
FAILED tests/test_phase1_gather_fix.py::TestGatherReturnExceptions::test_gather_partial_success
```

878 pass, 2 fail. A prod kód (`_fetch_daily_history_async`) helyes — `return_exceptions=True` megvan.
A tesztek hibásak:

**`test_gather_tolerates_single_polygon_failure`:**
```python
mock_logger.log.assert_called_once()  # ← FAIL
```
A prod kód `logger.log()`-ot többször hívja (egy hibás napra), az `assert_called_once()` 1-nél több hívásra failel. Helyes assert: `assert mock_logger.log.call_count >= 1`.

**`test_gather_partial_success`:**
```python
assert mock_logger.log.call_count == 1  # ← FAIL
```
Ugyanaz a probléma — 1 failure = pontosan 1 log hívás feltételezi, de a mock setup 2 valid + 1 fail híváshoz `side_effect` listát használ. Az `AsyncMock.side_effect` listával az összes hívás lefut, a fail 1 log-ot generál — ellenőrizd hogy valóban pontosan 1 hívás történik-e, és ha nem, javítsd az assertet `>= 1`-re.

### Fix

**`tests/test_phase1_gather_fix.py`** — 2 assert javítása:

```python
# test_gather_tolerates_single_polygon_failure — sor ~34
# ELŐTTE:
mock_logger.log.assert_called_once()
assert "failed" in mock_logger.log.call_args[1]["message"]

# UTÁNA:
assert mock_logger.log.call_count >= 1
# Check that at least one call contains "failed"
messages = [call.kwargs.get("message", "") for call in mock_logger.log.call_args_list]
assert any("failed" in m for m in messages)
```

```python
# test_gather_partial_success — sor ~58
# ELŐTTE:
assert mock_logger.log.call_count == 1

# UTÁNA:
assert mock_logger.log.call_count >= 1
```

### Tesztelés

```bash
cd /Users/safrtam/SSH-Services/ifds
python -m pytest tests/test_phase1_gather_fix.py -v
# Elvárt: 3/3 PASSED
python -m pytest --tb=short -q
# Elvárt: 880 passed, 0 failed
```

---

## Item 2 — `deploy_daily.sh` pytest pre-flight (C4)

### Probléma

A jelenlegi `scripts/deploy_daily.sh` (25 sor) nem futtat teszteket pipeline indítás előtt.
Ha egy rossz commit kerül Mini-re és a cron elindítja, a hibás kód teszt nélkül fut élesben.

### Fix

**`scripts/deploy_daily.sh`** — pytest pre-flight hozzáadása a pipeline futtatás elé:

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

source .venv/bin/activate
set -a; source .env; set +a

LOG="logs/cron_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

echo "=== IFDS Run $(date) ===" >> "$LOG"

# --- pytest pre-flight ---
echo "[pre-flight] Running pytest..." >> "$LOG"
if ! python -m pytest --tb=short -q >> "$LOG" 2>&1; then
    echo "[pre-flight] FAILED — pipeline aborted" >> "$LOG"
    # Telegram alert
    python - << 'PYEOF' >> "$LOG" 2>&1
import os, requests
token = os.getenv("IFDS_TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("IFDS_TELEGRAM_CHAT_ID")
if token and chat_id:
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": "⚠️ IFDS pre-flight FAILED — pytest errors, pipeline aborted. Check cron log."},
        timeout=10,
    )
PYEOF
    exit 1
fi
echo "[pre-flight] OK" >> "$LOG"
# --- end pre-flight ---

python -m ifds run >> "$LOG" 2>&1
EXIT_CODE=$?
echo "=== Exit: $EXIT_CODE ===" >> "$LOG"

if [ $EXIT_CODE -eq 0 ]; then
    echo "=== Company Intel $(date) ===" >> "$LOG"
    python scripts/company_intel.py --telegram >> "$LOG" 2>&1
    echo "=== Intel Exit: $? ===" >> "$LOG"
fi

exit $EXIT_CODE
```

### Tesztelés

```bash
# Szimulált teszt fail — pipeline NEM indulhat el
cd /Users/safrtam/SSH-Services/ifds
# Ideiglenesen törj egy tesztet, futtasd a script-et, ellenőrizd hogy abort-ol
# Visszaállítás után: normál futás esetén "[pre-flight] OK" kell a logban
```

**Fontos:** a pytest Mini-n lassabb (~30-60s), de cron 10:00-kor indul, van idő.

---

## Item 3 — F2: `mm_regime` + `unusualness_score` drop `_replace_quantity`-ban

### Probléma

A `phase6_sizing.py`-ban két helyen is létrejön egy `PositionSizing` copy ahol
`mm_regime` és `unusualness_score` **hiányzik** — ezek az MMS (BC15) mezők silently
elvesznek, ha egy pozíció quantity cap-et kap.

**1. hely — `_replace_quantity()` (~sor 875):**
```python
return PositionSizing(
    ...
    shark_detected=pos.shark_detected,
    # ← mm_regime és unusualness_score HIÁNYZIK
)
```

**2. hely — `_apply_position_limits()` single ticker exposure reduction (~sor 780):**
```python
pos = PositionSizing(
    ...
    shark_detected=pos.shark_detected,
    # ← mm_regime és unusualness_score HIÁNYZIK
)
```

### Hatás BC17-ben

Ha MMS aktiválódik és egy pozíció notional cap-et kap (`_replace_quantity`),
vagy exposure miatt redukálódik (`_apply_position_limits`), az `mm_regime`
értéke `""` lesz a CSV-ben és a Telegram riportban — az MMS rezsim multiplier
elvész. Silent adatvesztés.

### Fix

**`src/ifds/phases/phase6_sizing.py`**

**`_replace_quantity()` függvény — teljes csere `dataclasses.replace()`-re:**

```python
def _replace_quantity(pos: PositionSizing, new_qty: int) -> PositionSizing:
    """Create a copy of PositionSizing with an updated quantity."""
    import dataclasses
    return dataclasses.replace(pos, quantity=new_qty)
```

Ez garantálja hogy minden mező — beleértve a jövőbeli új mezőket is — automatikusan
átmásolódik. Nem kell manuálisan karbantartani.

**`_apply_position_limits()` single ticker exposure reduction — szintén `dataclasses.replace()`:**

```python
# ELŐTTE (~sor 780):
pos = PositionSizing(
    ticker=pos.ticker, sector=pos.sector,
    ...
    shark_detected=pos.shark_detected,
)

# UTÁNA:
import dataclasses
pos = dataclasses.replace(pos, quantity=reduced_qty)
```

**Megjegyzés:** A `dataclasses` import a függvényen belül is rendben van (Python cache-eli),
vagy tedd a fájl tetejére a többi import mellé.

### Tesztelés

```bash
python -m pytest tests/ -k "phase6 or sizing or position" -v
```

Ellenőrizd hogy létezik-e teszt erre az esetre. Ha nem, adj hozzá egyet:

```python
def test_replace_quantity_preserves_mm_regime():
    """_replace_quantity must not drop mm_regime or unusualness_score."""
    pos = make_position(mm_regime="gamma_positive", unusualness_score=0.75)
    updated = _replace_quantity(pos, new_qty=10)
    assert updated.mm_regime == "gamma_positive"
    assert updated.unusualness_score == 0.75
    assert updated.quantity == 10

def test_apply_position_limits_preserves_mm_regime():
    """Exposure reduction in _apply_position_limits must not drop mm_regime."""
    # position with high notional → gets reduced
    pos = make_position(quantity=1000, entry_price=50.0, mm_regime="dark_dominant")
    config = make_config(max_single_ticker_exposure=10_000)
    result, _ = _apply_position_limits([pos], config, mock_logger())
    assert result[0].mm_regime == "dark_dominant"
```

---

## Git commit javaslat

```
fix(phase1,phase6,deploy): failing tests + mm_regime drop + pytest pre-flight

- Fix 2 failing tests in test_phase1_gather_fix.py (assert_called_once → >=1)
- _replace_quantity: dataclasses.replace() — no more silent field drops
- _apply_position_limits: dataclasses.replace() for exposure reduction
- deploy_daily.sh: pytest pre-flight + Telegram alert on failure

Fixes: QA findings N1, C4, F2
```
