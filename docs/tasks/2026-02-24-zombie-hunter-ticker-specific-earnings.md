# Task: Zombie Hunter — ticker-specifikus earnings endpoint

**Date:** 2026-02-24  
**Priority:** CRITICAL — ma este pipeline futás előtt kell pusholni  
**Scope:** `src/ifds/phases/phase2_universe.py` + `src/ifds/data/fmp.py`  
**Trigger:** ALC (Alcon) ma jelent (EARN = 02-24), mégis bekerült a mai pozíciólistába.
Az FMP bulk `/stable/earnings-calendar` endpoint nem tartalmazta — ugyanaz a bug mint tegnap KEP-nél.
A már implementált `get_next_earnings_date()` (ticker-specifikus `/stable/earnings?symbol=`) helyesen mutatta `02-24`-et a Telegram EARN oszlopban. Ezt kell a Zombie Hunter inputjaként használni.

---

## A probléma

A jelenlegi `_exclude_earnings()` függvény (`phase2_universe.py`) egy **bulk** FMP endpointot hív:

```python
earnings_data = fmp.get_earnings_calendar(
    from_date=today.isoformat(),
    to_date=to_date.isoformat(),
)
```

Ez a `/stable/earnings-calendar` endpoint **nem megbízható ADR-ekre és kisebb cap részvényekre** — ALC és KEP is kiesett belőle.

A `get_next_earnings_date(ticker)` metódus (`fmp.py`, tegnap implementálva) a `/stable/earnings?symbol=` endpointot használja, amely **ticker-specifikusan és megbízhatóan** adja vissza a következő earnings dátumot. Ezt kell a Zombie Hunter inputjaként használni.

---

## Megoldás

Az `_exclude_earnings()` logikáját **kettős ellenőrzésre** cseréljük:

1. **Megtartjuk** a bulk calendar lekérdezést — gyors, lefedi a ticker-ek nagy részét
2. **Hozzáadjuk** a ticker-specifikus ellenőrzést azon ticker-ekre, amelyek **nem estek ki** a bulk calendar alapján

Ez a megközelítés:
- Nem lassítja le a pipeline-t feleslegesen (csak a bulk által kihagyott ticker-ekre hív extra API-t)
- Megőrzi a backward compatibilityt
- Megoldja az ADR és kisebb részvény miss-eket

---

## Implementáció

### `src/ifds/phases/phase2_universe.py` — `_exclude_earnings()` csere

A teljes `_exclude_earnings()` függvényt cseréld le az alábbira:

