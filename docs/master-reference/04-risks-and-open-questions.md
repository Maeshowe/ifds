# 04 — Aktív kockázatok és nyitott kérdések

**Utoljára frissítve**: 2026-05-28 (Day 8 — teljes Day 1-8 finding-átvezetés a Log Review chat által, Tamás kérésére. Új P0: P&L tracking gap (§0.11). Új §9 szekció: Day 6-8 finding-ok.)
**Cél**: a swing pivot W21+ aktív backlog tételeit és a strukturális finding-okat tartalmazza, prioritás-sorrendben. **Ezt használd, ha gyorsan akarsz tudni mi a legfontosabb most**.

> **⚠️ AKTÍV P0 (2026-05-28)**: a Day 8 realized P&L tracking gap (§0.11) — a `close_positions.py` exit-jei NEM frissítik a `cumulative_pnl.json`/`daily_metrics`-et. Valódi vs hivatalos cumulative eltérés **$819** (IBKR Net Liq -$779,64 vs daily_metrics +$39,33). Azonnali deploy: `2026-05-26-daily-metrics-auto-update-from-reconcile.md` Rész 3.

> **Korszakváltás (2026-05-14)**: a Day 63 milestone outcome alapján a régi 15-elemű backlog **drasztikusan átalakult**: **6 dropolva** (a swing pivot strukturálisan eliminálja), **4 átalakítva**, **6 új aktív**. A swing pivot 3 fázisú reset roadmap a `docs/decisions/2026-05-14-day63-decision-outcome.md` 6. fejezetében.

---

## 0. ⚠️ P0 — KRITIKUS, AZONNALI AKCIÓ (Day 1 GO-LIVE review)

**Időpont**: 2026-05-18 napi review során azonosítva (Log Review chat). Mindhárom **Day 2 (kedd, 2026-05-19) reggel** kezelendő a Dev chat által, mielőtt a 14:30 CEST cron újra futna.

**Forrás**: [`docs/review/2026-05-18-daily-review.md`](../review/2026-05-18-daily-review.md) — 6. szakasz

### 0.1 ✅ A régi `pt_monitor.py` 5-perces logika "futás"-a (RESOLVED 2026-05-20)

**Státusz**: ✅ RESOLVED — root cause **NEM** legacy 5-perces cron, hanem **pytest pre-flight FileHandler binding pollution**. Fix: `lib/log_setup.py::_resolve_log_dir()` redirect pytest alatt tmp dir-be. Commit: lásd `docs/tasks/2026-05-19-pt-monitor-replay-diagnosis.md` §6.

**Eredeti megfigyelés**: A `pt_monitor_2026-05-18.log` szerint a régi 5-perces monitor logic **3 időpontban** "futott" Day 1-en (12:06:58, 14:25:09, 14:25:52). A `pt_monitor_2026-05-19.log` Day 2-n megismételte ugyanezt (16:37:19). Mindenhol LION/SDRL "Trail SL hit"/"LOSS_EXIT Scenario B"/"IBKR cancelOrder" üzenetek — DE a LION/SDRL NEM aktív pozíció.

**Diagnózis (2026-05-20, CC)**: a `scripts/paper_trading/lib/log_setup.py::setup_pt_logger("monitor")` modul-import időben bind-ol egy `FileHandler`-t a process-wide `logging.getLogger("monitor")`-hoz, ami a **produkciós** `logs/pt_monitor_YYYY-MM-DD.log`-ra ír. A `tests/test_pt_monitor*.py` 28 teszt-je (LION/SDRL state mockokkal) `logger.info()` / `logger.warning()` hívásokat tartalmaz — ezek a hívások a `deploy_daily.sh` pytest pre-flight ablakában a produkciós logfile-ra szivárognak. A 14:25 (5/18) és 16:37 (5/19) bélyegek pontosan egybeesnek a Mac Mini-n manuálisan futtatott `deploy_daily.sh --phases 1-3` időpontokkal — bizonyítva más logfile-ok (pl. `state/phase13_ctx.json.gz`) mtime-jával.

**A legacy 5-min code path élesben halott**: `submit_orders.py` 2026-05-15 óta NEM ír `scripts/paper_trading/logs/monitor_state_YYYY-MM-DD.json`-t (swing pivot átállás). Még ha valaki manuálisan `python pt_monitor.py`-t futtatna `--mode=scenario_a` default-tal, a `load_state(today_str)` üres dict-et adna vissza → early `return`. **Élesben semmilyen pt_monitor 5-perces logika nem futott** — csak a pytest-binding okozott logfile pollution-t.

**Fix**:
- `lib/log_setup.py::_resolve_log_dir(log_dir)` új helper: ha `PYTEST_CURRENT_TEST` set ÉS `log_dir == "logs"` (implicit default) → redirect `$IFDS_PT_LOG_DIR` vagy `$TMPDIR/ifds_pt_logs_test/`-re. Produkciós cron (PYTEST_CURRENT_TEST not set) bit-for-bit változatlan.
- `tests/test_log_setup_isolation.py` (5 új regressziós teszt) verifikálja az izolációt mind a 10+ PT script-re.

**Test deltas**: 1740 → 1745 passing.

**Mérséklő tényező visszaigazolva**: ahogy a Day 1 review feltételezte, **nincs live impact** — a "SELL parancsok" puszta log-szöveg-pollution, nem IBKR API hívás. A test fixture-ök `MagicMock(IB)`-et használtak.

**Másodlagos finding ugyanabból a 16:37 ablakból**: lásd §8.1.7 — a `state/uw_shadow/2026-05-19.json` is overwritten lett ugyanazzal a `_mock_phase4()` AAPL fixture-rel. Ugyanaz a class of bug (unmocked production sink a `tests/test_pipeline_e2e.py::test_full_pipeline_flow`-ban), mint a `d3fce73` Phase 4 snapshot fix-elte volt — csak más fájlon. Külön fix-elve commit-tal.

### 0.2 ✅ `pt_submit` előzetes kísérlet 14:34:13 CEST + Error 10349 TIF (WITHDRAWN 2026-05-28)

**Státusz**: ✅ WITHDRAWN — a Day 4, 5, 7, 8 submit-ok (4/4 nap) mind tiszta 15:31:01+ futási időpontban, NINCS Error 10349 TIF, NINCS pre-market előzetes kísérlet. A §0.4 (Error 354 RESOLVED, `Bypass Order Precautions`) + §0.5 (retry orchestrator) együtt strukturálisan lezárta. A Day 1-i 14:34 pre-market submit egyszeri legacy wrapper artefakt volt (§8.2.4 `deploy_intraday.sh` audit), nem ismétlődött. **Lezárva 4 nap stabil submit után.**

**Mi (eredeti)**: A `pt_submit_2026-05-18.log` szerint **két submit attempt** futott:
- **14:34:13 CEST** — 56 perccel a 15:30 entry előtt. **NEM dokumentált a briefingben**. MASI sikerült, **LBRT és EC `status=Cancelled`** Error 10349 ("Order TIF was set to DAY based on order preset")
- **15:30:02 CEST** — "Skipping LBRT/MASI/EC: already has position or swing state" — vagyis a 14:34 és 15:30 között **mindhárom megnyílt az IBKR-ben**, de **nem világos hogyan** (a 14:34 cancel és a 15:30 skipping között valami történt — silent retry? IBKR async fill? manuális resubmit?)

**Strukturális probléma**: 
1. **Honnan a 14:34-es előzetes submit?** Lehetséges források: (A) `cron_intraday_20260518_143000.log` magában tartalmaz egy submit phase-t, (B) második cron entry crontab-ban, (C) Tamás manuálisan
2. **Error 10349 TIF "DAY" preset hiba**: a 15:30 CEST submit (= 9:30 ET piacnyitás) után a NYSE csak ~6 órát tart nyitva. **A "DAY" TIF preset alapérték NEM kompatibilis** a swing pivot 15:30 entry-időpontjával.

**Akció**: Dev chat vizsgálja meg:
1. A `submit_orders.py` Error 10349-handling és TIF konfigurációt (`config.py` vagy `defaults.py`-ban)
2. A `cron_intraday_*.log`-ot a 14:30-as run-ra (19 KB) — tartalmaz-e submit phase-t?
3. A 14:34-15:30 közötti **silent retry** mechanika dokumentálását vagy eltávolítását (ha nem szándékos)

### 0.3 ⚠️ Phase 2 universe-building TIMEOUT (P1)

**Mi**: A `cron_20260518_142505.log` és `cron_20260518_142549.log` **mindkettő `KeyboardInterrupt`-tal halt el Phase 2-ben**:
- 14:25:05 cron: `_exclude_earnings` futures.as_completed timeout
- 14:25:49 cron: `_exclude_sec_filings` rate-limit sleep timeout

Mindkettő Phase 0-1-et sikeresen lefutott (1711 pytest passed, BMI=52,7% YELLOW LONG), **de Phase 2 universe-building közben halt el** parent-cron timeout miatt. A sikeres futás a `cron_intraday_20260518_143000.log`-ban (19 KB) van.

**Strukturális probléma**: A Phase 2 universe-building (earnings exclusion + SEC EDGAR 10-Q lookup) **lassú** — a SEC EDGAR rate-limit sleep + futures.as_completed várás összesen **> 60s** lehet, ami a parent-cron timeout-ját túllépi.

**Akció**: Dev chat vagy:
1. Emelje a Phase 2 timeout-ot a crontab parent-job-ban
2. Optimalizálja a `sec_edgar.py:_http_get_json` rate-limit logikát
3. Csökkentse a Phase 2 work futures concurrency-jét

### 0.4 ✅ Day 3 IBKR Error 354 — new-ticker market data block (RESOLVED 2026-05-20 19:00 CEST)

**Státusz**: ✅ RESOLVED — Tamás bekapcsolta az IBKR TWS Global Configuration → **API → Precautions** → **"Bypass Order Precautions for API Orders"** beállítást. 1-share VLO live smoke test (clientId=18, `/tmp/ibkr_debug_submit.py`) **t=1.0s status=Filled @ $254.08**, semmilyen Error 354 vagy TIF warning. Cleanup: SELL 1 share @ $253.19 (P&L -$0.89 negligible). Final reconcile_state.py: state ≡ IBKR mind a 7 ticker-en.

**A pontos beállítás helye** (a Day 4+ session-höz):
- TWS/Gateway → File → Global Configuration → **API → Precautions** szekció (NEM a Presets → Stocks → Precautionary Settings, ami numeric Price Percentage / Size Limit guard, NEM market data block).
- **Az első checkbox**: "Bypass Order Precautions for API Orders" → enable + Apply + OK.
- Hatás: minden API-ról jövő order (clientId=10 submit_orders, clientId=11 close_positions, stb.) bypass-olja az IBKR paper account összes Order Precaution-jét — beleértve a "no market data" Error 354 block-ot.
- A többi API → Precautions checkbox (Bond warning, negative yield, called bond, same action pair, price-based volatility, redirect order, overfill, route marketable) **nem szükséges** a swing pivot use-case-hez.



**Időpont**: 2026-05-20 (Day 3 swing pivot) 15:31 CEST cron-driven submit + 16:05/16:20 CEST manual retry-k.

**Forrás**: `logs/pt_submit_2026-05-20.log` + `/tmp/ibkr_debug_submit.py` diagnostic.

