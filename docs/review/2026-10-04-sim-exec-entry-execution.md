# SIM-EXEC — a belépési végrehajtás ellenpróbája (LMT vs. next-day MKT)

**Dátum:** 2026-10-04 · **Keret:** post-gate, **leíró** · a 4. pont
**Task (a kitöltési szabályt és a variánsokat a futás ELŐTT rögzítette):** `docs/tasks/2026-10-04-entry-execution-counterfactual.md`
**Reprodukció:** `python scripts/analysis/entry_execution.py [--sensitivity]`

---

## 0. Egy helyreigazítás, ami az egész keretet érinti

> **Két napja egy nem-összemérhető összehasonlítást ismételtem.** Azt írtam, hogy a kapu
> ρ = **+0,073**-a „a breakeven IC (0,15–0,18) felénél van". **Ez a két szám nem ugyanaz
> az estimand:**
>
> | | Mit mér | Minta |
> |---|---|---|
> | Kapu ρ | Spearman(S_j, szektor-relatív forward hozam) **a megkötött trade-eken** | 79 pozíció, range-restricted (csak a legjobb score-ok) |
> | FRL `mean_IC` | a **napi keresztmetszeti** Spearman IC **átlaga** az összes pontozott néven | ~90–1400 név/nap × ~96 nap |
>
> A `breakeven_ic` képlet (`cost_annual_bps / (σ_cs × (252/h) × 10⁴)`, Grinold-közelítés)
> a **keresztmetszeti mean_IC-re** van levezetve. Tehát a breakeven **a FRL mean_IC-hez
> mérendő, nem a kapu ρ-jához.**
>
> **A rigorózus szám rosszabb, nem jobb:** a HYP-005 **h=1** karon a mért
> `mean_ic = +0,0079` — ez a jelenlegi breakeven IC-nek kb. **1/20-a**. A h=5/h=7
> `mean_IC` **még nem létezik** (PARK) — pontosan ezt fogja a blokkolt újrateszt
> előállítani.
>
> A következtetés iránya nem változik, de a **nagyságrend** igen, és egy laza
> összehasonlítást nem hagyok a dokumentációban.

---

## 1. Az eredmény egy sorban

**Minden LMT-variáns jobb a tényleges MKT-belépőnél**, a legjobb (V1) **+$2 442**-vel —
**de a könyv így is veszteséges** (−$2 915). A végrehajtási oldal valódi, mért nyereség;
**önmagában nem elégséges.**

| | |
|---|---|
| Közös minta | **n=78** |
| **V0 baseline** (tényleges next-day MKT) | **−$5 357,89** |
| **V1** (LMT @ tervezett ár, DAY) | **−$2 915** · **+$2 442** |
| V2 (LMT @ tervezett, 2 session) | −$2 915 · +$2 442 |
| V3 (LMT @ tervezett +0,25·ATR) | −$3 236 · +$2 122 |
| V4 (LMT @ tervezett +0,50·ATR) | −$3 352 · +$2 006 |
| **Variánsok, amik verik a V0-t** | **4/4** |

---

## 2. A legfontosabb kontextus: az execution plan MINDIG LIMIT-et írt

```
$ cat output/execution_plan_run_*.csv | awk -F, 'NR>1 && $2=="BUY"{print $3}' | sort -u
LIMIT        (669/669 sor)
```

**Mind a 669 BUY-sor `LIMIT`.** A V1 tehát **nem új ötlet — ez az eredeti terv**, amit a
swing pivot a submit-oldalon MKT-ra írt felül. A mérés azt mondja, hogy **a plan saját
utasításához visszatérve** a minta veszteségének kb. **45%-a nem keletkezett volna.**

Ez egyben **megoldja a §11.20 eredet-rejtélyét** is: a szintek azért maradtak a
`limit_price`-hoz horgonyozva, mert a **terv limit-alapú volt**; csak a beadás változott.
A §11.20 „valószínű eredet (NEM verifikált)" hipotézise ezzel **megerősítve**.

---

## 3. A mechanizmus — miért nyer a limit

| Eset | V0 (MKT) | V1 (LMT @ tervezett) |
|---|---|---|
| A nyitás a limit **alatt** | fill ≈ nyitás (kedvező) | fill = **nyitás** (ugyanaz) |
| A nyitás a limit **felett**, a nap leérinti | fill ≈ nyitás (**adverz**) | fill = **tervezett ár** |
| A nyitás felette, és sosem jön vissza | fill ≈ nyitás (adverz) | **nincs fill** |

**A limit egyoldalú javítás:** levágja az adverz oldalt, miközben a kedvező oldalt
megtartja. Ezt a számok igazolják: az **ár-javulás +$2 971**, ami ~azonos a SIM-1-ben
külön mért **teljes adverz slippage-dzsel ($2 936)** — két független úton ugyanaz a szám.
(A nettó belépési slippage $1 958 volt = $2 936 adverz − $979 kedvező; a limit az adverz
részt szünteti meg, a kedvezőt nem adja fel.)

---

## 4. Adverz szelekció — a csapda, amit meg KELLETT mérni

A kérdés nem az volt, hogy mennyi slippage-et spórolunk, hanem hogy **az elszalasztott
belépők nem voltak-e épp a nyertesek**.

| Variáns | betöltött | kimaradt | átlag V0 P&L betöltött | átlag V0 P&L kimaradt | gap |
|---|---:|---:|---:|---:|---:|
| **V1 / V2** | 72 | **6** | −$76 | **+$16** | **+$92** ⚠️ |
| V3 | 76 | 2 | −$68 | −$103 | −$35 |
| V4 | 78 | 0 | −$69 | — | — |

