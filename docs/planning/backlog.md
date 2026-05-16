# IFDS — Fejlesztési Backlog
<!-- Frissíti: Chat/CC, in-place -->
<!-- Utolsó frissítés: 2026-05-14 (Day 63 outcome + Swing pivot) -->

> **⛔ KORSZAKVÁLTÁS (2026-05-14)**: a Day 63 milestone outcome alapján a rendszer **swing pivot**-ot indít. A BC24 és BC25 **PARKOLT** (új scoring felülmúrja őket). Új primáris BC: **BC26 — Swing Pivot Reset** (W21-W30, 8-10 hét). Részletes döntési dok: [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md).

## Kész BC-k (BC1–23)

| BC | Tartalom | Lezárva |
|----|----------|---------|
| BC1–16 | Pipeline, API-k, async, SIM-L1, factor vol | Q1 2026 |
| BC17 | Preflight, monitor_positions, Trail A+B | 2026-03 |
| BC18 | EWMA, MMS activation, Crowdedness shadow | 2026-03 |
| BC19 | SIM-L2 Mód 1, Phase 4 snapshot | 2026-04 |
| BC20 | SIM-L2 Mód 2 re-score engine | 2026-04 |
| BC20A | Swing Hybrid Exit (pipeline split, MKT entry, swing hold) | 2026-04 |
| BC21 | Risk Layer (Correlation Guard, Cross-Asset Regime, Portfolio VaR) | 2026-04 |
| **BC23** | **Scoring & Exit Redesign** (súlyok, TP/SL, positions, simplify) | **2026-04-13** |

## W17 Follow-up — DONE (2026-04-13 ... 2026-04-17)

- TP1 1.25×ATR csökkentés (W16 0/18 hit rate trigger) ✅
- Scoring validation rerun BC23 post-deploy adaton ✅
- Flow component decomposition analysis (232 trade) ✅
- **UW Client Quick Wins** (`533763b`) — header, limit 500, premium aggregation ✅
- **Phase 4 Snapshot Enrichment** (`97fbeda`) — dollar + GEX fields ✅

W17 mérés (ápr 20-24) lezárult: Net +$593, Excess vs SPY +0.13%, Score corr r=+0.18.

## Folyamatban — **W21+ Swing Pivot Reset (2026-05-19 — 2026-07-25)**

**Új primáris BC**: a Day 63 outcome alapján a régi rendszer **negatív expectancy-jű** (Kelly $f^* = -0.23$), **kvázi-zéró edge-gel** (Pearson $\rho = 0$). A swing pivot a **kvantitatívan helyes irány** (mutual information $h=5$ napi holding mellett 5× erősebb).

### Fázis 1 (W21-W22, máj 19 - máj 30) — OPERATIONAL CLEANUP

- IBKR paper account reset (Tamás, máj 19-22)
- IBKR Gateway monitoring + Telegram alert deploy (CC, ~1 óra)
- 10-Q SEC Filing Exclusion + 10 napi earnings exclusion (CC, ~2-3 óra)
- UW config: scoring deaktiválás, shadow log infra (CC, ~1-2 óra)
- Strategic-review `$354 → $665` korrekció (Chat) ✅ KÉSZ 2026-05-14
- Master-reference frissítés (Chat) ✅ KÉSZ 2026-05-14
- Új architektúra design doc skeleton (Chat)

### Fázis 2 (W23-W24, jún 2 - jún 13) — ANALYTIC + DESIGN

- Entry timing backtest (Chat, ~1-2 óra) — 4 alternatív időablak a 60+ napi adaton
- M_contradiction sign-flip elemzés (Chat, ~1 óra)
- Új scoring design doc (`docs/design/swing-scoring-spec.md`) — PCR + OTM-inverse only
- Új risk management spec (`docs/design/swing-risk-spec.md`) — mental stop, time-stop, hard SL
- Új position sizing spec (`docs/design/swing-sizing-spec.md`) — rolling 10-12, 0.35% risk
- CC prototípusok (unit-test szinten, ~3-5 óra)

### Fázis 3 (W25-W30, jún 16 - júl 25) — RE-DEPLOY + ÚJ PAPER TRADING

- W25: új scoring + universum deploy (CC, ~4-6 óra)
- W26 első napjai: új risk management + position sizing deploy (CC, ~8-12 óra)
- **Kb. jún 23 (W26 hétfő)**: IBKR paper reset + **új paper trading INDÚL Day 1-en**
- W27-W30: napi review-k + heti elemzések

**Új Day 63 milestone**: **kb. 2026-09-15 (W37)** — élő kereskedés döntés első valós alapja.

---

## Befejezett — W18-W20 (2026-04-27 — 2026-05-13)

- MID Bundle Integration Shadow Mode — CC DONE 2026-04-27
- M_contradiction multiplier ×0.80 deploy — CC DONE
- W19 paper trading adat: -$241 (4 nap), -0.54%/nap excess
- W20 D1-D3: snapshot fix DEPLOYED (`d3fce73`), dp_pct rekal DEPLOYED (`9a169b9`), tiered BMI guard (`b6db393`)
- Day 63 milestone formal kimenet: **PAPER FOLYTATÁS default** (2026-05-14) ✅

---

## Parkolt / halasztott

