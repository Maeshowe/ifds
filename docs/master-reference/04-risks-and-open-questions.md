# 04 — Aktív kockázatok és nyitott kérdések

**Utoljára frissítve**: 2026-05-14 (Day 63 outcome + Swing pivot bejelentés)
**Cél**: a swing pivot W21+ aktív backlog tételeit és a strukturális finding-okat tartalmazza, prioritás-sorrendben. **Ezt használd, ha gyorsan akarsz tudni mi a legfontosabb most**.

> **Korszakváltás (2026-05-14)**: a Day 63 milestone outcome alapján a régi 15-elemű backlog **drasztikusan átalakult**: **6 dropolva** (a swing pivot strukturálisan eliminálja), **4 átalakítva**, **6 új aktív**. A swing pivot 3 fázisú reset roadmap a `docs/decisions/2026-05-14-day63-decision-outcome.md` 6. fejezetében.

---

## 1. P1 — Sürgős, Fázis 1 (W21-W22) deploy

### 1.1 IBKR Gateway monitoring + Telegram alert ⭐ OPERATIONAL RISK

**Mi**: 2026-05-11 16:20 CEST — az IBKR Gateway elérhetetlen volt (timeout × 3 retry), a `submit_orders.py` failelt. Tamás 55 perccel később (17:15 CEST) vette észre, kézi rögzítés.

**Miért P1**:
- A jelenlegi rendszer **nem riasztja Tamást**, ha az IBKR Gateway leáll a 16:20-i submit-időpontban.
- Egy másik IBKR-akadás esetén a rendszer **csendben hibázhat** — Tamás csak EOD-időpontban (22:00 körül) látja.
- **Swing-architektúrán is releváns**: a 15:30 CEST entry-időnél is ugyanaz a kockázat.

**Megoldás**: a `submit_orders.py`-be IBKR connection failure detection + Telegram bot értesítés (meglévő Telegram bot infrastruktúra).

**Effort**: ~1 óra CC + 2-3 unit teszt

**Owner**: CC (W21+ azonnali deploy)

**Forrás**: [`docs/review/2026-05-11-daily-review.md`](../review/2026-05-11-daily-review.md)

### 1.2 10-Q SEC Filing Exclusion + 10 napi earnings exclusion bővítés ⭐ SWING-EN KRITIKUSABB

**Mi**: AGNC 2026-05-04 — 10-Q SEC filing event 17:21 CEST, **NEM** earnings release, így a 7 napos earnings exclusion nem zárta ki. Eredmény: -$380 6-split LOSS_EXIT.

**Miért P1 a swing-en (REWORKED)**:
- A 7 napos earnings exclusion már **nem elégséges** swing horizonton (5 napi hold)
- **Új keret**: 10 napi earnings exclusion (hold × 2 buffer) + 10-Q SEC filing exclusion
- A jelenlegi earnings-szűrő nem fedi le a 10-Q / 10-K SEC filing event-eket

**Megoldás**:
1. `defaults.py`: `earnings_exclusion_days: 7 → 10`
2. SEC EDGAR API integráció — 10-Q és 10-K filing dátumok lekérdezése
3. Phase 2 universe-ből kizárás 10 napi előretekintéssel

**Effort**: ~2-3 óra CC

**Owner**: CC (W21+ azonnali deploy)

---

## 2. P2 — Fázis 2 analitikus + design (W23-W24)

### 2.1 Entry timing optimalizáció backtest ⭐ A SWING PIVOT KVANTITATÍV MEGALAPOZÁSA

**Mi**: A jelenlegi 16:20 CEST entry-idő strukturálisan a reggeli rally peak-jére esik. A swing pivot 15:30 CEST entry-t javasol (market open). **Kvantitatív validáció szükséges**.

**Megoldás (analitikus, NEM kód deploy)**:

Backtest a 60+ napi adaton 4 hipotetikus entry-időablakkal:
- 15:30 CEST (market open = 09:30 ET) — **az új javasolt**
- 16:20 CEST (jelenlegi = 10:20 ET)
- 17:15 CEST (= 11:15 ET, reggeli profit-taking utáni)
- 18:30 CEST (= 12:30 ET, lunchtime drift)

Minden ticker × minden hipotetikus entry-időpontra:
1. Visszaszámolni a hipotetikus entry-árat (Polygon 1-min bars)
2. Újrakalkulálni a P&L-t (a tényleges exit-tel)
3. Aggregátum analízis: melyik időablak ad a legjobb total P&L-t, a legkisebb LOSS_EXIT triggerelést, a legjobb excess vs SPY-t

