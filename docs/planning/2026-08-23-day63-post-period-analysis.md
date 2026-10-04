Status: OPEN
Updated: 2026-08-23
Note: A swing-éra 63 kereskedési napjának (2026-05-18 → 08-17) UTÓLAGOS, KVANTITATÍV elemzése, kiegészítve a Day 64-67 (08-18 → 08-21) adattal. Kiegészíti — nem váltja ki — a `2026-08-18-day63-period-summary-and-proposal.md`-t: az ott leírt tények változatlanok, ez a dokumentum három olyan számítást ad hozzájuk, amely eddig nem készült el (kritérium-erő, költség-korlát, barrier-geometria). G3: nincs jel-érvényességi nyelv — minden állítás LEÍRÓ. G1: az FRL-eredetű számok itt is INADMISSIBILISEK a kapuba.

# Day 63 utáni elemzés — kritérium-erő, költség-korlát, exit-geometria

> ⚠️ **G3/G1-keret.** A kapu **2026-09-22**. Ez a dokumentum **leíró**; nem állít semmit a jel
> érvényességéről, és **nem jelzi előre** a kapu kimenetelét. A §3 pre-reg küszöbök
> **nem módosíthatók**, és az alábbi javaslatok egyike sem nyúl hozzájuk. Az FRL-eredetű
> mennyiségek (IC, cost-model) **örökre leírók és inadmissibilisek a kapuba** (G1/§7) —
> itt kizárólag a **kapu utáni** napirend priorizálásához használjuk.

---

## 1. Miért most, és mi ennek a dokumentumnak a hozzáadott értéke

A `2026-08-18-day63-period-summary-and-proposal.md` a periódus **tényeit** rögzítette
(n=39 minta, exit-bontás, STOP-állás, D5/D6/§5.6 döntések). Ez a dokumentum három olyan
**számítást** tesz hozzá, amely eddig nem készült el, és amely a kapu utáni napirendet
érdemben átrendezi:

1. **A három §3 kritérium statisztikai ereje** n=63-on — mekkora a mérőműszer felbontása.
2. **A költség-korlát és a mért IC viszonya** — melyik oldalon van a kötő korlát.
3. **A 79,5%-os TIME_STOP-arány barrier-geometriai vizsgálata** — anomália-e vagy várt érték.

Mindhárom **adat nélkül is kiszámítható volt**: a kritérium-erő a küszöbök és a mintaméret
függvénye, a barrier-geometria a paramétereké. Ezért a rögzítésük most **nem** post-hoc
racionalizálás, hanem a mérőműszer felbontásának dokumentálása **a leolvasás előtt**.

> **Ez a dokumentum időérzékeny.** Ha ugyanezek a számok 09-22 UTÁN, az eredmény ismeretében
> kerülnének papírra, megkülönböztethetetlenek lennének a mentegetőzéstől. Ezért kerülnek le
> most, a kapu előtt, változtatás nélkül.

**Módszer és források.** Minden szám mellett a forrás. Olvasott anyag: `docs/STATUS.md`,
`docs/planning/2026-08-18-day63-period-summary-and-proposal.md`,
`docs/planning/2026-07-25-gate-protocol-preregistration.md`,
`docs/master-reference/04-risks-and-open-questions.md` §11.12–11.16 + §12,
`docs/review/2026-08-21-daily-review.md`, `research/attempt_ledger.jsonl`,
`research/cost_model.json`. Számítások: lásd A. függelék (reprodukálható).

---

## 2. Állás — 2026-08-21 (Day 67), tényszerűen

| Mutató | Day 63 (08-17) | Day 67 (08-21) | Forrás |
|---|---|---|---|
| Kumulatív | −$449,88 (−0,45%) | **−$1 532,57 (−1,53%)** | 08-21 review §1, IBKR-verifikált |
| NetLiq | $99 110,62 | $98 974,06 | IBKR |
| Nyitott pozíció | 8 | 6 (unrealized −$225,96) | `reconcile_state` OK |
| `excess_10d_mean` | −0,36% | −0,05% | daily_metrics |
| `cum_30d` | −1,01% | **−2,15%** | daily_metrics |

