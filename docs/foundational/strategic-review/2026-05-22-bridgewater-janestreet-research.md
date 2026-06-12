# Bridgewater All Weather + Jane Street 0DTE Flow

**Strategic Research — Modern intézményi methodology-k sole operator szempontból**

**Készült:** 2026-05-22 (W21, IFDS Swing Pivot Phase 1)
**Kontextus:** IFDS Day 63 milestone lezárva, swing pivot reset W21–W30
**Cél:** A klasszikus flow + GEX + dark pool scoring null edge eredménye után (Pearson r ≈ 0, p=0.996) strukturális tanulság modern intézményi methodology-kból
**Hossz:** ~10 ezer szó
**Javasolt path:** `docs/strategic-review/2026-05-22-bridgewater-janestreet-research.md`

---

## 0. Framing — Miért épp ez a két methodology

A 2026-05-08 strategic review (`2026-05-08-strategic-review-mathematical.md`) megmutatta, hogy az IFDS scoring rendszerben két strukturális defektus van:

1. **A "kompozit" hipotézis nem igazolható.** A 7-komponensű flow + 3-komponensű tech + 5-komponensű fundamental aggregálás után Pearson r ≈ 0. Bonferroni-korrekció után csak két komponens éli túl: PCR (+0.203) és OTM call inverz (-0.194). A többi vagy zaj, vagy ellentétes irányú.

2. **Az időhorizont-paradoxon.** A 6 órás holding alatt a flow signal nem tudja érvényesíteni magát; a swing pivot 3–5 napos horizonra való átállás kvantitatívan ~5× erősebb mutual information-t ad (a strategic-review mathematical §5.2 szerint).

A kérdés most már nem az, hogy "milyen újabb indikátort tegyek a scoring-ba". A kérdés az, hogy **milyen strukturális paradigmák tudnak segíteni egy 1-személyes operátor által futtatott $100k-$500k tőkéjű systematic trading platform-nak**, ami nem versenyezhet sebességben, infrastruktúrában, vagy adatmélységben a top-tier intézményekkel.

A két választott methodology két ellentétes pólust képvisel:

- **Bridgewater All Weather** = **strukturális makrokeretrendszer**. Risk-based asset allocation, leverage-zett liquid futures, négy makrorendszer-kvadráns. Az időhorizont **évek**. A célja nem alpha-keresés, hanem **resilient beta**.
- **Jane Street** = **mikrostruktúra-mesterműhely**. Market-making, 0DTE flow exploitation, milliszekundumos műveletek, opciós kockázat-arbitrázs. Az időhorizont **másodpercek-órák**. A célja **liquidity provision profit + structural edge**.

A két pólus között ott van az IFDS jelenlegi pozíciója: **systematic equity trading, multi-day swing horizon, sole operator**. Sem az egyik, sem a másik nem reprodukálható közvetlenül, **de mindkettőből transzferálható strukturális megértés**, ami a swing pivot scoring/sizing/risk rétegét megalapozhatja.

A dokumentum struktúrája:

- **I. rész — Bridgewater All Weather** (§1–§5)
- **II. rész — Jane Street + 0DTE Flow** (§6–§10)
- **III. rész — Szintézis az IFDS swing pivot kontextusban** (§11)
- **IV. rész — Aggregált action items** (§12)
- **V. rész — Forrásminősítés** (§13)

---

# I. BRIDGEWATER ALL WEATHER

## 1. Methodology overview

### 1.1 A keletkezés és a paradigma

Az All Weather-t Ray Dalio és a Bridgewater research csapat 1996-ban indította, **eredetileg Dalio saját trust-portfólióját kezelni**. Az alapkérdés egyetlen mondatba sűríthető: **"hogyan építhető olyan portfólió, ami az összes elképzelhető makrokörnyezetben működik, anélkül hogy bárkinek meg kelljen jósolnia, melyik fog jönni?"**.

A 2003-ban institutional investor-ok számára nyitották meg; jelenleg ~\$92.1 milliárd AUM-ot kezel a Bridgewater (2024 év vége), és **2025-ben az All Weather +15.3%-ot, a Pure Alpha +26.2%-ot produkált** (Institutional Investor, 2025-10-01). 2025 márciusában elindult az **ALLW ETF** (State Street + Bridgewater partnership), ami először tette retail-elérhetővé a methodology-t.

A paradigmaváltás a 60/40-hez (60% részvény / 40% kötvény) képest a következő: **a 60/40 nem 60/40 kockázat, hanem ~90/10 kockázat**, mert a részvények volatilitása ~3–4×-e a kötvényeknek. Egy "valódi" diverzifikáció ezért nem capital-arányos, hanem **risk-arányos**.

### 1.2 A négy makro-kvadráns

Dalio alapfeltevése az, hogy egy adott pillanatban két makroökonómiai változó határozza meg az eszközárakat:

- **Growth** (gazdasági növekedés — gyorsuló vs lassuló)
- **Inflation** (infláció — emelkedő vs csökkenő)

Ezekből 2 × 2 = **4 makrokvadráns** áll elő, mindegyikben más eszközosztály a "leader":

| Kvadráns | Növekedés | Infláció | Leader eszközök |
|----------|-----------|----------|-----------------|
| 1 | Gyorsul (+) | Csökken (–) | Equities (developed market), nominal bonds |
| 2 | Gyorsul (+) | Emelkedik (+) | Commodities, inflation-linked bonds, EM equities |
| 3 | Lassul (–) | Csökken (–) | Nominal long bonds, gold (defenzív komponens) |
| 4 | Lassul (–) | Emelkedik (+) | Inflation-linked bonds, commodities, gold |

A logika: **mindegyik kvadránsban kell legyen egy eszköz, ami pozitívan teljesít**. Ha a portfólió risk-mértékben egyenlően van elosztva a négy kvadráns között, akkor a regime-átmenetek nem semmisítik meg a portfóliót.

### 1.3 Risk parity allokáció

A risk parity matematikai alapja az, hogy minden eszközosztály annyit kontribuál a portfólió-volatilitásból, amennyi a célzott risk-súlya. Ehhez **capital allocation ≠ risk allocation**.

Egy klasszikus 60/40 (60% S&P, 40% UST):
- Equity vol ≈ 16% évi
- UST 10y vol ≈ 6% évi
- Capital weight: 60/40
- **Risk weight: ~91/9** (mert a részvény vol 3× nagyobb)

Egy risk-parity 50/50 (risk-súlyban):
- Capital weight: ~27/73 (equity / bonds)
- **Risk weight: 50/50**

De a 73% kötvénysúly **alacsony várt hozamot ad**. Ezért a Bridgewater **leverage-et** tesz rá: a portfóliót ~150–200% gross exposure-re emeli, hogy a várt hozam összemérhető legyen a 60/40-hez, **de jobb Sharpe-rátával**.

Az ALLW ETF 2025-12-31 állapota (a Bridgewater napi model portfolio-ja alapján):

| Eszközosztály | Notional weight |
|---------------|-----------------|
| Nominal government bonds | 73.1% |
| Equities (global) | 43.6% |
| Inflation-linked bonds | 36.5% |
| Commodities | 34.0% |
| **Total notional** | **~187%** |

Az ~88%-os leverage swap-ekkel és futures-ökkel valósul meg, nem margin-borrowing-gal. Ez **kritikus** — a futures-leverage nem hív margin call-t napi mark-to-market alapon (a margin posting és a swap collateral kezelése automatizált).

### 1.4 A Bridgewater "research engine" — az allokáció napi újraértékelése

A klasszikus risk-parity (mint az 1990-es évek akadémiai változata) **statikus súlyokkal** dolgozik: kvartális rebalance, fix risk-target. A Bridgewater All Weather **dinamikus**: napi szinten újraszámolják a kovariancia-mátrixot és a regime-valószínűségeket, és **napi model portfolio update-et küldenek** a State Street-nek (az ALLW kezelője).

Ez az evolúció — a "static risk parity → dynamic risk-budgeting" — a Bridgewater proprietary tudás. A publikus források csak annyit árulnak el, hogy:

- **Real-time correlation matrix update** (napi)
- **Macro regime probability** (négy kvadráns nowcasting-ja)
- **Vol scaling** (a target portfolio vol-t fenntartják, ha a piaci vol megugrik → deleverage)

Az AI-és AIA15 fund-ok mindenese a Pure Alpha (active macro overlay), az All Weather a **"optimal beta strategy"** — a SEC filing-ekben Bridgewater ezt explicit így pozícionálja: nem akar alpha-t kifejteni, csak a piaci risk premia-t hatékonyan begyűjteni.

### 1.5 Miért működik intézményi szinten

Több strukturális ok:

**1. Skála és cost.** Egy \$50–500 milliárd AUM-on a leverage-zett futures futtatása nagyon olcsó. A swap counterpart-ek kompetitív tier-1 árazást adnak, a futures-margin alacsony, és a treasury yield-ből finanszírozható a leverage költsége. Egy retail befektető számára ez nagyságrendekkel költségesebb.

