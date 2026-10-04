Status: DONE
Updated: 2026-10-04
Note: A Dev/Chat FRL-szal zarodokumentuma (2026-07-21 -> 07-25). UTOLAGOS, VALTOZTATAS
NELKULI archivalas 2026-10-04-en — a torzs datumozott pillanatkep, ezert NEM lett
frissitve. FIGYELEM: a 2. szakasz a HYP-005-ot PARKED {h5,h7}-kent irja le; ezt az
e885ce3 (ujrateszt, KILL) es az 50eddb5 (komponens-dekompozicio) azota meghaladta.
A tenyleges allapot: docs/STATUS.md.

# FRL Dev Handoff — 2026-07-25

**Chat:** IFDS Dev (FRL-tervezés és -kiépítés, 2026-07-21 → 07-25)
**Következő session:** ebből a handoffból + a lenti belépési pontokból indul.
**Kanonikus dokumentumok:** `docs/design/2026-07-21-factor-research-loop-spec.md` (v2) ·
`docs/design/frl/TRACKER.md` (CC vezeti) · `docs/design/frl/hypotheses/` ·
`research/attempt_ledger.jsonl` · `research/runs/<date>/report.md`

---

## 1. Mi épült meg (S0–S6, MIND DONE)

A teljes Factor Research Loop infra, két lezárt hipotézis-fordulattal:

- **FRL-0 kapu** (GO, `30b948c`+`990d855`): score-szemantika audit — a scan-matrix
  Total_Score éra-konzisztens kanonikus oszlop (legacy: rácsos kompozit ≤05-15;
  swing: folytonos S_j EWMA(5) ≥05-18); JSONL swing-érában NEM score-validátor;
  tech_filter→NaN; score==0→NaN (9f49a38, Reason-felülírás gyökérokkal).
- **Loader + IC-motor + ledger + holdout + registry + lint** (`8b8b216`, `a02bc1d`,
  `7f74c58`): sector-relative Spearman IC h∈{1,3,5,7}, kézi Newey-West (statsmodels
  ellen validált, dev-only), BH-FDR q=0.10 + Šidák-család, éra-kvalifikált bar
  `max(0.02, 2×SE)`, PENDING-first ledger, holdout egy-érintés (K=4 hét, 5-nap purge),
  sanity-gate, hypothesis-first lint, PARK auto-retest.
- **Decision provenance** (`48451ce`): auto-verdikt + `confirm_decision` humán
  override, audit-lánccal.
