---
Status: DONE
Updated: 2026-03-28
Note: get_bmi_momentum_guard() phase6_sizing.py, runner.py guard+Telegram, 9 teszt.
Note: Phase 6 — BMI momentum guard. Ha BMI 3+ napja csökken és delta > -1.0 → max_positions csökkentés.
---

# BMI Momentum Guard — Csökkenő BMI Trend Védelem

## Probléma

A BMI YELLOW rezsim (25-80%) LONG stratégiát futtat, de nem veszi figyelembe
a BMI *irányát*. Az elmúlt 5 napon a BMI folyamatosan csökkent
(49.9 → 49.4 → 49.2 → 48.8 → 47.6), miközben a rendszer továbbra is
full LONG-ba ment 6-8 pozícióval. Az eredmény: 3 egymás utáni nagy vesztes nap
(-$472, -$459, -$421 = -$1,352 három nap alatt).

A BMI abszolút értéke (47.6%) még messze van a RED küszöbtől (80%), tehát
a rezsimváltás nem segít. Ami kell: a **trend irányának** figyelembe vétele
a pozíciószám meghatározásakor.

**Prioritás:** P1 — közvetlen drawdown csökkentés
**Becsült idő:** 1.5 óra

---

## Design

### BMI Momentum Guard logika

```python
def get_bmi_momentum_guard(
    bmi_history: list[dict],
    config: Config,
) -> int | None:
    """Check BMI momentum and return reduced max_positions if needed.
    
    Returns None if no reduction needed, otherwise the reduced max_positions.
    """
    min_days = config.tuning.get("bmi_momentum_days", 3)
    min_delta = config.tuning.get("bmi_momentum_min_delta", -1.0)
    reduced_positions = config.tuning.get("bmi_momentum_max_positions", 5)
    
    if len(bmi_history) < min_days + 1:
        return None  # Not enough history
    
    # Check last N days: is BMI declining every day?
    recent = bmi_history[-(min_days + 1):]  # +1 to compute N deltas
    
    consecutive_decline = 0
    total_delta = 0.0
    for i in range(1, len(recent)):
        delta = recent[i]["bmi"] - recent[i-1]["bmi"]
        if delta < 0:
            consecutive_decline += 1
            total_delta += delta
        else:
            consecutive_decline = 0
            total_delta = 0.0
    
    if consecutive_decline >= min_days and total_delta <= min_delta:
        return reduced_positions
    
    return None
```

### Hol fut

**Phase 6** — a `_apply_position_limits()` ELŐTT, a `max_positions` értéket
felülírjuk ha a guard aktiválódik.

```python
# runner.py — Phase 6 hívás előtt
from ifds.state.history import BMIHistory

bmi_hist = BMIHistory(state_dir=config.runtime.get("state_dir", "state"))
entries = bmi_hist.load()

if config.tuning.get("bmi_momentum_guard_enabled", True):
    reduced = get_bmi_momentum_guard(entries, config)
    if reduced is not None:
        logger.log(EventType.PHASE_DIAGNOSTIC, Severity.WARNING, phase=6,
                   message=f"[BMI GUARD] BMI declining {min_days}+ days "
                           f"(delta={total_delta:+.1f}) → max_positions: "
                           f"{config.runtime['max_positions']} → {reduced}")
        # Temporarily override max_positions
        original_max = config.runtime["max_positions"]
        config.runtime["max_positions"] = reduced
```

**Alternatíva:** A guard-ot közvetlenül Phase 6 `run_phase6()`-ban is meg
lehet hívni (kevesebb runner módosítás). A `bmi_history` state fájlt a
`BMIHistory.load()` metódussal olvasni — nincs extra API hívás, az adatok
a `state/bmi_history.json`-ban vannak.

---

## Config kulcsok

```python
# defaults.py TUNING
"bmi_momentum_guard_enabled": True,       # Feature flag
"bmi_momentum_days": 3,                    # Min consecutive declining days
"bmi_momentum_min_delta": -1.0,            # Min total BMI drop over period
"bmi_momentum_max_positions": 5,           # Reduced max positions (from 8)
```

### Küszöb indoklás

- **3 nap:** Elég hosszú, hogy ne reagáljon egynapos ingadozásra, de elég
  rövid, hogy a márc 25-27-i helyzetet elkapta volna (5 nap csökkenés)
