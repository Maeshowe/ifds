# Kvantitatív Intraday Trading Rendszer — Stratégiai Felülvizsgálat

**Időszak**: 2026. március 13. – 2026. május 8. (60 kereskedési nap)
**Verzió**: 1.0
**Készült**: 2026. május 8.
**Célközönség**: portfolio menedzserek, befektetési bizottság, döntéshozók
**Státusz**: döntéselőkészítő anyag — a stratégiai irányváltás megalapozására

---

## Tartalom

1. Vezetői összefoglaló
2. A rendszer áttekintése
3. A módszertan részletes leírása
4. Empirikus eredmények — 60 nap, 378 ügylet
5. Strukturális diagnózis — mi működik, mi nem
6. A 2026 áprilisi újratervezés mérlege
7. Három stratégiai irány — döntéselőkészítés
8. Javasolt ütemterv és kockázatkezelés
9. Függelékek

---

# 1. Vezetői összefoglaló

## A rendszer célja

A vizsgált rendszer egy **kvantitatív, opciós flow-vezérelt amerikai részvény-kereskedési platform**, amely napi szinten 3-5 long pozíciót nyit a kereskedési nap nyitása után 45 perccel, és ezeket a piac zárásáig (átlagosan 5,5–6 órás holding period) tartja. A rendszer **automatizált**, emberi felülbírálás nélkül fut egy dedikált infrastruktúrán; a kereskedési döntés a piaci adatok napi feldolgozásán (BMI – Big Money Index, szektor-rotáció, opciós flow, fundamentális szűrés, gamma exposure) alapuló kompozit pontszámból következik.

A platform marketingjében és belső dokumentációjában "swing trading rendszer"-ként szerepel; **a tényleges kereskedési viselkedése azonban intraday momentum/flow trading**, mivel a holding period kevesebb mint egy kereskedési nap. Ezt a fontos pontot a 5. fejezet diagnosztikája részletesen tárgyalja, mert **stratégiai következménye van**.

## Empirikus mérleg (60 nap, 378 ügylet)

| Mutató | Érték |
|--------|-------|
| Kumulatív bruttó hozam | -1,46% (~$100 000 névleges tőkén ~-$1 460) |
| Win rate (ügylet szinten) | 46,6% |
| Átlagos hozam ügyletenként | -$3,15 |
| Profit-küszöb hit ráta (T1) | 9,5% |
| Stop-loss / loss-exit | 12,4% |
| Piaczárás (MOC) exit | 74,1% |
| Átlagos napi forgalom | 6,3 ügylet |
| Becsült éves jutalék-teher | ~$8 400 (~8,4% a bázis tőkén) |

A `**Pearson r ≈ 0**` korreláció a kompozit pontszám és a realizált hozam között (p=0,996) **statisztikailag null edge-et** jelez a teljes pontszámrendszerre vonatkozóan. A 60 napi minta tehát **nem támasztja alá**, hogy a jelenlegi pontozási eljárás strukturális alpha-t generálna a piaci iránytól függetlenül.

## A három legfontosabb stratégiai döntési pont

**1. Az "intraday momentum/flow" karakter strukturálisan kitett.** A 6 órás holding period a kereskedési nap legvolatilisabb periódusait fedi le (opening range, lunch lull, closing rotation), ami a flow signalnek nem ad elegendő időt arra, hogy érvényesüljön. A 60 napi adat alátámasztja: a profit a kis részt képező T1/T2 hit-eken (12,7% összesen) keletkezik, miközben a stop-loss / loss-exit kategóriák nettó deficitje -$4 335. A platform a "flow signal megtalálása" szempontjából működőképes, de a "flow signal monetizálása" szempontjából strukturálisan korlátozott.

**2. A pontozási rendszer csak részben használja a saját adatait.** A flow al-komponens dekompozíciója (2026 áprilisi belső elemzés alapján) megmutatta, hogy a **PCR (put-call ratio, +0,203\*\*)** és az **RVOL (relatív volumen, +0,147\*)** statisztikailag szignifikáns pozitív prediktorok, miközben a **dark pool százalék** változó **inaktív** (minden ügyleten 0 érték), és az **OTM call score** (-0,194\*\*) **negatív szignifikáns** — vagyis a magasabb OTM call jelzés rosszabb hozamot prediktál. A jelenlegi kompozit pontszám ezeket a finding-okat **NEM** tükrözi: az OTM call magas érték még mindig pozitív bónuszt ad, a PCR súlya pedig nincs kiemelve.

**3. Az implementált 2026 áprilisi újratervezés részlegesen orvosolta a strukturális problémákat.** A 13 pontos cselekvési tervből 8 elem implementálódott, **5 elem nem** — köztük a legradikálisabb: a "dinamikus pozíciószám" (kötelező 3-5 pozíció helyett "csak ha érdemes"). A nem implementált elemek között szerepelnek a multiplier chain egyszerűsítése, a "Call Wall" alapú profit-küszöb kikapcsolása, és a flow al-komponens dekompozíción alapuló pontozási rekalibráció.

## Ajánlás

**A jelenlegi rendszer nem alkalmas élő pénzes kereskedés indítására** a 2026 májusi adatok alapján. A 60 napi paper trading **strukturális megfigyeléseket szolgáltatott**, amelyek mentén **három különböző radikalitású továbblépési útvonal** vázolható (lásd 7. fejezet):

- **A. Inkremeális finomítás** (1-2 hónap, alacsony kockázat) — a 13 pontos terv befejezése + a flow dekompozíció finding-jainak átvezetése;
- **B. Időtáv-átalakítás** (2-3 hónap R&D, közepes-magas kockázat) — a 6 órás holding 3-5 napos hold időtávra való kiterjesztése (az "igazi swing" karakterhez közelítés);
- **C. Hibrid kísérletek** (1-2 hét, alacsony kockázat) — mean reversion overlay, opciós-flow priorítása.

Az ajánlott útvonal — kvantitatív szempontból — **A + C kombinációja**, a teljesítmény Day 90 felülvizsgálatáig, és **B opció R&D fázisának párhuzamos indítása**. Az **élő pénzes kereskedés indítása leghamarabb Day 120 (kb. 2026 július eleje) körül lehet realisztikus**, ha a Day 90 felülvizsgálat ezt indokolja.

A részletes érvelés és számszerű alátámasztás a 4-7. fejezetekben.

---

# 2. A rendszer áttekintése

## 2.1 Mit csinál a rendszer

A kvantitatív platform **napi rendszerességgel, automatizáltan** azonosít és nyit long részvénypozíciókat egy kötött szabályrendszer alapján. A folyamat hat fázisban zajlik:

**Diagnosztika (makró-érzékelés).** A reggeli óráiban a rendszer ellenőrzi az adatszolgáltatók elérhetőségét, beolvassa a VIX volatilitási index és a 10 éves államkötvény-hozam (TNX) aktuális értékét, valamint a yield curve állapotát (2s10s spread). Ezek az adatok a későbbi pozícióméretezést és kockázati kontrollt befolyásolják.

**BMI rezsim-érzékelés (Big Money Index).** A platform egy saját fejlesztésű "BMI" indikátort használ, amely a napi piaci volumen-spike-ok (2σ feletti rendkívüli volumen-eltérések) alapján méri az "intézményi vásárlási nyomást". Az indikátor három állapotot különböztet meg: GREEN (≤25%, agresszív long), YELLOW (25-80%, normál long), RED (≥80%, defenzív/short). A 2026 első négy hónapjában az indikátor **az idő ~90%-ában YELLOW állapotban** volt, ami a "normál long" stratégiát eredményezi. Egy kiegészítő mechanizmus, a "BMI Momentum Guard", csökkenti a maximális pozíciószámot 8-ról 5-re, ha a BMI 3 napon át csökkenő trendet mutat.

**Univerzum-építés.** Az amerikai részvénypiacról a rendszer egy szűrőkészlettel választja ki azt az alapsokaságot, amelyből a kereskedési jelölteket meríti. A szűrők: minimum $2 milliárd piaci kapitalizáció, minimum $5 részvényárfolyam, napi 500 ezer részvény átlagforgalom, és **az opciós piaci aktivitás**. Egy kiegészítő szűrő kiveszi azokat a részvényeket, amelyek a következő 7 naptári napon belül **earnings jelentést** közölnek (az earnings event-ek a rendszer szempontjából strukturális kockázatot jelentenek). Ez tipikusan ~1 400-1 500 részvényt szűkít ~210-280-ra a hét közepén.

**Szektor-rotáció.** A 11 alapszektor ETF-jei (XLK, XLF, XLE, XLV, XLI, XLP, XLY, XLB, XLC, XLRE, XLU) közül a rendszer az 5 napos relatív teljesítményt mérve azonosítja a top 3 "leader" és bottom 3 "laggard" szektort. A laggard szektorokba tartozó részvényeket egy -20 pontos pontszám-büntetéssel terheli; a leader szektor részvényeit egy +15 pontos bónusszal jutalmazza. Egy kiegészítő "VETO" szabály teljesen kizárja azokat a szektorokat, amelyek mindkét rövid és hosszú távú trend mutatóra negatívak.

**Részvény-értékelés (a rendszer szíve).** Minden átszűrt részvényre egy **0-100 közötti kompozit pontszám** számítódik három alkomponens súlyozott összegéből:
- **Flow score** (60% súly): opciós flow indikátorok kompozitja — relatív volumen, dark pool százalék, put-call ratio, out-of-the-money call ratio, blokkügyletek száma, vásárlási nyomás;
- **Technikai score** (30% súly): RSI ideális zóna pontszám, SMA50 fölött/alatt jelző, és **3 hónapos relatív teljesítmény az S&P 500-hoz képest** (a "RS vs SPY" bónusz, amelynek súlya a 2026 áprilisi átalakításkor 40-ről 15-re csökkent);
- **Fundamentális score** (10% súly, csökkentve a korábbi 30%-ról): bevétel-növekedés, EPS-növekedés, profit margin, ROE, eladósodottság.

A pontozást egy **EWMA simítás** stabilizálja (10 napos exponenciálisan súlyozott mozgóátlag), és egy **frissesség-bónusz** (95% feletti pontszám esetén az ügylet kizárása, "túlzsúfolt trade" elkerülés).

