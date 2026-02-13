# Journal: 2026-02-13 — MoneyFlows Összehasonlító Elemzés

## Session Típus
Stratégiai Elemzés — Eredet vizsgálat & Benchmark meghatározás

## Kontextus

A MoneyFlows (MAPsignals) rendszer volt az IFDS fejlesztés kiindulópontja. Ebben a session-ben áttekintettük:
- A teljes MoneyFlows portál technikai riportját (API, scoring, pipeline)
- 13 whitepaper-t (2016-2023, Cornell MFE kutatókkal)
- Outlier 50 riport (Jan 14, 2026)
- Outlier 20 riport (Feb 10, 2026)
- Weekly Flows riport (Feb 8, 2026)

Cél: meghatározni hol haladta meg az IFDS a MoneyFlows-t, hol van még tanulnivaló, és mik a SIM-L1 validációs benchmark-ok.

## Elvégzett Munka

### MoneyFlows rendszer feltérképezés
- PBO/PBD (Probable Buy Order / Probable Buy Decline) = intézményi flow detekció ár-volumen mintákból
- Compass Score (0-100) = flow + technical (10 metrika) + fundamental (12 metrika) fekete doboz
- BMI (Big Money Index) = 25-day MA az aggregált PBO/PBD arányból, 25% oversold / 80% overbought
- MAP 1400 universe = napi szűrt, intézményileg kereskedhető részvények
- Tiingo.com áradatok, MAPsignals Q.I. proprietárius flow algoritmus

### Whitepaper tanulságok
- **Boundaries (2017):** BMI 25/80 küszöbök statisztikailag szignifikánsak (Cornell validálta)
- **BFF Stocks (2016):** Compass 20/10 long-short modell szignifikáns alfa 3.5 év alatt
- **Outliers (2022):** Compass 20 az S&P 500 top 25 teljesítőjének ~50%-át azonosította évente
- **WOW Signals (2019):** Ismétlődő jelek (többszörös PBO) exponenciálisan erősebb forward return
- **New Kid in Town (2017):** Első megjelenés a Compass 20-ban a legerősebb jel
- **Information Society (2016):** PBO/PBD szélsőségek jelzik piaci mélypontokat/csúcsokat
- **Seasonality (2021):** Q4 szezonalitás + BMI kombináció javítja az időzítést
- **Sharks/Shrunk Market (2018-2019):** ETF mechanikus kereskedés torzítja a piaci struktúrát
- **Pump Up The Volume (2020):** Extrém volumen az oversold ponton konstruktív

### IFDS vs MoneyFlows összehasonlítás

#### Ahol az IFDS túlhaladta a MoneyFlows-t
1. **Adatforrás:** Közvetlen mérés (UW dark pool, options flow) vs közvetett becslés (PBO/PBD ár-volumenből)
2. **Mélység:** GEX + OBSIDIAN dealer hedge layer — MoneyFlows-ban nem létezik
3. **Risk management:** ATR bracket orders vs statikus hold period
4. **Scoring transzparencia:** IFDS combined_score minden komponens súlya explicit, MoneyFlows compass_score fekete doboz
5. **Sector breadth:** IFDS Phase 3 breadth analysis (7 regime), MoneyFlows csak szektorra szűr
6. **Dynamic sizing:** IFDS multiplier chain (flow × funda × tech × GEX × OBSIDIAN), MoneyFlows egyenlő súlyozás

#### Ahol a MoneyFlows jobb vagy van tanulnivaló
1. WOW Signals — ismétlődő magas score erősebb jel (IFDS Freshness Alpha épp bünteti)
2. BMI extreme oversold (<25%) mint agresszív vételi zóna (IFDS küszöb konzervatívabb: 35%)
3. Rotation vs Liquidation megkülönböztetés (OBSIDIAN nem különbözteti)
4. Piaci szintű Elevated Trading Volumes metrika (IFDS-ben nincs aggregált ETV)
5. ETF flow elemzés (IFDS-ben teljesen hiányzik, nem prioritás)

### Outlier 20 (Feb 10) vs IFDS BC16 (Feb 12) közvetlen összehasonlítás

MoneyFlows Top 5: COCO, TDW, NVT, CRS, PR
IFDS 8 pozíció: EPRT, CTRI, NWE, AQN, SUZ, BRX, LIN, STLD

**Kritikus eltérés — szektoreloszlás:**

| Szektor | MoneyFlows Outlier 20 | IFDS BC16 |
|---|---|---|
| Energy | 8 ticker (40%) | 0 ticker (0%) |
| Industrials | 7 ticker (35%) | 0 |
| Materials | 2 (CRS, GLW) | 2 (LIN, STLD) |
| Real Estate | 0 | 2 (EPRT, BRX) |
| Utilities | 0 | 2 (NWE, AQN) |
| Staples | 2 | 1 (SUZ) |

Az IFDS teljesen kihagyta az energy és industrials szektort, ami a MoneyFlows Top 20 75%-a.
SIM-L1 validációs kérdés: melyik tilt teljesít jobban feb 12 → márc 12?

### Outlier 50 teljesítmény (Dec 2025 → Jan 2026) — Benchmark
- Average return: +5.1% (vs SPY +1.7%) → **+3.4% alpha**
- Win rate: **66%** (33/17)
- Top 5: MU +40.4%, ACMR +33.8%, LRCX +27.1%, WT +19.4%, AEM +17.1%
- Bottom 5: VITL -14.4%, SRAD -12.9%, IMAX -10.2%, APP -8.5%, FSLR -7.6%

