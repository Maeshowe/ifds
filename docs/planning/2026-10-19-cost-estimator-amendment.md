# PRE-REG AMENDMENT — a költség-becslő: csak valódi súrlódás, oldalanként mérve

**Dátum:** 2026-10-19
**Státusz:** ⏳ **JAVASLAT — Tamás döntésére vár.** Implementáció csak jóváhagyás után.
**Módosítja:** FRL-spec **§5.3** (becslő) · `scripts/research/frl_cost.py::build_cost_model`
**Előzmény:** `docs/review/2026-10-18-roundtrip-cost.md` §8 — három nyitott kérdés, itt eldöntve

---

## 0. IDŐZÍTÉSI TANÚSÍTVÁNY

> A 2026-10-18-i riport **kimondta**, hogy a cserét **nem implementálom**, amíg az
> (a)/(b)/(c) nyitott. Ez a dokumentum azokat **méréssel** dönti el, és **az
> implementáció előtt** rögzíti az eredményt. A score-család mind a 17 kara
> **statisztikai** KILL (`|IC| < éra-bar`), a (e) kapuig el sem jutottak — tehát
> **egyetlen verdikt sem függ ettől** (bizonyítva: §5).

---

## 1. Amit a 2026-10-18-i riport nyitva hagyott

| | Kérdés |
|---|---|
| **(a)** | A kilépési késleltetés költség, vagy kettős könyvelés a gross ellen? |
| **(b)** | A gross `close(t)`-hez horgonyoz, a költség a plan áráhozz — melyik a helyes? |
| **(c)** | A kapuba a pontbecslés vagy a felső korlát menjen? |

---

## 2. (a) ELDÖNTVE — a késleltetés KETTŐS KÖNYVELÉS

**A modell holding-periódusa `close(t) → close(t+h)`** (`frl_returns`: *„Returns are
close-to-close over NYSE trading days"*; HYP-005: *„a forward return t-napi close-tól"*).

A `TIME_STOP` fillje **`close(t+h)`** — **pontosan a modell kilépési pontja**. Amit
„késleltetésnek" mértem (`close(D−1) → close(D)`), az **a tartási perióduson BELÜL** van,
és a `gross = IC·σ_cs(h)·(252/h)` tag **már jóváírja**. Költségként terhelni **kétszer
vonná le ugyanazt**.

> ✅ **Döntés: a kilépési oldalon kizárólag a VÉGREHAJTÁSI slippage a költség**
> (fill vs. az ordertípus által ígért ár), a shortfall **nem**.

## 3. (b) ELDÖNTVE — és a mérés egy elkerülhető hibát tárt fel

A horgony-kérdést nem érveléssel, hanem **dekompozícióval** döntöttem el (n=80):

| Szakasz | előjeles | 95% CI | p | adverz |
|---|---:|---|---:|---:|
| plan → **OPEN** (overnight/pre-open rés) | **−1,5 bp** | [−20,7; +17,8] | **0,878** | 46% |
| **OPEN → fill** (a csengő utáni elsodródás) | **+48,3 bp** | **[+31,0; +64,3]** | **<0,0001** | **78%** |

**Az overnight rés nulla** — a plan ára kiváló becslése a nyitásnak. A belépési költség
**teljes egésze** a nyitás **utáni** elsodródás, és a fill a napi sáv **69%-ánál** landol.

> ✅ **Döntés: a költség a VALÓDI SÚRLÓDÁS — `fill` vs. az az ár, ami a kereskedés
> pillanatában elérhető volt** (belépésnél `open`, kilépésnél az ordertípus referenciája).
> A döntés-ártól mért elsodródás **horizont-eltérés, nem súrlódás**, és a gross
> specifikációjába tartozik, nem a költségbe.

### 3.1 🔴 A mechanizmus — és belső validáció két független oldalról

A submit cron **15:31 Budapest = 09:31 ET**, **egy perccel a nyitó csengő UTÁN** →
lemaradunk a **nyitó aukcióról**, és megvesszük az első percek momentumát.

A kilépési oldal **függetlenül megerősíti**:

