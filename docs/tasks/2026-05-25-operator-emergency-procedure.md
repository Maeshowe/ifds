# Task — Operator Emergency Procedure (4 dokumentált pattern)

**Created**: 2026-05-25 (Log Review chat, CC javaslatára)
**Priority**: **P3** — dokumentációs task, NEM blokkol semmit
**Owner**: Log Review chat (Claude) — írás + frissítés. Tamás — jóváhagyás, kiegészítés, használat.
**Status**: REVIEWED v1.3 (Pattern 5b finomítás Day 14-i Sunday-skip incidens után, 2026-06-01)
**Becsült munka**: ~1.5 óra Log Review chat-ben + ~20 min CC kódbázis-verify
**Related**:
- `docs/master-reference/04-risks-and-open-questions.md` §0.4 (Error 354), §0.5 (Gateway timeout), §0.10 (Day 3 manual TWS bracket)
- `docs/tasks/2026-05-23-state-reconciliation-from-ibkr.md` (P0 task — az automatikus reconcile logika)
- `docs/review/2026-05-21-daily-review.md` §9, `docs/review/2026-05-22-daily-review.md` §9

---

## 1. Áttekintés

A swing pivot architektúra automatizált pipeline-ja **normál esetekben emberi beavatkozás NÉLKÜL** fut. **Bizonyos rendkívüli helyzetekben** azonban Tamás manuális beavatkozása szükséges — IBKR Workstation-en (TWS) vagy Mac Mini-n a terminálban. Ez a dokumentum **4 dokumentált pattern-t** rögzít a W21 (2026-05-18 → 2026-05-22) tapasztalatai alapján, hogy ezek a beavatkozások:

- **Reprodukálhatók** legyenek (lépésről lépésre)
- **Audit-trail**-jel rendelkezzenek (mit, mikor, miért)
- **Ne okozzanak state-divergence-t** a Python kódbázis (`swing_positions.json`, `cumulative_pnl.json`) és az IBKR (Positions, Trades, Orders) között

### Általános alapelv

**Minden manuális beavatkozás után KÖTELEZŐ** a `state/swing_positions.json` + `cumulative_pnl.json` és az IBKR állapot szinkronizálása.

- **Day 7+ napokon** ezt a `pt_monitor.py::_reconcile_state_from_ibkr` (P0 task Rész 1) **automatizálja** — a 22:00 CEST EOD eval-ban detektál minden divergence-t.
- **Day 6 előtti manuális beavatkozásokra** **utólagos retroaktív reconcile** szükséges (mint a `retroactive_reconcile_w21.py` script a P0 task Rész 2-ben).

### Mikor használd ezt a dokumentumot

- **A cron pipeline elakadt vagy hibázott** (`pt_submit_*.log` Error-okkal, Gateway disconnect, vagy egyéb)
- **Az IBKR oldalon valami "elcsúszott"** a state-tel (pl. élő child order amit nem ismersz fel)
- **Egy pozíciót gyorsan kell zárni** (pl. nem várt earnings event vagy makró-shock)

### Mikor NE használd

- **Rutinszerű napi events** (TP1/SL trigger, EOD close, MOC) — ezek **automatizáltak**, nem kell beavatkozás
- **Nem-blokkoló warning-ok** a logokban — `04-risks` §1-§3 P1-P2-P3 entry-k, ezek **nem emergency**

---

## 2. Pattern 1 — IBKR Error 354 (market data block)

### Mikor jelentkezik

A `pt_submit_YYYY-MM-DD.log` log-ban explicit Error 354 üzenet, pl.:

```
Error 354, reqId XXX: Requested market data is not subscribed.
Delayed market data is not available.
```

**Forrás**: az IBKR Paper Account market data subscription beállítása **NEM tartalmazza** a real-time L1 quote-ot bizonyos ticker-ekre (gyakran kevésbé likvid mid-cap-ekre). A `submit_orders.py` a `validate_contract` lépésnél ütközik.

**Történelmi incident**: 2026-05-20 (Day 3) — 3 ticker (VLO, ON, CNC) Error 354-be ütközött. Megoldás Tamás Workstation Configuration beállítása: "**Bypass Order Precautions for API Orders**" toggle bekapcsolva. **A jövőbeni napokon Error 354 valószínűleg NEM jelentkezik újra** ezzel a beállítással.

### Recovery procedure

#### 2.1 Diagnostic (a hibajelenség azonosítása)

1. **Logok ellenőrzése**: `tail -n 200 logs/pt_submit_$(date +%Y-%m-%d).log` — keress Error 354 sorokat
2. **IBKR Workstation kapcsolat ellenőrzése**: TWS megnyitva-e, csatlakoztatva-e a Paper Account-hoz (DUH118657)
3. **Workstation Configuration ellenőrzése**: Edit → Global Configuration → API → Settings → "Bypass Order Precautions for API Orders" toggle **bekapcsolva** kell legyen

#### 2.2 Resolution — Workstation Configuration

**Ha a toggle NEM bekapcsolva**:

```
TWS → Edit → Global Configuration → API → Settings
  ✓ "Bypass Order Precautions for API Orders"
  ✓ "Bypass Bond warning for API Orders" (opcionális)
  ✓ "Bypass No Overfill Protection precaution for destination Orders"
→ Apply → OK
→ TWS restart (Edit → Restart) — a beállítás csak újraindítás után érvényesül
```

Ezután a pipeline cron újrafutni fog automatikusan a következő percekben (heartbeat alapján), VAGY:

```bash
# Mac Mini terminálban (Tamás), kézi újrafutás:
cd ~/SSH-Services/ifds
python scripts/paper_trading/submit_orders.py --resume
```

A `--resume` flag a state-tudatos duplikáció-szűréssel megakadályozza, hogy ugyanazok a ticker-ek **kétszer kerüljenek beadásra**.

#### 2.3 Fallback — manuális TWS Order Entry (Day 3 minta)

**Ha a Configuration fix NEM működik** és az pozícionálás kritikus (pl. nagy S_j ticker, nem lehet kihagyni a napot):

1. **Olvasd ki** a `output/execution_plan_run_YYYYMMDD_*.csv` legutóbbi sorát (ticker, qty, planned entry, stop, TP1, TP2):
   ```bash
   tail -n 5 output/execution_plan_run_*.csv | column -t -s,
   ```

2. **TWS Order Entry** (kézzel, ticker-ként):
   - **Symbol**: pl. `VLO`
   - **Order Type**: `MKT` (market)
   - **Action**: `BUY`
   - **Quantity**: pl. `16`
   - **TIF**: `DAY`
   - **Bracket order template aktiválása** (ha biztonsági SL+TP1 szükséges):
     - **Profit Target** (LMT): a CSV `take_profit_1` érték (pl. `$276.05`)
     - **Stop Loss** (STP): a CSV `stop_loss` érték (pl. `$244.71`)
   - **Submit** + **Confirm**

3. **⚠️ FONTOS**: a TWS GUI Order Entry-vel feladott pozíciók **ORDER_REF üres lesz** (NEM `IFDS_SWING_{sym}`), ami **state-divergence-t okoz** a `swing_positions.json`-tól. Ez a Day 3-i minta, ami a W21-ben a Day 4-5-i autonóm bracket-trigger-eket okozta.

4. **Bejelentés a Log Review chat-nek**: rögzítsd a manuális entry-t (ticker, qty, ár, planned bracket szintek) — a Day 6+ napokon a `pt_monitor.py::_reconcile_state_from_ibkr` ezt automatikusan detektálja és a `swing_positions.json`-t frissíti, DE **csak ha a child bracket trigger-el** (Day 4 VLO SL és Day 5 ON TP1 minta).

#### 2.4 Post-emergency action

- **Day 7+ napokon**: a `pt_monitor.py::_reconcile_state_from_ibkr` automatikusan detektálja a state-IBKR divergence-t és frissíti a `swing_positions.json`-t + `daily_metrics`-t. Tamás-nak **nincs további tennivalója**.
- **Day 6 előtti napokon (pl. utólagos audit)**: futtasd a `retroactive_reconcile_w21.py` scriptet a hiányzó realized P&L rögzítéséhez.

### Audit-trail kötelező rögzítés

A Log Review chat **napi review** szakaszában rögzítendő:
- Manual entry időpontja (CEST)
- Ticker-ek + qty + tényleges fill ár
- Bracket szintek (ha feladott child SL/TP1)
- Reason (Error 354 vagy más)

Példa Day 3 review §0.4 entry: "VLO/ON/CNC manual TWS Order Entry submit, 2026-05-20 ~16:25 CEST, Error 354 workaround. Planned szintek + manual TWS bracket".

---

## 3. Pattern 2 — IBKR Gateway timeout → `--resume` flag használat

### Mikor jelentkezik

A `pt_submit_YYYY-MM-DD.log` log-ban explicit timeout vagy connection failure:

```
ERROR submit: API connection to 127.0.0.1:7497 timed out after 30s
ERROR submit: Failed to connect to IBKR Gateway (3/3 retries)
```

A `lib/retry_orchestrator.py::IBKRSubmitOrchestrator` automatikusan **3 retry-t** próbál exponential backoff-fal (0s, 30s, 90s — a `retry_delays`-tól függően), majd ha minden sikertelen → `SubmitExhaustedError` és `sys.exit(1)`.

**Történelmi incident**: 2026-05-20 (Day 3) — submit retry storm, 5 attempt 35 perc alatt (`04-risks` §0.5). A retry_orchestrator azóta P2 hotfix-szel javítva (`docs/tasks/2026-05-21-submit-retry-storm.md`).

### Recovery procedure

#### 3.1 Diagnostic (a Gateway állapotának felmérése)

1. **IBKR Gateway proc check** (Mac Mini terminál):
   ```bash
   pgrep -fl 'IB Gateway' || echo "Gateway NEM fut"
   lsof -i :7497 || echo "Port 7497 NEM nyitva"
   ```

2. **Gateway log check**: `~/Jts/launcher.log` és `~/Jts/ibgateway/XXXX/logs/`

3. **Heartbeat check**: `tail -n 20 logs/pt_heartbeat_monitor_$(date +%Y-%m-%d).log`

#### 3.2 Resolution — Gateway újraindítás

**Ha a Gateway nem fut**:
```bash
# Mac Mini terminálban (Tamás):
open -a "IBKR Gateway"
# vagy GUI-ból: Applications/IB Gateway/ibgateway-stable.app
```

Ezután belépés a Paper Account-ba (Tamás-féle saved credentials), majd **TWO-Factor Auth megerősítés** ha kéri.

#### 3.3 Resolution — `--resume` flag használat

**Miután a Gateway újra elérhető**:

```bash
cd ~/SSH-Services/ifds
python scripts/paper_trading/submit_orders.py --resume
```

