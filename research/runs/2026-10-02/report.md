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

- PASS funda_block: ic=+1.000 expected_sign=+1

## IC — éra-bontásban (G5: pooled nézet nincs)

| Faktor | h | Éra | napok | T_eff | mean IC | ICIR | NW t | p | éra-bar | verdikt |
|---|---|---|---|---|---|---|---|---|---|---|
| `funda_block` | 1 | legacy | 0 | 0.0 | n/a | n/a | n/a | n/a | ∞ | inconclusive |
| `funda_block` | 1 | swing | 62 | 62.0 | 0.0015 | 0.02 | 0.14 | 0.887 | 0.0215 | inconclusive |
| `funda_block` | 3 | legacy | 0 | 0.0 | n/a | n/a | n/a | n/a | ∞ | inconclusive |
| `funda_block` | 3 | swing | 62 | 20.7 | -0.0045 | -0.05 | -0.30 | 0.767 | 0.0301 | inconclusive |
| `funda_block` | 5 | legacy | 0 | 0.0 | n/a | n/a | n/a | n/a | ∞ | inconclusive |
| `funda_block` | 5 | swing | 62 | 12.4 | -0.0021 | -0.02 | -0.10 | 0.921 | 0.0408 | inconclusive |
| `funda_block` | 7 | legacy | 0 | 0.0 | n/a | n/a | n/a | n/a | ∞ | inconclusive |
| `funda_block` | 7 | swing | 62 | 8.9 | 0.0047 | 0.05 | 0.21 | 0.842 | 0.0457 | inconclusive |
| `funda_block` | 10 | legacy | 0 | 0.0 | n/a | n/a | n/a | n/a | ∞ | inconclusive |
| `funda_block` | 10 | swing | 62 | 6.2 | 0.0034 | 0.04 | 0.13 | 0.905 | 0.0545 | inconclusive |

## Multiplicitás-defláció (a teljes ledger-történeten)

| Hipotézis | sáv | éra | variánsok | családi p (Šidák) | BH q=0.10 | Bonferroni |
|---|---|---|---|---|---|---|
| HYP-007 | v1 | legacy | 5 | n/a | fail | fail |
| HYP-007 | v1 | swing | 5 | 0.9993 | fail | fail |

## Perzisztencia és forgási költség

| Faktor | half-life (nap) | implikált éves költség (bp) |
|---|---|---|
| `funda_block` | 799.8 | 53 |

## Bruttó vs költséggel terhelt IC (§5.3 cost-kapu)

> Feltevés (az egyetlen): egy dollár-semleges, normalizált faktor-súlyú portfólió horizontonként ≈ `IC × σ_cs` hozamot termel (Grinold-közelítés). A per-oldal költség és a forgás **empirikus**.

> **(e) gazdasági kapu** (pre-reg 2026-10-04): PROMOTE-hoz `|mean IC| ≥ breakeven(p75)`. A medián és a p75 küszöb **közötti** sáv `INCONCLUSIVE_ON_COST` — soha nem kerekítjük PROMOTE-ra. A bukás `PARK_UNECONOMIC`, **nem KILL**: a gyógymód a végrehajtás, nem a faktor eldobása.

| Faktor | h | Éra | mean IC | σ_cs | bruttó bp/év | költség bp/év | **nettó bp/év** | breakeven IC (medián) | **breakeven IC (p75) ← kapu** | (e) |
|---|---|---|---|---|---|---|---|---|---|---|
| `funda_block` | 1 | legacy | n/a | 0.0273 | n/a | 53 | **n/a** ❌ | 0.0008 | **0.0012** | — |
| `funda_block` | 1 | swing | 0.0015 | 0.0262 | 101 | 53 | **48** | 0.0008 | **0.0013** | ✅ |
| `funda_block` | 3 | legacy | n/a | 0.0462 | n/a | 53 | **n/a** ❌ | 0.0014 | **0.0022** | — |
| `funda_block` | 3 | swing | -0.0045 | 0.0461 | 175 | 53 | **123** | 0.0014 | **0.0022** | ✅ |
| `funda_block` | 5 | legacy | n/a | 0.0605 | n/a | 53 | **n/a** ❌ | 0.0017 | **0.0028** | — |
| `funda_block` | 5 | swing | -0.0021 | 0.0600 | 63 | 53 | **10** | 0.0017 | **0.0028** | ⚠️ sáv |
| `funda_block` | 7 | legacy | n/a | 0.0745 | n/a | 53 | **n/a** ❌ | 0.0020 | **0.0032** | — |
| `funda_block` | 7 | swing | 0.0047 | 0.0710 | 120 | 53 | **68** | 0.0021 | **0.0034** | ✅ |
| `funda_block` | 10 | legacy | n/a | 0.0914 | n/a | 53 | **n/a** ❌ | 0.0023 | **0.0037** | — |
| `funda_block` | 10 | swing | 0.0034 | 0.0842 | 73 | 53 | **20** | 0.0025 | **0.0040** | ⚠️ sáv |