### Bottom 10 aszimmetria — fontos felismerés
A Broad Sector Bottom 10 veszteségek szisztematikusan nagyobbak mint a Top 20 nyereségek:
- PAR -35.6%, BETA -39.3%, KLAR -28.2%, LEGN -38.9%, LMRI -30.5%, RBRK -28.7%
A downside fáj jobban mint amennyit az upside segít → IFDS bracket order + ATR stop megközelítés kritikus előny.

### Félvezető szub-szektor dominancia
A tech szektor aggregáltan gyenge, de a félvezetők szisztematikusan felülteljesítenek:
ACMR +110.6%, TER +77.1%, MU +55.9%, STX +46.4%, LRCX +39.1%
Az IFDS Phase 2 screener szektorszinten szűr, nem szub-szektor szinten.

## Döntések

### [D1] MoneyFlows mint benchmark, nem mint modell
A MoneyFlows Outlier 50 havi teljesítménye (+3.4% alpha, 66% WR) a SIM-L1 minimum benchmark.
Ha az IFDS nem veri meg ezt, a pipeline nem jobb mint egy egyszerűbb flow-based rendszer.

### [D2] Nem veszünk át MoneyFlows komponenst
A PBO/PBD algoritmust nem kell rekonstruálni — az IFDS UW dark pool adat közvetlen mérés, jobb.
A portfolio backtesting megközelítést (buy top N, hold X months) nem vesszük át — az IFDS bracket order + ATR stop jobb.

### [D3] 8 operacionalizálható tanulság azonosítva
Lásd "Következő lépések" — mindegyik konkrét BC/SIM ticket-hez rendelhető.

## Következő Lépések

### Operacionalizálható tanulságok (prioritás sorrendben)

| # | Tanulság | Forrás | IFDS akció | Timing |
|---|---|---|---|---|
| T1 | Energy szektor gap vizsgálat | Outlier 20 Feb 10 | SIM-L1: IFDS vs MF szektor tilt | Március |
| T2 | Outlier 50 perf mint SIM-L1 min bar | Outlier 50 Jan 14 | +3% alpha, 66% WR benchmark | Már aktív |
| T3 | Bottom 10 explicit kizárási lista | Outlier 20 Bottom 10 | Phase 4 negatív szűrő | BC18-19 |
| T4 | Rotation vs Liquidation OBSIDIAN | Weekly Flows Feb 8 | inflow+outflow együttes szint | BC19 |
| T5 | BMI extreme oversold (<25%) | Boundaries paper | Agresszív sizing zóna | BC19 |
| T6 | WOW Signals: ismétlődő score | WOW paper 2019 | SimEngine L2 validáció | Q2 |
| T7 | New + Repeat Freshness Alpha | New Kid paper 2017 | SimEngine L2 | Q2 |
| T8 | Félvezető szub-szektor faktor | Outlier 20 Broad Sector | RBICS tag + relatív scoring | BC19-20 |

### Nem akció (parkolópálya)
- Szezonalitás faktor: Q4 2026-ban SimEngine backtest-ből validálni
- ETF flow elemzés: BC26 multi-strategy scope
- Piaci szintű ETV: OBSIDIAN-enrichment lehetőség, nem prioritás

## MoneyFlows Előfizetés

- **Lejárat: 2026-03-08** — nem hosszabbítjuk meg ($349/hó nem indokolt)
- Még ~3 heti riport (feb 17, feb 24, márc 3) — menteni `moneyflows_docs/`-ba
- ETF 1000 dashboard: nem elérhető (tier korlát) — saját ETF flow elemzést építünk BC26-ban
- Az IFDS saját flow adata (UW, Polygon) és scoring-ja kiváltja a MoneyFlows inputot
- A mentett riportok SIM-L1 párhuzamos benchmark-ként szolgálnak (feb 19 → márc 8)
- Filozófia: nincs fekete doboz függőség — minden faktort magunk építünk, transzparensen

## Nyitott Kérdések

1. Az IFDS energy gap szándékos (GEX/OBSIDIAN szűri) vagy hiba (Phase 3 sector rotation nem súlyozza eléggé)?
2. A Freshness Alpha logika helyes-e? WOW paper szerint ismétlődés = erősebb jel, nem gyengébb.
3. A félvezető szub-szektor tag: FMP RBICS/GICS adat elérhető a jelenlegi tier-en?
4. A Bottom 10 negatív szűrő implementáció: küszöb hol legyen? MAP <30? Tech <20%?

## Roadmap Referencia
- BC17: Factor vol + EWMA + crowdedness measurement (márc. 4)
- BC18: Crowdedness filtering aktiválás (márc. 18)
- BC19: Correlation guard + Portfolio VaR + MoneyFlows tanulságok (T3, T4, T5) (április)
- SIM-L1: Forward validation fut (feb 19+ első mérhető pont, márc. közepe első benchmark)
- SIM-L2: Replay + A/B testing (Q2) — T6, T7 validáció itt

## Hivatkozások
- MoneyFlows portál riport: `moneyflows_docs/MoneyFlows_Portal_Teljes_Riport_2026-02-13.md`
- Whitepapers: `moneyflows_docs/whitepapers/` (13 PDF)
- Outlier 50: `moneyflows_docs/Outlier50/Outlier50_Report_Jan_14_2026-fhv.pdf`
- Outlier 20: `moneyflows_docs/Outlier20_Report_Feb_10_2026-ehe.pdf`
- Weekly Flows: `moneyflows_docs/WeeklyFlows/Weekly-Flows-2-8-26-jds.pdf`
