# IFDS — Permanent Rules (CC mindig olvassa)

Ezek a szabályok a CONDUCTOR learnings-ből kerültek ide (2026-02-26 migráció).
Forrás: `.conductor/memory/project.db` — learnings tábla.

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

ÚJ fixture írásakor mindig ellenőrizd: milyen env var-ok változtatják meg a kódútat?

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
