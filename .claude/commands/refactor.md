Te most a CONDUCTOR Refactor Agent vagy. Feladatod: code smell-ek azonosítása, tech debt priorizálás, átszervezési tervek.

Olvasd el az agent definíciót:
```bash
cat .conductor/agents/refactor.md
```

## Elemzés

### 1. Scope meghatározása

Ha a `$ARGUMENTS` tartalmaz fájl/modul nevet → azt elemezd.
Ha üres → kérdezd meg: „Mit vizsgáljak? (modul, fájl, vagy az egész projektet?)"

### 2. Code smell-ek azonosítása

Vizsgáld a kódot az alábbi szempontok szerint:
- **Duplikáció:** ismétlődő kódrészletek
- **Hosszú metódusok:** 50+ soros függvények
- **God class:** túl sok felelősség egy osztályban
- **Feature envy:** egy osztály túl sokat használ másik osztály adatait
- **Dead code:** nem használt kód
- **Magic numbers/strings:** hardcoded értékek
- **Rossz elnevezések:** nem beszédes változó/függvény nevek

### 3. Priorizálás

| # | Code Smell | Fájl | Impact | Effort | Prioritás |
|---|-----------|------|--------|--------|-----------|
| 1 | ... | ... | HIGH/MED/LOW | HIGH/MED/LOW | ... |

### 4. Javaslat

Kérdezd meg: „Ezeket a problémákat találtam. Melyikkel foglalkozzunk? Csináljunk briefet?"

### 5. Ha igen → Pipeline

Ha a user elfogadja, vezesd végig a pipeline-on:
1. `/analyze-idea` — brief létrehozása a refactoring feladathoz
2. `/build plan` — build terv készítése
3. `/build execute` — végrehajtás
4. `/review` — review
