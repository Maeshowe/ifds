# 03 — Day 63 milestone OUTCOME + Új Day 126 keret

**Utoljára frissítve**: 2026-05-14 (Day 63 OUTCOME rögzítve, korszakváltás)
**Aktuális állapot**: **Day 63 LEZÁRVA, paper folytatás default kimenettel — DE új swing architektúrán**

---

## 1. Day 63 milestone — formális kimenet (2026-05-14)

A 2026-04-28-i Day 63 decision framework (`docs/decisions/2026-04-28-day63-decision-framework.md`) 3 kimenetét formálisan kiértékeltük 2026-05-14-én:

| Kimenet | Feltétel | Tényleges érték | Eredmény |
|---|---|---|---|
| **ÉLESÍTÉS** | +$3,000 ÉS +1.5% kumulatív excess vs SPY ÉS 20+ napi nem-Stagflation | kumulatív -$1,623, távolság **-$4,623** | **NEM teljesült** |
| **LEÁLLÍTÁS** | 10 napi excess átlag < -1.5% VAGY VIX > 25 30+ napra | 10 napi átlag **-0.35%** (buffer ~1.15%); VIX W20 átlag 18.1 | **NEM aktivált** |
| **PAPER FOLYTATÁS** (default) | Egyik fenti sem | ✅ | **Aktivált** |

**De a "folytatás" RADIKÁLISAN MÁS ARCHITEKTÚRÁN** — nem inkremeális finomítás. Részletes érvelés: `docs/decisions/2026-05-14-day63-decision-outcome.md`.

---

## 2. 63 napi végeredmények — kvantitatív összefoglaló

| Mutató | Érték | Statisztikai értelmezés |
|---|---|---|
| Trading days | 63 (2026-03-13 → 2026-05-13) | |
| Ügyletek száma | ~410 | átlag 6.5/nap |
| Kumulatív paper P&L | **-$1,623.78** | papír aggregát |
| Kumulatív % (paper) | **-1.62%** | |
| Tényleges valós (bug-korrekciókkal) | **~-$1,400 to -$1,500** | -1.40 to -1.50% |
| Win rate | ~45-47% | véletlentől nem különbözik |
| **Pearson r (kompozit S vs R)** | **-0.000 (p=0.996)** | $H_0$ NEM elutasítva, $|\rho_{\text{true}}| < 0.10$ |
| **Kelly criterion $f^*$** | **-0.23 (konzervatív) / -0.46 (default)** | **Negatív expectancy** |
| **Sharpe ratio (annualized)** | **~-38.8** | Extrém negatív |
| **Éves súrlódás-teher** | **~19-21%** | Top decile hedge fund teljesítmény-szint |
| Bonferroni-szignifikáns flow al-komponensek | 2/7 (PCR, OTM-inverse) | 5 = noise |
| BMI regime | YELLOW 100% | Degenerált a vizsgált mintán |

**Verdikt** (intézményi szinten): a jelenlegi rendszer aktuális formájában **NEM élesíthető**. **De az építőelemek érdemleges fundament** egy újabb iterációhoz.

---

## 3. A Day 63 keret elavultsága

A 2026-04-28-i keret **strukturálisan irreális**: az ÉLESÍTÉS küszöb (+30% annualizált) **a 19-21%-os éves súrlódás-teher fölött** olyan szintet követelne, amit **csak top decile hedge fund-ok** érnek el. A LEÁLLÍTÁS küszöb működik (jól kalibrált, a default nem-katastrofális visszatartást ad).

**A keret revíziója szükséges** — az új keret a 4. fejezetben (Day 126 milestone).

---

## 4. ÚJ Day 126 milestone (kb. 2026-09-15, W37)

### 4.1 Definíció

**Day 126** = az új paper trading 63 napja után. Az új rendszer Day 1-je: kb. **2026-06-23 (W26 hétfő)** — az IBKR paper account reset és az új scoring + risk + sizing deploy után. **Day 126 naptári dátum (becsült)**: 2026-09-15 ± 1 hét, a Fázis 3 indulásától függően.

