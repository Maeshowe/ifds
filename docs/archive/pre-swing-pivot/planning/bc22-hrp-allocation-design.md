# BC22 — HRP Allokáció + Pozíciószám Bővítés — Design Document

**Státusz:** DRAFT v2 — 2026-04-03 (review feedback beépítve)
**Dátum:** 2026-04-03
**Prioritás:** P2
**Becsült effort:** ~10-12 óra CC (eredeti becslés 8h → reálisabb 10-12h)
**Scope:** Portfólió allokáció optimalizálás, pozíciószám 8→15
**Érint:** phase6_sizing.py, risk/hrp_allocator.py (ÚJ), defaults.py, models/market.py, SimEngine

**Review:** 2026-04-03, portfólió-kezelési szempontú review (v1 → v2 változások jelölve ⚡)

---

## 1. Motiváció

### Jelenlegi rendszer (BC21 utáni állapot)

```
Phase 1-5 → Top N ticker (score szerint rangsorolva, szűrve)
                ↓
Phase 6   → Multiplier chain: M_total = M_flow × M_insider × M_funda × M_gex × M_vix × M_utility × M_target
          → quantity = floor(AdjustedRisk / stop_distance)
          → Position limits: max 8, max 3/szektor, VaR < 3%
                ↓
Execution → Bracket order (MKT entry + SL + TP1)
```

**Problémák:**

1. **Naiv egyenlő kockázat-allokáció** — minden pozíció azonos base risk ($500, azaz 0.5% × $100k). A multiplier chain finomít (+/- 25-100%), de nem veszi figyelembe a pozíciók közötti korrelációt az allokációnál.

2. **Portfólió-szintű diverzifikáció hiánya** — a szektorcsoport-limitek (BC21 korrelációs guard) bináris: benne/kint. Nincs „mennyit" döntés a korreláció alapján. Ha 3 Energy ticker van (DVN, XOM, NE), mindegyik azonos risk-kel fut, holott a közöttük lévő korreláció ~0.7+ → a tényleges kockázat magasabb mint 3 × $500.

3. **8 pozíció túl kevés a diverzifikációhoz** — 8 pozícióval 1-2 szektor dominál. A paper trading adatok mutatják: gyakran 3 Energy + 3 Utilities (márc 17), vagy 5 pozíció egy szektorcsoportban. 15 pozícióval jobb szektorszórás érhető el.

4. **A HRP nem igényel expected return becslést** — csak kovariancia mátrixot. Ez pont az IFDS-hez való: az expected return becslés a leggyengébb pont a portfólió optimalizálásban, és az IFDS scoring még nem validált ehhez (az a BC24 Black-Litterman scope).

### Tervezett rendszer

```
Phase 1-5 → Top N ticker (score szerint rangsorolva, szűrve)
                ↓
Phase 6   → 1) Multiplier chain (változatlan) → combined score + risk multiplier
          → 2) HRP/HERC allokáció → optimális súlyok (korreláció alapján)
          → 3) Score-tilt: HRP súlyok × score-rank bonus → végleges súlyok
          → 4) Quantity = floor(tilted_weight × total_risk_budget / stop_distance)
          → 5) Position limits: max 15, VaR < 3%, szektorcsoport-limitek
                ↓
Execution → Bracket order (változatlan)
```

---

## 2. Előfeltételek és Indítási Kritériumok

### Hard előfeltételek (BLOKKOLÓ — ezek nélkül BC22 NEM indítható)

| # | Előfeltétel | Státusz | Megjegyzés |
|---|---|---|---|
| E1 | BC20 (SIM-L2 Mód 2) lezárva | ✅ DONE 2026-04-03 | `9cb823d` `5b96270` `037fe4c` |
| E2 | BC21 (Risk Layer) lezárva | ✅ DONE 2026-04-03 | `69bec6a` `c63ee67` |
| E3 | BC20A (Swing Hybrid Exit) lezárva | ✅ DONE 2026-04-03 | 5 fázis, 5 commit |
| E4 | Paper Trading Day 63 kiértékelés | ⏳ ~2026-05-14 | **KRITIKUS** — pozíciószám döntés |
| E5 | Swing rendszer legalább 3 hét stabil futás | ⏳ ~2026-04-28 | Hétfőtől (ápr 6) fut |
| E6 | Legalább 30 nap Phase 4 snapshot adat | ✅ ~40 nap | `state/phase4_snapshots/` |

### Soft előfeltételek (JAVASOLT — nélkülük is indítható, de kockázatos)

| # | Előfeltétel | Megjegyzés |
|---|---|---|
| S1 | Crowdedness élesítés (~ápr 7) | A crowdedness shadow adatok segítenek a HRP kovariancia becslésben |
| S2 | Skip Day Shadow kiértékelés (~máj 2) | Ha élesítjük, a pipeline logikája változik |
| S3 | GEX Call Wall TP1 Override fix (backlog) | A TP1 logika befolyásolja a P&L-t, ami a HRP validálásához kell |

