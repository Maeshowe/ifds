Múltbeli tanulságok felszínre hozása a jelenlegi task előtt.

## Használat

```
/replay close_positions
/replay phase1 async
/replay paper trading MOC
```

## Mit csinál

Az aktuális task leírásából kulcsszavakat keres a tanulság archívumokban.

### 1. Keresés

```bash
# ifds-rules.md-ben
grep -i "<kulcsszó>" .claude/rules/ifds-rules.md

# learnings-archive.md-ben  
grep -i "<kulcsszó>" docs/planning/learnings-archive.md

# task fájlokban (hasonló régebbi taskok)
grep -rl "<kulcsszó>" docs/tasks/ 2>/dev/null | head -5
```

### 2. Output formátum

```
REPLAY BRIEFING: <task>
═══════════════════════════════

Releváns rules (.claude/rules/ifds-rules.md):
  1. [PaperTrading] IBKR ClientId collision — minden script egyedi clientId-t használ
  2. [Pipeline] Freshness Alpha mutation guard — original_scores BEFORE mutáció

Releváns learnings (docs/planning/learnings-archive.md):
  1. [correction] close_positions TP/SL sync delay — reqPositions + 5s sleep kell
  2. [decision] Szcenárió B threshold 0.5% — indoklás: ...)

Hasonló task fájlok:
  - 2026-03-05-close-positions-tp-sl-awareness.md (Status: DONE)

Javaslat: [konkrét figyelmeztető pont a fentiek alapján]
```

### 3. Ha nincs találat

"Nem találtam releváns learningst erre a taskra. Ha valami tanulságos derül ki implementáció közben, használd a `/learn correction` commandot."

---

**Trigger:** "replay", "mit tudok erről", "korábbi tapasztalat", task fájl átadása előtt ha kéri a user.
