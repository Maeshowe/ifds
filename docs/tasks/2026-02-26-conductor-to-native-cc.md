Status: DONE
Updated: 2026-03-07
Note: Migráció végrehajtva 2026-02-26

# Task: CONDUCTOR → Native Claude Code Migration

**Dátum:** 2026-02-26  
**Prioritás:** 🟡 BC17 előtt (de nem blokkolja)  
**Becsült idő:** 2-3h  
**Érintett fájlok:** `.claude/`, `src/conductor/`, `.conductor/`, `CLAUDE.md`

---

## Probléma

A CONDUCTOR (`src/conductor/`, `.conductor/`) egy saját fejlesztésű Python session management eszköz. Felváltja a natív Claude Code mechanizmusok (`hooks/`, `rules/`, `agents/`) kombinációjával, amelyek mögött Anthropic support és dokumentáció áll.

**A CONDUCTOR értékes tartalma amit meg kell őrizni:**
- 8 learning (1 rule, 4 discovery, 2 correction, 1 mixed) → markdown fájlokba
- 5 agent definíció → `.claude/agents/`-be
- 12 command → `.claude/commands/`-ban marad (már ott van)

**Ami elveszhet (nem használt aktívan):**
- `decisions` tábla: 0 sor
- `tasks` tábla: 0 sor (a task management `docs/tasks/`-ban él)
- `build_plans`, `reviews`, `briefs`: BC1-4 archívum (febr. 8-9.), operatívan irreleváns

---

## Fix — 6 lépés sorrendben

### Lépés 1: Learnings exportálása markdown fájlokba

Hozd létre: `.claude/rules/ifds-rules.md`

```markdown
# IFDS — Permanent Rules (CC mindig olvassa)

Ezek a szabályok a CONDUCTOR learnings-ből kerültek ide (2026-02-26 migráció).
Forrás: `.conductor/memory/project.db` — learnings tábla.

---

## IBKR Paper Trading — ClientId collision (rule, 2026-02-21)

Minden script KÖTELEZŐEN egyedi clientId-t használ:
- submit_orders.py → clientId=10
- close_positions.py → clientId=11  
- eod_report.py → clientId=12
- nuke.py → clientId=13

Ugyanaz a clientId session takeover-t okoz — az előző connection csendben ledobódik.
Mindig `ib.sleep(2-3)` kell connect után a pozíció/order szinkronhoz.

---

## Phase 6 Scoring — Freshness Alpha mutation guard (correction, 2026-02-09)

`phase6_sizing.py`: az `original_scores` dict-et BEFORE kell rögzíteni,
mielőtt a `_apply_freshness_alpha` mutálja a `combined_score`-t.
`fresh_tickers` típusa: `set[str]` (NEM `dict[str, float]`).
`_calculate_position` mindkét paramétert külön kapja: `original_scores` + `fresh_tickers`.

---

## Testing — AsyncMock warning (correction, 2026-02-21)

Ha sync kódút tesztelünk, ami NEM hívja az async függvényt:
`patch` hívásban `new=MagicMock()` — NEM `AsyncMock`.
AsyncMock nem-awaited coroutine-t hoz létre → RuntimeWarning.
scipy paired t-test azonos különbségekkel: precision loss → adj slight noise.

---

## FileCache TTL (correction, beépített BC18-prep)

A FileCache TTL check mindig frissnek mutatott stale adatot — proper expiry check kell.
Javítva BC18-prep-ben.
```

Hozd létre: `docs/planning/learnings-archive.md`

```markdown
# IFDS — Learnings Archive

CONDUCTOR `project.db`-ből exportálva 2026-02-26-án (migráció).
Operatív szabályok: `.claude/rules/ifds-rules.md`

---

## BC14 állapot (discovery, 2026-02-11)

BC10: scoring calibration, BC11: circuit breakers + robustness,
BC12: signal dedup + monitoring CSV + async phases,
BC13: survivorship bias, telegram alerts, daily trade limits, notional caps,
BC14: sector breadth analysis (7 regimes, divergence detection, FMP ETF holdings).
636 tests. Breadth adj isolated from ticker scores — crowding stable at 43.

## BC18-prep tanulságok (discovery, 2026-02-21)

Trading calendar: `pandas_market_calendars` opcionális, weekday-only fallback-kel.
Danger zone filter: bottom-10% performers kizárása universe-ből.
FileCache TTL broken volt — mindig stale adatot adott vissza.

## BC19 SIM-L2 Mode 1 (discovery, 2026-02-21)

Parameter sweep engine Phase 4 snapshot persistence-szel.
Paired t-test comparison (scipy). SimVariant config overrides: tuning dict patches-ként.
Phase 4 snapshots: `output/snapshots/YYYY-MM-DD.json`.

## BC18 scope döntés (discovery, 2026-02-21)

IBKR Connection Hardening (retry 3x, 5s/15s timeout, Telegram alert) → BC18-ba kerül.
BC25 Auto Execution bővítve long-running mode-dal.

## Paper Trading PnL tracking (discovery, 2026-02-21)

`cumulative_pnl.json` vs IBKR Realized PnL eltérés: nuke.py előző nap záróárral számol,
nem tényleges fill árral. OBSIDIAN aktiválás NEM dátumfüggő: store entry count >= 21/ticker.
```