### Indítási döntés logika

```
HA Day 63 kiértékelés eredménye POZITÍV (P&L javul, TP1 hit rate > 30%)
  ÉS Swing rendszer 3+ hete stabil
  ÉS Paper Trading folytatás JÓVÁHAGYVA (Tamás)
AKKOR → BC22 indítható (tervezett: ~máj 18)

HA Day 63 kiértékelés NEGATÍV (súlyos P&L romlás)
AKKOR → BC22 PARKOLT — először a scoring/exit rendszert kell javítani

HA Day 63 eredmény SEMLEGES (minimális javulás)
AKKOR → BC22 indítható, de pozíciószám bővítés SHADOW módban (számol, de nem alkalmaz)
```

---

## 3. Ütemezés

### Reális időterv

| Dátum | Esemény | Megjegyzés |
|---|---|---|
| 2026-04-06 | Swing Hybrid Exit éles indítás | Deployment checklist végrehajtása |
| 2026-04-06 → 05-14 | Paper Trading Day 33 → Day 63 | Swing rendszer tesztelés + adat gyűjtés |
| **2026-05-14** | **Day 63 kiértékelés** | **GO/NO-GO döntés** a BC22-re |
| 2026-05-18 | BC22 indítás (ha GO) | Phase 22A tervezés + implementáció |
| 2026-05-18 → 05-25 | Phase 22A — HRP Engine | ~6 óra CC |
| 2026-05-25 → 06-01 | Phase 22B — Pozíciószám bővítés | ~4 óra CC |
| 2026-06-01 → 06-08 | Shadow mode (HRP fut, de nem hat) | Validálás a jelenlegi rendszerrel párhuzamosan |
| **2026-06-08** | **HRP élesítés** (ha shadow eredmények jók) | Tamás jóváhagyás |

### Kockázat: Mi van ha Day 63 NEGATÍV?

Ha a paper trading kiértékelés negatív, BC22 nem parkol végtelen — az HRP Engine (22A) implementálható shadow módban. A pozíciószám bővítés (22B) az, ami vár a jóváhagyásra.

---

## 4. Architektúra

### 4.1. Új modul: `src/ifds/risk/hrp_allocator.py`

```python
"""Hierarchical Risk Parity / HERC Allocator — Riskfolio-Lib wrapper.

Pipeline integration point: Phase 6, AFTER scoring, BEFORE position limits.
Input:  Top N scored tickers + historikus napi return DataFrame
Output: Allokációs súlyok dict[str, float] (ticker → weight, sum ≈ 1.0)
"""

import riskfolio as rp
import pandas as pd

class HRPAllocator:
    """Wrapper a Riskfolio-Lib HCPortfolio köré, IFDS-specifikus defaultokkal."""

    def __init__(self, config: dict):
        self.model = config.get("hrp_model", "HERC")        # HRP | HERC | NCO
        self.rm = config.get("hrp_risk_measure", "CVaR")     # CVaR | MV | MAD
        self.codependence = config.get("hrp_codependence", "pearson")
        self.linkage = config.get("hrp_linkage", "ward")
        self.covariance_method = config.get("hrp_cov_method", "ledoit")
        self.min_lookback = config.get("hrp_min_lookback", 60)  # min trading days

    def calculate_weights(
        self,
        returns: pd.DataFrame,     # tickers × daily returns (60+ nap)
        scores: dict[str, float],  # ticker → combined_score (score tilt-hez)
        score_tilt: float = 0.3,   # score hatás erőssége (0 = pure HRP, 1 = pure score rank)
    ) -> dict[str, float]:
        """HRP/HERC súlyok számítása, IFDS score-tilt-tel.

        ⚡ Review: CVaR becsléshez min 60 nap return kell tickerenként.
        Ha bármelyik ticker < min_lookback napja → kizárás az HRP-ből,
        a többi ticker HRP súlyt kap, a kizárt ticker fallback (chain) risk-kel.

        Returns:
            dict[str, float] — ticker → allokációs súly (sum ≈ 1.0)
        """
        # ⚡ Review: Ticker-szintű adat validáció
        valid_tickers = [c for c in returns.columns if returns[c].dropna().shape[0] >= self.min_lookback]
        excluded_tickers = [c for c in returns.columns if c not in valid_tickers]

        if len(valid_tickers) < 10:
            raise ValueError(f"Insufficient tickers for HERC: {len(valid_tickers)} < 10 minimum")

        filtered_returns = returns[valid_tickers]
        ...

    def _apply_score_tilt(
        self,
        raw_weights: dict[str, float],
        scores: dict[str, float],
        tilt_strength: float,
    ) -> dict[str, float]:
        """Score-alapú tilt: a magasabb IFDS score-ú tickerek nagyobb súlyt kapnak.

        Módszer: z-score normalizált score × tilt_strength → súly moduláció.
        w_tilted = w_hrp × (1 + tilt_strength × z_score(combined_score))
        Utána renormalizálás (sum = 1.0).
        """
        ...
```

