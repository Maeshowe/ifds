# Komponens-dekompozíció — mind a három blokk tiszta null

**Dátum:** 2026-10-04 · **Attemptek:** A-0011…A-0014 (Flow), A-0015…A-0018 (Tech), A-0019…A-0023 (Funda)
**Pre-reg:** `docs/planning/2026-10-04-component-decomposition-preregistration.md` (a retest eredménye **előtt** rögzítve)
**Reprodukció:** `python scripts/research/run_frl_batch.py --hyp HYP-006 --date 2026-10-02` (és `--hyp HYP-008`)
✅ **Mind a 13 verdikt MEGERŐSÍTVE** (Tamás, 2026-10-04), `human_confirmed: true`.

---

## 1. Az eredmény

### HYP-006 — Flow blokk (súly **0,60**)

| h | T_eff | mean IC | éra-bar | NW t | p | verdikt |
|---|---:|---:|---:|---:|---:|---|
| 1 | **62,0** | **+0,0089** | 0,0273 | 0,65 | 0,517 | KILL (A-0011) |
| 3 | 20,7 | −0,0021 | 0,0260 | −0,16 | 0,875 | KILL (A-0012) |
| 5 | 12,4 | −0,0011 | 0,0275 | −0,08 | 0,937 | KILL (A-0013) |
| 7 | 8,9 | −0,0080 | 0,0295 | −0,54 | 0,603 | KILL (A-0014) |

Šidák-családi p (m=4, swing): **0,9455** → BH q=0,10 **fail**.

### HYP-008 — Technical blokk (súly **0,30**)

| h | T_eff | mean IC | éra-bar | NW t | p | verdikt |
|---|---:|---:|---:|---:|---:|---|
| 1 | **62,0** | −0,0028 | 0,0303 | −0,19 | 0,854 | KILL (A-0015) |
| 3 | 20,7 | +0,0053 | 0,0322 | 0,33 | 0,745 | KILL (A-0016) |
| 5 | 12,4 | **+0,0071** | 0,0251 | 0,57 | 0,583 | KILL (A-0017) |
| 7 | 8,9 | +0,0054 | 0,0244 | 0,44 | 0,670 | KILL (A-0018) |

Šidák-családi p (m=4, swing): **0,9699** → BH q=0,10 **fail**.

**Mind a 8 kar a 6,0-os adekvácia-floor FÖLÖTT bukott** (T_eff 8,9–62,0). A h=1
karokon a T_eff **62,0** — ez a projekt eddigi **legerősebb** null-mérése.

### HYP-007 — Fundamentals blokk (súly **0,10**) — AMENDMENT-1 után

| h | T_eff | mean IC | éra-bar | p | h / t½ | verdikt |
|---|---:|---:|---:|---:|---:|---|
| 1 | 62,0 | +0,0015 | 0,0215 | 0,887 | 0,001 | KILL (A-0019) |
| 3 | 20,7 | −0,0045 | 0,0301 | 0,767 | 0,004 | KILL (A-0020) |
| 5 | 12,4 | −0,0021 | 0,0408 | 0,921 | 0,006 | KILL (A-0021) |
| 7 | 8,9 | +0,0047 | 0,0457 | 0,842 | 0,009 | KILL (A-0022) |
| **10** | **6,2** | **+0,0034** | 0,0545 | 0,905 | 0,013 | KILL (A-0023) |

Šidák-családi p (m=5, swing): **0,9993** — a három blokk **leglaposabb** eredménye.

**A h-görbe NEM emelkedik**, sőt előjelet vált. Egy lassú faktornál, aminek a jele
attenuálva is jelen van, az IC-nek **nőnie** kellene a horizonttal — ez az
attenuációs olvasat tesztelhető következménye, és **nem teljesül**.

⚠️ **h ∈ {20, 60} nem futott** (T_eff 3,10 és 0,52 < floor 6,0) — regisztrálva,
erő-kapuzva, attempt nélkül. A null tehát **gyenge** bizonyíték marad azon a
tartományon, ahol a faktor 800 napos időskálája ténylegesen él. Esedékesség a
jelenlegi adatütemen: h=20 ≈ **+12 hét**, h=60 ≈ **+60 hét**.

