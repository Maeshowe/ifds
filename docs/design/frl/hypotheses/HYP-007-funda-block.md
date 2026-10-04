Status: TESTED
Updated: 2026-10-04
Data-lane: v1
Attempt-family: A-0019..A-0023 (AMENDMENT-1 elfogadva 2026-10-04; fut h ∈ {1,3,5,7,10}, erő-kapuzva h ∈ {20,60})

# HYP-007 — Fundamentals blokk keresztmetszeti IC (az S_j 0,10 súlyú komponense)

> ✅ **AMENDMENT-1 ELFOGADVA (Tamás, 2026-10-04).** A horizont-halmaz
> **h ∈ {1,3,5,7} ∪ {10,20,60}**, **kizárólag ehhez a hipotézishez** (a motor
> gépileg kikényszeríti: `cfg.LONG_HORIZONS_BY_HYPOTHESIS`). A `DRAFT` feloldva.
> Részletek: `docs/planning/2026-10-04-component-decomposition-preregistration.md`
> AMENDMENT-1.

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

**A javaslat (ELFOGADVA, Tamás 2026-10-04):** **h ∈ {20, 60}** hozzáadása
**kizárólag a HYP-007-hez**.

🔴 **Implementációs kiterjesztés — NEM a jóváhagyott javaslat része:** a
regisztrált halmazba **h=10 is bekerült**, mert a T_eff-floor (6,0) mellett a 62
dev-napon ez a leghosszabb ma mérhető horizont — a javaslat két horizontja
(20, 60) erő-kapuzva **nem futott**. CC adta hozzá és ugyanabban a fordulóban
futtatta is; **Tamásnak nem volt alkalma külön jóváhagyni.** A h=10 KILL-t
(A-0023) Tamás a 2026-10-04-i batch-confirmmal megerősítette. A verdikt h=10
nélkül **azonos** (Šidák m=4 → 0,99705, m=5 → 0,99931; mindkettő BH-fail), és a
kiterjesztés iránya **konzervatív** (nagyobb m = magasabb küszöb). Részletek:
pre-reg AMENDMENT-1 §A-1.2 provenienciai helyesbítés.

**Miért nem post-hoc hangolás:** a half-life a faktor **saját
autokorrelációja** — a hozamoktól **matematikailag független**, és **minden
IC-mérés ELŐTT** mérve. A horizont-rács hozzáigazítása a faktor **mért
időskálájához** pre-regisztráció, nem az eredmény felé hangolás.

**Governance:** a h ∈ {1,3,5,7} a spec §5.1 szintű pre-regisztrált konstans.
Az amendment **nem** módosítja a `cfg.IC_HORIZONS` alapértelmezést — egy
**hipotézis-szintű** bővítést vezet be (`LONG_HORIZONS_BY_HYPOTHESIS`), így a
HYP-006/HYP-008 halmaza és verdiktje **érintetlen**.

🔴 **MÉRHETŐSÉGI KAPU (a meglévő erő-szabály, a futás ELŐTT mérve):**
`T_eff = n_nap / h`, floor 6,0. A 2026-10-02-i dev-ablakon (62 swing nap):

| h | T_eff | futtatható? |
|---:|---:|---|
| 1 / 3 / 5 / 7 | 62,0 / 20,7 / 12,4 / 8,9 | ✅ |
| **10** | **6,20** | ✅ a leghosszabb ma mérhető |
| **20** | **3,10** | ❌ 120 dev-nap kell (58 hiányzik, ≈ +12 hét) |
| **60** | **0,52** | ❌ 360 dev-nap kell (298 hiányzik, ≈ +60 hét) |

→ **Most fut: h ∈ {1,3,5,7,10}.** A h=20 és h=60 **regisztrált, de nem futtatott**
— nem nyílik rájuk attempt, nincs BH-infláció; az auto-retest indítja, ahogy a
minta nő.

⚠️ **Attenuációs olvasat (a §4.2 kiterjesztése a horizont-tengelyre):** h ≪ t½
mellett az IC **attenuálódik**, ezért egy **null a rövid horizontokon gyenge**
bizonyíték, egy **pozitív erős**. Horizont-adekvácia **kaput megfontoltam és
elvetettem** (AMENDMENT-1 §A-1.4): a valódi faktorkutatás rutinszerűen tesztel
lassú faktorokat h ≪ t½-n és talál jelet — egy ilyen kapu legitim kutatást
blokkolna.

## Eredmény (2026-10-04, A-0019..A-0023)

Dev swing **62 nap** (05-18..08-28), legacy üres, holdout-érintés **0**.
Futás: `--hyp HYP-007 --horizons 1,3,5,7,10` (az erő-kapun átment horizontok).

| h | T_eff | mean IC | éra-bar | p | h / t½ | verdikt |
|---|---:|---:|---:|---:|---:|---|
| 1 | 62,0 | +0,0015 | 0,0215 | 0,887 | 0,001 | KILL (A-0019) |
| 3 | 20,7 | −0,0045 | 0,0301 | 0,767 | 0,004 | KILL (A-0020) |
| 5 | 12,4 | −0,0021 | 0,0408 | 0,921 | 0,006 | KILL (A-0021) |
| 7 | 8,9 | +0,0047 | 0,0457 | 0,842 | 0,009 | KILL (A-0022) |
| **10** | **6,2** | **+0,0034** | 0,0545 | 0,905 | 0,013 | KILL (A-0023) |

Šidák-családi p (m=5, swing): **0,9993** → BH q=0,10 **fail**. Ez a három blokk
közül a **leglaposabb** eredmény.

**A h-görbe NEM emelkedik.** Egy lassú faktornál, aminek a jele attenuálva is
jelen van, az IC-nek **nőnie** kellene a horizonttal (ez a §A-1.4 attenuációs
olvasat tesztelhető következménye). A mért sorozat
(+0,0015 / −0,0045 / −0,0021 / +0,0047 / +0,0034) **előjelet is vált**, és
nagyságrendben a bar tizede–huszada marad. **Nincs kibontakozó jel.**

⚠️ **A h ∈ {20, 60} NEM futott** — erő-kapuzva (T_eff 3,10 és 0,52 a 6,0-os floor
alatt), attempt nem nyílt rájuk, BH-inflációt nem okoztak. Auto-retestre várnak.
Az attenuációs olvasat szerint tehát a null **gyenge** bizonyíték marad azon a
tartományon, ahol a faktor időskálája ténylegesen él.

✅ **MEGERŐSÍTVE (Tamás, 2026-10-04)** — mind az 5 attempt, `human_confirmed: true`.
Riport: `docs/review/2026-10-04-component-decomposition.md`

## KILL/PARK indoklás (ha releváns)

—
