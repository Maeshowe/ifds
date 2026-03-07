# IFDS — Master Roadmap & BC Registry

**Utolsó frissítés:** 2026-03-07
**Státusz:** AKTÍV

**Referencia fájlok:**
- Részletes BC scope: ez a fájl
- CC workflow: `CLAUDE.md` + `.claude/commands/`
- Permanens rules: `.claude/rules/ifds-rules.md`
- Tanulságok: `docs/planning/learnings-archive.md`
- Task fájlok: `docs/tasks/YYYY-MM-DD-*.md`

---

## Critical Task Audit (2026-03-07)

A korábban OPEN-nek jelölt 6 critical task valójában **mind implementálva van** a kódban.
Dokumentációs lag volt — a task fájlokban nincs `Status: DONE` fejléc.

| # | Task | Kód státusz | Task fájl státusz |
|---|------|-------------|-------------------|
| 1 | `phase1_regime.py` asyncio.gather `return_exceptions=True` | ✅ Kész (`_fetch_daily_history_async`) | ⚠️ Hiányzó Status header |
| 2 | `eod_report.py` idempotency guard | ✅ Kész (`existing_dates` check) | ⚠️ Hiányzó Status header |
| 3 | `submit_orders.py` circuit breaker halt + `--override-circuit-breaker` | ✅ Kész (`sys.exit(1)` + flag) | ⚠️ Hiányzó Status header |
| 4 | `close_positions.py` MOC split >500 | ✅ Kész (`MAX_ORDER_SIZE=500` + while loop) | ⚠️ Hiányzó Status header |
| 5 | `eod_report.py` MOC orderRef='' fix | ✅ Kész (`pnl_by_symbol` + MOC path) | ⚠️ Hiányzó Status header |
| 6 | `close_positions.py` TP/SL awareness | ✅ Kész (`get_net_open_qty` + `reqExecutions`) | ⚠️ Hiányzó Status header |

**Teendő (CC):** Task fájlok tetejére `Status: DONE` / `Updated: 2026-03-07` fejléc hozzáadása.
Lásd: CC Tooling Phase 4 — task státusz konvenció.

**MISSING_FEATURES.md nyitott elemek:**
- `strategy.dark_pool.min_block_size` + `min_notional` config kulcsok → BC17 preflight scope
- SimEngine offline replay → BC20 (SIM-L2 Mód 2)
- Trailing Stop Engine live → BC17-18 (pt_monitor.py)

---

## BC Registry — Priorizált Lista

### Prioritizálási szempontok

```
P0 = Blokkoló — nélkülük a következő BC nem indítható
P1 = BC hatékonyságot növelő — production quality javítás
P2 = Tervezett fejlesztés — ütemezett
P3 = Hosszú táv — Q2-Q3
```

---

## FÁZIS 0 — Azonnal (márc 7-10)

### Phase_00 — Task státusz dokumentáció
**Prioritás:** P0 | **Effort:** 30 perc CC
**Scope:**
- Mind a 6 closed critical task fájlba `Status: DONE` fejléc
- CC Tooling Phase 4 aktiválása: minden task fájl tetejére status header
  ```
  Status: DONE
  Updated: 2026-03-07
  Note: Implementálva, tesztek passing
  ```
- `grep -rl "Status: OPEN\|Status: WIP" docs/tasks/` → Chat session nyitáskor futtatható

### Phase_01 — CRGY nuke (hétfő márc 9, 15:30 CET ELŐTT)
**Prioritás:** P0 | **Effort:** manuális (Tamás)
- `python scripts/paper_trading/nuke.py` — CRGY 672 db long lezárása

---

## BC17 — EWMA + Crowdedness Shadow + OBSIDIAN Aktiválás
**Tervezett:** ~2026-03-18 (paper trading vége előtt)
**Prioritás:** P1

### Phase_17A — BC17 Preflight Hardening
**Task:** `docs/tasks/2026-02-27-bc17-preflight-hardening.md`
**Scope:**
- `phase6_sizing.py` → `dataclasses.replace()` (MMS field drop megelőzés)
- `validator.py` → OBSIDIAN regime multiplier keys validálás
- Phase 2/4/6 atomic file write-ok
- `deploy_daily.sh` → pytest pre-flight + flock + Telegram alert + state backup
- `strategy.dark_pool.min_block_size` + `min_notional` config kulcsok (MISSING_FEATURES)
- API retry tesztek: `test_base_client.py` + `test_async_base_client.py`