**A W34 hét** (08-17 – 08-21): Net −$1 082,69, **0/5 nyerő nap**, excess vs SPY **+0,30%**
(mert az SPY heti −1,37%-ot esett). A hét abszolút értékben rossz volt, relatíve enyhén jobb
az indexnél — a két állítás nem mond ellent, de külön olvasandó.

**A `cum_30d` mozgása**: −1,28% → −2,15% egy hét alatt (**−0,87 pp**). A −3,0%-os leállítási
küszöbtől mért távolság **0,85 pp** — a valaha volt legkisebb (08-21 review §5).
Változatlan heti tempó mellett a küszöb egy héten belül elérhető. *Ez aritmetika, nem
előrejelzés (G3).*

---

## 3. Finding 1 — a három §3 kritérium n=63-on zaj-dominált

A pre-reg §3 három küszöbe (`+$2 000` / `Sharpe > 0,5` / `≥ 25` pozitív excess nap)
**gazdasági intuícióból** származik, nem erő-számításból. A mérőműszer felbontása:

### 3.1 Sharpe > 0,5 (60 napi ablak, realized-only, annualizált)

| | Érték |
|---|---|
| Megfigyelt (Day 63) | **+0,090** |
| SE(Sharpe_ann) T=60-on | **2,049** |
| 95% CI | **[−3,93; +4,11]** |
| A 0,5-ös küszöb távolsága | **0,20 SE** |

Az annualizált Sharpe standard hibája a becslés **22-szerese**. A küszöb a becslés
bizonytalansági sávjának belsejében van.

**Mennyi minta kellene?** Egy 0,5-ös Sharpe 0-tól való elkülönítése 80%-os erővel,
kétoldali 5%-on: **~7 900 kereskedési nap ≈ 31 év**. (Sharpe 1,0-hoz ~7,9 év,
Sharpe 1,5-höz ~3,5 év.)

**Következmény:** ez a kritérium 60 napon **nem statisztikai teszt**. Átmegy vagy megbukik,
de a kimenete a mintavételi zajt méri, nem a stratégiát.

### 3.2 Kumulatív > +$2 000

$2 000 a $100k-on = **+2,0%**. A 63 napos kumulatív standard hibája a napi
portfólió-volatilitás függvénye:

| napi vol | SE(63 nap) | a +2,0% küszöb |
|---|---|---|
| 0,30% | 2,38% (=$2 381) | 0,84 SE |
| 0,40% | 3,17% (=$3 175) | 0,63 SE |
| 0,50% | 3,97% (=$3 969) | 0,50 SE |

A küszöb **kevesebb mint 1 SE-re** van a nullától minden ésszerű vol-feltevés mellett.

### 3.3 Pozitív excess napok ≥ 25 (D5: a megfigyelt napokra)

Ez a legélesebb megállapítás. Egy **érmefeldobás** (p=0,5) 63 napon:
- várható érték **31,5** pozitív nap, sd 3,97
- a 25-ös küszöb **1,64 sd-vel a null-átlag ALATT** van
- **P(egy érme átmenne rajta) = 93,5%**

A három kritérium közül tehát az, amelyiket a puszta véletlen 93,5%-os eséllyel teljesíti,
**megbukott**: 25/63 = 39,7% (a nominális nevezőn). Egyoldali binomiális teszt arra, hogy a
valódi arány 50% alatt van: **p = 0,065** a nominális, **p = 0,342** a megfigyelt (25/54)
nevezőn.

> Ez a periódus egyetlen olyan száma, amely a null-hipotézist egyáltalán feszegeti — és
> **ellenkező irányba**, mint amit a keret keresett. **Nem szignifikáns** (p=0,065 > 0,05),
> és a D5 szerinti megfigyelt nevezőn nem is közelíti a szignifikanciát. Leíró megjegyzés,
> nem következtetés (G3).

### 3.4 A hátralévő út a kapuig — az 1. kritérium megvalósíthatósága

08-24 → 09-22 között **21 kereskedési nap** van (Labor Day 09-07 nélkül).

| | Érték |
|---|---|
| Jelenlegi kumulatív | −$1 532,57 |
| A küszöbig | **+$3 532,57** |
| Szükséges napi átlag | **+$168,22/nap** (+0,168%/nap ≈ **+53%/év**) |
| Megfigyelt éra-átlag (Day 1-67) | **−$22,87/nap** |
| P(elérés), napi vol 0,30% / 0,40% / 0,50% | **0,2% / 1,4% / 4,0%** |