**2. Diverzifikációs előnyök over time.** A Bridgewater 30+ évnyi adatai szerint az All Weather Sharpe-rátája 1.0 közeli, miközben a 60/40 ~0.5. Ez **2× alpha-szerű alapú risk-adjusted return** — de **nem alpha**, hanem **strukturált beta**.

**3. Resilience drawdown-okban.** 2008-ban a 60/40 ~-27%, az All Weather ~-3.9% (Bridgewater eredeti adatok). 2020 Q1 COVID: 60/40 ~-15%, All Weather ~-12% (kevesebb előny, mert minden eszköz együtt esett). **2022: a stocks-bonds együttes esése miatt a RPAR (hasonló strategy) -22.8% volt, rosszabb mint a S&P -18.1%.** Ez a paradigma kritikus pontja: **amikor a korrelációs struktúra összeomlik, a risk-parity nem véd**.

**4. Long-horizon compounding.** A risk-parity előnye **csak több cikluson keresztül** mutatkozik meg. Egyetlen 5-10 éves periódusban (különösen 2010-2021 részvény-bull-ban) a 60/40 győzhet. A 30+ éves Sharpe-ratio előny csak a **több makrorezsim** átvészelése után érzékelhető.

### 1.6 A 2022-2024 stress-teszt

A klasszikus risk-parity 2022-ben **rosszul** szerepelt, és ez a methodology kritikus stressztesztje:

- 2022 elején a 10-éves UST kezdte a "bear market in bonds"-ot (yield emelkedett 1.5%-ról 4.5%-ra)
- A stocks egyidejűleg estek (Fed agresszív kamatemelése)
- A historical equity-bond negative correlation **pozitívvá** vált
- A leverage **felerősítette a veszteséget**: az RPAR -22.8% volt vs S&P -18.1%

A Bridgewater 2024-ben publikálta a "All Weather is back" analitikát, amelyben elismerik, hogy 2022 volt a methodology legrosszabb éve azóta, mióta institutional investor-ok számára elérhető. **Két strukturális válasz**:

- **Vol scaling** — amikor a piaci vol megugrik, a leverage automatikusan csökken
- **Regime nowcasting refinement** — a 4-kvadráns "Inflation up + Growth down" zónába gyorsabban átsorolódott a portfolio 2023-tól

A 2024-2025 erős teljesítmény (All Weather +15.3% 2025-ben) arra utal, hogy a methodology **adaptálható**, de a 2022-es esemény figyelmeztet: **a leverage és a korrelációs struktúra megsokszorozhatja a veszteséget, ha a feltételezett diverzifikáció ideiglenesen összeomlik**.

### 1.7 Mit közöl a Bridgewater publikusan vs mit tart titokban

**Publikus:**
- Az alap-konstrukció (4 kvadráns, risk parity, leverage)
- A vol-target koncepció
- Az asset class shortlist (equities, nominal bonds, IL bonds, commodities)
- A Dalio által írt könyvek (kvalitatív filozófia)

**Nem publikus:**
- A pontos korrelációs nowcasting módszerek
- A regime probability számítás (4-kvadráns dynamic weights)
- A specific leverage-rebalance algoritmusok
- A Pure Alpha (active overlay) jelek és pozícionálás

A retail befektető számára a publikus információ **elég ahhoz, hogy a kerettel együtt élni tudjon**, de **nem elég ahhoz, hogy maga reprodukálja a Bridgewater eredményeit**. Ez fontos epistemikus pont — bármely retail-szintű "All Weather" portfólió a kerettel dolgozik, **nem a Bridgewater proprietary engine-jével**.

---

## 2. Strukturális reproducálhatóság sole operator szempontból

### 2.1 Mit lehet közvetlenül adaptálni

**A 4-kvadráns regime-mátrix mint mental model.** Ez az IFDS MID dashboard-jában már létezik (a "GIP regime classification" 8 állapota a Bridgewater 4-kvadráns-jából bővített). A **konceptuális keret** semmibe nem kerül, és változtat azon, **hogyan gondolkozunk a kockázatról**. A "nem akarunk 5 egyirányú equity-pozíciót" gondolat a 4-kvadráns logikájából következik: minden napunk lényegében egy **kvadráns-fogadás**, és a 5 pozíció csak 1 kvadráns-fogadásban (Growth+, Inflation-) erős — a többi kvadránsban kitett.

**Risk-parity logika a portfolio-on belül.** A swing pivot 12 rolling pozíciója lehet úgy is sized, hogy **risk-arányos** legyen capital-arányos helyett. A jelenlegi terv 0.35% risk-per-trade × 12 pozíció = 4.2% portfolio risk, de **nem minden pozíció ugyanannyi kockázatot képvisel** (volatility és correlation szerint). Egy egyszerű HRP/HERC (Hierarchical Risk Parity) — mint a BC22 design dokumentumban szerepel — közvetlen alkalmazása a Bridgewater logikának.

**Vol scaling.** Az All Weather egyik strukturális komponense az, hogy **amikor a VIX vagy a realized vol megugrik, a leverage csökken**. Ezt az IFDS jelenleg is csinálja (M_VIX multiplier), de eddig **ad-hoc módon**. A Bridgewater logika szerint a vol-scaling **dinamikus**: nem küszöb-alapú (VIX > 20 = redukció), hanem **continuous** (a portfolio risk target fix, és a leverage napi szinten skálázódik a realized vol szerint).

### 2.2 Mit lehet részlegesen adaptálni

**Multi-asset diversification.** Az IFDS jelenleg pure long equity rendszer. Ha valódi multi-asset diverzifikáció kell, akkor **a sole operator pozíciónak ki kellene terjednie equity + bond + commodity + gold-ra**. Ez 4 instrumentum (vagy ETF: SPY/IEF/DBC/GLD), és a swing horizont mellett kezelhető. **De**: a 4-asset risk-parity portfolio **nem alpha-strategy**, hanem **beta-strategy**. Ha az IFDS célja edge-keresés (Pearson r > 0 a scoring és a return között), akkor a multi-asset diversification **nem cseréli ki az alphát**, csak **kísérheti**.

**Leverage retail-szinten.** A Bridgewater 1.8× leverage-et fut. Egy sole operator \$100k-on **2× leverage-et tudna futtatni** IBKR margin-ra vagy futures-on, **de**:
- A margin interest jelentős (~5-6% évi)
- A futures contract size (e.g. ZN — 10yr UST, \$100k notional/contract) **diszkrét és túl nagy** kis portfolio-hoz
- A korrelációs összeomlás veszélye (2022!) megsokszorozódik leverage-zel

**Reális következtetés**: \$100k-os portfólión a leverage **nem éri meg** kockázatban. Az ALLW ETF (1.8× leverage beépített) **olcsóbb és biztonságosabb**, ha valódi All Weather kitettséget akar a felhasználó — ~50bps TER.

**Dynamic regime detection.** Az IFDS MID dashboard-ja már nowcastolja a makro-regime-et (Stagflation, Goldilocks, etc.). A Bridgewater publikus leírása szerint a dynamic regime-overlay-t **Bayesian update-tel** csinálják, de a publikus információ kevés a részletekről. **Saját nowcasting építhető** (a MID dashboard tényleg ezt csinálja), de a Bridgewater pontos súlyozása nem reprodukálható.

### 2.3 Mit NEM lehet adaptálni

**1. A diverzifikáció skálája.** A Bridgewater 50+ eszközben pozícionál (különböző country bonds, EM equities, individual commodities). Egy sole operator-nak ez **operatívan nem kezelhető**: a daily monitoring, a rebalancing, a tax efficiency mind problémát jelent. Reálisan 4-8 instrumentum a max.

**2. A leverage-cost előny.** A Bridgewater \$50-100 milliárd kontraktusi tier-1 árazást kap. Egy retail futures-trader minimum 3-5 bps spread-szerű cost-ot fizet az implicit financing-en, és a roll-cost is jelentős.

**3. A research engine.** A Bridgewater 50+ analyst, real-time data feeds, proprietary regime nowcasting models. Ezeket egy sole operator **soha** nem fogja reprodukálni. A publikus akadémiai irodalom segít a keretek felépítésében, de a **dinamikus, valós idejű regime-classification** scale-előnyt igényel.

**4. A pszichológiai resilience.** A risk-parity stratégiák a 2022-eshez hasonló stressz-periódusokban **érzelmileg nehezen tarthatók**. Egy institutional investor LP-szerződésben kötelezett a hosszú távú perspektívára; egy sole operator-nak van választása, hogy "mégis kiszálljon". A 2008-as financial crisis-ben a Bridgewater All Weather **csak 3.9% drawdown-t** mutatott, de **a 2008-as Pure Alpha +14% volt** ugyanakkor — az LP-k egyik kérdése volt, hogy "miért is fogjuk az All Weather-t, ha a Pure Alpha jobb?". A Bridgewater jól tudta megválaszolni intézményi alapon. Egy sole operator önmagával nem tud LP-szerződésszintű kötelezettséget kötni.