**Opciós pozíció-elemzés (Gamma Exposure).** A piacvezetők gamma-exponáltságát az opciós piaci adatokból számolja a rendszer; pozitív GEX (gamma-pozitív) esetén a market makerek mozgásai stabilizáló hatásúak (ár-fluktuáció csillapítása), negatív GEX esetén destabilizáló (volatilitás-felerősítő). Ez egy szorzótényezőként hat a pozíció-méretre: pozitív GEX → 1,0×, negatív GEX → 0,5×, magas-vol → 0,6×.

**Pozíció-méretezés.** A végső lépésben a rendszer egy szorzótényező-láncot (multiplier chain) alkalmaz a kockázat-adjustált pozíció-méretre: M_VIX × M_GEX × M_target × M_contradiction. A kockázat-küszöb pozíciónként 0,7% (a 2026 áprilisi átalakítás előtt 0,5% volt). A maximum pozíciószám 5 (korábban 8).

## 2.2 Az exit-mechanika

A pozíciók egy **kettős "bracket" rendszerben** kerülnek beadásra az IBKR (Interactive Brokers) elektronikus brókerszolgáltatásnál. Minden pozíció két részre osztódik 50/50 arányban (a 2026 áprilisi átalakítás óta; korábban 33/67):

- **Bracket A**: T1 (első profit-küszöb) = entry + 1,25×ATR (Average True Range) — a 2026 áprilisi érték 0,75×ATR volt, majd a 13 pontos terv 1,5×ATR-re javasolta emelni, de a végső paraméter **1,25×ATR** lett. Ha a T1 trigger-elődik, a maradék pozíció trailing stop-pal követi az árat.
- **Bracket B**: T2 (második profit-küszöb) = entry + 2,0×ATR (korábban 3,0×ATR). Ha az ár 19:00 CEST-ig nem éri el a T2-t, egy "soft floor" mechanizmus aktiválódhat (a "Breakeven Lock"), amely az aktuális trail stop-ot az entry árra emeli, ezzel megvédi a futó profitot.
- **Stop-loss**: entry – 1,5×ATR.
- **Loss-exit**: a piaci nyitás után -2% mozgás esetén a rendszer korai exit-et triggerelhet, a hagyományos stop-loss-tól függetlenül.
- **Market-on-close (MOC)**: minden 21:40 CEST-ig le nem zárt pozíció a piaczárás-rendelési mechanizmussal kerül lezárásra (16:00 ET, az amerikai piaci napzárás).

## 2.3 Az infrastruktúra rövid bemutatása

A rendszer egy dedikált macOS Mini gépen fut (a fejlesztés egy laptopon történik, a production a Mini-n). Az időzítést egy időzített batch-folyamat (cron) végzi, az alábbi főbb lépésekkel CET időzónában:

- **22:00 (előző este)**: BMI-számítás, univerzum-építés, szektor-rotáció. Eredmény: az aznapi kereskedési jelölteket tartalmazó "snapshot".
- **16:15**: a részvény-értékelés (Phase 4), a pozíció-méretezés (Phase 6), és a megbízások beadása az IBKR-be. Ez **45 perccel a piaci nyitás után**, a 10:15 ET-nek felel meg.
- **16:00–22:00, 5 perces intervallumokkal**: a pozíciók monitorozása, a trailing stop-ok frissítése, a 19:00-i Breakeven Lock kiértékelése.
- **21:40**: a swing exit logika; az aznap nem-lezárt pozíciók MOC-ra állítása.
- **22:05**: napi P&L riport.

## 2.4 Adatszolgáltatók

A rendszer négy külső adatforrásra támaszkodik (frissített 2026-05-14, az `API_STACK.md` alapján):

| Forrás | Havi költség | Napi hívásszám | Funkció |
|--------|--------------|----------------|---------|
| Polygon | ~$376 | ~1 500+ | OHLCV árak, opciós lánc, BMI, VIX |
| Financial Modeling Prep (FMP) | ~$139 | ~4 000+ | Screener, earnings, fundamentumok, insider, target price |
| Unusual Whales | ~$150 | ~300+ | Dark pool, GEX, opciós flow |
| FRED (Federal Reserve) | ingyenes | ~5 | VIX backup, TNX, yield curve |

**Teljes futási költség**: ~$665/hó adatszolgáltatókért, plusz a hardver és infrastruktúra.

> *V1.0 érték: ~$354/hó (Polygon $229 + FMP $75 + UW $50). Korrekció 2026-05-14: a tényleges API tier-k költsége a frissített `API_STACK.md` alapján magasabb.*

## 2.5 Mit nem csinál a rendszer

Néhány fontos pont a tisztázás kedvéért:

- **Nincs short pozíció-nyitás.** A "zombie" (gyenge fundamentumú) részvények short oldali listája szerepel a kódban, de a 2026 áprilisi átalakítás után **a short ág inaktív**. A rendszer **mindig long-only**.
- **Nincs többnapos pozíció.** Bár a kódban van egy "max_hold_trading_days: 5" paraméter, a gyakorlati exit-mechanika dominánsan piaczárásra zár (74,1% MOC), és a többnapos hold ritka kivétel.
- **Nincs portfolio-szintű optimalizáció.** A pozíciók egyenkénti pontszám szerint kerülnek beadásra. A korreláció-szabályok és sektor-koncentráció felső plafonok léteznek (max 2 pozíció szektoronként, csoportonként 2-3 pozíció), de **nincs HRP (hierarchical risk parity)** vagy **mean-variance optimalizáció**.
- **Nincs emberi felülbírálás a pozíció-beadás előtt.** A 16:15 CEST cron-folyamat a megbízásokat azonnal beadja az IBKR-be — a pozíciónyitás közötti és a kereskedés közötti emberi döntéshozatal **nem része a rendszernek**. Ez egy **fontos design-döntés**, amelyet az 5. fejezet részletesen tárgyal.

---

# 3. A módszertan részletes leírása

## 3.1 A kompozit pontszám matematikai szerkezete

A részvények pontozása egy súlyozott összegként számítódik:

```
KOMPOZIT_PONTSZÁM = 0,60 × FLOW_SCORE + 0,30 × TECHNIKAI_SCORE + 0,10 × FUNDAMENTÁLIS_SCORE
```

A három komponens egyenként 0-100 közötti értékkel rendelkezik (a flow esetén egy 50-es bázis köré épül, +/- al-komponens-bónuszokkal).

### Flow score (60% súly)

A flow score 7 al-komponens összegéből épül fel:

| Al-komponens | Maximum bónusz | Mit mér | Pearson r vs P&L |
|---------------|----------------|---------|------------------|
| RVOL (relatív volumen) | +30 | Az aznapi vol az átlaghoz képest | **+0,147\*** |
| Dark Pool % | +15 | Off-exchange forgalom aránya | n/a (inaktív) |
| Put-Call Ratio (PCR) | +15 | Pesszimista/optimista opciós pozícionálás | **+0,203\*\*** |
| OTM Call Ratio | +10 | Out-of-the-money call vétel aránya | **-0,194\*\*** |
| Block Trade Count | +15 | Nagy blokk-ügyletek száma | -0,117 |
| Buy Pressure | +15 / -15 | VWAP fölött/alatt zárás | +0,068 |
| Squat Bar | +10 | Magas vol + szűk spread | +0,036 |

A **rendszer egy belső validációs elemzése** (2026 április) megerősítette a flow al-komponensek **statisztikai prediktivitását**. A PCR (+0,203\*\*) és RVOL (+0,147\*) **szignifikáns pozitív prediktorok**; az OTM call ratio (-0,194\*\*) **szignifikáns negatív prediktor** (a hipotézisstól ellentétes irány); a többi nem-szignifikáns vagy gyengén negatív.

**A jelenlegi pontozási eljárás ezeket a finding-okat NEM tükrözi:**
- Az OTM call ratio továbbra is **pozitív bónuszt** ad (+10 pont) — a tényleges hatás **negatív**.
- A PCR súlya **nincs felfelé átkalibrálva** a relatív erőssége miatt.
- A dark pool % minden ügyletre 0 — az adat nem fut, vagy hibás az integráció.

### Technikai score (30% súly)

A technikai score három al-komponensből áll:

- **RSI ideális zóna**: ha az RSI a [45, 65] tartományban van, +30 pont; [35, 45) vagy (65, 75] esetén +15. A logika: a "nem túladott, nem túlvásárolt" zóna a leginkább alkalmas momentum-trade-re.
- **SMA50 bónusz**: ha az árfolyam a 50 napos mozgóátlag fölött, +30 pont. A logika: a középtávú trend-szűrő.
- **3 hónapos relatív teljesítmény az S&P 500-hoz** (RS vs SPY): a 2026 áprilisi átalakításig +40 pont súlyú volt; **most +15** a 2026 áprilisi 13 pontos terv egyik javaslata szerint.

### Fundamentális score (10% súly, korábban 30%)

A fundamentális score egy 50-es bázis körüli pontszám, amelyre az alábbi tényezők bónuszokat/büntetéseket adnak:
- Bevétel-növekedés (>10% YoY → +5; <-10% → -5)
- EPS-növekedés (>15% → +5; <-15% → -5)
- Profit margin (>15% → +5; <0% → -5)
- ROE (>15% → +5; <5% → -5)
- D/E arány (<0,5 → +5; >2,0 → -5; >3,0 → -10)
- Interest coverage (<1,5 → -5)

A 60 napi adatban a fundamentális score Pearson r értéke **-0,088** (nem szignifikáns negatív). A "backward-looking" probléma: a jó fundamentumok már beárazódtak az árfolyamba, így a jelenlegi pontszám nem ad új információt.

## 3.2 A pozíció-méretezés és a "multiplier chain"

A pozíció-méret a következő képlet szerint:

```
POZ_RISK = (ACCOUNT_EQUITY × 0,007) × M_total
M_total = clamp(M_VIX × M_GEX × M_target × M_contradiction, 0,25, 2,0)
```

