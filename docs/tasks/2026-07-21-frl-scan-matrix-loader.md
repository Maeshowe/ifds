Status: DONE
Updated: 2026-07-21
Note: Freeze-safe (read-only elemző-tooling, signal_attribution-wiring precedens). Production kódot NEM érint. Spec: docs/design/2026-07-21-factor-research-loop-spec.md (§4, §11). R1#1: a task KÉT fázisú — A-fázis (FRL-0 kapu) önállóan fut és jelent, a B-fázis (loader-build) KIZÁRÓLAG a GO-verdikt után indulhat.

# FRL-1 — Keresztmetszeti loader + score-szemantika audit + return-mátrix

## Probléma

Az FRL (Factor Research Loop) alap-adatrétege hiányzik: nincs egységes, éra-címkézett,
gap-kezelt betöltő a napi keresztmetszeti forrásokra (full_scan_matrix CSV + ifds_run
JSONL), és nincs forward-return mátrix. Ezen felül a 2026-07-21-i felderítés három
verifikálatlan szemantika-kérdést hagyott nyitva, amelyek nélkül az IC-számítás rossz
oszlopon futhat.

## Megközelítés

### A-FÁZIS — FRL-0 GO/STOP KAPU: V1 score-szemantika audit (önálló, jelentés-köteles)

**Ez nem előkészítő lépés, hanem kapu.** A B-fázis (loader-build, ~4-5h) NEM kezdhető
el a kapu-riport és a GO-verdikt előtt — a dp_pct-strukturális-nulla és a phase4
AAPL-mock hibaosztály harmadik előfordulását zárjuk ki, MIELŐTT 8-10h buildet
építenénk rá.

**Kapu-riport:** a task §Eredmény szekciója + 5-10 soros összefoglaló Tamásnak.
**GO:** a swing-érás kanonikus score-oszlop azonosított, éra-konzisztens, nem degenerált.
**STOP:** ha a swing-érás score-oszlop éra-inkonzisztens vagy degenerált → a v1
score-fakor sáv érvénytelen, re-scope: a loader a v2/OHLCV sávra szűkül, a spec §4.2
frissítendő (Chat).

Kérdések, amikre a task írásos választ ad (a task-fájl §Eredmény szekciójába):
1. A `full_scan_matrix` Total_Score oszlopa érá-nként pontosan mit tartalmaz?
   (legacy nyers kompozit vs S_j EWMA-percentilis; a swing-érában a "swing_score"
   reject-sorok vs tech-filter sorok bontásában)
2. Miért Total_Score > 0 csak 115 sor a 257 pontozottból a 2026-07-20-i fájlban?
   (várható ok: a tech-filter előtti kiesők 0-val íródnak — verifikálandó a writer kódban)
3. A JSONL `TICKER_SCORED` a swing-érában melyik score-t logolja? (a 2026-07-14 minta
   .0/.5-lépésközű legacy-stílusú kompozitot mutatott, miközben a uw_shadow tizedes
   S_j-ket — a kettő leképezése dokumentálandó)
4. V3 keresztvalidáció: 3 mintanapon (1 legacy: 2026-04-15 — figyelem, a phase4_snapshot
   aznap mock-polluted, a CSV-t NEM érinti, de ellenőrizendő; 2 swing: 2026-06-25,
   2026-07-14) ticker-halmaz és score-egyezés a CSV és a JSONL között.

Kód-belépési pontok: `_apply_swing_scoring` (src/ifds/scoring/swing_score.py wiring),
a full_scan_matrix writer (`write_full_scan_matrix` hívási helye a runner.py-ban),
a TICKER_SCORED emitter a Phase 4-ben.

### V2 — Mini polygon-cache felmérés (A-fázis része, SSH, ~5 perc, nem blokkoló)

```
ssh ifds-mini "du -sh ~/SSH-Services/ifds/data/cache/polygon; \
  find ~/SSH-Services/ifds/data/cache/polygon -type f | head -20"
```
+ 1-2 fájl tartalom-mintája: daily bars / options / egyéb; dátum-lefedettség.
Eredmény a task §Eredmény szekciójába — ha daily-bar cache van értelmes lefedéssel,
a return-mátrix builder ezt használja elsődleges forrásként, Polygon API fallbackkel.

---

### B-FÁZIS — loader-build (KIZÁRÓLAG FRL-0 GO után)

