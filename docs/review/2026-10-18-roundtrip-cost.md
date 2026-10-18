# A valódi round-trip költség — a kilépési oldal először megmérve

**Dátum:** 2026-10-18 · **Keret:** a 2. lépés, read-only mérés
**Task:** `docs/tasks/2026-10-18-true-roundtrip-cost.md`
**Reprodukció:** `python scripts/analysis/roundtrip_cost.py`

---

## 1. Két lelet, és a második a fontosabb

**(1) A kilépési oldal NEM ingyenes.** Előjeles shortfall **+50,0 bp** (belépés: +38,8).
A motor `2c` feltevése — „a kilépés annyiba kerül, mint a belépés" — **nagyjából helyes**,
sőt enyhén **alábecsüli** a kilépést.

**(2) De a BECSLŐ rossz.** A cost-model `median(|slippage|)`-et használ, ami a
**szimmetrikus drift félszélességét is költségnek számolja** — pedig az kiátlagolódik.

| | n | `median\|.\|` | **előjeles átlag** | adverz |
|---|---:|---:|---:|---:|
| **Belépés** (swing, MIND) | 82 | **83,5** | +38,9 | 70% |
| **Belépés, tisztított (`qty>0`)** | **80** | 83,0 | **+46,6** *(notional: **+42,0**)* | 70% |
| **Kilépés** shortfall | 108 | 123,4 | **+50,0** | 62% |
| Kilépés — csak végrehajtás | 108 | 10,1 | +23,2 | 60% |

> 🔴 **ADATHIBA, a panel találta (az én ellenőrzésem rossz mezőt nézett).** A
> `slippage_per_ticker[T].qty` a **ténylegesen betöltött** darab, és **2 sorban nulla**:
> **MSM 2026-06-04 (−377 bp)** és **VLO 2026-05-20 (−167 bp)** — **pontosan a két
> legnagyobb KEDVEZŐ print**, olyan trade-ekre, amik **meg sem történtek**. Én a plan
> `quantity` mezejével ellenőriztem (az mindig > 0, mert *tervezett* darab), és ezért
> nem láttam.
>
> ⚠️ **Az irány számít:** a szennyezés **lefelé** húzta a becslésemet (38,9 helyett 46,6),
> azaz **abba az irányba, ami a kaput könnyebbé teszi**. A házszabály szerint pont ez a
> konfiguráció kíván a legtöbb figyelmet.
>
> Tiszta belépési költség: **+42,0 bp** notional-súlyozva, nap-klaszterezett bootstrap
> **95% CI [+17,3; +64,9]**, egyoldalas 95% felső korlát **+61,5 bp** (n=80, 50 nap).

> 🔴 **VISSZAVONVA (2026-10-18, adverzariális panel).** Eredetileg azt írtam ide, hogy a
> SIM-1 dollár-könyvelése (`$1 958 / $477 264 = 41,0 bp`) **független földelés** az
> előjeles becslőre. **Ez TAUTOLÓGIA:** a per-trade bp-k notional-súlyozott átlaga
> *algebrailag azonos* a teljes dollár-költség / teljes notional hányadossal. Ugyanaz a
> szám kétféleképpen leírva — **nem tudott volna nem egyezni**. Ez volt a riport
> legtöbbet hordozó érve, és nem érv.
>
> **Ami VALÓBAN bizonyítja a cserét, az nem empirikus, hanem Jensen:** `E|X| ≥ |E[X]|`,
> szigorú egyenlőtlenséggel, valahányszor X előjelet vált. A belépési printek **30%-a
> kedvező**, tehát a `median|.|` **definíció szerint felfelé torzít** — a spec
> „torzítatlan" indoklása megfordítva igaz.

## 2. A fal

| Konvenció | round trip | **breakeven IC** |
|---|---:|---:|
| **Feltételezett** `2c`, median\|.\| — a mai motor | 167,0 bp | **0,2783** |
| Mért be+ki, median\|.\| | 206,9 bp | 0,3448 |
| Mért be+ki, előjeles, **shortfall**-alapú kilépéssel | 92,0 bp | **0,1533** |
| Mért be+ki, előjeles, **végrehajtás**-alapú kilépéssel | 65,2 bp | **0,1087** |

**A fal nagyjából feleződik — de hogy 0,153-ra vagy 0,109-re, az három nyitott
modellezési kérdésen múlik (lásd §8). Ez 1,4×-es bizonytalanság, és ezért NEM
implementáltam a cserét.**

És ha a §11.28-ban dokumentált (szándékosan **nem** implementált) konstrukciós
korrekciót is beszámítjuk (`κ = φ(z_c)/q ≈ 1,8` long-only top-q könyvre), a fal
**~0,082** lenne.

⚠️ **A verdikt ettől nem változik.** A score-család mért `|IC| < 0,009` —
a javított falhoz képest is **16×** hiány (κ-val ~9×). De a szám, amit két hete
mondtam, **kétszer akkora volt a valósnál**.

## 3. Estimand-fegyelem — amit előre ki kellett kerülni

A meglévő két szám **nem volt összemérhető**, és naiv összeadásuk megismételte volna
a 2026-10-04-i hibát:

| Szám | Referencia | Mit mér |
|---|---|---|
| belépési 83,5 bp | a plan `limit_price`-a | **döntés → fill** (drift + végrehajtás) |
| SIM-1 exit 6,6 / 61,2 bp | az ordertípus ígérte ár | **csak végrehajtás** |

Ezért **három külön nevesített metrika** mindkét oldalon: *implementation shortfall*,
*execution slippage*, *delay cost*. A riport **soha nem vonja össze őket.**

### A döntési pont levezetése (cronból + kódból, nem feltételezve)

| Exit-típus | Flag | Submit | Fill | Döntési ár |
|---|---|---|---|---|
| `TIME_STOP` | D−1 20:00 UTC eod_eval | D 19:40 UTC | D close | **D−1 close** |
| `TP1/TP2/*_SL` | D 20:00 UTC eod_eval | D+1 13:30 UTC | D+1 open | **D close** |

A fill-időbélyegek ezt megerősítik: **68 fill 19:59–20:00 UTC** (záró) és
**34 fill 13:30–13:32 UTC** (nyitás).

## 4. 🔴 A kilépési késleltetés egy JAVÍTHATÓ tervezési döntés

| Exit-típus | n | shortfall | ebből végrehajtás | **ebből késleltetés** |
|---|---:|---:|---:|---:|
| TIME_STOP | 68 | 121,9 | **5,4** | **122,6** |
| TP1 | 25 | 116,7 | 37,9 | 60,1 |
| MENTAL_SL | 10 | 155,1 | 73,1 | 81,2 |

*(median |bp|; előjeles alapon a teljes kilépésre shortfall +50,0 = végrehajtás +23,2
+ késleltetés +26,8)*

**A TIME_STOP végrehajtása gyakorlatilag ingyen van (5,4 bp) — a költség a
KÉSLELTETÉSBEN van.** Az ok szerkezeti: a döntés a D−1-i 20:00 UTC eod_evalon
születik, a végrehajtás D 19:40-kor — **egy teljes session** elsodródás.

> Ez **nem piaci adottság, hanem tervezési döntés**. A belépő referenciája ~1 órával
> a fill előtti; a kilépőé **egy teljes sessionnel**. Ugyanazon a napon döntve és
> végrehajtva a kilépési késleltetés nagy része megszűnne.

## 5. Minta és kizárások

**119 exit láb → 108 árazva, 11 kizárva**, tételesen:
10 × „nincs fill-rekord" (a korai swing-napok, ahol a `trades.details` még nem létezett)
+ 1 × adat-egészség: **PFGC 2026-07-28, fill 114,07 a napi sávon kívül
[114,68 ; 116,71]** — ugyanaz az ellenőrzés, ami a SIM-1-ben is két rossz fillt fogott.

## 6. Korlátok

1. **A döntési pont levezetett, nem logolt.** A cron + a `swing_positions.py`
   akció-szemantika alapján; a fill-időbélyegek megerősítik, de egy
   `decision_price` mező a ledgerben jobb lenne. Backlog-tétel.
2. **Egyetlen rezsim** (2026-05-18 → 09-30), 108 láb.
3. **A `median|.|` sorokat megtartom** az összehasonlíthatóságért a
   `cost_model.json`-nal — de a breakeven-hez az előjeles a helyes.
4. **Nem módosítottam a `cost_model.json`-t.** A becslő cseréje a
   `frl_cost.build_cost_model`-ben **értékelő-motor-változás**, külön döntés —
   ez a riport a bemenete, nem a végrehajtása.
5. A `TRAIL_SL` n=1 és a `TP2` n=4 — ezek a sorok zajosak, nem következtetésre valók.

## 7. Mit jelent ez a következő lépésre

A fal **0,280 → 0,148**, és ennek **két harmada a becslő-csere**, nem a kilépési oldal
felfedezése. A végrehajtási javítás tere:

- a **kilépési késleltetés** (~27 bp előjelesen) nagyrészt **szerkezeti és javítható**
- a **belépési oldal** LMT-vel (SIM-EXEC: +$2 442) szintén
- a maradék tiszta végrehajtás (**execution only: +23,2 bp kilépésen**) a piac ára

Együtt ~0,10 alá vihető fal reálisnak tűnik — de **a mért |IC| < 0,009 ettől még
egy nagyságrenddel alatta van.**

---

# 8. ⛔ MIÉRT NEM IMPLEMENTÁLTAM A BECSLŐ-CSERÉT (2026-10-18, panel után)

Tamás mindkét döntésre igent mondott. Elvégeztem a munkát, és **mindkettő „még nem"-re
fordult** — nem meggondolás, hanem a mérés eredménye.

## 8.1 A csere IRÁNYA biztos, a SZÁMA nem

Három független lencse **egyhangúan** (3/3) azt mondja, a becslő változzon — és a
Jensen-érv perdöntő. **De a konkrét szám három nyitott kérdésen múlik:**