ahol:
- **M_VIX**: a piaci volatilitás védelmi szorzója — VIX 20 alatt 1,0×, magasabb értéken arányosan csökkentve, VIX 50 fölött 0,1× (extrém piacon kvázi zéró pozíció);
- **M_GEX**: a market maker gamma-exponáltság szorzó — pozitív 1,0×, negatív 0,5×, magas-vol 0,6×;
- **M_target**: az analyst consensus target ár védelme — ha az árfolyam 20% fölött van a 12 hónapos target felett, 0,85×; ha 50% fölött, 0,60×;
- **M_contradiction**: a 2026 májusi új komponens — **fundamentális ellenmondás-jelző**. Akkor aktiválódik, ha az alábbi kondíciók közül egy vagy több teljesül: kevesebb mint 50% earnings beat az utolsó 4 negyedévben, az ár 2% fölött a consensus target felett, az ár az analyst HIGH target fölött, vagy 2+ recent downgrade az utolsó 30 napban. Hatás: 0,80× szorzó.

## 3.3 Az exit-mechanika logikája

A 50/50 bracket-osztás után a két fele eltérő logika szerint exit-elhet:

**Bracket A (50% pozíció-méret):**
1. Ha az ár eléri a T1-et (entry + 1,25×ATR), az ezen a részen lévő pozíció lezárul, és a maradék fél átkapcsol trailing stop-ra (1×ATR távolság).
2. Ha az ár nem éri el a T1-et, és a 21:40 CEST-i swing close trigger-elődik, a pozíció a piaczárás rendelésével (MOC) lezárul.
3. Ha az ár a stop-loss küszöböt (entry - 1,5×ATR) éri el, a pozíció veszteséggel zárul.
4. Ha a piaci nyitástól a pozíció -2% feletti mozgást mutat, egy "loss exit" mechanizmus aktiválódik a hagyományos stop-loss megelőzésére.

**Bracket B (50% pozíció-méret):**
1. T2-re céloz (entry + 2×ATR), ami egy ambíciózusabb cél.
2. Ha 19:00 CEST-ig az ár +1% fölé emelkedett (becsült küszöb), egy "Breakeven Lock" mechanizmus aktiválódik: a trail stop az entry árra emelkedik. Ez **megvédi a futó profit egy részét** akkor is, ha az ár visszaesik a T2 elérése előtt.
3. Ha a T2 trigger-elődik, a maradék pozíció trailing stop-ra kapcsol.

A profit-küszöb hit ráták szerint a T1 (1,25×ATR) ~9,5%-ban triggerelődik, a T2 (2×ATR) csak ~0,8%-ban. A pozíciók **74%-a piaczárás-rendelésen** zárul, ami a holding period 6 órás keretét kvázi-determinisztikussá teszi.

## 3.4 A makró-kontextus és a kockázatkezelés

A rendszer makró-szintű kockázatkezelést a következőképp valósítja meg:

- **VIX-érzékelés**: a VIX érték 20 fölött arányosan csökkenti a pozíció-méretet (0,02-os decay rate). VIX 30 fölött a "magas-vol" rezsim aktiválódik (M_GEX 0,6×).
- **Cross-Asset Regime**: 5 ETF (HYG, IEF, RSP, SPY, IWM) 20 napos relatív teljesítményéből számolt rezsim-osztályozás (RISK_ON, NEUTRAL, RISK_OFF, CRISIS). RISK_OFF rezsimben a max pozíciószám 5-ről 4-re csökken; CRISIS-ben (VIX > 30 + 3 ETF lefelé) 5-ről 3-ra.
- **Yield curve monitor**: a 2s10s spread inverziója egy "fél szavazat" a Cross-Asset rezsim-szavazásban; deep inverzió (-0,5% alatti) egy "teljes szavazat".
- **Korreláció-szabályok**: a portfolio-szintű korreláció-koncentráció szabályok: max 2 pozíció szektoronként, max 3 cyclical / 2 defensive / 2 financial / 2 commodity csoportonként.
- **Portfolio VaR**: 95%-os bizalmi szinten max 3% account VaR (Value-at-Risk).
- **Circuit breaker**: ha a kumulatív paper hozam 3% alá esik, a rendszer automatikusan leáll; emberi felülbírálással újraindítható.

---

# 4. Empirikus eredmények — 60 nap, 378 ügylet

## 4.1 A teljes mintaadatok

A 2026 március 13. és május 8. között végrehajtott paper trading futás a következő mérleget eredményezte:

| Mutató | Érték | Megjegyzés |
|--------|-------|-------------|
| Időszak | 60 kereskedési nap | 12 naptári hét, 1-2 ünnepi szünet |
| Összes ügylet | 378 | átlagosan ~6,3 ügylet/nap |
| Win rate | 46,6% | medián hozam: -$1,25 |
| Bruttó hozam | -$1 191,65 | százalékban: -1,19% |
| Becsült jutalék-teher | ~$1 080 (60 nap × ~$18) | éves alapon ~8,4% |
| Nettó hozam | ~-$2 270 | becsült (paper aggregát kissé eltérő) |
| Score range | 85,5 – 142,5 | Q1: 85,5-92,5; Q5: 95,0-142,5 |

A **nettó hozam** és a **bruttó hozam** közötti diszkrepanciát egy strukturális technikai bug ("LOSS_EXIT bracket SL" duplikált zárás), valamint a paper aggregátok két különböző számítási módja okozza; ezt a 5. fejezet részletesen tárgyalja.

## 4.2 A pontszám-prediktivitás validálása

A 60 napi adat statisztikai elemzése a kompozit pontszám és a realizált hozam közötti összefüggésre az alábbi eredményeket adta:

| Mutató | Érték | p-érték | Értelmezés |
|--------|-------|---------|------------|
| Pearson r (score vs P&L $) | -0,000 | 0,996 | **Statisztikailag null** |
| Spearman rs (score vs P&L $) | -0,007 | 0,898 | Konfirmáció: nincs monoton kapcsolat |
| Pearson r (score vs P&L %) | +0,005 | 0,929 | A scaling sem segít |

**Értelmezés**: a 378 ügylet adata alapján a kompozit pontszám **nem ad meg alpha-t**. Egy magasabb pontszámú részvény **NEM** prediktál jobb hozamot, mint egy alacsonyabb pontszámú.

## 4.3 Quintile analízis — a "magas pontszám paradoxon"

A 378 ügylet pontszám szerinti 5 egyenlő részre osztásával az alábbi mintázat tárul fel:

| Quintile | Pontszám tartomány | N | Átlagos hozam | Median | Win rate | Total hozam |
|----------|---------------------|---|----------------|--------|----------|-------------|
| Q1 | 85,5 – 92,5 | 75 | -$1,72 | -$0,96 | 48,0% | -$129 |
| Q2 | 92,5 – 94,0 | 76 | **+$11,57** | +$2,66 | **53,9%** | **+$880** |
| Q3 | 94,0 (mid) | 75 | **-$17,88** | -$1,47 | **32,0%** | **-$1 341** |
| Q4 | 94,0 – 95,0 | 76 | +$1,01 | +$4,56 | 53,9% | +$76 |
| Q5 | 95,0 – 142,5 | 76 | -$8,91 | -$6,52 | 44,7% | -$677 |

**A Q5 (a "legjobb" pontszámú részvények) total hozama -$677**, miközben a **Q2 (a közepes pontszám) +$880**. **Ez nem véletlen**: a 60 napi adat strukturálisan ezt a mintát mutatja. A "magas pontszám paradoxon" — minél magasabb a pontszám, annál rosszabb a hozam — több mintán is megerősíthető:

- A "freshness bonus" mechanizmus, amely 90 napon át a pipeline-ban nem szerepelt részvényeket 50%-kal magasabb pontszámmal jutalmazta, ezekre a részvényekre **negatív hozamot** generált — mert pont azért nem voltak korábban a pipeline-ban, mert nem voltak prediktívek.
- A "RS vs SPY" bónusz (+40 pont, most +15) momentum-chasing logikán alapul: "melyik részvény teljesített a legjobban az utolsó 3 hónapban?". Egy **bearish vagy oldalozó piacon** ez a logika a "legkevésbé esett" részvényeket választja, amelyeknek **kevés mozgástere felfelé**.
- A magas pontszámú részvények gyakran **alacsony likviditású mid-cap energy/biotech/lithium** részvények (példák: NE Noble Corp, SQM Sociedad Quimica, BUD Anheuser-Busch ADR), ahol a slippage és a likviditás-deficit elnyeli az esetleges edge-et.

## 4.4 Az alkomponens-szintű prediktivitás

A flow al-komponens dekompozíció (232 ügylet, snapshot-tal enriched mintán) az alábbi statisztikákat adja:

| Al-komponens | Pearson r | p | Spearman | Prediktív státusz |
|---------------|-----------|---|----------|-------------------|
| **PCR (put-call)** | **+0,203** | **0,002** | +0,114 | **Erős pozitív** |
| **RVOL** | **+0,147** | **0,026** | +0,103 | **Pozitív** |
| OTM Call | -0,194 | 0,003 | -0,184 | **Erős NEGATÍV** |
| Block Trade | -0,117 | 0,076 | -0,134 | Gyenge negatív |
| Buy Pressure | +0,068 | 0,301 | +0,038 | Nem szignifikáns |
| Squat Bar | +0,036 | 0,588 | +0,038 | Nem szignifikáns |
| Dark Pool % | n/a | n/a | n/a | **Inaktív (minden = 0)** |

**Stratégiai következmény**: a "klasszikus" opciós flow indikátorok (**PCR** és **RVOL**) a tényleges prediktorok, **NEM** a "modern" institutional flow indikátorok (dark pool %, block trade). Az OTM call ratio **inverz hatású** — a magas OTM call vásárlás (gyakran retail FOMO jelölő) **rosszabb hozamot** prediktál.

A jelenlegi pontozási rendszerben:
- **OTM call**: +10 pont bónusz a magas értékre — tényleges hatás: **negatív szignifikáns**, tehát **invertálni vagy kikapcsolni** indokolt.
- **PCR**: +15 pont bónusz max — a **tényleges prediktivitás miatt akár 25-30 pontig emelhető**.
- **Dark Pool**: az adat nem fut (minden ügyleten 0); az integráció valószínűleg hibás.

