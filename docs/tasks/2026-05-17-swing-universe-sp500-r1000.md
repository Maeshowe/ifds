# Task: Swing Universe — S&P 500 + Russell 1000 forrás

**Status:** DONE
**Updated:** 2026-05-18 (Ülés A, deploy ahead of schedule)
**Actual effort:** ~1.5h (live smoke + header-driven parser rewrite Russell 1000-hez)
**Priority:** P0 (Fázis 3 deploy, BLOKKOLÓ — minden további task függősége)
**Created:** 2026-05-17 (vasárnap, Fázis 2+3 deploy nap)
**Owner:** Claude Code
**Estimated effort:** ~1h CC

**Source decision:** [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) §3.9 — Döntés [9]: "Universum: S&P 500 + Russell 1000 (~1000)".

**Depends on:** nincs (ez minden további swing task előfeltétele)

---

## 1. A változás

A jelenlegi `Phase 2` FMP screener-alapú universum (~1390 ticker) lecserélve **S&P 500 + Russell 1000 union** (~1000-1100 ticker, dedupe után).

**Indoklás (Day 63 outcome §3.9):**
- A swing horizon (3-5 nap) **likviditás-érzékenyebb** mint az intraday — a Russell 1000 alsó határa (~$700M-1B market cap) elfogadható, de a Russell 2000 small-cap rétege a swing slippage-érzékenység miatt **kizárandó**
- A `S_j > 50` Bonferroni-minimum scoring threshold **stable universe distribution-t igényel** — a heti-szezonális FMP screener-rotáció (universum változás 30%+ napi) instabilizálja a percentile normalizálást
- A `S&P 500 + Russell 1000` egy **stabil, kvantitatív értelemben jól dokumentált** indexszet — a percentile rang-distribúció stabil
- A `state/universe_snapshots/` survivorship bias védelem (BC13) **változatlanul aktív**

## 2. Adat forrás

Két megközelítés (vagylagos, a CC választhat a megbízhatóbb alapján):

### 2.A — Wikipedia parse (egyszerű, free)

- S&P 500: `https://en.wikipedia.org/wiki/List_of_S%26P_500_companies` → 1. táblázat, ticker oszlop
- Russell 1000: `https://en.wikipedia.org/wiki/Russell_1000_Index` → "List of components" táblázat (~1000 ticker)

**Előny**: ingyenes, nincs API-key, megbízhatóan frissített
**Hátrány**: HTML scrape, format-érzékeny (Wikipedia oldalstruktúra módosulhat)

### 2.B — Polygon `/v3/reference/tickers` (paid)

Polygon Advanced tier-en: `GET /v3/reference/tickers?type=CS&market=stocks&active=true`, de **NEM** indexszet — minden listed common stock. Index-membership-et **külön nem ad** közvetlenül.

**Előny**: stabil API, rate-limited
**Hátrány**: nincs natív index filter, post-filter szükséges

### Javasolt: 2.A (Wikipedia) + 2.B fallback

Elsődleges: Wikipedia parse. Ha sikertelen (HTML changed, network) → Polygon-ról minden CS listed, majd FMP `/v3/index-listings?index=sp500` és `index=russell1000` cross-check.

A két forrás **uniója + dedupe** = ~1000-1100 ticker.

## 3. Implementáció

### 3.1. Új modul: `src/ifds/data/swing_universe.py` (~80 sor)

```python
"""S&P 500 + Russell 1000 union universe source."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
import json
import requests

logger = logging.getLogger(__name__)

SP500_WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
R1000_WIKI = "https://en.wikipedia.org/wiki/Russell_1000_Index"

class SwingUniverseSource:
    def __init__(self, cache_dir: Path, cache_ttl_days: int = 7):
        self.cache_dir = cache_dir
        self.cache_ttl = timedelta(days=cache_ttl_days)

    def get_universe(self) -> list[str]:
        """Visszaadja a S&P 500 + Russell 1000 union ticker listát (~1000-1100)."""
        cached = self._load_cache()
        if cached:
            return cached
        sp500 = self._fetch_sp500()
        r1000 = self._fetch_russell1000()
        universe = sorted(set(sp500) | set(r1000))
        self._write_cache(universe)
        return universe

    def _fetch_sp500(self) -> list[str]:
        """Wikipedia parse, fallback FMP."""
        ...

    def _fetch_russell1000(self) -> list[str]:
        """Wikipedia parse, fallback FMP."""
        ...
```

