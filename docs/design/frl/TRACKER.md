Status: WIP
Updated: 2026-07-25
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
| S3 | FRL-2 | **DONE** | `frl-ic-engine` | `a02bc1d` | 6 modul + 74 teszt (2084 passing); NW statsmodels ellen validálva |
| S4 | FRL-3 | **DONE** | `frl-hypothesis-registry` | `7f74c58` | template + 7 HYP (DRAFT) + lint + batch-gate; 2109 passing |
| S5 | FRL-4 | **DONE** | — | `9f49a38`, `48451ce` | HYP-004 **KILLED** (pre-reg (a), Tamás megerősítve); 2139 passing |
| S6 | FRL-5 | **DEPLOYOLVA** | `frl-cross-section-enrichment` | `08d072d`, `faa56d3`, `d10c8de` | push+Mini pull kész (2158 passed/1 skipped); ⏳ első éles fájl: **07-24 14:30** |

Státusz-jelölés: TODO → WIP → DONE / BLOCKED / STOP.

## Nyitott döntések

| # | Döntés | Állapot |
|---|---|---|
| D_A | v2 enrichment sink freeze alatti deploy | **DÖNTVE: IGEN** (Tamás, 2026-07-21) — build+teszt kész, deploy a 7 lépéses szekvencia szerint (3. lépésnél tartunk) |
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
| 2026-07-25 | **Első éles sink-fájl verifikálva** (07-24): n_rows 433=csv 433, n_scored **238=238** (pontos), nyers mezők 100% non-null a pontozott sorokon, swing_score 238/238 + legacy_composite 0/238, unscored→null (0 leak). **A 40-napos v2 óra elindult.** — **Második fordulat batch** (HYP-005, run 07-24): előjel helyes mind a 4 h-n, emelkedő görbe (0.008→0.052), Šidák-p 0.2564 (BH-fail), half-life 10.3 nap. **Verdikt-javaslat: PARK-until-swing-power** (primary h=5 alulfeszített/jó előjel; h=1/h=3 KILL) → Tamásra vár. **Auto-verdikt logikai rés javítva** (`079e4a1`): swing-only faktor eddig nem tudott PARK-olni (nincs legacy láb) → T_eff-adekvácia gate (§5.5, floor=6); HYP-004 KILL változatlan (regressziós teszt). cost-model n=28→31, 95.5→97.0 bp. **+17 teszt → 2182 passing.** |
| 2026-07-23 | **HYP-005 faktor kész** (`bc651b3`): `factors/sj_live.py` — az élő swing score, swing-only éra-guarddal a faktorban is; sanity PASS (+1.000). **A batch NEM futott**: a §10 heti-egy-batch kadencia szerint a HYP-005 futás a **pénteki (07-24) sync utáni ablakban** megy (+2-3 swing-nap a T_eff-hez). **+12 teszt → 2171 passing.** |
| 2026-07-23 | **Tracked-vs-syncelt feloldás** (Tamás-döntés, `8e0d296`): `docs/analysis/` **untrackelve + .gitignore** (Mini generálja → rsync-terület), `docs/review/` **tracked marad** (MacBookon születik). Mini: backup → pull (a git törölte) → visszaállítás → `diff -rq` **0 eltérés** → backup takarítva; 2158 passed/1 skipped. Ház-elv rögzítve: rsync a gép-generált state-nek, git az ember-írta dokumentumoknak. Új szabály az `ifds-rules`-ba (`56043c3`): **freeze alatt `git add` csak explicit path-listával, `-A`/`.` sweep TILOS**. |
| 2026-07-23 | **S6 DEPLOYOLVA.** Push (22 commit `6457abe`→`d10c8de`) + Mini ff-only pull, Tamás-jóváhagyással. Mini-verifikáció: **2158 passed, 1 skipped** (a skip a statsmodels-referencia — dev-only, szándék szerint), `state/research_cross_section/` a suite után **nem jött létre** (előfeltétel-1 élesben is áll). `04-risks` **§11.11** rögzítve. Doc-átvezetés (`d10c8de`): §8.2 tábla — az a-trió **HYP-005**-be konszolidálva (S_j élő aggregát, REGISTERED), HYP-001b/002b/003b vázak v2 sávra újraírva, §4.5 gap-sor a 07-22 áramszünetre. ⏳ Első éles sink-fájl: **07-24 14:30 CEST**; az FRL v2 40-napos órája ekkor indul. |
| 2026-07-23 | **Mini-restart ellenőrzés a 07-22 outage után**: boot 07-22 09:30 (a tegnapi elérhetetlenség **hálózat**, nem gép), 0 orphan, mai 14:30 cron hibátlan. **07-22 teljesen kimaradt** (nincs cron log). Outage-hatás verifikálva: 1 késett exit (**USFD** MENTAL_SL, a 07-21 eod már flag-elte, stop 95.08 vs close 94.75) — ára **+$7.28 a javunkra** (07-22 open 94.63 vs 07-23 open 94.50), nem P1; a nyitott pozíciók közül **egyik sem tört stopot** 07-22-én; ledger ép (38 nap, cum $107.62). |
| 2026-07-21 | Tracker létrehozva; sorrend rögzítve (S0–S6, 3 eltéréssel a spectől); környezeti tények felvéve (statsmodels hiány → kézi NW). |
| 2026-07-21 | **S0 DONE** (spec+task már commitolva `a7e186f`/`6457abe`; tracker `30b948c`). |
| 2026-07-21 | **S1 FRL-0 DONE → GO.** V1/1-3 + V3 + 102-napos éra-sweep + V2 (Mini-cache üres). 5 kötelező B-fázis következmény rögzítve. S2 WIP. |
| 2026-07-21 | **S6 FRL-5 build DONE** (`08d072d`). **D_A: IGEN** (Tamás) → doc-átvezetés (`43c07a5`) + `04-risks` §12 (`3d50bb9`). Sink: a teljes pontozott keresztmetszet napi gzip-perzisztálása, **swing_score és legacy_composite külön mezőben** (az FRL-0 szemantika-tanulság a forrásnál kódolva), tech_filter/danger_zone → null (nem 0.0). **Előfeltétel-1 bizonyítva** (`faa56d3`): sentinel-fájllal, 2159-teszt után mtime+sha256+fájlhalmaz változatlan, **negatív kontrollal** (patch nélkül a suite tényleg prodba ír, és az új grep-audit teszt elkapja). **+20 teszt → 2159 passing.** ⏳ Tamás push-jóváhagyására vár. |
| 2026-07-21 | **S5 FRL-4 DONE — a loop első teljes fordulata lezárult.** `factors/reversal.py` (HYP-004) + első éles batch (`research/runs/2026-07-20/`) → **KILL** a pre-reg (a) szerint, **Tamás megerősítette** (A-0001..A-0004 `human_confirmed: true`), HYP-004 `Status: KILLED`. Két adathiba és egy governance-rés kifogva, mindhárom teszttel zárva: (1) **VETO-maszkolt 0.0 sorok** (`9f49a38`) — a scan-writer felülírja a Reason-t, 6179 legacy sor lépett volna be 0.0 faktor-értékkel → `score == 0` → NaN; (2) **SHADOW-guard flag-esítve** (`DAY63_GATE_PASSED`) a számított dátum helyett; (3) **decision provenance** (`48451ce`) — `decision_source`/`human_confirmed` + riport-backlog. **2109 → 2139 passing.** |
| 2026-07-21 | **S4 FRL-3 DONE** (`7f74c58`). Template + 7 HYP-fájl (mind DRAFT) + `frl_lint.py` + batch hypothesis-first gate (DRAFT → `BLOCKED`, nincs ledger-sor). HYP-004 tartalma teljes (Chat). **+25 teszt → 2109 passing.** Két új szabály az `ifds-rules`-ba (`45ee0a4`): tolerancia-alapú degeneráció-guard, hermetikus teszt. |
| 2026-07-21 | **S3 FRL-2 DONE** (`a02bc1d`). factors/ sanity-kontraktus + IC-motor + ledger + holdout + riport + batch; **+74 teszt → 2084 passing**, ruff/black tiszta, 0 prod-írás. Kézi Newey-West **statsmodels ellen validálva** (rel 1e-6, dev-only dep, skipif-fel). Két TDD-fogás: (1) `daily_ic` degenerált-rang guard — szektoron belül konstans faktor pct-rangjainak szórása 1e-16, a pandas `corr` 1.0-t ad rá → tiszta szektor-fogadás tökéletes szektor-neutrális jelnek látszott volna; (2) a batch-teszt a valós `returns.parquet`-et olvasta → `returns_frame` injektálás + guard-teszt. |
| 2026-07-21 | **S2 FRL-1 DONE** (`8b8b216`). 4 modul (config/loader/returns/cost) + 25 teszt → **2010 passing**, 0 prod-state írás. Live schema-verifikáció: `get_grouped_daily` 12 388 sor, `T`/`c` igazolva. E2E smoke 06-29→07-20: 8 nap, 0 unexpected-missing, h=1 join 100%. **Cost-modell forrás-korrekció**: `daily_metrics.execution.slippage_per_ticker` (nem `pending_exits`) → swing medián **95.5 bp/oldal**, p75 137, n=28 (a 75 bp ~27%-kal alábecsül); legacy referencia 19 bp (5×, végrehajtási stílus-váltás → nem prior). |
