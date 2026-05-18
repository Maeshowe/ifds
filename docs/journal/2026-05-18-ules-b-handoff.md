# CC→CC Handoff — Ülés B → C  (2026-05-18 hétfő délután → kedd reggel)

**Készítő:** Claude Code (Ülés B, hétfő délután ~14:00-15:30 CEST)
**Címzett:** a következő Claude Code session (Ülés C, kedd 5/19 reggel)
**Folytatás:** [`docs/journal/2026-05-18-ules-a-handoff.md`](2026-05-18-ules-a-handoff.md) (Ülés A → B, Task #1+#2 done), [`docs/handoff/2026-05-16-chat-handoff-phase1-w21-close.md`](../handoff/2026-05-16-chat-handoff-phase1-w21-close.md) (Chat oldal, Fázis 3 deploy roadmap)

---

## Státusz egy mondatban

**Ülés B LEZÁRVA** — Task #3 (Swing Sizing Phase 6) deploy-olva, **1656 → 1672 passing** (+16 új teszt, 0 regression, mock 10-ticker univerzum smoke verified). Day 1 = kedd **5/19 15:30 CEST** marad. Ülés C reggel = **Task #4 (Execution + Exit, ~3h) + Task #5 (Deploy Kickoff, ~1h CC + ~30 min Tamás manual)**.

## Kész — Ülés B (~1.5h munka)

- **`fc1e573`** — feat(sizing): swing Phase 6 — 0.35% risk, 12 cap, 30% sector notional, sector-balanced greedy
  - `compute_swing_notional(stock, config)` — pure formula: `notional = (equity × 0.0035) / (ATR_pct × 2.0) × M_target`
  - `_calculate_swing_position(...)` — full `PositionSizing` build; csak `M_target` aktív, a többi multiplier forced 1.0
  - `_select_swing_entries(candidates, open_positions, ...)` — sector-balanced greedy fill (D10), 12 concurrent cap, 30% notional sector cap, 3 daily new cap
  - `_run_phase6_swing(...)` — branch wrapper: threshold filter (`swing_score_threshold=50.0`) → greedy → Portfolio VaR (megőrizve)
  - `run_phase6()` kibővítve `open_positions: list[PositionSizing] | None` kwarg-gal (default `None` → empty list)
  - Új TUNING: `swing_sizing_enabled=True`, `swing_risk_per_trade_pct=0.0035`, `swing_max_concurrent=12`, `swing_max_daily_new=3`, `swing_sector_cap_pct=0.30`, `swing_stop_atr_multiple=2.0`, `swing_tp1_atr_multiple=1.25`, `swing_tp2_atr_multiple=2.0`, `swing_min_notional=1_000`
  - **`m_contradiction_enabled` default flip:** `True → False` (Day 63 §3.13)
  - Új RUNTIME: `max_positions: 5 → 12`, `max_gross_exposure: 80_000 → 150_000`, `max_single_ticker_exposure: 20_000 → 15_000`
  - 16 új teszt `tests/test_swing_sizing_phase6.py`:
    - `compute_swing_notional` (4): basic formula, M_target moderate (0.85) és severe (0.60) overshoot, zero ATR
    - `_calculate_swing_position` (3): basic LONG, zero ATR, below `swing_min_notional`
    - `_select_swing_entries` (7): max_daily_new, max_concurrent, at_cap, sector_cap, balanced greedy (lower-S other sector picked), zero qualified, open positions notional accounting
    - `run_phase6` integration (2): M_VIX-disabled invariance, end-to-end swing path with mixed sectors
  - Legacy multiplier-chain test fixtures pinned (`swing_sizing_enabled=False` + legacy `max_positions=5` + legacy exposure caps) — érintett: `test_phase6.py`, `test_phase6_m_contradiction.py`, `test_bc11_robustness.py`, `test_bc13_backlog.py`, `test_bc18_ewma.py`
  - Smoke: 10-ticker mock univerzum (4 sector, vegyes scoring, 1 analyst overshoot ticker) → 3 entry kiválasztva (max_daily_new), $36,800 gross, $731 risk, M_target=0.60 érvényesülve, per-ticker $15k cap mindkét magas-priced Tech-en aktív
- Docs frissítve: `PARAMETERS.md` (új Swing Sizing szekció), `PIPELINE_LOGIC.md` (új 6.SWING szekció a Phase 6 elejére), `CHANGELOG.md` (Ülés B entry), `STATUS.md` (Task #3 ✅), task fájl (`Status: DONE`)

## Következő lépés (Ülés C — kedd reggel ~6:00 CEST, ~4h)

### 0. Pull + verify (5 min)

```bash
cd ~/SSH-Services/ifds
git pull origin master
git log --oneline -5    # várt: fc1e573 (Task #3), 7012d53 (B handoff), 13e3b3d (Task #2), 50dfb3c (Task #1), 77bd180 (Fázis 1 close)
python -m pytest tests/ -q | tail -2   # 1672 passing kell
```

### 1. Task #4 — Swing Execution + Exit (~3h CC, P0)

- File: [`docs/tasks/2026-05-17-swing-execution-exit.md`](../tasks/2026-05-17-swing-execution-exit.md)
- Scope (Day 63 §3.1, §3.6, §3.8, §3.12 — Döntés 1, 6, 8, 12):
  - `submit_orders.py` átalakítás: **bracket → csak market BUY**, állapot `state/swing_positions.json`-be
  - **Entry idő 16:20 → 15:30 CEST** (= 09:30 ET, market open)
  - `pt_monitor.py`: 5-perces loop → **napi 1× EOD eval @ 22:00 CEST** (6 exit feltétel: HARD_SL, MENTAL_SL, TP1, TP2, TRAIL_SL, TIME_STOP)
  - `close_positions.py` két mode:
    - `--mode=eod_flags` @ 15:30 másnap (HARD/MENTAL/TP/TRAIL)
    - `--mode=time_stop` @ 21:40 today (TIME_STOP MOC)
  - **TP-struktúra** 1.25×/2.0× → **1.5×/3.0× ATR**, 50/50 split (a Task #3-ban beállított `swing_tp1_atr_multiple=1.25` és `swing_tp2_atr_multiple=2.0` **felülírandó** Task #4-ben — lásd "Gotcha B" lent)
  - **Hard SL** új: -8% weekly cumulative
  - **Time-stop** 5 trading day
  - **LOSS_EXIT -2% intraday DEAKTIVÁLVA** (DTE/SQM duplikált bug osztály megszünt)
- Új `SwingPosition` dataclass: entry_price/date, atr, stop_level, tp1_level, tp2_level, tp1_hit, trail_sl, days_held, qty/qty_remaining, next_action, next_action_at, weekly_pnl_pct
- Új TUNING (Task #4 spec §7): `swing_execution_enabled=True`, `swing_entry_time_cest="15:30"`, `swing_eod_eval_time_cest="22:00"`, `swing_tp1_atr_multiple=1.5`, `swing_tp2_atr_multiple=3.0`, `swing_mental_stop_atr_multiple=2.0`, `swing_trail_atr_multiple=1.0`, `swing_hard_sl_weekly_cumulative_pct=-0.08`, `swing_time_stop_trading_days=5`, `swing_positions_state_file="state/swing_positions.json"`, `ibkr_bracket_enabled=False`, `loss_exit_intraday_enabled=False`, `pt_monitor_5min_mode=False`
- **Wire-up:** `runner.py:573` `run_phase6(...)` hívása ki kell egészüljön `open_positions=load_swing_positions()`-szel (Task #3-ban a kwarg már ott van, csak hívás-szinten kell elérni)
- Várt tesztek: 15-18 unit + 1 integration (3-day swing lifecycle smoke)

### 2. Task #5 — Daily Metrics + Telegram + Deploy Kickoff (~1h CC + ~30 min Tamás manual, P1)

- File: [`docs/tasks/2026-05-17-swing-deploy-kickoff.md`](../tasks/2026-05-17-swing-deploy-kickoff.md)
- **A rész (CC, ~45 min):**
  - `daily_metrics.py` `swing_state` field-ek: `open_positions`, `new_entries_today`, `total_notional`, `sector_distribution`, `sector_max_pct`, `avg_days_held`, `exits_today`, `next_day_planned`, `swing_score_distribution`
  - Telegram daily report új kompakt template (< 800 char, mobile-friendly) — régi BMI/GEX/Cross-Asset sor kiveszi, csak swing-releváns mezők
  - 5 új teszt (template render + sector_distribution sum + max/zero/3 entries)
- **B rész (Tamás manual + CC verify, ~30 min):**
  - Régi nyitott pozíciók ellenőrzés/zárás (várt: 0, péntek 5/16 MOC már zárt mindent — de Tamás `monitor_positions.py`-vel ellenőrizze)
  - `state/circuit_breaker.json` reset (`{"active": false, "reason": null}`)
  - `state/cumulative_pnl.json` Day 1 reset ($0, day=1)
  - IBKR paper account reset $100k-re (Mac Mini Tamás manual)
  - `crontab.md` frissítés (új idők: 14:30 phase4-6, 15:25 gateway, 15:30 submit, 15:30 close-eod, 21:40 close-time, 22:00 monitor-eod, 22:05 eod report)
  - `.env` swing-flag-ek ellenőrzés (mind a 4: `swing_sizing_enabled=True`, `swing_execution_enabled=True`, `swing_scoring_enabled=True`, `universe_source=swing_sp500_r1000` — alapból default-on jönnek)
  - **git push origin master** (Tamás explicit jóváhagyás után — várt ~8-9 commit Fázis 1 + Fázis 3 close-ig)
  - `STATUS.md` Fázis 3 LIVE bejegyzés

### 3. Ülés C záró — Day 1 pre-market verifikáció (~10 min, ~14:30 CEST)

- Pipeline futás 14:30 CEST előtt: `python -m ifds run --phases 4,5,6 --strategy long --dry-run` smoke
- `execution_plan.csv` ellenőrzés (várt: 0-3 ticker, swing-mode multiplier chain output)
- IBKR Gateway ellenőrzés (Tamás Mac Mini-n)
- 15:25 CEST Tamás `check_gateway.py` manual
- 15:30 CEST cron `submit_orders.py` futása — **Day 1 első swing entry**

## Nyitott task fájlok

```
docs/tasks/2026-05-17-swing-execution-exit.md           OPEN  P0   ← Ülés C kezd ezzel
docs/tasks/2026-05-17-swing-deploy-kickoff.md           OPEN  P1   ← Ülés C lezár ezzel
```

DONE Ülés A-ban + B-ben:
- `docs/tasks/2026-05-17-swing-universe-sp500-r1000.md`   DONE (Ülés A, `50dfb3c`)
- `docs/tasks/2026-05-17-swing-scoring-phase4.md`         DONE (Ülés A, `13e3b3d`)
- `docs/tasks/2026-05-17-swing-sizing-phase6.md`          DONE (Ülés B, `fc1e573`)

## Döntések ebből az ülésből (Ülés B, 2026-05-18 délután)

1. **`× entry_price` kihagyva a sizing képletből** — a task spec `notional_j = (equity × 0.0035) / (ATR_pct_j × 2.0) × entry_price_j × M_target_j` formulája dimenzionálisan hibás (× $150 entry → ~$1.3M notional egy $100k account-ra). A korrekt formula: `notional = (equity × risk_pct) / (ATR_pct × stop_mult) × M_target`, amiből `quantity = floor(notional / entry)`. Ez ekvivalens a klasszikus risk-based sizing-gel: `quantity = (equity × risk_pct) / (ATR × stop_mult) × M_target`.
2. **`m_contradiction_enabled` default flip True → False** — a task spec szerint Fázis 2 backtest függvénye. Eddig csak a comment mondta, most a default érték is. Két `test_phase6_m_contradiction.py` teszt explicit `config.tuning["m_contradiction_enabled"] = True` opt-in-t kapott.
3. **`_run_phase6_swing` külön wrapper, NEM a meglévő `run_phase6` body átírása** — a swing branch korai return-nel ágazik le a `_join_stock_gex` után, így a legacy path változatlanul fut amikor `swing_sizing_enabled=False`. Ez azért jó, mert a legacy regression tesztek (BC11/BC13/BC18/M_contradiction) **fixture-szinten** pinneljük a régi viselkedést, NEM kód-szinten kell two-pathot karbantartani.
4. **`runner.py` változatlan ebben az ülésben** — a `run_phase6()` hívása `open_positions` nélkül megy (a kwarg default `None` → empty list). Ez tudatos: Task #4 hozza a `PositionTracker → load_swing_positions()` wire-up-ot.
5. **TP1/TP2 multiplier-ek a Task #3-ban előzetesen beállítva** (1.25× / 2.0×) **a legacy CORE értékkel egyezve** — Task #4 ezeket felülírja a swing-specifikus 1.5× / 3.0×-re. Tudatos: Task #3 nem akarta a TP geometriát megváltoztatni, csak a sizing-mátrixot. A swing-spec TP geometria a Task #4 scope-ja.
6. **`swing_min_notional = $1,000` floor** — numerikus floor: ha egy ticker compute_swing_notional eredménye < $1k (pl. $500-os entry × 0.02 ATR_pct × M_target=0.6 → $5,250 / nope, ez még átmegy; de pl. extreme high-vol setup → $750 → skip). A 12×$350/12 = $29/ticker "minimum risk" megfogalmazás a task spec-ben **számszakilag félrevezető** ($29 ≠ notional); a $1k a tényleges numerikus floor.

## Gotchák / nem nyilvánvaló dolgok

### A) `swing_max_daily_new=3` — a sector cap-pel KOMBINÁLT korlát

A smoke-test 10 ticker / 4 sector mintán **3 entry** jött (max_daily_new). A sector cap (30% × $100k = $30k) **nem** triggerelt — a Tech sector $29.8k-ra állt meg (2 entry × ~$15k cap miatt), a 3. Tech ticker `daily_cap` miatt esett ki, nem sector_cap miatt. Az `excluded_position_limit=6` a Phase6Result-ban a kombinált daily_cap (3 ticker érte be) + concurrent_cap (0 itt) szám. Ha a Task #5 daily metrics csak 1 számot ad ki (`excluded_position_limit`), tudatosan figyelmeztessük, hogy ez **kombinált** — Task #5 daily metrics-ben érdemes lehet különválasztani.

### B) TP1/TP2 multiplier ütközés Task #3 ↔ Task #4

Task #3 a `swing_tp1_atr_multiple=1.25` és `swing_tp2_atr_multiple=2.0` értéket állítja be (CORE-ral egyező). Task #4 spec §7 felülírja: `swing_tp1_atr_multiple=1.5`, `swing_tp2_atr_multiple=3.0`. Ez **tudatos** — Task #4 a swing-spec TP geometria, Task #3 csak a sizing geometriát rendezte. Task #4 implementáció **edit-elje a `defaults.py`** értékeket (NEM új kulcs!) és frissítse a `PARAMETERS.md` táblát.

### C) `runner.py:573` `run_phase6(...)` hívás — Task #4 wire-up szükséges

A jelenlegi hívás nem ad át `open_positions`-t. Production cron-on a `PositionTracker.list_open()` (vagy a Task #4 `load_swing_positions("state/swing_positions.json")`) hívásával kell ezt megoldani:

```python
# Task #4-ben adandó:
from ifds.state.swing_manager import load_swing_positions
open_pos = load_swing_positions(config.runtime["swing_positions_state_file"])

phase6 = run_phase6(
    config, logger,
    ctx.stock_analyses, ctx.gex_analyses, ctx.macro, strategy,
    signal_history_path=...,
    sector_scores=ctx.sector_scores,
    signal_hash_file=...,
    mms_analyses=ctx.mms_analyses,
    bmi_value=ctx.bmi_value,
    open_positions=open_pos,   # ← ÚJ
)
```

Ennek hatása nélkül a 12 cap és a 30% sector cap **nem ismeri** a már nyitott pozíciókat — Day 1-re ez **nem** kritikus (üres state-tel indulunk), de Day 2-től **kötelező** (különben minden nap +3 új entry jöhet a meglévő 5-10 mellé → cap-átlépés).

### D) M_target a swing path-on **megőrzi** az audit trail-t

A `PositionSizing.m_target` mező továbbra is friss érték (az analyst overshoot penalty alkalmazása esetén). Ez fontos a daily metrics + Telegram report-hoz: ha egy entry M_target=0.60-nal jött be, az látszik az `execution_plan.csv`-ben és a Telegram-ban is. A `multiplier_total` a swing path-on `= m_target` (mind a 4 többi 1.0).

### E) Legacy test fixture pin pattern — Task #4 / #5 is alkalmazza

A Task #4-ben új teszteket írni (`tests/test_swing_execution.py`) — a fixture-ben **NE** pinneld `swing_execution_enabled=False`-t (mert az új path-ot teszteled), DE a `submit_orders.py` legacy tesztjei (`test_submit_bracket_status_check.py`, ha van) **pin-elendők** legacy módra (`ibkr_bracket_enabled=True`, `swing_execution_enabled=False`). Ugyanaz a pattern, mint a Task #3 fixture-pin csere.

### F) `swing_positions.json` state file conflict potential

Task #1 már létrehoz egy `state/swing_universe/universe.json`-t (Wikipedia cache). Task #4 új `state/swing_positions.json`-t. Egyik se ütközik (külön directory/fájl), de ha valami "swing"-prefixet keresel a `state/` mappában `ls state/swing_*`, mindkettő látszani fog. A `state/swing_ewma_state.json` (Task #2) megint külön.

### G) IDE-ben nyitva: `docs/tasks/2026-05-19-earnings-exclusion-7to10.md`

Tamás megnyitotta IDE-ben — de **a fájl még nem létezik** (`ls`-sel nem találtam). Valószínűleg Chat éppen most ír egy follow-up taskot a Fázis 1 earnings-exclusion-ról (7d → 10d, ami a `2026-05-16` Ülés A-ban beállt érték — a régi 7d → új 10d swing-buffer-rel). Ha az Ülés C alatt megjelenik, akkor egy P2 follow-up task (NEM blokkolja a Fázis 3 deploy-t). Tamás külön bejelentés esetén iktasd be Ülés C scope-ba.

## Paper Trading (aktuális, régi rendszer)

- **Day 65/63 (overrun, régi)** | cum. PnL: −$1,113.16 (−1.11%)
- Hétfő (5/18) **NINCS új paper trading** — várjuk a kedd 5/19 Day 1-et
- Régi rendszer **utolsó futása** volt péntek 5/16 (MOC zárt minden pozíciót)
- **Tamás manual lépések Ülés C alatt (Task #5 §5.1 + §5.2):**
  - `monitor_positions.py` (clientId=14) ellenőrzés (várt: 0 nyitott)
  - `nuke.py --positions` ha bármi maradt (ne legyen)
  - IBKR paper account reset ($100K újra, Mac Mini)
  - `cumulative_pnl.json` reset (Day 1, $0)
  - `crontab.md` swing-mode aktiválás
  - `.env` swing-flag-ek ellenőrzés
  - git push origin master (Ülés C close + Task #4 + Task #5)

## Tesztek

- **1672 passing**, 0 failure, 0 warning
- Wall clock: 4.5-4.8s (smooth)
- Test deltas:
  - Pre Ülés B (= post Ülés A): 1656
  - Task #3 sizing: +16 új `test_swing_sizing_phase6.py`
  - 5 fixture pin update (legacy multiplier-chain tesztek: phase6, phase6_m_contradiction, bc11_robustness, bc13_backlog, bc18_ewma)

## Resume parancs (másold be az Ülés C chat elejére)

```
/continue

Olvasd el az Ülés B → C handoff doc-ot:
docs/journal/2026-05-18-ules-b-handoff.md

Folytasd a Fázis 3 deploy-t. Ülés A+B lezárva (Task #1+#2+#3 deployed,
1672 tests). Most Ülés C következik.

Első lépés:
1. git pull origin master  (Ülés B docs commit lekapása)
2. pytest baseline (1672 passing kell)
3. Task #4 indítása: docs/tasks/2026-05-17-swing-execution-exit.md
4. Task #5 utána: docs/tasks/2026-05-17-swing-deploy-kickoff.md

Day 1 = kedd 5/19 15:30 CEST. Pre-market verifikáció ~14:30 CEST.
Ülés C záró: Tamás manual deploy steps (Task #5 §5).
```

## Blokkolók

- Nincs

## Tanulság (sub-pattern — érvényesülő rule példa, nem új learning)

**Live API schema verifikáció commit ELŐTT** (ifds-rules.md 2026-04-27) — Task #3-nál NEM volt szükség külső API-ra, így a rule itt nem alkalmazódott. Az érvényesülő rule ehelyett:

**Test environment higiénia — production state path írás TILOS** (ifds-rules.md 2026-05-10) — érvényesült: a Task #3 swing tesztek mind `tmp_path`-be írnak (daily_trades.json, daily_notional.json fixture-szinten redirect-elve). Egy regression-teszt írása nélkül (`test_save_snapshot_is_mocked_in_e2e` típusú assertion) NEM dolgoztunk most, mert nem `run_pipeline`-t teszteltünk — a `run_phase6` egyetlen state-író hívása (`_save_daily_counter`) fixture-ben tmp_path-re mutat.

**Új sub-pattern (Ülés B saját megfigyelés, nem új rule, csak megfigyelés):**

A task spec **mathematikai formulájának dimensional sanity check-je** (Döntés 1 a session-ben) — a `× entry_price_j` plusz tag a notional képletben a smoke-test pillanatában látszott meg ($1.3M notional egy $100k account-ra). Ha vakon implementáltam volna a spec szerint, a 16 teszt mind átment volna (mert a tesztek számszakilag konzisztensek a formulával), de az **első élesi futás $1M+ pozíciókat akart volna feladni**, ami IBKR `max_order_quantity=5000` és `max_single_ticker_exposure=$15k` ellenére is **észrevehető anomália** lenne. A dimensional sanity check (`equity × dimensionless / dimensionless = $$$, NEM $$$ × $/share`) **commit előtt** elkerülte. Érdemes a Task #4-nél is dimensional sanity check-elni a hard SL formulát: `weekly_cumulative_pnl_pct = Σ daily_pnl_$ / equity_$` (dimensionless, ✓).