### Phase_17B — monitor_positions.py (leftover warning)
**Task:** `docs/tasks/2026-03-07-monitor-positions-leftover-warning.md`
**Scope:**
- Új script: IBKR pozíciók vs mai execution plan — ha nincs a planben → Telegram WARNING
- Crontab: `10 9 * * 1-5` (09:10 UTC = 10:10 CET)
- clientId=14, log: `logs/pt_monitor_positions.log`

### Phase_17C — pt_monitor.py Trailing Stop Szcenárió A
**Task:** `docs/tasks/2026-03-07-pt-monitor-trailing-stop-scenario-a.md`
**Előfeltétel:** Phase_17A kész
**Scope:**
- `pt_submit.py` → `monitor_state_YYYY-MM-DD.json` inicializálás
- Új script: `pt_monitor.py` — 5 percenként (09:00-19:55 UTC)
- TP1 fill detektálás → Bracket B SL cancel → trail aktiválás
- Breakeven protection: `trail_sl >= entry_price`
- Telegram: aktiváláskor + SL ütésekor
- clientId=15

### Phase_17D — EWMA + Crowdedness Shadow + OBSIDIAN Rezsim
**Scope:**
- EWMA smoothing (span=10) a scoring-ban
- Good/Bad Crowding mérés (shadow mode)
- OBSIDIAN factor volatility aktiválás (~márc 20, 21 nap baseline)
- T5: BMI extreme oversold (<25%) agresszív sizing
- OBSIDIAN rezsim multiplier élesítése Phase 6-ban
- OBSIDIAN dark pool küszöb kalibráció (DD/ABS újrakalibrálás 21 nap után)

---

## BC18 — Crowdedness Filtering + Trailing Stop B
**Tervezett:** ~2026-04-01
**Prioritás:** P1

### Phase_18A — Crowdedness Filtering Élesítés
**Scope:**
- BC17 shadow adatok elemzése (2 hét)
- Crowdedness composite score élesítése
- Clipping threshold finomhangolás

### Phase_18B — pt_monitor.py Trailing Stop Szcenárió B
**Task:** `docs/tasks/2026-03-07-pt-monitor-trailing-stop-scenario-b.md`
**Előfeltétel:** Phase_17C (Szcenárió A) kész
**Scope:**
- 19:00 CET időalapú trail aktiválás
- Küszöb: `current_price > entry_price * 1.005`
- Trail scope: `full` (total_qty), orderRef: `IFDS_{sym}_TRAIL`
- Cancel ALL SL orders (Bracket A + B)
- TP1/TP2 limit orderek megmaradnak
- CEST váltás automatikus (zoneinfo alapú)
- `scenario_b_activated` + `scenario_b_eligible` state mezők

---

## BC19 — ✅ KÉSZ (2026-02-18)
SIM-L2 Mód 1 — parameter sweep + Phase 4 snapshot persistence

---

## BC20 — SIM-L2 Mód 2 + T10 A/B + Trail Szimuláció
**Tervezett:** ~2026-04-első fele
**Prioritás:** P2

### Phase_20A — SIM-L2 Mód 2 Re-Score Engine
**Scope:**
- Re-score engine a Phase 4 snapshot-okból (~30+ nap adat)
- `replay.py` Mód 2 branch: Phase 4 intermediate data + override config
- Tesztek: `test_sim_rescore.py`

### Phase_20B — T10 A/B Teszt (Freshness Alpha vs WOW Signals)
**Scope:**
- Variáns A (baseline): lineáris freshness penalty
- Variáns B: U-alakú logika (New Kid +15%, WOW +10%, Stale -20%, Persistent +5%)
- Paired t-test: p < 0.05 VAGY ΔP&L > +$500 és ΔWR > +5%
- T7: New Kid + Repeat bónusz validálás
- T6: WOW Signals ismétlődő score validálás

### Phase_20C — SIM-L2 Trail Szimuláció Támogatás
**Scope:**
- `broker_sim.py` multi-day + partial exit szimulálás
- SIM variáns config-ok: `tp1_atr`, `trailing_stop_atr`, `max_hold_days`
- Paper Trading trail adatok összehasonlíthatósága SIM-mel
- Dokumentálás: melyik naptól aktív a trail (PT vs SIM divergencia)

