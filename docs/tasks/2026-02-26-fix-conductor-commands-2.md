# Fix: Maradék CONDUCTOR hivatkozások — 3 fix + 4 törlés

**Dátum:** 2026-02-26  
**Prioritás:** 🟡 BC17 előtt  
**Előzmény:** `f58e6c7` — 5 command javítva. Ez a maradék 7.

---

## Törlendő fájlok (4 db)

Ezek CONDUCTOR-specifikus infrastruktúrára épültek, natív CC-vel nincs értelmes megfelelőjük:

```bash
rm .claude/commands/build.md
rm .claude/commands/docs.md
rm .claude/commands/setup-env.md
rm .claude/commands/pause.md
```

**Indoklás:**
- `build.md` — a brief/build plan rendszer teljes egészében CONDUCTOR volt; a `docs/tasks/` workflow váltotta ki
- `docs.md` — a discovery mentés a `/learn`-be olvadt
- `setup-env.md` — `python -m conductor setup-env check` nem létező parancs, IFDS-ben nincs önálló környezet ellenőrzési igény
- `pause.md` — session state mentés, értelmét vesztette DB nélkül

---

## Javítandó fájlok (3 db)

### `/test` — `.claude/commands/test.md`

Tartsd meg a pytest futtatás logikát, távolítsd el a DB mentést.

**Elvárt viselkedés:**
```
1. Futtasd: python -m pytest --tb=short -q
2. Értelmezd az outputot:
   - total, passed, failed, errors, skipped, duration
3. Mutasd tömören:
   - Ha zöld: "N teszt zöld (X.Xs)"
   - Ha piros: "N teszt, F bukott. Bukott tesztek: [lista]"
4. Ha van failure → adj konkrét javítási javaslatot

NE futtasd: python -m conductor test save (törött)
NE olvasd: cat .conductor/agents/test.md (archívban van)
```

---

### `/review` — `.claude/commands/review.md`

Tartsd meg a code review workflow-t, távolítsd el a CONDUCTOR build plan betöltést és DB mentést.

**Elvárt viselkedés:**
```
1. Scope meghatározása $ARGUMENTS-ből:
   - Ha fájl/modul nevet tartalmaz → azt reviewzd
   - Ha üres → kérdezd meg: "Mit vizsgáljak?"

2. Review folyamat (változatlan):
   - Olvasd el az érintett fájlokat
   - Vizsgáld: helyesség, minták, tesztek, edge case-ek
   - Kategorizáld: CRITICAL | WARNING | INFO
   - Mutasd táblázatban

3. Verdikt: APPROVED | CHANGES_REQUESTED | REJECTED

4. Mentés helyett:
   Ha CHANGES_REQUESTED vagy CRITICAL találat van →
   írj task fájlt: docs/tasks/YYYY-MM-DD-review-findings.md
   tartalma: a táblázat + verdikt

NE futtasd: python -m conductor review create (törött)
NE olvasd: cat .conductor/agents/code-review.md (archívban van)
```

---

### `/refactor` — `.claude/commands/refactor.md`

Tartsd meg a code smell elemzést, távolítsd el a CONDUCTOR pipeline hivatkozásokat.

**Elvárt viselkedés:**
```
1. Scope meghatározása $ARGUMENTS-ből:
   - Ha fájl/modul nevet tartalmaz → azt elemezd
   - Ha üres → kérdezd meg: "Mit vizsgáljak?"

2. Code smell elemzés (változatlan):
   - Duplikáció, hosszú metódusok, god class, feature envy,
     dead code, magic numbers, rossz elnevezések
   - Mutasd priorizálva: Impact × Effort mátrix

3. Javaslat után:
   - Ha a user elfogadja → írj task fájlt:
     docs/tasks/YYYY-MM-DD-refactor-[modul].md
   - NE hivatkozz /analyze-idea vagy /build parancsokra
     (nem léteznek)

NE olvasd: cat .conductor/agents/refactor.md (archívban van)
```

---

## Tesztelés

```bash
# Ellenőrizd hogy a törölt fájlok eltűntek:
ls .claude/commands/
# Elvárt: build.md, docs.md, setup-env.md, pause.md NEM szerepel

# Ellenőrizd hogy a javított fájlokban nincs conductor hivatkozás:
grep -r "conductor" .claude/commands/
# Elvárt: 0 találat
```

Nincs pytest hatás — csak markdown fájlok.

---

## Git commit

```
fix: remove remaining conductor references from slash commands

Delete: build.md, docs.md, setup-env.md, pause.md (conductor-specific, no native equivalent)
Fix: test.md, review.md, refactor.md (remove conductor DB calls, keep core logic)
No functional pipeline changes, no test impact.
```
