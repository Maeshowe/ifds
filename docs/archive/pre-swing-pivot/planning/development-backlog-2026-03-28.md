# IFDS — Hátralévő Fejlesztések Összefoglaló

**Dátum:** 2026-03-28
**Aktuális állapot:** BC18 DONE, 1054+ teszt, Paper Trading Day 30/63

---

## Ami KÉSZ van (BC1-18 + quick wins)

| BC | Tartalom | Státusz |
|---|---|---|
| BC1-16 | Pipeline (Phase 0-6), API-k, async, SIM-L1, factor vol framework | ✅ |
| BC17 | Preflight, monitor_positions, Trail Stop A+B | ✅ |
| BC18 | EWMA, MMS activation (min_periods 10), Crowdedness shadow, T5, Factor Vol | ✅ |
| BC19 | SIM-L2 Mód 1 parameter sweep + Phase 4 snapshot | ✅ |
| Quick wins | TP1 0.75×ATR, VIX SL cap, 2s10s shadow, EWMA log, contradiction penalty, BMI guard | ✅ |

**Élesben futó feature-ök:** EWMA simítás, MMS multiplierek (51 ticker), TP1 0.75×ATR,
VIX-adaptív SL cap, contradiction penalty (M_target), BMI momentum guard,
crowdedness shadow log, 2s10s yield curve shadow log.

---

## Q2 — Április-Június (~3 hónap)

### BC20 — SIM-L2 Mód 2 + A/B Teszt + Trail SIM (~ápr 7-18)
**Prioritás:** P2 | **Becsült:** ~12 óra CC
**SORREND: BC20 ELŐBB mint BC20A** — az M_target és BMI guard hatását csak
szimulációval lehet visszamenőleg mérni. Ha a Swing Exit jön előbb,
elveszítjük a baseline-t az összehasonlításhoz.

| Phase | Tartalom | Előfeltétel |
|---|---|---|
| 20A | Re-Score Engine — Phase 4 snapshot-okból újraszámolás más config-gal | BC18 DONE ✅ |
| 20B | T10 A/B Teszt — Freshness Alpha (lineáris) vs WOW Signals (U-alakú) | 20A kész |
| 20C | Trail SIM — broker_sim.py multi-day + partial exit szimulálás | 20A kész |

**Miért fontos:** Amíg nincs Mód 2, nem tudjuk tudományosan mérni, hogy az EWMA,
MMS, contradiction penalty ténylegesen javít-e a scoring-on. Jelenleg "érzésre"
nézzük a review-kban.

---

### BC20A — Swing Hybrid Exit (~ápr 21 — máj 9)
**Prioritás:** P2 | **Becsült:** ~25-30 óra CC (korábbi 21h optimista) | **Design:** `swing-hybrid-exit-design.md`

Ez az **igazi game changer** — az 1-napos MOC exit rendszerből swing trading-re váltás.
A Position Tracker teljesen új state management komponens, és az async path frissítése
Phase 4/6-ban további effort.

| Phase | Tartalom | Effort |
|---|---|---|
| 20A_1 | VWAP Modul — Polygon 5-min bars, entry quality filter | 2h |
| 20A_2 | Position Tracker — `state/open_positions.json`, hold day, TP1 status | 3h |
| 20A_3 | Pipeline Split + MKT Entry — Phase 1-3 (22:00) / Phase 4-6 (15:45) + MKT entry | 3h |
| 20A_4 | close_positions.py Swing — hold tracking, breakeven SL, TRAIL, max D+5 | 3h |
| 20A_5 | SimEngine Swing — broker_sim multi-day, partial exit, trail szimulálás | 4h |
| — | Async path frissítés — Phase 4 VWAP fetch + Phase 6 swing sizing integráció | 3h |
| — | Tesztelés — unit + integration (Position Tracker, SimEngine Swing, pipeline split) | 5h |
| — | Puffer — review, debug, edge cases (D+5 rollover, partial fill, breakeven edge) | 5h |
| **Összesen** | | **~28h** |

**Amit megold:**
- MOC exit dominancia (30 napból 22-ben minden trade MOC-on zárt)
- AVWAP slippage (limit→MKT váltás, garantált fill)
- TP2 soha nem érhető el (trail stop helyettesíti)
- Pozíciók 5 napig nyitva maradhatnak (swing hold)

---

### BC21 — Risk Layer + Cross-Asset Regime (~máj 11-22)
**Prioritás:** P2 | **Becsült:** ~10 óra CC

| Phase | Tartalom |
|---|---|
| 21A | Korrelációs Guard + Portfolio VaR — ne legyen 5 utility egyszerre |
| 21B | Cross-Asset Regime — HYG/IEF, RSP/SPY, IWM/SPY szavazás + 2s10s (4. szavazó) |

**Amit megold:**
- BMI momentum guard jelenleg "gyors fix" → a Cross-Asset Regime az igazi megoldás
- 2s10s yield curve shadow → Szint 2 küszöbök + Szint 3 integráció
- Portfolio VaR → nem csak ticker-szintű risk, hanem portfólió-szintű

---

### BC22 — HRP Allokáció (~máj 25 — jún 6)
**Prioritás:** P2 | **Becsült:** ~8 óra CC

