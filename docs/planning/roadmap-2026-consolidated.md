# IFDS Konszolidált Roadmap 2026

**Utolsó frissítés:** 2026-02-24
**Státusz:** AKTÍV — véglegesítve

---

## Aktuális állapot (2026-02-24)

| Elem | Státusz |
|------|---------|
| Pipeline (Phase 1-6) | ✅ Production (BC16) |
| SIM-L1 Forward Validation | ✅ Kész, adatgyűjtés folyamatban |
| SIM-L2 Mód 1 Parameter Sweep | ✅ Kész (BC19, commit 66242a8) |
| Paper Trading | 🔄 Day 6/21 (IBKR DUH118657, cum PnL -$61.63) |
| OBSIDIAN Baseline | 🔄 Day 9/21 (461 ticker, max 7 entry/ticker, 0 ticker >=21) |
| Phase 4 Snapshot | ✅ Aktív (gyűjtés feb 19-től) |
| IBKR Connection Hardening | ✅ Kész (retry 3x, timeout 15s, Telegram alert) |
| Zombie Hunter 2-pass | ✅ Kész (bulk + ticker-specific earnings exclusion) |
| Telegram EARN oszlop | ✅ Kész (per-ticker FMP earnings date) |
| Tesztek | 848 passing, 0 failure, 0 warning |
| Swing Hybrid Exit | ✅ Design APPROVED |

---

## BC Ütemterv

### BC17 — Factor Vol + EWMA + Crowdedness Mérés + OBSIDIAN Aktiválás
**Tervezett:** ~2026-03-04 (OBSIDIAN 21 nap elérése)
**Scope:**
- EWMA smoothing (span=10) a scoring-ban — [D1 Gemini javaslat elfogadva]
- Good/Bad Crowding mérés (shadow mode — mér, nem szűr)
- OBSIDIAN factor volatility aktiválás (21 nap baseline megvan)
- **T5:** BMI extreme oversold (<25%) agresszív sizing zóna
- **OBSIDIAN rezsim multiplier értékek élesítése Phase 6-ban:**
  | Rezsim | Multiplier | Indoklás |
  |--------|-----------|----------|
  | Γ⁺ (gamma_positive) | 1.0–1.05 | Stabil, alacsony vol környezet — nem veszélyes |
  | Γ⁻ (gamma_negative) | 0.6–0.7 | Dealer short gamma, amplifikált mozgások — érdemi kockázat |
  | DD (dark_dominant) | 1.1–1.15 | Intézményi akkumuláció — pozitív signal (feltéve: DP adat megbízható) |
  | ABS (absorption) | 1.05–1.1 | Passzív felszívás — pozitív LONG-ban |
  | DIST (distribution) | 0.85 | Smart money elad — negatív, de nem akut (Γ⁻ + DIST = 0.7×0.85 = 0.595, nem túl agresszív) |
  | VOLATILE | 0.75 | Instabil rezsim — óvatosság |
  | NEU (neutral) | 1.0 | Nincs hatás |
  | UND (undetermined) | 1.0 | Nincs hatás (baseline gyűjtés közben) |
- **OBSIDIAN dark pool küszöb kalibráció:** A DD (`dark_share > 0.70`) és ABS (`dark_share > 0.50`) küszöbök az eredeti aetherveil rendszerből származnak, ir-reálisan magasak a jelenlegi UW batch adatokhoz képest (tipikus dark_share: 0.001-0.005). 21 nap adat alapján az eloszlást kiértékeljük és a küszöböket újrakalibráljuk. Emellett: UW batch `max_pages` (15→30-50) növelés mérlegelése a jobb DP coverage-ért.

**OBSIDIAN store helyzet (2026-02-21):** 461 ticker, 8 pipeline run, max 6 entry (AQN). Megjelenési ráta a top tickereknél ~75% (6/8 run). 21 entry-hez ~28 run kell → első tickerek ~márc 20 körül érik el. Aktiválás fokozatos: a stabil, visszatérő tickerek kapnak először z-score-t — ez kívánt viselkedés a swing trading universe-ben. BC17 márc 4-re indul (EWMA + crowdedness), OBSIDIAN fokozatosan aktiválódik utána.

**Előfeltétel:** OBSIDIAN store gyűjtés folyamatos (márc 4-re ~12 run, első 21-es küszöb ~márc 20)

### BC18 — Crowdedness Filtering Aktiválás
**Tervezett:** ~2026-03-18
**Scope:**
- Crowdedness composite score élesítése (BC17-ben shadow mode-ban méri)
- Clipping threshold finomhangolás a mért adatok alapján
- ~~**IBKR connection hardening**~~ → ✅ KÉSZ (2026-02-24, commit aa22f5a)
  - Retry (3x, 5s delay, 15s timeout), Telegram alert, env var override
  - Port konstansok: PAPER_PORT=7497, LIVE_PORT=7496
