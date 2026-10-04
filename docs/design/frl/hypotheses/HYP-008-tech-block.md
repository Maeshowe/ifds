Status: TESTED
Updated: 2026-10-04
Data-lane: v1
Attempt-family: A-0015..A-0018 (pre-reg: docs/planning/2026-10-04-component-decomposition-preregistration.md)

# HYP-008 — Technical blokk keresztmetszeti IC (az S_j 0,30 súlyú komponense)

> **Keret:** lásd HYP-006. Az aggregát-null nem tudja szétválasztani a
> „nincs jel" és a „kioltják egymást" eseteket; ez a hipotézis a technikai
> komponenst mérei külön.

## Mechanizmus (MIÉRT létezne — kötelező, teszt ELŐTT írva)

**Keresztmetszeti momentum / trend-perzisztencia.** A blokk három tagja
(`rsi_score` + `sma50_bonus` + `rs_spy_score`) együtt azt rangsorolja, hogy egy
papír a saját trendjében és a piachoz képest hol áll. A közgazdasági történet a
szakirodalom **legtöbbször replikált anomáliája**: az árfolyam-momentum
alulreagálásból és lassú információ-diffúzióból táplálkozik, a vesztes oldal
pedig a **disposition effect** szerint túl korán eladó befektető, aki a
nyertesét realizálja és a vesztesét tartja.

📌 **Ez a három közül a legerősebb a priori jelölt**: ennek van független,
külső szakirodalmi támasza — a Flow és a Funda mechanizmusa házon belüli.
Következésképp **ha ez is tiszta null adekvát erővel, az erős jelzés a teljes
jelcsalád ellen**, nem csak egy komponens ellen.

## Várt előjel és horizont

**POZITÍV** (`expected_sign = +1`). A momentum **több napon akkumulál**, ezért a
maximumot **h=5–7** körül várjuk, és **emelkedő** h-görbét h=1 → h=7 felé.

## Ki a vesztes oldal / milyen frikció tartja fenn

Disposition-effect szerint korán realizáló befektetők és a lassan áttételeződő
információ. A frikció, ami fenntartja: a momentum **drawdown-kockázata**
(momentum-crash), amit sok szereplő nem tud elhordozni — ez tartja a prémiumot.

## Költségprofil (várt turnover)

🔴 **Mért (2026-10-04, a hozamoktól független):** napi rang-autokorreláció
**ρ = 0,781** → **half-life 2,8 nap**. A 83,5 bp/oldal empirikus költségen
`(252/2,8) × 2 × 83,5 ≈ **15 044 bp/év**`, amiből a **breakeven IC (h=5) ≈ 0,4975**.

**Következmény, előre kimondva:** 0,50-es IC-t keresztmetszeti faktor
**gyakorlatilag nem produkál**. Ez a blokk tehát ezen a végrehajtási költségen is
**gazdaságilag halott**, és a (e) kapu `PARK_UNECONOMIC`-ot fog adni, ha
statisztikai jelet talál. Referenciaként: **1 bp/oldal** végrehajtáson a
breakeven IC ≈ **0,006** lenne — vagyis ez a blokk **csak közel ingyenes
végrehajtással** válik életképessé. A gyógymód a végrehajtás, nem a faktor.

## Pre-reg metrika és kill-kritérium

Standard §5.1–5.4 + a (e) gazdasági kapu (2026-10-04). Éra: **KIZÁRÓLAG swing**.
Kötelező szűrő: **`|Total_Score| > 1e-9`** (pre-reg §4.1) — a nem pontozott
sorok kizárása. (A `Tech_Score` a nem pontozott sorokban **valódi** értéket
hordoz, nem defaultot, de a szűrő egységesen alkalmazandó: a három blokkot
ugyanazon a mintán kell mérni, különben a blokkok nem összehasonlíthatók.)

Kill/Park: azonos a HYP-006-tal — (a) adekvát T_eff-en bukó családi p → KILL;
(b) szignifikáns negatív előjel → KILL; (c) elégtelen T_eff → PARK;
(e) `|mean IC| < breakeven(p75)` → `PARK_UNECONOMIC`.

⚠️ **Felbontás-korlát:** a `Tech_Score` napi **~6 distinct** értéket vesz fel
~561 név között — erős holtverseny, a Spearman **a nulla felé** attenuál. Egy
**null gyenge** bizonyíték ezen a karon (pre-reg §4.2); egy pozitív lelet erős.

## Eredmény (2026-10-04)

Dev swing **62 nap** (05-18..08-28), legacy üres, holdout-érintés **0**.

| h | T_eff | mean IC | éra-bar | p | verdikt |
|---|---:|---:|---:|---:|---|
| 1 | 62.0 | −0,0028 | 0.0303 | 0.854 | KILL (A-0015) — a motor (b)-t írt, de (a) is tüzelt volna |
| 3 | 20.7 | +0,0053 | 0.0322 | 0.745 | KILL (A-0016) — adekvát erő, valódi null (a) |
| 5 | 12.4 | +0,0071 | 0.0251 | 0.583 | KILL (A-0017) — adekvát erő, valódi null (a) |
| 7 | 8.9 | +0,0054 | 0.0244 | 0.670 | KILL (A-0018) — adekvát erő, valódi null (a) |

Šidák-családi p (m=4, swing): **0,9699** → BH q=0,10 **fail**.
**Mind a 4 kar a 6,0-os adekvácia-floor FÖLÖTT bukott** → pre-reg **(a): valódi null**.
A h=1 karon a T_eff **62,0** — a projekt eddigi legerősebb null-mérése.

**A h-görbe alakja:** h=1-ről emelkedik, maximum h=5-en — **a pre-regisztrált alak**. A mechanizmus tehát **nem fordítva** működik —
mérhető nagyságrendben **nincs jelen**.

⚠️ **Verdikt `auto`, `human_confirmed: false` — Tamás megerősítésére vár.**
Riport: `docs/review/2026-10-04-component-decomposition.md`

## KILL/PARK indoklás (ha releváns)

—
