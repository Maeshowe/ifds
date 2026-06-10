# IFDS — Permanent Rules (CC mindig olvassa)

Ezek a szabályok a CONDUCTOR learnings-ből kerültek ide (2026-02-26 migráció).
Forrás: `.conductor/memory/project.db` — learnings tábla.

---

## CC edit-stratégia — kis, egyenkénti editek a nagy multi-edit payload helyett (correction, 2026-06-10)

A szerkesztő-connector **lefagy** a nagy, többszerkesztéses `edit_file` payloadoknál
(sok hunk egy hívásban); a **kis, egyenkénti `Edit`-ek stabilan mennek**.

**Szabály:** ne kötegelj sok hunkot egyetlen nagy edit-payloadba — bontsd
**egyenkénti, fókuszált `Edit` hívásokra** (egy logikai változás / hívás). Ez a
meglévő "egyszerre max ~4 fájl egy batch-ben" higiénia kiegészítése a **hunk-szám**
dimenzióval: nem csak a fájlszám, a **payload-méret** is számít. Egy nagy
többfájlos refaktort inkább több, kis editre tagolj, mintsem egy óriás payloadra.

**Példa-megfelelés:** a 2026-06-10-i signal_attribution + entry_score-perzisztálás
(SwingPosition mező + submit_orders ×2 + close_positions + pending_exits) **5+ külön
kis Edit**-tel ment stabilan, fagyás nélkül.

---

## Cumulative-drift diagnózis — timestamp-reconciliation + baseline-carry ELŐbb, mint "tracking-bug" (rule, 2026-06-06)

Egy `cumulative_drift` flag (tracked cumulative + unrealized ≠ NetLiq − initial)
**TILOS** azonnal "tracking-bug"-ként kezelni. Először a teljes DAYS_30
broker-reconciliation kell, mert a drift gyakran **baseline-reset artifact**,
nulla tracking-hibával.

**Szabály:**

1. **Timestamp-alapú (NEM dátum-alapú) reconciliation** a reset-pontig: a
   tracked cumulative-ot a `get_account_trades` `realized_pnl` összegéhez kell
   mérni, ahol a trade `trade_time` **szigorúan a `reset_at` után** van. A
   dátum-bucket sum téves: a reset napján (5/18) lehet pre-reset fill
   (pl. AVDL.CVR CVR settlement 04:00Z, a 10:05Z reset ELŐTT, −$47.92), amit a
   tracking helyesen kizár, de a date-sum tévesen bevon.

2. **Pre-pivot cash-carry ellenőrzés**: az IBKR paper account a pivotnál NEM
   feltétlenül flat-$100k-ra resetel. Rekonstruáld a cash-t a post-reset
   trade-lábakból (`100000 + Σ(SELL net) − Σ(BUY net) − Σ comm`) és vesd össze
   a tényleges `total_cash_value`-val — a különbség a carry (2026-06-06: **+$208.37**,
   az account ~$100,208-ra resetelt).

3. **Accrued interest**: `NetLiq − cash − pos_mkt` = credit-interest a
   cash-egyenlegen (nem realized P&L; 2026-06-06: $12.89).

4. **Penny-szintű identitás** a verdikt előtt:
   `NetLiq = 100000 + carry + tracked_realized + unrealized + accrued`.
   Ha záródik → nincs tracking-bug; a drift könyvelési artifact → `BASELINE_OFFSET_USD`
   a cross-checkbe (nem recorder-fix).

**Példa-megfelelés:** a 6/6-i P0 `cumulative_drift −$218` → a tracked +245.25
**pontosan** == post-reset broker realized; a drift = carry(+208.37) + accrued(+12.89).
Nulla post-pivot tracking-hiba.

**Referencia:** `docs/analysis/cumulative-drift-investigation-2026-06-08.md`,
`generate_review.BASELINE_OFFSET_USD`, commit `7f43c2e`.

---

