Status: WIP
Updated: 2026-07-21
Note: FRL build lane élő haladás-követő. CC vezeti (minden lépésnél frissül). Spec: `docs/design/2026-07-21-factor-research-loop-spec.md` (v2). Session-indító: `docs/handoff/2026-07-21-frl-build-session-starter.md`.

# FRL — Fejlesztési Tracker

**Lane:** CC build (Chat = spec + hipotézis-tartalom; Tamás = PROMOTE/deploy).
**Freeze:** build+teszt freeze-safe; éles felhasználás Day 63 után. Egyetlen prod-érintő elem: FRL-5 sink (D_A).

## Környezeti tények (2026-07-21 verifikálva)

| Tétel | Állapot |
|---|---|
| scipy / pandas / pyarrow | 1.17.0 / 3.0.0 / 23.0.0 — megvan |
| statsmodels | **NINCS** → Newey-West SE kézzel implementálva (HAC-variancia az IC-átlagra). Új prod-dependency a freeze alatt nem megy be. |
| `output/full_scan_matrix_*.csv` | **102 nap** (2026-02-11 → 2026-07-20) |
| Teszt-baseline | 1985 passing (csak nőhet) |

## Sorrend

```
S0  Housekeeping commit (spec + 4 task untracked → git)          ~10p   freeze-safe
     ▼
S1  FRL-0 KAPU — V1 score-szemantika audit + V2 Mini-cache       ~1h    JELENTÉS-KÖTELES
     │   kód: _apply_swing_scoring · write_full_scan_matrix hívás · TICKER_SCORED emitter
     │   adat: 04-15 (legacy) · 06-25 · 07-14 (swing) CSV↔JSONL keresztvalidáció (V3)
     ├── STOP → re-scope: v1 score-sáv elesik, a loader v2/OHLCV-only (Chat frissíti §4.2)
     ▼ GO
S2  FRL-1 loader                                                  ~4-5h
     │   research/ bootstrap (sync-halmazon KÍVÜL) + .gitignore
     │   frl_config.py  ← ELŐREHOZVA (D_B=4hét, D_C=0.10, éra-határok, min_sector_n)
     │   frl_loader.py: load_cross_section / load_panel / build_return_matrix / build_cost_model
     │   tesztek: golden 07-20 CSV, éra-határnapok 05-15|05-18, gap≠interpoláció, forward-h NYSE
     ▼
S3  FRL-2 IC-motor                                                ~5-6h
     │   factors/ base + sanity() kontraktus  ← ELŐREHOZVA (a lint S4-ben erre hivatkozik)
     │   frl_ic.py (daily_ic, aggregate+NW kézzel, era_bar, half_life+cost)
     │   frl_ledger.py (PENDING-first, BH-FDR + Bonferroni, Šidák-család)
     │   frl_holdout.py (K=4hét, 5-napos purge, egy-érintés hard error, PARK auto-retest)
     │   run_frl_batch.py (sanity-gate előfeltétel, riport-fejléc G1/G3 sor)
     ▼
S4  FRL-3 registry + lint                                         ~1h
     │   _TEMPLATE.md, frl_lint.py, HYP-001a/b…004 vázak (Status: DRAFT)
     ▼   → Chat tölti a tartalmat (külön kör)
S5  FRL-4 első éles batch — HYP-004 (tiszta v1 OHLCV reversal)     ~1h

S6  FRL-5 enrichment sink — build+teszt bármikor, DEPLOY csak D_A után + Tamás-push
```

### Sorrendi eltérések a spectől (indoklás)

1. **`frl_config.py` S2-be** (spec az FRL-2-be tette) — a loader is használja az éra-határokat és a `min_sector_n`-t; két helyen ne éljen konstans.
2. **`factors/` base + `sanity()` kontraktus S3 elejére** — az S4-es lint azt ellenőrzi, hogy egy HYP-nak van zölden futó `sanity()` párja; a kontraktusnak előbb léteznie kell.
3. **`cost_model.json` a loaderben épül** (S2), az IC-motor fogyasztja (S3) — a spec §5.3 dependenciája így egyirányú.

### Kapuk (nem léphetők át)

