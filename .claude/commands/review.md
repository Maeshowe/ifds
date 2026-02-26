Te most a CONDUCTOR Code Reviewer vagy. Feladatod: az elkészült munkát a brief és a build terv alapján ellenőrizni.

Olvasd el az agent definíciót:
```bash
cat .conductor/agents/code-review.md
```

## Mit vizsgáljunk?

Ha a `$ARGUMENTS` tartalmaz plan ID-t, azt a build terv outputját vizsgáld.
Ha a `$ARGUMENTS` üres, keresd a nemrég befejezett terveket:

```bash
python -m conductor build list --status completed
```

Kérdezd meg: "Melyik buildet vizsgáljam?"

## Review folyamat

### 1. Kontextus betöltés
```bash
python -m conductor build get --id <PLAN_ID>
```
Töltsd be a build tervet ÉS a linkelt briefet, hogy megértsd mit kértek vs. mit építettek.

### 2. Kód vizsgálat
Minden fájlra a `files_to_create` és `files_to_modify` listából:
- Olvasd el a fájlt
- Ellenőrizd a brief `scope_essential` elemei alapján
- Ellenőrizd az acceptance criteria alapján
- Nézd meg:
  - **Helyesség:** Azt csinálja amit a brief kért?
  - **Minták:** Követi a meglévő kód konvenciókat?
  - **Tesztek:** Vannak tesztek az új/változott kódhoz?
  - **Edge case-ek:** Kezeli a nyilvánvaló szélső eseteket?

### 3. Eredmények bemutatása
Minden találatot kategorizálj:
- **CRITICAL:** Bugok, hiányzó kötelező funkció, biztonsági problémák
- **WARNING:** Hiányzó tesztek, inkonzisztens minták, potenciális problémák
- **INFO:** Stílus javaslatok, apró javítások

Mutasd be táblázatban:
| # | Súlyosság | Fájl | Találat | Javaslat |
|---|-----------|------|---------|----------|
| 1 | CRITICAL  | path/to/file.py | ... | ... |
| 2 | WARNING   | path/to/file.py | ... | ... |

### 4. Verdikt
A találatok alapján:
- **APPROVED** — Nincs kritikus probléma, a warning-ok elfogadhatók
- **CHANGES_REQUESTED** — Kritikus problémák vagy túl sok warning
- **REJECTED** — Alapvető problémák, nem felel meg a briefnek

Kérdezd meg: "Ez a review eredmény. Egyetértesz? Mentsem?"

### 5. Mentés
```bash
python -m conductor review create --plan-id <PLAN_ID> --brief-id <BRIEF_ID> --type code --data '{"scope": "...", "findings": [{"severity": "...", "file": "...", "finding": "...", "suggestion": "..."}], "verdict": "...", "summary": "..."}'
```

Ha a verdikt **approved**:
```bash
python -m conductor analyze-idea status --id <BRIEF_ID> --set completed
```
Mondd: "A brief lezárva! A munka jóváhagyva."

Ha a verdikt **changes_requested**:
Mondd el pontosan mit kell javítani, és javasold a `/build execute` újrafuttatását.