*Megjegyzés a definícióhoz:* a §3/1 kritérium **éra-kumulatív** (a D2 csak a Sharpe- és a
pozitív-nap-ablakot kötötte az utolsó N trading naphoz). 09-22-én az éra ~88 trading nap
lesz, míg a két ablakos kritérium ~06-24-ig néz vissza.

### 3.5 Összefoglalva

**A kapu nem tud diszkriminálni.** Mindhárom kritérium olyan felbontású, hogy a kimenetük
elsősorban a mintavételi zajt tükrözi. Ez **nem a fegyelem kritikája** — a pre-registráció,
a freeze, a G1/G3–G7, a pinelt wrapper és az attempt-ledger fegyelme intézményi színvonalú,
és a projekt legerősebb eszköze. A hiba a **küszöbök kalibrációjában** van: a mérőműszer
felbontása nagyobb, mint a mérendő jelenség.

---

## 4. Finding 2 — a kötő korlát a végrehajtási költség

> ⚠️ **G1: az alábbi minden száma FRL-eredetű vagy FRL-származék — INADMISSIBILIS a kapuba**,
> sem mellette, sem ellene. Kizárólag a **kapu utáni** SIM-napirend priorizálásához szolgál.

### 4.1 A számok

| | Érték | Forrás |
|---|---|---|
| Mért belépési rés (medián) | **87,5 bp/oldal** (p75 137, max 377; n=54, 05-20 → 08-20) | `research/cost_model.json` |
| Korábbi batch-értékek | 95,5 (n=28) → 97,0 (n=31) | 04-risks §12.2 |
| Ebből következő **breakeven IC** @97,0 bp | **0,15 – 0,18** (h=5/h=7) | 04-risks §12.2 |
| ugyanez @87,5 bp-re skálázva | 0,135 – 0,162 | lineáris skálázás |
| Mért IC — a **live S_j**, h=5 | **+0,0435** (ICIR 0,647; T_eff 4,6) | `attempt_ledger` A-0007 |
| Mért IC — a **live S_j**, h=7 | **+0,0522** (ICIR 0,803; T_eff 3,3) | `attempt_ledger` A-0008 |
| **A rés** | **3,1× (h=5) / 2,6× (h=7)** a 87,5 bp-es breakevenhez | számítás |

Az A-0007 és A-0008 státusza **`PARK_UNTIL_SWING_POWER`** — alulfeszített, jó előjel, a
{h5,h7} ébresztési család Šidák m=2-vel pre-regisztrálva a retest-adat ELŐTT.

### 4.2 A 87,5 bp természete

Ez **nem spread és nem market impact**. Ez a *T-záró pontozás → T+1 nyitó MKT fill* rés.
A legacy same-day stílus mediánja **19 bp** volt (04-risks §12.2) — a swing-stílus tehát
**~4,6-szeresét fizeti**.

Két további tény:

- **A rés szisztematikusan adverz.** A 08-18-i állás szerint **17/24 = 70,8%** adverz
  (periódus-összefoglaló §4). Egyoldali binomiális teszt p=0,5 ellen: **p = 0,032**.
  95% CI az adverz arányra: [0,489; 0,874]. Nem szimmetrikus zaj. *(A sorozat azóta n=28-ra
  nőtt; az adverz-arány frissítése hátravan.)*
- **A rés nagyobb, mint a teljes jel.** IC=0,0435 mellett, 12 pozíciót választva a
  ~96 kvalifikáltból (felső 12,5%, szelekciós intenzitás 1,65), 5,5%-os 5 napos
  kereszt-metszeti szórásnál a várt 5 napos többlethozam **~0,39%**. A **medián belépési rés
  0,875%** — a jel **2,2-szerese**.

### 4.3 A költség-érzékenység

A breakeven IC közelítőleg lineáris a költségben:

