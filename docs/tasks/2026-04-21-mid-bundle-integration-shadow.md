# MID Bundle Integration — Shadow Mode + Offline Sector Comparison

**Status:** PROPOSED (W18 scope, implementation after W17 weekly metrics)  
**Created:** 2026-04-21  
**Priority:** P2 — nem blokkoló, de megalapozza a BC25 döntést  
**Estimated effort:** ~4-5h CC  
**Depends on:**
- W17 heti metrika kiértékelés (péntek ápr 24) — BC23 GO/NO-GO
- MID bundle API éles (már készen, `https://mid.ssh.services/api/bundle/latest`)

**NEM depends on:**
- BC22 HRP (parkolt)
- BC24 Institutional Flow (független munkafolyam)

---

## Kontextus

A MID ma (2026-04-21) release-elt egy új API-t:

```python
bundle = httpx.get(
    "https://mid.ssh.services/api/bundle/latest",
    headers={"X-API-Key": API_KEY}
).json()
```

A válasz 5 részből áll:
- `bundle.flat` — 17 headline mező (regime, TPI, RPI, ESI, VIX, SPY, stb.)
- `bundle.engines.tpi` — TPI state detaillal
- `bundle.narratives` — LLM-generált makro narratívák
- `bundle.questions` — Question Board (napi fő kérdés)
- **`bundle.etf_xray.sectors`** — 40 szektor + institutional consensus ← **ez a kulcs**

