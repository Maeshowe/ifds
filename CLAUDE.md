# IFDS — Institutional Flow Decision Suite

## Projekt
Multi-faktoros kvantitatív kereskedési rendszer (swing trading, US equities).
6-fázisú pipeline: BMI regime → Universe → Sectors → Stock Analysis → GEX/MMS → Position Sizing.
Specifikáció: IDEA.md | Pipeline logika: docs/PIPELINE_LOGIC.md | Paraméterek: docs/PARAMETERS.md

## Státusz
- **Production** — Mac Mini cron 22:00 CET (Mon-Fri), `scripts/deploy_daily.sh`
- **BC16 kész** — Phase 1 async (282s→17s), factor volatility framework, SIM-L1 validation engine
- **BC19 kész** — SIM-L2 Mód 1 (parameter sweep + Phase 4 snapshot persistence)
- **861 teszt**, 0 failure, 0 warning
- **BC18-prep kész** — Trading calendar, danger zone filter, cache TTL fix
- **IBKR Connection Hardening kész** — retry logic, timeout, Telegram alert, port konstansok
- **MMS store**: gyűjtés folyamatban (day 8/21, aktiválás ha store >=21 entry/ticker)
- **Paper Trading**: Day 5/21 (IBKR paper account DUH118657, Mac Mini cron, cum. PnL +$278 estimated)
- **Swing Hybrid Exit**: design APPROVED (`docs/planning/swing-hybrid-exit-design.md`)
- **Következő**: BC17 (EWMA + crowdedness mérés + MMS aktiválás) — ha store >=21 entry

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

---

## Session Management (Native CC)

**Session indítás** — automatikus (hook betölti a journal kontextust)

**Session lezárás** — minden munkamenet végén:
/wrap-up

A `/wrap-up` command generálja az összefoglalót és ír egy új journal entry-t
`docs/journal/YYYY-MM-DD-session-close-N.md` formátumban.

Ha a user `/wrap-up`-ot mond ARGUMENTS nélkül, NE kérdezd meg a user-t — generáld az összefoglalót magad az adott session-ből.

**Tanulság rögzítés:**
/learn [rule|discovery|correction] <tartalom>

Rule kategória → `.claude/rules/ifds-rules.md`-be kerül (CC legközelebb olvassa).
Discovery/correction → `docs/planning/learnings-archive.md`-be kerül.

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
│   ├── phase5_mms.py           # MMS (Market Microstructure Scorer) classifier (factor vol BC16)
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
└── data/                       # API clients, cache, adapters
│   └── phase4_snapshot.py      # Daily Phase 4 data persistence

scripts/paper_trading/          # IBKR paper trading (submit, close, eod)
docs/planning/                  # Design docs (SimEngine L2 etc.)
docs/tasks/                     # CC task files
docs/journal/                   # Chat session állapotmentések (READ ONLY)

.claude/rules/                  # CC rules (permanent, per-session loaded)
.claude/agents/                 # CC agent definitions
.claude/scripts/                # Session hooks (start/end)
```

## Roadmap 2026

Részletes: `docs/planning/roadmap-2026-consolidated.md`

```
Q1 (jan-márc):  BC1-18 (pipeline + validation + crowdedness)     ← MOST ITT
                IBKR Connection Hardening KÉSZ (retry, timeout, Telegram alert)
                BC19 KÉSZ (SIM-L2 Mód 1)
Q2 (ápr-jún):   BC20 SIM-L2 Mód 2 + T10 A/B
                BC21 Risk Layer (korrelációs guard + VaR)
                BC22 HRP allokáció (Riskfolio-Lib, 8→15 pozíció)
                BC23 ETF BMI (broad ETF universe flow intelligence)
Q3 (júl-szept):  BC24 Black-Litterman + analyst estimates
                BC25 Auto Execution (Polygon WS → IBKR + long-running mode)
                BC26 Multi-Strategy framework
Q4 (okt-dec):   BC27-30 Dashboard + Alpha Decay + Retail
```

## Aktuális Kontextus
<!-- CC frissíti a /wrap-up során -->
- **Utolsó journal**: docs/journal/2026-02-24-session-close-2.md
- **Aktív BC**: nincs (BC19 kész, BC17 ~márc 4)
- **Feb 26**: QA fixes (asyncio.gather, EOD idempotency, circuit breaker halt, doc sync) + MOC split — 861 teszt
- **Feb 24 deliveries**: EARN oszlop Telegram, Zombie Hunter 2-pass, IBKR Connection Hardening, Telegram Phase 2 breakdown — 848 teszt
- **Aktív egyéb**: Paper Trading Day 6/21 (folyamatban, EOD 22:05 CET), MMS gyűjtés day 9/21, Phase 4 snapshot aktív
- **Swing Hybrid**: design doc APPROVED, implementáció BC20A-ba tervezve
- **Blokkolók**: nincs
- **MMS baseline**: day 9/21 (Feb 11,12,13,17,18,19,20,23,24). Megjelenési ráta ~75% a top tickereknél → 21 entry-hez ~28 run kell (~márc 20). BC17 márc 4: EWMA + crowdedness indul, MMS fokozatosan aktiválódik utána.
- **Paper Trading**: cum. PnL -$61.63 (-0.062%), Day 4/21 lezárva (Feb 17-20). trades_2026-02-20.csv rekonstruálva, cumulative_pnl.json helyreállítva.
- **Következő mérföldkő**: 2026-03-02 SIM-L2 first comparison run (task: docs/tasks/2026-03-02)
