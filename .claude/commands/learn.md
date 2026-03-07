Learning rögzítése fájlba.

## 1. Parsing

Parse `$ARGUMENTS` — elvárt formátum: `[category] [content]`

Ha `$ARGUMENTS` elején nincs kategória → kérdezd meg:
- **rule** — állandó szabály, mindig kövesd (→ `.claude/rules/ifds-rules.md`)
- **discovery** — hasznos felfedezés, kontextus (→ `docs/planning/learnings-archive.md`)
- **correction** — hiba javítás, "ezt csináld másképp" (→ `docs/planning/learnings-archive.md`)
- **decision** — architektúrális döntés + indoklás (→ `docs/planning/learnings-archive.md`)

## 2. Formázás

```
[LEARN] Kategória: Egy soros szabály
Mistake: Mi ment rosszul (opcionális)
Correction: Hogyan kell helyesen (opcionális)
```

**Kategóriák (IFDS-specifikus):**
- `Pipeline` — Phase 1-6 logika, scoring, sizing
- `PaperTrading` — IBKR scripts, order management
- `Testing` — pytest, fixture-ök, env isolation
- `Git` — commit, branch, workflow
- `Config` — PARAMETERS.md, defaults.py, TUNING kulcsok
- `API` — Polygon, FMP, UW, FRED client szabályok
- `Architecture` — design döntések, modulok közötti kapcsolatok
- `CC` — Claude Code session kezelés, tooling

## 3. Mentés

**Ha category == "rule":**
Fűzd hozzá a `.claude/rules/ifds-rules.md` fájlhoz:
```
## [rövid cím] (rule, YYYY-MM-DD)
[content]
```

**Ha category == "discovery" | "correction" | "decision":**
Fűzd hozzá a `docs/planning/learnings-archive.md` fájlhoz:
```
## [rövid cím] ([category], YYYY-MM-DD)
[content]
```

Mutasd meg mit fogsz hozzáadni, várj jóváhagyásra, utána ments.

## 4. Megerősítés

```
Learning mentve → [fájl]
#[kategória]: [egy soros összefoglaló]
```

---

**Trigger:** "jegyezd meg", "tanuld meg", "add hozzá a szabályokhoz", "remember this", `/learn rule ...`, `/learn correction ...`
