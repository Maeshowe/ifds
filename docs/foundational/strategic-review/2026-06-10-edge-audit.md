# IFDS Edge Audit — Production-Readiness Döntési Dokumentum

**Dátum**: 2026-06-10 (szerda) — swing pivot Day 17 záró / Day 18 reggel
**Verzió**: 1.2 (2026-06-10 — v1.1: forrás-korrekció, institutional research megtalálva; v1.2: a CC-review 4 gap-jének átvezetése — jel-izoláló attribúció [L0/L1/L2], adatköltség-trim előrehozás Day 21-re, W23 súlyozás-korrekció, MID-függőség pontosítás. Kizárólag szigorító/pontosító irány; changelog a dokumentum végén.) — REFERENCIA-DOKUMENTUM, a Day 63 (≈2026-08, W31) és Day 126 (≈2026-09-15, W37) kiértékelés rögzített viszonyítási pontja
**Készítette**: Chat (Claude), Tamás (Product Owner) megbízásából
**Jelleg**: kritikus, döntés-szintű audit — NEM scoring-javítási javaslatgyűjtemény
**Forrásbázis**: `CLAUDE.md`, `docs/STATUS.md`, `docs/decisions/2026-05-14-day63-decision-outcome.md`, `docs/foundational/strategic-review/2026-05-08-*` (summary + full + mathematical), `docs/master-reference/04-risks-and-open-questions.md`, `docs/planning/backlog.md`, napi review-k Day 1–17 (kiemelten `docs/review/2026-06-09-daily-review.md`)
**Kiegészítő forrás (v1.1)**: a 2026-05-22-es Bridgewater/Jane Street institutional research **megtalálva**: `~/SSH-Services/pandoc/2026-05-22-bridgewater-janestreet-research.md` (a repón KÍVÜL él; szinkronizálandó ide: `docs/foundational/strategic-review/`). Tartalma a §3.b routing-ot **függetlenül megerősíti** — a szintézise (§11.4) explicit: a modern intézményi methodology-k tanulsága regime/sizing overlay, NEM új scoring-komponens. Deploy-érintő action itemjei (A2 HRP-sizing, A4 entry-timing A/B, A5 continuous vol-scaling) a jelen dokumentum §4.2/1 parameter freeze-e alá esnek Day 63-ig — design-munka mehet, deploy nem.

---

## 0. Verdikt egy bekezdésben

Az IFDS ma egy **mérnökileg production-grade hordozó, amelyben egy statisztikailag még igazolatlan jel fut** — és ez a kombináció **pontosan ott van, ahol Day 17-en lennie kell**. A legacy rendszer halála kvantitatívan lezárt tény (Pearson ρ≈0, Kelly f* negatív minden számítási módon, 19–21% éves súrlódás), a swing pivot pedig egy **futó, jól megtervezett out-of-sample kísérlet**, amelynek a kimenete ma még nem tudható — a jelenlegi +$767 cumulative és a 57%-os TP-hit ráta biztató, de n=14 exit statisztikailag **semmire nem elég**. A mai napon egyetlen védhető döntés létezik: **a kísérlet érintetlen végigvitele paraméter-freeze mellett**, kiegészítve az ebben a dokumentumban MOST rögzített attribúciós teszttel és kill-kritériumokkal. A legnagyobb kockázat nem az, hogy nincs edge — az időben kiderül és olcsó. A legnagyobb kockázat az, hogy **menet közbeni beavatkozásokkal vagy utólagos kapu-mozgatással tönkretesszük a kísérlet bizonyító erejét**, és Day 126-on megint nem tudjuk, mit mértünk.

---

## 1. Diagnózis — hol áll a rendszer a „mérnökileg kész / statisztikailag igazolatlan" térképen

### 1.1 A pozíció

A két tengely szándékosan független, és a rendszer a két tengelyen **extrém aszimmetrikus** helyen áll:

- **Engineering tengely**: a sole-operator kategória felső sávja. 1926 passing teszt, broker-authoritative P&L-lánc (Part A `ib.fills()` 0 fallback, Option B, restatement-tooling), 11/11 éles reconcile SILENT OK (23 trading napi tiszta mental-stop futás), autonóm submit-retry orchestrator, context-freshness guard, NYSE-naptár-korrekt day-count, VIX Polygon I:VIX, automatizálódó review-pipeline. A Day 1–17 alatt felmerült összes operatív bug (days_held calendar-bug, ATR floor/ceiling, stale context, P&L tracking gap) **azonosítva, javítva, élesen verifikálva**. Egy intézményi ops-due-diligence ezen a rétegen ma átmenne.
- **Statisztikai tengely**: a nullpont és az első detektálható jel között. A legacy 63 nap **bizonyított null** (erős evidencia |ρ_true| < 0.10-re, n=378). A swing horizonton a jel léte **hipotézis**, amelynek tesztje Day 17/63-nál tart, és a minta első 8 napja bug-torzított.

**Az aszimmetria stratégiai következménye**: a további mérnöki munka határhaszna mára alacsony — a szűk keresztmetszet nem kód, hanem **naptári idő** (adat-akkumuláció). Minden óra, amit most infrastruktúrára költesz a bugfixen és a review-automatizáción túl, a rossz tengelyen dolgozik.

### 1.2 Erős / Gyenge / Halott mátrix