### 2.4 Az IFDS-re vetített konkrét következmények

**Most (W21–W30 swing pivot reset):**
- A scoring layer-en kívül **érdemes egy "regime overlay" layer-t** beépíteni, ami a MID-ből jövő regime-classification-t fordítja sizing-multiplier-ré. Ez a Bridgewater 4-kvadráns logikájának közvetlen leszármazottja.
- A 12 rolling pozíció risk-súlya **HRP/HERC alapon** kerüljön elosztásra, nem fix 0.35% per position. (BC22 design ezzel foglalkozik.)
- A vol-scaling **continuous** legyen, ne küszöb-alapú: a target portfolio vol fix, és a base risk skálázódik a 20-day realized vol szerint.

**Közép-távon (post Day 90 ~jún 23+):**
- Érdemes megfontolni, hogy a tisztán long equity rendszerhez **van-e értelme bond/commodity overlay-t adni** mint **strategic asset allocation** réteget. Konkrétan: a portfolio 70%-a swing equity (IFDS scoring), 30%-a passive All Weather-clone (ALLW ETF). Ez **separation of concerns**: az alpha-réteg a swing scoring, a beta-réteg a passive resilience.
- Ez NEM az IFDS scoring redesign, hanem **portfolio-level architecture decision**. Külön strategic decision document szükséges.

**Hosszú-távon (post Day 126+ live trading):**
- Ha az IFDS live trading-be megy, az All Weather "vol scaling" és "regime overlay" gondolatok **közvetlenül beépíthetők** a live risk management-be.
- A 2022-es lecke: **a korrelációs struktúra-összeomlás mindig possibility**. Akár stress-test scenárió alapján (50% UST vol scaling + 30% leverage cut feltételezett katasztrófa esetén) érdemes elővizsgálni.

---

## 3. Konkrét tanulási anyag

A források minőség- és relevancia-sorrendben.

### 3.1 Foundational papers (1-3 kritikus)

**1. Dalio, Ray — "Principles for Navigating Big Debt Crises" (2018)** — *kötelező alapolvasmány*
- Free PDF: https://www.principles.com/big-debt-crises/
- ~470 oldal, de a "Archetypal Big Debt Cycle" 1-100. oldala a lényeg
- A makrokvadráns-rendszer **nem itt szerepel explicit**, de a debt-cycle / asset performance összefüggés a 4-kvadráns intellektuális alapja
- **Olvasási idő: 8–15 óra**
- **Kritikus, mert**: ez az egyetlen olyan Dalio-anyag, amely a tényleges Bridgewater research approach-ot (debt cycle phasing) bemutatja, anélkül hogy "principles for life and work" típusú motivational lenne

**2. Qian, Edward — "Risk Parity Fundamentals" (2016)** — *technikai alapmű*
- ISBN: 978-1498738798, CRC Press
- ~240 oldal, a risk-parity matematikai alapja
- Edward Qian a PanAgora-ban dolgozott (Bridgewater versenytársa), és **ő a "risk parity" terminus megalkotója** (2005)
- A könyv tartalmazza a leverage és vol-scaling matematikai kezelését
- **Olvasási idő: 15–25 óra**
- **Kritikus, mert**: a Dalio-irodalom kvalitatív; a Qian-könyv az egyetlen kompakt, technikai treatment

**3. Asness, Frazzini, Pedersen — "Leverage Aversion and Risk Parity" (Financial Analysts Journal, 2012)** — *az akadémiai vita*
- DOI: 10.2469/faj.v68.n1.1
- ~14 oldal akadémiai paper
- Az AQR (Cliff Asness) cáfolata a risk-parity hatékonyságáról: szerintük a risk-parity high-Sharpe **azért is** működik, mert nem mindenki tud leverage-et felvenni, és így van **leverage-premium**. Tehát egy "leverage-restriction relaxer" stratégia.
- **Olvasási idő: 2–3 óra**
- **Kritikus, mert**: ez az egyetlen olyan akadémiai paper, amely **valódi mechanizmust** ad a risk-parity high-Sharpe-jára. Anélkül, hogy ezt érted, nem érted, hogy a methodology **miért nem fog mindig működni** (ha mindenki ezt csinálja, az edge eltűnik)

### 3.2 Könyvek (2-4 kiegészítő)

**1. Dalio, Ray — "Principles: Life and Work" (2017)** — *kvalitatív, de hasznos a kultúra megértéséhez*
- 567 oldal, csak az "Investment Principles" rész (~80 oldal) releváns
- A 4-kvadráns-rendszer **explicit** itt szerepel először publikusan (a Dalio nélküli prior publikációkban implicit volt)
- **Olvasási idő: 4–8 óra (csak az invest. rész)**

**2. Bernstein, Peter — "Capital Ideas" (1992)** — *történelmi háttér*
- Markowitz, Sharpe, Tobin alapművei röviden összefoglalva
- A risk-parity intellektuális gyökerei (mean-variance optimization) itt kezdődnek
- **Olvasási idő: 8–12 óra**

**3. Lo, Andrew — "Adaptive Markets" (2017)** — *evolutionary frame*
- Lo (MIT) érve: a klasszikus efficient market hipotézis hiányos; a piacok **alkalmazkodó ökoszisztémák**
- Ez magyarázza, hogy **miért nem fog egy stratégia örökké működni** (ha mindenki All Weather-t fut, az edge eltűnik)
- **Olvasási idő: 10–15 óra**

**4. Roncalli, Thierry — "Introduction to Risk Parity and Budgeting" (2013)** — *advanced technical*
- Csak ha valaki a matematikát mélységében akarja érteni
- A Qian-könyv kiegészítése, mélyebb optimalizációs treatment
- **Olvasási idő: 25–40 óra (csak részletes olvasásra)**

### 3.3 Podcast / talk (1-2)

**1. "Odd Lots" — Ray Dalio interjúk (Bloomberg, 2022, 2024)**
- 2-3 epizód, ~60-90 perc/epizód
- Tracy Alloway és Joe Weisenthal aposztrofikus kérdezések; Dalio kevésbé monotón mint a saját könyveiben
- **Hallgatási idő: 4–6 óra**

**2. "The Investors Podcast — Bob Prince interjú" (2023)**
- Prince a Bridgewater co-CIO-ja, valószínűleg ő a vezető technikai elme Dalio mellett
- Ritkán nyilatkozik, ezért értékes
- **Hallgatási idő: 1.5 óra**

### 3.4 Effort total

| Anyag | Idő |
|-------|-----|
| Foundational papers (3) | 25–43 óra |
| Books (2–4 lényeges) | 22–35 óra |
| Podcast / talk | 6–8 óra |
| **Minimum useful** (Dalio Debt Crises + Qian + Asness + 1 podcast) | **~32 óra** |
| **Comprehensive** | **~80 óra** |

---

## 4. Egy konkrét gyakorlati lépés

**MOST végrehajtható lépés (1-2 hét, ~5-8 óra effort):**

**"Build a simple 4-asset risk-parity portfolio backtest on the IFDS infrastructure"**

A cél nem a Bridgewater All Weather reprodukálása, hanem **a 4-kvadráns logika empirikus megérzése a saját adatainkon**.

**Lépések:**

1. **4 asset ETF lekérése Polygon-ból** (1 óra)
   - SPY (US equity)
   - IEF (7-10 year UST)
   - GLD (gold)
   - DBC (commodity broad)
   - 5-10 év daily close

2. **Realized vol becslés** (1 óra)
   - 60-day rolling annualized vol mindegyik ETF-re
   - Korrelációs mátrix napi szinten (Ledoit-Wolf shrinkage)

3. **Naive risk-parity portfolio** (2 óra)
   - Súlyok: `w_i ∝ 1 / vol_i`
   - Quarterly rebalance
   - Backtest 2015–2025
   - Sharpe, MaxDD, Calmar számítása

4. **Levered risk-parity** (1 óra)
   - Ugyanaz, de target volatility 10% évi
   - `leverage = 0.10 / portfolio_vol`
   - Backtest, ugyanazok a metrikák

5. **Összevetés 60/40-nel és S&P-vel** (1 óra)
   - Egy táblázat: Annual return, Sharpe, MaxDD, Calmar, 2022 performance
   - **Kiemelt: 2022-as performance** — itt láthatóvá válik a methodology gyengesége

6. **Konklúzió: érdemes-e a swing pipeline portfólió-szintjén kiegészíteni?** (1 óra)
   - Ha a 4-asset risk-parity Sharpe > 0.7 és MaxDD < 15% 2015-2025-ben → igen, érdemes mint **strategic overlay** (70% IFDS swing + 30% RP)
   - Ha Sharpe < 0.5 vagy MaxDD > 20% → nem éri meg, és helyette a swing scoring layer-en kell dolgozni