| Ordertípus | n | tiszta végrehajtás |
|---|---:|---:|
| **TIME_STOP — MOC (aukciós)** | 68 | **+1,4 bp** |
| TP1 — market a csengő után | 25 | +46,8 bp |
| MENTAL_SL — market a csengő után | 10 | +80,8 bp |

**Az aukciós megbízás gyakorlatilag ingyen van; a csengő utáni market 47–81 bp.**
A belépési +48,3 bp **ugyanaz a mechanizmus, ugyanakkora** — két független oldal,
egy magyarázat. Ez nem feltevés: a saját adatunk.

## 4. (c) ELDÖNTVE — a meglévő kétküszöbös szerkezet megmarad

A (e) kapu ma **medián + p75** sávval dolgozik, és a köztes zóna `INCONCLUSIVE_ON_COST`.
Ez **már** a konzervatív, aszimmetrikus-veszteség-tudatos terv. Nem kell új fogalom —
csak a két szám előjeles analógja:

| (e) kapu slot | ma | **előjeles analóg** |
|---|---|---|
| `breakeven(median)` | `median(\|slippage\|)` | **pontbecslés** (notional-súlyozott előjeles átlag) |
| `breakeven(p75)` ← a kötő | `p75(\|slippage\|)` | **egyoldalas 95% felső konfidencia-korlát** |

> ⚠️ A p75 analógja **nem** az előjeles p75 — az egy per-trade kvantilis, míg a becslő
> most egy **portfólió-szintű első momentum**. A bizonytalanság a **középértékben** van,
> tehát a sáv felső vége a **középérték** felső korlátja.

## 5. Az új becslő és a fal

```
cost_bps_per_side_entry = notional-súlyozott előjeles (fill − open)/open,  qty > 0
cost_bps_per_side_exit  = előjeles (reference − fill)/reference,           per ordertípus
round_trip              = c_entry + c_exit            # NEM 2·c_entry
breakeven_ic            = round_trip / (σ_cs(h) · 1e4)
```

| | belépés | kilépés | round trip | **breakeven** |
|---|---:|---:|---:|---:|
| **pontbecslés** (medián-slot) | 48,3 | 23,2 | **71,5 bp** | **0,1192** |
| **felső korlát** (p75-slot, kötő) | 64,3 | 31,7 | **96,0 bp** | **0,1600** |
| *a mai motor (2 × median\|.\|)* | *83,5* | *—* | *167,0 bp* | *0,2783* |

**Kötelező adat-higiénia:** a `qty = 0` sorok **kizárva** — `MSM 2026-06-04 (−377 bp)` és
`VLO 2026-05-20 (−167 bp)` **meg nem történt trade-ek**, és véletlenül a két legnagyobb
kedvező print, tehát a szennyezés **lefelé** torzított.

## 6. Verdikt-invariancia (kötelező kísérő)

A `promote_verdict()` **ténylegesen lefuttatva** mind a 23 ledger-soron, a régi és az új
költség-modellel → **a bizonyítást az implementációs commit tartalmazza**. Elvárás: **0/23**,
mert mind a 17 score-családi kar `|IC| < éra-bar` miatt a (e) kapuig **el sem jut**.

## 7. 🟢 És egy AKCIÓKÉPES, SZIGNIFIKÁNS lelet

**A belépési +48,3 bp [31,0; 64,3], p < 0,0001 nem piaci adottság — egy perc késlekedés.**
Nyitó-aukciós (MOO) megbízással a nyitás **az** a fill.

| Forgatókönyv | round trip | breakeven |
|---|---:|---:|
| ma | 71,5 bp | 0,1192 |
| **MOO belépővel** | **23,2 bp** | **0,0387** |

**A fal a mai motorhoz képest 7×-esére javulna.** ⚠️ A mért `|IC| < 0,009` ettől **még
mindig 4× alatta van** — a halott jelet ez sem menti meg. De egy **jövőbeli** jelcsalád
küszöbe 0,278-ról **~0,04-re** esne, és ez **gyökeresen megváltoztatja, mi kereshető**.

📌 Ez **konzisztens a SIM-EXEC-kel** (+$2 442 limit-belépővel) — és **megmagyarázza**:
nem a tervezett ár volt különleges, hanem a nyitás utáni momentum elkerülése.