| Réteg | Státusz | Evidencia | Megjegyzés |
|---|---|---|---|
| Execution + ops infra (cron, IBKR, retry, reconcile) | **ERŐS** | 23 napi tiszta futás, 11/11 silent OK, orchestrator | Production-grade; ez a projekt **valódi, átvihető asset-je** |
| Mérés / tracking (broker-authoritative P&L) | **ERŐS** | fix-package #1–#6 + recorder-robust élesen verifikálva Day 16–17 | A Day 8-i $819-os tracking-szakadék típusa strukturálisan lezárt |
| Folyamat-fegyelem (pre-regisztrált kapuk, dokumentáció, permanent record) | **ERŐS** | Day 63 keret betartva, döntési docok, review-prognózis vs tény tracking | Ritka erény hobbiprojektben — ez az önámítás elleni fő védvonal |
| Daily-eval exit-architektúra (mental stop, time-stop) | **ERŐS-ÍGÉRETES** | 8/9 fordulat-nyertes (WST +$262 felülteljesítés); bracket-bug osztály eliminálva | A 8/9 kis minta, de a *mechanizmus* (gap-rezisztencia, nincs intraday whipsaw) strukturális |
| Sector-balanced greedy + sizing (0.35%, ATR-sáv) | **ERŐS-ÍGÉRETES** | MASI 8 nap top-S_j, 0 boomerang; koncentráció-capek élesek | Egyszerű, átlátható, kevés szabad paraméter |
| **A jel maga (PCR + OTM-inverz a swing horizonton)** | **IGAZOLATLAN** | n=14 exit, 17 nap, ebből 8 bug-torzított | **Ez az egyetlen kérdés, ami számít** — minden más réteg ezt szolgálja |
| Entry timing (15:30 CEST) | **GYENGE (igazolatlan)** | A Fázis 2 entry-timing backtest (P2.1) **nem készült el** — érveléssel választott paraméter | Nem blokkoló, de a Day 63 olvasatnál tudni kell: ez nem validált |
| Next-day MKT fill mechanika (TP1/TP2 flag → másnapi market) | **GYENGE (vegyes)** | 4 minta: 2 kedvező / 2 kedvezőtlen, átlag −0.53% | Backlog #7 helyesen Day 21+ adatra vár — ne nyúlj hozzá addig |
| Legacy kompozit scoring, multiplier chain, BMI-rezsim | **HALOTT** | ρ≈0; M_VIX/M_GEX/BMI degenerált a teljes mintán | Lezárt, dokumentált — ne térj vissza hozzá |
| UW dark pool / GEX a scoringban | **HALOTT (shadow-ban)** | dp_pct ρ=−0.265 alulvizsgált, 95% CI [−0.486, −0.012] | Day 90 audit (n≈150–180) dönt — a shadow-first elv helyes |
| IBKR bracket architektúra | **HALOTT** | 4 strukturális bug-instancia 13 nap alatt | A mental stop strukturálisan eliminálta — visszaút nincs |

### 1.3 A súrlódás-oldal: a pivot egyetlen MÁR BIZONYÍTOTT nyeresége

A legacy 19–21%-os éves súrlódás-terhe három komponensből állt: commission ~8.4%, slippage ~3–5%, adat ~8%. A swing pivot a turnover-t kb. ötödére vágta — a Day 17-i teljes napi commission **$2.21** volt $409 realized mellett. Éves szinten a commission-drag becsült ~0.5–1%-ra esett, a slippage az entry-oldalon megmaradt (±0.3–0.7%/pozíció, de ötödannyi pozíción). **A domináns drag mostantól az adatköltség**: $665/hó = ~$8,000/év = 8.0% a $100k papír-tőkén. A break-even bruttó alpha-cél így ~19–21%-ról **~9–10%-ra esett** ($100k-n), és tőke-skálázással tovább esik (lásd §5.2). **Ez a pivot legbiztosabb hozadéka, és teljesen független attól, hogy a jel működik-e.** Érdemes így gondolni rá: a pivot a játék megnyerhetőségét állította helyre; hogy meg is nyerjük-e, az a jel kérdése.

---

## 2. A swing tézis epistemológiai státusza — mi bizonyított, mi hipotézis, mi torzít

Ez a szakasz az audit magja, mert a Day 63/126 olvasatnál itt fog eldőlni, hogy önámítunk-e.

### 2.1 Bizonyított (magas konfidencia, lezárt)

1. **A legacy intraday rendszernek nincs detektálható edge-e** — ρ(S,R) ≈ 0, n=378, a 80%-os power-küszöb |ρ|=0.144 fölött semmi. Erős evidencia a |ρ_true| < 0.10 tartományra.
2. **A legacy rendszer negatív expectancy-jű** — Kelly f* = −0.23 (konzervatív) / −0.46 (default), számítási módra robusztusan.
3. **A bracket-architektúra strukturálisan hibás volt** — 4 duplikált-zárás-instancia 13 nap alatt, nem patchelhető osztály.
4. **A súrlódás-kollapszus megtörtént** — mérhető, nem zaj (§1.3).

### 2.2 Hipotézis (a futó kísérlet tárgya — NEM tény)