### 4.2 ÉLESÍTÉS kritériumai (3 feltétel EGYIDEJŰLEG)

| # | Kritérium | Küszöb | Indoklás |
|---|---|---|---|
| 1 | Kumulatív paper P&L | > **+$2,000** | ~+8% annualizált, +$100k tőkén realisztikus |
| 2 | Sharpe ratio (annualized) | > **0.5** | Top quartile alatt, de statisztikailag érdemleges |
| 3 | Pozitív excess vs SPY napok | > **25 / 63** (40%) | Karakter-konzisztencia tesztje |

### 4.3 LEÁLLÍTÁS kritériumai (bármelyik trigger)

- 10 napi excess vs SPY átlag < **-1.0%** (szigorúbb mint a régi -1.5%)
- VAGY 30 napi kumulatív < **-3.0%** (catastrophic drawdown)
- VAGY 15 napi excess < **-1.0%** (gyors leállítás)

**Aktiválódás esetén**: 24 órás cooldown + graceful exit. Új strategic-review készül, esetleg **teljes projekt leállítás** mint utolsó opció.

### 4.4 DEFAULT — PAPER FOLYTATÁS

Ha sem ÉLESÍTÉS, sem LEÁLLÍTÁS nem aktivál: paper trading folytatódik **Day 180 (kb. 2026-11-15) újraértékelésig**.

### 4.5 Élesítés esetén — élő pénzes trading

**$10,000 tőkével** induló élő trading.

**Védelmek**:
- **3% drawdown circuit breaker** automatikus leállítással
- **Napi notional limit**: max $25k single position, $200k total daily turnover
- **Pre-submit Telegram notification** minden order előtt 5 perc cooldown-nal
- **Weekly review** (kötelező manuális Tamás-átfutás, nincs hands-off)
- **Account-szintű VaR limit**: 4% (a 0.35% × 12 = 4.2% theoretical max alapján)

**Allokáció scaling**: ha az élő $10k tőke 30 napra pozitív (>+$300 net), akkor **opcionálisan $25k-ra emelhető**. **Soha NEM** automatikus — Tamás manuális döntése.

---

## 5. 3 fázisú Reset Roadmap (W21-W30)

A Day 63 outcome alapján 8-10 hetes átalakítás:

### Fázis 1 (W21-W22, máj 19 - máj 30) — OPERATIONAL CLEANUP

**Tamás (manuális)**:
- Máj 19: `nuke.py --positions` cleanup, IBKR bracket order cancel
- Máj 20-22: **IBKR paper account reset** ($100k újra)

**CC (implementáció, ~5h)**:
- Máj 19-22: IBKR Gateway monitoring + Telegram alert
- Máj 23-25: 10-Q SEC Filing Exclusion + 10 napi earnings exclusion
- Máj 26-30: UW config — scoring deaktiválás, shadow log infra

**Chat (dokumentáció)**:
- Master-reference frissítés ✅ (2026-05-14)
- Strategic-review $354→$665 korrekció ✅ (2026-05-14)
- Új architektúra design doc skeleton

### Fázis 2 (W23-W24, jún 2 - jún 13) — ANALYTIC + DESIGN

**Chat (analitikus, ~5h)**:
- Entry timing backtest (4 alternatív időablak a 60+ napi adaton)
- M_contradiction sign-flip elemzés (n=6 fired esetből 4 nyertes)
- Új scoring design (`docs/design/swing-scoring-spec.md`)
- Új risk management spec (mental stop, time-stop, hard SL)
- Új position sizing spec (rolling 10-12, 0.35% risk)

**CC (prototípusok, ~3-5h)**: unit-test szintű prototípusok, NEM deploy.

**Tamás**: design review

### Fázis 3 (W25-W30, jún 16 - júl 25) — RE-DEPLOY + ÚJ PAPER TRADING

