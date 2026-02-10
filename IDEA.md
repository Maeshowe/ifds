# Institutional Flow Decision Suite (IFDS)
## Üzleti és Funkcionális Specifikáció v2.0

**Dokumentum verzió:** 2.0  
**Státusz:** DRAFT  
**Dátum:** 2026-02-04  
**Készítette:** [Név]  
**Jóváhagyta:** [Csapat validáció szükséges]

---

## Dokumentum célja

Ez a specifikáció az Institutional Flow Decision Suite (IFDS) rendszer újratervezésének alapdokumentuma. A dokumentum célja:

1. **Üzleti logika rögzítése** – A kereskedési döntések matematikai és logikai alapjainak pontos leírása
2. **Változtatások definiálása** – A jelenlegi rendszer (MoneyFlows v13) és a célállapot közötti különbségek
3. **Fejlesztési alap** – Claude Code számára értelmezhető, végrehajtható specifikáció
4. **Csapat validáció** – Az üzleti logika ellenőrizhetősége nem-technikai stakeholderek által

---

## 1. Vezetői Összefoglaló (Executive Summary)

### 1.1 Rendszer definíció

Az **Institutional Flow Decision Suite (IFDS)** egy multi-faktoros kvantitatív kereskedési rendszer, amely a piac strukturális adatai alapján azonosít rövid távú kereskedési lehetőségeket az amerikai részvénypiacon.

### 1.2 Alapvető megközelítés

A rendszer szakít a hagyományos, késleltetett technikai indikátorokkal (RSI, MACD, Bollinger), helyette három strukturális tényezőt vizsgál:

| Faktor | Leírás | Adat típus |
|--------|--------|------------|
| **Intézményi tőkeáramlás** | Dark Pool likviditás, nagy volumenű tranzakciók | Volume Price Analysis |
| **Gamma Exposure (GEX)** | Market Makerek fedezeti kényszere | Opciós derivatívák |
| **Fundamentális minőség** | Vállalati pénzügyi egészség | Mérleg, eredménykimutatás |

### 1.3 Fő képesség

A rendszer naponta egyszer, piacnyitás előtt (6:30 ET) végigfuttatja a teljes amerikai részvényuniverzumot (~3000 ticker) egy szűrési csővezetéken ("funnel"), és kiválasztja a legmagasabb konfidenciájú kereskedési lehetőségeket (5-8 pozíció).

### 1.4 Változtatások motivációja (v13 → v2.0)

| Probléma | Jelenlegi állapot | Célállapot |
|----------|-------------------|------------|
| Átláthatóság | Nincs egységes eseménynapló | Strukturált, auditálható eseményfolyam |
| Monitoring | Logfájlok kézi elemzése | Valós idejű állapot dashboard |
| Konfiguráció | YAML-ök közötti rejtett függőségek | Validált, egyszerűsített paraméterek |
| Adatforrás | Polygon-ból számolt GEX/Dark Pool | Unusual Whales közvetlen adatok |

---

## 2. Rendszer Hatókör és Korlátozások

### 2.1 Hatókör (In Scope)

- Amerikai részvénypiac (NYSE, NASDAQ)
- Napi frekvenciájú szignálgenerálás (EOD)
- Long és Short stratégiák
- Semi-automatikus végrehajtás (IBKR API)

### 2.2 Kívül esik (Out of Scope)

- Intraday kereskedés (napon belüli)
- Forex, kriptovaluták, árupiaci termékek
- Fully automated trading (emberi jóváhagyás szükséges)
- Backtest motor (külön fejlesztés, Monte Carlo szimuláció)

### 2.3 Célközönség

- **Elsődleges:** A rendszer üzemeltetője (1 fő, technikai háttérrel)
- **Másodlagos:** Üzleti validátorok (2-3 fő, kereskedési háttérrel)

---

## 3. Adatforrások és Infrastruktúra

### 3.1 Külső adatszolgáltatók

A rendszer kizárólag auditálható, intézményi minőségű adatforrásokat használ. Web scraping tilos.

| Adat típus | Szolgáltató | Végpont | Frissítési frekvencia |
|------------|-------------|---------|----------------------|
| Price & Volume (OHLCV) | Polygon.io | `/v2/aggs/ticker/{ticker}/range` | Napi |
| Options Chain | Polygon.io | `/v3/snapshot/options/{underlyingAsset}` | Napi |
| Dark Pool Flow | Unusual Whales | `/api/darkpool/{ticker}` | Napi |
| Gamma Exposure | Unusual Whales | `/api/stock/{ticker}/greeks` | Napi |
| Fundamentals | FMP | `/stable/company-screener` | Napi |
| Earnings Calendar | FMP | `/stable/earning-calendar` | Napi |
| Insider Trading | FMP | `/v4/insider-trading` | Napi |
| Macro (VIX, Yields) | FRED | Több végpont | Napi |