## Rate-limit-érzékeny változtatás — live smoke a teljes terheléssel (rule, 2026-05-14)

Új rate-limit-érzékeny kódút bevezetése (per-ticker külső API hívás, batch
→ per-instance switch, semaphore-tuning, parallel → sequential refactor, stb.)
ESETÉN **TILOS** extrapolált smoke-test-tel élesíteni. Minden ilyen
változtatás előtt **kötelező egy live smoke a tényleges production
terheléssel** (méret, párhuzamosság, semaphore-méret).

**Példa-sértés:** a 2026-05-10-i `9a169b9` commit `UWBatchDarkPoolProvider`
→ `UWDarkPoolProvider` switch-et deployolt egy **20-ticker × 300ms = 6s
serial** smoke alapján "≈ 250 hívás/nap, rendben"-re extrapolálva. A
production valójában **1425 ticker × sem_uw=5 parallel = ~17 req/s burst**-öt
generált → **304 HTTP 429** az első élesi futáskor. Két nap utáni iteratív
hotfix kellett (`90cf5b4` two-pass + `1f0ffb9` sequential+delay) ahhoz, hogy
0-szerű hibarátára érkezzen a rendszer.

**Szabály:**

1. **A smoke-test paramétereinek azonosnak kell lenniük a production
   paraméterekkel:**
   - Ticker-szám: production `passed` vagy `analyzed` size (NEM "20 minta")
   - Párhuzamosság: production `sem_uw`/`async_max_tickers` érték (NEM "1 serial")
   - Időbeli sűrűség: production batch-/burst-mintázat (NEM "lassan, kézzel")
   - API tier: production API key tier (NEM dev key magasabb limittel)

2. **Méret-extrapoláció TILOS** rate-limit-érzékeny mérésnél. A
   "20 × X ms × N = total time" formula **nem mond semmit** a tényleges
   server-side rate-limit állapotról, mert a server **frekvenciára**, nem
   abszolút hívásszámra érzékeny.

3. **A smoke output-jának 3 metrikát kell tartalmaznia:**
   - **Success rate** (ok / total) — várt: ≥95% production-ready számára
   - **Hard error rate** (429 + exception) — várt: ≤5%
   - **Wall-clock idő** — várt: férjen el a production cron ablakban

4. **Ha a smoke 429-eket termel, NEM szabad commit-olni** a változtatást.
   Iterálj a paraméterekkel (sequential delay, semaphore csökkentés,
   exponential backoff, batch-hibrid) ÉS futtasd újra a live smoke-ot,
   amíg a 3 metrika kapuban nincs.

5. **A smoke parancsot ad-hoc Python script-ben futtasd** (NE pytest-ben,
   mert az nem realisztikus terhelést ad). Mentsd el `scripts/analysis/`-ba
   reprodukálhatóság miatt, ha gyakori a finomítás.

**Példa-megfelelés:**

A 2026-05-13-i `1f0ffb9` commit deploy-olása előtt **élő smoke** futott a
**166-ticker mai passed list-en** (`logs/ifds_run_20260513_141500.jsonl`
TICKER_SCORED események), 200ms delay sequential konfiggal, sync UW client-en
(server-side rate-limit szempontból ekvivalens az async-kel). Eredmény:
**158/166 success (95.2%), 0 hard error, 77.6s** — minden 3 metrika passed,
a commit ki lett deploy-olva. A holnapi (5/14) production cron a végleges
validáció.

**Referencia:**

- Példa-sértés commit: `9a169b9` (per-ticker switch elégtelen smoke-kal)
- Iteratív javítás láncolat: `90cf5b4` → `1f0ffb9`
- Példa-megfelelő smoke: 2026-05-13 ad-hoc script, 166 ticker, sequential+200ms
- Diagnosztika a production log-ból: `cron_intraday_20260512_161500.log`
  (304 errors) → `cron_intraday_20260513_161500.log` (146 errors)

---

