# CC→CC Handoff — Ülés A → B  (2026-05-18 hétfő reggel → délután)

**Készítő:** Claude Code (Ülés A, hétfő reggel 08:49-11:57 CEST)
**Címzett:** a következő Claude Code session (Ülés B, hétfő délután ~14:00)
**Folytatás:** [`docs/journal/2026-05-16-handoff.md`](2026-05-16-handoff.md) (Fázis 1 zárás), [`docs/handoff/2026-05-16-chat-handoff-phase1-w21-close.md`](../handoff/2026-05-16-chat-handoff-phase1-w21-close.md) (Chat oldal)

---

## Státusz egy mondatban

**Ülés A LEZÁRVA** — Task #1 (Swing Universe S&P 500 + R1000) és Task #2 (Phase 4 swing scoring + EWMA) deployolva, 1624 → **1656 passing** (+32 új teszt, Wikipedia live smoke verified, 2-day EWMA chain verified) — az új paper trading **Day 1 = kedd 5/19 15:30 CEST** marad (a tervezett 1 napi csúszás, Tamás döntés).

## Kész — Ülés A (3h munka)

- **`50dfb3c`** — feat(universe): S&P 500 + Russell 1000 swing universe source (Day 63 §3.9)
  - Új modul `src/ifds/data/swing_universe.py` — Wikipedia primary (stdlib `html.parser`), FMP fallback, 7d cache, header-driven Symbol column detection
  - Phase 2 `_screen_long_universe` integráció — FMP screener intersect swing union
  - Live smoke: SP500=503, R1000=1002, union=1008 (497 overlap)
  - 14 új teszt
- **`13e3b3d`** — feat(scoring): swing Phase 4 — PCR + OTM-inverse percentile + EWMA(5) (Day 63 §3.13)
  - Új modul `src/ifds/scoring/swing_score.py` — `compute_percentile_score`, `compute_raw_swing_score`, `SwingEwmaState`, `compute_swing_scores`
  - Phase 4 `_apply_swing_scoring` post-processor (sync + async paths)
  - Phase 6 M_VIX gating (`m_vix_enabled=False` default)
  - 18 új teszt
  - 2-day EWMA smoke verified: AAPL Day 1=81.67 → Day 2=59.44 (α=0.333 blend)

## Folyamatban — Ülés A vége utáni docs commit (most kerül push-ra)

- `docs/journal/2026-05-18-ules-a-handoff.md` (ez a fájl)
- `docs/journal/2026-05-18-session-close-ules-a.md` (journal close)
- `docs/STATUS.md` frissítve
- 1 docs commit, push origin/master

## Következő lépés (Ülés B — délután ~14:00 CEST, ~2.5h)

### 0. Pull + verify (5 min)

```bash
cd ~/SSH-Services/ifds
git pull origin master
git log --oneline -5    # várt: 4-5 mai commit a top-en (50dfb3c, 13e3b3d, és a docs commit)
python -m pytest tests/ -q | tail -2   # 1656 passing kell
```

### 1. Task #3 — Phase 6 sizing átalakítás (~2h CC, P0)

- File: [`docs/tasks/2026-05-17-swing-sizing-phase6.md`](../tasks/2026-05-17-swing-sizing-phase6.md)
- Scope (Day 63 §3.7, §3.11 — Döntés 7, 11):
  - **0.35% risk per position** (jelenlegi: dinamikus risk multiplier)
  - **12 concurrent position cap** (jelenlegi: 5)
  - **30% notional sector cap** (jelenlegi: 3 position/sector)
  - **Sector-balanced greedy fill** (D10 elfogadott Chat-döntés) — score-ranked rotation per-sector
- Új TUNING: `swing_position_risk_pct: 0.0035`, `swing_max_positions: 12`, `swing_sector_notional_cap_pct: 0.30`
- A meglévő `_calculate_position` + `_apply_position_limits` átalakítása
- Várt tesztek: 10-15 (sector cap, max positions cap, greedy ordering, risk allocation precision)

### 2. Ülés B vége handoff B → C (Task #4-re)

- Push
- Új CC→CC handoff doc
- Kedd reggeli Ülés C = Task #4 (execution + exit, ~3h) + Task #5 (deploy kickoff, ~1h)

## Nyitott task fájlok

```
docs/tasks/2026-05-17-swing-sizing-phase6.md             OPEN  P0   ← Ülés B kezd ezzel
docs/tasks/2026-05-17-swing-execution-exit.md            OPEN  P0   ← Ülés C
docs/tasks/2026-05-17-swing-deploy-kickoff.md            OPEN  P1   ← Ülés C
```

DONE Ülés A-ban:
- `docs/tasks/2026-05-17-swing-universe-sp500-r1000.md`   DONE
- `docs/tasks/2026-05-17-swing-scoring-phase4.md`         DONE

## Döntések ebből az ülésből (Ülés A, 2026-05-18 reggel)

1. **Wikipedia HTML parsing stdlib-only** (no lxml/bs4) — egy `html.parser.HTMLParser` subclass kezeli mind az SP500 (Symbol col 0) és R1000 (Symbol col 1) layoutot **header-driven** detekcióval (`<th>` "Symbol"/"Ticker" match), nem hard-coded column-indexszel
2. **`id="constituents"` table targeting** — mind a két Wikipedia page ezzel az ID-vel jelöli a komponens-táblát
3. **Class-share normalizálás `.` → `-`** — `BRK.B → BRK-B` (FMP/Polygon/IBKR konvenció)
4. **Phase 2 swing source = FMP screener INTERSECT union** — nem külön quote-fetch (per-ticker FMP enrichment megőrizve)
5. **Phase 4 swing scoring = POST-PROCESSING overlay** — a legacy combined_score pipeline fut, utána a swing-post-processor recovery-zi a legacy-clipped + min_score tickereket és újraértékeli ewma_score-on
6. **Test fixture pinning** — `swing_scoring_enabled=False` + `universe_source=fmp_screener` + `m_vix_enabled=True` per-suite a legacy regressziós tesztekhez (rule: test env hygiene)