**(a) A kilépési késleltetés valószínűleg NEM költség, hanem kettős könyvelés.**
A `TIME_STOP` döntése naptári (`days_held >= 5`), nem ár-alapú. A „késleltetés", amit
mértem (D−1 close → D close), **a papír aznapi hozama** — ami a **tartási perióduson
BELÜL** van, tehát a `gross = IC·σ_cs(h)·(252/h)` tag **már jóváírja**. Újra terhelni
kettős könyvelés. Ha így van, a kilépési költség a **végrehajtás (+23,2 bp)**, nem a
shortfall (+50,0) → a fal **0,153 helyett 0,109**.

**(b) Horgony-eltérés a gross és a cost között.** A `gross` a `σ_cs`-t a **close-to-close**
`fwd_ret_h`-n méri (tehát a modell belépője az **előző záró**), a költséget viszont a plan
**12:30 UTC-s limit-árához** mérem. **Két különböző horgony** — a panel szerint ugyanaz a
hibaosztály, mint a most javított h/HL.

**(c) Pont-becslés vagy felső korlát menjen a kapuba?** A (e) kapu vesztesége
**aszimmetrikus**: egy hamis PROMOTE tőkét tesz egy halott faktor mögé, egy hamis KILL
csak lehetőséget. Aszimmetrikus veszteség mellett nem a torzítatlan pontbecslés az
optimális input, hanem egy **konzervatív kvantilis** (+61,5 bp a +42,0 helyett). És a
(e) kapu `p75` sávjának előjeles analógja **nem** az előjeles p75, hanem a **felső
konfidencia-korlát** — más transzformáció a központi becslőre és a sávra.

> **Ez 0,109 és 0,20 közti tartomány — 1,4–1,8×.** Egyet kiválasztani belőle most
> ugyanaz lenne, mint amit a h/HL képlettel tettem: **számot szállítani, mielőtt értem.**

## 8.2 És a kilépési késleltetés javítása sem indokolt

| Típus | n | késleltetés | **95% CI** | p |
|---|---:|---:|---|---:|
| TIME_STOP | 68 | +37,1 bp | **[−12,7; +89,8]** | 0,167 |
| TP1 | 25 | +29,7 bp | [−6,1; +64,8] | 0,121 |
| ÖSSZES | 108 | +26,8 bp | **[−7,2; +61,5]** | 0,134 |

**Egyik CI sem zárja ki a nullát.** A $803-as „nyeremény" pontbecslés, CI-je nagyjából
[−$200; +$1 800]. **Egy production kereskedési kódút-változtatást nem szabad egy nem
szignifikáns hatásra alapozni** — pláne, ha (a) szerint a hatás nagy része amúgy sem
költség.

**Ami megmarad belőle, az strukturális, nem statisztikai:** a `days_held >= 5` **nem
igényel árat**, tehát nincs ok egy teljes session drift-kitettséget hordozni érte.
Ez **variancia-csökkentés nulla költséggel és szabály-változás nélkül** — jó mérnöki
érv akkor is, ha a várható érték nulla. **Backlog-tétel, nem most.**

## 8.3 ✅ ELDÖNTVE (2026-10-19) — mindhárom, méréssel

| | Döntés | Alap |
|---|---|---|
| **(a)** | A késleltetés **kettős könyvelés** → a kilépési költség a **végrehajtási slippage** | a modell `close(t)→close(t+h)`-t kreditál, a TIME_STOP fillje `close(t+h)` — a „késleltetés" a perióduson belül van |
| **(b)** | A költség a **valódi súrlódás** (fill vs. a kereskedés pillanatában elérhető ár) | dekompozíció: plan→OPEN **−1,5 bp (p=0,88)**, OPEN→fill **+48,3 bp (p<0,0001)** |
| **(c)** | A meglévő **medián+p75** szerkezet marad; az analógok: **pontbecslés** és **egyoldalas 95% felső korlát** | a (e) kapu sávja már az aszimmetrikus veszteség kezelése |

**A fal:** pontbecslés **0,1192**, kötő felső korlát **0,1600** (ma: 0,2783).

🟢 **És egy szignifikáns, akcióképes lelet:** a belépési +48,3 bp **nem piaci adottság**,
hanem **egy perc késlekedés** — a submit 09:31 ET-kor megy, a nyitó csengő **után**.
Belső validáció a kilépési oldalról: **MOC (aukciós) +1,4 bp**, csengő utáni market
**+47…+81 bp**. MOO belépővel a fal **0,0387** lenne — **7× javulás**.

Amendment: `docs/planning/2026-10-19-cost-estimator-amendment.md` (Tamás döntésére vár).

## 8.4 Amit MOST érdemes

1. A **`qty=0` szűrő** a `frl_cost.build_cost_model`-be — ez **tiszta adat-higiénia**,
   nem modellezési döntés: meg nem történt trade-ekre nem rögzítünk slippage-et.
   (Ettől a `median|.|` 83,5 → 83,0, a kapu gyakorlatilag nem mozdul.)
2. A három nyitott kérdés **(a)/(b)/(c) eldöntése** — ez a becslő-csere pre-reg
   amendmentjének tartalma, és **a 3-as lépés előtt kell**.
3. **Utána** a csere, egyben, egy amendmenttel és verdikt-invariancia-bizonyítással.
