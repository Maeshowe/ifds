Status: DONE
Updated: 2026-10-23
Note: Tamás jóváhagyta 2026-10-23-án — a §4 MIND A NÉGY lépése. Az 1-2. VÉGREHAJTVA ugyanaznap (lezárás + az 5 HYP-007 verdikt kihúzása a tallóból, a verdiktek érintetlenül); a 3-4. (pre-reg + bar-alapú panel + EGY faktorcsalád) friss sessionben, szándékosan — egy pre-reg, amit ugyanaz a session ír, aki az érvelést csinálta, epistemikusan rosszabb.

# Döntési rekord — az IFDS score-család lezárása (§3)

## 0. Mi ez és mi nem

> ✅ **JÓVÁHAGYVA — Tamás, 2026-10-23.** Mind a négy lépés. Az **1–2. végrehajtva**
> ugyanaznap (lásd §9); a **3–4. friss sessionben** indul.

Ez eredetileg **javaslat** volt, nem meghozott döntés. A `docs/STATUS.md` „A nyitott stratégiai döntés"
szekciója három utat kínál — (A) új jelcsalád, (B) végrehajtás-vezérelt újraindítás,
(C) a jelcsalád lezárása. Tamás 2026-10-23-án (A) és (C) között kért javaslatot.

A rekord a bizonyítékot is tartalmazza, **beleértve a javaslat ellen szólót**, hogy a
döntés később felülvizsgálható legyen azon az alapon, amin született.

---

## 1. A javaslat

> **(C) — a score-család lezárása.** A ledger 23 sora az eredeti verdikten marad; nem
> futtatunk újra semmit. **De a lezárás nem a projekt lezárása, és nem zárja be az (A)-t**
> — a §4 négy lépése egy héten belül megválaszolhatóvá teszi, hogy az (A) egyáltalán
> érdemes-e, ~8 perc gépidőért és nulla új előfizetésért.

---

## 2. 🔴 Ahol a javaslattevő saját vezető érve megdőlt

Ezt elsőként kell rögzíteni, mert e nélkül a rekord félrevezető.

2026-10-23-án, néhány órával a javaslat előtt, CC azt írta, hogy a döntő érv a
**végrehajtási fal**, és idézte a `2026-10-19-execution-wall-by-horizon.md` §2.1-ét:
*„olyan jelet kellene találni, amilyen a szakirodalomban nem létezik."*

**Ez az érv nem áll meg.** A `scripts/research/frl_ic.py:295-313` docstringje — ami **ezt
a döntést megelőzően** került a kódba — tételesen felsorol három dokumentált, szándékosan
**nem alkalmazott** alábecslést a gross oldalon, és mind a három **lefelé** mozdítja a falat:

| korrekció | szorzó | forrás |
|---|---|---|
| KONSTRUKCIÓ — a gross dollár-semleges Grinold-alak, a költség koncentrált long-only top-q könyvre terhelve; `κ = φ(z_c)/q` | 1,8× (q=0,10) … **2,79×** (a tényleges q=0,0067) | `frl_ic.py:300-307` |
| ESTIMATOR — Spearman rang-IC vs Grinold Pearson-ja | ~1,047× | `frl_ic.py:308-311` |
| NEVEZŐ — a költség a bruttó könyvre, az `IC·σ_cs` a `z/N` vektorra | ~1,25× | `frl_ic.py:312-313` |

A kód maga mondja ki: *„mixing them is the same category of error as the frequency mix
this module just fixed"*, és a jelenlegi számot **„conservative"**-nak nevezi.

Korrigálva a h=5-ös fal: mai végrehajtással **0,042–0,067** (a publikált 0,1489 helyett),
MOO-val **0,019–0,030**. A mért |IC| = 0,0130 ettől **1,4×-en belül** van.

> **Következmény:** a végrehajtási fal **soha nem volt a kötő korlát**. A statisztikai kapu
> volt — az ERRATA E-6 már bizonyította, hogy mind a 23 soron `bh_pass = False`.
> **Aki (A) mellett érvel, ez a legerősebb érve**, és a lezárás indoklásából ki kell venni.

---

## 3. Amin a javaslat áll

