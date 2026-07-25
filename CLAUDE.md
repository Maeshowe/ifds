# IFDS — Institutional Flow Decision Suite

## Projekt
Multi-faktoros kvantitatív kereskedési rendszer (swing trading, US equities).
6-fázisú pipeline: BMI regime → Universe → Sectors → Stock Analysis → GEX/MMS → Position Sizing.
Specifikáció: IDEA.md | Pipeline logika: docs/PIPELINE_LOGIC.md | Paraméterek: docs/PARAMETERS.md

## Státusz

> ⚠️ **Élő állapot: `docs/STATUS.md`** — az EGYETLEN dinamikus állapotfájl (session-start hook betölti).
> Teszt-szám, paper trading nap, cumulative P&L, nyitott tételek, következő mérföldkő: **mind ott**.
> Itt SOHA ne duplikáld — a korábbi inline státusz-blokk 3,5 hónapig elavultan élt (1291 teszt vs. valós 2182;
> Day 33 vs. valós 47), és félreorientálta a friss sessionöket.

- **Production** — Mac Mini, split pipeline: Phase 1-3 (22:00) + Phase 4-6 (15:45 Budapest)
- **Architektúra** — swing pivot (2026-05-18 óta): 5-napos hold, mentális stop, MKT entry.
  A BC1–BC21 + BC20A (Swing Hybrid Exit) alapréteg kész; részletek: `CHANGELOG.md`.
- **Paper trading** — IBKR paper `DUH118657`, 63 napos periódus. Aktuális nap/P&L: `docs/STATUS.md`.
- **Parameter freeze** — Day 63-ig érvényes (kivételek + log: `docs/master-reference/04-risks-and-open-questions.md` §11).

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