**CC (implementáció, ~15-20h)**:
- W25: új scoring + universum deploy
- W26 első napjai: új risk management + position sizing deploy
- Integration tests, smoke tests

**Tamás**: **kb. jún 23 (W26 hétfő)** — IBKR paper account reset, **új paper trading INDUL Day 1-en**

**Chat**: napi review-k + heti elemzések

---

## 6. A swing pivot 14 fő paramétere (összefoglaló)

| Paraméter | Régi (BC23) | Új (Swing pivot) | Indoklás |
|---|---|---|---|
| Hold időtáv | 6 óra intraday | **3-5 trading nap** | Mathematical doc 5.2 mutual information optimum |
| Entry idő | 16:20 CEST | **15:30 CEST market open** | Flow signal aggregation után, NEM peak-rally |
| Risk per position | 0.7% ($700) | **0.35% ($350)** | Same gross exposure, alacsonyabb VaR |
| Stop multiplier | 1.5× ATR | **2.0× ATR** | Overnight gap buffer |
| Concurrent positions max | 5 | **12 (steady state ~10)** | Több diverzifikáció |
| Daily new entries | 5 (fix) | **2-3 (dinamikus)** | Csak ha érdemes |
| Total portfolio VaR | 10-15% spike | **4-6% steady** | |
| Universum | 1390 ticker | **S&P 500 + Russell 1000 (~1000)** | Likvid mid+large-cap |
| Earnings exclusion | 7 nap | **10 nap** | Hold × 2 |
| Sector cap | 2 ticker/sector hard | **30% notional/sector** | Intézményi sztenderd |
| Stop-loss típus | IBKR bracket SL + LOSS_EXIT -2% | **Mental stop, daily eval** | Bracket bug strukturális megszüntetése |
| TP struktúra | TP1 1.25×ATR, TP2 2.0×ATR | **TP1 1.5×ATR (50%), TP2 3.0×ATR** | Új scaling |
| Scoring | 7-komp flow + 3-komp tech + 6-komp funda | **PCR + OTM-inverse only** | Bonferroni-szignifikáns minimum |
| Multiplier chain | 4 aktív (M_VIX, M_GEX, M_target, M_contradiction) | **1 aktív (M_target)** | 3 degenerált / sign-flip-elhetetlen |

**Pipeline ~70%-kal egyszerűbb lesz.**

---

## 7. Strukturális megfigyelések — W17-W19+W20 (a Day 63 előtti utolsó hetek)

### 7.1 A "magas pontszám paradoxon" megerősítése

4 egymás utáni nap (W19 D1-D4) a legmagasabb pontszámú ticker a leggyengébb performer. Ez **statisztikailag jelentős minta** és megerősíti a 60 napi Pearson r ≈ 0 finding-ot.

### 7.2 Bull rally underperform pattern

3-4 dokumentált bull napi excess átlag **-0.78%** (W19 D3 +1.39% SPY, excess -1.14%; W20 D3 +0.56% SPY, excess -0.74%). **A long-only intraday struktúra defenzív erő risk-off / lateral napokon, kompromittált bull rally napokon.**

### 7.3 LOSS_EXIT bracket SL duplikált zárás — 4 instancia 13 napon belül

| Dátum | Ticker | Kár | Hatás |
|---|---|---|---|
| 2026-05-01 | DTE | -$988 (paper) | Első instancia |
| 2026-05-07 | SQM | -$425 (valós) | Második instancia |
| 2026-05-12 | FORM | ~-$200 (valós) | **ÚJ MINTA**: MOC fill után másnap aktivált |
| 2026-05-12 | AAPL | ~-$150 (valós) | Negyedik instancia |

**Strukturális, NEM patchelhető** — a swing pivot mental stop architektúra **strukturálisan eliminálja**.

### 7.4 M_contradiction × M-szorzó "double jeopardy"