### 3.1 A null verdiktek 18/23-ban érintetlenek — saját méréssel

A 2026-10-23-i négy adatdefekt felvetette, hogy a 23 KILL nem arról a rendszerről szólt,
amit a terv leír. Megmérve a valódi panelen (84 832 sor, 86 nap, 11 szektor, 2 019 ticker,
`frl_loader` + `frl_ic` + a `returns.parquet`):

| mérés | eredmény |
|---|---|
| **A)** a breadth-defekt mint **szektor-konstans**, a szektor-semleges IC-n | **ΔIC = 0,000e+00 bitre pontosan**, h = 1, 3, 5, 7, 10 |
| **B) KONTROLL** — ugyanaz az eltolás **nem** szektor-semleges poololt IC-n | Δ **+0,0049 … +0,0069** |
| **C)** EWMA-szivárgás (per-ticker átmenet, 8 seed × 5 horizont) | legrosszabb \|ΔIC\| = **9,49e-04** = az éra-bar **3,2%-a** |

A (B) kontroll a lényeg: nélküle a nulla azt is jelenthetné, hogy a teszt érzéketlen.
Az immunitás **a szektor-semleges konstrukció tulajdonsága** — a `daily_ic` docstringje
analitikusan is kimondja: *„a monotone shift by the sector mean cannot change within-sector
ranks."*

**Következmény a 23 attemptre:**

| hipotézis | attempt | bemenet | érintett? |
|---|---:|---|---|
| HYP-004 reversal | 4 | `past_ret_5` (tiszta OHLCV) | nem |
| HYP-005 aggregát | 6 | `Total_Score` | csak a 9,5e-04-es szivárgás |
| HYP-006 **flow (súly 0,60)** | 4 | `Flow_Score` | **nem** — ép adat (pcr 99,8%, otm 99,8%, gex 99,6%) |
| HYP-008 **tech (0,30)** | 4 | `Tech_Score` | **nem** |
| HYP-007 **funda (0,10)** | 5 | `Funda_Score` | **IGEN — nem biztonságos** |

**18/23 érintetlen; 5 nem biztonságos.** A Flow és a Tech **önállóan null, ép adaton**.

### 3.2 A saját, előre megírt szabály 31 kereskedési napja teljesül

`cum_30d < −3,0%` — először **2026-09-11-én** (−3,38%), a kapun **−5,22%**, azóta
folyamatosan. A gate-protokoll kimondja, hogy ilyenkor a „default: paper folytatás"
**nem hívható**. Egy leállítási szabály, amit előre megírsz és aztán nem tartasz be,
megszűnik leállítási szabály lenni — és ennek a projektnek az egész epistemikus
felépítménye ezen áll.

### 3.3 A kapu nem szorosan bukott

| kritérium | küszöb | tény | távolság |
|---|---|---|---|
| kumulatív P&L | > +$2 000 | **−$5 193,86** | $7 193,86 |
| Sharpe (60d) | > +0,5 | **−7,174** | — |
| pozitív excess nap | ≥ 25 | 36/79 ✅ | az egyetlen teljesülő, ebből 8 nap 0-exites |

### 3.4 Ami az (A)-t MA megöli: nem a fal, hanem az óra

A használható panel **ma nulla nap** — a 2026-10-04-i 62 napot a D-U3 (10-20) és a
scoring-éra határ (10-23) is kiütötte. Öt éra-határ öt hónap alatt. Előre gyűjtve, h=5-en,
Šidák m=3 és 80% erő mellett a döntés-képes válasz **2027 vége és 2029 között** van —
0-a-23-ból alapráta mellett.

---

## 4. A négy lépés

| # | mit | mikor | ára |
|---|---|---|---|
| **1** | **A score-család lezárva.** A ledger sorai az eredeti verdikten maradnak; nincs újrafuttatás (garden-of-forking-paths). | a döntéssel | 0 |
| **2** | **Az 5 HYP-007 funda verdikt kihúzása a tallóból** — könyvelési korrekció, nem újramérés. A `04-risks` §6.7 már rögzíti az okot. | a döntéssel | 0 |
| **3** | **Írásos pre-reg, az adat megnézése ELŐTT**: (a) a κ-konstrukciós korrekció verdikt-stabilitási tartománnyal, (b) a bar-alapú panel univerzum-definíciója, (c) a jutalék (mérve **2,65 bp/kör**, ma hiányzik a költségmodellből). | a 4. ELŐTT | ~2 óra |
| **4** | **348 session backfill + EGY pre-regisztrált faktorcsalád** a bar-alapú panelen. Ha az is null, a válasz sokkal jobb bizonyítékkal zárul, mint ma. | ~1 hét | **~8 perc gépidő, 0 új előfizetés** |

