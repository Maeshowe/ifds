# Task: 10-Q / 10-K SEC Filing Exclusion (Phase 2 universum-szűrés)

**Status:** DONE
**Priority:** P1 (Fázis 1, [`04-risks §1.2`](../master-reference/04-risks-and-open-questions.md))
**Created:** 2026-05-21 (W21 D3 szerda)
**Updated:** 2026-05-16 (Ülés B — deployed; 1611-ticker live smoke 100% success, 0 429, 16 flagged)
**Owner:** Claude Code
**Estimated effort:** ~2–3h (SEC EDGAR API integráció + Phase 2 szűrés + cache + tesztek)

**Source decision:** [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) §3.10 — a 10 napi earnings exclusion-höz **kapcsolódó** plus védelem: a 10-Q és 10-K SEC filing event-eket is ki kell zárni.

**Depends on:** [`2026-05-19-earnings-exclusion-7to10.md`](2026-05-19-earnings-exclusion-7to10.md) — előbb deployolva, hogy a 10 napi időablak közös legyen.

**NEM depends on:** semmilyen swing pivot komponens. A 10-Q exclusion a régi és új architektúrán **egyaránt** releváns.

---

## 1. A probléma

A 60 napi paper trading dokumentált 3 earnings-szűrő lyukat. Egyikük, az **AGNC 2026-05-04**, **NEM** earnings release volt, hanem **10-Q SEC filing event** 17:21 CEST-kor. A 7 napos earnings exclusion (még a 10 napira való emelés után is) **nem zárja ki**, mert:
- Az FMP `/earnings_calendar` endpoint **csak earnings release-eket** tartalmaz
- A 10-Q (negyedéves) és 10-K (éves) jelentések **külön event-ek**, gyakran az earnings release-től **eltérő dátummal**

**Eredmény (AGNC):** -$380 6-split LOSS_EXIT, a pozíció a 10-Q közben tartózkodott a piacon.

**Ezt a típusú esemény-rést a 7→10 napi earnings exclusion önmagában NEM oldja meg** — szükséges a 10-Q / 10-K filing dátumok lekérdezése a SEC EDGAR-tól.

## 2. A SEC EDGAR API — alapok

SEC EDGAR ingyenes, regisztráció nélküli REST API, a `User-Agent` header **kötelező** (cég/személy + email kapcsolat). Rate limit: **10 req/sec per IP**.

A releváns endpoint a "company submissions":

```
GET https://data.sec.gov/submissions/CIK{cik_10_digit_zero_padded}.json
Headers: User-Agent: "IFDS Trading Research safrtam@example.com"
```

A response a cég utolsó ~1000 filing-ját tartalmazza, ebből szűrhető a `form` mező alapján:
- `10-Q` — quarterly report
- `10-K` — annual report
- `8-K` — current report (gyakori esemény, **nem zárandó ki** automatikusan, mert magában foglalja az earnings release-eket is)

**Mezők:** `filingDate`, `reportDate`, `form`, `accessionNumber`, `primaryDocument`.

**A ticker → CIK leképezés** egy különálló JSON: `https://www.sec.gov/files/company_tickers.json` (~12 000 tételes mapping, kb. 600 KB, naponta frissítendő).

## 3. Architektúra

```
Phase 2 universe builder
  ↓
  for each candidate ticker:
    cik = ticker_to_cik(ticker)  ← cache: state/sec_cik_map.json (refresh 30d)
    upcoming_filings = sec_filings_for_cik(cik)  ← cache: state/sec_filings/{cik}.json (refresh 1d)
    if any filing.expectedDate in next 10 days and filing.form in ('10-Q', '10-K'):
      exclude
  ↓
  filtered universe
```

**Kulcs design döntés:** A SEC EDGAR a **múltbeli** filing-eket adja vissza, NEM a **jövőbeli várt** filing-eket. A "10-Q a következő 10 napon belül" predikció **a múltbeli quarterly cycle-ből kalkulálandó**:

```python
def predict_next_10q_date(filings):
    """A negyedéves 10-Q cycle alapján predikció:
    az utolsó 10-Q-tól számolt +90 nap ± toleranc.
    """
    last_10q = max(f for f in filings if f.form == "10-Q")
    predicted = last_10q.filingDate + timedelta(days=90)
    # Toleranc ±10 nap a real-world quarterly variabilitás miatt (Tamás döntés 2026-05-15)
    return predicted, tolerance_days=10
```