| bp/oldal | breakeven IC | h=5 (0,0435) fedezi? | h=7 (0,0522) fedezi? | |
|---|---|---|---|---|
| 97 | 0,150 – 0,180 | nem | nem | §12.2 publikált |
| 87,5 | 0,135 – 0,162 | nem | nem | **jelenlegi mért** |
| 50 | 0,077 – 0,093 | nem | nem | |
| 30 | 0,046 – 0,056 | nem | **igen** | |
| 19 | 0,029 – 0,035 | **igen** | **igen** | legacy same-day |

**A leíró megállapítás:** a mért IC és a költség-implikálta breakeven közti rés
**a költségoldalról zárható, a jeloldalról nem** — a jelnek háromszor erősebbnek kellene
lennie, a költségnek háromszor kisebbnek. Az egyik nem a rendszer kontrollja alatt áll,
a másik igen.

> **Ez NEM állítás arról, hogy a jel érvényes** (G3). Az IC-becslés alulfeszített
> (T_eff 3,3–4,6), a CI tartalmazza a 0-t, és a `PARK_UNTIL_SWING_POWER` státusz pontosan
> ezt fejezi ki. Az állítás annyi: **ha** van jel a mért nagyságrendben, a jelenlegi
> végrehajtási stílus mellett nem monetizálható; alacsonyabb költségnél igen.

---

## 5. Finding 3 — a 79,5%-os TIME_STOP-arány barrier-geometria, nem anomália

A periódus-összefoglaló §2 a 79,5%-os TIME_STOP-arányt nevezi „a periódus legfontosabb
strukturális ténye"-ként, és a D6 SIM-napirend #1 tétele ennek nyomán a `max_hold`-érzékenység.

**Szimuláció** (driftmentes bolyongás, 5 napos tartás, barrierek +3,0 ATR / −2,0 ATR,
napon belüli érintés, 200 000 pálya, 26 lépés/nap):

| ATR / napi σ | no-touch (TIME_STOP) | TP2 elsőnek | SL elsőnek |
|---|---|---|---|
| 1,0 | 49,3% | 16,1% | 34,5% |
| 1,2 | 64,3% | 9,7% | 26,0% |
| **1,4** | **75,4%** | 5,3% | 19,3% |
| **1,6** | **83,4%** | 2,8% | 13,8% |
| **MEGFIGYELT (n=39)** | **79,5%** | **10,3%** | **10,3%** |

A no-touch arány a reális ATR/σ-tartományban (1,4–1,6) **pontosan a megfigyelt szinten van**.

**Következmény:** a `max_hold=5` nem „túl korán" vagy „túl későn" vág — a **barrierek túl
szélesek** egy 5 napos tartáshoz. Az exit gyakorlatilag „tarts 5 napot, vidd el, ami van".

### 5.1 A barrier-ág és a TIME_STOP-tömb szétválasztása

| Exit-típus | n | Σ R | átlag R |
|---|---|---|---|
| TIME_STOP | 31 | **−10,25%** | −0,331% |
| TP2 | 4 | +25,08% | +6,269% |
| MENTAL_SL | 4 | −18,99% | −4,747% |
| **Barrier-ág nettó (TP2+SL)** | 8 | **+6,09%** | — |
| **Összes** | 39 | −4,16% | −0,107% |

**A periódus teljes vesztesége a TIME_STOP-tömbből jön.** A barrier-ág nettója enyhén
pozitív. A 4:4-es TP2:SL arány a driftmentes elméleti 40:60-tól n=8-on nem elkülöníthető
(kétoldali binomiális **p = 0,72**).

### 5.2 A TIME_STOP-tömb: a jel legtisztább olvasata

A TIME_STOP-tételek azok, amelyeken **nincs barrier-torzítás** — az 5 napos hozam
csonkítatlanul látszik. Átlag **−0,331%**, n=31:

| feltételezett szórás | SE | t | p | 95% CI |
|---|---|---|---|---|
| 2,0% | 0,359% | −0,92 | 0,364 | [−1,04%; +0,37%] |
| 2,5% | 0,449% | −0,74 | 0,467 | [−1,21%; +0,55%] |
| 3,0% | 0,539% | −0,61 | 0,544 | [−1,39%; +0,73%] |
| 3,5% | 0,629% | −0,53 | 0,602 | [−1,56%; +0,90%] |

