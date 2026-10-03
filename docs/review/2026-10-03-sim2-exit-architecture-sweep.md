# SIM-2 — exit-architektúra sweep a fix belépőkön

**Dátum:** 2026-10-03 · **Keret:** D6 SIM-napirend 2. tétel, **post-gate, leíró**
**Task (a rácsot a futás ELŐTT rögzítette):** `docs/tasks/2026-10-03-sim2-exit-architecture-sweep.md`
**Reprodukció:** `python scripts/analysis/exit_sweep.py [--stage2]`

---

## 1. Az eredmény egy sorban

**A pre-regisztrált rács mind a 15 cellája veszteséges. Egyik sem különbözik
szignifikánsan a baseline-tól (0/14, Šidák).** Az exit-architektúra **nem menti meg** a
könyvet.

| | |
|---|---|
| Közös minta (mind a 15 cellában feloldható) | **n=75** |
| Baseline (max_hold=5, TP1=1,5) Σ | **−$5 206** |
| **Legjobb cella** (max_hold=3, TP1=2,0) Σ | **−$4 187** (vs baseline **+$1 019**, p=0,35) |
| Legrosszabb cella (max_hold=15, TP1=2,0) Σ | −$6 278 |
| **Cellák Σ > 0-val** | **0/15** |
| **Šidák-szignifikáns cellák** (α_per=0,00366) | **0/14** |
| Legjobb a 2. szakasz exploratív terével együtt (25 cella) | **−$3 582** |

A legjobb cella előnye (+$1 019) **nem szignifikáns még korrekció nélkül sem**
(p=0,35; bootstrap CI [−$1 106, +$3 099]).

---

## 2. A teljes rács — minden cella, nem a legjobb

| max_hold | TP1 | Σ P&L | vs baseline | p (párosított) | bootstrap 95% CI | csúcs-slot |
|---:|---:|---:|---:|---:|---:|---:|
| 3 | 1,0 | −4 945 | +261 | 0,806 | [−1 817, +2 305] | 7 |
| 3 | 1,5 | −4 391 | +815 | 0,449 | [−1 294, +2 891] | 7 |
| **3** | **2,0** | **−4 187** | **+1 019** | **0,349** | [−1 106, +3 099] | 7 |
| 5 | 1,0 | −5 559 | −353 | 0,104 | [−796, +38] | 10 |
| **5** | **1,5** | **−5 206** | **baseline** | — | — | 10 |
| 5 | 2,0 | −5 179 | +27 | 0,908 | [−443, +485] | 10 |
| 7 | 1,0 | −4 886 | +321 | 0,708 | [−1 322, +2 006] | 12 |
| 7 | 1,5 | −4 864 | +342 | 0,701 | [−1 354, +2 084] | 12 |
| 7 | 2,0 | −4 915 | +291 | 0,753 | [−1 497, +2 081] | 12 |
| 10 | 1,0 | −5 343 | −137 | 0,901 | [−2 264, +2 033] | **14** ⚠️ |
| 10 | 1,5 | −4 749 | +457 | 0,719 | [−1 954, +2 963] | **14** ⚠️ |
| 10 | 2,0 | −5 289 | −83 | 0,950 | [−2 642, +2 526] | **14** ⚠️ |
| 15 | 1,0 | −5 722 | −516 | 0,715 | [−3 197, +2 293] | **18** ⚠️ |
| 15 | 1,5 | −5 633 | −427 | 0,795 | [−3 563, +2 786] | **18** ⚠️ |
| 15 | 2,0 | −6 278 | −1 072 | 0,578 | [−4 816, +2 673] | **18** ⚠️ |

⚠️ = **nem megvalósítható**: a cella több egyidejű pozíciót igényel, mint az élő
`max_concurrent=12`. Az ilyen cellák eredménye **felső korlát**, nem elérhető hozam.

**A TP1-tengely gyakorlatilag inert**: 1,0 / 1,5 / 2,0 között a különbség minden
`max_hold`-nál ~$700 alatt, előjelben sem következetes.

---

## 3. A kitettség-diagnosztika — itt válik a kép értelmessé

| | |
|---|---|
| Pearson r(Σ pozíció-nap, Σ P&L) a 15 cellán | **−0,738** |
| OLS meredekség | **−$1,95 / pozíció-nap** |
| Baseline kitettség | 371 pozíció-nap |

**Minél több időt töltünk a piacon, annál többet veszítünk — aggregáltan monoton.**
Ez a **belépők negatív várható driftjének** a szignatúrája, nem egy elhangolt exitnek.
Ezt a 2. szakasz is megerősíti: a **szorosabb** stop (1,0–1,5·ATR) mindkét horgonynál
jobb a 2,0-nál — vagyis minden javulás ugyanabból a forrásból jön: **kevesebb
piaci kitettség**.

Egy edge-gel rendelkező könyvnél ennek a **fordítottja** igaz: a hosszabb tartás engedi
az edge-et akkumulálni. Itt a hosszabb tartás vérzik.

> ⚠️ **Fontos korlát az általánosításban:** a 15 cella **ugyanazt a 75 pozíciót** használja,
> tehát erősen korrelált — az r = −0,738 **leíró**, nincs hozzá p-érték. És az eredmény
> **erre a jelre feltételes**: NEM mutatja, hogy a hosszabb tartás egy *másik* jelnél
> rossz lenne. Azt mutatja, hogy **ezeket a belépőket** nem lehet exitekkel megjavítani.

