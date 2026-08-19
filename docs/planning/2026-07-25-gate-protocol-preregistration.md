Status: OPEN
Updated: 2026-08-18
Note: PRE-REGISZTRÁCIÓ — a kapu-végrehajtás rögzítése MIELŐTT az adat beérkezik. D1–D4 lezárva. 2026-08-18: a §5 kizárási lista LEZÁRVA, a §D3/M realized-only korlát rögzítve, a §9 első LEÍRÓ futás megtörtént (NEM go/no-go; a kapu 2026-09-22). 2026-08-18 (2. kör): D5 (`≥ 25` a megfigyelt napokra), D6 (kétsávos: prod fagyva 09-22-ig + revíziók SIM-ben) és §5.6 (pinelt WRAPPER, implementálva: `gate_sample.py`) MIND DÖNTVE. Nyitott: a wrapper pinelése a kapu előtt. CC nem módosít pre-reg kritériumot; ez a végrehajtás protokollja.

# Kapu-protokoll pre-regisztráció — Day 63 / Day 126

## Miért most

A napi review-k **Day 47/63**-nál tartanak, a freeze „Day 63-ig" szól — a mérföldkő
**~16 trading nap** múlva van. A kapu-végrehajtás részleteit **most kell rögzíteni**,
mert utólag, az eredmény ismeretében kritériumot vagy mintát választani pontosan az,
amit a pre-reg fegyelem tilt (a G1/§6.6 guardrail lényege).

---

## 1. A központi tisztázás: a „Day 63" a review-kban NEM a kapu

Ez a legfontosabb megállapítás, és eddig implicit maradt:

- A napi review fejlécének **„Day N/63"** egy **nap-számláló** (`daily_metrics::day_number`,
  NYSE trading nap a 2026-05-18-i swing pivot óta).
