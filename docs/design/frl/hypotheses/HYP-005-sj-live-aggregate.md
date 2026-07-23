Status: REGISTERED
Updated: 2026-07-21
Data-lane: v1
Attempt-family: (a batch tölti)

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

(a batch tölti)

## KILL/PARK indoklás

(ha releváns)