### 1. lépés — Loader modul

Új: `scripts/research/frl_loader.py` (+ `scripts/research/__init__.py`)

- `load_cross_section(date) -> DataFrame` — a CSV a törzs, a JSONL a validátor-réteg
  (ticker-halmaz diff logolva); oszlopok normalizálva, `era` címke (legacy: ≤2026-05-15,
  swing: ≥2026-05-18), a V1-audit szerinti kanonikus score-oszlop(ok) kiválasztásával
- `load_panel(start, end) -> DataFrame` — multi-nap panel; hézagok (06-27→07-06,
  07-15/16, NYSE-ünnepek) explicit hiányzó napként, SOHA nem interpolálva;
  NYSE-naptár a meglévő `trading_days_between` util-ból
- `build_return_matrix(tickers, start, end) -> DataFrame` — Polygon daily close,
  forward h-napos hozamok h∈{1,3,5,7}; cache: `research/cache/returns.parquet`
  (gitignore); forrás-prioritás: Mini-cache (ha V2 pozitív) → Polygon API
- `build_cost_model() -> research/cost_model.json` — R1#3; forrás-korrekció (8b8b216):
  `state/daily_metrics/<date>.json → execution.slippage_per_ticker[*].slippage_pct`
  (a pending_exits-ben nincs slippage-mező); next-day-fill |slippage| medián és p75
  bp/oldal, `era=swing` default; első output: 95.5/137.0 bp (n=28, small_n_warning);
  a heti batch frissíti
- Szektor-mapping: a CSV `Sector_Name` oszlopa a kanonikus (konzisztens a
  sector-relative IC-hez)

### 2. lépés — research/ könyvtár bootstrap

`research/` top-level létrehozása + `research/cache/` a .gitignore-ba + README
(a spec §4.3 sync-topológia indoklásával: a sync-halmazon KÍVÜL van, mert a
Mini-master --delete rsync törölné).

## Implementációs terv (fájlok)

Új:
- `scripts/research/frl_loader.py`
- `scripts/research/README.md` (V1/V2 audit-eredmények + használat)
- `research/README.md`, `research/cache/.gitkeep`
- `.gitignore` bővítés: `research/cache/`

Tesztek (`tests/test_frl_loader.py`):
- golden-file: 2026-07-20 CSV parse (433 sor, 7 ACCEPTED, status-bontás)
- éra-címkézés határnapokon (05-15 / 05-18)
- gap-nap → hiányzó, nem interpolált
- JSONL-validátor diff-riport (szintetikus eltéréssel)
- return-mátrix forward-h helyessége szintetikus árakon (NYSE-naptárral, hétvége-átlépés)

## Commit

`feat(research): FRL cross-section loader + score-semantics audit (freeze-safe, read-only)`

## Eredmény — FRL-0 kapu-riport (2026-07-21, CC)

### VERDIKT: **GO** — egy kötelező scope-módosítással (a JSONL nem score-validátor a swing-érában)

A swing-érás kanonikus score-oszlop **azonosított, éra-konzisztens és NEM degenerált**.
A `full_scan_matrix.Total_Score` a swing-érában a **swing S_j EWMA(5)** érték; a
"115/257" nem adathiba, hanem az előjeles S_j-eloszlás nulla körüli centrálása.

### V1/1 — Mit tartalmaz a `Total_Score` érá-nként (kódból verifikálva)