**Várt eredmény**: az 15:30 entry előnyét kvantitatívan validálja, vagy más optimumot talál.

**Effort**: ~1-2 óra Chat-oldali

**Owner**: Chat (Fázis 2, W23)

**Forrás**: [`docs/review/2026-05-12-daily-review.md`](../review/2026-05-12-daily-review.md) — "ENTRY TIMING HIPOTÉZIS" + Tamás javaslata

### 2.2 M_contradiction sign-flip vizsgálat

**Mi**: 7 napos M_contradiction LIVE iránybeli helyesség: **33%** (2 ✓ + 4 ✗ a 6 fired esetből). **Rosszabb mint random**. A "double jeopardy" minta (FORM máj 11, CENX máj 12) megerősíti.

**Hipotézis**: a sign-flip ($M_c = 1.2 \times$ a $0.8 \times$ helyett) lehet, hogy pozitív expectancy-t ad. **Kvantitatív backtest szükséges**.

**Megoldás (analitikus)**:
- A 60+ napi adat összes M_contradiction fired esetére: ha sign-flippelt ($M_c \to 1.2$), mennyi lett volna a P&L?
- Bayes-faktor a sign-flip vs deaktiválás vs status quo között
- Döntés: (A) sign-flip, (B) deaktiválás ($M_c = 1.0$), (C) Status quo (status: alulvizsgált)

**Effort**: ~1 óra Chat-oldali

**Owner**: Chat (Fázis 2, W23)

### 2.3 TP1 cél revízió (új swing TP-struktúra)

**Mi**: A régi `tp1_atr_multiple: 1.25` swing horizonton **újrakalibrálandó**. A swing pivot új struktúrája:
- **TP1**: +1.5× ATR (~+4-5%) → 50% qty zárás, trail SL felfelé
- **TP2**: +3.0× ATR (~+8-10%) → maradék 50% zárás
- **SL (mental)**: -2.0× ATR (~-5-6%) — overnight gap buffer

**Megoldás**: `defaults.py` config update + scoring-független TP/SL logika a swing architektúra design dokban.

**Effort**: ~30 min config + ~1 óra CC unit teszt

**Owner**: CC (Fázis 2 design → Fázis 3 deploy)

### 2.4 Dinamikus pozíciószám — rolling 10-12, 0.35% risk

**Mi**: A 2026-04-11-i 13 pontos terv #7 javaslata — **dinamikus pozíciószám**. A swing pivot keretében az új paraméterek:
- Risk per position: **0.35%** ($350)
- Concurrent positions cap: **12 (steady state ~10)**
- Daily new entries: **2-3** (NEM kötelező napi 3-5)

Ha nincs minőségi flow signal egy adott napon, **NEM kereskedünk**. A "csak ha érdemes" filozófia.

**Indoklás**: a swing-en a 10-12 concurrent miatt a jelenlegi 5 fix napi entry **túl agresszív**.

**Megoldás**: `defaults.py` config + Phase 6 sizing logika átalakítás.

**Effort**: ~1 óra CC

**Owner**: CC (Fázis 3 deploy)

---

## 3. P3 — Fázis 3 vagy később

### 3.1 ADR earnings adatforrás fix

**Mi**: BUD 2026-05-05 — ADR earnings event, az FMP `/stable/earnings?symbol=BUD` **NEM tartalmazta** a 2026-05-05 dátumot. **5-10 hasonló eset** mehetett le észrevétlenül a 60 napi adatban.

**Megoldás (kombinált)**:
- (A) Polygon `tickers/{ticker}/events` — jobban lefedi ADR-eket
- (D) Hard-coded ADR blacklist konfig — top 50-100 ADR earnings dátum manuális tracking

**Effort**: ~3-4 óra CC

**Owner**: CC (Fázis 3, W25-W26 között)

### 3.2 Breakeven Lock profit-küszöb (swing-integrált)

**Mi**: A régi "Breakeven Lock" mechanizmus profit-trigger ~+1% felett aktivál. A swing TP/exit struktúrában a profit-küszöb integrálandó.

**Megoldás**: a swing exit logika design fázisban (Fázis 2) eldől.

**Effort**: ~30 min config (a design után)

**Owner**: CC (Fázis 3 deploy)