> ⚠️ **A 3. lépés sorrendje nem felcserélhető.** A κ-korrekció **csak előre rögzítve**
> elfogadható; utólag pontosan az a mozdulat, amit a házszabály tilt (a kapu lazítása az
> eredmény ismeretében). A `(e)` gazdasági kapu §6.1(2) ezt sértésnek nevezi.

A 4. lépés azért olcsó, mert a bar-alapú panel **konstrukció szerint rezsim-független**
(minden napra újraszámolt likviditási szűrő lezárt bar-okból), tehát nem kell megvárni az
előre gyűjtött adatot. A tagság viszont **visszamenőleg nem rekonstruálható** — ezért az
univerzum-definíció a 3(b) pre-reg tárgya. Terv: `docs/planning/2026-08-24-ohlcv-store-design.md`.

---

## 5. Két korrekció, az út választásától függetlenül

1. **`docs/STATUS.md:70` téves, és élő döntési bemenet.** A félélet-tábla a Funda
   breakeven IC-jét `0,0017 🟢`-ként mutatja. Ez a **§11.28 ELŐTTI maradvány**: a javított
   `breakeven_ic` félélet-független, tehát a Funda breakevenje ugyanaz, mint mindenki
   másé. A cella **~65×-ös kedvező irányú hibát** mutat, és a 88. sor nyitott fenntartása
   részben erre épül. A „Funda strukturálisan olcsó" érv ezzel halott; csak a
   „6-ból 2 bemeneten mérődött" érv marad.
