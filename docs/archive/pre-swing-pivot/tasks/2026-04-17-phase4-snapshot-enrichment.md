# Phase 4 Snapshot Enrichment — Persist dollar-weighted institutional signals

**Status:** DONE — **DEPENDS ON** `2026-04-17-uw-client-quick-wins.md` (W18 elején éles)
**Updated:** 2026-04-17
**Priority:** P2 — a Quick Wins **folytatása**, nem alternatívája
**Effort:** ~1.5-2h CC
**Depends on:**
- `2026-04-17-uw-client-quick-wins.md` **— élesben 2-3 napig fusson először**
- Verifikáció: `docs/analysis/uw-quick-wins-verification.md` megmutatja, hogy az új `dp_volume_dollars` mező valódi $ értékeket ad

**Ref:** `scripts/analysis/ticker_liquidity_audit_v2.py`, `docs/analysis/uw-api-inventory-v2.md`

---

## A két task kapcsolata

```
Quick Wins (most):
  UW adapter → _aggregate_dp_records() visszaadja:
    dp_volume_dollars ✓
    block_trade_dollars ✓
    (új mezők az adapter outputjában)

      ↓ de: ez NEM megy tovább a model-be és a snapshot-ba

Snapshot Enrichment (ez a task):
  FlowAnalysis model-be átvitt új mezők
  Phase 4 _analyze_flow() kiolvassa és beállítja őket
  Phase 5 GEX mezők → StockAnalysis model-be
  _stock_to_dict() elmenti őket a snapshot-ba

      ↓ eredmény:
  
  A ticker_liquidity_audit_v2 és a flow_decomposition
  dollár-alapú elemzést tud csinálni → BC24 alapozás
```

**Prerekvizit:** a Quick Wins élesben kell legyen és adatot adjon. Ha a verifikációs script azt mutatja, hogy a `dp_volume_dollars` továbbra is 0 vagy közel ahhoz, akkor **állj** — mélyebb vizsgálat kell, nem ennek a taskba rohanás.

## Motiváció

A ticker_liquidity_audit_v2 azt mutatta:
- 1265 unique ticker / 43 snapshot
- 92.4% a persistent ticker-eknek csak 0-10% DP coverage
- **Oka: a snapshot nem tárolja a dollár-alapú DP adatot**

A Quick Wins ezt az adapter szintjén megoldja (új mezők keletkeznek). De ezek az új mezők **nem jutnak el a snapshot-ig** a jelenlegi pipeline-ban. Ez a task ezt orvosolja.

## Változások

### 1. FlowAnalysis model kiegészítés

**Fájl:** `src/ifds/models/market.py` — `FlowAnalysis` dataclass

Új mezők (opcionális default értékekkel a backward compatibility miatt):
```python
# Dollar-weighted dark pool metrics (BC24 foundation)
dp_volume_shares: int = 0          # abszolút DP shares, a meglévő dark_pool_pct alapja
total_volume: int = 0               # teljes napi stock volume (likviditás kontextus)
dp_volume_dollars: float = 0.0     # _aggregate_dp_records-ből (QW után)
block_trade_dollars: float = 0.0   # block trade-ek dollár összeg
venue_entropy: float = 0.0          # Shannon entropy venue eloszláson (már kiszámolódik)
```

**Tesztelés:** a meglévő `test_flow_analysis_*` tesztek default értékekkel működnek. Új teszt: `test_flow_analysis_enriched_fields` explicit beállítással.

### 2. Phase 4 `_analyze_flow()` kiegészítés

**Fájl:** `src/ifds/phases/phase4_stocks.py`

A `_analyze_flow()` jelenleg az adapterből kapott dp_data-ból csak a `dark_pool_pct`, `block_trade_count` mezőket használja. Most bővítjük:

```python
flow = FlowAnalysis(
    rvol=rvol,
    rvol_score=rvol_score_total,
    dark_pool_pct=dp_data.get("dp_pct", 0.0),
    dp_pct_score=dp_pct_score,
    # ... meglévő mezők ...
    # ÚJ mezők (QW után elérhetőek):
    dp_volume_shares=dp_data.get("dp_volume", 0),
    total_volume=dp_data.get("total_volume", 0),
    dp_volume_dollars=dp_data.get("dp_volume_dollars", 0.0),
    block_trade_dollars=dp_data.get("block_trade_dollars", 0.0),
    venue_entropy=dp_data.get("venue_entropy", 0.0),
)
```

### 3. Phase 5 GEX mezők a StockAnalysis-be

**Fájl:** `src/ifds/models/market.py` — `StockAnalysis` dataclass

**Két opció** (bármelyik OK):

**A) Új opcionális GEXData blob:**
```python
@dataclass
class StockAnalysis:
    # ... meglévő mezők ...
    gex: dict | None = None  # Phase 5 outputja, {"net_gex", "call_wall", "put_wall", "zero_gamma"}
```

**B) Lapos mezők a StockAnalysis-ben:**
```python
net_gex: float | None = None
call_wall: float | None = None
put_wall: float | None = None
zero_gamma: float | None = None
```

**Javaslat: B)** — egyszerűbb a snapshot mentésnél, nincs nested serializálás. Ha később a GEX bonyolultabb lesz (Vanna/Charm QW4 után), akkor lehet GEXData dataclass.

**Fájl:** `src/ifds/phases/phase5_gex.py` — a Phase 5 run végén a StockAnalysis objektumot módosítja a GEX adatokkal. Ez már részben létezik (a `M_gex` multiplier-hez), csak a mezőket kell beírni a StockAnalysis-be.

