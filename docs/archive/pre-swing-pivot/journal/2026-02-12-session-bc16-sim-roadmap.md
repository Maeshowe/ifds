# Journal: 2026-02-12 — BC16, SIM-L1, Roadmap, Claude Környezet

## Session Típus
Implementáció + Stratégiai Tervezés

## Elvégzett Munka

### BC16 Complete (commit: 023aade → 1b2e946)
- Phase 1 async BMI: 282s → 16.7s (17× gyorsulás)
- Semaphore tuning: FMP=8, Polygon=10 (FMP 12-nél HTTP 429)
- Factor volatility framework: VOLATILE regime, regime_confidence, OBSIDIAN store
  - `factor_volatility_enabled: False` — aktiválás márc. 4 (21 nap baseline)
- Freshness Alpha fix: `min(100.0, ...)` cap eltávolítva, score range 0-150
- Összesen: 294s → 130s (2.3× teljes speedup)

### SIM-L1 Forward Validation Engine (commit: 1b2e946)
- `src/ifds/sim/` modul: models, broker_sim, validator, report
- IBKR bracket order szimuláció: 33/66 split, fill window=1 nap
- Pesszimista: same-day TP+Stop → Stop
- Async Polygon fetch, FileCache, 10 napos horizont
- Level 2/3 ready architektúra
- 752 teszt (24 új), 0 failure

### Tesztek: 752 passing

## Döntések

### [D1] Gemini PG elemzés értékelése
- **Expected Performance Matrix**: spekulatív, nincs backtest mögötte → ignorálni
- **Fat Finger / TWAP**: félreérti a rendszert (max_order_quantity = darab, nem dollár)
- **EWMA javaslat**: ELFOGADVA → BC17-be beépítjük (ewma_span=10)
- **Good/Bad Crowding**: ELFOGADVA → BC17 crowdedness composite-ba
- **Shadow Mode**: már tervben van (BC17 mér, BC18 szűr)

### [D2] SimEngine nem fut folyamatosan
- Napi egyszeri futtatás: `python -m ifds validate --days 10`
- Első érdemi futtatás: ~feb. 19 (5+ nap adat)

### [D3] Platform alternatívák (QuantRocket, QuantConnect, Portfolio123)
- **ELVETETTÜK**: az IFDS specifikus adatforrásai (UW, GEX, OBSIDIAN) egyik sem támogatja
- Custom rendszer marad, de ipari komponensek (Riskfolio-Lib) integrálása jön

### [D4] Hosszú távú vízió: Signal Generator → Portfolio Management
- Fázis 1 (BC19-20): Korrelációs guard + Portfolio VaR
- Fázis 2 (BC21-22): HRP allokáció (Riskfolio-Lib, 8→20 pozíció)
- Fázis 3 (BC23+): Score-Implied μ + Black-Litterman
- OBSIDIAN szerepe minden fázisban nő (ticker→portfólió→allokáció szint)

### [D5] Claude Környezet Refaktor
- Journal → repo (megosztott kontextus Chat ↔ CC)
- CLAUDE.md frissítve (CC operációs kézikönyv)
- Agent refaktor: 10 → 6 aktív CC agent, stratégiai agent-ek → Chat
- Wrap-up: CC auto-generálja a summary-t

## OBSIDIAN Státusz
- Store: day 2/21
- Aktiválás: ~2026-03-04
- Factor volatility: implementálva, disabled

## Következő Lépések
1. ✅ Journal → repo struktúra (ez a fájl)
2. ✅ CLAUDE.md frissítés (elkészült)
3. BC17 prompt frissítés (EWMA + good/bad crowding hozzáadva)
4. Agent refaktor (AGEN-1 jelöléssel, BC17 mellett)
5. SIM-L1 első futtatás: ~feb. 19
6. BC17 indítás: ~márc. 4

## Nyitott Kérdések
- FMP API tier review: magasabb tier vagy alternatíva (Tiingo, EOD)?
- Portfólió pozíciószám: mikor 8→15→20?
- VectorBT paraméter sweep: SimEngine Level 3 scope?

## Roadmap 2026

```
Q1: BC1-18 (pipeline + validáció + crowdedness)    ← ITT TARTUNK
Q2: BC19-22 (risk layer + HRP + SimEngine L2-L3)
Q3: BC23-26 (BL + auto execution + multi-strategy)
Q4: BC27-30 (dashboard + alpha decay + retail packaging)
```
