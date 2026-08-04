Status: OPEN
Updated: 2026-07-25
Note: PRE-REGISZTRÁCIÓ — a kapu-végrehajtás rögzítése MIELŐTT az adat beérkezik. Két Tamás-döntést kér (D1 definíció, D2 dátum-bázis) + egy P1 hiányosságot jelez (nem monitorozott STOP-triggerek). CC nem módosít pre-reg kritériumot; ez a végrehajtás protokollja.

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

## 5. Minta-integritás — a kizárási lista (rögzített, bővíthető)

A kapu-futás **kizárja**:
- **Outage-napok**: 06-29→07-07 (Mini SSH-orphan), **07-15, 07-16** (áramszünet),
  **07-22** (FileVault-zárolás) — nincs pipeline-esemény.
- **Outage-késleltetett exitek (n=3)**: ITT/XPO (07-15), PFGC/BIRK (07-20), USFD (07-23)
  — a stratégia szándéka szerinti időpontnál 2 nappal később, mérhetően rosszabbul zártak
  (§11.10; az USFD-nél ~−$91 a becsléshez képest).
- Indoklás: `docs/planning/2026-07-01-day126-replan-proposal.md` §3 D2 (pause-and-resume,
  gate criteria UNCHANGED) + 04-risks §11.10.

**Nem zárjuk ki** (tényszerűen rögzítve, de a minta része): a self-reentry esetek
(PFGC 07-21, USFD 07-23) — ezek a stratégia normál működéséből fakadnak (max_hold ↔
belépő-jel ellentmondás), nem külső üzemzavarból. Day 63-input megfigyelésként.

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
| **A** | **Day 63 (~08-17) esemény**: freeze-feloldás + az ELSŐ leíró `signal_attribution` futás | CC | **~08-17** | 📋 nyitott |
| **B** | A kizárási lista véglegesítése (a §5 lista zárása a kapu-futás előtt) | CC + Tamás | **2026-09-22 előtt** | 📋 nyitott |
| **C** | Kapu-futás: `signal_attribution` (pinned `c5e9ed0`), egyszeri, a §6 protokoll szerint | CC | **2026-09-22** | 📋 nyitott |

**Ez a dokumentum a pre-regisztráció.** A §3 kritériumok nem módosíthatók; a D1/D2
döntés a *definíciót* tisztázza, nem a küszöböket. Minden későbbi változtatás
dátummal és indoklással ide kerül.
