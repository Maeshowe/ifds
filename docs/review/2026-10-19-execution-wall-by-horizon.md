# A fal horizont × végrehajtás szerint — és miért a végrehajtás az első lépés

**Dátum:** 2026-10-19
**Előzmény:** `docs/review/2026-10-19-cost-estimator-implementation.md` (a becslő cseréje)
**Cél:** a 3-as pont (új jelcsalád) **tervezési premisszáinak** megmérése, mielőtt
bármilyen pre-reg születik.

---

## 0. Adat-egészség (a 2026-10-04-i szabály szerint, nem feltételezve)

`research/cache/returns.parquet` — épült **2026-10-04 10:48**, panel **2026-02-11 … 10-02**,
2 301 048 sor. Horizontonkénti utolsó nem-NaN dátum, ami a frissesség valódi mérője:

| | h=1 | h=3 | h=5 | h=7 | h=10 | h=20 | h=60 |
|---|---|---|---|---|---|---|---|
| utolsó adat | 10-01 | 09-29 | 09-25 | 09-23 | 09-18 | 09-03 | 07-09 |

Mindegyik pontosan `10-02 − h` session — **nincs elavulás**. A σ_cs a **pontozott
univerzumon** mérve (napi 226–1824 név, átlag 986), nem a teljes piacon: a h=5-es
**0,0593** egyezik a pre-regben használt 0,06-tal, tehát a rács konzisztens a motorral.

---

## 1. A rács

Három végrehajtási forgatókönyv. Mindhárom szám **mért**, nem feltételezett:

| | belépés | kilépés | round trip (pont / kötő) |
|---|---|---|---|
| **A — ma** | 09:31 market, +40,3 / +52,2 bp | vegyes, +23,2 / +32,5 bp | **63,5 / 84,7 bp** |
| **B — MOO belépő** | nyitó aukció, **+1,35 / +3,93 bp** | változatlan | **24,6 / 36,5 bp** |
| **C — minden aukciós** | nyitó aukció | záró aukció (MOC) | **2,7 / 7,9 bp** |

> Az aukció **nem ingyen van: +1,35 bp (pont) / +3,93 bp (kötő)** — ezt a 68 MOC-kilépés
> közvetlenül megmérte. A csengő utáni market ugyanezen a mintán **+60,4 / +80,1 bp**.
> Vagyis az aukció és a csengő utáni market között **45×** a különbség.

**Breakeven |IC| = round_trip / (σ_cs(h) · 10⁴)**, a kötő (felső korlát) ágon:

| h | σ_cs | napok | T_eff | erő | **A — ma** | **B — MOO** | **C — aukciós** |
|---:|---:|---:|---:|:---:|---:|---:|---:|
| 1 | 0,0260 | 85 | 85,0 | OK | 0,3264 | 0,1405 | 0,0303 |
| 3 | 0,0457 | 83 | 27,7 | OK | 0,1852 | 0,0797 | 0,0172 |
| **5** | 0,0593 | 81 | 16,2 | OK | **0,1428** | **0,0615** | **0,0132** |
| **7** | 0,0697 | 79 | 11,3 | OK | **0,1216** | **0,0523** | **0,0113** |
| **10** | 0,0831 | 76 | 7,6 | OK | **0,1019** | **0,0439** | **0,0095** |
| 20 | 0,1152 | 66 | 3,3 | ⛔ gated | 0,0736 | 0,0317 | 0,0068 |
| 60 | 0,2060 | 31 | 0,5 | ⛔ gated | 0,0411 | 0,0177 | 0,0038 |

A `T_eff = napok / h`; a `MIN_ADEQUATE_T_EFF = 6,0` alatt a kar **erő-kapuzott** (spec §5.5),
tehát ma **h ≤ 10** tesztelhető. A h=20 ~2027 tavaszán, a h=60 ~2028-ban nyílik.

**Viszonyítás:** a publikált, erős keresztmetszeti részvény-faktorok IC-je **0,02–0,05**.

---

## 2. Amit ez kimond

### 2.1 🔴 A mai végrehajtással a keresés aritmetikailag reménytelen

Minden **statisztikailag tesztelhető** horizonton (h ≤ 10) az A-fal **0,102–0,326**.
Ez a documentált legjobb faktorok **2–16-szorosa**. Nem arról van szó, hogy nehéz
jelet találni — arról, hogy **olyan jelet kellene találni, amilyen a szakirodalomban
nem létezik**. Egy új jelcsalád pre-regje a mai végrehajtás ellen egy eleve halott
keresés formalizálása lenne.

### 2.2 A B forgatókönyv ingyen van, és egyedül is nagyságrendet mozdít

A MOO belépő **nem stratégia-változás**: a döntés már megvan az előző záróból, a
mai 15:31-es cron egy perccel a csengő UTÁN adja be. Aukcióba adni **ugyanazt a
döntést hajtja végre korábban, jobb áron** — nem veszít információt, nem változtat
a tartási perióduson, nincs trade-off. A fal h=5-en **0,1428 → 0,0615** (2,3×),
h=10-en **0,1019 → 0,0439**.

### 2.3 A C forgatókönyv a nagy nyereség — de NEM ingyen, és még nincs megmérve

A fal h=5-en **0,0132**, a mai A-hoz képest **10,8×**. És a kilépési oldal
**már most 63%-ban aukciós** (68 MOC a 108 lábból); a teljes kilépési költséget
a 40 csengő utáni láb (TP1/TP2/stopok) adja.

> ⚠️ **De a stopot MOC-ra tenni stratégia-változás, nem plumbing.** Ha egy stop
> nem tüzelhet intradayben, hanem záróig tart, az **rosszabb kilépési árat** jelent
> — ez valódi gazdasági költség, amit ez a tábla **nem** tartalmaz (a tábla súrlódás,
> nem elmaradt haszon). A C-t **csak ellenpróba után** szabad nettó nyereségnek
> nevezni (SIM-2 típusú futás a 108 lábon). Addig a C a **felső korlát**, nem terv.

---

## 3. A következtetés sorrendje

| | lépés | státusz |
|---|---|---|
| **1** | **MOO belépő** (D-C4) — a keresés előfeltétele, nem optimalizáció | jóváhagyott fix-listán, **nincs implementálva** |
| **2** | **MOC-kilépés ellenpróba** — a C forgatókönyv nettó hatása a 108 lábon | nincs megmérve |
| **3** | **Új jelcsalád pre-reg**, h ∈ {5, 7, 10}, a **B-fal** (0,0615 / 0,0523 / 0,0439) ellen | a B-fal a konzervatív premissza; a C csak bónusz |

**Amiért a sorrend nem felcserélhető:** a falat nem szabad a keresés UTÁN javítani —
az pontosan az a mozdulat, amit a házszabály tilt (a kapu lazítása az eredmény
ismeretében). Ha a végrehajtás javul, azt **a jelcsalád pre-regje ELŐTT** kell
rögzíteni, hogy a küszöb a futás előtt álljon.

**Amit ez nem mond:** hogy a B-fal mellett a keresés sikerülni fog. A h=10-es 0,0439
a publikált sáv **felső szélén** van, és az alapráta egy egyszemélyes operátornak
publikus vendor-adatból továbbra is alacsony. Csak annyit mond, hogy a B-fal mellett
a keresés **nem eleve lehetetlen**, a mai A-fal mellett pedig az.
