# IFDS — Institutional Flow Decision Suite

## Projekt
Multi-faktoros kvantitatív kereskedési rendszer (swing trading, US equities).
6-fázisú pipeline: BMI regime → Universe → Sectors → Stock Analysis → GEX/MMS → Position Sizing.
Specifikáció: IDEA.md | Pipeline logika: docs/PIPELINE_LOGIC.md | Paraméterek: docs/PARAMETERS.md

## Státusz (2026-03-21)
- **Production** — Mac Mini cron 22:00 CET (Mon-Fri), `scripts/deploy_daily.sh`
- **BC16 kész** — Phase 1 async (282s→17s), factor volatility framework, SIM-L1 validation engine
- **BC19 kész** — SIM-L2 Mód 1 (parameter sweep + Phase 4 snapshot persistence)
- **987 teszt**, 0 failure, 0 warning
- **BC18-prep kész** — Trading calendar, danger zone filter, cache TTL fix
- **IBKR Connection Hardening kész** — retry logic, timeout, Telegram alert, port konstansok
- **Witching Day Calendar kész** — `src/ifds/utils/calendar.py`, submit_orders.py skip + Telegram alert
- **AVWAP Limit→MKT kész** — `scripts/paper_trading/pt_avwap.py`, unfilled entry → AVWAP dip+cross → MKT
- **Scenario B Loss Exit kész** — 19:00 CET −2.0% threshold → immediate MKT close
- **Paper Trading**: Day 25 lezárult (IBKR paper account DUH118657, cum. PnL +$20.37)
- **Trailing Stop**: Scenario A + B implementálva (`pt_monitor.py`)
- **Swing Hybrid Exit**: design APPROVED (`docs/planning/swing-hybrid-exit-design.md`)
- **Következő**: BC18 (EWMA + crowdedness shadow + MMS aktiválás) — ~ápr 1

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
- Comparison: `python -m ifds compare --config sim_variants_test.yaml`

## Környezetek

| Gép | Szerepkör | Mit fut |
|-----|-----------|----------|
| **MacBook** | Fejlesztői környezet | VSCode + Claude Code, git, tesztek |
| **Mac Mini** | Production | Pipeline cron (22:00 CET), IBKR Gateway, paper trading scripts |

- Kód: MacBook-on fejlesztés → push → Mac Mini-n fut
- IBKR Gateway: **csak Mac Mini-n** fut (paper account DUH118657)
- Manuális scriptek (`nuke.py`, `submit_orders.py`, fill árak): **Mac Mini terminal** (Tamás)
- SSH: `ssh safrtam@mac-mini` (vagy a `sync_from_mini.sh` script)

## Commit Convention

```
feat:     új funkció
fix:      bug javítás
docs:     csak dokumentáció (PARAMETERS.md, PIPELINE_LOGIC.md stb.)
test:     csak tesztek
chore:    konfiguráció, tooling, függőségek
data:     data pipeline, API client változás
refactor: viselkedés változás nélküli átírás
```

**Commit scope** (opcionális, de ajánlott):
```
feat(phase4): ...
fix(close_positions): ...
data(polygon): ...
```

**Commit üzenet:** a task fájlban mindig benne van — használd azt.
Ha nincs task fájl: rövid imperatív mondat + kontextus a body-ban.

---

## Task Files

CC a taskokat a `docs/tasks/YYYY-MM-DD-*.md` fájlokból kapja (Chat írja).
Minden task fájl tartalmazza: probléma, megközelítés, implementációs terv, tesztelés, commit üzenet.

### Task fájl kötelező fejléc (minden task fájlban az első 3 sor)

```
Status: OPEN | WIP | DONE | BLOCKED
Updated: YYYY-MM-DD
Note: <opcionális rövid megjegyzés>
```

CC minden task fájl megnyitásakor frissíti a `Status` sort:
- Megnyitáskor: `OPEN` → `WIP`
- Commit után: `WIP` → `DONE`
- Ha blokkoló van: `BLOCKED` + `Note:` mezőbe az ok

