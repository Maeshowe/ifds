# Task: Snapshot Regresszió Diagnózis + Fix

**Status:** DONE
**Priority:** P1 — production data pipeline blocker
**Created:** 2026-05-08
**Updated:** 2026-05-08
**Owner:** Claude Code

**ROOT CAUSE (2026-05-08 diagnosztika):** `tests/test_pipeline_e2e.py::test_full_pipeline_flow` futtatja a valós `run_pipeline`-t mockolt phase result-okkal. A runner a Phase 4 mock után meghívja a **valódi** `save_phase4_snapshot()`-ot a default `state/phase4_snapshots/` útvonalra, **production fájlokat felülírva**. A `_mock_phase4()` `combined_score=78.0` AAPL-t ad vissza — pontosan ezt mutatták a regressziós snapshotok. A `deploy_daily.sh` 22:00 cron pre-flight pytest-je naponta megsemmisítette a 16:15 cron 93-ticker-es snapshotját.

**FIX (commit pending):** `@patch("ifds.data.phase4_snapshot.save_phase4_snapshot", return_value=None)` decorator a `test_full_pipeline_flow`-ra + új `TestSnapshotIsolation::test_save_snapshot_is_mocked_in_e2e` regressziós teszt, ami biztosítja hogy a mock hívva van.

**Hipotézis:** **NEM A/B/C** — egyik sem volt. A Phase 1-3 context, a passed lista és a serializáció mind rendben voltak. A bug egy **teszt-sanitációs hiba**: a teszt környezet az élesi state mappába írt.

---

## Kontextus — a 2026-05-08 dark pool debug felfedezte

A `flow-decomposition.md` (232 trade, ápr 13-i scope) auditja közben felfedezve:

```
2026-02-23 → 575 tickers (46 KB)
2026-03-04 → 554 tickers (45 KB)
2026-04-01 → 470 tickers (38 KB)
2026-04-10 → 1 ticker  (0.4 KB)  ← REGRESSZIÓ kezdete
2026-04-13 → 1 ticker  (0.4 KB)
...
2026-05-07 → 1 ticker  (0.5 KB)
```

**Minden ápr 10. utáni Phase 4 snapshot CSAK az AAPL-t tartalmazza.** A flow-decomposition korábbi audit-ja ezért a **régi (Feb-Apr 1) mintán futott** — minden BC23 utáni adat snapshot-szempontból **hasznavehetetlen**.

**Implikációk a teljes BC23 utáni időszakra:**
- A scoring rekalibráció (BC23, 2026-04-13) hatása **objektíven NEM mérhető** a 232-trade alapú flow-decomposition mintán
- A Day 63 / Day 90 értékelés **nem támaszkodhat** snapshot alapú elemzésekre az ápr 10. utáni időszakra
- A weekly_metrics.py kimenetek (W17-W18-W19) **részlegesen invalidak**, ahol snapshot-alapú számítás történt

## Diagnosztikai protokoll

### 1. lépés — A 16:15 Phase 4-6 cron log átolvasása

```bash
cd ~/SSH-Services/ifds
ls -la logs/cron_intraday_2026-05-0[1-7]*.log

# Kiválasztani egy friss log-ot, és átolvasni:
# - Phase 1-3 context betöltése sikeres-e? (`state/phase13_ctx.json.gz`)
# - Hány ticker került a Phase 4-be?
# - A `phase4.passed` lista hány tickert tartalmaz?
```

**Várt finding**: vagy a Phase 1-3 context **nem töltődik be** (üres lista), vagy a `passed` lista **csak az AAPL-t** tartalmazza.

### 2. lépés — A Phase 1-3 context fájl ellenőrzése

```bash
ls -la state/phase13_ctx.json.gz

# Friss-e?
stat -f '%Sm' state/phase13_ctx.json.gz

# Hány tickert tartalmaz?
zcat state/phase13_ctx.json.gz | python -m json.tool | grep -c '"ticker"'

# Az universe lista ellenőrzése:
zcat state/phase13_ctx.json.gz | python -c "
import json, sys
ctx = json.load(sys.stdin)
print(f'Universe size: {len(ctx.get(\"universe\", []))}')
print(f'First 10: {ctx.get(\"universe\", [])[:10]}')
"
```

**Várt finding**: ha az universe lista **rendben van** (~250-300 ticker), akkor a bug a Phase 4 oldalon. Ha az universe **csak AAPL** vagy üres, akkor a bug a Phase 1-3 → Phase 4 átadásában.