**Alternatív megközelítés:** a `dataset/forms_8K` `2.02` item-jét nézni (az earnings release event), és ahonnan 10-Q tipikusan 30-45 napon belül következik. Ez **komplexebb**, és a `predict_next_10q_date` becslés ~85%-os pontossága az IFDS scope-jához **elégséges** (false positive = unfair kizárás, false negative = exposed pozíció).

## 4. Implementáció lépésekben

### 4.1. Új modul: `src/ifds/data/sec_edgar.py` (~80 sor)

```python
"""SEC EDGAR API kliens — 10-Q / 10-K filing exclusion."""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import requests

logger = logging.getLogger(__name__)

SEC_BASE = "https://data.sec.gov"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
USER_AGENT = "IFDS Trading Research safrtam@example.com"  # Tamás email kitöltendő
RATE_LIMIT_SLEEP = 0.11  # 10 req/sec biztonsággal

class SecEdgarClient:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cik_map = self._load_or_fetch_cik_map()

    def _load_or_fetch_cik_map(self) -> dict[str, str]:
        """Ticker → 10-digit CIK leképezés, 30 napi cache."""
        ...

    def get_recent_filings(self, ticker: str, max_age_days: int = 1) -> list[dict]:
        """A ticker utolsó filing-jeit kéri le, 1 napi cache."""
        ...

    def has_upcoming_10q_or_10k(self, ticker: str, lookahead_days: int = 10) -> bool:
        """Igaz, ha a következő `lookahead_days` napon belül 10-Q/10-K várható."""
        filings = self.get_recent_filings(ticker)
        if not filings:
            return False
        predicted, tolerance = predict_next_10q_date(filings)
        days_until = (predicted - datetime.now(timezone.utc)).days
        return -tolerance <= days_until <= lookahead_days

def predict_next_10q_date(filings: list[dict]) -> tuple[datetime, int]:
    """A negyedéves cycle becslése. Tolerancia ±10 nap (Tamás döntés 2026-05-15)."""
    ...
```

### 4.2. Phase 2 integráció

A `src/ifds/phases/phase2_universe.py`-ben (vagy ahol a `NearEarnings` predikátum van):

```python
# Új szűrés a meglévő earnings exclusion után
if config["sec_filing_exclusion_enabled"]:
    sec_client = SecEdgarClient(cache_dir=Path("state/sec_cache"))
    candidates = [
        t for t in candidates
        if not sec_client.has_upcoming_10q_or_10k(t.symbol, lookahead_days=config["earnings_exclusion_days"])
    ]
```

### 4.3. Új TUNING paraméterek (`defaults.py`)

```python
# SEC EDGAR Filing Exclusion (2026-05-21, Fázis 1)
"sec_filing_exclusion_enabled": True,
"sec_filing_lookahead_days": 10,           # Egyezzen az earnings_exclusion_days-szel
"sec_filing_quarterly_tolerance_days": 10,  # ±10 nap a 10-Q predikcióhoz (Tamás döntés 2026-05-15)
"sec_filing_cache_dir": "state/sec_cache",
"sec_filing_cik_refresh_days": 30,
"sec_filing_filings_refresh_days": 1,
```

### 4.4. Új RUNTIME / env

```python
# RUNTIME["sec_user_agent"]: kötelező SEC EDGAR-hoz
# Env var: IFDS_SEC_USER_AGENT
```

### 4.5. Tesztek

```python
# tests/test_sec_edgar.py

def test_predict_next_10q_quarterly_cycle():
    """A legutóbbi 10-Q +90 nap a következő várt dátum."""
    ...

def test_has_upcoming_10q_within_window():
    """Ha a következő 10-Q ≤10 napra van, True."""
    ...

def test_has_upcoming_10q_outside_window():
    """Ha a következő 10-Q >10 napra van, False."""
    ...

def test_cik_map_uses_cache():
    """30 napi cache: nem hív API-t friss cache esetén."""
    ...

def test_filings_cache_refresh_on_stale():
    """1 napi cache: stale → fetch + write."""
    ...

def test_user_agent_header_required():
    """A request fejléc User-Agent kötelező."""
    ...

def test_rate_limit_sleep_applied():
    """A 10 req/sec rate limit betartva."""
    ...

def test_agnc_2026_05_04_excluded_retroactively():
    """Mock filings: az AGNC 2026-05-04 esete kizárná-e a Phase 2-ben.

    Mock data: AGNC last 10-Q 2026-02-04, predicted next 10-Q 2026-05-05.
    Lookahead from 2026-05-04: 1 nap → True → exclude.
    """
    ...
```

