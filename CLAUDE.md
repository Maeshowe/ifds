# IFDS — Institutional Flow Decision Suite

## Projekt
Multi-faktoros kvantitatív kereskedési rendszer (swing trading, US equities).
6-fázisú pipeline: BMI regime → Universe → Sectors → Stock Analysis → GEX/OBSIDIAN → Position Sizing.
Specifikáció: IDEA.md | Pipeline logika: docs/PIPELINE_LOGIC.md | Paraméterek: docs/PARAMETERS.md

## Státusz
- **Production** — Mac Mini cron 22:00 CET (Mon-Fri), `scripts/deploy_daily.sh`
- **BC16 kész** — Phase 1 async (282s→17s), factor volatility framework, SIM-L1 validation engine
- **752 teszt**, 0 failure
- **OBSIDIAN store**: gyűjtés folyamatban (day 2/21, aktiválás ~2026-03-04)
- **Következő**: BC17 (factor vol aktiválás + EWMA + crowdedness mérés) — ~márc. 4

## Alapszabályok
- Ez PÉNZÜGYI rendszer — Human-in-the-loop minden döntésnél
- Semmi nem megy prodba jóváhagyás nélkül
- API kulcsokat SOHA ne commitolj (.env-ben vannak)
- Tesztek MINDIG futnak commit előtt: `python -m pytest tests/ -q`
- Változtatás után frissítsd: CHANGELOG.md, PARAMETERS.md, PIPELINE_LOGIC.md

## Tech Stack
- Python 3.12, async/await, SQLite
- API-k: Polygon (bars, options), FMP (fundamentals), Unusual Whales (dark pool, GEX), FRED (VIX, TNX)
- Futtatás: `source .env && python -m ifds run`
- Validáció: `python -m ifds validate --days 10`

---

## CONDUCTOR — Session & Agent Management

A CONDUCTOR a projekt session-kezelő és agent-rendszere. SQLite DB: `.conductor/memory/project.db`
Agent definíciók: `.conductor/agents/*.md`

### Session Workflow (KÖTELEZŐ)

**Session indítás** — minden munkamenet elején:
```bash
python -m conductor continue --project-dir .
```
Ez betölti az előző session kontextusát (summary, open tasks, decisions, rules) és új session-t indít.

**Session lezárás** — minden munkamenet végén:
```bash
python -m conductor wrap-up --summary "<összefoglaló>" --project-dir .
```
Az összefoglalóban legyen: mit csináltunk, hány teszt, milyen commit, mi a következő lépés.

Ha a user `/wrap-up`-ot mond ARGUMENTS nélkül, NE kérdezd meg a user-t — generáld az összefoglalót magad az adott session-ből.

**Emergency save** (ha a session megszakad):
```bash
python -m conductor pause --project-dir .
```

### Tanulság rögzítés
Ha bármilyen fontos felfedezés, hiba, vagy szabály merül fel a session során:
```bash
python -m conductor learn --content "<tanulság>" --category "<rule|discovery|correction>" --project-dir .
```
- **rule**: állandó szabály, mindig kövesd (pl. "FMP semaphore max 8, mert 12-nél 429-ek jönnek")
- **discovery**: hasznos felfedezés (pl. "Freshness Alpha score-t nem szabad 100-ra cap-elni")
- **correction**: hiba javítás (pl. "Phase 1 async-hoz asyncio.run() kell, nem await")

### Mikor használd a többi CONDUCTOR parancsot

**Új feature ötlet** → `/analyze-idea` (BA agent strukturálja a követelményeket)
**Build terv készítés** → `/build plan` (Lead Dev agent lépésekre bontja)
**Kód review** → `/review` (Code Review agent ellenőrzi)
**Döntés rögzítés** → `/decide` (döntés a DB-be kerül)
**Teszt eredmény** → `/test save` (teszt futtatás eredménye a DB-be)

### Automatikus CONDUCTOR használat

A következő helyzetekben MINDIG használd a megfelelő CONDUCTOR parancsot, ne várd meg hogy a user kérje:

1. **Session eleje** → `/continue` (kontextus betöltés)
2. **Session vége** → `/wrap-up` (állapot mentés)
3. **Fontos felfedezés** → `/learn --category discovery`
4. **Hiba amit máskor is el kellene kerülni** → `/learn --category rule`
5. **Döntés ami befolyásolja a projekt irányát** → `/decide`

### Amit NE csinálj
- NE hagyj session-t lezáratlanul
- NE felejtsd el a `/continue`-t session elején
- NE kérdezd meg a user-t a wrap-up summary-ról — generáld magad
- NE használj CONDUCTOR parancsot ha nincs inicializálva (`.conductor/` mappa hiányzik)

---

## Journal — Megosztott Kontextus

A `docs/journal/` könyvtár tartalmazza a Claude Chat session-ök állapotmentéseit.
Ezek a stratégiai döntéseket, architektúrális gondolkodást, és a "miértek"-et tartalmazzák.

**Session elején MINDIG olvasd el az utolsó 1-2 journal entry-t:**
```bash
ls -t docs/journal/ | head -2 | xargs -I{} cat docs/journal/{}
```

A journal entry-k struktúrája:
- Elvégzett munka
- Döntések (sorszámozva: D1, D2, ...)
- Következő lépések
- Nyitott kérdések
- Roadmap referencia

**A journal a Chat-ben keletkezik, nem CC-ben.** Te (CC) olvasod, de nem írod.
Ha a user hivatkozik egy korábbi döntésre vagy kontextusra, keresd a journal-ban.

---

## Fájl Struktúra (referencia)

```
src/ifds/
├── config/defaults.py          # CORE/TUNING/RUNTIME config
├── phases/
│   ├── phase1_regime.py        # BMI (async BC16)
│   ├── phase2_universe.py      # FMP screener + earnings exclusion
│   ├── phase3_sectors.py       # Sector rotation + breadth
│   ├── phase4_stocks.py        # Multi-factor scoring
│   ├── phase5_gex.py           # GEX regime + OBSIDIAN dispatch
│   ├── phase5_obsidian.py      # OBSIDIAN MM classifier (factor vol BC16)
│   └── phase6_sizing.py        # Position sizing + risk management
├── sim/
│   ├── models.py               # Trade, ValidationSummary
│   ├── broker_sim.py           # IBKR bracket simulation
│   ├── validator.py            # Forward validation engine
│   └── report.py               # Validation report
├── output/telegram.py          # Daily Telegram report
├── models/market.py            # All dataclasses and enums
└── data/                       # API clients, cache, adapters

src/conductor/                  # CONDUCTOR session & agent system
.conductor/agents/              # Agent personality definitions
.conductor/memory/project.db    # Session DB (SQLite + FTS5)
docs/journal/                   # Chat session állapotmentések (READ ONLY)
```

## Roadmap 2026

```
Q1: BC1-18 (pipeline + validáció + crowdedness)         ← CURRENT
Q2: BC19-22 (risk layer + HRP + SimEngine L2-L3)
Q3: BC23-26 (BL + auto execution + multi-strategy)
Q4: BC27-30 (dashboard + alpha decay + retail packaging)
```

## Aktuális Kontextus
<!-- CC frissíti a /wrap-up során -->
- **Utolsó journal**: docs/journal/2026-02-12-session-bc16-sim-roadmap.md
- **Aktív BC**: nincs (BC16 kész, BC17 márc. 4)
- **Aktív egyéb**: SIM-L1 kész, adatgyűjtés folyamatban (első validáció ~feb. 19)
- **Blokkolók**: nincs
- **OBSIDIAN baseline**: day 2/21
