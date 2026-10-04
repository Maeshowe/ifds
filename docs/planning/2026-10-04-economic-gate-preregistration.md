# PRE-REGISZTRÁCIÓ — (e) gazdasági szignifikancia-kapu az FRL PROMOTE-kritériumokhoz

**Dátum:** 2026-10-04
**Státusz:** ⏳ **JAVASLAT — Tamás döntésére vár.** Implementáció csak jóváhagyás után.
**Érinti:** `scripts/research/frl_holdout.py::promote_verdict`, FRL-spec §5.3 / §5.4
**Keret:** post-gate keret-revízió. A 2026-09-22-i kapu lezárult (`docs/decisions/2026-10-03-gate-run-outcome.md`).

---

## 0. IDŐZÍTÉSI TANÚSÍTVÁNY (ez a dokumentum legfontosabb sora)

> **Ez a szöveg a HYP-005 {h=5, h=7} PARK-olt karok ÚJRATESZTJE ELŐTT készült.**
> A megnövelt swing-mintán (2026-05-18 → 10-02, ~96 session) az újrateszt **még nem futott
> le**, és **nem is futhat le**, amíg ez a kapu el nem dőlt. Ha fordított sorrendben
> történne, a kapu **post-hoc** lenne — pontosan az, amit a házszabály tilt
> (`ifds-rules.md`: *„Értékelő-motor fix csak pre-reg szöveghez igazításként"*).
>
> **Hard constraint:** a HYP-005 újrateszt **BLOKKOLT**, amíg a (e) kritérium
> státusza (elfogadva / elutasítva / módosítva) írásban nem rögzül.

---

## 1. Miért — a rés, amit három mérés tárt fel

### 1.1 A konvergáló bizonyíték

| Mérés | Eredmény |
|---|---|
| Kapu-futás (2026-10-03) | L2 ρ = **+0,073**, CI [−0,150, +0,289], n=79 |
| SIM-1 (`ae5e668`) | a §11.20 exit-geometria javítása **≈$0** (−$8, CI [−707, +649]) |
| SIM-2 (`0429c73`) | exit-architektúra: **0/15 cella pozitív, 0/14 szignifikáns** |

A veszteség dekompozíciója (n=78, realizált −$7 657,43): slippage **−$1 958 (26%)** ·
commission −$215 (3%) · geometria ≈$0 · exit-architektúra ≈$0 ·
**reziduális = a belépők maguk ≈ −$5 500 (72%)**.

A mechanikai magyarázatok elfogytak. Ami marad: **a jel és a költségszint viszonya.**

### 1.2 A rés a motorban — kódból verifikálva

Az FRL-spec **§5.3 címe szó szerint**: *„Half-life — költség-kapu, **NEM** kill-kapu"*.
És a motor ezt pontosan így implementálja:

- `frl_ic.costed_view()` **már kiszámolja** a `gross_annual_bps`, `cost_annual_bps`,
  `net_annual_bps`, `breakeven_ic` és `survives_cost` mezőket (Grinold-közelítés:
  dollár-neutrális, faktor-súlyozott portfólió hozama ≈ `IC × σ_cs` horizontonként).
- `frl_report.py:177` **ki is írja** őket a riportba.
- **De `frl_holdout.py:141` `promote_verdict(era_summaries, expected_sign, bh_pass)`
  egyáltalán NEM kap költség-inputot.**

**Következmény: egy faktor PROMOTE-olhat statisztikailag, miközben gazdaságilag
veszteséges.** A §5.4 (a)–(d) kritériumok mind statisztikaiak (BH-FDR, éra-bar,
előjel-egyezés, swing-előjel-minimum). Egyik sem kérdezi meg, hogy a jel **kifizeti-e
a saját kereskedését**.

### 1.3 Miért éppen most releváns

A HYP-005 (`sj_live_aggregate`) **maga az élő S_j score** mint keresztmetszeti faktor.
A 2026-07-25-i batch verdiktje (Tamás-megerősítve):

| Kar | T_eff | mean IC | éra-bar | Verdikt |
|---|---:|---:|---:|---|
| h=1 | 23,0 | +0,0079 | 0,0311 | **KILL** (adekvát erő, valódi null) |
| h=3 | 7,7 | — | — | **KILL** (adekvát erő) |
| h=5 | 4,6 | — | — | **PARK_UNTIL_SWING_POWER** (jó előjel, alulfeszített) |
| h=7 | 3,3 | — | — | **PARK_UNTIL_SWING_POWER** |

Az újrateszt-család **{h5, h7}, m=2** írásban rögzítve **2026-07-24-én** (lásd
`ifds-rules.md`). A swing-minta akkor 23 nap volt; **most ~96** → a T_eff a 6-os
adekvácia-floor fölé kerül, tehát **az újrateszt esedékes és most már feszített**.

Ha az újrateszt a jelenlegi (a)–(d) kritériumokkal fut le, és a h=5 kar átmegy, a
motor **PROMOTE-ot adna egy olyan jelre, amiről a kapu-futás már megmérte, hogy a
pontbecslése a breakeven IC felénél van.** Ezt a rést kell **előre** zárni.

---

## 2. Amit ez a módosítás NEM változtat (és nem is változtathat)

A házszabály szerint egy értékelő-motor módosítása **kizárólag** előre rögzített
kritériumhoz igazításként legitim, és **soha nem lazíthat**. Ezért tételesen:

| Már pre-regisztrált tétel | Státusz |
|---|---|
| BH-FDR q = 0,10 a teljes ledger-történeten (§5.4) | **VÁLTOZATLAN** |
| Éra-kvalifikált bar: `max(0,02; 2×SE(mean IC))` (§5.2) | **VÁLTOZATLAN** |
| `MIN_ADEQUATE_T_EFF = 6,0` (§5.5, `079e4a1`) | **VÁLTOZATLAN** |
| KILL (a) / sign-contradiction (b) / PARK (c) gate-logika | **VÁLTOZATLAN** |
| Legacy-only PROMOTE tilalma + swing-előjel-minimum (§5.4 d) | **VÁLTOZATLAN** |
| HYP-005 újrateszt-család {h5, h7}, m=2 (2026-07-24) | **VÁLTOZATLAN** |
| Šidák-korrigált családi minimum-p (§5.4) | **VÁLTOZATLAN** |
| Holdout-politika: 4 hét rolling, 5 nap purge (§7) | **VÁLTOZATLAN** |
| Éra-bontás kötelező (G5) | **VÁLTOZATLAN** |

**Ez a módosítás egy kaput ADD HOZZÁ. Egyet sem lazít, egyet sem távolít el.**
Egyetlen korábbi verdikt sem változik visszamenőleg (lásd §6.3).

---

## 3. A (e) KRITÉRIUM — a kapu szövege

### 3.1 A szabály

> **(e) Gazdasági szignifikancia.** PROMOTE-hoz a faktornak a hivatkozott érán
> teljesítenie kell:
>
> ```
> |mean_IC_éra|  ≥  breakeven_ic( cost_bps_per_side = p75 )
> ```
>
> ahol a `breakeven_ic` a `frl_ic.costed_view()` már implementált képlete:
>
> ```
> breakeven_ic = cost_annual_bps / (σ_cs × (252/h) × 10 000)
> ```
>
> A `cost_annual_bps` a `research/cost_model.json`-ból, **`era=swing`** szűrővel.

### 3.2 Miért a p75 és nem a medián — a kalibráció független forrásból

A házszabály megköveteli, hogy a küszöb **a mért adattól független forrásból** legyen
kalibrálva, és egy tartományon belül **verdikt-stabil** legyen.

- A költség-input **konstrukció szerint független** az IC-méréstől: a
  `slippage_per_ticker` **belépési fill vs. tervezett ár** sorozatból jön, nem a
  hozam-vs-score kapcsolatból. A két mérés nem oszt közös szabadsági fokot.
- A **p75 választása a slippage-eloszlás saját alakjából** jön, nem egy általam
  választott biztonsági szorzóból:

| Cost-modell verzió | medián bp/oldal | p75 | p75/medián |
|---|---:|---:|---:|
| 2026-07-20 (első) | 95,5 | 137,0 | 1,43 |
| 2026-07-24 | 97,0 | 137,0 | 1,41 |
| **2026-09-22 (aktuális, n=82)** | **83,5** | **136,0** | **1,63** |

A p75-ön mérni tehát ekvivalens egy **~40–60%-os marzs-követeléssel**, amit **az
eloszlás diszperziója határoz meg**, nem én. Ez egyben a §3.3 stabilitási
követelményt is kielégíti: a p75 **a konzervatív végpont**, tehát a verdikt
definíció szerint nem fordulhat meg szigorúbb költség felé.

### 3.3 Verdikt-stabilitás — kötelező riportálás

A riport **mindkét** küszöböt kiírja (medián és p75 breakeven IC). Döntési szabály:

| Helyzet | Verdikt |
|---|---|
| `\|IC\| ≥ breakeven(p75)` | (e) **teljesül** |
| `breakeven(medián) ≤ \|IC\| < breakeven(p75)` | **INCONCLUSIVE_ON_COST** — nem PROMOTE |
| `\|IC\| < breakeven(medián)` | (e) **bukik** |

A középső sáv explicit „nem tudjuk" — **nem** kerekítjük PROMOTE-ra.

### 3.4 Amit a (e) NEM tesz

- **Nem KILL.** Lásd §4.
- **Nem helyettesíti** az (a)–(d) statisztikai kritériumokat. Mind az öt kell.
- **Nem a `half_life` / `implied_turnover_cost_bps` mezőre épül** — az §5.3 szerint
  továbbra is diagnosztika, nem kapu. A (e) a `costed_view` net/breakeven ágára épül.

---

## 4. A bukás KÖVETKEZMÉNYE — új verdikt: `PARK_UNECONOMIC`

**Egy valódi jelet nem szabad megölni azért, mert a MI végrehajtásunk drága.**

Ha a faktor (a)–(d)-t teljesíti, de (e)-t nem:

```
PARK_UNECONOMIC
```

Jelentése: *a jel keresztmetszetileg kimutatható, de ezzel a végrehajtási stílussal
(next-day MKT open, 83,5 bp/oldal medián, 71% adverz fill) nem kiaknázható.*

**A gyógymód a végrehajtás, nem a faktor eldobása.** Ezért a `PARK_UNECONOMIC`
automatikus újrateszt-triggert kap, amit **a cost-modell javulása** indít (ahogy a
`PARK_UNTIL_SWING_POWER`-t a T_eff növekedése). Konkrét kapcsolódás: a
**belépési-végrehajtás ellenpróba** (SIM-EXEC, `docs/tasks/2026-10-04-entry-execution-counterfactual.md`)
méri, mennyit nyerne egy LMT / nyitó-aukciós stílus — és ez a mérés **ugyanaz az input**,
ami a `PARK_UNECONOMIC` újratesztjét kiváltaná.

Ez a `PARK_UNECONOMIC` a **helyes** olvasat a jelenlegi bizonyítékra is: a kapu
ρ = +0,073-a a breakeven (0,15–0,18) **alatt** van, de a nullától sem különböztethető
meg — ez nem „nincs jel", hanem **„nem kifizetődő ezen a költségszinten"**.

---

## 5. A HYP-005 ÚJRATESZT — előre rögzített kimenet-mátrix

A család **{h5, h7}, m=2** (2026-07-24, változatlan). A riportnak **mind a négy**
alábbi lehetőséget előre nevén kell nevezni, hogy az eredmény ne legyen értelmezhető
többféleképpen:

| # | Kimenet | Olvasat | Következő lépés |
|---|---|---|---|
| **1** | (a)–(d) bukik **adekvát T_eff-en** (≥6) | Az S_j score-családnak **nincs** keresztmetszeti edge-e. A h=1/h=3 KILL már ezt mutatta. | **Nincs élesítés.** A választás: új jelcsalád vagy leállás. |
| **2** | (a)–(d) átmegy, **(e) bukik** | A jel valós, de **ezzel a végrehajtással nem kiaknázható**. | `PARK_UNECONOMIC`. A kritikus út a **végrehajtás** (SIM-EXEC → 4. pont). Élesítés csak ÚJ élő pre-reggel, javított végrehajtással. |
| **3** | (a)–(d) átmegy, **(e) INCONCLUSIVE_ON_COST** | A jel a medián- és p75-küszöb között van. | Nem PROMOTE. Költség-oldali javítás + újrateszt. |
| **4** | Minden átmegy | Jelölt egy **új, pre-regisztrált élő periódusra**. | Új élő pre-reg (minta, kapu-dátum, küszöbök) — a 2026-07-25-i protokoll **nem** újrahasznosítható. |
| **5** | Ismét PARK alulfeszítettségre | Nincs döntés. | Adatgyűjtés folytatódik, újrateszt a T_eff növekedésével. |

### 5.1 Amit az újrateszt NEM dönt el

A HYP-005 **egyetlen faktor-család** (az aggregált S_j). Egy KILL **nem** jelenti, hogy
az S_j **komponensei** (momentum, flow, GEX, fundamentals) külön-külön is halottak —
az aggregálás elrejthet egymást kioltó részjeleket. A komponens-szintű dekompozíció
**külön hipotézis**, külön pre-reggel és a Šidák-családba beszámítva.

---

## 6. Governance

### 6.1 Mi minősül e pre-reg megsértésének

1. A HYP-005 újrateszt lefuttatása **mielőtt** a (e) státusza írásban rögzül.
2. A p75 → medián (vagy bármilyen lazább) küszöb-csere **az eredmény látása után**.
3. Az `INCONCLUSIVE_ON_COST` sáv PROMOTE-ként kezelése.
4. A `PARK_UNECONOMIC` KILL-ként kezelése (vagy fordítva).
5. A §2 táblázat bármely „VÁLTOZATLAN" tételének módosítása ebben a körben.

### 6.2 Kötelező kísérők az implementációhoz

A házszabály (`ifds-rules.md`) szerint minden értékelő-motor-fixhez kell:

1. **Pre-reg forrás megnevezése** a commit-üzenetben és a kódkommentben →
   *ez a dokumentum, §3.1*.
2. **Érzékenységi ellenőrzés**: a §3.3 mátrix **maga** az érzékenységi szabály
   (medián vs p75 sáv), és a kalibráció független forrásból (§3.2).
3. **Regressziós teszt, ami egy KORÁBBI, megerősített verdiktet őriz**: a
   **HYP-004 KILL** és a **HYP-005 h=1/h=3 KILL** változatlanságát teszt védi.
4. **Nincs újrafuttatás verdikt-generálásért**: a meglévő 8 ledger-sor a régi
   verdikten marad; a (e) **csak a jövőbeli attemptekre** él.

### 6.3 Visszamenőleges hatás: NINCS

A (e) kapu **nem** értékeli újra a lezárt attempteket. A HYP-004 (4 KILL) és a
HYP-005 h=1/h=3 (2 KILL) **változatlan**. A HYP-005 h=5/h=7 **PARK** marad, amíg az
újrateszt le nem fut — és az újrateszt **már (e)-vel** fut.

---

## 7. Mit kérek Tamástól

| Döntés | Opciók |
|---|---|
| **D-E1** | (e) kritérium **elfogadva** / elutasítva / módosítva |
| **D-E2** | Küszöb: **p75** (javasolt) / medián / más, írásban indokolva |
| **D-E3** | `PARK_UNECONOMIC` mint új verdikt-érték: **elfogadva** / nem |
| **D-E4** | A HYP-005 újrateszt blokkolása a D-E1 döntésig: **megerősítve** / nem |

A jóváhagyásig **nem nyúlok** a `promote_verdict`-hez és **nem futtatom** az
újratesztet. A 4. pont (belépési-végrehajtás ellenpróba) ettől **független** és
párhuzamosan fut — az nem értékelő-motor, hanem leíró mérés.
