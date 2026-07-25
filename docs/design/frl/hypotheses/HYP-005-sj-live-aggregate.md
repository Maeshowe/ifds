Status: PARKED
Updated: 2026-07-24
Data-lane: v1
Attempt-family: A-0005..A-0008 (2026-07-24; h5/h7 PARK, h1/h3 KILL — Tamás megerősítve)

# HYP-005 — S_j élő aggregát, keresztmetszeti IC (transzform-szintű)

## Mechanizmus

Az S_j a legacy Day 63 dekompozíció két Bonferroni-szignifikáns komponenséből épült
(PCR +0.203**, OTM-call −0.194**, 232 ügylet, trade-szinten) — PCR-percentilis +
OTM-inverse-percentilis, EWMA(5). A közgazdasági történet: a magas PCR-percentilis
pesszimista opciós pozícionálást jelez (rövid horizontú contrarian prémium), az
OTM-inverz a retail-FOMO-val szembeni fogadás. Ez a hipotézis azt teszi mérhetővé,
amit eddig csak feltettünk: hogy a trade-szintű legacy finding keresztmetszeti,
transzformált formában is él-e. FONTOS: ez a signal_attribution kapu-teszt LEÍRÓ
ikertestje — G1 mindkét irányban: az eredménye a Day 63 deliberációban nem
idézhető, se pro, se kontra.

## Várt előjel és horizont

POZITÍV; h=5 elsődleges (a rendszer tartási horizontja), a h-görbe várhatóan púpos
(h=3–5 maximum). Sanity: expected_sign=+1.

## Ki a vesztes oldal / milyen frikció tartja fenn

Rövid horizontú retail opciós flow-chaserek; a jel részvény-oldali kiaknázása
keresztmetszeti infrastruktúrát és inventory-kockázat-viselést igényel — ezért
nem arbitrálódik el azonnal.

## Költségprofil (várt turnover)

Az EWMA(5) simítás mérsékelt turnover-t implikál; várt half-life 4–8 nap (mérendő
— az első empirikus half-life adat magáról az élő jelről); costed-IC a
cost_model.json aktuális swing-értékén (jelenleg 95.5 bp/oldal).

## Pre-reg metrika és kill-kritérium

Standard §5.1–5.4; éra: KIZÁRÓLAG swing (a legacy Total_Score más képlet, az
éra-guard dobja). Lookahead-konvenció: a jel a 14:30 CEST futásból, a forward
return t-napi close-tól — assert-tel rögzítve a return-builderben.
Kill/Park: (a) családi Šidák p ≥ 0.10 elégséges T_eff mellett → KILL mint
FRL-faktorjelölt (leíró verdikt, NEM kapu-állítás); (b) szignifikáns NEGATÍV
előjel → KILL, a mechanizmus-tézis keresztmetszeti formája megdőlt (szintén
leíró); (c) T_eff elégtelen → PARK-until-swing-power, auto-retest (a bar heti
~5 nappal lazul).

## Eredmény

**Első batch (2026-07-24, A-0005..A-0008)** — dev swing 23 nap (05-18..06-18),
legacy üres (swing-only), holdout-érintés **0**.

| h | T_eff | mean IC | NW t | p | éra-bar | verdikt (Tamás megerősítve 2026-07-24) |
|---|---|---|---|---|---|---|
| 1 | 23.0 | +0.0079 | 0.51 | 0.617 | 0.0311 | **KILL** — adekvát erő, valódi null (a) |
| 3 | 7.7 | +0.0235 | 1.01 | 0.347 | 0.0467 | **KILL** — szabály-vezérelt lezárás marginális erőn (floor fölött, de bar≈0.045 vs mért 0.024, nem erős null-bizonyíték) |
| **5** | **4.6** | **+0.0435** | **2.37** | 0.077 | 0.0367 | **PARK_UNTIL_SWING_POWER** — alulfeszített, jó előjel (c) |
| 7 | 3.3 | +0.0522 | 3.54 | 0.071 | 0.0295 | **PARK_UNTIL_SWING_POWER** — alulfeszített, jó előjel (c) |

Šidák-családi p (m=4): **0.2564** (BH-fail). Half-life **10.3 nap**; implikált
forgás 4750 bp/év; breakeven IC 0.15–0.18 (költség-kapu külön, jövőbeli akadály —
a HYP-005 G1 szerint NEM tradeability-állítás). A h-görbe **emelkedő** (0.008→0.052),
a maximum **nem lokalizált** a dev-ablakon belül → a horizont-választás önmagában
nem post-hoc; a családi defláció (Šidák) kezeli.

## Ébresztési család — PRE-REGISZTRÁCIÓ (rögzítve 2026-07-24, a retest-adat ELŐTT)

**A PARK-olt család: {h5, h7}, Šidák m=2.** A h1/h3 a pre-reg (a) kritérium szerint
**terminálisan KILLED** (adekvát T_eff, tiszta null) — végleg kikerültek a családból.
A jövőbeli auto-retest (`retest_due`, a bar heti ~5 nappal lazuló szintjén) **csak
a {h5, h7} párra** fut, m=2 Šidák-korrekcióval.

**Miért ITT és MOST rögzítjük:** a család-szűkítés (m=4 → m=2) utólag, a retest-adat
látása után **támadható lenne** (garden-of-forking-paths). Azzal, hogy a szűkítés
indoka (h1/h3 adekvát-erős KILL) és a maradék család ({h5,h7}, m=2) a **retest ELŐTT**
kerül írásba, a szűkítés **pre-regisztrált**, nem post-hoc. Ez a sor a governance-lényeg.

## KILL/PARK indoklás

A verdikt-javaslat teljes indoklása: `research/runs/2026-07-24/verdict-proposal.md`.
Kulcs: az előjel helyes mind a 4 horizonton, a primary h=5 T_eff=4.6 a §5.5
detektálhatósági küszöb (≈6) alatt → a családi p bukása **erő-korlátos, nem
null-jelzés** → (c) PARK. A holdout **nem** költött. A v2 sáv (HYP-001b/002b)
~szeptember közepén érik; a HYP-005 (transzform) + v2 (nyers) együtt adja az a/b-képet.