### Lépés 2: `.claude/agents/` struktúra létrehozása

Hozd létre az alábbi könyvtárat és másold át + adaptáld a conductor agenteket.
A conductor-specifikus `python -m conductor` hivatkozásokat el kell távolítani.

**Fájlok létrehozása:**

`.claude/agents/lead-dev.md` — forrás: `.conductor/agents/lead-dev.md`  
`.claude/agents/code-reviewer.md` — forrás: `.conductor/agents/code-review.md`  
`.claude/agents/test-engineer.md` — forrás: `.conductor/agents/test.md`  
`.claude/agents/refactor.md` — forrás: `.conductor/agents/refactor.md`  
`.claude/agents/docs-updater.md` — forrás: `.conductor/agents/docs.md`  
`.claude/agents/devops.md` — forrás: `.conductor/agents/devops.md`  

Minden agent fájl elejére kerüljön egy frontmatter blokk:
```markdown
---
name: <agent-name>
description: <egy sor leírás — mikor delegálj ide>
tools: [Read, Write, Edit, Bash, Grep, Glob]
---
```

Conductor-hivatkozások eltávolítása minden agent fájlból:
- `python -m conductor learn` → törölni
- `python -m conductor decide` → törölni  
- `python -m conductor wrap-up` → törölni
- Bármilyen DB write logika → törölni

### Lépés 3: `.claude/rules/` kiegészítése

Az `ifds-rules.md` mellé hozd létre:

**`.claude/rules/security.md`**
```markdown
# Security Rules

- API kulcsokat SOHA ne commitolj — csak `.env`-ben
- `.env` mindig `.gitignore`-ban van
- `*.env*` pattern a `.gitignore`-ban ellenőrizendő minden commit előtt
- Secrets logba SOHA nem kerülnek — log üzeneteknél maszkold az API key-eket
- Paper trading: IBKR paper account (DUH118657) — nem live account
```

**`.claude/rules/testing.md`**
```markdown
# Testing Rules

- Minden commit előtt KÖTELEZŐ: `python -m pytest tests/ -q`
- 0 failure, 0 warning a minimum — ne commitolj piros tesztekkel
- Új feature → új tesztek (legalább happy path + 1 edge case)
- Mock: AsyncMock csak valóban async kódútnál, különben MagicMock
- Jelenlegi baseline: 853 passing (2026-02-26) — ez csak nőhet
```

**`.claude/rules/git-workflow.md`**
```markdown
# Git Workflow Rules

Commit prefix kötelező:
- `fix:` — bug javítás
- `feat:` — új funkció  
- `docs:` — csak dokumentáció
- `test:` — csak tesztek
- `chore:` — konfiguráció, tooling
- `refactor:` — viselkedés változás nélküli átírás

Commit üzenetbe kerül: mit, miért, teszt szám (pl. "feat: EWMA smoothing BC17 — 870 tests")
Push csak Tamás jóváhagyásával — CC commitol, Tamás pusholja.
```

### Lépés 4: Memory persistence hook adaptálása

Klónozd le lokálisan (csak olvasáshoz, ne installáld mint plugin):

```bash
cd /tmp && git clone --depth 1 https://github.com/affaan-m/everything-claude-code.git ecc-ref
```

Olvasd el: `/tmp/ecc-ref/hooks/hooks.json` és `/tmp/ecc-ref/scripts/hooks/`

Hozd létre: `.claude/hooks.json`

Az ECC `memory-persistence` hook logikáját adaptáld IFDS-re.
**Bash-t használj Node.js helyett** — a Mac Mini-n Python és Bash elérhető, Node nem garantált.

