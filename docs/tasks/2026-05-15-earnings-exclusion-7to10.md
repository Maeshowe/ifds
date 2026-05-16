# Task: earnings_exclusion_days 7 → 10 (config + dokumentáció)

**Status:** DONE
**Priority:** P1 (Fázis 1 előkészítés)
**Created:** 2026-05-15 (Chat által írás, pre-Fázis 1 deploy)
**Updated:** 2026-05-16
**Deploy:** 2026-05-16 (CC Ülés A, Fázis 1 W21 close)
**Owner:** Claude Code
**Estimated effort:** ~20–30 min (config + tests + docs)

**Source decision:** [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) §3.10 — Döntés [10]: "Earnings exclusion → 10 nap előretekintés (hold × 2)".

**Depends on:** nincs

**Related task:** [`2026-05-15-sec-10q-exclusion.md`](2026-05-15-sec-10q-exclusion.md) — a 10-Q SEC filing exclusion integráció (külön task, mert új API integráció, 2-3h scope). **A két task FÜGGETLEN** — a 7→10 váltás önmagában is értékes védelem.

---

## 1. A változás

```python
# src/ifds/config/defaults.py TUNING["earnings_exclusion_days"]

# ELŐTTE
"earnings_exclusion_days": 7,   # Skip if earnings within 7 calendar days

# UTÁNA
"earnings_exclusion_days": 10,  # Skip if earnings within 10 calendar days
                                 # (swing hold × 2 buffer — Day 63 outcome §3.10)
```

## 2. Indoklás

Day 63 outcome §3.10 + mathematical doc 5.2:
- A swing pivot **5 napi maximum hold** (time-stop, [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) §3.8).
- Egy 5 napi hold közben egy earnings event **gap-kockázat** — a mental stop overnight gap-rezisztens, de a `-8% weekly cumulative` hard SL aktiválódhat.
- Hold × 2 buffer = 10 nap **előretekintés** garantálja, hogy a pozíció **teljes ideje earnings-free**.
- A 60 napi adat 3 dokumentált earnings-szűrő lyukat mutatott (DTE máj 1, AGNC máj 4, BUD máj 5) — az AGNC eset 10-Q event volt (külön task), de a DTE és BUD esetek **legalábbis részben** a 7-napos időablak rövidsége miatt csúsztak be.

## 3. Mikor deploy?

**DÖNTÉS (Tamás 2026-05-15): AZONNALI DEPLOY JÓVÁHAGYVA** — W21 D1 hétfő (máj 19), NEM Fázis 3-mal együtt. Indoklás:

| Szempont | Azonnali deploy | Fázis 3 deploy |
|---|---|---|
| Stricter (kevesebb pozíció) hatás | ~5–10% univerzum-csökkenés | ugyanannyi |
| A régi rendszer W21–W24 ~20 napi tovább fut → kevesebb earnings-bug instancia | ✅ + | ❌ — |
| Mérési zavar a Day 63 keret retroaktív összehasonlításában | minimális (Day 63 már lezárult) | nincs |
| Konzisztencia a 10-Q exclusion task-kal | együtt deploy-olható | együtt deploy-olható |

**Nettó:** azonnali deploy + Fázis 3-ban a 10-Q exclusion is bekerül = teljes védelem.

## 4. Fájl-szintű változások

### `src/ifds/config/defaults.py`

A `TUNING["earnings_exclusion_days"]: 7` → `10`. (A `swing_management.earnings_exit_days: 1` **NEM** érintve — az egy másik paraméter, az exit logika része, nem az universe filter.)

### Tesztek

`tests/test_universe_earnings_exclusion.py` (vagy ahol a Phase 2 earnings szűrés tesztelve van):

```python
def test_earnings_within_10_days_excluded():
    """Earnings 9 napon belül → kizárás (új küszöb)."""
    ticker = make_ticker(next_earnings_in_days=9)
    universe = build_universe([ticker], earnings_exclusion_days=10)
    assert ticker.symbol not in universe

def test_earnings_at_exactly_10_days_excluded():
    """Earnings pontosan 10 napra → kizárás (inclusive küszöb)."""
    ticker = make_ticker(next_earnings_in_days=10)
    universe = build_universe([ticker], earnings_exclusion_days=10)
    assert ticker.symbol not in universe

def test_earnings_at_11_days_included():
    """Earnings 11 napra → marad."""
    ticker = make_ticker(next_earnings_in_days=11)
    universe = build_universe([ticker], earnings_exclusion_days=10)
    assert ticker.symbol in universe
```

Ha létezik a régi 7-napi teszt (`test_earnings_within_7_days_excluded`), át kell írni 10-re (vagy paramétrizált tesztet csinálni a kettőre).

### Dokumentáció

Ha létezik `docs/PARAMETERS.md` és/vagy `docs/PIPELINE_LOGIC.md` (a 2026-02-26-i `earnings_exclusion_days 5→7` task ezeket frissítette), itt is frissítendők ugyanazon a 7 → 10 mintán.

## 5. Validáció (Tamás közreműködésével)

A deploy után a következő Phase 2 cron futás (22:00 CEST) log-jában ellenőrizendő:

```bash
# Mac Mini-n
grep -E "earnings_exclusion|earnings.*exclud" logs/cron_phase123_$(date +%Y%m%d)*.log
```

**Várt finding:** az "excluded due to earnings" count emelkedjen ~30–50%-kal (a 7-napi ablak ~7-10 tickert szűr ki, a 10-napi ~10-15-öt — becslés a 60 napi átlagból).

Ha a universe size **drasztikusan** csökken (pl. 50%+), az gyanús → root cause analysis.

## 6. Commit message

```
config(universe): earnings_exclusion_days 7 → 10 for swing hold × 2 buffer

Day 63 outcome §3.10: swing 5-day max hold requires 10-day earnings
exclusion window (hold × 2) to guarantee earnings-free position lifetime.

The 60-day sample showed 3 earnings event leaks (DTE 2026-05-01,
AGNC 2026-05-04, BUD 2026-05-05). This change addresses the leaks
that came from the 7-day window being shorter than swing hold length.
AGNC was a 10-Q filing event (not earnings release) — handled by the
separate sec-10q-exclusion task.

Tests updated: 3 cases (9d, 10d, 11d).
Docs updated: PARAMETERS.md (if exists), PIPELINE_LOGIC.md (if exists).

Refs: docs/decisions/2026-05-14-day63-decision-outcome.md §3.10
```

## 7. Out of scope (explicit)

- **10-Q SEC filing exclusion** — külön task ([`2026-05-15-sec-10q-exclusion.md`](2026-05-15-sec-10q-exclusion.md))
- **ADR earnings adatforrás fix** — Fázis 3, [`04-risks 3.1`](../master-reference/04-risks-and-open-questions.md)
- **earnings_exit_days változtatása** — a swing exit logika része, az új scoring spec dokumentumban (Fázis 2) tervezett

## Kapcsolódó

- `src/ifds/config/defaults.py` TUNING `earnings_exclusion_days`
- `docs/decisions/2026-05-14-day63-decision-outcome.md` §3.10 (Decision 10)
- `docs/tasks/2026-02-26-earnings-exclusion-days-doc-fix.md` (előzmény: 5 → 7 váltás)
- `docs/master-reference/04-risks-and-open-questions.md` §1.2 (10-Q exclusion P1)