---

## BC20A — Swing Hybrid Exit (Pipeline Refactor)
**Tervezett:** ~2026-04 (BC20-val párhuzamosan)
**Prioritás:** P2
**Design doc:** `docs/planning/swing-hybrid-exit-design.md`
**Előfeltétel:** BC20C (SIM trail szimulációs support) kész

### Phase_20A_1 — VWAP Modul
**Scope:**
- `src/ifds/phases/vwap.py` — VWAP kalkuláció Polygon 5-min bars-ból
- VWAP guard logika: REJECT >2%, REDUCE >1%, BOOST <-1%, NORMAL ±1%
- Tesztek

### Phase_20A_2 — Position Tracker
**Scope:**
- `src/ifds/state/position_tracker.py`
- State: `state/open_positions.json`
- Mezők: entry_date, entry_price, total_qty, remaining_qty, tp1_triggered,
  tp1_qty, trail_qty, sl_price, hold_days, max_hold_days, atr_at_entry

### Phase_20A_3 — Pipeline Split + MKT Entry
**Scope:**
- `runner.py` → `--phases 1-3` / `--phases 4-6` CLI flag
- `scripts/deploy_intraday.sh` — 15:45 CET cron: Phase 4-6 + submit
- `submit_orders.py` → MKT entry (nem LMT), partial TP1 bracket (33%/67%), OCA group
- `phase6_sizing.py` → VWAP guard + TP1 = 0.75× ATR + position split info

**IBKR bracket struktúra:**
```
Parent: BUY {qty} MKT
  Child 1: SELL {qty_tp1} LMT @ entry + 0.75×ATR  (TP1, 33%, OCA)
  Child 2: SELL {qty}     STP @ entry - 1.5×ATR    (SL, full, OCA)
```

### Phase_20A_4 — close_positions.py Swing Management
**Scope:**
- Hold day tracking (trading nap számolás, pandas_market_calendars)
- Breakeven SL: ha ár > entry + 0.3×ATR → SL felhúzás entry-re
- IBKR TRAIL order: 1× ATR (VOLATILE regime: 0.75× ATR)
- Max hold D+5 → MOC fallback
- Earnings check: T9 trading calendar (korai exit)

### Phase_20A_5 — SimEngine Swing Support
**Scope:**
- `broker_sim.py` + `validator.py` multi-day swing szimulálás
- TP1 (33% partial exit) + trail + SL + max_hold_days napról napra

---

## BC21 — Risk Layer: Korrelációs Guard + Portfolio VaR + Cross-Asset Rezsim
**Tervezett:** ~2026-04-második fele
**Prioritás:** P2

### Phase_21A — Korrelációs Guard + Portfolio VaR
**Scope:**
- Pozíció-korrelációs guard (ne legyen 5 utility egyszerre)
- Portfolio-szintű VaR kalkuláció
- T4: Rotation vs Liquidation megkülönböztetés OBSIDIAN-ban
- Max szektor koncentráció limit

### Phase_21B — Cross-Asset Rezsim Réteg
**Scope:**
- 3 arány monitorozása: HYG/IEF (kapuőr), RSP/SPY (breadth), IWM/SPY (feltételes)
- 4 szintű gradiens — szavazási rendszer:
  ```python
  votes = 0
  if hyg_ief < sma20(hyg_ief):   votes += 1  # mindig szavaz
  if rsp_spy < sma20(rsp_spy):   votes += 1  # mindig szavaz
  if iwm_spy < sma20(iwm_spy) and hyg_ief < sma20(hyg_ief):
      votes += 1                              # csak HYG megerősítéssel
  ```
- VIX küszöb-tolás (NEM multiplikátor-lánc):
  | Szint | Feltétel | VIX küszöb delta | Max pozíció | Min score |
  |-------|---------|------------|-------------|----------|
  | NORMAL | 0 szavazat | ±0 | 8 | 70 |
  | CAUTIOUS | 1 szavazat | -1 | 8 | 70 |
  | RISK_OFF | 2 szavazat | -3 | 6 | 75 |
  | CRISIS | 3 szavazat + VIX>30 | -5 | 4 | 80 |
- API: Polygon ETF bars — HYG, IEF, RSP, SPY, IWM (Advanced tier)

---

## BC22 — HRP Allokáció + Riskfolio-Lib
**Tervezett:** ~2026-05
**Prioritás:** P2