### 4.2. Phase 6 integrációs pont

```
JELENLEGI Phase 6 flow:
  candidates (scored) → _size_position() per ticker → _apply_position_limits() → output

ÚJ Phase 6 flow:
  candidates (scored)
    → IF hrp_enabled:
        1. Historikus return adat lekérés (Polygon, 60+ nap)
        2. HRPAllocator.calculate_weights() → súlyok
        3. _size_position_hrp() — súly-alapú méretezés
        4. _apply_position_limits() → output (változatlan)
    → ELSE:
        Jelenlegi multiplier chain (fallback)
```

A **multiplier chain NEM szűnik meg** — a HRP az allokációs súlyt adja (mennyit az összesből), a multiplierek továbbra is módosítják az adott ticker kockázatát. A kombináció:

```python
# Jelenlegi (multiplier chain only):
risk_usd = base_risk × M_total  # base_risk = $500 fix
quantity = floor(risk_usd / stop_distance)

# Új (HRP + multiplier chain):
hrp_risk_usd = total_risk_budget × hrp_weight[ticker]  # budget arányos
adjusted_risk_usd = hrp_risk_usd × M_total             # multiplier finomít
quantity = floor(adjusted_risk_usd / stop_distance)
```

Ahol `total_risk_budget = account_equity × risk_per_trade_pct × max_positions` (pl. $100k × 0.5% × 15 = $7,500). A HRP elosztja ezt a 15 ticker között, a multiplier chain módosítja.

### 4.3. Return adat forrás

A historikus return adatok forrása: **Polygon Daily Bars** (már használjuk Phase 1-ben és Phase 4-ben).

```python
# ⚡ Review: 60-90 kereskedési nap szükséges a CVaR becsléshez
# A min_lookback=60 nem a ticker szám, hanem az idősor hossz!
# (Az MMS min_periods=10 más: az egy feature store entry count, nem return history)
# 60 kereskedési nap → ~90 naptári nap lookback
# Polygon Advanced tier: aggregates endpoint, max 50k results/call
# Batch-elhető: 15 ticker × 60 nap = 900 data point → 1 API call per ticker
```

**Két adat beszerzési stratégia:**

**A) Phase 6-ban real-time lekérés** — egyszerű, de lassú (+15 API hívás)
**B) Phase 1-3 context-ben előre lekérés** — gyorsabb, de a ctx.json.gz növekszik

**Javasolt: B)** — a Phase 1-3 (22:00) context-be belekerül a return mátrix, a Phase 4-6 (15:45) csak használja. Ez konzisztens a Pipeline Split architektúrával.

### 4.4. Kovariancia becslés

| Módszer | Előny | Hátrány | Riskfolio-Lib param |
|---|---|---|---|
| **Ledoit-Wolf shrinkage** | Robusztus, stabil kis mintán (15 ticker, 60 nap) | Kissé konzervatív | `method_cov='ledoit'` |
| Historical | Egyszerű | Instabil ha N ticker > N napok | `method_cov='hist'` |
| Gerber | Korrelációt a moves irányából számol, nem magnitudeból | Kevésbé ismert | `method_cov='gerber1'` |

**Javasolt: Ledoit-Wolf** — a 15 ticker / 60 nap arány mellett a shrinkage stabilizálja a mátrixot.

### 4.5. PositionSizing modell bővítés

```python
@dataclass
class PositionSizing:
    # ... meglévő mezők ...
    hrp_weight: float = 0.0           # HRP/HERC allokációs súly (0-1)
    hrp_risk_usd: float = 0.0        # HRP-ból származó risk budget
    allocation_mode: str = "chain"    # "chain" | "hrp" — melyik rendszer méretezett
```

```python
@dataclass
class Phase6Result:
    # ... meglévő mezők ...
    hrp_enabled: bool = False
    hrp_model: str = ""               # "HRP" | "HERC"
    hrp_weights: dict = field(default_factory=dict)   # ticker → weight
    hrp_cluster_count: int = 0
    total_risk_budget: float = 0.0
    hrp_fallback_count: int = 0       # ⚡ Review: fallback gyakoriság nyomkövetés
    hrp_excluded_insufficient_data: list = field(default_factory=list)  # ⚡ tickerek < min_lookback
    hrp_sector_limit_overrides: int = 0  # ⚡ Review: hányszor írta felül a szektor-limit a HERC-et
```

---

## 5. Design Döntések

### D1: HRP vs HERC vs NCO

**Döntés:** HERC (Hierarchical Equal Risk Contribution)

