# Day 63 KIÉRTÉKELÉS — Döntési Dokumentum

**Dátum**: 2026-05-14 (csütörtök)
**Milestone**: Paper Trading Day 63/63 teljesítve
**Verzió**: 1.0
**Készült**: Chat (Claude) + Tamás (Product Owner)
**Célközönség**: Tamás (PO), CC (implementáció), jövőbeli Chat-instanciák
**Formátum**: stratégiai döntési dokumentum (NEM napi review)
**Kapcsolódó docs**:
- `docs/strategic-review/2026-05-08-strategic-review-summary.md` (5 oldal)
- `docs/strategic-review/2026-05-08-strategic-review-full.md` (25 oldal)
- `docs/strategic-review/2026-05-08-strategic-review-mathematical.md` (~30 oldal, formális keret)
- `docs/master-reference/` (5 fájl, élő dashboard)
- `docs/review/2026-05-08` → `2026-05-13-daily-review.md` (8 napi friss adat)

---

## Executive Summary

A 2026. március 13. és 2026. május 13. közötti 63 napos paper trading időszak (n=410+ ügylet) **technikailag sikeresen lezárult** — minden Day 63 keret-feltétel a biztonságos sávban maradt. **De a matematikai kiértékelés egyértelmű**: a jelenlegi rendszer **negatív expectancy-jű** (Kelly criterion $f^* = -0.23$ konzervatív, $-0.46$ default), **kvázi-zéró edge-gel** (Pearson $\rho(S, R) = -0.000$), és **19-21%-os éves súrlódás-teherrel**, ami **top decile hedge fund teljesítmény-szintet** igényelne a break-even-hez.

**Egy intézményi befektető ezt a stratégiát ma allokáció nélkül hagyná.**

Az eredmény azonban **NEM kudarc** — 63 napi élesben futás **erős kvantitatív megfigyeléseket** szolgáltatott, amelyek alapján **stratégiai pivot** lehetséges, NEM teljes leállítás. A "tiszta lap" megközelítés (Tamás döntés, 2026-05-13) **a matematikailag korrekt válasz**.

**14 stratégiai döntés** (6 fő + 2 kvantitatív technikai + 6 implementációs) lefekteti a következő 8-10 hetes átalakítást és az új 63 napos paper trading futás kereteit:

| # | Döntés | Választás |
|---|---|---|
| 1 | **Day trading vs Swing trading** | **SWING (3-5 nap hold)** |
| 2 | **UW API** | **Shadow log Day 90-ig**, scoring-ban deaktiválás |
| 3 | **15 backlog idea** | **KEEP 6 / REWORK 4 / DROP 5** |
| 4 | **Strategic-review nem-implementált** | **3 elvégzendő, 2 elvetendő** |
| 5 | **Reset roadmap** | **3 fázisú, W21-W30 (8-10 hét)** |
| 6 | **Entry/exit timing** | **15:30 CEST entry, 3-5 nap hold, mental stop** |
| 7 | **Pozíció-méretezés** | **Rolling 10-12 equal-weight, 0.35% risk/position** |
| 8 | **Time-stop** | **5 trading nap full MOC exit** |
| 9 | **Universum** | **S&P 500 + Russell 1000 (~1000 likvid)** |
| 10 | **Earnings exclusion** | **10 nap előretekintés (hold × 2)** |
| 11 | **Sector concentration cap** | **30% notional/szektor** |
| 12 | **Stop-loss típus** | **Mental stop, daily eval, NINCS IBKR bracket** |
| 13 | **Scoring revízió** | **PCR + OTM-inverse only** (Bonferroni-szignifikáns minimum) |
| 14 | **Új élesítési kritérium** | **Day 126: +\\$2,000 + Sharpe>0.5 + 25+ napi pos excess** |

**Új Day 126 milestone**: kb. 2026-09-15 (W37). Akkor lesz az élő kereskedés döntésnek **első valós alapja**.

---

## 1. Day 63 keret formális kiértékelése

### 1.1 Számszerű végeredmény (paper aggregát alapon)

| Mutató | 60 napi (strat-rev) | 63 napi (most) | Változás |
|---|---|---|---|
| Trading days | 60 | 63 | +3 |
| Ügyletek száma | 378 | ~410 | +32 |
| Kumulatív paper P&L | -\$1,460 | **-\$1,623.78** | -\\$163 |
| Kumulatív % (paper) | -1.46% | **-1.62%** | -0.16% |
| Tényleges valós (SQM/FORM/AAPL bug-korrekciókkal) | n/a | **~-\$1,400 to -\$1,500 (-1.40 to -1.50%)** | becsült |
| Win rate | 46.6% | ~45% (becsült) | -1.6% |
| Pearson r (kompozit S vs R) | -0.000 (p=0.996) | változatlan | n/a |
| Avg slippage | +0.20% | +0.10% (W19-W20 jobb) | -0.10% |
| Snapshot fix utáni adat | nincs | **8 nap, 142-161 qualified** | ÚJ |

### 1.2 Day 63 keret 3 kimenet kiértékelése

**Az eredeti Day 63 keret (2026-04-28 decision framework)** három kimenetet definiált:

| Kimenet | Feltétel | Eredmény |
|---|---|---|
| **ÉLESÍTÉS** | +\$3,000 ÉS +1.5% kumulatív excess vs SPY ÉS 20+ napi nem-Stagflation | **NEM teljesült** (kumulatív -\$1,623, távolság -\\$4,623) |
| **LEÁLLÍTÁS** | 10 napi excess átlag < -1.5% VAGY VIX > 25 30+ napra | **NEM aktivált** (10 napi átlag -0.35%, buffer ~1.15%; VIX W20 átlag 18.1) |
| **PAPER FOLYTATÁS** (default) | A két fenti egyike sem | ✓ **Aktivált** |

### 1.3 Hivatalos kimenet: PAPER FOLYTATÁS

A Day 63 keret szerinti **default kimenet AKTIVÁLT**. A paper trading folytatódik **DE radikálisan más architektúrán** (lásd 4. fejezet), NEM a jelenlegi setup inkremeális finomításával.

**A Day 63 keret elavult**: az ÉLESÍTÉS küszöb (+30% annualizált) **strukturálisan nem realisztikus** egy 19-21% éves súrlódás-teher mellett. A LEÁLLÍTÁS küszöb működik. **A keret revíziója szükséges** (lásd 7. fejezet — Új Day 126 milestone).

### 1.4 Komparáció a strategic-review (2026-05-08) javaslatával

A 2026-05-08-i strategic-review-summary 7.5 fejezete az **A + C kombináció + B párhuzamos R&D** útvonalat javasolta, **Day 90 értékeléssel**. **6 nap eltelt azóta**, és **5 új kvantitatív adatpont** változtatja a képet:

| Adatpont (2026-05-08 → 2026-05-13) | Új információ | Implikáció |
|---|---|---|
| Snapshot fix DEPLOYED | A scoring-validation újrafuttatható teljes mintán | A 60 napi r=0 finding stabil |
| 4 LOSS_EXIT bracket SL bug instancia | 13 napon belül, 1-2 nap eltolással is | Strukturális, NEM patchelhető |
| FORM + CENX dupla M-szankció pattern | Multi-feature kölcsönhatás (M_c × M_target, M_c × M_gex) | M_contradiction sign-flip a valószínűbb |
| UW HTTP 429 50→170+ ticker | A per-ticker fetch infrastrukturálisan instabil | UW használhatatlan production-ban |
| PAAS Breakeven Lock pozitív validáció | A feature alaplogikája rendben | Megtartandó az új architektúrán |

