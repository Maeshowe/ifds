Session lezárás: journal entry írása.

## 1. Summary generálás
Ha a `$ARGUMENTS` tartalmaz summary-t → használd azt.
Ha `$ARGUMENTS` üres → NE kérdezd meg a user-t! Generáld magad a session alapján:
- Mit csináltunk (feature-ök, fix-ek, döntések)
- Hány teszt fut (ha volt teszt futtatás)
- Commit hash (ha volt commit)
- Mi a következő lépés

## 2. Journal entry írása
Írj journal entry-t: `docs/journal/YYYY-MM-DD-session-close.md`

Formátum:
```
# Session Close — YYYY-MM-DD HH:MM

## Mit csináltunk
[összefoglaló]

## Következő lépés
[mi jön]

## Commit(ok)
[hash(ek) ha volt]
```

Ha a nap folyamán már volt session-close → az új fájl neve legyen `session-close-2.md`, `-3.md` stb.

## 3. Megerősítés
Erősítsd meg: "Session lezárva, journal mentve: docs/journal/YYYY-MM-DD-session-close.md"