## 4.5 Az exit-statisztika strukturális problémája

A 378 ügylet exit-típusonként az alábbiak szerint oszlik meg:

| Exit típus | N | Átlag hozam | Total hozam | Megjegyzés |
|-------------|---|-------------|-------------|------------|
| **T1 (profit)** | 36 | +$32,95 | **+$1 186** | 9,5% hit ráta |
| **T2 (profit)** | 3 | +$286,03 | **+$858** | 0,8% hit ráta — kvázi nem létezik |
| **Trail (profit)** | 3 | +$33,39 | +$100 | Trail aktiválás ritka |
| **MOC (semi-determined)** | 280 | +$3,36 | +$940 | A pozíciók 74%-a — hatás "napi piaci irány lottó" |
| **SL (loss)** | 15 | -$78,87 | **-$1 183** | Hard stop-loss |
| **Loss Exit (loss)** | 32 | -$98,50 | **-$3 152** | Soft stop-loss (intraday -2%) |
| Nuke (manuális) | 9 | +$6,51 | +$59 | Operátori beavatkozás |

**Strukturális finding**:
- A nettó profit-oldal (T1+T2+Trail+MOC) = **+$3 084**
- A nettó loss-oldal (SL+LossExit) = **-$4 335**
- **Nettó deficit**: **-$1 251** csak az exit-mechanikából.

A **profit-küszöbök (T1, T2) kevés hit-rátájú** (10,3% összesen), de **profitábilis** ügyletenként; a **loss-mechanikák (SL, LossExit)** gyakoribbak (12,4%) és **nagyobb átlag-veszteséget** termelnek.

A **risk-reward arány az ATR-multiplikátorokból**:
- T1 = +1,25×ATR profit
- SL = -1,5×ATR veszteség
- A naiv R:R arány: 1,25 / 1,5 = **0,83 : 1** — **kedvezőtlen**.

A loss-exit mechanizmus (-2% intraday) gyakran **a bracket-stop-loss előtt** triggerel, ami egy **second-order** hatást generál: a loss-exit -2%-os küszöbe valós időben **agresszívebb védelem**, mint az 1,5×ATR alapú stop-loss, ami **növeli a hibapontot** (a piaci zaj könnyebben triggereli).

## 4.6 A heti / havi hozam-profil és a piaci kontextus

A 60 napi időszakot a következő makró-rezsimek jellemezték:
- **Március 13 — április 17**: Stagflation regime (Day 1-25), a S&P 500 ~+2% kumulatív, VIX ~17-19 átlag.
- **Április 20 — május 1**: Stagflation regime mid-stage (Day 26-40), magasabb VIX (20-22), oldalazó S&P.
- **Május 4 — május 8**: Stagflation regime late-stage (Day 41-60), VIX visszacsökkent 17-re, S&P +1-2%.

A heti hozam-profil:

| Hét | Időszak | Net P&L | Excess vs SPY | Win rate napokra |
|-----|---------|---------|---------------|------------------|
| W11-15 | márc 13 – ápr 10 | -$1 661 | -2,1% | 13/25 |
| W16 | ápr 13-17 | +$1 661 | -2,7% | 4/5 (napok) |
| W17 | ápr 20-24 | +$593 | +0,1% | 3/5 |
| W18 | ápr 27 – máj 1 | -$1 106 | -1,9% | 2/5 |
| W19 | máj 4-8 | -$728 (becsült) | -0,5%/nap | 2/5 |

**Megfigyelések**:
- A kumulatív P&L 60 napi végösszege ~-$1 460 (a paper aggregát -$1 616, korrekció a duplikált bracket bug miatt).
- A "bull rally underperform" minta: a SPY +1% fölötti napokon a rendszer rendszerszerűen **alulteljesít** (excess negatív). Ezeken a napokon a long-only intraday struktúra **nem fogja meg** a teljes piaci momentumot, mert a 3-5 koncentrált pozíció és a 6 órás holding ablak nem elég.
- A "risk-off underperform" minta a **kevésbé kifejezett**: a SPY -0,3% és +0,3% közötti "lateral" napokon a rendszer relatíve jobb teljesítményt mutat (W17 +0,13% excess átlag, W19 +0,21% és -0,18% mild risk-off napokon).
- A **W17 +0,13%** kumulatív excess a 60 napi adat **legjobb hete**; a **W18 -1,9%** a legrosszabb. A heti heterogenitás nagy.

## 4.7 Költségszerkezet és a rejtett súrlódás

A turnover-szempontú elemzés:

- **Átlagos napi ügyletszám**: 6,3 (bracket-osztások miatt ~3-5 ticker × 1,5 trade)
- **Becsült commission per trade**: ~$2,86 (IBKR Pro tier)
- **Napi commission**: ~$18
- **Havi commission**: ~$378
- **Éves commission** (240 nap): **~$8 400** — a $100 000 bázis-tőkén **8,4%** éves drag

Ezen felül:
- **Slippage**: átlagosan +0,15-0,25% entry-nél (sample: 60 napi adat). A "high-score, low-liquidity" mid-cap esetekben (NE +0,72%, QCOM +0,59%) lényegesen magasabb. Becsült éves slippage drag: **~3-5%**.
- **Az adatszolgáltatók havi költsége**: $665 (frissített 2026-05-14) — ez a $100k bázison **~8%** éves drag.
- **Az infrastruktúra fix költsége** (Mac Mini, áram, internet): elhanyagolható vagy ~$50/hó.

**Összesített éves súrlódás**: **8,4% commission + 3-5% slippage + 8% adat = ~19-21% gross drag**. A rendszernek **19-21% bruttó alpha-t** kell termelnie ahhoz, hogy break-even legyen. A 60 napi adat alapján **a rendszer ~-1,5%-os bruttó hozamot termelt**, ami a súrlódás-penaltyekkel együtt ~ **-20-22% a "mit kéne ahhoz, hogy működjön" mértékhez képest**.

> *V1.0 érték: ~15-17% gross drag (~$354/hó és ~4% adat-drag mellett). Korrekció 2026-05-14: a frissített $665/hó adat-költség ~8% drag-et eredményez.*

---

# 5. Strukturális diagnózis — mi működik, mi nem

## 5.1 A legmélyebb finding: az időtáv-paradoxon

A platform leírásában "swing trading rendszer"-ként szerepel, de **a tényleges működése 6 órás intraday momentum trading**. A különbség nem szemantikai, hanem **strukturális**:

| Karakterisztika | Igazi swing (3-5 nap) | Jelenlegi rendszer (6 óra) |
|------------------|------------------------|------------------------------|
| Time horizon | Több napi várt mozgás | Fél napi várt mozgás |
| Earnings event timing | Marginális kockázat | **Strukturális kockázat** (mert a 6 órás ablakon belül történhet) |
| Slippage hatás a hozamra | Elhanyagolható | **Komoly** (a profit-küszöbökhöz közeli %) |
| Afternoon retracement | Marginális | **Strukturális** (a holding period végén) |
| A flow signal "play out" ideje | Több napi tér | **6 óra — kompresszálva** |
| Mean reversion vs momentum | Vegyes regime-érzékeny | **Csak momentum** |

A 6 órás holding period **strukturálisan kitett** a következő piaci karakteresztikáknak:

1. **Earnings event timing**: 3 dokumentált eset 7 nap alatt (DTE 2026-05-01, AGNC 2026-05-04, BUD 2026-05-05). A platform earnings-szűrője csak 7 naptári nap előretekintéssel zár ki tickert; ha az earnings a holding period **közben** (pl. piaci nyitás előtt) történik, a pozíció kitett az event-re. **A jelenlegi mechanizmus nem kezeli** a 10-Q SEC filing eseményeket vagy az ADR earnings-ek FMP adatszolgáltatói lefedettségi hiányait.

2. **Slippage és piaci nyitás közelisége**: a 16:15 CEST entry (10:15 ET) a piaci nyitás után 45 perccel — ez az **opening range** vége környéke, amikor a piaci ár még nem stabilizálódott. Egy magas-pontszámú, alacsony likviditású mid-cap esetében (példa: NE Noble Corp, score 95.0, +0,72% slippage, $50M napi forgalom) a slippage **-$68 ügyletenként** elnyeli a kis edge-et. A **2026 áprilisi 13 pontos terv** a submit időt 15:45-ről 16:15-re tolta, ami **enyhített** ezen, de **nem oldotta meg**.

3. **Afternoon retracement (a "végére visszaesik" mintázat)**: a 60 napi adat statisztikailag mutatja a "kora délutáni peak, késő délutáni retracement" pattern-t — **bullish napokon kevésbé jelentkezik** (példa: QCOM 2026-05-07 +10,55% TP2 hit), **lateral/vegyes napokon erősebb** (példa: PTEN 2026-05-05, peak 19:11 CEST +0,76% felett, MOC -0,48% — 2,5 óra alatt 1,55% retracement). A 6 órás holding **strukturálisan** ki van téve ennek, miközben egy 3-5 napi holding kevésbé érzékeny.

4. **A "Breakeven Lock" mechanizmus túl szigorú profit-küszöbe**: az "automatikus profit-megőrző" funkció csak ~1% profit fölött aktivál (becsült küszöb a megfigyelt UEC 2026-05-06 esetből). A 60 napi adatban a trail aktivációk gyakran csak +0,5-0,7% profit körül történnek; **ezek nem kapnak soft floor-t**, és gyakran retracement-en lefutják az időszakot.

A 6 órás time horizon **NEM kompenzálja** ezeket a strukturális tényezőket; egy hosszabb (3-5 napi) horizon **jobb idő-teret adna a flow signal érvényesülésére**, kompenzálva a single-day noise-t. **Ez a leghosszabb távú stratégiai finding.**

## 5.2 A pontszám-paradoxon

A 4. fejezet adatai azt mutatták, hogy a magas kompozit pontszám **rosszabb** hozamot prediktál, mint a középső pontszám. Ennek mélyebb okai:

