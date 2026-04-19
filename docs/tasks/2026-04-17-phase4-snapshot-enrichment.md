# Phase 4 Snapshot Enrichment — Persist dollar-weighted institutional signals

**Status:** OPEN
**Updated:** 2026-04-17
**Priority:** P2 — nem blokkoló, de a BC24 design document előfeltétele
**Effort:** ~1-2h CC
**Depends on:** —
**Ref:** `scripts/analysis/ticker_liquidity_audit.py` (első iteráció korlátai)

---

## Motiváció

A ticker liquidity audit első iterációja azt mérte, hogy **van-e** institutional adat egy tickerre; de azt nem, hogy **érdemes-e**. A jelenlegi Phase 4 snapshot (`src/ifds/data/phase4_snapshot.py` → `_stock_to_dict()`) **nem tárolja**:

- `dp_volume` (abszolút shares darabszám) — dollár-alapú signal strength
- `total_volume` (teljes napi volume) — likviditás kontextus, DP/total normalizáláshoz
- `venue_entropy` — a Shannon entropy már kiszámolódik `_aggregate_dp_records()`-ben, de a FlowAnalysis model-ben nem perzisztálódik
- **Phase 5 GEX mezők:** `net_gex`, `call_wall`, `put_wall`, `zero_gamma` — ezek jelenleg csak in-memory-ban élnek a Phase 6 sizing részeként

Ez a hiány megakadályozza:
1. A dollár-alapú institutional liquidity audit-ot (Cat. A vs Cat. D "valódi" küszöbbel)
2. A BC24 Institutional Conviction Score tervezést (venue entropy, block intensity dollárban)
3. A GEX idősor elemzést (regime detection, Gamma Flip Point stabilitás)

## Változások

### 1. FlowAnalysis model kiegészítés

**Fájl:** `src/ifds/models/market.py` — `FlowAnalysis` dataclass

Új mezők:
```python
# Dollar-weighted dark pool metrics
dp_volume_shares: int = 0          # abszolút DP shares (nem %)
total_volume: int = 0               # teljes napi stock volume
dp_volume_dollars: float = 0.0     # dp_volume_shares × avg_price
venue_entropy: float = 0.0          # Shannon entropy a DP venue-eloszlásra
block_trade_dollars: float = 0.0   # blokk trade-ek összdollár értéke ($500K+)
```

### 2. `_aggregate_dp_records()` kiegészítés

**Fájl:** `src/ifds/data/adapters.py`

A függvény már kiszámolja ezeket (lines 290-330), csak a return dict-be kell hozzáadni:
```python
return {
    # ... meglévő mezők ...
    "dp_volume_dollars": sum(size * price for record in records ...),
    "block_trade_dollars": sum(size * price for record in records
                               if size * price > 500_000),
}
```

### 3. `FlowAnalysis`-ba betöltés a Phase 4-ben

**Fájl:** `src/ifds/phases/phase4_stocks.py`

A `_analyze_flow()` függvényben a DP adatokat már megkapjuk; a új mezőket átírjuk a FlowAnalysis-ba.

### 4. Phase 5 GEX mezők perzisztálása

**Fájl:** `src/ifds/models/market.py` + `src/ifds/data/phase4_snapshot.py`

Két opció:

**A) GEX mezőket a StockAnalysis model-be:**
```python
@dataclass
class StockAnalysis:
    # ... meglévő mezők ...
    gex: GEXData | None = None  # Phase 5 után töltve
```

**B) Külön Phase 5 snapshot:**
```
state/phase5_snapshots/2026-04-17.json.gz
```

**Javaslat: A opció.** A Phase 4-5 már most is ugyanazon a ticker-univerzumon dolgozik; érdemes egy fájlban tárolni. A `save_phase4_snapshot()`-ot át kell nevezni (`save_pipeline_snapshot()`) és a mentés timing-ját Phase 5 után tolni.

### 5. `_stock_to_dict()` kiegészítés

**Fájl:** `src/ifds/data/phase4_snapshot.py`

```python
def _stock_to_dict(stock) -> dict:
    # ... meglévő mezők ...
    return {
        # ... meglévő ...
        # New flow fields
        "dp_volume_shares": fl.dp_volume_shares,
        "total_volume": fl.total_volume,
        "dp_volume_dollars": fl.dp_volume_dollars,
        "venue_entropy": fl.venue_entropy,
        "block_trade_dollars": fl.block_trade_dollars,
        # New GEX fields (if Phase 5 ran)
        "net_gex": stock.gex.net_gex if stock.gex else None,
        "call_wall": stock.gex.call_wall if stock.gex else None,
        "put_wall": stock.gex.put_wall if stock.gex else None,
        "zero_gamma": stock.gex.zero_gamma if stock.gex else None,
    }
```

Megjegyzés: A `snapshot_to_stock_analysis()` (inverz függvény) a BC20 Mód 2 re-score-hoz használja a snapshot-okat. Ha új mezők kerülnek be, a visszaolvasást is frissíteni kell.

## Tesztek

- `test_phase4_snapshot_enriched_fields` — a save + load megőrzi az új mezőket
- `test_snapshot_backward_compatible` — **a régi snapshot-ok (pre-BC24) is betölthetők** (új mezők default értéket kapnak)
- Integration: egy Phase 4-5 futás után a snapshot tartalmazza mind a flow, mind a GEX új mezőket

**Kritikus:** A backward compatibility miatt **a régi snapshot-ok NE törlődjenek**, és a load függvény kezelje a hiányzó mezőket (getattr defaulttal).

## Commit

```
feat(phase4): enrich snapshot with dollar-weighted institutional signals

- FlowAnalysis: dp_volume_shares, total_volume, dp_volume_dollars,
  venue_entropy, block_trade_dollars
- StockAnalysis: optional gex field (populated after Phase 5)
- phase4_snapshot: renamed to pipeline_snapshot (saves after Phase 5)

Prerequisite for:
- Dollar-weighted liquidity audit (Cat A/B/C/D with real thresholds)
- BC24 Institutional Conviction Score
- GEX time-series regime detection

Backward compatible: old snapshots load with default values for new fields.
```

## Timeline

- **Implementáció:** 1-2h
- **Első új snapshot generálódik:** a következő napi Phase 4-5 futásnál
- **2 hét múlva (~10 új snapshot):** elég adat az első dollár-alapú re-audit-hoz → a **BC24 design document pontos univerzumára** támaszkodhat

## Nem változik

- A régi snapshot formátum olvasható marad (BC20 Mód 2 re-score nem törik)
- A Phase 4-5 futási logika ugyanaz, csak a mentendő kimeneti mezők bővülnek
- A flow/scoring számítás változatlan — **csak az adatok mentését bővítjük**
