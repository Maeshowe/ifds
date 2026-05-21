# Task: Sector Metric Clarity — Rename + Config Explicit + Reject Hotfix

Status: DONE
Updated: 2026-05-21
Note: Implementálva (~25 min CC, kvantitatív). daily_metrics.py rename `sector_max_pct` → `sector_observed_max_pct` + új explicit `sector_cap_pct` mező (config-tükör). sector-cap-hotfix.md REJECTED + CC audit szöveg appended. +1 regression test (`test_swing_state_includes_sector_cap_pct`). 1746 → 1747 passing, 0 regression.

**Priority:** P3 (meta-finding, NEM kód-bug — csak szemantikai tisztaság)
**Created:** 2026-05-21
**Owner:** Claude Code
**Estimated effort:** ~25 min CC

**Source**:
- A 2026-05-21 Log Review chat false positive incident (15% sector cap félreértelmezés)
- CC kvantitatív audit (4 forrás 30%-ra, 0 forrás 15%-ra)
- Day 1 (2026-05-19) Dev chat előzetes jelzése: "a `sector_max_pct: 15.0` egy DAILY METRIC, NEM CONFIG"

---

## 1. Háttér

A `daily_metrics_*.json` `swing_state.sector_max_pct` mező **observed daily max** sector concentration, NEM `defaults.py swing_sector_cap_pct` (30%) config cap. A két érték közeli (15.0 vs 30.0) és a mező-név félreérthető — Day 3 (2026-05-20) Log Review chat **false positive**-et eszkalált emiatt (`docs/tasks/2026-05-21-sector-cap-hotfix.md` task fájl javaslat, hibás 15% cap értékkel).

**Strukturális tanulság**: a workflow self-correction működött (Log Review hibás eszkaláció → Dev review → CC kvantitatív audit + reject), de **a félreérthető mezőnév strukturálisan ismétlődést okozhat**. A megoldás: explicit szemantikai szétválasztás.

## 2. Scope — két részfeladat

### 2.1. `sector-cap-hotfix.md` task REJECTED jelölés

**Fájl**: `docs/tasks/2026-05-21-sector-cap-hotfix.md`

**Módosítás**: a fájl tetején `Status: OPEN` → `Status: REJECTED — false positive`. Plus a fájl végére hozzáadni:

```markdown
---

## CC kvantitatív audit (2026-05-21)

**Eredmény**: REJECT — a task hipotézisek mind hibásak.

**Kód oldal**: a `_select_swing_entries` (`phase6_sizing.py:1297-1378`) HELYESEN iterál `open_positions`-en a `sector_notionals` számolásnál (line 1321-1325). A task §2 (A) hipotézis HAMIS — nem bug.

**Spec oldal — cap-érték forrás-audit**:

| Forrás | Cap érték |
|---|---|
| `defaults.py:342` | 0.30 (30%) |
| `docs/decisions/2026-05-14-day63-decision-outcome.md` §3.11 | 30% (4× explicit említés) |
| `docs/tasks/2026-05-17-swing-sizing-phase6.md` (eredeti spec) | 30% (11× explicit) |
| `docs/review/2026-05-20-daily-review.md` §0.6 | 15% ⚠️ (csak ITT, post-hoc) |
| `docs/tasks/2026-05-21-sector-cap-hotfix.md` (jelen task fájl) | 0.15 |

**A 15%-os cap-érték SEMMILYEN design/spec dokumentumban NEM létezik** — csak a Day 3 daily review §0.6-ban és a hotfix task fájlban (post-hoc).

**A `daily_metrics.swing_state.sector_max_pct: 20.63`** számított display érték (max sector arány a portfolioban), NEM config cap.

**Day 3 állapot**:
- Healthcare 20.63% ($20,626)
- Spec cap (30%): $30,000 → 20.63% < 30% → NINCS cap-megsértés
- Daily review feltételezett cap (15%): $15,000 → 20.63% > 15% → "megsértés" (téves)

**Strukturális tanulság**: a workflow self-correction működött (anomaly detection → Dev review → kvantitatív audit → reject). Permanent record szempontból ez a két-chat workflow első dokumentált false-positive-szűrési példája. Permanent record-ba érdemes mint **pattern-evidencia** a Day 90 milestone értékelésen.

**Follow-up**: a félreértés-forrás strukturális megelőzése a `2026-05-21-sector-metric-clarity.md` task-ban (jelen).

— CC, 2026-05-21
```