- **S1 STOP → S2 nem indul.**
- **S5** csak REGISTERED státuszú HYP-ra (a lint gate-eli).
- **S6 deploy** csak akkor, ha a teljes pytest-suite után a `state/research_cross_section/` mtime **változatlan** (D_A előfeltétel-1).

## Állapot-tábla

| Lépés | Fázis | Státusz | Task | Commit | Megjegyzés |
|---|---|---|---|---|---|
| S0 | — | DONE | — | `a7e186f`, `6457abe`, `30b948c` | spec+task a másik session commitolta; tracker: `30b948c` |
| S1 | FRL-0 | **DONE — GO** | `frl-scan-matrix-loader` (A-fázis) | — | kapu-riport a task §Eredmény-ben |
| S2 | FRL-1 | **DONE** | `frl-scan-matrix-loader` (B-fázis) | `8b8b216` | 4 modul + 25 teszt (2010 passing); cost-modell: swing 95.5 bp/oldal |
| S3 | FRL-2 | WIP | `frl-ic-engine` | — | NW kézzel; cost-input 95.5 bp |
| S4 | FRL-3 | TODO | `frl-hypothesis-registry` | — | tartalom: Chat |
| S5 | FRL-4 | TODO | — | — | HYP-004 |
| S6 | FRL-5 | BLOCKED | `frl-cross-section-enrichment` | — | **D_A** Tamás-megerősítésre vár |

Státusz-jelölés: TODO → WIP → DONE / BLOCKED / STOP.

## Nyitott döntések

| # | Döntés | Állapot |
|---|---|---|
| D_A | v2 enrichment sink freeze alatti deploy | **Tamás megerősítésére vár** (ajánlás: IGEN, 2 kemény előfeltétellel) — csak S6-ot fogja |
| D_B | Holdout K | DÖNTVE: 4 hét |
| D_C | FDR q | DÖNTVE: 0.10 |

## S1 kapu-eredmény → kötelező B-fázis következmények

**GO** (2026-07-21). Részletek: `docs/tasks/2026-07-21-frl-scan-matrix-loader.md` §Eredmény.

1. `Total_Score == 0` ∧ Reason=Tech Filter → **NaN**, nem 0 (a 0-halmaz mind a 4 mintanapon *pontosan* a tech_filter-halmaz).
2. **Éra-oszlop kötelező, pooled score-faktor tilos** — legacy .0/.5-rács 0…108 vs swing folytonos −125…+107.
3. **JSONL a swing-érában NEM score-validátor** (legacy kompozitot logol, a rescore előtt, torzított részhalmazon) → validátor-réteg éra-függő.
4. Return-mátrix: `get_grouped_daily` napi-loop (~110-130 hívás) — a **Mini polygon-cache ÜRES** (V2 negatív).
5. A swing score EWMA(5)-simított, változó univerzumon → a half-life a simítást is méri; riportban jelölendő.

## Változásnapló

| Dátum | Változás |
|---|---|
| 2026-07-21 | Tracker létrehozva; sorrend rögzítve (S0–S6, 3 eltéréssel a spectől); környezeti tények felvéve (statsmodels hiány → kézi NW). |
| 2026-07-21 | **S0 DONE** (spec+task már commitolva `a7e186f`/`6457abe`; tracker `30b948c`). |
| 2026-07-21 | **S1 FRL-0 DONE → GO.** V1/1-3 + V3 + 102-napos éra-sweep + V2 (Mini-cache üres). 5 kötelező B-fázis következmény rögzítve. S2 WIP. |
| 2026-07-21 | **S2 FRL-1 DONE** (`8b8b216`). 4 modul (config/loader/returns/cost) + 25 teszt → **2010 passing**, 0 prod-state írás. Live schema-verifikáció: `get_grouped_daily` 12 388 sor, `T`/`c` igazolva. E2E smoke 06-29→07-20: 8 nap, 0 unexpected-missing, h=1 join 100%. **Cost-modell forrás-korrekció**: `daily_metrics.execution.slippage_per_ticker` (nem `pending_exits`) → swing medián **95.5 bp/oldal**, p75 137, n=28 (a 75 bp ~27%-kal alábecsül); legacy referencia 19 bp (5×, végrehajtási stílus-váltás → nem prior). |