### 3.2 Adatforrás prioritás

**Új architektúra (v2.0):** Ha az Unusual Whales közvetlen adatot szolgáltat (pl. GEX, Dark Pool), azt használjuk. Ha nem elérhető, fallback a Polygon-alapú számításra.

```
Unusual Whales (közvetlen) → Polygon (számított) → Hiányzó adat (skip ticker)
```

### 3.3 API Health Check követelmények

A rendszer futtatás előtt validálja az összes kritikus végpontot:

| Végpont | Timeout | Retry | Kritikus? |
|---------|---------|-------|-----------|
| Polygon Aggregates | 10s | 3× | Igen |
| Polygon Options | 15s | 3× | Igen |
| Unusual Whales | 10s | 3× | Nem (fallback van) |
| FMP Screener | 10s | 3× | Igen |
| FMP Earnings | 10s | 3× | Igen |
| FRED | 10s | 3× | Igen |

**Szabály:** Ha bármely "Kritikus" végpont nem elérhető 3 retry után, a rendszer leáll és alertet küld.

---

## 4. Pipeline Workflow (Fázisok)

A rendszer moduláris felépítésű, szekvenciális szűrési logikát ("Funnel") alkalmaz. Minden fázis szűkíti a jelöltek halmazát.

```
┌─────────────────────────────────────────────────────────────────────┐
│  INPUT: ~10,000 ticker (teljes US equity piac)                      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FÁZIS 0: Rendszer Diagnosztika                                     │
│  - API Health Check                                                 │
│  - Circuit Breaker státusz                                          │
│  - Macro Regime (VIX, Yield Curve)                                  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FÁZIS 1: Market Regime (BMI)                                       │
│  - LONG / SHORT stratégia kiválasztása                              │
│  OUTPUT: strategy_mode ∈ {LONG, SHORT}                              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FÁZIS 2: Universe Building                                         │
│  - Likviditási szűrés                                               │
│  - Zombie Hunter (earnings kizárás)                                 │
│  OUTPUT: ~3,000 ticker                                              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FÁZIS 3: Sector Rotation                                           │
│  - Momentum ranking (11 szektor ETF)                                │
│  - Sector BMI (túlvett/túladott szektorok)                          │
│  OUTPUT: sector_scores, sector_veto_list                            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FÁZIS 4: Individual Stock Analysis (párhuzamos)                    │
│  - Technical Analysis                                               │
│  - Flow Analysis (Dark Pool, RVOL)                                  │
│  - Fundamental Scoring                                              │
│  OUTPUT: ~200-300 jelölt (score ≥ 70)                               │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FÁZIS 5: GEX Analysis (Top 100)                                    │
│  - Gamma Exposure számítás                                          │
│  - Call Wall, Put Wall, Zero Gamma                                  │
│  OUTPUT: ~70-90 jelölt (NEGATIVE GEX kiszűrve)                      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FÁZIS 6: Risk Management & Sizing                                  │
│  - Dynamic position sizing                                          │
│  - Multiplier-ek alkalmazása                                        │
│  - Sector diversification                                           │
│  OUTPUT: 5-8 végleges pozíció                                       │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  OUTPUT: execution_plan.csv → IBKR                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. Fázis Specifikációk

### 5.0 Fázis 0: Rendszer Diagnosztika és Makro Környezet

**Cél:** Mielőtt bármilyen elemzés történne, a rendszer validálja az adatkapcsolatokat és felméri a piaci "időjárást".

#### 5.0.1 Circuit Breaker Check

A rendszer ellenőrzi, hogy aktív-e a Circuit Breaker (korábbi veszteség miatt).

**Szabály:**
```
HA global_guard.is_circuit_breaker_active = TRUE:
    → HALT! Telegram alert küldése
    → Manuális reset szükséges