### 3.2. Phase 2 integráció

A `src/ifds/phases/phase2_universe.py`-ben:

```python
def build_universe(config):
    if config["universe_source"] == "swing_sp500_r1000":
        source = SwingUniverseSource(cache_dir=Path(config["swing_universe_cache_dir"]))
        candidates = source.get_universe()
    else:
        # Régi FMP screener (megőrzendő mint fallback)
        candidates = fmp_screener(...)

    # Common filters (market cap, price, volume) változatlanok
    # Earnings + 10-Q exclusion (Fázis 1 DONE)
    return filtered_candidates
```

### 3.3. Új TUNING paraméterek (`defaults.py`)

```python
# Swing Universe (2026-05-17, Day 63 §3.9)
"universe_source": "swing_sp500_r1000",  # "fmp_screener" | "swing_sp500_r1000"
"swing_universe_cache_dir": "state/swing_universe",
"swing_universe_cache_ttl_days": 7,       # Wikipedia havi indexrebalansz miatt
```

## 4. Tesztek (5-7)

```python
def test_swing_universe_returns_around_1000_tickers():
    """~1000-1100 ticker visszaadva (kombinált S&P 500 + Russell 1000)."""

def test_swing_universe_no_duplicates():
    """Dedupe működik — az S&P 500 ⊂ Russell 1000 átfedés kezelve."""

def test_swing_universe_uses_cache():
    """7 napi cache: nem hív API-t friss cache esetén."""

def test_swing_universe_cache_refresh_on_expire():
    """7+ napi cache → fetch + write."""

def test_swing_universe_wikipedia_failure_falls_back_to_fmp():
    """Wikipedia HTML changed → FMP fallback."""

def test_phase2_integration_swing_source():
    """Phase 2 build_universe() helyesen használja a swing source-ot ha config kéri."""
```

## 5. Validáció (Tamás)

A deploy után az első Phase 2 cron futás (22:00 CEST):

```bash
ls -la state/swing_universe/
cat state/swing_universe/universe.json | python -m json.tool | head -20
# Várt: ~1000-1100 ticker
```

A Phase 2 log:
```
Universe source: swing_sp500_r1000
Total candidates: 1024 (S&P 500: 502, Russell 1000: 1003, union: 1024)
After filters (market_cap, price, volume, earnings, 10-Q): 873
```

## 6. Out of scope

- **Russell 2000** beolvasása — explicit kizárt (slippage-érzékenység)
- **NASDAQ-100** vagy más index — a Russell 1000 magában foglalja
- **Realtime index-membership API** (S&P S-DOW Indices, FTSE Russell) — fizetős, 7 napi Wikipedia-frissítés elegendő

## 7. Commit message

```
feat(universe): S&P 500 + Russell 1000 swing universe source

Day 63 outcome §3.9: replace FMP screener (~1390 unstable) with
S&P 500 + Russell 1000 union (~1000-1100 stable) for swing horizon.

- New module: src/ifds/data/swing_universe.py
  - Wikipedia primary, FMP fallback
  - 7-day cache (monthly index rebalance buffer)
- Phase 2 integration: config-toggleable universe_source
  - "swing_sp500_r1000" (default for swing pivot)
  - "fmp_screener" (legacy, kept as fallback)

Tests: 6 unit + 1 integration.

Refs: docs/decisions/2026-05-14-day63-decision-outcome.md §3.9
```

## 8. Kapcsolódó

- [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) §3.9
- [`docs/design/swing-pivot-architecture.md`](../design/swing-pivot-architecture.md) §2.1
- [`docs/tasks/2026-05-17-swing-scoring-phase4.md`](2026-05-17-swing-scoring-phase4.md) (függőség — a percentile normalizáláshoz stabil universe-distribúció kell)