## 8. Mit kérek

| Döntés | |
|---|---|
| **D-C1** | A becslő „csak valódi súrlódás, oldalanként" alakra — **elfogadva / nem** |
| **D-C2** | `qty = 0` sorok kizárása (adat-higiénia) — **elfogadva / nem** |
| **D-C3** | A p75-slot = egyoldalas 95% felső korlát — **elfogadva / nem** |
| **D-C4** | A **MOO belépő** felvétele a javítandók közé (production, nem most) — **igen / nem** |

---

# ERRATA — 2026-10-19, a jóváhagyás UTÁN, az implementáció ELŐTT

> **Státusz:** a D-C1…D-C4 jóváhagyás megtörtént (2026-10-19, Tamás: „Mind a 4 igen").
> Az implementáció **elindítása előtt** egy 67-ágenses adverzariális panel (5 lencse,
> minden lelet külön cáfoló ágenssel) a fenti dokumentumban **tényszerű hibákat** talált.
> A házszabály szerint *„a pre-reg a kánon; a motor csak implementál"* — ha a pre-reg
> valótlant állít, **a pre-reg a hibás, és előbb azt kell javítani.**
> Az alábbi E-1…E-7 **nem** módosítja a D-C1…D-C4 döntések szellemét; a tényalapjukat
> helyesbíti. Ahol a helyesbítés **döntést igényel**, az §E-8-ban van, nyitva.

## E-1 🔴 A D-C2 indoklása tényszerűen HAMIS

A §5 „Kötelező adat-higiénia" bekezdés azt állítja, hogy `MSM 2026-06-04` és
`VLO 2026-05-20` **„meg nem történt trade-ek"**. Mindkettő **valódi trade**:

| | fill | exit | realizált P&L | jutalék a fájlban |
|---|---:|---:|---:|---:|
| VLO 2026-05-20 | 258,23 | 253,19 | **−5,04** | 1,12 |
| MSM 2026-06-04 | 112,79 | 117,30 | **+130,66** | 3,92 |

Mindkettőnek van `trades.details` sora és jutalék-terhelése — három független bizonyíték
arra, hogy a trade megtörtént.

**A valódi mechanizmus egy writer-sémaváltás.** A 181 `slippage_per_ticker` sorból
**80 hordoz `qty` kulcsot, 101 nem, és `qty == 0` sor SEHOL nincs** (0 db). Az első nap,
amikor `qty` kulcs megjelenik: **2026-06-08**. A swing-érában ennél korábbi belépési láb
pontosan kettő van: VLO és MSM.

Következmény: **a D-C2 szó szerint nulla sorra illeszkedik.** A `float(row.get("qty") or 0) > 0`
alakú implementáció csendben *hiányzó-mező*-szabállyá alakítana egy *nem-trade*-szabályt.

Másodlagos tévedés ugyanabban a mondatban: VLO **nem** a második legkedvezőbb print, hanem
a hatodik (ITT −3,23, DE −2,06, USFD −1,89, XPO −1,79 mind kedvezőbb, és mind bent marad).

> ⚠️ **Ezt én állítottam a jóváhagyás kérésekor is, szóban.** A D-C2-re adott „igen"
> egy hamis tényállításra épült. Lásd §E-8/D-E2.

## E-2 A §5 táblája nem reprodukálható a §4/§5 saját szabályaiból

| szám | §-ban előírt szabály | amit a tábla valójában mutat |
|---|---|---|
| belépés 48,3 | §5: **notional-súlyozott** előjeles átlag | **súlyozatlan** átlag (a §5 saját képlete 46,9-et ad) |
| belépés 64,3 | §4: **egyoldalas 95%** felső korlát | iid bootstrap **97,5.** percentilis = kétoldalas 95% CI felső vége (§4 szabálya 61,7) |
| kilépés 31,7 | §4: egyoldalas 95% | iid **95.** percentilis ✅ |

Vagyis **egyetlen táblában két különböző percentilis-szabály** szerepel, és a belépési
felső korlát ellentmond a §4 saját szövegének. Egyik sem nap-klaszterezett, pedig az
előzmény-riport (2026-10-18) az volt.

A belépési pontbecslés létrája: `48,3 (publikált, súlyozatlan) → 46,9 (a §5 saját
súlyozásával) → 45,3 (fill-in-bar szűrővel)`.
A felső korláté: `64,3 (kétoldalas felső) → 61,7 (a §4 szövege szerint) → 63,6
(nap-klaszterezés) → 59,9 (notional-súlyozás) → 58,3 (fill-in-bar szűrő)`.

**A kilépési oldal hű** (pont 23,2 azonos; a felső korlát 32,5 vs. 31,7 a klaszterezésből,
konzervatív irányban).

> A §4 szöveg és a §5 képlet a kánon, **nem az illusztratív tábla**. Egy 46,9 / 59,9-et
> kiadó motor tehát **hűségesebb** a pre-reghez, mint a tábla — de a különbséget ki kell
> mondani, mert a publikált tábla a pre-regisztrált artefaktum.

## E-3 A dokumentum egy MÁSIK pre-reget is módosít, de ezt a fejléce nem mondja ki

A fejléc szerint a módosítás tárgya „FRL-spec §5.3 · `frl_cost.py::build_cost_model`".
A **D-C3 valójában a `breakeven(p75)` slot szemantikáját írja át**, ami a
`docs/planning/2026-10-04-economic-gate-preregistration.md` **§3.1/§3.2** hatálya alá esik.
Annak a dokumentumnak a **§6.1 (2)** pontja a *„p75 → medián (vagy bármilyen lazább)
küszöb-csere az eredmény látása után"*-t **kimondott sértésként** nevezi meg.

Az új becslőt fixen tartva: a §3.1 slot-címke szó szerinti olvasata **118,5 bp → 0,1976**
küszöböt adna, a D-C3 UCB95-je **90,8 bp → 0,1514** — vagyis a PROMOTE-ot kapuzó egyetlen
küszöb **19–23%-kal lazul**, az eredmények ismeretében.

**Tamás 2026-10-19-i jóváhagyása megadja ehhez a felhatalmazást**, de:
1. a fejlécnek hivatkoznia kell a (e)-kapu pre-regre,
2. a `2026-10-04-economic-gate-preregistration.md`-be **visszamutató bejegyzés** kell,
3. a `scripts/research/frl_holdout.py` `EconomicView` docstringje a mostantól **hamis**
   §3.2 kalibrációt állítja („p75/median 1,41–1,63", „nem fordulhat szigorúbb költség felé")
   — javítandó; ez a fájl **hiányzott** a tervezett implementációs listából.

## E-4 🔴 A két oldal NEM ugyanazt a populációt fedi

A belépési slippage-rögzítő **az első 13 swing-session alatt gyakorlatilag nem működött**:

| | ablak | n | napok |
|---|---|---:|---:|
| belépés | **2026-06-08 … 09-22** | 78 | 48 |
| kilépés | **2026-06-03 … 09-30** | 108 | 59 |

93 ledger-pozícióból **13-nak nincs belépési fill-rekordja**, mind 2026-05-22…06-05
között, és **egyik sem esik `KNOWN_GAPS` napra** — ez rögzítő-hiba, nem outage.
(Gyökérok: a `filled` a submit-idejű `entry_price` volt a `8c28a4b`-ig, 2026-06-09.)

A `round_trip = c_entry + c_exit` tehát egy **80/93 pozíción** mért belépést ad össze egy
**93 pozíción** mért kilépéssel — és a belépési oldal által **nem látott** 13 pozíció
adja a könyv néhány **legadverzebb kilépési lábát** (AKAM TP1 06-03 **+137,2 bp**,
ST TP1 06-03 **+85,0 bp**).

**A 13 láb nem veszett el:** a `slippage_backfill_map.json` broker-autoritatív IBKR BUY
filleket tartalmaz mindegyikre. Bevonásukkal n=89, 55 nap (2026-05-22…09-22), és a
belépés **+45,3/+58,3 → +40,3/+52,2 bp**, a fal **0,1142/0,1514 → 0,1059/0,1412**.

A §5 tábla **egyik ablakot sem közli** — ez sérti a 2026-10-04-i derivált-cache
lefedettség-fejléc szabályt.

## E-5 A fill-in-bar egészség-szűrő pre-reg nélküli, és engedékeny irányba mozdít

A `low×0,995 ≤ fill ≤ high×1,005` szűrő a dokumentumban **sehol nem szerepel**. Hatása
a belépési pontbecslésre **−1,6 bp**, és a `0,005` tolerancia **szabad paraméter**.
Ez az egyetlen olyan implementációs döntés, ami **utólagos kizárási szabály** az
eredmények ismeretében, **engedékeny irányba** — tehát a teljes házszabály-kísérőkészletet
(érzékenység + független kalibráció + riportba írás) **neki kell vinnie**, vagy el kell hagyni.

## E-6 🔴 A §6 verdikt-invariancia-bizonyítás ÜRES, és az indoklása hamis

A §6 azt mondja, 0/23 azért várható, mert „mind a 17 score-családi kar `|IC| < éra-bar`
miatt a (e) kapuig el sem jut". Saját méréssel (robbanó sentinel `EconomicView`, ami
minden mezőolvasásra `AssertionError`-t dob):