1. **PCR + OTM-inverz prediktív a 3–5 napos horizonton.** Kritikus őszinteségi pont: a két komponens a 232-trade-es **intraday** mintán lett kiválasztva, Bonferroni-korrekcióval — ami védi a within-sample multiple-testing ellen, de **nem védi a selection effect ellen**: ugyanazon az adaton választottuk ki a komponenseket, amelyik a pivotot motiválta (Bailey–López de Prado 2014, Harvey–Liu–Zhu 2016 pontosan erről szól). A swing futás **az első valódi out-of-sample teszt**. Amíg le nem fut, a „Bonferroni-szignifikáns minimum" címke a *módszertan* minőségét igazolja, nem a jel létét.
2. **Az 5× mutual information állítás.** A mathematical doc 5.2 maga kvalifikálja: az $I \propto h\rho^2$ linearizált martingál-modell, ami figyelmen kívül hagyja a jel mean-reversion-jét és a noise-variancia $h$-val való növekedését. **Ez a pivot-érvelés leggyengébb láncszeme** — és nem is kell rá támaszkodni, mert a pivot olcsóbb, erősebb érvei (súrlódás-kollapszus, bug-osztály eliminálás, multi-day play-out lehetőség) önmagukban elegendőek voltak. Javaslat: a Day 63/126 kommunikációban az „5×" számot ne kezeld predikcióként, csak motivációként.
3. **A 15:30 entry optimális.** A tervezett backtest (Fázis 2, P2.1) nem készült el — érvelt, nem validált paraméter.

### 2.3 A jelenlegi 17 napos minta ismert torzításai

1. **Day 1–8 bug-torzított** — calendar-day TIME_STOP (−$479 közvetlen kár), stale context entry-k, ATR-floor hiánya, P&L tracking gap. A −$779 mélypont nem a tervezett rendszer teljesítménye. Ugyanakkor: a Day 9–17 felfutás részben e bugfixek *utáni* tiszta architektúra terméke — a két irányú torzítást a §4.2/2 pre-regisztrált kettős elemzés kezeli.
2. **n=14 exit, ~52 várható Day 63-ig** — a TP-hit ráta 57.1% vs legacy 9.5% látványos, de a 95% CI egy 14-elemű mintán ±26 százalékpont. Irány, nem bizonyíték.
3. **Kedvező piaci szakasz**: a Day 16–17 bull-rebound napokra esett. A legtöbbet érő adatpont ezzel szemben a W23: **+3.39% excess egy −2.58% SPY / VIX +39.7% major risk-off héten** — de (v1.2 korrekció) ez is **egyetlen rezsim-epizód (n=1)**, amely részben szektor-kompozíciós szerencse lehet (a könyv defenzív szektorokban állt). Helyes súlya: **egy a több szükséges feltétel közül**, nem perdöntő karakter-bizonyíték. A stock-attribúció ezt önmagában nem oldja fel (szelekciós ρ-t mér, nem regime-timinget); az L2 szektor-reziduális elemzés (§4.2/3) utólag részben tesztelhetővé teszi, de regime-evidenciát csak több risk-off epizód adhat.
4. **Narratív momentum a review-kban.** A Day 17 review ⭐⭐⭐-jelölései és „rekord"-framingje érthetők, de a Day 63 olvasatnál pszichológiai kockázat: az eufórikus napi narratíva hajlamosít a kapu utólagos jóindulatú értelmezésére. Védelem: a Day 63 kiértékelés **script-alapú** legyen (mint a HRP GO/NO-GO design-ban), és ez a dokumentum a rögzített referencia.

### 2.4 Ami a 17 napból ennek ellenére informatív

A kis-n fenntartás mellett három dolog már most jelez: (1) a **mechanikai integritás** — 23 tiszta trading nap, 0 strukturális incidens az új architektúrán; (2) a **költség-modell beigazolódása** — a turnover- és commission-kollapszus a tervek szerint; (3) a **karakter-konzisztencia** — a low-beta defenzív profil (W23) és a daily-eval fordulat-statisztika (8/9) az architektúra *szándékolt* viselkedését mutatja. Ezek szükséges, de nem elégséges feltételei az edge-nek.

---

## 3. Három forgatókönyv becsületes összevetése

**Keretező megjegyzés, ami az egész szakaszt meghatározza**: a három forgatókönyv NEM mai választási lehetőség, hanem **szekvenciális kapuk rendszere**. Ma, Day 17-en, egyetlen védhető akció van — az (a) —, mert a (b) vagy (c) menet közbeni indítása megsemmisítené a futó kísérlet bizonyító erejét, és visszavinne a „garden of forking paths" csapdájába, amiből a Day 63 outcome doc épp kivezetett. Az audit feladata nem a választás, hanem **a routing-feltételek MOSTANI rögzítése**: milyen Day 63/126 evidencia visz az (a) folytatásába, melyik a (b)-be, melyik a (c)-be.

### 3.a — A swing pivot végigvitele a jelenlegi terv szerint

**Karakter**: a futó kísérlet érintetlen befejezése Day 63-ig, majd Day 126-ig, a Day 63 outcome doc 14 döntése és e dokumentum §4 kiegészítései szerint.

**Mit kellene látnunk, hogy ezt válasszuk**: semmit — **ez a default**, és csak a már rögzített LEÁLLÍTÁS-triggerek (10 napi excess < −1.0%, 30 napi kumulatív < −3.0%, 15 napi excess < −1.0%) szakíthatják meg. A Day 21 checkpoint (−$1,500 küszöb) Day 17-en 151% bufferben.