A `--resume` flag:
- **Megkerüli a heartbeat STUCK alert-et** (a `last_submit_attempt.json` régi timestamp-jét)
- **State-tudatos duplikáció-szűrést** alkalmaz (az `IBKR positions` + `swing_positions.json` open list alapján)
- **Új cron cycle-t** indít a backoff reset-tel

#### 3.4 Post-emergency action

- A `--resume` futás után a `daily_metrics.json` automatikusan frissül a következő pipeline phase-ek által (Phase 4-6-EOD)
- **Telegram-on értesítést kapsz** a sikeres submit-ról (`📈 IFDS Swing Submit — YYYY-MM-DD`)

### Audit-trail rögzítés

A Log Review chat napi review §3 "Pipeline Log Review" szakaszában rögzítendő:
- Gateway timeout időpontja
- Recovery időpontja (Gateway restart + `--resume`)
- Submit attempt count (`--resume` cycle szerint)

---

## 4. Pattern 3 — Bracket SL/TP1 cleanup (manuális TWS cancel)

### Mikor jelentkezik

Az IBKR Workstation **Orders** ablakban élő (PreSubmitted vagy Submitted állapotú) child SL vagy TP1 order, ami:

- **Nem a swing pivot architektúra része** (a `submit_swing_market_only` csak parent MKT-t ad be, NINCS child order)
- **A `swing_positions.json` mental szintjeitől eltér** (planned-alapú vs tényleges-fill-alapú)
- **Veszélyes az autonóm trigger lehetősége** (mint a Day 4-5-i VLO SL és ON TP1 esetek)

**Történelmi incident**: 2026-05-22 (Day 5) — Day 3-i manuális TWS bracket-ek után a CNC SELL Stop $55,50 + Limit $61,89 GTC élő order-ek. A Log Review chat 2026-05-25 reggeli IBKR Orders ablak elemzése után Tamás kézzel cancellálta (08:26 CEST, IBKR Orders ablak: 2 × Cancelled).

### Recovery procedure

#### 4.1 Diagnostic (élő child order-ek azonosítása)

**IBKR TWS** → **Account Window** → **Orders** tab → **Filter**: `All Orders`

Keresse az alábbi mintát:
- **SELL Stop** order GTC TIF, **nem a `swing_positions.json` `stop_level`** szintjén
- **SELL Limit** order GTC TIF, **nem a `swing_positions.json` `tp1_level` / `tp2_level`** szintjén
- **ORDER_REF üres** vagy random TWS-generált string (NEM `IFDS_*` prefix)

#### 4.2 Resolution — manuális cancel

**Minden élő child order-re egyenként**:

1. **Right-click** az order soron → `Cancel Order`
2. **Confirm** dialógus → `OK`
3. **Verify**: az Order status `Cancelled`-re változik (a 2026-05-25-i CNC eset módja)

**⚠️ FIGYELEM**: csak a **child order-eket** cancelld, NE a parent positions-t. Ha véletlenül a positiont zárod le → state-divergence + nem várt realized P&L.

#### 4.3 Verify state consistency

A cancel után:

1. **IBKR Positions** ablak ellenőrzése: a ticker továbbra is szerepel (parent position megmaradt)
2. **IBKR Orders ablak**: csak Cancelled státuszú entry-k az adott ticker-re
3. **`swing_positions.json` ellenőrzése**: a ticker `qty_remaining > 0`, `tp1_hit: false`, `trail_sl: null` — vagyis mental-stop módban van

#### 4.4 Post-emergency action

- A Day 7+ napokon a `pt_monitor.py::_reconcile_state_from_ibkr` továbbra is figyelni fogja a state-IBKR konzisztenciát
- **Új P3 alert** lehetőség: ha a `_reconcile_state_from_ibkr` **élő child order-eket észlel** a swing pivot architektúrában (ahol nem kéne legyen), **WARNING** Telegram-ra a Tamás-i manual cancel kérése (lásd §7.1 backlog)

### Audit-trail rögzítés

A Log Review chat napi review §6 "Anomalies / Notes" szakaszában rögzítendő:
- Detected child order(s): ticker, type (Stop/Limit), level, TIF
- Cancel időpont (CEST)
- IBKR Orders ablak screenshot ID (a `04-risks` §0.10 mintára)

---

## 5. Pattern 4 — `nuke.py` + manual position cleanup

### Mikor jelentkezik

**Rendkívüli helyzetek**, ahol a pipeline state vagy az IBKR pozíció **inkonzisztens**, és a `pt_monitor.py::_reconcile_state_from_ibkr` automatikus megoldás **NEM elég**:

- **Strukturális bug** a pipeline-ban, ami minden napi futáson hibás state-et generál
- **Manuális test cleanup** (mint Day 3-i `IFDS_DEBUG_VLO` 1+1 share Tamás teszt — `04-risks` §0.4-hez kapcsolódó)
- **Pánikhelyzet**: nem várt makró-event, kényszerű full portfolio close

**Történelmi incident**:
- 2026-05-20 (Day 3) ~20:57:08 CEST: VLO 1 BOT @ $254.08 (`IFDS_DEBUG_VLO`) → 20:58:51 SLD @ $253.19 (`IFDS_DEBUG_VLO_CLEANUP`) — Tamás teszt
- Korábbi legacy: HYMC -140 SHORT bug az 5. bracket SL trigger esetén (2026-05-14 Day 63 milestone, `nuke.py --positions` + manuális IBKR TWS bracket order cancel)

### Recovery procedure

#### 5.1 Diagnostic — mit nuke-olunk

**Lépésről lépésre**:

1. **State snapshot** (BACKUP készítés mindenből — kötelező):
   ```bash
   cd ~/SSH-Services/ifds
   BACKUP_DATE=$(date +%Y-%m-%d_%H%M%S)
   mkdir -p state/backups/$BACKUP_DATE
   cp state/swing_positions.json state/backups/$BACKUP_DATE/
   cp scripts/paper_trading/logs/cumulative_pnl.json state/backups/$BACKUP_DATE/
   cp -r state/daily_metrics state/backups/$BACKUP_DATE/
   ```

2. **IBKR Positions ellenőrzése** (mit lát az IBKR pre-flight health check-en):
   ```bash
   python scripts/paper_trading/check_gateway.py
   ```
   A `check_gateway.py` **NEM fogad argumentumokat** — csak egy connectivity smoke (clientId=17, 3s timeout, 1 retry). A részletes IBKR pozíció-listához használd a TWS GUI **Account Window → Positions** tab-ot vagy egy egyszeri Python REPL-t:
   ```bash
   python -c "from ib_async import IB; ib = IB(); ib.connect('127.0.0.1', 7497, clientId=99); print(ib.positions()); ib.disconnect()"
   ```

3. **Egyezzen a mit-nuke-olunk-szándékkal**:
   - **⚠️ FONTOS**: a `nuke.py` **CSAK az IBKR oldalt** kezeli (orders + positions API hívásokon át). **A state fájlokhoz EGYÁLTALÁN NEM nyúl** (`swing_positions.json`, `cumulative_pnl.json`, `daily_metrics/`). State fájlok manuális reset-jéhez NEM a `nuke.py` a megfelelő tool — lásd §5.4 alább.
   - **Csak IBKR orders cancel** (`--orders`): minden élő order (parent + child + GTC) cancel, IBKR pozíciók ÉRINTETLENÜL
   - **Csak IBKR pozíciók zárás** (`--positions`): minden nyitott IBKR pozíció MKT SELL-vel zárva, élő order-ek ÉRINTETLENÜL
   - **Default (flag nélkül)**: **MINDKETTŐ** — orders cancel + positions close

#### 5.2 Resolution — `nuke.py` futtatás