**Effort**: ~5 min CC.

### 2.2. `daily_metrics.py` szemantikai tisztaság

**Fájl**: `scripts/paper_trading/daily_metrics.py` (vagy ahol a `swing_state` JSON struktúra generálódik)

**Módosítás**: a `swing_state` blokkban a mezőnév átnevezése + új config-explicit mező hozzáadása:

```python
# JELENLEGI:
"swing_state": {
    # ...
    "sector_max_pct": compute_sector_max_observed_pct(state),  # félreérthető
    # ...
}

# ÚJ:
"swing_state": {
    # ...
    "sector_observed_max_pct": compute_sector_max_observed_pct(state),  # observed daily max
    "sector_cap_pct": config.get("swing_sector_cap_pct") * 100,         # config cap (explicit)
    # ...
}
```

A `sector_cap_pct: 30.0` mező **explicit a defaults.py-ből származó cap érték**, így a JSON olvasója (Log Review chat vagy bármi/aki) **NEM tud félreérteni**.

**Hatás**: Day 4+ (2026-05-22 péntek-től) `daily_metrics_*.json` minden olvasója látja:
- `sector_observed_max_pct: 20.63` (mai max)
- `sector_cap_pct: 30.0` (config cap)
- Egyértelmű: 20.63 < 30 → no violation

**Effort**: ~15 min CC + 1-2 unit teszt.

## 3. Implementáció lépésekben

1. **`sector-cap-hotfix.md` REJECT** (5 min) — `Status` átírás + CC audit szöveg hozzáadása
2. **`daily_metrics.py` rename** (5 min) — `sector_max_pct` → `sector_observed_max_pct`
3. **Új `sector_cap_pct` mező hozzáadása** (5 min) — `config["swing_sector_cap_pct"] * 100`
4. **Tesztek update + új** (5 min):
   - Régi tesztek a `sector_max_pct` referencia átírva `sector_observed_max_pct`-re (~2-3 teszt)
   - Új teszt: `test_daily_metrics_includes_sector_cap_pct` — a config cap explicit jelen van
5. **Commit + push** (3 min)

**Összesen**: ~25 min CC.

## 4. Commit message

```
chore(metrics): sector cap semantic clarity — rename + explicit config + reject false-positive task

Day 3 (2026-05-20) Log Review chat false-positive incident:
sector_max_pct (observed daily max) mistakenly interpreted as
config cap (30% per defaults.py + Day 63 outcome §3.11).
CC kvantitatív audit rejected the proposed "hotfix" — no bug exists.

Structural prevention:
1. daily_metrics.py: rename sector_max_pct → sector_observed_max_pct
2. daily_metrics.py: add sector_cap_pct = swing_sector_cap_pct * 100
3. docs/tasks/2026-05-21-sector-cap-hotfix.md: REJECTED status +
   CC quantitative audit appended (permanent record).

Tests: ~2 updated + 1 new (test_daily_metrics_includes_sector_cap_pct).

Refs: docs/tasks/2026-05-21-sector-cap-hotfix.md (REJECTED)
      docs/tasks/2026-05-21-sector-metric-clarity.md (this task)
      docs/decisions/2026-05-14-day63-decision-outcome.md §3.11
```

## 5. Out of scope

- A `04-risks` `§9` ÚJ szakasz (meta-finding-ek) — Dev chat scope, holnap reggel
- A "Production path env var" Fázis 4 backlog (§8.2.5) — külön task

## 6. Kapcsolódó

- `docs/tasks/2026-05-21-sector-cap-hotfix.md` (REJECTED jelölés célja)
- `scripts/paper_trading/daily_metrics.py` (rename + új mező)
- `src/ifds/config/defaults.py:342` (`swing_sector_cap_pct: 0.30`)
- `docs/decisions/2026-05-14-day63-decision-outcome.md` §3.11 (30% cap eredeti döntés)
- `docs/master-reference/04-risks-and-open-questions.md` (jövőbeli §9 meta-finding szakaszhoz hivatkozás)