| Phase | Tartalom |
|---|---|
| 22A | Hierarchical Risk Parity — Riskfolio-Lib, score-alapú allokáció |
| 22B | Pozíciószám bővítés 8→15 — exposure limit recalibráció |

---

### BC23 — ETF Flow Intelligence (~jún 8-27)
**Prioritás:** P2 | **Becsült:** ~12 óra CC

| Phase | Tartalom |
|---|---|
| 23A | ETF Flow Intelligence — UW ETF in/outflow, szektor rotáció megerősítés |
| 23B | L2 Szektoros Finomítás — 42 ETF, szektor-szintű momentum rangsor |
| 23C | MCP Server Alap — IFDS pipeline introspekció API |

---

## Q3 — Július-Szeptember

### BC24 — Black-Litterman + Company Intel v2
**Prioritás:** P3

| Phase | Tartalom |
|---|---|
| 24A | Score→Expected Return mapping, Black-Litterman modell, HRP→BL transition |
| 24B | MCP-alapú Company Intel v2, adjusted EPS, short interest, napi auto futás |

### BC25 — Auto Execution
**Prioritás:** P3

| Phase | Tartalom |
|---|---|
| 25A | Polygon WebSocket + IBKR auto submit + Telegram human approval loop |
| 25B | IBGatewayManager long-running — heartbeat, reconnect, watchdog |

### BC26 — Multi-Strategy Framework
**Prioritás:** P3

| Phase | Tartalom |
|---|---|
| 26A | Mean Reversion stratégia — Laggard + OVERSOLD szektorok |
| 26B | ETF-szintű kereskedés — momentum stratégia |

---

## Q4 — Október-December

### BC27-30 — Dashboard + Alpha Decay + Retail Packaging
**Prioritás:** P3 | Még nincs részletes scope

- Dashboard (web UI a pipeline eredményekhez)
- Alpha Decay monitoring (a stratégia hatékonysága idővel)
- Retail Packaging (ha éles kereskedésre váltunk)

---

## SimEngine Roadmap

| Level | Státusz | BC |
|---|---|---|
| L1 Forward Validation | ✅ Kész | BC16 |
| L2 Mód 1 Parameter Sweep | ✅ Kész | BC19 |
| L2 Mód 2 Re-Score | Következő | BC20 |
| L2 Trail Szimuláció | Következő | BC20 |
| L3 Full Backtest (VectorBT) | Q3 | BC24+ |

---

## Shadow Mode Feature-ök (adatgyűjtés, nincs hatás)

Ezek most logolnak, de nem hatnak a scoring/sizing-ra. 2-3 hét adat után döntünk az élesítésről:

| Feature | Shadow óta | Élesítés | Megjegyzés |
|---|---|---|---|
| Crowdedness composite score | 2026-03-23 | ~ápr 7 (2 hét adat), BC20 ELŐTT is jöhet | B+C+C döntés kész |
| 2s10s Yield Curve | 2026-03-27 | ~ápr 10 (2 hét), élesítés BC21-ben (~máj) | Természetes helye ott van |
| EWMA score delta log | 2026-03-27 | Már aktív (monitoring) | — |

---

## Nyitott Design Döntések

| # | Kérdés | Mikor kell dönteni |
|---|---|---|
| 1 | Crowdedness élesítés (shadow→active) — B+C+C működik? | ~ápr 7 (2 hét shadow adat márc 23-tól) |
| 2 | 2s10s Szint 2 küszöbök | ~ápr 10 (2 hét shadow adat márc 27-től) |
| 3 | ~~BC20A indítás timing~~ | **ELDÖNTVE: BC20 (SIM) előbb, baseline megőrzés** |
| 4 | Paper trading → éles kereskedés váltás | Day 63 (~máj 14) + kiértékelés |
| 5 | Pozíciószám 8→15 | BC22, paper trading adatok alapján |

---

## Összesített becsült effort

| Időszak | BC-k | Becsült CC effort |
|---|---|---|
| Április (ápr 7 — ápr 30) | BC20 + BC20A eleje | ~35-40 óra |
| Május (máj 1 — máj 31) | BC20A vége + BC21 + BC22 | ~25-30 óra |
| Június (jún 1 — jún 30) | BC23 | ~12 óra |
| Júl-Szept | BC24-26 | ~30 óra |
| Okt-Dec | BC27-30 | TBD |
| **Összesen Q2-Q3** | | **~100-110 óra** |

---

## Legfontosabb kérdés

**Nem a BC sorrend a legégetőbb**, hanem: a paper trading mostani -0.57% drawdown
mit mutat az új feature-ökkel? Az M_target, BMI momentum guard, TP1 0.75×ATR,
VIX SL cap, MMS multiplierek (51 ticker) és EWMA simítás **mind hétfőtől élesben**.
Az április végi review (Day ~50/63) megmutatja:
- Javult-e a TP1 hit rate (0.75×ATR vs korábbi 2×ATR)?
- Az M_target penalty csökkentette-e a contradiction veszteségeket?
- A BMI guard működött-e csökkenő BMI trend esetén?
- Az MMS multiplierek (51 ticker aktív) javult-e a méretezés?
- A piac recovery fázisában hogyan teljesít a rendszer?

Ezeket az adatokat a BC20 SIM-L2 Mód 2 fogja tudományosan mérni a baseline-nal
összehasonlítva.