## "X feature nem prediktív" verdikt elé adat-egészség check (rule, 2026-05-10)

A scoring validation / korreláció elemzés alapú "X feature nem ad alpha-t"
verdikteket **TILOS** elfogadni anélkül, hogy a feature input-ját az adott
adatfolyamban közvetlenül ellenőriznénk. A "nincs jel" mérés gyakran azt
jelenti, hogy "az adat strukturálisan nullán van", nem azt, hogy a jel
maga nem prediktív.

**Szabály:**

1. Mielőtt egy feature-re "nem prediktív → eltávolítjuk / sign-flip-pelünk /
   konfigurációt finomítunk" döntés születne, **kötelező** egy adat-egészség
   ellenőrzés:
   - A feature input mezőjének (pl. `dp_pct`, `pcr_score`, `m_target`)
     **valós eloszlása** az aktuális production snapshot-okban (min/max/
     median, nem-nulla arány).
   - Ha a mező eloszlása **degenerált** (pl. minden quintile range 0.0–0.0,
     vagy max <1% valós küszöb 40% mellett) → **az adat broken, nem a jel**.
   - Akkor és csak akkor legitim a "nem prediktív" verdikt, ha a mező
     normál eloszlású és a korreláció stat. szignifikánsan ~0.

2. **Retrospektív audit utat** kell tervezni a production pipeline mellé,
   ami a broken pontokat megkerüli — pl. read-only közvetlen API hívás
   történelmi adatra (`date=YYYY-MM-DD` filter) az aktuális live trade-ek
   ticker × date kombinációira. Kódvátozás nélkül mérhető a feature valós
   prediktív tartalma.

3. **Két különálló bug egyszerre** lehet a strukturális 0 mögött:
   - Adatforrás bug (pipeline hibás coverage / threshold lehetetlen / save
     hibás)
   - Scoring bug (sign / threshold / aggregálás hibás)

   Az audit eredménye után **mindkettőt fix-elni kell**, csak az egyiket
   nem elég.

**Példa-sértés (mit ne csináljunk):**

A 2026-05-08-i `flow-decomposition.md` "dp_pct_score Pearson r = n/a, mind
0" verdiktje 232 trade-en futott, de a 232 enriched trade snapshotokban
**mind a 232 esetben dp_pct_score = 0 volt** — nem mert a jel nulla, hanem
mert (a) a snapshot regresszió (Apr 10 óta single AAPL ticker, lásd
`d3fce73`) miatt a recent snapshot-ok hasznavehetetlenek voltak, és
(b) a `dark_pool_volume_threshold_pct=40` küszöb soha nem fire-olt valós
7-15%-os DP eloszláson. A retrospektív per-ticker audit
(`scripts/analysis/dp_pct_retrospective_audit.py`,
`/api/darkpool/{ticker}?date=YYYY-MM-DD`) **szignifikáns INVERZ**
korrelációt mutatott (Pearson r=-0.265, p=0.041, n=60). A scoring
sign-flip + threshold rekalibráció (12%/18%, -10/-15) commit
`9a169b9`-ben deployolva.

**Referencia:**

- Audit script: `scripts/analysis/dp_pct_retrospective_audit.py`
- Audit report: `docs/analysis/dp-pct-retrospective-audit.md`
- Bug 1 fix (snapshot regression): commit `d3fce73`
- Bug 2 fix (sign-flip + threshold + per-ticker fetch): commit `9a169b9`
- Téves verdikt forrás: `docs/analysis/flow-decomposition.md`

---

## Test environment higiénia — production state path írás TILOS (rule, 2026-05-10)

