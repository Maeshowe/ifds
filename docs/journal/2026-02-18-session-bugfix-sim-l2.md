# Journal: 2026-02-18 — Bugfixes + SimEngine L2 Mód 1

## Session Típus
Bugfix + Feature Development + Tervezés

## Elvégzett Munka

### Bug 1: close_positions.py MOC timing fix (commit: pre-66242a8)
- **Probléma:** BHP (51 shares) és EGP (55 shares) overnight carry — entry orders filled AFTER 21:45 CET close_positions.py run
- **Fix:** Cancel all `IFDS_` prefixed open orders BEFORE querying positions for MOC
- **Sorrend:** connect → cancel IFDS orders → sleep(2) → query positions → MOC submit
- 752 tests passing

### Bug 2: OBSIDIAN day counter fix (commit: pre-66242a8)
- **Probléma:** Telegram riport "day 1/21" mutatott 4 egymást követő napon (feb 12-18)
- **Gyökérok:** `_determine_baseline_state()` EMPTY-t ad 21 napig (z-score None ha n < min_periods)
- **Fix:** `baseline_days` mező hozzáadva `ObsidianAnalysis`-hoz, `len(store.load(ticker))`-ból populálva, telegram.py `max(baseline_days)` mutatja
- console.py-ban nem volt day counter — nem kellett módosítani

### BC19: SimEngine L2 Mód 1 — Parameter Sweep (commit: 66242a8)
- **Új fájlok:** replay.py, comparison.py, phase4_snapshot.py + 2 test fájl
- **Módosított:** models.py, report.py, cli.py, defaults.py, pipeline/runner.py
- **+1,364 sor**, 784 teszt (752 + 32 új), 0 failure
- Fixes: numpy bool cast, missing return in write_comparison_csv
- Phase 4 snapshot persistence: gzipped JSON, wired into pipeline runner

### SIM-L2 Tervezés: Design Doc APPROVED
- `docs/planning/simengine-l2-design.md` — véglegesítve
- 5 döntési pont lezárva (scipy mandatory, YAML, BC19 előtt OBSIDIAN, Phase 4 snapshot, 30 trade min)

### Első SIM-L2 Comparison Futtatás
- 3 variáns: baseline (1.5/2/3 ATR), wide_stops (2/3/4), tight_stops (1/1.5/2)
- 62 trade, 50 filled, 3-5 kereskedési nap bar (korai adat)
- Eredmény: baseline -$2037, wide -$1882, tight -$1811
- p-value > 0.6 mindkét challenger-re — nem szignifikáns (kevés adat)
- Leg2 WR = 0% mindenhol — TP2 nem érhető el 5 nap alatt
- **Következő érdemi futtatás: 2026-03-02** (task létrehozva)

### Stale Cache Probléma Azonosítva
- Forward-looking date range cache (`to_date` > today) régi eredményt ad
- Workaround: `rm -rf data/cache/polygon/aggregates` minden futtatás előtt
- Rendszerszintű fix: backlog-ba téve (cache TTL check)

## Döntések

### [D1] scipy mandatory
Telepítve mindkét gépen. Egzakt p-value-val döntünk, nincs szemre ellenőrzés.

### [D2] YAML config variánsokhoz
pyyaml dependency, olvashatóbb mint JSON, comments támogatás.

### [D3] BC19 timing: OBSIDIAN előtt
L2 Mód 1 independent BC17/18-tól. L1-re épít ami kész.

### [D4] Phase 4 re-score: teljes Phase 4 snapshot
Kompromisszum: csak "passed" tickers (~390/nap) snapshot-olása, nem mind 1200. BC19-ben gyűjtés indul, BC20-ban használjuk.

### [D5] Presidents' Day (2026-02-16) NYSE zárva
Megerősítve: feb 16 hétfő ünnep. Kereskedési napok feb 12-től: 12, 13, 17. 3 bar/ticker helyes.

## Tesztek: 784 passing (752 + 32 új)

## Pipeline Státusz
- OBSIDIAN: day 4/21 (fix deployed, holnaptól helyes counter)
- Paper Trading: Day 2 (close_positions fix deployed, 21:45 CET-re aktív)
- Phase 4 Snapshot: aktív (holnapi pipeline futtatáskor első snapshot)

## Következő Lépések
1. 2026-03-02: SIM-L2 first meaningful comparison (task: `docs/tasks/2026-03-02-sim-l2-first-comparison-run.md`)
2. BC17 (márc 4): EWMA + crowdedness + OBSIDIAN aktiválás
3. Cache TTL fix: backlog (nem blokkoló)
4. BHP/EGP: ma 21:45-kor close_positions.py kezeli (ha még nyitva vannak)

## Fájlok
- Design doc: `docs/planning/simengine-l2-design.md` (APPROVED)
- Bugfix task: `docs/tasks/2026-02-18-bugfix-close-positions-obsidian-day.md`
- BC19 task: `docs/tasks/2026-02-18-sim-l2-mode1-parameter-sweep.md`
- Márc 2 task: `docs/tasks/2026-03-02-sim-l2-first-comparison-run.md`
- Test YAML: `sim_variants_test.yaml`