> **2026-07-25 — IFDS = CC-only, egyelőre** (Tamás-döntés): a Dev/Chat-szál szüneteltetve; CC felel a teljes
> review-stackért (napi + heti `weekly_metrics.py` + biweekly `scoring_validation.py` + interpretáció) és
> minden IFDS operatív munkáért (task-írás, bugfix, FRL, journal, STATUS). Az epistemikus guardrailek
> (freeze, G1 gate-szeparáció, G3 no-signal-validity-nyelv Day 63-ig, pre-reg) VÁLTOZATLANOK. Lásd memória:
> [[division-of-labor-chat-cc]]. Reverzibilis („egyelőre").

A taskok a `docs/tasks/YYYY-MM-DD-*.md` fájlokban élnek (a CC-only alatt CC írja és implementálja).
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
grep -lE "^Status:[[:space:]]*(OPEN|WIP)" docs/tasks/*.md 2>/dev/null
```

> **Archive konvenció**: lezáráskor (`Status: DONE`/`REJECTED`) a task `git mv`-vel
> a `docs/tasks/archive/`-ba kerül; a gyökérben csak aktív task marad. A lekérdezés
> nem rekurzív (`*.md` glob) és a `^Status:` header-sorra horgonyoz (egy body-ban
> idézett "Status: OPEN" string ne okozzon false-positive-ot). Lásd `docs/tasks/archive/README.md`.

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

A `docs/journal/` könyvtár tartalmazza a session-ök állapotmentéseit (stratégiai döntések, architektúrális
gondolkodás, a "miértek").

Session elején a hook automatikusan betölti az utolsó 2 journal entry-t.

**2026-07-25 óta (CC-only): a journalt CC írja** a `/wrap-up`-kor (`docs/journal/YYYY-MM-DD-session-close.md`).
Korábban a Chat-szál termelte; a Dev-szál szüneteltetéséig CC a szerző is. A korábbi Chat-journalok
READ-ONLY referenciák maradnak.

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
│   ├── phase6_sizing.py        # Position sizing + risk management + VWAP guard + corr guard
│   └── vwap.py                 # VWAP module (5-min bars, entry quality filter)
├── risk/
│   ├── cross_asset.py          # Cross-Asset Regime (HYG/IEF, RSP/SPY, IWM/SPY + 2s10s)
│   └── portfolio_var.py        # Parametric VaR, position trimming
├── sim/
│   ├── models.py               # Trade (+ swing fields), SimVariant, ComparisonReport
│   ├── broker_sim.py           # Bracket + swing simulation (TP1 partial, trail, breakeven)
│   ├── rescore.py              # Mode 2 re-score engine (Phase 4 snapshot → config variants)
│   ├── wow_freshness.py        # U-shaped freshness (New Kid, WOW, Stale, Persistent)
│   ├── validator.py            # L1 forward validation + sim_mode dispatch
│   ├── replay.py               # L2 parameter sweep + Mode 2 re-score comparison
│   ├── comparison.py           # L2 paired t-test comparison
│   └── report.py               # Validation + comparison reports
├── state/
│   ├── position_tracker.py     # OpenPosition + PositionTracker (JSON CRUD)
│   ├── swing_manager.py        # Swing lifecycle (breakeven, trail, max hold, earnings)
│   └── history.py              # BMI history persistence
├── pipeline/
│   ├── runner.py               # Pipeline orchestrator (--phases split, trading day guard)
│   └── context_persistence.py  # Phase 1-3 context save/load (gzipped JSON)
├── output/telegram.py          # Telegram (macro snapshot + trading plan + daily report)
├── models/market.py            # All dataclasses and enums (40+ types)
├── utils/
│   ├── trading_calendar.py     # NYSE calendar (exchange_calendars, trading days)
│   ├── calendar.py             # NYSE holidays, early close, witching days
│   └── io.py                   # Atomic JSON/Parquet write helpers
└── data/                       # API clients, cache, adapters
    └── phase4_snapshot.py      # Daily Phase 4 snapshot + snapshot_to_stock_analysis()

scripts/paper_trading/          # IBKR paper trading (submit, close, eod, monitor)
scripts/paper_trading/lib/      # Shared: log_setup, event_logger, trading_day_guard, telegram_helper
scripts/tools/                  # events_to_sqlite.py
scripts/deploy_daily.sh         # Phase 1-3 (22:00) or full pipeline
scripts/deploy_intraday.sh      # Phase 4-6 + submit (15:45)
sim/configs/                    # YAML variant configs (1d vs swing, freshness A/B, etc.)
docs/tasks/                     # CC task fájlok (CC-only óta CC írja+implementálja)
docs/planning/                  # Design docs, roadmap, backlog
docs/journal/                   # session állapotmentések (CC-only óta CC írja /wrap-up-kor)
docs/CODEMAPS/                  # Architecture docs (architecture, backend, data, dependencies)
```

## Roadmap 2026

Részletes (Phase-alapú struktúra): `docs/planning/roadmap-2026-consolidated.md`

```
Q1 (jan-márc):  BC1-18 + quick wins — Pipeline, Validation, MMS, EWMA, Crowdedness shadow, TP1/VIX SL/M_target/BMI guard
Q2 (ápr-jún):   BC20-23 — SIM-L2 Mód 2 (~ápr 7-18), Swing Exit (~ápr 21-máj 9), Risk Layer (~máj 11-22), HRP (~máj 25-jún 6), ETF Flow (~jún 8-27)
Q3 (júl-szept):  BC24-26 — Black-Litterman, Auto Exec, Multi-Strategy
Q4 (okt-dec):   BC27-30 — Dashboard, Alpha Decay, Retail Packaging
```

**BC struktúra:** BC_xx → Phase_xx → Tasks_xx
Minden BC több Phase-ből áll, minden Phase egy vagy több task fájlhoz köthető.

## Aktuális Kontextus
→ **Élő státusz:** `docs/STATUS.md` (automatikusan betöltődik session-start hook-kal)
→ **Backlog:** `docs/planning/backlog.md`

Stabil referencia (ritkán változik):
- Teszt baseline: 1291 passing (2026-04-03) — csak nőhet
- PT account: IBKR DUH118657, $100K initial, 63 napos paper trading periódus
- PT clientId-k: submit=10, close=11, eod=12, nuke=13, monitor=14, trail=15, avwap=16, gateway=17
- MMS: `mms_enabled=True`, `factor_volatility_enabled=True`, `mms_min_periods=10`
- TP1: `tp1_atr_multiple=0.75`
- Pipeline split: Phase 1-3 (22:00 Budapest) + Phase 4-6 (15:45 Budapest)
- Swing: 5-day hold, MKT entry, VWAP guard, PositionTracker, breakeven + trail
- Risk: Cross-Asset Regime, Correlation Guard, Portfolio VaR 3%
- Deployment: `docs/tasks/2026-04-03-monday-deployment-checklist.md`
- Crontab: `scripts/crontab.md`