**Output:** egy 5-10 oldalas backtest report `docs/strategic-review/2026-XX-XX-risk-parity-backtest.md` formátumban, és egy döntésjavaslat: "érdemes-e fenntartani a Bridgewater-inspired regime overlay-t a swing pivot post-Day 90 fázisában?".

**Az érték nem a precíz Bridgewater-reprodukció, hanem a két dolog kvantitatív megérzése**:
1. Milyen nagy a Sharpe-előny a 60/40-hez képest a saját adat-spektrumon?
2. Mennyit "költ" a methodology a 2022-szerű stressz-periódusban?

Ez a két szám fogja a döntés alapját képezni — nem a Dalio-könyvek "spirit"-je.

---

## 5. Critical caveats — amit a populáris ábrázolás félreért

**1. "Az All Weather mindig stabil" → HIBA.**

A 2022-es teljesítmény (~-15% YTD All Weather, ~-22.8% RPAR) megmutatta, hogy **amikor stocks és bonds együtt esnek, a leverage rontja a helyzetet**. A populáris ábrázolás (Dalio interjúk, ETF marketing) elhallgatja, hogy a risk-parity **strukturális feltevése** (stocks-bonds negative correlation) **regime-függő**. 2022-ben ez a feltevés ideiglenesen megszűnt.

**2. "Risk parity = magic Sharpe enhancement" → HIBA.**

Az Asness-paper (2012) szerint a risk-parity Sharpe-előnye **legalábbis részben** abból származik, hogy a leverage-aversion miatt nem mindenki tud risk-parity-t futtatni. Ha mindenki ezt csinálná, az edge **eltűnne**. Az ALLW ETF retail-elérhetősége **éppen ezen az úton fenyegeti a strategy long-term Sharpe-ját**.

**3. "Sole operator-nak retail All Weather strategy működik" → CSAK ÉS KIZÁRÓLAG egy bizonyos formában.**

A retail All Weather (ALLW, RPAR, UPAR ETF-ek) működik **mint passive beta exposure**. **NEM működik** mint **DIY leverage with treasury/gold futures** — ehhez prof. trader szintű derivatives-tudás kell, és a 2022-es típusú events a sole operator-t kinyírják. Ezért: **vagy az ETF-et veszi, vagy hagyja**.

**4. "A Bridgewater Pure Alpha az All Weather-hez tartozik" → HIBA.**

Ez két **különálló** stratégia. A Pure Alpha az active macro overlay (long/short, sok eszközosztály, alpha-keresés). Az All Weather a strukturális beta. **A 26.2% YTD 2025 (Pure Alpha) NEM az All Weather**, az csak 15.3%. Sok retail marketing keveri a kettőt, és **az ALLW ETF csak All Weather-t reprodukál, Pure Alpha-t NEM**.

**5. "Dalio személyes szerepe ma is döntő" → HIBA.**

Dalio 2022-ben formálisan teljesen kivonult a daily operations-ből (Nir Bar Dea és Mark Bertolini co-CEO-k). A 2023-as restructuring **megkérdőjelezi**, hogy a methodology jelenleg ugyanolyan, mint a klasszikus Dalio-éra alatt. A 2025-2026 erős performance arra utal, hogy az új vezetés **adaptálta** a methodology-t (vol scaling, regime nowcasting refinement), **de** a publikus információ erről kevés.

**6. "Az All Weather nem alpha, hanem beta" → IGAZ, és ez fontos.**

A Bridgewater explicit pozícionálja az All Weather-t **"optimal beta strategy"-ként**. Ez azt jelenti: **nem várható el, hogy a piacot konzisztensen verje**. Az alapcélkitűzés a **stabilabb Sharpe és kisebb drawdown** — nem a **magasabb return**. Aki azt várja, hogy a methodology az S&P-t verje *minden* évben, **félreérti a paradigma alapját**.

---

# II. JANE STREET + 0DTE FLOW

## 6. Methodology overview

### 6.1 A cég és a kontextus

A Jane Street 1999/2000-ben alapult New York City-ben (a források között kis eltérés van — 1999 a céges history, 2000 az aktívlét kezdete). Jelenleg ~2 600 alkalmazott, 45 országban, és **2025 nettó trading revenue $39.6 milliárd** (rekord). Q1 2026 alone $16.1 milliárd. Profit Q1-ben "doubled to \$10.3 billion" (5paisa, 2026-05).

Ez **abszolút nagyságrendi különbség** a Bridgewaterhez képest: a Bridgewater AUM-ot kezel és management-fee-t kap; a Jane Street **principal trading**, saját könyvön kereskedik.

Az eredeti 4 alapítóból **csak Robert Granieri maradt** 2026-ra. A cég híresen **secretive** — ritkán nyilatkozik publikusan, nem publikál akadémiai paper-eket (eltérően a Renaissance-tól vagy a DE Shaw-tól), és a methodology-jukról a tudás **közvetett**: SEC filing-ek, SEBI vizsgálatok, és a 2 600 alkalmazott "kiszivárgó" gondolkodása conference-eken és podcast-okon.

### 6.2 A 0DTE explosion mint piaci esemény

A Jane Street-t kontextusba kell tenni: **az amerikai opciós piac 2022-2025 között radikálisan átalakult**.

- A Cboe **2022-ben vezette be a daily SPX expirations-t** (hétfő, kedd, szerda, csütörtök, péntek mind expiry nap)
- Ettől kezdve **a "0DTE option"** (zero days to expiration) mint product class indult
- 2023 közepén: ~40% of SPX volume
- 2024 vége: ~50%+
- **2025: 57-61% of SPX volume = 0DTE**, average daily volume 2.15M (Q3 2025), peak 2.7M (Oct 2025)
- Single-day peak: 6.4M contracts (~70% növekedés late-2024 óta)

A "retail vs institutional" megoszlás:
- Cboe Q4 2025 data: market makers 2.8M contracts/day, customers 2.3M, pro customers 202.6k, firms 24k, broker-dealers 9.7k
- Retail estimált: 50-60% of SPX 0DTE flow (CBOE saját estimation)
- Institutional flow ~40-50% — főleg vertical spreads, korai napi pozícióvétel

A Jane Street ebben a piacban **a top market maker** szerepét tölti be (a többiek: Citadel Securities, Susquehanna, Optiver, IMC).

### 6.3 A market making mint methodology

A Jane Street alapvetően **market maker**, nem proprietary directional trader (legalábbis a profit-mix többsége). A market making logika:

**1. Spread capture.** Minden bid/ask spread egy "edge". Ha 1000 SPY put-on a spread $0.02, és a Jane Street market maker, akkor mindkét oldalt teljesítve $20 profit per contract pair. Skálán (milliárdok kontraktusban) ez óriási bevétel.

**2. Inventory risk management.** A market maker akkor csinál pénzt, ha **gyorsan átadja a kezében lévő pozíciókat**. Ha a market trend megy egy irányba, a market maker rákényszerül a hedge-elésre — ez **delta hedging** dinamikája.

**3. Adverse selection avoidance.** Az igazi edge nem a spread, hanem **a contraflow ellen tudni hedge-elni**. Ha egy "informed trader" (pl. hedge fund) tudja, hogy a piac le fog menni, és puts-okat vásárol, a market maker veszít — kivéve, ha a market maker képes detektálni az informed flow-t és előre hedge-elni. **A Jane Street ebben kiváló.**

**4. Cross-venue arbitrage.** A Jane Street 45 országban, sok venue-n market maker. Egy SPY ETF árazás és a 500 underlying stock árazása **percről percre** divergál. A Jane Street ezt arbitrálja milliszekundumokban.

### 6.4 A 0DTE-specifikus dinamika

A 0DTE options market making **eltér** a klasszikus market making-től, mert:

**1. Gamma explosion az expiráció előtt.** Egy 0DTE option gamma-ja a delivery előtti utolsó órákban **exponenciálisan nő**. A market maker pozíció **kicsi időablakban** óriási delta-mozgásra kötelezett.

**2. A "gamma squeeze" mechanizmus.** Ha sok retail nagyon out-of-the-money calls-t vásárol, és a piac elindul felfelé, a market maker (aki short calls) **rákényszerül a underlying megvételére** (delta hedge). Ez **felerősíti a momentum-ot**. Ez egy ún. **negative gamma regime**.

**3. A "pin risk" mechanizmus.** Ha a market maker net long gamma (kvázi alkalmas a moves "felszívására"), akkor minden underlying-elmozdulást **vissza-hedge-elnek** (sell rallies, buy dips). Ez **mean-reversion**-t okoz. Ez **positive gamma regime**.

A két regime közötti **flip point** = **gamma flip level**. Ha az SPX a flip felett, range-bound action várható; ha alatt, trending volatility.

