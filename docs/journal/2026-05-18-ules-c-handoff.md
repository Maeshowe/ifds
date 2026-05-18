# CC→Tamás Handoff — Ülés C → Manual Deploy  (2026-05-18 hétfő este → kedd 5/19 reggel)

**Készítő:** Claude Code (Ülés C, hétfő este)
**Címzett:** Tamás — manual deploy kickoff lépések a Task #5 §5 szerint, majd kedd 5/19 reggel pre-market verifikáció
**Folytatás:** [`2026-05-18-ules-b-handoff.md`](2026-05-18-ules-b-handoff.md) (Ülés B → C, Task #3 done)

---

## Státusz egy mondatban

**Ülés C CC-scope LEZÁRVA** — Task #4 (Swing Execution + Exit) és Task #5 A rész (Daily Metrics + Telegram) deploy-olva, **1672 → 1711 passing** (+39 új teszt, 0 regression). A maradék **Task #5 B rész = Tamás manual + git push** (kb. ~30 min). Day 1 = kedd **5/19 15:30 CEST**.

## Kész — Ülés C (~2h CC munka)

### `e887749` — feat(execution): swing 15:30 entry + mental stop + daily EOD eval (Task #4)

**Új modul: `src/ifds/state/swing_positions.py`**
- `SwingPosition` dataclass (entry_price/date/atr, stop_level, tp1_level, tp2_level, tp1_hit, trail_sl, days_held, qty/qty_remaining, next_action, next_action_at, weekly_pnl_pct, sector, direction, m_target)
- `evaluate_position_eod(...)` — 6-condition eval (priority: HARD_SL → MENTAL_SL → TP2 → TP1 → TRAIL_SL → TIME_STOP → HOLD), pure
- `evaluate_all_positions(...)` — batch eval helper
- `apply_executed_exit(...)` — TP1 → partial (qty_remaining csökken, tp1_hit=True), mások → None (full close)
- `load_swing_positions(...)` / `save_swing_positions(...)` — atomic JSON I/O
- `to_position_sizing_stub(...)` — SwingPosition → PositionSizing stub a runner sector cap math-hoz
- `build_swing_position_from_sizing(...)` — friss SwingPosition kalkuláció CSV `stop_loss`-ból

**`submit_orders.py`** — új `submit_swing_market_only(...)` branch:
- Csak market BUY (no bracket OCA), `orderRef=IFDS_SWING_{sym}`
- ATR visszafejtése a CSV `stop_loss`-ból: `ATR = (entry - stop_loss) / swing_mental_stop_atr_multiple`
- `save_swing_positions(state_file, ...)` az entry után
- Silent-reject guard megmarad (paper account `algoStrategy` rule)
- Tamás `python ifds.config.loader.Config()` betöltésével detektálja a swing módot

**`pt_monitor.py`** — új `--mode=eod_eval` argparse branch:
- `run_eod_eval()` betölti `state/swing_positions.json`-t, fetched Polygon daily bar minden tickerre
- `evaluate_all_positions(...)` → state frissítés
- Telegram exit summary az kiürülő flagű ticker-ekre
- A legacy 5-min scenario_a path változatlan (csak gating-elve)

**`close_positions.py`** — új `--mode=eod_flags` és `--mode=time_stop` branch:
- `run_swing_eod_flags(state_file, today_str)` — 15:30 CEST, market SELL a HARD_SL/MENTAL_SL/TP1/TP2/TRAIL_SL flagű pozíciókra (TP1 → 50% partial, mások → full close)
- `run_swing_time_stop(state_file, today_str)` — 21:40 CEST MOC SELL a TIME_STOP flagű pozíciókra
- Legacy `--mode=moc` (régi MOC zárás) megmarad (`default`)

**`runner.py:573` wire-up** — `run_phase6(...)` hívása `open_positions=` kiegészítve:
```python
open_positions = []
if config.tuning.get("swing_execution_enabled", False):
    from ifds.state.swing_positions import (
        load_swing_positions, to_position_sizing_stub,
    )
    state_file = config.tuning["swing_positions_state_file"]
    open_swings = load_swing_positions(state_file)
    open_positions = [to_position_sizing_stub(p) for p in open_swings]
```
Day 1-re üres state → empty list (12 cap és sector cap változatlan).

**Új TUNING (defaults.py):**
- `swing_execution_enabled=True`, `swing_entry_time_cest="15:30"`, `swing_eod_eval_time_cest="22:00"`
- `swing_close_eod_action_time_cest="15:30"`, `swing_close_time_stop_time_cest="21:40"`
- `swing_tp1_sell_pct=0.50`, `swing_mental_stop_atr_multiple=2.0`, `swing_trail_atr_multiple=1.0`
- `swing_hard_sl_weekly_cumulative_pct=-0.08`, `swing_time_stop_trading_days=5`
- `swing_positions_state_file="state/swing_positions.json"`
- `ibkr_bracket_enabled=False`, `loss_exit_intraday_enabled=False`, `pt_monitor_5min_mode=False`
- **`swing_tp1_atr_multiple: 1.25 → 1.5`**, **`swing_tp2_atr_multiple: 2.0 → 3.0`** (swing-spec TP geometria, ülés B-ben Task #3 utáni override)

**Tesztek (`tests/test_swing_execution.py`):** 33 új teszt
- State I/O (roundtrip, missing, malformed)
- Pure helpers (weekly_pnl_pct, sell_qty TP1 50% / full exit, builder, stub converter)
- 6-condition EOD eval (HOLD, MENTAL_SL, TP1, TP2, HARD_SL, TIME_STOP)
- Priority order (HARD > MENTAL, TP2 > TP1)
- Trail SL (inactive before TP1, init after, ratchet upward only, trigger when below)
- Batch eval (mixed actions, missing OHLC)
- Apply exit (TP1 partial, full-exit returns None)
- Friday entry calendar-5-days TIME_STOP
- M_target audit trail roundtrip
- TUNING wiring (all 13 keys present, TP multipliers match spec, legacy gates off)
- 3-day swing lifecycle integration smoke (Day 1 entry → Day 2 TP1 partial → Day 3 trail hit)
- Runner open_positions loader (empty state, conversion preserves notional & sector)

### `a907060` — feat(metrics): swing_state daily metrics + compact Telegram template (Task #5 A)

**`scripts/paper_trading/daily_metrics.py` — új `_build_swing_state(...)`:**
```python
"swing_state": {
    "open_positions": int,
    "max_concurrent": 12,
    "new_entries_today": int,
    "new_entries_tickers": list[str],
    "total_notional": float,
    "total_notional_pct_equity": float,
    "sector_distribution": dict[sector, $],
    "sector_max_pct": float,
    "avg_days_held": float,
    "max_days_held": int,
    "exits_today": dict[action, count],
    "next_day_planned": {"exits_at_1530": list, "time_stops_at_2140": list},
    "swing_score_distribution": {
        "qualifying_threshold_50": int,
        "threshold": 50.0,
        "selected_for_entry": int,
        "top_3_scores": [{"ticker", "S_j", "sector"}],
    },
}
```

**Új modul: `src/ifds/output/swing_telegram.py`** — `format_swing_compact_telegram(metrics) -> str`:
- Mobile-friendly < 800 char template
- Swing-only mezők; régi BMI / GEX / Cross-Asset Regime sorok elhagyva
- Top 3 Sj rendezett listája, holnapra tervezett 15:30 + 21:40 exitek, UW shadow összegzés, VIX + SPY snippet

**Tesztek (`tests/test_swing_metrics_telegram.py`):** 6 új teszt
- Compact format (< 800 char + tartalmaz "Day 1" + "NVDA")
- Zero entries / zero exits
- Max entries (3 új + 12/12 cap, nincs overflow)
- Top scores section omitted when empty
- `_build_swing_state` sector_distribution sums to total_notional
- Empty state file → safe defaults

**Docs frissítve:**
- `docs/PARAMETERS.md` — új "Swing Execution + Exit" szekció (13 új TUNING kulcs táblázattal, exit priority order, SwingPosition schema)
- `docs/PIPELINE_LOGIC.md` — új "6.SWING-EXIT" szekció (daily timeline, evaluate_position_eod kontrakt, runner wire-up)
- `docs/CHANGELOG.md` — Task #4 + Task #5 entries
- `docs/STATUS.md` — Ülés C bejegyzés
- Task files (4, 5) — Status frissítve

---

## Maradék — Task #5 B rész (Tamás manual + CC verify, ~30 min)

A következő lépéseket **Tamás végzi el manual** (a Mac Mini-n), majd git push:

### B.1 — Régi nyitott pozíciók ellenőrzés/zárás (várt: 0)

```bash
# Mac Mini-n
cd ~/SSH-Services/ifds
python scripts/paper_trading/monitor_positions.py     # clientId=14
# Várt: 0 nyitott — péntek 5/16 MOC zárta mindet
# Ha bármi maradt → nuke.py --positions (Tamás külön döntés)
```

### B.2 — Circuit breaker reset

```bash
mkdir -p state
echo '{"active": false, "reason": null, "reset_at": "2026-05-18T22:00:00Z"}' > state/circuit_breaker.json
```

### B.3 — Cumulative P&L Day 1 reset

```bash
# scripts/paper_trading/logs/cumulative_pnl.json — Day 1, $0
python - <<'PY'
import json
from datetime import date, datetime, timezone
data = {
    "cumulative_pnl": 0.0,
    "cumulative_pnl_pct": 0.0,
    "trading_days": 1,
    "daily_history": [],
    "reset_at": datetime.now(timezone.utc).isoformat(),
    "reset_note": "Day 1 swing pivot deploy (2026-05-18)",
}
with open("scripts/paper_trading/logs/cumulative_pnl.json", "w") as f:
    json.dump(data, f, indent=2)
print("OK — cumulative_pnl Day 1 reset")
PY
```

### B.4 — IBKR paper account reset $100k-re

**Mac Mini, IBKR TWS / Gateway:**
- Login → Account → Paper Trading Reset → "Reset to $100,000"
- Verify: account DUH118657 → Balance: $100,000.00

### B.5 — Crontab frissítés (swing cron)

**Új cron entry-k (`crontab -e`):**

```cron
# IFDS Swing — Day 1 = 2026-05-18 hétfő
30 14 * * 1-5  cd ~/SSH-Services/ifds && /usr/bin/python3 -m ifds run --phases 4,5,6 --strategy long >> logs/cron_intraday_$(date +\%Y\%m\%d_\%H\%M).log 2>&1
25 15 * * 1-5  cd ~/SSH-Services/ifds && /usr/bin/python3 scripts/paper_trading/check_gateway.py >> scripts/paper_trading/logs/cron_gateway_$(date +\%Y\%m\%d_\%H\%M).log 2>&1
30 15 * * 1-5  cd ~/SSH-Services/ifds && /usr/bin/python3 scripts/paper_trading/submit_orders.py >> scripts/paper_trading/logs/cron_submit_$(date +\%Y\%m\%d_\%H\%M).log 2>&1
30 15 * * 1-5  cd ~/SSH-Services/ifds && /usr/bin/python3 scripts/paper_trading/close_positions.py --mode=eod_flags >> scripts/paper_trading/logs/cron_close_eod_$(date +\%Y\%m\%d_\%H\%M).log 2>&1
40 21 * * 1-5  cd ~/SSH-Services/ifds && /usr/bin/python3 scripts/paper_trading/close_positions.py --mode=time_stop >> scripts/paper_trading/logs/cron_close_time_$(date +\%Y\%m\%d_\%H\%M).log 2>&1
0  22 * * 1-5  cd ~/SSH-Services/ifds && /usr/bin/python3 scripts/paper_trading/pt_monitor.py --mode=eod_eval >> scripts/paper_trading/logs/cron_monitor_eod_$(date +\%Y\%m\%d_\%H\%M).log 2>&1
5  22 * * 1-5  cd ~/SSH-Services/ifds && /usr/bin/python3 scripts/paper_trading/eod_report.py >> scripts/paper_trading/logs/cron_eod_$(date +\%Y\%m\%d_\%H\%M).log 2>&1
0  22 * * 0    cd ~/SSH-Services/ifds && /usr/bin/python3 -m ifds run --phases 1,2,3 >> logs/cron_macro_$(date +\%Y\%m\%d_\%H\%M).log 2>&1
```

A **régi** entry-ket (16:20 submit, 5-min pt_monitor scenario_a, 21:45 close MOC, 19:00 AVWAP) **kommentezd ki** (`# ` prefix), ne töröld — fallback ha vissza kell térni.

`scripts/crontab.md` frissítését `/wrap-up` cikluson belül CC megírja a hétfői cron-helyzetbe.

### B.6 — `.env` swing-flag-ek ellenőrzés

```bash
cd ~/SSH-Services/ifds
grep -E 'IFDS_(POLYGON|FMP|FRED|UW|MID|TELEGRAM|IBKR)' .env | head -10
# Várt: minden kulcs jelen van
# A swing-flag-ek (swing_sizing_enabled, swing_execution_enabled stb.) NEM env var-ok,
# csak a defaults.py-ban — alapból True default-on jönnek
```

### B.7 — Git push origin master

**Ülés C close + minden commit:**

```bash
cd ~/SSH-Services/ifds
git log --oneline -10
# Várt sorrend (HEAD-től):
#   a907060 feat(metrics): swing_state daily metrics + compact Telegram template
#   e887749 feat(execution): swing 15:30 entry + mental stop + daily EOD eval
#   0c00138 docs(handoff): 2026-05-18 Ülés B close + C kickoff — Fázis 3 mid-deploy
#   fc1e573 feat(sizing): swing Phase 6 — 0.35% risk, 12 cap, 30% sector notional
#   7012d53 docs(handoff): 2026-05-18 Ülés A close + B kickoff
#   13e3b3d feat(scoring): swing Phase 4 — PCR + OTM-inverse percentile + EWMA(5)
#   50dfb3c feat(universe): S&P 500 + Russell 1000 swing universe source
#   77bd180 docs(handoff): Fázis 1 W21 close
#   d1b2206 docs(journal): 2026-05-16 Ülés C close
#   68f6633 feat(scoring): UW dark pool / GEX deactivation + shadow logging

git push origin master
# Tamás explicit jóváhagyás után — 9 commit Fázis 1 + Fázis 3 close-ig (Mac Mini-n CI/CD nincs, manuális push)
```

### B.8 — STATUS.md Fázis 3 LIVE bejegyzés

A current STATUS.md már Ülés C záró állapotában van (1711 passing). Tamás push után CC `/wrap-up` cikluson belül átírja "Phase 3 — DEPLOY LIVE (2026-05-18 hétfő este)" header-rel a következő `/wrap-up`-on.

---

## Kedd 5/19 reggel — Day 1 pre-market verifikáció (~10 min, ~14:30 CEST)

### Tamás Mac Mini-n:

```bash
cd ~/SSH-Services/ifds
git pull origin master

# 1. Tesztek (várt: 1711 passing)
python -m pytest tests/ -q | tail -2

# 2. Phase 4-6 dry-run smoke (várt: 0-3 ticker)
python -m ifds run --phases 4,5,6 --strategy long --dry-run

# 3. execution_plan.csv ellenőrzés
ls -la output/execution_plan_run_$(date +%Y%m%d)_*.csv
head -5 $(ls -t output/execution_plan_run_*.csv | head -1)
# Várt: 0-3 ticker, swing-mode multiplier_total (= M_target, 0.6-1.0 között)

# 4. IBKR Gateway ellenőrzés
python scripts/paper_trading/check_gateway.py
# Várt: "Gateway alive | account DUH118657 | NetLiq $100,000.00"

# 5. 15:25 CEST — manual check_gateway megint
# 6. 15:30 CEST — cron submit_orders.py futása, Day 1 első swing entry
# 7. 15:30 + 1.5 min — Telegram MEGFIGYELÉS:
#    "📈 IFDS Swing Submit — 2026-05-19  |  X pozíció | Total open: X"
# 8. 22:00 CEST — cron pt_monitor.py --mode=eod_eval futása (Day 1 EOD)
#    Várt: "🌙 IFDS Swing EOD — 2026-05-19" (HOLD-ok mindenhol, esetleg 0 exit)
# 9. 22:05 CEST — cron eod_report.py
#    Új compact swing Telegram template
```

### Day 1 sikerkritériumok:

- ✅ 15:30 CEST submit_orders.py futott, **state/swing_positions.json létrejött** N pozícióval (N ∈ [0, 3])
- ✅ Telegram "Swing Submit" message megjött
- ✅ IBKR DUH118657-en N nyitott pozíció látszik
- ✅ 22:00 EOD eval futott, **0 exit Day 1-re** (mind HOLD — egyik 6-condition se trigger-el az első napon, hacsak nem extreme intraday volatilitás)
- ✅ 22:05 EOD Telegram daily report megjött az új compact formátumban

### Day 1 failure modes (mit ne lépj át csendben):

- ❌ submit_orders.py exit 1 / Telegram nincs → check `scripts/paper_trading/logs/cron_submit_*.log`
- ❌ state file nincs → IBKR connection probléma vagy CSV stale → futtass manual `submit_orders.py --dry-run` smoke-ot
- ❌ Phase 4-6 cron 14:30 nem futott / execution_plan üres → manual `python -m ifds run --phases 4,5,6 --strategy long`
- ❌ check_gateway 15:25 hibázik → restart IBKR Gateway, várj 60s, retry
- ❌ Day 2+ regression: ha pt_monitor EOD eval Polygon `get_aggregates` timeout-ot dob → fallback: másnap 15:30-kor manual ellenőrzés a state-en

---

## Tesztek

- **1711 passing**, 0 failure, 0 warning
- Wall clock: 4.8-5.4s
- Test deltas Ülés C alatt:
  - Pre Ülés C (= post Ülés B): 1672
  - Task #4: +33 új `test_swing_execution.py`
  - Task #5 A: +6 új `test_swing_metrics_telegram.py`
  - `test_daily_metrics.py::test_output_has_required_keys` kibővítve `swing_state` kulccsal

---

## Döntések ebből az ülésből (Ülés C, 2026-05-18 este)

1. **Új `swing_positions.py` modul külön a `swing_manager.py`-tól** — a legacy `swing_manager.py` (BC20A) az IBKR bracket + IBKR TRAIL order világához készült, a Task #4 mental-stop arch teljesen más adatmodell. Külön modul → tisztán testable + nincs konfúzió a két állapot között. A `swing_manager.py` továbbra is megmarad a legacy path-on (`swing_execution_enabled=False` esetén).
2. **ATR reconstrukció a CSV `stop_loss`-ból, nem új CSV oszlop** — az execution_plan.csv schema változatlan; `submit_orders.py` `submit_swing_market_only` számolja a SwingPosition `atr`-ját `(entry - stop_loss) / swing_mental_stop_atr_multiple = (entry - stop_loss) / 2.0` képletből. Új CSV oszlop nem szükséges (eg. `atr` direct), ez a math tisztán visszafejtődik.
3. **`pt_monitor.py --mode=eod_eval` flag, NEM külön script** — a CC task spec szerint `pt_monitor.py` átalakítása szerepelt (NEM külön `pt_monitor_eod.py`). Argparse branch a top-level main-en, run_eod_eval() új function — a legacy 5-min scenario_a path változatlan. Cron-on `--mode=eod_eval` flag kapcsol a swing path-ra.
4. **Polygon napi bar fetch a 22:00 EOD eval-hoz, NEM IBKR snapshot** — a 16:00 ET market-close pillanatában a Polygon `get_aggregates(ticker, today_iso, today_iso, "day", 1)` adja az official OHLC-t. IBKR-n a `reqMktData` snapshot pontatlanabb (delayed quote vs. official close). Polygon FileCache amúgy is használjuk a Phase 4-6 cron-on, így nincs extra API hívás-szerződés-jelleg.
5. **TIME_STOP same-day MOC 21:40, NEM next-day** — a CC spec §4.1 szerint a TIME_STOP **today 21:40 MOC** (a többi flag next-day 15:30). Implementálva: `evaluate_position_eod` `today` ágon TIME_STOP-ra fut, `close_positions.py --mode=time_stop` 21:40 cron-on. Ez különbözik a HARD/MENTAL/TP/TRAIL-től (azok next-day 15:30 MARKET SELL-lel mennek).
6. **TP1 50% partial → `apply_executed_exit` returns updated SwingPosition** — a TP1 a state-ben **megmarad** (csak `qty_remaining` csökken és `tp1_hit=True`), míg minden más exit teljes zárást jelent (state-ből törölve). Ez a clean lifecycle a 3-day integration smoke teszttel verifikálva.
7. **`format_swing_compact_telegram` pure formatter `src/ifds/output/swing_telegram.py`-ban** — NEM a `scripts/paper_trading/eod_report.py`-ban. A tisztaság miatt: pure formatter (no IO, no IBKR) tisztán test-elhető, és az `eod_report.py` mostani struktúrája lassan átalakul a swing-pattern-re egy későbbi taskban (Task #5 B Tamás manual feloldja). Most a Task #5 A scope: csak a formatter + daily_metrics swing_state field-ek.
8. **`open_positions` wire-up runner.py-ben, NEM külön config-fattens** — a `Config.tuning["swing_execution_enabled"]` flag-re kapcsolt branch a runner.py-ben tölti be a `load_swing_positions(state_file)`-t és konvertálja `to_position_sizing_stub`-bal. Day 1-re üres state → empty list → 12 cap és 30% sector cap is változatlanul fut.

---

## Gotchák / nem nyilvánvaló dolgok

### A) Mac Mini cron-on a Phase 4-6 már 14:30 CEST-kor fut (régi: 22:00)

A régi rendszerben Phase 1-3 (BMI/Universe/Sectors) 22:00-kor futott (`deploy_daily.sh`), Phase 4-6 (Stocks/GEX/Sizing) **15:45 CEST**-kor (`deploy_intraday.sh`). Az új swing-cron Phase 4-6-ot **14:30**-ra előrehozza (1h-val az entry előtt, így a CSV 14:55-re kész). A Phase 1-3 cron időpont (BMI/Universe/Sectors) **változatlan** — vasárnap 22:00 CEST egyszer hetente (új universe + macro snapshot).

### B) `IFDS_SWING_*` orderRef konvenció — NEM ütközik a legacy `IFDS_*`-szal

Az új swing entry-k `orderRef=IFDS_SWING_{sym}` (pl. `IFDS_SWING_NVDA`), a swing exit-ek `IFDS_SWING_{sym}_{action}` (pl. `IFDS_SWING_NVDA_TP1`, `IFDS_SWING_NVDA_TIME_STOP`). A legacy bracket order-ek `IFDS_{sym}_A` / `IFDS_{sym}_B` formátumúak — a `_SWING_` infix tisztán elválasztja.

### C) `_atr_from_row` zero-stop_mult divizió-védelem

A submit `_atr_from_row(t)` `return 0.0`-t ad ha `swing_mental_stop_atr_multiple <= 0`. A SwingPosition `atr=0.0` esetén a trail és TP/SL szintek mind = `entry_price` — ez **logikailag broken**, de **nem crash**. Production-on `swing_mental_stop_atr_multiple=2.0` keményen wired → soha nem trigger-elődik. Egy regression-teszt érdemes lehet erre Phase 4 backteszt-előtt.

### D) `compute_weekly_pnl_pct` nem `weekly`, hanem `since-entry`

A "weekly cumulative P&L" megnevezés kissé félrevezető — a képlet `(today_close - entry_price) * qty_remaining / equity`, ami **a position entry óta** unrealized P&L, NEM az utolsó 7 nap. A -8% HARD_SL kapu így a teljes hold ideje alatti drawdown-ot fedi, NEM a heti rolling-et. Ez **konzisztens a Task #4 spec §4.1**-gyel (`weekly_cumulative_pnl_pct`), de a name shorthand. Ha a Fázis 2 backteszt szigorúbb 7-day rolling-et indokol, az egy Task #6 lesz.

### E) `next_day_planned` listák — `ticker_action` formátumúak

A daily metrics `next_day_planned.exits_at_1530 = ["AAPL_TP1", "MSFT_MENTAL_SL"]` formátumot ad (ticker_action). A Telegram formatter ezt változatlanul printeli — Tamás Mac Mini terminálban manuálisan szét tudja olvasni. Ha a Task #5 B-ben szebb output kell, a `format_swing_compact_telegram` `exits_at_1530` ágában a `_` split-elhető szebb formátumra.

### F) `pt_monitor --mode=eod_eval` Polygon timeout-on idle marad

Ha a Polygon `get_aggregates(...)` `None`-t ad vissza (rate-limit, timeout, ticker delisted), a `ohlc_map`-ben az adott ticker nincs benne, az `evaluate_all_positions` az adott pozíciót **változatlanul** hagyja (next_action a régi marad, jellemzően HOLD). **Nincs forced exit timeout-ra** — ez tudatos: jobb HOLD egy nappal, mint hibás exit-flag. Day N+1-en a Polygon valószínűleg megint válaszol.

### G) `loss_exit_intraday_enabled=False` és `pt_monitor_5min_mode=False` — régi pt_monitor amúgy is nem futna

A régi 5-min pt_monitor.py (clientId=14, 15) a swing cron-ban **nincs ütemezve** (a `0 22 * * 1-5` csak `--mode=eod_eval`-t hív). Az ide kapcsolódó TUNING flagek a defaults.py-ban dokumentációs nature-rel állnak — a Config validator-ja ellenőrzi, hogy mindkét flag False legyen swing mode-ban. Ha valaki manual újra-cron-olja a régi 5-min mode-ot, a `pt_monitor_5min_mode=False` egy assertion-szerű korlát majd Phase N+1-ben (jelenleg csak documentation, NEM runtime guard).

### H) `swing_positions.json` `last_updated` UTC ISO-format, NEM tényleges trade idő

A `save_swing_positions` `last_updated`-je amikor a file-t kiírtuk, NEM amikor az adott pozíció state-je változott. Per-position timestamp egyedi field-ben volna szebb (`next_action_at` van — az **a** specifikus mező a `next_action` set-elésekor). A `last_updated` csak audit/forensic-célú.

---

## Paper Trading (új rendszer, Day 1 = 2026-05-19 kedd)

- **Régi rendszer utolsó futása** péntek 5/16 MOC, 0 nyitott pozíció maradt
- **Day 65/63 (overrun, régi)**: cum. PnL -$1,113.16 (-1.11%) — ezzel a régi paper trading **LEZÁRVA**
- **Új rendszer Day 1**: $100,000 reset (Tamás Mac Mini-n IBKR Account Reset), swing-mode aktív
- **IBKR clientId-k**: submit=10, close=11, eod=12, nuke=13, monitor=14, gateway=17 (változatlan; `pt_monitor --mode=eod_eval` clientId=15 marad)

---

## Blokkolók

- Nincs CC oldali blokkoló. A Task #5 B (Tamás manual) lépéseit Tamás végzi.

---

## Tanulság (sub-pattern — érvényesülő rule példa)

**Test environment higiénia — production state path írás TILOS** (ifds-rules.md 2026-05-10) — érvényesült:
- A Task #4 swing tesztek mind `tmp_path`-be írnak (`save_swing_positions(tmp_path / ".../swing.json", ...)`)
- A Task #5 `_build_swing_state` teszt `monkeypatch.setattr(_loader, "Config", lambda: FakeCfg())` formula a fake Config + tmp_path state_file átirányítást használja
- Egyetlen teszt sem ír a tényleges `state/swing_positions.json`-be

**Új sub-pattern (Ülés C megfigyelés, nem új rule):**

**Az állapot-modul + pure formatter külön választása (Ülés C Döntés 1 + 7).** A `swing_positions.py` (data + logic) és a `swing_telegram.py` (rendering) külön modulok — a state schema változtatása nem érint a Telegram formátumot és vica versa. Ez kontrasztban a régi `eod_report.py` 600+ soros tömbjével, ahol állapot, IBKR, Telegram és CSV-write mind keveredtek. A jövőben (`/replay` vagy `/develop` task előtt) érdemes ezt a pattern-t alkalmazni a `pt_monitor.py` és `eod_report.py` swing-pattern refactor-jánál (egy későbbi Task #6+).

---

## Resume parancs (Tamás kedd 5/19 reggel ~07:00 CEST):

```
/continue

Day 1 swing pivot DEPLOY napja (kedd 5/19).
Ülés C lezárva (Task #4 + #5 A, 1711 tests, 0 regression).

Status: post-deploy verifikáció

Első lépés:
1. git pull origin master
2. pytest baseline (1711 passing kell)
3. docs/journal/2026-05-18-ules-c-handoff.md §B (Tamás manual lépések) ellenőrzés:
   - circuit_breaker.json reset OK?
   - cumulative_pnl.json Day 1 reset OK?
   - IBKR paper $100k reset OK?
   - crontab.md új swing entry-k aktívak?
   - .env minden API kulcs jelen van?
4. ~14:30 CEST: Phase 4-6 cron monitoring (execution_plan.csv 14:55-re)
5. 15:25 CEST: check_gateway.py manual
6. 15:30 CEST: submit_orders.py első Day 1 entry (várt: 0-3 ticker)
7. Telegram megfigyelés (Swing Submit message ~15:31)
8. 22:00 CEST: pt_monitor.py --mode=eod_eval futás (Day 1 mind HOLD várt)
9. 22:05 CEST: eod_report.py (új compact swing template)

Ha Day 1 0 entry-vel kezd, várj 1-2 nap — a Phase 4 PCR + OTM-inverse percentile
threshold S_j > 50.0 + a Phase 6 sector cap a kezdeti kondicionálásnál szigorú lehet.
Day 5-re ~5-8 nyitott pozíció várt (12 cap-ből).
```

---

**Készítette:** Claude Code (Ülés C, 2026-05-18 hétfő este ~21:30 CEST)
**Tester:** 1711 passing, wall clock 4.8s, 0 regression
**Commits:**
- `e887749` feat(execution): swing 15:30 entry + mental stop + daily EOD eval (Task #4)
- `a907060` feat(metrics): swing_state daily metrics + compact Telegram template (Task #5 A)
**Pull-required commits előző session-ökből (Tamás push-olja origin/master-re):**
- `e887749` (Task #4)
- `a907060` (Task #5 A)
- `0c00138` (Ülés B handoff)
- `fc1e573` (Ülés B Task #3 sizing)
- `7012d53` (Ülés A handoff)
- `13e3b3d` (Ülés A Task #2 scoring)
- `50dfb3c` (Ülés A Task #1 universe)
- `77bd180` (Fázis 1 close)
- `d1b2206` (Ülés C journal, korábbi hét)
- `68f6633` (Fázis 1 scoring)

Total: ~10 commit a `git push origin master`-ben Tamás engedélyezése után.