- **T_eff-adekvácia gate** (2. fordulat fix): PARK-út legacy-láb nélkül is él;
  floor=6 pinelve; precedens-szabály az ifds-rules-ban ("motor-fix eredmény után
  KIZÁRÓLAG pre-reg-hez igazításként").
- **v2 enrichment sink ÉLESBEN** (D_A: Tamás IGEN 07-23; deploy 07-23-24, `08d072d`
  → `6ece241` → `0f52bf4`): `state/research_cross_section/YYYY-MM-DD.json.gz`,
  első fájl 07-24 verifikálva (238 = scan-matrix scored, swing_score/legacy_composite
  külön mező, 0 leak). Grep-audit teszt zárja a sink-patch rést strukturálisan.
- Tesztszám a hét elején 1985 → most **2182 passing**; 1 skip (statsmodels a Minin,
  szándékos).

## 2. Hipotézis-állapot

| HYP | Státusz | Lényeg |
|---|---|---|
| HYP-004 (5-napos szektor-rel. reversal) | **KILLED** (A-0001..04, Tamás 07-21) | 8/8 negatív előjel (mechanizmus-irány OK), defláció után nem válik el; breakeven IC 0.29–0.74 vs bar — nagyságrendi költség-rés. Alacsony-turnover variáns ÚJ HYP-ként nyitva. |
| HYP-005 (S_j élő aggregát, leíró ikertest) | **PARKED** (A-0005..08, Tamás 07-24) | h1: KILL (valódi null, T_eff 23); h3: KILL (szabály-vezérelt lezárás marginális erőn — NEM erős null); h5/h7: PARK-until-swing-power (+0.044/+0.052, jó előjel, alulfeszített). **Ébresztési család pre-reg: {h5, h7}, Šidák m=2, rögzítve 07-24.** G1 mindkét irányban — kapu-deliberációban NEM idézhető. |
| HYP-001b/002b/003b (nyers PCR / OTM-inv / RVOL) | DRAFT, v2 | 40-napos óra indult 07-24-én → tesztelhető ≈ **szept. közepe** (≈ Day 63 kapu környéke). Tartalmat Chat írja a beéréskor. |

## 3. Kulcs-számok és -szabályok (ne számold újra, itt vannak)

- Cost-model (`research/cost_model.json`, heti frissítés): swing |slippage| medián
  **97.0 bp/oldal** (n=31, 07-24-i állás), p75 ~137; legacy 19 bp. h=5 teljes rotáció
  ≈ ~9.5%/év költség-korlát. 04-risks §12.2-ben Day 63-inputként.
- bar_swing jelenleg ≈0.045–0.05 (T_eff(h=5)≈4.6–8 között horizonttól függően),
  heti ~5 nappal lazul.
- Governance: G1–G7 a specben; auto-verdikt human_confirmed-ig nem végleges;
  heti EGY batch (péntek, 22:16 sync után); pooled csak éra-bontással; holdout-touch
  eddig: **0**.

## 4. Nyitott / figyelendő tételek

1. **Pénteki ritmus**: batch (cost-model + PARK-családok auto-újraértékelés) → riport
   → Chat verdikt-javaslat CSAK ha van döntendő → Tamás megerősítés. A HYP-005
   ébresztés várhatóan szept. eleje-közepe (bar-zsugorodás), addig "not yet" sorok.
2. **Sub-score oszlop-audit** (CC-nél, egysoros): swing-érás Flow/Tech/Funda élő vagy
   halott kód-út — ettől függ, visszahozhatók-e komponens-szintű a-tesztek.
3. **04-risks §12.1**: `execution_plan.py:179` Reason-felülírás — post-Day-63 prod-fix
   jelölt (FRL-oldalon kezelve).
4. **Lookahead-assert**: HYP-005 pre-regben előírva (14:30 CEST jel vs t-close return
   kezdet) — CC jelezte a return-builderben, ellenőrizd a TRACKER-ben, hogy explicit
   teszt fedi-e.
5. Scan-matrix gap-lista a spec §4.5-ben (06-27→07-06, 07-15/16, 07-22, 04-06/07);
   új gap CSAK oda, interpoláció tilos.
6. `docs/analysis/` git-ből kivéve (sync-only), `docs/review/` tracked — a
   [[sync-delete-vs-local-commits]] feloldás kész, ne nyisd újra.

## 5. Session-nyitási protokoll (következő Dev session)

1. Olvasd: ez a handoff → `docs/design/frl/TRACKER.md` → legutóbbi
   `research/runs/<date>/report.md` → registry-státuszok.
2. Ellenőrizd a "Megerősítésre váró döntések" szekciót a legutóbbi riportban.
3. A Tamás-megerősítések (07-24: HYP-005 családi verdikt + T_eff-gate) CC-bevitelét
   verifikáld a ledgerben (A-0005..08 `human_confirmed: true`).
4. Freeze él Day 63-ig: FRL read-only lane, minden output leíró, G1/G3 változatlan.

## 6. Döntésnapló (Tamás)

| Dátum | Döntés |
|---|---|
| 07-21 | FRL-keret jóváhagyva; R1 (Log Review chat 6-pont) beépítve |
| 07-21 | FRL-0 GO; HYP-004 KILL megerősítve |
| 07-23 | **D_A: IGEN** (v2 sink freeze alatti deploy, R1-előfeltételekkel); D_B=4 hét, D_C=q0.10 |
| 07-24 | HYP-005: családi PARK, h1/h3 láb-KILL, ébresztési család {h5,h7}; T_eff-adekvácia gate a két kikötéssel |
