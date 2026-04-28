# Daily Metrics — VIX Close Backfill from Phase 0 Diagnostics

**Status:** PROPOSED (W18 nice-to-have, ~30-45min CC)
**Created:** 2026-04-28
**Priority:** P3 — kis CC task, kozmetikai jellegű, de a daily review-k mérőszám-konzisztenciáját javítja
**Estimated effort:** ~30-45 min CC

**Depends on:**
- nincs

**NEM depends on:**
- M_contradiction multiplier (independent)
- MID Bundle Integration (independent)

---

## Kontextus

A `state/daily_metrics/2026-04-27.json` (és valószínűleg minden korábbi nap is) `market.vix_close: null`-t tartalmaz, miközben a **Phase 0 Diagnostics** és a **Telegram összefoglaló** mindketten **rögzítik a VIX záró értéket** napról napra.

A `scripts/paper_trading/daily_metrics.py` 197-199. sorai:

```python
# --- VIX (from Phase 0 log or snapshot) ---
# Not available directly — leave as None for now
vix_close = None
```

Tehát ez **NEM regresszió**, hanem a kezdetektől explicit `None` placeholder. A TODO komment elismeri, hogy a Phase 0 már rögzíti a VIX-et, csak a daily_metrics nem olvassa vissza.

## Mi a cél

A `daily_metrics.py` script **töltse fel** a `market.vix_close` mezőt minden nap, hogy:

1. A daily review-k konzisztens piaci kontextus táblázatot tudjanak építeni (VIX, SPY, MID regime egy helyen)
2. A walk-forward analízis és a heti/havi metrikák **historikus VIX-szériát** tudjanak hivatkozni
3. A `mid_vs_ifds_sector_comparison.py` (vasárnapi script) a VIX szintet, mint regime context indikátort, használhassa

## Adatforrás opciók

A VIX érték **több helyen** elérhető a pipeline futás után. Az implementálási sorrend prioritása **a megbízhatóság alapján**:

### Opció A — Phase 0 diagnostic event log (preferált)

A Phase 0 Diagnostics már rögzíti a VIX-et `EventLogger`-rel. A typical event ilyen formában:

```json
{
  "phase": 0,
  "event_type": "PHASE_DIAGNOSTIC",
  "severity": "INFO",
  "message": "VIX: 18.85 (delta -3.28%)",
  "data": {"vix_close": 18.85, "vix_delta_pct": -3.28}
}
```

**Hely:** `logs/cron_intraday_YYYYMMDD_*.log` (vagy hasonló) JSON-formátumban

**Implementáció:**
```python
def _load_phase0_vix(target_date: str) -> tuple[float | None, float | None]:
    """Parse VIX close + delta from Phase 0 diagnostic log for target date."""
    date_str = target_date.replace("-", "")
    # Find latest cron log for this date
    pattern = str(PROJECT_ROOT / "logs" / f"cron_intraday_{date_str}_*.log")
    files = sorted(glob.glob(pattern))
    if not files:
        return None, None

    # Parse JSON events from latest log; find phase=0 events with vix_close in data
    with open(files[-1]) as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                if (event.get("phase") == 0 and
                    isinstance(event.get("data"), dict) and
                    "vix_close" in event["data"]):
                    return event["data"].get("vix_close"), event["data"].get("vix_delta_pct")
            except (json.JSONDecodeError, KeyError):
                continue
    return None, None
```

### Opció B — Polygon API direct fetch (fallback)

Ha a Phase 0 log parsolás nem megy (pl. event format változás), egyszerű Polygon hívás:

```python
def _fetch_vix_close(target_date: str) -> float | None:
    """Fetch VIX close from Polygon (mirrors _fetch_spy_return pattern)."""
    api_key = os.environ.get("IFDS_POLYGON_API_KEY")
    if not api_key:
        return None
    try:
        client = PolygonClient(api_key)
        bars = client.get_aggregates("I:VIX", target_date, target_date, timespan="day")
        return bars[0].get("c") if bars else None
    except Exception as e:
        logger.warning(f"VIX fetch failed: {e}")
        return None
```

**Megjegyzés:** A Polygon ticker `I:VIX` — index szimbólum. CC ellenőrizze, hogy a `PolygonClient` támogatja-e az `I:` prefixet, vagy más szintaxist kell. Ha nem, akkor `^VIX` vagy hasonló.

### Opció C — Phase 0 snapshot fájl (ha létezik)

Ha létezik egy `state/phase0_snapshots/YYYY-MM-DD.json` jellegű fájl, ami a diagnostics outputjának strukturált változatát tartalmazza, az a legegyszerűbb forrás. **CC ellenőrizze**, létezik-e ilyen fájl. Ha nem, ne hozzon létre — a A) opció elegendő.

## Scope — 3 pont

### 1. Implementáció

**Fájl:** `scripts/paper_trading/daily_metrics.py`

A 197-199. soron lévő placeholder helyett:

```python
# --- VIX close (from Phase 0 log) ---
vix_close, vix_delta_pct = _load_phase0_vix(target_date)
if vix_close is None:
    # Fallback: direct Polygon API
    vix_close = _fetch_vix_close(target_date)
    vix_delta_pct = None  # Csak a Phase 0 log tartalmazza a delta-t
```

A `market` szekció bővítése:

```python
"market": {
    "spy_return_pct": round(spy_return, 2) if spy_return is not None else None,
    "vix_close": round(vix_close, 2) if vix_close is not None else None,
    "vix_delta_pct": round(vix_delta_pct, 2) if vix_delta_pct is not None else None,  # új
    "strategy": "LONG",
},
```