A 2026-04-20 tapasztalat (XLB IFDS VETO-zva, de MID szerint #1 momentum leader) felvetette a kérdést: **jobb-e a MID CAS-alapú sector rotation, mint az IFDS saját Phase 3 momentum számítás?**

**Még nem tudjuk.** Ezért ez a task **NEM** váltja le a Phase 3-at. Shadow mode-ban gyűjt adatot, és **offline** méri, hogy a MID vagy az IFDS lett volna jobb.

## A task NEM része — tisztázás

- **NINCS** Phase 3 refactor a scoring/VETO logikában. A sector rotation marad pontosan úgy, ahogy ma van
- **NINCS** `bundle.narratives` Telegram integráció (külön feature, ha kell majd, külön task)
- **NINCS** regime-aware scoring (BC25+ scope, a MID bundle ezt lehetővé teszi, de **későbbi munka**)
- **NINCS** BC24 érintés — a BC24 (dollar-weighted flow scoring) továbbra is W19-W22 scope

**A célja ennek a task-nak egyetlen dolog:** adatot gyűjteni ahhoz, hogy a W19 elején tudjunk **adatvezérelt döntést** hozni a BC25-ről.

## Scope — 4 pont

### 1. MIDClient implementáció

**Fájl:** `src/ifds/data/mid_client.py` (új)

```python
"""MID API client — consumes /api/bundle/latest.

This client is currently used only for shadow-mode data collection. It does
NOT affect the IFDS Phase 3 sector rotation or scoring pipeline.

Rate limit policy: cache the bundle for 5 minutes; MID data refreshes daily,
so one call per pipeline run is sufficient.
"""

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MIDClient:
    """HTTP client for MID (Macro Intelligence Dashboard) bundle API."""
    
    BASE_URL = "https://mid.ssh.services/api"
    CACHE_TTL_SECONDS = 300  # 5 minutes
    
    def __init__(self, api_key: str, timeout: int = 10):
        self._api_key = api_key
        self._timeout = timeout
        self._cache: dict[str, Any] | None = None
        self._cache_ts: float | None = None
    
    def get_bundle(self, force_refresh: bool = False) -> dict[str, Any]:
        """Fetch full MID bundle snapshot.
        
        Args:
            force_refresh: bypass cache
            
        Returns:
            Full bundle dict, or empty dict {} on failure (non-fatal).
        """
        # Cache hit
        if not force_refresh and self._cache and self._cache_ts:
            if time.time() - self._cache_ts < self.CACHE_TTL_SECONDS:
                return self._cache
        
        try:
            response = httpx.get(
                f"{self.BASE_URL}/bundle/latest",
                headers={"X-API-Key": self._api_key},
                timeout=self._timeout,
            )
            response.raise_for_status()
            bundle = response.json()
            self._cache = bundle
            self._cache_ts = time.time()
            return bundle
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.warning(f"MID API unavailable: {e}. Returning empty bundle.")
            return {}
    
    def get_sectors(self) -> list[dict]:
        """Return sector CAS list from bundle.etf_xray.sectors.
        
        Returns:
            List of sector dicts, or [] on failure.
        """
        bundle = self.get_bundle()
        return bundle.get("etf_xray", {}).get("sectors", [])
    
    def get_regime(self) -> dict[str, Any]:
        """Return current regime + TPI state from bundle.flat + bundle.engines.tpi."""
        bundle = self.get_bundle()
        flat = bundle.get("flat", {})
        tpi = bundle.get("engines", {}).get("tpi", {})
        return {
            "regime": flat.get("regime"),
            "tpi_score": flat.get("tpi"),
            "tpi_state": tpi.get("state"),
            "growth": flat.get("growth"),
            "inflation": flat.get("inflation"),
            "policy": flat.get("policy"),
            "rpi": flat.get("rpi"),
            "esi": flat.get("esi"),
        }
```

**Környezeti változó:** `MID_API_KEY` a `.env` fájlban (Tamás állítja be manuálisan a Mac Mini-n).

**Tesztek (~3):**
- `test_mid_client_cache` — kétszer hívva csak egy HTTP call
- `test_mid_client_fallback_on_error` — hálózati hiba esetén üres dict, nem crashel
- `test_mid_client_get_sectors` — bundle.etf_xray.sectors kivonás OK

### 2. Napi bundle snapshot storage

**Fájl:** `src/ifds/data/mid_bundle_snapshot.py` (új)

A napi pipeline futás (16:15 CEST) elején vagy **után** hívjuk a MIDClient-et, és a teljes bundle-t elmentjük:

```python
"""Store daily MID bundle snapshots for offline analysis.

Path: state/mid_bundles/YYYY-MM-DD.json.gz
Same gzipped pattern as state/phase4_snapshots/.
"""

import gzip
import json
from datetime import date
from pathlib import Path

from ifds.data.mid_client import MIDClient

SNAPSHOT_DIR = Path("state/mid_bundles")


def save_bundle_snapshot(
    bundle: dict,
    target_date: date | None = None,
) -> Path | None:
    """Save bundle JSON gzipped to state/mid_bundles/YYYY-MM-DD.json.gz.
    
    Returns path on success, None on failure (non-fatal).
    """
    if not bundle:
        return None
    
    target = target_date or date.today()
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / f"{target.isoformat()}.json.gz"
    
    try:
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False)
        return path
    except (OSError, IOError):
        return None


def load_bundle_snapshot(target_date: date) -> dict | None:
    """Load a saved bundle snapshot."""
    path = SNAPSHOT_DIR / f"{target_date.isoformat()}.json.gz"
    if not path.exists():
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, IOError, json.JSONDecodeError):
        return None
```

**Integráció a pipeline-ba:**

A legcélszerűbb a `Phase 0: Diagnostics` **után**, a Phase 1 **előtt** hívni. A Phase 0 már hív macro adatokat (FRED, VIX), így a MID hívás természetesen illik ide.

**Fájl:** `src/ifds/phases/phase0_diagnostics.py` — egy új lépés a végén:

```python
# Phase 0 végén, a macro regime return előtt:
try:
    from ifds.data.mid_client import MIDClient
    from ifds.data.mid_bundle_snapshot import save_bundle_snapshot
    import os
    
    mid_key = os.environ.get("MID_API_KEY")
    if mid_key:
        mid_client = MIDClient(api_key=mid_key)
        bundle = mid_client.get_bundle()
        if bundle:
            saved_path = save_bundle_snapshot(bundle)
            if saved_path:
                logger.info(f"MID bundle saved: {saved_path}")
except Exception as e:
    logger.warning(f"MID bundle snapshot failed (non-fatal): {e}")
```

**Kritikus:** a try-except külső. Ha a MID nem elérhető, a Phase 0 **folytatódik**, a pipeline **nem blokkolódik**. A bundle snapshot **bonus adat**, nem követelmény.

**Tesztek (~3):**
- `test_save_bundle_snapshot` — mock bundle → fájl létrejön
- `test_load_bundle_snapshot` — save majd load, az eredeti dict visszajön
- `test_phase0_mid_graceful_failure` — MIDClient hibáját lenyel, Phase 0 nem crashel

### 3. Offline összehasonlító script

**Fájl:** `scripts/analysis/mid_vs_ifds_sector_comparison.py` (új)

Ez a script a **hétvégén / péntek esténként** fut, és egy markdown riportot generál a `docs/analysis/` alá.

```python
"""MID vs IFDS Sector Rotation — Offline Comparison.

Compare the sector decisions of:
- IFDS Phase 3 (from cron_YYYYMMDD.log parsed sector rotation output)
- MID CAS (from state/mid_bundles/YYYY-MM-DD.json.gz)

For each day:
1. Which sectors did IFDS VETO?
2. Which sectors did MID mark OVERWEIGHT / UNDERWEIGHT?
3. What was the forward 5-day return of each sector?
4. Who was "correct" — did IFDS's veto save money, or miss alpha?

Output: docs/analysis/mid-vs-ifds-sectors-YYYY-MM-DD.md
"""
```

**Amit a script csinál:**

1. Betöltött az összes MID bundle snapshot-ot (`state/mid_bundles/*.json.gz`)
2. Az IFDS Phase 3 kimenetet parsolja a cron logokból (a sector momentum táblát, a VETO listát)
3. Az 11 sector ETF historikus árait lekéri Polygon-ról (már van adapter)
4. Számít minden szektorra és minden napra:
   - IFDS decision (Leader / Neutral / Laggard / VETO)
   - MID CAS state (OVERWEIGHT / ACCUMULATING / NEUTRAL / DECREASING / UNDERWEIGHT / INSUFFICIENT)
   - Forward 5-day return (vs SPY)
5. Agreement matrix: hány napon hány szektoron egyeztek, hány napon nem
6. Performance: az egyet nem értő napokon melyik rendszer jobb prognózissal bírt

**Output markdown tartalma:**

```markdown
# MID vs IFDS Sector Comparison — 2026-04-27

Data window: 2026-04-21 to 2026-04-27 (5 trading days)

## Summary

- Total sector-day decisions: 55 (11 sectors × 5 days)
- IFDS = MID agreement: 38 (69%)
- Disagreements: 17 (31%)
- In disagreements:
  - IFDS correct (ex-post): 7 (41%)
  - MID correct (ex-post): 10 (59%)

## Notable disagreements

| Date | Sector | IFDS | MID | Forward 5d Return | Who won |
|------|--------|------|-----|-------------------|---------|
| 04-20 | XLB | VETO | OVERWEIGHT | +3.2% vs SPY | MID |
| 04-21 | XLE | VETO | OVERWEIGHT | +1.8% vs SPY | MID |
| ...

## Regime-context breakdown

- STAGFLATION (5 days): MID advantage +2.1% avg
- GOLDILOCKS (0 days): N/A

## Recommendation
...
```

**Tesztek:** nincs külön unit test. A script **manuálisan fut**, Tamás vagy Chat hívja a hétvégén. Smoke test: `python scripts/analysis/mid_vs_ifds_sector_comparison.py --days 5`.

### 4. STATUS.md + backlog frissítés CC által

CC, amikor a task-ot lezárja, írja be a STATUS.md "Élesben futó feature-ök" szekcióba:

```
- **MID Bundle Snapshot (shadow mode)**: napi MID bundle mentés a state/mid_bundles/-be. Phase 3 NINCS érintve, csak adatgyűjtés.
```

És a backlog.md "Folyamatban lévő" szekcióba:

```
### W18 MID Shadow Mode (2026-04-27 — 2026-05-01)
- MIDClient + bundle snapshot storage ✅ deployed
- Offline sector comparison script ✅ ready
- Adatgyűjtés fut, W19 elején értékelés → BC25 GO/NO-GO
```

## Mi NEM része a task-nak (fontos)

**A következő dolgok később jönnek, NE implementáld most:**

### Ezek későbbi task-ok, nem ennek a része:
- **BC25 — Phase 3 MID CAS váltás** — csak W19 adatvezérelt döntés után
- **Bundle.narratives → Telegram integráció** — külön feature
- **Bundle.questions dashboard** — külön feature  
- **Regime-aware scoring** (STAGFLATION-ben fundamental weight↑) — BC25+ scope, a backlog-ideas.md-ben van
- **Historikus bundle lekérdezés** — a MID projekt oldalán van, itt nem foglalkozunk vele

## Tesztek összesen

- 3 új unit test a MIDClient-re
- 3 új unit test a bundle_snapshot-ra
- 2 új integration test (Phase 0 graceful failure + MID API mock)
- **Összesen: ~8 új teszt**

A meglévő 1352 tesztnek **változatlanul kell futnia** — a Phase 0 bővülése **opcionális** lépés (ha MID_API_KEY nincs beállítva, átugorja).

## Commit terv

**Egyetlen commit:**

```
feat(mid): integrate MID bundle API in shadow mode

Adds MIDClient that consumes /api/bundle/latest for macro regime,
sector CAS states, and institutional consensus data.

Bundle is fetched once per pipeline run (cached 5min) and saved to
state/mid_bundles/YYYY-MM-DD.json.gz for offline analysis.

Integration point: Phase 0 Diagnostics, after macro regime computation.
Failure mode: non-fatal — if MID API is unavailable, pipeline proceeds
normally without MID data.

Shadow mode only — Phase 3 sector rotation, scoring, and VETO logic
are UNCHANGED. The offline comparison script
(scripts/analysis/mid_vs_ifds_sector_comparison.py) generates a weekly
report comparing IFDS vs MID sector decisions against forward returns.

The goal is to gather 5-10 days of parallel data to inform a W19
decision: should we refactor Phase 3 to consume MID CAS (BC25), or
keep the current local momentum calculation?

Tests: 8 new, all 1352+ existing tests unchanged.

Depends on:
- MID bundle API live (released 2026-04-21)
- MID_API_KEY environment variable on Mac Mini

Not affected:
- Phase 3-6 scoring/sizing logic
- BC23 paper trading evaluation (shadow data only)
- BC24 Institutional Flow (separate, independent work stream)
```

## Rollback terv

Minden változás **additive**:
- Új fájlok: `mid_client.py`, `mid_bundle_snapshot.py`, comparison script
- Módosított fájl: `phase0_diagnostics.py` — egy new try-except blokk a végén

**Rollback módok:**
- **Soft:** `MID_API_KEY` unset a `.env`-ben → a try-except átugorja, Phase 0 változatlanul fut
- **Hard:** `git revert` a commit-on — minden változtatás eltűnik

**Kockázat:** alacsony. A Phase 0 hibabiztos, a snapshot storage külön mappába ír, nincs side-effect a többi fázisra.

## Sikerkritériumok (1-2 hét live után)

| Metrika | Elvárás |
|---------|---------|
| MID bundle sikeresen lekérdezve | 5/5 napon |
| MID bundle snapshot mentve | state/mid_bundles/ 5 napi gzip fájl |
| Phase 0 crash MID hiba miatt | 0 |
| Comparison script futtat | manuálisan hétvégén |
| Agreement rate (IFDS vs MID sector decision) | referencia érték megszületik |

## W19 döntés — mi következik (nem ennek a task-nak a része)

**Ha az 5-napos offline összehasonlítás azt mondja:**

**Opció A — MID konzekvensen jobb (~15% vagy több alpha eltérés):**  
→ Új, kisebb task (BC25 Phase 1): a Phase 3 sector rotation átváltása MID CAS-re. Effort: ~3-4h CC (a MIDClient már van).  
→ BC24 (dollar-weighted flow) marad a tervezett W19-W22 scope-ban, párhuzamosan halad.

**Opció B — MID és IFDS nagyjából egyenlő (±5%):**  
→ Nincs refactor. A MIDClient marad szolgáltatásként (hasznos a `regime_state` lekérdezéshez a backlog-ideas "Regime-Aware Position Sizing"-hoz).  
→ BC25 átütemezve, esetleg a BC24 után.

**Opció C — IFDS jobb:**  
→ Nincs refactor. A MIDClient maradhat adatszintézisre / Telegram enrichment-re, de a scoring-ra nem.

Mindhárom opció **adat-vezérelt**, nem spekulatív.

## Kapcsolódó dokumentumok

- `docs/tasks/future-2026-04-17-bc-ifds-phase3-from-mid.md` — az eredeti BC25 terv, most ez a task a Phase 1
- `docs/planning/backlog-ideas.md` — "Regime-Aware Position Sizing" szekció
- `docs/planning/operational-playbook.md` — hétvégi MID vs IFDS elemzés rutin
- `/mid/docs/planning/BC-etf-xray-institutional-13f-layer.md` — a MID oldali BC
- `docs/STATUS.md` — W17 2 napos kontraszt (hétfő -$433, kedd +$553)