**Minden ésszerű szórás mellett megkülönböztethetetlen a nullától.** Ez összhangban van
a `signal_attribution` leíró futásával (L2 Spearman h=5: −0,018 / −0,008, CI tartalmazza
a 0-t) és az FRL-lel: **nem „nincs jel" — hanem „nem mértük meg"**.

### 5.3 Következmény a D6 SIM-napirendre

A jelenlegi sorrend: `max_hold` → MENTAL_SL → TP2-elérés → végrehajtási stílus.

A fentiek alapján **ez a sorrend fordítva helyes**:

| # | Napirendi pont | Mit fog találni |
|---|---|---|
| 1 (volt 4) | **Végrehajtási stílus** | itt lakik a 3,1-szeres rés — ez az egyetlen tétel, amely a kötő korlátot mozgatja |
| 2 (volt 1) | `max_hold`-érzékenység | barrier-geometriát; a barrier-szélesség és a tartási idő EGYÜTT vizsgálandó, külön-külön félrevezet |
| 3 (volt 2) | MENTAL_SL kalibráció | n=4 — nincs mit kalibrálni |
| 4 (volt 3) | TP2-elérés | n=4 — nincs mit kalibrálni |

---

## 6. Elvégzett konzisztencia-ellenőrzések

| Ellenőrzés | Eredmény |
|---|---|
| n = 31+4+4 | **39** ✓ (egyezik a periódus-összefoglalóval) |
| win = 14+4+0 | **18/39 = 46,2%** ✓ |
| ΣR = −10,25+25,08−18,99 | **−4,16% → átlag −0,1067%** ✓ (közölt: −0,107%) |
| Kereskedési napok 08-24 → 09-22 | **21** (Labor Day 09-07 kizárva) |

A periódus-összefoglaló §2 számai belsőleg konzisztensek; nem találtam eltérést.

---

## 7. Javaslatok — a kapu ELŐTT (freeze-safe, prod-érintés nélkül)

### 7.1 🔴 Rögzítsd 09-22 ELŐTT, hogy a kapu mit fog és mit nem fog jelenteni

**Ez a lista legidőérzékenyebb tétele.** A §3-ban levezetett erő-számok adat nélkül is
kiszámíthatók voltak. Rögzíteni kell — a kapu-riport kötelező kísérőjeként — hogy:

- a kapu **eljárási kötelezettség**, amelyet betartunk, és amelynek a menete pinelt;
- a kimenete **nem bizonyíték** a jel mellett vagy ellen (a kritériumok felbontása a
  §3.1–3.4 szerint nem elegendő a diszkriminációhoz);
- a **default (PAPER FOLYTATÁS)** a legvalószínűbb kimenet, és a **leállítási ág** (`cum_30d`)
  jelenleg közelebb van, mint az élesítési.

⚠️ **Ez NEM küszöb-mozgatás.** A §3 küszöbök változatlanok. A dokumentálás tárgya a
mérőműszer felbontása, nem a mérce helye. A kettőt írásban élesen szét kell választani.

### 7.2 Az üzemviteli kockázat most nagyobb, mint a stratégiai

63-ból **9 outage trading nap (14,3%)**, 5 esemény, ebből **3 FileVault-osztályú**
(07-22, 08-07, 08-21). A 08-21-i eset (04-risks §11.16) új hibaalakot mutatott:
**a gép fent volt, az SSH egész nap zöld, a `cron` mégsem futott 8,5 órán át**. A
`monitor_submit_heartbeat.py` maga is cron-job, tehát **elvileg képtelen** ezt detektálni.

Ez most a **kapu-minta integritásának legnagyobb egyedi kockázata**, és teljesen ismert
mérnöki eszközökkel javítható:

1. `LaunchDaemon` a user-cron helyett (rendszer-kontextus, login-független)
2. **külső** heartbeat a MacBookról a mai `logs/` fájlok meglétére
3. auto-login + FileVault-csomag
4. `check_gateway.py` **indítsa is** a Gateway-t, ne csak jelezzen

**Infra, nem kereskedési logika → freeze-safe, a D6 nem tiltja.**

### 7.3 A két nyitott Tamás-döntés — konkrét javaslat

**§5.1 — mi számít outage-napnak (részleges kiesés).** A jelenlegi kritérium
(*hiányzik-e a `daily_metrics` fájl*) 08-21-en **némán átengedte** az érdemben csonka napot.