### 6.5 Akadémiai konszenzus a 0DTE hatásokról

A legfontosabb akadémiai paper a témán **Dim, Eraker, Vilkov (2024)**:
- "0DTEs: Trading, Gamma Risk and Volatility Propagation" — SSRN 4692190
- Empirikus eredmények:
  - Market maker net gamma **a legtöbb napon pozitív** (pin/mean-reversion regime dominál)
  - Pozitív MM gamma → intraday **price reversal** (volatility attenuation)
  - Negatív MM gamma → intraday **momentum** (volatility amplification)
  - Az evidence **delta-hedging-konzisztens**, NEM information-based trading-konzisztens
- **Implikáció:** a 0DTE flow **nem mint signal**, hanem mint **structural force** működik — a market maker hedging-pattern-ek a hangsúlyosak.

A Cboe-saját analitika (Mandy Xu, "0DTEs Decoded", 2025-05): a SPX 0DTE put/call ratio **közel 1-en marad** (~50/50 balanced flow), míg a non-0DTE PCR ~0.85-0.95 (put-heavy, hedging-szerű). Ez azt jelenti, hogy **a 0DTE flow tactical, nem hedging**, és nem ad direkt signal-t a tényleges market sentiment-re.

Egy 2025-12 arXiv paper (Eaton et al.): **LLM-ek 91.2% pontossággal képesek detektálni a gamma exposure pattern-eket** SPY-on, ha a raw GEX értékek hozzáférhetők. Ez azt sugallja, hogy a **GEX-based pattern recognition kvantifikálható**, és nem csak "fekete művészet".

### 6.6 A SEBI India ügy mint módszertani feltárás

2025 július 4-én a SEBI (India szabályozó) **105-oldalas interim order**-t adott ki a Jane Street ellen. A felhozott vád: **systemás index manipuláció** a Bank Nifty derivative-eken.

A SEBI dokumentum szerint a Jane Street **"Patch I"** időablakban (9:15–11:46 AM india local time, ~21 trading napon) az alábbi struktúrát követte:

**Délelőtt (Patch I):**
- Bank Nifty komponens stocks (Kotak Bank, SBI, Axis Bank) **aggresszív vétele**
- Volume 20%+ of market-wide traded value egyes stock-okra
- Orders **last traded price felett** — direkt liftelve az árat
- **Egyidejűleg**: short calls + long puts a Bank Nifty index opciókon

**Délután:**
- A long cash positions **unwinding** (eladás)
- Index esik
- Short call + long put pozíciók profitot termelnek

A SEBI ezt **manipulationnak** klasszifikálta. A Jane Street **"legitimate index arbitrage"-nek** nevezte. A jogi vita folyamatban van, július 21-2025 részleges feloldás történt.

**Methodology-szempontból ez extrém érdekes**, mert kvázi-betekintést ad egy "secretive" cég strukturális gondolkodásába:
- **Time-of-day asymmetric positioning** — a délelőtti cash market activity és a délutáni unwinding kombinációja
- **Cross-market arbitrage** — a cash market liquidity-t használták az options pricing manipulálására
- **Scale-leverage** — egy retail méretű trader **soha** nem tudná ezt csinálni (volume 20%+ a market-ben)

**Stratégiai tanulság:** a Jane Street nyilvánvalóan **nem csak spread-capture-rel** csinál pénzt. **Strukturális mikrostruktúra-arbitrázs** is jelentős profit-forrás, ami **scale-függő** és **regulatórikus szürke zónában** van.

### 6.7 A pénz forrása — strukturált összegzés

A Jane Street ~\$40B éves bevételének valószínű (publikus + leak-elt információ alapján) megoszlása:

| Forrás | Becsült részesedés | Magyarázat |
|--------|--------------------|------------|
| ETF market making | ~35-45% | A cég eredeti core üzlete, óriási skálán |
| Equity options market making (0DTE-vel) | ~25-35% | 0DTE explosion 2022-tól |
| Cross-asset arbitrage | ~10-15% | ETF vs underlying, cross-venue |
| Crypto market making | ~5-10% | 2021-2023 növekedés |
| Medium-frequency strategies (minutes-days) | ~5-15% | Recent disclosure, nem csak HFT |
| **AI/tech investments (Anthropic, CoreWeave)** | **separate** | Ez nem trading P&L, hanem equity stake |

A "medium-frequency" rész (Q1 2026 disclosure) **különösen érdekes** — ez azt jelenti, hogy a Jane Street **NEM csak HFT-t** csinál. **Multi-day swing positions is részei a stratégiának**, gépi alapon. Ez közelebb áll az IFDS jelenlegi struktúrájához.

---

## 7. Strukturális reproducálhatóság sole operator szempontból

### 7.1 Mit lehet közvetlenül adaptálni

**A 0DTE GEX mint structural signal (NEM directional indicator).** Az IFDS jelenleg GEX-et használ M_GEX multiplier formájában (positive GEX → 1.0×, negative → 0.5×). Ez a Dim-Eraker-Vilkov paper alapján **defenzíve helyes**, de **explicit használni a 0DTE-specifikus GEX-et** (ami szignifikánsan eltér a teljes GEX-től, mert a 0DTE gamma a magas) **jobb signal-t adhat**:

- **Above gamma flip + high 0DTE GEX** = range-bound regime → trend-following stratégia gyengébb, mean-reversion erősebb
- **Below gamma flip + high 0DTE GEX** = trending regime → trend-following stratégia erősebb

Ez **regime overlay** lehet a swing scoring-on; nem egy új scoring komponens, hanem **modulátor**.

**Vertical spread thinking.** A Jane Street institutional flow elemzéséből (CBOE) kiderült, hogy az **intézmények vertical spread-eket** preferálják 0DTE-ben, nem outright options-t. A swing pivot pozíciók **vertikális spread-ekkel hedge-elhetők** alacsony cost-tal. Például: egy 5-napi long XYZ stock pozíciót lehet **5-napi long put + short OTM put** struktúrával védeni. Ez nem egyenlő a Jane Street-tel, de **a logikát** átveszi.

**Time-of-day positioning.** A SEBI ügyből (Patch I time-window 9:15-11:46 AM) az alapelv az, hogy **a market activity time-of-day asymmetric**. Az IFDS jelenleg 15:30 CEST belépést alkalmaz (a swing pivot pivottal módosítva 16:20 CEST → 15:30 CEST). A **belépés-időzítés** további finomítása érdemleges: empirikusan a market open + 30 perces időszak után a flow signal jobb értelmezhetőséggel rendelkezik (less noise, less opening-range effects).

### 7.2 Mit lehet részlegesen adaptálni

**Cross-venue arbitrage.** A Jane Street ETF arbitrage 30%+ of revenue. Egy sole operator-nak ez **nem reprodukálható** real-time, mert nincs LATAM tier1 data feed, nincs colocation. **DE** a **statisztikai cross-asset edge** (pl. a sector ETF (XLE) és a top 5 underlying stocks együttes mozgása) **detektálható** és **alkalmazható** szétszórt jelek alapján. Ez nem ad nagy edge-et, de **nem requires HFT infrastructure**.

**Inventory risk thinking.** A market maker mindig az inventory-ját kezeli. Egy systematic trading rendszerben az **inventory = open positions**. A swing pivot 12 rolling pozíciója egy inventory; **a portfolio-level inventory risk** (gross delta, gross gamma if any options, sector concentration) mind **market maker thinking**. Ez közvetlenül beépíthető a portfolio risk monitor-ba.

**Adaptive bid/ask spread (limit order strategy).** A Jane Street **soha nem fizet bid-ask spread-et**. Egy sole operator néha **fizethet limit orderrel a near touch**-on (1-2 ticken belül), és ezzel **csökkentheti a slippage-et**. Ez nem revolutionary, de a "always market order" approach-tól **0.05-0.15% per trade** spórolás.

### 7.3 Mit NEM lehet adaptálni

**1. HFT infrastruktúra.** A Jane Street milliszekundumos végrehajtás, colocation, custom hardware. Egy sole operator **soha** nem fog ehhez közelíteni. **És nem is kell.** Az IFDS swing horizon (3-5 nap) ezt **strukturálisan nem igényli**.

**2. Adverse selection detection.** A Jane Street tudja, ki kereskedik vele a másik oldalon (vagy legalábbis statisztikailag becsli). Egy IBKR retail-szintű felhasználó **nem rendelkezik** ilyen adattal. **De**: az **aggregálódó orderflow** (e.g. NYSE order imbalance signal) **részben pótolja** ezt. Ez az IFDS pipeline-jában már szerepel az "OTM call ratio" és "block trade count" formájában, de **mindkettő gyenge prediktornak bizonyult** Bonferroni után.

**3. Cross-venue arbitrage skála.** Lásd fent.

