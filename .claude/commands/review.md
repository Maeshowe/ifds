Code review — kód vizsgálat és értékelés.

## 1. Scope meghatározása
Ha a `$ARGUMENTS` tartalmaz fájl/modul nevet → azt reviewzd.
Ha a `$ARGUMENTS` üres → kérdezd meg: "Mit vizsgáljak?"

## 2. Kód vizsgálat
Az érintett fájlokra:
- **Helyesség:** Azt csinálja amit kell?
- **Minták:** Követi a meglévő kód konvenciókat?
- **Tesztek:** Vannak tesztek az új/változott kódhoz?
- **Edge case-ek:** Kezeli a nyilvánvaló szélső eseteket?

## 3. Eredmények bemutatása
Minden találatot kategorizálj:
- **CRITICAL:** Bugok, hiányzó kötelező funkció, biztonsági problémák
- **WARNING:** Hiányzó tesztek, inkonzisztens minták, potenciális problémák
- **INFO:** Stílus javaslatok, apró javítások

Mutasd be táblázatban:
| # | Súlyosság | Fájl | Találat | Javaslat |
|---|-----------|------|---------|----------|
| 1 | CRITICAL  | ... | ... | ... |

## 4. Verdikt
- **APPROVED** — Nincs kritikus probléma, a warning-ok elfogadhatók
- **CHANGES_REQUESTED** — Kritikus problémák vagy túl sok warning
- **REJECTED** — Alapvető problémák

## 5. Mentés
Ha CHANGES_REQUESTED vagy CRITICAL találat van →
írj task fájlt: `docs/tasks/YYYY-MM-DD-review-findings.md` (táblázat + verdikt).
