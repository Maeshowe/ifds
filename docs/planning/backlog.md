# IFDS — Fejlesztési Backlog
<!-- Frissíti: Chat/CC, in-place -->
<!-- Utolsó frissítés: 2026-04-17 -->

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

## Folyamatban — W18 Shadow Mode (2026-04-27 — 2026-05-01)

- **MID Bundle Integration Shadow Mode** — CC DONE 2026-04-27
  - `MIDClient` + bundle snapshot storage (`state/mid_bundles/YYYY-MM-DD.json.gz`)
  - Phase 0 hook (non-blocking, X-API-Key header)
  - Offline `mid_vs_ifds_sector_comparison.py` script
  - 25 új test, 1377 passing
  - Aktiválás: Mac Mini `MID_API_KEY` beállítás (Tamás, kedd reggel)
- **M_contradiction multiplier ×0.80** — CC pending (Chat task fájl szerda reggel)
- Adatgyűjtés W18 alatt → W19 elején BC25 GO/NO-GO döntés

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

### BC24 — Institutional Flow Intelligence (~W19–W22, május 4–29)
**Prioritás:** P1 | **Becsült:** ~20–25 óra CC, fázisokban
**Design alapja:** `docs/analysis/uw-api-inventory-v2.md`

| Phase | Tartalom | Effort |
|-------|----------|--------|
| 24A | UW Spot GEX váltás (static → spot-exposures/strike) | ~3h |
| 24B | UW Flow Alerts integráció (sweep detection) | ~4h |
| 24C | UW Market Tide integráció (aggregate sentiment) | ~3h |
| 24D | UW Net Premium Ticks (intraday flow catalyst) | ~4h |
| 24E | Institutional Conviction Score (dollar-weighted DP + GEX composite) | ~4h |
| 24F | BC24 integrált scoring A/B teszt vs BC23 | ~3h |

**Előfeltétel:** W18 végén dollár-alapú `ticker_liquidity_audit_v3` eredmény — ez
definiálja a BC24 ticker univerzumát (Institutional Relevance Filter).

**Amit megold:**
- A flow komponens végre valódi institutional signal, nem retail zaj
- Intraday catalyst detection (net prem ticks + flow alerts)
- A szektor VETO nem csak momentum-alapú lesz (BC25-ben MID CAS-szel együtt)

### BC25 — MID ETF X-Ray Integráció (~W23+, május 18-)
**Prioritás:** P2 | **Becsült:** ~2 nap CC
**Előfeltétel:** **MID oldali** BC `BC-etf-xray-institutional-13f-layer` legalább Phase B
kész. Task: `docs/tasks/future-2026-04-17-bc-ifds-phase3-from-mid.md`

| Phase | Tartalom |
|-------|----------|
| 25A | MIDClient + Phase 3 sector rotation átváltás MID CAS-re |
| 25B | Új VETO logika: DIVERGENT_SMART_SELL állapot kezelés |
| 25C | Consensus-alapú sector scoring (Flow CAS + 13F + UW Unusual konvergencia) |

### BC26 — Multi-Strategy Framework (~Q3)
**Prioritás:** P3 | **Státusz:** OUTLINE ONLY
Ha a BC24+25 után a scoring alap stabil, multi-stratégia hozzáadás (event-driven /
mean reversion / momentum).

---

## Paper Trading mérföldkövek

| Dátum | Esemény |
|-------|---------|
| **2026-05-14** | Day 63 — **éles vs paper döntés** |
| 2026-06-xx | BC24 élesben 2–3 hét után: első teljes-hónapos értékelés |
| 2026-07-xx | BC25 MID integráció, ha menetelő |

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