### 3.3 Phase 4 snapshot enrichment

**Mi**: A jelenlegi `state/phase4_snapshots/` csak a winner ticker-eket menti. A teljes ticker tábla mentése javasolt a Bonferroni-szignifikáns flow al-komponensek (PCR, OTM-inverse) longitudinális elemzéséhez.

**Megoldás**: Phase 4 snapshot logika módosítás — minden ~250-300 ticker mentése scoring táblával.

**Effort**: ~30-45 min CC + 3-4 unit teszt

**Owner**: CC (Fázis 3 deploy, az új scoring-gal párhuzamosan)

---

## 4. DROPPED — a swing pivot által strukturálisan eliminált backlog

A korábbi 15 backlog idea közül **8 dropolt**:

| # | Eredeti backlog | Drop indoklás |
|---|---|---|
| 1 | **LOSS_EXIT bracket SL cancellation** (4 instancia bug) | Mental stop architektúra strukturálisan eliminálja a bracket-rendszert |
| 2 | `nuke.py --orders` scope expansion | NINCS bracket order swing-en, `--positions` elég |
| 3 | UW rate limit kezelés finomítás | UW shadow log, scoring-ban deaktiválva (Day 90 audit) |
| 4 | LOSS_EXIT küszöb finomítás per-ticker ATR | Mental stop architektúra |
| 5 | dp_pct fallback default (universum-medián) | UW scoring-ban deaktiválva |
| 6 | Slippage-adjusted scoring validation | Új scoring eleve slippage-szembesített |
| 7 | High-score liquidity check | A "magas pontszám paradoxon" a scoring revízión át kezelendő (Bonferroni-minimum) |
| 8 | monitor.py belső replay események jelölése | Alacsony prioritás, későbbi |

**Plus a 2026-04-11 13 pontos terv**:
- `#10 Call wall T1 kikapcsolás` → **automatikusan megtörténik** (scoring egyszerűsítés kiveszi M_GEX-et)
- `#11 VWAP guard egyszerűsítés` → **automatikusan megtörténik** (új entry 15:30 market open, NEM AVWAP-alapú)
- `#12 Multiplier chain egyszerűsítés` → **a scoring revízió felülírja** (csak M_target marad)
- `#13 Flow al-komponens dekompozíció` → **MÁR ELVÉGEZTE** a 232-trade audit

---

## 5. Strukturális finding-ok (Day 63 alapján)

### 5.1 A "magas pontszám paradoxon" — kvantitatívan megerősített

**60 napi adat (n=378)**: Pearson $\rho(S, R) = -0.000$ (p=0.996). A 95% CI a true effekten: $[-0.10, +0.10]$. **Strong evidence** a "small effect" tartományra.

**Quintile minta**:
- Q1 (alsó 75): -$129 / -$1.72 átlag
- Q2 (közepes 76): **+$880 / +$11.57** ⭐
- Q3 (közép 75): **-$1,341 / -$17.88** ⚠️
- Q4 (felső 76): +$76 / +$1.01
- Q5 (legfelső 76): -$677 / -$8.91

**Stratégiai következmény**: a swing pivot **PCR + OTM-inverse only scoring** (Bonferroni-szignifikáns minimum) **strukturálisan kezelhetővé** teszi a paradoxont. A tech és funda sub-score (kvázi-zaj) **kikerül**.

### 5.2 Az időtáv-paradoxon — mathematical doc 5.2 mutual information

A flow signal **$h$-step mutual information** modellje: $I \propto h \cdot \rho^2$.

Ha a 1-step $\rho = 0.14$ (Bonferroni-szignifikáns PCR korreláció), akkor:
- $h=1$: $I \approx 0.020$
- $h=3$: $I \approx 0.059$
- **$h=5$: $I \approx 0.098$** ← **5× erősebb signal**
- $h=7$: $I \approx 0.137$ (de overnight gap risk-aggregáció)

**Optimum**: $h \in \{3, 5\}$ nap. A swing pivot **5 napi time-stop**-pal ezt operacionalizálja.

### 5.3 Negatív Kelly criterion — matematikai konkluzió

**Konzervatív (csak determinisztikus exit-ek)**: $f^* = 0.50 \cdot 50/92.56 - 0.50 = -0.23$
**Default (összes exit)**: $f^* = 0.466 \cdot 15.07/92.56 - 0.534 = -0.458$

