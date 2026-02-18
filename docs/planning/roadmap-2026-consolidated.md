# IFDS Konszolidált Roadmap 2026

**Utolsó frissítés:** 2026-02-18
**Státusz:** AKTÍV — véglegesítve

---

## Aktuális állapot (2026-02-18)

| Elem | Státusz |
|------|---------|
| Pipeline (Phase 1-6) | ✅ Production (BC16) |
| SIM-L1 Forward Validation | ✅ Kész, adatgyűjtés folyamatban |
| SIM-L2 Mód 1 Parameter Sweep | ✅ Kész (BC19, commit 66242a8) |
| Paper Trading | 🔄 Day 4/21 (IBKR DUH118657) |
| OBSIDIAN Baseline | 🔄 Day 4/21 (aktiválás ~márc 4) |
| Phase 4 Snapshot | ✅ Aktív (gyűjtés holnaptól) |
| Tesztek | 784 passing, 0 failure |

---

## BC Ütemterv

### BC17 — Factor Vol + EWMA + Crowdedness Mérés
**Tervezett:** ~2026-03-04 (OBSIDIAN 21 nap elérése)
**Scope:**
- EWMA smoothing (span=10) a scoring-ban — [D1 Gemini javaslat elfogadva]
- Good/Bad Crowding mérés (shadow mode — mér, nem szűr)
- OBSIDIAN factor volatility aktiválás (21 nap baseline megvan)
- **T5:** BMI extreme oversold (<25%) agresszív sizing zóna

**Előfeltétel:** OBSIDIAN day 21/21 ✅ (márc 4-re meglesz)

### BC18 — Crowdedness Filtering Aktiválás
**Tervezett:** ~2026-03-18
**Scope:**
- Crowdedness composite score élesítése (BC17-ben shadow mode-ban méri)
- Clipping threshold finomhangolás a mért adatok alapján
- **T3:** Bottom 10 explicit negatív szűrő (Phase 4)
- **T9:** Trading calendar earnings exclusion (`pandas_market_calendars`)

**Előfeltétel:** BC17 + 2 hét crowdedness adat

### ~~BC19~~ → KÉSZ (2026-02-18)
SIM-L2 Mód 1 (parameter sweep + Phase 4 snapshot persistence)

### BC20 — SIM-L2 Mód 2 (Re-Score) + T10 A/B
**Tervezett:** ~2026-04-első fele
**Scope:**
- Re-score engine a Phase 4 snapshot-okból
- **T10:** Freshness Alpha vs WOW Signals A/B teszt
- **T7:** New Kid + Repeat bónusz logika validálás
- **T6:** WOW Signals ismétlődő score validálás
- Döntés: Freshness Alpha módosítás production-be megy-e

**Előfeltétel:** Phase 4 snapshot-ok gyűlnek (feb 19-től), minimum 30 nap adat

### BC21 — Risk Layer: Korrelációs Guard + Portfolio VaR
**Tervezett:** ~2026-04-második fele
**Scope:**
- Pozíció-korrelációs guard (ne legyen 5 utility egyszerre)
- Portfolio-szintű VaR kalkuláció
- **T4:** Rotation vs Liquidation megkülönböztetés OBSIDIAN-ban
- Max szektor koncentráció limit

**Eredeti terv:** BC19 volt → eltolódott, mert BC19 = SIM-L2

### BC22 — HRP Allokáció + Riskfolio-Lib
**Tervezett:** ~2026-05
**Scope:**
- Hierarchical Risk Parity allokáció integrálás (Riskfolio-Lib)
- Pozíciószám növelés: 8 → 15
- OBSIDIAN portfólió-szintű regime (ticker→szektor→portfólió)
- Score-alapú allokáció (nem egyenlő súlyozás)

### BC23 — ETF BMI: Broad ETF Flow Intelligence
**Tervezett:** ~2026-05/06
**Scope:**
- **Széles ETF univerzum flow elemzés** (~100-200 ETF, nem csak 11 SPDR)
  - Tematikus ETF-ek (ARKK, SOXX, XBI, TAN, HACK stb.)
  - Size-factor ETF-ek (IWM, MDY, IJR)
  - Regionális / nemzetközi (EEM, VEA, FXI)
  - Fixed income / commodity (TLT, GLD, USO)
- UW `get_etf_in_outflow()` endpoint használata
- ETF flow → szektor rotációs megerősítés (Phase 3 kiegészítés)
- ETF flow → makro regime jelzés (Phase 1 kiegészítés)
- Aggregált intézményi flow heatmap

**Eredet:** HELIOS modul (v1.0), MoneyFlows "ETF 1000 dashboard" kiváltása, UW API feb 2 elemzés
**API:** UW ETF flow endpoint (Basic tierben elérhető)

### BC24 — Score-Implied μ + Black-Litterman Views
**Tervezett:** ~2026-06/07
**Scope:**
- IFDS score → expected return mapping
- Black-Litterman modell: market equilibrium + IFDS views
- FMP analyst estimates integráció
- HRP → BL transition az allokációban

### BC25 — Auto Execution
**Tervezett:** ~2026-07/08
**Scope:**
- Polygon real-time WebSocket → IBKR automatikus order submission
- Paper Trading eredmények alapján élesítés
- Human approval loop (Telegram notification → confirmation)
- Circuit breaker: max napi veszteség, max pozíciószám

