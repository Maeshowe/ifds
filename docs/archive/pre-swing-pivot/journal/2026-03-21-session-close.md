# Session Close — 2026-03-21

## Összefoglaló
BC18 teljes egészében implementálva (MMS activation, factor vol, T5 sizing, EWMA smoothing, crowdedness shadow). Witching day calendar, AVWAP limit-to-market, Scenario B loss exit is elkészült. Q1 roadmap (BC1-18) lezárva, BC20 következik.

## Mit csináltunk
1. **Witching Day Calendar** — `src/ifds/utils/calendar.py`, submit_orders.py witching check + `--override-witching` flag, 10 teszt
2. **AVWAP Limit→MKT** — `scripts/paper_trading/pt_avwap.py` (clientId=16), state machine (IDLE→WATCHING→DIPPED→DONE), bracket rebuild, 15 teszt
3. **Scenario B Loss Exit** — 25-day data analysis (119 MOC trades, Polygon 1-min bars), -2.0% threshold elfogadva (+$457 net, 64% win), `cancel_all_orders()` + MKT SELL, 5 teszt
4. **BC18 Phase_18B** — `mms_enabled: True`, `factor_volatility_enabled: True`, T5 BMI oversold sizing (<25% → ×1.25), 8 teszt
5. **BC18 Phase_18A/1** — EWMA score smoothing (span=10), `_ewma_score()` + state persistence, 9 teszt
6. **BC18 Phase_18A/2** — Crowdedness shadow mode, `compute_crowding_score()` ∈ [-1,+1], Decision B+C+C, 11 teszt
7. **BC18 task files** — 3 task fájl létrehozva, mind DONE-ra zárva
8. **Docs** — CLAUDE.md, roadmap, MEMORY.md frissítve

## Döntések
- **Scenario B loss threshold: -2.0%** — 25-day paper trading data analysis alapján. -0.5% (eredeti javaslat) negatív net impact (-$424), -2.0% pozitív (+$457, 64% win rate)
- **Crowdedness B+C+C** — dark_share > 0.55, gradiens bad crowding (< -0.7 kiszűr, közepes penaltyzik), no good boost
- **MMS aktiválás** — 25-day baseline (21 volt a minimum), config flag flip
- **AVWAP crontab** — `*/1 14-16 * * 1-5` (CET), március 29-től `*/1 15-17 * * 1-5` (CEST)

## Commit(ok)
- `233fd39` — feat(calendar): add witching day detection and order submission skip
- `18ab724` — feat(pt_avwap): AVWAP-based limit-to-market conversion
- `1b354e6` — feat(pt_monitor): Scenario B loss-making exit at 19:00 CET
- `e4bd7ef` — docs: update CLAUDE.md
- `a077b65` — docs(tasks): create BC18 task files
- `332e4fb` — feat(phase6): activate MMS regime multipliers and factor volatility (BC18B)
- `47d395e` — feat(phase6): EWMA score smoothing (BC18A, span=10)
- `b700c18` — feat(phase5): crowdedness shadow mode (BC18A)
- `38409f2` — docs: milestone update — BC18 DONE

## Tesztek
- 1015 passing, 0 failure (+58 a sessionben, 957→1015)

## Paper Trading
- Day 25 lezárult (cum. PnL +$20.37, +0.020%)
- PT scriptek: submit(10), close(11), eod(12), nuke(13), monitor(15), avwap(16)
- Mac Mini crontab: pt_avwap.py hozzáadandó (*/1 14-16 * * 1-5 CET)

## Következő lépés
- **BC20** (~ápr első fele): SIM-L2 Mód 2 Re-Score + Freshness A/B + Trail Sim
- **Config élesítés** (manuális, Tamás): `ewma_enabled: True`, `crowdedness_shadow_enabled: True`
- **CEST átállás** (márc 29): pt_avwap crontab módosítás (14-16 → 15-17), pt_monitor (14-20 → 15-21)

## Blokkolók
- Nincs
