# Session Close — 2026-03-27

## Összefoglaló
Három BC18 follow-up task implementálva: MMS min_periods fix (0→51 aktív ticker), EWMA shadow log (Phase 6 visibility), és 2s10s yield curve spread shadow log (Phase 0 makró kontextus).

## Mit csináltunk
1. **MMS min_periods 21→10** — state/mms/ felmérés: 0 ticker >=21, max PAA 16/30 nap. Root cause: universe rotáció. Fix: `mms_min_periods` 21→10, 51 ticker aktiválódik azonnal.
2. **EWMA shadow log** — Phase 6: per-ticker DEBUG (raw, ewma, prev, delta) + aggregált INFO (count, avg/max delta) + PHASE_COMPLETE data bővítés. 4 teszt.
3. **2s10s yield curve spread** — `FREDClient.get_yield_curve_2s10s()` (T10Y2Y), Phase 0 shadow log (NORMAL/FLATTENING/INVERTED), `MacroRegime` 2 optional mező, Telegram Macro sor bővítve. 10 teszt.

## Döntések
- **mms_min_periods 21→10** — universe rotáció miatt 21 soha nem teljesülne; 10 entry ~2.5 hét, ésszerű minimum
- **yield_curve: shadow only** — 2-3 hétig gyűjtünk, aztán döntünk Szint 2 (küszöbök) / Szint 3 (BC21 integráció) bevezetéséről

## Commit(ok)
- `58ed5a1` — fix(phase5): MMS min_periods 21→10
- `83fc1b9` — feat(phase6): EWMA shadow log
- `45026df` — feat(phase0): 2s10s yield curve spread shadow log

## Tesztek
- 1048 passing, 0 failure (+10 a sessionben)

## Paper Trading
- Day 29 (cum. PnL −$151.28, −0.15%) — veszteséges nap

## Következő lépés
- **CEST swap** (márc 29, holnap): pt_avwap (14-16→15-17), pt_monitor (14-20→15-21) — Mac Mini crontab
- **MMS regime eloszlás** figyelése holnaptól (51 ticker aktív, min_periods=10)
- **BC20** (~ápr első fele): SIM-L2 Mód 2 Re-Score + Freshness A/B + Trail Sim

## Blokkolók
- Nincs
