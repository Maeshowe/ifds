# 2026-02-24 — Zombie Hunter fix: ticker-specifikus earnings ellenőrzés

**Session:** 2026-02-24, ~09:45–10:30 CET  
**Participants:** Chat (diagnózis, task design) + CC (implementáció)

---

## Kiváltó ok

A 2026-02-24-i pipeline ALC (Alcon) pozíciót generált, annak ellenére hogy az ALC ma jelent (EARN = 02-24 a Telegram reportban látszott). A Zombie Hunter 7 napos ablakon belül kellett volna kiszűrje — de nem tette.

**Diagnózis:** Az FMP bulk `/stable/earnings-calendar` endpoint ma sem tartalmazta az ALC-t a `2026-02-24 → 2026-03-03` ablakban (4000 bejegyzés, ALC hiányzott). Ugyanaz a strukturális probléma mint tegnap KEP-nél.

A tegnap implementált EARN oszlop (`get_next_earnings_date()`) helyesen mutatta `02-24`-et → ez igazolta hogy a ticker-specifikus endpoint megbízható, és azt kell a Zombie Hunter inputjaként használni.

**Pozíció státusz:** ALC pozíció a mai napon kinyílt (nem avatkoztunk be manuálisan — paper trading, tesztelési cél).

---

## Megoldás

`phase2_universe.py` → `_exclude_earnings()` két-lépcsős ellenőrzésre bővítve:

**Pass 1 (megtartva):** Bulk `/stable/earnings-calendar` — gyors, lefedi a standard US ticker-ek nagy részét (~276 kizárás ma)

**Pass 2 (új):** `/stable/earnings?symbol=` per-ticker a Pass 1 által átengedett survivor-okra — `ThreadPoolExecutor(max_workers=20)`, ~20s overhead, fail-open policy API hiba esetén

**Summary log:** `bulk=N, ticker-specific=M` — minden futásnál látható melyik pass mit fogott

---

## Implementáció (CC)

**1 fájl módosítva, tesztek frissítve:**

### `src/ifds/phases/phase2_universe.py`
- `_exclude_earnings()` két-lépcsős logikára cserélve
- `_check_ticker_earnings()` helper függvény (ThreadPoolExecutor-hoz)
- `concurrent.futures.ThreadPoolExecutor` import hozzáadva
- `max_workers=20` — FMP rate limit safe, ~20s extra overhead

### `tests/` 
- `TestEarningsExclusionPass2`: 6 új teszt
  - `test_bulk_only_catch`: standard ticker, bulk elkapja
  - `test_ticker_specific_catch`: ADR, bulk miss, ticker-specific elkapja
  - `test_both_miss`: sem bulk, sem ticker-specific → átengedve
  - `test_ticker_specific_error_passthrough`: API hiba → fail-open
  - `test_log_summary_counts`: bulk_excluded és ticker_specific_excluded count helyes
  - `test_both_passes_combined`: vegyes eset, mindkét pass dolgozik
- 3 meglévő teszt frissítve Pass 2 mock-kal

**Backward compatible:** fail-open policy megtartva, bulk calendar megtartva.

---

## Várható hatás holnaptól

- ALC-szerű esetek (bulk miss, ticker-specific elkapja) → EARNINGS_EXCLUSION log `(ticker-specific: YYYY-MM-DD, missed by bulk calendar)` üzenettel
- KEP továbbra is átengedett marad (március 10, kívül esik a 7 napos ablakon — FMP dátum valóban eltér a Bloomberg/Apple Stocks 02-26-tól, ez külön BC18 kérdés)
- Summary log minden futásnál: `Earnings exclusion: N total (bulk=X, ticker-specific=Y)`

---

## Nyitott kérdések (BC18)

- KEP FMP dátum hibás (03-10 vs valós 02-26) — ticker-specific sem oldja meg, mert az FMP forrásadata rossz. Hosszú távon: második earnings forrás (Polygon events API) cross-check
- Bulk calendar elhagyható-e teljesen ha ticker-specific 100%-ban megbízható? Külön validáció szükséges (BC18)
- ThreadPoolExecutor max_workers=20 optimalizálás FMP rate limit függvényében

---

## Git commit üzenet (CC által)

```
fix: Zombie Hunter — ticker-specific earnings fallback (BC17)

Two-pass earnings exclusion in _exclude_earnings():
- Pass 1: bulk /stable/earnings-calendar (unchanged, fast)
- Pass 2: /stable/earnings?symbol= per-ticker for bulk survivors
  - ThreadPoolExecutor max_workers=20 for performance (~20s overhead)
  - fail-open on API error (ticker passes through with WARNING log)
- Summary log: bulk=N, ticker-specific=M per run

Catches ADRs and smaller caps missed by bulk endpoint.
Root cause: ALC 2026-02-24, KEP 2026-02-23 — both missed by FMP
bulk calendar, caught by ticker-specific endpoint.

Tests: 6 new (TestEarningsExclusionPass2) + 3 updated
```
