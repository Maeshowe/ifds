Status: DONE
Updated: 2026-03-07
Note: 33 task fájl fejlécezve (30 DONE, 3 OPEN)

# Task: Phase_00 — Task státusz fejlécek + CLAUDE.md Aktuális Kontextus frissítés

**Dátum:** 2026-03-07
**Prioritás:** 🔴 P0 — azonnal (hétfő márc 9 reggel)
**Érintett fájlok:** `docs/tasks/*.md` (6 fájl), `CLAUDE.md`

---

## Háttér

A 6 critical task implementálva van a kódban, de a task fájlokból
hiányzik a `Status: DONE` fejléc. A CLAUDE.md mostantól kötelezővé
teszi a státusz fejlécet minden task fájlban.

---

## Teendő 1 — Status fejlécek a lezárt task fájlokba

Az alábbi 6 task fájl **első 3 sorába** add be a fejlécet:

```
Status: DONE
Updated: 2026-03-07
Note: Implementálva — kód ellenőrizve 2026-03-07
```

**Érintett fájlok (mind DONE):**
- `docs/tasks/2026-02-25-moc-order-size-limit-fix.md`
- `docs/tasks/2026-02-26-circuit-breaker-halt.md`
- `docs/tasks/2026-02-26-eod-idempotency-guard.md`
- `docs/tasks/2026-02-26-phase1-asyncio-gather-fix.md`
- `docs/tasks/2026-03-05-eod-report-moc-orderref-fix.md`
- `docs/tasks/2026-03-05-close-positions-tp-sl-awareness.md`

## Teendő 2 — Status fejlécek a többi régi task fájlba

A `docs/tasks/` mappában lévő összes többi fájl is kapjon fejlécet.
Futtasd le, hogy meghatározd melyik DONE és melyik OPEN/WIP:

```bash
ls docs/tasks/*.md
```

Ökölszabály:
- 2026-02-18 … 2026-02-27 közötti fájlok → valószínűleg DONE
  (ezek BC17/18-prep, BC19, session-commit stb. feladatok)
- 2026-03-02-sim-l2-first-comparison-run.md → DONE (futtatva márc 2)
- 2026-03-05-* → DONE (implementálva, lásd Teendő 1)
- 2026-03-07-* → OPEN (trailing stop taskok, monitor)

Ha bizonytalan egy fájl státuszában, tedd `Status: DONE` és a Note-ba
`Note: Ellenőrizendő — feltételezetten kész`.

## Teendő 3 — Új task fájlok fejléce

A 2026-03-07-es trailing stop és monitor task fájlok már rendelkeznek-e
fejléccel? Ha nem, add hozzá:

```
Status: OPEN
Updated: 2026-03-07
Note: BC17/BC18 scope
```

Érintett fájlok:
- `docs/tasks/2026-03-07-monitor-positions-leftover-warning.md`
- `docs/tasks/2026-03-07-pt-monitor-trailing-stop-scenario-a.md`
- `docs/tasks/2026-03-07-pt-monitor-trailing-stop-scenario-b.md`

## Teendő 4 — CLAUDE.md Aktuális Kontextus frissítés

A `CLAUDE.md` alján az `## Aktuális Kontextus` szekciót frissítsd a
valós állapotra (teszt szám, utolsó commit hash):

```bash
python -m pytest tests/ -q 2>/dev/null | tail -1   # teszt szám
git log --oneline -1                                  # utolsó commit
```

---

## Tesztelés

```bash
# Ellenőrzés: minden task fájlnak van-e fejléce
grep -rL "^Status:" docs/tasks/*.md
# Üres output = minden fájlban van fejléc ✓

# Nyitott taskok listája
grep -rl "Status: OPEN\|Status: WIP" docs/tasks/
```

---

## Git commit

```
chore(docs): add Status headers to all task files, update CLAUDE.md

Add mandatory Status/Updated/Note headers to all docs/tasks/*.md files.
Mark 6 critical tasks as DONE (implementations verified in codebase):
- asyncio.gather return_exceptions (phase1_regime.py)
- EOD idempotency guard (eod_report.py)
- circuit breaker halt + --override flag (submit_orders.py)
- MOC order split >500 (close_positions.py)
- MOC orderRef='' fix (eod_report.py)
- TP/SL fill-aware MOC qty (close_positions.py)

Update CLAUDE.md: current status, task workflow rules,
docs update rules, BC structure.
```