**Ok 1**: a kompozit **3 komponensét egyenlő szignifikancia-súllyal** keveri össze, miközben az adatok szerint **csak a flow szignifikáns** (Pearson +0,136*); a tech (-0,085) és a funda (-0,088) nem-szignifikánsak vagy gyengén negatívak. A 30%-os technikai súly és a 10%-os fundamentális súly **zajt ad a pontszámhoz**, ami elrejti a flow signal-t.

**Ok 2**: a flow score 7 al-komponense közül **csak a PCR és az RVOL prediktív** (4.4 fejezet); az OTM call **inverz hatású**; a többi nem-szignifikáns. A 7 indikátor összegzése egyetlen pontszámba **információt veszít**, és a **negatív szignifikáns OTM** pozitív bónuszt ad. **A flow signal "diluted" mintát mutat**.

**Ok 3**: a magas pontszámú részvények strukturálisan **alacsony likviditású** mid-cap energy/biotech/lithium részvények (a 4. fejezet végi felsorolás). Ezeknél a slippage **arányosan nagyobb**, és a kis edge-et felemészti.

**Ok 4**: a "RS vs SPY" bónusz (a technikai score legnagyobb komponense) **momentum-chasing** logika — a 3 hónapos legjobb teljesítményt érintő részvények **bull regime-ben** ad jó signal-t, de **vegyes/oldalozó regime-ben** valójában **negatív predictivity-t** mutat. A 60 napi (mostly Stagflation) adatban ez a finding statisztikailag igazolódik.

**Ok 5**: a **freshness bonus** mechanizmus (a 2026 áprilisi átalakítás óta inaktív, de a korábbi mintában működött) a pipeline-ba újra-belépő részvényekre 1,5× pontszám-szorzást alkalmazott. A 90 napon át pipelined-on kívüli részvények ezek után **a Q5 quintile-ba kerültek**, de a tényleges hozam **negatív** volt — **a legjobb minta példája arra, hogy az új signal nem feltétlen az erős signal**.

## 5.3 A költségszerkezet a kis edge-et elnyeli

A 4.7 szakasz szerint az éves súrlódás-teher a következő:
- Commission: ~8,4%
- Slippage: ~3-5%
- Adatszolgáltatók: ~4%
- **Total**: ~15-17% bruttó

A pontozási rendszer a 60 napi adat alapján **kvázi-zéró edge-et** termel (Pearson r ≈ 0). A flow al-komponens a **maximális realisztikus pozitív edge** ~+0,2 Pearson — ami **kis edge** statisztikai szempontból, és **könnyen elnyelhető** a súrlódással.

**A költségcsökkentés fontos stratégiai irány**:
- **Pozíciószám csökkentése** (5 fix → "csak ha érdemes", átlagosan 2-3) — a turnover ~50%-os csökkenésével a commission ~$4 200/év = 4,2% drag.
- **A 16:15 entry kissé később** (16:30-17:00 között, az opening range stabilizálódása után) — a slippage csökkenése ~30-50%.
- **Az adatszolgáltatók optimalizálása** (a 13 pontos terv 13. javaslata, NEM implementálva): bizonyos FMP hívások kihagyása a fundamentális score-hoz a 10% súly mellett.

## 5.4 Az implementációs hibák strukturálisak, nem ad-hoc

A 60 napi adat két jelentős strukturális technikai hibát hozott felszínre:

**Bug 1: a "loss-exit + bracket stop-loss" duplikált zárás (DTE 2026-05-01, SQM 2026-05-07)**

Amikor a "loss-exit" (-2% intraday) trigger-elődik, a rendszer egy MARKET SELL megbízást küld a teljes pozícióra. **Az IBKR-ben már létező bracket stop-loss megbízásokat azonban nem törli**. Amikor az ár tovább esik a bracket stop ár alá, **az IBKR autonóm módon** triggereli a stop-ot, **és short pozíciót nyit** a long zárása után.

A két dokumentált eset:
- DTE 2026-05-01: 4-split, leftover -130 short, valós kár ~-$988
- SQM 2026-05-07: 3-split, leftover -91 short, valós kár ~-$425

**Két alkalom 6 nap alatt = strukturális bug**, nem ad-hoc edge case. Egy implementációs javítás (a meglévő bracket order-ek explicit kancellálása a loss-exit előtt) megoldja, ~30-45 perces fejlesztés.

**Bug 2: az earnings calendar adatszolgáltatói hiányai**

A 60 napi időszak alatt 3 különböző earnings event "lyukad le" az earnings-szűrőn:
- DTE (2026-05-01): a fundamentális szolgáltató (FMP) earnings calendar-jában 2 jó beat / 4 quarter szerepelt — a strict <0,5 küszöb nem aktiválódott.
- AGNC (2026-05-04): 10-Q SEC filing event, nem earnings release. A jelenlegi szűrő csak earnings release-eket vesz figyelembe.
- BUD (2026-05-05): európai ADR earnings — az FMP-ben **a mai dátum** entry **NEM létezik**, csak a következő (~3 hó) várt earnings dátum. Az ADR earnings az FMP rendszerében hiányos.

**3 strukturális adat-rés egy hét alatt** azt jelzi, hogy az earnings-szűrés **nem robosztus** ADR-ekre és nem-earnings binary event-ekre. **Megoldás**: alternatív adatforrás (Polygon `tickers/{ticker}/events` vagy SEC EDGAR), vagy egy hard-coded ADR blacklist a top 50-100 európai/ázsiai ADR earnings dátumával.

**Mind a két bug** P1 prioritású backlog idea-ként rögzítve van. A hatás összesen **kb. -$1 500** a 60 napi adatban, ha ezeket az eseteket korrekt kezeléssel zártuk volna.

## 5.5 Az emberi felülbírálás strukturális hiánya

A 16:15 CEST cron-folyamat a megbízásokat **azonnal** beadja az IBKR-be, **emberi felülbírálás nélkül**. Ezt a Linda Raschke-féle "discretionary judgment + systematic execution" filozófia szerint **szándékosan így van**: a discretionary réteg **a fejlesztési iterációkban** működik, **nem a real-time submitben**.

**De** a 60 napi adat azt mutatja, hogy bizonyos esetekben **az emberi felülbírálás megelőzhetné a strukturális problémákat**:
- Az ADR earnings (BUD) esetén, ha a kereskedő reggel látja, hogy a részvény pre-market +9% (ami earnings BEAT-re utal), kihagyhatja a pozíciót.
- A 10-Q SEC filing események (AGNC) esetén egy gyors filing-feedjel ellenőrzés megelőzhetné a -$380 veszteséget.

A jelenlegi rendszerben **nincs "kill switch"** a 16:15 cron és az IBKR submit között. **Egy 5-15 perces emberi review-ablak** (16:00-16:15 CEST) érdemleges, de **strukturálisan a hobbiprojekt szintjén nem reális** a portfolio manager napi rendelkezésre állását igénylve.

A javaslat **stratégiai szinten**: ha a rendszer élő pénzes kereskedésre kerül, **egy automatizált "pre-submit check" réteg** (10-Q feed, ADR earnings calendar, news sentiment) **plusz** egy **mobile push-notification a pozíciókról a submit előtt** — egy 2-5 perces "veto-ablak" minimális emberi friction-nel.

---

# 6. A 2026 áprilisi újratervezés mérlege

## 6.1 A 13 pontos terv eredete

2026 április 11-én egy strukturált belső elemzés (a 60 napi paper trading első 30 napjának adatai alapján) 13 konkrét javaslatot fogalmazott meg a rendszer teljesítményének javítására. A javaslatok alapja:
- A scoring validation eredménye (Pearson r ≈ 0)
- A quintile analízis "magas pontszám paradoxon" mintája
- Az exit-statisztika 90% MOC dominanciája és a fordított R:R aránya
- A flow al-komponens dekompozíció (akkori) hipotézise

## 6.2 Implementációs státusz (2026-05-08 állapot)

A 13 pontos tervből **8 elem teljesen implementálva**, **1 részben**, **4 nem implementálva**. A részletes mátrix:

| # | Javaslat | Cél | Tényleges állapot | Státusz |
|---|----------|-----|--------------------|---------|
| 1 | Frissesség-bónusz kikapcsolása | 1,5 → 1,0 | 1,0 | ✓ |
| 2 | RS vs SPY bónusz csökkentése | 40 → 15 | 15 | ✓ |
| 3 | Pontozási súlyok átrendezése (flow-first) | flow 0,40→0,60, funda 0,30→0,10 | 0,60 / 0,10 / 0,30 | ✓ |
| 4 | T1 emelése | 0,75 → 1,5 ATR | 1,25 ATR | (!) Részben |
| 5 | T2 csökkentése | 3,0 → 2,0 ATR | 2,0 ATR | ✓ |
| 6 | Bracket-osztás megfordítása | 33/67 → 50/50 | 50/50 | ✓ |
| 7 | Dinamikus pozíciószám | "csak ha érdemes", max 5 | Fix 5, küszöb-paraméter rögzítve de inaktív | ✗ |
| 8 | Submit idő tolása | 15:45 → 16:15 | 16:15 | ✓ |
| 9 | MMS sizing kikapcsolása | True → False | False | ✓ |
| 10 | Call Wall T1 kikapcsolása | call wall override → mindig ATR | NEM kikapcsolva | ✗ |
| 11 | VWAP guard egyszerűsítése | REJECT + REDUCE → csak REJECT | NEM egyszerűsítve | ✗ |
| 12 | Multiplier chain egyszerűsítése | 7 → 3 multiplier | 4 aktív (M_VIX, M_GEX, M_target, M_contradiction) | (!) Részben |
| 13 | Flow al-komponens dekompozíció | Elemzés kifutottatás | **LEFUTOTT** (kritikus finding) | ✓ |

## 6.3 A nem-implementált elemek és potenciális hatása

A 4 teljesen nem-implementált elem (7, 10, 11, 12) közül **a 7. (dinamikus pozíciószám)** a leglényegesebb stratégiai finding-ot képviseli:

**Dinamikus pozíciószám (7. pont)** — a 13 pontos terv ezt a javaslatot a rendszer "fundamentális karakterváltoztatásaként" jellemezte. A jelenlegi mechanizmus **napi 5 pozíciót nyit kötelezően** (vagy 4-3, ha BMI Momentum Guard / Cross-Asset Regime aktív), függetlenül attól, hogy hány részvény ér el az "elfogadható" pontszám-küszöböt (85+).

A 60 napi adat azt mutatja, hogy **2 nap egymás után csak 3 ticker** ütötte át a 85-os küszöböt érdemleges flow score-ral (W19 D3 és D4: ERIC, CDNS, UEC csütörtökön + RMBS, QCOM, SQM pénteken). A jelenlegi rendszer **erőltette** az 5 pozíciót, ami **alacsonyabb minőségű ticker-ek beadását** jelenti.

A javasolt módosítás:
```
max_positions = min(5, len([c for c in candidates if c.combined_score >= 85]))
```

Ha 0 ticker ér el a küszöböt → **NEM kereskedünk azon a napon**. Ez egy **fundamentális filozófiai váltás**: a jelenlegi rendszer "mindig kereskedik", a javasolt "csak ha érdemes". A becsült hatás: a turnover ~30-40%-os csökkenése + a minőségi szelekció erősödése = **havi ~0,5-1% alpha-javulás**.

**Multiplier chain részleges egyszerűsítése (12. pont)** — a 7 multiplier-ből 4 aktív; az M_flow, M_insider, M_funda, M_utility 1.0 fix lett, az M_VIX, M_GEX, M_target megmaradt, és **2026 májusban hozzáadódott egy új M_contradiction multiplier**. A 13 pontos terv 3 aktív multiplier-t javasolt. A jelenlegi 4 aktív + 1 új = **5 aktív multiplier**. Az M_contradiction az első élő hét adata szerint **irányhelyes** (a 4/5 aktiválás veszteséges pozíciót szignáltatott), de a 60 napi adat alapján **statisztikailag kis n**.

**Call Wall T1 kikapcsolás (10. pont)** és **VWAP guard egyszerűsítés (11. pont)** — ezek **technikai egyszerűsítések**, amelyeknek a hatása **kis-közepes**. A 60 napi adatban időnként megfigyelhetők "azonnali T1 trigger" esetek (entry után 1-2 perccel a T1 az árbörzébe kerül), amelyek a Call Wall override-ból eredhetnek. Hatás-becslés: havi ~0,1-0,2% alpha-javulás.

## 6.4 A 13. pont (flow al-komponens dekompozíció) megcáfolja az eredeti hipotézist

A 13 pontos terv a 13. javaslatban felvetette, hogy a flow score 7 al-komponense közül a **dark pool % és a buy pressure** valószínűleg az "institutional flow edge" hordozója, és érdemes a súlyukat felfelé átkalibrálni.

Az **elemzés tényleges eredménye** (a 4.4 fejezet adatai szerint) **megcáfolja** ezt a hipotézist:
- **Dark pool %**: az adat 232/232 ügyleten 0 — **nem fut**, vagy hibás integráció.
- **Buy pressure**: Pearson r +0,068 (nem szignifikáns).
- **A tényleges prediktorok**: PCR (+0,203\*\*) és RVOL (+0,147\*) — **klasszikus opciós flow indikátorok**, NEM "modern institutional flow".
- **OTM call**: -0,194\*\* — **NEGATÍV szignifikáns**, vagyis a magas OTM call jelzés **rosszabb** hozamot prediktál.

**Ez egy fontos epistemológiai pont**: a 2026 áprilisi terv **ad-hoc hipotézis** alapján priorizált; a tényleges adat-driven elemzés **más eredményt** hoz. A jelenlegi pontozási rendszer **ezt a finding-ot nem tükrözi**: az OTM call továbbra is pozitív bónusz, a PCR súlya nem emelt fel.

## 6.5 Az újratervezés tényleges hozam-hatása

A 8 implementált elem **összesített hatása** a 60 napi adatban kevert:
- **W11-W15** (átalakítás előtti, ~25 nap): -$1 661 / 25 nap = **-$66/nap**
- **W16-W19** (átalakítás utáni, ~35 nap): +$420 / 35 nap = **+$12/nap** (becsült)

A **hozam-trend javult**, a kumulatív veszteség **stabilizálódott**, **de** az átalakítás **nem hozott tartós pozitív alpha-t**. A 4 nem-implementált elem (köztük a stratégiai szempontból legfontosabb dinamikus pozíciószám) **jelentős további hatást ad** a tervek szerint.

---

# 7. Három stratégiai irány — döntéselőkészítés

A 60 napi paper trading és a strukturális diagnózis alapján három különböző radikalitású továbblépési útvonal vázolható. **A három opció kölcsönösen nem zárja ki egymást** — a kombinált megközelítés (A + C, B fázisos) a legrealisztikusabb stratégia.

## 7.1 Opció A — Inkremeális finomítás (status quo + a hét backlog idea megvalósítása)

**Karakter**: a 2026 áprilisi 13 pontos terv befejezése + a 2026 májusi paper trading hét során azonosított 7 backlog idea megvalósítása.

**Konkrét teendők**:

| Prioritás | Tétel | Hatás | Erőfeszítés |
|------------|-------|-------|-------------|
| P1 | Loss-exit / bracket stop-loss duplikált zárás bugfix | ~$200-400/hó visszanyert veszteség | ~30-45 min |
| P1 | 10-Q SEC filing exclusion (AGNC eset) | 10-Q event-ek prevenciója | ~2-3 óra |
| P1 | ADR earnings adatforrás javítása (BUD eset) | ADR earnings event prevenció | ~3-4 óra |
| P2 | Breakeven Lock profit-küszöb csökkentés (1% → 0,5%) | Trail aktivációk megőrzése | ~10-15 min |
| P2 | T1 cél revízió (1,25 → 1,0×ATR) | TP1 hit ráta növekedés | ~30 min |
| P3 | Phase 4 snapshot teljes ticker-tábla mentése | Kvantitatív elemzés alapja | ~30-45 min |
| P3 | Magas-pontszám alacsony-likviditás szorzó | Slippage csökkentés | ~1 óra |
| **+ a 4-11-i terv 4 nem-implementált eleme** | Dinamikus pozíciószám, Call Wall T1 kikapcsolás, VWAP egyszerűsítés, multiplier chain | ~1-2% havi alpha | ~3-4 óra |
| **+ flow al-komponens-rekalibráció** | OTM call invertálás, PCR súly emelés, dark pool integráció ellenőrzése | ~0,3-0,5% havi alpha | ~3-4 óra |

**Becsült várt hatás**: ~+0,5-1% havi alpha javulás (bruttó, súrlódás előtt). A 60 napi -1,46% kumulatív hozamot **break-even közelébe** hozhatja.

**Kockázat**: alacsony. Minden módosítás paraméter-szintű vagy lokalizált kódváltozás. A 13 pontos terv 8 elemet már bizonyítottan kezelt; a maradék 5 a logika folytatása.

**Időigény**: 4-6 hét fejlesztés + 4 hét új paper trading validáció = **kb. 2-3 hónap** Day 90 értékeléshez.

**Hátrány**: az inkremeális finomítás **NEM oldja meg** a 5.1 fejezetben tárgyalt "időtáv-paradoxont". Ha a 6 órás holding strukturálisan rossz (ami a 60 napi adat alapján valószínű), az inkremeális finomítás **stabilizálja a -1 — 0% havi hozamot**, **de nem ad pozitív alpha-t**.

## 7.2 Opció B — Időtáv-átalakítás (multi-day swing architektúra)

**Karakter**: a 6 órás holding period kiterjesztése 3-5 napos hold időtávra. **Ez a stratégia fundamentális architektúra-változtatása**, nem inkremeális finomítás.

**Konkrét lépések**:

**Fázis 1 (R&D, 1-1,5 hónap)** — kvantitatív backtest:
- A meglévő 60 napi pipeline-snapshot adatokból visszaszámítani: ha a kiválasztott részvényeket **3 napig**, **5 napig**, **7 napig** hold-oltuk volna (T1/T2 ATR célokat ennek megfelelően skálázva), milyen hozamot termeltek volna?
- Az analízis a **flow signal "play out" idő** szempontjából: a PCR és RVOL alapú edge **több napon keresztül** érvényesül-e?
- A "tartás-kockázat" számítása: overnight gap kockázat, intraday news event kitettség, korreláció szektorok között.

**Fázis 2 (új scoring és holding mechanika, 3-4 hét)**:
- Új pontozási logika **multi-day flow momentum-ra** (3 napi átlag PCR és RVOL, 3 napi szektor-momentum, 3 napi GEX trend).
- **Dinamikus holding period** (3-5 nap, a flow signal eltűnéséig vagy az ATR-alapú profit/loss küszöbökig).
- Új exit-mechanika: piaczárás-rendelés helyett **napi monitoring + exit-trigger feltételek**.

**Fázis 3 (új paper trading futás, 2-3 hónap)**:
- Új 60-90 napi paper trading az új holding időtávval.
- Day 90 eredmény-mérés.

**Becsült várt hatás (kvalitatív)**:
- **Pozitív tényezők**: a flow signal "play out" hosszabb időn keresztül, kevesebb intraday noise, csökkent earnings event-kitettség (mert a többnapi pozíciók gyakran már átestek az event-en), kevesebb turnover/jutalék.
- **Negatív tényezők**: overnight gap kockázat, hosszabb hold idő alatt nagyobb event-tér, korreláció-koncentráció növekedése, esetleg kevesebb kvalifikáló ticker.
- **Becsült havi alpha**: **+0,5 — +2%** (bruttó, súrlódás előtt) — kvalifikálandó a backteszttel.

**Kockázat**: közepes-magas. Új architektúra = új bug-felület, új paper trading futás = új learning curve.

**Időigény**: **3-6 hónap** összesen (R&D + új paper).

**Stratégiai érték**: ez a **legmélyebb finding** mentén dolgozik. Ha a 60 napi adat azt sugallja, hogy a 6 órás holding strukturálisan rossz, akkor **az időtáv kiterjesztése a leghatékonyabb módja az alpha-növelésnek**. **De**: a backtest eredménye **nem garantált**; ha a kvantitatív elemzés azt mutatja, hogy a multi-day hold sem ad érdemleges alpha-t, akkor az opció **NEGATÍV** eredményű.