A teszt környezetnek **soha** nem szabad a production `state/`,
`logs/`, `output/` mappákba írnia. A `tests/test_pipeline_e2e.py`
2026-04-10 óta naponta felülírta a `state/phase4_snapshots/` production
snapshotjait, mert a `test_full_pipeline_flow` futtatta a valódi
`run_pipeline`-t mockolt fázisokkal, **de nem mockolta a
`save_phase4_snapshot`-ot**. A runner ezért a default
`state/phase4_snapshots/` path-ra írta a `_mock_phase4()` AAPL rekordot,
naponta megsemmisítve a 16:15-i éles 93-ticker snapshot-ot. A bug **28
napig észrevétlen volt**, mert az AAPL output "értelmesen" tűnt és a
downstream kódban nem volt assertion ami tört volna.

**Szabály:**

1. **Minden teszt, ami a `run_pipeline`-t (vagy bármilyen production
   entrypoint-ot) közvetlenül futtatja, KÖTELESEN mockolja az összes
   I/O sink-et** — különösen:
   - `save_phase4_snapshot` (`ifds.data.phase4_snapshot`)
   - `write_shadow_snapshot` (`ifds.data.uw_shadow`)
   - `save_phase13_context` (`ifds.pipeline.context_persistence`)
   - `save_mid_bundle_snapshot` (`ifds.data.mid_bundle_snapshot`)
   - `write_execution_plan`, `write_full_scan_matrix`, `write_trade_plan`
   - Telegram / Anthropic / IBKR clients

2. **Regressziós teszt-pattern**: minden mock decorator-hoz adj egy
   asserciót, hogy a mock **hívva volt**:
   ```python
   assert mock_save_snapshot.called, (
       "save_phase4_snapshot mock was not invoked — runner may have "
       "bypassed the patch and written to production state/."
   )
   ```
   Ez a "test mocked itself out" antipattern detektálja, ha egy jövőbeli
   refactor a patch path-t elcsúsztatja.

3. **Pre-commit/CI ellenőrzés**: a `state/`, `logs/`, `output/` mappák
   **mtime-ja** a teszt suite futás után **nem változhat**, csak
   `tmp_path`-ben létrehozott fájlok keletkezhetnek.

**Példa-sértés (mit ne csináljunk):**

A `tests/test_pipeline_e2e.py::test_full_pipeline_flow` (2026-04-10 előtt
hozzáadva) `@patch(_P4, return_value=_mock_phase4())` decorator-ral
mockolta a Phase 4 result-ot, **de nem patcholta a save_phase4_snapshot-ot**.
A runner line 614 `save_phase4_snapshot(ctx.stock_analyses, snap_dir)` a
default `"state/phase4_snapshots"` path-ra írt. A 22:00
`deploy_daily.sh` pre-flight pytest naponta felülírta a 16:15 cron éles
snapshotját egyetlen AAPL rekorddal (combined_score=78.0). A
`flow-decomposition.md` ezért a régi (Feb-Apr 1) snapshotokon futott; a
BC23 utáni időszak teljes adata invalidálódott. Fix:
`d3fce73` — `@patch("ifds.data.phase4_snapshot.save_phase4_snapshot")`
+ `TestSnapshotIsolation::test_save_snapshot_is_mocked_in_e2e`
regressziós teszt.

**Referencia:**

- Detection commit: `d3fce73`
- Affected period: 2026-04-10 → 2026-05-08 (28 trading days)
- Symptom: `state/phase4_snapshots/{date}.json.gz` mtime mindig 22:00,
  content mindig single AAPL combined_score=78.0
- Future audit: keresd más hasonló pattern-eket (patch-eletlen runner.*
  hívások a tests/-ben)

**Második előfordulás (2026-05-19):**

A `d3fce73` fix csak a `save_phase4_snapshot` sink-et patch-elte. A
`write_shadow_snapshot` (`ifds.data.uw_shadow`, runner.py line 665, a
"Day 63 outcome §3.2, 2026-05-26" óta hozzáadott shadow log writer)
**szintén patch-eletlen** maradt. Day 2 (2026-05-19) manuális
`deploy_daily.sh --phases 1-3` pytest pre-flight overwrote a
`state/uw_shadow/2026-05-19.json`-t a 14:30 cron által írt ~90-ticker
adatból egyetlen AAPL combined_score=78.0 rekordra (`captured_at:
14:37:19+00:00` = 16:37 CEST, pontosan a manuális deploy ablakban).