```
a (e) kaput ELÉRŐ sorok: 0/23
  az éra-bart ÁTLÉPŐ sorok: 4  (A-0003, A-0004, A-0007, A-0008)
```

Mind a 23 sort a **`bh_pass = False`** állítja meg, **nem** az éra-bar — és négy soron
az éra-bar állítása kifejezetten **hamis**. Mivel a `promote_verdict` az
`economic_views`-t csak az `if not reasons:` ágon olvassa, a **0/23 eredmény bármilyen
költségmodellre igaz** — NaN-ra, negatívra, robbanó objektumra is. **Semmit nem bizonyít.**

Hogy a változás **nem** semleges ott, ahol a kapu tényleg aktív:

| \|IC\| | régi sáv (0,2783 / 0,4533) | új sáv (0,1142 / 0,1514) |
|---:|---|---|
| 0,05 | fail | fail |
| **0,12** | fail | **inconclusive** |
| **0,16** | fail | **ok** |
| 0,30 | inconclusive | **ok** |

## E-7 A bootstrap paraméterei nincsenek pre-regisztrálva

A jóváhagyott szöveg nem rögzíti az **újramintavételezési egységet** (nap-klaszter vs. iid),
a **replikációszámot**, a **magot**, a **percentilis-szabályt** és a **súlyozást** — és a
publikált számok más módszerrel készültek, mint amit szállítani készültem.