> **Javaslat:** az outage-kritérium legyen **„lefutott-e a 14:30 Phase 4-6 ÉS a 15:31 submit"**
> — vagyis tudott-e a stratégia egyáltalán cselekedni. Logból ellenőrizhető, szemantikailag
> a helyes kritérium, és gépileg kikényszeríthető a `verify_outage_days()`-ben.
> **Új pin szükséges** (jelenlegi: `68fc00e`).

**§5.2 — az EQH/DLB napon belüli (2h21m) késés.**

> **Javaslat: NE számítson kizárásnak.** Ha a napon belüli csúszás kizáró ok, a szabály
> korlátlanná válik (minden fill késik valamennyit, csak a küszöb kérdés). A küszöb legyen:
> **„az exit más kereskedési napon hajtódott végre, mint szándékolt"**. Ezzel az eddigi
> 4 §5.2-eset besorolása **változatlan** marad, a szabály zárt lesz, és a minta nem
> csökken tovább (n=39 marad).

---

## 8. Javaslatok — a kapu UTÁN

### 8.1 Cseréld a kapu-keretet P&L-küszöbről IC-küszöbre

A `+$2 000 / Sharpe>0,5 / 25 nap` hármas **elérhető mintán soha nem lesz döntőképes**
(§3.1: 31 év). Az FRL-ben viszont **már megvan a helyes műszer**: sector-relatív Spearman IC,
Newey-West SE (lag=h−1), era-kvalifikált bar, BH-FDR, attempt-ledger, one-touch holdout.

> **Az új pre-reg tárgya:** *a live S_j IC-je h∈{5,7}-en, elegendő T_eff mellett, a
> költség-implikálta breakeven felett.* Ez **elérhető mintán** eldönthető.

A megfogalmazás részletei (küszöb, T_eff-floor, holdout-protokoll) a kapu utáni, **új**
pre-regisztráció tárgya — ez a dokumentum nem rögzít küszöböt.

### 8.2 A #1 kutatási kérdés a végrehajtási stílus

Konkrétan mérendő (SIM-L2 / Mode 2 re-score + `broker_sim`):

1. **Mean-reverteál-e a nyitó rés napon belül?** Ha igen, a belépés eltolása órákkal
   ingyen visszaad a 87,5 bp-ből.
2. **LMT a T-záró referenciaáron ±sávval**: a biztos 87,5 bp-t **fill-rate költséggé**
   alakítja. Mekkora fill-rate mellett éri meg?
3. **Van-e olyan pontozási időablak, amelyben a jel és a végrehajtás ugyanabban a
   szesszióban van?** A legacy 19 bp-je ebből jött. Az akadály adat-elérhetőségi
   (a PCR/OTM percentilis teljes napi opciós flow-ból számol) — ez a korlát explicit
   vizsgálandó, nem adottságként kezelendő.

### 8.3 Egyszerűsítés — konkrét tételek

| Mit | Miért |
|---|---|
| **TP1 részleges + trail** | 39-ből 8 tételen aktivált (20%); a barrier-ág nettó hozzájárulása +6,09%. Cserébe `tp1_hit` / `qty_remaining` / `trail_sl` / self-reentry állapotgép, amely **három külön defektet** termelt: `exit_type` félrecímkézés (08-21 review §6), a `reconcile_state` darabszám-vaksága (u.o.), self-reentry súrlódás. **20%-os aktiválásért ez a komplexitás nem fizet.** Alternatíva: egy TP + egy stop, vagy tiszta time-stop. |
| **Self-reentry** | Emergens viselkedés: a `max_hold` kikényszeríti az exitet olyan pozíción, amely még kvalifikál — majd a rendszer újra belép. **Két oldal × 87,5 bp = 175 bp** elszórva. n=3, a DLB az egyetlen, amelynek mindkét oldala mérve van (−$79,22 → +$154,47). **Javaslat:** ha a pozíció a `max_hold`-on még kvalifikál, **hosszabbítson**, ne lépjen ki és vissza. |
| **Multiplier-chain maradvány** | Csak `M_target` aktív, a többi 1.0-ra fagyva. A chain-infrastruktúra egyetlen szorzóért fut — összevonható. |
| **UW-kódutak** | Már eldöntve (§11.14): kapu utáni takarítás, saját taskkal. Változatlanul helyes. |