**4. A SEBI-típusú "Patch I" stratégia.** Ehhez **piaci szinten dominans pozíció** kell (20%+ volume). Egy sole operator **soha** nem lesz ennyi piacban — és **nem is kéne, mert ez a regulatórikus szürke zóna**. **Ez fontos:** **NEM cél a methodology-t mint stratégiát reprodukálni**, csak **a strukturális megértést** átvenni.

**5. Market making spread profit.** Egy sole operator-nak nincs liquidity provision quote-küldési privilégiuma a major exchange-eken (anélkül, hogy market maker license-et szerezne, ami nem retail option).

### 7.4 Az IFDS-re vetített konkrét következmények

**Most (W21–W30):**

- **A swing pivot scoring layer egyik felülvizsgálati pontja a 0DTE GEX-specific signal beépítése**. A jelenlegi GEX a teljes pozíciókészletet aggregálja; a 0DTE-specifikus GEX (különösen az SPX index szinten) **regime overlay** lehet, ami **megmondja, hogy a piac aznapja "range-bound" vagy "trending" várhatóan**. Ez a swing pozíció-belépés (15:30 CEST) **timing**-jét javíthatja.
- **A PCR (put-call ratio) az egyetlen flow signal, amely a Bonferroni után életben maradt** (+0.203 ✱✱). A Jane Street kontextusból tanulság: **a 0DTE PCR ~1.0 (balanced), a non-0DTE PCR ~0.85-0.95 (put-heavy hedging)**. **A különbség informatív**: ha a non-0DTE PCR hirtelen elmozdul (pl. 1.1 fölé), az **institutional hedge unwinding-ot** jelez — ez **directional signal** lehet.
- **A Phase 1-3 univerzum (S&P 500 + Russell 1000, ~1000 ticker) szűkíthető lehet "high 0DTE GEX-exposure" tickerekre**. Single-stock 0DTE volume még mindig kicsi, de a top 20-30 ticker (AAPL, NVDA, TSLA, META, etc.) **rendelkezik 0DTE-vel**, és ezeken a GEX-pattern detection jobban működik.

**Közép-távon (post Day 90 ~jún 23+):**

- Ha az IFDS-be **vertical spread overlay**-t építenénk a swing equity pozíciókhoz (egy long stock + short OTM call = covered call típus), akkor a portfolio risk profile **strukturálisan jobb**: a maximális drawdown csökken, a Sharpe-ratio javul. **De** ez kódolásilag jelentős komplexitás, és IBKR-szintű spread order management nem triviális.
- A **time-of-day asymmetric belépés** systematic teszttel javítható: a 15:30 CEST vs 16:00 CEST vs 16:30 CEST belépések közötti performance különbség **kvantitatív, és a swing pivot W23-W24 backtest fázisában** vizsgálandó.

**Hosszú-távon (post Day 126+ live):**

- A **GEX-based regime detection** (range-bound vs trending) **közvetlenül beépíthető a sizing layer-be**: range-bound napokon az M_total multiplier-t csökkenteni (kisebb pozíció), trending napokon növelni.
- A **medium-frequency strategy** (Jane Street disclosure, "minutes to days") az IFDS swing horizonjához közel áll. **Soha** nem fogja az IFDS reprodukálni a Jane Street profit-szintjét, de **a strukturális megértés** segít a swing pivot design-ban.

---

## 8. Konkrét tanulási anyag

### 8.1 Foundational papers (1-3 kritikus)

**1. Dim, Eraker, Vilkov — "0DTEs: Trading, Gamma Risk and Volatility Propagation" (2024)** — *KÖTELEZŐ*
- SSRN ID: 4692190
- Free PDF: https://papers.ssrn.com/sol3/Delivery.cfm/4692190.pdf?abstractid=4692190
- ~40 oldal akadémiai paper
- **A leg kritikusabb 0DTE paper**: empirikusan kimutatja, hogy a market maker net gamma a legtöbb napon **pozitív**, és **negatívan korrelál** a future intraday volatilitással. Ez az alap minden GEX-based reasoning-hoz.
- **Olvasási idő: 6–10 óra (mély értelmezéssel)**

**2. Almeida, Freire, Hizmeri — "0DTE Asset Pricing" (2024, Princeton WP)** — *FONTOS*
- Princeton University Working Paper
- A 0DTE option pricing rátermettsége — szigorúan kvantitatív
- **Olvasási idő: 4–6 óra**

**3. Adams, Fontaine, Ornthanalai — "The Market for 0-Days-to-Expiration: The Role of Liquidity Providers in Volatility Attenuation" (2024, Bank of Canada / Univ. Toronto WP)** — *KIEGÉSZÍTŐ*
- A liquidity provider (market maker) szerepe a vol attenuation-ben
- **Olvasási idő: 4–6 óra**

### 8.2 Books (2-4 kiegészítő)

**1. Aaron Brown — "Red-Blooded Risk: The Secret History of Wall Street" (2011)** — *kvalitatív, market maker thinking*
- Aaron Brown a Morgan Stanley és az AQR egykori risk manager-e
- A market making logika és az inventory risk gondolkodás bemutatása
- **Olvasási idő: 12–18 óra**

**2. Euan Sinclair — "Volatility Trading" (2013, 2nd ed.)** — *technikai, options-specific*
- ISBN: 978-1118347133
- A klasszikus volatility trading methodology — kvantitatív megközelítés
- Sinclair a "Talk on Trade" podcast-okban gyakori vendég
- **Olvasási idő: 25-35 óra (mély olvasással)**

**3. Sheldon Natenberg — "Option Volatility and Pricing" (2nd ed., 2014)** — *referenciakönyv*
- ISBN: 978-0071818773
- A klasszikus options-pricing tankönyv, market maker szempontból
- **Olvasási idő: 30-50 óra (kerettartalmilag, ha az olvasó nem options-trader)**

**4. Bennett, Colin — "Trading Volatility" (2014)** — *advanced trader's manual*
- Free PDF available (Goldman Sachs eredetileg, később publikus): https://trading-volatility.com/
- Skew, vol surface, gamma trading — kvantitatív részletek
- **Olvasási idő: 20-30 óra**

### 8.3 Podcast / talk (1-2)

**1. "The Talk on Trading" podcast — Euan Sinclair episodes (multiple)**
- Sinclair a market making + volatility trading egyik publikus voice-ja
- Az episodes praktikusak: how-to-think-about-volatility, NEM hype
- **Hallgatási idő: 6-12 óra (több epizód)**

**2. "Macro Hive Podcast" — institutional flow analysis episodes (2024-2025)**
- A 0DTE flow és intraday volatility dinamikája gyakori téma
- **Hallgatási idő: 4-8 óra**

### 8.4 Effort total

| Anyag | Idő |
|-------|-----|
| Foundational papers (3) | 14-22 óra |
| Books (csak Sinclair + Bennett a minimum) | 45-65 óra |
| Podcast | 6-12 óra |
| **Minimum useful** (Dim et al. + Sinclair + 1 podcast sorozat) | **~35 óra** |
| **Comprehensive** | **~100 óra** |

---

## 9. Egy konkrét gyakorlati lépés

**MOST végrehajtható lépés (1-2 hét, ~6-10 óra effort):**

**"Validate the 0DTE GEX as regime overlay on the IFDS Phase 4 universe"**

A cél nem a Jane Street market making reprodukálása, hanem **annak empirikus tesztelése, hogy a 0DTE GEX (vagy egy proxy) regime-classification-ként használható-e** az IFDS swing pivot scoring-ban.

**Lépések:**

1. **0DTE GEX adat lekérése Unusual Whales-en keresztül vagy proxy számolás** (2-3 óra)
   - Az UW shadow-log mode-ban már fut (Phase 1 deactivated scoring)
   - SPX 0DTE put GEX + call GEX napi tracking
   - Ha az UW nem adja, a Polygon options chain-ből számolható: ∑ (gamma × OI × 100 × spot)
   - 60-90 nap historical adat

2. **Gamma flip level becslés** (1-2 óra)
   - A "gamma flip level" = az a spot ár, ahol a net dealer gamma 0-ra esik
   - Heurisztika: a "max pain" stratégia + put-call gamma egyensúly
   - Naponta számítva, és hasonlítva a tényleges SPX close-hoz

3. **Regime classification napi szinten** (1 óra)
   - `above_flip_HighGEX` = range-bound regime
   - `below_flip_HighGEX` = trending regime
   - `low_GEX` = no signal regime

4. **Backtest: a IFDS Phase 4-6 historikus döntéseinek post-hoc analízise** (2-3 óra)
   - A 60 napi paper trading adat újraértelmezése GEX-regime szerint
   - **Hipotézis**: a range-bound napokon az IFDS swing pozíciók profit-arányosabbak; a trending napokon a stop-out gyakoribb
   - Ha a regime és a performance közötti korreláció **erős (Pearson > 0.20)** → érdemes regime overlay-t építeni

