# IFDS — Kereskedési Folyamat (Swing Trading Hybrid)

**Verzió:** 2.1 (Swing Hybrid Exit)
**Dátum:** 2026-02-19

---

## Mi ez a rendszer?

Az IFDS (Institutional Flow Detection System) egy automatizált részvénykiválasztó és kockázatkezelő rendszer, amely intézményi pénzáramlásokat, fundamentális mutatókat, technikai jeleket és opciós piaci adatokat kombinál, hogy 3-5 napos swing trade jelzéseket generáljon az amerikai részvénypiacon.

A rendszer nem kereskedik automatikusan — jelzéseket ad, amelyeket félautomata módon hajt végre egy IBKR paper trading számlán, emberi felügyelet mellett.

---

## Napi Működés

### Előző este (22:00 CET)

A rendszer három makroszintű elemzést végez el a nap végi végleges piaci adatokból:

**Piaci hőfok mérés (BMI):**
Kb. 3000 intézményileg kereskedhető részvény napi ár- és volumenadatából számolja a Big Money Indexet. Ez egy 25 napos mozgóátlag az akkumuláció/disztribúció arányából. Ha a BMI 25% alatt van, a piac túladott — agresszívabb vételi zóna. Ha 80% felett, túlvett — óvatosabb megközelítés.

**Szektorrotáció:**
11 SPDR szektor ETF (XLK, XLF, XLE stb.) + AGG kötvény benchmark 5 napos relatív teljesítménye alapján rangsorolja a szektorokat Leader/Neutral/Laggard kategóriákba. Szektoronként kiszámolja a szektorszintű BMI-t és a breadth mutatókat (részvények hány %-a van az SMA50/200 felett). A Laggard szektorok vétói érvényesek — onnan nem vásárolunk, kivéve ha a szektor BMI extrém túladott (mean reversion lehetőség).

**Univerzum szűrés:**
~1200 részvényből szűri le a kereskedhető univerzumot: min. $2Mrd piaci kapitalizáció, min. 500K napi forgalom, nem áll earnings bejelentés előtt a következő 3 kereskedési napon belül.

### Másnap délelőtt (15:45 CET / 9:45 ET)

15 perccel az NYSE nyitás után — amikor az opening auction lezárult és az árak stabilizálódtak — a rendszer elvégzi az egyedi részvényelemzést friss intraday adatokkal:

**Többfaktoros pontozás (~400 részvény):**
Minden részvény három dimenzió mentén kap pontot:
- **Flow score (40%):** Intézményi pénzáramlás iránya. Dark pool blokk kereskedések (UW), nagy volumenű napok iránya (Polygon), opciós flow irány.
- **Fundamentális score (30%):** Bevételnövekedés, ROE, adósság/saját tőke arány, nettó árrés, insider kereskedések (Shark signal).
- **Technikai score (30%):** RSI pozíció, relatív volumen (RVOL), buy pressure, ár pozíció az SMA20/50/200-hoz képest.

A szektorbonus/malus a Phase 3 eredménye alapján módosítja a végső pontszámot. Minimum 70 pont kell a továbbjutáshoz.

**Gamma Exposure (GEX) szűrő:**
Az opciós piac struktúráját elemzi — hol vannak a legnagyobb nyitott opciós pozíciók, és ez hogyan befolyásolja az árdinamikát. Negatív gamma környezetben (ahol a market makerek erősítik a mozgást) nem lépünk be long pozícióba.

**VWAP ellenőrzés:**
A napi VWAP (Volume Weighted Average Price) az a szint, ahol az intézményi kereskedők átlagosan vásároltak aznap. Ha az aktuális ár több mint 2%-kal a VWAP felett van, az entry túl drága — kihagyjuk. Ha a VWAP alatt vagyunk, az kedvező belépési pont.

**Pozícióméretezés:**
A végső 6-8 részvényre dinamikus pozícióméretet számol. A kockázat trade-enként a számlaméret 0.5%-a ($500 / $100K számlán). A tényleges méret egy szorzólánc eredménye:
```
Pozícióméret = Alap kockázat × Flow szorzó × Funda szorzó × GEX szorzó × VIX szorzó
```
Magas VIX (piaci félelem) → kisebb pozíciók. Erős flow + fundamentális háttér → nagyobb pozíciók.

### Order Submission (~15:48 CET)

A rendszer automatikusan beküld IBKR-be:
- **Market order** (garantált fill a stabilizálódott piaci áron)
- **Take Profit** limit order a pozíció 50%-ára: entry + 0.75× ATR
- **Stop Loss** a teljes pozícióra: entry - 1.5× ATR

### Napközbeni kereskedés

Nincs beavatkozás. Az IBKR szervere kezeli a bracket ordereket:
- Ha az ár eléri a TP1 szintet → a pozíció fele automatikusan záródik profittal
- Ha az ár eléri a SL szintet → a teljes pozíció záródik veszteséggel
- Ha egyik sem → a pozíció nyitva marad

### Nap végén (21:45 CET)

