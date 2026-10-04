# FRL batch — 2026-10-02

> **Leíró elemzés — Day 63 gate-input NEM (G1/G3).**

## Ablakok

- dev 2026-05-18..2026-08-28 | purge 2026-08-31..2026-09-04 | holdout 2026-09-08..2026-10-02
- Panel: legacy 64 nap, swing 62 nap
- Hiányzó nap: 12 (nem várt: 5) — soha nem interpolált
  - ⚠️ nem dokumentált hiány: 2026-04-06, 2026-04-07, 2026-07-22, 2026-08-07, 2026-08-21
- Adat-anomáliák: tech_filter_with_nonzero_score=0, unscored_masked_by_reason=5784

## Költségmodell (empirikus)

- 83.5 bp/oldal (medián), p75 136.0 bp, n=82, éra=swing
- Forrás: `state/daily_metrics/*.json::execution.slippage_per_ticker`

## Sanity-kapu

- PASS sj_live_aggregate: ic=+1.000 expected_sign=+1

## IC — éra-bontásban (G5: pooled nézet nincs)

| Faktor | h | Éra | napok | T_eff | mean IC | ICIR | NW t | p | éra-bar | verdikt |
|---|---|---|---|---|---|---|---|---|---|---|
| `sj_live_aggregate` | 5 | legacy | 0 | 0.0 | n/a | n/a | n/a | n/a | ∞ | inconclusive |
| `sj_live_aggregate` | 5 | swing | 62 | 12.4 | 0.0130 | 0.17 | 0.87 | 0.401 | 0.0298 | inconclusive |
| `sj_live_aggregate` | 7 | legacy | 0 | 0.0 | n/a | n/a | n/a | n/a | ∞ | inconclusive |
| `sj_live_aggregate` | 7 | swing | 62 | 8.9 | 0.0087 | 0.11 | 0.47 | 0.648 | 0.0368 | inconclusive |

## Multiplicitás-defláció (a teljes ledger-történeten)

| Hipotézis | sáv | éra | variánsok | családi p (Šidák) | BH q=0.10 | Bonferroni |
|---|---|---|---|---|---|---|
| HYP-005 | v1 | legacy | 2 | n/a | fail | fail |
| HYP-005 | v1 | swing | 2 | 0.6411 | fail | fail |

## Perzisztencia és forgási költség

| Faktor | half-life (nap) | implikált éves költség (bp) |
|---|---|---|
| `sj_live_aggregate` | 9.9 | 4241 |

## Bruttó vs költséggel terhelt IC (§5.3 cost-kapu)

> Feltevés (az egyetlen): egy dollár-semleges, normalizált faktor-súlyú portfólió horizontonként ≈ `IC × σ_cs` hozamot termel (Grinold-közelítés). A per-oldal költség és a forgás **empirikus**.

> **(e) gazdasági kapu** (pre-reg 2026-10-04): PROMOTE-hoz `|mean IC| ≥ breakeven(p75)`. A medián és a p75 küszöb **közötti** sáv `INCONCLUSIVE_ON_COST` — soha nem kerekítjük PROMOTE-ra. A bukás `PARK_UNECONOMIC`, **nem KILL**: a gyógymód a végrehajtás, nem a faktor eldobása.

| Faktor | h | Éra | mean IC | σ_cs | bruttó bp/év | költség bp/év | **nettó bp/év** | breakeven IC (medián) | **breakeven IC (p75) ← kapu** | (e) |
|---|---|---|---|---|---|---|---|---|---|---|
| `sj_live_aggregate` | 5 | legacy | n/a | 0.0605 | n/a | 4241 | **n/a** ❌ | 0.1392 | **0.2267** | — |
| `sj_live_aggregate` | 5 | swing | 0.0130 | 0.0600 | 393 | 4241 | **-3848** ❌ | 0.1404 | **0.2286** | ❌ |
| `sj_live_aggregate` | 7 | legacy | n/a | 0.0745 | n/a | 4241 | **n/a** ❌ | 0.1582 | **0.2576** | — |
| `sj_live_aggregate` | 7 | swing | 0.0087 | 0.0710 | 223 | 4241 | **-4019** ❌ | 0.1660 | **0.2704** | ❌ |

## Döntések

> A batch verdiktje **auto** (mechanikusan triggerelt pre-reg kritérium), `human_confirmed: false`-szal születik. A döntés Tamásé (spec §10) — a megerősítés vagy felülírás explicit művelet.

- **KILL** (auto) — `sj_live_aggregate` h=5 (HYP-005, v1, attempt A-0009): BH-FDR not passed at the ledger-deflated level; swing era inconclusive (|IC|=0.0130 < bar 0.0298); adequate T_eff clean fail (swing T_eff=12.4, legacy T_eff=0.0 vs floor 6) — genuine null (pre-reg a)
- **KILL** (auto) — `sj_live_aggregate` h=7 (HYP-005, v1, attempt A-0010): BH-FDR not passed at the ledger-deflated level; swing era inconclusive (|IC|=0.0087 < bar 0.0368); adequate T_eff clean fail (swing T_eff=8.9, legacy T_eff=0.0 vs floor 6) — genuine null (pre-reg a)

### Megerősítésre váró döntések

| Attempt | Hipotézis | Variáns | Auto-verdikt | Zárva |
|---|---|---|---|---|
| A-0009 | HYP-005 | `sj_live_aggregate_h5` | KILL | 2026-10-04T07:24:56+00:00 |
| A-0010 | HYP-005 | `sj_live_aggregate_h7` | KILL | 2026-10-04T07:24:56+00:00 |

**2 döntés vár emberi megerősítésre.** Megerősítés: `frl_ledger.confirm_decision(attempt_id, by=..., note=...)`; felülírás: ugyanaz `decision=` paraméterrel (az auto-verdikt `auto_decision`-ként megmarad).

## Holdout

- Az aktuális holdout-ablakot eddig 0 hipotézis érintette.

## Megjegyzések

- A swing score-oszlop EWMA(5)-simított — a half-life a simítást is méri, nem csak a nyers jel perzisztenciáját (FRL-0 #5).
- A dev-ablak vége max(h) trading nappal a legutolsó bar-nap előtt van.
