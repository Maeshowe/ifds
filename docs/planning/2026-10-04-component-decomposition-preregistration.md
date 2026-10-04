# PRE-REGISZTRÁCIÓ — az S_j score komponens-dekompozíciója (HYP-006 / 007 / 008)

**Dátum:** 2026-10-04
**Státusz:** 📋 **REGISZTRÁLVA, NEM FUTTATVA.** A mérés külön indítás.
**Keret:** post-gate keret-revízió, „A" opció (`docs/review/2026-10-04-sim-exec-entry-execution.md` nyomán)
**Előzmény:** `docs/planning/2026-10-04-economic-gate-preregistration.md` (a (e) kapu, elfogadva)

---

## 0. IDŐZÍTÉSI TANÚSÍTVÁNY

> **Ez a dokumentum a HYP-005 {h=5, h=7} újrateszt ELŐTT készült.**
> Ha az aggregát bukását **látva** válogatnám össze a komponenseket, az
> garden-of-forking-paths lenne — a komponens-halmaz utólagos igazítása a
> kimenethez. A sorrend ezért nem kényelmi kérdés.
>
> A §3 komponens-halmaz, a §5 előjel-várakozások és a §6 döntési szabályok
> **mind a mérés előtt** rögzültek. Post-hoc komponens-bővítés **TILOS**.

---

## 1. A hipotézis

Az S_j egy **súlyozott kompozit**. A HYP-005 aggregát-teszt h=1-en
`mean_ic = +0,0079`-et adott **adekvát erővel** (T_eff=23) — tiszta null.

**De egy aggregát-null két dolgot jelenthet:**

- **(i)** egyik komponensnek sincs keresztmetszeti jele, **vagy**
- **(ii)** van jel, de a komponensek **kioltják egymást** (ellentétes előjelű
  részjelek egy fix súlyozásban).

Az aggregát-teszt a kettőt **szerkezetileg nem tudja szétválasztani.** Ez a
dekompozíció választja szét.

**Miért nem kettős mintavétel:** ugyanaz az adat, de **más hipotézis** — a
kioltás-hipotézis nem következik és nem is cáfolható az aggregát-mérésből. A
többszörös tesztelés árát a ledger BH-FDR deflációja fizeti ki (§7), nem egy
érvelés.

---

## 2. A score pontos szerkezete (kódból, `phase4_stocks.py:1103`)

```
combined = ( 0,60 · clip(50 + flow.rvol_score, 0, 100)
           + 0,10 · (50 + funda_score)
           + 0,30 · (rsi_score + sma50_bonus + rs_spy_score)
           + sector_adj
           ) · insider_multiplier
```

