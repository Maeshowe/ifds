Code smell elemzés és refactoring javaslatok.

## 1. Scope meghatározása
Ha a `$ARGUMENTS` tartalmaz fájl/modul nevet → azt elemezd.
Ha üres → kérdezd meg: „Mit vizsgáljak? (modul, fájl, vagy az egész projektet?)"

## 2. Code smell-ek azonosítása
Vizsgáld a kódot:
- **Duplikáció:** ismétlődő kódrészletek
- **Hosszú metódusok:** 50+ soros függvények
- **God class:** túl sok felelősség egy osztályban
- **Feature envy:** egy osztály túl sokat használ másik osztály adatait
- **Dead code:** nem használt kód
- **Magic numbers/strings:** hardcoded értékek
- **Rossz elnevezések:** nem beszédes változó/függvény nevek

## 3. Priorizálás
| # | Code Smell | Fájl | Impact | Effort | Prioritás |
|---|-----------|------|--------|--------|-----------|
| 1 | ... | ... | HIGH/MED/LOW | HIGH/MED/LOW | ... |

## 4. Javaslat
Kérdezd meg: „Ezeket a problémákat találtam. Melyikkel foglalkozzunk?"

Ha a user elfogadja → írj task fájlt: `docs/tasks/YYYY-MM-DD-refactor-[modul].md`
