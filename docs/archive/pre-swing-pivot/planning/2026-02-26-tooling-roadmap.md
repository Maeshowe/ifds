# IFDS — Claude Code Tooling Roadmap (post-CONDUCTOR)

**Dátum:** 2026-02-26  
**Státusz:** Tervezés — implementáció a CONDUCTOR migráció után

---

## Az új struktúra célja

A CONDUCTOR kivonása után az IFDS Claude Code infrastruktúra teljes mértékben az Anthropic
natív eszközeire épül. Nincs saját Python csomag, nincs SQLite DB, nincs manuális session management.

```
.claude/
├── agents/          ← Specializált sub-agentek (CC delegál ide)
├── commands/        ← Slash commandok (már megvan, 12 db)
├── rules/           ← Állandó szabályok (CC mindig olvassa)
├── scripts/         ← Hook scriptek (Bash)
├── hooks.json       ← Trigger-alapú automatizáció
└── settings.local.json
```

---

## Fázis 1 — Alap migráció (most: 2026-02-26)

Lásd: `docs/tasks/2026-02-26-conductor-to-native-cc.md`

Eredmény: CONDUCTOR kiváltva, natív struktúra él.

---

## Fázis 2 — Rules finomítás (BC17 közben, ~márc 4)

Az első iterációban a rules általánosak. BC17 implementáció közben CC tanul —
minden `/learn rule` hívás gazdagítja az `ifds-rules.md`-t.

Várható új rules BC17 után:
- EWMA paraméter constraints (alpha értéktartomány, window)
- Crowdedness shadow mode — mit szabad/tilos módosítani amíg shadow fut
- OBSIDIAN fokozatos aktiválás — tickerenkénti feltétel ellenőrzés kötelezettsége

Nincs külön task szükséges — organikusan kerülnek be `/learn rule` hívásokkal.

---

## Fázis 3 — Skills és Contexts (BC17 után, ~márc közép)

### `skills/continuous-learning/`

Mit csinál: session végén automatikusan kivonja a tanult mintákat és
hozzáfűzi a learnings archívumhoz. Nem kell manuálisan `/learn`-t hívni.

IFDS adaptáció — a pattern extraction fókuszáljon:
- Pipeline bug minták (melyik phase-ben, milyen típus)
- API quirk-ök (rate limit, timeout, response format változások)
- Scoring edge case-ek

Implementáció: `.claude/skills/continuous-learning/SKILL.md` + Stop event hook.

### `contexts/`

IFDS-specifikus context injection módok:
- `contexts/pipeline-debug.md` — pipeline hiba diagnosztizáláshoz
- `contexts/bc-implementation.md` — BC fejlesztéshez (szigorúbb testing rules)
- `contexts/paper-trading-review.md` — EOD log elemzéshez

Alacsony prioritás — a jelenlegi CLAUDE.md kontextus egyelőre elegendő.

---

## Fázis 4 — Task státusz loop (BC17 után, ~márc közép)

Ez a legfontosabb hiányzó elem: CC → Chat visszacsatolás.

### Task státusz konvenció

Minden `docs/tasks/YYYY-MM-DD-*.md` fájl első 3 sora:
```
Status: OPEN | WIP | DONE | BLOCKED
Updated: YYYY-MM-DD
Note: <opcionális rövid megjegyzés>
```

CC minden task fájl megnyitásakor és commit előtt frissíti a Status sort.

Chat session elején egy sorral látja a nyitott taskokat:
```bash
grep -rl "Status: OPEN\|Status: WIP" docs/tasks/ 2>/dev/null
```

### CLAUDE.md auto-update hook

CC minden `git commit` után futtat egy update scriptet:
`.claude/scripts/update-context.sh`

A script frissíti a CLAUDE.md `## Aktuális Kontextus` szekcióját:
- Utolsó commit hash és üzenet
- Nyitott task fájlok száma
- Teszt szám (utolsó pytest output alapján)

Eredmény: Chat mindig friss állapotot lát anélkül, hogy Tamásnak kellene
kézzel frissíteni a project instructions-t.

---

## Fázis 5 — MCP integráció (BC20 előtt, ~április)

Egyelőre nem prioritás. BC20 előtt érdemes megvizsgálni:

GitHub MCP: CC közvetlenül kezel issue-t, PR-t. Releváns ha a repo GitHub-on él.

Custom IFDS MCP (ha megéri): egy saját MCP szerver ami exponál:
- IBKR paper account státuszt
- Napi pipeline log summaryt
- Cumulative P&L-t

BC22-23 táján válik relevánssá, ha a paper trading live-ra vált.

---

## Összefoglalás

| Fázis | Mikor | Mit |
|---|---|---|
| 1 — Alap migráció | 2026-02-26 | CONDUCTOR → natív CC |
| 2 — Rules finomítás | BC17 közben (~márc 4) | Organikus, /learn hívásokból |
| 3 — Skills + Contexts | BC17 után (~márc közép) | continuous-learning, context injection |
| 4 — Loop rendszer | BC17 után (~márc közép) | Task státusz + CLAUDE.md auto-update |
| 5 — MCP | BC20 előtt (~április) | GitHub MCP, esetleg custom IFDS MCP |

---

## Mi NEM kerül be

- Go/TypeScript/Playwright agentek — irreleváns stack
- `instinct-status/import/export` commandok — túl komplex, nincs ROI
- `verification-loop` skill — pytest + QA audit lefedi
- Plugin marketplace rendszer — overhead nélkül kézzel kezeljük