`write_full_scan_matrix` ([execution_plan.py:203](src/ifds/output/execution_plan.py#L203)):
`Total_Score = round(stock.combined_score, 2)` — a Phase 4 **futás VÉGI** állapota.
A `_apply_swing_scoring` ([phase4_stocks.py:110](src/ifds/phases/phase4_stocks.py#L110))
felülírja a `combined_score`-t az EWMA-simított S_j-vel **minden candidate**-en (= minden
ticker, ami a strukturális filtereket túlélte), és ez a hívás **megelőzi** a CSV-írást
(run_phase4 vége, [runner.py:428](src/ifds/pipeline/runner.py#L428)). Mindkét kódúton
(sync 481, async 1663) azonos.

| Éra | `Total_Score` jelentése | Skála | Granularitás |
|---|---|---|---|
| legacy (≤05-15) | legacy kompozit `0.60·Flow + 0.10·Funda + 0.30·Tech + sector_adj` | ~0…108, ritkán kis negatív | **100% .0/.5 rács** |
| swing (≥05-18) | `EWMA₅(100·(PCR_pct − OTM_pct) + sector_adj)` | −125…+107 | **54-61% folytonos** |

**A két éra skálája és eloszlása inkompatibilis** → a spec **G5 éra-bontása nem
opcionális, hanem matematikai kényszer**. Pooled IC éra-bontás nélkül értelmetlen.

### V1/2 — Miért `Total_Score > 0` csak 115 a 257 pontozottból (07-20)

**Megoldva, nem bug.** A 433 sor bontása: **176 tech_filter** (SMA200 alatt → a ticker
soha nem került scoringba, `combined_score` marad a 0 default) + **257 scored** (250
`swing_score` reject + 7 ACCEPTED). A 257-en belül 115 pozitív / 142 negatív — pontosan
az, amit egy percentilis-**különbség** jeltől várunk (medián ≈ 0).

Gépi bizonyíték mind a 4 mintanapon: a `Total_Score == 0` halmaz **pontosan egyenlő** a
`Tech Filter (Price < SMA200)` halmazzal (551/551, 357/357, 258/258, 176/176).
→ **Loader-szabály:** a 0-értékű tech_filter sorok **NEM faktorérték-nullák**, hanem
hiányzó megfigyelések → az IC-panelből `NaN`-ként kizárandók, nem 0-ként bevonva.
(Ez lett volna a dp_pct-strukturális-nulla harmadik előfordulása, ha 0-ként kerül be.)

### V1/3 — Mit logol a `TICKER_SCORED` a swing-érában

**A legacy kompozitot, a swing-rescore ELŐTT** — kódból ([phase4_stocks.py:396](src/ifds/phases/phase4_stocks.py#L396)
sync, [1573](src/ifds/phases/phase4_stocks.py#L1573) async: az emitter a legacy
min_score/clipping ág `else`-ében ül, a `_apply_swing_scoring` jóval később fut).
Empirikusan: a JSONL score-tartomány mind a 4 napon **70.00–95.00, 100% .0/.5 rács**
(= a legacy `min_score=70` / `clipping=95` kapu), miközben a CSV −99…+88 folytonos.

**Ez a handoffban jelzett (b) gyanú megerősítve — de ártalmatlan, mert a CSV a kanonikus.**
Következmény a scope-ra: **a JSONL a swing-érában NEM használható score-validátornak**
(más mennyiséget mér), és ráadásul **torzított részhalmaz** (csak a legacy-passed ~50-90
ticker, nem a teljes 257-es keresztmetszet). A loader JSONL-rétege ezért:
- legacy éra: valódi score-cross-check (lásd V3);
- swing éra: **kizárólag** ticker-halmaz-lefedettség és `TICKER_FILTERED` kizárási-ok
  forrás — score-egyezést tilos elvárni (különben hamis riasztás).

### V3 — CSV ↔ JSONL keresztvalidáció (3+1 mintanap)

| Nap | Éra | CSV sor | TICKER_SCORED | JSONL ⊆ CSV | Score-egyezés | JSONL tartomány |
|---|---|---|---|---|---|---|
| 2026-04-15 | legacy | 1372 | 138 | ✅ | **138/138** | 70.0–93.0 (.0/.5) |
| 2026-06-25 | swing | 876 | 176 | ✅ | 0/176 *(várt)* | 70.0–94.0 (.0/.5) |
| 2026-07-14 | swing | 653 | 90 | ✅ | 0/90 *(várt)* | 70.0–94.5 (.0/.5) |
| 2026-07-20 | swing | 433 | 50 | ✅ | 0/50 *(várt)* | 70.0–95.0 (.0/.5) |

A legacy napon **tökéletes egyezés** (a két sink ugyanazt a mennyiséget írja) — ez
validálja magát a keresztvalidációs módszert. A swing napok 0%-os egyezése a V1/3
kódolvasat közvetlen empirikus visszaigazolása, nem inkonzisztencia.
04-15 megjegyzés: a `phase4_snapshot` aznapi mock-pollúciója a CSV-t **nem érinti**
(1372 valós sor, 138 ACCEPTED).

### Teljes 102-napos éra-sweep (degeneráció-keresés)

| Éra | Napok | Σsor (átl.) | Pontozott (átl.) | ACCEPTED (átl.) | Negatív score (átl.) | Folytonos-arány |
|---|---|---|---|---|---|---|
| legacy (02-11→05-15) | 66 | 1324 | 861 | 275 | 1.6 | 0.00 |
| swing (05-18→07-20) | 36 | 759 | 425 | 34 | 216 | 0.43–0.61 |

**Éra-határ empirikusan tiszta:** 05-15 az utolsó .0/.5-rácsos nap, 05-18 az első
folytonos + `swing_score` reason-os nap; átmeneti/kevert nap **nincs**.
**Degenerált swing-nap: 0** (nincs olyan nap, ahol a folytonos-arány < 0.2 vagy hiányzik
a `swing_score` reason). A 05-20-i univerzum-zsugorodás (1479 → 329 sor) valós
univerzum-váltás, nem adathiba — a loader panel-lefedettségi riportjában megjelenítendő.

### V2 — Mini polygon-cache: **ÜRES** (negatív lelet)

`ssh ifds-mini du -sh ~/SSH-Services/ifds/data/cache` → **0B**, `data/cache/polygon` 0 fájl.
A lokális MacBook-cache is 16K (gyakorlatilag üres). → **A return-mátrix forrása a Polygon API.**

**Költség-optimalizáció (új lelet, a taskban nem szerepelt):** a
`PolygonClient.get_grouped_daily(date)` ([polygon.py:113](src/ifds/data/polygon.py#L113))
EGY hívásban adja a teljes US piac napi OHLCV-jét, és **cache-elt**. A return-mátrix így
~**110-130 hívásból** (nap/hívás) felépíthető a ~1500 ticker × per-ticker aggregates
helyett. A loader ezt használja elsődlegesen, `get_aggregates` fallbackkel.

### Következmények a B-fázisra (kötelezően kódolandó)

1. `Total_Score == 0` ∧ `Reason` = Tech Filter → **NaN**, nem 0 (faktor-panel).
2. Éra-oszlop kötelező; **pooled score-faktor tilos** (skála-inkompatibilitás).
3. JSONL-validátor: score-egyezés csak legacy érán; swing érán ticker-lefedettség +
   `TICKER_FILTERED` ok — a diff-riport ezt éra-függően értékeli.
4. Return-mátrix: `get_grouped_daily` napi-loop + cache; `research/cache/returns.parquet`.
5. A swing score **EWMA(5)-simított** és **kereszmetszeti percentilis-alapú**, változó
   univerzumon (144–830 pontozott/nap) → a faktor auto-korrelált (a half-life mérés ezt
   a simítást méri, nem csak a nyers jel perzisztenciáját) — a riportban jelölendő.

### Nyitott (nem blokkoló)

- V4 (legacy phase4_snapshot mock-szűrő) — csak ha a snapshot forrásként bejön; most nem.

---

## Eredmény — B-fázis (loader-build, 2026-07-21, CC)

### Szállított modulok

Flat modulok a `scripts/research/`-ben (nincs `__init__.py`) — a
`scripts/paper_trading/` ház-minta szerint minden belépési pont a saját könyvtárát
teszi a `sys.path`-ra. **Indok:** a `scripts/research/` csomagnév ütközne a
top-level `research/` adat-könyvtárral (namespace-package shadowing), ha a projekt
gyökér is a `sys.path`-on van — `python -m pytest` esetén az.

| Modul | Tartalom |
|---|---|
| `frl_config.py` | éra-határok, D_B=4 hét, D_C=q0.10, horizontok, `MIN_SECTOR_N`, `ERA_BAR_FLOOR`, ismert gap-ek, összes útvonal |
| `frl_loader.py` | `load_cross_section` / `load_panel` / `require_single_era` / `validate_with_events` / `available_days` |
| `frl_returns.py` | `closes_from_grouped` / `forward_returns` / `build_return_matrix` / `research_cache` |
| `frl_cost.py` | `collect_slippage` / `build_cost_model` / `load_cost_model` / `round_trip_cost_bps` |

`research/` bootstrap kész (`README.md` a §4.3 sync-indoklással, `cache/`, `runs/`),
`.gitignore`: `research/cache/*` (a ledger és a runs **tracked**).

**Tesztek: 25 új, `tests/test_frl_loader.py` — suite 1985 → 2010 passing, 0 failure.**
Teszt-környezet higiénia ([[test-env-hygiene]]): a teljes suite lefutása után a
`state/`, `output/`, `logs/`, `research/` alatt **egyetlen fájl mtime-ja sem változott**.

### Az öt kötelező FRL-0 következmény kódolva

| # | Hol | Regressziós teszt |
|---|---|---|
| 1 | `load_cross_section`: tech_filter → `NaN`, `scored=False`; a nem-tech_filter 0.0 megmarad és anomália-számlálóba kerül | `TestTechFilterIsNaN` (2) |
| 2 | `require_single_era()` `ValueError`-t dob pooled score-faktorra | `TestEraLabelling` (4, határnapok 05-15/16/18) |
| 3 | `validate_with_events()`: score-összevetés **csak** legacy érán, swing érán ticker-lefedettség | `TestEventLogValidator` (4) |
| 4 | `build_return_matrix()` `get_grouped_daily`-vel, `research/cache/api` FileCache-sel | `TestForwardReturns` (3) |
| 5 | EWMA-simítás megjegyzés a modul-docstringben + a batch-riportba kerül (S3) | — |

### Live API schema-verifikáció (ház-szabály: commit ELŐTT)

`get_grouped_daily("2026-07-20")` → **12 388 sor**, kulcsok:
`['T','c','h','l','n','o','t','v','vw']`. A `T`/`c` mezőnév-feltevés **élőben
igazolva** (AAPL c=326.59). Nem placeholder-ből dolgoztunk.

### End-to-end smoke (valós adat, 06-29 → 07-20)

- Panel: **8 nap, 5 544 sor**, coverage 53.3% — a 7 hiányzó nap **mind ismert gap**
  (Mini-outage 06-29→07-06, áramszünet 07-15/16), `unexpected_missing = []`. ✅
- Anomáliák: `zero_score_not_tech_filter = 0`, `tech_filter_with_nonzero_score = 0`
  → a 0↔tech_filter identitás a teljes ablakon is tartja magát.
- Pontozott/nap átlag: 417.8; egyedi pontozott ticker: 572.
- Return-mátrix: 24 nap, 13 728 sor, **13.9 s** (cache-eltelten újrafuttatva ~0 s).
- Join-lefedettség a pontozott sorokon: **h=1 → 100.0%**, h=5 → 80.0% (a hiányzó
  20% a mai naphoz közeli napok, ahol a forward-ablak még nem telt le — helyesen
  NaN, nem eldobva).

**Következmény a batch-re:** a dev-ablak vége mindig `max(h)` trading nappal
korábbi, mint a legutolsó elérhető bar-nap; ezt a riport kiírja.

### `build_cost_model()` első valós output (Chat kérésére)

**Forrás-korrekció:** a task `state/pending_exits/`-et jelölt meg, de azok a
rekordok **nem tartalmaznak slippage mezőt** (kulcs, ticker, entry_price,
entry_date, qty, exit_type, sector, entry_score, submitted_at, processed). A
hiteles slippage-sorozat: `state/daily_metrics/<date>.json` →
`execution.slippage_per_ticker[*].slippage_pct` (előjeles %, belépési MKT-fill vs
tervezett limit), amit a `daily_metrics.py::_build_entry_slippage` ír.

`research/cost_model.json` (2026-07-21):

| Éra | n | medián \|slip\| | p75 | max | modell-input |
|---|---|---|---|---|---|
| **swing** (05-20 → 07-20) | **28** | **95.5 bp/oldal** | **137.0 bp** | 377.0 bp | **95.5 bp** ⚠️ kis-n |
| legacy (referencia) | 99 | 19.0 bp | 31.0 bp | 450.0 bp | — (nem használjuk) |

**Értelmezés:** a 75 bp-s induló feltevés **alábecsül ~27%-kal** a swing-érán
(95.5 vs 75), a p75 pedig 137 bp — a round-trip **~191 bp** a medián-inputtal.
Az 5x-ös legacy/swing különbség (19 → 95.5 bp) végrehajtási stílus-váltás
(intraday LMT → next-day MKT open), tehát a legacy minta **nem prior** a swingre —
ezért az `era=swing` az alapértelmezett szűrő. `small_n_warning: true` (28 < 30),
a heti batch minden futáskor újraszámolja.

**A HYP-004 costed-IC riportja ezen a 95.5 bp-os inputon fut**, nem a 75-ösön.