---

## 2. A kioltás-hipotézis NEM támogatott

A dekompozíció azért indult, mert egy aggregát-null két dolgot jelenthet:
(i) egyik komponensnek sincs jele, vagy (ii) **kioltják egymást**.

A (ii) **nagy, ellentétes előjelű** komponens-IC-ket kíván (pl. Flow +0,04 és
Tech −0,03). A mért értékek: **minden |IC| < 0,009**, és mindegyik **messze a
saját bar-ja alatt** (0,024–0,032). **Nincs mit kioltani.**

### 2.1 Egy aritmetikai hiba, amit NEM követek el

Csábító lenne a maradék Funda-blokk IC-jét kiszámolni az aggregátból és a két
mért blokkból. **Ez érvénytelen:** egy súlyozott összeg **Spearman** IC-je
**nem** a komponensek Spearman IC-jeinek súlyozott összege — a rangok nem
adódnak össze. Az aggregát a súlyozott összeg rangja, nem a rangok súlyozott
összege. **A Funda-blokk IC-je tehát nem következtethető ki; meg kell mérni.**

---

## 3. A h-görbék ALAKJA megfelel a pre-regnek — a SZINTJE nulla

Ez a legfinomabb lelet, és érdemes kimondani:

| Hipotézis | Pre-regisztrált várakozás | Mért alak |
|---|---|---|
| HYP-006 Flow | *„a volumen-jelek gyorsan bomlanak → maximum h=1/h=3, csökkenő görbe"* | maximum **h=1**-en (+0,0089), majd lefordul ✅ |
| HYP-008 Tech | *„a momentum több napon akkumulál → maximum h=5–7, emelkedő görbe"* | h=1-ről **emelkedik**, maximum **h=5**-en (+0,0071) ✅ |

**A mechanizmusok nem fordítva működnek — egyszerűen mérhető nagyságrendben
nincsenek jelen.** Mindkét görbe a megjósolt *irányba* mutat, és mindkettő
**a bar negyede–harmada** alatt marad.

---

## 4. A gazdasági kapu meg sem szólalt — de a half-life lelet áll

A (e) kapu a PROMOTE-ágat fogja el; itt a statisztikai kapu előbb ölt, tehát a
(e) nem jutott szóhoz. A **futás előtt mért** half-life azonban továbbra is
érvényes, és azt mondja, hogy **még egy valós jel is kiaknázhatatlan** lett volna:

| Blokk | t½ (nap) | költség bp/év | breakeven IC (h=5) |
|---|---:|---:|---:|
| Flow | **0,4** | 114 682 | **3,79** ⛔ matematikailag lehetetlen |
| Tech | **2,8** | 15 044 | **0,4975** ⛔ gyakorlatilag lehetetlen |
| Funda | **799,8** | **53** | **0,0017** 🟢 |

*(A half-life a faktor saját rang-autokorrelációja — a hozamoktól független,
tehát nulla információt hordoz az IC-ről. Független úton verifikálva:
ρ = 0,151 / 0,781 / 0,999.)*

---

## 5. Hol állunk — 90% a súlyozásból megerősített null

| Komponens | Súly | Státusz |
|---|---:|---|
| Aggregált S_j (HYP-005) | — | **KILLED** mind a 4 horizonton (megerősítve) |
| **Flow blokk** (HYP-006) | **0,60** | **KILLED** mind a 4 horizonton (ma) |
| **Tech blokk** (HYP-008) | **0,30** | **KILLED** mind a 4 horizonton (ma) |
| **Funda blokk** (HYP-007) | **0,10** | **KILLED** h ∈ {1,3,5,7,10} (ma) |

> **A score súlyozásának 100%-a megerősített keresztmetszeti null, adekvát erővel,
> emberi megerősítéssel.** Az aggregát és mind a három súlyozott komponens KILL.
>
> **Egyetlen fenntartás:** a Funda-blokk a **saját időskáláján** (t½ 800 nap) még
> nincs megmérve — a h=20/60 erő-kapuzva vár. Az attenuációs olvasat szerint ez a
> null a leggyengébb a háromból. **De** a h-görbe ott sem emelkedik, ami a
> „kibontakozó lassú jel" hipotézis ellen szól.