**Indoklás:**
- A HRP a Marcos López de Prado eredeti modellje — egyszerű, de a klasztereken belül naiv risk parity-t használ (egyenlő kockázat-elosztás, nem optimális)
- A **HERC** a klasztereken belül is risk contribution alapján allokál — jobb diverzifikáció
- Az NCO túl komplex a jelenlegi fázishoz (klaszterenkénti mean-variance optimalizálás, μ vektort igényel)
- Riskfolio-Lib-ben `model='HERC'` egyetlen paraméter

**⚡ Review — Linkage method érzékenység:**
A HERC implementáció a linkage method-ra nagyon érzékeny (single → hosszú láncok, complete → tömör csoportok, ward → kiegyensúlyozott). A klaszter struktúra drámaian változhat linkage váltással. **A SIM-L2-ben tesztelni kell: ward vs complete vs average linkage hatása az allokációra.** A `hrp_linkage` config paraméterként elérhető, A/B variánsként futtatható.

### D2: Risk measure a klaszterezéshez

**Döntés:** CVaR (Conditional Value at Risk)

**Indoklás:**
- A standard deviation szimmetrikus — egyformán bünteti a felfelé és lefelé kilengést
- A CVaR a tail risk-re fókuszál — az IFDS kontextusban (downside protection) ez relevánsabb
- Riskfolio-Lib-ben `rm='CVaR'`

**⚡ Review — CVaR adatigény:**
A CVaR becsléshez jóval több adatpont kell, mint standard deviation-höz. A tail-ben definíció szerint kevés megfigyelés van (α=5% → 60 nap return-ből csak ~3 esik a tail-be). Ezért:
- **min_lookback = 60 kereskedési nap** (nem 10 mint az MMS min_periods!)
- Ha egy ticker < 60 nap history-val rendelkezik → kizárás az HRP-ből, multiplier chain fallback
- **Validálás a shadow módban:** a CVaR becslés stabilitása (rolling window, variance a napi újraszámítások között). Ha a CVaR értékek napi 20%+ ingadoznak → fontolóra venni a min_lookback emelését 90-re, vagy átváltást MV (standard deviation) risk measure-re
- **Fallback risk measure:** ha a CVaR túl instabil → `hrp_risk_measure_fallback: "MV"` config

### D3: Score Tilt erőssége

**Döntés:** `score_tilt = 0.3` (30% befolyás)

**Indoklás:**
- `0.0` = pure HERC (csak korreláció alapján allokál) — figyelmen kívül hagyja a pipeline scoring-ot
- `1.0` = pure score rank (a HERC lényegében kikapcsol) — visszatérünk a naiv rendszerhez
- `0.3` = a HERC adja az alapot, a score finomít — ha egy ticker 95 pontos (vs átlag 80), ~15%-kal nagyobb súlyt kap
- Ez A/B tesztelhető a SIM-L2-vel (tilt=0.0 vs 0.3 vs 0.5)

**⚡ Review — Kontextus-függőség:**
A tilt hatása piaci környezettől függ: magas korrelációs piacon (pl. a jelenlegi bearish regime, ahol minden szektor együtt mozog) a HERC kevesebb diverzifikációs lehetőséget talál → a tilt aránylag több hatást fejt ki. Alacsony korrelációs piacon a HERC aktívabban allokál → a tilt kevésbé változtat. Ez az A/B tesztek értékelésénél fontos kontextus.

### D4: Fallback stratégia

**Döntés:** Ha a HRP számítás sikertelen → jelenlegi multiplier chain

**Indoklás:**
- A Riskfolio-Lib dobhat hibát ha a return mátrix szinguláris, vagy túl kevés adat van
- A multiplier chain production-proven (30+ nap paper trading) — biztonságos fallback
- Log + Telegram alert ha fallback aktiválódik

**⚡ Review — Fallback gyakoriság monitorozás:**
A fallback aktiválódást nem elég logolni — a **gyakoriságát nyomon kell követni** mint minőségi metrika. Ha a fallback heti 2+ alkalommal aktiválódik, az a HERC input adatok minőségére utal (pl. túl sok új ticker kevés history-val, vagy szinguláris korreláció struktúra). Ilyenkor a gyökérok kezelése szükséges:
- return history hossz növelése (60 → 90 nap)
- min ticker szám emelése (10 → 12)
- visszaváltás MV-re CVaR helyett

Implementáció: `state/hrp_fallback_log.jsonl` — napi append, heti összesítés a Telegram-ben.

### D5: Pozíciószám — 8 → 15 (de NEM 20)

**Döntés:** max_positions = 15

**Indoklás:**
- 10+ ticker szükséges a HRP-hez (kevesebb tickerrel a klaszterezés nem informatív)
- 15 jó egyensúly: elég a diverzifikációhoz, de nem annyi hogy a monitoring ellenőrizhetetlen
- 20+ pozíció: $100k accounton a pozícióméretek ~$5k alá esnének → nem érdemi mozgás
- Az IBKR MAX_ORDER_SIZE=500 split logika 15 pozícióval is kezelhető
- A szektorcsoport-limitek (BC21) átskáláz: cyclical 5→8, defensive 4→6, financial 3→4, commodity 3→4