### Task implementáció workflow

**Implementáció előtt:**
1. Olvasd el a task fájlt teljesen
2. Ellenőrizd a kapcsolódó spec szekciót
3. Futtasd a meglévő teszteket: `pytest --tb=short -q`
4. Frissítsd a Status-t `WIP`-re

**Implementáció közben:**
5. Implementálj → tesztelj → commit

**Implementáció után:**
6. Minden meglévő teszt passing maradjon
7. Új funkcionalitáshoz tesztek kötelezők
8. Commitálj a task fájlban megadott commit üzenettel
9. Frissítsd a Status-t `DONE`-ra, `Updated:` mezőt mai dátumra
10. Frissítsd az érintett docs fájlokat (PARAMETERS.md, PIPELINE_LOGIC.md, CHANGELOG.md)

### Nyitott taskok gyors lekérdezése

```bash
grep -rl "Status: OPEN\|Status: WIP" docs/tasks/ 2>/dev/null
```

---

## Dokumentációs Szabályok

**Mikor kell docs fájlt frissíteni:**

| Változás típusa | Frissítendő fájl(ok) |
|---|---|
| Új config kulcs / TUNING paraméter | `docs/PARAMETERS.md` |
| Pipeline logika változás (Phase 1-6) | `docs/PIPELINE_LOGIC.md` |
| Bármi commitálva | `CHANGELOG.md` |
| Új design döntés | `docs/planning/roadmap-2026-consolidated.md` |
| Tanulság, amit jövőben tudni kell | `docs/planning/learnings-archive.md` |
| Prod script változás (crontab, deploy) | README.md érintett szekció |

**Mikor NEM kell docs fájlt frissíteni:**
- Bugfix, ami nem változtatja a viselkedést/paramétereket
- Tesztek hozzáadása
- Refactor (viselkedés változás nélkül)
- Paper trading scripts belső logika (eod_report, close_positions stb.)

**PARAMETERS.md és PIPELINE_LOGIC.md frissítés formátuma:**
- Az érintett szekciót frissítsd, ne appendeld
- Ha új TUNING kulcs kerül `defaults.py`-ba, PARAMETERS.md-ben is legyen benne a leírással

---

## Session Management (Native CC)

**Session indítás** — automatikus (hook betölti a journal kontextust)

**Session lezárás** — minden munkamenet végén:
`/wrap-up`  — quality gates + journal entry + CLAUDE.md szinkron

Ha a user `/wrap-up`-ot mond ARGUMENTS nélkül, NE kérdezd meg a user-t — generáld magad.

## Command készlet

| Command | Mikor | Mit csinál |
|---------|-------|------------|
| `/continue` | Session elején | Journal betöltés, nyitott taskok, utolsó commit |
| `/wrap-up` | Session végén | Quality gates + journal + CLAUDE.md frissítés |
| `/handoff` | Ha váltasz gépet/sessiont | Átadó dok a következő sessionnek |
| `/commit` | Implementáció után | Quality gates + konvencionális commit üzenet |
| `/develop` | Új feature megírása előtt | Research→Plan→Implement→Commit fázisok |
| `/where-am-i` | Orientációhoz | Snapshot: PT státusz, tesztek, nyitott taskok |
| `/replay <kulcsszó>` | Task előtt | Releváns korábbi tanulságok felszínre hozása |
| `/learn [rule\|correction\|discovery\|decision]` | Tanulságnál | Rögzítés `ifds-rules.md` vagy `learnings-archive.md`-be |
| `/decide` | Döntésnél | Strukturált döntési rekord |
| `/review <fájl>` | Commit előtt | CRITICAL/WARNING/INFO findings + verdikt |
| `/test` | Implementáció közben/után | pytest futtatás + értelmezés |
| `/refactor <fájl>` | Kód minőség vizsgálat | Code smell analízis + priorizált javaslatok |
| `/doctor` | Ha valami nem stimmel | IFDS setup + CC konfiguráció health check |