- **-1.0 delta:** Az elmúlt hét átlagos napi BMI drop -0.46 volt, a
  3 napos kumulált drop -1.4 → ez a küszöb aktiválódott volna márc 25-re
- **5 pozíció:** 8-ról 5-re — 37% csökkentés. Nem állítja le a kereskedést,
  csak óvatosabb. A 3/szektor limit miatt ez 5 ticker max 2 szektorból.

### Visszaállás

Amikor a BMI emelkedni kezd (az utolsó napi delta pozitív), a guard
automatikusan deaktiválódik — a `consecutive_decline` nullázódik, a
`max_positions` visszaáll 8-ra. Nincs hisztérézis, nincs manuális reset.

---

## Telegram alert

```python
if reduced is not None:
    send_telegram(
        f"⚠️ BMI MOMENTUM GUARD aktív\n"
        f"BMI {min_days}+ napja csökken ({total_delta:+.1f})\n"
        f"Max pozíciók: {original_max} → {reduced}"
    )
```

---

## Példa — hogyan működött volna márc 23-27 között

| Dátum | BMI | Delta | Csökkenő napok | Guard aktív? | Max pos |
|-------|-----|-------|----------------|--------------|---------|
| 03-21 | 49.9 | — | 0 | Nem | 8 |
| 03-23 | 49.9 | 0.0 | 0 | Nem | 8 |
| 03-24 | 49.4 | -0.5 | 1 | Nem | 8 |
| 03-25 | 49.2 | -0.2 | 2 | Nem | 8 |
| 03-26 | 48.8 | -0.4 | 3 (sum: -1.1) | **Igen** | **5** |
| 03-27 | 47.6 | -1.2 | 4 (sum: -2.3) | **Igen** | **5** |

Márc 26-27-en 6 helyett max 5 pozíciót vett volna → ~20% kisebb exposure,
ami ~$270 kevesebb veszteség lett volna a két napon.

---

## NE csináljuk

- **Rezsim váltás** (YELLOW → piros jellegű) — a BMI momentum guard nem
  változtatja a stratégiát (LONG marad), csak a méretet csökkenti
- **BMI előrejelzés** — nem próbáljuk megjósolni a BMI-t, csak a trendet figyeljük
- **Automatikus SHORT váltás** — az BC21 Cross-Asset Regime scope
- **Hisztérézis** — ha a BMI emelkedni kezd, a guard azonnal feloldja. Nem
  várunk X napot az újra aktiválásig.

---

## Tesztelés

1. Unit: 3 nap csökkenés, delta=-1.5 → guard aktív, max_positions=5
2. Unit: 2 nap csökkenés → guard NEM aktív
3. Unit: 3 nap csökkenés, delta=-0.5 → guard NEM aktív (delta nem elég)
4. Unit: 4 nap csökkenés + 1 nap emelkedés → guard deaktiválódik
5. Unit: kevesebb mint 4 nap history → guard NEM aktív (insufficient data)
6. Unit: bmi_momentum_guard_enabled=False → guard nem fut
7. Integration: BMIHistory.load() → guard kiszámítása → Phase 6 max_positions override
8. Meglévő tesztek: 1034+ passing — regresszió

---

## Commit üzenet

```
feat(phase6): BMI momentum guard — reduce positions on declining trend

When BMI declines for 3+ consecutive days with cumulative delta <= -1.0,
reduce max_positions from 8 to 5 to limit exposure in deteriorating
market conditions.

Uses BMIHistory state (state/bmi_history.json), no extra API calls.
Auto-deactivates when BMI trend reverses.

Config: bmi_momentum_guard_enabled, bmi_momentum_days (3),
        bmi_momentum_min_delta (-1.0), bmi_momentum_max_positions (5).
```

---

## Érintett fájlok

- `src/ifds/phases/phase6_sizing.py` — `get_bmi_momentum_guard()` + max_positions override
- `src/ifds/state/history.py` — BMIHistory.load() (már létezik, nem kell módosítani)
- `src/ifds/config/defaults.py` — bmi_momentum config kulcsok
- `src/ifds/pipeline/runner.py` — guard hívás Phase 6 előtt + log + Telegram
- `docs/PARAMETERS.md` — frissítés
- `tests/test_bmi_momentum_guard.py` — új tesztek