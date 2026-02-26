Learning rögzítése fájlba.

## 1. Parsing
Parse `$ARGUMENTS` — elvárt formátum: `[category] [content]`
- Ha `$ARGUMENTS` elején category kulcsszó áll (rule, discovery, correction) → használd
- Ha nincs category → kérdezd meg:
  - **rule** — állandó szabály, mindig kövesd
  - **discovery** — hasznos felfedezés, kontextus
  - **correction** — hiba javítás, ezt csináld másképp legközelebb

## 2. Mentés

**Ha category == "rule":**
Fűzd hozzá a `.claude/rules/ifds-rules.md` fájlhoz:
```
## [rövid cím] (rule, YYYY-MM-DD)
[content]
```

**Ha category == "discovery" VAGY "correction":**
Fűzd hozzá a `docs/planning/learnings-archive.md` fájlhoz:
```
## [rövid cím] ([category], YYYY-MM-DD)
[content]
```

## 3. Megerősítés
Erősítsd meg: "Learning mentve → [fájl]"
