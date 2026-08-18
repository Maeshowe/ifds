Status: OPEN
Updated: 2026-08-18
Note: A 63 napos swing paper-periódus (2026-05-18 → 08-17) tényszerű összefoglalója + javaslat a folytatásra. TAMÁS-DÖNTÉST KÉR: D5 (kritérium-3 számlálási bázis), D6 (a paraméter-revíziók útja a kapu-ablakban). G3: nincs jel-érvényességi nyelv — minden állítás LEÍRÓ.

# A 63 napos swing paper-periódus — összefoglaló és javaslat

> ⚠️ **G3-keret.** A kapu **2026-09-22**. Ez a dokumentum **leíró**; nem állít semmit a jel
> érvényességéről, és **nem jelzi előre** a kapu kimenetelét. A pre-reg §3 kritériumok
> **nem módosíthatók** — az alábbi javaslatok egyike sem nyúl hozzájuk.

## 1. Hol tartunk — a pre-reg kritériumok Day 63-as állása

**A Day 63 nem kapu (D1).** Az alábbi tehát **állás-jelentés, nem verdikt.**
A §3 szerint a *távolság riportálható*, az *előrejelzés tilos*.

### ÉLESÍTÉS — mind a három EGYIDEJŰLEG kell

| # | Kritérium | Küszöb | Day 63 tény | Áll? |
|---|---|---|---|---|
| 1 | Kumulatív paper P&L | > **+$2 000** | **−$449,88** (távolság: $2 449,88) | ✗ |
| 2 | Sharpe (60 napi, realized-only, annualizált) | > **0,5** | **+0,090** | ✗ |
| 3 | Pozitív excess vs SPY napok | > **25 / 63** | **25 / 54 megfigyelt** (46,3%) | ⚠️ **lásd D5** |

### LEÁLLÍTÁS — bármelyik elég

| Trigger | Küszöb | Tény (D4: a `mean` az irányadó) | Áll? |
|---|---|---|---|
| 10 napi excess átlag | < −1,0% | **−0,36%** | ✓ nincs |
| 15 napi excess átlag | < −1,0% | **−0,26%** | ✓ nincs |
| 30 napi kumulatív | < −3,0% | **−1,01%** | ✓ nincs |

**→ A default (PAPER FOLYTATÁS) áll fenn.** Egyik leállítási feltétel sem aktivált, és a
STOP-mean **3× egymás után javult**.

> A `sum`-olvasat BREACH-en áll (10d −3,57%, 15d −3,91%), de **D4 szerint ez megfigyelés,
> nem trigger** — a pre-reg szó szerint „átlag"-ot mond.

### 🔴 D5 — TAMÁS-DÖNTÉST KÉR: a 3. kritérium számlálási bázisa

A kritérium szövege: **„> 25 / 63 nap"**. Két kétértelműség, amit a kapu ELŐTT kell zárni:

1. **Szigorú vagy megengedő reláció?** A tény **pontosan 25** — ami `> 25`-nek **nem** felel meg,
   `≥ 25`-nek igen. **Egyetlen napon múlik.**
2. **Mi a nevező?** A 9 outage-nap miatt **54 megfigyelt nap** van a 63-ból. A 40%-os arány
   (25/54 = 46,3%) teljesül, a nominális 63-as nevező (25/63 = 39,7%) **nem**.

⚠️ **Ezt most kell eldönteni, az eredmény ismerete NÉLKÜL is elfogultsági kockázat** — de a
kockázat kisebb, mint a kapunál dönteni, amikor a döntés már közvetlenül egy kimenetelt választ.
**CC javaslata: `≥ 25` a megfigyelt napokra vetítve (arány-alapú, 40%)** — mert a §5 kizárási
elv (az outage-napok nem számítanak bele) már így működik a STOP-triggereknél is, és
a kettő közti következetlenség önmagában hiba. **De ez Tamás döntése, és írásban kell rögzülnie.**

### A §D3/M korlát a 3. kritériumon (kötelező olvasat)
A 25 pozitív napból **5 nap 0-exites**, ahol `excess ≡ −SPY` — ott a számláló **piaci irányt
mér, nem stratégiai teljesítményt**. Az exites napokra szűkítve: **20 / 35**.

---

## 2. Mi történt — a periódus tényszerű képe

### Zárt pozíciók (§5-szűrt minta, n=39)

| Mérőszám | Érték |
|---|---|
| Win rate | **18/39 = 46,2%** |
| Átlag R | **−0,107%** (medián −0,322%) |
| Átlag nyerő / vesztő | **+3,370%** / **−3,086%** (payoff 1,09) |
| Profit factor (R-alapon) | **0,936** |