### 4.6. Validáció (Tamás közreműködésével)

A deploy után a következő Phase 2 cron log:

```bash
grep -E "sec_filing|10-Q|10-K|EDGAR" logs/cron_phase123_$(date +%Y%m%d)*.log
```

**Várt finding:** néhány ticker explicit "excluded — upcoming 10-Q in N days" log-ot mutat.

Plusz: a `state/sec_cache/` mappa létrejön, benne `cik_map.json` és `filings/{cik}.json` fájlokkal.

## 5. Tagolási megfontolás — egyetlen task vagy kettő?

A 2-3h scope egyetlen task fájlon belül **kezelhető**, NEM tagolom külön sub-task-okra. Indoklás:

- A SEC EDGAR kliens (4.1) és a Phase 2 integráció (4.2) **szorosan összefüggnek** — egy commit hatékonyabb
- A tesztek (4.5) az implementációval párhuzamosan írandók
- A 7→10 nap config change **külön task** ([`2026-05-19-earnings-exclusion-7to10.md`](2026-05-19-earnings-exclusion-7to10.md)) — ott önállóan deploy-olható, és a SEC integrációhoz NEM kell

Ha a CC implementáció közben a scope-ot túl nagynak találja (pl. a `predict_next_10q_date` heuristika bonyolultabb mint becsültem), **megengedett a kettős tagolás**:
- Sub-task A: SEC EDGAR kliens + cache (csak adat-beolvasás, NEM Phase 2 integráció), ~1.5h
- Sub-task B: Phase 2 integráció + tesztek, ~1h

## 6. Commit message draft

```
feat(phase2): SEC EDGAR 10-Q / 10-K filing exclusion

Closes 04-risks §1.2 P1 — the 60-day sample showed an AGNC 2026-05-04
case where a 10-Q filing event (not an earnings release) caused a
-$380 LOSS_EXIT. The FMP earnings calendar doesn't cover SEC filing
events, so a separate data source is needed.

- New module: src/ifds/data/sec_edgar.py (SecEdgarClient)
  - Ticker → CIK mapping (30-day cache)
  - Recent filings per ticker (1-day cache)
  - Quarterly 10-Q prediction (±10 day tolerance)
  - Rate-limited (10 req/sec, SEC requirement)
  - Mandatory User-Agent header

- Phase 2 integration: new filter after earnings_exclusion_days check
  - Configurable lookahead (default: 10 days, matches earnings window)
  - Configurable tolerance (default: ±10 days)

- 8 unit tests + 1 retroactive AGNC validation test

Refs: docs/decisions/2026-05-14-day63-decision-outcome.md §3.10
```

## 7. Out of scope (explicit)

- **8-K event filtering** — magas false positive rate (az 8-K-k 70%-a routine), nem éri meg
- **ADR earnings adatforrás fix (P3.1)** — külön task ([`04-risks §3.1`](../master-reference/04-risks-and-open-questions.md))
- **SEC EDGAR full-text search** — most csak filing metadata kell
- **A `predict_next_10q_date` ML-modell verzió** — a heuristika ~85% pontosság elégséges, ML felesleges komplexitás

## 8. Döntések (Tamás 2026-05-15)

### Döntés 1 — `User-Agent` header: env var-on keresztül

A `IFDS_SEC_USER_AGENT` env var-ból töltődik, hogy a tényleges email NE kerüljön a git-be. A kódban a default literal egy placeholder, amely WARNING-ot vált ki ha nincs beállítva:

```python
USER_AGENT_DEFAULT = "IFDS Trading Research <set IFDS_SEC_USER_AGENT env>"
USER_AGENT = os.getenv("IFDS_SEC_USER_AGENT", USER_AGENT_DEFAULT)

if "<set IFDS_SEC_USER_AGENT env>" in USER_AGENT:
    logger.warning(
        "IFDS_SEC_USER_AGENT not configured — SEC EDGAR requests may be rate-limited or rejected. "
        "Set env var to 'Your Name your.email@example.com' format."
    )
```