**Verified flag-tábla** ([scripts/paper_trading/nuke.py:51-54](../../scripts/paper_trading/nuke.py#L51-L54)):

| Flag | Hatás | Use case |
|------|-------|----------|
| (nincs flag) | orders cancel + positions close | Full pánik-zárás (default) |
| `--orders` | csak orders cancel | Orphan bracket cleanup tömegesen (Pattern 3 alternative) |
| `--positions` | csak positions close | Pozíció-pánik, orders ÉRINTETLENÜL |
| `--dry-run` | csak audit print | Bármelyik fenti móddal kombinálható |

**Példák**:

```bash
# Csak audit (semmi action) — minden esetben javasolt ELŐSZÖR
python scripts/paper_trading/nuke.py --dry-run

# Csak orders cancel — orphan bracket tömeges cleanup
python scripts/paper_trading/nuke.py --orders --dry-run
python scripts/paper_trading/nuke.py --orders

# Csak positions close — pozíció-pánik (orders maradnak)
python scripts/paper_trading/nuke.py --positions --dry-run
python scripts/paper_trading/nuke.py --positions

# Default — mindkettő (orders cancel + positions close)
python scripts/paper_trading/nuke.py --dry-run
python scripts/paper_trading/nuke.py
```

**⚠️ FIGYELEM**: a `nuke.py --positions` **NEM cancellálja** az IBKR-ben élő child bracket order-eket. Ha vannak (mint a 2026-05-14-i HYMC SHORT bug eset), futtasd ELŐSZÖR `--orders`-szel (vagy default móddal, ami mindkettőt csinálja), VAGY utána Pattern 3 (manual TWS cancel).

#### 5.3 Post-nuke recovery

1. **Backup verify**: `ls -lh state/backups/$BACKUP_DATE/`
2. **IBKR Positions verify** (`nuke.py` után): TWS GUI → Account → Positions tab, várt érték `0` pozíció (ha `--positions` vagy default futott)
3. **IBKR Orders verify**: TWS GUI → Account → Orders tab, várt: minden élő order `Cancelled` státusz (ha `--orders` vagy default futott)
4. **State-fájl konzisztencia**: a `nuke.py` futtatása **divergence-t okoz** a state fájl és az IBKR között (state szerinti pozíciók "nyitottnak" mutatkoznak, IBKR-ben már nincsenek). Ez a divergence a következő `pt_monitor.py` EOD eval-on `_reconcile_state_from_ibkr` által **automatikusan korrigálódik** (Day 7+). Day 6 előtti `nuke.py` futtatás után **`retroactive_reconcile_w21.py`-szerű utólagos manuális reconcile** szükséges.

#### 5.4 State fájl reset (NEM `nuke.py`-vel)

Ha **kizárólag a `state/swing_positions.json` vagy `cumulative_pnl.json` reset** a cél (IBKR pozíciók érintetlenül), a megfelelő tool:

- **Egyetlen ticker korrekció** (pl. retroaktív SL/TP1 rögzítés): `scripts/admin/retroactive_reconcile_w21.py` mintára egyedi script
- **Teljes újraindítás** (pl. új Day 1 reset): manuális Python REPL vagy egyedi script — **NEM ajánlott prod-on**, csak fejlesztői környezetben

A `nuke.py`-nek **nincs** state-reset capability-je és **nem is tervezett** hogy legyen (separation of concerns: `nuke.py` = IBKR oldal, `retroactive_reconcile_w21.py` típusú script-ek = state oldal).

### Audit-trail kötelező rögzítés

A `nuke.py` automatikusan logol:
- `logs/pt_nuke_YYYY-MM-DD.log` — minden művelet (mit, hány ticker, milyen state)
- Telegram értesítés: `🔧 NUKE — Day N: M positions closed, state reset`

**Log Review chat** napi review §6 vagy egy dedikált `docs/journal/YYYY-MM-DD-nuke-event.md` fájlban rögzítendő:
- Trigger reason (mi miatt kellett a nuke)
- Backup helye (`state/backups/$BACKUP_DATE/`)
- Tényleges P&L impact (a `nuke.py` SELL fills összesítése)

---

## 5b. Pattern 5 — Phase 1-3 weekly cron silent-fail (`phase13_ctx.json.gz` stale)

### Mikor jelentkezik

A vasárnap 22:00 CET `0 22 * * 0` cron (`scripts/deploy_daily.sh --phases 1-3`) **sikertelenül** vagy **részben** lefutott, és a `state/phase13_ctx.json.gz` mtime régebbi mint 24-48 óra. Detektálási csatornák:

**Automatikus** (Day 90+ alapértelmezett):
- `scripts/check_phase13_freshness.py` cron `0 23 * * 0` — vasárnap 23:00, 1 órával a cron után
- Telegram WARNING template:
  ```
  ⚠️ Phase 1-3 context STALE — mtime <YYYY-MM-DD HH:MM>, age <H>h
  A vasárnapi 22:00 heti macro cron silent-fail gyanú.
  Manuális futtatás: ./scripts/deploy_daily.sh --phases 1-3
  ```

**Manuális diagnose**:
```bash
ls -la state/phase13_ctx.json.gz
tail -50 logs/cron_$(date +%Y%m%d -v-monday)_22*.log  # legutóbbi vasárnap
grep -E 'Traceback|Error|AttributeError' logs/cron_*_22*.log
```

**Történelmi incident**: 2026-04-03 (`e9d617a2`) — NYSE calendar bevezetésekor a `runner.py:107` `EventType.PIPELINE_COMPLETE` típuskeresési hibát rejtett (nem létező enum value). Latens 7 hétig, mert (a) csak a NYSE-closed-day kódútban tört, (b) tesztkörnyezet globálisan deaktiválta a guardot (`conftest.py`: `IFDS_SKIP_TRADING_DAY_GUARD=1`), (c) a vasárnap esti cron stderr/stdout-ja log-fájlba ment, manuálisan nem nézte senki. **Első éles crash**: 2026-05-24 22:00. **Detektálva**: 2026-05-26 (Day 7) reggel, Phase 1-3 context 8 napos. **Fixed**: `EventType.PIPELINE_COMPLETE` → `EventType.PIPELINE_END` (runner.py:107) + 4 új regression teszt (`tests/test_runner_skip_path.py`).

### Recovery procedure

#### 5b.1 Diagnostic (mit jelent a stale Phase 1-3 context)

**Hatás**:
- A **vasárnap esti BMI** (Phase 1) — `bmi_history.json` lehet up-to-date in-place writeból, de a **regime classification** stale (a guard előtti save-ből)
- A **universe szűrés** (Phase 2) — szigorúan stale, a Phase 4 a 8 napos universe alapján szűr
- A **sector rotation** (Phase 3) — szigorúan stale, a Phase 4 sector adjustment 8 napos sector ranking alapján számol
- A **hétközi intraday** (`30 14 * * 1-5` Phase 4-6) **stale Phase 1-3 context-szel** fut, hibás jeleket termelhet

**Verify parancsok**:
```bash
# Mac Mini-n:
ls -la state/phase13_ctx.json.gz state/bmi_history.json state/sector_history.json
# várt: mtime mindhárom legutóbbi VASÁRNAP 22:05 körül (Phase 1-3 success esetén)
```

#### 5b.2 Resolution — manuális Phase 1-3 futtatás

**Hétköznap reggeli (10:00 előtti) re-run**:

```bash
# Mac Mini terminálban (Tamás):
cd ~/SSH-Services/ifds

# 1. Bug-fix deploy verify (kötelező — különben ujra crash):
git log --oneline -5 | grep -E 'PIPELINE_END|skip_path'
# várt: legutóbbi commit hash a fix-szel (pl. fix(runner): EventType.PIPELINE_END)

# 2. Manuális Phase 1-3 futtatás trading-day guard-dal:
./scripts/deploy_daily.sh --phases 1-3 2>&1 | tee logs/manual_phase13_$(date +%Y%m%d_%H%M%S).log

# 3. Verify Phase 1-3 context frissült:
ls -la state/phase13_ctx.json.gz
# várt: mtime aktuális (mai dátum)

# 4. Verify a context tartalmaz friss BMI + universe + sector rankings:
python -c "import gzip, json; d=json.load(gzip.open('state/phase13_ctx.json.gz')); print(f'tickers={len(d.get(\"universe\", []))}  bmi={d.get(\"bmi_regime\", \"?\")}  sectors={len(d.get(\"sector_rankings\", []))}')"
```

**Trading-day NYSE-closed alatt** (vasárnap esti weekly cron, vagy holiday) — KÖTELEZŐ env-prefix:

```bash
# IFDS_SKIP_TRADING_DAY_GUARD override — a Sunday cron SZÁNDÉKA pont ez
IFDS_SKIP_TRADING_DAY_GUARD=1 ./scripts/deploy_daily.sh --phases 1-3
```

**Mikor kell ez az override**:
- **Vasárnap esti weekly Phase 1-3 cron** (`0 22 * * 0` Mac Mini crontab) — produkciós, állandó. A vasárnap NYSE-closed nap, és a runner trading-day guard-ja egyébként SKIP-elné a futást. A 2026-04-03-i `e9d617a2` (NYSE calendar) kezdetben crash-elte a SKIP path-t (`PIPELINE_COMPLETE` enum bug); a Day 7-i `304a64d` fix óta a SKIP **tisztán** lefut, DE pont ettől **a context stale marad** — a runner kilép, és a Phase 1-3 nem termel friss `phase13_ctx.json.gz`-t. Az override visszaadja a vasárnapi cron eredeti szándékát: a következő heti BMI + universe + sector ranking generálását.
- **Hétközi manuális backfill** (Day 7 vagy Day 14 minta) — ad-hoc.

**⚠️ Hétközi (1-5) production cron-ban NEM szabad használni**: ott a guard helyes (NYSE holiday-on ne pazaroljon API rate-limitet).

**Második előfordulás (Day 14, 2026-05-31)**: a `304a64d` óta a SKIP nem crash-el, csak `[SKIP] NYSE closed today` log + Telegram-üzenet → a 23:00 freshness check WARNING-ot küldött, a context 5 napos lett (5/26 → 5/31). Detektálva 2026-06-01 reggel. Crontab patch: a `0 22 * * 0` sorba `IFDS_SKIP_TRADING_DAY_GUARD=1` env-prefix beillesztve (`scripts/crontab.md` 36. sor). Manuális Phase 1-3 refresh ugyanaznap 13:34-kor → friss context a hétfő 14:30 intraday-hez.

#### 5b.3 Post-recovery action

**Ha a stale Phase 1-3 context aktív intraday-t érintett**:

- A pipeline-output (`output/execution_plan_*.csv`) **ne legyen automatikusan submitted** újra (a `submit_orders.py` már lefutott a stale context alapján)
- **Manuális TWS pozíció review**: az adott napi entries (pl. AMH/EOG/AKAM) **stale sector ranking alapján** lettek scored — a pozíciók megmaradnak (mental-stop architektúra → bracket nem trigger autonóm), DE a Day 8+ EOD evals **a frissített Phase 1-3 context-szel** számolnak
- **Journal entry** + **`04-risks` §X új P3 entry** (rekord audit-trail)

#### 5b.4 Preventive monitoring (Day 90+ alapértelmezett)

**Cron** (`crontab -l` listáz):
```cron
# Vasárnap 23:00 — Phase 1-3 freshness check (1 órával a 22:00 cron után)
0 23 * * 0 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/check_phase13_freshness.py
```

A script:
- Olvassa a `state/phase13_ctx.json.gz` mtime-t
- Ha age > 48h (configurable) → Telegram WARNING
- NEM auto-fix-el (Tamás döntés)

### Audit-trail kötelező rögzítés

A Log Review chat napi review §3 vagy egy dedikált `docs/journal/YYYY-MM-DD-phase13-stale-incident.md`-ben rögzítendő:
- Stale detection időpont (CEST)
- Detection forrás (Telegram WARNING vs manuális grep)
- Manuális re-run időpont + parancs + log fájl referencia
- Affected intraday futás(ok) (`logs/cron_intraday_*_143000.log` ticker output)
- Affected position(s) — ha a stale alapján submitted (`logs/pt_submit_*.log`)
- Bug root-cause (kód-szintű — pl. enum mismatch, env var missing, API timeout)

---

## 6. Post-emergency állapot-ellenőrzési lista

**Minden manuális beavatkozás után** kötelezően ellenőrizendő (Tamás vagy a Log Review chat következő session-jében):

### 6.1 IBKR konzisztencia

- [ ] **IBKR Positions** ablakban a tényleges nyitott pozíciók száma egyezik a `swing_positions.json` `qty_remaining > 0` count-jával
- [ ] **IBKR Orders** ablakban **nincs orphan** child SL/TP1/TP2 order (csak Cancelled vagy Filled státuszú entry-k)
- [ ] **IBKR Trades** ablakban (Last 6 Days) minden SLD entry-nek **MEGFELELŐ realized P&L** logolva van a `cumulative_pnl.json daily_history`-ban

### 6.2 State-fájl konzisztencia

- [ ] **`swing_positions.json`** — minden nyitott pozíció `qty_remaining > 0`, `closed_at: null`, `close_reason: null`
- [ ] **`daily_metrics/YYYY-MM-DD.json`** — `pnl.gross + pnl.commission == pnl.net`, `trades.details` lista nem üres ha volt closing event
- [ ] **`cumulative_pnl.json daily_history`** — `tp1_hits + sl_hits + tp2_hits + trail_hits + moc_hits + loss_exit_hits >= trades count`

### 6.3 Pipeline log konzisztencia

- [ ] **`logs/pt_submit_*.log`** — utolsó futás `INFO` (NEM `ERROR` vagy `WARNING`) heartbeat-tel zárul
- [ ] **`logs/pt_monitor_*.log`** — utolsó EOD eval `[SWING EOD] Evaluated N positions — M exit flags set` sorral
- [ ] **`logs/pt_heartbeat_monitor_*.log`** — `[OK] submit_orders heartbeat OK` vagy a sikertelen attempt explicit detektálva

### 6.4 Telegram audit

- [ ] **Telegram channel** értesítések megfelelnek a tényleges events-nek (NEM hiányzik értesítés, NEM duplikálva)

---

## 7. Új CC tasks következménye ezen procedure-ből

A 4 pattern dokumentálása **új P2-P3 CC task-okat** indokolhat:

### 7.1 Pattern 3 detect — orphan child order WARNING

**Új CC scope**: a `pt_monitor.py::_reconcile_state_from_ibkr` (P0 task Rész 1) **bővítendő** egy ellenőrzéssel:

```python
# Pseudo-code, pt_monitor.py
def detect_orphan_child_orders(ib, swing_state):
    """Detect IBKR child orders that don't correspond to the mental-stop architecture.

    A swing-pivot pozícióhoz NEM tartozhat IBKR SELL Stop vagy SELL Limit order
    (a mental-stop architektúra szerint). Ha mégis van élő child order:
    - WARNING Telegram-ra
    - WARNING `pt_monitor` log-ba
    - NEM cancellálunk automatikusan (kockázat-csökkentés — Tamás döntése)
    """
    orphans = []
    for trade in ib.openTrades():
        order = trade.order
        if order.action == "SELL" and order.orderType in ("STP", "LMT"):
            sym = trade.contract.symbol
            if sym in swing_state.tickers:  # swing-pivot ticker
                orphans.append({
                    "ticker": sym,
                    "type": order.orderType,
                    "price": order.auxPrice if order.orderType == "STP" else order.lmtPrice,
                    "tif": order.tif,
                    "order_ref": order.orderRef or "<empty>",
                })
    if orphans:
        msg = "⚠️ ORPHAN CHILD ORDERS detected:\n"
        for o in orphans:
            msg += f"  - {o['ticker']}: {o['type']} @ ${o['price']} {o['tif']} (ref: {o['order_ref']})\n"
        msg += "Manual TWS cancel needed (Pattern 3 in 2026-05-25-operator-emergency-procedure.md)"
        telegram.send(msg)
        logger.warning(msg)
```

**Effort**: ~30 min CC (a P0 task Rész 1 részeként integrálva).

### 7.2 Pattern 4 — `nuke.py` enhancement

**Új P3 CC scope**: a `nuke.py --positions` **detektálja és cancellálja** az élő child bracket order-eket **ELŐSZÖR**, **MIELŐTT** zárná a pozíciókat. Ez megoldja a Day 5-i HYMC SHORT bug pattern-t (a `nuke.py` zárta a pozíciót, de a bracket SL külön triggert generált és short pozíciót nyitott).

**Effort**: ~1 óra CC.

**Status**: backlog idea, NEM része a 2026-05-23 P0 task scope-jának.

---

## 8. Referenciák

### A 4 pattern forrásai

| Pattern | Forrás | Dokumentum |
|---------|--------|------------|
| Pattern 1 (Error 354) | Day 3 incident | `04-risks` §0.4 |
| Pattern 2 (Gateway timeout) | Day 3 incident | `04-risks` §0.5 + `docs/tasks/2026-05-21-submit-retry-storm.md` |
| Pattern 3 (bracket cleanup) | Day 4-5 felfedezés + Day 6 CNC cancel | `04-risks` §0.10 + `docs/review/2026-05-22-daily-review.md` §9 |
| Pattern 4 (`nuke.py`) | Day 63 milestone HYMC eset (2026-05-14) | `04-risks` §0.4 legacy entry + `docs/decisions/2026-05-14-day63-decision-outcome.md` |
| Pattern 5 (Phase 1-3 cron silent-fail) | 2026-05-24 vasárnap esti cron crash + 2026-05-26 Day 7 reggeli detektálás | `e9d617a2` regression commit, `runner.py:107` fix-szel deploy, `tests/test_runner_skip_path.py` 4 regression teszt |

### Kapcsolódó task-ok

- **P0**: [`docs/tasks/2026-05-23-state-reconciliation-from-ibkr.md`](2026-05-23-state-reconciliation-from-ibkr.md) — automatikus reconcile + retroaktív Day 4-5 rögzítés
- **P2**: [`docs/tasks/2026-05-21-submit-retry-storm.md`](2026-05-21-submit-retry-storm.md) — autonóm retry logic (Pattern 2)
- **P1**: [`docs/tasks/2026-05-19-ibkr-gateway-monitoring.md`](2026-05-19-ibkr-gateway-monitoring.md) — Gateway monitoring + Telegram alerts

### A `nuke.py` jelenlegi capabilities (VERIFIED 2026-05-25 by CC)

**Lokáció**: [`scripts/paper_trading/nuke.py`](../../scripts/paper_trading/nuke.py) (159 sor, 1 `main()` function)

**Verified flag-ek** ([nuke.py:51-54](../../scripts/paper_trading/nuke.py#L51-L54)):

| Flag | Hatás | Notes |
|------|-------|-------|
| (nincs flag) | orders cancel + positions close | Default (lib defaults: both true) |
| `--orders` | csak orders cancel | `do_orders=True, do_positions=False` |
| `--positions` | csak positions close | `do_orders=False, do_positions=True` |
| `--dry-run` | audit print, NEM submit | Bármelyikkel kombinálható |

**KRITIKUS**: `nuke.py` **CSAK** IB API hívásokkal dolgozik (`ib.cancelOrder()`, `ib.placeOrder(MKT SELL)`). **Semmilyen** state fájlt **NEM** ír/olvas:

```bash
$ grep -E 'swing_positions|cumulative_pnl|daily_metrics|state/' scripts/paper_trading/nuke.py
# (zero match)
```

State fájl reset-hez NEM ez a tool — lásd §5.4.

### Egyéb script-ek verified state (2026-05-25 by CC)

| Script | Verified | Notes |
|--------|----------|-------|
| `submit_orders.py` | ✓ | `--dry-run`, `--test-connection`, `--file`, `--override-circuit-breaker`, `--override-witching`, `--resume` |
| `check_gateway.py` | ✓ | **NINCS argparse** — health check only, clientId=17, 3s timeout |
| `pt_monitor.py::_reconcile_state_from_ibkr` | ✓ | Private function (underscore prefix), [pt_monitor.py:256](../../scripts/paper_trading/pt_monitor.py#L256) |
| `lib/retry_orchestrator.py::IBKRSubmitOrchestrator` | ✓ | + `SubmitExhaustedError`, `retry_delays` |
| `submit_orders.py::submit_swing_market_only` | ✓ | [submit_orders.py:195](../../scripts/paper_trading/submit_orders.py#L195) |

---

## 9. Verziók és frissítések

| Verzió | Dátum | Változtatás | Aki |
|--------|-------|-------------|------|
| v1 (DRAFT) | 2026-05-25 | Kezdő verzió, 4 pattern W21 tapasztalat alapján | Log Review chat |
| **v1.1 (REVIEWED)** | **2026-05-25** | **CC kódbázis-verify: `nuke.py` flag-ek javítva (`--state-only`/`--full` fikció törölve), `check_gateway.py --verbose` flag törölve (nincs argparse), `reconcile_state_from_ibkr` → `_reconcile_state_from_ibkr` (private prefix), §5.4 új szekció (state reset NEM `nuke.py`-vel)** | **CC** |
| **v1.2** | **2026-05-26** | **Pattern 5 hozzáadás (Phase 1-3 weekly cron silent-fail) — 2026-05-24-i éles crash incident alapján. §8 forrás-tábla bővítés. `EventType.PIPELINE_COMPLETE` → `_END` fix runner.py:107 + 4 regression teszt (`tests/test_runner_skip_path.py`)** | **CC** |
| **v1.3** | **2026-06-01** | **Pattern 5b §5b.2 finomítás — a Day 14-i (2026-05-31) második incidens után: a `304a64d` SKIP-fix óta a vasárnapi cron tisztán fut, DE a guard miatt context-et nem termel. Crontab patch: `IFDS_SKIP_TRADING_DAY_GUARD=1` env-prefix a `0 22 * * 0` Sunday cron sorba. `scripts/crontab.md` 36. sor frissítve.** | **CC** |
| TBD | TBD | Tamás felülvizsgálat + kiegészítés | Tamás |

### Tervezett frissítések (Day 7+ alapján)

- **Pattern 1 (Error 354)**: ha a Workstation Configuration fix tartós, **a §2.3 manual TWS fallback** archive-only referenceként megmarad (mint a Day 4-5-i autonóm bracket-trigger forrás-magyarázat), DE a §2.1-§2.2 (Configuration fix) **kiemelt fókuszt kap** mint elsődleges recovery path. **Hivatkozás**: `04-risks` §0.10 (Day 3 manual TWS bracket consequence).
- **Pattern 3 (bracket cleanup)**: a P0 task Rész 1 orphan-detect logika után **a manual cancel** ritkábban szükséges. **Backlog szétbontás** (W22-W23): (a) **detect-only** WARNING Telegram + manual cancel, ~30 min CC integrálva a Rész 1 iterációba; (b) **auto-cancel mode** config flag mögött, ~1.5h CC + extensive testing, **csak ha (a) 5+ napi stabil** és Tamás explicit kéri.
- **Pattern 4 (`nuke.py`)**: a P3 enhancement (orphan bracket cancel a nuke előtt) után **ezt a pattern-t egyszerűsíteni lehet** (kevesebb manuális lépés).
- **⭐ Új Pattern 5 javaslat (W22 backlog)**: IBKR Gateway 2FA timeout recovery procedure (mobile prompt timeout esetén). **NEM volt W21-i incident**, P3 nice-to-have.
- **⭐ §5.3 (post-nuke recovery) kockázat-leírás bővítés (v1.2 TODO)**: stale state-pattern Day 7 előtti `nuke.py` futtatás esetén — **mennyi időre veszélyes** a state ↔ IBKR divergence? Pl. ha Day 4-en futtatod a `nuke.py`-t és 22:00-ig nem fut `_reconcile_state_from_ibkr` mert még Day 7 előtt vagy → a `pt_submit` Day 5 reggel **stale state** alapján skipping-el ticker-eket. Bővítendő részletes timing-diagram-mal.
- **CC kódbázis-verify rule (v1.2 TODO)**: a Log Review chat-i `.claude/rules/ifds-rules.md`-ben javasolt új rule rögzíteni: **"ha technikai flag-eket vagy command signature-öket dokumentálok, KÖTELEZŐ beolvasni a tényleges `argparse` blokkot vagy a script első 50 sorát"**. Ez a v1 → v1.1 átmenet 6 ténybeli hiba ismétlésének megelőzése. **Dev chat döntés szükséges**: jóváhagy-e + ki implementálja az ifds-rules.md update-t.

---

**A dokumentum vége.**

**Használati javaslat**: ez a dokumentum **gyors-lookup** céllal készült (Tamás emergency-ben). Tartsd elérhetőnek a Mac Mini és MacBook-on egyaránt. Ha új emergency pattern jelentkezik (W22-W30 időszakban), a Log Review chat **bővíti** ezt a dokumentumot.