**A csapda valós, de kicsi.** A V1 tényleg a jobb trade-ekből vág ki (gap +$92/pozíció),
**de csak 6 pozíciót szalaszt el**, összesen **+$98** elmaradt P&L-lel — szemben a
**+$2 971** ár-javulással. A két erő aránya ~30:1 a limit javára.

---

## 5. Robusztusság — a kitöltési szabály szándékosan optimista

A task §3.2 előre kimondta: a napi bar nem bizonyítja, hogy egy sorban álló LMT-t a `low`
érintése tényleg kitöltött volna (queue-pozíció, részteljesülés). Ezért a szabály
**felülbecsli a fill-arányt** → **a limit javára torzít**. A degradálás:

| Megkövetelt letörés a limit alá | fill-arány | Σ P&L | vs V0 |
|---:|---:|---:|---:|
| 0,00% (alap) | 92% | −2 915 | **+2 442** |
| 0,10% | 91% | −2 822 | +2 536 |
| 0,25% | 88% | −3 064 | +2 293 |
| 0,50% | 86% | −2 723 | +2 635 |
| 1,00% | 69% | −1 800 | **+3 558** |

**Az előny minden tesztelt degradálást túlél**, +$2 293 és +$3 558 között. Sőt az 1%-os
marzsnál **nő** — mert ott a kimaradó belépők nettó vesztesek. A verdikt tehát
**nem a marginális érintéseken áll.**

---

## 6. A költség-modell hatása — a kapcsolat a (e) gazdasági kapuhoz

| Sorozat | n | medián bp | p75 bp | átlag bp |
|---|---:|---:|---:|---:|
| Tényleges next-day MKT \|slippage\| | 78 | **83,9** | 125,4 | 89,6 |
| **V1 LMT @ tervezett \|slippage\|** | 72 | **4,4** | **58,2** | 35,7 |

*(A 83,9 bp medián független úton reprodukálja a `cost_model.json` 83,5 bp-ját — a
pipeline cross-validálva.)*

A `breakeven_ic` **lineáris** a `cost_bps_per_side`-ban, tehát ugyanazzal a `k`-val skálázik:

| Bázis | k | breakeven IC (h=5/h=7) |
|---|---:|---|
| medián | 0,052 | 0,15–0,18 → **0,008–0,009** |
| **p75 (a megbízható)** | **0,464** | 0,15–0,18 → **0,070–0,084** |

> ⚠️ **A medián bázis itt NEM megbízható.** A V1 slippage-eloszlásnak **nullában
> pont-masszája** van (a fillek nagy része *pont* a limiten), ezért a mediánja alábecsli
> a költséget. **A p75 a helyes bázis** — és pontosan ez az, amit a `2026-10-04`-i
> (e) gazdasági kapu pre-reg **előre** rögzített. Ez a pre-regisztráció egyik haszna:
> a küszöb-választás már megvolt, mielőtt kiderült, hogy a medián félrevezető lenne.

**És a §0 figyelmeztetés itt él élesben:** ez a breakeven a **FRL keresztmetszeti
mean_IC-re** vonatkozik. A HYP-005 h=1 `mean_ic = +0,0079` — ez a **javított** (p75-alapú)
0,070–0,084-es küszöbnek is kb. **1/10-e**. A h=5/h=7 `mean_IC` a blokkolt újrateszt
outputja lesz.

---

## 7. Validáció

- **V0 baseline-konzisztencia:** Σ = **−$5 357,89**, **centre azonos** a SIM-1 B-számával.
- **Ár-javulás cross-check:** +$2 971 ≈ a SIM-1-ben függetlenül mért teljes adverz
  slippage ($2 936).
- **Cost-modell cross-check:** a mért 83,9 bp medián ≈ a `cost_model.json` 83,5 bp-ja.
- Örökölt hitelességi kapu: a harness a SIM-1-ben validálva (exit-szekvencia 72/76 = 95%,
  szint-rekonstrukció 9/9 centre, végrehajtási modell megmérve).

---

## 8. Korlátok (őszintén)

1. **A fill-arány felülbecsült** (§5) — ezért a degradálási táblázat, nem egyetlen szám.
2. **A kimaradt belépők kapacitást szabadítanának fel** — élesben egy nem-betöltött LMT
   helyére más pozíció léphetett volna. A mérés ezt **nem** modellezi (ugyanaz a korlát,
   mint a SIM-2 slot-kontenciója). Iránya: a limit javára.
3. **A V2 azonos a V1-gyel** — a 2. session egyetlen további fillt sem hozott. Vagyis a
   limit vagy az első napon teljesül, vagy soha; a hosszabb érvényesség értéktelen.
4. **Egyetlen piaci rezsim** (2026-05-18 → 10-02, ~4,5 hónap).
5. **Nem következik élesítés.** Ez leíró mérés. Egy limit-stílusú belépő élesítése
   **új élő pre-regisztrációt** kíván (minta, kapu-dátum, küszöbök).
6. A `+$2 442` **nem** teszi nyereségessé a könyvet: −$5 358 → −$2 915. A végrehajtás a
   veszteség ~45%-át magyarázza, **a maradék 55% továbbra is a belépők.**

---

## 9. Keretezés (G1 / pre-reg)

Post-gate, leíró. A kapu mintájába/küszöbeibe visszamenőleg **nem** számít be, és azokat
**nem** módosítja. A (e) gazdasági kapu pre-regje (`docs/planning/2026-10-04-economic-gate-preregistration.md`)
**Tamás döntésére vár**; a HYP-005 újrateszt **blokkolt** addig. Ez a mérés a
`PARK_UNECONOMIC` újratesztjének **inputja**, nem a kapu helyettesítője.