### 4. `_stock_to_dict()` kiegészítés

**Fájl:** `src/ifds/data/phase4_snapshot.py`

```python
def _stock_to_dict(stock) -> dict:
    # ... meglévő mezők ...
    return {
        # ... meglévő ticker/sector/scoring/technical/flow/fundamental ...
        # ÚJ — Flow dollar metrics
        "dp_volume_shares": fl.dp_volume_shares,
        "total_volume": fl.total_volume,
        "dp_volume_dollars": fl.dp_volume_dollars,
        "block_trade_dollars": fl.block_trade_dollars,
        "venue_entropy": fl.venue_entropy,
        # ÚJ — GEX mezők (Phase 5 after)
        "net_gex": getattr(stock, "net_gex", None),
        "call_wall": getattr(stock, "call_wall", None),
        "put_wall": getattr(stock, "put_wall", None),
        "zero_gamma": getattr(stock, "zero_gamma", None),
    }
```

### 5. Backward compatibility a snapshot loading-ban

**Fájl:** `src/ifds/data/phase4_snapshot.py` — `snapshot_to_stock_analysis()`

A BC20 Mód 2 re-score a régi snapshot-okat olvassa. Új mezők hiányoznak a régi snapshot-okban, tehát:

```python
def snapshot_to_stock_analysis(record: dict) -> "StockAnalysis":
    # ... meglévő ...
    flow = FlowAnalysis(
        # ... meglévő ...
        dp_volume_shares=record.get("dp_volume_shares", 0),      # default 0 ha régi
        total_volume=record.get("total_volume", 0),
        dp_volume_dollars=record.get("dp_volume_dollars", 0.0),
        block_trade_dollars=record.get("block_trade_dollars", 0.0),
        venue_entropy=record.get("venue_entropy", 0.0),
    )
    stock = StockAnalysis(
        # ... meglévő ...
    )
    # GEX mezők a StockAnalysis-re beállítva
    stock.net_gex = record.get("net_gex")
    stock.call_wall = record.get("call_wall")
    stock.put_wall = record.get("put_wall")
    stock.zero_gamma = record.get("zero_gamma")
    return stock
```

**Kritikus:** a **43 meglévő snapshot** változatlanul olvasható lesz, az új mezők pedig `0` vagy `None` értéket kapnak. A BC20 Mód 2 re-score nem törik.

## Tesztek

- `test_flow_analysis_enriched_fields` — új mezők alapértelmezetten 0, explicit beállítással is működnek
- `test_stock_analysis_gex_fields` — GEX mezők opcionálisak
- `test_snapshot_save_and_load_enriched` — új mezőkkel mentett + betöltött snapshot megőrzi az értékeket
- `test_snapshot_load_backward_compatible` — **kritikus**: a régi 43 snapshot valamelyikét betölti, nem hal meg hiányzó mezőre
- Integration: egy Phase 4+5 futás után a mentett snapshot tartalmazza a dollár mezőket, és a ticker_liquidity_audit_v2 ezeken dolgozva más eloszlást ad

**Kritikus regressziós teszt:** a meglévő scoring nem változik! Az új mezők **csak tárolásra** kerülnek, a combined_score kiszámítása változatlan.

## Commit

```
feat(models+snapshot): enrich snapshots with dollar-weighted flow + GEX

FlowAnalysis model gains dollar-weighted dark pool fields:
- dp_volume_shares, total_volume, dp_volume_dollars
- block_trade_dollars, venue_entropy

These fields are populated by Phase 4 _analyze_flow() from the enriched
_aggregate_dp_records() output (UW client Quick Wins commit 0xXXXXXX).

StockAnalysis gains optional Phase 5 GEX fields:
- net_gex, call_wall, put_wall, zero_gamma

_stock_to_dict() and snapshot_to_stock_analysis() are extended with
backward compatibility: existing 43 snapshots load with default values
(0 for shares/dollars, None for GEX fields). BC20 Mode 2 re-score unaffected.

Scoring logic unchanged — this task only extends data persistence. The
scoring can use the new fields in a follow-up commit (W19+ BC24 design).

Prerequisite for:
- Dollar-weighted ticker_liquidity_audit_v3 (Cat A/B/C/D with real thresholds)
- BC24 Institutional Conviction Score
- GEX time-series regime detection

Refs:
- docs/analysis/uw-api-inventory-v2.md
- docs/analysis/ticker-liquidity-audit-v2.md
- docs/tasks/2026-04-17-uw-client-quick-wins.md (prereq)
```

## Timeline

| Időpont | Esemény |
|---------|---------|
| Most | Quick Wins task CC-nél fut, commit |
| Hétfő-kedd | Quick Wins élesben, verifikációs script |
| Szerda | **Döntési pont**: a QW verifikáció sikeres? Ha igen → CC megkapja ezt a taskot |
| Csütörtök-péntek | CC implementálja ezt |
| Jövő hét hétfőtől | Új snapshot-ok az új mezőkkel gyűjtődnek |
| **W19 péntek (május 1)** | ~10 új snapshot gyűlt → dollár-alapú `ticker_liquidity_audit_v3` futás |

## Nem változik

- A Phase 4-5 futási logika — ugyanúgy fut, csak a mentendő kimenetek bővülnek
- A flow/scoring számítás — a new mezők csak **perzisztálva vannak**, a scoring még nem használja
- A 43 meglévő snapshot — változatlanul olvasható, backward compatible
- A BC20 Mód 2 re-score — továbbra is működik, az új mezőket default értékkel olvassa