## Döntések

> A batch verdiktje **auto** (mechanikusan triggerelt pre-reg kritérium), `human_confirmed: false`-szal születik. A döntés Tamásé (spec §10) — a megerősítés vagy felülírás explicit művelet.

- **KILL** (auto) — `funda_block` h=1 (HYP-007, v1, attempt A-0019): BH-FDR not passed at the ledger-deflated level; swing era inconclusive (|IC|=0.0015 < bar 0.0215); adequate T_eff clean fail (swing T_eff=62.0, legacy T_eff=0.0 vs floor 6) — genuine null (pre-reg a)
- **KILL** (auto) — `funda_block` h=3 (HYP-007, v1, attempt A-0020): BH-FDR not passed at the ledger-deflated level; swing era inconclusive (|IC|=0.0045 < bar 0.0301); swing sign does not match the hypothesis (-0.0045 vs +1); swing sign contradiction — terminal (pre-reg b)
- **KILL** (auto) — `funda_block` h=5 (HYP-007, v1, attempt A-0021): BH-FDR not passed at the ledger-deflated level; swing era inconclusive (|IC|=0.0021 < bar 0.0408); swing sign does not match the hypothesis (-0.0021 vs +1); swing sign contradiction — terminal (pre-reg b)
- **KILL** (auto) — `funda_block` h=7 (HYP-007, v1, attempt A-0022): BH-FDR not passed at the ledger-deflated level; swing era inconclusive (|IC|=0.0047 < bar 0.0457); adequate T_eff clean fail (swing T_eff=8.9, legacy T_eff=0.0 vs floor 6) — genuine null (pre-reg a)
- **KILL** (auto) — `funda_block` h=10 (HYP-007, v1, attempt A-0023): BH-FDR not passed at the ledger-deflated level; swing era inconclusive (|IC|=0.0034 < bar 0.0545); adequate T_eff clean fail (swing T_eff=6.2, legacy T_eff=0.0 vs floor 6) — genuine null (pre-reg a)

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
| A-0019 | HYP-007 | `funda_block_h1` | KILL | 2026-10-04T08:49:31+00:00 |
| A-0020 | HYP-007 | `funda_block_h3` | KILL | 2026-10-04T08:49:31+00:00 |
| A-0021 | HYP-007 | `funda_block_h5` | KILL | 2026-10-04T08:49:31+00:00 |
| A-0022 | HYP-007 | `funda_block_h7` | KILL | 2026-10-04T08:49:31+00:00 |
| A-0023 | HYP-007 | `funda_block_h10` | KILL | 2026-10-04T08:49:31+00:00 |

**13 döntés vár emberi megerősítésre.** Megerősítés: `frl_ledger.confirm_decision(attempt_id, by=..., note=...)`; felülírás: ugyanaz `decision=` paraméterrel (az auto-verdikt `auto_decision`-ként megmarad).

## Holdout

- Az aktuális holdout-ablakot eddig 0 hipotézis érintette.

## Megjegyzések

- A swing score-oszlop EWMA(5)-simított — a half-life a simítást is méri, nem csak a nyers jel perzisztenciáját (FRL-0 #5).
- A dev-ablak vége max(h) trading nappal a legutolsó bar-nap előtt van.