A position management script lefut:
1. **Hold day számolás:** Hányadik kereskedési napja van nyitva a pozíció?
2. **Breakeven check:** Ha a pozíció 0.3× ATR-nél többet nyert → stop loss felhúzás breakeven-re
3. **Trailing stop frissítés:** Ha a TP1 már triggered (50% zárva), a maradékra trailing stop = 1× ATR
4. **Max hold day:** Ha a pozíció 5 kereskedési napja nyitva → MOC (Market on Close) zárás
5. **Earnings check:** Ha a következő napon earnings van → azonnali zárás

---

## Kockázatkezelés

| Szabály | Érték | Cél |
|---------|-------|-----|
| Max kockázat / trade | 0.5% számlaméret | Egyetlen trade nem veszélyezteti a portfóliót |
| Max nyitott pozíció | 8 | Diverzifikáció, nem túl sok figyelendő |
| Max azonos szektorból | 2 pozíció | Szektor-koncentráció elkerülése |
| Stop Loss | 1.5× ATR | Volatilitás-adaptív, nem fix % |
| Max tartási idő | 5 kereskedési nap | Nem ragadunk bent rossz pozícióban |
| Danger zone szűrő | D/E > 5 és margin < -10% | Pénzügyileg veszélyes cégek kiszűrése |
| Circuit breaker | -$5,000 kumulatív | Ha a teljes paper trading veszteség eléri, leállás és felülvizsgálat |
| VWAP guard | >2% VWAP felett → skip | Nem veszünk túlárazott entry-t |

### ATR — Average True Range

Az ATR a részvény átlagos napi mozgásterjedelmét méri (14 napos ablak). Minden kockázatkezelési szint ehhez igazodik, nem fix százalékokhoz. Egy $50-os részvény $2-es ATR-rel és egy $200-os részvény $8-as ATR-rel azonos logikával kezelődik — a volatilitáshoz képest arányosan.

---

## Jelek Forrásai

| Adatforrás | Mit ad | Felhasználás |
|-----------|--------|-------------|
| **Polygon.io** | Ár- és volumenadatok (napi + intraday), opciós lánc | BMI, technikai score, GEX, VWAP |
| **Unusual Whales** | Dark pool tranzakciók, intézményi flow | Flow score, market sentiment |
| **FMP** | Pénzügyi kimutatások, növekedés, insider trade-ek | Fundamentális score, Shark signal |
| **FRED** | VIX, kötvényhozam (TNX) | Makro regime, VIX szorzó |

---

## Teljesítménymérés

### Paper Trading (folyamatban)
- **Időtartam:** 21 kereskedési nap (2026-02-17 → 2026-03-17)
- **Számla:** IBKR paper account (DUH118657), $100K induló tőke
- **Jelenlegi állapot:** Day 2/21, kumulatív P&L: -$46.73 (-0.05%)
- **Benchmark:** MoneyFlows Outlier 50 teljesítmény (+3% alpha, 66% win rate)

### SimEngine validáció
A rendszer tartalmaz egy szimulációs motort, amely historikus adatokon visszateszteli a jelzéseket. A paraméter sweep motor (SIM-L2) párhuzamosan futtat variánsokat (eltérő ATR szorzók, tartási idők, TP szintek) és párosított t-teszttel méri a szignifikáns különbségeket. Az első érdemi összehasonlító futtatás 2026-03-02-re tervezett (~100+ trade, 15+ kereskedési nap adata).

---

## Architektúra Áttekintés

```
┌─────────────────────────────────────────────────┐
│                    IFDS Pipeline                 │
├─────────────────────────────────────────────────┤
│                                                  │
│  22:00 CET                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Phase 1  │→ │ Phase 2  │→ │ Phase 3  │      │
│  │ BMI      │  │ Universe │  │ Sectors  │      │
│  │ Regime   │  │ Screen   │  │ Rotation │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                  │
│  15:45 CET                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Phase 4  │→ │ Phase 5  │→ │ Phase 6  │      │
│  │ Stock    │  │ GEX +    │  │ Sizing + │      │
│  │ Scoring  │  │ OBSIDIAN │  │ VWAP     │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                     │            │
│                              Execution Plan      │
│                                     │            │
│  ┌──────────────────────────────────▼──────┐    │
│  │         IBKR Paper Trading              │    │
│  │  MKT Entry → TP1 (50%) → Trail (50%)   │    │
│  │  Max 5 nap → MOC exit                  │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  21:45 CET                                       │
│  ┌─────────────────────────────────────────┐    │
│  │      Position Management                │    │
│  │  Hold tracking, Trail update, Max day   │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

## Fejlesztési Állapot

| Komponens | Státusz |
|-----------|--------|
| Pipeline Phase 1-6 | ✅ Production |
| Paper Trading (1 napos) | ✅ Működik |
| Swing Trading Hybrid Exit | 📋 Tervezés fázisban |
| VWAP modul | 📋 Tervezett |
| Position Tracker | 📋 Tervezett |
| SimEngine backtest | ✅ Működik (SIM-L1, L2 Mód 1) |
| OBSIDIAN (dealer hedge) | 🔄 Adatgyűjtés (day 4/21) |

---

*Utolsó frissítés: 2026-02-19*
