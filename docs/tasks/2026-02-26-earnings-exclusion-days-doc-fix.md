# Task: earnings_exclusion_days — dokumentáció javítás 5→7

**Date:** 2026-02-26
**Priority:** CRITICAL (doc sync) — félrevezető dokumentáció
**Source:** QA Audit `2026-02-26-doc-sync.md` Finding P1, PL1, XD1
**Scope:** `docs/PARAMETERS.md`, `docs/PIPELINE_LOGIC.md`

---

## A probléma

Az `earnings_exclusion_days` értéke a kódban (`defaults.py:103`) **7**, de a dokumentációban **5** szerepel — 3 helyen.

| Fájl | Sor | Jelenlegi érték | Helyes érték |
|---|---|---|---|
| `docs/PARAMETERS.md` | Universe Building szekció | `5` | `7` |
| `docs/PIPELINE_LOGIC.md` | ~274. sor | `earnings_exclusion_days=5` | `earnings_exclusion_days=7` |
| `docs/PIPELINE_LOGIC.md` | ~1487. sor | `kizár ha <5 napra earnings` | `kizár ha <7 napra earnings` |

`IDEA.md`-ben szintén 5 szerepel, de az historikus spec — nem kell módosítani.

---

## Fix

### PARAMETERS.md
```
# ELŐTTE
earnings_exclusion_days = 5

# UTÁNA
earnings_exclusion_days = 7
```

### PIPELINE_LOGIC.md — ~274. sor
```
# ELŐTTE
earnings_exclusion_days=5

# UTÁNA
earnings_exclusion_days=7
```

### PIPELINE_LOGIC.md — ~1487. sor
```
# ELŐTTE
kizár ha <5 napra earnings

# UTÁNA
kizár ha <7 napra earnings
```

---

## Git

```bash
git add docs/PARAMETERS.md docs/PIPELINE_LOGIC.md
git commit -m "docs: fix earnings_exclusion_days 5→7 in PARAMETERS.md and PIPELINE_LOGIC.md

Code (defaults.py:103) uses 7 since BC18-prep but docs still said 5.
3 occurrences fixed: PARAMETERS.md (1x), PIPELINE_LOGIC.md (2x).
IDEA.md intentionally not changed (historical spec).

QA Finding: 2026-02-26-doc-sync.md P1/PL1/XD1 [CRITICAL]"
git push
```