**Az A+C+B(R&D) javaslat helyett ma az indokolt választás: a B opció FÁZIS 2 azonnali indítása** (multi-day swing pivot), inkremeális finomítások nélkül. **A 6 nap új adat ezt egyértelműen alátámasztja.**

---

## 2. Intézményi szintű kritikai értékelés

A doc ezen szakasza **intézményi befektető szemmel** értékeli a rendszert. **NEM** a fejlesztői vagy hobby-perspektíva — egy hipotetikus külső allokátor (pl. fund-of-funds, family office, prop trading desk) szempontjából.

### 2.1 Risk-adjusted return analysis

A 60 napi minta empirikus Sharpe ratio (annualizált, mathematical doc 9.7):

$$\text{SR}_{60} \approx -38.8$$

Ez a szám **extrém**, és a kis n (60 nap) miatt **standard hibája is nagy** (kb. ±10-15 körüli intervallum). **De az IRÁNY egyértelmű**: a kockázat-arányosított hozam **erősen negatív**. Egy intézményi mandátum **0.5-0.7 minimum Sharpe**-ot követel meg a paper-szintű validációhoz; **0.8-1.5 Sharpe** a top decile hedge fund-szint.

**A jelenlegi rendszer ezen küszöbök közelébe sem ér**.

### 2.2 Signal-to-noise ratio

A Pearson $\rho(S, R) = -0.000$ (p=0.996) **erős bizonyíték** arra, hogy a true effect $|\rho_{\text{true}}| < 0.10$. A 80% statisztikai power-küszöbe ($n=378$): $|\rho_{\min}| = 0.144$ (mathematical doc 4.1).

**Implikáció**: a rendszer **edge-je** — ha létezik — **olyan kicsi, hogy a 60 napi adat azt nem detektálja**. Ez **NEM** azt jelenti, hogy nincs edge; csak azt, hogy a jelenlegi feature-set és horizon **alulvizsgált**.

**Stratégiai válasz**: a swing horizon (5×-ös mutual information növekedés) **a kvantitatív elsődleges esély** egy detektálható edge-re.

### 2.3 Operational risk

**A bracket SL bug 4 instancia 13 napon belül** = ~30% napi probabilitás egy duplikált zárásra. Egy production system **nem operálható ilyen frekvenciával** — egy intézményi prime broker az első hónapban felfüggesztené a számlát.

**A UW HTTP 429 instabilitás** (50→170+ ticker egy hét alatt) **strukturális adat-dependency risk**. Egy intézményi rendszer **redundáns adatforrásokkal** (2-3 független provider) működne. **A Polygon+FMP+FRED triász érdemleges baseline**, de **a UW egyedi feature-ei** (dark pool, GEX) **nem reprodukálhatók** alternatív szolgáltatóval.

**A `nuke.py --positions` scope-hiánya** (orders_cancelled: 0) **alapszintű operational hibája** — egy intézményi rendszerben **default cleanup logika** van.

### 2.4 Strategy character — explicit dokumentált

A 60+ napi minta **stabil karaktert mutat**:
- **Defenzív erő risk-off / lateral napokon** (+0.21%, +0.49% excess)
- **Gyengeség bull rally napokon** (-0.74% extrém ma; -0.78% átlag 4 bull napra)
- **Mid-cap / low-liquidity tickerek** rosszul teljesítenek (HYMC, SDRL, TGB)
- **High-cap blue-chip tickerek** breakeven körül (NVDA, AAPL, GOOG)

**Ez egy "low-beta + flow alpha attempt" karakter**. **A low-beta rész működik** (defenzív outperform). **A flow alpha attempt NEM működik** — pontosan ez a Pearson r=0 finding.

**Stratégiai implikáció**: a swing pivot **a flow alpha attempt-et erősítse** (multi-day mutual information), **a low-beta karaktert megtartva** (likvid mid+large-cap, S&P 500 + Russell 1000).

### 2.5 Verdikt

**A jelenlegi rendszer az aktuális formában NEM élesíthető.** **De az építőelemek** (snapshot fix, Breakeven Lock, sector rotation, az 1390-ticker Phase 2 universum-screener, a daily_metrics infra) **érdemleges fundament** egy újabb iterációhoz.

**A stratégiai pivot — NEM teljes elhagyás — a racionális válasz.**

---

## 3. A 14 stratégiai döntés részletes érvelése

### 3.1 Döntés [1]: Day trading vs Swing trading → SWING

**Helyzet**: a jelenlegi rendszer **kvázi-intraday** (16:20 entry → 22:00 MOC, 6 órás hold), de **napokon át tartó IBKR bracket struktúrával**. **Ez a hibrid** maga a strukturális bug-források gyökere.

**Opciók**:
- **Day trading proper**: 15:30 CEST entry + 22:00 MOC, csak intraday, no overnight, no bracket. Magas frequency, magas commission drag.
- **Swing proper**: 3-5 napos holding, NO intraday MOC, multi-day flow signal aggregation. Alacsonyabb frekvencia, alacsonyabb drag.
- **Status quo hibrid**: a 4 instancia bracket bug + entry timing finding miatt **strukturálisan rossz**.

**Érvelés Swing mellett**:
1. **Mathematical doc 5.2 mutual information modell**: a flow signal $h$-step mutual information $I \propto h \cdot \rho^2$. Ha $h=1$-step $\rho = 0.14$, akkor $h=5$ esetén $I \approx 0.10$ \(\Rightarrow\) **5× erősebb signal**. Az 5 napos swing **kvantitatív optimum** ezen modell szerint.
2. **Kelly criterion negatív** intraday horizon-on: $f^* \in [-0.23, -0.46]$. **Swing horizon-on a Kelly újrakalkulálható** — várható pozitív, ha a signal-strength tényleg 5×-ös.
3. **A LOSS_EXIT -2% küszöb agresszivitása** (NVDA, TGB ma) **intraday-spec probléma**. Swing-en NEM létezik (overnight gap-rezisztens).
4. **A bull rally underperform pattern** (-0.78% excess 4 bull napon) **intraday-spec**. Multi-day swing **overnight gap exposure-rel** másképp kezelhető.
5. **Bracket SL bug strukturális megszüntetése** — a mental stop (daily eval) **architektúrálisan kizárja** a bracket-trigger duplikációt (lásd 3.12 döntés).

**Day trading ELVETÉSE indoka**:
- A 60 napi adat **intraday horizonton mérte** a Pearson r=0-t — **újabb intraday futás várhatóan ugyanezt fogja mutatni**
- A magas frekvencia (5×/nap entry-exit) **commission drag-et növel**
- A flow signal **valódi lead-ideje** (a strategic-review szerint 3-5 nap) **NEM intraday**

**Status quo hibrid ELVETÉSE indoka**:
- 4 bracket SL bug instancia 13 napon belül **nem patchelhető architektúrális szinten**
- Az entry timing 16:20 vs 15:30 finding **csak kvantitatív backtest-tel** dönthető el, ami a fázis 2-ben **párhuzamosan** futhat a swing pivottal