**Erősségek**: az egyetlen út, ami tiszta out-of-sample evidenciát termel; a kill-kritériumok előre rögzítettek; a költség-oldal már igazolt. **Gyengeségek**: ha a jel halott, ezt leghamarabb Day 63-on (irányjelzés) / Day 126-on (első érdemi power) tudjuk meg — a naptári idő nem rövidíthető. **Kockázat**: a legnagyobb kockázata éppen a menet közbeni „jobbítás" kísértése (lásd §6).

### 3.b — Részleges újratervezés: melyik réteg?

A rétegenkénti elimináció egyértelmű választ ad. Execution/ops: erős, nem kandidát. Mérés: erős, nem kandidát. Sizing/risk: egyszerű, élesen működik, nem kandidát. Horizon: most váltottunk, újra váltani adat nélkül értelmetlen. **Egyetlen réteg marad, ahol részleges újratervezésnek értelme van: a jel-réteg — és ott is egy konkrét, már előkészített irány: a MID regime-overlay.**

A logika az 50/30/20 keretből jön: a hozamok ~50%-át a piaci irány, ~30%-át a szektor-szelekció, ~20%-át a stock picking hajtja. A jelenlegi swing scoring a 20%-os komponensben keres edge-et (PCR + OTM-inverz stock-szinten), a szektor-rotáció a 30%-osban dolgozik — **az 50%-os komponens (piaci irány / regime) lefedetlen**, miközben a MID Bundle shadow 2026-04-27 óta gyűjti pontosan ezt az adatot. A legnagyobb elméleti hozam-javulás itt van, és a shadow-first elv szerint az integráció előkészítése már fut.

**Mit kellene látnunk, hogy ezt válasszuk (routing-feltétel, MOST rögzítve, v1.2-ben pontosítva)**: Day 126-on a kumulatív P&L **pozitív vagy null-közeli**, DE a jel-izolált attribúciós teszt (§4.2/3, L2 szektor-reziduális szint) azt mutatja, hogy a hozam NEM a stock-szelekcióból jön — azaz az L2 ρ ≈ 0 a swing mintán, miközben a portfolió-szintű eredmény él. Ez azt jelentené: a hordozó + a kockázatkezelés + a szektor-réteg termel, a stock-jel nem — és akkor a következő iteráció a regime-réteg (MID → sizing/expozíció), NEM újabb stock-indikátor. Ez konzisztens a „nem szaporítunk indikátort" elveddel: a MID-overlay nem új jel a meglévő mellé, hanem a hiányzó 50%-os komponens.

**Függőség-pontosítás (v1.2)**: a MID **önálló, aktívan fejlesztett adatforrás-projekt (API)** — a mathtech ebből fogyaszt, és az IFDS (b)-ága is így tenné. A függőség tehát **a MID API stabilitása/elérhetősége**, nem a MID belső fejlesztése. A (b) kapu előfeltétele ezért egy **MID API readiness-audit** a Day 126 döntés inputjaként: a shadow-időszak (2026-04-27 óta gyűlő MID Bundle adat) uptime-, adatminőség- és lefedettség-ellenőrzése — meglévő adaton, új munka nélkül. Ha a readiness-audit negatív, a (b) ág nem indítható, akkor sem, ha a routing-evidencia megvan.

**Megjegyzés (v1.2-ben frissítve)**: a Lab institutional-methodology kutatás (2026-05-22, megtalálva: `~/SSH-Services/pandoc/`) konklúziója a §3.b routing-ot függetlenül megerősíti — regime/sizing overlay, nem új scoring-komponens. A doc szinkronizálandó az IFDS repóba a Day 126 kapu előtt, hogy a kapu-döntésnél kéznél legyen.

### 3.c — Stratégiai pivot: a pipeline mint hordozó, más jelforrással

**Karakter**: annak elismerése, hogy a flow-alapú stock-szelekciós jel (PCR/OTM-családdal) ebben a formában nem termel edge-et, és a projekt valódi asset-je — a production-grade hordozó (execution, risk, tracking, automation) — más jelforrást kap. Kandidátok (priorizálás a Lab-kutatás dolga, NEM ezé a dokué): MID-regime mint elsődleges jel (timing/expozíció-vezérlés stock-picking nélkül, pl. szektor-ETF rotáció a meglévő Phase 3 logikára építve); vagy a Lab-ból érkező, előre regisztrált egyetlen új jel-család. Szigorú szabály: **egyszerre egy jel-család, pre-regisztrált validációs tervvel** — a 7-komponensű flow-score hígulási hibáját nem ismételjük meg.

**Mit kellene látnunk, hogy ezt válasszuk (routing-feltétel)**: (i) Day 126-on LEÁLLÍTÁS-trigger aktivál, VAGY (ii) Day 180-ig sem a kumulatív P&L, sem az attribúció nem mutat életjelet (§4.2/6 globális kill). Ekkor a PCR/OTM-családú jelkeresés **ebben a formában lezárul**, és a graceful-exit doktrína lép életbe: a hordozó megőrzése, a tanulságok rögzítése, a MID önálló értéke, és a Lab dönt a következő jel-családról vagy a hobbi-státuszról.

**Erőssége**: a sunk-cost-mentes gondolkodás intézményesítése. **Gyengesége**: minden új jel-család új 63–126 napos validációs ciklus — a naptári költség magas, ezért csak kimerített (a)/(b) után racionális.

### 3.4 Összevető mátrix