5. **Döntésjavaslat** (1 óra)
   - Ha a regime overlay szignifikáns prediktor → implementálni Phase 2 (W23-W24) design-ban
   - Ha nem → archive (a 0DTE GEX nem ad swing-horizon signal-t, csak intraday-t — ami az IFDS-nek nem érdekes)

**Output:** egy 5-10 oldalas validation report `docs/strategic-review/2026-XX-XX-0dte-gex-regime-overlay-validation.md` formátumban, döntéssel a Phase 2 design-ra.

**Az érték:** ha a 0DTE GEX **mégis** szignifikáns regime indicator, akkor **egyetlen új komponens** a scoring overlay-en jobb edge-et adhat, mint **3-4 új scoring component**. Bonferroni-tudatos megközelítés.

---

## 10. Critical caveats — amit a populáris ábrázolás félreért

**1. "0DTE destabilizes markets" → A Cboe és az akadémiai konszenzus szerint NEM.**

A populáris narratíva (Wall Street Journal cikkek 2023-2024, "0DTE will cause the next flash crash") **az adatokkal nem egyeztethető össze**. A net gamma exposure ~0.04-0.17% of S&P futures liquidity — strukturálisan kicsi. A balanced flow (PCR ~1.0) miatt a 0DTE **nem one-sided force**. Aki ezt félreérti, **téves directional bias-szal** építi a stratégiáját.

**2. "Jane Street csak HFT-t csinál" → HIBA.**

A Q1 2026 disclosure szerint a Jane Street **medium-frequency strategies-t is fut** (minutes to days holding period). Ez közelebb áll az IFDS swing horizonjához, és **a tanulás iránya is ide kell hogy mutasson** — nem a millisecond-arbitrázs.

**3. "A SEBI vádak igazolják, hogy a Jane Street manipulál" → SEMLEGES.**

A SEBI ügy **jogilag nem zárult le**. A Jane Street pozíciója: legitimate index arbitrage. A SEBI pozíciója: manipuláció. **Mindkét pozíció racionális**. A retail operator szempontjából **lényegtelen** a jogi végeredmény — a strukturális tanulság (time-of-day asymmetric positioning + cross-market arbitrage) **független** a jogi minősítéstől. **Ne építsd a stratégiádat arra a feltevésre, hogy egy ilyen módszer "OK"**, mert egy retail-szinten egyébként sem alkalmazható.

**4. "GEX a piac mozgásának egyetlen oka" → ALAPHIBA.**

Bármilyen GEX-based regime overlay **csak akkor működik**, ha **a piaci aktivitás többi része nem dominál**. Egy CPI release reggel, egy FOMC döntés délután, egy geopolitikai esemény — mindezek **felülírják** a GEX-pattern-eket. A GEX **másodlagos signal**, nem primary driver. Az IFDS pipeline-ban ezt **modulátorként** kell használni, nem primary scoring-ként.

**5. "A Jane Street public papers segítenek" → MA NEM LÉTEZNEK.**

A Jane Street **soha nem publikál** akadémiai paper-eket (eltérően Renaissance, DE Shaw, Two Sigma, AQR). Aki a Jane Street methodology-t tanulja, **közvetett források** alapján teszi: SEBI documentumok, SEC filings, alkalmazottak konferencia-előadásai, és **az akadémiai irodalom a 0DTE-ről** (amit a Cboe és univerzitások publikálnak).

**6. "A retail 0DTE trader-ek random sasok" → A Cboe adatok szerint NEM.**

A Cboe 2025-ös elemzése szerint a retail 0DTE trader-ek **meglepően sophisticated**-ek: vertical spreads, defined-risk strategies, systematic yield strategies. A naiv "retail = degenerate" narratíva **nem támogatott** az aggregálódó adatokkal. **De**: a Cboe data sample-en a retail option flow **medián P&L** -$3.28, average +$1.45 — a P&L disztribúció **erősen skewed** (skew 4.47, kurtosis 33.58). **Tehát**: van néhány nagy nyerő retail trader (a tail-ben), és sok kis vesztes. **Ez egy lottery-szerű disztribúció**, nem strukturális edge.

**7. "Az ALLW + 0DTE = hibrid retail strategy" → NINCS PUBLIKUS EVIDENCIA EZ MELLETT.**

Tényleg nincs olyan publikus stratégia, ami **All Weather long-term beta + 0DTE-flow alpha**-t kombinálná retail-szinten. Aki ezt akarja kipróbálni, **első kísérletező**. Ez **nem feltétlenül rossz**, de **nem alátámasztott** sem akadémiai, sem industry-szintű bizonyítékokkal.

---

# III. SZINTÉZIS AZ IFDS SWING PIVOT KONTEXTUSBAN

## 11.1 Két methodology, két IFDS-réteg

A két methodology **különböző IFDS réteghez** kapcsolódik:

| Methodology | Hatás-réteg | Időhorizont | Implementáció |
|-------------|-------------|--------------|---------------|
| **Bridgewater All Weather** | Portfolio-szintű sizing + regime overlay | Months-years | Sizing layer + 4-quadrant macro classifier |
| **Jane Street + 0DTE flow** | Scoring + entry timing | Days | Scoring overlay + GEX regime |

A swing pivot scoring (PCR + OTM-inverse) **Bonferroni-konzervatív** — ami helyes. De **ezen kívül** lehet **mindkét methodology-t** úgy beilleszteni, **hogy ne új scoring komponensként** szerepeljen, hanem **modulátorként**:

1. **Bridgewater-réteg:** macro regime classifier → multiplier a base risk-en
2. **Jane Street réteg:** 0DTE GEX classifier → multiplier az entry timing-en + sizing-on

Ez **separation of concerns**: a scoring layer-rel **nem nyúl össze**, és **független backtest-elhetők**.

## 11.2 A "what to NOT do" lista

A két methodology tanulmányozása után a következő **csapdák** kerülendők:

**1. "Build a 4-asset multi-asset portfolio with futures leverage."**

Túl kicsi a tőke (\$100-500k), túl nagy a 2022-szerű korrelációs összeomlás veszélye, és nincs operatív kapacitás. Az ALLW ETF + IFDS swing kombinációja **vagy** önálló swing equity rendszer az opció — ne keverjük össze a kettőt.

**2. "Reproduce Jane Street market making on retail platform."**

Nem reprodukálható. Az infrastruktúra-gap (HFT, colocation, multi-venue routing) **strukturális**, nem áthidalható. **A market making mint metafora hasznos, de mint stratégia nem.**

**3. "Build a 7-component scoring with new GEX-derived metrics."**

Pont ez az, ami a Day 63 milestone-on **megbukott**. Az új scoring komponensek **Bonferroni-szintet** kell teljesítsenek. A modern methodology-k tanulsága **nem új komponensek**, hanem **strukturális keret**.

**4. "Add active macro overlay (Pure Alpha-style) to IFDS."**

A Bridgewater Pure Alpha-t **50+ analyst** futtatja real-time global macro forecasts-szal. Egy sole operator-nak ez **nem reprodukálható**. A MID dashboard **regime classification** annyit ér, amennyit, **de** az **active directional bet** (e.g. "long USD/JPY because Fed will hike") **soha** nem fog egy sole operator-tól megbízhatóan jönni.

## 11.3 A "what to DO" lista (prioritás szerint)

**P1 (most, Phase 1-2 W23-W24 közben):**

1. **0DTE GEX regime overlay validáció** (lásd §9 gyakorlati lépés)
   - 6-10 óra effort
   - Bemenet: UW shadow log + Polygon
   - Kimenet: docs/strategic-review/0dte-gex-validation.md
   - Döntés: implementálni Phase 2-ben vagy archív

2. **HRP/HERC portfólió allokáció design véglegesítése** (BC22 dokumentum már létezik)
   - A Bridgewater risk-parity logika közvetlen alkalmazása
   - 12 pozíció risk-súlya nem fix 0.35%, hanem HRP-clusterezett
   - Implementálás CC task-ban, Phase 3 (W25+) deploy

3. **Macro regime overlay design (4-quadrant + sizing multiplier)**
   - A MID dashboard regime classification → sizing multiplier
   - Design dokumentum: docs/design/macro-regime-overlay.md
   - 4-6 óra effort

**P2 (Phase 2-3 közben, W24-W26):**

4. **Time-of-day belépés A/B teszt** (15:30 / 16:00 / 16:30 CEST)
   - Backtest a 60 napi adaton, post-hoc 
   - Jane Street SEBI ügy time-of-day asymmetria-tanulság
   - 4-6 óra effort

5. **Continuous vol-scaling (helyett küszöb-alapú)**
   - Jelenleg M_VIX küszöbös; átállás continuous-ra
   - Bridgewater "target portfolio vol" logika
   - 3-5 óra effort

**P3 (post-Day 90, ha az alapok stabilak):**

