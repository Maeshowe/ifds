# Session Close — 2026-03-26

## Összefoglaló
BC18 follow-up taskok: MMS min_periods 21→10 (universe rotation fix, 51 ticker aktiválódik) + EWMA shadow log (per-ticker DEBUG + aggregált INFO a pipeline logban).

## Mit csináltunk
1. **MMS Undetermined Investigation** — state/mms/ felmérés: 863 ticker, max 16 entry (PAA), 0 ticker >=21. Root cause: universe rotáció, tickerek nem maradnak bent 21 napig. Fix: `mms_min_periods` 21→10, 51 ticker aktiválódik azonnal.
2. **EWMA Shadow Log** — Phase 6-ban per-ticker DEBUG log (raw, ewma, prev, delta) + aggregált INFO log (count, avg/max delta) + PHASE_COMPLETE data bővítés (ewma_applied, ewma_avg_delta). 4 új teszt.
3. **Task status audit** — 2026-03-07-phase00 task DONE-nak jelölve (grep false positive a body-ban)

## Döntések
- **mms_min_periods 21→10** — trade-off: kevésbé stabil z-score 10 megfigyelésből, de az eredeti 21 soha nem teljesül universe rotáció miatt. 10 entry ~2.5 hét adat, ésszerű minimum.

## Commit(ok)
- `58ed5a1` — fix(phase5): MMS min_periods 21→10 — universe rotation prevented activation
- `83fc1b9` — feat(phase6): add EWMA shadow log for daily review visibility

## Tesztek
- 1038 passing, 0 failure (+4 a sessionben)

## Paper Trading
- Day 28 (cum. PnL +$307.75, +0.31%)

## Következő lépés
- **Mac Mini**: git pull (3 commit ahead) — MMS min_periods + EWMA log aktiválódik holnapi pipeline futásnál
- **Mac Mini CEST swap** (márc 29): pt_avwap (14-16 → 15-17), pt_monitor (14-20 → 15-21)
- **BC20** (~ápr első fele): SIM-L2 Mód 2 Re-Score + Freshness A/B + Trail Sim
- **MMS**: holnaptól 51 ticker aktiválódik (min_periods=10), figyelni a regime eloszlást

## Blokkolók
- Nincs