**⚡ Review — HERC vs szektor-limit interferencia:**
A HERC és a szektorcsoport-limitek interferálhatnak: ha a HERC azt mondja, hogy 3 tech tickerbe menjen a kockázat 40%-a, de a szektor-limit cap-eli → a maradék kockázatot máshova kell elosztani, ami torzíthatja az allokációt. Kezelés:

1. **Logolás:** ha a `_apply_position_limits()` egy HERC-allokált tickert kiszűr, az explicit log:
   ```
   [HERC_OVERRIDE] NVDA excluded by cyclical group limit — HERC weight was 11.2%
   ```
2. **Metrika:** `hrp_sector_limit_overrides` counter a Phase6Result-ben
3. **Ha gyakori (>3 ticker/nap):** fontolóra venni a HERC-ben constraint-ek bevezetését (`port.optimization(..., w_max=0.15, w_min=0.02)`) — így a HERC eleve figyelembe veszi a szektor-limiteket, és nem kell utólag kiszűrni

### D6: Shadow mód bevezetés

**Döntés:** 1 hét shadow → élesítés (Tamás jóváhagyás után)

**Indoklás:**
- A HRP allokáció párhuzamosan fut a multiplier chain mellett, mindkettő eredményét logoljuk
- Telegram-ben: „HRP suggest: AAPL 12.3%, MSFT 8.7% vs Current: AAPL 12.5%, MSFT 12.5%"
- 1 hét shadow adat után összehasonlítás: a HRP ajánlások visszamenőleg jobbak-e

**⚡ Review — Shadow kiértékelés mélyítése:**
Az 1 hetes shadow alatt ne **csak** a P&L-t hasonlítsuk — a HERC előnye elsősorban a kockázat-kezelésben, nem a hozamban mutatkozik. Kiértékelési dimenziók:

| Dimenzió | Mérés | Miért fontos |
|---|---|---|
| P&L | Hipotetikus HERC P&L vs tényleges chain P&L | Alapmetrika |
| **Max pozíció koncentráció** | Legnagyobb pozíció % a teljes allokációból | HERC-nek alacsonyabb kell legyen |
| **Szektordiverzifikáció** | Szektorok száma + HHI | HERC-nek jobb kell legyen |
| **Realized volatility** | Portfólió napi return szórása | HERC-nek alacsonyabb kell legyen |
| **Tail risk** | Legrosszabb nap P&L | HERC-nek kisebb drawdown |
| **CVaR stabilitás** | Napi HERC CVaR becslések szórása | Ha >20% → min_lookback emelés kell |

Shadow log formátum:
```json
{
  "date": "2026-06-02",
  "chain_pnl": -123.45,
  "hrp_hypothetical_pnl": -98.20,
  "chain_max_weight": 0.167,
  "hrp_max_weight": 0.112,
  "chain_hhi": 0.125,
  "hrp_hhi": 0.089,
  "chain_sectors": 4,
  "hrp_sectors": 6,
  "herc_cvar_daily_change_pct": 4.2
}
```

---

## 6. Fázisok és Taskok

### Phase 22A — HRP Engine (~7 óra CC — ⚡ emelve az extra validáció miatt)

| Task | Tartalom | Effort |
|---|---|---|
| 22A_1 | `riskfolio-lib` telepítés + dependency management | 0.5h |
| 22A_2 | `src/ifds/risk/hrp_allocator.py` — HRPAllocator class (HERC, CVaR, Ledoit, score tilt) | 2h |
| 22A_3 | Phase 1-3 return mátrix előkészítés (ctx.json.gz bővítés) | 1h |
| 22A_4 | Phase 6 integráció — `hrp_enabled` flag, HRP sizing path, fallback | 1.5h |
| 22A_5 | ⚡ CVaR stabilitás validáció + ticker adat guard (min_lookback) | 0.5h |
| 22A_6 | ⚡ HERC override logging + fallback frequency tracker | 0.5h |
| 22A_7 | Tesztek — HRP unit (mock returns), integration (Phase 6 end-to-end), fallback, data guard | 1h |

**22A_1 — Dependency management:**
```bash
pip install riskfolio-lib==7.2.1
# Dependencies: cvxpy, scipy, scikit-learn, statsmodels, arch (GARCH)
# Cython-compiled wheel (cp312-macosx_10_13_universal2)
# requirements.txt + Mac Mini deploy szinkron!
```

