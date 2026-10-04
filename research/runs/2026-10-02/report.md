# FRL batch — 2026-10-02

> **Leíró elemzés — Day 63 gate-input NEM (G1/G3).**

## Ablakok

- dev 2026-05-18..2026-08-28 | purge 2026-08-31..2026-09-04 | holdout 2026-09-08..2026-10-02
- Panel: legacy 64 nap, swing 62 nap
- Hiányzó nap: 12 (nem várt: 0) — soha nem interpolált
- Adat-anomáliák: tech_filter_with_nonzero_score=0, unscored_masked_by_reason=5784

## Költségmodell (empirikus)

- 83.5 bp/oldal (medián), p75 136.0 bp, n=82, éra=swing
- Forrás: `state/daily_metrics/*.json::execution.slippage_per_ticker`

## Sanity-kapu

- PASS tech_block: ic=+1.000 expected_sign=+1

## IC — éra-bontásban (G5: pooled nézet nincs)

| Faktor | h | Éra | napok | T_eff | mean IC | ICIR | NW t | p | éra-bar | verdikt |
|---|---|---|---|---|---|---|---|---|---|---|
| `tech_block` | 1 | legacy | 0 | 0.0 | n/a | n/a | n/a | n/a | ∞ | inconclusive |
| `tech_block` | 1 | swing | 62 | 62.0 | -0.0028 | -0.02 | -0.19 | 0.854 | 0.0303 | inconclusive |
| `tech_block` | 3 | legacy | 0 | 0.0 | n/a | n/a | n/a | n/a | ∞ | inconclusive |
| `tech_block` | 3 | swing | 62 | 20.7 | 0.0053 | 0.05 | 0.33 | 0.745 | 0.0322 | inconclusive |
| `tech_block` | 5 | legacy | 0 | 0.0 | n/a | n/a | n/a | n/a | ∞ | inconclusive |
| `tech_block` | 5 | swing | 62 | 12.4 | 0.0071 | 0.07 | 0.57 | 0.583 | 0.0251 | inconclusive |
| `tech_block` | 7 | legacy | 0 | 0.0 | n/a | n/a | n/a | n/a | ∞ | inconclusive |
| `tech_block` | 7 | swing | 62 | 8.9 | 0.0054 | 0.06 | 0.44 | 0.670 | 0.0244 | inconclusive |

## Multiplicitás-defláció (a teljes ledger-történeten)

| Hipotézis | sáv | éra | variánsok | családi p (Šidák) | BH q=0.10 | Bonferroni |
|---|---|---|---|---|---|---|
| HYP-008 | v1 | legacy | 4 | n/a | fail | fail |
| HYP-008 | v1 | swing | 4 | 0.9699 | fail | fail |

## Perzisztencia és forgási költség

| Faktor | half-life (nap) | implikált éves költség (bp) |
|---|---|---|
| `tech_block` | 2.8 | 15044 |

## Bruttó vs költséggel terhelt IC (§5.3 cost-kapu)

> Feltevés (az egyetlen): egy dollár-semleges, normalizált faktor-súlyú portfólió horizontonként ≈ `IC × σ_cs` hozamot termel (Grinold-közelítés). A per-oldal költség és a forgás **empirikus**.

> **(e) gazdasági kapu** (pre-reg 2026-10-04): PROMOTE-hoz `|mean IC| ≥ breakeven(p75)`. A medián és a p75 küszöb **közötti** sáv `INCONCLUSIVE_ON_COST` — soha nem kerekítjük PROMOTE-ra. A bukás `PARK_UNECONOMIC`, **nem KILL**: a gyógymód a végrehajtás, nem a faktor eldobása.

