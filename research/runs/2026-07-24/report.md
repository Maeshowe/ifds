# FRL batch — 2026-07-24

> **Leíró elemzés — Day 63 gate-input NEM (G1/G3).**

## Ablakok

- dev 2026-05-18..2026-06-18 | purge 2026-06-22..2026-06-26 | holdout 2026-06-29..2026-07-24
- Panel: legacy 64 nap, swing 23 nap
- Hiányzó nap: 2 (nem várt: 2) — soha nem interpolált
  - ⚠️ nem dokumentált hiány: 2026-04-06, 2026-04-07
- Adat-anomáliák: tech_filter_with_nonzero_score=0, unscored_masked_by_reason=5779

## Költségmodell (empirikus)

- 97.0 bp/oldal (medián), p75 137.0 bp, n=31, éra=swing
- Forrás: `state/daily_metrics/*.json::execution.slippage_per_ticker`

## Sanity-kapu

- PASS sj_live_aggregate: ic=+1.000 expected_sign=+1

## IC — éra-bontásban (G5: pooled nézet nincs)

| Faktor | h | Éra | napok | T_eff | mean IC | ICIR | NW t | p | éra-bar | verdikt |
|---|---|---|---|---|---|---|---|---|---|---|
| `sj_live_aggregate` | 1 | legacy | 0 | 0.0 | n/a | n/a | n/a | n/a | ∞ | inconclusive |
| `sj_live_aggregate` | 1 | swing | 23 | 23.0 | 0.0079 | 0.10 | 0.51 | 0.617 | 0.0311 | inconclusive |
| `sj_live_aggregate` | 3 | legacy | 0 | 0.0 | n/a | n/a | n/a | n/a | ∞ | inconclusive |
| `sj_live_aggregate` | 3 | swing | 23 | 7.7 | 0.0235 | 0.29 | 1.01 | 0.347 | 0.0467 | inconclusive |
| `sj_live_aggregate` | 5 | legacy | 0 | 0.0 | n/a | n/a | n/a | n/a | ∞ | inconclusive |
| `sj_live_aggregate` | 5 | swing | 23 | 4.6 | 0.0435 | 0.65 | 2.37 | 0.077 | 0.0367 | mérhető |
| `sj_live_aggregate` | 7 | legacy | 0 | 0.0 | n/a | n/a | n/a | n/a | ∞ | inconclusive |
| `sj_live_aggregate` | 7 | swing | 23 | 3.3 | 0.0522 | 0.80 | 3.54 | 0.071 | 0.0295 | mérhető |

## Multiplicitás-defláció (a teljes ledger-történeten)

| Hipotézis | sáv | éra | variánsok | családi p (Šidák) | BH q=0.10 | Bonferroni |
|---|---|---|---|---|---|---|
| HYP-005 | v1 | legacy | 4 | n/a | fail | fail |
| HYP-005 | v1 | swing | 4 | 0.2564 | fail | fail |

## Perzisztencia és forgási költség

| Faktor | half-life (nap) | implikált éves költség (bp) |
|---|---|---|
| `sj_live_aggregate` | 10.3 | 4750 |

## Bruttó vs költséggel terhelt IC (§5.3 cost-kapu)

> Feltevés (az egyetlen): egy dollár-semleges, normalizált faktor-súlyú portfólió horizontonként ≈ `IC × σ_cs` hozamot termel (Grinold-közelítés). A per-oldal költség és a forgás **empirikus**.

| Faktor | h | Éra | mean IC | σ_cs | bruttó bp/év | költség bp/év | **nettó bp/év** | breakeven IC |
|---|---|---|---|---|---|---|---|---|
| `sj_live_aggregate` | 1 | legacy | n/a | 0.0273 | n/a | 4750 | **n/a** ❌ | 0.0691 |
| `sj_live_aggregate` | 1 | swing | 0.0079 | 0.0266 | 529 | 4750 | **-4221** ❌ | 0.0709 |
| `sj_live_aggregate` | 3 | legacy | n/a | 0.0462 | n/a | 4750 | **n/a** ❌ | 0.1223 |
| `sj_live_aggregate` | 3 | swing | 0.0235 | 0.0482 | 952 | 4750 | **-3798** ❌ | 0.1174 |
| `sj_live_aggregate` | 5 | legacy | n/a | 0.0605 | n/a | 4750 | **n/a** ❌ | 0.1558 |
| `sj_live_aggregate` | 5 | swing | 0.0435 | 0.0639 | 1403 | 4750 | **-3347** ❌ | 0.1474 |
| `sj_live_aggregate` | 7 | legacy | n/a | 0.0745 | n/a | 4750 | **n/a** ❌ | 0.1771 |
| `sj_live_aggregate` | 7 | swing | 0.0522 | 0.0748 | 1407 | 4750 | **-3342** ❌ | 0.1763 |

## Döntések

> A batch verdiktje **auto** (mechanikusan triggerelt pre-reg kritérium), `human_confirmed: false`-szal születik. A döntés Tamásé (spec §10) — a megerősítés vagy felülírás explicit művelet.

- **KILL** (auto) — `sj_live_aggregate` h=1 (HYP-005, v1, attempt A-0005): BH-FDR not passed at the ledger-deflated level; swing era inconclusive (|IC|=0.0079 < bar 0.0311)
- **KILL** (auto) — `sj_live_aggregate` h=3 (HYP-005, v1, attempt A-0006): BH-FDR not passed at the ledger-deflated level; swing era inconclusive (|IC|=0.0235 < bar 0.0467)
- **KILL** (auto) — `sj_live_aggregate` h=5 (HYP-005, v1, attempt A-0007): BH-FDR not passed at the ledger-deflated level
- **KILL** (auto) — `sj_live_aggregate` h=7 (HYP-005, v1, attempt A-0008): BH-FDR not passed at the ledger-deflated level

### Megerősítésre váró döntések

| Attempt | Hipotézis | Variáns | Auto-verdikt | Zárva |
|---|---|---|---|---|
| A-0005 | HYP-005 | `sj_live_aggregate_h1` | KILL | 2026-07-25T07:19:44+00:00 |
| A-0006 | HYP-005 | `sj_live_aggregate_h3` | KILL | 2026-07-25T07:19:44+00:00 |
| A-0007 | HYP-005 | `sj_live_aggregate_h5` | KILL | 2026-07-25T07:19:44+00:00 |
| A-0008 | HYP-005 | `sj_live_aggregate_h7` | KILL | 2026-07-25T07:19:44+00:00 |

**4 döntés vár emberi megerősítésre.** Megerősítés: `frl_ledger.confirm_decision(attempt_id, by=..., note=...)`; felülírás: ugyanaz `decision=` paraméterrel (az auto-verdikt `auto_decision`-ként megmarad).

## Holdout

- Az aktuális holdout-ablakot eddig 0 hipotézis érintette.

## Megjegyzések

- A swing score-oszlop EWMA(5)-simított — a half-life a simítást is méri, nem csak a nyers jel perzisztenciáját (FRL-0 #5).
- A dev-ablak vége max(h) trading nappal a legutolsó bar-nap előtt van.