```python
def _exclude_earnings(tickers: list[Ticker], fmp: FMPClient,
                      exclusion_days: int,
                      logger: EventLogger) -> tuple[list[Ticker], list[str]]:
    """Exclude tickers with earnings within the exclusion window.

    Two-pass approach:
    1. Bulk FMP earnings-calendar (fast, covers most tickers)
    2. Ticker-specific /stable/earnings?symbol= for any ticker that
       survived pass 1 (catches ADRs and others missed by bulk endpoint)

    Returns (filtered_tickers, excluded_symbols).
    """
    if not tickers:
        return tickers, []

    today = date.today()
    to_date = today + timedelta(days=exclusion_days)
    today_str = today.isoformat()
    to_date_str = to_date.isoformat()

    # --- Pass 1: Bulk calendar ---
    earnings_data = fmp.get_earnings_calendar(
        from_date=today_str,
        to_date=to_date_str,
    )

    ec_count = len(earnings_data) if earnings_data else 0
    logger.log(EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=2,
               message=f"Earnings calendar: {ec_count} entries ({today_str} to {to_date_str})",
               data={"earnings_entries": ec_count,
                     "from_date": today_str,
                     "to_date": to_date_str})

    # Build set of symbols caught by bulk
    bulk_earnings_symbols: set[str] = set()
    if earnings_data:
        for entry in earnings_data:
            symbol = entry.get("symbol")
            if symbol:
                bulk_earnings_symbols.add(symbol.upper())

    # Pass 1 filter
    filtered = []
    excluded = []
    for ticker in tickers:
        if ticker.symbol.upper() in bulk_earnings_symbols:
            excluded.append(ticker.symbol)
            logger.log(
                EventType.EARNINGS_EXCLUSION, Severity.DEBUG, phase=2,
                ticker=ticker.symbol,
                message=f"{ticker.symbol} excluded: earnings within {exclusion_days} days (bulk calendar)",
            )
        else:
            filtered.append(ticker)

    bulk_excluded_count = len(excluded)

    # --- Pass 2: Ticker-specific check for survivors ---
    # Uses /stable/earnings?symbol= — more reliable for ADRs and smaller caps
    pass2_filtered = []
    pass2_excluded = []

    for ticker in filtered:
        try:
            next_date = fmp.get_next_earnings_date(ticker.symbol)
            if next_date and today_str <= next_date <= to_date_str:
                pass2_excluded.append(ticker.symbol)
                excluded.append(ticker.symbol)
                logger.log(
                    EventType.EARNINGS_EXCLUSION, Severity.INFO, phase=2,
                    ticker=ticker.symbol,
                    message=(
                        f"{ticker.symbol} excluded: earnings within {exclusion_days} days "
                        f"(ticker-specific: {next_date}, missed by bulk calendar)"
                    ),
                )
            else:
                pass2_filtered.append(ticker)
        except Exception as e:
            # On error: fail-open (let ticker through), log warning
            logger.log(EventType.PHASE_DIAGNOSTIC, Severity.WARNING, phase=2,
                       ticker=ticker.symbol,
                       message=f"{ticker.symbol} earnings check error: {e} — passing through")
            pass2_filtered.append(ticker)

    logger.log(
        EventType.PHASE_DIAGNOSTIC, Severity.INFO, phase=2,
        message=(
            f"Earnings exclusion: {len(excluded)} total "
            f"(bulk={bulk_excluded_count}, ticker-specific={len(pass2_excluded)})"
        ),
        data={
            "total_excluded": len(excluded),
            "bulk_excluded": bulk_excluded_count,
            "ticker_specific_excluded": len(pass2_excluded),
            "ticker_specific_catches": pass2_excluded,
        },
    )

    return pass2_filtered, excluded
```

### `src/ifds/data/fmp.py` — `get_next_earnings_date()` — nincs változás

A tegnap implementált metódus változatlanul marad. A Phase 2 mostantól közvetlenül hívja.

---

## Teljesítmény

A Pass 2 az ~1400 universe tickerre fut ticker-specifikus API hívásokkal. Ez potenciálisan lassú lehet. Két opció:

**A) Szekvenciális (egyszerű, biztonságos):**
Az FMP rate limit ~300 req/perc, 1400 hívás ~5 perc lenne. **Nem elfogadható.**

**B) Async batch (helyes megoldás):**
Az async Phase 4 mintájára — de a Phase 2 jelenleg szinkron. Helyette: a `get_next_earnings_date()` hívásokat **thread pool**-lal párhuzamosítjuk, max 20 párhuzamos hívással.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def _check_ticker_earnings(args):
    ticker, fmp, today_str, to_date_str, exclusion_days = args
    try:
        next_date = fmp.get_next_earnings_date(ticker.symbol)
        if next_date and today_str <= next_date <= to_date_str:
            return ticker.symbol, True, next_date
        return ticker.symbol, False, next_date
    except Exception as e:
        return ticker.symbol, False, None  # fail-open
```

A `_exclude_earnings()` Pass 2 blokkjában:

```python
# --- Pass 2: Ticker-specific check (parallel) ---
pass2_excluded = []
pass2_filtered = []
max_workers = 20  # FMP rate limit safe

args_list = [(t, fmp, today_str, to_date_str, exclusion_days) for t in filtered]