**Agent delegálás:**
Speciális feladatokhoz: @lead-dev, @code-reviewer, @test-engineer, @refactor, @devops

---

## Journal — Megosztott Kontextus

A `docs/journal/` könyvtár tartalmazza a Claude Chat session-ök állapotmentéseit.
Ezek a stratégiai döntéseket, architektúrális gondolkodást, és a "miértek"-et tartalmazzák.

Session elején a hook automatikusan betölti az utolsó 2 journal entry-t.

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
│   ├── phase5_gex.py           # GEX regime + MMS dispatch
│   ├── phase5_mms.py           # MMS (Market Microstructure Scorer) — factor vol BC16
│   └── phase6_sizing.py        # Position sizing + risk management
├── sim/
│   ├── models.py               # Trade, ValidationSummary, SimVariant, ComparisonReport
│   ├── broker_sim.py           # IBKR bracket simulation
│   ├── validator.py            # L1 forward validation engine
│   ├── replay.py               # L2 parameter sweep orchestrator
│   ├── comparison.py           # L2 paired t-test comparison
│   └── report.py               # Validation + comparison reports
├── output/telegram.py          # Daily Telegram report
├── models/market.py            # All dataclasses and enums
├── utils/
│   ├── trading_calendar.py    # NYSE calendar (exchange_calendars)
│   ├── calendar.py            # Special market days (witching)
│   └── io.py                  # Atomic JSON/Parquet write helpers
└── data/                       # API clients, cache, adapters
    └── phase4_snapshot.py      # Daily Phase 4 data persistence

scripts/paper_trading/          # IBKR paper trading (submit, close, eod, monitor, avwap)
docs/tasks/                     # CC task fájlok (Chat írja, CC implementálja)
docs/planning/                  # Design docs, roadmap, backlog
docs/journal/                   # Chat session állapotmentések (READ ONLY for CC)
docs/qa/                        # QA audit kimenetek (READ ONLY for CC)

.claude/rules/                  # CC rules (permanent, per-session loaded)
.claude/agents/                 # CC agent definitions
.claude/scripts/                # Session hooks (start/end)
```

## Roadmap 2026

Részletes (Phase-alapú struktúra): `docs/planning/roadmap-2026-consolidated.md`

```
Q1 (jan-márc):  BC1-17  — Pipeline + Validation + Crowdedness shadow + Trail Stop A+B
Q2 (ápr-jún):   BC18-23 — EWMA, SIM-L2 Mód 2, Swing Exit, Risk Layer, HRP, ETF BMI
Q3 (júl-szept):  BC24-26 — Black-Litterman, Auto Exec, Multi-Strategy
Q4 (okt-dec):   BC27-30 — Dashboard, Alpha Decay, Retail Packaging
```

**BC struktúra:** BC_xx → Phase_xx → Tasks_xx
Minden BC több Phase-ből áll, minden Phase egy vagy több task fájlhoz köthető.

## Aktuális Kontextus
<!-- CC frissíti a /wrap-up során -->
- **Utolsó journal**: docs/journal/2026-03-11-session-close.md
- **Aktív BC**: BC17 DONE, BC18 planned (~ápr 1)
- **BC18 scope**: Phase_18A EWMA + Crowdedness shadow → Phase_18B MMS factor vol + T5 sizing
- **Nyitott taskok**: nincs (mind DONE)
- **Teszt szám**: 987 passing, 0 failure
- **Utolsó commit**: `1b354e6` — feat(pt_monitor): Scenario B loss-making exit at 19:00 CET
- **Paper Trading**: Day 25 lezárult (cum. PnL +$20.37, +0.020%)
- **MMS aktiválás**: store ≥21 entry/ticker → config toggle (`mms_enabled: True`)
- **PT scriptek**: submit(10), close(11), eod(12), nuke(13), monitor(15), avwap(16)
- **Blokkolók**: nincs