## 7.3 Opció C — Hibrid kísérletek (mean reversion overlay, opciós flow priorítás)

**Karakter**: az "A" útvonalon belül néhány **kis kockázatú, kis idő** kísérlet, amelyek a meglévő architektúrára overlay-ként alkalmazódnak.

**Konkrét kísérletek**:

**C.1 — Mean reversion overlay (1-2 hét)**:
- Egy ATR-alapú "túl messze ment" trigger overlay: ha az intraday profit > 2,5×ATR a piaci nyitás óta, alkalmazni egy szigorúbb trail (1×ATR helyett 0,5×ATR).
- A logika: az erős momentum napokon (mint a QCOM 2026-05-07 +10%-on) ez **NEM aktiválódik** (mert a profit a teljes piacival együtt mozog), a vegyes/oldalozó napokon (mint a PTEN 2026-05-05 +0,76%) **megőrzi a profitot**.
- Várt hatás: havi ~+0,1-0,3% alpha.

**C.2 — Opciós flow priorítás (1-2 hét)**:
- A flow score súlyait átrendezni a dekompozíció finding-jai szerint: PCR súly +50%, RVOL súly +30%, OTM call invertálás (a magas OTM call **csökkenti** a pontot), block trade súly nullázás.
- **Az új súlyok validálása az utolsó 60 napi snapshot adaton** (nem előrelátó becslés, hanem múltbeli rekalibráció).
- Várt hatás: havi ~+0,3-0,5% alpha.

**C.3 — Időablak-shift (kis, 1 hét)**:
- A 16:15 entry tolása **16:30-17:00 közé** (az opening range stabilizációs vége után).
- Várt hatás: a slippage csökkenése ~30-50%; havi ~+0,2-0,3% alpha.

**Becsült várt hatás (összesen, C.1 + C.2 + C.3)**: **+0,6 — +1,1% havi alpha**.

**Kockázat**: alacsony. Mind a három kísérlet **paraméter-szintű** vagy **overlay-jellegű**, könnyen visszavonható.

**Időigény**: **2-4 hét** kombinálva. A C kísérletek **párhuzamosan futtathatók** az A inkremeális útvonallal.

## 7.4 Az opciók összehasonlító mátrixa

| Szempont | Opció A — Inkremeális | Opció B — Multi-day swing | Opció C — Hibrid kísérletek |
|----------|------------------------|----------------------------|------------------------------|
| Várt havi alpha | +0,5% — +1% | +0,5% — +2% (kvalifikálandó) | +0,6% — +1,1% |
| Időigény | 2-3 hónap | 3-6 hónap | 2-4 hét |
| Kockázat | Alacsony | Közepes-magas | Alacsony |
| Architektúra-változás | Nincs | Fundamentális | Overlay |
| Strukturális problémát old meg | Részben (költség, dinamikus pozíció) | **Igen** (időtáv-paradoxon) | Részben (időablak, scoring) |
| Paper trading szükséges? | Folytatás | Új 60-90 nap | Folytatás |
| Visszafordítható? | Igen | Részben (az új arch. nehéz lenne visszaadaptálni) | Igen |

## 7.5 Az ajánlott útvonal: A + C kombináció + B párhuzamos R&D

A három opció **NEM zárja ki egymást**. A gyakorlati ajánlás:

**Lépés 1 (most — Day 90)**: Opció A és Opció C **párhuzamos megvalósítása**. Az A útvonal a 13 pontos terv befejezése + a 7 backlog idea kezelése. A C útvonal a 3 hibrid kísérlet — különösen a flow score rekalibrációja a dekompozíció finding-jai mentén. Ez **2-3 hónap fejlesztés + paper trading** = Day 90 értékelés.

**Lépés 2 (párhuzamosan, R&D fázis)**: Opció B **első fázisa** — a kvantitatív backtest a meglévő 60 napi adaton. **Ez NEM aktivál új paper trading futást**, csak elemzést. Az időigénye 1-1,5 hónap, és a Day 90-ig **döntésjavaslat lesz arra**, hogy érdemes-e a B útvonalat folytatni (új scoring + paper trading).

**Lépés 3 (Day 90 értékelés)**:
- Ha az A + C eredmény **pozitív havi alpha** (+0,5% +): **élő pénzes kereskedés indítása opció**, $10k tőkével (a 2026-04-28 keret szerint).
- Ha az A + C eredmény **0 körül vagy negatív, B backtest pozitív**: a B útvonal teljes kifejlesztése (új scoring + új paper trading), Day 150-180 körüli újraértékelés.
- Ha **mindkét útvonal negatív**: graceful exit — a projekt hobbi-státuszba, a tanulságok rögzítése, esetleg a MID makró-rezsim érzékelő rendszer önállóan használható portfolio context layer-ként.

---

# 8. Javasolt ütemterv és kockázatkezelés

## 8.1 Az ajánlott útvonal időbeli felbontása

| Időablak | Tevékenység | Várt eredmény |
|----------|-------------|----------------|
| Day 60-65 (most) | Day 63 értékelés a meglévő keret szerint; várt kimenet: paper folytatás | Folytatás vs leállítás döntés |
| Day 60-90 (4 hét) | Opció A megvalósítása (5 nem-implementált elem, 7 backlog idea); Opció C kísérletek párhuzamosan | ~2-3 hónap fejlesztés (~30-50 fejlesztői óra) |
| Day 70-90 (3 hét) | Opció B Fázis 1: kvantitatív backtest a meglévő adaton | Backtest eredménye → döntés |
| Day 90 | Day 90 értékelés: A + C eredmény + B backtest | Stratégiai döntés (3 ágra) |
| Day 90-120+ | Az ágválasztás szerint: élő kereskedés / B teljes kifejlesztés / graceful exit | |

## 8.2 A pénzügyi kockázat kezelése

A jelenlegi paper trading **nem visel tényleges pénzügyi kockázatot**, csak az adatszolgáltatói költséget (~$665/hó, frissített 2026-05-14). A tényleges pénzügyi kitettség az **élő pénzes kereskedés indításakor** jelenik meg.

A 2026 áprilisi döntéshozási keret (Day 63 framework) a következő kritériumokat határozza meg:
- **ÉLESÍTÉS**: Day 63 kumulatív > +$3 000 ÉS 20+ napi nem-Stagflation regime + +1% kumulatív excess vs SPY → $10 000 tőke élő kereskedés.
- **LEÁLLÍTÁS**: 20+ napi VIX > 18 + < -1,5% kumulatív excess → projekt archív.
- **PAPER FOLYTATÁS** (default): a fenti két feltétel között.

A 2026-05-08 állapot szerint a **default kimenet a legvalószínűbb**: kumulatív ~-1,46%, 9 napi excess átlag -0,54%/nap, VIX 17,1 stabil, leállítási feltétel inaktív.

## 8.3 A javasolt élesítési kritérium módosítása

A 2026 áprilisi keret **+$3 000 / 60 nap = +5% / 60 nap = +30% éves bruttó hozam-cél** túl ambíciózus. A professzionális hedge fund szektor top decile szint ~+15-20% éves alpha **adózás és súrlódás után**. A 2026 áprilisi diszkussziókban Tamás (a projekt vezetője) maga elismerte, hogy a "havi 1,5-2% alpha" túl magas; a realisztikus első cél: **havi 0,75-1% alpha**.

A jelen dokumentum azt javasolja, hogy az **élesítési kritérium revíziója**:
- **Régi**: Day 63 kumulatív > +$3 000.
- **Új**: Day 90 kumulatív > +$2 500 (~+2,5% / 90 nap = ~+10% éves) ÉS **a kumulatív excess vs SPY > +1%** ÉS **20+ napi nem-Stagflation regime**.

A 30 napi időablak-tolás (Day 63 → Day 90) lehetővé teszi:
- Az opció A + C megvalósítását
- Az opció B backtest-jét
- A stabil értékelést

## 8.4 A kockázatcsökkentési struktúrák

Az élő kereskedés indítása (ha indul) az alábbi kockázatcsökkentési rétegekkel:

1. **$10 000 tőke** — a paper trading 100k-ról 10k-ra csökkenése **automatikus 10×-es kockázatcsökkenés**. A 0,7% ügyletkockázat 70 USD/ügylet, ami kezelhető.
2. **Circuit breaker** — a 3% account drawdown automatikusan leállítja a rendszert.
3. **Daily notional limit** — max $25 000 napi notional, max $200 000 napi total, max $25 000 single-position.
4. **Pre-submit notification** — egy automatizált rendszer mobile push-tal jelzi a tervezett pozíciókat 5 perccel a submit előtt; ha a portfolio manager nem reagál, a pozíció automatikusan beadódik (default: igen).
5. **Heti review** — a tényleges teljesítmény heti review-ja, **strukturált döntésekkel** a következő hét stratégiájáról.

## 8.5 Graceful exit forgatókönyv

Ha a 60-90 napi adatok azt mutatják, hogy **sem a A+C, sem a B útvonal nem ad pozitív alpha-t**, a projekt **graceful exit** opciója:

1. **Az infrastruktúra megőrzése** adatgyűjtési célokra (paper trading folytatása, scoring history).
2. **A makró-rezsim érzékelő (MID — Macro Intelligence Dashboard) önálló használata** mint portfolio context layer — a GIP regime classification, a yield curve monitor, a cross-asset flow monitor önállóan értékesek lehetnek diszkrecionális döntéshozatalban.
3. **A tanulságok rögzítése** — a 60-180 napi paper trading **negatív eredménye is értékes tanulság** a piaci hatékonyság, a pontozási rendszerek limitációi, és a kvantitatív momentum/flow trading nehézségeiről.
4. **A projekt archiválása** — git history megőrzése, dokumentáció lezárása, a kód továbbra is futtatható (de aktív kereskedés nélkül).