**Mi**: a `submit_orders.py` (Day 3 cron + 3 manual retry) **silenty failed** a 3 új ticker submit-ján (VLO 16, ON 27, CNC 95). A 4 régi ticker (LBRT/MASI/EC/PFGC) érintetlen az IBKR-ben. Igazi ok: **IBKR Error 354** — "trying to submit an order without having market data for this instrument. Restriction is specified in Precautionary Settings of Global Configuration/Presets."

**Diagnosis paranormálitás**: a `submit_orders.py` status check 1.5s-cel a placeOrder után PreSubmitted-et lát (valid) → state-be írja a 3 position-t + Telegram heartbeat-et küld → DE az IBKR async cancel-li post-disconnect → state=7, IBKR=4 divergencia.

**Hamis nyomok kizárva**: Error 10349 (TIF preset) csak warning, nem cancel reason. A 16:05-i `tif='GTC'` + 16:20-i `tif='DAY'` patch-ek mindkettő ugyanezt a 354-et okozta → kód-level fix önmagában NEM elég.

**Day 1+2 vs Day 3 különbség**: a swing-pivot előtt `lib/orders.create_swing_bracket` MarketOrder-PARENT + OCA bracket-et küldött. A paper account a parent-et silenty fillelte Error 354 ellenére (bracket override quirk — `04-risks` §0.1 magyarázat: ott "phantom fill" mint operatív megfigyelés). A swing-pivot `submit_swing_market_only` bare MarketOrder bracket nélkül → nincs OCA override mechanizmus → Error 354 valódi cancel.

**Workaround (alkalmazva Day 3-on)**:
1. Tamás manuálisan adta fel a 3 BUY MKT order-t az IBKR TWS Workstation Order Entry-n. A GUI csak interaktív "no market data" warning-ot ad → Override + Submit → fillodott (actual fills: VLO@$258.55, ON@$109.48, CNC@$59.27).
2. State revert (7→4) + manual append a 3 új SwingPosition-nel + entry_price update az actual IBKR fill árakra + stop/TP recompute (2.0×ATR / 1.5×ATR / 3.0×ATR Day 1 reconstruction pattern szerint).
3. `reconcile_state.py` post-fix smoke: silent OK (state ≡ IBKR mind a 7 ticker-en).

**Code commits a Day 3 incident során** (mind merged, NEM elégséges önmagukban a 354 ellen):
- `3bf382b` — `submit_orders.py` `tif='GTC'` + `outsideRth=True` (helytelen — GTC invalid for MarketOrder)
- `e3677f2` — `tif='DAY'` korrekció (still hits Error 354)

**Permanent fix backlog**: lásd `docs/tasks/2026-05-21-ibkr-error354-market-data-fix.md`. Két opció:
- **A)** IBKR Workstation **Global Configuration → Presets → Precautionary Settings → "Block submitting orders without market data" DISABLE**. Tamás manuálisan kell, hogy beállítsa. Globális hatás, nincs kód-változás.
- **B)** Code patch: `ib.reqMktData(contract)` warm-up a `placeOrder` ELŐTT a `submit_swing_market_only`-ban. Risk: ha a paper account NEM ad streaming subscription-t, ez sem segít.

**Strukturalis konzekvencia**: minden új-ticker entry (Day 4+ universe rotation alapján) ugyanúgy blokkolva lesz Error 354-gyel, amíg a (A) opció nem áll. **Tamás holnapi (Day 4, 2026-05-21) cron előtt teljesítse az (A) opciót**, máskülönben azonnali manual Workstation submit kell minden új ticker-re.