## E-8 Amit a helyesbítések nyitva hagynak — Tamás döntése

| | Kérdés | Javaslatom |
|---|---|---|
| **D-E1** | Bevonjuk-e a 13 backfill-lábat, hogy a két oldal ugyanazt az érát fedje? (n=78→89; fal 0,1142/0,1514 → 0,1059/0,1412) | **Igen** — a populáció-egyezés korrektségi követelmény. Az irány engedékeny, de ez következmény, nem indok. |
| **D-E2** | A D-C2 sorsa, miután az indoklása hamis és `qty==0` sor nincs | **Töröljük.** VLO valódi trade → marad; MSM a bar-egészség-check miatt amúgy is kiesik (dátum-elcsúszott sor). |
| **D-E3** | A fill-in-bar szűrő: regisztráljuk kísérőkkel, vagy elhagyjuk? | **Regisztráljuk** — a tolerancia és az érzékenység a riportba. |
| **D-E4** | Súlyozás: a §5 betűje (belépés súlyozott, kilépés nem) vagy mindkettő súlyozva? | **A §5 betűje**, a „mindkettő súlyozva" (63,1 bp / 0,1051) **érzékenységként**. |
| **D-E5** | Felső korlát: a §4 **szövege** (egyoldalas 95%, nap-klaszterezett) a tábla 97,5. percentilise helyett? | **A szöveg** — a tábla eltérése erratában rögzítve (fent). |
| **D-E6** | Az invariancia-bizonyítás kicserélése: pozitív kontroll + szintetikus (e)-kapu regressziós teszt + horizontonkénti `economic_status` rács **mért** σ_cs-sel | **Igen** — a jelenlegi forma semmit nem bizonyít. |