### 5.1 Az AMENDMENT-1 és ami belőle futott

A regisztrált h ∈ {1,3,5,7} rács a Funda-blokk **799,8 napos** half-life-jához
mérve **0,1–0,9%** — félre-specifikált. Így futtatva **KILL-t rögzítenék egy
olyan teszten, ami nem volt alkalmas a hipotézis vizsgálatára**, és a `KILLED`
státusz a jövőben lezártnak tűnne. Ez rosszabb, mint nem mérni.

**Javaslat:** **h ∈ {20, 60}** hozzáadása **kizárólag a HYP-007-hez**.
Nem post-hoc hangolás: a half-life a hozamoktól **matematikailag független** és
**minden IC-mérés előtt** mérve; a rács hozzáigazítása a faktor **mért
időskálájához** pre-regisztráció. **De** érinti a `cfg.IC_HORIZONS` spec-konstanst
→ **governance-döntés (Tamás)**, nem az enyém. Ára: Šidák-család 12 → 14 attempt.

---

## 6. Egy motor-megfigyelés (NEM javítom — post-hoc lenne)

Négy KILL a pre-reg **(b) „előjel-ellentmondás — terminális"** úton született
(A-0012/13/14, A-0015), pedig a mért |IC| ott **0,0011–0,0080**, azaz a bar
**tizede–negyede**. A (b) kritérium **kizárólag az előjelre** tüzel, a
nagyságtól függetlenül — így egy **zaj-szintű** negatív leolvasás
„a mechanizmus megdőlt" címkét kap.

**A verdiktet ez nem érinti:** mind a négy karon a T_eff ≥ 6, tehát az **(a)**
kritérium (valódi null) **önmagában is** KILL-t adott volna. Csak az **indoklás
szövege** félrevezető.

📌 Ezt **megfigyelésként** rögzítem, **nem javítom** — a motor módosítása az
eredmények látása után csak előre rögzített kritériumhoz igazításként legitim,
és a (b) kritérium szövege így szól. Ha a (b)-hez magnitúdó-feltétel kell, az
**külön, előre rögzített** döntés.

---

## 7. Korlátok

1. **Felbontás.** `Flow_Score` ~16,7 / `Tech_Score` ~6,0 distinct érték ~561 név
   között. A holtverseny a Spearman-t **a nulla felé** attenuálja → a null
   **gyengébb** bizonyíték, mint egy pozitív lelet lenne (pre-reg §4.2). A
   `Tech_Score` 6 szintjén ez érdemi. **Nem** vezettem be új gépi küszöböt rá:
   nem kalibrálható független forrásból.
2. **Swing-éra only**, 62 nap, dev-ablak 05-18..08-28. A legacy láb üres.
3. **A Flow blokk 7-tagú**, és **4 tag UW-eredetű** (kivezetve). Egy null itt
   tehát nem mondja meg, hogy a Polygon-tagok (`rvol`, `squat`, `buy_pressure`)
   külön-külön nullák-e — az al-score-dekompozíció **külön pre-reg, szűkebb
   univerzum** (pre-reg §3.1).
4. **T_eff 62,0 a h=1 karokon igen erős, de nem végtelen:** egy |IC| < 0,005
   nagyságú jel továbbra is láthatatlan. A verdikt „nincs **használható** jel",
   nem „matematikailag nulla".
5. A `Tech_Score` a nem pontozott sorokban **valódi** értéket hordoz (nem
   defaultot), de a `|Total_Score| > 1e-9` szűrőt **egységesen** alkalmaztam,
   hogy a három blokk **ugyanazon a mintán** legyen mérve, különben nem
   összehasonlíthatók.

---

## 8. Keretezés (G1 / pre-reg)

Post-gate, leíró. A 2026-09-22-i kapu lezárult; ez a mérés a kapu mintájába vagy
a §3 küszöbeibe **visszamenőleg nem** számít be. A kapu az S_j-t a **megkötött
trade-eken** mérte (n=79, range-restricted); ez a **teljes keresztmetszeten**
méri a blokkjait — **más estimand, más minta** (`04-risks` §11.24).