---

## 4. 2. szakasz — exploratív stop-próba (következtetés nélkül)

A rácson **kívül**, kizárólag hipotézis-generáló céllal. Egy itt kiválasztott
konfiguráció **ezen az adaton semmilyen körülmények között nem promótálható**.

| max_hold / TP1 | stop 1,0 | stop 1,5 | **stop 2,0 (prod)** | stop 2,5 | stop 3,0 |
|---|---:|---:|---:|---:|---:|
| 3 / 2,0 | −3 804 | **−3 582** | −4 187 | −4 110 | −4 110 |
| 5 / 1,5 | −4 091 | −4 296 | −5 206 | −5 090 | −5 022 |

**Mind a 10 exploratív cella is veszteség.** A legjobb (3 / 2,0 / stop 1,5) **−$3 582**
— $477k telepített notionalon, 75 pozíción. Ez nem stratégia.

---

## 5. Validáció

### 5.1 Baseline-konzisztencia (a task §6 előírta)

A (5 / 1,5) cella a **saját feloldott halmazán (78/78)** Σ = **−$5 357,89** — ez
**centre azonos** a SIM-1 publikált B-számával. A harness paraméterezése tehát helyes;
a riportban szereplő −$5 206 ugyanaz a cella a **közös 75-ös** mintán.

### 5.2 A közös minta szabálya működött

A 78-ból **3 pozíció** esett ki: **MANH 09-14, EXLS 09-21, MD 09-22** — pontosan a
**három legfrissebb belépő**, amelyeknek nincs elég előre-bar a `max_hold=15` celláhez.
Ez az a szelekciós artefakt, amit a szabály megelőzni hivatott: nélküle a hosszabb hold
azért tűnt volna jobbnak, mert elhagyja a legutóbbi pozíciókat.

### 5.3 Örökölt hitelességi kapu

A harness a SIM-1-ben validált: exit-szekvencia **72/76 (95%)** egyezés a ledgerrel, a
szint-rekonstrukció a termelés tárolt geometriájával **9/9-ben centre** egyezik, a
végrehajtási modell megmérve (MOC-láb 6,6 bp, next-day MKT láb 61 bp).
`tests/test_sim1_regression.py` pineli a publikált SIM-1 számokat, hogy a megosztott
minta-összeállítás refaktora ne tudja elcsúsztatni őket.

---

## 6. Mit jelent ez

**A hipotézis-tér bezárult a mechanika felől.** Három független mérés mutat ugyanarra:

| Mérés | Eredmény | Következtetés |
|---|---|---|
| Kapu (2026-10-03) | L2 ρ = **+0,073**, CI [−0,150, +0,289] | a mért költségen a breakeven IC **0,15–0,18** → a jel a küszöb **alatt** |
| SIM-1 | geometria-javítás **≈$0** (CI [−707, +649]) | a §11.20 defekt **nem** okozta a veszteséget |
| **SIM-2** | **0/15 cella pozitív, 0/14 szignifikáns** | az exit-architektúra **nem** okozta, és nem javítja |

A dekompozíció így áll össze (n=78 minta, tényleges realizált −$7 657,43):
belépési slippage **−$1 958 (26%)** · commission −$215 (3%) · geometria **≈$0** ·
exit-architektúra **≈$0** · **reziduális = a belépők maguk ≈ −$5 500 (72%)**.

**Amit NEM mond:** nem bizonyítja, hogy a jel bizonyítottan nulla vagy negatív — a kapu
ereje egy *kis* edge-re nem volt elég (|ρ| ≈ 0,36–0,38 kellett volna n=79-en). Azt mondja,
hogy **a mechanikai magyarázatok elfogytak**, és ami marad, az a jel és a költségszint
viszonya.

---

## 7. Korlátok (őszintén)

1. **n=75** a közös mintán (78-ból, 93 swing-éra zárt pozícióból). A kizárások tételesen
   a SIM-1 riportban; a futás előtt rögzítve.
2. **A belépők fixek.** Ez szándékos elhatárolás, de azt is jelenti, hogy a sweep **nem**
   modellezi a slot-kontenciót: élesben egy rövidebb `max_hold` több *új* belépőt is
   engedett volna. A csúcs-slot kolonna ezt jelzi, de nem korrigálja.
3. **A cellák erősen korreláltak** (ugyanaz a 75 pozíció) → a kitettség-korreláció leíró.
4. **Egyetlen piaci rezsim** (2026-05-18 → 10-02, ~4,5 hónap). Egy másik rezsimben a
   `max_hold`-érzékenység más lehet.
5. A legjobb cella előnye **nem szignifikáns korrekció nélkül sem** — nem állítom, hogy
   `max_hold=3` jobb. Azt állítom, hogy **egyik sem nyereséges**.
6. A 2. szakasz **exploratív**: 10 további cella, inferencia nélkül. Beleszámítva összesen
   25 bejárt konfiguráció — a „legjobb 25-ből" érték **felső-torzított**, és **így is
   −$3 582**.

---

## 8. Keretezés (G1 / pre-reg)

Post-gate, leíró. A kapu mintájába/küszöbeibe visszamenőleg **nem** számít be, és azokat
**nem** módosítja — a pre-reg a kánon. Bármely jövőbeli élő periódus **új
pre-regisztrációt** kíván; ez a szám annak **inputja**.
