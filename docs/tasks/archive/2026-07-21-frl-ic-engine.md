Status: DONE
Updated: 2026-07-21
Note: Freeze-safe (read-only elemző-tooling). Előfeltétel: frl-scan-matrix-loader B-fázis DONE (FRL-0 kapu GO). Spec: docs/design/2026-07-21-factor-research-loop-spec.md (§5, §6, §7, §10) — v2, R1 beépítve. D_B=4 hét és D_C=q0.10 DÖNTVE (review-konszenzus).

# FRL-2 — IC-motor + attempt-ledger + heti batch-riport

## Probléma

Az FRL 3-5. lépéséhez (TEST → SCORE → DECIDE) nincs számító- és adminisztrációs réteg:
napi szektor-relatív Spearman IC, ICIR Newey-West korrekcióval, half-life, ledger-alapú
defláció (BH-FDR), holdout-ablak kezelés, és a heti riport.

## Megközelítés

### IC-motor (`scripts/research/frl_ic.py`)

- `daily_ic(panel, factor_col, h) -> Series` — szektoron belüli rank-korreláció a
  faktor és a szektor-relatív forward return között (spec §5.1); min 5 név/szektor/nap,
  alatta a szektor kimarad aznap (logolva)
- `aggregate(ic_series, h) -> dict` — mean_ic, icir, Newey-West t (lag=h−1), p;
  + nem-átfedő robusztussági nézet (minden h-adik nap); + éra-bontás (legacy/swing/pooled
  — pooled CSAK a két éra-oszlop mellett, G5)
- `era_bar(ic_series) -> float` — R1#2: `max(0.02, 2 × SE(mean IC))` a futáskori
  tényleges T_eff-ből; a PROMOTE-kritérium (b) pontja ezt használja, éránként
- `half_life(panel, factor_col) -> float` — napi keresztmetszeti rank-autokorreláció
  átlaga → t½ = −ln2/ln ρ; + `implied_turnover_cost_bps` — R1#3: a cost-input a
  `research/cost_model.json`-ból (a loader-task építi a pending_exits |slippage|
  medián/p75-ből), NEM konstans feltevés; fallback 75 bp/oldal ⚠️ kis-n

### Attempt-ledger (`scripts/research/frl_ledger.py`)

- Append-only `research/attempt_ledger.jsonl`, séma a spec §6 szerint
- KÖTELEZŐ sorrend: a sor `decision: "PENDING"`-gel a teszt FUTTATÁSA ELŐTT íródik
  (a "nem tetszett, nem logolom" kiskapu zárása); a metrikák és a döntés utólag
  frissülnek ugyanazon a soron (rewrite-on-close, backup-pal)
- `deflate(ledger) -> DataFrame` — BH-FDR q=0.10 a teljes történeten + Bonferroni
  másodoszlop; h-variánsok családkezelése Šidák-családi minimum-p-vel (spec §5.4)

### Holdout-kezelés (`scripts/research/frl_holdout.py`)

- Gördülő utolsó K=4 hét, 5 trading-napos purge a határon (spec §7)
- `holdout_test(hyp_id, factor)` — hipotézisenként EGYSZER hívható; a ledger
  `holdout_touched` flag-je gate-eli, ismételt hívás hard error
- Átmenet-kritérium kódolva: előjel-egyezés ÉS |IC_holdout| ≥ 0.5×|IC_dev| ÉS
  családi p < 0.10
- PROMOTE-előfeltételek kódolva (spec §5.4, R1#2/R1#4): éra-kvalifikált bar +
  swing-előjel minimum; legacy-only erő → `PARK_UNTIL_SWING_POWER` státusz,
  auto-retest újraértékelés minden batch-futáskor

### Batch-orchestrátor (`scripts/research/run_frl_batch.py`)

- CLI: `--date` (default: legutóbbi sync-nap), `--hyp HYP-###` (szűkítés), `--dry-run`
- **Per-faktor sanity-gate (R1#6) előfeltételként:** a batch minden faktorra előbb a
  `sanity()` párját futtatja (ismert-előjelű szintetikus panel → várt előjelű IC);
  bukott sanity → az attempt el sem indul, ledger-sor sem íródik, a riportban
  SANITY_FAIL bejegyzés
- Kimenet: `research/runs/YYYY-MM-DD/report.md` — éra-bontott IC-táblák, defláció-oszlopok,
  half-life, "inconclusive" jelölés ahol T_eff elégtelen (spec §5.5), holdout-érintés
  számláló, ledger-diff összefoglaló
- Riport-fejléc KÖTELEZŐ sora: "Leíró elemzés — Day 63 gate-input NEM (G1/G3)."
- Futtatás: MacBook, heti egyszer, a pénteki 22:16-os sync után; a Mini-t nem érinti

## Implementációs terv (fájlok)

Új:
- `scripts/research/frl_ic.py`
- `scripts/research/frl_ledger.py`
- `scripts/research/frl_holdout.py`
- `scripts/research/run_frl_batch.py`
- `scripts/research/frl_config.py` (K, q, cost_bps, min_sector_n — D_B/D_C ide)

Tesztek (`tests/test_frl_ic.py`, `tests/test_frl_ledger.py`, `tests/test_frl_holdout.py`):
- IC helyessége szintetikus panelen ismert korrelációval (pozitív/negatív/zéró)
- era_bar képlet: kis T_eff → magas bar; növekvő T_eff → 0.02 floor felé konvergál
- PARK_UNTIL_SWING_POWER auto-retest: szintetikus ledger + növekvő swing-minta →
  átsorolás pontosan a bar-átléphetőségi ponton
- sanity-gate: buggos (előjel-flippelt) faktor → SANITY_FAIL, nincs ledger-sor
- Newey-West vs naiv SE: overlapping szintetikus adaton a NW szélesebb CI-t ad
- min_sector_n kizárás
- ledger PENDING-first invariáns; rewrite-on-close backup
- BH-FDR ismert p-vektoron (kézzel számolt referenciával)
- holdout egy-érintés hard error; purge-határ helyessége NYSE-naptáron
- riport-generátor golden-file (szintetikus inputból determinisztikus md)

## Commit

`feat(research): FRL IC engine + attempt ledger + weekly batch report (freeze-safe)`
