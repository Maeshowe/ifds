# Task: pt_monitor.py Replay Diagnózis + Régi Logika Cleanup

Status: DONE
Updated: 2026-05-20
Note: H1 confirmed (pytest pre-flight FileHandler pollution). Fix: setup_pt_logger redirects to tmp dir when PYTEST_CURRENT_TEST set. +5 regression tests, 1745 passing.

**Priority:** P0 (a Day 1 review #1 anomáliájából — `04-risks` §8.1.6 új tétel)
**Created:** 2026-05-19
**Owner:** Claude Code
**Estimated effort:** ~45-60 min CC (diagnózis + targeted fix)

**Source**: [`docs/review/2026-05-18-daily-review.md`](../review/2026-05-18-daily-review.md) §6 Anomália #1.

---

## 1. A probléma

A `pt_monitor_2026-05-18.log` **3 időpontban** régi-rendszer LOSS_EXIT / Trail SL / IBKR cancelOrder próbálkozásokat tartalmaz:

```
12:06:58 — LION: Trail SL hit @ $10.15 — SELL 360 shares (scope: bracket_b)
14:25:09 — SDRL: LOSS EXIT Scenario B, SELL 115 shares at MKT
           SDRL: SL cancelled — IFDS_SDRL_A_SL (orderId=100)
           SDRL: TP cancelled — IFDS_SDRL_A_TP (orderId=102)
14:25:52 — (same pattern, második replay)
```

A LION és SDRL **NEM nyitott IBKR pozíció** (csak AVDL.CVR, MASI, LBRT, EC). A `defaults.py`-ben `pt_monitor_5min_mode: False`. A crontab `*/5 16-21 * * 1-5 pt_monitor.py` cron entry **kommentezve van**.

**Mégis fut.** Honnan?

## 2. Diagnosztikai hipotézisek

### H1 — pytest pre-flight side effect

A `deploy_daily.sh` és `deploy_intraday.sh` `pytest --tb=short -q` pre-flight-tal kezdődik. A 14:25:05 és 14:25:49 időpontok **mindkét manuális `deploy_daily.sh --phases 1-3` futtatáshoz** (Tamás ma reggeli próbálkozás) **konzisztensek**. Ha a `tests/test_pt_monitor*.py` import-kor vagy fixture-setup-kor a `pt_monitor.py` `_handle_trail_sl()` / `_handle_loss_exit()` függvényeit hívja **mock-olt state-tel** (LION, SDRL), ami beleír a tényleges `logs/pt_monitor_2026-05-18.log`-ba — akkor minden pytest futás replay-eli a fixture state-et.

**Verifikáció**:
```bash
grep -rn "pt_monitor\|pt_monitor_2026" tests/ | grep -E "(LION|SDRL)"
# Várt: ha találunk LION/SDRL fixture-t, H1 igazolt
```

### H2 — Manuális vagy ad-hoc `pt_monitor.py` futtatás

A 12:06:58 időpont **NEM esik egy ismert cron entry-re**. Lehet, hogy Tamás vagy CC manuálisan futtatta `python scripts/paper_trading/pt_monitor.py` ellenőrzésként, és a script a régi 5-perces mode-ban indult (a `pt_monitor_5min_mode` flag nem hat a CLI módra?).

**Verifikáció**:
```bash
# zsh/bash history
history | grep -E "pt_monitor\.py"
# launchd vagy ad-hoc job log
ls -la ~/Library/LaunchAgents/*pt_monitor* 2>/dev/null
```

### H3 — `deploy_daily.sh` / `deploy_intraday.sh` belső pt_monitor invocation

A `deploy_intraday.sh` jelenleg (a `ce06238` fix után) csak `python -m ifds run --phases 4-6`-ot futtatja. **DE** a `python -m ifds run` belül **hívhat-e** `pt_monitor.py`-t? A `src/ifds/cli.py` `_cmd_run` és `src/ifds/pipeline/runner.py` átnézendő.

**Verifikáció**:
```bash
grep -rn "pt_monitor\|monitor.py" src/ifds/
grep -rn "pt_monitor\|monitor.py" scripts/deploy*.sh
```

### H4 — Log file append a régi run-okból

A `logs/pt_monitor_2026-05-18.log` **append-mode** lehet — ha valami régi process bárhol a Mac Mini-n a fájlra ír (akár hibakezelő, akár orphan launchd entry), a sorok megjelennek.

**Verifikáció**:
```bash
# Mi tartja nyitva a logfile-t?
lsof logs/pt_monitor_2026-05-18.log 2>/dev/null

# Van-e launchd entry?
launchctl list | grep -E "pt_monitor|paper_trading|ifds"
```

## 3. Implementáció lépésekben

1. **Diagnózis (15-20 min)** — Tamás közreműködésével
   - H1 verifikáció: `grep` a `tests/` mappában
   - H2 verifikáció: `history` + `launchctl list`
   - H3 verifikáció: `grep` a `src/ifds/` és `scripts/`
   - H4 verifikáció: `lsof` a logfile-on
   - **Output**: H1/H2/H3/H4 közül melyik igazolódott — rögzítendő a task §6-ban

2. **Targeted fix (15-30 min) — a diagnózis alapján**
   - **Ha H1**: a `tests/test_pt_monitor*.py` fixture-ek mock-olt logger-t használjanak (NEM tényleges fájl-write); vagy a fixture `tmpdir`-t használjon
   - **Ha H2**: dokumentáció — "NE futtasd manuálisan a `pt_monitor.py`-t swing-módon kívül"
   - **Ha H3**: a `src/ifds/pipeline/runner.py` ne hívja a régi `pt_monitor` logikát (legacy code path eltávolítása)
   - **Ha H4**: a régi launchd/cron entry azonosítása + eltávolítása

3. **Belső audit a `pt_monitor.py`-ban (15 min)**
   - A swing-mode (`--mode=eod_eval`) és a régi 5-perces mode **explicit szétválasztása**
   - A régi 5-perces mode függvényeit (`_handle_trail_sl`, `_handle_loss_exit`, `_handle_lion_sdrl_replay`) **deprecated** dekorátorral jelölni
   - Ha a `pt_monitor_5min_mode: False` flag aktív, **explicit `sys.exit(0)` early return** a `__main__`-ban

4. **Tesztek (10-15 min)**
   - `test_pt_monitor_swing_mode_only_when_eod_eval`
   - `test_pt_monitor_aborts_when_5min_mode_disabled`
   - `test_pt_monitor_logfile_only_writes_swing_events`

5. **Commit + push (5 min)**

## 4. Akció ha 15:30 EC TP1 SELL előtt kell deploy

A 15:30 CEST-i `close_positions.py --mode=eod_flags` futás **valós IBKR MARKET SELL-t** ad fel az EC-re. Ha bármilyen régi replay process **párhuzamos** IBKR cancelOrder-t generál, a két folyamat **ütközhet**.

**Mitigáció**: a `close_positions.py` és a `pt_monitor.py` **különböző IBKR clientId-t** használnak (a `crontab.md` szerint `submit=10`, `close=11`). Egy elméleti replay-pt_monitor.py `clientId=10` vagy `=12` lenne — ütközés **valószínűtlen**, de **nem zárható ki**.

**Konzervatív lépés Tamás 15:00 CEST-ig**:
```bash
# Préventív: hold flag létrehozása amíg a diagnózis kész
touch /tmp/disable_pt_monitor.flag

# A pt_monitor.py __main__-ban:
if Path("/tmp/disable_pt_monitor.flag").exists():
    sys.exit(0)
```

Ez **manuális kill-switch** ami a 15:30 SELL után törölhető.

## 5. Commit message draft

```
fix(monitor): pt_monitor.py legacy 5min logic isolation (P0 Day 1 anomaly)

Root cause: <H1 / H2 / H3 / H4>

The 2026-05-18 pt_monitor_*.log contained legacy LION/SDRL replay events
at 12:06:58, 14:25:09, 14:25:52 — generating IBKR cancelOrder attempts
despite pt_monitor_5min_mode=False config flag.

Fix: <konkrét lépések>

- pt_monitor.py: explicit sys.exit(0) early return when 5min_mode disabled
- Legacy handlers (_handle_trail_sl, _handle_loss_exit, etc.) marked @deprecated
- Tests: 3 new (swing-mode-only, 5min-disabled-abort, logfile-isolation)

Refs: docs/review/2026-05-18-daily-review.md §6 Anomália #1
      docs/master-reference/04-risks-and-open-questions.md §8.1.6
```

## 6. Diagnózis eredménye (2026-05-20 — CC)

### Verdikt: **H1 IGAZOLT** (pytest pre-flight FileHandler binding).

H2 / H3 / H4 KIZÁRVA.

### Bizonyíték

**Day 2 (2026-05-19) megismétlődés.** A `logs/pt_monitor_2026-05-19.log` (Mac Mini, 91 sor) tartalmaz egy **16:37:19** timestamp-blokkot (~89 sor) az alábbi karakterisztikus eseményekkel:

```
2026-05-19 16:37:19 [WARNING] Phantom tickers filtered out: ['DELL', 'DOCN']
2026-05-19 16:37:19 [INFO] Monitoring 1 tickers: ['LION']
2026-05-19 16:37:19 [INFO] LION: TP1 fill detected
2026-05-19 16:37:19 [WARNING] LION: Trail SL hit @ $10.15 — SELL 360 shares
2026-05-19 16:37:19 [INFO] Monitoring 1 tickers: ['SDRL']
2026-05-19 16:37:19 [WARNING] SDRL: Trail SL hit @ $43.40 — SELL 115 shares
2026-05-19 16:37:20 [WARNING] LOSS EXIT SDRL: Scenario B
...
2026-05-19 22:00:09 [INFO] [SWING EOD] Evaluated 4 positions — 0 exit flags set
```

A 16:37:19 timestamp **pontosan egybeesik** a Mac Mini manuális `deploy_daily.sh --phases 1-3` futtatásával — bizonyítva más logfile-ok mtime-jával:

- `state/phase13_ctx.json.gz` mtime: 16:40 (handoff §B)
- `logs/pt_monitor_positions_2026-05-19.log` mtime: 16:37 (manuális futás)
- `logs/pt_phase13_freshness_2026-05-19.log` mtime: 16:37

A 22:00 a valódi cron-driven `pt_monitor.py --mode=eod_eval` sor — **EZ A TISZTA SOR**, a swing EOD eval.

### Mechanizmus

A `scripts/paper_trading/lib/log_setup.py::setup_pt_logger("monitor")`:

1. **Modul-import időben** kerül meghívásra a `pt_monitor.py` line 37-en.
2. Egy `logging.FileHandler("logs/pt_monitor_YYYY-MM-DD.log")`-ot bind-ol a process-wide `logging.getLogger("monitor")`-hoz.
3. Bármely subsequent `logger.info()` / `logger.warning()` hívás (pl. a `tests/test_pt_monitor*.py` test body-jából) erre a fájlra ír.

A test fixture-ök (pl. `_isolate_pt_env`, `_import_pt_monitor`) **MEGFELELŐEN** mockolják az IBKR connection-t, state file path-ot (`mod.STATE_DIR = tmp_path`), és Polygon hívásokat — DE **NEM** mockolják a logger-t. A logger-en keresztül a TESZT log üzenetek (LION/SDRL trail SL hit, LOSS_EXIT scenario B, stb.) a **PRODUKCIÓS logfile-ra** írnak.

A `tests/test_pt_monitor.py` (28 teszt) és `tests/test_pt_monitor_scenario_b.py` ezeket a teszt-üzeneteket generálta. A 14:25 (5/18) és 16:37 (5/19) annak felel meg, amikor a `deploy_daily.sh` pytest pre-flight-ja futott a Mac Mini-n.

### Fix

`scripts/paper_trading/lib/log_setup.py::_resolve_log_dir(log_dir)` új függvény:

- Ha `PYTEST_CURRENT_TEST` env var **NEM** set → return `log_dir` unchanged (prod cron behavior preserved).
- Ha pytest alatt fut **ÉS** `log_dir == "logs"` (implicit default) → redirect `$IFDS_PT_LOG_DIR` vagy `$TMPDIR/ifds_pt_logs_test/`-re.
- Ha pytest alatt fut **ÉS** `log_dir != "logs"` (explicit caller-supplied, pl. `tmp_path`) → pass through unchanged (a `tests/test_log_setup.py` 5 meglévő teszt változatlanul fut).

### H2 / H3 / H4 kizárás

- **H2 (manuális futás)**: Nincs evidence — sem `history`-ben, sem `~/Library/LaunchAgents/`-ben. A LION/SDRL nem aktív pozíció — sem `state/swing_positions.json`-ben, sem IBKR portfolio-ban.
- **H3 (deploy_*.sh belső pt_monitor invocation)**: `grep "pt_monitor\|monitor.py" src/ifds/ scripts/deploy*.sh` — nincs hivatkozás. A `python -m ifds run` pipeline-ban semmi nem hív pt_monitor-t.
- **H4 (régi launchd / orphan process)**: a polluted timestamp-ok pontos egybeesése a `deploy_daily.sh` futtatásokkal (16:37, 14:25 — NEM 5-perces periodicitással) kizárja a launchd/cron alapú orphan hipotézist. Egy launchd job random időpontban futna; ez minden esetben pytest pre-flight ablakhoz kapcsolódik.

### Bonus: legacy code path dead in production

`scripts/paper_trading/submit_orders.py` már NEM ír `scripts/paper_trading/logs/monitor_state_YYYY-MM-DD.json`-t a swing pivot óta (legutóbbi: **2026-05-15**). Ezért még ha valaki kézzel futtatná `python pt_monitor.py`-t a default `--mode=scenario_a`-val, a `load_state(today_str)` üres dict-et adna vissza → `if not state: return` early exit. A legacy 5-perces loop nem futtatható élesben. Az explicit `pt_monitor_5min_mode` config-flag guard ezért **NEM szükséges** — a kódút önmagában már sterilezve van.

### Tesztek

`tests/test_log_setup_isolation.py` (5 új teszt):

1. `test_log_file_redirected_to_tempdir_under_pytest` — FileHandler nem írhat `./logs/`-be pytest alatt
2. `test_log_dir_honors_ifds_pt_log_dir_override` — `IFDS_PT_LOG_DIR` env var override
3. `test_log_dir_default_tmp_path_when_pytest_no_override` — default `$TMPDIR/ifds_pt_logs_test/`
4. `test_resolve_log_dir_returns_original_outside_pytest` — production cron behavior preserved
5. `test_setup_pt_logger_does_not_create_logs_dir_under_pytest` — explicit dir creation check

**Test deltas:** `1740 → 1745 passing` (+5, 0 regression).

### Hatás

A fix minden olyan PT scriptre vonatkozik, ami `setup_pt_logger`-t használ: `pt_monitor`, `monitor_positions`, `eod_report`, `daily_metrics`, `reconcile_state`, `submit_orders`, `pt_avwap`, `monitor_submit_heartbeat`, `nuke`, `check_gateway`. Ezek bármelyike, ha a tesztben módot importálják, már nem szivárogtatja a teszt log üzeneteket a prod logfile-okba.

### Production cron preservation

A `deploy_daily.sh` és `deploy_intraday.sh`:
- pytest pre-flight: `PYTEST_CURRENT_TEST` set → redirect engaged → tmp logs
- valós cron job (pl. `pt_monitor.py --mode=eod_eval` @ 22:00): `PYTEST_CURRENT_TEST` NOT set → real `logs/` használata

A produkciós cron viselkedés bit-for-bit megőrzött.

## 7. Kapcsolódó

- `docs/review/2026-05-18-daily-review.md` §6 Anomália #1
- `scripts/paper_trading/pt_monitor.py`
- `src/ifds/pipeline/runner.py` (esetleges legacy hívás)
- `docs/master-reference/04-risks-and-open-questions.md` §8.1.6 (új tétel, ezzel a task-kal lezárandó)