**22A_2 — HRPAllocator implementáció:**
```python
import riskfolio as rp

class HRPAllocator:
    def calculate_weights(self, returns, scores, score_tilt=0.3):
        # ⚡ Review: ticker-szintű adat validáció
        valid_cols = [c for c in returns.columns
                      if returns[c].dropna().shape[0] >= self.min_lookback]
        if len(valid_cols) < 10:
            raise ValueError(f"Insufficient tickers: {len(valid_cols)} < 10")

        port = rp.HCPortfolio(returns=returns[valid_cols])
        w = port.optimization(
            model=self.model,          # 'HERC'
            codependence=self.codependence,  # 'pearson'
            obj='MinRisk',
            rm=self.rm,                # 'CVaR'
            rf=0,
            linkage=self.linkage,      # 'ward'
            method_cov=self.covariance_method,  # 'ledoit'
            leaf_order=True,
        )
        raw_weights = w.to_dict()['weights']  # ticker → float
        if score_tilt > 0 and scores:
            return self._apply_score_tilt(raw_weights, scores, score_tilt)
        return raw_weights
```

**22A_3 — Return mátrix a context-ben:**
```python
# Phase 1-3 (22:00 CET) — _fetch_hrp_returns():
# Polygon daily bars, 90 naptári nap lookback (= ~60 kereskedési nap)
# Output: DataFrame, tickers × daily log returns
# Mentés: ctx.json.gz["hrp_returns"] (gzipped, ~5-10KB 15 tickerre)
# ⚡ Az összes ACCEPTED ticker return-jét lekérni (nem csak top 15)
#   mert a Phase 4-6 scoring változtathatja a rangsort
```

**22A_4 — Phase 6 integráció:**
```python
# phase6_sizing.py — run_phase6() kiegészítés:
hrp_enabled = config.tuning.get("hrp_enabled", False)
if hrp_enabled and hrp_returns is not None:
    allocator = HRPAllocator(config.tuning)
    scores = {s.ticker: s.combined_score for s in candidates}
    try:
        hrp_weights = allocator.calculate_weights(hrp_returns, scores)
        total_risk_budget = account_equity * risk_pct * max_positions
        for candidate in candidates:
            w = hrp_weights.get(candidate.ticker, 1.0 / len(candidates))
            candidate_risk = total_risk_budget * w * M_total[candidate.ticker]
            # ... size position with HRP risk budget
    except Exception as e:
        logger.log(FALLBACK, f"HRP failed: {e}, using multiplier chain")
        _log_fallback_event(e)  # ⚡ Review: fallback frequency tracking
        # fallback to existing logic
```

### Phase 22B — Pozíciószám Bővítés (~5 óra CC — ⚡ emelve)

| Task | Tartalom | Effort |
|---|---|---|
| 22B_1 | Config: max_positions 8→15, exposure limits recalibráció | 0.5h |
| 22B_2 | Szektorcsoport-limitek rescale (BC21 korrelációs guard) | 0.5h |
| 22B_3 | VaR threshold és risk_per_trade átszámítás | 0.5h |
| 22B_4 | IBKR bracket order management (15 × bracket = 45 order) | 0.5h |
| 22B_5 | Telegram + monitoring bővítés (15 pozíció → kompaktabb formátum) | 0.5h |
| 22B_6 | ⚡ HERC vs szektor-limit interferencia logolás + override metrika | 0.5h |
| 22B_7 | Tesztek — position limit, VaR, szektorcsoport, HERC override | 1h |
| 22B_8 | SimEngine 22B variáns — 8 vs 15 pozíció összehasonlítás | 0.5h |

**22B_1 — Config módosítások:**
```python
# defaults.py RUNTIME
"max_positions": 15,                    # volt: 8
"max_gross_exposure": 150_000,          # volt: 100_000 (15 × ~$10k avg)
"max_single_ticker_exposure": 15_000,   # volt: 20_000 (kisebb per-ticker)

# defaults.py TUNING
"risk_per_trade_pct": 0.35,             # volt: 0.5 → 15 × 0.35% = 5.25% total risk
                                         # VAGY marad 0.5% + HRP csökkenti per-ticker
```

**22B_2 — Szektorcsoport rescale:**
```python
"sector_group_max_cyclical": 8,    # volt: 5 (15/8 × 5 ≈ 9, de conservative)
"sector_group_max_defensive": 6,   # volt: 4
"sector_group_max_financial": 4,   # volt: 3
"sector_group_max_commodity": 4,   # volt: 3
"max_positions_per_sector": 4,     # volt: 3
```

**22B_3 — Risk recalibráció:**

Két lehetséges stratégia:

**A) Fix total risk budget:**
- total_risk = $100k × 5% = $5,000/nap
- 15 pozíció: ~$333/pozíció (vs jelenlegi ~$625)
- Kisebb pozíciók → kisebb per-trade P&L → stabilabb equity curve
- HRP optimalizálja az elosztást (nem egyenlő)

**B) Fix per-trade risk, nagyobb total exposure:**
- risk_per_trade marad 0.5% = $500/pozíció
- 15 × $500 = $7,500 total risk (7.5% account)
- Nagyobb drawdown potenciál, de több diverzifikáció

