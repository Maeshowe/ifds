# FRL batch — 2026-07-20

> **Leíró elemzés — Day 63 gate-input NEM (G1/G3).**

## Ablakok

- dev 2026-05-18..2026-06-12 | purge 2026-06-15..2026-06-22 | holdout 2026-06-23..2026-07-20
- Panel: legacy 64 nap, swing 19 nap
- Hiányzó nap: 2 (nem várt: 2) — soha nem interpolált
  - ⚠️ nem dokumentált hiány: 2026-04-06, 2026-04-07
- Adat-anomáliák: tech_filter_with_nonzero_score=0, unscored_masked_by_reason=5778

## Költségmodell (empirikus)

- 95.5 bp/oldal ⚠️ kis-n (medián), p75 137.0 bp, n=28, éra=swing
- Forrás: `state/daily_metrics/*.json::execution.slippage_per_ticker`

## Sanity-kapu

- PASS sector_relative_reversal_5d: ic=-1.000 expected_sign=-1

## IC — éra-bontásban (G5: pooled nézet nincs)

| Faktor | h | Éra | napok | T_eff | mean IC | ICIR | NW t | p | éra-bar | verdikt |
|---|---|---|---|---|---|---|---|---|---|---|
| `sector_relative_reversal_5d` | 1 | legacy | 59 | 59.0 | -0.0183 | -0.12 | -0.94 | 0.350 | 0.0388 | inconclusive |
| `sector_relative_reversal_5d` | 1 | swing | 19 | 19.0 | -0.0144 | -0.09 | -0.40 | 0.693 | 0.0718 | inconclusive |
| `sector_relative_reversal_5d` | 3 | legacy | 59 | 19.7 | -0.0143 | -0.11 | -0.82 | 0.421 | 0.0347 | inconclusive |
| `sector_relative_reversal_5d` | 3 | swing | 19 | 6.3 | -0.0705 | -0.50 | -1.88 | 0.118 | 0.0749 | inconclusive |
| `sector_relative_reversal_5d` | 5 | legacy | 59 | 11.8 | -0.0298 | -0.29 | -1.52 | 0.157 | 0.0393 | inconclusive |
| `sector_relative_reversal_5d` | 5 | swing | 19 | 3.8 | -0.0950 | -0.67 | -2.54 | 0.085 | 0.0749 | mérhető |
| `sector_relative_reversal_5d` | 7 | legacy | 59 | 8.4 | -0.0278 | -0.26 | -1.42 | 0.199 | 0.0392 | inconclusive |
| `sector_relative_reversal_5d` | 7 | swing | 19 | 2.7 | -0.1087 | -0.80 | -3.36 | 0.078 | 0.0647 | mérhető |

## Multiplicitás-defláció (a teljes ledger-történeten)

| Hipotézis | sáv | éra | variánsok | családi p (Šidák) | BH q=0.10 | Bonferroni |
|---|---|---|---|---|---|---|
| HYP-004 | v1 | legacy | 4 | 0.4946 | fail | fail |
| HYP-004 | v1 | swing | 4 | 0.2787 | fail | fail |

## Perzisztencia és forgási költség

| Faktor | half-life (nap) | implikált éves költség (bp) |
|---|---|---|
| `sector_relative_reversal_5d` | 2.4 | 19827 |

## Bruttó vs költséggel terhelt IC (§5.3 cost-kapu)

> Feltevés (az egyetlen): egy dollár-semleges, normalizált faktor-súlyú portfólió horizontonként ≈ `IC × σ_cs` hozamot termel (Grinold-közelítés). A per-oldal költség és a forgás **empirikus**.

| Faktor | h | Éra | mean IC | σ_cs | bruttó bp/év | költség bp/év | **nettó bp/év** | breakeven IC |
|---|---|---|---|---|---|---|---|---|
| `sector_relative_reversal_5d` | 1 | legacy | -0.0183 | 0.0273 | 1256 | 19827 | **-18571** ❌ | 0.2887 |
| `sector_relative_reversal_5d` | 1 | swing | -0.0144 | 0.0270 | 979 | 19827 | **-18848** ❌ | 0.2916 |
| `sector_relative_reversal_5d` | 3 | legacy | -0.0143 | 0.0462 | 554 | 19827 | **-19273** ❌ | 0.5107 |
| `sector_relative_reversal_5d` | 3 | swing | -0.0705 | 0.0495 | 2934 | 19827 | **-16893** ❌ | 0.4767 |
| `sector_relative_reversal_5d` | 5 | legacy | -0.0298 | 0.0605 | 909 | 19827 | **-18918** ❌ | 0.6505 |
| `sector_relative_reversal_5d` | 5 | swing | -0.0950 | 0.0658 | 3151 | 19827 | **-16676** ❌ | 0.5976 |
| `sector_relative_reversal_5d` | 7 | legacy | -0.0278 | 0.0745 | 745 | 19827 | **-19082** ❌ | 0.7393 |
| `sector_relative_reversal_5d` | 7 | swing | -0.1087 | 0.0761 | 2977 | 19827 | **-16849** ❌ | 0.7236 |

## Döntések

- **KILL** — `sector_relative_reversal_5d` h=1 (HYP-004, v1, attempt A-0001): BH-FDR not passed at the ledger-deflated level; swing era inconclusive (|IC|=0.0144 < bar 0.0718)
- **KILL** — `sector_relative_reversal_5d` h=3 (HYP-004, v1, attempt A-0002): BH-FDR not passed at the ledger-deflated level; swing era inconclusive (|IC|=0.0705 < bar 0.0749)
- **KILL** — `sector_relative_reversal_5d` h=5 (HYP-004, v1, attempt A-0003): BH-FDR not passed at the ledger-deflated level
- **KILL** — `sector_relative_reversal_5d` h=7 (HYP-004, v1, attempt A-0004): BH-FDR not passed at the ledger-deflated level

## Holdout

- Az aktuális holdout-ablakot eddig 0 hipotézis érintette.

## Megjegyzések

- A swing score-oszlop EWMA(5)-simított — a half-life a simítást is méri, nem csak a nyers jel perzisztenciáját (FRL-0 #5).
- A dev-ablak vége max(h) trading nappal a legutolsó bar-nap előtt van.