### Phase_22A — HRP Engine
**Scope:**
- Hierarchical Risk Parity allokáció (Riskfolio-Lib)
- Score-alapú allokáció (nem egyenlő súlyozás)
- OBSIDIAN portfólió-szintű regime (ticker→szektor→portfólió)

### Phase_22B — Pozíciószám Bővítés
**Scope:**
- 8 → 15 pozíció (paper trading adatok alapján döntünk)
- Exposure limit recalibráció az új mérethez

---

## BC23 — ETF BMI: Broad ETF Flow Intelligence
**Tervezett:** ~2026-05/06
**Prioritás:** P2
**Design doc:** `docs/planning/etf-universe-design.md`

### Phase_23A — ETF Flow Intelligence (Réteg 1, ~1000 ETF)
**Scope:**
- UW `get_etf_in_outflow()` endpoint
- ETF flow → szektor rotációs megerősítés (Phase 3 kiegészítés)
- ETF flow → makró regime jelzés (Phase 1 kiegészítés)
- Aggregált intézményi flow heatmap

### Phase_23B — L2 Szektoros Finomítás (Réteg 2, 42 ETF)
**Scope:**
- 10 CONDITIONAL ticker döntése (SKYY, HACK, KIE, XAR, ITA, JETS, XRT, TAN, ICLN, LIT)
- L1→L2 mapping alkalmazása Phase 3-ban
- L2 ETF-ek momentum rangsorolása szektoron belül

### Phase_23C — MCP Server Alap
**Scope:**
- IFDS pipeline introspekció: státusz, P&L, pozíciók, rezsim, logok
- Meglévő API-k (FRED, FMP, Polygon, UW) fölé rétegezve

---

## BC24 — Score-Implied μ + Black-Litterman Views
**Tervezett:** ~2026-06/07
**Prioritás:** P3

### Phase_24A — Black-Litterman Integráció
**Scope:**
- IFDS score → expected return mapping
- Black-Litterman modell: market equilibrium + IFDS views
- FMP analyst estimates integráció
- HRP → BL transition az allokációban

### Phase_24B — Company Intel v2
**Scope:**
- MCP-alapú Company Intel
- Adjusted EPS, short interest, options flow summary
- Napi automatikus futás MCP pull modellben

---

## BC25 — Auto Execution
**Tervezett:** ~2026-07/08
**Prioritás:** P3

### Phase_25A — WebSocket + Auto Submit
**Scope:**
- Polygon real-time WebSocket → IBKR automatikus order submission
- Human approval loop (Telegram → confirmation)
- Circuit breaker: max napi veszteség, max pozíciószám

### Phase_25B — IBGatewayManager Long-Running
**Scope:**
- Heartbeat (30s polling), reconnect event loop
- `on_reconnected()` hook (order/subscription újraindítás)
- Gateway watchdog (supervisord/launchd)

---

## BC26 — Multi-Strategy Framework
**Tervezett:** ~2026-08/09
**Prioritás:** P3

### Phase_26A — Mean Reversion Stratégia
**Scope:**
- Laggard + OVERSOLD szektorok
- Stratégia allokáció BMI regime alapján

### Phase_26B — ETF-Szintű Kereskedés
**Scope:**
- ETF-szintű kereskedés (nem csak egyedi részvények)
- Momentum stratégia (Leader szektorok, WOW signals)

---

## CC Tooling Roadmap (párhuzamos)

| Fázis | Mikor | Mit | Státusz |
|-------|-------|-----|---------|
| 1 — CONDUCTOR → natív | 2026-02-26 | `.claude/` struktúra, slash commandok | ✅ KÉSZ |
| 2 — Rules finomítás | BC17 közben | `/learn rule` organikus bővítés | 🔄 Folyamatos |
| 3 — Skills + Contexts | BC17 után | `continuous-learning` skill, context injection | 📋 ~márc közepe |
| 4 — Task státusz loop | BC17 után | Status header minden task fájlban, CLAUDE.md auto-update | 📋 ~márc közepe |
| 5 — MCP integráció | BC20 előtt | GitHub MCP, custom IFDS MCP előkészítés | 📋 ~április |

**Task fájl konvenció (Phase 4-től minden új taskban kötelező):**
```
Status: OPEN | WIP | DONE | BLOCKED
Updated: YYYY-MM-DD
Note: <opcionális>
```