### 2. Tesztek

**Fájl:** `tests/test_daily_metrics_vix.py` (új) vagy a meglévő `tests/test_daily_metrics.py` bővítése

**3-4 új teszt:**

```python
def test_load_phase0_vix_from_log():
    """Parses VIX from a sample Phase 0 log line."""

def test_load_phase0_vix_returns_none_if_no_log():
    """Returns (None, None) if log file missing."""

def test_load_phase0_vix_handles_malformed_lines():
    """Skips JSON decode errors in log gracefully."""

def test_fetch_vix_close_from_polygon():
    """Uses mocked PolygonClient to verify the fallback."""

def test_vix_close_in_metrics_output():
    """Integration: build_daily_metrics returns vix_close populated."""
```

### 3. Backfill (opcionális, ha Tamás kéri)

Ha érdekes lenne a historikus napokra VIX-et utólag betölteni:

```bash
# A meglévő --date paraméter már támogatja
for d in $(ls state/daily_metrics/*.json | xargs -n1 basename | sed 's/.json//'); do
    python scripts/paper_trading/daily_metrics.py --date "$d"
done
```

**Megjegyzés:** A backfill **felülírja** a meglévő daily_metrics fájlokat. Ezért ezt csak **manuálisan** futtatja Tamás, ha akarja, **NEM része a CC commit-nak**.

## Success criteria

1. **Tesztek:** 3-4 új teszt + a teljes test suite zöld marad
2. **Live verification:** kedd este (ápr 28) a daily_metrics futás után:
```bash
jq '.market.vix_close, .market.vix_delta_pct' state/daily_metrics/2026-04-28.json
```
**Várt:** valós VIX szám (pl. `18.85` és `-3.28`), nem `null`

## Risk

**Alacsony.** Indoklás:

1. **Read-only operáció** — csak a daily_metrics output bővül, semmilyen pipeline döntés nem változik
2. **Graceful failure** — ha a Phase 0 log parsolás nem megy, a Polygon fallback ad esélyt; ha az se megy, akkor `null` (jelenlegi viselkedés, nincs regresszió)
3. **Nem új API hívás per se** — a Polygon kliens már használt az SPY-ra, csak egy újabb ticker

## Out of scope (explicit)

- **Phase 0 log format módosítás** — ha a log nem tartalmazza a strukturált data-t, az **külön CC task** (Phase 0 diagnostics enrichment, P3+)
- **VIX trend / historical analysis** — csak a daily close kell, nem heti/havi metrika
- **Backfill commit** — Tamás manuálisan, ha akarja
- **Alternative VIX sources** (CBOE direct, FRED) — Polygon fallback elég

## Implementation order (CC számára)

1. **Olvasás / megerősítés** (5 min)
   - Egy minta Phase 0 log file struktúra ellenőrzése: van-e benne `phase=0` event JSON-formátumban `vix_close` mezővel?
   - Ha nincs JSON struktúrált event, csak prose log üzenet (pl. "VIX: 18.85"), akkor regex parser kell — egyszerűbb
2. **`_load_phase0_vix()` függvény** (10 min)
3. **`_fetch_vix_close()` Polygon fallback** (5 min) — szinte másolat az `_fetch_spy_return`-ből
4. **`build_daily_metrics` integráció** (5 min)
5. **Tesztek** (15 min) — fixture-szel mock log file-ok
6. **Smoke test** (5 min) — kedd este `python scripts/paper_trading/daily_metrics.py --date 2026-04-28`
7. **Commit + push** (5 min)

**Összesen:** ~30-45 min.

## Commit message draft

```
feat(daily_metrics): populate vix_close from Phase 0 log + Polygon fallback

The daily_metrics.py script previously left market.vix_close as None
with a TODO comment. The Phase 0 Diagnostics already records VIX close
+ delta in its event log (e.g. logs/cron_intraday_*.log), and Polygon
provides VIX as a backup data source.

This commit:
  - Adds _load_phase0_vix() to parse VIX from Phase 0 log events
  - Adds _fetch_vix_close() as Polygon fallback (similar to existing
    _fetch_spy_return pattern)
  - Populates market.vix_close and market.vix_delta_pct in output JSON

Verified manually: 2026-04-28 daily_metrics shows vix_close=<actual>
instead of null.

Tests:
  - test_load_phase0_vix_from_log
  - test_load_phase0_vix_returns_none_if_no_log
  - test_load_phase0_vix_handles_malformed_lines
  - test_fetch_vix_close_from_polygon
  - test_vix_close_in_metrics_output
```

## Kapcsolódó

- Forrás daily_metrics fájl: `state/daily_metrics/2026-04-27.json` (vix_close: null)
- A javítandó kód: `scripts/paper_trading/daily_metrics.py:197-199`
- Reference Polygon minta: `scripts/paper_trading/daily_metrics.py::_fetch_spy_return`
- Phase 0 log példa: `logs/cron_intraday_20260427_*.log`

## Implementáció időzítése

- **CC bármikor a héten** (alacsony prioritás, de ha kedd-szerda közi szabadidő van, könnyű kis task)
- **Nem blokkolja** a M_contradiction implementációt (szerda) — ez után, csütörtök reggel is végezhető
- **Vasárnapi MID comparison-höz** előny, ha addigra él — a VIX szint értékes regime context indikátor

## Megjegyzés

Ez egy **adat-konzisztencia javítás**, nem új feature. A Telegram összefoglaló már kiírja a VIX-et naponta, csak a strukturált JSON output nem. Ha CC-nek szabadideje van, ez **30 perc, low-risk, immediate value**.