| Dátum | Ticker | Double penalty | Eredmény |
|---|---|---|---|
| 2026-05-11 | FORM | M_c (0.8) × M_target (0.85) = 0.68 | Nap legjobb nyerője (+$214) |
| 2026-05-12 | CENX | M_c (0.8) × M_gex_high_vol (0.6) = 0.48 | Nap legjobb nyerője (+$172) |

**7 napos M_contradiction LIVE iránybeli helyesség**: **33%** (2 ✓ + 4 ✗ a 6 fired esetből) — **rosszabb mint random**. Sign-flip vizsgálat a Fázis 2-ben.

---

## 8. A Day 63 kiértékelés komparációja a 2026-05-08 strategic-review-val

A 2026-05-08-i strategic-review-summary **A + C kombináció + B párhuzamos R&D** útvonalat javasolt, Day 90 értékeléssel. **6 nap eltelt azóta**, és **5 új kvantitatív adatpont** megváltoztatta a képet:

| Adatpont | Új információ | Implikáció |
|---|---|---|
| Snapshot fix DEPLOYED | A scoring-validation újrafuttatható | 60 napi r=0 finding stabil |
| 4 LOSS_EXIT bracket SL bug instancia | 13 napon belül, eltolással is | Strukturális, NEM patchelhető |
| FORM + CENX dupla M-szankció | Multi-feature kölcsönhatás | M_contradiction sign-flip valószínűbb |
| UW HTTP 429 50→170+ ticker | Per-ticker fetch infrastrukturálisan instabil | UW production-ban nem használható |
| PAAS Breakeven Lock pozitív validáció | A feature alaplogikája rendben | Megtartandó az új architektúrán |

**Az A+C+B(R&D) javaslat helyett ma az indokolt választás: a B opció FÁZIS 2 azonnali indítása** (multi-day swing pivot), inkremeális finomítások nélkül. A 6 nap új adat ezt egyértelműen alátámasztja.

---

## 9. Heti mérőszámok a 63 napi időszakban (összefoglaló)

| Hét | Időszak | Net P&L | Excess vs SPY (átlag) | Kulcs esemény |
|-----|---------|---------|-----------------------|----------------|
| W11-15 | márc 13 – ápr 10 | -$1,661 | -2.1%/nap | BC23 pre-deploy |
| W16 | ápr 13-17 | +$1,661 | -2.73%/nap | BC23 deploy első hét |
| W17 | ápr 20-24 | +$593 | **+0.13%/nap** ⭐ | Legjobb hét |
| W18 | ápr 27 – máj 1 | -$1,106 | -1.90%/nap | DTE bracket bug első instancia |
| W19 | máj 4-8 | -$241 (4 nap) | -0.54%/nap | SQM bracket bug, QCOM TP2 |
| W20 | máj 11-13 (3 nap) | -$530 | -0.38%/nap | FORM+AAPL bug, snapshot fix DEPLOYED |

**A heti heterogenitás nagy** — W17 vs W18 ~$1,700 swing. **Karakter**: defenzív erő risk-off / lateral napokon, kompromittált bull rally napokon.

---

## 10. Mit NEM csinálunk W21-től (és miért)

| Korábbi terv | Akció | Indoklás |
|---|---|---|
| BC24 Institutional Flow Intelligence | **PARKOLT** | Új scoring (PCR + OTM-inverse only) ezt felülírja |
| BC25 IFDS Phase 3 ← MID CAS | **PARKOLT Day 126-ig** | Új paper trading futás után döntés |
| Az A+C+B kombinációs roadmap | **MÓDOSÍTVA** | Csak B (swing pivot), 6 nap új adat alapján |
| Inkremeális finomítás a régi rendszerre | **NEM** | Strukturális bug-források nem patchelhetők |
| Élő pénzes kereskedés Day 90-en | **NEM** | Új Day 126 milestone az első valós döntés |

---

**A frissítésért felel**: Chat (Claude) — eseményalapú (új finding, új milestone). A következő nagy milestone: **Új Day 63 (kb. 2026-09-15, W37)** = Day 126 az eredeti naptáron.