### BC26 — Multi-Strategy Framework
**Tervezett:** ~2026-08/09
**Scope:**
- Mean Reversion stratégia (Laggard + OVERSOLD szektorok)
- Momentum stratégia (Leader szektorok, WOW signals)
- Stratégia allokáció a BMI regime alapján
- ETF-szintű kereskedés (nem csak egyedi részvények)

---

## SimEngine Levels

| Level | Státusz | Scope |
|-------|---------|-------|
| **L1** | ✅ Kész (BC16) | Forward validation, egyetlen config |
| **L2 Mód 1** | ✅ Kész (BC19) | Parameter sweep (ATR, hold days) |
| **L2 Mód 2** | BC20 (április) | Re-score, Phase 4 snapshot-okból, T10 A/B |
| **L3** | Q3 (BC24+) | Full backtest, Polygon 20Y history, VectorBT |

---

## MoneyFlows Tanulságok Státusz

| # | Tanulság | Státusz | BC |
|---|----------|---------|-----|
| T1 | Energy szektor gap | ❌ ELENGEDVE — nem elegendő információ | — |
| T2 | Outlier 50 benchmark (+3% alpha, 66% WR) | ✅ AKTÍV — SIM-L1 méri | — |
| T3 | Bottom 10 negatív szűrő | 📋 TERVEZETT | BC18 |
| T4 | Rotation vs Liquidation OBSIDIAN | 📋 TERVEZETT | BC21 |
| T5 | BMI extreme oversold (<25%) sizing | 📋 TERVEZETT | BC17 |
| T6 | WOW Signals validálás | 📋 TERVEZETT | BC20 |
| T7 | New Kid + Repeat Freshness Alpha | 📋 TERVEZETT | BC20 |
| T8 | Félvezető szub-szektor faktor | ❌ ELENGEDVE | — |
| T9 | Trading Calendar earnings exclusion | 📋 TERVEZETT | BC18 |
| T10 | Freshness Alpha vs WOW A/B teszt | 📋 TERVEZETT | BC20 |
| T11 | Company Intelligence Phase 7 | 🔄 Standalone kész, pipeline later | BC24+ |

---

## Párhuzamos Munkafolyamatok

```
Idővonal:
         Feb                  Márc                  Ápr                  Máj            
    ─────┬───────────────────┬───────────────────┬───────────────────┬─────────
         │                   │                   │                   │
Paper    │ ████████████████████████ (21 nap) ████│                   │
Trading  │ Day 4/21          │ KÉSZ márc 9       │ Éles döntés       │
         │                   │                   │                   │
OBSIDIAN │ ███████████████████│ AKTÍV márc 4      │                   │
         │ Day 4/21          │ Day 21 ✓          │                   │
         │                   │                   │                   │
Phase 4  │ █████████████████████████████████████████████████████████████
Snapshot │ Gyűjtés indul     │                   │ BC20 használja    │
         │                   │                   │                   │
BC17     │                   │ ████████          │                   │
         │                   │ márc 4-18         │                   │
         │                   │                   │                   │
BC18     │                   │        ████████   │                   │
         │                   │        márc 18+   │                   │
         │                   │                   │                   │
BC20     │                   │                   │ ████████          │
         │                   │                   │ SIM-L2 Mód 2     │
         │                   │                   │                   │
BC21     │                   │                   │        ████████   │
         │                   │                   │        Risk Layer │
         │                   │                   │                   │
SIM-L1   │ ████████████████████████████████████████████████████████████
Futtatás │ Folyamatos (napi) │ Első benchmark    │ Éles monitoring   │
         │                   │ márc közepe       │                   │
         │                   │                   │                   │
SIM-L2   │                   │ márc 2            │                   │
Comp.    │                   │ First Run ▲       │ BC20 A/B tesztek  │
```

---

## Nyitott Kérdések (frissített)

| # | Kérdés | Státusz |
|---|--------|---------|
| 1 | Energy szektor gap | ❌ LEZÁRVA — elengedve |
| 2 | Portfólió méret (8→15→20) | ⏸ PARKOLT — Paper Trading adatok alapján döntünk (BC22) |
| 3 | FMP tier review | ✅ LEZÁRVA — API_STACK.md kész |
| 4 | Félvezető szub-szektor | ❌ LEZÁRVA — elengedve |
| 5 | VectorBT paraméter sweep | 📋 SimEngine L3 scope (Q3) |
| 6 | Cache TTL fix (stale forward-looking) | 📋 Backlog — workaround: rm -rf |
| 7 | ETF BMI broad universe scope | 📋 BC23 (Q2/Q3) |

---

## Éves Nézet

```
Q1 (jan-márc):  BC1-18 — Pipeline + Validation + Crowdedness         ← MOST ITT
                BC19 KÉSZ (SIM-L2 Mód 1)
Q2 (ápr-jún):   BC20-23 — SIM-L2 Mód 2, Risk Layer, HRP, ETF BMI
Q3 (júl-szept):  BC24-26 — Black-Litterman, Auto Exec, Multi-Strategy
Q4 (okt-dec):   BC27-30 — Dashboard, Alpha Decay, Retail Packaging
```