A graceful exit **NEM "kudarc"**, hanem **strukturált tanulság-rögzítés**. A 60+ napi paper trading **valós adatokat** szolgáltatott, amelyek a következő iteráció (akár egy másik kvantitatív rendszer) **fundamentumát képezhetik**.

---

# 9. Függelékek

## 9.1 A 2026 áprilisi 13 pontos terv tételenkénti státusza

(Részletes táblázat — lásd 6.2 fejezet)

## 9.2 A makró-rezsim érzékelő (MID) projekt rövid bemutatása

A vizsgált rendszer mellett egy másik, önálló projekt is fejlődik a környezetben: a **MID — Macro Intelligence Dashboard**. Ez **NEM kereskedési rendszer**, hanem **makró-rezsim azonosító keretrendszer**. A MID célja: "illuminate, don't instruct" — a makró-környezet (Growth, Inflation, Policy) **strukturált értelmezése**, amely **diszkrecionális döntéshozatalt** támogat.

A MID főbb moduljai:
- GIP Engine (Growth + Inflation + Policy → 8-rezsim klasszifikáció: Goldilocks, Reflation, Overheating, Stagflation, Deflation, Disinflation, Recovery, Inflationary Boom)
- Recession Probability Indicator (Sahm rule, yield curve, credit, M2)
- Yield Curve + Fisher Decomposition + 6-fázis regime
- Cross-Asset Flow Monitor (vol-scaled momentum, korrelációs mátrix, szektor-rotáció)
- FX GIP Differentials (USD/JPY, EUR/USD)
- Positioning (COT z-scores, GEX, PCR, VIX term structure)
- Catalyst Engine (esemény-katalógus, érzékenységi mátrix)
- Situation Room (Edge Finder, Attribution, Daily Briefing, Institutional Lens)
- ETF X-Ray (40 ETF Composite Alignment Score)
- EU/HU Macro Layer (Eurostat, MNB)

A MID **napi shadow snapshot**-okat produkál a kereskedési rendszer részére, amelyek **eddig nem voltak integrálva** a kereskedési döntésekbe. A 2026 májusi paper trading során **megfigyelhető volt**, hogy a MID rezsim-osztályozása (Stagflation, Late-stage Day 18+) **konzisztens** a szubjektív piaci értékeléssel.

**Stratégiai szerep**: a MID **portfolio context layer-ként használható**. Például: Stagflation regime-ben a kereskedési rendszer pozíció-méretezése **kisebb**, vagy a sector-rotation szabályok **defenzívebb sektor-súlyokat** alkalmaznak. **A MID és a kereskedési rendszer közötti integráció a következő iteráció (B opció vagy az élő kereskedés) kulcs eleme lehet**.

## 9.3 Glosszárium

| Rövidítés | Jelentés |
|-----------|----------|
| ATR | Average True Range — átlag valós napi ár-tartomány, volatilitás-mérés |
| BMI | Big Money Index — az intézményi vásárlási nyomás napi mérőszáma |
| EWMA | Exponentially Weighted Moving Average — exponenciálisan súlyozott mozgóátlag |
| GEX | Gamma Exposure — az opciós piacvezetők gamma-pozíciójának összesítése |
| HRP | Hierarchical Risk Parity — hierarchikus kockázat-paritáson alapuló portfolio-optimalizáció |
| MOC | Market-on-Close — piaczárás-rendelés |
| OTM | Out-of-The-Money — opciók, amelyek strike ára kívül esik az aktuális árfolyam-tartományon |
| PCR | Put-Call Ratio — put és call opciók forgalmi aránya |
| RVOL | Relative Volume — aznapi forgalom az átlaghoz viszonyítva |
| RS vs SPY | Relative Strength vs SPY — relatív teljesítmény az S&P 500-hoz képest |
| SL | Stop-Loss — automatikus veszteség-zárás |
| SMA | Simple Moving Average — egyszerű mozgóátlag |
| TNX | 10-Year Treasury Note Yield — 10 éves államkötvény-hozam |
| TP1 / T1 | Take-Profit 1 — első profit-küszöb |
| TP2 / T2 | Take-Profit 2 — második profit-küszöb |
| VAR | Value-at-Risk — kockázatképesség statisztikai becslés |
| VIX | Volatility Index — az S&P 500 30 napi várt volatilitása |
| VWAP | Volume-Weighted Average Price — volumennel súlyozott átlagár |

## 9.4 A pénzügyi és statisztikai megjelölések

- **Pearson r**: lineáris korrelációs együttható (-1 — +1)
- **Spearman rs**: rang-korrelációs együttható (-1 — +1)
- **p-érték**: statisztikai szignifikancia-érték (kisebb = szignifikánsabb)
- **`*`**: p < 0,05 (5%-os szignifikancia)
- **`**`**: p < 0,01 (1%-os szignifikancia)
- **Q1, Q2, ... Q5**: 5 egyenlő részre osztott quintile a pontszám szerint
- **alpha**: a piaci hozamtól független excess hozam

## 9.5 A teljes scoring validation tábla

(Az 1. fejezet adatai részletesebb formában — lásd `docs/analysis/scoring-validation.md`)

| Pontszám tartomány | N | Win rate | Átlag hozam | Median hozam | Átlag % | Total hozam |
|--------------------|---|----------|-------------|---------------|---------|-------------|
| 89-91 | 12 | 58,3% | +$43,92 | n/a | +2,17% | +$527 |
| 91-93 | 70 | 44,3% | -$7,17 | n/a | -0,17% | -$502 |
| 93-999 | 286 | 47,6% | -$2,84 | n/a | +0,01% | -$813 |

Quintile-ek (5 egyenlő rész):
| Quintile | Pontszám | N | Átlag hozam | Win rate |
|----------|----------|---|-------------|----------|
| Q1 | 85,5 — 92,5 | 75 | -$1,72 | 48,0% |
| Q2 | 92,5 — 94,0 | 76 | **+$11,57** | 53,9% |
| Q3 | 94,0 (mid) | 75 | **-$17,88** | 32,0% |
| Q4 | 94,0 — 95,0 | 76 | +$1,01 | 53,9% |
| Q5 | 95,0 — 142,5 | 76 | -$8,91 | 44,7% |

## 9.6 Az exit-statisztika részletei

(A 4.5 fejezet adatai részletesebben)

| Exit típus | N | Átlag P&L | Átlag % | Total P&L | Win rate (becsl.) |
|-------------|---|-----------|---------|-----------|---------------------|
| TP1 | 36 | +$32,95 | +1,44% | +$1 186 | 100% |
| TP2 | 3 | +$286,03 | +10,49% | +$858 | 100% |
| Trail | 3 | +$33,39 | +0,81% | +$100 | 100% |
| MOC | 280 | +$3,36 | +0,07% | +$940 | ~50% |
| SL | 15 | -$78,87 | -1,74% | -$1 183 | 0% |
| Loss Exit | 32 | -$98,50 | -2,12% | -$3 152 | 0% |
| Nuke | 9 | +$6,51 | -0,11% | +$59 | n/a |

**Profit-oldal nettó**: +$3 084 (T1+T2+Trail+MOC)
**Loss-oldal nettó**: -$4 335 (SL+LossExit)
**Strukturális deficit**: -$1 251 — a 60 napi -$1 191 hozam ~1:1-ben az exit-mechanikából.

## 9.7 A flow al-komponens dekompozíció részletei

(A 4.4 fejezet adatai részletesebben)

| Komponens | Pearson r | p | Spearman rs | p | Avg score | Q5-Q1 spread |
|-----------|-----------|---|-------------|---|-----------|--------------|
| **PCR** | **+0,203** | **0,002** | +0,114 | 0,082 | 11,19 | +$17,83 |
| **RVOL** | **+0,147** | **0,026** | +0,103 | 0,118 | 40,91 | +$44,14 |
| **OTM call** | **-0,194** | **0,003** | -0,184 | 0,005 | 7,20 | -$58,37 |
| Block trade | -0,117 | 0,076 | -0,134 | 0,042 | 0,13 | -$44,21 |
| Buy pressure | +0,068 | 0,301 | +0,038 | 0,563 | 18,97 | -$10,43 |
| Squat bar | +0,036 | 0,588 | +0,038 | 0,560 | 0,13 | n/a |
| Dark pool % | n/a | n/a | n/a | n/a | 0,00 | n/a |

**Stratégiai következmény**: a PCR és RVOL **felfelé kalibrálva**, az OTM call **invertálva vagy kikapcsolva**, a dark pool **debug-olva** — együttesen ~+0,3-0,5% havi alpha-javulás.

## 9.8 A BMI és makró rezsim 60 napi mérlege

| Hét | BMI átlag | VIX átlag | SPY heti hozam | Stagflation regime | IFDS heti P&L |
|-----|-----------|-----------|----------------|---------------------|----------------|
| W11-13 | 65 (YELLOW) | 18 | -1,2% | Igen | -$1 200 |
| W14-15 | 70 (YELLOW) | 17 | +1,5% | Igen | -$461 |
| W16 | 68 | 17 | +0,5% | Igen | +$1 661 |
| W17 | 72 | 18 | +0,8% | Igen | +$593 |
| W18 | 65 | 19 | +0,3% | Igen | -$1 106 |
| W19 | 70 | 17,5 | +1,1% | Igen | -$728 |

**A BMI az időszakban végig YELLOW** (50-80% sávban), ami a "normál long" stratégiát eredményezi. **Sosem volt GREEN (≤25%) sem RED (≥80%) regime**. A SHORT ág (a "zombie" universe) **inaktív volt** a teljes időszakban.

---

**A dokumentum vége.**

A jelen anyag **döntéselőkészítő**, nem **döntés**. A három stratégiai irány (A — Inkremeális, B — Multi-day swing, C — Hibrid kísérletek) **nem zárja ki egymást**, és **a kombinált útvonal** (A + C, B párhuzamos R&D) **a legrealisztikusabb** a 2026 májusi 60 napi paper trading adatok alapján.

A javasolt következő lépés: a **csapat-megvitatás**, ahol a portfolio menedzser, a kvant-fejlesztő, és a befektetési bizottság a három opciót **strukturált formában értékelheti**, és a Day 90 felülvizsgálatig **az ütemterv véglegesíthető**.
