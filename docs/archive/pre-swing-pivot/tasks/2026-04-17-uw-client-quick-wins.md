# UW Client Quick Wins — Header, Limit, Premium Aggregation

**Status:** DONE
**Updated:** 2026-04-17
**Priority:** P1 — a liquidity audit v2 megmutatta, hogy a DP adatok 92.4%-a 0-10% coverage-ben van, ami valószínűleg bug + konfigurációs probléma kombinációja
**Effort:** ~1.5h CC
**Ref:** `docs/analysis/uw-api-inventory-v2.md`, `docs/analysis/ticker-liquidity-audit-v2.md`

---

## Motiváció

A UW API doc (skill.md) és a mi adapterünk összehasonlítása 3 kritikus problémát derített ki:

1. **Hiányzó kötelező `UW-CLIENT-API-ID: 100001` header** — minden UW kérés specifikáció-nem-konform
2. **`limit=200`** — a UW támogatja a `limit=500` default/max-ot, azaz **2.5× több DP trade rekord** kérhető tickeren
3. **`premium` mezőt nem aggregáljuk** — a response minden trade-nél tartalmazza a dollár volume-ot, de mi csak a shares-t (size) összegezzük

A három változás együtt **várhatóan** megjavítja a 0%-ra kerekedő `dp_pct` problémát, amit a ticker_liquidity_audit és a flow_decomposition is említett.

## Változások — 3 pont

### 1. `UW-CLIENT-API-ID` header hozzáadása

**Fájlok:** `src/ifds/data/unusual_whales.py`, `src/ifds/data/async_clients.py`

```python
# unusual_whales.py:40 (és async_clients.py megfelelő része)
def _auth_headers(self) -> dict[str, str]:
    if self._api_key:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "UW-CLIENT-API-ID": "100001",    # ÚJ
            "User-Agent": "PythonClient",
            "Accept": "application/json",     # ÚJ — explicit
        }
    return {}
```

**Teszt:** meglévő UW tesztek nem törnek. Ellenőrzés: egy live hívás előtt/után, payload méret és response tartalom változik-e (feltehetően több mező vagy gazdagabb response).

### 2. `limit=500` a ticker DP hívásoknál

**Fájlok:**
- `src/ifds/data/unusual_whales.py:65` — `get_dark_pool()`
- `src/ifds/data/async_clients.py` — `AsyncUWClient.get_dark_pool()`

```python
# RÉGI:
data = self._get(endpoint, params={"limit": 200}, headers=self._auth_headers())
# ÚJ:
data = self._get(endpoint, params={"limit": 500}, headers=self._auth_headers())
```

**Ne** változtasd meg a `get_dark_pool_recent()` limit paraméterét (batch prefetch) — az már a max 500-at használja helyesen.

**Teszt:** integration teszt, hogy a response mérete több. A meglévő `test_uw_client_get_dark_pool` working példái változatlanul működnek (kevesebb rekord is valid).

### 3. `premium` mező aggregálása

**Fájl:** `src/ifds/data/adapters.py` → `_aggregate_dp_records()`

```python
def _aggregate_dp_records(records: list[dict]) -> dict:
    """..."""
    import math
    from collections import Counter

    dp_buys = 0
    dp_sells = 0
    dp_volume = 0               # meglévő (shares)
    dp_volume_dollars = 0.0     # ÚJ — dollar amount
    total_volume = 0
    block_trade_count = 0
    block_trade_dollars = 0.0   # ÚJ — block trade dollar total
    venue_counts: Counter = Counter()

    for record in records:
        size = _safe_int(record.get("size", 0))
        dp_volume += size

        # ÚJ: premium = trade dollar value (size × price, precomputed)
        premium = _safe_float(record.get("premium", 0))
        dp_volume_dollars += premium

        # Each DP record carries the stock's total day volume
        vol = _safe_int(record.get("volume", 0))
        if vol > total_volume:
            total_volume = vol

        price = _safe_float(record.get("price", 0))

        # Block trade detection ($500K+ notional)
        notional = size * price
        if notional > 500_000:
            block_trade_count += 1
            block_trade_dollars += notional  # ÚJ

        # ... többi változatlan ...

    # ... buys/sells classification változatlan ...

    dp_pct = round((dp_volume / total_volume) * 100, 2) if total_volume > 0 else 0.0

    return {
        "dp_volume": dp_volume,
        "dp_volume_dollars": dp_volume_dollars,     # ÚJ
        "total_volume": total_volume,
        "dp_pct": dp_pct,
        "dp_buys": dp_buys,
        "dp_sells": dp_sells,
        "signal": signal,
        "source": "unusual_whales",
        "block_trade_count": block_trade_count,
        "block_trade_dollars": block_trade_dollars, # ÚJ
        "venue_entropy": venue_entropy,
    }
```