---

## SimEngine Szintek

| Level | Státusz | BC |
|-------|---------|-----|
| L1 Forward Validation | ✅ Kész (BC16) | — |
| L2 Mód 1 Parameter Sweep | ✅ Kész (BC19) | — |
| L2 Mód 2 Re-Score | BC20 | Phase_20A |
| L2 Trail Szimuláció | BC20 | Phase_20C |
| L3 Full Backtest (VectorBT) | Q3 BC24+ | — |

---

## MoneyFlows Tanulságok

| # | Tanulság | Státusz | Phase |
|---|----------|---------|-------|
| T1 | Energy szektor gap | ❌ ELENGEDVE | — |
| T2 | Outlier 50 benchmark | ✅ AKTÍV — SIM-L1 méri | — |
| T3 | Bottom 10 negatív szűrő | ✅ KÉSZ | — |
| T4 | Rotation vs Liquidation OBSIDIAN | 📋 | Phase_21A |
| T5 | BMI extreme oversold sizing | 📋 | Phase_17D |
| T6 | WOW Signals validálás | 📋 | Phase_20B |
| T7 | New Kid + Repeat Freshness Alpha | 📋 | Phase_20B |
| T8 | Félvezető szub-szektor faktor | ❌ ELENGEDVE | — |
| T9 | Trading Calendar earnings exclusion | ✅ KÉSZ | — |
| T10 | Freshness Alpha vs WOW A/B | 📋 | Phase_20B |
| T11 | Company Intelligence Phase 7 | 🔄 Standalone kész | Phase_24B |

---

## Parkolt

| Elem | Indok |
|------|-------|
| VectorBT CC Skill | BC20 előtt nincs elég snapshot adat |
| MCP Server — IFDS introspekció | Phase_23C scope |
| Company Intel v2 MCP | Phase_24B scope |

---

## Idővonal

```
         Márc                  Ápr                   Máj              Jún+
    ─────┬───────────────────┬────────────────────┬─────────────────┬──────
         │                   │                    │                 │
Phase    │ 00+01              │                    │                 │
_00/_01  │ Status docs + CRGY│                    │                 │
         │                   │                    │                 │
Paper    │ ████ márc 17 KÉSZ │                    │                 │
Trading  │ Day 14→21         │ Éles döntés        │                 │
         │                   │                    │                 │
BC17     │ ████████████████  │                    │                 │
17A+B+C  │ Preflight+Monitor │                    │                 │
+D       │ Trail A + EWMA    │                    │                 │
         │                   │                    │                 │
BC18     │        ███████████│                    │                 │
18A+B    │        Crowd+Trail│                    │                 │
         │        B ~ápr 1   │                    │                 │
         │                   │                    │                 │
BC20     │                   │ ████████           │                 │
20A+B+C  │                   │ SIM Mód 2+T10+Trail│                 │
         │                   │                    │                 │
BC20A    │                   │ ████████████       │                 │
Swing    │                   │ VWAP+PosTrk+Split  │                 │
Exit     │                   │ +close+SimEng      │                 │
         │                   │                    │                 │
BC21     │                   │        ████████    │                 │
Risk     │                   │        VaR+Cross-  │                 │
Layer    │                   │        Asset       │                 │
         │                   │                    │                 │
BC22     │                   │                    │ ████████        │
HRP      │                   │                    │ Riskfolio-Lib   │
         │                   │                    │                 │
BC23     │                   │                    │      ███████████│
ETF BMI  │                   │                    │ +MCP server     │
         │                   │                    │                 │
SIM-L1   │ ████████████████████████████████████████████████████████
         │ Folyamatos napi futás                                    │
Phase 4  │ ████████████████████████████████████████████████████████
Snapshot │ BC20-ra ~30+ nap  │ BC20 használja     │                 │
```

---

## Éves nézet

```
Q1 (jan-márc):  BC1-17  — Pipeline + Validation + Crowdedness shadow + Trail Stop A
Q2 (ápr-jún):   BC18-23 — Trail B, SIM-L2 Mód 2, Swing Exit, Risk Layer, HRP, ETF BMI
Q3 (júl-szept):  BC24-26 — Black-Litterman, Auto Exec, Multi-Strategy
Q4 (okt-dec):   BC27-30 — Dashboard, Alpha Decay, Retail Packaging
```
