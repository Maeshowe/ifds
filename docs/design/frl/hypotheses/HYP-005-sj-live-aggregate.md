Status: TESTED
Updated: 2026-10-04
Data-lane: v1
Attempt-family: A-0005..A-0008 (2026-07-24; h5/h7 PARK, h1/h3 KILL — Tamás megerősítve) | ÚJRATESZT 2026-10-04: a pre-regisztrált {h5,h7} családra, m=2

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

## ÚJRATESZT-FELHATALMAZÁS (2026-10-04)

`Status: PARKED → TESTED`. Indoklás, tételesen:

1. **A család előre rögzítve.** `{h5, h7}`, Šidák **m=2** — a fenti
   „Ébresztési család" szekcióban, **2026-07-24-én, a retest-adat ELŐTT**. A futás
   `--horizons 5,7`-tel megy; a h1/h3 **terminálisan KILLED**, azokra attempt nem
   nyílik (házszabály: *„Nincs újrafuttatás verdikt-generálásért"*).
2. **Az erő megnőtt.** Az első batch dev-ablaka swing **23 nap** volt (05-18..06-18);
   a swing-éra most **~96 session**-ig tart (10-02). A h=5 T_eff 4.6 volt a 6,0-os
   adekvácia-floor alatt — ez a PARK (c) indoka; a megnövelt mintán a floor
   átléphető, tehát az újrateszt **esedékes és most már feszített**.
3. **Az értékelő-motor az újrateszt ELŐTT változott, nem utána.** A (e) gazdasági
   kapu (`docs/planning/2026-10-04-economic-gate-preregistration.md`, Tamás D-E1…D-E4
   elfogadva) **a futás előtt** került be, időzítési tanúsítvánnyal. A kapu csak a
   PROMOTE-ágat fogja el; a HYP-005 korábbi KILL/PARK verdiktjeit regressziós teszt
   őrzi (`TestConfirmedVerdictsAreUnchanged`).
4. **A korábbi ledger-sorok érintetlenek.** Az A-0005..A-0008 a régi
   auto-verdikten és Tamás megerősítésén marad; az újrateszt **új** attempt-sorokat
   nyit, nem írja át a régieket.

⚠️ **G1/G3 változatlanul:** a kapu-futás 2026-10-03-án lezárult, tehát a G3 nyelvi
tilalom feloldódott — de ez a mérés **post-gate, leíró**, a kapu mintájába vagy a §3
küszöbeibe visszamenőleg **nem** számít be. És a kapu ρ-ja (trade-szintű, n=79,
range-restricted) **nem összemérhető** az itt mért keresztmetszeti `mean_IC`-vel
(lásd a 2026-10-04-i helyreigazítást, `04-risks` §11.24).

## ÚJRATESZT EREDMÉNY (2026-10-04, A-0009 / A-0010)

Dev swing **62 nap** (05-18..08-28), legacy üres, holdout-érintés **0**.
Futás: `--hyp HYP-005 --horizons 5,7 --date 2026-10-02`.

| h | T_eff | mean IC | NW t | p | éra-bar | auto-verdikt |
|---|---:|---:|---:|---:|---:|---|
| **5** | **12.4** | **+0.0130** | 0.87 | 0.401 | 0.0298 | **KILL** — adekvát erő, valódi null (a) |
| **7** | **8.9** | **+0.0087** | 0.47 | 0.648 | 0.0368 | **KILL** — adekvát erő, valódi null (a) |

Šidák-családi p (m=2): **0.6411** (BH-fail). A 2026-07-24-i `PARK_UNTIL_SWING_POWER`
ezzel **feloldva**: a T_eff a 6,0-os floor fölé került (12.4 és 8.9), és a jel **nem
jelent meg** — ez a pre-reg **(a)** kritériuma.

⚠️ **Verdikt `auto`, `human_confirmed: false` — Tamás megerősítésére vár.**
Status `TESTED` marad, amíg a `TESTED → KILLED` tranzíció meg nem történik.

🔴 **Stale-cache csapda, elkapva:** az első dry-run a 2026-07-25-i
`returns.parquet`-ből olvasott (`fwd_ret_5` csak 07-17-ig) → 35 nap, mean IC
**+0.0384**, Šidák p **0.0440**, **BH PASS** → **(a)–(d) mind teljesült**, a verdikt
`PARK_UNECONOMIC` lett volna (és a (e) kapu nélkül **PROMOTE**: bruttó 1 182 bp/év vs
költség 4 241 bp/év = **nettó −30,6%/év**). A return-mátrix újraépítése után (162 nap)
a +0.0384 **+0.0130-ra regresszált**. Részletek:
`docs/review/2026-10-04-hyp005-retest.md` §2.

**Ezzel az aggregát mind a 4 horizonton KILL adekvát erővel** (h1 T_eff 23, h3 7.7,
h5 12.4, h7 8.9). A család egyetlen nyitott kérdése a **komponens-dekompozíció**
(HYP-006/007/008), ami **ennek a futásnak az eredménye ELŐTT** került regisztrálásra.