| Szempont | (a) Végigvitel | (b) Jel-réteg + MID overlay | (c) Pivot más jelforrásra |
|---|---|---|---|
| Mikor aktuális | **MOST (default)** | Day 126 kapu | Day 126 LEÁLLÍTÁS vagy Day 180 null |
| Evidencia-igény | nincs (fut) | P&L pozitív + stock-attribúció null | P&L negatív + attribúció null |
| Naptári költség | 0 (már fut) | +63–126 nap új futás | +126–189 nap |
| Mit kockáztat | menet közbeni tinkering | a futó kísérlet, ha korán indul | semmit, ha tényleg kimerült (a)+(b) |
| Sole-operator teher | alacsony (automatizált) | közepes (MID-integráció ~10–20h) | magas (új jel + új validáció) |
| Önámítás-kockázat | kapu-mozgatás | „mégis volt edge, csak..." narratíva | sunk cost tagadása |

---

## 4. Validációs terv — előre rögzített kill-kritériumokkal

### 4.1 Ami már rögzített, és amihez NEM nyúlunk

A Day 63 outcome doc 14. döntése a Day 126 keretet előre rögzítette, és ez a dokumentum **megerősíti, változtatás nélkül**:

| Kapu | ÉLESÍTÉS (mindhárom együtt) | LEÁLLÍTÁS (bármelyik) | DEFAULT |
|---|---|---|---|
| **Day 126** (≈2026-09-15) | kumulatív > +$2,000 ÉS Sharpe₆₃ > 0.5 ÉS 25+ pozitív excess-nap /63 | 10 napi excess átlag < −1.0% VAGY 30 napi kum. < −3.0% VAGY 15 napi excess < −1.0% | PAPER FOLYTATÁS → Day 180 |

Köztes pont: **Day 21 checkpoint** (−$1,500 küszöb) — már él, Day 17-en 151% buffer.

### 4.2 Amit MOST, Day 17-en rögzítünk (az adat felhalmozódása ELŐTT)

Ezek kiegészítések, nem módosítások — szigorító irányban pre-regisztrálni az adat előtt legitim; lazítani utólag nem lenne az.

**1. Parameter freeze (Day 18 → Day 63).** A scoring-, sizing-, exit- és universum-paraméterek (S_j küszöb, 0.35% risk, ATR-sáv 0.5–5%, TP1/TP2/stop szorzók, time-stop 5 trading nap, sector cap 30%, max 12 concurrent, 15:30 entry) **befagyasztva**. Kivétel kizárólag: bugfix, amely a *dokumentált tervezett viselkedést* állítja helyre (mint a days_held vagy az ATR-floor volt) — minden ilyen fix külön logolva a `04-risks`-ben, a Day 63 kiértékelés mellékleteként. Display/tracking-fix (pl. a §5.1 Telegram-render) szabadon mehet, mert a kereskedési viselkedést nem érinti. A Backlog #7 (TP1-limit) és #8 (TIME_STOP-elhalasztás) **Day 63-ig csak adatgyűjtés, deploy NEM** — a jelenlegi trigger-küszöbeik (Day 21+/10 TP1, Day 30+/5 bear-nap) elemzésre jogosítanak, élesítésre nem.

**2. A bug-torzított Day 1–8 kezelése — kettős elemzés, előre rögzítve.** A **hivatalos kapu a teljes Day 1–63 mintán** értékelődik (a kaput nem mozgatjuk, akkor sem, ha ez nekünk kedvezőtlen — a Day 1–8 veszteségei benne maradnak a +$2,000 küszöbben). Mellette **pre-regisztrált másodlagos elemzés**: ugyanazok a metrikák a Day 9–63 „tiszta architektúra" mintán. A két olvasat együtt riportolandó; ha csak a tiszta minta teljesít, az NEM élesítési alap, hanem a DEFAULT-ág (Day 180 folytatás) melletti érv. Ez a sorrend ma kerül rögzítésre, hogy szeptemberben ne lehessen „kreatívan" választani.

**3. Attribúciós teszt — a kapu-rendszer hiányzó statisztikai szerve, MOST pre-regisztrálva.** A Day 126 három kritériuma portfolió-szintű; egyik sem válaszolja meg a kérdést, ami a (b)/(c) routing-hoz kell: **a stock-szelekciós jel termel-e**. Ezért: Day 63-on és Day 126-on számítandó a Pearson és Spearman ρ(S_j entry-score, R realized per-trade) a swing-minta összes lezárt ügyletén, 95% CI-vel (Fisher-z). Értelmezési küszöbök MOST rögzítve, a melléklet power-táblájával összhangban: Day 63 (~n=50–60 exit) **csak irányjelzés** (a 80% power-küszöb |ρ|≈0.36–0.38 — kis/közepes effekt nem detektálható); Day 126 (~n=100–110) az első érdemi olvasat (küszöb |ρ|≈0.27); a ρ≈0.15–0.20-as „kicsi de valós" effekthez Day 180+ pooled minta kell (n≥180, küszöb ≈0.21). **Routing-szabály**: pozitív P&L + CI-ben a 0 → (b) ág evidencia; negatív P&L + CI-ben a 0 → (c) ág evidencia; pozitív P&L + 0-t kizáró pozitív CI → a swing tézis megerősítve.