Fix: a `tests/test_pipeline_e2e.py`-ben mind a `test_full_pipeline_flow`,
mind a `TestSnapshotIsolation::test_save_snapshot_is_mocked_in_e2e`
decorátor-stack-jébe hozzáadva:

```python
@patch("ifds.data.uw_shadow.write_shadow_snapshot", return_value=None)
```

+ asserciós védelem: `assert mock_write_shadow.called`. Day 90
(~2026-08-26) UW Bayesian recalibration audit a 2026-05-19-i shadow
log-ot **KIHAGYJA** (ireverzibilis loss; az egész napi UW dark pool
signal calibration adata 1 mock-AAPL rekorddá zsugorodott).

**Tanulság**: minden új sink, ami `runner.py`-be kerül, mindkét e2e
test patch-stack-be adandó. A "test mocked itself out" assert pattern
NEM véd új sink hozzáadása ellen — csak a meglévő patch-eknek a
refactorolás során való elcsúszása ellen.

---

## Live API integráció — schema verifikáció commit ELŐTT (rule, 2026-04-27)

Új külső API integrációk (REST kliens, válasz-mező mapping) ESETÉN kötelező
**egy live diagnostic dump** futtatása az **első commit ELŐTT**:

```python
client = SomeClient(api_key=os.environ["SOME_KEY"])
data = client.fetch_endpoint()
print("top-level keys:", sorted(data.keys()))
print("sample sub-dict:", sorted(data["sub"].keys()))
print("sample value:", data["sub"]["field"])
```

A task fájlban / dokumentációban szereplő mező-példák (`bundle.flat.growth`,
`response.results[].close`, stb.) gyakran **csak placeholder-ek**, vagy a doc
elavult. A tényleges API mezőnevek eltérhetnek (camelCase vs snake_case,
prefix/suffix konvenció, nested vs flat). Mock fixture önmagában nem szűri ki
ezt — a teszt zöld lehet, miközben élesben minden mező `None`.

**Szabály:**

1. Új API kliens: a `client.fetch_*()` metódus első futtatása **élő API-val**
   történik, és az output kulcsait kézzel ellenőrizzük (Mac Mini terminal vagy
   egyszer egy diagnostic notebook). Ezt megelőzi a mock fixture-ök írását.

2. A mock test fixture **a tényleges live response-ból** származik (sample
   payload), NEM a task spec / doc példákból.

3. **Sikerkritérium**: az első commit után az élő futás 100%-os mező-coverage-ot
   produkál (semmi `None` ott, ahol érték kellene). Ha None-ok vannak,
   first-commit verifikáció kimaradt.

**Példa-sértés (mit ne csináljunk):**
A 2026-04-27-i MID Bundle integráció `get_regime()`-je 20 mezőből 9-et
`None`-nal adott vissza Mac Mini-n. Két commit (`a3dfaf7` → `41f8e23` → `25806f2`)
kellett a fix-hez. Az élő bundle a `flat.g_score/i_score/p_score` és
`engines.tpi.level/level_description/tpi_score` kulcsokat használja, nem a
task fájlban szereplő `flat.growth/inflation/policy` és
`engines.tpi.state/description` mintát. Egy `print(client.get_bundle()['flat'].keys())`
az első commit előtt megtakarította volna a fix ciklust.

**Referencia:** `25806f2` (fix), `src/ifds/data/mid_client.py::get_regime`,
`tests/test_mid_client.py::sample_bundle` fixture (a fix után már a live
schemát tükrözi).

---

## IBKR ExecutionFilter — nem szigorú dátum-szűrő (rule, 2026-04-15)