with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = {executor.submit(_check_ticker_earnings, args): args[0] for args in args_list}
    for future in as_completed(futures):
        ticker_obj = futures[future]
        try:
            symbol, should_exclude, next_date = future.result()
        except Exception:
            pass2_filtered.append(ticker_obj)
            continue

        if should_exclude:
            pass2_excluded.append(symbol)
            excluded.append(symbol)
            logger.log(
                EventType.EARNINGS_EXCLUSION, Severity.INFO, phase=2,
                ticker=symbol,
                message=(
                    f"{symbol} excluded: earnings within {exclusion_days} days "
                    f"(ticker-specific: {next_date}, missed by bulk calendar)"
                ),
            )
        else:
            pass2_filtered.append(ticker_obj)
```

**Várható futási idő Pass 2:** 1400 ticker / 20 párhuzamos ≈ 70 batch × ~0.3s = ~20s extra overhead. Elfogadható (a teljes pipeline ~145s).

---

## Tesztelés

```python
# Manuális ellenőrzés: ALC és KEP ma kiestek volna-e?
import os, sys, datetime
sys.path.insert(0, "src")
from ifds.data.fmp import FMPClient

fmp = FMPClient(api_key=os.environ["IFDS_FMP_API_KEY"])
today = datetime.date.today().isoformat()
to_date = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()

for ticker in ["ALC", "KEP", "SKM", "GE", "LMT", "NVDA"]:
    d = fmp.get_next_earnings_date(ticker)
    in_window = d and today <= d <= to_date
    print(f"{ticker}: next={d}, in_window={in_window}")
```

Elvárt:
```
ALC:  next=2026-02-24, in_window=True   ← kizárva
KEP:  next=2026-03-10, in_window=False  ← átengedve (valóban március)
SKM:  next=2026-03-XX, in_window=False
GE:   next=2026-04-XX, in_window=False
LMT:  next=2026-04-XX, in_window=False
NVDA: next=2026-02-26, in_window=True   ← kizárva (bulk is elkapja)
```

**Unit tesztek** (`tests/test_phase2_earnings.py`):
- `test_bulk_only_catch`: ticker benne van bulk-ban → kizárva
- `test_ticker_specific_catch`: ticker nincs bulk-ban, de ticker-specific elkapja → kizárva
- `test_both_miss`: sem bulk, sem ticker-specific nem adja vissza → átengedve
- `test_ticker_specific_error_passthrough`: API hiba → fail-open, átengedve
- `test_log_summary_counts`: bulk_excluded és ticker_specific_excluded count helyes

---

## Git

```bash
git add src/ifds/phases/phase2_universe.py
git commit -m "fix: Zombie Hunter — ticker-specific earnings fallback (BC17)

Two-pass earnings exclusion in _exclude_earnings():
- Pass 1: bulk /stable/earnings-calendar (unchanged, fast)
- Pass 2: /stable/earnings?symbol= per-ticker for bulk survivors
  - ThreadPoolExecutor max_workers=20 for performance
  - fail-open on API error (ticker passes through with WARNING log)

Catches ADRs and smaller caps missed by bulk endpoint.
Root cause: ALC excluded 2026-02-24, KEP 2026-02-23 — both missed
by FMP bulk calendar, caught by ticker-specific endpoint.

Closes: #earnings-adr-miss"
git push
```

---

## Megjegyzések

- **Fail-open policy megtartva:** API hiba esetén a ticker átengedett, nem kizárt — konzisztens a korábbi bulk viselkedéssel
- **`get_next_earnings_date()` változatlan** — tegnapi implementáció újrafelhasználva
- **Bulk calendar megtartva** — a ~276 standard US ticker gyorsan kiesik, a Pass 2 csak a maradékra fut
- **BC18 scope:** hosszú távon a bulk calendar elhagyható ha a ticker-specific megbízhatóan lefed mindent — de ez külön validációt igényel
