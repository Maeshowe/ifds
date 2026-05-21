# UW API Inventory — amit használunk, amit nem, és a kritikus bugok

**Frissítés:** 2026-04-17
**Forrás:** UW API docs (https://api.unusualwhales.com/docs), skill.md, institutional.md
**Cél:** BC24 design alapdokumentuma — a flow/institutional intelligence elemhez

---

## 1. Kritikus bugok a jelenlegi kódban

### 🚨 Bug #1 — Hiányzó kötelező header

A UW skill.md (AI Anti-Hallucination Protocol) szerint **minden** UW kérésnek tartalmaznia kell:

```
UW-CLIENT-API-ID: 100001
```

A mi `src/ifds/data/unusual_whales.py` `_auth_headers()` függvénye ezt nem küldi. A kérések most is mehetnek (Bearer token elég a authentikációhoz), **de** a szerver valószínűleg eltérően kezeli őket:
- Potenciálisan korlátozott response payload
- Potenciálisan silenced hibák vagy rate limit eltérések

**Fix:** egyetlen sor hozzáadás mindkét client-ben (sync + async):

```python
def _auth_headers(self) -> dict[str, str]:
    if self._api_key:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "UW-CLIENT-API-ID": "100001",  # ÚJ — kötelező header
            "User-Agent": "PythonClient",
            "Accept": "application/json",  # explicit
        }
    return {}
```

### 🔢 Bug #2 — Alacsony `limit` a darkpool hívásoknál

A `/api/darkpool/{ticker}` endpoint doc-ja szerint:
- **`limit` default: 500, max: 500, min: 1**

A mi kódunk `limit=200`-at küld:
```python
# unusual_whales.py:65
data = self._get(endpoint, params={"limit": 200}, ...)
```

**Hatás:** 2.5× kevesebb trade rekord tickerenként. A likvid tickereknél (SPY, AAPL, NVDA napi 1000+ DP trade) **ez a limit bevágja a napi képet**.

**Fix:** `"limit": 500`.

### 💰 Bug #3 — `premium` mező nem aggregálódik

A `/api/darkpool/{ticker}` response minden trade-hez tartalmazza a **`premium`** mezőt (= size × price = dollár volume). Példa a response-ból:
```json
{"size": 6400, "price": "18.99", "premium": "121538.56", ...}
```

A mi `_aggregate_dp_records()` (src/ifds/data/adapters.py) csak a `size`-ot aggregálja shares darabban:

```python
for record in records:
    size = _safe_int(record.get("size", 0))
    dp_volume += size    # ← csak shares, nem dollár
```

**Hatás:** A `dp_pct` **kerekítéssel 0-hoz** esik olyan tickereken ahol a shares alapú pct néhány tized százalék — mert a batch limit csak a legnagyobb blokkokat kapja meg, és ezek shares száma relatíve kicsi a napi volume-hoz képest.

**Fix:**

```python
# _aggregate_dp_records() kiegészítés
dp_volume_dollars = 0.0
for record in records:
    premium = _safe_float(record.get("premium", 0))
    dp_volume_dollars += premium
# ...
return {
    # ... meglévő mezők ...
    "dp_volume_dollars": dp_volume_dollars,  # ÚJ
}
```

Ezután a scoring-ban használjuk a **dollár-alapú pct**-et:
```python
dp_pct_dollars = dp_volume_dollars / (total_volume * avg_price) * 100
```

---

## 2. Jelenleg használt endpointok

| Endpoint | Használat | Fájl |
|----------|-----------|------|
| `/api/darkpool/{ticker}` | Per-ticker DP (fallback) | `UWDarkPoolProvider` |
| `/api/darkpool/recent` | Batch DP prefetch | `UWBatchDarkPoolProvider` |
| `/api/stock/{ticker}/greek-exposure` | Aggregate greeks (nem aktív) | `get_greeks()` |
| `/api/stock/{ticker}/greek-exposure/strike` | **Static** GEX per strike | `UWGEXProvider` |

**Fontos tanulság:** a `/api/stock/{ticker}/greek-exposure/strike` a **STATIC** GEX-et adja (open interest × gamma, konstans a nap során). A UW skill.md szerint **létezik egy SPOT verzió is**:

- `/api/stock/{ticker}/spot-exposures/strike` — **az aktuális spot ár alapján újraszámolt**, intraday frissülő GEX

A mi BC24 "Gamma Flip Point" analízishez **pontosan a spot verzió kell**. A váltás minimális kódmódosítás (endpoint URL csere a UWGEXProvider-ben).

---

## 3. Új endpoint ajánlás (TIER 1-3)

### 🔥 TIER 1 — BC24 Phase 1 (Institutional Flow Core)

#### Dark Pool + Options Flow

| Endpoint | Mit ad | Miért fontos |
|----------|--------|--------------|
| `/api/option-trades/flow-alerts` | **Sweep alertek** market-wide | Multi-exchange szimultán execution = institutional urgency. Params: `is_call`, `is_put`, `is_otm`, `min_premium`, `ticker_symbol`, `size_greater_oi`. **Ez hiányzik a jelenlegi flow_score-ból teljesen.** |
| `/api/screener/option-contracts` | **Hottest chains** screener | Market-wide unusual options. Params: `min_volume_oi_ratio`, `min_premium`, `type`. **Ez a Phase 2 screener-rel összehangolva: dinamikus catalyst detektor.** |
| `/api/stock/{ticker}/net-prem-ticks` | **Per-minute net premium** buy vs sell | Intraday flow — a "mikor" kérdésre válasz. **Pontosan a time-misalignment problémát kezeli.** |
| `/api/stock/{ticker}/flow-recent` | Ticker-specifikus recent flow | Watchlist monitoring reggel |

#### GEX (intraday frissülő)

| Endpoint | Mit ad | Miért |
|----------|--------|-------|
| `/api/stock/{ticker}/spot-exposures/strike` | **SPOT GEX** per strike (váltás static helyett) | Intraday frissülő, a BC24 Gamma Flip Point analízishez |

#### Institutional 13F (Moneyflows core)

| Endpoint | Mit ad | Miért |
|----------|--------|-------|
| `/api/institutions` | Bulk list (~9000 institution) | SQLite cache alap |
| `/api/institutions/latest_filings` | Új 13F bejelentések | Event detection |
| `/api/institution/{ticker}/ownership` | **Ki vesz/adja el ma?** | **Ez a Moneyflows alapötlet konkretizálása** |
| `/api/institution/{cik}/activity/v2` | Per-institution trading | Druckenmiller/Tepper/egyén trading követés |

#### Market Aggregate

| Endpoint | Mit ad | Miért |
|----------|--------|-------|
| `/api/market/market-tide` | Aggregate sentiment (net_call_premium, net_put_premium) | **MID integráció** + regime filter |

### TIER 2 — BC24 Phase 2

| Endpoint | Mit ad |
|----------|--------|
| `/api/stock/{ticker}/greeks` | Per-strike, per-expiry greeks (Vanna/Charm) |
| `/api/stock/{ticker}/interpolated-iv` | IV percentiles |
| `/api/stock/{ticker}/options-volume` | Volume/PC ratio |
| `/api/institution/{cik}/holdings` | Teljes portfolio |
| `/api/institution/{cik}/sectors` | Sector bontás |

### TIER 3 — BC25+ (későbbi)

| Endpoint | Megjegyzés |
|----------|------------|
| `/api/congress/recent-trades` | Politician trading (érdekes, de nem prioritás) |
| `/api/news/headlines` | Egyszerű news feed |
| `/api/stock/{ticker}/financials` | **Redundáns** FMP-vel |
| `/api/stock/{ticker}/technical-indicator/{function}` | **Redundáns** Polygon-nal |
| `/api/insider/transactions` | **Redundáns** FMP-vel |

---

## 4. UW Institutional SQLite Architecture (TIER 1 speciális)

A UW skill.md javasolja: a **9,000 institution** metaadatát egyszer töltsd be SQLite-ba, aztán helyi gyors lookup. Ez pont beleillik a MID architektúrába (a MID már SQLite-ot használ).

**Kulcs concepts:**

**9 táblázat** — institutions + institution_activity. CIK = 10-digit zero-padded string PRIMARY KEY.

**1500 tagged institution:**
- `hedge_fund` (~1300)
- `known` (~curated important funds)
- `activist`, `13d_activist`
- `value_investor`, `biotech`, `tiger_club`, `technology`
- `small_cap`, `credit`, `energy`, `event`, `real_estate`, `esg`, `public_companies`

**Per-ticker positioning buckets:**
- `closed` = exited
- `new` = first_buy == current quarter → **erős signal**
- `added` = meglévő pozíció növelés
- `trimmed` = csökkentés
- `held` = unchanged

**Multi-quarter trajectory (historical_units 8 negyedévre):**
- `building` — multi-quarter accumulation → **building conviction**
- `harvesting` — systematic reduction → profit taking
- `new_conviction` — fresh thesis
- `volatile` — tactical trading
- `steady` — long-term hold

**Ez a BC24 "Institutional Conviction Score" alapja lehet.**

---

## 5. Quick Wins — azonnal implementálható fixek

Sorrendben prioritás szerint:

### QW1 — `UW-CLIENT-API-ID` header (5 perc)
**Fájlok:** `unusual_whales.py`, `async_clients.py`  
**Hatás:** minden UW kérés specifikáció-konform lesz  
**Kockázat:** minimális

### QW2 — `limit=500` a DP ticker hívásokban (2 perc)
**Fájlok:** `unusual_whales.py:65`, `async_clients.py` megfelelő rész  
**Hatás:** 2.5× több trade rekord per ticker  
**Kockázat:** enyhén nagyobb payload (ignorálható)

### QW3 — `premium` mező aggregálása (20 perc + teszt)
**Fájl:** `src/ifds/data/adapters.py` → `_aggregate_dp_records()`  
**Új mezők:** `dp_volume_dollars`, `block_trade_dollars`  
**Hatás:** dollár-alapú `dp_pct` mérés → valódi institutional signal strength  
**Kockázat:** új mezők, meglévő számítások változatlanok. A scoring később használja.

### QW4 — `spot-exposures/strike` váltás static helyett (10 perc + teszt)
**Fájl:** `src/ifds/data/adapters.py` → `UWGEXProvider.get_gex()`  
**Hatás:** intraday frissülő GEX, Gamma Flip Point analízishez alap  
**Kockázat:** response schema **feltehetően azonos**, de ellenőrizni kell. Ha eltérő, adapter-waktan kell.

### QW5 — Rate limit monitoring skill integráció (30 perc)
**Forrás:** https://unusualwhales.com/skills/uw-api-usage-monitor-skill.md  
**Kimenet:** napi dashboardon UW API usage mérő, pipeline-on belül rate limit reporting  
**Hatás:** láthatóvá teszi ha a BC24 több endpoint bevezetés túl sokat kér → kerekítve a rate limit határához  

**A QW1-3 fejezhet egyetlen commit-ba.** A QW4 külön, mert teszteléssel. A QW5 később.

---

## 6. Dokumentumfeltérképezés — amit még meg kell néznem

A session-ben elért UW doc-k:
- ✅ Overview / landing
- ✅ Ticker Darkpool Trades endpoint
- ✅ skill.md (AI reference)
- ✅ institutional.md skill

**Amit még nem néztem meg:**
- `/api/market/market-tide` részletes schema — a MID-hez kulcs
- `/api/option-trades/flow-alerts` részletes schema — a sweep detector szívverése
- `/api/stock/{ticker}/spot-exposures/strike` — a SPOT GEX response schema
- `/api/stock/{ticker}/net-prem-ticks` — intraday flow schema
- https://unusualwhales.com/skills/uw-api-usage-monitor-skill.md
- MID ETF X-Ray forráskódból (nem live webapp)

**Következő session feladata:** ezeket átnézni, majd a BC24 design document első draft-ja.

---

## 7. Hallucinált (nem létező) endpointok

A UW skill.md explicit "blacklist"-et ad arról, hogy melyik endpoint-okat **NE** próbálják meg a LLM-ek:

- ❌ `/api/options/flow` → használd `/api/option-trades/flow-alerts`
- ❌ `/api/flow` vagy `/api/flow/live`
- ❌ `/api/stock/{ticker}/flow` → használd `/api/stock/{ticker}/flow-recent`
- ❌ `/api/stock/{ticker}/options` → használd `/api/stock/{ticker}/option-contracts`
- ❌ `/api/unusual-activity`
- ❌ Bármely `/api/v1/` vagy `/api/v2/` prefix (kivétel: `/api/institution/{cik}/activity/v2`)
- ❌ Query params `apiKey=` vagy `api_key=` — **csak** `Authorization` header

Ezek a blacklist-ek arra utalnak, hogy a UW **sokszor látja** ezeket a hibákat LLM-ek által generált kódokban. A mi CC jövőbeli kódjának explicit **ezeken kívül** kell mozognia.

---

## 8. UW MCP Server — alternatíva elérés

A UW biztosít egy **hivatalos MCP servert** (https://api.unusualwhales.com → MCP Server resource). Ez egy natív Claude/AI integráció, amit mi jelenleg NEM használunk.

**Előnyök:**
- Natív Claude hívások (Opus 4.7 közvetlenül kérheti, nincs REST wrapping)
- UW maintenance → automatikus endpoint követés
- Nincs HTTP boilerplate

**Hátrányok:**
- A mi pipeline Python-ban fut, a CC automatizálások Bash + Python
- MCP integráció a pipeline-ba bonyolult (a CC-nek kell MCP kliens)
- Rate limiting közös a REST-tel

**Javaslat:** **Continue REST**. A MCP integráció nem ad funkcionális különbséget a mi pipeline-unknak. De ha egy **manuális elemzés/kutatás** (pl. "ki vesz ma AAPL-t?") érdekes, a Claude.ai-ban közvetlenül a UW MCP-t lehet használni.

---

## 9. Következő lépések

**Azonnali (ma/holnap):**
1. CC task a QW1-3 implementációra — egyszerű, kis kockázatú
2. A debug script bővítése: mérje meg a QW1-3 hatását egy before/after összehasonlítással

**1 hét múlva (W18 vége):**
3. CC task a QW4 implementációra — spot GEX váltás tesztelve
4. Snapshot enrichment task (már írva: `docs/tasks/2026-04-17-phase4-snapshot-enrichment.md`) ezzel összekapcsolva

**2 hét múlva (W19):**
5. BC24 design document első draft
6. Az új endpoint-ok fokozatos integrálása (Flow Alerts → Market Tide → Institutional 13F)

**Fontos:** Mielőtt a BC24 design irányvonalat eldönti, a QW1-3 élesben kell futnia **legalább egy hét**, és a dp_pct metrikákat újra kell mérni. Ha a `UW-CLIENT-API-ID` header + limit 500 + premium aggregálás után **még mindig** 0%-ok dominálnak, akkor valódi rendszerszintű probléma van, nem konfig.
