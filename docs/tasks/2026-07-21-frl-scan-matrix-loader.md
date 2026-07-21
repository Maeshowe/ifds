Status: OPEN
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
- `build_cost_model() -> research/cost_model.json` — R1#3: a `pending_exits/`
  slippage-mezőiből a next-day-fill |slippage| medián és p75 (bp/oldal); induló
  fallback 75 bp ⚠️ kis-n címkével; a heti batch frissíti
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

## Eredmény (a végrehajtás tölti)

- V1 válaszok: …
- V2 polygon-cache: …
- V3 keresztvalidáció: …