**Javasolt: A)** — a total risk budget maradjon kontrolláltan alacsony, a HRP ossza el. A `risk_per_trade_pct` csökken 0.5% → 0.35%, de a HERC allokáció miatt a jó tickerek nagyobb szeletet kapnak.

**Nyitott döntés (Tamás):** A vs B stratégia. A Day 63 kiértékelés eredményei alapján döntünk.

---

## 7. Kockázatok és Mitigáció

| Kockázat | Valószínűség | Hatás | Mitigáció |
|---|---|---|---|
| Riskfolio-Lib dependency conflict (cvxpy, scipy) | Közepes | Magas | Telepítés előtt `pip freeze` snapshot, venv izolálás |
| ⚡ CVaR becslés instabilitás (kevés tail adat) | Közepes | Közepes | min_lookback=60, CVaR stabilitás monitoring, MV fallback |
| HERC szinguláris mátrix (kevés ticker, kevés adat) | Alacsony | Közepes | Fallback multiplier chain + min 10 ticker guard |
| 15 pozíció → IBKR order overload (45+ bracket) | Alacsony | Magas | submit_orders.py batch delay (0.5s/order) |
| Return adat hiány (új ticker, nincs 60 nap history) | Közepes | Alacsony | Ticker kizárás az HRP-ből, multiplier chain fallback |
| Day 63 kiértékelés NEGATÍV → BC22 parkol | Közepes | Magas | Phase 22A shadow módban implementálható |
| Score tilt túl erős → visszatérünk a naiv allokációhoz | Alacsony | Közepes | A/B teszt SIM-L2-vel (tilt=0 vs 0.3 vs 0.5) |
| ⚡ HERC vs szektor-limit interferencia | Közepes | Közepes | Override logolás, constraint bevezetés ha gyakori |
| ⚡ Fallback túl gyakori (heti 2+) | Alacsony | Közepes | min_lookback emelés 90-re, MV fallback |
| Pipeline runtime növekedés (HRP számítás) | Alacsony | Alacsony | HERC 15 tickerre <1s, nem bottleneck |

---

## 8. Monitoring és Kiértékelés

### Shadow mód metrikák (1 hét)

A shadow módban a HRP allokáció fut, de a pipeline a jelenlegi multiplier chain-nel méretez. Mindkét eredményt logjuk:

```
[HRP_SHADOW] AAPL: chain_risk=$487, hrp_risk=$612 (weight=8.2%, tilt=+1.1σ)
[HRP_SHADOW] XOM: chain_risk=$487, hrp_risk=$298 (weight=4.0%, tilt=-0.7σ)
[HRP_SHADOW] Portfolio divergence: 23.4% (chain vs HRP allokáció)
```

**⚡ Review — Bővített shadow log:**
```
state/hrp_shadow.jsonl (napi append):
{
  "date": "2026-06-02",
  "chain_pnl": -123.45,
  "hrp_hypothetical_pnl": -98.20,
  "chain_max_weight": 0.167,
  "hrp_max_weight": 0.112,
  "chain_hhi": 0.125,
  "hrp_hhi": 0.089,
  "chain_sectors": 4,
  "hrp_sectors": 6,
  "hrp_realized_vol": 0.0134,
  "chain_realized_vol": 0.0158,
  "hrp_worst_day_pnl": -234.50,
  "chain_worst_day_pnl": -312.80,
  "herc_cvar_daily_change_pct": 4.2,
  "fallback_activated": false,
  "sector_limit_overrides": 1,
  "tickers_excluded_data": ["NEWT"]
}
```

### Kiértékelési metrikák (élesítés után 2 hét)

| Metrika | Mérés | Cél |
|---|---|---|
| Portfolio Sharpe Ratio | Napi return / std | Javulás vs 8-pozíciós baseline |
| Max Drawdown | % csúcstól | < 5% (jelenlegi ~2-3% csúcs) |
| Koncentrációs index | HHI (Herfindahl) | < 0.15 (8 pos: ~0.125, egyenletes) |
| ⚡ Max pozíció koncentráció | Legnagyobb pozíció % | < 12% (jelenleg ~12.5%) |
| Szektor diverzifikáció | # szektorok a portfólióban | > 5 (jelenlegi: tipikusan 3-4) |
| ⚡ Realized volatility | Portfólió napi return szórása | Alacsonyabb mint chain |
| VaR accuracy | Tényleges napi P&L vs VaR estimate | VaR átlépés < 5% a napokon |
| TP1 hit rate | Változik-e a kisebb pozíciók miatt? | Ne csökkenjen |
| HRP fallback rate | Hányszor fallback-elt a chain-re | < 5% (ritkán) |
| ⚡ CVaR stabilitás | Napi HERC CVaR becslések szórása | < 20% |
| ⚡ Szektor override rate | Szektor-limit által felülírt HERC allokációk | < 3 ticker/nap |

### Telegram bővítés