### BC22 — HRP Allokáció
**Státusz:** PARKOLVA
**Indok:** A stock selection edge nem bizonyított (BC23 W16: r=−0.414 korreláció). Nincs
értelme allokálási optimalizáláson dolgozni, amíg a scoring alapjai nem adnak alpha-t.
**Újraértékelés:** amikor a BC24 intézményi flow integráció után a scoring korreláció
pozitív.

### GEX Call Wall TP1 Override
**Státusz:** LEZÁRHATÓ — a BC23 már eltávolította a call_wall TP1 override-ot, a BC24
Spot GEX váltás (UW `/api/stock/{ticker}/spot-exposures/strike`) pedig helyettesíti a
problémás részt. Formálisan megjelölve zárva.

### TradingView Layer 1–3 taskok (2026-04-02-es task fájlok)
**Státusz:** PARKOLT (P3, nem sürgős) — az IFDS alap-edge még nem bizonyított,
vizualizációs réteg építésének pillanatnyilag kicsi az érték-hozzáadása.

---

## Új BC-k — tervezett

### BC26 — **Swing Pivot Reset** (~W21-W30, máj 19 - júl 25) ⭐ PRIMÁRIS
**Prioritás:** P0 (a rendszer egyetlen aktív fejlesztési iránya) | **Becsült:** ~25-35 óra CC + ~10-15 óra Chat
**Design alapja:** [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md)

| Fázis | Tartalom | Effort |
|-------|----------|--------|
| 26A | Operational cleanup (W21-W22): IBKR reset, monitoring, 10-Q exclusion, UW deaktiválás | ~5h CC |
| 26B | Analytic + design (W23-W24): entry timing backtest, M_c sign-flip, scoring/risk/sizing spec | ~10h Chat |
| 26C | Scoring deploy (W25): PCR + OTM-inverse only, universum S&P 500 + Russell 1000 | ~4-6h CC |
| 26D | Risk + sizing deploy (W26): mental stop, time-stop, hard SL, rolling 10-12, 0.35% risk | ~8-12h CC |
| 26E | **Új paper trading INDÚL (W26 D1, kb. jún 23)** — napi monitoring + heti review | ongoing |
| 26F | Day 63 milestone (W37, kb. 2026-09-15) — új keret: +$2k + Sharpe>0.5 + 25 pos excess | milestone |

**Amit megold:**
- A 4 instancia LOSS_EXIT bracket SL bug **strukturálisan eliminálódik** (mental stop architektúra)
- A 6 órás intraday holding **strukt. korlátai megszűnnek** (afternoon retracement, slippage, earnings event)
- A flow signal **mutual information 5× erősebb** lesz $h=5$ napi holding mellett
- A scoring **70%-kal egyszerűbb** (PCR + OTM-inverse only, Bonferroni-szignifikáns minimum)

### BC24 — Institutional Flow Intelligence ~~W19-W22~~ **PARKOLT** ⛔
**Új státusz:** PARKOLT (Day 90+ újraértékelés)
**Indok:** az új scoring (PCR + OTM-inverse only) **felülírja** a UW-alapú BC24 javaslatokat. Day 90-en a UW shadow log audit (n=150-180) **újra-aktiválás** lehetőséget ad, ha a true $\rho$ érdemleges.

### BC25 — MID ETF X-Ray Integráció **PARKOLT Day 126-ig** ⛔
**Új státusz:** PARKOLT Day 126 (új milestone) után
**Indok:** a swing pivot **elsődleges**. A MID integráció csak az új 63 napi paper trading sikere után. A MID bundle shadow log működik a Fázis 3 alatt, **adatgyűjtési céllal**.

### BC26 (eredeti) — Multi-Strategy Framework **ÁTKERESZTELVE BC27-re**
**Indok:** a Day 63 outcome új BC26-ot definiál (Swing Pivot Reset). A régi BC26 (multi-strategy) újraértékelendő Q4 2026-ban, ha a swing pivot Day 126 sikeres.

---

## Paper Trading mérföldkövek

| Dátum | Esemény | Státusz |
|-------|---------|---------|
| 2026-05-14 | **Day 63 (eredeti) — milestone outcome** | ✅ LEZÁRT (PAPER FOLYTATÁS default) |
| 2026-05-19 | Fázis 1 Operational Cleanup indítása (W21 D1) | folyamatban |
| ~2026-06-23 | **Új paper trading INDÚL Day 1-en** (W26 D1, sw. pivot) | tervezett |
| ~2026-09-15 | **Új Day 63 milestone (W37) — éles vs paper döntés** | tervezett |
| ~2026-11-15 | Day 180 újraértékelés (ha PAPER FOLYTATÁS újra default) | tentatív |

---

## Felelősségek

- **Chat**: analízis, BC scope írás, doc update javaslat, heti/napi metrika értékelés
- **CC**: implementáció, tesztek, commit, push
- **Tamás**: futtatás Mac Mini-n, jóváhagyás, IBKR, Telegram ellenőrzés

---

## Kapcsolódó

- Aktuális állapot → `docs/STATUS.md`
- Napi/heti rutin → `docs/planning/operational-playbook.md`
- Régi roadmap → `docs/planning/archive/roadmap-2026-consolidated-pre-bc23.md`
- BC scope design docs → `docs/planning/bc23-scoring-exit-redesign.md`, `docs/analysis/uw-api-inventory-v2.md`
