# IFDS — Current Status
<!-- Frissíti: CC (/wrap-up), Chat (session végén) -->
<!-- Utolsó frissítés: 2026-05-20 16:45 CEST — Day 3 swing pivot. 7 nyitott pozíció (4 régi: LBRT/MASI/EC/PFGC + 3 új Day 3: VLO 16@$258.55, ON 27@$109.48, CNC 95@$59.27 — manual IBKR Workstation submit Error 354 miatt). State≡IBKR reconciled. 5 új commit ma (aba9720 log_setup pytest redirect Task #G, 1eb9755 write_shadow_snapshot sink, bd54857 save_phase13_context sink Task #H, d930d14 Telegram pollution fix §8.1.9, 3bf382b+e3677f2 incomplete TIF patches). 1746 passing. Holnap Task #I — Error 354 permanent fix (Tamás IBKR Workstation Precautionary Settings disable). -->
<!-- Korábbi: 2026-05-19 16:50 CEST — Day 2 stabil. Task #T (Telegram swing-aware, 5 réteg, 27 új teszt) + #D (state/IBKR reconcile, 7 teszt) + #E (Phase 1-3 freshness, 5 teszt) DEPLOYED. EC TP1 50% SELL filled 15:30. 4 nyitott pozíció: LBRT/MASI/EC-166/PFGC. 1740 passing. Holnap Task #G (pt_monitor replay diagnózis, P0, ~60 min). -->
<!-- Korábbi: 2026-05-18 12:10 CEST — Fázis 3 deploy LIVE (1711 passing, Day 1 indul) -->
<!-- Korábbi: 2026-05-18 CC Ülés C — Swing Execution + Exit DEPLOY (1705 passing) -->
<!-- Korábbi: 2026-05-18 CC Ülés B — Swing Sizing Phase 6 DEPLOY (1672 passing) -->
<!-- Korábbi: 2026-05-18 CC Ülés A — Swing Universe + Swing Phase 4 scoring DEPLOY (1656 passing) -->
<!-- Korábbi: 2026-05-16 CC Ülés C — UW dark pool / GEX deactivation + shadow log DEPLOY (1624 passing) -->

## ⭐ MÉRFÖLDKŐ: Day 63 LEZÁRULT (2026-05-14)

**Hivatalos kimenet**: **PAPER FOLYTATÁS (default)** — DE radikálisan más architektúrán.

**Részletes döntési dokumentum**: [`docs/decisions/2026-05-14-day63-decision-outcome.md`](decisions/2026-05-14-day63-decision-outcome.md) (14 stratégiai döntés)

**Kumulatív 63 napi**: -$1,623.78 paper aggregát / ~-$1,400-1,500 valós (bug-korrekciókkal)

### Day 63 keret 3 kimenet kiértékelése

| Kimenet | Feltétel | Eredmény |
|---|---|---|
| ÉLESÍTÉS | +$3,000 ÉS +1.5% kumulatív excess vs SPY | NEM teljesült (-$1,623, távolság -$4,623) |
| LEÁLLÍTÁS | 10 napi excess < -1.5% VAGY VIX > 25 30+ napra | NEM aktivált (10 napi átlag -0.35%, buffer ~1.15%) |
| **PAPER FOLYTATÁS** (default) | A két fenti egyike sem | ✅ **AKTIVÁLT** |

---

## Stratégiai fókusz: SWING PIVOT (W21-W30, 8-10 hét)

A jelenlegi rendszer **negatív expectancy-jű** (Kelly $f^* = -0.23$ konzervatív, $-0.46$ default), **kvázi-zéró edge-gel** (Pearson $\rho(S, R) = -0.000$), **19-21% éves súrlódás-teherrel**. **Intézményi befektető allokáció nélkül hagyná.**

A 60 napi adat **strukturális tanulságokat** szolgáltatott — a **B opció (multi-day swing)** kvantitatívan a legjobb pivot:
- Mathematical doc 5.2: a flow signal mutual information $h=5$ napi holding mellett **5× erősebb** ($I \approx 5\rho^2 \approx 0.10$)
- Kelly criterion swing horizonton **újrakalkulálható**, várhatóan pozitív
- A LOSS_EXIT bracket SL bug (4 instancia 13 napon belül) **strukturálisan eliminálódik** a mental stop architektúrával

### 14 stratégiai döntés (Day 63 outcome doc)

| # | Téma | Választás |
|---|---|---|
| 1 | Day vs Swing | **SWING (3-5 nap hold)** |
| 2 | UW API | **Shadow log Day 90-ig**, scoring-ban deaktiválás |
| 3 | 15 backlog idea | **KEEP 6 / REWORK 4 / DROP 5** |
| 4 | Strategic-review nem-implementált | **3 elvégzendő, 2 elvetendő** |
| 5 | Reset roadmap | **3 fázisú, W21-W30** |
| 6 | Entry/exit timing | **15:30 CEST entry, 3-5 nap hold, mental stop** |
| 7 | Pozíció-méretezés | **Rolling 10-12 equal-weight, 0.35% risk/position** |
| 8 | Time-stop | **5 trading nap full MOC exit** |
| 9 | Universum | **S&P 500 + Russell 1000 (~1000 likvid)** |
| 10 | Earnings exclusion | **10 nap előretekintés (hold × 2)** |
| 11 | Sector concentration cap | **30% notional/szektor** |
| 12 | Stop-loss típus | **Mental stop, daily eval, NINCS IBKR bracket** |
| 13 | Scoring revízió | **PCR + OTM-inverse only** (Bonferroni-szignifikáns minimum) |
| 14 | Új élesítési kritérium | **Day 126: +$2,000 + Sharpe>0.5 + 25+ napi pos excess** |

### Új Day 126 milestone

**Naptári dátum (becsült)**: 2026-09-15 (W37). Akkor lesz az élő pénzes kereskedés döntésének **első valós alapja**.

---

## 3 fázisú reset roadmap

### Fázis 1 — Operational cleanup (W21-W22, máj 19 - máj 30)

**Cél**: a régi architektúra "lezárása", az új scoping előkészítése.

**Tamás (manuális)**:
- Máj 19 (h): `nuke.py --positions` AAPL/AVDL.CVR teljes takarítás
- Máj 19: IBKR TWS UI — minden függő bracket TP/SL order manuális cancel
- Máj 20-22: IBKR paper account reset ($100k újra)

**Chat**:
- ✅ Day 63 outcome doc (KÉSZ — `docs/decisions/2026-05-14-day63-decision-outcome.md`)
- ✅ Strategic-review $354 → $665 korrekció (KÉSZ, 2026-05-14)
- 🔄 Master-reference frissítés (folyamatban)
- 🔄 Backlog frissítés (folyamatban)
- 🔄 Új handoff doc (folyamatban)
- ⏳ Új architektúra design doc (`docs/design/swing-pivot-architecture.md`)

**CC**:
- ✅ IBKR Gateway monitoring DONE (commit `5b337da`, 2026-05-16) — §10 Fix C heartbeat + §11 Telegram silent-swallow fix Mac Mini-n verifikálva (1582 passed). §3 H1 igazolt (Telegram alert SOHA nem ért el a requests.post-ig 2026-05-11-én), H2 részleges (check 16:00 → 20 perc submit előtt). Fix A nem szükséges (load_dotenv), Fix B halasztva a swing pivot átállás utánra.
- ✅ Earnings exclusion 7 → 10 nap DEPLOYED (commit `d3be2fe`, 2026-05-16)
- ✅ **10-Q / 10-K SEC Filing Exclusion DEPLOYED** (Ülés B, 2026-05-16) — `src/ifds/data/sec_edgar.py` + Phase 2 `_exclude_sec_filings` 3-pass + 25 új teszt (1582 → 1607). Live schema verify done (AAPL CIK 0000320193 parallel-array schema), 1611-ticker live smoke **100% success, 0 hard error, 16 flagged**, wall clock 12.9 min (cold cache, daily TTL után inkrementális). 4 Tamás döntés (User-Agent env, ±10d tolerance, 2d cache fallback → fail-open) implementálva.
- ✅ **UW dark pool / GEX deactivation + shadow log DEPLOYED** (Ülés C, 2026-05-16) — `src/ifds/data/uw_shadow.py` (build/write/load/summary helpers), Phase 4 `dp_pct` bonus gating + Phase 6 `M_GEX` gating (both default OFF), runner post-Phase 6 snapshot write to `state/uw_shadow/YYYY-MM-DD.json`, `daily_metrics.py` `uw_shadow_summary` field, 17 új teszt (1607 → 1624). Phase 5 GEX exclusion (NEGATIVE LONG) változatlan. Day 90 (~2026-08-26) Bayesi rekalibrációhoz folytatólagos shadow gyűjtés.

#### Fázis 3 deploy folyamatban (2026-05-18, vasárnap kimaradt → hétfő-kedd 3 ülésben)
- ✅ **Task #1 Swing Universe DEPLOYED** (Ülés A, 2026-05-18 hétfő reggel, commit `50dfb3c`) — `src/ifds/data/swing_universe.py` Wikipedia parser (stdlib only, header-driven Symbol detection, class-share normalizálás), Phase 2 FMP screener intersect swing union, 7d cache, FMP fallback. Live smoke: SP500=503 + R1000=1002 = union 1008 (497 overlap). 14 új teszt (1624 → 1638).
- ✅ **Task #2 Swing Scoring Phase 4 DEPLOYED** (Ülés A, 2026-05-18 hétfő reggel, commit `13e3b3d`) — `src/ifds/scoring/swing_score.py` (compute_percentile_score, compute_raw_swing_score, SwingEwmaState, compute_swing_scores), Phase 4 `_apply_swing_scoring` post-processor (sync + async paths) recoveryzi a legacy clipping/min_score exclusion-okat és újraértékel a `S_j > 50` Bonferroni-küszöbre, EWMA(5) state persistence `state/swing_ewma_state.json`. Phase 6 M_VIX gating (`m_vix_enabled=False`). 18 új teszt (1638 → 1656). 2-day EWMA chain smoke verified.
- ✅ **Task #3 Swing Sizing Phase 6 DEPLOYED** (Ülés B, 2026-05-18 hétfő délután) — `compute_swing_notional` képlet (0.35% risk, ATR_pct denominator, 2.0×ATR stop), `_calculate_swing_position` (csak M_target aktív), `_select_swing_entries` sector-balanced greedy fill (D10), `_run_phase6_swing` wrapper. Új TUNING: `swing_sizing_enabled=True`, `swing_max_concurrent=12`, `swing_sector_cap_pct=0.30`, `m_contradiction_enabled=False` default flip. RUNTIME: `max_positions: 5→12`, `max_gross_exposure: 80k→150k`, `max_single_ticker_exposure: 20k→15k`. 16 új teszt (1656 → **1672**). Smoke verified (10-ticker univerzum, 3 entry, sector cap + M_target overshoot penalty érvényesülve).
- ✅ **Task #4 Swing Execution + Exit DEPLOYED** (Ülés C, 2026-05-18) — `src/ifds/state/swing_positions.py` új modul (SwingPosition dataclass + 6-condition `evaluate_position_eod` + state I/O + batch helpers), `submit_orders.py` `submit_swing_market_only` branch (market BUY only, no bracket), `pt_monitor.py` `--mode=eod_eval` (Polygon-driven daily 22:00 CEST eval), `close_positions.py` `--mode=eod_flags|time_stop` (next-day 15:30 + same-day 21:40 MOC), `runner.py` `open_positions` wire-up. Új TUNING: `swing_execution_enabled=True`, `swing_mental_stop_atr_multiple=2.0`, `swing_trail_atr_multiple=1.0`, `swing_hard_sl_weekly_cumulative_pct=-0.08`, `swing_time_stop_trading_days=5`, `swing_positions_state_file`, `ibkr_bracket_enabled=False`, `loss_exit_intraday_enabled=False`, `pt_monitor_5min_mode=False`. **TP1 multiplier 1.25 → 1.5**, **TP2 2.0 → 3.0** (swing-specifikus TP geometria). 33 új teszt (1672 → **1705**), 3-day swing lifecycle integration smoke verified.
- ✅ **Task #5 A rész (CC technikai) DEPLOYED** (Ülés C, 2026-05-18) — `daily_metrics.py` `_build_swing_state` block (open_positions, sector_distribution, exits_today, next_day_planned, swing_score_distribution), `src/ifds/output/swing_telegram.py` `format_swing_compact_telegram` pure formatter (< 800 char mobile-friendly). 6 új teszt + 1 existing test bővítve (1705 → **1711**).
- ⏳ Task #5 B rész (Tamás manual + push) — circuit_breaker reset, cumulative_pnl Day 1 reset, IBKR paper $100k reset, crontab update, .env ellenőrzés, **git push origin master** (~9 commit Fázis 1 + Fázis 3 close-ig)

**Day 1 = kedd 5/19 15:30 CEST** (1 nap csúszás a vasárnapi pihenőnap miatt — Tamás döntés, intézményi szempontból irreleváns).

### Fázis 2 — Analytic + Design (W23-W24, jún 2 - jún 13)

**Cél**: a swing pivot kvantitatív megalapozása + technikai design.

**Chat**:
- Entry timing backtest (4 alternatív időablak a 60+ napi adaton, ~1-2 óra)
- M_contradiction sign-flip elemzés (~1 óra)
- Új scoring design doc (`docs/design/swing-scoring-spec.md`) — PCR + OTM-inverse
- Új risk management spec (`docs/design/swing-risk-spec.md`) — mental stop, time-stop, hard SL
- Új position sizing spec (`docs/design/swing-sizing-spec.md`) — rolling 10-12, 0.35% risk

**CC**:
- Design specifikációk alapján prototípusok (unit-test szinten) — NEM deploy (~3-5 óra)

### Fázis 3 — Re-deploy + új paper trading (W25-W30, jún 16 - júl 25)

**Cél**: új architektúra élesítése + 63 napi paper trading futás.

**CC**:
- Új scoring funkcionál deploy (~3-4 óra)
- Universum builder módosítás (S&P 500 + Russell 1000 union, ~1-2 óra)
- Új risk management deploy (~5-8 óra)
- Új position sizing deploy (~3-4 óra)
- Integration tests, smoke tests (~3-5 óra)

**Tamás (manuális)**:
- Kb. jún 23 (W26 hétfő): IBKR paper account reset + **új paper trading INDUL Day 1-en**

**Új Day 63 milestone**: kb. **2026-09-15 (W37)** — élő kereskedés döntés első valós alapja.

---

## Új W21+ aktív backlog (9 tétel, drasztikusan csökkentve)

A korábbi 15+1 idea-ból **6 dropolva** (a swing pivot strukturálisan eliminálja), **4 átalakítva**, **6 új aktív** (köztük 1 új P1 = dinamikus pozíciószám).

### P1 — Fázis 1 azonnali (W21-W22)

| # | Tétel | Effort | Owner |
|---|---|---|---|
| P1.1 | IBKR Gateway monitoring + Telegram alert | ~1 óra | CC |
| P1.2 | 10-Q SEC Filing Exclusion (10 napi earnings + 10-Q) | ~2-3 óra | CC |

### P2 — Fázis 2 analitikus (W23-W24)

| # | Tétel | Effort | Owner |
|---|---|---|---|
| P2.1 | Entry timing optimalizáció backtest | ~1-2 óra | Chat |
| P2.2 | M_contradiction sign-flip vizsgálat | ~1 óra | Chat |
| P2.3 | TP1 cél revízió (új swing TP-struktúra: 1.5/3.0× ATR) | ~30 min config + ~1 óra CC | CC |
| P2.4 | Dinamikus pozíciószám (rolling 10-12, 0.35% risk) | ~1 óra CC | CC |

### P3 — Fázis 3 vagy később

| # | Tétel | Effort | Owner |
|---|---|---|---|
| P3.1 | ADR earnings adatforrás fix | ~3-4 óra CC | CC |
| P3.2 | Breakeven Lock profit-küszöb (swing-integrált) | ~30 min config | CC |
| P3.3 | Phase 4 snapshot enrichment | ~30-45 min CC | CC |

### DROPPED (a swing pivot által strukturálisan eliminált)

- **LOSS_EXIT bracket SL cancellation** (4 instancia bug): mental stop architektúra → bracket NINCS, bug megszűnik
- **`nuke.py --orders` scope expansion**: NINCS bracket order, `--positions` elég
- **UW rate limit kezelés finomítás**: UW shadow log, scoring-ban deaktiválva
- **LOSS_EXIT küszöb finomítás per-ticker ATR**: mental stop architektúra
- **dp_pct fallback default**: UW scoring-ban deaktiválva
- **Slippage-adjusted scoring validation**: új scoring eleve slippage-szembesített
- **High-score liquidity check**: a "magas pontszám paradoxon" a scoring revízión át kezelendő
- **monitor.py belső replay események jelölése**: alacsony prioritás, későbbi

Részletes mátrix: [`docs/decisions/2026-05-14-day63-decision-outcome.md`](decisions/2026-05-14-day63-decision-outcome.md) — 4. fejezet.

---

## Élesben futó feature-ök (a régi rendszer utolsó hete, W20 vége)

> **Megjegyzés**: ezek a feature-ök a Fázis 3 deploy után **átalakulnak vagy megszűnnek**. A Fázis 1-2 (W21-W24) alatt **változatlanul futnak**, mert nincs új deploy.

- Pipeline Split: Phase 1-3 (22:00 CEST) + Phase 4-6 (16:15 CEST)
- MKT entry + VWAP guard (csak REJECT >2%)
- Swing Management: 5 napos hold, TP1 50% partial, TRAIL, breakeven SL, D+5 MOC
- Dynamic positions: max 5, score threshold 70 (Phase 4) / 85 qualified
- UW Client v2 + Snapshot v2 (kötelező header, dollár-alapú DP)
- Cross-Asset Regime + Korrelációs Guard + Portfolio VaR 3%
- EWMA simítás, M_target penalty, BMI momentum guard (tiered: 3-4 nap → 4, 5-6 → 3, 7+ → 2)
- TP1 1.25×ATR, dp_pct sign-flip (-10/-15 penalty)
- Sequential dp enrichment (200ms delay, élesben 95.2% success)

### Shadow mode (Fázis 1-ben deaktiválandók)

| Feature | Shadow óta | Új státusz |
|---|---|---|
| Crowdedness composite | 2026-03-23 | Fázis 3-ban **újra-értékelendő** swing kontextusban |
| Skip Day Shadow Guard | 2026-04-02 | Fázis 3-ban **átalakítva** vagy dropolt |
| MID Bundle Shadow | 2026-04-27 | **Megőrzendő** — portfolio context layer az új architektúrán |
| **UW dark pool + GEX shadow** | **2026-05-19 (új)** | Day 90 érdemleges power-rel audit (n=180) |

---

## Paper Trading

**Day 63/63 LEZÁRULT** | IBKR DUH118657 (kb. máj 22-én reset)

A Fázis 1 cleanup végén Tamás `nuke.py --positions` futtatja, IBKR paper account reset, $100k újra. **Új paper trading kb. jún 23 (W26 D1) indul.**

### W20 utolsó hete (régi rendszer)

| Nap | Net P&L | Excess | Megjegyzés |
|---|---|---|---|
| W20 D1 (h, máj 11) | +$28 | -0.19% | mild bull underperform, manuális 17:15 entry, snapshot fix DEPLOYED |
| W20 D2 (k, máj 12) | -$369 | -0.20% | TGB+NVDA LOSS_EXIT, entry timing finding |
| W20 D3 (sz, máj 13) | -$189 | -0.74% | bull rally EXTRÉM underperform, FORM/AAPL bracket bug |
| W20 D4 (cs, máj 14) | **DAY 63** | — | **Milestone** — outcome doc készítés |

---

## Tesztek

**1582 passing**, 0 failure (utolsó update: 2026-05-16 Ülés A — earnings 7→10 +3, IBKR Gateway monitoring +15)

> **Fázis 3 deploy után**: a tesztkészlet **átalakul** — sok régi teszt elavul (bracket-mechanika, multiplier chain), új tesztek (mental stop, time-stop, rolling 10-12 sizing).

---

## Utolsó commitok

- `5b337da` — feat(monitoring): IBKR Gateway pre-flight + heartbeat alerting baseline (Ülés A, W21 szombat)
- `d3be2fe` — config(universe): earnings_exclusion_days 7 → 10 (Ülés A, W21 szombat)
- `800b781` — docs(handoff): Fazis 1 W21 multi-session execution plan for Mon 5/18 market open
- `41896a6` — docs(wrap-up): 2026-05-16 session close — rate-limit rule + W20-W21 bulk docs sync
- `81a316b` — docs: W20-W21 wrap — Day 63 decision + weekly metrics + handoffs + new tasks (W21 szombat)
- `33a665f` — docs(rules): add rate-limit live-smoke rule (W21 szombat)
- `5dea269` — docs(wrap-up): 2026-05-13 session close — sequential dp enrichment hotfix
- `1f0ffb9` — fix(phase4): sequential dp enrichment with 200ms delay
- `8a44178` — docs(wrap-up): 2026-05-12 session close
- `b6db393` — fix(phase6): tiered BMI momentum guard
- `90cf5b4` — fix(phase4): two-pass dp scoring
- `9a169b9` — feat(scoring): dp_pct sign-flip + threshold recalibration

---

## Blokkolók

**Nincs aktív blokkolók**. A Fázis 1 cleanup a Tamás IBKR reset után (máj 22-25 körül) indul érdemben.

**Várt blokkolók (Fázis 3 előtt)**:
- IBKR paper account állapota (Tamás manuális reset szükséges)
- Új design dokumentumok (Fázis 2 végén) Tamás review-ja

---

## Kapcsolódó docs

- **Day 63 outcome** (a fő dokumentum): [`docs/decisions/2026-05-14-day63-decision-outcome.md`](decisions/2026-05-14-day63-decision-outcome.md)
- **Strategic-review**: [`docs/strategic-review/2026-05-08-strategic-review-summary.md`](strategic-review/2026-05-08-strategic-review-summary.md) (5 oldal), [`...full.md`](strategic-review/2026-05-08-strategic-review-full.md) (25 oldal), [`...mathematical.md`](strategic-review/2026-05-08-strategic-review-mathematical.md) (~30 oldal)
- **Master-reference**: [`docs/master-reference/INDEX.md`](master-reference/INDEX.md) (frissítendő Fázis 1-ben)
- **Backlog**: [`docs/planning/backlog-ideas.md`](planning/backlog-ideas.md) (frissítendő Fázis 1-ben)
- **API_STACK**: [`docs/API_STACK.md`](API_STACK.md) (frissítendő Fázis 1-ben, 2026-03-01-i elavult)
- **Régi handoff**: [`docs/handoff/2026-05-08-chat-handoff-strategic-review.md`](handoff/2026-05-08-chat-handoff-strategic-review.md)
- **Új handoff** (folyamatban): [`docs/handoff/2026-05-14-chat-handoff-day63-outcome.md`](handoff/)

---

## 🔑 Egy mondatban — a következő 8-10 hét

A 60 napi paper trading **negatív expectancy-jű intraday rendszert** rögzített; a **swing pivot** (3-5 napi hold, PCR + OTM-inverse scoring, mental stop, rolling 10-12 sizing) **a kvantitatívan helyes irány**, ami **8-10 hét reset után** (W21-W30) egy **új 63 napi paper trading futást** indít — az **élő pénzes kereskedés első valós döntési pontja kb. 2026-09-15 (W37)**.
