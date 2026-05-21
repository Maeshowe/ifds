Status: DONE
Updated: 2026-04-03
Note: BC20A Phase_20A_1 — VWAP Modul (~2h CC)
Depends: BC20 kész (baseline SIM megvan)

# BC20A Phase_20A_1 — VWAP Modul (Entry Quality Filter)

## Cél

VWAP (Volume Weighted Average Price) kalkuláció Polygon 5-min bars-ból,
entry quality filter a Phase 6-ban.

## Scope

### 1. `src/ifds/phases/vwap.py` — Új modul

```python
def calculate_vwap(bars_5min: list[dict]) -> float:
    """Calculate VWAP from intraday 5-minute bars.
    
    VWAP = Σ(typical_price × volume) / Σ(volume)
    typical_price = (high + low + close) / 3
    """

def vwap_entry_check(
    current_price: float,
    vwap: float,
    reject_pct: float = 2.0,
    reduce_pct: float = 1.0,
    boost_pct: float = -1.0,
) -> str:
    """Check entry quality relative to VWAP.
    
    Returns: "REJECT" | "REDUCE" | "BOOST" | "NORMAL"
    """

async def fetch_intraday_vwap(
    polygon: AsyncPolygonClient,
    tickers: list[str],
    date_str: str,
) -> dict[str, float]:
    """Fetch 5-min bars and calculate VWAP for multiple tickers."""
```

### 2. Polygon API hívás

```
GET /v2/aggs/ticker/{ticker}/range/5/minute/{today}/{today}
```

Polygon Advanced tier: unlimited calls, real-time, 5-min aggregates.
A jelenlegi `polygon.py` sync client-jébe + `async_clients.py`-ba is kell.

### 3. Phase 6 integráció (csak előkészítés)

A VWAP guard logika helye: `_calculate_position()` függvényben, de
egyelőre **shadow módban** (logol, nem szűr). Az élesítés a Phase_20A_3-ban
(Pipeline Split + MKT Entry) történik.

```python
# phase6_sizing.py — shadow VWAP log
if vwap_data and ticker in vwap_data:
    vwap = vwap_data[ticker]
    distance_pct = (entry - vwap) / vwap * 100
    logger.log(EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=6,
               message=f"[VWAP] {ticker} price={entry:.2f} vwap={vwap:.2f} "
                       f"dist={distance_pct:+.1f}%")
```

## Tesztelés

- `test_vwap.py`:
  - calculate_vwap: 5 bars → correct VWAP
  - calculate_vwap: 0 volume bar → skipped
  - calculate_vwap: empty bars → 0.0
  - vwap_entry_check: price 3% above VWAP → "REJECT"
  - vwap_entry_check: price 1.5% above → "REDUCE"
  - vwap_entry_check: price 2% below → "BOOST"
  - vwap_entry_check: price at VWAP → "NORMAL"
- `pytest` all green

## Commit

```
feat(vwap): add VWAP module with entry quality filter

Polygon 5-min bars VWAP calculation + entry quality check
(REJECT >2%, REDUCE >1%, BOOST <-1%, NORMAL). Shadow mode
in Phase 6 — full activation in Phase_20A_3 pipeline split.
```