6. **4-asset risk parity backtest** (lásd §4 gyakorlati lépés)
   - 5-8 óra effort
   - Döntés: érdemes-e strategic asset allocation overlay (70% IFDS + 30% RP)

7. **Vertical spread overlay vizsgálat** (Jane Street institutional flow lecke)
   - Csak ha a swing equity konzisztens edge-et mutat (cumulative > +\$2k Day 126-ig)
   - Komplexitásnövelés indoka kell

## 11.4 Az epistemológiai pont

A legfontosabb tanulság **nem** kvantitatív, hanem **metaként**:

> **A két methodology-tól nem új scoring komponenseket vegyél át, hanem strukturális gondolkodást.**

A Day 63 milestone azt mutatta meg, hogy **több komponensű scoring → magasabb noise → null edge**. A modern intézményi methodology-k **nem azért működnek**, mert sok komponensük van, hanem mert a **strukturális keretrendszerük helyes**:

- A Bridgewater **4-kvadráns + risk-parity + leverage** = elegáns, kevés-paraméteres keret
- A Jane Street **market making + GEX-aware + cross-venue arbitrage** = strukturális edge, nem prediktív edge

Az IFDS swing pivot scoring-ja **PCR + OTM-inverse** (Bonferroni-tisztított, minimal scoring). **Ez helyes.** A modern methodology-k **fölé** kerülnek, **regime overlay** és **sizing modulator** szinten — **nem helyébe**.

Ez a "less is more" gondolat **mindkettő** methodology mély leckéje, ha az operátor figyelmesen tanulmányozza őket — és ezt **a populáris ábrázolás éppen elhomályosítja**.

---

# IV. AGGREGÁLT ACTION ITEMS

A két methodology tanulmányozásából **konkrét, végrehajtható** action item-ek (CC task-formátumra fordítandó):

| # | Action | Erőforrás | Fázis | Prioritás |
|---|--------|-----------|-------|-----------|
| A1 | 0DTE GEX regime overlay validation (UW shadow log + Polygon, 60-90 nap historical, regime classification + post-hoc P&L korreláció) | 6-10 óra | Phase 1 (W23) | P1 |
| A2 | HRP/HERC sizing design — BC22 dokumentum véglegesítése a 12 rolling pozícióra alkalmazva (Bridgewater risk-parity logika) | 4-6 óra spec + CC task | Phase 2 (W24) | P1 |
| A3 | Macro regime overlay design dokumentum (MID 4-quadrant → sizing multiplier) | 4-6 óra | Phase 2 (W24) | P1 |
| A4 | Time-of-day belépés A/B teszt (15:30 vs 16:00 vs 16:30 CEST, backtest a 60 napi adaton) | 4-6 óra | Phase 2 (W24) | P2 |
| A5 | Continuous vol-scaling (M_VIX redesign küszöb-mentesre, Bridgewater logika) | 3-5 óra spec + CC task | Phase 2-3 (W25) | P2 |
| A6 | 4-asset risk parity backtest (SPY/IEF/GLD/DBC, Sharpe + MaxDD + 2022 performance) | 5-8 óra | Phase 3 (post-W26) | P3 |
| A7 | Vertical spread overlay vizsgálat (csak ha A1-A5 sikeres) | TBD | Post Day 90 | P3 |

**Tanulási roadmap (parallel CC tasks-szel):**

| Anyag | Tematika | Ütemezés | Idő |
|-------|----------|----------|-----|
| Dim-Eraker-Vilkov (0DTE paper) | A1 megalapozása | Phase 1, W22-W23 | 6-10 óra |
| Asness-Frazzini-Pedersen (Leverage Aversion) | A2-A3 megalapozása | Phase 1-2, W22-W24 | 2-3 óra |
| Qian (Risk Parity Fundamentals) | A2 mélyítése | Phase 2-3, W23-W26 | 15-25 óra |
| Sinclair (Volatility Trading) | A1-A7 háttér | Phase 3+ | 25-35 óra |
| Dalio (Big Debt Crises) | A3 háttér | Phase 3+ | 8-15 óra |

**Összes effort becslés:**
- **Implementation (A1-A6)**: ~30-50 óra (CC tasks-on keresztül)
- **Spec és design dokumentumok**: ~20-30 óra (Dev chat)
- **Tanulás (minimum useful)**: ~30-40 óra
- **GRAND TOTAL**: ~80-120 óra, kb. **2-3 hónap parallel a swing pivot Phase 1-3 fázisokkal**

---

# V. FORRÁSMINŐSÍTÉS

**Megjelölés**: [○] = elsődleges/peer-reviewed, [◐] = ipari elismert, [●] = másodlagos/újságírói

| Forrás | Megjelölés | Megjegyzés |
|--------|------------|------------|
| Dim-Eraker-Vilkov "0DTEs: Trading, Gamma Risk and Volatility Propagation" (2024, SSRN 4692190) | [○] | Working paper, mainstream finance academia |
| Almeida-Freire-Hizmeri "0DTE Asset Pricing" (Princeton, 2024) | [○] | Princeton WP, peer-reviewed reputable authors |
| Adams-Fontaine-Ornthanalai (Bank of Canada / U. Toronto, 2024) | [○] | Central bank research, academic standards |
| Asness-Frazzini-Pedersen "Leverage Aversion and Risk Parity" (FAJ 2012) | [○] | Top-tier finance journal, peer-reviewed |
| Dalio "Principles for Navigating Big Debt Crises" (2018) | [◐] | Practitioner book, nem peer-reviewed, de elsődleges forrás Dalio-tól |
| Qian "Risk Parity Fundamentals" (2016, CRC Press) | [○] | Akadémikus szerző (PanAgora), peer-reviewed (de könyv, nem journal) |
| Sinclair "Volatility Trading" (2013) | [◐] | Practitioner book, de tankönyv-szintű kvantitatív |
| Cboe "0DTEs Decoded" (Mandy Xu, May 2025) | [◐] | Industry research, Cboe data, megbízható de promotional bias |
| SEBI India 105-page interim order on Jane Street (July 2025) | [◐] | Regulatórikus dokumentum, faktuális adatok, de egyirányú interpretáció |
| Institutional Investor "Bridgewater Extends Strong Run" (Oct 2025) | [◐] | Iparági szaklap, megbízható performance disclosure |
| ALLW ETF prospectus + State Street investor data | [○] | SEC filings, faktuális |
| Reuters "Jane Street rakes in record \$16.1B" (May 2026) | [◐] | Iparági hír, megbízható forrás |
| "Detailed Analysis of Jane Street's Market Manipulation" (marketcalls.in, 2025) | [●] | Indiai retail traders blog, alapja SEBI dokumentum (megbízható), de interpretáció biased |
| "Jane Street Big Moves 2025" (ainvest.com) | [●] | Iparági blog, tényadatok keverve marketinggel |
| TradeEdge / FlashAlpha 0DTE blogs (2025-2026) | [●] | Iparági blogok, hasznos heurisztikák, nem akadémiai |

**Megjegyzés a "Jane Street firm" forrásokkal kapcsolatban**: a Jane Street **nem publikál** firsthand stratégia-leírásokat. A dokumentumban szereplő methodology-leírás **közvetett forrásokra** támaszkodik (akadémiai, regulatórikus, és industry leak-ek). Aki precíz reprodukciót akar, **nem fog tudni**; a strukturális megértés azonban a közvetett forrásokból is elérhető.

**Bizonytalanságok és explicit hiányzó információk:**

- A Jane Street belső methodology pontos részletei **nem publikusak**, és **a dokumentumban szereplő profit-mix becslés** (§6.7) **becsült**, nem hivatalosan disclosure-ozott.
- A Bridgewater Pure Alpha pontos pozícionálási logikája **nem publikus**.
- A 2022-es risk-parity drawdown pontos forrása stratégia-szintű felülvizsgálatra ad okot, de **a tényleges Bridgewater-belső reakció** nem publikus.
- Az ALLW ETF pontos napi rebalance algoritmusa **csak general guideline-szinten** ismert.

Ahol konkrét számokra hivatkozom, ott a forrás a §13 felsorolásból kereshető. Ahol becslést adok ("körülbelül", "valószínűleg"), ott azt explicit jelöltem.

---

**A dokumentum vége.**

**Javaslat a következő lépésre:** az §12 A1 action item (0DTE GEX regime overlay validation) **közvetlenül belekerül** a Phase 1 backlog-ba mint CC task. A spec dokumentum 4-6 óra alatt megírható, a CC implementáció további 4-6 óra. Az **eredmény döntése** a Phase 2 (W23-W24) design fázis bemenete.

**Kérdezz vissza, ha:**
- Egy specifikus methodology-t mélyebben akarsz látni (pl. csak a Bridgewater regime nowcasting matematikája)
- A 0DTE GEX validation CC task-spec dokumentumát konkrétan akarod megírni
- Az AQR / factor decay témakör (D_B3 placeholder volt) is érdekel