**Kép: közel szimmetrikus, enyhén negatív eloszlás.** A −$449,88 kumulatív **−0,45%** a tőkén —
a periódus nem katasztrófa, hanem **lapos**.

### Exit-típus szerinti bontás (STRUKTURÁLIS megfigyelés, nem jel-állítás)

| Exit-típus | n | win | átlag R | Σ R |
|---|---|---|---|---|
| **TIME_STOP** (max_hold) | **31 (79,5%)** | 14/31 | −0,331% | **−10,25%** |
| **TP2** | 4 (10,3%) | **4/4** | **+6,269%** | **+25,08%** |
| **MENTAL_SL** | 4 (10,3%) | **0/4** | −4,747% | **−18,99%** |

**A periódus legfontosabb strukturális ténye: a pozíciók ~80%-a nem célon és nem stopon zárul,
hanem a `max_hold` lejáratán.** A TP2-ág ritka (10%), de nagy és 4/4 nyerő; a MENTAL_SL-ág
ugyanolyan ritka, de 0/4 és nagy. A nettó eredményt a **TIME_STOP-tömb** hordozza,
és az ~nullán van (−0,33% átlag).

> Ez **exit-architektúra-megfigyelés**, nem a jelről szóló állítás (G3). Hogy a `max_hold=5`
> túl korán vagy túl későn vág-e, **nincs megmérve** — ezt a §4 javaslat teszi mérhetővé.

### A periódus üzemviteli terhelése
- **9 outage trading nap** (5 esemény) — a 63-ból **14,3%**. Ebből **3 esemény (07-22, 08-07 + a
  gyökérok) FileVault**, 1 áramszünet, 1 SSH-orphan.
- **6 pozíció** outage-késleltetett exittel, **mind a 4 esemény rosszabbul zárt a szándékoltnál**.
- A `signal_attribution` minta ezért **43 → 39** (a nyers 53 zárt lábból).

---

## 3. Amit a periódus MEGVÁLASZOLT (és amit nem)

**Megválaszolt (leíró, magas bizonyosság):**
- A **swing-architektúra üzemszerűen működik** — a cron-lánc, a ledger, a reconcile, a
  broker-authoritatív P&L-könyvelés végigvitte a 63 napot. Ahol elakadt, ott **külső** ok volt
  (áram, FileVault, SSH-orphan), nem logikai hiba.
- A **STOP-triggerek nem aktiváltak** egyetlen olvasat szerint sem (a `mean`-en).
- A **UW-jel nélkülözhető** — a rendszer 2 hónapja Polygon-only GEX-en fut, output-invariánsan.

**NEM válaszolt meg (és a kapuig nem is fog):**
- **Van-e jel-alapú edge.** A leíró futás elsődleges metrikája **−0,018 / −0,008**, a CI
  mindkettőn tartalmazza a 0-t, és `n=39` a detektálható effektus-méret alatt van. **Ez nem
  „nincs edge" — ez „nem mértük meg".** A minta 09-22-ig nő.
- **Jó-e a `max_hold=5`.** A 79,5%-os TIME_STOP-arány ezt a kérdést élesíti, de nem dönti el.

---

## 4. 🔴 D6 — A KÖZPONTI KÉRDÉS: hogyan folytassuk a kapuig?

### A feszültség, amit fel kell oldani

- **D1** kimondta: a freeze feloldásának egyik indoka, hogy **„a scoring-revíziók elindulhatnak"**.
- **D2** kimondta: a kapu **2026-09-22**, és a kritérium-ablakok az **utolsó N trading napra** szólnak.

**Ez a kettő ütközik.** Számszerűen: a 09-22-vel záruló 63 trading napos ablak **2026-06-24-én
kezdődik**, és ebből **25 nap (40%) esik a freeze-feloldás UTÁNRA**.

> **Ha most hozzányúlunk a production paraméterekhez, a kapu-ablak 40%-a más konfiguráción fut,
> mint a másik 60% — azaz a kritérium egy éra-poolozott mintán mérne. Ez pontosan az a
> G5-hibaosztály, amit a protokoll a `scoring_validation.py`-nál már ismert nyitott tételként
> jelöl.**

### A négy út

| Út | Mit jelent | Ítélet |
|---|---|---|
| **(A) De facto freeze-hosszabbítás 09-22-ig** | prod-paraméterek érintetlenül | Tiszta kapu, de **5 hét fejlesztési idő elveszik** |
| **(B) Változtatunk most, a kapu-ablakot újrabázoljuk** | az ablak a változás napjától indul | 09-22-re **n≈25 nap** — a 63-as ablakhoz **elégtelen** |
| **(C) Változtatunk most, a kaput kitoljuk** | új dátum | **D2-sértés** (a fix dátum lényege az volt, hogy megszűnjön a csúszkálás) |
| **(D) Kétsávos: prod fagyva + revíziók SIM-ben** | a production konfig változatlan 09-22-ig; a revíziók a meglévő SIM-L2 / Mode 2 re-score infrán futnak | ✅ **CC JAVASLATA** |