```

**Circuit Breaker aktiválódik, ha:**
$$
DailyDrawdown > DrawdownLimit_{pct}
$$

Ahol:
- $DailyDrawdown = \frac{AccountEquity_{start} - AccountEquity_{current}}{AccountEquity_{start}} \times 100$
- $DrawdownLimit_{pct} = 3\%$ (konfigurálható)

#### 5.0.2 Macro Regime Filter (FRED API)

**VIX (Volatilitási Index):**

| VIX érték | Piaci állapot | Rendszer viselkedés |
|-----------|---------------|---------------------|
| VIX ≤ 15 | Low volatility | Normál működés |
| 15 < VIX ≤ 20 | Normal | Normál működés |
| 20 < VIX ≤ 30 | Elevated | Óvatos (VIX penalty aktív) |
| VIX > 30 | Panic Mode | Szigorúbb szűrés, félméret |

**VIX Penalty képlet:**
$$
VIX_{multiplier} = \max\left(0.25, 1.0 - (VIX - 20) \times 0.02\right) \quad \text{ha } VIX > 20
$$

**TNX (10-Year Treasury Yield) – Rate Sensitivity:**

$$
\text{Ha } TNX > SMA_{20}(TNX) \times 1.05 \text{, akkor a Technology szektor büntetést kap}
$$

A kamatérzékeny szektorok (Technology, Real Estate) alacsonyabb pontszámot kapnak emelkedő kamatkörnyezetben.

---

### 5.1 Fázis 1: Market Regime (Big Money Index)

**Cél:** Meghatározni, hogy a piac egésze LONG vagy SHORT stratégiát preferál.

#### 5.1.1 BMI definíció

A Big Money Index (BMI) egy szélesség-alapú (market breadth) indikátor, amely az intézményi tőkeáramlás irányát méri.

**Számítás lépései:**

1. **Big Money Signal detektálás** minden tickerre:

$$
BigMoneyBuy_i = 
\begin{cases} 
1 & \text{ha } Volume_i > \mu_{vol,20} + k \cdot \sigma_{vol,20} \text{ ÉS } Close_i > Open_i \\
0 & \text{különben}
\end{cases}
$$

$$
BigMoneySell_i = 
\begin{cases} 
1 & \text{ha } Volume_i > \mu_{vol,20} + k \cdot \sigma_{vol,20} \text{ ÉS } Close_i < Open_i \\
0 & \text{különben}
\end{cases}
$$

Ahol:
- $\mu_{vol,20}$ = 20 napos átlagos volumen
- $\sigma_{vol,20}$ = 20 napos volumen szórás
- $k = 2.0$ (volume spike sigma küszöb)

2. **Napi aggregálás:**

$$
B_t = \sum_{i=1}^{N} BigMoneyBuy_{i,t}
$$

$$
S_t = \sum_{i=1}^{N} BigMoneySell_{i,t}
$$

3. **Napi arány:**

$$
R_t = \frac{B_t}{B_t + S_t} \times 100
$$

4. **BMI (25 napos mozgóátlag):**

$$
BMI_t = SMA_{25}(R)
$$

#### 5.1.2 BMI Regime döntési tábla

| BMI érték | Regime | Stratégia | Értelmezés |
|-----------|--------|-----------|------------|
| BMI ≤ 25% | GREEN | LONG (Agresszív) | Túladott piac, vételi lehetőség |
| 25% < BMI < 80% | YELLOW | LONG (Normál) | Semleges piac |
| BMI ≥ 80% | RED | SHORT (Zombies) | Túlvett piac, short/védekezés |

#### 5.1.3 BMI Divergencia detektálás

**Bearish Divergence:**
$$
\text{Ha } SPY_{change,5d} > 1\% \text{ ÉS } BMI_{change,5d} < -2 \text{ pont}
$$

Jelentés: Az árfolyam emelkedik, de az intézményi támogatás csökken → gyengeség jele.

---

### 5.2 Fázis 2: Universe Building és Kockázatszűrés

**Cél:** A teljes amerikai részvénypiac (~10,000 ticker) szűkítése kereskedhető halmazra.

#### 5.2.1 LONG Universe szűrők (FMP Stable Screener)

| Paraméter | Feltétel | Indoklás |
|-----------|----------|----------|
| Market Cap | $> \$2,000,000,000$ | Mid-Cap+ (intézményi likviditás) |
| Price | $> \$5$ | Penny stock szűrés |
| Avg Daily Volume | $> 500,000$ | Intézményi kereskedhetőség |
| ETF | $= FALSE$ | Csak egyedi részvények |
| Has Options | $= TRUE$ | GEX számításhoz szükséges |

**Eredmény:** ~3,000 ticker

#### 5.2.2 SHORT (Zombie) Universe szűrők

| Paraméter | Feltétel | Indoklás |
|-----------|----------|----------|
| Market Cap | $> \$500,000,000$ | Shortolható méret |
| Avg Daily Volume | $> 500,000$ | Likviditás |
| Debt/Equity | $> 3.0$ | Túladósodott |
| Net Margin | $< 0$ | Veszteséges működés |
| Interest Coverage | $< 1.5$ | Nem tudja fizetni a kamatokat |

**Eredmény:** ~200 ticker (Zombie lista)

#### 5.2.3 Zombie Hunter Modul (Earnings Risk Avoidance)

**Cél:** Kizárni azokat a papírokat, amelyeknél közelgő bináris esemény (gyorsjelentés) van.

**Szabály:**
$$
\text{Ha } EarningsDate \leq Today + 5 \text{ nap} \Rightarrow \text{KIZÁRÁS}
$$

**Indoklás:** A gyorsjelentés körüli ármozgás kiszámíthatatlan (bináris kimenetel), nem illeszkedik a rendszer statisztikai előnyéhez.

---

### 5.3 Fázis 3: Sector Rotation és Momentum

**Cél:** A tőkeáramlás irányának meghatározása szektor szinten.

#### 5.3.1 Vizsgált szektorok (SPDR ETF-ek)

| ETF | Szektor | BMI Oversold | BMI Overbought |
|-----|---------|--------------|----------------|
| XLK | Technology | 12% | 85% |
| XLF | Financials | 10% | 80% |
| XLE | Energy | 10% | 75% |
| XLV | Healthcare | 12% | 80% |
| XLI | Industrials | 12% | 80% |
| XLP | Consumer Defensive | 15% | 75% |
| XLY | Consumer Cyclical | 9% | 80% |
| XLB | Basic Materials | 12% | 80% |
| XLC | Communication Services | 12% | 80% |
| XLRE | Real Estate | 9% | 85% |
| XLU | Utilities | 15% | 75% |

#### 5.3.2 Momentum Ranking számítás

Minden szektor ETF-re:

**Trend meghatározás:**
$$
Trend = 
\begin{cases} 
UP & \text{ha } Price > SMA_{20} \\
DOWN & \text{ha } Price \leq SMA_{20}
\end{cases}
$$

**Momentum (5 napos relatív teljesítmény):**
$$
Momentum_{5d} = \frac{Price_{today} - Price_{t-5}}{Price_{t-5}} \times 100
$$

**Rangsorolás:**
- Top 3 momentum → **Leader** (+15 pont bónusz)
- Bottom 3 momentum → **Laggard** (-20 pont büntetés)
- Többi → **Neutral** (0 pont)

#### 5.3.3 Sector BMI Regime

Minden szektorra külön BMI számítás (ugyanaz a képlet, de csak a szektor tickereire):

| Sector BMI | Regime | LONG döntés |
|------------|--------|-------------|
| BMI < Oversold küszöb | OVERSOLD | Engedélyezett (Mean Reversion lehetőség) |
| Oversold ≤ BMI ≤ Overbought | NEUTRAL | Engedélyezett |
| BMI > Overbought küszöb | OVERBOUGHT | VETO (nem kereskedünk) |

#### 5.3.4 Szektor Veto Mátrix (LONG stratégiában)

| Momentum | Sector BMI | Döntés | Score módosítás |
|----------|------------|--------|-----------------|
| Leader | Bármi | ENGEDÉLYEZETT | +15 |
| Neutral | NEUTRAL | ENGEDÉLYEZETT | 0 |
| Neutral | OVERSOLD | ENGEDÉLYEZETT | 0 |
| Neutral | OVERBOUGHT | **VETO** | - |
| Laggard | OVERSOLD | ENGEDÉLYEZETT (MR) | -5 |
| Laggard | NEUTRAL | **VETO** | - |
| Laggard | OVERBOUGHT | **VETO** | - |

**MR = Mean Reversion:** Laggard szektor + OVERSOLD állapot = potenciális fordulós lehetőség.

---

### 5.4 Fázis 4: Individual Stock Analysis

**Cél:** Minden átmenő ticker részletes elemzése három dimenzióban.

#### 5.4.1 Technical Analysis

**SMA Trend Filter:**
$$
TechnicalPass = 
\begin{cases} 
TRUE & \text{ha } Price > SMA_{200} \text{ (LONG)} \\
TRUE & \text{ha } Price < SMA_{200} \text{ (SHORT)} \\
FALSE & \text{különben}
\end{cases}
$$

**RSI (14 napos):**
$$
RSI_{14} = 100 - \frac{100}{1 + RS}
$$

Ahol:
$$
RS = \frac{SMA_{14}(Gains)}{SMA_{14}(Losses)}
$$

| RSI | Állapot | Pontszám módosítás |
|-----|---------|-------------------|
| RSI < 30 | Túladott | +5 (LONG) |
| 30 ≤ RSI ≤ 70 | Semleges | 0 |
| RSI > 70 | Túlvett | -5 (LONG) |

**ATR (Average True Range, 14 napos):**
$$
TR_t = \max(High_t - Low_t, |High_t - Close_{t-1}|, |Low_t - Close_{t-1}|)
$$
$$
ATR_{14} = SMA_{14}(TR)
$$

Az ATR a stop loss és position sizing alapja.

#### 5.4.2 Flow Analysis (Dark Pool & VPA)

Ez a modul keresi az intézményi lábnyomokat az ár és a volumen divergenciájában.

**RVOL (Relative Volume):**
$$
RVOL = \frac{Volume_{today}}{SMA_{20}(Volume)}
$$

| RVOL | Értelmezés | Pontszám |
|------|------------|----------|
| RVOL < 0.5 | Alacsony érdeklődés | -10 |
| 0.5 ≤ RVOL < 1.0 | Normál | 0 |
| 1.0 ≤ RVOL < 1.5 | Emelkedett | +5 |
| RVOL ≥ 1.5 | **Szignifikáns intézményi érdeklődés** | +15 |

**Spread Analysis:**
$$
Spread = High - Low
$$
$$
SpreadRatio = \frac{Spread_{today}}{SMA_{10}(Spread)}
$$

**Squat Bar Detection (Akkumuláció):**

Logika: Ha az RVOL extrém magas, de a SpreadRatio alacsony, az azt jelenti, hogy a piac "beszorult" – valaki (Market Maker vagy intézmény) minden eladást felszív anélkül, hogy az ár esne.

$$
SquatBar = 
\begin{cases} 
TRUE & \text{ha } RVOL > 2.0 \text{ ÉS } SpreadRatio < 0.9 \\
FALSE & \text{különben}
\end{cases}
$$

**Jelzés:** Rejtett Akkumuláció → +10 pont bónusz

**Dark Pool Activity (Unusual Whales):**

Ha a Dark Pool volumen > 40% a teljes napi volumenből:
$$
DarkPoolSignal = 
\begin{cases} 
BULLISH & \text{ha } DP_{buys} > DP_{sells} \\
BEARISH & \text{ha } DP_{sells} > DP_{buys} \\
NEUTRAL & \text{különben}
\end{cases}
$$

#### 5.4.3 Fundamental Scoring

**Növekedés (Growth):**
- Revenue Growth YoY: +5 ha > 10%, -5 ha < -10%
- EPS Growth YoY: +5 ha > 15%, -5 ha < -15%

**Hatékonyság (Efficiency):**
- Net Margin: +5 ha > 15%, -5 ha < 0%
- ROE: +5 ha > 15%, -5 ha < 5%

**Biztonság (Safety):**
- Debt/Equity: +5 ha < 0.5, -10 ha > 2.0
- Interest Coverage: -10 ha < 1.5

**Insider Activity:**
$$
InsiderScore = \sum_{i=1}^{30d} (BuyTransactions_i - SellTransactions_i)
$$

| Insider Score | Értelmezés | Multiplier |
|---------------|------------|------------|
| > 3 | Erős belső vásárlás | 1.25× |
| ≥ 0 | Semleges | 1.0× |
| < -3 | Erős belső eladás | 0.75× |

#### 5.4.4 Combined Score számítás

$$
CombinedScore = w_{flow} \times FlowScore + w_{funda} \times FundaScore + w_{tech} \times TechScore + SectorAdj
$$

Ahol:
- $w_{flow} = 0.40$ (40%)
- $w_{funda} = 0.30$ (30%)
- $w_{tech} = 0.30$ (30%)
- $SectorAdj$ = Leader/Laggard/MR módosítás

**Minimum küszöb:**
$$
\text{Ha } CombinedScore < 70 \Rightarrow \text{KIZÁRÁS}
$$

---

### 5.5 Fázis 5: Gamma Exposure (GEX) Analysis

**Cél:** A derivatív piac (opciók) hatásának modellezése az alaptermék árára.

#### 5.5.1 GEX elméleti háttér

A Market Makerek delta-semleges pozíciót tartanak. Amikor opciót adnak el, fedezeti ügyletet (delta hedging) kell végezniük az alaptermékben. A Gamma Exposure megmutatja, hogy egy adott árszinten mekkora fedezeti vételi/eladási kényszert jelent ez.

#### 5.5.2 GEX képlet (Strike-onként)

$$
GEX_{strike} = \Gamma \times OpenInterest \times 100 \times SpotPrice^2 \times 0.01
$$

Ahol:
- $\Gamma$ = Az opció gamma értéke (a delta változásának mértéke)
- $OpenInterest$ = Nyitott kontraktusok száma az adott strike-on
- $100$ = 1 kontraktus = 100 részvény
- $SpotPrice$ = Aktuális részvényár
- $0.01$ = Normalizálás

#### 5.5.3 Aggregált GEX metrikák

**Net GEX:**
$$
NetGEX = \sum_{strikes} GEX_{calls} - \sum_{strikes} GEX_{puts}
$$

**Call Wall:** A strike szint, ahol a legnagyobb pozitív GEX koncentrálódik.
$$
CallWall = \arg\max_{strike}(GEX_{call,strike})
$$

**Put Wall:** A strike szint, ahol a legnagyobb negatív GEX koncentrálódik.
$$
PutWall = \arg\max_{strike}(|GEX_{put,strike}|)
$$

**Zero Gamma Level:** A szint, ahol a GEX előjelet vált.
$$
ZeroGamma = strike \text{ ahol } \sum_{s \leq strike} GEX_s \approx 0
$$

#### 5.5.4 GEX Regime osztályozás

| Feltétel | Regime | Értelmezés | Multiplier |
|----------|--------|------------|------------|
| Price > ZeroGamma ÉS NetGEX > 0 | POSITIVE | Alacsony volatilitás, mágnes hatás | 1.0× |
| Price < ZeroGamma | NEGATIVE | Magas volatilitás, instabil | 0.5× |
| Átmenet környékén | HIGH_VOL | Fokozott kockázat | 0.6× |

**LONG stratégiában:**
$$
\text{Ha } GEXRegime = NEGATIVE \Rightarrow \text{KIZÁRÁS}
$$

#### 5.5.5 GEX alapú árcélok

**Take Profit 1 (elsődleges):** Call Wall szintje
$$
TP_1 = CallWall
$$

**Take Profit 2 (másodlagos):** 3× ATR
$$
TP_2 = Entry + 3 \times ATR_{14}
$$

---

### 5.6 Fázis 6: Risk Management és Position Sizing

**Cél:** Dinamikus pozícióméret meghatározása a konfidencia és kockázat alapján.

#### 5.6.1 Alap kockázat számítás

$$
BaseRisk_{USD} = AccountEquity \times RiskPerTrade_{pct}
$$

Ahol:
- $AccountEquity = \$100,000$ (példa)
- $RiskPerTrade_{pct} = 0.5\%$ (alap)

$$
BaseRisk_{USD} = 100,000 \times 0.005 = \$500
$$

#### 5.6.2 Multiplier-ek

A végső kockázatot több tényező módosítja:

| Multiplier | Feltétel | Érték |
|------------|----------|-------|
| $M_{flow}$ | FlowScore > 80 | 1.25× |
| $M_{insider}$ | InsiderScore > 3 | 1.25× |
| $M_{funda}$ | FundaScore < 60 | 0.50× |
| $M_{gex}$ | GEXRegime = NEGATIVE | 0.50× |
| $M_{gex}$ | GEXRegime = HIGH_VOL | 0.60× |
| $M_{vix}$ | VIX > 20 | $\max(0.25, 1 - (VIX-20) \times 0.02)$ |
| $M_{utility}$ | CombinedScore ≥ 85 | $1 + \frac{Score - 85}{100}$ (max 1.3×) |

#### 5.6.3 Végső kockázat és pozícióméret

$$
FinalRisk_{USD} = BaseRisk_{USD} \times M_{flow} \times M_{insider} \times M_{funda} \times M_{gex} \times M_{vix} \times M_{utility}
$$

**Stop Loss távolság (ATR alapú):**
$$
StopDistance = k \times ATR_{14}
$$

Ahol $k = 1.5$ (konfigurálható)

**Pozícióméret (darabszám):**
$$
Quantity = \left\lfloor \frac{FinalRisk_{USD}}{StopDistance} \right\rfloor
$$

#### 5.6.4 Példa számítás

```
Ticker: NVDA
AccountEquity: $100,000
BaseRisk: $500 (0.5%)
FlowScore: 85 → M_flow = 1.25
InsiderScore: 2 → M_insider = 1.0
FundaScore: 78 → M_funda = 1.0
GEXRegime: POSITIVE → M_gex = 1.0
VIX: 18 → M_vix = 1.0
CombinedScore: 88 → M_utility = 1.03

