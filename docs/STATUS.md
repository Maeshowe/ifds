# IFDS — Állapot
Frissítve: 2026-11-11

## Cél most
A projekt lezárva (2026-11-11). Technikailag működik, de a jelcsalád nem hozta a várt eredményt (keresztmetszeti null mind a négy horizonton). A mappa helye: `~/SSH-Services/_archive/ifds`.

## Kész ebben a körben
- A régi STATUS szó szerint: `docs/archive/STATUS-2026-11-11.md` (ott a teljes indoklás és az operatív állapot).
- A `claude/mystifying-swartz` worktree törölve; a benne maradt, nem commitolt QA-jegyzetek: `docs/archive/qa-2026-02/` (nincs gitben).
- A Mac Mini cronja leállítva: a 16 IFDS-sor kikommentezve (`# IFDS-OFF 2026-11-11:` előtag), mentés a Minin: `~/crontab-backup-2026-11-11`. Visszakapcsolás: `crontab ~/crontab-backup-2026-11-11`. A signum, az aetherveil és az LLM jobjai futnak tovább.
- A GitHub-repó (`Maeshowe/ifds`) a záró commit után archiválva (csak olvasható; új push előtt vissza kell állítani).
- A MID `ifds` és `ifds-shadow-mode-w18` kulcsa egyelőre marad (Tamás, 11-11: a kockázatot vállalja).

## Rám vár
- Fizetős API-k — Javaslat: mondd le, amit csak az IFDS használt; előbb egy mid sessionben nézd meg, mit használ a mid, a signum és a morning_news (a signum ugyanazon a Massive-kulcson fut).
- Az IBKR Gateway a Mac Minin (ha fut) — Javaslat: leállítható, a cron már nem használja.
- A `docs/foundational/strategic-review/2026-05-22-bridgewater-janestreet-research.pdf` nincs gitben — Javaslat: maradjon is így (külső anyag, nyilvános repó).

## Fontos fájlok
- `docs/archive/STATUS-2026-11-11.md` — a lezárás előtti teljes állapot és döntési háttér
- `scripts/crontab.md` — a Mac Mini ütemezése (a leállításhoz)
- `docs/tasks/2026-10-04-operational-backlog.md` — elhalasztott operatív tételek