Hook struktúra `.claude/hooks.json`-ban:
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [{
          "type": "command",
          "command": "bash .claude/scripts/session-start.sh"
        }]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [{
          "type": "command", 
          "command": "bash .claude/scripts/session-end.sh"
        }]
      }
    ]
  }
}
```

Hozd létre: `.claude/scripts/session-start.sh`
```bash
#!/bin/bash
# IFDS session start — betölti a legutolsó journal kontextust
JOURNAL_DIR="docs/journal"
if [ -d "$JOURNAL_DIR" ]; then
  ls -t "$JOURNAL_DIR" | head -2 | while read f; do
    echo "=== Journal: $f ==="
    cat "$JOURNAL_DIR/$f"
  done
fi
```

Hozd létre: `.claude/scripts/session-end.sh`
```bash
#!/bin/bash
# IFDS session end — figyelmezteti CC-t hogy írjon journal entry-t
echo "[IFDS Hook] Session ending. Ha nem volt még wrap-up: futtasd a /wrap-up commandot."
```

### Lépés 5: CLAUDE.md frissítése

A CLAUDE.md-ből **töröld** a teljes `## CONDUCTOR — Session & Agent Management` szekciót (kb. 60 sor).

**Helyére** kerüljön:

```markdown
## Session Management (Native CC)

**Session indítás** — automatikus (hook betölti a journal kontextust)

**Session lezárás** — minden munkamenet végén:
/wrap-up

A `/wrap-up` command generálja az összefoglalót és ír egy új journal entry-t
`docs/journal/YYYY-MM-DD-session-close-N.md` formátumban.

**Tanulság rögzítés:**
/learn [rule|discovery|correction] <tartalom>

Rule kategória → `.claude/rules/ifds-rules.md`-be kerül (CC legközelebb olvassa).
Discovery/correction → `docs/planning/learnings-archive.md`-be kerül.

**Agent delegálás:**
Speciális feladatokhoz: @lead-dev, @code-reviewer, @test-engineer, @refactor, @devops
```

### Lépés 6: Archiválás és cleanup

```bash
# Archiválás (NEM törlés — visszaállítható ha valami hiányzik)
mkdir -p archive/conductor-2026-02-26
cp -r .conductor/ archive/conductor-2026-02-26/
cp -r src/conductor/ archive/conductor-2026-02-26/src-conductor/

# pyproject.toml-ban conductor dependency ellenőrzése
grep -i conductor pyproject.toml

# .gitignore — conductor DB kizárása (ha nincs már benne)
grep -q ".conductor/memory" .gitignore || echo ".conductor/memory/*.db" >> .gitignore
```

**NE töröld** a `.conductor/` és `src/conductor/` könyvtárakat — archive után 2 héttel, ha minden rendben, akkor lehet.

---

## Tesztelés

```bash
# 1. Rules és agents struktúra
ls -la .claude/rules/
ls -la .claude/agents/

# 2. Frontmatter ellenőrzés az agentekben
head -5 .claude/agents/lead-dev.md

# 3. hooks.json valid JSON
python3 -c "import json; json.load(open('.claude/hooks.json')); print('hooks.json OK')"

# 4. Scripts futtatható
chmod +x .claude/scripts/session-start.sh .claude/scripts/session-end.sh
bash .claude/scripts/session-start.sh | head -5

# 5. Teljes test suite — a migráció nem ronthat tesztet
python -m pytest tests/ -q

# 6. CONDUCTOR hivatkozások száma a CLAUDE.md-ben (csak archív megjegyzés maradhat)
grep -c "conductor" CLAUDE.md
```

---

## Git commit üzenet

```
chore: migrate CONDUCTOR to native CC (rules, agents, hooks)

- Export 8 learnings → .claude/rules/ifds-rules.md + docs/planning/learnings-archive.md
- Move conductor agents → .claude/agents/ with CC frontmatter
- Add .claude/rules/ (security, testing, git-workflow)
- Add memory-persistence hooks (session-start/end scripts)
- Remove CONDUCTOR section from CLAUDE.md
- Archive .conductor/ and src/conductor/ to archive/
- No functional changes to pipeline
853 tests passing
```

---

## Validáció (Chat ellenőrzi commit után)

Chat kéri az alábbi outputokat:
1. `ls .claude/rules/ .claude/agents/ .claude/scripts/`
2. `cat .claude/rules/ifds-rules.md` — mind a 3 rule látható
3. `python -m pytest tests/ -q` — teszt szám nem csökkent
4. `grep -c "conductor" CLAUDE.md` — alacsony szám (csak archív referencia)