## Gotchák / nem nyilvánvaló dolgok

### A) Branch név: `master`, nem `main`

A Chat handoff `git push origin main`-t ír egy helyen — a tényleges branch `master`.

### B) Két `_recompute_dp_pct_score` (uw_shadow + phase4_stocks)

Ez tudatos. A `ifds.scoring.swing_score` modul **NEM** importálja a `phase4_stocks._recompute_dp_pct_score`-t — kerülje a Phase 4 internal import-okat.

### C) State files már a working tree-ben

A Wikipedia live smoke létrehozta a `state/swing_universe/universe.json` fájlt (untracked). Ez gitignore-olt elvileg — ellenőrizd a `.gitignore`-t Ülés B elején, ha nincs benne `state/` mappa, add hozzá.

### D) Phase 4 post-processor két helyen van wire-elve

Sync (`run_phase4` ~line 350) + async (`_run_phase4_async` ~line 1502). Mindkettő ugyanazt a `_apply_swing_scoring(analyzed, config, logger)` hívja. Ha módosítod a logikát, mindkét helyen működnie kell — a tesztek a sync path-on mennek, de production async path is aktív (`async_enabled=True` Mac Mini-n).

### E) Phase 4 swing post-processor a Pass-2 dp_provider ENRICHMENT UTÁN fut

Tudatos: a dp_provider pass-2 enrichment (`_enrich_passed_with_dp_sync/async`) is a régi `combined_score`-t használja a re-scoring-hoz. A swing post-processor utána fut, és felülírja a `combined_score`-t az ewma swing score-ra. **A dp_provider re-scoring eredménye nem hat a swing scoring-ra** — ez akkor lenne probléma, ha a swing score-ban dp_pct szerepelne, de NEM (Fázis 1-ben deaktiválva: `uw_dark_pool_scoring_enabled=False`).

### F) Phase 6 M_VIX vs M_target

Most: `M_GEX=1.0` (Fázis 1), `M_VIX=1.0` (Task #2), `M_contradiction=1.0` (default). **Csak M_target aktív** a sizing multiplier chain-ben (Decision 13). Task #3-nak ezt **kötelesen** át kell venni — a 0.35%/position risk allocation után M_target továbbra is alkalmazandó (analyst overshoot védelem).

### G) State files location konvenció

- `state/swing_universe/universe.json` (~1000 ticker, 7d TTL) — Task #1
- `state/swing_ewma_state.json` (per-ticker EWMA history) — Task #2
- `state/swing_positions.json` (új, mental stop tracking) — Task #4 (Ülés C)

A `state/` directory már létezik (BC19 phase4_snapshots + UW shadow log használja). Új fájlok automatikusan ott kerülnek létre.

## Paper Trading (aktuális, régi rendszer)

- **Day 65/21 (overrun, régi)** | cum. PnL: −$1,204.48 (−1.20%)
- Hétfő (5/18) **NINCS új paper trading** — várjuk a kedd 5/19 Day 1-et
- Tamás manual lépések HÉTFŐN (Task #5 §5 deploy checklist):
  - `nuke.py --positions` régi AAPL/AVDL.CVR
  - IBKR paper account reset ($100K újra)
  - `cumulative_pnl.json` reset (Day 1, $0)
  - `crontab.md` — `deploy_intraday.sh` DISABLE hétfőre, kedd reggel re-enable
  - `.env` swing-flag-ek ellenőrzés (mind a 4 most már default OFF/ON helyesen)

## Tesztek

- **1656 passing**, 0 failure, 0 warning
- Wall clock: 4.4-5.0s (smooth)
- Test deltas:
  - Pre Ülés A: 1624
  - Task #1 (universe): +14 új test_swing_universe.py
  - Task #2 (scoring): +18 új test_swing_score.py
  - 3 legacy test fixture pin (test_phase4, test_phase6, test_phase6_m_contradiction)

## Resume parancs (másold be az Ülés B chat elejére)

```
/continue

Olvasd el az Ülés A → B handoff doc-ot:
docs/journal/2026-05-18-ules-a-handoff.md

Folytasd a Fázis 3 vasárnapi deploy roadmap-ot. Ülés A lezárva (Task #1 + #2 deployed, 1656 tests). Most Ülés B következik.

Első lépés:
1. git pull origin master  (Ülés A docs commit lekapása)
2. pytest baseline (1656 passing kell)
3. Task #3 indítása: docs/tasks/2026-05-17-swing-sizing-phase6.md

Day 1 = kedd 5/19 15:30 CEST. Hétfő nincs új paper trading. Ülés C kedd reggel = Task #4 + #5.
```

## Blokkolók

- Nincs

## Tanulság (sub-pattern — érvényesülő rule példa, nem új learning)

**Live API schema verifikáció commit ELŐTT** (ifds-rules.md 2026-04-27) — érvényesült: a Wikipedia parser első verziója a Russell 1000-en 0 ticker-t adott vissza (mert az SP500 layout szerint a Symbol az első oszlopban van, de a R1000 layout-ban a második). A header-driven detection rewrite után 1002 symbol ✓. **Ha "20-ticker smoke" alapján deployoltam volna, hétfő reggel 0 R1000-es ticker → universe = 503 SP500 only → senki nem észreveszi mert működik, csak felére csökkenne az universe.**

A live smoke (`python -c "fetch_russell1000_from_wikipedia()"`) **commit előtt** azonnal megmutatta a hibát. **A rule értékes**.