FinalRisk = $500 × 1.25 × 1.0 × 1.0 × 1.0 × 1.0 × 1.03 = $643.75

ATR_14 = $4.50
StopDistance = 1.5 × $4.50 = $6.75
Quantity = floor($643.75 / $6.75) = 95 db
```

#### 5.6.5 Sector Diversification

**Szabály:** Maximum 2 pozíció azonos szektorból.

Ha 3+ jelölt van ugyanabból a szektorból, a legalacsonyabb score-ú kiesik.

#### 5.6.6 Position Limits

| Limit típus | Érték |
|-------------|-------|
| Max pozíciók száma | 8 |
| Max pozíció/szektor | 2 |
| Max single position risk | 1.5% |
| Max gross exposure | $100,000 |
| Max single ticker exposure | $20,000 |

---

## 6. Execution Plan Output

### 6.1 CSV struktúra

A pipeline végén generált `execution_plan.csv` tartalma:

| Oszlop | Típus | Leírás |
|--------|-------|--------|
| instrument_id | string | Ticker (pl. "NVDA") |
| direction | string | "BUY" vagy "SELL" |
| order_type | string | "LMT" (limit order) |
| limit_price | float | Belépési ár |
| quantity | int | Darabszám |
| stop_loss | float | Stop loss ár |
| take_profit_1 | float | TP1 (Call Wall vagy 2×ATR) |
| take_profit_2 | float | TP2 (3×ATR) |
| risk_usd | float | Kockázat dollárban |
| score | float | Combined score |
| gex_regime | string | "POSITIVE" / "NEUTRAL" / "HIGH_VOL" |
| sector | string | GICS szektor |
| multiplier_total | float | Összes multiplier szorzata |

### 6.2 Stop Loss számítás

$$
StopLoss = Entry - (k \times ATR_{14})
$$

Ahol $k = 1.5$ (alapértelmezett)

### 6.3 Take Profit szintek

| Szint | Számítás | Cél |
|-------|----------|-----|
| TP1 | $CallWall$ vagy $Entry + 2 \times ATR$ | Elsődleges target |
| TP2 | $Entry + 3 \times ATR$ | Másodlagos target (R/R 1:3) |

### 6.4 Scale-Out szabály

$$
\text{Ha } Price \geq Entry + 2 \times ATR \Rightarrow \text{Zárás 33\%-on, Stop → Break-Even}
$$

---

## 7. Freshness Alpha (Új Szignál Bónusz)

### 7.1 Koncepció

A whitepaper kutatások alapján azok a részvények, amelyek **90 napja először** adnak vételi jelet, statisztikailag felülteljesítik a visszatérőket.

### 7.2 Implementáció

**Signal History tracking:**
- Minden nap mentésre kerül a Top 20 ticker és score
- Parquet formátum: `signal_history.parquet`

**Freshness Check:**
$$
IsFresh_i = 
\begin{cases} 
TRUE & \text{ha } LastSignalDate_i > 90 \text{ nap vagy NULL} \\
FALSE & \text{különben}
\end{cases}
$$

**Freshness Bónusz:**
$$
\text{Ha } IsFresh = TRUE \Rightarrow Score = Score \times 1.5
$$

---

## 8. Clipping Logic (Crowded Trade védelem)

### 8.1 Koncepció

A túl magas pontszám (>90) nem jobb, hanem rosszabb – mean reversion / túlhúzottság kockázata ("mindenki bullish").

### 8.2 Implementáció

$$
\text{Ha } CombinedScore > 90 \Rightarrow \text{SKIP (Crowded Trade)}
$$

**Log:** `{ticker} score {score} - TOO CROWDED (Skipping)`

---

## 9. Monitoring és Observability követelmények

### 9.1 Jelenlegi állapot (v13)

- Logfájlok (`logs/cron.log`)
- Telegram alertek (végeredmény)
- Nincs valós idejű állapot

### 9.2 Célállapot (v2.0)

| Követelmény | Leírás |
|-------------|--------|
| **Strukturált logging** | JSON formátum, kereshető mezők |
| **Pipeline Events** | Minden fázis kezdete/vége, átmenő tickerek száma |
| **Health Dashboard** | API státusz, utolsó futás, hibák |
| **Metrics** | Futásidő/fázis, ticker/másodperc, hiba arány |
| **Alerting** | Circuit breaker, API hiba, 0 szignál |

### 9.3 Event struktúra (példa)

```json
{
  "timestamp": "2026-02-04T11:30:00Z",
  "event_type": "PHASE_COMPLETE",
  "phase": "UNIVERSE_BUILDING",
  "duration_ms": 1250,
  "input_count": 10000,
  "output_count": 3000,
  "filters_applied": ["market_cap", "price", "volume", "earnings"],
  "errors": []
}
```

---

## 10. Konfiguráció egyszerűsítés

### 10.1 Jelenlegi állapot (v13)

- `config/settings.yaml` (~150 paraméter)
- Rejtett függőségek (pl. scoring weights ↔ risk multipliers)
- Nincs validáció

### 10.2 Célállapot (v2.0)

**Rétegelt konfiguráció:**

| Réteg | Tartalom | Ki módosítja |
|-------|----------|--------------|
| **Core** | Algoritmus konstansok (képletek) | Fejlesztő |
| **Tuning** | Küszöbértékek, súlyok | Operátor |
| **Runtime** | Account size, API kulcsok | Környezet |

**Validáció:**
- Induláskor minden paraméter típus és tartomány ellenőrzés
- Inkonzisztencia → hibaüzenet és HALT

---

## 11. Unusual Whales integráció terv

### 11.1 Jelenlegi állapot (Polygon)

| Adat | Forrás | Módszer |
|------|--------|---------|
| GEX | Polygon Options Snapshot | Számított (képletből) |
| Dark Pool | Polygon Aggregates | Becsült (volumen alapján) |

### 11.2 Célállapot (Unusual Whales)

| Adat | Forrás | Előny |
|------|--------|-------|
| GEX | UW `/stock/{ticker}/greeks` | Közvetlen, pontosabb |
| Dark Pool | UW `/darkpool/{ticker}` | Valós DP tranzakciók |
| Options Flow | UW `/flow/all` | Intézményi flow alerts |

### 11.3 Adapter pattern

```
┌─────────────────┐     ┌──────────────────┐
│  GEX Interface  │ ←── │  UW Adapter      │ (elsődleges)
└─────────────────┘     └──────────────────┘
         ↑                      ↓ (fallback)
         │              ┌──────────────────┐
         └───────────── │  Polygon Adapter │
                        └──────────────────┘
