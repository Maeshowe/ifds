# Task Archive

Lezárt task fájlok (`Status: DONE` vagy `Status: REJECTED`).

## Konvenció

- Egy task **lezárásakor** (`Status: DONE` / `REJECTED`) ide kerül `git mv`-vel
  a `docs/tasks/` gyökérből.
- A `docs/tasks/` gyökérben **csak aktív task** marad (`OPEN` / `WIP`).
- A "nyitott taskok" lekérdezés ezért **nem rekurzív** és a header-sorra horgonyoz:
  ```bash
  grep -lE "^Status:[[:space:]]*(OPEN|WIP)" docs/tasks/*.md 2>/dev/null
  ```
  (A `*.md` glob nem lép be az `archive/`-ba; a `^Status:` horgony megakadályozza,
  hogy egy body-szövegben idézett "Status: OPEN" string false-positive-ot okozzon —
  ez volt a 2026-05-21-sector-metric-clarity false-positive gyökéroka.)

## Megjegyzés

A 2026-05-15 … 2026-05-29 közötti **status-header nélküli** régi taskok a gyökérben
maradtak (nincs explicit `DONE`/`REJECTED` fejlécük) — ezek nem szennyezik a nyitott-
task lekérdezést. Ha egy ilyen lezárul, kapjon `Status: DONE` fejlécet és kerüljön ide.