**3a. Jel-izoláció (v1.2 — a CC-review #1 gap-jének átvezetése).** A fenti ρ(S_j, realized-R) — mostantól **L0** — confound-olja a jel prediktív erejét az exit-réteg elkapó/levágó hatásával. A kiegészítő spec (`2026-06-10-signal-isolating-attribution-spec.md`) kétszintű izolációt ad: **L1** = exit-független, fix-horizontú forward return; **L2** = szektor-reziduális forward return = a tényleges stock-szelekciós alpha. **A §3 és §4.3 routing-szabályok ρ-ja az L2** — az „L0 pozitív + L2 ≈ 0 → (b) ág" megkülönböztetést az L0 egyedül nem tudja. További pre-regisztrációs fegyelem, MOST rögzítve: **(i)** az egyetlen elsődleges döntési metrika az **L2 Spearman ρ, h=5, szektor-relatív változat**; a h∈{1,3}, a Pearson, a béta-korrigált variancia és a kvintilis-tábla exploratív/támogató (a horizont-profil maga is multiple testing — ha Day 126-on a h=3 „jobbnak tűnik", az nem döntési alap, hanem a következő iteráció hipotézise); **(ii)** az exit-típus szerinti stratifikáció post-treatment conditioning (az exit-típus maga is kimenet) → kizárólag leíró diagnosztika, inferencia soha; **(iii)** a script mindkét mintán emittál (teljes Day 1–63 + Day 9+ clean-sample, a §4.2/2-vel illeszkedve); **(iv)** a spec + a `scripts/analysis/signal_attribution.py` Day 63 előtti commitja **maga a pre-regisztráció zárja** — minden későbbi script-módosítás dokumentált amendment a `04-risks`-ben; **(v)** a mostani n=14-es smoke-run kimenete explicit „plumbing validation, NOT evidence" címkét kap.

**4. A Sharpe-kritérium őszinte értelmezése.** 63 napi mintán az annualizált Sharpe standard hibája ≈ √(252/63) ≈ **2.0** (melléklet B). Egy megfigyelt 0.5-ös Sharpe tehát önmagában statisztikailag megkülönböztethetetlen a 0-tól ÉS a 2-től is. A kritérium funkciója **sanity-bar és irány-konzisztencia**, nem bizonyíték — a hármas keret (P&L + Sharpe + excess-napok) együtt ad értelmet, és pontosan ezért helyes, hogy az élesítés $10k-val indul: **a $10k éles szakasz maga is a validáció része, nem a jutalom** (lásd §4.4).

**5. Az excess-nap kritérium őszinte értelmezése.** 25/63 pozitív excess-nap p=0.5 binomiális null alatt a várható érték (31.5) ALATT van — vagyis a kritérium érme-feldobással is ~80%-ban teljesülne. Nem mozgatjuk (a kapu szent), de a Day 126 olvasatnál a súlya: karakter-konzisztencia-teszt, nem statisztikai evidencia. A statisztikai terhet a §4.2/3 attribúciós teszt viszi.

**6. Globális kill-kritérium a jelkeresésre (a kérdésed iii. pontja).** HA Day 180-ig (≈2026-11-15, a DEFAULT-ág végigfutása esetén, pooled n≥120 exit) SEM (i) a kumulatív nettó P&L nem pozitív, SEM (ii) az attribúciós ρ 90% CI-je nem zárja ki a 0-t pozitív irányban → **a PCR/OTM-családú flow-jelkeresés ebben a formában leáll**. Nem iterálunk tovább rajta, nem finomhangoljuk, nem keresünk hozzá újabb flow-változatot. A pipeline hordozó-státuszba kerül, a (c) forgatókönyv kapuja nyílik, a döntést a Lab-kutatás outputja informálja. Ez a mondat azért kerül ide ma, Day 17-en, a jelenlegi +$767-es eufória közepén, mert **most olcsó kimondani, és szeptemberben-novemberben drága lenne**.

**7. Adatköltség-kapu — v1.2-ben kétlépcsősítve.** **(i) Day 21 (≈jún 14): halott-feed audit** — gyors „élő feature vs shadow-kötött vs sehol-nem-használt" leltár a $665/hó minden komponensére (~1 óra, Chat/CC). A **ténylegesen sehol-nem-használt** feedek lekapcsolása paper alatt nulla validációs kockázat és azonnali megtakarítás; a shadow-kötött feedek (UW → Day 90 audit, n≈150–180, ~2026-08-26) és az élő feedek (FMP a Phase 2-ben, Polygon primér) **maradnak**. Elvárás-kalibráció: a zsákmány valószínűleg kicsi, de a checklist ingyen van. **(ii) Day 126: teljes racionalizálási tábla** — minden komponensre: mely élő feature használja, mi a kiváltási költség, mi a drag a cél-tőkén. Élesítés esetén a stack a $10k-s szakaszban változatlan maradhat (a validáció folytonossága fontosabb), de a skálázási döntésnél ($25k+) a tábla kötelező input.

### 4.3 Kimenet → akció tábla (Day 126)

| Day 126 kimenet | Attribúció | Akció |
|---|---|---|
| ÉLESÍTÉS-kapu teljesül | ρ CI > 0 | $10k éles, a Day 63 doc 7.5 védelmi rétegeivel; skálázás csak +30 nap pozitív után, manuálisan |
| ÉLESÍTÉS-kapu teljesül | ρ CI tartalmazza a 0-t | **Óvatos ág**: $10k éles VAGY +63 nap paper — Tamás-döntés, de a dilemma MOST dokumentált: a P&L jöhet a hordozóból (risk/szektor/piac), nem a jelből; a $10k éles ekkor is védhető, mert a validációt folytatja valós súrlódással |
| DEFAULT | ρ irányban pozitív | Folytatás Day 180-ig változatlanul |
| DEFAULT | ρ ≈ 0 | Folytatás Day 180-ig + a (b) ág (MID-overlay) design-munkája megkezdhető párhuzamosan (deploy nélkül) |
| LEÁLLÍTÁS | bármi | Graceful exit protokoll + (c) kapu nyílik; post-mortem strategic review kötelező |

*(v1.2: a tábla „Attribúció" oszlopának ρ-ja a §4.2/3a szerinti **L2 Spearman, h=5** — az L0 önmagában nem routing-alap.)*

### 4.4 Élesítés esetén — a $10k szakasz mint validációs fokozat

A Day 63 outcome doc védelmi rétegei (3% circuit breaker, notional limitek, pre-submit Telegram veto-ablak, heti kötelező review) változatlanul érvényesek. Egy kiegészítő rögzítés: a $10k szakasz **saját, előre definiált mérőszámmal** fusson — 30 nap után a paper-vs-éles slippage- és fill-eltérés riport (a paper MKT fill-ek optimizmusának számszerűsítése), mert ez az egyetlen információ, amit a paper futás elvileg sem tud megadni. A $10k→$25k skálázás kritériuma (>+$300 net / 30 nap) marad, mindig manuális Tamás-döntéssel.

---

## 5. Sole-operator és tőke-realitás

### 5.1 Idő-allokáció (heti néhány óra)

A szűk keresztmetszet a naptári idő, nem a munkaóra — ebből következik a helyes allokáció: **(1)** napi review: a CC-automatizáció befejezése (a §5.1–5.3 display-fixekkel) után a cél a heti <1 óra manuális teher; **(2)** fejlesztés: Day 63-ig KIZÁRÓLAG bugfix + automatizáció (parameter freeze, §4.2/1); **(3)** a felszabaduló órák a Lab-ra és a MID-re menjenek — azok a KÖVETKEZŐ iterációt táplálják, és nem érintik a futó kísérletet. Ez a felosztás egyben az unatkozó-operátor-tinkering elleni strukturális védelem: legyen hova tenni az energiát, ami nem a futó rendszer.

### 5.2 Tőke-méretezés ($100–500k) és a költség-drag

| Cél-tőke | Adat-drag ($8k/év) | Commission+slippage (swing, becsült) | Teljes drag | Break-even bruttó alpha |
|---|---|---|---|---|
| $100k | 8.0% | ~1.5–2% | ~9.5–10% | ~10% — ambiciózus, de már nem hedge-fund-top-decile |
| $250k | 3.2% | ~1.5–2% | ~4.7–5.2% | ~5% — reális középtáv |
| $500k | 1.6% | ~1.5–2% | ~3.1–3.6% | ~3.5% — kényelmes |

Két következmény: **(i)** az éles skálázási pálya gazdasági logikája: a $10k–25k szakasz tisztán validáció (ott a drag irreleváns, a tét a mechanika), a költség-racionalitás $100k felett kezdődik, és $250k+ az a szint, ahol egy szerény (3–5%) valós alpha már nettó pozitív; **(ii)** likviditási oldalon az S&P 500 + Russell 1000 universum $500k-n is bőven elég — 0.35% risk = $1,750/trade, tipikus notional $15–35k/pozíció, ami a cél-universum napi forgalmának töredéke. A sizing-formula változtatás nélkül skálázódik.

### 5.3 Human-in-the-loop

A jelenlegi felállás (autonóm pipeline + mental stop + napi 22:00 eval + Tamás-jóváhagyású deploy-ok) a helyes egyensúly. Éles üzemben a pre-submit veto-ablak (5 perc, default: megy) megtartandó; a kísértés, hogy a veto-ablakból diszkrecionális felülbírálási réteg legyen, **kerülendő** — a Raschke-elv szerint a diszkréció az iterációkban él, nem a real-time submitben, és minden kézi felülbírálás szennyezi a validációs mintát.

---

## 6. Önámítás-katalógus — mit NE csinálj a következő 109 napban

Ez a szakasz szándékosan személyes hangú, mert a §4 kapu-rendszerének a leggyengébb pontja mindig az operátor.

1. **Ne mozgasd a kaput — egyik irányba sem.** A +$2,000 / Sharpe 0.5 / 25 excess-nap hármas akkor is a kapu, ha Day 50-en +$3,500-nál jársz („már most teljesült, élesítsünk korábban") és akkor is, ha Day 60-on +$1,800-nál („majdnem, adjunk még két hetet"). Mindkét mondat kapu-mozgatás.
2. **Ne értelmezd át menet közben a metrikát.** A „broker-authoritative vs filesystem" kettősség most tiszta; ha Day 63-on a kettő eltér, a broker számít — ez ma kerül rögzítésre.
3. **Ne deployolj jel-érintő változást** a freeze alatt, akkor sem, ha a napi adat „nyilvánvalóvá" teszi (Backlog #7/#8 tipikus kísértés). A nyilvánvalóság n=4 mintán a zaj hangja.
4. **Ne fogadd el a pozitív P&L-t a jel bizonyítékaként** attribúció nélkül — a 50/30/20 keret szerint a hozam fele a piaci irányból jöhet, és a W24 történetesen rebound-hét.
5. **Ne folytasd a jelkeresést a Day 180 globális kill után** „még egy utolsó variáns" alapon. A kill-kritérium pont arra való, hogy ezt a beszélgetést feleslegessé tegye.
6. **Ne hagyd, hogy a review-k ⭐-inflációja** beépüljön a milestone-olvasatba — a Day 63 kiértékelést script számolja, ez a doc a referencia, a napi narratíva nem input.

---

## 7. Mellékletek

### A. Statisztikai erő — attribúciós teszt (Pearson ρ, α=0.05 kétoldali, 80% power)

| n (lezárt exit) | Detektálható |ρ| küszöb | Mikor várható |
|---|---|---|
| 50–60 | 0.36–0.38 | Day 63 (≈2026-08) — csak irányjelzés |
| 100–110 | ≈0.27 | Day 126 (≈2026-09-15) — első érdemi olvasat |
| 180+ | ≈0.21 | Day 180 pooled (≈2026-11) — kis-közepes effekt |
| 350+ | ≈0.15 | csak többszörös futással — a „kicsi de valós" tartomány |

(Exit-ráta becslés a Day 1–17 mintából: ~0.8 exit/trading nap.)

### B. A Sharpe-kritérium standard hibája

Napi hozamokon, N napos mintán: SE(SR_daily) ≈ √((1+SR²/2)/N) ≈ 1/√N kis SR-nél. Annualizálva: SE(SR_ann) ≈ √252 · 1/√N = √(252/N). N=63 → **SE ≈ 2.0**; N=126 → SE ≈ 1.41; N=252 → SE ≈ 1.0. Következmény: a Sharpe-küszöb a Day 126/180 horizonton sanity-bar; valódi statisztikai konfirmáció (pl. SR=1 a 0-tól megkülönböztetve) több éves track recordot igényel — ezért szekvenciális a tőke-skálázás, és ezért nem önálló döntési szerv a Sharpe.

### C. Forrásdokumentumok

`docs/decisions/2026-05-14-day63-decision-outcome.md` (14 döntés + Day 126 keret) · `docs/foundational/strategic-review/2026-05-08-strategic-review-{summary,full,mathematical}.md` (legacy diagnózis, Kelly, power-elemzés, Bonferroni) · `docs/master-reference/04-risks-and-open-questions.md` (Day 1–8 bug-történet, prioritás-tábla) · `docs/planning/backlog.md` (BC26, #7/#8 P3 triggerek) · `docs/review/2026-06-09-daily-review.md` (Day 17 állapot, 17-napos minta-statisztika) · `docs/STATUS.md` (élő státusz) · Bailey & López de Prado (2014), Harvey–Liu–Zhu (2016) — selection effect / multiple testing keret. **Megtalálva (v1.1)**: 2026-05-22 institutional research — `~/SSH-Services/pandoc/2026-05-22-bridgewater-janestreet-research.md`; szinkronizálandó az IFDS repóba (`docs/foundational/strategic-review/`) a Day 126 kapu előtt. Konklúziója konzisztens a §3.b/§3.c routing-gal.

---

## 8. Záró összefoglaló — a döntés egy mondatban

A rendszer mérnökileg kész és statisztikailag igazolatlan; a helyes válasz nem több mérnöki munka és nem korai ítélet, hanem **a futó kísérlet fegyelmezett, paraméter-fagyasztott végigvitele a ma rögzített attribúciós teszttel és kill-kritériumokkal** — Day 63 irányt mutat, Day 126 dönt élesítésről vagy routing-ról, Day 180 a jelkeresés végső kapuja ebben a formában; és ha az utolsó kapu zárva marad, az nem kudarc, hanem a projekt eddigi legértékesebb, legolcsóbban megszerzett információja.

---

## 9. Changelog

- **v1.0** (2026-06-10 délelőtt, Chat): eredeti audit — diagnózis, 3 forgatókönyv, validációs terv kill-kritériumokkal.
- **v1.1** (2026-06-10, CC): forrás-korrekció — a 2026-05-22 institutional research megtalálva (`~/SSH-Services/pandoc/`); kapu- vagy tartalmi változás nincs.
- **v1.2** (2026-06-10 este, Chat, a CC-review 4 gap-je alapján): §2.3/3 W23 súlyozás-korrekció (n=1 rezsim-epizód); §3.b MID-függőség pontosítás (MID = adatforrás-API projekt, readiness-audit mint (b)-előfeltétel); §4.2/3a jel-izoláló attribúció (L0/L1/L2, elsődleges metrika = L2 Spearman h=5, stratifikáció leíró, kettős minta, commit = pre-reg zár, smoke-run címke); §4.2/7 adatköltség-kapu kétlépcsősítése (Day 21 halott-feed audit); §4.3 L2-lábjegyzet. Minden változás szigorító/pontosító; a Day 126 kapu-kritériumok érintetlenek.

---

**A dokumentum vége.** Rögzítve: 2026-06-10, swing pivot Day 17 (cumulative +$767.09, Day 18 várt 4-exit nap). Ez a dokumentum a Day 63 és Day 126 kiértékelés kötelező referencia-inputja; módosítása az adatgyűjtési időszak alatt kizárólag szigorító irányban legitim.