```

---

## 12. Jóváhagyás és következő lépések

### 12.1 Dokumentum státusz

| Szekció | Státusz | Jóváhagyó |
|---------|---------|-----------|
| 1-4. Áttekintés | DRAFT | - |
| 5. Pipeline fázisok | DRAFT | Üzleti csapat |
| 6. Execution | DRAFT | Üzleti csapat |
| 7-8. Freshness/Clipping | DRAFT | Üzleti csapat |
| 9-11. Technikai | DRAFT | Fejlesztő |

### 12.2 Következő lépések

1. **Üzleti validáció** – Csapat átnézi a 5-8. szekciót
2. **Technikai specifikáció** – Architektúra, API design, adatmodell
3. **Migrációs terv** – v13 → v2.0 átállás lépései
4. **Claude Code fejlesztés** – Specifikáció alapján

---

## Függelék A: Képlet összefoglaló

| Képlet | Definíció |
|--------|-----------|
| BMI | $SMA_{25}\left(\frac{B_t}{B_t + S_t} \times 100\right)$ |
| RVOL | $\frac{Volume_{today}}{SMA_{20}(Volume)}$ |
| GEX | $\Gamma \times OI \times 100 \times Spot^2 \times 0.01$ |
| Stop Loss | $Entry - k \times ATR_{14}$ |
| Position Size | $\lfloor \frac{FinalRisk}{StopDistance} \rfloor$ |
| VIX Multiplier | $\max(0.25, 1 - (VIX-20) \times 0.02)$ |

---

## Függelék B: Glosszárium

| Kifejezés | Definíció |
|-----------|-----------|
| **BMI** | Big Money Index – intézményi tőkeáramlás iránya |
| **GEX** | Gamma Exposure – opciós fedezeti kényszer |
| **RVOL** | Relative Volume – volumen az átlaghoz képest |
| **Call Wall** | Strike szint, ahol a legtöbb call GEX koncentrálódik |
| **Zero Gamma** | Szint, ahol a GEX előjelet vált |
| **ATR** | Average True Range – volatilitás mérőszám |
| **Zombie** | Pénzügyileg gyenge vállalat (short jelölt) |
| **Mean Reversion** | Átlaghoz visszatérés stratégia |
| **Circuit Breaker** | Automatikus kereskedés leállítás veszteség esetén |

---

*Dokumentum vége*
