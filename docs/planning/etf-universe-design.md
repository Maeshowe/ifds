# IFDS ETF Universe — Design Document

**Dátum:** 2026-02-26  
**Státusz:** Kutatási fázis lezárva — BC23 előkészítés  
**Kapcsolódó BC:** BC23 (ETF BMI Flow Intelligence, ~Q2 2026)

---

## Kontextus

A jelenlegi Phase 3 (Sector Rotation) 11 SPDR ETF-et vizsgál naponta:
- 5 napos relatív momentum alapján rangsorolja a szektorokat
- Az első 3 (Leader) szektorból választunk részvényt
- Az utolsó 3 (Laggard) szektort kizárjuk a vizsgálatból
- A közbülső szektorokra VETO mátrix dönt

Ez a struktúra production-ban fut, stabil, nem bővítjük BC23 előtt.

---

## Két Különböző Réteg — Két Különböző Cél

### Réteg 1: Intézményi Pénzáramlás (~1000 ETF)

**Mi ez:**  
Az intézményi tőke mozgásának követése a teljes ETF ökoszisztémán belül.
Hová áramlik a pénz — melyik asset class, szektor, téma, geográfia kap figyelmet.

**Cél:**  
Makró szintű flow intelligence — nem equity szelekció, hanem a piac egészének
"hőtérképe". Megelőzi a szektor rotációt, mielőtt az L1 ETF árakban megjelenne.

**Analógia:**  
MoneyFlows megközelítés (1000+ ETF aggregált flow elemzés), de IFDS-re szabva
és UW ETF flow endpoint-ra építve.

**Univerzum (~1000 ETF):**
- 11 SPDR L1 szektor ETF (alap)
- 31 IFDS L2 industry/thematic ETF (validálva)
- Size-factor ETF-ek (IWM, MDY, IJR — small/mid cap)
- Regionális / nemzetközi (EEM, VEA, FXI, EWJ stb.)
- Fixed income (TLT, IEI, HYG, IEF, LQD)
- Commodity (GLD, SLV, USO, DBA)
- Inverse / volatility (VXX, UVXY, SH, PSQ)
- Broad thematic (ARKK, BOTZ, ICLN, LIT stb.)

**API:** UW `get_etf_in_outflow()` — Basic tierben elérhető, napi aggregált flow

**BC scope:** BC23

---

### Réteg 2: Szektoros Kontextus — Equity Szelekció (42 ETF)

**Mi ez:**  
Kétszintű struktúra a jelenlegi Phase 3 mellé / után:
- **L1 (11 SPDR):** makró barométer — melyik szektor nyeri a napot (már production)
- **L2 (31 industry/thematic ETF):** finomabb jel — az L1 győztes szektoron belül
  melyik industry group / téma a legerősebb

**Cél:**  
Equity trade szelekció támogatása. Ha az XLK Leader, a SOXX vs IGV vs CIBR
megmutatja hogy semiconductor, szoftver, vagy kiberbiztonsági részvénybe érdemes-e menni.

**A granularitás amit ad:**  
`SOXX outperform XLK` → semiconductor flow erős az IT szektoron belül → 
semiconductor részvényt preferálunk az IT szektorból jövő jelöltekből.

**Jelenlegi állapot:**
- L1: ✅ Production (BC16)
- L2: ⏸ BC23-ra halasztva — komplexitás vs. haszon mérlegelés alapján

**Miért halasztva:**  
Az L2 bevezetése a Phase 3-ba érdemi komplexitást hozna (L1→L2 mapping,
momentum aggregálás, VETO logika bővítés) amely veszélyezteti a pipeline
jelenlegi, validált eredményeit. Előbb a BC17-BC22 alapokat kell lerakni.

---

## A Két Réteg Kapcsolata

```
Réteg 1 (1000 ETF flow)          Réteg 2 (42 ETF szektoros)
─────────────────────────         ──────────────────────────
"Hová megy az intézményi pénz?"   "Melyik szektorból válasszunk részvényt?"

Makró szintű megerősítés    ──→   L1 Leader szektor validálása
pl. XLK-ba flow + SOXX flow ──→   Semiconductor részvény LONG

Korai rotáció jelzés        ──→   Következő Leader szektor előrejelzése
pl. XLV-be inflow már van   ──→   Healthcare L1 hamarosan Leader lesz
```

A két réteg egymást erősíti: ha az intézményi flow (Réteg 1) és a 
szektoros momentum (Réteg 2) ugyanabba az irányba mutat, erősebb a jel.

---

## 42 ETF Univerzum — Validált Állapot (2026-02-26)

**Validáció:** `scripts/validate_etf_holdings.py` → `docs/planning/etf_holdings_validation_20260226.json`  
**Eredmény:** 42/42 OK, 100%, átl. 221ms latencia, FMP `/stable/etf/holdings`

### L1 — 11 SPDR Szektor ETF (mind YES)

| Ticker | Szektor | AUM ($M) |
|--------|---------|----------|
| XLK | Information Technology | 88,860 |
| XLF | Financials | 52,270 |
| XLE | Energy | 37,600 |
| XLV | Health Care | 41,560 |
| XLY | Consumer Discretionary | 23,760 |
| XLP | Consumer Staples | 15,890 |
| XLI | Industrials | 23,450 |
| XLB | Materials | 7,120 |
| XLC | Communication Services | 16,340 |
| XLRE | Real Estate | 5,890 |
| XLU | Utilities | 13,450 |