Az `ib.reqExecutions(ExecutionFilter(time="yyyyMMdd 00:00:00"))` **nem garantáltan
szűr** a megadott időponttól. Régebbi napok executionjei átszivároghatnak ugyanazzal
az `orderRef`-fel (pl. ha a submit újra beadta másnap ugyanazt a tickert), és ez
phantom fill detektálást okoz.

**Szabály:**

Minden `reqExecutions()` eredményt **KÖTELEZŐEN post-filterelni** kell az
execution dátumára:

```python
today = date.today()
fills = ib.reqExecutions(ExecutionFilter(time=f"{today:%Y%m%d} 00:00:00"))
for fill in fills:
    if fill.execution.orderRef != target_ref:
        continue
    exec_date = getattr(fill.execution.time, "date", lambda: None)()
    if exec_date != today:
        logger.debug(f"ignoring stale execution: {fill.execution}")
        continue
    # ... valós mai fill
```

Az ExecutionFilter.time az IBKR szerver időzónájában (NY) értelmeződik,
nem a kliens localban — 22:00 CEST ≈ 16:00 EDT környékén a határ körül
bőven van lehetőség tegnapi fillek beszivárgására.

**Referencia:** `1bffb57` (date guard), `tp1_was_filled()` a pt_monitor.py-ban,
`tests/test_bc23_cleanup.py::TestTp1WasFilledDateGuard` (4 regression teszt).
Gyökérok: LION/SDRL/DELL/DOCN phantom fillek a 22:00 UTC rollover után.

---

## IBKR Paper Account — Adaptive algo silent reject (rule, 2026-04-08)

Az IBKR paper account (DUH118657) csendben elutasítja az `algoStrategy='Adaptive'`
(vagy bármilyen algo) ordereket. **Nincs error, nincs log entry, nincs bejegyzés
az Orders tab-ban, és `ib.placeOrder()` normálisan tér vissza.** Ezért a submit
script tud "Submitted: 8 tickers"-t logolni, miközben 0 order van az IBKR-ben.

**Szabályok:**

1. Paper account entry order → `MarketOrder` (vagy `LimitOrder`) **algoStrategy NÉLKÜL**.
   SOHA ne használj `algoStrategy='Adaptive'`-t paper accounton.

2. Minden `ib.placeOrder()` után KÖTELEZŐ `ib.sleep(~1-2s)` + `trade.orderStatus.status`
   ellenőrzés. Valid státuszok:
   `{PreSubmitted, Submitted, Filled, PendingSubmit, PendingCancel}`.
   Bármi más (`Cancelled`, `Inactive`, `ApiCancelled` stb.) silent rejection
   → WARNING log az `orderRef` + teljes `trade.log` entries-szel.

3. Bracket submit után post-submit verification: `ib.openTrades()` cross-check
   a várt `orderRef` halmaz ellen. Hiányzó entry = silent reject.

**Referencia:** `72d5655` (status check), `788cf6d` (MarketOrder switch),
`tests/test_submit_bracket_status_check.py` (10 regression teszt),
`scripts/paper_trading/lib/orders.py::create_day_bracket` + `submit_bracket`.

---

## IBKR Paper Trading — ClientId collision (rule, 2026-02-21)

Minden script KÖTELEZŐEN egyedi clientId-t használ:
- submit_orders.py → clientId=10
- close_positions.py → clientId=11
- eod_report.py → clientId=12
- nuke.py → clientId=13

Ugyanaz a clientId session takeover-t okoz — az előző connection csendben ledobódik.
Mindig `ib.sleep(2-3)` kell connect után a pozíció/order szinkronhoz.

---

## Phase 6 Scoring — Freshness Alpha mutation guard (correction, 2026-02-09)

`phase6_sizing.py`: az `original_scores` dict-et BEFORE kell rögzíteni,
mielőtt a `_apply_freshness_alpha` mutálja a `combined_score`-t.
`fresh_tickers` típusa: `set[str]` (NEM `dict[str, float]`).
`_calculate_position` mindkét paramétert külön kapja: `original_scores` + `fresh_tickers`.