2. **A MOO-költség tautológia.** `frl_fills.py:265-270`: `order_type_reference(TIME_STOP)
   → bar.close`, és a hivatalos záró **maga az aukciós ár** — a 68 lábon mért +1,35 bp
   tehát bar-vs-fill eltérés, nem költség. Belépő oldalon `reference = bar.open`, így egy
   valódi MOO-fill **konstrukció szerint ≈0-t mérne**. A teljes B-forgatókönyv egy **nem
   cáfolható számon** és egy olyan order-típuson áll (`tif="OPG"`), amit ez az IBKR paper
   számla soha nem fogadott el (`crontab.md:93` — „NINCS ÉLŐ SMOKE"), és amiről a
   házszabály tudja, hogy **csendben utasít el** (ifds-rules, 2026-04-08).

---

## 6. A legerősebb érv a javaslat ELLEN

Rögzítve, mert a rekord e nélkül önigazolás lenne. Két, egymástól független tétel:

**(a) A fal nem köt (lásd §2).** Ha a κ-korrekciók helyesek — és a repó saját kódjában
állnak, a döntés előtt —, akkor a korrigált C-fal h=5-en **0,0051–0,0080**, amit a már
mért |IC| = 0,0130 **meghalad**. Vagyis a gazdaságtan soha nem volt az akadály, és
„az aritmetika reménytelenné teszi" nem érvényes lezárási indok.

**(b) Egy deklarált sáv sosem nyílt meg.** A `scripts/research/factors/sj_live.py`
docstringje szerint a faktor *„a megépített transzformációt méri (percentilis-leképezés +
EWMA + szektor-korrekció együtt), nem a nyers PCR/OTM jeleket — azok a v2 sáv
(HYP-001b/002b), külön attempt-család."* A ledger ezt megerősíti: csak HYP-004/005/006/007/008
szerepel. Tehát **„a score-család 100%-ban null" pontosan igaz minden MEGÉPÍTETT ÉS
TESZTELT transzformációra, és hallgat ugyanazon adat egy deklarált sávjáról.** Ehhez jön,
hogy a pontozott sorok **13,9%-a** pontosan a `Flow_Score = 100` kapon ül — a flow-faktor
felső ~14%-a **egyetlen holtverseny**, ami valódi erővesztés.

> Ez a két tétel **nem fordítja meg** a javaslatot — a §3.2-es előre megírt szabály és a
> §3.4-es óra attól még áll —, de meghatározza, **mit kell a 3. lépésben pre-regisztrálni**,
> és hogy a 4. lépés faktorcsaládja ésszerűen lehet a soha meg nem nyitott v2 sáv.

---

## 7. Amit mértem, és amit nem

**Saját mérés / verifikáció:** a §3.1 mindhárom csatornája (a kontrollal együtt); a kapu
számai a forrásdokumentumból; a fal képlete és a `cost_model.json`; a `frl_ic.py`
κ-docstringje; a `STATUS.md:70` hibás cellája; a négy adatdefekt (ma javítva); az FMP
VIX-út éles bizonyítása szabotált Polygon- és FRED-klienssel.

**NEM saját mérés (panel-ügynökök, keresztvizsgálat nélkül — a kör time-outolt):** a ledger
verdikt-eloszlása (21 KILL + 2 PARK), az irodalmi IC-sávok és hivatkozások, az erő- és
idővonal-projekciók, a 2,65 bp jutalék-mérés, a q=0,0067-es tényleges koncentráció.
**Egy panel-állítást megcáfoltam:** a Stocks-leminősítés NEM veszi el az 543 sessionös
ablakot (543 nap ≈ 2,15 év, a Developer 10 évet ad).

---

## 8. Mi NEM dől el ezzel

- **Az (A) nem zárul be.** A 4. lépés után újra kell kérdezni, jobb bizonyítékkal.
- **A projekt nem áll le.** Az infrastruktúra (pipeline, FRL, pre-reg fegyelem, sim-harness,
  bar-tár, 2664 teszt) megmarad, és egy másik jelcsaládot is kiszolgál.
- **Az élő MOO smoke** továbbra is a legolcsóbb egyetlen mérés, ami a gazdaságtant
  eldöntené: ≥30 láb a 09:29:30-as midponthoz mérve, jutalékkal. Egy újraindítási nap,
  nulla API-költség. A panel két független lencséje ezt nevezte meg mint az egyetlen dolgot,
  ami megfordítaná őket.

---

## 9. Végrehajtás — 2026-10-23

### 9.1 (1. lépés) A score-család lezárva

A ledger 23 sora **érintetlen**: egyetlen `decision` sem változott, nincs újrafuttatás.
A lezárás a §3 stratégiai döntés rögzítése, nem a mérések visszamenőleges átírása.

### 9.2 (2. lépés) Az 5 HYP-007 verdikt kihúzva a TALLÓBÓL — a verdiktek maradnak

Mechanizmus: `frl_ledger.strike_from_evidence()` — **kizárólag additív** annotáció
(`evidence_status`, `evidence_strike_reason`, `evidence_struck_by`, `evidence_struck_at`).
A `decision`, az `auto_decision`, a `metrics` és a megerősítési nyom **változatlan**.

| attempt | hyp | h | decision | evidence_status |
|---|---|---:|---|---|
| A-0019 … A-0023 | HYP-007 | 1, 3, 5, 7, 10 | **KILL (változatlan)** | `struck` |

A `deflate()` többszörösség-korrekciója **kihagyja** a kihúzott sorokat, tehát a BH `m`-je
nem számol olyan bizonyítékkal, amit a projekt megtagadott. A tallóban maradó családok:
HYP-004, HYP-005, HYP-006, HYP-008 (legacy + swing) — **18 sor a 23-ból**.

**Idempotens**, és ez nem elméleti: a `confirm_decision`-t egy cross-session dupla hívás
korrumpálta egyszer, felülírva az `auto_decision`-t és eltüntetve, hogy egy ember
KILL→PARK váltást csinált. Egy második strike itt **no-op** — élesben is ellenőrizve,
egyetlen sor sem változott.

Tesztek: `tests/test_ledger_evidence_strike.py` (+12), köztük a production-ledger
állapotát őrző három assert (pontosan az 5 funda-sor van kihúzva; mindegyik KILL maradt;
a másik 18-on nincs strike-mező).

