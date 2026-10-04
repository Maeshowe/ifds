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

> 🔴 **HELYESBÍTVE (2026-10-04, repo-audit).** A korábbi szöveg azt állította, hogy a
> 2026-05-15 … 05-29 közötti régi taskok mind „status-header nélküliek". **Ez 12-re
> nézve hamis volt:** `**Status:** DONE` fejlécet hordoztak **félkövér** formában,
> amit a `^Status:` horgonyos lekérdezés nem lát — tehát lezártként ültek a gyökérben,
> és a README indoklása fedezte őket. Mind a 12 normalizálva a 3 soros alakra és
> ide archiválva (ebből 1 `WIP`-ről `DONE`-ra: a swing-deploy B része a 2026-05-18-i
> go-live-val lezárult).
>
> **Tanulság:** a „nem szennyezi a lekérdezést" **nem** azonos a „nincs mit
> archiválni"-val. Egy lekérdezés, ami nem lát egy fájlt, nem bizonyíték arra, hogy
> a fájl a helyén van.

A gyökérben **négy** régi, valóban status-header nélküli task maradt
(`2026-05-23`, `2026-05-25`, `2026-05-28`, `2026-05-29`) plusz a `future-*`
placeholder (`Status: PLANNED` — szándékosan nem az enumból, mert nem indítható).
Ezek nem szennyezik a nyitott-task lekérdezést. Ha egy ilyen lezárul, kapjon
**nem-félkövér** `Status: DONE` fejlécet és kerüljön ide.
