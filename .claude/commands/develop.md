Funkció fejlesztés strukturált fázisokban: Research → Plan → Implement → Commit.

## Feature: $ARGUMENTS

---

### Fázis 1: Research

Ismerd meg a scope-ot mielőtt bármit változtatnál:

1. Érintett fájlok és meglévő minták keresése
2. Függőségek és korlátok ellenőrzése
3. Kapcsolódó task fájl olvasása: `docs/tasks/` — van-e vonatkozó `.md`?
4. Kapcsolódó spec olvasása: `docs/PIPELINE_LOGIC.md`, `docs/PARAMETERS.md`

**Confidence score (0-100):**
- Scope tiszta (0-20): pontosan tudod melyik fájlok változnak?
- Pattern ismert (0-20): van hasonló minta a kódbázisban?
- Függőségek (0-20): tudod mi függ az érintett kódtól?
- Edge case-ek (0-20): azonosíthatók a szélső esetek?
- Teszt stratégia (0-20): tudod hogyan verifikálod?

**Döntés:**
- Score ≥ 70 → mutasd a research findingeket, lépj tovább Fázis 2-be
- Score < 70 → azonosítsd a hiányzó kontextust, gyűjtsd be, score újra

---

### Fázis 2: Plan

Mutasd be a tervet jóváhagyásra:

```
TERV: [Feature neve]

Cél: [egy mondat]

Módosítandó fájlok:
1. src/ifds/phases/phase_X.py — [mit változtat]
2. scripts/paper_trading/xxx.py — [mit változtat]

Új fájlok:
1. scripts/paper_trading/yyy.py — [célja]

Megközelítés:
1. [lépés + indoklás]
2. [lépés + indoklás]

Kockázatok:
- [lehetséges probléma + mitigáció]

Teszt stratégia:
- [hogyan verifikálod]

Kapcsolódó task fájl: docs/tasks/YYYY-MM-DD-xxx.md
```

**Várd meg a "proceed", "jóváhagyva", vagy "ok" visszajelzést mielőtt implementálsz.**

---

### Fázis 3: Implementáció

Hajtsd végre a jóváhagyott tervet:

1. Módosítások a terv sorrendjében
2. Minden fájlváltozás után futtass tesztet: `python -m pytest tests/ -q`
3. Minden 5 módosítás után rövid review-pause
4. Végén teljes quality gate: `python -m pytest --tb=short -q`

---

### Fázis 4: Review & Commit

1. Self-review: `git diff --cached` — `print()`, TODO, credential?
2. Összefoglaló a usernek
3. Commit a task fájlban megadott üzenettel (vagy `/commit` command)
4. Task fájl Status → `DONE`, Updated → mai dátum

---

### Learning capture

Implementáció után kérdezd meg:
- Volt correction a terv közben?
- Van pattern amit érdemes rögzíteni?
- `[LEARN] Kategória: Szabály` formátumban javasold ha igen.

---

**Trigger:** "fejleszd", "implementáld", "csináld meg a [feature]-t", vagy task fájl átadásakor.