### L2 — 31 Industry/Thematic ETF

**YES (20 db) — Aktív, validált:**

| Ticker | Fókusz | L1 kapcsolat | AUM ($M) |
|--------|--------|--------------|----------|
| SMH | Semiconductors | XLK | 23,500 |
| SOXX | Semiconductors | XLK | 11,200 |
| IGV | Software | XLK | 5,800 |
| CIBR | Cybersecurity | XLK | 4,100 |
| KRE | Regional Banks | XLF | 3,200 |
| KBE | Banks broad | XLF | 2,100 |
| XBI | Biotech | XLV | 6,900 |
| IBB | Biotech broad | XLV | 7,200 |
| IHI | Medical Devices | XLV | 4,300 |
| XOP | Oil & Gas E&P | XLE | 3,100 |
| XME | Metals & Mining | XLB | 1,800 |
| PAVE | Infrastructure | XLI | 7,800 |
| XHB | Homebuilders | XLY | 2,100 |
| ITB | Homebuilders broad | XLY | 3,400 |
| FDN | Internet | XLK/XLC | 3,200 |
| KWEB | China Internet | XLC | 5,100 |
| BOTZ | Robotics/AI | XLK | 2,800 |
| ARKK | Disruptive Innovation | Cross | 8,900 |
| IYR | Real Estate broad | XLRE | 3,400 |
| ARKK | Disruptive Innovation | Cross | 8,900 |

**CONDITIONAL (10 db) — API OK, besorolás nyitott (BC23-ra):**

| Ticker | Fókusz | Megjegyzés |
|--------|--------|------------|
| SKYY | Cloud Computing | Átfed IGV-vel |
| HACK | Cybersecurity | Átfed CIBR-rel |
| KIE | Insurance | Egyedi IG, maradhat YES |
| XAR | Aerospace & Defense equal weight | Átfed ITA-val |
| ITA | Aerospace & Defense cap weight | Nagyobb, likvid |
| JETS | Airlines | Egyedi, maradhat YES |
| XRT | Retail | Egyedi equal weight, maradhat YES |
| TAN | Solar | Részben átfed ICLN-nel |
| ICLN | Clean Energy broad | Szélesebb mint TAN |
| LIT | Lithium / Battery | Egyedi thematic, maradhat YES |

**NO (2 db) — Likviditás miatt kizárva:**

| Ticker | Ok |
|--------|-----|
| XSD | Kis AUM, alacsony likviditás, SMH/SOXX lefedi |
| KCE | Kis AUM, KRE/KBE lefedi |

---

## Tervezett BC23 Implementáció

### 1. fázis: ETF BMI Flow Intelligence (Réteg 1)

```
UW get_etf_in_outflow() → ~1000 ETF napi flow adat
→ Flow score per ETF (beáramlás / kiáramlás normalizálva)
→ Szektor aggregálás (L1 szintre összegzés)
→ Phase 1 / Phase 3 megerősítő jel
```

**Output:** `etf_flow_regime` — melyik szektor kap intézményi pénzt

### 2. fázis: L2 Szektoros Finomítás (Réteg 2)

```
Phase 3 Leader szektorok (top 3) 
→ L1→L2 mapping alkalmazása
→ L2 ETF-ek momentum rangsorolása az adott szektoron belül
→ Részvény szelekció az erős L2 industry group-ból
```

**Példa:**
```
Phase 3 Leader: XLK (IT)
  L2 ranglista XLK-n belül:
    1. SOXX: +4.2% (5d momentum)
    2. IGV:  +2.1%
    3. CIBR: +1.8%
  → Semiconductor részvényeket preferálunk az IT jelöltek közül
```

---

## Nyitott Kérdések BC23-ra

1. **CONDITIONAL besorolás** — a 10 CONDITIONAL ETF végső YES/NO döntése
2. **Flow normalizálás** — UW ETF flow adat mértékegysége, összehasonlíthatóság
3. **L1→L2 mapping** — pontosan melyik L2 ETF melyik L1 szektorhoz tartozik
   (egyes ETF-ek cross-szektor: ARKK, BOTZ, FDN)
4. **Flow vs Momentum súlyozás** — Réteg 1 flow és Réteg 2 momentum hogyan
   kombinálódik a végső jelben
5. **Frissítési frekvencia** — ETF flow napi vs. intraday elérhetőség UW-n

---

## Kapcsolódó Fájlok

- `scripts/validate_etf_holdings.py` — FMP holdings API validátor
- `docs/planning/etf_holdings_validation_20260226.json` — Validáció eredménye
- `uploads/IFDS_ETF_GICS_Mapping.xlsx` — 42 ETF teljes GICS mapping
- `src/ifds/phases/phase3_sectors.py` — Jelenlegi Phase 3 implementáció
- `docs/planning/roadmap-2026-consolidated.md` — BC23 ütemterv

---

*Következő lépés: BC23 tervezési session (várhatóan Q2 2026, BC21 után)*