**Production env beállítás** (Tamás, Mac Mini-n):
```bash
launchctl setenv IFDS_SEC_USER_AGENT "Safranszki Tamas safrtam@example.com"
# Tamás a tényleges email-t választja (az IBKR Telegram bot env-eknél is ugyanaz a minta).
```

### Döntés 2 — Quarterly tolerancia: ±10 nap

A `predict_next_10q_date` heuristika ±10 napi tolerancia-ablakot használ (a `sec_filing_quarterly_tolerance_days: 10` TUNING param fent frissítve). Indoklás:

| Tolerancia | False positive (méltatlan kizárás) | False negative (átszívárgó 10-Q) |
|---|---|---|
| ±3 nap | ~1% | ~30% (túl agresszív) |
| ±7 nap | ~5–10% | ~5–10% (a kockázat-aszimmetriának nem felel meg) |
| **±10 nap** | **~10–15%** | **~2–5%** (Tamás választott) |
| ±14 nap | ~20% | ~1% (túl konzervatív) |

**A kockázat-aszimmetria**: false positive olcsó (1–2 ticker méltatlanul kizárt 1000-es univerzumból, van pótlék), false negative DRÁGA (AGNC 2026-05-04 = -$380 / split). A ±10 nap a kockázat-aszimmetriának megfelelő konzervatív-közbenső érték.

**A `lookahead_days: 10` + `tolerance: ±10`** = **20 napi effektív védőzóna** a várt 10-Q körül. A Fázis 3 deploy előtt a 60 napi mintán backteszttel ellenőrzendő a tényleges false positive ráta — ha >15%, érdemes ±7-re csökkenteni.

### Döntés 3 — Failure mode: (C) cache-only fallback → (A) fail-open

A SEC EDGAR API leesett vagy rate-limit hibája esetén a Phase 2 viselkedése:

```python
def has_upcoming_10q_or_10k(self, ticker: str, lookahead_days: int = 10) -> bool:
    """
    Failure mode (Tamás 2026-05-15):
    1. Próbáld a friss API hívást
    2. API fail → cache fallback ha cache <= 2 napi (reasonable freshness)
    3. Cache miss vagy stale → fail-open (return False) + WARNING log + Telegram alert
    """
    try:
        filings = self._fetch_filings_fresh(ticker)  # API + write cache
    except SecEdgarError as e:
        cache_age = self._get_cache_age(ticker)
        if cache_age is not None and cache_age.days <= 2:
            filings = self._load_cache(ticker)
            logger.info(f"SEC EDGAR fallback to {cache_age.days}-day-old cache for {ticker}")
        else:
            logger.warning(
                f"SEC EDGAR API failed for {ticker} and cache stale ({cache_age}) — fail-open"
            )
            self._notify_telegram_once_per_day(
                "⚠️ SEC EDGAR API degraded — Phase 2 in fail-open mode for stale-cache tickers"
            )
            return False  # Fail-open: don't exclude
    # ... normal predikció logika
```

**Indoklás**: a kockázat-aszimmetria a cache fallback-re fordítva: ha az API rövid ideig (~pár óra) leesik, a 2 napi cache még jó (a quarterly cycle lassan változik). 2+ napi outage esetén a fail-open elfogadható, mert a 10 napi earnings exclusion (már aktív) elegendő alapvédelem, és a 12 concurrent cap + 2-3 daily new entry természetes módon korlátozza a kitettséget.

**Telegram alert egyszer per nap** (`state/sec_alert_last_sent.json`) megakadályozza a spam-et.

## Kapcsolódó

- `docs/decisions/2026-05-14-day63-decision-outcome.md` §3.10
- `docs/master-reference/04-risks-and-open-questions.md` §1.2
- `docs/tasks/2026-05-19-earnings-exclusion-7to10.md` (függőség)
- `docs/review/2026-05-04-daily-review.md` (AGNC -$380 case dokumentációja)
- SEC EDGAR API docs: https://www.sec.gov/edgar/sec-api-documentation