---

## 9. Amit NEM javaslok

- **Nem javaslom a §3 küszöbök módosítását** — sem most, sem a kapunál. A periódus-összefoglaló
  §6 ezt már kimondta, és igaza van. Az erő-elemzés dokumentálása (§7.1) **nem** küszöb-mozgatás;
  a kettőt írásban szét kell választani.
- **Nem javaslom a projekt leállítását.** Egyetlen pre-reg leállítási feltétel sem aktivált,
  és a §4 költség-aritmetika **konkrét, mérhető, javítható** okot ad — ez lényegesen jobb
  helyzet, mint egy megmagyarázhatatlan null.
- **Nem javaslom új jelcsalád indítását most.** A HYP-004 mind a 4 horizonton KILL; a HYP-005
  h=5/h=7 `PARK_UNTIL_SWING_POWER`, jó előjellel és alulfeszítve. Új faktor keresése azelőtt,
  hogy a költségoldal rendbe kerülne, **ugyanabba a falba fut** (§4.3).
- **Nem javaslom a `max_hold` izolált SIM-vizsgálatát** a §5 alapján. A barrier-szélesség és a
  tartási idő **együtt** határozza meg a no-touch arányt; külön-külön mindkettő félrevezet.

---

## 10. Egy mondatban

A második 63 nap **nem azt mutatta meg, hogy nincs jel — hanem azt, hogy a mérőrendszer
felbontása nem elegendő a döntéshez, és hogy az architektúra ~4,6-szeresét fizeti a
végrehajtásért annak, amit a legacy stílus fizetett**; a kapu utáni ciklus helyes tárgya
ezért a végrehajtási költség és a kritérium-keret, nem a scoring.

---

## A. függelék — reprodukálhatóság

A §3–§5 számításai `numpy` 2.4 / `scipy` 1.17 / `pandas` 3.0 alatt készültek, determinisztikus
seeddel (`default_rng(7)` a barrier-szimulációhoz). Bemenetek és képletek:

| Számítás | Bemenet | Képlet / módszer |
|---|---|---|
| Sharpe SE (§3.1) | Ŝ_ann=0,090; T=60 | SE_pp = √((1+Ŝ_pp²/2)/T); SE_ann = SE_pp·√252 |
| Sharpe minta-igény | S_cél | n = (z_0,975+z_0,80)²·(1+S_pp²/2)/S_pp² |
| Kumulatív SE (§3.2) | napi vol; T=63 | SE = vol·√63 |
| Érme-átmenet (§3.3) | n=63; p=0,5; k=25 | 1 − BinomCDF(25; 63; 0,5) |
| Egyoldali binom. teszt | 25/63 és 25/54 | `scipy.stats.binomtest(..., alternative='less')` |
| Kereskedési napok (§3.4) | 08-24 → 09-22 | `pd.bdate_range` − Labor Day (09-07) |
| Várt 5 napos hozam (§4.2) | IC=0,0435; q=12/96; σ_cs | IC·σ_cs·E[z\|z>Φ⁻¹(1−q)], E[·]=φ(z)/q |
| Adverz-teszt (§4.2) | 17/24 | `binomtest(17,24,0.5,alternative='greater')` |
| Barrier-szimuláció (§5) | ±3,0/−2,0 ATR; 5 nap; 26 lépés/nap; 200e pálya | első érintés összehasonlítás |
| TIME_STOP t-teszt (§5.2) | átlag −0,331%; n=31 | t = átlag/(sd/√n), Student-t, df=30 |

**Nem használt adat:** a napi excess idősor nyers formában nem került beolvasásra; a §3.2
SE-becslés ezért **parametrikus feltevésre** épül (napi vol-sáv), nem mért szórásra.
A pontosítás a `state/daily_metrics/*.json` `excess_pct` sorozatából elvégezhető, és
az eredményt **nem várhatóan** változtatja meg érdemben (a küszöb minden feltevés mellett
1 SE alatt marad) — de a rés jelölve van.

**Nem frissített szám:** az adverz-arány (17/24) a 08-18-i állás; a sorozat azóta n=28.
A frissítés a következő review-ban elvégezhető.