> ⚠️ **A kódban lévő docstring elavult** (`0.40 · Flow + 0.30 · Funda + 0.30 · Tech`),
> a `defaults.py` szerint a valódi súlyozás **0,60 / 0,10 / 0,30** (BC23 óta:
> *„flow-first … funda reduced — no P&L correlation"*). A docstring javítása az
> operatív backlogba kerül; **a mérés a config szerinti súlyokkal érvényes**.

### 2.1 A `flow.rvol_score` maga is 7-tagú összeg

A mező **neve** `rvol_score`, de a tartalma:

```
rvol_score + squat_bonus + pcr_score + otm_score
           + block_trade_score + dp_pct_score + buy_pressure_score
```

Vagyis **a kioltás-probléma egy második szinten is fennáll**, épp a legnagyobb
súlyú (0,60) blokkon belül.

### 2.2 Adat-proveniencia és a UW-korlát

| Al-score | Blokk | Forrás | Előre is kutatható? |
|---|---|---|---|
| `rvol_score` (igazi RVOL) | flow | Polygon bars | ✅ |
| `squat_bonus` | flow | Polygon (volumen + spread) | ✅ |
| `buy_pressure_score` | flow | Polygon (OHLC + VWAP) | ✅ |
| `dp_pct_score` | flow | **UW** dark pool | ❌ csak történetileg |
| `pcr_score` | flow | **UW** options | ❌ |
| `otm_score` | flow | **UW** options | ❌ |
| `block_trade_score` | flow | **UW** | ❌ |
| `funda_score` | funda | FMP | ✅ |
| `insider_multiplier` | (multiplikatív) | FMP / SEC | ✅ |
| `rsi_score`, `sma50_bonus`, `rs_spy_score` | tech | Polygon | ✅ |
| `sector_adj` | (additív) | Phase 3 / Polygon | ✅ |

**A UW kivezetésével a flow-blokk 7 al-score-ából 4 a jövőben nem táplálható**
(`docs/decisions/2026-08-18-uw-decommission.md`). Ez **gyakorlati korlát a
hasznosíthatóságon**, nem a mérésen: ha a flow-jel kizárólag a UW-tagokból jönne,
az **nem lenne implementálható** — ezt a §6.4 külön kezeli.

---

## 3. A KOMPONENS-HALMAZ — a mérés ELŐTT rögzítve

**Csak az számolható, ami a teljes keresztmetszetben létezik.** A
`output/full_scan_matrix_*.csv` a **blokk-szintű** score-okat hordozza
(`Flow_Score`, `Funda_Score`, `Tech_Score`) — az al-score-okat **nem**.

Ezért a regisztrált halmaz **pontosan három** faktor:

| Hipotézis | Faktor | Oszlop | Súly az S_j-ben |
|---|---|---|---|
| **HYP-006** | Flow blokk | `Flow_Score` | **0,60** |
| **HYP-007** | Fundamentals blokk | `Funda_Score` | 0,10 |
| **HYP-008** | Technical blokk | `Tech_Score` | 0,30 |

Horizontok: **h ∈ {1, 3, 5, 7}** (a spec §5.1 szerint), a **h=5 az elsődleges**.
A spec §5.4 szerint egy hipotézis h-variánsai **EGY attempt-családot** alkotnak,
Šidák-korrigált családi minimum-p-vel → **3 család, 12 attempt**.

### 3.1 Amit NEM regisztrálok most, és miért

- **Al-score-szintű dekompozíció** (a 7 flow-tag külön): a teljes
  keresztmetszetben **nincs meg** az adat. A `state/phase4_snapshots/` csak a
  *passed* tickereket tartja (~90/nap a ~561 helyett), a `state/uw_shadow/` pedig
  csak a UW-mezőket. Ez **szűkebb univerzum és más minta** → **külön pre-reg
  kell hozzá**, és csak akkor érdemes, ha a HYP-006 jelet mutat.
- **`insider_multiplier` és `sector_adj`**: nem additív blokkok (multiplikatív /
  Phase-3-eredetű), a scan matrix nem tartja őket külön. Nem regisztráltak.
- **Súly-újraoptimalizálás**: ez **nem** faktor-teszt, hanem illesztés ugyanazon
  az adaton. Kifejezetten kizárva.

---

## 4. ADAT-EGÉSZSÉG — a mérés előtti kötelező szűrő

A házszabály (*„X feature nem prediktív" verdikt elé adat-egészség check*) szerint
a mezők eloszlását **a verdikt előtt** ellenőriztem. Eredmény (86 swing-éra nap,
84 832 (ticker, nap) sor):

| Csoport | Flow_Score | Funda_Score | Tech_Score |
|---|---|---|---|
| `Total_Score ≠ 0` (n=48 275) | 10–100, **18** distinct | 40–60, **5** distinct | 0–75, **6** distinct |
| `Total_Score = 0` (n=36 557) | **~100% pontosan 50** | **~100% pontosan 50** | 0–75, valódi |

### 4.1 🔴 KÖTELEZŐ SZŰRŐ: `Total_Score ≠ 0`

A **nem pontozott sorokban a `Flow_Score` és a `Funda_Score` a default 50-en áll**
(nincs rájuk adjustment alkalmazva). Ha bekerülnének, **43%-os konstans masszát**
injektálnának a napi rangsorba — a `dp_pct` strukturális-nulla hibaosztály pontos
megfelelője, csak fordítva: nem nulla, hanem **default**.

→ A faktor-számítás **kizárólag** a `Total_Score ≠ 0` sorokon fut (ez egyben a FRL
meglévő `score == 0 → NaN` szabálya). Így **~561 név/nap × 86 nap**.

→ **Guard-teszt kötelező**: a szűrő nélküli futás a `Flow_Score` napi módusz-arányát
40% felett mutatja; a teszt ezt a szűrt adaton 20% alatt követeli meg.

### 4.2 ⚠️ A FELBONTÁS KORLÁTJA — előre kimondva

A blokk-score-ok **durván kvantáltak** (5, 6 és 18 distinct érték ~561 név között).
Ez **nem degeneráció** (a mezők nem konstansok, a tolerancia-szabály teljesül), de
a Spearman-t **lefelé attenuálja**: a holtverseny-csoportok a rangsort elmossák.

**Következmény, előre rögzítve:** egy **null** a `Funda_Score` (5 szint) és a
`Tech_Score` (6 szint) karokon **gyenge bizonyíték** — alacsony felbontás ≠ nincs
jel. Egy **pozitív** lelet viszont erős (az attenuáció a nulla felé hat, nem el
tőle).

**NEM vezetek be új gépi küszöböt erre.** Nem tudom független forrásból
kalibrálni, és a házszabály szerint egy nem-kalibrálható döntési konstans tiltott.
Helyette:

1. **Kötelező diagnosztika a riportban**: faktor-éránként a napi **distinct
   érték-szám átlaga** és a **legnagyobb holtverseny-csoport átlagos aránya**.
2. A meglévő `era_bar = max(0,02; 2×SE(mean IC))` **részben automatikusan
   korrigál**: a sok holtverseny zajosabb napi IC-t ad → nagyobb `std_ic` →
   nagyobb SE → magasabb bar. Az attenuációt viszont **nem** korrigálja.
3. Ha egy KILL olyan karon születik, ahol az átlagos distinct érték-szám **< 8**,
   a riport ezt `low_resolution` jelzéssel írja ki, és a terminális KILL
   **Tamás megerősítését** kívánja (mint a HYP-004/005 esetében).

---

## 5. MECHANIZMUSOK ÉS ELŐJEL-VÁRAKOZÁSOK (spec §8.1 template)

### HYP-006 — Flow blokk (`Flow_Score`), súly 0,60

- **Mechanizmus (miért létezne):** szokatlan volumen szűk spreaddel = intézményi
  akkumuláció a mozgás előtt; a VWAP-hoz mért záróár és a bar-on belüli pozíció
  a napon belüli vételi nyomást proxyzza. A vesztes oldal a **passzív/retail
  flow**, ami anélkül kereskedik, hogy az akkumulációt látná.
- **Várt előjel:** **+**
- **Várt horizont:** **rövid** — a volumen-jelek gyorsan bomlanak, tehát
  h=1/h=3 **erősebb**, mint h=5/h=7. (Ha a h-görbe ennek a fordítottja, az a
  mechanizmus ellen szól, nem mellette.)
- **Költségprofil:** magas forgás (napi volumen-jel) → a (e) kapu itt a
  legszigorúbb. Ez a faktor **akkor** érdekes, ha a jel a költséget is kifizeti.
- **Kill-kritérium:** a §6 szerint.

### HYP-007 — Fundamentals blokk (`Funda_Score`), súly 0,10

- **Mechanizmus:** minőség/érték prémium; a vesztes oldal a rossz fundamentumokat
  túl-extrapoláló befektető.
- **Várt előjel:** **+**
- **Várt horizont:** **hosszú** — h=7 ≥ h=5 > h=3 > h=1.
- **⚠️ Ismert prior, kimondva:** a BC23 épp azért vitte le a súlyát 0,30 → 0,10,
  mert *„no P&L correlation"*. Ez tehát **részben egy ismert null újratesztje**
  — ezt előre rögzítem, hogy utólag ne „megerősítésként" olvassuk. A felbontás
  itt a legrosszabb (5 szint), tehát a §4.2 aszimmetria ezen a karon a legélesebb.
- **Költségprofil:** alacsony forgás (lassú faktor) → a (e) kapu itt a leglazább.

### HYP-008 — Technical blokk (`Tech_Score`), súly 0,30

- **Mechanizmus:** keresztmetszeti momentum / trend-perzisztencia (RSI + SMA50 +
  relatív erő SPY ellen) — a szakirodalom legtöbbször replikált anomáliája. A
  vesztes oldal a **disposition-effect** szerint túl korán eladó befektető.
- **Várt előjel:** **+**
- **Várt horizont:** **h=5–7** a természetes (a momentum több napon akkumulál).
- **Költségprofil:** közepes forgás.
- 📌 **Ez a legerősebb a priori jelölt**: a három közül ennek van független,
  szakirodalmi támasza. Ha ez is tiszta null adekvát erővel, az **erős** jelzés
  a teljes jelcsalád ellen.

---

## 6. DÖNTÉSI SZABÁLYOK

### 6.1 A motor változatlan

A verdiktet a **meglévő, pre-regisztrált** `promote_verdict` adja — BH-FDR
q=0,10 a teljes ledger-történeten, éra-kvalifikált bar, előjel-egyezés,
swing-előjel-minimum, `MIN_ADEQUATE_T_EFF = 6,0`, **és a (e) gazdasági kapu**
(2026-10-04, elfogadva). **Semmit nem módosítok a motoron ehhez a hipotézishez.**

### 6.2 Előre rögzített kimenet-mátrix

| # | Kimenet | Olvasat |
|---|---|---|
| 1 | **Mind a 3 KILL adekvát T_eff-en** | A kioltás-hipotézis **cáfolva**: nem azért nulla az aggregát, mert a részek kioltják egymást — a részek maguk is nullák. **Ez a C forgatókönyv (jelcsalád leállítása) felé dönt.** |
| 2 | **≥1 blokk PROMOTE** | Valódi, költséget is kifizető részjel egy fix súlyozásban elrejtve. Jelölt egy **új, pre-regisztrált** élő periódusra — a súly-újrahangolás viszont **külön** kérdés, új pre-reggel. |
| 3 | **≥1 blokk `PARK_UNECONOMIC`** | A részjel valós, de a végrehajtás drága. A kritikus út a **végrehajtás** (SIM-EXEC, §11.24), nem a faktor. |
| 4 | **Ellentétes előjelek a blokkok között** | A **kioltás-hipotézis igazolva** — és ekkor a fix 0,60/0,10/0,30 súlyozás **bizonyítottan rossz**. Ez a legérdekesebb kimenet, de a súly-revízió akkor sem ezen az adaton történhet. |
| 5 | **PARK alulfeszítettségre / `low_resolution`** | Nincs döntés; adatgyűjtés folytatódik. |

### 6.3 Előjel-ellentmondás ≠ kioltás-bizonyíték önmagában

Egy **negatív** blokk-IC csak akkor számít kioltásnak, ha **szignifikáns** (BH
után) **és** a §4.2 felbontás-korlát nem magyarázza. Egy zajos −0,01 nem kioltás.
Ezt azért rögzítem előre, mert a 4. kimenet a legcsábítóbb félre-olvasás.

### 6.4 🔴 Implementálhatósági feltétel (a UW-korlát)

Ha a **HYP-006 (flow) PROMOTE-ol**, a lelet **nem használható fel**, amíg nem
tisztázott, hogy a jel a **Polygon-tagokból** (`rvol`, `squat`, `buy_pressure`)
jön-e, vagy a **kivezetett UW-tagokból** (`dp_pct`, `pcr`, `otm`, `block_trade`).
Ez az al-score-dekompozíció — **külön pre-reg, szűkebb univerzum** (§3.1).

→ **Előre rögzítve:** egy flow-PROMOTE **önmagában nem jogosít** élesítésre.

---

## 7. MULTIPLICITÁS

- **3 család** (HYP-006/007/008), családon belül Šidák-korrigált minimum-p a
  h ∈ {1,3,5,7} variánsokra (spec §5.4).
- **BH-FDR q = 0,10 a ledger TELJES történetén.** A ledger a mérés előtt
  8 attemptet tart; a HYP-005 újrateszt +2-t, ez a halmaz +12-t ad → **22**.
  A defláció ezt automatikusan beszámítja — **nem** én korrigálok kézzel.
- A **§3 halmaz zárt.** Minden további faktor új pre-reget és új ledger-sorokat
  kíván, a BH-családba beszámítva.

---

## 8. HOLDOUT

Mindhárom hipotézis **érintetlen** holdouttal indul (G6: egy érintés per
hipotézis, örökre). A dev/purge/holdout felosztást a `compute_windows` adja
(4 hét rolling holdout, 5 nap purge). **A holdoutot csak PROMOTE-jelölt
érinti** — a KILL/PARK a dev-ablakon dől el.

⚠️ `holdout_congestion`: ha 3 hipotézis egy ablakban érintené a holdoutot, a
spec §7 szerint a 3. PROMOTE a következő gördülésig vár. Ez a halmaz **pont 3
család**, tehát a torlódás reális — és **szándékosan** nem bontom kisebb
batchekre, mert az a holdout-érintést sokszorozná.

---

## 9. MIT NEM DÖNT EL EZ A MÉRÉS

1. **Nem dönt az S_j súlyozásáról.** Egy kioltás-lelet a súlyokat *kérdésessé*
   teszi, de az új súlyok **nem illeszthetők ezen az adaton** (§3.1).
2. **Nem dönt az al-score-okról** (§3.1, §6.4).
3. **Nem élesít semmit.** Bármely élő periódus **új élő pre-regisztrációt**
   kíván (minta, kapu-dátum, küszöbök); a 2026-07-25-i protokoll
   **nem újrahasznosítható**.
4. **Nem módosítja visszamenőleg** a kapu eredményét vagy a HYP-004/005
   verdikteket.

---

## 10. KERETEZÉS (G1 / pre-reg)

Post-gate, leíró. A 2026-09-22-i kapu lezárult; ennek a mérésnek az eredménye a
kapu mintájába vagy a §3 küszöbeibe **visszamenőleg nem számít be**. A kapu az
S_j-t a **megkötött trade-eken** mérte (n=79, range-restricted); ez a mérés a
**teljes keresztmetszeten** méri a blokkjait — **más estimand, más minta**
(lásd a 2026-10-04-i helyreigazítást, §11.24).

---

# AMENDMENT-1 (2026-10-04) — hosszú horizontok a HYP-007-hez

**Státusz:** ✅ **ELFOGADVA (Tamás, 2026-10-04).**

## A-1.0 IDŐZÍTÉSI TANÚSÍTVÁNY

> **Ez az amendment a HYP-007 BÁRMELY IC-mérése ELŐTT készült.** A HYP-007
> `Status: DRAFT` volt és **egyetlen attempt sem nyílt rá**. A HYP-006 és a
> HYP-008 ekkor már lefutott (A-0011..A-0018, mind KILL) — de azok **más
> faktorok, más attempt-családok**, és az ő eredményük a HYP-007 horizontjáról
> semmit nem mond.
>
> Az indoklás alapja a **mért half-life**, ami a faktor saját rang-autokorrelációja:
> a hozamoktól **matematikailag független**, tehát nulla információt hordoz az
> IC-ről. A horizont-rács hozzáigazítása a faktor **mért időskálájához**
> pre-regisztráció, nem az eredmény felé hangolás.

## A-1.1 A probléma

| | |
|---|---|
| `Funda_Score` mért half-life | **799,8 nap** (ρ = 0,999, függetlenül verifikálva) |
| Leghosszabb eredetileg regisztrált horizont | h=7 |
| h=7 a half-life arányában | **0,9%** |

A §3 rács (h ∈ {1,3,5,7}) a Flow (t½ 0,4 nap) és a Tech (t½ 2,8 nap) blokkhoz
**illeszkedik**, a Fundához **nem**.

## A-1.2 Amit az amendment regisztrál

**A HYP-007 engedélyezett horizont-halmaza: h ∈ {1, 3, 5, 7} ∪ {10, 20, 60}.**

> 🔴 **PROVENIENCIA-HELYESBÍTÉS (2026-10-04, repo-audit tárta fel).**
> **Tamás a `{20, 60}`-at hagyta jóvá** — pontosan azt, amit a HYP-007 DRAFT
> javasolt. A **h=10 implementátori kiterjesztés, NEM a jóváhagyott javaslat
> része.** CC adta hozzá a §A-1.3 mérhetőségi mérés után (a {20,60} erő-kapuzva
> nem futhatott, a h=10 a leghosszabb ma mérhető horizont), és **ugyanabban a
> fordulóban le is futtatta** — Tamásnak nem volt alkalma külön jóváhagyni.
>
> **Ez eljárási eltérés, és CC hibája.** Kimondva, nem elnyelve.
>
> **Amit NEM érint:** a verdikt. A családi minimum-p a h=3 karon van (0,767),
> tehát Šidák `m=5` → **0,99931**, `m=4` (h=10 nélkül) → **0,99705** — **mindkettő
> BH-fail, a KILL azonos**. Az eltérés iránya ráadásul **konzervatív**: az m 4→5
> növelése **emeli** a promóciós küszöböt, nem csökkenti.
>
> **A ledger append-only**: A-0023 marad, Tamás a 2026-10-04-i batch-confirmmal
> megerősítette. Újrafuttatás vagy sor-törlés **nem** történik (ifds-rules).

**Kizárólag a HYP-007-hez.** A HYP-006 és HYP-008 halmaza **változatlan**
({1,3,5,7}) — ők le is futottak azon. A motor ezt **gépileg kikényszeríti**
(`cfg.LONG_HORIZONS_BY_HYPOTHESIS`), hogy egy későbbi futás ne tudjon csendben
nem-regisztrált horizontot futtatni egy másik hipotézisre.

**Multiplicitás:** a HYP-007 családja a ténylegesen lefuttatott variánsok
Šidák-korrigált minimum-p-je, és a BH-FDR a teljes ledger-történeten fut — a
defláció tehát automatikusan beszámítja. **Nem korrigálok kézzel.**

## A-1.3 🔴 Mérhetőségi kapu — a MEGLÉVŐ erő-szabály, nem új gépezet

`T_eff = n_nap / h`, a floor `MIN_ADEQUATE_T_EFF = 6,0` (spec §5.5, változatlan).
A 2026-10-02-i dev-ablakon (62 swing nap) **a futás előtt** mérve:

| h | használható dev-nap | T_eff | futtatható? |
|---:|---:|---:|---|
| 1 | 62 | 62,00 | ✅ |
| 3 | 62 | 20,67 | ✅ |
| 5 | 62 | 12,40 | ✅ |
| 7 | 62 | 8,86 | ✅ |
| **10** | 62 | **6,20** | ✅ **a leghosszabb ma mérhető** |
| **20** | 62 | **3,10** | ❌ — 120 dev-nap kell (58 hiányzik) |
| **60** | 31 | **0,52** | ❌ — 360 dev-nap kell (298 hiányzik) |

**Szabály, előre rögzítve:** egy regisztrált horizont **akkor fut**, ha a T_eff-je
eléri a 6,0-os floort. A h=20 és h=60 tehát **regisztrált, de nem futtatott** —
nem nyílik rájuk attempt, nincs BH-infláció. Az újraindításuk a **meglévő
auto-retest** mechanizmus dolga, ahogy a minta nő (~5 nap/hét adatgyűjtési módban).

**Becsült esedékesség a jelenlegi adatütemen:** h=20 ≈ **+12 hét**, h=60 ≈ **+60 hét**.

## A-1.4 ⚠️ Egy kaput MEGFONTOLTAM ÉS ELVETETTEM

Felmerült egy **horizont-adekvácia kapu** a `MIN_ADEQUATE_T_EFF` mintájára:
*„ha h < 0,1 × half-life, a bukás horizont-alulfeszített, nem null → PARK"*.
Az AR(1)-logika csábító (h/t½ = 0,1-nél a jel ~7%-a fejeződött ki), és a
meglévő verdikteket sem írta volna át (Flow h/t½ ≈ 17,5 · Tech ≈ 2,5 ·
aggregát ≈ 0,7 — mind átmenne).

**Mégis elvetem.** A valódi faktorkutatás **rutinszerűen** tesztel lassú
faktorokat rövid horizonton: egy ~3 éves half-life-ú value-faktor havi (h≈21)
IC-je h/t½ ≈ 0,03 mellett mérődik, és ott **találnak** 0,02–0,05 nagyságú jelet.
Egy ilyen kapu tehát **legitim kutatást blokkolna** egy olyan küszöbbel, amit
nem tudok a gyakorlattal összhangban kalibrálni.

**Helyette — a már regisztrált olvasat kiterjesztése a horizont-tengelyre
(§4.2 analógia):** a h ≪ t½ **attenuálja** az IC-t, ezért

- egy **null** a HYP-007-en a rövid horizontokon **gyenge** bizonyíték,
- egy **pozitív** lelet ugyanott **erős**.

A riportnak ki kell írnia a **h / half-life arányt**, hogy az olvasó lássa,
mekkora attenuációval néz szembe. **Új gépi küszöböt nem vezetek be** — ugyanaz
az indok, mint a felbontás-korlátnál (§4.2): nem kalibrálható független forrásból,
és a házszabály szerint egy nem-kalibrálható döntési konstans tiltott.

## A-1.5 Amit az amendment NEM változtat

| Tétel | Státusz |
|---|---|
| `cfg.IC_HORIZONS` **alapértelmezett** rács (1,3,5,7) | **VÁLTOZATLAN** |
| HYP-006 / HYP-008 horizont-halmaza és verdiktjei | **VÁLTOZATLAN** |
| `MIN_ADEQUATE_T_EFF = 6,0` | **VÁLTOZATLAN** |
| BH-FDR q=0,10, Šidák családi minimum-p | **VÁLTOZATLAN** |
| (e) gazdasági kapu | **VÁLTOZATLAN** |
| Holdout-politika (4 hét + 5 nap purge, G6) | **VÁLTOZATLAN** |
| A §3 komponens-halmaz (pontosan 3 faktor) | **VÁLTOZATLAN** |

## A-1.6 Futtatási terv

**Most fut:** HYP-007, h ∈ **{1, 3, 5, 7, 10}** — mind a T_eff-floor fölött.
**Nem fut:** h = 20, 60 — regisztrálva, erő-kapuzva, auto-retestre vár.
