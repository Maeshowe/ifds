# Task: Dark Pool % Debug — UW Adatintegráció Validálása

**Status:** DIAGNOSED — read-only audit done, fix scope deferred to Tamás decision
**Priority:** P1 — API-stratégia stratégiai döntés blokkoló
**Created:** 2026-05-08
**Updated:** 2026-05-08
**Owner:** Claude Code

**Diagnosztikai eredmények rögzítve:**
- `docs/analysis/dp-pct-retrospective-audit.md` — 60 trade, W17-W19, per-ticker UW historikus
- **Két különálló bug felfedezve**:
  1. **Snapshot regresszió** (2026-04-01 470 ticker → 2026-04-10 1 ticker AAPL) — production cron / pipeline split fallout
  2. **Threshold + batch coverage együtt** — `dark_pool_volume_threshold_pct=40` + `UWBatchDarkPoolProvider` (3000 records system-wide ~5000 ticker = 0-1 record/ticker)
- **Stratégiai finding**: dp_pct ↔ P&L per share = **-0.265 (p=0.041, szignifikáns INVERZ!)**, Spearman ρ = -0.327 (p=0.011). Q1 (low dp_pct) win rate 58%, Q5 (high dp_pct) win rate 25%, Q5-Q1 spread = -$163. **A jelenlegi scoring +15 bonus a magas dp_pct-re fordítva használja a jelet** — a tickerek, amelyek bonus-t kapnak, valójában rosszabbul teljesítenek per share.
- **Következő lépés (Tamás döntésére):** scoring sign-flip / removal vs UW dropping vs threshold-ek újrahangolása.

---

## Probléma

A `flow-decomposition.md` (232 ügylet, 2026 májusi elemzés) szerint:

```
| dp_pct_score | 232 | n/a | n/a | 0.00 |
```

**A `dp_pct_score` minden 232 ügyleten 0 érték.** Ez vagy:
1. Az adat **nem fut** (UW API hívás nem történik vagy hibás)
2. A snapshot **mentési logikájában** van bug (az adat fut, de nem mentődik)
3. A scoring **kalkulációs logikájában** van bug (az adat mentődik, de a score nem számítódik)

**Ez egy stratégiai döntés blokkoló**: az UW $150/hó értékének megítélése a dark pool % prediktív erejétől függ. Amíg ez nem tisztázott, az UW kannibalizáció / megtartás döntés **nem hozható meg**.

## A debug folyamat

### 1. lépés — Snapshot adatok ellenőrzése

```bash
cd ~/SSH-Services/ifds
ls -la state/phase4_snapshots/2026-05-0[1-7]*.json.gz
# Egy frissesti snapshot kibontása és a dp_pct mező ellenőrzése
zcat state/phase4_snapshots/2026-05-07.json.gz | python -m json.tool | grep -i 'dp_pct\|dark'
```

**Várt eredmény**: vagy konkrét érték (pl. 35.2, 52.7) **vagy null/0 minden tickerre**.

### 2. lépés — UW API direkt hívás

```bash
.venv/bin/python -c "
from src.ifds.data.unusual_whales import UWClient
import os
client = UWClient(api_key=os.environ['IFDS_UW_API_KEY'])
# Egy ismert ticker (a 2026-05-07 universumából) — pl. QCOM
result = client.get_dark_pool('QCOM')
print(f'QCOM dark pool result: {result}')
"
```

**Várt eredmény**: a UW API válasza a QCOM dark pool adatra. Ha üres / null / error → **az API hívás maga hibás**.

### 3. lépés — A scoring logika átolvasása

```bash
grep -rn 'dp_pct' src/ifds/ --include='*.py' | head -30
```

A `dp_pct_score` mezőt a Phase 4-ben kell számolni. Megnézendő: a scoring kalkuláció lefut-e, és a snapshot mentés tartalmazza-e a számolt értéket.

## Hipotézisek

### Hipotézis A: Az API hívás nem fut

**Tünet**: a UW API direkt hívás üres / error.
**Ok**: rate limit (?), endpoint változás (UW API verzió frissítés), auth probléma.
**Megoldás**: az UW API client kód (~/SSH-Services/ifds/src/ifds/data/unusual_whales.py) frissítése.

### Hipotézis B: Az API hívás fut, de a mentés bug

**Tünet**: a UW API direkt hívás visszaad értéket, de a snapshot-ban 0.
**Ok**: a Phase 4 snapshot mentési logikájában a `dp_pct_score` mező nincs serializálva, vagy default 0-ra állítva.
**Megoldás**: a `phase4_snapshots/` mentési kódjának javítása.

### Hipotézis C: A scoring logika hibás

**Tünet**: az API + snapshot rendben, de a scoring kalkuláció nem számolja a dp_pct_score-t.
**Ok**: a `compute_flow_score()` függvényben a `dp_pct_score` komponens nincs hozzáadva, vagy 0-ra állítva.
**Megoldás**: a scoring függvény javítása.

## A debug eredményei és a következő lépés

A debug **bármelyik hipotézisre lefutva** egy **konkrét fix-et** ad. A fix után:

1. **Újrafuttatni a `flow_decomposition.py` analízist** a meglévő (most már korrigált) snapshot adaton.
2. **Megfigyelni a Pearson r-t** a `dp_pct_score` és a P&L között:
   - Ha **Pearson r > +0,15, p < 0,05** → a dark pool % **prediktív** → **UW MARAD**, dark pool súly emelése javasolt
   - Ha **Pearson r ~0 vagy negatív** → a dark pool % **nem prediktív** → **UW KANNIBALIZÁCIÓ** lehetséges (a PCR és GEX self-built Polygon-ról)

3. **A stratégiai dokumentum frissítése** (`docs/strategic-review/2026-05-08-strategic-review-full.md` és `-summary.md`):
   - 2.4 fejezet (Adatszolgáltatók) frissítése — pontos ár ($665/hó, NEM $354)
   - 6. fejezet kiegészítése — az API-stratégiai következtetés
   - Az `API_STACK.md` frissítése — a 2026-03-01-i adat update-jelölése

## Várt eredmény (becslés)

A `flow_decomposition.md` finding-jaiból (a többi UW komponens sem prediktív): **valószínűleg a 'működik de nem prediktív' eset**. Ekkor a stratégiai irány:

- **UW kannibalizáció** (3-5 fejlesztői nap): self-built PCR (Polygon chain) + self-built GEX (Polygon snapshot) + self-built dark pool % (Polygon Trades + TRF szűrő — már a 2026-03-01-i `API_STACK.md`-ben "BC19 tervezett" feature-ként szerepel).
- **Egyszerűsödés**: 1 API-val kevesebb, ~200-300 sor kódot kannibalizálunk, simpler snapshot mentés.
- **Költségváltozás**: -$150/hó (UW elhagyás). Lehet, hogy a Polygon Options upgrade Developer → Advanced szükséges (+$120/hó) ha real-time options Trades kell — **nettó -$30/hó**, és **simpler arch**.

## Kapcsolódó

- `docs/analysis/flow-decomposition.md` (232 ügylet finding)
- `docs/API_STACK.md` (2026-03-01-i, frissítendő)
- `docs/strategic-review/2026-05-08-strategic-review-full.md` (2.4 fejezet frissítendő)
- `src/ifds/data/unusual_whales.py` (UW API client)
- `src/ifds/scoring/flow.py` (a `dp_pct_score` kalkuláció helye — feltételezhető)
- `src/ifds/phases/phase4_stocks.py` (a snapshot mentési logika)