- A **pre-regisztrált döntési kritériumok** viszont a **Day 126** keretre szólnak
  (`docs/decisions/2026-05-14-day63-decision-outcome.md` §3.14) — a régi Day 63 keretet
  ugyanez a dokumentum **elavultnak** nyilvánította (§7: *„az ÉLESÍTÉS küszöb (+30% annualizált)
  strukturálisan nem realisztikus… a keret revíziója szükséges"*).

**Következmény:** a közelgő swing Day 63 (~08-17) **nem go/no-go kapu**, hanem
— javaslat szerint — a **freeze feloldásának** pontja és az **első `signal_attribution`
futás** (leíró) alkalma. A tényleges élesítési/leállítási döntés a Day 126 kereté.

## 2. Két nyitott definíciós kérdés — TAMÁS-DÖNTÉS (D1, D2)

> ## ✅ MIND A HÁROM DÖNTÉS MEGSZÜLETETT — Tamás, 2026-07-28
>
> - **D1:** a swing Day 63 (~08-17) = **freeze-feloldás + első, LEÍRÓ `signal_attribution` futás**. NEM go/no-go.
> - **D2:** a kapu **konkrét naptári dátumot** kap — **2026-09-22** —, a „Day N" címke elhagyva.
>   A kritérium-ablakok (60-napi Sharpe, 25/63 pozitív excess nap) az utolsó N **trading** napra.
> - **D3:** a **pre-reg realized-only mező marad a mérvadó**; a mark-to-market variáns diagnosztika.
>
> A §3 küszöbök (+$2 000 / Sharpe>0,5 / 25+ nap) **változatlanok** — a döntések a *definíciót* tisztázták.

### D1 — Mi történik a swing Day 63-nál (~2026-08-17)?
**✅ DÖNTÉS (Tamás, 2026-07-28): (a) freeze-feloldás + (b) első LEÍRÓ `signal_attribution` futás + (c) a
kapu előkészítése — NEM élesítési/leállítási döntés.** Indoklás: a freeze nem húzódik szeptemberig (a
scoring-revíziók elindulhatnak), és a kapu-eszköz tényleges outputját **időben látjuk**, mielőtt éles
döntés függne tőle (ha bug/adathiány van benne, nem a legrosszabb pillanatban derül ki).

Javaslat (CC): **(a) freeze feloldása** + **(b) első teljes `signal_attribution` futás,
leíró jelleggel** + **(c) a Day 126 kapu előkészítése** — de **NEM** élesítési/leállítási
döntés. Alternatíva, ha te másképp látod: a Day 63 maradjon önálló köztes kapu saját
(újra-pre-regisztrálandó) kritériumokkal.

### D2 — Dátum-bázis: a „Day 126 ≈ 2026-09-15" és a trading-nap-számolás nem egyezik
**✅ DÖNTÉS (Tamás, 2026-07-28): a kapu KONKRÉT NAPTÁRI DÁTUMOT kap — `2026-09-22` —, a „Day N" címke
elhagyva.** A kritérium-ablakok (60-napi Sharpe, 25/63 pozitív excess nap) az utolsó N **trading** napra
vonatkoznak. Indoklás: a „melyik Day 126" kétértelműség így **véglegesen megszűnik**.

A dátum kalibrációja (CC-számolás, 2026-07-28): az eredeti ~09-15 szándék + az eddigi outage-delta ~1 hét.
Adat-elégségesség: **07-28 → 09-22 ≈ 40 trading nap**, a jelenlegi 41 tényleges adatnaphoz adva
**≈ 81 tényleges nap** — a 63-as kritérium-ablakhoz bőven elég, további outage-ok mellett is.
*(Referenciaként: a 63. tényleges adatnap ~2026-08-26 — a kapu ennél lényegesen később van, szándékosan.)*

A `2026-07-01-day126-replan-proposal.md` §2.1 ezt már flagelte, és **máig nyitott**.
Az aritmetika (CC, 2026-07-25) egy valószínű magyarázatot ad — **egység-keveredés**:

| Olvasat | Számítás | Eredmény |
|---|---|---|
| Day 63 **trading** nap (a review-k számlálója) | 05-18 + 63 NYSE-nap | **~2026-08-17** |
| Day 126 **naptári** nap (az outcome doc olvasata) | 05-18 + 126 naptári nap | **~2026-09-21** (a doc „~09-15"-öt ír) |
| Day 126 **trading** nap | 05-18 + 126 NYSE-nap | ~2026-11 közepe |

A „Day 126 ≈ 09-15" tehát **naptári** számlálással konzisztens, a review-k viszont
**trading**-napot számolnak. **Ez a kétértelműség feloldandó, mielőtt a kapu esedékes.**
A kiesés-delta (07-15, 07-16, 07-22 + a 06-29→07-07 outage) **bármelyik bázisra ugyanaz**
(a kiesés *pause*, nem csökkenti a követelményt — replan §2.1).

### D4 — `mean` vagy `sum` olvasat a STOP-triggereknél?
**✅ DÖNTÉS (Tamás, 2026-08-04): a `mean` az irányadó**; a `sum` **megfigyelésként** tovább riportálódik.

**Kontextus — a döntés az első breach UTÁN született, ezért a ház-szabály hatálya alá esik**
(`ifds-rules.md`: *„Értékelő-motor fix csak pre-reg szöveghez igazításként — a pre-reg a kánon"*).
A 4 kötelező kísérő:

1. **Pre-reg forrás**: `2026-05-14 §3.14` szó szerint *„10 napi excess vs SPY **átlag** < −1,0%"* —
   az **„átlag" = mean**. A döntés a **szöveghez** igazít, nem az eredmény felé. A D4-kétértelműség
   **előre, 2026-07-25-én** rögzítve (e dokumentum §2 eredeti változata), a breach **előtt**.
2. **Érzékenység**: a 2026-08-03-i breach-nél `mean` = −0,22% vs a −1,0% küszöb (**a küszöb ~4,5×-e a
   mért értéknek → verdikt-stabil**); `sum` = −2,21% (breach). A két olvasat **érdemben eltér**, ezért a
   döntés nem kozmetikai.
3. **Regressziós védelem**: a `stop_trigger_monitor.py` **mindkét olvasatot** számolja és riportálja
   továbbra is; csak a **halt-jelzés** kötődik a `mean`-hez. A `sum` elmozdulása látható marad.
4. **Nincs újrafuttatás verdiktért**: a monitor determinisztikus, egyetlen futás/nap.

**Következmény**: a 2026-08-03-i breach **nem halt-feltétel**. A `sum`-olvasat −2,21%-os értéke
megfigyelésként rögzítve (a könyv 10 nap alatt ~2,2%-kal maradt el a SPY-tól — **MTM-mel is igazolva**,
tehát valós lemaradás, nem mérési artifact).

### D3 — Mi az „excess vs SPY" mérvadó definíciója? (a STOP-monitor építése hozta felszínre)
**✅ DÖNTÉS (Tamás, 2026-07-28): a pre-reg realized-only mező MARAD a mérvadó; a mark-to-market variáns
diagnosztikaként fut mellette.** Ha a kettő valaha **ellentétes irányba** mutat egy küszöb körül, az
**P1 jelzés Tamásnak — nem automatikus felülbírálás**. Indoklás: utólag mérőszámot cserélni ugyanaz a
hibaosztály, mint kritériumot cserélni. A `stop_trigger_monitor.py` már mindkettőt számolja.

A pre-reg kritérium „excess vs SPY"-t mond, de a `daily_metrics::excess_return` mező
**realized-only**: `portfolio_return_pct` = aznapi realizált P&L / tőke.
**Verifikálva (2026-07-25):** 07-20 realized −$438,55 / $99 901 = **−0,44%**, pontosan a mező
értéke; és a **swing-napok 38%-án** (15/39) `portfolio_return_pct = 0.0`, tehát azokon
`excess = −SPY` — a mező **indexirányt mér, nem stratégiai teljesítményt**.

| Olvasat | Definíció | Jelenlegi 10-napos átlag |
|---|---|---|
| **Realized-only** (a pre-reg mező, ahogy van) | realizált P&L / tőke − SPY | **−0,04%** |
| **Mark-to-market** (diagnosztika) | NetLiq nap/nap Δ − SPY | **−0,01%** |

Ma a kettő **egyetért** (mindkettő messze a −1,0% küszöbtől), tehát nincs gyakorlati
következménye — de ez **szerencse, nem garancia**: egy nagy nyitott-pozíció-mozgás
szétnyithatja őket. A `stop_trigger_monitor.py` **mindkettőt** számolja és riportálja.

**Javaslat (CC):** a **pre-reg mező marad a mérvadó** (realized-only) — mert az szerepel a
pre-registrációban, és utólag mérőszámot cserélni ugyanaz a hibaosztály, mint kritériumot
cserélni. A mark-to-market **diagnosztikaként** fut mellette; ha a kettő valaha
**ellentétes irányba** mutat egy küszöb körül, az önmagában P1-es jelzés Tamásnak — nem
automatikus felülbírálás. Alternatíva, ha te másképp döntesz: az MTM lesz a mérvadó, de
akkor ezt **most** kell rögzíteni, nem a kapunál.

### D3/M — MÓDSZERTANI KORLÁT (rögzítve 2026-08-18, a kapu-futás előtt)

> **Ez NEM a mérvadó mező cseréje.** A D3-döntés változatlan: a **realized-only** mező marad
> irányadó, az MTM diagnosztika. Az alábbi a mező **ismert, számszerűsített torzítása** —
> a pre-reg kritérium ettől érvényes marad, de az olvasata ezzel együtt értendő.

**A torzítás mechanizmusa.** A `daily_metrics::excess_return` `portfolio_return_pct` mezője
**realized-only**: aznapi realizált P&L / tőke. Egy **0 exites** napon ez **definíció szerint
0,00%** — tehát `excess = −SPY`. Eső tapén ez **automatikusan „felülteljesítést" mér**, akkor is,
ha a nyitott könyv aznap veszít; emelkedő tapén automatikusan lemaradást. A mező ilyen napokon
**indexirányt mér, nem stratégiai teljesítményt**.

**Számszerűsítés (swing-éra, 2026-05-18 → 08-17, `state/` ledger):**

| Mérőszám | Érték |
|---|---|
| Napok `daily_metrics`-szel | **56** (2026-08-19-ig; 9 outage-nap hiányzik) |
| Ebből **0-realizált** nap (`portfolio_return_pct = 0`) | **19 → 33,9%** |
| Napok **mindkét** olvasattal (az MTM 06-04-től él) | **44** |
| Ebből **ellentétes előjelű** | **12 → 27,3%** |
| — ebből **0-exites** | **3** |
| — ebből **volt exit** | **9** |
| \|realized − MTM\| rés | medián **0,27 pp**, átlag **0,34 pp**, max **1,20 pp** |
| 10-napos átlag (2026-08-19) | realized **−0,01%** \| MTM **−0,10%** |

> **⚠️ A mechanizmus pontosítása (2026-08-19).** A szétválás **NEM** a 0-exites napokhoz kötött:
> a 12 ellentétes-előjelű napból **csak 3** volt 0-exites, **9-en volt exit**. A 0-exit eset a
> **szélsőérték** (ott `excess ≡ −SPY`), nem a mechanizmus. Az általános ok tágabb: **a
> realized-olvasat nem látja a nyitott könyv mozgását**. Példa (2026-08-19): realized **−0,30%**
> vs MTM **+0,02%** — 1 exit mellett, mert a nyitott könyv aznap **+$326-ot javult**, miközben a
> realizált −$96,64 volt. A 2026-08-18-i daily review ezt tévesen a 0-exites napokhoz kötötte;
> a review §6-ban korrigálva.

**⚠️ Korrekció a 2026-08-17-i review-hoz.** Az ott rögzített *„a D3 szerinti ellentétes-előjelű
eset MA ELŐSZÖR áll fenn"* **nem pontos**, két okból:

1. **Ellentétes előjel korábban is volt** — 11 napon, **először 2026-06-08-án**. Ami 08-17-en
   új: a **rés nagysága** (0,85 pp) — ez a **legnagyobb ellentétes-előjelű** rés a sorozatban.
2. **A D3 P1-feltétele szigorúbb**: „ellentétes irányba mutat **egy küszöb körül**". Ez
   **soha nem állt fenn** — gördülő 10-napos átlagon a két olvasat **egyetlen ablakban sem**
   került a −1,0% küszöb ellentétes oldalára. **08-17-en sem.**

Vagyis a jelenség **szisztematikus** (a napok negyede), nem egyedi esemény — és a **pre-reg
küszöb-döntést eddig egyszer sem befolyásolta**. Ez erősebb indok a rögzítésére, mint az
anekdota volt.

**Következmény a kapura (kötelező olvasat):**
- A **„pozitív excess vs SPY napok > 25/63"** élesítési kritérium a realized-only mezőn fut.
  A 19 nulla-realizált nap kimenetele ott **mechanikusan a `−SPY` előjelére redukálódik** —
  vagyis a számláló ezen a részhalmazon **piaci irányt számol, nem stratégiai teljesítményt**.
  A kritérium **változatlanul érvényes** (pre-reg), de a kapu-riportban a **0-exites napok
  száma és azok hozzájárulása külön kimutatandó**.
- A `signal_attribution` elsődleges metrikáját ez **nem érinti**: az L1/L2 belépéstől számított
  h-napos hozamon fut, nem a napi excess-mezőn.
- A **STOP-triggereknél** a monitor mindkét olvasatot számolja és riportálja; a D3 P1-jelzés
  akkor esedékes, ha a kettő **egy küszöb körül** válik szét (eddig nem történt meg).

**Ezt a korlátot a kapu-futás riportjában szó szerint idézni kell.**

### D3/P — ADAT-PROVENIENCIA (rögzítve 2026-08-18, Tamás UW-kivezetési döntése nyomán)

A kapu-minta **GEX/dark-pool jele Polygon-forrásból** származik, nem Unusual Whales-ből.
A UW **kivezetve** (`docs/decisions/2026-08-18-uw-decommission.md`); a kulcs 2026-06-24 óta
hiányzik, a flip (04-risks §11.7) **output-invariánsnak bizonyult**. Ez a **teljes swing-érára**
igaz, tehát a minta ebből a szempontból **homogén** — **nem éra-keveredés, nem G5-sértés**.

**Ezt a mondatot is szó szerint idézni kell a kapu-riportban.**

## 3. A pre-regisztrált kritériumok (szó szerint, `2026-05-14…§3.14`) — NEM módosítható

**ÉLESÍTÉS — mind a három EGYIDEJŰLEG:**

| Kritérium | Küszöb |
|---|---|
| Kumulatív paper P&L | > **+$2,000** |
| Sharpe ratio (60 napi) | > **0.5** |
| Pozitív excess vs SPY napok | > **25 / 63 nap** (40%) |

**LEÁLLÍTÁS — bármelyik elég:**
- 10 napi excess vs SPY átlag < **−1.0%**
- VAGY 30 napi kumulatív < **−3.0%**
- VAGY 15 napi excess < **−1.0%**

**DEFAULT: PAPER FOLYTATÁS**, Day 180 újraértékelés.

### D5 ✅ DÖNTVE (Tamás, 2026-08-18) — a 3. kritérium számlálási bázisa

A „> 25 / 63 nap" szöveg **két ponton** kétértelmű volt, és a Day 63-as tény (**pontosan 25**)
mindkettőt élesre állította: `> 25`-nek nem felel meg, `≥ 25`-nek igen; a nevező pedig lehet
63 (nominális) vagy 54 (megfigyelt, a 9 outage-nap nélkül).

**✅ DÖNTÉS: `≥ 25`, a MEGFIGYELT napokra vetítve (arány-alapú, 40%).**

Indoklás: a §5 kizárási elv (az outage-napok nem számítanak bele) **már így működik a
STOP-triggereknél** — a kettő közti következetlenség önmagában hiba lenne. A küszöb **nem
változott** (a 40%-os arány a pre-reg szám); a döntés a *számlálási bázist* tisztázza,
ahogy a D1–D4 is definíciót tisztázott.

⚠️ **Rögzítve az eredmény ismeretében** — ez elfogultsági kockázat, és így is van
dokumentálva. A választás azért vállalható, mert (a) a kapunál dönteni **nagyobb** kockázat
lenne (ott a döntés már közvetlenül egy kimenetelt választ), és (b) a döntés a projekt
**máshol már alkalmazott** elvét terjeszti ki, nem újat vezet be.

**A §D3/M korlát ezen a kritériumon külön kimutatandó**: a 25 pozitív napból **5 nap 0-exites**,
ahol `excess ≡ −SPY` (piaci irány, nem stratégiai teljesítmény). Exites napokra szűkítve: **20/35**.

### D6 ✅ DÖNTVE (Tamás, 2026-08-18) — kétsávos folytatás a kapuig

**A feszültség:** a **D1** megengedte, hogy „a scoring-revíziók elindulhatnak"; a **D2** viszont
a kritérium-ablakokat az utolsó N **trading napra** tette. A 2026-09-22-vel záruló 63 napos ablak
**2026-06-24-én kezdődik**, és ebből **25 nap (40%) a freeze-feloldás UTÁNRA esik**. Prod-paraméter
változtatás most **éra-poolozná** a kapu-mintát — a G5-hibaosztály.

**✅ DÖNTÉS: KÉTSÁVOS.**
1. **A production konfiguráció FAGYVA marad 2026-09-22-ig** — a kapu-ablak homogén marad.
2. **A revíziók a meglévő SIM-infrán futnak** (`sim/rescore.py` Mode 2 re-score,
   `sim/comparison.py` párosított t-teszt, `python -m ifds compare`). A D1 szándéka így
   **maradéktalanul teljesül** — csak nem az élő számlán.
3. **A SIM-eredmények G1 szerint NEM kapu-inputok**, sem mellette, sem ellene. A SIM a
   **kapu utáni** döntés inputja.

**SIM-napirend** (a periódus adatai szerint priorizálva —
`docs/planning/2026-08-18-day63-period-summary-and-proposal.md` §4):
`max_hold`-érzékenység (az exitek **79,5%-a** itt zárul) → MENTAL_SL kalibráció (0/4 win) →
TP2-elérés (4/4 win, ritka) → végrehajtási stílus.

> Jelenlegi állás (2026-07-24, tényszerű, **előrejelzés nélkül** — G3): cumulative
> **−$423.70 (−0.42%)**. A Sharpe és a pozitív-excess-nap számláló **nincs kiszámolva**
> (lásd §4). A kapu-kimenetel előrejelzése tilos; a távolság riportálható.

## 4. ✅ P1 LEZÁRVA (2026-07-25) — a monitor élesítve

> **MEGVALÓSÍTVA** (`ad4b28b`): `scripts/analysis/stop_trigger_monitor.py` + 15 teszt
> (2182 → **2197 passing**), a v6 §5 kötelező napi sorral. **Jelenlegi állás: nincs breach**
> egyik olvasat szerint sem (10d mean −0,04%, MTM −0,01% vs a −1,0% küszöb).
> Az alábbi a feltárás eredeti leírása (megőrizve, mert a *hiba osztálya* a tanulság).

### Az eredeti hiányosság: a LEÁLLÍTÁS-triggereket SEMMI nem monitorozta

**Verifikálva (2026-07-25):** sem a `generate_review_data.py`, sem a `weekly_metrics.py`,
sem a review `flags` mezője nem számol **gördülő 10/15 napos excess-átlagot** vagy
**30 napos kumulatív drawdownt**. A daily review napi excesst ad, a heti report heti
excesst — a pre-reg trigger-ablakok egyike sem.

**Kockázat:** egy leállítási feltétel **retroaktívan** derülhet ki (hetekkel a tényleges
sérülés után) — pont az a hibaosztály, amit a projekt máshol szigorúan zár.

**Javaslat (freeze-safe, read-only, CC-task):** `stop_trigger_monitor` a napi
review-pipeline mellé (a `daily_equity` + `daily_metrics::excess_return` sorozatból):
- gördülő 10/15 napos excess-átlag + 30 napos kumulatív, **napi számolás**
- a **daily review §5 ops-checklist** kap egy kötelező sort: `STOP-triggerek: ✓ / ⚠️ <érték>`
- **kizárólag jelez**, nem cselekszik — a leállítás Tamás-döntés (human-in-the-loop)
- a kontamináció-kizárás (§5) itt is érvényes: az outage-napok nem számítanak bele

## 5. Minta-integritás — a kizárási lista ✅ **LEZÁRVA (2026-08-18)**

> **Státusz: a lista a 2026-08-18-i véglegesítéssel LEZÁRT** (§8/B). A kapu-futásig (2026-09-22)
> **csak új outage-esemény** bővítheti; minden más bővítés a kapu ELŐTT, írásban, indoklással
> történhet — a futás után **soha**. A számok a `state/` ledgerből, 2026-08-17-i (Day 63) állapot.

### 5.1 Outage-napok — **9 trading nap, 5 esemény**

Verifikálva: a `state/daily_metrics/` a swing-éra 63 trading napjából **54-et** tartalmaz;
a hiányzó 9 pontosan az alábbi lista, és a `day_number` ugrások (28→34, 39→42, 44→46, 56→58)
ezekkel **maradék nélkül egyeznek**. Nincs pipeline-esemény, nincs interpoláció.

| # | Esemény | Trading napok | day_number | Gyökérok |
|---|---|---|---|---|
| 1 | Mini SSH-orphan | 06-29, 06-30, 07-01, 07-02, 07-06 | 29–33 | orphan prod-process (07-03 ünnep) |
| 2 | Áramszünet | 07-15 | 40 | áramkimaradás |
| 3 | Áramszünet | 07-16 | 41 | áramkimaradás |
| 4 | FileVault-zárolás | 07-22 | 45 | feloldó-képernyő, ~26h |
| 5 | FileVault-zárolás | 08-07 | 57 | feloldó-képernyő, ~13h |

> ⚠️ A korábbi „5 outage-nap" megfogalmazás **5 eseményt** jelentett, nem 5 napot. A tényleges
> szám **9 trading nap**. A kapu-minta ezért 63 helyett **54 megfigyelt napra** épül.

### 5.2 Outage-késleltetett exitek — **6 pozíció, 4 esemény**

A korábbi „n=4" **eseményt** számolt; pozíció-szinten **6** tétel érintett:

| Pozíció (ticker, entry) | Exit | Esemény | Realized R | Sorsa a mintában |
|---|---|---|---|---|
| ITT (2026-07-07) | 07-15 | #2 | n/a | **már kiesik** — adathiány (kézi reconcile) |
| XPO (2026-07-07) | 07-15 | #2 | n/a | **már kiesik** — adathiány (kézi reconcile) |
| PFGC (2026-07-08) | 07-20 | #2/#3 | **−5,285%** | **§5 alapján kizárva** |
| BIRK (2026-07-08) | 07-20 | #2/#3 | **−5,213%** | **§5 alapján kizárva** |
| USFD (2026-07-14) | 07-23 | #4 | **−9,365%** | **§5 alapján kizárva** |
| DE (2026-07-30) | 08-10 | #5 | **+1,813%** | **§5 alapján kizárva** |

A kizárás oka **a végrehajtás időpontja**, nem a veszteség iránya (a DE **pozitív**, mégis kizárt).
A realizált kimenetel eddig 4/4 kedvezőtlen, de a mechanizmus **elvben kétirányú** — a 2026-08-10-i
korrekció (a 08-08-i heti zárás „a késés kedvez" állítását a hétfői kimenetel megfordította) ezt
mutatja. Indoklás: `2026-07-01-day126-replan-proposal.md` §3 D2 + 04-risks §11.10.

### 5.3 A lezárás számszerű hatása

| Minta | n | L2 h=5 Spearman (elsődleges) | L0 Spearman |
|---|---|---|---|
| Eszköz-natív (a pin, szűrés nélkül) | **43** | −0,018 CI [−0,317, +0,284] | −0,252 CI [−0,513, +0,052] |
| **§5-szűrt protokoll-minta** | **39** | −0,008 CI [−0,323, +0,308] | −0,185 CI [−0,473, +0,138] |

A §5 kizárás az **elsődleges** metrikát 0,010-del mozdítja (érdemben nem), az **L0**-t 0,067-del —
ez várt, mert a 4 kizárt tétel épp az **exit-kontaminált** ág. Az L1/L2 konstrukció szerint
**exit-független** (belépéstől számított h-napos hozam), tehát a késett exitek **elvileg is csak
az L0-t** érinthetik. Ez a §5-kizárás módszertani határa: a **kapu elsődleges metrikáját alig
mozgatja**, a realizált olvasatot viszont igen.

⚠️ **Küszöb-artefakt**: az eszköz saját `n < 40` kapuja miatt a §5-szűrt minta (n=39) a riportban
automatikusan a **„PLUMBING VALIDATION ONLY — NOT EVIDENCE"** fejlécet kapja, a nem-szűrt (n=43)
nem. A kettő közti különbség **a mintaválasztás, nem a jel** — 2026-09-22-ig a minta bővül.

### 5.4 A Day 9 clean cut jelenleg **hatástalan** (verifikálva)

`full = clean = clean_exit = 43` (és a §5-szűrt mintán 39) — mert **minden Day 9 előtti belépés
már adathiány miatt kiesik** (a 8 májusi tétel: AMH×2, CDNS, AKAM, ST, EOG, JHG, ROIV).

**Érzékenységi ellenőrzés** (a `day_number` mező ismert defektje miatt kötelező): a mező a korai
szakaszon **megbicsaklik** — 05-28, 05-29 és 06-01 **mind `day_number = 9`**, és a 8-as, 11-es
index kimarad. A határzónában (valós index 8–12) lévő betöltött tételek: WST (06-01, rögzített 9 /
valós 10), MSM (06-02, 10/11), BEN és VNO (06-03, 12/12). **Mind a négy ≥ 9 mindkét indexelés
szerint** → a clean cut tagsága **egyetlen tételnél sem fordul meg**. A cut robusztus; a defekt
a kapu-mintát nem érinti.

> Megjegyzés: a `day_number` **nem egyedi kulcs** a két éra között (a pre-pivot 1-napos éra
> 04-13…05-15 fájljai 41–65-ös számokat viselnek, ütközve a swing-éra 42–63-mal). A betöltő
> **dátum szerint** keres, ezért nincs éra-keveredés — de a mezőt kulcsként használni tilos.

### 5.5 Amit **NEM** zárunk ki (változatlan)

A self-reentry esetek (PFGC 07-21, USFD 07-23) — a stratégia normál működéséből fakadnak
(max_hold ↔ belépő-jel ellentmondás), nem külső üzemzavarból. Day 63-input megfigyelésként.

### 5.6 ✅ DÖNTVE (Tamás, 2026-08-18) — a §5 kizárás **pinelt WRAPPER**-be kerül

A pinelt `c5e9ed0` **csak adat-elérhetőségi** kizárást ismer; a §5 minta-integritási kizárás
nincs benne, miközben a §6/2 a mintát „entry-alapú clean cut **+ a §5 kizárások**"-ként
definiálja. A pre-reg a kánon → **az eszköz tér el**, nem fordítva.

**✅ DÖNTÉS: (b) dokumentált wrapper** — a pin **érintetlen** marad. Indoklás: a pin
sérthetetlensége a **G1** lényege, és a §6/2 a mintát amúgy is a **protokoll** (nem az eszköz)
hatáskörébe teszi. **Következmény:** ez **NEM értékelő-motor-módosítás** — a
`signal_attribution.py` egyetlen sora sem változik, tehát az ifds-rules 4 kötelező kísérője
(pre-reg forrás, érzékenységi ellenőrzés, regressziós teszt, nincs újrafuttatás) itt
**nem alkalmazandó**.

**Implementáció: `scripts/analysis/gate_sample.py`** (2026-08-18, 13 teszt). A wrapper:

| Garancia | Hogyan |
|---|---|
| A pin nem változhat a futás előtt (**§6/1 gépileg**) | `verify_pin()` — `git diff --quiet c5e9ed0`; eltérés → leáll |
| A §5 lista **befagyasztott adat**, nem futásidejű konfig | modul-szintű `frozenset`/tuple, protokoll-forrással |
| **Új outage nem csúszhat át némán** | `verify_outage_days()` — a deklarált lista ütköztetve a `daily_metrics` tényleges hiányával, **a data-frontierig** (nem az utolsó ismert outage-ig, különben pont a következőre lenne vak) |
| A kizárás **pozíció-kulcsú** (ticker + entry_date) | különben a 3 PFGC-tételből 3 esne ki 1 helyett — **regressziós teszt őrzi** |
| Az analízis-kód **nem másolódik** | a pinelt függvények **importálva** hívódnak |
| Read-only | a trading state-be nem ír |

**Verifikálva:** a wrapper a 2026-08-18-i ad-hoc futás számait **pontosan** reprodukálja —
n=39, L2 Spearman h=5 **ρ=−0,008 CI [−0,323, +0,308]**.

**A wrapper pinje: `68fc00e`** (2026-08-18) — ugyanaz a fegyelem, mint a `c5e9ed0`-nál.

⚠️ **Tervezési következmény, tudatosan vállalva:** a §5 lista **növekvő adat**, de a pinelt
**kódban** él — tehát **minden új outage `gate_sample.py` módosítást és ÚJ PINT kíván**.
Ez szándékos: így minden minta-változás **külön commit + indoklás**, vagyis folyamatos
audit-nyom keletkezik, nem egyetlen, utolsó pillanatban felvett pin.

**Szabály:** ha 2026-09-22 előtt új outage történik → (1) a §5.1 lista frissül,
(2) `gate_sample.py` frissül, (3) **az új pin és az ok ide + a 04-risks-be kerül a futás
ELŐTT**. A `verify_outage_days()` gondoskodik róla, hogy ez ne maradjon el némán: a wrapper
**leáll**, ha a deklarált lista és a tényleges állapot eltér.

## 6. A kapu-futás végrehajtási protokolja

1. **Eszköz**: `scripts/analysis/signal_attribution.py`, **pinned `c5e9ed0`** — az
   EGYETLEN kapu-input (G1). A pin nem változhat a futás előtt; ha változna, az
   új pin és az ok a 04-risks-be kerül a futás ELŐTT.
2. **Minta**: entry-alapú clean cut + a §5 kizárások. A `n` (included/excluded) a riport
   első sora.
3. **Sorrend**: előbb a minta-definíció és a kizárások fixálása → **utána** a futtatás.
   A futás után a mintán nem módosítunk.
4. **Output**: `docs/analysis/` (rsync territory) + a döntési rekord a
   `docs/decisions/`-be, a §3 kritériumok melletti tényszerű állással.
5. **Kettős futás tilos**: egyetlen futás, egyetlen riport. Ha technikai hiba miatt
   újra kell futtatni, az ok dokumentálandó (a „amíg jó nem jön ki" ellen).

## 7. Inadmissibilis a kapuba (G1, mindkét irányban)

- **Minden FRL-output** — a HYP-004 KILL, a HYP-005 PARK, az IC-becslések, a cost-model:
  **ÖRÖKRE leíró**. Sem pro, sem kontra nem idézhető a kapu-deliberációban.
- A napi/heti review-k **leíró** megfigyelései (slippage-sorozat, self-reentry n, excess-napok)
  — kontextus, nem kapu-input. A kapu-inputot kizárólag a §6/1 eszköz állítja elő.
- A `scoring_validation.py` biweekly riport — leíró, és jelenleg **éra-poolozott**
  (G5-sértés, ismert nyitott tétel), tehát végképp nem kapu-input.

## 8. Következő lépések

| # | Tétel | Kié | Mikor | Státusz |
|---|---|---|---|---|
| D1 | Mi a swing Day 63 | Tamás | — | ✅ **freeze-feloldás + leíró futás** (2026-07-28) |
| D2 | Dátum-bázis | Tamás | — | ✅ **konkrét dátum: 2026-09-22**, „Day N" elhagyva (2026-07-28) |
| D3 | Az excess mérvadó definíciója | Tamás | — | ✅ **realized-only marad**, MTM diagnosztika (2026-07-28) |
| D4 | `mean` vagy `sum` olvasat a STOP-triggereknél | Tamás | — | ✅ **`mean` az irányadó** (a pre-reg „átlag" szó szerint); `sum` megfigyelés (2026-08-04) |
| P1 | STOP-trigger monitor (§4) | CC | — | ✅ **KÉSZ** (`ad4b28b`, 2026-07-25) |
| **A** | **Day 63 esemény**: freeze-feloldás + az ELSŐ leíró `signal_attribution` futás | CC | 08-17 / 08-18 | ✅ **KÉSZ** (freeze 08-17, leíró futás **2026-08-18**, §9) |
| **B** | A kizárási lista véglegesítése (a §5 lista zárása a kapu-futás előtt) | CC + Tamás | 2026-09-22 előtt | ✅ **LEZÁRVA** (2026-08-18, §5) — csak új outage bővítheti |
| **C** | Kapu-futás: `signal_attribution` (pinned `c5e9ed0`), egyszeri, a §6 protokoll szerint | CC | **2026-09-22** | 📋 nyitott |
| **D** | §5-mechanizmus döntés (újra-pinelés vs. pinelt wrapper, §5.6) | Tamás | — | ✅ **WRAPPER** (2026-08-18); implementálva: `gate_sample.py`, 13 teszt |
| **D'** | A `gate_sample.py` pinelése | CC | — | ✅ **pin: `68fc00e`** (2026-08-18); új outage → új pin + ok, a futás ELŐTT |
| **E** | A D3/M korlát + az UW-proveniencia mondat idézése a kapu-riportban | CC | 2026-09-22 | 📋 nyitott |
| **D5** | A 3. kritérium számlálási bázisa | Tamás | — | ✅ **`≥ 25`, megfigyelt napokra (40%)** (2026-08-18) |
| **D6** | A paraméter-revíziók útja a kapu-ablakban (D1↔D2 feszültség) | Tamás | — | ✅ **KÉTSÁVOS** — prod fagyva 09-22-ig + revíziók SIM-ben (2026-08-18) |

**Ez a dokumentum a pre-regisztráció.** A §3 kritériumok nem módosíthatók; a D1/D2
döntés a *definíciót* tisztázza, nem a küszöböket. Minden későbbi változtatás
dátummal és indoklással ide kerül.

---

## 9. Az ELSŐ, LEÍRÓ `signal_attribution` futás — 2026-08-18

> ⚠️ **EZ NEM A KAPU-FUTÁS, ÉS NEM GO/NO-GO.** A kapu **2026-09-22** (D2). **G3: jel-érvényességi
> nyelv tilos** a kapu-futásig — az alábbi **kizárólag leíró**. Az „irány" itt **nem** jelent
> bizonyítékot sem mellette, sem ellene: a minta a saját eszköz-küszöb (n≥40) és a pre-reg
> power-küszöb (|ρ|≈0,36–0,38 detektálható) alatt vagy annak határán van.

**Futás.** Eszköz: `scripts/analysis/signal_attribution.py`, **pin `c5e9ed0` — verifikálva
változatlan** (`git diff c5e9ed0 -- <fájl>` üres a futás pillanatában). Read-only; a trading
state-be nem írt. Forward-hozamok: Polygon napi bar-ok.
Output (rsync-terület, `docs/analysis/`, nem tracked):
`signal-attribution-2026-08-18-{full,clean,clean_exit}.md` + `-protocol-s5.md`.

**Minta.** Zárt, pozíció-szintű swing trade-ek Day 1–63-ból. Betöltve 43, adat-elérhetőségi
kizárás 10 (8 májusi hiányzó leg-P&L + ITT/XPO kézi reconcile). A §5 kizárás további 4 tételt
vesz ki → **n=39**. A `full`/`clean`/`clean_exit` **azonos** (§5.4).

| Metrika | Eszköz-natív n=43 | §5-protokoll-minta n=39 |
|---|---|---|
| **L2 sector-relative Spearman, h=5** (elsődleges) | **−0,018** CI [−0,317, +0,284] | **−0,008** CI [−0,323, +0,308] |
| L2 Spearman h=1 | +0,097 CI [−0,210, +0,386] | +0,016 CI [−0,301, +0,330] |
| L2 Spearman h=3 | −0,016 CI [−0,314, +0,286] | −0,074 CI [−0,380, +0,248] |
| L1 (exit-izolált) Spearman h=5 | −0,335 CI [−0,577, **−0,038**] | −0,292 CI [−0,556, +0,026] |
| L0 realizált Spearman | −0,252 CI [−0,513, +0,052] | −0,185 CI [−0,473, +0,138] |
| L0 realizált Pearson | −0,219 CI [−0,487, +0,087] | −0,181 CI [−0,470, +0,143] |

**Tényszerű megállapítások (következtetés nélkül):**
- Az **elsődleges metrika CI-je mindkét mintán tartalmazza a 0-t**; a pontbecslés mindkettőn
  |ρ| < 0,02, azaz a detektálható effektus-méret **egy nagyságrenddel** alatta.
- **Egyetlen** CI zárja ki a 0-t: az **L1 h=5 a nem-szűrt mintán** (−0,335, felső határ −0,038).
  A §5-szűrt mintán **ugyanez a CI már tartalmazza a 0-t** (+0,026). Egy nominális 95%-os CI
  6 horizont-metrikából — **többszörös-tesztelési korrekció nélkül**; és a két minta ellentétes
  eredménye maga mutatja az instabilitást. **Ebből semmilyen jel-állítás nem vonható le** (G3).
- A §5 kizárás az elsődleges metrikán **0,010**-et mozdít, az L0-n **0,067**-et (§5.3).
- A **kizárás iránya nem „szépíti" a képet**: a 4 kizárt tétel realizált hozama −5,3% / −5,2% /
  −9,4% / **+1,8%** — a kivételük az **L0-t emeli** (−0,252 → −0,185). Ezt a futás előtt
  rögzített §5 diktálta, nem az eredmény.

**Protokoll-megfelelés:** §6/1 pin ✓ | §6/2 minta+kizárások a riport elején ✓ | §6/3 a minta
**a futás előtt** fixálva (§5 lezárás 08-18) ✓ | §6/4 output `docs/analysis/` ✓ | §6/5 kettős
futás — **a kapu-futás továbbra is egyszeri lesz**; a mai leíró futás a §8/A tétel, nem a kapu ✓.

**Nyitva marad a kapuig:** a §5.6 mechanizmus-döntés (D tétel) és a §D3/M korlát riport-idézése.