- ~~**T3:** Bottom 10 explicit negatív szűrő~~ → ✅ KÉSZ (BC18-prep, 2026-02-18)
- ~~**T9:** Trading calendar earnings exclusion~~ → ✅ KÉSZ (BC18-prep, 2026-02-18)

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

### BC21 — Risk Layer: Korrelációs Guard + Portfolio VaR + Cross-Asset Rezsim
**Tervezett:** ~2026-04-második fele
**Scope:**
- Pozíció-korrelációs guard (ne legyen 5 utility egyszerre)
- Portfolio-szintű VaR kalkuláció
- **T4:** Rotation vs Liquidation megkülönböztetés OBSIDIAN-ban
- Max szektor koncentráció limit
- **Cross-asset rezsim réteg (piac-szintű):**
  - 3 arány monitorozása: **HYG/IEF** (credit spread, legsúlyozottabb), **RSP/SPY** (breadth), **IWM/SPY** (small cap rel. erő)
  - UUP kihagyva (kontextusfüggő, nem tiszta rezsim-indikátor)
  - **4 szintű gradiens** szavazási rendszerrel (3 arány, hány SMA20 alatt):
    | Szint | Feltétel | VIX küszöb | Max pozíció | Min score |
    |-------|---------|------------|-------------|----------|
    | NORMAL | 0/3 negatív | 20 (alap) | 8 | 70 |
    | CAUTIOUS | 1/3 negatív | 19 (-1) | 8 | 70 |
    | RISK_OFF | 2/3 negatív | 17 (-3) | 6 | 75 |
    | CRISIS | 3/3 negatív + VIX > 30 | 15 (-5) | 4 | 80 |
  - **Nem önálló szorzó** a multiplier chain-ben, hanem a **VIX küszöböket tolja el** rezsim szerint (exponenciális szorzó-lánc büntetés elkerülése)
  - **IWM/SPY feltételes szavazat:** IWM/SPY önmagában NEM szavaz (kamatkörnyezet-érzékeny, zajos). Csak ha HYG/IEF is negatív, akkor kap szavazatot. Logika:
    ```python
    votes = 0
    if hyg_ief < sma20(hyg_ief):   votes += 1  # credit spread — mindig szavaz
    if rsp_spy < sma20(rsp_spy):   votes += 1  # breadth — mindig szavaz
    if iwm_spy < sma20(iwm_spy) and hyg_ief < sma20(hyg_ief):
        votes += 1                              # small cap — csak credit megerősítéssel
    ```
  - Eredmény: HYG/IEF a "kapuőr", IWM csak megerősítő. IWM egyedül = 0 szavazat (pl. kamatemelési ciklus nem triggerel CAUTIOUS-t)
  - Indoklás: a VIX küszöb-tolás megakadályozza a szorzó-lánc exponenciális büntetését, miközben a cross-asset és VIX információ egy dimenzióba olvad
  - HYG/IEF prioritás: credit market gyorsabban áraz be kockázatot mint equity, ritkán hamis pozitív
  - **Kapcsolódás OBSIDIAN-hoz:** két rétegű rezsim-információ — piac-szintű (cross-asset = globális kapu) + ticker-szintű (OBSIDIAN = egyedi finomhangolás)
  - API: Polygon ETF bars (HYG, IEF, RSP, SPY, IWM) — már elérhető Advanced tierben

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
- **IBGatewayManager long-running mode:** heartbeat (30s polling), reconnect event loop, `on_reconnected()` hook (order/subscription újraindítás), Gateway watchdog (supervisord/launchd)

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
| T3 | Bottom 10 negatív szűrő | ✅ KÉSZ (2026-02-18) | BC18-prep |
| T4 | Rotation vs Liquidation OBSIDIAN | 📋 TERVEZETT | BC21 |
| T5 | BMI extreme oversold (<25%) sizing | 📋 TERVEZETT | BC17 |
| T6 | WOW Signals validálás | 📋 TERVEZETT | BC20 |
| T7 | New Kid + Repeat Freshness Alpha | 📋 TERVEZETT | BC20 |
| T8 | Félvezető szub-szektor faktor | ❌ ELENGEDVE | — |
| T9 | Trading Calendar earnings exclusion | ✅ KÉSZ (2026-02-18) | BC18-prep |
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
| 6 | Cache TTL fix (stale forward-looking) | ✅ LEZÁRVA (to_date cap + trading calendar) |
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