---

## Testing — AsyncMock warning (correction, 2026-02-21)

Ha sync kódút tesztelünk, ami NEM hívja az async függvényt:
`patch` hívásban `new=MagicMock()` — NEM `AsyncMock`.
AsyncMock nem-awaited coroutine-t hoz létre → RuntimeWarning.
scipy paired t-test azonos különbségekkel: precision loss → adj slight noise.

---

## FileCache TTL (correction, beépített BC18-prep)

A FileCache TTL check mindig frissnek mutatott stale adatot — proper expiry check kell.
Javítva BC18-prep-ben.

---

## Cron env isolation — test fixture env var kontroll (rule, 2026-03-02)

A `deploy_daily.sh` `source .env`-vel betölti a prod env-et (`IFDS_ASYNC_ENABLED`, `IFDS_UW_API_KEY` stb.)
a pytest pre-flight ELŐTT. Minden test config fixture-nek KÖTELEZŐEN explicit kell kezelnie
az összes viselkedés-módosító env var-t:
1. Sync fixture-ökben: `monkeypatch.setenv("IFDS_ASYNC_ENABLED", "false")`
2. Async fixture-ökben: `monkeypatch.delenv("IFDS_UW_API_KEY", raising=False)` ha a teszt nem számít UW client-re
3. **Side-effect env-ek** (külső szolgáltatást hívnak, ha set-ek):
   - `monkeypatch.delenv("IFDS_TELEGRAM_BOT_TOKEN", raising=False)` — a runner.py:680-720
     `send_macro_snapshot`/`send_trading_plan`/`send_daily_report` hívások a `_mock_phase1/2/3()`
     fixture data-val ÉLŐ Telegram üzenetet küldenek a `.env` token+chat_id alapján.
   - `monkeypatch.delenv("IFDS_TELEGRAM_CHAT_ID", raising=False)` — ugyanezen ok miatt.

ÚJ fixture írásakor mindig ellenőrizd: milyen env var-ok változtatják meg a kódútat? Külön
figyelemmel a kifelé-hívó env-ekre (Telegram, Slack, IBKR, stb.) — `delenv` nélkül a teszt
külső pollution-t okozhat.

**Példa-sértés (2026-05-20 09:41+09:44)**: a `tests/test_pipeline_e2e.py::env_setup` fixture
NEM clear-elte az `IFDS_TELEGRAM_*` env var-okat. A Task #H `bd54857` által hozzáadott
`test_phase13_context_save_is_mocked` teszt (phase=(1, 3) → runner.py:686
`send_macro_snapshot(ctx, ...)`) **két ÉLŐ MACRO SNAPSHOT** üzenetet küldött Tamásnak a
`_mock_phase1/2/3()` fixture data-val (BMI=45.0%, Screened=3000, Passed=2, XLK only).
Fix: `env_setup` extended + 3 defensive `@patch` decorator (`send_macro_snapshot`,
`send_trading_plan`, `send_daily_report`).

---

## CC session kontextus: journal + STATUS.md (rule, 2026-03-28)

`session-start.sh` (UserPromptSubmit hook) minden CC promptnál betölti:
1. `docs/journal/` utolsó 2 entry — narratív kontextus (mi történt)
2. `docs/STATUS.md` — aktuális projekt állapot (élő, mindig friss)

`CLAUDE.md` Aktuális Kontextus szekció stabil referencia (ritkán változik) —
NEM frissítjük `/wrap-up`-kor. `docs/STATUS.md` az egyetlen dinamikus állapotfájl.
`/wrap-up` → `docs/STATUS.md` in-place frissítés (nem új fájl, nem CLAUDE.md).

---

## Git push policy (rule, 2026-02-26)

CC commitol, Tamás pusholja. Push csak explicit jóváhagyással.
