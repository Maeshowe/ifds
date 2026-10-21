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

> 🔴 **MÁSODIK ELŐFORDULÁS (2026-10-21).** A fenti tanulság ellenére a gyökérben maradt
> öt nem-kompatibilis fejléc, és a README **előző bekezdése fedezte őket** azzal, hogy
> „nem szennyezik a nyitott-task lekérdezést". Ez a kettőre nézve **hamis** volt:
> `2026-05-28` (a review-pipeline) **valóban `WIP`** volt, `2026-05-23` (state
> reconciliation) pedig **semmilyen status-sort nem tartalmazott** — a lekérdezés
> mindkettőt **öt hónapig** kihagyta, miközben a tartalmuk közben el is készült
> (`reconcile_state.py` + 22:15 cron, illetve a `/daily-review` command). Mellettük:
> `2026-05-29` félkövér `DONE`, `future-2026-04-17` félkövér `PLANNED` (ami nem is
> érvényes állapot), és három `DONE` fájl, ami egyszerűen nem lett archiválva.
>
> **A javítás ezúttal nem újabb normalizálás, hanem a RÉS zárása:**
> `tests/test_task_header_hygiene.py` — line-1 `Status:`, line-2 `Updated:`,
> nem-jövőbeli dátum, és a gyökérben nem maradhat `DONE`/`REJECTED`; plusz egy teszt,
> ami a CLAUDE.md-ben publikált grepet és a guard regexét **egymáshoz méri**. Nevesített
> allowlist az egyetlen kivételnek (`2026-05-25-operator-emergency-procedure.md` — élő
> operátori runbook, 10 helyről hivatkozva, köztük a `scripts/crontab.md` és egy teszt).
> A guard **visszavezetéssel verifikálva** (félkövér header → piros; gyökérben hagyott
> `DONE` → piros). Hibaalak: ugyanaz, mint a sink-auditnál — nem az egyes előfordulást,
> a **rést** zárjuk.

A gyökérben ezért ma **csak aktív munka** van: `OPEN` / `WIP` / `BLOCKED` fejléccel, plusz
az allowlistolt runbook. Lezáráskor a fájl **nem-félkövér** `Status: DONE` (vagy
`REJECTED`) fejlécet kap, `Updated:` sort a mai dátummal, és `git mv`-vel ide kerül.
