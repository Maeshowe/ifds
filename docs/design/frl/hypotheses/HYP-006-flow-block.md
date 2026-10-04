Status: TESTED
Updated: 2026-10-04
Data-lane: v1
Attempt-family: A-0011..A-0014 (pre-reg: docs/planning/2026-10-04-component-decomposition-preregistration.md)

# HYP-006 — Flow blokk keresztmetszeti IC (az S_j 0,60 súlyú komponense)

> **Keret:** a HYP-005 aggregát mind a 4 horizonton KILL, adekvát erővel
> (A-0005..A-0010, Tamás megerősítve). Egy aggregát-null **szerkezetileg nem
> tudja** szétválasztani, hogy (i) egyik komponensnek sincs jele, vagy (ii) a
> komponensek **kioltják** egymást a fix 0,60/0,10/0,30 keverésben. A megfigyelt
> +0,0130 mindkettővel egyformán konzisztens (pl. Flow +0,04 és Tech −0,03 →
> 0,60·0,04 + 0,30·(−0,03) = +0,015). Ez a hipotézis az első komponenst mérei.

## Mechanizmus (MIÉRT létezne — kötelező, teszt ELŐTT írva)

Szokatlanul magas relatív volumen **szűk spreaddel** (squat bar) intézményi
akkumulációt jelez a mozgás előtt: a vevő méretet gyűjt anélkül, hogy az árat
elvinné. A `buy_pressure` komponens ugyanezt a napon belüli lábnyomot méri a
záróár bar-on belüli pozíciójával és a VWAP-hoz mért viszonyával. A vesztes oldal
a **passzív és retail flow**, ami anélkül kereskedik, hogy az akkumulációt látná,
és likviditást ad az információval rendelkező vevőnek.

⚠️ **Összetétel-figyelmeztetés:** a blokk a `flow.rvol_score` mezőre épül, ami a
neve ellenére **7-tagú összeg** (`rvol`, `squat`, `pcr`, `otm`, `block_trade`,
`dp_pct`, `buy_pressure`). Ebből **4 tag UW-eredetű** és a UW **kivezetve**
(`docs/decisions/2026-08-18-uw-decommission.md`). Ezért egy PROMOTE **önmagában
nem jogosít élesítésre**, amíg nem tisztázott, hogy a jel a Polygon-tagokból
jön-e — az al-score-dekompozíció **külön pre-reg, szűkebb univerzum**
(pre-reg §3.1, §6.4).

## Várt előjel és horizont

**POZITÍV** (`expected_sign = +1`). A volumen-jelek **gyorsan bomlanak**, ezért a
maximumot **h=1 / h=3** körül várjuk, és **csökkenő** h-görbét h=5 → h=7 felé.
Ha a görbe **emelkedő**, az a mechanizmus ellen szól, nem mellette.

## Ki a vesztes oldal / milyen frikció tartja fenn

Passzív/retail likviditás-adók és indexkövető flow. A jel részvény-oldali
kiaknázása keresztmetszeti infrastruktúrát és inventory-kockázat-viselést kíván,
ezért nem arbitrálódik el azonnal — de a frikció **kétélű**: a gyors bomlás
magas forgást követel, és a forgás a saját költségét termeli (lásd alább).

## Költségprofil (várt turnover)

🔴 **Mért (2026-10-04, a hozamoktól független):** napi rang-autokorreláció
**ρ = 0,151** → **half-life 0,4 nap**. Ez a 83,5 bp/oldal empirikus költségen
`(252/0,4) × 2 × 83,5 ≈ **114 682 bp/év**` implikált forgási költséget ad, amiből
a **breakeven IC (h=5) ≈ 3,79** — ami **matematikailag lehetetlen** (|IC| ≤ 1).

**Következmény, előre kimondva:** ez a blokk ezen a végrehajtási költségen
**bármilyen elérhető IC mellett gazdaságilag halott**. A (e) kapu ezért
mechanikusan `PARK_UNECONOMIC`-ot ad, ha statisztikai jelet talál — és ez a
**helyes** olvasat: *a jel lehet valós, de a forgása miatt nem kiaknázható.*
A gyógymód a **végrehajtás** (SIM-EXEC, 04-risks §11.24), nem a faktor eldobása.
Referenciaként: 1 bp/oldal végrehajtáson a breakeven IC ≈ 0,045 lenne.

## Pre-reg metrika és kill-kritérium

Standard §5.1–5.4 + a (e) gazdasági kapu (2026-10-04). Éra: **KIZÁRÓLAG swing**.
Kötelező szűrő: **`|Total_Score| > 1e-9`** — a nem pontozott sorokban a
`Flow_Score` a **default 50**-en áll (36 557 valós soron verifikálva), ami 43%-os
konstans masszát injektálna a napi rangsorba (pre-reg §4.1).

Kill/Park: (a) családi Šidák p a BH-deflált szinten bukik **adekvát T_eff
(≥ 6) mellett** → **KILL**; (b) szignifikáns **NEGATÍV** előjel → KILL (a
mechanizmus keresztmetszeti formája megdőlt); (c) T_eff elégtelen → **PARK**
auto-retesttel; (e) statisztikailag átmegy, de `|mean IC| < breakeven(p75)` →
**`PARK_UNECONOMIC`**.

⚠️ **Felbontás-korlát:** a `Flow_Score` napi **~16,7 distinct** értéket vesz fel
~561 név között, tehát holtversenyben gazdag → a Spearman **a nulla felé**
attenuál. Egy **null gyengébb** bizonyíték, mint egy pozitív lelet
(pre-reg §4.2). Diagnosztika kötelező a riportban.

## Eredmény (2026-10-04)

Dev swing **62 nap** (05-18..08-28), legacy üres, holdout-érintés **0**.

| h | T_eff | mean IC | éra-bar | p | verdikt |
|---|---:|---:|---:|---:|---|
| 1 | 62.0 | +0,0089 | 0.0273 | 0.517 | KILL (A-0011) — adekvát erő, valódi null (a) |
| 3 | 20.7 | −0,0021 | 0.0260 | 0.875 | KILL (A-0012) — a motor (b)-t írt, de (a) is tüzelt volna |
| 5 | 12.4 | −0,0011 | 0.0275 | 0.937 | KILL (A-0013) — ugyanaz |
| 7 | 8.9 | −0,0080 | 0.0295 | 0.603 | KILL (A-0014) — ugyanaz |

Šidák-családi p (m=4, swing): **0,9455** → BH q=0,10 **fail**.
**Mind a 4 kar a 6,0-os adekvácia-floor FÖLÖTT bukott** → pre-reg **(a): valódi null**.
A h=1 karon a T_eff **62,0** — a projekt eddigi legerősebb null-mérése.

**A h-görbe alakja:** maximum h=1-en, majd lefordul — **a pre-regisztrált alak**. A mechanizmus tehát **nem fordítva** működik —
mérhető nagyságrendben **nincs jelen**.

⚠️ **Verdikt `auto`, `human_confirmed: false` — Tamás megerősítésére vár.**
Riport: `docs/review/2026-10-04-component-decomposition.md`

## KILL/PARK indoklás (ha releváns)

—