**Implementáció**:
- Új scoring (Phase 4 revízió, lásd 3.13 döntés)
- Új risk management (overnight gap monitor, weekly SL, mental stop)
- Új position sizing (0.35% risk × 10-12 concurrent, lásd 3.7 döntés)
- IBKR bracket TP/SL **eltávolítva**, csak market BUY entry-vel és market SELL exit-tel

**Várt hatás**: a Kelly criterion **pozitív irányba mozdul** (várható $f^* > 0$ a swing horizonton). **A Day 126 milestone-n** a tesztelendő hipotézis.

### 3.2 Döntés [2]: UW API → Shadow log Day 90-ig, scoring-ban deaktiválás

**Helyzet**: a UW API jelenlegi használata: **dp_pct** (inverz prediktor, marginal sig $p=0.041$, alulvizsgált) + **GEX** (degenerált, 75% undetermined). **A 60-trade audit konfidencia-intervalluma** $\rho \in [-0.486, -0.012]$ **széles** — a true effect bizonytalan. **HTTP 429 instabil** infrastruktúra.

**Opciók**:
- **Azonnali elhagyás**: \$150/hó × 2 hó = \$300 megtakarítás. **DE**: elveszítjük az érdemleges power-rel ($n=150$, Day 90) történő validáció lehetőségét.
- **Shadow log + scoring deaktiválás**: marad heti \$150 költség, **de a scoring-ban neutral** értékek (dp_pct_score=0, M_gex=1.0). Day 90-en újraértékelés $n \approx 150-180$ mintán **érdemleges power-rel**.

**Érvelés Shadow log mellett**:
1. **Mathematical doc 4.4 power-analízis**: $n=60$ mintán a $|\rho|=0.265$ effekt **alulvizsgált** (power csak $|\rho|>0.353$-ra elég). **$n=150-180$ mintán** a $|\rho|=0.21$ detektálható 95% szignifikanciával.
2. **Bayesi update lehetőség**: a strategic-review 6.2 fejezetében a "classical opciós flow" Bayes-faktora 5-10× a "modern institutional flow" javára — **de** a prior konfidencia $\sim 0.55-0.65$, nem 0.9+. **A Day 90 friss adat** decisive update-et adhat.
3. **Opcionalitási érték**: \$300 egy intézményi context-ben **triviális ár** egy potenciális \$1,800/év recurring költség kontrollált validációjáért. A "real option" framework (mathematical doc 7.2) explicit kvantifikálja ezt.

**Stratégiai forgatókönyvek Day 90-en**:
- **Bull case** (true $\rho > 0.30$, vagy szignifikáns sign-flip-pel): UW marad, ÚJRA scoring-aktiválás
- **Base case** (true $\rho \in [-0.20, +0.20]$): UW elhagyás, Polygon+FMP+FRED triász véglegesítve
- **Bear case** (HTTP 429 frekvencia még magasabb, vagy true $\rho \approx 0$): azonnali elhagyás

**A Polygon+FMP+FRED triász jelenlegi gap-jei**:
- **PCR (Put-Call Ratio)**: a Polygon options endpoint-ról **kalkulálható** (low-cost CC build, ~2-3 óra). A jelenleg UW által szolgáltatott PCR helyettesíthető.
- **Dark pool %**: **NINCS** alternatív szolgáltató ezen az árszinten. UW egyedi.
- **GEX (Gamma Exposure)**: **NINCS** alternatív Polygon options strike-level data-n keresztül kalkulálható (saját implementáció, ~10-15 óra CC). **Magas effort, low confidence**.

**Ha Day 90-en UW elhagyás**: a `dp_pct` és `GEX` feature-ek **véglegesen kiesnek** a rendszerből. **A scoring-ban a PCR + OTM-inverse marad** (Bonferroni-szignifikáns minimum, lásd 3.13 döntés).

**Implementáció (most, Fázis 1)**:
- `defaults.py`: `weight_dp_pct = 0.0`, `M_gex = 1.0` minden ticker
- UW config: marad active, ne deploy-oljunk fix-et az 1.6 backlog idea-ra (UW rate limit kezelés — most P3-ra dropolt)
- Shadow log: a `daily_metrics.py` rögzítse a UW dp_pct + GEX értékeket egy külön `uw_shadow_*.json` fájlba, amit a Day 90 analízis használ

### 3.3 Döntés [3]: 15 backlog idea → KEEP 6 / REWORK 4 / DROP 5

A részletes mátrix a 4. fejezetben. **Lényeg**:

**KEEP 6 — Fázis 1 azonnali deploy (W21-W22)**:
1. LOSS_EXIT bracket SL cancellation (P1) — DROPOLVA, mert a mental stop architektúra megszünteti
2. ~~`nuke.py --orders` scope expansion~~ → DROPOLVA, swing-en a brackets megszűnnek
3. IBKR Gateway monitoring + Telegram alert (P1)
4. Entry timing backtest (P2 — analitikus, a swing pivot validációjához)
5. M_contradiction sign-flip analízis (P2)
6. Dinamikus pozíciószám (P2 — strategic-review 2026-04-11 #7 javaslat)

**REWORK 4 — a swing architektúrán átalakítva**:
1. Breakeven Lock profit-küszöb csökkentés (P2 → P3, swing-en kevésbé kritikus)
2. TP1 cél revízió (P2 → swing TP/exit struktúrába integrálva)
3. 10-Q SEC Filing Exclusion (P1 → P1, **swing-en KRITIKUSABB** — 10 napi earnings ablakkal kombinálva)
4. ADR earnings adatforrás fix (P1 → P2, swing-en kevésbé akut)

**DROP 5 — nem releváns új architektúrán**:
1. UW rate limit kezelés finomítás (UW shadow log, nem scoring-elem)
2. dp_pct fallback default (UW elhagyandó scoring-ból)
3. Slippage-adjusted scoring validation (új architektúrára épülő scoring-validation eleve slippage-szembesített)
4. monitor.py belső replay események jelölése (alacsony prioritás, későbbi fázis)
5. High-score liquidity check (a "magas pontszám paradoxon" a scoring revízión át kezelendő — Bonferroni-minimum)

**Plus 2 új DROP a swing pivot következményeként**:
- **LOSS_EXIT bracket SL cancellation** (eredeti P1 #1, 4 instancia bug): a mental stop architektúra **strukturálisan eliminálja** \(\Rightarrow\) a fix elavul, NEM kell deploy-olni
- **`nuke.py` scope expansion**: ugyanígy, a swing-en NINCS bracket order \(\Rightarrow\) a `nuke.py --positions` elég

**Implementációs implikáció**: a Fázis 1 (W21-W22) **drasztikusan rövidül** — sok korábbi P1 már elavul az új architektúrán.

### 3.4 Döntés [4]: Strategic-review nem-implementált → 3 elvégzendő, 2 elvetendő

A 2026-04-11-i 13 pontos terv 5 nem-implementált eleme:

**ELVÉGZENDŐ (új swing architektúrán)**:
- **#7 Dinamikus pozíciószám** (várt +0.5-1% havi alpha): MUST DO. A swing-en **különösen kritikus** — ha nincs minőségi flow signal, NE forszáljunk pozíciókat. A 10-12 max concurrent nem **kötelező napi 2-3 entry**-t jelent.
- **#10 Call wall T1 kikapcsolás**: egyszerűsítés. A swing TP/exit struktúrában nincs T1 — full revízió.
- **#11 VWAP guard egyszerűsítés**: egyszerűsítés. A swing-en az entry **15:30 market open**, VWAP nem releváns.

**ELVETÉS**:
- **#12 Multiplier chain egyszerűsítés**: a swing pivot **teljes scoring-átalakítása** ezt magába foglalja (csak $M_{\text{target}}$ marad, esetleg $M_{\text{contradiction}}$ sign-flip elemzéstől függően).
- **#13 Flow al-komponens dekompozíció**: **MÁR ELVÉGEZTE** a 232-trade audit. Eredmény: PCR + OTM-inverse a Bonferroni-szignifikáns minimum (lásd 3.13).

### 3.5 Döntés [5]: Reset roadmap → 3 fázisú, W21-W30

Részletes ütemezés a 6. fejezetben. **Lényeg**:

**Fázis 1 (W21-W22, máj 19 - máj 30 — 2 hét) — OPERATIONAL CLEANUP**:
- IBKR account reset (Tamás)
- UW scoring deaktiválás (Chat config + CC)
- Strategic-review docs \$354→\$665 korrekció (Chat, 10 min)
- `daily_metrics.py` shadow log bővítés (CC, 30 min)
- Backlog idea housekeeping (Chat: master-reference frissítés)

**Fázis 2 (W23-W24, jún 2 - jún 13 — 2 hét) — ANALYTIC**:
- Entry timing backtest (Chat, 1-2 óra)
- M_contradiction sign-flip elemzés (Chat, 1 óra)
- Scoring revízió design (Chat + Tamás review)
- Új risk management spec (Chat + CC, 2-3 óra)
- Pozíció sizing infrastruktúra (CC, 2-3 óra)

**Fázis 3 (W25-W30, jún 16 - júl 25 — 6 hét) — RE-DEPLOY + ÚJ PAPER TRADING**:
- Új scoring deploy (CC, 3-4 óra)
- Új risk management deploy (CC, 5-8 óra)
- Új position sizing deploy (CC, 2-3 óra)
- IBKR paper account reset (Tamás, kb. jún 23)
- **Új 63 napos paper trading kezdődik kb. jún 23 (W25 D1)**
- **Új Day 63 milestone: kb. 2026-09-15 (W37)** — az élő kereskedés döntésének valós alapja

### 3.6 Döntés [6]: Entry/exit timing → 15:30 CEST entry, 3-5 nap hold, mental stop

A swing pivot közvetlen következménye.

**Entry**: 15:30 CEST = 09:30 ET market open. **A 2.5 backlog idea (entry timing backtest)** validálja a 60+ napi adaton, de a swing horizonton **az opening price strukturálisan optimális** a flow signal aggregation után (a Phase 2-4-5-6 pipeline 14:15 CEST után fut, az execution_plan 14:30 körül kész — bőven idő a 15:30 market open-i submit-re).

**Hold**: 3-5 trading nap. A **time-stop 5 nap** (3.8 döntés) hard limitet ad. A korai exit (TP hit, SL hit, mental stop) lehetséges.

**Mental stop**: nincs IBKR bracket SL. A `monitor.py` 22:00-i EOD futása **napi close árat** értékeli minden pozícióra:
- Ha close < entry × (1 - 2×ATR%) \(\Rightarrow\) másnap reggel 15:30 CEST MARKET SELL
- Intraday "panic" gap (>5% mid-day mozgás): 17:00 monitor opcionálisan trigger-elhet

**Hard SL (catastrophic)**: pozíció-szintű -8% weekly cumulative \(\Rightarrow\) azonnali full MARKET SELL. Ez egy biztonsági háló, NEM normál exit.

### 3.7 Döntés [7]: Pozíció-méretezés → Rolling 10-12 equal-weight, 0.35% risk

A 2 kvantitatív technikai döntés egyike, részletes elemzés a 2026-05-14 chat-conversation-ben.

**Paraméterek**:
- Risk per position: **0.35% (\\$350)**
- Stop multiplier: **2.0× ATR** (overnight gap buffer)
- Avg notional per position: \\$6,000-8,000
- Concurrent positions cap: **12 (steady state ~10)**
- Daily new entries: **2-3** (NEM kötelező napi 3-5 a jelenlegi 5-ből)
- Total gross exposure: \\$80-100k (similar to current)
- Total portfolio VaR: **4-6% steady** (vs jelenlegi 10-15% spike)

**Sizing képlet**:

```
notional_i = (equity × 0.0035) / (ATR_pct × 2.0) × entry_price
```

**Példák**:

| Ticker | Ár | Daily ATR | Stop distance | Notional | Qty |
|---|---|---|---|---|---|
| NVDA | \$220 | 3% | \$13.20 | \\$5,833 | 26 share |
| FORM | \$150 | 5% | \$15.00 | \\$3,500 | 23 share |
| AAPL | \$290 | 2.5% | \$14.50 | \\$7,000 | 24 share |

A magas-vol tickerek **automatikusan kisebb pozíciót kapnak** (volatility-adjusted).

### 3.8 Döntés [8]: Time-stop → 5 trading nap full MOC exit

A 2. kvantitatív technikai döntés.

**Triggerek (prioritási sorrendben)**:
1. **TP2**: +3.0× ATR (~+8-10%) \(\Rightarrow\) teljes pozíció zárás
2. **TP1**: +1.5× ATR (~+4-5%) \(\Rightarrow\) 50% qty zárás, trail SL felfelé
3. **Mental stop (SL)**: close < entry - 2.0× ATR \(\Rightarrow\) másnap MARKET SELL
4. **Time-stop**: 5 trading nap eltelt \(\Rightarrow\) teljes pozíció MOC SELL
5. **Hard SL (catastrophic)**: -8% weekly cumulative \(\Rightarrow\) azonnali MARKET SELL

**Indoklás 5 nap**:
- Mathematical doc 5.2 mutual information optimum: $h \in \{3, 5\}$ nap
- Heti rhythmm-mel kompatibilis (hétfő entry → péntek exit)
- A 60+ napi flow signal lead-time-ja ~3-5 nap (strategic-review-summary)
- Az overnight gap exposure 5×-szöröse a 1 napinak — kezelhető 2.0× ATR mental stop-pal

### 3.9 Döntés [9]: Universum → S&P 500 + Russell 1000 (~1000 likvid)

**Helyzet**: jelenleg Phase 2 1390 ticker → 142-161 qualified. A swing 3-5 napos hold strukturálisan érzékenyebb a **likviditásra** (overnight gap, multi-day price discovery).

**Érvelés**:
- A 60 napi minta **mid/small-cap tickerei** (HYMC \$44, SDRL \$43, TGB \\$7) **gyakran a vesztes oldalon**
- A swing-en a **likvid mid+large-cap** jobb pivotálási environment
- S&P 500 (500 ticker) + Russell 1000 (top 1000 by market cap, de S&P 500 hozzátartozik) = **kb. 1000 unique ticker**, mind likvid (market cap > \$2B, avg volume > \$50M)
- A small-cap universum (Russell 2000 mid+small, kb. 2000 ticker) **elveszett** — **de** a 60 napi adat azt mutatja, hogy ez **NEM negative impact** (a small-cap a veszteseink fő forrása)

**Implementáció**: Phase 2 universe builder módosítás (CC, 1-2 óra). Új constants: `RUSSELL_1000_TICKERS`, `SP500_TICKERS`, union → universe.

### 3.10 Döntés [10]: Earnings exclusion → 10 nap előretekintés

**Indoklás**: 5 napi hold × 2 = **10 nap előretekintés**, hogy a pozíció **teljes ideje** earnings-free legyen.

**Példa**: hétfő (D1) entry → péntek (D5) exit (5 trading nap). Ha a ticker earnings szerda van (D3), a pozíció **3 napi gap-kockázattal** szembesül. A 10 napi exclusion ezt megakadályozza.

**Plus**: a **10-Q SEC Filing Exclusion** (P1 backlog idea) **újra-aktiválandó P1-re** — egy 10-Q közben kiadott swing pozíció overnight 5-10%-ot mozdulhat (lásd AGNC máj 4 esete).

**Implementáció**: a jelenlegi `earnings_exclusion_days: 7` → `10` a `defaults.py`-ban. **Plus** a CC `10-Q exclusion` task deploy (P1, 2-3 óra).

### 3.11 Döntés [11]: Sector concentration cap → 30% notional/szektor

**Helyzet**: jelenleg 2 ticker/sector kemény cap, 5 concurrent mellett ~40% maximum.

**Érvelés a notional-alapra**:
- **Intézményi sztenderd** (dollár-koncentráció, NEM ticker-szám)
- A 10-12 concurrent mellett a 3 ticker/sector cap **túl szigorú** (csak 25% maximum)
- A 30% notional gives flexibility: lehet 4-5 közepes pozíció vagy 2-3 nagyobb egy szektorban
- VaR számítása **könnyebb** dollár-koncentráción alapulva

**Számítás**: 30% × \$80k gross = **\$24k max egy szektorban**. Ha az átlag pozíció \\$6,000, akkor **max 4 ticker/szektor** dollár-arányosan.

**Implementáció**: a Phase 6 sizing módosítás (CC, ~1 óra). A `max_per_sector_pct: 0.30` új paraméter.

### 3.12 Döntés [12]: Stop-loss típus → Mental stop, daily eval, NINCS IBKR bracket

A swing pivot **legmélyebb architektúrális változása**. Részletes elemzés a 2026-05-14 chat-conversation-ben.

**Lényeg**:
- IBKR bracket TP/SL **eltávolítva**
- Csak market BUY entry (15:30 CEST) + market SELL exit (mental stop, TP, time-stop, hard SL)
- `monitor.py` 22:00-i EOD futása **napi close árat** értékeli \(\Rightarrow\) másnap reggel MARKET SELL ha SL átment

**Strukturálisan kiküszöböli**:
- A 4 instancia bracket bug (DTE, SQM, FORM, AAPL)
- A `nuke.py --positions` scope-hiánya (nincs függő bracket order)
- Az intraday volatilitás okozta agresszív LOSS_EXIT (-2% küszöb intraday-spec)

**Trade-off — overnight gap risk**:
- Ha pénteken close \$200, hétfő nyitás \$185 (-7.5%) \(\Rightarrow\) a "tervezett" -6% SL **nem teljesül** szigorúan
- **Ezért a 0.35% risk per position konzervatív** — egyetlen gap nem dönt
- **A hard SL (-8% weekly)** kezelni a catastrophic gap eseteket

**Implementáció**: `submit_orders.py` refaktor (CC, ~3-4 óra). A bracket TP/SL eltávolítása, `monitor.py` SL evaluation logika hozzáadása.

### 3.13 Döntés [13]: Scoring revízió → PCR + OTM-inverse only (Bonferroni-minimum)

A **legradikálisabb scoring döntés**. **Csak a Bonferroni-szignifikáns 2 al-komponens** marad.

**Indoklás**:
- Mathematical doc 4.3: 14 hypothesis-teszt után **csak PCR ($\rho=+0.203^{**}$) és OTM-call ($\rho=-0.194^{**}$) marad szignifikáns**
- Az RVOL ($\rho=+0.147$) Bonferroni után **NEM szignifikáns** (a kritikus küszöb 0.193)
- A többi 4 al-komponens (dark pool %, block trade, buy pressure, squat bar) **nem prediktív**
- A tech sub-score ($\rho \approx 0.05$) és funda sub-score ($\rho \approx 0$) **kvázi-zaj**

**Új scoring funkcionál**:

```
S_j(t) = 100 × (PCR_score_j(t) - OTM_score_j(t)) + sector_rotation_adjustment(t)
```

Ahol:
- `PCR_score_j(t)` \(\in\) [0, 1]: normalizált put-call ratio (alacsony = bullish, magas = bearish kontraindikátor)
- `OTM_score_j(t)` \(\in\) [0, 1]: normalizált OTM call ratio (magas = retail FOMO kontraindikátor, **NEM bullish**)
- Sector rotation: a Phase 3 leader/laggard adjustment (a meglévő működik)

**Threshold**: csak `S_j > 50` tickerek kvalifikálnak (nincs kompozit-küszöb 70 vagy 85). A daily top-N (10-12) **rangsor** alapján szelektál a Phase 6.

**Multiplier chain — drastikusan egyszerűsödik**:
- $M_{\text{VIX}}$ → **DEAKTIVÁLVA** (degenerált a 60 napi mintán, VIX < 20)
- $M_{\text{GEX}}$ → **DEAKTIVÁLVA** (75% undetermined, UW shadow log csak)
- $M_{\text{contradiction}}$ → **DEAKTIVÁLVA** (33% iránybeli helyesség, sign-flip Day 90 elemzés után dönt)
- $M_{\text{target}}$ → **MARAD** (>20% overshoot → ×0.85, >50% → ×0.60). Ez **kvalitatív védelem** a túlfutásra.

**Egyszerűsödés mértéke**: a Phase 4 7-komponens flow + 3-komponens tech + 6-komponens funda → **2-komponens flow + sector adjustment**. A multiplier chain 4 szorzó → **1 szorzó (M_target)**. A pipeline **~70%-kal egyszerűbb**.

**Várt hatás**: a flow signal **tiszta**, NEM noise-elnyelt. A Bonferroni-szignifikáns 2 komponens **valódi edge-et** jelez a swing horizonton. **Day 126 milestone tesztel.**

### 3.14 Döntés [14]: Új élesítési kritérium → Day 126: +\\$2,000 + Sharpe>0.5 + 25+ napi pos excess

A jelenlegi Day 63 keret (+\\$3,000 / -1.5% leállítás) **strukturálisan nem realisztikus** (~+30% annualizált a 19-21% éves súrlódás-teher felett).

**Új keret (Day 126, kb. 2026-09-15)**:

| Kritérium | Küszöb | Megjegyzés |
|---|---|---|
| Kumulatív paper P&L | > **+\$2,000** | ~+8% annualizált (+\$100k tőkén) |
| Sharpe ratio (60 napi) | > **0.5** | Statisztikailag érdemleges (top quartile alatt) |
| Pozitív excess vs SPY napok | > **25 / 63 nap** (40%) | Karakter-konzisztencia tesztje |

**Mindhárom egyidejűleg** kell teljesülnie az ÉLESÍTÉS-hez.

**LEÁLLÍTÁS feltételek**:
- 10 napi excess vs SPY átlag < **-1.0%** (szigorúbb mint a jelenlegi -1.5%)
- VAGY 30 napi kumulatív < **-3.0%** (catastrophic drawdown)
- VAGY 15 napi excess < **-1.0%** (gyors leállítás-trigger)

**DEFAULT**: PAPER FOLYTATÁS, Day 180 újraértékelés.

**Indoklás a magasabb bar mellett**:
- A 0.5 Sharpe **statisztikailag detektálható** edge a Day 126 mintán (60+ napi adat)
- A +\\$2,000 **realisztikus** ha a swing pivot tényleg 5×-szöröse a signal mutual information-t
- A 25+ napi pozitív excess **karakter-teszt** — a "low-beta defensive + flow alpha attempt" valós-e

**Élesítés esetén**: \$10,000 tőkével élő pénzes trading, **3% drawdown circuit breaker**, **napi notional limit** (max \$25k single, \\$200k total).

---

## 4. A 15 backlog idea KEEP/REWORK/DROP mátrixa

| # | Backlog idea | Eredeti prioritás | Új döntés | Új prioritás | Indoklás |
|---|---|---|---|---|---|
| 1 | LOSS_EXIT bracket SL cancellation | P1 (kritikus) | **DROP** | n/a | A mental stop architektúra strukturálisan eliminálja |
| 2 | `nuke.py --orders` scope expansion | P1 | **DROP** | n/a | A swing-en NINCS bracket order |
| 3 | IBKR Gateway monitoring + Telegram alert | P1 | **KEEP** | P1 | Operational risk, swing-en is releváns |
| 4 | UW rate limit kezelés finomítás | P1 | **DROP** | n/a | UW shadow log, scoring-ban deaktiválva |
| 5 | 10-Q SEC Filing Exclusion | P1 | **REWORK** | **P1** | Swing-en **KRITIKUSABB** (10 napi earnings ablakkal) |
| 6 | ADR earnings adatforrás fix | P1 | **REWORK** | P2 | Swing-en kevésbé akut |
| 7 | Breakeven Lock profit-küszöb csökkentés | P2 | **REWORK** | P3 | Swing TP/exit struktúrába integrálva |
| 8 | TP1 cél revízió | P2 | **REWORK** | P2 | Új TP-struktúra (1.5/3.0× ATR) |
| 9 | M_contradiction × M-szorzó deduplikáció | P2 | **REWORK** | **P2** | Most: M_c sign-flip vizsgálat (Day 90) |
| 10 | LOSS_EXIT küszöb finomítás per-ticker ATR | P2 | **DROP** | n/a | Mental stop architektúra |
| 11 | Entry timing optimalizáció backtest | P2 | **KEEP** | **P2** | **Kvantitatív megalapozás a swing pivot mellett** |
| 12 | Phase 4 snapshot enrichment | P3 | **KEEP** | P3 | Hosszú távú strukturális |
| 13 | High-score liquidity check | P3 | **DROP** | n/a | A scoring revízió a Bonferroni-minimumra kezelendő |
| 14 | dp_pct fallback default (universum-medián) | P3 | **DROP** | n/a | dp_pct scoring-ban deaktiválva |
| 15 | Slippage-adjusted scoring validation | P3 | **DROP** | n/a | Az új scoring eleve slippage-szembesített |
| 16 | monitor.py belső replay események jelölése | P3 | **DROP** | n/a | Alacsony prioritás, későbbi |
| **Új** | **Dinamikus pozíciószám** | n/a (strategic-review #7) | **KEEP** | **P2** | A swing-en KRITIKUS — ne forszáljunk pozíciókat |

**Új W21+ aktív lista (6 tétel)**:

| Prioritás | Idea | Effort | Owner | Fázis |
|---|---|---|---|---|
| **P1** | IBKR Gateway monitoring + Telegram alert | ~1 óra | CC | Fázis 1 |
| **P1** | 10-Q SEC Filing Exclusion (10 napi earnings + 10-Q) | ~2-3 óra | CC | Fázis 1 |
| **P2** | Entry timing optimalizáció backtest | ~1-2 óra | Chat | Fázis 2 |
| **P2** | M_contradiction sign-flip vizsgálat | ~1 óra | Chat | Fázis 2 |
| **P2** | TP1 cél revízió (új TP-struktúra) | ~30 min config + ~1 óra CC | CC | Fázis 2 |
| **P2** | Dinamikus pozíciószám | ~1 óra CC | CC | Fázis 2 |
| P2 | ADR earnings adatforrás fix | ~3-4 óra CC | CC | Fázis 3 |
| P3 | Breakeven Lock profit-küszöb (swing-integrált) | ~30 min config | CC | Fázis 3 |
| P3 | Phase 4 snapshot enrichment | ~30-45 min CC | CC | Fázis 3 |

**Drasztikus csökkenés**: 15+1 idea → **9 aktív** (4 P1, 4 P2, 1 P3). **6 dropolva, 4 átalakítva**.

---

## 5. Strategic-review nem-implementált revíziója

A 2026-04-11-i 13 pontos terv 5 nem-implementált elemének részletes kezelése:

| # | Eredeti javaslat | Új döntés | Indoklás |
|---|---|---|---|
| #7 | Dinamikus pozíciószám | **ELVÉGZENDŐ Fázis 2-ben** | Swing-en kritikus — ne forszáljunk pozíciókat |
| #10 | Call wall T1 kikapcsolás | **AUTOMATIKUSAN MEGTÖRTÉNIK** | A scoring egyszerűsítés (3.13 döntés) kiveszi a M_GEX-et |
| #11 | VWAP guard egyszerűsítés | **AUTOMATIKUSAN MEGTÖRTÉNIK** | Az új entry (15:30 market open) NEM AVWAP-alapú |
| #12 | Multiplier chain egyszerűsítés | **ELVÉGZENDŐ Fázis 2-ben** | 4 szorzó → 1 (M_target) |
| #13 | Flow al-komponens dekompozíció | **MÁR ELVÉGEZTE** | A 232-trade audit szolgáltatta a Bonferroni-eredményeket |

---

## 6. A 3 fázisú reset roadmap részletes ütemterve

### Fázis 1 (W21-W22, máj 19 - máj 30 — 2 hét) — OPERATIONAL CLEANUP

**Cél**: a régi architektúra "lezárása", az új scoping előkészítése.

**Tamás (manuális, MacMini)**:
- **Máj 19 (h, W21 D1)**: `nuke.py --positions` AAPL/AVDL.CVR teljes takarítás
- **Máj 19**: IBKR TWS UI ellenőrzés — minden függő bracket TP/SL order manuális cancel-elése (esetleg API hívással egy ad-hoc script)
- **Máj 20-22 (k-cs)**: IBKR paper account reset — minden pozíció, minden függő order kitakarítva, \\$100k újra
- **Máj 23-25 (p-v)**: pihenés

**Chat (én, MacBook)**:
- **Máj 19-20**: Master-reference frissítés a Day 63 döntésekkel (15 backlog → 9 aktív, deprecated lista)
- **Máj 19**: Strategic-review docs \$354→\$665 korrekció (2.4 fejezet a full-ban + a mathematical 4.5)
- **Máj 21-23**: A Day 63 doc finalizálása, Tamás review
- **Máj 24-30**: Új architektúra design dokumentumok (`docs/design/swing-pivot-architecture.md`)

**CC (implementáció, MacBook → Mac Mini)**:
- **Máj 19-22 (W21)**: IBKR Gateway monitoring + Telegram alert (1.7 → 1.6 backlog) — ~1 óra
- **Máj 23-25**: 10-Q SEC Filing Exclusion + 10 napi earnings exclusion bővítés — ~2-3 óra
- **Máj 26-30 (W22)**: UW config: scoring-ban deaktiválás, shadow log infra (`uw_shadow_*.json`) — ~1-2 óra

**Fázis 1 deliverable**: a régi rendszer "tiszta", az új rendszer technikai alapja előkészítve. A `defaults.py` átmeneti config-tal (UW deaktiválva, 10 napi earnings, IBKR monitoring aktív).

### Fázis 2 (W23-W24, jún 2 - jún 13 — 2 hét) — ANALYTIC + DESIGN

**Cél**: a swing pivot kvantitatív megalapozása + technikai design.

**Chat (analitikus + design)**:
- **Jún 2-6 (W23)**:
  - Entry timing backtest (2.5 backlog, ~1-2 óra) — 4 alternatív időablak a 60+ napi adaton
  - M_contradiction sign-flip elemzés (2.3 backlog, ~1 óra) — n=6 fired esetből 4 nyertes \(\Rightarrow\) döntés
- **Jún 9-13 (W24)**:
  - Új scoring design dokumentum (`docs/design/swing-scoring-spec.md`) — Bonferroni-minimum (PCR + OTM-inverse)
  - Új risk management spec (mental stop, time-stop, hard SL) — `docs/design/swing-risk-spec.md`
  - Új position sizing spec (rolling 10-12, 0.35% risk) — `docs/design/swing-sizing-spec.md`
  - Tamás review (kb. 1-2 óra)

**CC (előkészítés)**:
- **Jún 2-13**: a design specifikációk alapján **prototípusok** (unit-test szinten) az új scoring funkcionálhoz. NEM deploy. Effort: ~3-5 óra.

**Tamás**:
- **Jún 2-13**: review a design dokumentumokon, kérdések, módosítások

**Fázis 2 deliverable**: 3 design doc + entry timing + M_contradiction analízis (mind a `docs/strategic-review/` mappába, mint Day 63 kiegészítő dokumentumok).

### Fázis 3 (W25-W30, jún 16 - júl 25 — 6 hét) — RE-DEPLOY + ÚJ PAPER TRADING

**Cél**: az új architektúra élesítése + 63 napi paper trading futás.

**CC (implementáció)**:
- **Jún 16-20 (W25)**:
  - Új scoring funkcionál deploy (`scoring/new_swing_scoring.py`) — ~3-4 óra
  - Universum builder módosítás (S&P 500 + Russell 1000 union) — ~1-2 óra
- **Jún 22-25 (W26 első napjai)**:
  - Új risk management deploy (mental stop, time-stop, hard SL) — `monitor.py` + `pt_close.py` átalakítás — ~5-8 óra
  - Új position sizing deploy (rolling 10-12, 0.35% risk, 30% sector cap) — `submit_orders.py` átalakítás — ~3-4 óra
- **Jún 26-30**: integration tests, smoke tests — ~3-5 óra

**Tamás**:
- **Kb. jún 23 (W26 hétfő)**: **IBKR paper account reset** és **új paper trading INDUL Day 1-en**
- Napi monitoring (kb. ahogyan most)

**Chat**:
- **Jún 23-30**: napi review-k az új rendszerről (W26 első hete, kritikus megfigyelési időszak)
- **Júl 1-25 (W27-W30)**: napi review-k + heti elemzések, master-reference frissítés

**Fázis 3 deliverable**: 63 napos paper trading futás az új swing architektúrán. **Day 63 milestone kb. 2026-09-15 (W37)**.

### Időrendi összefoglaló

```
W21  máj 19-23  Fázis 1 — Operational cleanup (Tamás + Chat + CC)
W22  máj 26-30  Fázis 1 — Operational cleanup + új design előkészítés
W23  jún 2-6    Fázis 2 — Analytic (entry timing + M_contradiction)
W24  jún 9-13   Fázis 2 — Design dokumentumok
W25  jún 16-20  Fázis 3 — Új scoring + universum deploy
W26  jún 23-27  Fázis 3 — Új risk + sizing deploy + paper trading INDUL
W27  jún 30-júl 4   Fázis 3 — Paper trading W2
...
W37  szept 15-19    Fázis 3 vége — Új Day 63 milestone
```

**Total effort becslés**: ~50-60 óra CC + ~30-40 óra Chat + ~10-15 óra Tamás manuális workflow

---

## 7. Új Day 126 milestone (kb. 2026-09-15)

### 7.1 Definíció

**Day 126** = az új paper trading 63 napja után. A teljes Day 0 (kezdés) — Day 126 (kiértékelés) **126 napos időszak** (eredeti 63 + új 63), de **a tényleges paper trading új mintaadata 63 nap**.

**Naptári dátum (becsült)**: 2026-09-15 (csüt) ± 1 hét, a Fázis 3 indulásától függően.

### 7.2 ÉLESÍTÉS kritériumai (3 feltétel együtt)

**Kritérium 1 — Kumulatív paper P&L**:
$$\text{Cumulative P\&L}_{63} > +\\$2{,}000$$
(~+8% annualizált, +\\$100k tőkén)

**Kritérium 2 — Sharpe ratio (annualizált)**:
$$\text{Sharpe}_{63} > 0.5$$
(top quartile alatt, de statisztikailag érdemleges)

**Kritérium 3 — Pozitív excess vs SPY napok**:
$$|\{t : r_{\text{port},t} > r_{\text{SPY},t}\}| > 25 / 63$$
(40% napi outperform aránya — karakter-konzisztencia)

**Mindhárom egyidejűleg** kell teljesülnie.

### 7.3 LEÁLLÍTÁS kritériumai (bármelyik)

- 10 napi excess vs SPY átlag < **-1.0%** (szigorúbb mint -1.5%)
- 30 napi kumulatív < **-3.0%** (catastrophic drawdown)
- 15 napi excess < **-1.0%** (gyors leállítás-trigger)

**Aktiválódás esetén**: 24 órás cooldown + graceful exit. Új strategic-review készül, esetleg **teljes projekt leállítás** mint utolsó opció.

### 7.4 DEFAULT — PAPER FOLYTATÁS

Ha sem ÉLESÍTÉS, sem LEÁLLÍTÁS nem aktivál: **paper trading folytatódik Day 180 (kb. 2026-11-15) újraértékelésig**. A 60 további napi adat az alkalmazott architektúra **kvantitatív érdemleges validációja**.

### 7.5 Élesítés esetén — élő pénzes trading

**\\$10,000 tőkével** induló élő trading.

**Védelmek**:
- **3% drawdown circuit breaker** automatikus leállítással
- **Napi notional limit**: max \$25k single position, \$200k total daily turnover
- **Pre-submit Telegram notification** minden order előtt 5 perc cooldown-nal
- **Weekly review** (kötelező manuális Tamás-átfutás, nincs hands-off)
- **Account-szintű VaR limit**: 4% (a 0.35% × 12 = 4.2% theoretical max alapján)

**Allokáció scaling**: ha az élő \$10k tőke 30 napra pozitív (>+\$300 net), akkor **opcionálisan \\$25k-ra emelhető**. **Soha NEM** automatikus — Tamás manuális döntése.

### 7.6 A 3 kimenet stratégiai következménye

| Day 126 kimenet | Action | Időhorizont |
|---|---|---|
| **ÉLESÍTÉS** | \\$10k élő pénzes trading indul | W37+ azonnali |
| **LEÁLLÍTÁS** | Graceful exit, post-mortem strategic-review | W38-W40 |
| **DEFAULT (folytatás)** | 60 további napi paper, Day 180 újraértékelés | W37-W46 |

---

## 8. Mellékletek

### 8.1 8 napi friss adat (2026-05-06 → 2026-05-13) — a Day 63 előtti utolsó adatok

| Nap | Net P&L | Cum P&L | SPY | Portfolio | Excess | LOSS_EXIT % | Megjegyzés |
|---|---|---|---|---|---|---|---|
| W19 D3 sze | +\$234 | -\$355 | +1.39% | +0.25% | -1.14% | 0% | bull underperform |
| W19 D4 csü | -\$501 | -\$857 | -0.31% | -0.49% | -0.18% | 25% (SQM) | risk-off near-neutral, SQM bug |
| W19 D5 pé | +\$486 | -\$371 | ~0% | +0.49% | +0.49% | 0% | lateral outperform |
| W20 D1 hé | +\$28 | -\$343 | +0.23% | +0.03% | -0.19% | 0% | mild bull underperform, manuális 17:15 entry, snapshot fix DEPLOYED |
| W20 D2 ke | -\$369 | -\$712 | -0.15% | -0.35% | -0.20% | 80% (TGB, NVDA) | mild risk-off underperform, entry timing finding |
| **W20 D3 sze** | **-\$189** | **-\$901** | **+0.56%** | **-0.18%** | **-0.74%** | 50% (SSRM) | **bull rally EXTRÉM underperform, FORM/AAPL bug 3+4 instancia** |

**Megjegyzés**: a "Cum P&L" itt a 6 napi mintán belüli kumulatív, NEM a teljes 63 napi. A teljes 63 napi kumulatív: **-\$1,623.78 (paper aggregát) / ~-\$1,400-1,500 (tényleges valós, becsült)**.

### 8.2 Kvantitatív szöveg-statisztikák (60 napi mathematical doc)

| Mutató | Érték | Statisztikai értelmezés |
|---|---|---|
| Pearson $\rho(S, R)$ | -0.0003 | $H_0$ NEM elutasítva, $|\rho_{\text{true}}| < 0.10$ |
| Statisztikai erő küszöb ($n=378$) | $|\rho_{\min}|=0.144$ | A megfigyelt $\rho$ alulvizsgált |
| Kelly criterion $f^*$ | $-0.23$ (konzervatív), $-0.46$ (default) | **Negatív expectancy** |
| Sharpe ratio (annualizált) | $\approx -38.8$ | Extrém negatív |
| Éves súrlódás-teher | ~19-21% | Top decile hedge fund küszöb |
| Bonferroni-szignifikáns al-komponensek | 2/7 (PCR, OTM-inverse) | Maradék 5 = noise |
| BMI regime | YELLOW 100% | Degenerált a vizsgált mintán |
| $M_{\text{VIX}}$ | 1.0 100% | Degenerált |
| $M_{\text{GEX}}$ undetermined | 75% | Degenerált |
| LOSS_EXIT bracket bug frequency | $\sim 3.3\%$ (60 napi) | Strukturális, magasabb-vol regime-ben 5-10% |
| 60-trade dark pool $\rho$ | $-0.265$, $p=0.041$ | Marginális szig., 95% CI $[-0.486, -0.012]$, **alulvizsgált** |
| M_contradiction LIVE 7 nap | 2/6 ✓ (33%) | Rosszabb mint random |
| 4 bracket SL bug instancia | 13 nap (DTE, SQM, FORM, AAPL) | Strukturális, NEM patchelhető |

### 8.3 Hivatkozott forrás-docok

- `docs/strategic-review/2026-05-08-strategic-review-summary.md` (5 oldal, portfolio menedzser)
- `docs/strategic-review/2026-05-08-strategic-review-full.md` (25 oldal, részletes elemzés)
- `docs/strategic-review/2026-05-08-strategic-review-mathematical.md` (~30 oldal, formális keret) — **az aktuális Day 63 doc fő hivatkozási alapja**
- `docs/master-reference/01-system-snapshot.md` (élő dashboard — paraméterek)
- `docs/master-reference/04-risks-and-open-questions.md` (élő dashboard — 15 backlog idea)
- `docs/review/2026-05-08-daily-review.md` → `2026-05-13-daily-review.md` (8 napi friss adat)
- `docs/decisions/2026-04-28-day63-decision-framework.md` (eredeti Day 63 keret)
- `docs/analysis/scoring-validation.md` (378-trade audit)
- `docs/analysis/flow-decomposition.md` (232-trade Bonferroni elemzés)

### 8.4 A 14 stratégiai döntés egyetlen táblázatban

| # | Téma | Döntés | Indoklás (egy mondat) |
|---|---|---|---|
| 1 | Day vs Swing | SWING (3-5 nap) | Mathematical doc 5.2: mutual information 5× erősebb $h=5$-nél |
| 2 | UW API | Shadow log Day 90-ig | \$300 megfizethető opcionalitási érték, $n=150-180$ érdemleges power |
| 3 | Backlog 15 idea | KEEP 6 / REWORK 4 / DROP 5 | A swing pivot strukturálisan eliminálja a bracket-relatált backlog-eket |
| 4 | Strategic-review #5 | 3 elvégzendő, 2 elvetendő | Dinamikus pozíciószám MUST DO, többi automatikus a scoring revízióval |
| 5 | Reset roadmap | 3 fázisú, W21-W30 | 2 hét cleanup + 2 hét analytic + 6 hét deploy + új 63 napi paper |
| 6 | Entry/exit timing | 15:30 entry, 3-5 nap, mental stop | A swing pivot közvetlen következménye, bracket bug strukturális megszüntetése |
| 7 | Pozíció-méretezés | Rolling 10-12, 0.35% risk | Same gross exposure, 1/5 per-position risk, alacsonyabb VaR |
| 8 | Time-stop | 5 trading nap MOC | Mathematical doc 5.2 optimum, weekly rhythm |
| 9 | Universum | S&P 500 + Russell 1000 | Likvid mid+large-cap, swing-friendly, low slippage |
| 10 | Earnings exclusion | 10 nap | Hold × 2 buffer, gap-protection |
| 11 | Sector cap | 30% notional | Dollar-koncentráció, intézményi sztenderd |
| 12 | Stop-loss típus | Mental stop, daily eval | Bracket bug strukturális megszüntetése |
| 13 | Scoring revízió | PCR + OTM-inverse only | Bonferroni-szignifikáns minimum, 70% pipeline egyszerűsödés |
| 14 | Új élesítés | Day 126: +\\$2k + Sharpe>0.5 + 25 pos excess | Realisztikus + statisztikailag érdemleges + karakter-konzisztens |

---

**A dokumentum vége.**

A Day 63 milestone formálisan **PAPER FOLYTATÁS (default)** kimenettel zárul. **De a "folytatás" radikálisan más architektúrán** — nem inkremeális finomítás, hanem **3 fázisú reset és új scoring/risk/sizing rendszer**.

A 14 stratégiai döntés alapján a következő **8-10 hét munkafolyamatban** **felépül** az új architektúra, és **kb. 2026-09-15 (W37)** lesz az **Új Day 63 milestone** — az **élő pénzes kereskedés első valós döntési pontja**.

**A graceful exit nem kudarc**, hanem strukturált tanulság-rögzítés. A 63 napi paper trading **konkrét kvantitatív megfigyeléseket** szolgáltatott, amelyek az új iteráció **fundamentumát képezik**.