### 3. lépés — A Phase 4 passed list logika átolvasása

```bash
grep -rn 'passed\|phase4.passed' src/ifds/phases/phase4_stocks.py | head -20

# Megnézni, hogyan szűr a Phase 4 a Phase 1-3 contextből
# Megnézni, hogy van-e egy "AAPL probe" debug logika valahol
```

**Várt finding**: vagy egy szűrési feltétel (combined_score >= 85, RVOL > X, stb.) **eltávolítja** a tickerek többségét, vagy **egy debug/probe kód** maradt benn (AAPL-only mock).

### 4. lépés — Git blame a regresszió időpontjára

```bash
# A pipeline-split commit (c90e634, ápr 3) és a BC23 deploy (0b905e6, ápr 13) között
git log --oneline --since='2026-04-03' --until='2026-04-13' -- src/ifds/phases/

# A Phase 4 changes-jeit megnézni
git log --oneline --since='2026-04-01' -- src/ifds/phases/phase4_stocks.py
```

**Várt finding**: egy konkrét commit, amely az AAPL-only viselkedést bevezette.

## A 3 lehetséges root cause

### Hipotézis A: Phase 1-3 context nem töltődik be

**Tünet**: a 16:15 cron-ban a `state/phase13_ctx.json.gz` nem olvasható, vagy üres listát ad vissza.

**Megoldás**: a `deploy_intraday.sh` script ellenőrzi a context fájl létezését és fríss-ességét. Ha hibás, hibajelzéssel megáll.

**Effort**: ~30-45 min (script módosítás + 2-3 unit teszt)

### Hipotézis B: Phase 4 passed list szűrési bug

**Tünet**: a context betöltődik, de a Phase 4 logikája **csak az AAPL-t** engedi át a snapshot-mentésre.

**Megoldás**: a `phase4_stocks.py`-ban a `passed` lista logika átvizsgálása, a hibás szűrési feltétel azonosítása és javítása.

**Effort**: ~1-1,5 óra (kód átolvasás + javítás + 4-5 unit teszt)

### Hipotézis C: Pipeline-split óta a context serializálás inkonzisztens

**Tünet**: a context fájl mentése és olvasása között adatvesztés (pl. a JSON serializáció hibás, vagy a gzip kompresszió bug).

**Megoldás**: a serializációs kód átvizsgálása, a 22:00 cron mentés és a 16:15 cron olvasás ellenőrzése.

**Effort**: ~2-3 óra (kód átolvasás + tesztek)

## A fix után

### 5. lépés — Snapshot regenerálás (opcionális, ha szükséges)

A snapshot fix után a **post-Apr 10 időszakban** sok hiányos snapshot van. Ha a `flow-decomposition.py` analízist újra futtatjuk, a frissesti adat **a fix utáni napokra** lesz csak.

**Opció**: az IBKR live trade adatok + a Polygon historikus árakból **retrospektív snapshot regenerálás**. Ez 1-2 nap fejlesztés, **NEM most** prioritás. Az új paper trading folyam (W20+) természetes módon új snapshot adatot fog termelni.

### 6. lépés — Tesztek

- A Phase 4 snapshot mentési logikára 3-4 unit teszt
- A 16:15 cron path-on integration smoke teszt (1 minta nappal)
- Egy konkrét regresszió teszt: ha a context hiányos, a snapshot mentés egyértelmű hibajelzéssel áll meg

### 7. lépés — Commit

```
fix(phase4): snapshot regression — restore full ticker universe in 16:15 cron

- Root cause: <hipotézis A/B/C alapján>
- Affected period: 2026-04-10 → 2026-05-08 (29 trading days)
- Snapshot before: 1 ticker (AAPL only)
- Snapshot after: full universe (~250-300 tickers)

The flow-decomposition.md analysis was based on Feb-Apr 1 data only.
Post-Apr 13 (BC23) scoring performance is now measurable.

Tests: <N új unit teszt>
```

## Kapcsolódó

- `docs/analysis/flow-decomposition.md` (232 trade, scope rögzítve)
- `docs/tasks/2026-05-08-dark-pool-debug.md` (a felfedező audit)
- `state/phase4_snapshots/` (a regresszió tárgya)
- `state/phase13_ctx.json.gz` (a context fájl)
- `src/ifds/phases/phase4_stocks.py` (a snapshot mentési logika)
- `scripts/deploy_intraday.sh` (a 16:15 cron entry point)