**Teszt:** 
- `test_aggregate_dp_records_includes_premium` — egy mock record list {size, price, premium} → dp_volume_dollars = sum(premium)
- `test_aggregate_dp_records_block_dollars` — a $500K+ notional trade-ek dollár értéke helyesen aggregálódik
- A meglévő `test_aggregate_dp_records_*` változatlanul működik (új mezők jelenléte nem töri őket)

## Verifikációs script

**Fájl:** `scripts/analysis/uw_quick_wins_verification.py` (ÚJ)

Egy összehasonlító script ami:

1. Kiválaszt 10 tickert a liquidity audit v2 top 30-ból (LITE, SNDK, MU, INTC, NVDA, TSM, AAOI, WDC, AMD, XOM)
2. **Két hívást** csinál minden tickerre:
   - RÉGI mód: limit=200, nincs UW-CLIENT-API-ID header
   - ÚJ mód: limit=500, UW-CLIENT-API-ID: 100001
3. Az `_aggregate_dp_records()` outputját összehasonlítja a két módból
4. Riportol:
   - dp_volume shares: régi vs új
   - dp_volume_dollars: régi (0, mert nem volt) vs új (valódi $ érték)
   - dp_pct: hogyan változott
   - trade count: 200 vs 500+
   - response status code (egyenlőek-e?)

**Cél:** objektív mérés, hogy a 3 fix ténylegesen javít-e az adatok minőségén. Ez lesz az argumentum, hogy élesítsük őket production-ben.

**Output:** `docs/analysis/uw-quick-wins-verification.md` — konkrét számokkal

## Tesztek

- Unit: mock-olt UW response-ok, új mezők jelenléte
- Integration: a meglévő `test_uw_*` és `test_dark_pool_*` tesztek változatlanul futnak
- Verification script: manuálisan futtatva, ember által elbírált output

**Kritikus:** semmi regressziót nem szabad okozni. Az új `dp_volume_dollars`, `block_trade_dollars` mezők opcionálisak minden downstream kódban — a scoring **jelenleg** nem változik, csak az adatok gyűjtése gazdagszik. A scoring változása külön CC task lesz (W18+).

## Commit

```
fix(uw-client): add required header, increase limit, aggregate premium

UW API skill.md specifies UW-CLIENT-API-ID: 100001 as required on all
requests. Add it to both sync and async clients along with Accept header.

The /api/darkpool/{ticker} endpoint supports limit up to 500 (doc default),
but our client was sending limit=200. Increase to 500 for 2.5x more DP
trade records per ticker call.

The response premium field (size × price, server-precomputed) was not
being aggregated. Add dp_volume_dollars and block_trade_dollars to
_aggregate_dp_records() output. Downstream consumers (flow scoring,
snapshot persistence) will use these in a follow-up commit.

No regression: all existing tests pass unchanged. New fields are
additive; dp_volume (shares) and dp_pct (shares-based) remain for
backward compatibility.

Verification script (scripts/analysis/uw_quick_wins_verification.py)
compares before/after data richness on top 10 liquid tickers.

Refs: docs/analysis/uw-api-inventory-v2.md
```

## Rollback

Mind a három változás **additive vagy tiszta konfig**, nincs destruktív módosítás. Rollback egyszerű `git revert`.

A `UW-CLIENT-API-ID` header hozzáadása elméletileg változtathatja a szerver-oldali viselkedést (pl. rate limit különbség), de:
- Nincs publikus dokumentáció arra, hogy a header hiánya eltérő rate limit-et eredményez
- Az UW skill.md ezt mint KÖTELEZŐT nevezi — feltételezzük, hogy a szerver jóindulatú defaulttal kezeli a header hiányt, de a jelenléte **nem rontja** a rate limitet

Ha **bármilyen** oldalhatás látszik (Telegram alertek, failed API calls hirtelen megnövekedése), a header egyedül visszavehető.

## Nem változik

- A Phase 4 scoring logika — a `dp_pct_score` számítás ugyanaz marad, csak a dp_pct input értelmesebb lesz
- A batch DP prefetch (`/api/darkpool/recent`) már 500 limit-et használ
- A GEX endpoint (`greek-exposure/strike`) — ennek a spot verzióra váltása külön task (QW4 a dokumentumban)
- A kliens osztályok szerkezete — csak header és params módosítás

## Siker kritériumok (1 hét live után)

| Metrika | Elvárt változás | Mérés |
|---------|-----------------|-------|
| Top 30 ticker dp_pct értékek | 0% → legalább 1-10% tartomány stabil | `ticker_liquidity_audit_v2` rerun |
| DP trade count / hívás (top 30) | átlag 50-100 → 150-300 | verification script |
| dp_volume_dollars jelenléte | nincs → valódi $ érték | új mező jelenlétének ellenőrzése |
| `dp_pct_score` correlation vs P&L | jelenleg 0 (broken) → mérhető korreláció | `scripts/analysis/flow_decomposition.py` rerun a W18 végén |