**Hatás összegzés**:
- ✅ Day 3 swing entry-k: VLO 16, ON 27, CNC 95 fillodtak (manual Workstation)
- ✅ State ≡ IBKR (7 position match)
- ⚠️ Permanent fix BACKLOG (Task #I, holnap reggel)
- ⚠️ A cron-driven submit ma 15:31-kor csendben failed, NEM detektálódott time-wise (csak Telegram heartbeat 15:45-kor jelzett "STUCK")
- ✅ **Follow-up (2026-05-21)**: a "csendes failure → manual intervention required" mintát az `IBKRSubmitOrchestrator` autonóm outer-retry framework lezárja (lásd §0.5).

**Owner**: CC (W22 hotfix, 2026-05-21 reggel) + Tamás (IBKR Workstation manual setting).

**Referencia**:
- Task fájl: `docs/tasks/2026-05-21-ibkr-error354-market-data-fix.md`
- Diagnostic script: `/tmp/ibkr_debug_submit.py` (1-share VLO test, captured Error 354)
- Submit log: `logs/pt_submit_2026-05-20.log` (15:31 + 15:52 + 16:05 + 16:20 attempts)
- Manual fills: VLO@$258.55 (-1.55% slip), ON@$109.48 (+3.26% slip), CNC@$59.27 (+0.20% slip)
- State backup chain: `state/swing_positions.json.bak.*` (4 backup, audit trail)

### 0.5 ✅ Day 3 submit retry storm — autonomous orchestrator deployed (RESOLVED 2026-05-21)

**Státusz**: ✅ RESOLVED — Task #L (`docs/tasks/2026-05-21-submit-retry-storm.md`) végrehajtva. A 2026-05-20 Day 3-i 15:31 CEST cron submit_orders failure — amelyik a Gateway-down ablakban (15:25-16:00) `sys.exit(1)`-gyel megszakadt — most autonóm outer-retry orchestrator kezeli.

**Mi**: a `submit_orders.py` jelenleg az IBKR connection elérhetetlenkor 3× belső retry-t csinált (`lib/connection.py:CONNECT_MAX_RETRIES=3`, 5s delay), majd `sys.exit(1)`. Ha a Gateway azon a 30 másodperces ablakon belül DOWN volt (Day 3-i 15:25-16:00 outage), nem volt további próbálkozás — manual operator intervention required.

**Fix architektúra**:
- **`scripts/paper_trading/lib/retry_orchestrator.py::IBKRSubmitOrchestrator`** — wrapper class outer-retry-jal. 5 attempt × exponential backoff (15s → 30s → 60s → 120s → 240s, total ~7.75 min). Minden attempt-nél: cheap gateway probe → ha down, backoff; ha alive, submit_callable hívás (ami belül `connect(raise_on_exhaust=True)`-tal csatlakozik).
- **`lib/connection.py`** — új `IBKRConnectionExhausted` exception + `raise_on_exhaust` kwarg a `connect()` függvényen. Backwards-compatible: minden caller default behaviour `sys.exit(1)`; csak a submit_orders.py kapcsolja be `raise_on_exhaust=True`-ra.
- **`submit_orders.py::main()`** — `--resume` CLI flag (manual retry trigger Telegram alert után) + orchestrator hívás + `SubmitExhaustedError` catch → `sys.exit(1)`.
- **`monitor_submit_heartbeat.py`** — STUCK threshold 300s → 900s. Az orchestrator outer-retry budget (max ~12 perc) NEM trippeli a heartbeat duplikált STUCK alert-jét.

**State-aware deduplication**: minden outer attempt-en a submit_callable belül friss `load_swing_positions()` + `get_existing_symbols(ib)` hívást indít (a meglévő `existing_swings` + `existing` szűrés alapján). Nincs double-submit risk — egy nehéz Gateway-down forgatókönyvben, ahol az 1-2 ticker fillodott egy belső attempt-en de a connection drop előtt, a következő outer attempt csak a hiányzó tickereket próbálja meg.

**Telegram alerting kétoldalú**:
- Inner connect failure (lib.connection): IBKR CONNECTION FAILED alert (mint eddig, változatlan)
- Outer all-retries-exhausted (orchestrator): SUBMIT EXHAUSTED alert + manual resume hint (`submit_orders.py --resume`)

A heartbeat 900s threshold csak akkor trippel, ha a teljes outer-retry budget se sikerül (~12 min) — ez a duplikált alert-prevencion belül.

**Tests**: `tests/test_retry_orchestrator.py` 9 új unit teszt (happy path, retry success, exhausted+Telegram, non-retryable propagate, gateway probe gating, backoff schedule, state reload, telegram failure non-blocking). **1747 → 1756 passing, 0 regression**.

**Hatás Day 4+ trading deploy-ra**:
- Gateway-down 5-12 perces ablakok **autonóm módon kezelve** — operator NEM kap STUCK alert-et, csak ha az outer-retry is exhausted
- Live trading deploy-nál (Day 126+) **éjjel-nappal manual intervention NEM szükséges** a típikus Gateway outage-okra
- A failure mode tisztán dokumentált: SUBMIT EXHAUSTED Telegram → operator `--resume` parancs vagy infrastructure investigation

**Referencia**:
- Task fájl: `docs/tasks/2026-05-21-submit-retry-storm.md` (Status: DONE)
- Új module: `scripts/paper_trading/lib/retry_orchestrator.py`
- Új exception: `lib/connection.py::IBKRConnectionExhausted`
- Tesztek: `tests/test_retry_orchestrator.py` (9 új)
- Day 3 incident timeline: `logs/pt_submit_2026-05-20.log` (15:31 cron failure + 5 manual retry/diagnostic)

### 0.10 ⚠️ State ≡ IBKR desync — Tamás Day 3-i manuális TWS bracket-jeinek autonóm trigger-je (PARTIAL RESOLVED 2026-05-28)

**Státusz**: 🔶 PARTIAL RESOLVED — a **monitoring réteg (Rész 1) DEPLOY-OLVA** (commit `5c8e79a`) és **2/2 napon ÉLESEN validálva** (Day 7 + Day 8 `_reconcile_state_from_ibkr` → SILENT OK, state ≡ IBKR). A Day 6 reggeli CNC bracket cancel óta NINCS autonóm IBKR bracket — a mental-stop architektúra integritása megerősítve. **DE a logging réteg (Rész 3) hiánya P0 KRITIKUS — lásd §0.11.** Task: [`docs/tasks/2026-05-23-state-reconciliation-from-ibkr.md`](../tasks/2026-05-23-state-reconciliation-from-ibkr.md).

**Day 7-8 update (2026-05-28)**: a Rész 1 (`pt_monitor.py::_reconcile_state_from_ibkr`) az ELSŐ (Day 7) és MÁSODIK (Day 8) éles futáson is SILENT OK — `pt_reconcile_{date}.log` mindkét napon "match (silent exit)". A monitoring strukturálisan működik. A Rész 2 (retroaktív Day 4-5 reconcile) lefutott. **A Rész 3 (daily_metrics/cumulative_pnl auto-update az exit-ekből) MÉG NINCS deploy-olva** → ez okozza a §0.11 P0 tracking gap-et.

**Mi (helyesbített magyarázat)**: A `submit_orders.py::submit_swing_market_only` kódja explicit: `# Single market BUY (no bracket).` (Day 63 §3.12). A swing pivot architektúra **MENTAL-STOP módban van** (helyes, ahogy a design doc írja) — NINCS autonóm IBKR bracket order a cron-driven 7 entry-re (LBRT, MASI, EC, PFGC, WMB, DXCM, AMH; orderRef `IFDS_SWING_{sym}`).

**A Day 4-5 autonóm bracket-trigger-ek forrása**: a Day 3-i §0.4 (IBKR Error 354 RESOLVED) workaround során Tamás **manuálisan adta fel** a VLO/ON/CNC ticker-eket az IBKR TWS Workstation Order Entry-n a TWS GUI bracket template-jével. Ezek a manuális TWS bracket-ek **planned-alapú szintekkel** kerultek be (a `pt_submit_2026-05-20.log` `stop $XX | TP1 $YY` ertékeivel), és **autonóm módon triggereltek** Day 4-5-en. ORDER_REF ÜRES (NEM `IFDS_*`), mert TWS GUI-ból manuálisan generált.

**Felfedezés forrása**: 2026-05-23 szombat reggeli IBKR TWS Trades + Positions + Orders képek elemzése (Log Review chat). Két autonóm bracket trigger felfedezve:

| Nap | Ticker | Trigger típus | Fill ár | Net P&L | Hivatalos `daily_metrics` | Forrás |
|-----|--------|---------------|---------|---------|---------------------------|---------|
| Day 4 (2026-05-21) | VLO | SL bracket 19:19:54 CEST | $244,61 | **-$227,06** | $0 ⚠️ | Tamás manuális Day 3 TWS bracket |
| Day 5 (2026-05-22) | ON | TP1 bracket 16:40:20 CEST | $115,41 | **+$159,12** | $0 ⚠️ | Tamás manuális Day 3 TWS bracket |

**Bracket level-ek a PLANNED entry-alapúak** (mert Tamás a TWS GUI-ban a planned-szinteket írta be). Példa: Day 3 VLO planned entry $262,62 → tényleges fill $258,55 (-1,55% slippage), de a manuális TWS bracket SL **$244,71-en maradt** (planned-alapú). A Day 4 SL trigger fill $244,61 = $0,10 a planned-alapú stop alatt. Az ON esetében: Day 3 ON planned $106,02 → filt $109,48, manuális TWS TP1 $115,41-en. Day 5 TP1 trigger $115,41 EXACT match.

**3 rétegű struktúra** (helyesbítve):
1. **Architektúra**: a swing pivot **HELYESEN mental-stop módban van** (a design doc szerint). A Day 4-5 trigger-ek **NEM a `submit_orders.py` viselkedése**, hanem Tamás Day 3-i manuális TWS bracket-jének autonóm mellékhatása.
2. **Monitoring-szintű**: `pt_monitor.py` nem hív `ib.positions()` vagy `ib.executions()` API-t a 22:00 EOD eval-ban → az autonóm bracket trigger-ek lokálisan láthatatlanok. **Ez egy valódi strukturális monitoring hiány**, függetlenül a Day 3-i manuális TWS bracket-ektől.
3. **Logging-szintű**: a `daily_metrics.pnl` realized-only és **nem tartalmazza** a bracket trigger-eket. A `cumulative_pnl.json daily_history.tp1_hits/sl_hits/tp2_hits` mezők **soha nem voltak update-elve** (még a Day 2-i EC TP1 fill-re sem, ami `IFDS_SWING_EC_TP1` order ref-fel logolt). **Strukturális, régóta fennálló logging bug**, független a Day 3-i manuális TWS bracket-ektől.

**W21 hatás** (a hivatalos $107,27 vs tényleges):

| Mutató | Hivatalos | Tényleges (IBKR alapján) |
|--------|-----------|--------------------------|
| Realized P&L | +$107,27 | **+$42,63** |
| TP1 hits | 0 | **2** (Day 2 EC + Day 5 ON) |
| SL hits | 0 | **1** (Day 4 VLO) |
| Open positions Day 5 záró | 10 | **8** (VLO és ON zárva) |
| Net Liq Day 5 záró | n/a | **$99 960,50** → -$39,50 a $100k baseline-ról |

**Tamás Day 6 reggeli manuális akció**: a CNC élő TWS bracket (Stop $55,50 + Limit $61,89 GTC) **manuálisan cancellálva** 2026-05-25 08:26 CEST-kor (IBKR Orders ablak megerősíti: 2 × Cancelled). **Többé NINCS autonóm bracket order az IBKR-ben** — a teljes 8-pozíciós portfolio mental-stop módban van.

**Hatás a Day 7+ napokra**: Day 7 (kedd 2026-05-26) reggel újra fut a pipeline. **Ha a state reconciliation NEM deploy-olt addig**, a `submit_orders.py` Day 7-en a VLO és ON ticker-eket "already has position or swing state" miatt skipping-elné, miközben az IBKR-ben mindkettő zárva van. Téves duplikáció-szűrés.

**Akció (α opció — hibrid status quo, Tamás döntése 2026-05-25)**: lásd `docs/tasks/2026-05-23-state-reconciliation-from-ibkr.md` (3 részes scope):
1. **State reconciliation** a `pt_monitor.py` 22:00 EOD eval-ba: `ib.positions()` + `ib.executions()` query, autonóm bracket trigger detect, state update
2. **Retroaktív Day 4-5 reconcile** (egyszeri script): a hiányzó -$227 és +$159 utólagosan rögzítése a `daily_metrics` és `cumulative_pnl`-ben
3. **TP1/SL/TP2 hit counter fix**: a `cumulative_pnl.json daily_history` hit-mezők frissítése Day 2 (EC TP1), Day 4 (VLO SL), Day 5 (ON TP1) számára

**NINCS architektúra-váltás szükséges** — a swing pivot már helyesen mental-stop módban van. A design doc és a Day 1 prezentáció NEM kell frissíteni.

**Owner**: CC (W21+ azonnali deploy, Day 7 reggelére)

**Referencia**:
- Task fájl: [`docs/tasks/2026-05-23-state-reconciliation-from-ibkr.md`](../tasks/2026-05-23-state-reconciliation-from-ibkr.md)
- Day 4 review §9: [`docs/review/2026-05-21-daily-review.md`](../review/2026-05-21-daily-review.md)
- Day 5 review §9 + W21 reconciled summary: [`docs/review/2026-05-22-daily-review.md`](../review/2026-05-22-daily-review.md)
- IBKR Trades log forrás: 2026-05-23 reggeli TWS screenshot-ok (Last 6 Days)
- Tamás manuális TWS bracket cancel megerősítés: 2026-05-25 08:26 CEST TWS Orders ablak
- A `submit_swing_market_only` kódja: `scripts/paper_trading/submit_orders.py` line ~250-330

### 0.11 ⚠️⚠️ Realized P&L tracking gap — a `close_positions.py` exit-jei nem frissítik a metrikát (ÚJ P0, felfedezve 2026-05-28 Day 8)

**Státusz**: ⚠️ OPEN, P0 KRITIKUS — azonnali deploy: `docs/tasks/2026-05-26-daily-metrics-auto-update-from-reconcile.md` Rész 3.

**Mi**: A Day 8-on (2026-05-27) **7 exit** történt az IBKR-en (EC TP2 + 6 TIME_STOP MOC), összesen **-$695,77 realized P&L**-lel. Sem a `cumulative_pnl.json`, sem a `daily_metrics/2026-05-27.json` NEM rögzítette — mindkét fájl `pnl: 0`, `exits: mind 0`.

| Forrás | Day 8 P&L | Cumulative |
|--------|-----------|-----------|
| `daily_metrics` + `cumulative_pnl.json` | **$0** | **+$39,33** |
| **IBKR (kanonikus, `get_account_trades`)** | **-$695,77 realized** | **-$656,44** (realized) |
| **IBKR Net Liq (`get_account_summary`)** | -$428,77 | **-$779,64** |

**A hivatalos tracking $819-cal felüljelez.**

**Root cause**: a `close_positions.py` (TP2/MOC/SL exit) végrehajtja az IBKR SELL-t és frissíti a state-et (10→4 pozíció ✓), DE NEM ír a `cumulative_pnl.json`/`daily_metrics`-be. A realized P&L tracking lánc megszakad az exit oldalon. Ez a §0.10 **Rész 3** hiányának közvetlen következménye.

**Miért rögzült a Day 2-5, de a Day 8 nem**: a Day 2-5 exit-eket a §0.10 Rész 2 (egyszeri retroaktív reconcile script, 2026-05-25) rögzítette utólag. A Day 8-i exit-ek MOST történtek, és a Rész 3 (folyamatos auto-update) hiányában nem rögzültek. **Minden jövőbeli TIME_STOP/TP2/SL exit ugyanígy láthatatlan marad, amíg a Rész 3 nem áll.**

**Fontos önkorrekció**: a Day 7 review a §0.10-et P0→P1-re downgrade-elte ("a logging csak retroaktív audit-trail-t érint"). A Day 8 ezt MEGCÁFOLJA — a teljes napi -$696 realized eltűnt, ami operatívan kritikus. **Vissza P0-ra.**

**Hatás**:
- A `cumulative_pnl.json` és `daily_metrics` jelenleg MEGBÍZHATATLAN a valódi teljesítmény szempontjából
- A Day 21 checkpoint (-$1 500 küszöb) értékelése lehetetlen pontos tracking nélkül (valódi -$779,64 vs hivatalos +$39,33)
- Az IBKR direkt kapcsolat ideiglenesen betlölti a gap-et (a daily review-k mostantól IBKR Net Liq + trades alapon számolnak)

**Akció**:
1. A `2026-05-26-daily-metrics-auto-update-from-reconcile.md` (Rész 3) AZONNALI deploy — `close_positions.py`-be P&L write a TP2/MOC/SL exit-ek után
2. Retroaktív Day 8 reconcile: -$695,77 + commission rögzítése
3. **Day 1-8 canonical P&L rekonstrukció** az IBKR `get_account_trades(DAYS_30)`-ból (a valódi tracking tábla a `docs/tasks/2026-05-28-automated-daily-review-pipeline.md` §5-ben)

**Owner**: CC (P0, azonnali) + Tamás (deploy jóváhagyás)

**Referencia**:
- P0 finding teljes diagnózis: [`docs/review/2026-05-27-daily-review.md`](../review/2026-05-27-daily-review.md) §0
- Blokkoló task: `docs/tasks/2026-05-26-daily-metrics-auto-update-from-reconcile.md` (Rész 3)
- Canonical P&L tábla: `docs/tasks/2026-05-28-automated-daily-review-pipeline.md` §5

---

## 1. P1 — Sürgős, Fázis 1 (W21-W22) deploy



### 1.1 IBKR Gateway monitoring + Telegram alert ⭐ OPERATIONAL RISK

**Mi**: 2026-05-11 16:20 CEST — az IBKR Gateway elérhetetlen volt (timeout × 3 retry), a `submit_orders.py` failelt. Tamás 55 perccel később (17:15 CEST) vette észre, kézi rögzítés.

**Miért P1**:
- A jelenlegi rendszer **nem riasztja Tamást**, ha az IBKR Gateway leáll a 16:20-i submit-időpontban.
- Egy másik IBKR-akadás esetén a rendszer **csendben hibázhat** — Tamás csak EOD-időpontban (22:00 körül) látja.
- **Swing-architektúrán is releváns**: a 15:30 CEST entry-időnél is ugyanaz a kockázat.

**Megoldás**: a `submit_orders.py`-be IBKR connection failure detection + Telegram bot értesítés (meglévő Telegram bot infrastruktúra).

**Effort**: ~1 óra CC + 2-3 unit teszt

**Owner**: CC (W21+ azonnali deploy)

**Státusz**: ✅ DONE 2026-05-16 (CC Ülés A, Fázis 1 W21 close). Telegram WARNING anti-pattern fix + heartbeat (Fix C) deploy-olva. A 2026-05-11-i csendes failure root cause-a azonosítva (H1: `_send_telegram_alert` `except Exception: pass` minta), 2026-05-18 sikeres pre-market verifikáció.

**Forrás**: [`docs/review/2026-05-11-daily-review.md`](../review/2026-05-11-daily-review.md)

**Implementáció**: [`docs/tasks/2026-05-15-ibkr-gateway-monitoring.md`](../tasks/2026-05-15-ibkr-gateway-monitoring.md)

### 1.2 10-Q SEC Filing Exclusion + 10 napi earnings exclusion bővítés ⭐ SWING-EN KRITIKUSABB

**Mi**: AGNC 2026-05-04 — 10-Q SEC filing event 17:21 CEST, **NEM** earnings release, így a 7 napos earnings exclusion nem zárta ki. Eredmény: -$380 6-split LOSS_EXIT.

**Miért P1 a swing-en (REWORKED)**:
- A 7 napos earnings exclusion már **nem elégséges** swing horizonton (5 napi hold)
- **Új keret**: 10 napi earnings exclusion (hold × 2 buffer) + 10-Q SEC filing exclusion
- A jelenlegi earnings-szűrő nem fedi le a 10-Q / 10-K SEC filing event-eket

**Megoldás**:
1. `defaults.py`: `earnings_exclusion_days: 7 → 10`
2. SEC EDGAR API integráció — 10-Q és 10-K filing dátumok lekérdezése
3. Phase 2 universe-ből kizárás 10 napi előretekintéssel

**Effort**: ~2-3 óra CC

**Owner**: CC (W21+ azonnali deploy)

**Státusz**: ✅ DONE 2026-05-16 (CC Ülés B, Fázis 1 W21 close). `earnings_exclusion_days: 7 → 10` config change deploy-olva, SEC EDGAR API integráció 1611-ticker live smoke 100% success, 0 HTTP 429. Tolerancia ±10 nap, failure mode (C) cache → (A) fail-open.

**Implementáció**: [`docs/tasks/2026-05-15-earnings-exclusion-7to10.md`](../tasks/2026-05-15-earnings-exclusion-7to10.md), [`docs/tasks/2026-05-15-sec-10q-exclusion.md`](../tasks/2026-05-15-sec-10q-exclusion.md)

---

## 2. P2 — Fázis 2 analitikus + design (W23-W24)

### 2.1 Entry timing optimalizáció backtest ⭐ A SWING PIVOT KVANTITATÍV MEGALAPOZÁSA

**Mi**: A jelenlegi 16:20 CEST entry-idő strukturálisan a reggeli rally peak-jére esik. A swing pivot 15:30 CEST entry-t javasol (market open). **Kvantitatív validáció szükséges**.

**Megoldás (analitikus, NEM kód deploy)**:

Backtest a 60+ napi adaton 4 hipotetikus entry-időablakkal:
- 15:30 CEST (market open = 09:30 ET) — **az új javasolt**
- 16:20 CEST (jelenlegi = 10:20 ET)
- 17:15 CEST (= 11:15 ET, reggeli profit-taking utáni)
- 18:30 CEST (= 12:30 ET, lunchtime drift)

Minden ticker × minden hipotetikus entry-időpontra:
1. Visszaszámolni a hipotetikus entry-árat (Polygon 1-min bars)
2. Újrakalkulálni a P&L-t (a tényleges exit-tel)
3. Aggregátum analízis: melyik időablak ad a legjobb total P&L-t, a legkisebb LOSS_EXIT triggerelést, a legjobb excess vs SPY-t

**Várt eredmény**: az 15:30 entry előnyét kvantitatívan validálja, vagy más optimumot talál.

**Effort**: ~1-2 óra Chat-oldali

**Owner**: Chat (Fázis 2, W23)

**Forrás**: [`docs/review/2026-05-12-daily-review.md`](../review/2026-05-12-daily-review.md) — "ENTRY TIMING HIPOTÉZIS" + Tamás javaslata

### 2.2 M_contradiction sign-flip vizsgálat

**Mi**: 7 napos M_contradiction LIVE iránybeli helyesség: **33%** (2 ✓ + 4 ✗ a 6 fired esetből). **Rosszabb mint random**. A "double jeopardy" minta (FORM máj 11, CENX máj 12) megerősíti.

**Hipotézis**: a sign-flip ($M_c = 1.2 \times$ a $0.8 \times$ helyett) lehet, hogy pozitív expectancy-t ad. **Kvantitatív backtest szükséges**.

**Megoldás (analitikus)**:
- A 60+ napi adat összes M_contradiction fired esetére: ha sign-flippelt ($M_c \to 1.2$), mennyi lett volna a P&L?
- Bayes-faktor a sign-flip vs deaktiválás vs status quo között
- Döntés: (A) sign-flip, (B) deaktiválás ($M_c = 1.0$), (C) Status quo (status: alulvizsgált)

**Effort**: ~1 óra Chat-oldali

**Owner**: Chat (Fázis 2, W23)

### 2.3 TP1 cél revízió (új swing TP-struktúra)

**Mi**: A régi `tp1_atr_multiple: 1.25` swing horizonton **újrakalibrálandó**. A swing pivot új struktúrája:
- **TP1**: +1.5× ATR (~+4-5%) → 50% qty zárás, trail SL felfelé
- **TP2**: +3.0× ATR (~+8-10%) → maradék 50% zárás
- **SL (mental)**: -2.0× ATR (~-5-6%) — overnight gap buffer

**Megoldás**: `defaults.py` config update + scoring-független TP/SL logika a swing architektúra design dokban.

**Effort**: ~30 min config + ~1 óra CC unit teszt

**Owner**: CC (Fázis 2 design → Fázis 3 deploy)

### 2.4 Dinamikus pozíciószám — rolling 10-12, 0.35% risk

**Mi**: A 2026-04-11-i 13 pontos terv #7 javaslata — **dinamikus pozíciószám**. A swing pivot keretében az új paraméterek:
- Risk per position: **0.35%** ($350)
- Concurrent positions cap: **12 (steady state ~10)**
- Daily new entries: **2-3** (NEM kötelező napi 3-5)

Ha nincs minőségi flow signal egy adott napon, **NEM kereskedünk**. A "csak ha érdemes" filozófia.

**Indoklás**: a swing-en a 10-12 concurrent miatt a jelenlegi 5 fix napi entry **túl agresszív**.

**Megoldás**: `defaults.py` config + Phase 6 sizing logika átalakítás.

**Effort**: ~1 óra CC

**Owner**: CC (Fázis 3 deploy)

---

## 3. P3 — Fázis 3 vagy később

### 3.1 ADR earnings adatforrás fix

**Mi**: BUD 2026-05-05 — ADR earnings event, az FMP `/stable/earnings?symbol=BUD` **NEM tartalmazta** a 2026-05-05 dátumot. **5-10 hasonló eset** mehetett le észrevétlenül a 60 napi adatban.

**Megoldás (kombinált)**:
- (A) Polygon `tickers/{ticker}/events` — jobban lefedi ADR-eket
- (D) Hard-coded ADR blacklist konfig — top 50-100 ADR earnings dátum manuális tracking

**Effort**: ~3-4 óra CC

**Owner**: CC (Fázis 3, W25-W26 között)

### 3.2 Breakeven Lock profit-küszöb (swing-integrált)

**Mi**: A régi "Breakeven Lock" mechanizmus profit-trigger ~+1% felett aktivál. A swing TP/exit struktúrában a profit-küszöb integrálandó.

**Megoldás**: a swing exit logika design fázisban (Fázis 2) eldől.

**Effort**: ~30 min config (a design után)

**Owner**: CC (Fázis 3 deploy)

### 3.3 Phase 4 snapshot enrichment

**Mi**: A jelenlegi `state/phase4_snapshots/` csak a winner ticker-eket menti. A teljes ticker tábla mentése javasolt a Bonferroni-szignifikáns flow al-komponensek (PCR, OTM-inverse) longitudinális elemzéséhez.

**Megoldás**: Phase 4 snapshot logika módosítás — minden ~250-300 ticker mentése scoring táblával.

**Effort**: ~30-45 min CC + 3-4 unit teszt

**Owner**: CC (Fázis 3 deploy, az új scoring-gal párhuzamosan)

---

## 4. DROPPED — a swing pivot által strukturálisan eliminált backlog

A korábbi 15 backlog idea közül **8 dropolt**:

| # | Eredeti backlog | Drop indoklás |
|---|---|---|
| 1 | **LOSS_EXIT bracket SL cancellation** (4 instancia bug) | Mental stop architektúra strukturálisan eliminálja a bracket-rendszert |
| 2 | `nuke.py --orders` scope expansion | NINCS bracket order swing-en, `--positions` elég |
| 3 | UW rate limit kezelés finomítás | UW shadow log, scoring-ban deaktiválva (Day 90 audit) |
| 4 | LOSS_EXIT küszöb finomítás per-ticker ATR | Mental stop architektúra |
| 5 | dp_pct fallback default (universum-medián) | UW scoring-ban deaktiválva |
| 6 | Slippage-adjusted scoring validation | Új scoring eleve slippage-szembesített |
| 7 | High-score liquidity check | A "magas pontszám paradoxon" a scoring revízión át kezelendő (Bonferroni-minimum) |
| 8 | monitor.py belső replay események jelölése | Alacsony prioritás, későbbi |

**Plus a 2026-04-11 13 pontos terv**:
- `#10 Call wall T1 kikapcsolás` → **automatikusan megtörténik** (scoring egyszerűsítés kiveszi M_GEX-et)
- `#11 VWAP guard egyszerűsítés` → **automatikusan megtörténik** (új entry 15:30 market open, NEM AVWAP-alapú)
- `#12 Multiplier chain egyszerűsítés` → **a scoring revízió felülírja** (csak M_target marad)
- `#13 Flow al-komponens dekompozíció` → **MÁR ELVÉGEZTE** a 232-trade audit

---

## 5. Strukturális finding-ok (Day 63 alapján)

### 5.1 A "magas pontszám paradoxon" — kvantitatívan megerősített

**60 napi adat (n=378)**: Pearson $\rho(S, R) = -0.000$ (p=0.996). A 95% CI a true effekten: $[-0.10, +0.10]$. **Strong evidence** a "small effect" tartományra.

**Quintile minta**:
- Q1 (alsó 75): -$129 / -$1.72 átlag
- Q2 (közepes 76): **+$880 / +$11.57** ⭐
- Q3 (közép 75): **-$1,341 / -$17.88** ⚠️
- Q4 (felső 76): +$76 / +$1.01
- Q5 (legfelső 76): -$677 / -$8.91

**Stratégiai következmény**: a swing pivot **PCR + OTM-inverse only scoring** (Bonferroni-szignifikáns minimum) **strukturálisan kezelhetővé** teszi a paradoxont. A tech és funda sub-score (kvázi-zaj) **kikerül**.

### 5.2 Az időtáv-paradoxon — mathematical doc 5.2 mutual information

A flow signal **$h$-step mutual information** modellje: $I \propto h \cdot \rho^2$.

Ha a 1-step $\rho = 0.14$ (Bonferroni-szignifikáns PCR korreláció), akkor:
- $h=1$: $I \approx 0.020$
- $h=3$: $I \approx 0.059$
- **$h=5$: $I \approx 0.098$** ← **5× erősebb signal**
- $h=7$: $I \approx 0.137$ (de overnight gap risk-aggregáció)

**Optimum**: $h \in \{3, 5\}$ nap. A swing pivot **5 napi time-stop**-pal ezt operacionalizálja.

### 5.3 Negatív Kelly criterion — matematikai konkluzió

**Konzervatív (csak determinisztikus exit-ek)**: $f^* = 0.50 \cdot 50/92.56 - 0.50 = -0.23$
**Default (összes exit)**: $f^* = 0.466 \cdot 15.07/92.56 - 0.534 = -0.458$

**Mindkettő negatív** — a rendszer **negatív expectancy-jű**. Csak a swing pivot 5×-szöröse signal-erősítés (mathematical doc 5.2) tudja **pozitív irányba mozdítani**.

### 5.4 Operacionális kockázatok — 4 strukturális instancia 13 napon belül

| Dátum | Ticker | Bug típus | Kár |
|---|---|---|---|
| 2026-05-01 | DTE | LOSS_EXIT + bracket SL ugyanazon napon | -$988 (paper) |
| 2026-05-07 | SQM | LOSS_EXIT + bracket SL ugyanazon napon | -$425 (valós) |
| 2026-05-12 | FORM | MOC fill + bracket másnap aktivált | ~-$200 (valós) |
| 2026-05-12 | AAPL | MOC fill + bracket másnap aktivált | ~-$150 (valós) |

**Strukturális, NEM patchelhető** — a swing pivot **mental stop architektúra eliminálja a bracket-rendszert**.

### 5.5 Makró-rezsim degeneráltság

A 60 napi mintán:
- BMI = YELLOW 100% (sosem GREEN, sosem RED)
- $M_{\text{VIX}} = 1.0$ 100% (VIX mindig < 20)
- $M_{\text{GEX}}$ undetermined: 75%

**A multiplier chain effektíven csak $M_{\text{target}}$-en és $M_{\text{contradiction}}$-on különböztet meg tickereket**. Ez **inkonzisztens differenciálás**. A swing pivot **csak $M_{\text{target}}$-et tartja meg** (M_contradiction sign-flip vizsgálat után dönt).

---

## 6. Nyitott kérdések (strukturális hipotézisek, NINCS aktív task)

### 6.1 Information ratio mérése a tilt-kalibrációhoz

A Bayes-update Day 90-en (UW shadow log audit, $n \approx 150-180$): ha a true $\rho_{\text{dp}}$ a $[-0.20, +0.20]$ tartományon kívülre esik, az UW visszahozható a scoring-ba. A 95% CI mérése **érdemleges power**-rel.

### 6.2 Linkage method érzékenység (jövő iterációhoz)

Ha a swing pivot Day 126-on sikeres, a következő iteráció (Q4 2026) **HRP/HERC allokáció**-t vizsgálhat. A linkage method (ward / complete / average) érzékenységét **15 tickerrel** kell tesztelni — a `docs/planning/bc22-hrp-allocation-design.md`-ben részletezve.

### 6.3 Cross-Asset Regime integráció a swing-en

A jelenlegi Cross-Asset Regime (HYG, IEF, RSP, SPY, IWM 20 napi momentum) **RISK_OFF / CRISIS** állapotokra csökkenti a max pozíciószámot. **Swing-en**: a 12 concurrent cap az új keret, de **CRISIS-ben 6-ra csökkentés** természetes. Implementáció a Fázis 3-ban.

### 6.4 MID Bundle integráció

A MID — Macro Intelligence Dashboard napi shadow snapshot-okat produkál. A swing pivot kontextusában **portfolio context layer** lehet — pl. Stagflation regime-ben a pozíciómért kisebb, vagy a sector-rotation szabályok defenzívebb sektor-súlyokat alkalmaznak. **BC25 W26+ scope**, Fázis 3 után.

### 6.5 SMA-inflexió mint exit-overlay (trend-alapú exit vizsgálat)

**Eredet**: Tamás 2026-05-28 felvetése a VLO (Day 3-4) kapcsán — "ha swing tradel a rendszer, amint inflexió van az 5 napos mozgóban, azonnal ki kellene lépnie".

**Tisztázás**: a swing pivot exit-logika jelenleg **kizárólag ATR-alapú** (mental stop 2,0×ATR + TP1 1,5×ATR + TP2 3,0×ATR + trail 1,0×ATR + time-stop + heti -8% hard SL). **NINCS SMA-inflexió trigger.** A régi rendszer SMA50-komponense *entry*-scoring volt (technikai score), NEM *exit*-trigger — a swing pivot az SMA-t sehol nem használja.

**A VLO konkrét eset NEM releváns precedens**: a VLO Day 4 SL-je Tamás Day 3-i manuális TWS bracket-jének autonóm trigger-je volt (§0.10), NEM a swing logika. Ráadásul a -5,4% egynapos zuhanásnál a mental stop (~$243,5, 2×ATR) nagyjából ott vitte volna ki (~$244), ahol a bracket — egy SMA-inflexió *lassabban* jelzett volna, tehát NEM védett volna jobban egy ilyen gyors esésnél.

**A design-kérdés érdeme**: az SMA-inflexió egy legitim trend-following swing exit-elv. A két filozófia különbsége: az ATR mental stop **kockázat-alapú** ("mennyit engedek veszíteni"), az SMA-inflexió **trend-alapú** ("ha a trend megfordul, kiszállok"). A swing pivot kvantitatív tézise (§5.2, flow mutual information $h=5$) inkább momentum/flow play-out-ra épül, ami illeszkedhetne egy trend-exithez.

**Javasolt vizsgálat (Fázis 2 backtest-overlay, NEM aktív task)**: a felgyűlő paper trading adaton (most n=9 closed, később több) visszamérni: egy 5-napos SMA-inflexió exit jobb total P&L-t / kisebb tail-veszteséget ad-e, mint a jelenlegi ATR mental stop. Beilleszthető a §2.1 (entry timing backtest) scope-jába mint exit-overlay dimenzió. Döntés: (A) marad tiszta ATR mental stop, (B) SMA-inflexió overlay hozzáadása, (C) hibrid (a kettő közül amelyik előbb triggerel).

**Effort**: ~1-2 óra Chat-oldali backtest (a §2.1-gyel együtt), kód-deploy csak ha a backtest pozitív.

**Owner**: Chat (Fázis 2, W23 — a §2.1 entry-timing backtesttel együtt).

---

## 7. Mit NEM csinálunk (és miért)

| Korábbi terv | Akció | Indoklás |
|---|---|---|
| **A+C kombinációs roadmap** (strategic-review 7.5) | **MÓDOSÍTVA** | 6 nap új adat → csak B (swing pivot) |
| Inkremeális finomítás a régi rendszerre | **NEM** | Strukturális bug-források nem patchelhetők |
| BC24 Institutional Flow Intelligence | **PARKOLT** | Új scoring (PCR + OTM-inverse only) felülírja |
| BC25 IFDS Phase 3 ← MID CAS | **PARKOLT Day 126-ig** | Új paper trading után döntés |
| Élő pénzes kereskedés Day 90-en | **NEM** | Új Day 126 milestone (kb. 2026-09-15) az első valós döntés |
| Komplex statisztikai modellek (random forest, neural net) | **NEM** | Kis n probléma (Bonferroni-minimum a tisztább alap) |

---

**A frissítésért felel**: Chat (Claude) — eseményalapú (új finding, új debug eredmény, új P1/P2/P3 task után). A Fázis 1-2 alatt heti konzisztencia-check.

---

## 8. Fázis 3 deploy utáni finding-ek (2026-05-18, Day 1 GO-LIVE)

A Day 1 GO-LIVE (2026-05-18) első operációs futamból **9 új tétel rögzítve** (3 P1 + 4 P2 + 1 permanent observation + 1 vasarnap esti Phase 1-3 cron freshness alert).

### 8.1 P1 — Strukturalis, Day 1 finding-ek

#### 8.1.1 ATR_pct floor minimum threshold (MASI 0.165% case)

**Mi**: MASI Day 1 entry-jén ATR=$0.295, ATR_pct=0.165%. Ez extrém alacsony — a swing TP1 distance csak +0.247%, mental SL distance -0.330%, ami kisebb mint az 1 standard daily noise (VIX 18.55 → ~1.16% expected daily move). A swing-target window strukturalisan fáls trigger-erzekeny.

**Strukturalis ok**: a swing pivot scoring (PCR + OTM-inverse percentile) NEM szűri ki a low-ATR tickereket. A sizing-formula `qty = (equity × 0.0035) / (ATR_pct × 2.0)` viszont óriási qty-t allocál (MASI: 604 share vs normál ~100), így a slippage és noise dominálnak.

**Javasolt fix** (`defaults.py`): `swing_atr_pct_floor: 0.005` (0.5% min daily volatilitás). MASI-t (0.165%) kiszűrné, tipikus mid-cap-ek (1-2%) bent maradnak.

**Effort**: ~30-45 min CC + 2-3 unit teszt + ~30 min backtest a 60 napi régi mintán a pontos floor kalibráláshoz.

**Akciváció**: Day 1 EOD post-mortem után (2026-05-19 kedd reggel), ha MASI tényleg gyors trigger-elt.

**Owner**: CC (P1 hotfix, ha az EOD eval mutatja a problémát)

#### 8.1.2 State/IBKR reconciliation gap

**Mi**: A swing system két source-of-truth-tal — `state/swing_positions.json` (mental stop / TP1 / TP2 levels) és IBKR positions (actual holdings) — csendben divergálni tud.

**Mai eset**: 14:34 pre-market submit → 14:42 manuális state reset → 15:30 NYSE open → mind a 3 ticker filled. A `state/swing_positions.json` üres, az IBKR-ben 3 nyitott pozíció. A swing system számára a 3 pozíció "elveszett" — az EOD eval 22:00-kor üres state-en futott volna, NULL exit logikával.

**Strukturalis kockázat**: bármilyen jövőbeli IBKR connection-bug, manuális state reset, vagy `nuke.py` invokáció ugyanezt a divergenciát hozhatja létre.

**Javasolt megoldás**: napi reconciliation script (`scripts/paper_trading/reconcile_state.py`) ami eltérés esetén:
- Telegram WARNING ("State/IBKR divergence: N IBKR positions not in state")
- NEM auto-fix — Tamás dönt rekonstrukció vs nuke
- Cron entry: `15 22 * * 1-5` (5 perccel az EOD eval után)

**Effort**: ~45 min CC + 2-3 unit teszt

**Owner**: CC (W22-ben javítás)

#### 8.1.3 Submit cron Telegram silence 0-submit esetén

**Mi**: A 15:30 cron `submit_orders.py` futott, detektálta hogy MASI/LBRT/EC már nyitott pozíció IBKR-ben (a 14:34-i pre-market submit-ok filled-ek), és skippelte: "Submitted: 0 tickers". NEM küldött Telegram üzenetet, mert a Telegram trigger az új submit-eken aktivál, NEM a cron heartbeat-en.

**Strukturalis kockázat**: ha bármilyen jövőbeli okból a `submit_orders.py` futása 0 új entry-vel zárul, Tamás nem kap visszajelzést hogy a cron lefutott. Hallgatás ≠ siker mintázat.

**Javasolt fix**: a `submit_orders.py` MINDIG küldjön Telegram-ot, akkor is ha 0 új entry:
- 0 submit → `"✓ Submit cron ran 15:30. Submitted: 0 new (N existing skipped)"`
- 1+ submit → meglévő "📈 IFDS Swing Submit" formátum

**Effort**: ~15 min CC

**Owner**: CC (W22 elején P1 hotfix)

#### 8.1.6 ✅ pt_monitor.py "5-min replay events" pollution (RESOLVED 2026-05-20)

**Státusz**: ✅ RESOLVED — root cause azonosítva (H1: pytest pre-flight FileHandler bind), fix deploy-olva (`lib/log_setup.py::_resolve_log_dir()`), +5 regressziós teszt. Részletes diagnózis: `docs/tasks/2026-05-19-pt-monitor-replay-diagnosis.md` §6.

**Áthivatkozás**: lásd §0.1 — eredetileg ott jelent meg mint P0, Day 1+Day 2 megfigyelés. Day 2 (2026-05-19) `pt_monitor_2026-05-19.log` 91 sora ugyanazt a LION/SDRL "Trail SL hit"/"LOSS_EXIT" mintát mutatta 16:37:19 timestamp-pal — pontosan a Mac Mini-n manuálisan futtatott `deploy_daily.sh --phases 1-3` pytest pre-flight ablakában.

**Fix kompozíció**:
- `scripts/paper_trading/lib/log_setup.py`: `_resolve_log_dir(log_dir)` helper redirect pytest alatt (`PYTEST_CURRENT_TEST` env var detektálással) tmp dir-be.
- Csak az implicit default (`log_dir="logs"`) redirektált — explicit caller-supplied `tmp_path` változatlanul áthalad (a meglévő 5 `test_log_setup.py` teszt változás nélkül passing).
- `tests/test_log_setup_isolation.py` (5 új teszt): a redirect viselkedés minden ágát védi.

**Hatás**: minden PT script (10+ darab) automatikusan védett pytest-bind pollution-tól. Produkciós cron viselkedés bit-for-bit változatlan.

#### 8.1.7 ✅ UW shadow log overwrite Day 2 — write_shadow_snapshot unmocked (RESOLVED 2026-05-20)

**Státusz**: ✅ RESOLVED — `tests/test_pipeline_e2e.py` decorátor-stack kibővítve `@patch("ifds.data.uw_shadow.write_shadow_snapshot")`-tal, +1 új assert a regressziós teszt-ben. A `d3fce73` fix második előfordulása.

**Mi**: Day 2 (2026-05-19) `state/uw_shadow/2026-05-19.json` reggel ~90+ ticker várt, de a fájl csak **1 ticker** (AAPL, combined_score=78.0, gex_value=500.0) — pontosan a `tests/test_pipeline_e2e.py::_mock_phase4()` fixture szignatúrája. `captured_at: 14:37:19+00:00` (= 16:37 CEST) megegyezik a manuális `deploy_daily.sh --phases 1-3` futtatás időpontjával.

**Root cause** (azonos a `d3fce73`-mal): a `runner.py` line 665 `write_shadow_snapshot(shadow_dir, trading_date, shadow_snapshot)` hívása **patch-eletlen** maradt a `tests/test_pipeline_e2e.py`-ben. A `test_full_pipeline_flow` mockolja a Phase 4 `run_phase4`-et `_mock_phase4()`-re (AAPL combined_score=78.0), majd a runner.py shadow log writer-e a mock-olt `ctx.stock_analyses`-t kiírja a **produkciós** `state/uw_shadow/YYYY-MM-DD.json`-ba.

A `d3fce73` (2026-05-08) csak a `save_phase4_snapshot` sink-et patch-elte. A `write_shadow_snapshot` a "Day 63 outcome §3.2" miatt KÉSŐBB lett hozzáadva a runner-hez (2026-05-26 koncepció szerint), de a teszt patch-stack-et nem frissítették vele.

**Fix**:
1. `tests/test_pipeline_e2e.py::test_full_pipeline_flow`: `@patch("ifds.data.uw_shadow.write_shadow_snapshot", return_value=None)` decorator hozzáadva
2. `tests/test_pipeline_e2e.py::TestSnapshotIsolation::test_save_snapshot_is_mocked_in_e2e`: ugyanaz a patch + új `assert mock_write_shadow.called` regressziós assert
3. `.claude/rules/ifds-rules.md` "Test environment higiénia" szabály bővítve a `write_shadow_snapshot`-tal és a második előfordulás dokumentálva

**Verifikáció**: fix után `python -m pytest tests/test_pipeline_e2e.py -q` futtatás után `state/uw_shadow/YYYY-MM-DD.json` NEM keletkezik (fix előtt: AAPL mock létrejött).

**Day 90 audit hatás** (KOMPROMITTÁLT, IREVERZIBILIS):

A 2026-05-19-i shadow log permanently lost — a 14:30 CEST cron által írt ~90-ticker tartalmat a 16:37-i pytest pollution overwrote, és csak a Phase 4 snapshot (`state/phase4_snapshots/2026-05-19.json.gz`, 11 KB, 14:34-i mtime) maradt meg a teljes phase4-context-ből. A Day 90 (~2026-08-26) UW Bayesian recalibration **kihagyja** 2026-05-19-et, mert a shadow log kontextus (`m_gex_would_have_been`, `dp_score_would_have_been`, `gex_analyses` snapshot) nem rekonstruálható retrospektíven csak a Phase 4 snapshot-ból.

**Lessons learned**: minden új sink, ami `runner.py`-be kerül, mindkét e2e patch-stack-be adandó (`test_full_pipeline_flow` + `TestSnapshotIsolation`). A "mock-was-called" assert pattern csak a MEGLÉVŐ patch-ek refactor során elcsúszása ellen véd, NEM új sink hozzáadása ellen. Audit-szabály: minden `runner.py` PR-nél `grep "from ifds\.\(data\|pipeline\|output\)\." src/ifds/pipeline/runner.py` outputot diff-elni a `@patch` decorator-okkal a `test_pipeline_e2e.py`-ban.

**Referencia**:
- Detection: 2026-05-20 napi review (Chat 1 UW shadow log gyanú)
- Fix commit: lásd git log "fix(tests): patch write_shadow_snapshot in e2e"
- Source rule: `.claude/rules/ifds-rules.md` "Test environment higiénia" § "Második előfordulás"
- Future audit: Day 90 calibration **SKIP 2026-05-19** (single-ticker AAPL mock)

#### 8.1.8 ✅ save_phase13_context e2e patch (proaktív, RESOLVED 2026-05-20)

**Státusz**: ✅ RESOLVED — Task #H proaktív patch a 04-risks §8.1.6/§8.1.7 audit-szabály szerint. NEM aktív pollution incidens volt, csak strukturális risk-megelőzés.

**Mi**: a `runner.py` sink-audit Day 2-én (2026-05-19) 5 sink-ből 4-et patch-eltnek talált a `tests/test_pipeline_e2e.py`-ben:

| Sink | Patch előtt |
|---|---|
| `save_phase4_snapshot` | ✅ patch-elt (`d3fce73`) |
| `write_shadow_snapshot` | ✅ patch-elt (`1eb9755`, §8.1.7) |
| `write_full_scan_matrix` | ✅ patch-elt |
| `write_trade_plan` + `write_execution_plan` | ✅ patch-elt |
| `save_phase13_context` | ❌ **patch-eletlen** ← Task #H scope |

**Strukturális risk**: ha bárki `pytest`-et futtat a Mac Mini-n a vasárnap 22:00 cron-ablak előtt (`--phases 1-3` formában), a pytest pre-flight a `state/phase13_ctx.json.gz`-t mock universe-szel felülírhatná. A Phase 4-6 cron a következő héten kompromittált context-tel dolgozna.

**Mérséklő tényező** (miért nem aktív pollution incidens): a meglévő e2e tesztek mind `run_pipeline()`-t hívnak (default `phase=None`), ami NEM triggereli a `save_phase13_context`-et (`isinstance(phase, tuple)` False). Csak akkor lett volna pollution, ha bárki tuple-phase teszteket adott volna hozzá vagy a runner.py-t refaktorálnák.

**Fix**:
1. Defenzív `@patch("ifds.pipeline.context_persistence.save_phase13_context", return_value=None)` mindkét meglévő e2e stack-be (`test_full_pipeline_flow`, `test_save_snapshot_is_mocked_in_e2e`) — risk-prevention jövőbeli refactor ellen.
2. Új dedikált teszt `TestSnapshotIsolation::test_phase13_context_save_is_mocked` — `run_pipeline(phase=(1, 3))` ténylegesen triggereli a save_phase13_context-et + `assert mock_save_phase13.called` regressziós védelem a patch wiring-ét bizonyítja.

**Test deltas**: 1745 → 1746 passing (+1 új dedikált teszt; NEM +2 mint a task spec sugallt — a meglévő flow tesztekben nem értelmes az assert, lásd Task §7 finding).

**Verifikáció**: pytest futtatás után `state/phase13_ctx.json.gz` mtime változatlan (May 19 16:40:48). Fix előtt egy hipotetikus tuple-phase tesztben a fájl felülíródott volna.

**Sink audit lezárás**: a runner.py 6 sink mind a 6 patch-elt — strukturálisan teljes körű. A pytest pre-flight pollution kockázata a `runner.py` teljes scope-jában lezárt.

**Out of scope (Fázis 4 backlog)**: a §5 task spec rögzített egy strukturálisan elegánsabb alternatívát ("Production path env var" — pl. `IFDS_STATE_DIR`-rel centralizált sink-isolation refactor). Effort: ~2-3 óra CC, közepes risk. Felvéve a backlog-ba, de a 6 targeted `@patch` a jelen audit-szabály szerint elég.

**Referencia**:
- Task fájl: `docs/tasks/2026-05-20-phase13-context-e2e-patch.md` §7
- Audit szabály: `04-risks` §8.1.6 + §8.1.7
- Predecessor commits: `d3fce73` (Phase 4 snapshot, 2026-05-08), `1eb9755` (UW shadow, 2026-05-20)

#### 8.1.9 ✅ Telegram pollution — env_setup nem clear-elte IFDS_TELEGRAM_* (INCIDENT, RESOLVED 2026-05-20)

**Státusz**: ✅ RESOLVED — Task #H tesztemen keresztül **aktív (nem proaktív)** pollution incidens. Tamás 2 ÉLŐ MACRO SNAPSHOT Telegram üzenetet kapott mock fixture data-val 2026-05-20 09:41 + 09:44 CEST időpontokban. Fix: `env_setup` fixture kibővítve `IFDS_TELEGRAM_*` delenv-vel + 3 defenzív `@patch` decorator.

**Mi**: a `tests/test_pipeline_e2e.py::env_setup` fixture API key-eket beállította, de **NEM clear-elte** az `IFDS_TELEGRAM_BOT_TOKEN` és `IFDS_TELEGRAM_CHAT_ID` env var-okat. A dev MacBook `.env`-jében valid Telegram credentials voltak. A Task #H (`bd54857`) által hozzáadott új `test_phase13_context_save_is_mocked` teszt:

1. Hívja `run_pipeline(phase=(1, 3))`
2. A `runner.py:685` elágazás aktiválódik: `if isinstance(phase, tuple) and phase == (1, 3):`
3. `send_macro_snapshot(ctx, config, logger, duration)` meghívódik
4. A `ctx` a mock Phase 1/2/3 data-t tartalmazza (`_mock_phase1/2/3()` fixture)
5. Token+chat_id valid → ténylegesen kiküldi a mock data-t Telegram-on

**Pollution evidencia** — a kiküldött MACRO SNAPSHOT üzenet (09:41 + 09:44) **100%-ban** egyezik a fixture szignatúrákkal:
- `_mock_phase1()`: `bmi_value=45.0`, `BMIRegime.YELLOW`, `ticker_count_for_bmi=100` → "BMI = 45.0% Regime = YELLOW Tickers used = 100"
- `_mock_phase2()`: `total_screened=3000`, 2 ticker (AAPL+MSFT) → "Screened: 3000 Passed: 2"
- `_mock_phase3()`: single XLK, `momentum_5d=2.5` → "XLK ^ +2.50% Leader UP"

A 09:41 + 09:44 timestamp pontosan megegyezik az én pytest futtatásaimmal (`pytest tests/test_pipeline_e2e.py -v` és `pytest tests/ -q` a Task #H commit ELŐTT — a commit timestamp `bd54857` = 09:44:22).

**Root cause**: a sink-audit (§8.1.6, §8.1.7, §8.1.8) a **file system pollution sink**-eket azonosította (`save_phase4_snapshot`, `write_shadow_snapshot`, `save_phase13_context`). Az **external side-effect sink**-eket (Telegram, Slack, IBKR, stb.) NEM auditálta. Ez egy 7. (telegram) sink osztály, amit kihagyott az audit scope.

**Fix**:

1. **`env_setup` fixture kibővítése** (`tests/test_pipeline_e2e.py`):
```python
monkeypatch.delenv("IFDS_TELEGRAM_BOT_TOKEN", raising=False)
monkeypatch.delenv("IFDS_TELEGRAM_CHAT_ID", raising=False)
```
Ez gracefully blokkolja az ÖSSZES telegram send-et a runner.py `if not token or not chat_id: return False` guards-okon keresztül.

2. **Defenzív `@patch` decoratorok** mindhárom telegram send entry point-ra:
- `@patch("ifds.output.telegram.send_macro_snapshot", return_value=True)`
- `@patch("ifds.output.telegram.send_trading_plan", return_value=True)`
- `@patch("ifds.output.telegram.send_daily_report", return_value=True)`

Mindkét meglévő e2e stack-be (`test_full_pipeline_flow`, `test_save_snapshot_is_mocked_in_e2e`) + a Task #H `test_phase13_context_save_is_mocked`-be (csak `send_macro_snapshot` a phase=(1,3) miatt).

3. **Regressziós assert** a `test_phase13_context_save_is_mocked`-ben:
```python
assert mock_tg_macro.called, (
    "send_macro_snapshot mock was not invoked — runner may have "
    "bypassed the patch and sent a live Telegram MACRO SNAPSHOT "
    "with mock fixture data (see 2026-05-20 09:41/09:44 incident)."
)
```

4. **`.claude/rules/ifds-rules.md` "Cron env isolation" szabály kibővítve** a Side-effect env (Telegram, Slack, IBKR) §-szal és az incident dokumentálásával.

**Belt-and-suspenders**: a két réteg (env clear + @patch) együtt biztosítja, hogy:
- Ha valaki visszaállítja az env var-okat egy másik fixture-ben → @patch még védi
- Ha valaki eltávolítja a @patch-ot → env var clear még védi
- Mindkettő egyszerre engedett ki kellene, hogy aktív legyen a pollution

**Verifikáció**:
```
$ IFDS_TELEGRAM_BOT_TOKEN=fake IFDS_TELEGRAM_CHAT_ID=fake \
  pytest tests/test_pipeline_e2e.py -v
8 passed   ✓ (mock + env clear mindkettő aktív)
```

**Permanent observation**: a sink-audit scope-ja kibővítendő minden olyan modulra, ami a `runner.py`-ból outbound network/messaging hívást tesz — nem csak file system writers. Audit-szabály frissítve.

**Referencia**:
- Detection: 2026-05-20 09:45 Tamás message — "ez így rendben van?"
- Incident timing: 09:41 + 09:44 CEST (két pytest run a `bd54857` commit előtt)
- Fix commit: lásd git log "fix(tests): patch Telegram sinks in e2e (Task #H follow-up)"
- Source rule update: `.claude/rules/ifds-rules.md` "Cron env isolation" § 3

### 8.2 P2 — Operációs, Day 1 finding-ek

#### 8.2.1 Pre-market submit + PreSubmitted státusz risk

**Mi**: 14:34-i pre-market submit során az IBKR Error 10349 (DAY TIF outside RTH) látszólag cancelled minden order-t. Két ticker (LBRT, EC) status=Cancelled visszajelzéssel, MASI PreSubmitted-ként marad. A 14:42-i state reset abból a feltevésből indult, hogy 3 order = cancelled. 15:30-kor mind a 3 order filled lett a NYSE open-en.

**Tanulság**: IBKR PreSubmitted vagy "Cancelled" státusz pre-market időben nem garantálja a végleges állapotot. State reset csak akkor biztonságos, ha az `ib.positions()` valóban üres (verifikálva, NEM csak a log alapján).

**Javasolt fix**: a manuális state reset folyamat (ha valaha újra kell) MUST:
1. `ib.positions()` ellenőrzés — 0 nyitott pozíció confirm
2. `ib.openOrders()` ellenőrzés — 0 pending order confirm
3. State reset csak ha mindketto üres

**Effort**: dokumentáció + opcionális script enhancement (`scripts/paper_trading/state_reset_safe.py`) — ~30 min

**Owner**: CC (W22+ alacsony prioritás, ritka manuális művelet)

#### 8.2.2 IBKR "Existing positions" guard — value-add component

**Mi**: A 15:30 `submit_orders.py` helyesen detektálta hogy MASI/LBRT/EC már nyitott pozíció IBKR-ben (az `existing_positions` check működött), és NEM duplázta őket.

**Permanent record**: ez a guard megorzendo minden refaktoring során. A 14:34 pre-market submit utáni 15:30 cron-on a teljes pozíciómennyiség duplázása ($3500+ extra notional) strukturalis kockázat lett volna nélküle.

**Akció**: NINCS — csak rögzítendő mint value-add component, megorzendo.

#### 8.2.3 Phase 2 `_exclude_earnings` intermittent thread hang

**Mi**: 14:25-i manuális Phase 1-3 futtatás közben a `_exclude_earnings` futtatás `as_completed(futures)` waiter-en lógott (KeyboardInterrupt-tal lezárva, mert 14:30 cron közeledett).

**Diagnózis**: párhuzamos FMP earnings calendar hívások (`ThreadPoolExecutor`) között valószínűleg egy nem-responsive request a thread-poolt blokkolta. FMP rate limit vagy `concurrent.futures` timeout config gyanú.

**Strukturalis kockázat**: a jövő vasárnap esti (5/24 22:00) heti rebalance cron-on ha ugyanez a thread hang fennáll, a Phase 1-3 silent fail-elhet és a Phase 4-6 a régi péntek esti context-tel dolgozik tovább.

**Javasolt megoldás**:
- (A) Telegram alert ha a vasárnap esti Phase 1-3 cron NEM termel friss `state/phase13_ctx.json.gz`-t vasárnap 23:00-ig (heartbeat-szerű)
- (B) `_exclude_earnings` thread pool timeout pattern (per-future timeout + `cancel_futures=True`)

**Effort**: (A) ~15-20 min CC, (B) ~30 min CC + 2-3 unit teszt. Mindketto érdemes.

**Owner**: CC (W22 elején)

#### 8.2.4 Legacy wrapper script audit

**Mi**: A `scripts/deploy_intraday.sh` a Fázis 3 deploy ELŐTT tartalmazott `submit_orders.py` és `company_intel.py` futtatást a Phase 4-6 után. A 14:30 cron-on ez a régi inline submit pre-market submit-ot termelt (lásd §8.2.1). A `2026-05-17-swing-execution-exit.md` Task #4 a `submit_orders.py`-t és `pt_monitor.py`-t átírta, de a wrapper scripteket NEM auditalta.

**Strukturalis kockázat**: lehet hogy más legacy wrapper scriptek (`scripts/deploy_daily.sh`, `scripts/setup_cron.sh`) is tartalmaznak swing pivot előtti logikát.

**Javasolt megoldás**: full audit + cleanup task:
- `scripts/deploy_intraday.sh` ✅ FIXED (`ce06238`)
- `scripts/deploy_daily.sh` — audit szükséges
- `scripts/setup_cron.sh` — audit szükséges
- `scripts/paper_trading/*.py` — egyenkénti audit a bracket/LOSS_EXIT/5min reference-ekre

**Effort**: ~30-45 min audit + ~30 min cleanup. Új task fájl: `docs/tasks/2026-05-19-legacy-wrapper-script-audit.md`.

**Owner**: CC (W22 első napjaiban, P2 prioritás)

### 8.3 Permanent observations

#### 8.3.1 AVDL.CVR un-nuke-able orphan pozíció

**Mi**: Az IBKR paper account-ban van egy AVDL.CVR (Avadel Pharmaceuticals Contingent Value Right) pozíció, ami a Day 1 előtti időszak öröksége. Tamás korábban próbálta `nuke.py`-vel kivenni, NEM sikerült (CVR instrumentumok specifikus IBKR cancel-keretet igényelnek, ami a `nuke.py` scope-ján kívül esik).

**Akció**: NINCS — a swing system számára transparent. A `monitor_positions.py` reggeli leftover check valoszinuleg flag-eli, de nem blokkolja a swing entry-ket.

**Permanent record**: ez NEM bug, NEM aktiv kockazat — egyszerűen egy "orphan" pozíció, amit a swing system nem érint. **Day 63+ inherited, NO action**.

**Owner**: NONE

---

## 9. Day 6-8 finding-ok (2026-05-26 — 2026-05-27, Memorial Day utáni újraindulás)

A Day 7 (2026-05-26, kedd) és Day 8 (2026-05-27, szerda) napi review-kból **9 új tétel** (1 P0 → §0.11, 2 P1, 2 P2, 4 megfigyelés/pozitív). Forrás: [`docs/review/2026-05-26-daily-review.md`](../review/2026-05-26-daily-review.md), [`docs/review/2026-05-27-daily-review.md`](../review/2026-05-27-daily-review.md).

### 9.1 ✅ Pattern 5 — stale Phase 1-3 context bug (P1, RESOLVED 2026-05-26)

**Státusz**: ✅ RESOLVED ugyanazon a napon — CC fix `304a64d` + 4 regressziós teszt + Pattern 5 doc entry (`2026-05-25-operator-emergency-procedure.md`).

**Mi**: A `e9d617a2` commit (2026-04-03) bevezette a Pipeline Split architektúrát (Phase 1-3 vasárnap esti context, Phase 4-6 14:30 cron a friss context-tel). Latens hiba: ha a vasárnap esti Phase 1-3 cron NEM termelt friss `state/phase13_ctx.json.gz`-t, a Phase 4-6 a régi context-tel folytatott — csendben, NINCS detection. **Latencia ~7 hét** (2026-04-03 → 2026-05-24 első éles crash a Memorial Day hétvége után).

**Eredmény Day 7-en**: a stale context **2 nem-kívánt entry-t** generált — EOG (Energy, S_j 68,6) + AKAM (Technology, S_j 61,8). A sector-balanced greedy nem ismerte fel az Energy szektor teltségét (4. Energy ticker lett az EOG). $8 666 notional + $2 commission. Tamás döntése: mental-stop módban szabadon kifut.

**Fix**: context freshness check (a Phase 4-6 NEM indul, ha a context > küszöb öreg) + Telegram alert + manuális Phase 1-3 recovery procedure. **CC verify szükséges** a pontos fix-tartalomra (a Log Review chat rekonstrukciója a review §8.2-ben).

**Tanulság**: a vasárnap esti Phase 1-3 cron freshness heartbeat (§8.2.3 már jelezte) most konkrét védelmet kapott.

### 9.2 ⚠️ `days_held` calendar-day vs trading-day inkonzisztencia (ÚJ P1, magas)

**Státusz**: ✅ DEPLOYED 2026-05-28 (CC commit `0b2ddaa`) — `trading_days_between()` + `evaluate_position_eod` trading-day számlálás, +9 regressziós teszt. A Day 8 TIME_STOP hullám **$479 közvetlen kárt** demonstrált (a fix előtt).

**Mi**: a `swing_positions.json` `days_held` mezője **calendar-day alapú**, NEM trading-day. Bizonyíték (Day 8 záró):
- WMB entry 5/21, days_held=5 (calendar) = **2 trading nap** (5/21, 5/22, 5/27) → mégis TIME_STOP-olt
- DXCM ugyanaz: 2 trading nap után exit
- A `swing_time_stop_trading_days=5` paraméter neve "trading_days"-re utal, de calendar-day-ként viselkedik (minden EOD eval +1, hétvégén is)

**Közvetlen költség (Day 8)**: WMB (-$379,10) + DXCM (-$100,06) = **-$479,16** realizálva 2 trading nap után az Energy/Healthcare szektor mélypontján. Trading-day alapú hold-nál ezek még 3 további trading napot kaptak volna.

**Strukutrális következmény**: a swing pivot kvantitatív tézise (mathematical doc §5.2: $h=5$ **trading** nap = 5× mutual information) **trading-day hold-ot feltételez**. A jelenlegi rendszer a calendar-bug miatt **NEM a tervezett swinget futtatja** — a TIME_STOP-ok 2-3 trading nap után túl korán jönnek. **A fix elengedhetetlen a tézis tisztességes teszteléséhez.**

**Javasolt fix**: `swing_positions.py::days_held` trading-day alapú számlálás (`utils/calendar.py::trading_days_between()`). Alternatíva: paraméter átnevezése `swing_time_stop_calendar_days`-re + design doc frissítés (DE az (A) preferred, mert a tézis trading-day alapú).

**Effort**: ~30 min CC + 3-4 regressziós teszt + ~15 min design doc.

**Owner**: CC (P1, W22).

### 9.3 ⚠️ ATR_pct floor hiánya — JHG megismétli a MASI Day 1 problémát (ÚJ P1)

**Státusz**: ✅ DEPLOYED 2026-05-28 (CC commit `4f2f8c0`) — `swing_atr_pct_floor: 0.005` + `swing_atr_pct_ceiling: 0.05` a `compute_swing_notional`-ben, +5 teszt. A §8.1.1 (MASI Day 1) **2. instanciája** 8 napon belül (a fix előtt).

**Mi**: a JHG Day 8 entry ATR=$0,09 (**0,17% relatív**) — gyakorlatilag azonos a MASI Day 1 0,165%-ával. A swing TP/SL sáv (±0,25-0,52%) **kisebb mint a tipikus napi noise** (VIX 16,92 → ~1,06% expected daily move) → fals trigger-érzékeny. Ráadásul az alacsony ATR a sizing-formulán keresztül **289 share / $14 976 notional / 15% portfolio** koncentrált pozíciót generált.

**A `swing_atr_pct_floor: 0.005` (§8.1.1 javaslat) MÉG NINCS deploy-olva** — ezért került be a JHG (0,17% < 0,5% floor). Magas S_j (88,5) ellenére strukutrálisan problémás.

**Javasolt fix**: `swing_atr_pct_floor: 0.005` deploy (§8.1.1) — most már 2 instanciával alátámasztva. **Day 9 megfigyelés**: a JHG várhatóan gyors TP1/stop triggert vagy fals exit-et produkál.

**Owner**: CC (P1, W22).

### 9.4 ⚠️ Single-position koncentráció — JHG 15% portfolio (ÚJ P2)

**Mi**: a JHG Day 8 entry $14 976 notional = **15,0% portfolio** egyetlen pozícióban. A 30% sector cap nem szegve, de a single-position koncentráció magas. A gyökérok ugyanaz mint a §9.3: alacsony ATR → nagy qty a sizing-formulából.

**Javasolt fix**: `swing_max_single_position_pct: 0.12` cap a Phase 6 sizing-ban (a 12 concurrent × ~8% átlag → ~100% logikával konzisztens). Az ATR floor (§9.3) + single-position cap együtt kezeli a problémát.

**Effort**: ~30 min CC + 2-3 teszt.

**Owner**: CC (P2, W22-23).

### 9.5 ATR_pct ceiling hiánya — AKAM 6,78% (ÚJ P2)

**Mi**: az AKAM Day 7 entry ATR=$9,985 (**6,78% relatív**) — a portfolio legmagasabb. A stop-távolság -13,58%, a TP2 +20,34%. Egy ilyen volatilis ticker normál napi mozgása 2-4% → a TP1/stop 1-2 nap alatt is kitörhet, a swing pivot 3-5 napi hold szándékához képest **túl érdes**.

**Javasolt fix**: `swing_atr_pct_ceiling: 0.05` (5% cap) — az ATR floor (§9.3) párja. Együtt egy **0,5% ≤ ATR_pct ≤ 5%** kvalifikáló sávot teremt.

**Effort**: ~30 min CC (a floor-ral együtt deploy-olható).

**Owner**: CC (P2, W22-23).

### 9.6 📝 EC TP2 mechanika — next-day market open SELL, NEM intraday limit (dokumentációs megfigyelés)

**Mi**: a swing pivot **első TP2 exit-je** (EC, Day 8) NEM a $14,65 TP2 limit-en történt, hanem a Day 8 **15:30 CEST market open MARKET SELL**-en ($14,44-14,51, gap-down a Day 7 záró $14,84-ről). A `pt_close.log` 15:30:06 "EC: TP2 → SELL 166 (MKT)".

**Mechanika**: a Day 7 EOD eval `next_action: TP2` flag-et állít (ha az ár > TP2 level), és a következő nap 15:30 close MARKET SELL-t ad. **Ez next-day-market, NEM intraday-limit** — a reggeli gap a fill árat befolyásolja (EC: -$60 a Day 7 mark-hoz képest). Az EC teljes hold +$344,18 (TP1 Day 2 +$112,31 + TP2 Day 8 +$231,87) — a swing pivot **legjobb teljes pozíció-eredménye**.

**Akció**: dokumentációs — a swing exit design doc-ban rögzíteni hogy a TP1/TP2 flag-ek next-day-market exit-et jelentenek, nem intraday limit-et. NINCS kódváltozás (a mechanika szándékos).

### 9.7 📝 EOG stale context örökség — figyelő pozíció (megfigyelés)

**Mi**: a Pattern 5 (§9.1) stale context EOG entry-je ($141,22 Day 7) Day 8 záróra $135,00-ra esett (**-$238,60 unrealized**). A stop $133,42 — a Day 8 záró ár csak 1,17%-kal felette. Ha Day 9-10-en eléri, -$343 realized. **Day 9 kritikus megfigyelés** (IBKR `get_price_snapshot` + `get_account_positions`).

### 9.8 📝 Első teljes kohorsz-eredmény negatív — -$651 realized (stratégiai megfigyelés, CHAT ítélet)

**Mi**: a Day 1-5 entries (mind lezárult, kivéve AMH) realizált összege **-$651,40**. Két nyertes (EC +$344, ON +$159) NEM ellensúlyozza a három nagy vesztest (LBRT -$419, WMB -$379, VLO -$227).

**Kontextus / mérséklő tényezők** (miért NEM stratégiai pánik 8 nap után):
- n=9 closed, kis minta — statisztikai következtetés értelmetlen
- a days_held calendar-bug (§9.2) korán TIME_STOP-olt (WMB/DXCM 2 trading nap)
- a stale context (§9.1) + ATR floor hiánya (§9.3) torzít
- Memorial Day + Energy szektor Day 8-i gyengesége egyszeri
- **a jelenlegi rendszer a calendar-bug miatt NEM a tervezett swinget futtatja** → a -$651 egy bug-torzított, nem-reprezentatív minta

**Stratégiai következtetés (CHAT)**: a days_held fix (§9.2) **a swing pivot tézis tisztességes teszteléséhez elengedhetetlen**, mielőtt bármilyen "a swing pivot nem működik" következtetés levonható lenne. **Ez CHAT-szintű ítélet, NEM rule-based flag.**

### 9.9 ✅ IBKR MCP connector + reconcile 2/2 silent OK (pozitív strukturális)

**Mi (két összefüggő pozitívum)**:
1. **`_reconcile_state_from_ibkr` 2/2 éles SILENT OK** (Day 7 + Day 8) — a mental-stop architektúra integritása megerősítve, NINCS autonóm bracket trigger a Day 6 CNC cancel óta.
2. **IBKR hivatalos MCP connector** (api.ibkr.com/v1/api/mcp, paper DUH118657) — Tamás 2026-05-27 felfedezte. A Claude.ai és CC connector OAuth átszinkronizál. A §0.11 P&L tracking gap miatt **jelenleg az egyetlen megbízható realized P&L forrás** a daily review-knak (get_account_summary Net Liq + get_account_trades).

**Hatás**: a review-automatizáció (`docs/tasks/2026-05-28-automated-daily-review-pipeline.md`) IBKR cross-check rétege ezt használja — a Day 8-szerű tracking gap-ek automatikus P0 flag-jeként (`daily_metrics P&L ≠ IBKR realized`). **Operating environment doc frissítés javasolt** (a connector mint új read-only tool-csatorna).

**Munkamegosztás (Tamás 2026-05-28 döntés)**: Chat = stratégia + tervezés; CC = review + bugfix + automatizáció. A napi review CC-ben automatizálódik (`/review-daily` manuális trigger, `ESCALATE-{date}.md` flag a stratégiai ítélet-igényű finding-okra), a stratégiai ítélet Chat-nél marad.

---

## 10. Aktív prioritás-összefoglaló (2026-05-28, Day 8)

| # | Finding | Prioritás | Státusz | Owner |
|---|---------|-----------|---------|-------|
| §0.11 | P&L tracking gap (close_positions nem ír metrikát) | **P0** | OPEN | CC azonnali |
| §9.2 | days_held calendar-bug ($479 Day 8 kár) | **P1** | ✅ DEPLOYED `0b2ddaa` | CC ✓ |
| §9.3 | ATR_pct floor hiánya (JHG = 2. instancia) | **P1** | ✅ DEPLOYED `4f2f8c0` | CC ✓ |
| §8.1.X / §5.4 (Day 7-8) | daily_metrics 5 logging anomália | **P1** | OPEN | CC W22 |
| §9.4 | Single-position koncentráció (JHG 15%) | P2 | OPEN | CC W22-23 |
| §9.5 | ATR_pct ceiling hiánya (AKAM 6,78%) | P2 | ✅ DEPLOYED `4f2f8c0` | CC ✓ |
| §0.10 | State≡IBKR monitoring | 🔶 PARTIAL | Rész 1 ✓, Rész 3 → §0.11 | CC |
| §0.2 | Error 10349 TIF | ✅ WITHDRAWN | 4/4 nap stabil | — |
| §0.5 | Submit retry storm | ✅ RESOLVED (P2 volt) | orchestrator deployed | — |
| §9.1 | Pattern 5 stale context | ✅ RESOLVED | `304a64d` | CC ✓ |
| §9.8 | Első kohorsz -$651 (bug-torzított) | megfigyelés | CHAT ítélet | Chat |
| §9.9 | Reconcile 2/2 + IBKR connector | ✅ pozitív | — | — |

**A következő lépés prioritása**: (1) §0.11 Rész 3 deploy [P0] → (2) §9.2 days_held fix [P1] → (3) §9.3+9.5 ATR floor+ceiling [P1+P2] → (4) review-automatizáció 1. fázis. A §0.11 és §9.2 együtt: a swing pivot tézis tisztességes teszteléséhez **mindkettő elengedhetetlen** a Day 21 checkpoint előtt.
