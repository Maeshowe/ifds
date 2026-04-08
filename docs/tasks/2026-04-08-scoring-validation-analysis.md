# Scoring Validáció & Multiplier Hatáselemzés

**Status:** DONE
**Updated:** 2026-04-08
**Priority:** HIGH — ez dönti el, hogy az IFDS-nek van-e edge-je
**Effort:** ~3h CC
**Scope:** Elemzési script, nem production kód. Kimenet: `docs/analysis/scoring-validation.md`

---

## Kontextus

37 kereskedési nap, -1.5% cum P&L, 0 TP2 hit, ~80% MOC exit. A kérdés: a scoring rendszer termel-e alpha-t, vagy a P&L pusztán a napi piaci irány függvénye?

## Elérhető adatok

- `state/phase4_snapshots/YYYY-MM-DD.json.gz` — ~36 nap, minden scored ticker
- `output/execution_plan_run_*.csv` — ~42 CSV, a kiválasztott tickerek + score + multiplierek
- `scripts/paper_trading/logs/cumulative_pnl.json` — napi P&L
- `scripts/paper_trading/logs/trades_YYYY-MM-DD.csv` — ticker-szintű fill árak + exit árak

## Feladat: `scripts/analysis/scoring_validation.py`

### 1. Score → P&L korreláció

Minden kereskedési napra:
- Execution plan-ból: ticker, score, entry price
- Trades CSV / EOD log: exit price, P&L, exit type
- Join: score ↔ P&L per ticker per nap

Kérdések:
- **Score quintiles**: a top quintile (93+) jobban teljesít-e mint a bottom (89-90)?
- **Score vs P&L scatter**: van-e korreláció? (Pearson/Spearman)
- **Win rate by score bucket**: 93+ vs 91-93 vs 89-91 → win rate (P&L > 0)

### 2. Score komponens hatás

Ha a Phase 4 snapshotban megvannak a flow/funda/tech alkomponensek:
- Melyik komponens korrelál legerősebben a P&L-lel?
- A flow (0.40 súly) valóban a legfontosabb?
- Ha egy komponenst kicserélnénk random-ra, mennyit változna a teljesítmény?

### 3. Multiplier chain értékelés

Az execution plan CSV-ben benne van: `multiplier_total`, `mult_vix`, `mult_utility`
- A többi multiplier (M_flow, M_insider, M_funda, M_gex, M_target) rekonstruálható a Phase 4 snapshotból?
- Kérdés: a magasabb M_total tickerek jobban teljesítenek-e?
- Scatter: M_total vs P&L per trade
- Ha M_total nem korrelál → a multiplierek csak zajt adnak

### 4. Piaci irány kontroll

A fenti korrelációk értéktelenek ha a piaci irány dominálja a P&L-t.
- Kontroll: SPY napi return az adott napon
- Kérdés: a score korrelál-e a P&L-lel **a napi piaci irány levonása után**?
  - Excess return = ticker P&L - (SPY return × ticker beta)
  - Ha a score korrelál az excess return-nel → van alpha
  - Ha nem → a scoring random, csak a piac irány számít

### 5. Exit típus elemzés

- TP1 hit rate score bucket-enként
- Átlagos P&L exit típusonként: TP1 vs SL vs MOC vs LOSS_EXIT vs TRAIL
- A MOC exit-ek átlag P&L-je közel nulla? (mert a napi irány random)

## Kimenet

`docs/analysis/scoring-validation.md` — táblák, korrelációs számok, scatter plotok (matplotlib → PNG mentés `docs/analysis/plots/`-ba)

## Fontos

- Ez NEM production kód — `scripts/analysis/` mappába kerül
- Read-only: a pipeline-t nem módosítja
- A snapshotok gzipped JSON-ok — `gzip` + `json` modulok kellenek
- SPY napi return a Polygon API-ból kérhető, vagy a Phase 0 logokból kiolvasható
- Ha a Phase 4 snapshot nem tartalmazza a score komponenseket → jelezd, mit tartalmaz

## Commit üzenet

```
analysis: scoring validation — score→P&L correlation, multiplier impact

Standalone analysis script to determine if IFDS scoring generates alpha.
Joins Phase 4 snapshots, execution plans, and trade results.
Output: docs/analysis/scoring-validation.md with tables and plots.
```