```
📊 HRP ALLOCATION (HERC, CVaR, tilt=0.3)
Clusters: 4 | Budget: $5,250
Top 3: AAPL 11.2% ($588) | MSFT 9.8% ($515) | DVN 8.1% ($425)
Bot 3: NE 3.2% ($168)  | ARMN 4.1% ($215) | PBF 4.5% ($236)
HHI: 0.089 | Sectors: 6/11 | VaR: 2.1%
⚡ Overrides: 1 (cyclical limit) | Fallback: 0 this week
```

---

## 9. Rollback terv

Ha a HRP allokáció az élesítés után 1 héten belül problémát okoz:

```python
# config.yaml:
hrp_enabled: false  # ← egyetlen flag, azonnali rollback
```

A pipeline automatikusan visszaáll a multiplier chain-re. A szektorcsoport-limitek és a VaR cap változatlanul marad (BC21). A max_positions 15→8 visszaállítása külön döntés (nem automatikus).

---

## 10. Összefoglalás — BC22 egy mondatban

A Phase 1-5 megmondja **mit** vegyünk, a multiplier chain megmondja **mennyire bízzunk benne** — a HRP/HERC megmondja **mennyit** az egyes tickerekből, a portfólió teljes kockázatának kontextusában.

---

## Appendix A — Riskfolio-Lib HCPortfolio API referencia

```python
import riskfolio as rp

port = rp.HCPortfolio(returns=returns_df)  # DataFrame: dates × tickers

w = port.optimization(
    model='HERC',              # HRP | HERC | NCO
    codependence='pearson',    # pearson | spearman | kendall | gerber1
    obj='MinRisk',             # MinRisk | Sharpe | ERC
    rm='CVaR',                 # MV | CVaR | MAD | VaR | EVaR ...
    rf=0,                      # Risk-free rate
    linkage='ward',            # single | complete | average | ward
    method_cov='ledoit',       # hist | ledoit | oas | shrunk | gl | ...
    leaf_order=True,           # Optimal Leaf Ordering
)

# w is a DataFrame with columns: 'weights', index: ticker names
# port.clusters — cluster assignments
# port.cov — covariance matrix used
```

**Verzió:** riskfolio-lib 7.2.1 (2026-02-18), Python 3.12 kompatibilis (cp312 wheel elérhető)

## Appendix B — Nyitott döntési pontok (Tamás)

| # | Döntés | Opciók | Ajánlás | Mikor kell |
|---|---|---|---|---|
| D_B1 | Risk stratégia (A vs B) | A: fix total risk 5% / B: fix per-trade 0.5% | A | Day 63 |
| D_B2 | Pozíciószám végleges | 12 / 15 / 18 | 15 | Day 63 adat |
| D_B3 | Score tilt erőssége | 0.0 / 0.3 / 0.5 | 0.3 (A/B teszt) | Phase 22A shadow |
| D_B4 | HERC vs HRP | HERC / HRP | HERC | Phase 22A |
| D_B5 | ⚡ Linkage method | ward / complete / average | ward (SIM-L2 teszt) | Phase 22A |
| D_B6 | ⚡ CVaR vs MV fallback trigger | CVaR instabilitás küszöb | 20% napi változás | Shadow hét |
| D_B7 | Élesítés jóváhagyás | GO / NO-GO | — | Shadow hét után |

## Appendix C — ⚡ Review Response Log

**Review forrás:** Portfólió-kezelési szempontú technikai review, 2026-04-03
**Reviewer megjegyzések és beépítés:**

| Review pont | Beépítve | Section |
|---|---|---|
| D1: Linkage method érzékenység — SIM-L2 teszt szükséges | ✅ D1 kiegészítés + D_B5 döntési pont | §5 D1 |
| D2: CVaR adatigény — 60-90 nap return, nem 10 | ✅ min_lookback=60, ticker guard, stabilitás monitoring | §5 D2, §4.1, §4.3 |
| D2: CVaR instabilitás → MV fallback | ✅ hrp_risk_measure_fallback config + D_B6 | §5 D2 |
| D3: Piaci kontextus-függőség | ✅ Megjegyzés az A/B teszt értékelésénél | §5 D3 |
| D4: Fallback gyakoriság tracking | ✅ hrp_fallback_log.jsonl + heti összesítés Telegram | §5 D4, §4.5 |
| D5: HERC vs szektor-limit interferencia | ✅ Override logolás + hrp_sector_limit_overrides metrika | §5 D5, §4.5, §8 |
| D5: HERC constraint-ek (w_max/w_min) ha gyakori override | ✅ Feltételes javaslat ha >3 ticker/nap | §5 D5 |
| D6: Shadow kiértékelés ne csak P&L | ✅ 6 dimenziós shadow log (koncentráció, vol, tail, CVaR stabilitás) | §5 D6, §8 |

**Becsült effort módosítás:** 8h → **12h** (a review alapján +4h extra validáció, monitoring, logging)