**Mindkettő negatív** — a rendszer **negatív expectancy-jű**. Csak a swing pivot 5×-szöröse signal-erősítés (mathematical doc 5.2) tudja **pozitív irányba mozdítani**.

### 5.4 Operacionális kockázatok — 4 strukturális instancia 13 napon belül

| Dátum | Ticker | Bug típus | Kár |
|---|---|---|---|
| 2026-05-01 | DTE | LOSS_EXIT + bracket SL ugyanazon napon | -$988 (paper) |
| 2026-05-07 | SQM | LOSS_EXIT + bracket SL ugyanazon napon | -$425 (valós) |
| 2026-05-12 | FORM | MOC fill + bracket másnap aktivált | ~-$200 (valós) |
| 2026-05-12 | AAPL | MOC fill + bracket másnap aktivált | ~-$150 (valós) |

**Strukturális, NEM patchelhető** — a swing pivot **mental stop architektúra eliminálja a bracket-rendszert**.

### 5.5 Makró-rezsim degeneráltság

A 60 napi mintán:
- BMI = YELLOW 100% (sosem GREEN, sosem RED)
- $M_{\text{VIX}} = 1.0$ 100% (VIX mindig < 20)
- $M_{\text{GEX}}$ undetermined: 75%

**A multiplier chain effektíven csak $M_{\text{target}}$-en és $M_{\text{contradiction}}$-on különböztet meg tickereket**. Ez **inkonzisztens differenciálás**. A swing pivot **csak $M_{\text{target}}$-et tartja meg** (M_contradiction sign-flip vizsgálat után dönt).

---

## 6. Nyitott kérdések (strukturális hipotézisek, NINCS aktív task)

### 6.1 Information ratio mérése a tilt-kalibrációhoz

A Bayes-update Day 90-en (UW shadow log audit, $n \approx 150-180$): ha a true $\rho_{\text{dp}}$ a $[-0.20, +0.20]$ tartományon kívülre esik, az UW visszahozható a scoring-ba. A 95% CI mérése **érdemleges power**-rel.

### 6.2 Linkage method érzékenység (jövő iterációhoz)

Ha a swing pivot Day 126-on sikeres, a következő iteráció (Q4 2026) **HRP/HERC allokáció**-t vizsgálhat. A linkage method (ward / complete / average) érzékenységét **15 tickerrel** kell tesztelni — a `docs/planning/bc22-hrp-allocation-design.md`-ben részletezve.

### 6.3 Cross-Asset Regime integráció a swing-en

A jelenlegi Cross-Asset Regime (HYG, IEF, RSP, SPY, IWM 20 napi momentum) **RISK_OFF / CRISIS** állapotokra csökkenti a max pozíciószámot. **Swing-en**: a 12 concurrent cap az új keret, de **CRISIS-ben 6-ra csökkentés** természetes. Implementáció a Fázis 3-ban.

### 6.4 MID Bundle integráció

A MID — Macro Intelligence Dashboard napi shadow snapshot-okat produkál. A swing pivot kontextusában **portfolio context layer** lehet — pl. Stagflation regime-ben a pozíciómért kisebb, vagy a sector-rotation szabályok defenzívebb sektor-súlyokat alkalmaznak. **BC25 W26+ scope**, Fázis 3 után.

---

## 7. Mit NEM csinálunk (és miért)

| Korábbi terv | Akció | Indoklás |
|---|---|---|
| **A+C kombinációs roadmap** (strategic-review 7.5) | **MÓDOSÍTVA** | 6 nap új adat → csak B (swing pivot) |
| Inkremeális finomítás a régi rendszerre | **NEM** | Strukturális bug-források nem patchelhetők |
| BC24 Institutional Flow Intelligence | **PARKOLT** | Új scoring (PCR + OTM-inverse only) felülírja |
| BC25 IFDS Phase 3 ← MID CAS | **PARKOLT Day 126-ig** | Új paper trading után döntés |
| Élő pénzes kereskedés Day 90-en | **NEM** | Új Day 126 milestone (kb. 2026-09-15) az első valós döntés |
| Komplex statisztikai modellek (random forest, neural net) | **NEM** | Kis n probléma (Bonferroni-minimum a tisztább alap) |

---

**A frissítésért felel**: Chat (Claude) — eseményalapú (új finding, új debug eredmény, új P1/P2/P3 task után). A Fázis 1-2 alatt heti konzisztencia-check.