### ✅ CC javaslata: (D) — kétsávos folytatás

**A production konfiguráció marad változatlan 2026-09-22-ig.** A D1 szándéka (a revíziók
elindulhatnak) **maradéktalanul teljesül** — csak nem a live számlán, hanem azon az
infrastruktúrán, amit pontosan erre építettünk:

- `sim/rescore.py` — **Mode 2 re-score**: a Phase 4 snapshotokból újraszámolt scoring
  config-variánsokkal, **élő futtatás nélkül**
- `sim/comparison.py` — **párosított t-teszt** a variánsok között
- `python -m ifds compare --config sim_variants_test.yaml`

**Amit ez megvesz:** a kapu-ablak **homogén marad** (egyetlen konfiguráció, nincs G5-sértés),
és 09-22-re **kész, megmért revízió-jelöltek** állnak rendelkezésre — nem ötletek.

**Amit ez nem enged meg:** a SIM-eredmények **nem kapu-inputok** (G1) — sem mellette, sem ellene.
Ez nem korlátozás, hanem a rend fenntartása: a SIM a **kapu utáni** döntés inputja.

### A javasolt SIM-napirend (prioritási sorrendben)

| # | Hipotézis | Miért ez | Eszköz |
|---|---|---|---|
| 1 | **`max_hold` érzékenység** (3 / 5 / 7 / 10 nap) | a periódus legerősebb strukturális ténye: az exitek **79,5%-a** itt zárul | Mode 2 re-score + broker_sim |
| 2 | **MENTAL_SL kalibráció** | 0/4 win, átlag −4,75% — a legrosszabb ág; a stop-távolság vagy a trigger vizsgálandó | broker_sim sweep |
| 3 | **TP2-elérés gyakorisága** | 4/4 win, +6,27% átlag — a ritka nagy ág; elérhető-e gyakrabban szorosabb TP2-vel | Mode 2 re-score |
| 4 | **Végrehajtási stílus** (MKT vs LMT/LOO) | slippage n=24, 17 adverz; az FRL cost-model mediánja ~96 bp/oldal | cost-model + broker_sim |

> A 4. tétel az FRL-lane-hez kapcsolódik (`research/cost_model.json`) — **a FRL-outputok
> ÖRÖKRE leírók és inadmissibilisek a kapuba (G1/§7)**; itt kizárólag a SIM-napirend
> priorizálásához használjuk.

---

## 5. Amit a kapuig el kell végezni (checklist)

| # | Tétel | Gazda | Határidő |
|---|---|---|---|
| 1 | **§5.6 mechanizmus-döntés** — a §5 kizárás nincs a pinelt eszközben (a kapu blokkolója) | **Tamás** | 09-22 ELŐTT |
| 2 | **D5** — a 3. kritérium számlálási bázisa (`>` vs `≥`, 63 vs megfigyelt nevező) | **Tamás** | 09-22 ELŐTT |
| 3 | **D6** — a kétsávos folytatás jóváhagyása (vagy más út választása) | **Tamás** | most |
| 4 | **FileVault** — 2 outage, a periódus üzemviteli terhelésének fő oka | **Tamás** | mielőbb |
| 5 | A §D3/M korlát + az UW-proveniencia mondat idézése a kapu-riportban | CC | 09-22 |
| 6 | Napi/heti/kétheti review-rutin változatlanul | CC | folyamatos |

## 6. Amit NEM javaslok

- **Nem javaslom a §3 küszöbök módosítását** — sem most, sem a kapunál. Ha a keret
  strukturálisan rossz (ahogy a 2026-05-14-i Day 63 dokumentum §7 az ELŐZŐ keretről kimondta),
  annak a felismerésnek a **kapu UTÁN**, az eredmény ismeretében, **új pre-regisztrációval**
  a helye — nem a kapu előtt, ahol a küszöb-mozgatás megkülönböztethetetlen a hangolástól.
- **Nem javaslom a UW-kódutak takarítását most** — dormant ágak, a kapu-ablak 40%-a a
  freeze-feloldás utánra esik, ott a prod-churn kockázat haszon nélkül. Kapu utáni task.
- **Nem javaslom a leállítást.** Egyetlen pre-reg leállítási feltétel sem aktivált, és a
  STOP-mean 3× egymás után javult.
