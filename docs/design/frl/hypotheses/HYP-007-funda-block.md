Status: DRAFT
Updated: 2026-10-04
Data-lane: v1
Attempt-family: — (SZÁNDÉKOSAN VISSZATARTVA, lásd §Visszatartás)

# HYP-007 — Fundamentals blokk keresztmetszeti IC (az S_j 0,10 súlyú komponense)

> ⛔ **`Status: DRAFT` — ez SZÁNDÉKOS, nem befejezetlenség.** A DRAFT a motorban
> **blokkolja az attempteket** (`RUNNABLE_STATUSES = ("REGISTERED", "TESTED")`).
> Az ok a §Visszatartás szekcióban: a regisztrált horizont-rács **félre-specifikált
> ehhez a faktorhoz**, és egy félre-specifikált teszten rögzített KILL **elégetné**
> a hipotézist. Governance-döntésre vár.

## Mechanizmus (MIÉRT létezne — kötelező, teszt ELŐTT írva)

**Minőség/érték prémium.** A blokk az FMP-fundamentumokból és a shark/insider
jelből épül. A közgazdasági történet: a befektetők **túl-extrapolálják** a rossz
közelmúltbeli fundamentumokat, és a minőségi papírokat tartósan diszkonttal
árazzák; a korrekció lassan, több negyedéven át következik be. A vesztes oldal a
rövid horizonton extrapoláló befektető.

⚠️ **Ismert prior, előre kimondva:** a **BC23** épp azért vitte le ennek a
blokknak a súlyát **0,30 → 0,10**-re, mert *„no P&L correlation"*. Ez tehát
részben **egy ismert null újratesztje** — ezt azért rögzítem, hogy az eredmény
utólag ne legyen „megerősítésként" olvasható. **De:** az a mérés **trade-szinten,
5 napos tartáson** történt, ahol egy ~800 napos half-life-ú jel **nem tud
megnyilvánulni**. A korábbi null tehát **nem** zárja le a kérdést — rossz
időskálán mérték.

## Várt előjel és horizont

**POZITÍV** (`expected_sign = +1`). **Lassú faktor:** a maximumot a **leghosszabb**
elérhető horizonton várjuk, monoton **emelkedő** h-görbével (h=7 ≥ h=5 > h=3 > h=1).
A h ∈ {1,3,5,7} rács a saját half-life-jának **0,1–0,9%-a** — lásd §Visszatartás.

## Ki a vesztes oldal / milyen frikció tartja fenn

Rövid horizonton extrapoláló befektetők és a negyedéves beszámolási ciklushoz
kötött figyelem. A frikciót a **horizont-kockázat** tartja fenn: a prémium
begyűjtése hónapokig tartó pozíciót és tracking-error-tűrést kíván, amit a
legtöbb szereplő nem tud elhordozni.

## Költségprofil (várt turnover)

🟢 **Mért (2026-10-04, a hozamoktól független):** napi rang-autokorreláció
**ρ = 0,999** → **half-life 799,8 nap**. A faktor gyakorlatilag **statikus**
(az FMP-fundamentumok negyedévente frissülnek, és a blokk mindössze 5 distinct
szintet vesz fel).

A 83,5 bp/oldal empirikus költségen `(252/799,8) × 2 × 83,5 ≈ **53 bp/év**`,
amiből a **breakeven IC (h=5) ≈ 0,0017**.

> 🟢 **Ez a három blokk közül az EGYETLEN, aminek életképes költségszerkezete
> van** — a breakeven IC **~80-szor alacsonyabb** az aggregátnál (0,1403) és
> **~2 200-szor** a Flow-blokknál (3,79). Ha ennek a blokknak **bármilyen**
> ~0,002 feletti keresztmetszeti IC-je van, **kifizeti a saját kereskedését.**

## Pre-reg metrika és kill-kritérium

Standard §5.1–5.4 + a (e) gazdasági kapu (2026-10-04). Éra: **KIZÁRÓLAG swing**.
Kötelező szűrő: **`|Total_Score| > 1e-9`** (pre-reg §4.1) — a nem pontozott
sorokban a `Funda_Score` a **default 50**-en áll.

Kill/Park: (a) adekvát T_eff-en bukó családi p → KILL; (b) szignifikáns negatív
előjel → KILL; (c) elégtelen T_eff → PARK; (e) `|mean IC| < breakeven(p75)` →
`PARK_UNECONOMIC`.

⚠️ **Felbontás-korlát — itt a LEGÉLESEBB:** a `Funda_Score` napi **~5,0 distinct**
értéket vesz fel ~561 név között (azaz ~112 név per holtverseny-csoport). Ez
effektíve egy **5-kosaras ordinális** faktor. A Spearman erősen **a nulla felé**
attenuál → egy **null ezen a karon a leggyengébb bizonyíték** a háromból
(pre-reg §4.2). Pozitív lelet viszont erős.

## 🔴 Visszatartás — miért DRAFT (2026-10-04)

**A regisztrált h ∈ {1,3,5,7} rács ehhez a faktorhoz félre-specifikált.**

| | |
|---|---|
| Mért half-life | **799,8 nap** |
| Leghosszabb regisztrált horizont | h=7 |
| h=7 a half-life arányában | **0,9%** |

Egy ~800 napos half-life-ú jel 5–7 napos forward hozamon mérve **definíció
szerint** alig mutat IC-t: a jel még nem tudott megnyilvánulni. Ha így
futtatnám, **KILL-t rögzítenék egy olyan teszten, ami nem volt alkalmas a
hipotézis vizsgálatára** — és a `KILLED` státusz a jövőben lezártnak tűnne.
Ez **rosszabb, mint nem mérni.**

**A javaslat:** **h ∈ {20, 60}** hozzáadása **kizárólag a HYP-007-hez**.

**Miért nem post-hoc hangolás:** a half-life a faktor **saját
autokorrelációja** — a hozamoktól **matematikailag független**, és **minden
IC-mérés ELŐTT** mérve. A horizont-rács hozzáigazítása a faktor **mért
időskálájához** pre-regisztráció, nem az eredmény felé hangolás.

**Miért nem döntök róla magam:** a h ∈ {1,3,5,7} a **spec §5.1 szintű,
pre-regisztrált konstans** (`cfg.IC_HORIZONS`). Módosítása **governance-döntés**
(mint a `MIN_ADEQUATE_T_EFF` floor), és a Šidák-családot is növeli
(12 → 14 attempt). **Tamás-döntés.**

Addig a HYP-006 és HYP-008 **a regisztrált rácson fut** — nekik h ∈ {1,3,5,7}
**helyes** (half-life 0,4 és 2,8 nap).

## Eredmény (a batch tölti)

—

## KILL/PARK indoklás (ha releváns)

—