| Faktor | h | Éra | mean IC | σ_cs | bruttó bp/év | költség bp/év | **nettó bp/év** | breakeven IC (medián) | **breakeven IC (p75) ← kapu** | (e) |
|---|---|---|---|---|---|---|---|---|---|---|
| `tech_block` | 1 | legacy | n/a | 0.0273 | n/a | 15044 | **n/a** ❌ | 0.2190 | **0.3567** | — |
| `tech_block` | 1 | swing | -0.0028 | 0.0262 | 185 | 15044 | **-14858** ❌ | 0.2277 | **0.3709** | ❌ |
| `tech_block` | 3 | legacy | n/a | 0.0462 | n/a | 15044 | **n/a** ❌ | 0.3875 | **0.6311** | — |
| `tech_block` | 3 | swing | 0.0053 | 0.0461 | 205 | 15044 | **-14839** ❌ | 0.3885 | **0.6328** | ❌ |
| `tech_block` | 5 | legacy | n/a | 0.0605 | n/a | 15044 | **n/a** ❌ | 0.4936 | **0.8039** | — |
| `tech_block` | 5 | swing | 0.0071 | 0.0600 | 214 | 15044 | **-14830** ❌ | 0.4979 | **0.8109** | ❌ |
| `tech_block` | 7 | legacy | n/a | 0.0745 | n/a | 15044 | **n/a** ❌ | 0.5610 | **0.9137** | — |
| `tech_block` | 7 | swing | 0.0054 | 0.0710 | 138 | 15044 | **-14906** ❌ | 0.5889 | **0.9592** | ❌ |

## Döntések

> A batch verdiktje **auto** (mechanikusan triggerelt pre-reg kritérium), `human_confirmed: false`-szal születik. A döntés Tamásé (spec §10) — a megerősítés vagy felülírás explicit művelet.

- **KILL** (auto) — `tech_block` h=1 (HYP-008, v1, attempt A-0015): BH-FDR not passed at the ledger-deflated level; swing era inconclusive (|IC|=0.0028 < bar 0.0303); swing sign does not match the hypothesis (-0.0028 vs +1); swing sign contradiction — terminal (pre-reg b)
- **KILL** (auto) — `tech_block` h=3 (HYP-008, v1, attempt A-0016): BH-FDR not passed at the ledger-deflated level; swing era inconclusive (|IC|=0.0053 < bar 0.0322); adequate T_eff clean fail (swing T_eff=20.7, legacy T_eff=0.0 vs floor 6) — genuine null (pre-reg a)
- **KILL** (auto) — `tech_block` h=5 (HYP-008, v1, attempt A-0017): BH-FDR not passed at the ledger-deflated level; swing era inconclusive (|IC|=0.0071 < bar 0.0251); adequate T_eff clean fail (swing T_eff=12.4, legacy T_eff=0.0 vs floor 6) — genuine null (pre-reg a)
- **KILL** (auto) — `tech_block` h=7 (HYP-008, v1, attempt A-0018): BH-FDR not passed at the ledger-deflated level; swing era inconclusive (|IC|=0.0054 < bar 0.0244); adequate T_eff clean fail (swing T_eff=8.9, legacy T_eff=0.0 vs floor 6) — genuine null (pre-reg a)

### Megerősítésre váró döntések

| Attempt | Hipotézis | Variáns | Auto-verdikt | Zárva |
|---|---|---|---|---|
| A-0011 | HYP-006 | `flow_block_h1` | KILL | 2026-10-04T08:00:38+00:00 |
| A-0012 | HYP-006 | `flow_block_h3` | KILL | 2026-10-04T08:00:38+00:00 |
| A-0013 | HYP-006 | `flow_block_h5` | KILL | 2026-10-04T08:00:38+00:00 |
| A-0014 | HYP-006 | `flow_block_h7` | KILL | 2026-10-04T08:00:38+00:00 |
| A-0015 | HYP-008 | `tech_block_h1` | KILL | 2026-10-04T08:00:41+00:00 |
| A-0016 | HYP-008 | `tech_block_h3` | KILL | 2026-10-04T08:00:41+00:00 |
| A-0017 | HYP-008 | `tech_block_h5` | KILL | 2026-10-04T08:00:41+00:00 |
| A-0018 | HYP-008 | `tech_block_h7` | KILL | 2026-10-04T08:00:41+00:00 |

**8 döntés vár emberi megerősítésre.** Megerősítés: `frl_ledger.confirm_decision(attempt_id, by=..., note=...)`; felülírás: ugyanaz `decision=` paraméterrel (az auto-verdikt `auto_decision`-ként megmarad).

## Holdout

- Az aktuális holdout-ablakot eddig 0 hipotézis érintette.

## Megjegyzések

- A swing score-oszlop EWMA(5)-simított — a half-life a simítást is méri, nem csak a nyers jel perzisztenciáját (FRL-0 #5).
- A dev-ablak vége max(h) trading nappal a legutolsó bar-nap előtt van.
